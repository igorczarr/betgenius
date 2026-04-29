# betgenius-backend/engine/inference_engine.py

import sys
import os
import io

# =====================================================================
# BLINDAGEM DE ENCODING PARA WINDOWS E CARREGAMENTO DO .ENV
# =====================================================================
if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import asyncio
import logging
import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

pd.set_option('future.no_silent_downcasting', True)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db
import redis.asyncio as redis
from core.config import settings

# Terminal Limpo, Padrão Bloomberg
logging.basicConfig(level=logging.INFO, format="%(asctime)s [INFERENCE-ENGINE] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

class MasterInferenceEngine:
    """
    O Oráculo Definitivo (Substitui predict_today e live_value_scanner).
    Utiliza o modelo XGBoost Alpha (1X2) treinado na Feature Store para varrer
    os jogos das próximas 48h, cruzar com as Odds e gritar as apostas +EV via Redis e PostgreSQL.
    """
    def __init__(self):
        self.models_dir = BASE_DIR / "brain" / "models"
        self.alpha_model_path = self.models_dir / "alpha_oracle_1x2.joblib"
        self.model = None
        self.redis_client = None

        # Parâmetros Estritos de Operação Quantitativa
        self.MIN_EV_THRESHOLD = 0.05   # Requeremos pelo menos 5% de Edge Real
        self.MAX_EV_THRESHOLD = 0.35   # Ignora ilusões estatísticas de 50%+ (armadilhas)
        self.MIN_PROB_WIN = 0.35       # A IA tem que ter pelo menos 35% de certeza que vai bater
        self.KELLY_FRACTION = 0.25     # Quarter Kelly (Proteção de Banca)
        
        # A Assinatura de DNA exata que o Alpha Oracle (2a) exige
        self.features = [
            'delta_elo', 'delta_wage_pct', 'delta_pontos', 'delta_posicao', 
            'delta_market_respect', 'delta_tension', 
            'delta_xg_micro', 'delta_xg_macro',
            'home_elo_before', 'away_elo_before',
            'home_pts_before', 'away_pts_before',
            'pos_tabela_home', 'pos_tabela_away',
            'home_xg_for_ewma_micro', 'home_xg_against_ewma_micro',
            'away_xg_for_ewma_micro', 'away_xg_against_ewma_micro',
            'home_xg_for_ewma_macro', 'away_xg_for_ewma_macro',
            'home_aggression_ewma', 'away_aggression_ewma', 
            'home_win_streak', 'home_winless_streak', 'home_clean_sheet_streak',
            'away_win_streak', 'away_winless_streak', 'away_clean_sheet_streak',
            'home_fraudulent_defense', 'home_fraudulent_attack',
            'away_fraudulent_defense', 'away_fraudulent_attack'
        ]

    async def connect(self):
        self.redis_client = await redis.from_url(settings.REDIS_URL)
        await db.connect()

    def _load_brain(self):
        if not self.alpha_model_path.exists():
            logger.error(f"❌ Cérebro não encontrado: {self.alpha_model_path}. Treine o Alpha Oracle primeiro (2a_model_alpha.py).")
            sys.exit(1)
        self.model = joblib.load(self.alpha_model_path)

    def _remove_overround(self, odd_h: float, odd_d: float, odd_a: float):
        """Remove a margem de lucro da casa de apostas para revelar a 'True Odd' do mercado."""
        if odd_h <= 1.0 or odd_d <= 1.0 or odd_a <= 1.0:
            return 0.0, 0.0, 0.0
        margin = (1.0/odd_h) + (1.0/odd_d) + (1.0/odd_a)
        return (1.0/odd_h)/margin, (1.0/odd_d)/margin, (1.0/odd_a)/margin

    def _calculate_kelly_stake(self, prob: float, odd: float) -> float:
        """Determina a fatia da banca baseada no Kelly Criterion (fator = 0.25)."""
        if odd <= 1.0: return 0.0
        b = odd - 1.0
        q = 1.0 - prob
        kelly_fraction = ((b * prob) - q) / b
        return max(0.0, kelly_fraction * self.KELLY_FRACTION)

    async def scan_and_predict(self):
        print("\n" + "="*90)
        print(" 🌐 INICIANDO RADAR PANÓPTICO: Scanner de Valor e Auditoria de Jogos (XGBoost Alpha)")
        print("="*90 + "\n")

        self._load_brain()
        await self.connect()

        try:
            async with db.pool.acquire() as conn:
                # Buscamos a Tabela Matriz, cruzada com os Nomes e Odds Atuais
                query = """
                    SELECT f.*, 
                           th.canonical_name as home_team, ta.canonical_name as away_team,
                           m.sport_key,
                           o_home.current_odd as live_odd_home, 
                           o_draw.current_odd as live_odd_draw, 
                           o_away.current_odd as live_odd_away
                    FROM quant_ml.feature_store f
                    JOIN core.matches_history m ON f.match_id = m.id
                    JOIN core.teams th ON m.home_team_id = th.id
                    JOIN core.teams ta ON m.away_team_id = ta.id
                    LEFT JOIN core.market_odds o_home ON m.id = o_home.match_id AND o_home.bookmaker = 'bet365' AND o_home.nome_mercado IN ('1', 'home')
                    LEFT JOIN core.market_odds o_draw ON m.id = o_draw.match_id AND o_draw.bookmaker = 'bet365' AND o_draw.nome_mercado IN ('x', 'draw')
                    LEFT JOIN core.market_odds o_away ON m.id = o_away.match_id AND o_away.bookmaker = 'bet365' AND o_away.nome_mercado IN ('2', 'away')
                    WHERE m.status = 'SCHEDULED' 
                    AND m.match_date >= CURRENT_DATE 
                    AND m.match_date <= CURRENT_DATE + INTERVAL '2 days'
                """
                records = await conn.fetch(query)

                if not records:
                    logger.warning("⚠️ Nenhum jogo agendado (com features) para as próximas 48h. A Matrix está vazia ou sem novos jogos.")
                    return

                df = pd.DataFrame([dict(r) for r in records])
                logger.info(f"🔎 Processando {len(df)} eventos agendados...\n")

                # Higienização de tipos para evitar crash do modelo
                for col in self.features:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

                # Previsão Multi-Classe (0=Away, 1=Draw, 2=Home)
                X_pred = df[self.features]
                probs = self.model.predict_proba(X_pred)
                
                df['prob_away'] = probs[:, 0]
                df['prob_draw'] = probs[:, 1]
                df['prob_home'] = probs[:, 2]

                opportunities_found = 0
                records_to_insert = []

                # Percorre jogo a jogo avaliando as assimetrias
                for _, row in df.iterrows():
                    match_id = int(row['match_id'])
                    home_team = row['home_team']
                    away_team = row['away_team']
                    
                    odd_h = float(row['live_odd_home']) if pd.notna(row['live_odd_home']) else 0.0
                    odd_d = float(row['live_odd_draw']) if pd.notna(row['live_odd_draw']) else 0.0
                    odd_a = float(row['live_odd_away']) if pd.notna(row['live_odd_away']) else 0.0

                    print("-" * 90)
                    print(f"⚽ {home_team} vs {away_team} | {row['sport_key']}")
                    
                    if odd_h <= 1.0 or odd_d <= 1.0 or odd_a <= 1.0:
                        print("🏦 BET365 ODDS    : [Aguardando abertura de mercado]")
                        print("🔴 [PASS] -> Sem dados suficientes para calcular EV.\n")
                        continue

                    p_h, p_d, p_a = row['prob_home'], row['prob_draw'], row['prob_away']

                    print(f"⚖️ TRUE ODDS (IA) : Home @ {1/p_h:.2f} ({p_h:.1%}) | Draw @ {1/p_d:.2f} ({p_d:.1%}) | Away @ {1/p_a:.2f} ({p_a:.1%})")
                    print(f"🏦 BET365 ODDS    : Home @ {odd_h:.2f} | Draw @ {odd_d:.2f} | Away @ {odd_a:.2f}")

                    # Remove o Overround (Margem da casa) para calcular o EV corretamente
                    true_m_h, true_m_d, true_m_a = self._remove_overround(odd_h, odd_d, odd_a)

                    ev_h = (p_h * true_m_h) - 1.0
                    ev_d = (p_d * true_m_d) - 1.0
                    ev_a = (p_a * true_m_a) - 1.0

                    print(f"📈 EXPECTED VALUE : Home {ev_h*100:.1f}% | Draw {ev_d*100:.1f}% | Away {ev_a*100:.1f}%")

                    target_market = None
                    target_ev = 0.0
                    target_prob = 0.0
                    target_odd = 0.0

                    # O Robô decide atirar onde a vantagem é maior e mais segura
                    if self.MIN_EDGE_THRESHOLD < ev_h < self.MAX_EV_THRESHOLD and p_h >= self.MIN_PROB_WIN:
                        target_market, target_ev, target_prob, target_odd = "Home", ev_h, p_h, odd_h
                        print(f"🟢 [SINAL] -> APOSTAR HOME (+EV de {ev_h*100:.1f}%)")
                    elif self.MIN_EDGE_THRESHOLD < ev_a < self.MAX_EV_THRESHOLD and p_a >= self.MIN_PROB_WIN:
                        target_market, target_ev, target_prob, target_odd = "Away", ev_a, p_a, odd_a
                        print(f"🟢 [SINAL] -> APOSTAR AWAY (+EV de {ev_a*100:.1f}%)")
                    else:
                        print("🔴 [PASS] -> Mercado eficiente ou variância muito alta.")

                    is_value_bet = bool(target_market is not None)

                    records_to_insert.append((
                        match_id, round(p_h, 4), round(p_d, 4), round(p_a, 4), 
                        round(ev_h, 4), round(ev_a, 4), is_value_bet
                    ))

                    if is_value_bet:
                        opportunities_found += 1
                        stake_pct = self._calculate_kelly_stake(target_prob, target_odd)
                        
                        # Formatando Payload para o ViewRadar (Vue.js Front-End)
                        payload = {
                            "hora": datetime.now().strftime("%H:%M:%S"),
                            "jogo": f"{home_team} x {away_team}",
                            "mercado": f"Vencedor: {target_market}",
                            "pinOpen": "N/A",
                            "pinClose": "N/A",
                            "trueOdd": round(1.0/target_prob, 2),
                            "softOdd": target_odd,
                            "bookie": "Bet365",
                            "ev": round(target_ev * 100, 2),
                            "kelly": round(stake_pct * 100, 2),
                            "sport": row['sport_key']
                        }

                        # Envia para o Front-End piscar na tela
                        await self.redis_client.publish("betgenius:stream:opportunities", json.dumps(payload))

                print()
                print("="*90)
                print(f"🏆 RESUMO: {opportunities_found} Assimetrias Institucionais Disparadas pro Dashboard.")
                print("="*90 + "\n")

                if records_to_insert:
                    # Registramos no Banco de Dados para controle do Gestor
                    await conn.executemany("""
                        INSERT INTO quant_ml.predictions 
                        (match_id, prob_home, prob_draw, prob_away, ev_home, ev_away, is_value_bet, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                        ON CONFLICT (match_id) DO UPDATE SET
                            prob_home=EXCLUDED.prob_home, prob_draw=EXCLUDED.prob_draw, prob_away=EXCLUDED.prob_away,
                            ev_home=EXCLUDED.ev_home, ev_away=EXCLUDED.ev_away, is_value_bet=EXCLUDED.is_value_bet, updated_at=NOW()
                    """, records_to_insert)

        except Exception as e:
            logger.error(f"❌ Falha Crítica na Inferência Preditiva: {e}")
        finally:
            await db.disconnect()
            if self.redis_client:
                await self.redis_client.aclose()

if __name__ == "__main__":
    # Ajuste para evitar erro de atributos caso rode independentemente antes do __init__ completo
    MasterInferenceEngine.MIN_EDGE_THRESHOLD = 0.05
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(MasterInferenceEngine().scan_and_predict())