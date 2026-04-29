# betgenius-backend/workers/4_sgp_tipster_brain.py
import sys
import os
import logging
import pandas as pd
import numpy as np
import joblib
from scipy.stats import poisson
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

pd.set_option('future.no_silent_downcasting', True)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SGP-AUDITOR] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

class SGPBacktestAnalyst:
    """
    O Auditor Quantitativo (The Tipster Metamodel).
    Roda semanalmente para avaliar se as 20 Narrativas S-Tier ainda dão lucro.
    Cruza as predições do passado com o Box Score real e detecta ajustes de mercado.
    """
    def __init__(self):
        self.models_dir = Path(__file__).parent / "brain" / "models"
        self.MIN_SGP_PROB = 0.65
        
        logger.info("==================================================================")
        logger.info(" 🛡️ INICIANDO AUDITORIA QUANTITATIVA: THE 20 NARRATIVES ")
        logger.info("==================================================================")
        
        try:
            self.oracle_alpha = joblib.load(self.models_dir / "alpha_classifier_1x2.joblib")
            self.oracle_beta = joblib.load(self.models_dir / "beta_oracle_ou25.joblib")
            self.oracle_gamma = joblib.load(self.models_dir / "gamma_oracle_btts.joblib")
            self.oracle_delta = joblib.load(self.models_dir / "delta_oracle_ht.joblib")
            self.oracle_epsilon = joblib.load(self.models_dir / "epsilon_oracle_corners.joblib")
            self.oracle_zeta = joblib.load(self.models_dir / "zeta_oracle_cards.joblib")
        except Exception as e:
            logger.error(f"❌ Falha ao carregar Oráculos. Rode o retreino primeiro: {e}")
            sys.exit(1)

    async def fetch_recent_completed_matches(self) -> pd.DataFrame:
        """Puxa a Feature Store e os Resultados Reais da última janela (45 dias)."""
        await db.connect()
        async with db.pool.acquire() as conn:
            query = """
                SELECT f.*, m.home_goals, m.away_goals, m.ht_home_goals, m.ht_away_goals,
                       (m.home_corners + m.away_corners) as total_corners,
                       (m.home_yellow + m.away_yellow + (m.home_red*2) + (m.away_red*2)) as total_cards,
                       m.sport_key, th.canonical_name as home_name, ta.canonical_name as away_name
                FROM quant_ml.feature_store f
                JOIN core.matches_history m ON f.match_id = m.id
                JOIN core.teams th ON m.home_team_id = th.id
                JOIN core.teams ta ON m.away_team_id = ta.id
                WHERE m.status = 'FINISHED' 
                AND m.match_date >= CURRENT_DATE - INTERVAL '45 days'
                ORDER BY m.match_date ASC
            """
            records = await conn.fetch(query)
        await db.disconnect()
        return pd.DataFrame([dict(r) for r in records]) if records else pd.DataFrame()

    def _get_raw_probs(self, p_alpha, p_beta, p_gamma, p_delta, p_epsilon, p_zeta):
        prob_o95_corn = 1.0 - poisson.cdf(9, p_epsilon)
        prob_o45_cards = 1.0 - poisson.cdf(4, p_zeta)
        
        return {
            '1X': np.clip(p_alpha[2] + p_alpha[1], 0, 0.98),
            'X2': np.clip(p_alpha[0] + p_alpha[1], 0, 0.98),
            'HT_1X': np.clip(p_delta[2] + p_delta[1], 0, 0.98),
            'O1.5': np.clip(p_beta[1] * 1.35, 0, 0.95),
            'U3.5': np.clip(p_beta[0] * 1.30, 0, 0.95),
            'BTTS_Y': p_gamma[1],
            'BTTS_N': p_gamma[0],
            'CORN_O8.5': np.clip(prob_o95_corn * 1.20, 0, 0.90),
            'CORN_U11.5': np.clip((1 - prob_o95_corn) * 1.25, 0, 0.90),
            'CARD_U5.5': np.clip((1 - prob_o45_cards) * 1.30, 0, 0.95),
            'CARD_O4.5': np.clip(prob_o45_cards * 1.20, 0, 0.90)
        }

    def _check_leg_won(self, leg_id, h_g, a_g, t_g, ht_h, ht_a, c_corn, c_card):
        if leg_id == '1X': return h_g >= a_g
        if leg_id == 'X2': return a_g >= h_g
        if leg_id == 'HT_1X': return ht_h >= ht_a
        if leg_id == 'O1.5': return t_g > 1.5
        if leg_id == 'U3.5': return t_g < 3.5
        if leg_id == 'BTTS_Y': return h_g > 0 and a_g > 0
        if leg_id == 'BTTS_N': return h_g == 0 or a_g == 0
        if leg_id == 'CORN_O8.5': return c_corn > 8.5
        if leg_id == 'CORN_U11.5': return c_corn < 11.5
        if leg_id == 'CARD_U5.5': return c_card < 5.5
        if leg_id == 'CARD_O4.5': return c_card > 4.5
        return False

    async def run_weekly_audit(self):
        df = await self.fetch_recent_completed_matches()
        if df.empty:
            logger.warning("Nenhum dado recente de partida finalizada na Feature Store.")
            return

        # Filtra aberrações de dados base
        df = df[df['home_elo_before'] > 100].reset_index(drop=True)
        days_simulated = (df['date'].max() - df['date'].min()).days or 1

        logger.info(f"🏟️ Janela de Validação: {df['date'].min().strftime('%d/%m/%Y')} até {df['date'].max().strftime('%d/%m/%Y')} ({days_simulated} dias)")
        logger.info(f"⚙️ Processando IA em {len(df)} partidas de alta liquidez...")

        # Previsão Massiva e Vetorizada
        preds_a = self.oracle_alpha.predict_proba(df[self.oracle_alpha.feature_names_in_])
        preds_b = self.oracle_beta.predict_proba(df[self.oracle_beta.feature_names_in_])
        preds_g = self.oracle_gamma.predict_proba(df[self.oracle_gamma.feature_names_in_])
        preds_d = self.oracle_delta.predict_proba(df[self.oracle_delta.feature_names_in_])
        preds_eps = np.clip(self.oracle_epsilon.predict(df[self.oracle_epsilon.feature_names_in_]), 1.0, 25.0)
        preds_z = np.clip(self.oracle_zeta.predict(df[self.oracle_zeta.feature_names_in_]), 0.5, 12.0)

        # Registo de Resultados: Nome do Script -> {entradas, acertos, investimento (units), retorno (units)}
        script_ledger = {}

        def record_script_result(condition, name, id1, id2, corr_p, corr_o, risk_prof, real_stats):
            if condition:
                p1, p2 = probs[id1], probs[id2]
                if p1 > 0.60 and p2 > 0.60:
                    joint_p = np.clip(p1 * p2 * corr_p, 0, min(p1, p2))
                    # Simula a Odd SGP teórica que a casa ofereceria
                    sgp_odd = max((1/p1 * 1.05) * (1/p2 * 1.06) * corr_o, 1.01)

                    # Aplicar os mesmos filtros estritos da API
                    if risk_prof == 'CONSERVATIVE' and (joint_p < 0.65 or sgp_odd < 1.30 or sgp_odd > 1.65): return
                    if risk_prof == 'MODERATE' and (joint_p < 0.35 or sgp_odd < 1.66 or sgp_odd > 2.99): return
                    if risk_prof == 'AGGRESSIVE' and (joint_p < 0.10 or sgp_odd < 3.00): return

                    if name not in script_ledger:
                        script_ledger[name] = {'risk': risk_prof, 'bets': 0, 'wins': 0, 'staked': 0.0, 'returned': 0.0}
                    
                    # Verificação do bilhete na vida real
                    h_g, a_g, t_g = real_stats['h_g'], real_stats['a_g'], real_stats['t_g']
                    ht_h, ht_a = real_stats['ht_h'], real_stats['ht_a']
                    c_corn, c_card = real_stats['c_corn'], real_stats['c_card']
                    
                    won = self._check_leg_won(id1, h_g, a_g, t_g, ht_h, ht_a, c_corn, c_card) and \
                          self._check_leg_won(id2, h_g, a_g, t_g, ht_h, ht_a, c_corn, c_card)
                          
                    # Padronizamos a Stake em 1 Unidade para análise pura de ROI
                    script_ledger[name]['bets'] += 1
                    script_ledger[name]['staked'] += 1.0
                    if won:
                        script_ledger[name]['wins'] += 1
                        script_ledger[name]['returned'] += sgp_odd

        for i in range(len(df)):
            row = df.iloc[i]
            
            d_elo, d_mkt_res, d_pts = row.get('delta_elo', 0), row.get('delta_market_respect', 0), row.get('delta_pontos', 0)
            h_xg_mic, a_xg_mic = row.get('home_xg_for_ewma_micro', 0), row.get('away_xg_for_ewma_micro', 0)
            h_xg_mac, a_xg_mac = row.get('home_xg_for_ewma_macro', 0), row.get('away_xg_for_ewma_macro', 0)
            h_def_f, a_def_f = row.get('home_fraudulent_defense', 0), row.get('away_fraudulent_defense', 0)
            h_att_f, a_att_f = row.get('home_fraudulent_attack', 0), row.get('away_fraudulent_attack', 0)
            h_tens, a_tens = row.get('home_tension_index', 0), row.get('away_tension_index', 0)
            h_aggr, a_aggr = row.get('home_aggression_ewma', 0), row.get('away_aggression_ewma', 0)
            h_cs_streak, h_rest = row.get('home_clean_sheet_streak', 0), row.get('home_rest_days', 7)
            a_winless = row.get('away_winless_streak', 0)

            probs = self._get_raw_probs(preds_a[i], preds_b[i], preds_g[i], preds_d[i], preds_eps[i], preds_z[i])
            
            r_stats = {
                'h_g': row['home_goals'], 'a_g': row['away_goals'], 't_g': row['home_goals'] + row['away_goals'],
                'ht_h': row['ht_home_goals'], 'ht_a': row['ht_away_goals'],
                'c_corn': row['total_corners'], 'c_card': row['total_cards']
            }

            # ================= THE 20 SCRIPTS (Idênticos à Produção) =================
            record_script_result(d_elo > 120 and h_def_f == 0 and a_xg_mac < 1.0, "S1: O Asfixiamento", '1X', 'U3.5', 1.15, 0.85, 'CONSERVATIVE', r_stats)
            record_script_result(d_elo < -150 and h_tens > 0.80 and h_aggr > 12.0, "S2: Síndrome de Golias", 'X2', 'U3.5', 1.15, 0.85, 'CONSERVATIVE', r_stats)
            record_script_result(h_xg_mic > 1.6 and a_def_f == 0 and a_aggr < 9.5, "S3: Cerco de Escanteios", '1X', 'CORN_O8.5', 1.05, 0.95, 'CONSERVATIVE', r_stats)
            record_script_result((h_xg_mic - a_xg_mic) > 0.80 and d_mkt_res > 0.15 and h_att_f == 0, "S4: Blitzkrieg de 1ºT", 'HT_1X', 'O1.5', 1.20, 0.80, 'CONSERVATIVE', r_stats)
            record_script_result(d_elo > 200 and a_xg_mac < 0.8, "S5: Domínio Absoluto", '1X', 'BTTS_N', 1.30, 0.80, 'CONSERVATIVE', r_stats)

            record_script_result(h_xg_mic > 1.4 and a_xg_mic > 1.2 and h_def_f == 1 and a_def_f == 1, "S6: O Caos Controlado", 'O1.5', 'CORN_O8.5', 1.05, 0.95, 'MODERATE', r_stats)
            record_script_result(h_tens > 0.85 and a_tens > 0.85 and abs(d_pts) < 4, "S7: Desespero Mútuo", 'BTTS_Y', 'O1.5', 1.40, 0.65, 'MODERATE', r_stats)
            record_script_result(d_elo > 100 and h_def_f == 1 and a_xg_mic > 1.2, "S8: A Falsa Fortaleza", 'BTTS_Y', 'O1.5', 1.40, 0.65, 'MODERATE', r_stats)
            record_script_result(d_elo < -100 and a_aggr > 11.5 and a_xg_mic > 1.5, "S9: Máquina de Transição", 'X2', 'O1.5', 1.15, 0.85, 'MODERATE', r_stats)
            record_script_result(d_elo > 150 and h_def_f == 1 and a_xg_mic > 1.3, "S10: A Zebra Morde de Volta", 'X2', 'BTTS_Y', 1.40, 0.70, 'AGGRESSIVE', r_stats)

            record_script_result((h_xg_mac + a_xg_mac) < 2.1 and h_tens < 0.6, "S11: A Trincheira", 'U3.5', 'CARD_U5.5', 1.05, 0.95, 'CONSERVATIVE', r_stats)
            record_script_result(h_att_f == 1 and a_att_f == 1 and h_winless >= 3 and a_winless >= 3, "S12: A Seca Crônica", 'U3.5', 'BTTS_N', 1.35, 0.70, 'MODERATE', r_stats)
            record_script_result(h_tens < 0.20 and a_tens < 0.20 and h_aggr < 9.0 and a_aggr < 9.0, "S13: Pacto Não Agressão", 'U3.5', 'CARD_U5.5', 1.05, 0.95, 'CONSERVATIVE', r_stats)
            record_script_result(-100 < d_elo < 0 and h_cs_streak >= 2 and row.get('home_xg_against_ewma_micro', 0) < 0.85, "S14: Armadilha Visitante", '1X', 'U3.5', 1.15, 0.85, 'CONSERVATIVE', r_stats)
            record_script_result(abs(d_elo) < 50 and h_xg_mic < 1.1 and a_xg_mic < 1.1, "S15: O Jogo de Xadrez", 'HT_1X', 'U3.5', 1.15, 0.85, 'CONSERVATIVE', r_stats)

            record_script_result(d_elo > 50 and h_def_f == 1 and h_att_f == 1 and a_def_f == 0, "S16: O Falso Favorito", 'X2', 'U3.5', 1.15, 0.85, 'AGGRESSIVE', r_stats)
            record_script_result(h_xg_mac < 1.0 and h_xg_mic > 1.6 and a_def_f == 1, "S17: Efeito Novo Técnico", '1X', 'O1.5', 1.15, 0.85, 'MODERATE', r_stats)
            record_script_result(a_winless > 4 and a_xg_mic < 0.70 and h_def_f == 0, "S18: Colapso Underdog", 'HT_1X', 'BTTS_N', 1.15, 0.85, 'CONSERVATIVE', r_stats)
            record_script_result(abs(d_elo) < 50 and h_tens > 0.85 and h_aggr > 13.0 and a_aggr > 13.0, "S19: O Matadouro (Faltas)", 'BTTS_Y', 'CARD_O4.5', 1.10, 0.85, 'AGGRESSIVE', r_stats)
            record_script_result(d_elo > 150 and h_rest <= 3 and a_tens > 0.7, "S20: Exaustão Continental", 'X2', 'CARD_O4.5', 1.15, 0.80, 'AGGRESSIVE', r_stats)

        # ==================== IMPRESSÃO DO RELATÓRIO FINAL ====================
        logger.info("\n" + "="*75)
        logger.info(" [ THE TIPSTER METAMODEL: RESULTADOS DA AUDITORIA (ÚLTIMOS 45 DIAS) ] ")
        logger.info("="*75)

        total_staked = 0.0
        total_returned = 0.0

        for name, data in sorted(script_ledger.items(), key=lambda x: (x[1]['returned'] - x[1]['staked']), reverse=True):
            b, w, stk, ret = data['bets'], data['wins'], data['staked'], data['returned']
            if b == 0: continue
            
            wr = (w / b) * 100
            roi = ((ret - stk) / stk) * 100
            total_staked += stk
            total_returned += ret
            
            # Limiares de Alerta do Fundo Quant
            risk = data['risk']
            if (risk == 'CONSERVATIVE' and roi < 0) or (risk == 'MODERATE' and roi < -5) or (risk == 'AGGRESSIVE' and roi < -15):
                status = "🔴 DEGRADADO (Mercado Ajustou)"
            elif roi > 20:
                status = "🔥 HYPER-ALPHA"
            else:
                status = "🟢 OPERACIONAL"

            logger.info(f"{name:<28} | Nível: {risk[:4]} | Entradas: {b:<3} | WR: {wr:>4.1f}% | ROI: {roi:>+5.1f}% -> {status}")

        global_roi = ((total_returned - total_staked) / total_staked * 100) if total_staked > 0 else 0
        logger.info("-" * 75)
        logger.info(f"📈 VOLUME TOTAL DE SINAIS VALIDADOS: {int(total_staked)} bilhetes simulados")
        logger.info(f"💵 YIELD LÍQUIDO DO PERÍODO: {global_roi:+.2f}%")
        logger.info("="*75 + "\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(SGPBacktestAnalyst().run_weekly_audit())