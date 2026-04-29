# betgenius-backend/engine/sgp_service.py
import numpy as np
import pandas as pd
import joblib
import logging
from pathlib import Path
from scipy.stats import norm, poisson

from core.database import db

logger = logging.getLogger(__name__)

class SGPCopulaEngine:
    """
    Motor de Correlação Quantitativa (Gaussian Copula).
    Calcula a Probabilidade Conjunta P(A ∩ B) de eventos não-independentes no mesmo jogo.
    """
    def __init__(self):
        self.correlation_matrix = {
            ('h2h_home', 'totals_over'): 0.30, ('h2h_home', 'totals_under'): -0.25,
            ('h2h_home', 'btts_yes'): 0.15, ('h2h_home', 'btts_no'): -0.10,
            ('h2h_away', 'totals_over'): 0.25, ('h2h_away', 'totals_under'): -0.20,
            ('totals_over', 'btts_yes'): 0.65, ('totals_under', 'btts_no'): 0.60,
            ('cards_over', 'totals_over'): 0.20, ('cards_over', 'btts_yes'): 0.15
        }

    def get_joint_probability(self, prob_A: float, prob_B: float, type_A: str, type_B: str) -> float:
        if not (0 < prob_A < 1) or not (0 < prob_B < 1): return prob_A * prob_B
        rho = self.correlation_matrix.get((type_A, type_B), self.correlation_matrix.get((type_B, type_A), 0.0))
        z_A, z_B = norm.ppf(prob_A), norm.ppf(prob_B)
        return max(0.01, min(0.99, prob_A * prob_B + rho * norm.pdf(z_A) * norm.pdf(z_B)))

class SGPService:
    """
    Microserviço S-Tier: The 20 Narratives, Cross-Game Parlays & Moonshots.
    """
    def __init__(self):
        self.copula = SGPCopulaEngine()
        self.models_dir = Path(__file__).parent.parent / "workers" / "brain" / "models"
        self.oracles = {}
        self._load_oracles()

    def _load_oracles(self):
        try:
            self.oracles['alpha'] = joblib.load(self.models_dir / "alpha_classifier_1x2.joblib")
            self.oracles['beta'] = joblib.load(self.models_dir / "beta_oracle_ou25.joblib")
            self.oracles['gamma'] = joblib.load(self.models_dir / "gamma_oracle_btts.joblib")
            self.oracles['delta'] = joblib.load(self.models_dir / "delta_oracle_ht.joblib")
            self.oracles['epsilon'] = joblib.load(self.models_dir / "epsilon_oracle_corners.joblib")
            self.oracles['zeta'] = joblib.load(self.models_dir / "zeta_oracle_cards.joblib")
            logger.info("🧠 Suíte Completa de Oráculos Carregada (Alpha a Zeta).")
        except Exception as e:
            logger.warning(f"⚠️ Oráculos incompletos. Modo Degradado ativado: {e}")

    async def get_current_bankroll(self) -> float:
        await db.connect()
        async with db.pool.acquire() as conn:
            banca = await conn.fetchval("SELECT current_balance FROM core.fund_wallets WHERE type = 'REAL' LIMIT 1")
            return float(banca) if banca else 5000.00

    async def get_match_context(self, match_id: int) -> pd.Series:
        await db.connect()
        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(f"SELECT * FROM quant_ml.feature_store WHERE match_id = {match_id}")
        if not record: return None
        return pd.Series(dict(record))

    async def get_live_market_odds(self, match_id: int) -> dict:
        live_odds = {}
        await db.connect()
        async with db.pool.acquire() as conn:
            records = await conn.fetch(f"SELECT categoria, nome_mercado, current_odd FROM core.market_odds WHERE match_id = {match_id}")
            for r in records:
                live_odds[f"{r['categoria']}_{r['nome_mercado']}"] = float(r['current_odd'])
        return live_odds

    def calculate_cross_game_probability(self, probabilities: list) -> float:
        """P(A ∩ B) para eventos independentes."""
        return np.prod(probabilities)

    def calculate_stake(self, bankroll: float, prob: float, odd: float, risk_profile: str) -> float:
        if odd <= 1.0: return 0.0
        full_kelly = (((odd - 1.0) * prob) - (1.0 - prob)) / (odd - 1.0)
        
        # Modo Loteria / Alavancagem Máxima (Ignora Kelly, aposta um troco fixo)
        if risk_profile == 'MOONSHOT':
            return round(bankroll * 0.001, 2) # 0.1% da banca estrito (Risco Mínimo, Retorno Assimétrico)

        if full_kelly <= 0: return 0.0

        # Travas Matemáticas Restritas
        if risk_profile == 'CONSERVATIVE': multiplier, max_risk = 0.25, 0.04
        elif risk_profile == 'MODERATE': multiplier, max_risk = 0.166, 0.025
        elif risk_profile == 'AGGRESSIVE': multiplier, max_risk = 0.10, 0.015
        else: multiplier, max_risk = 0.10, 0.01

        return round(bankroll * min(full_kelly * multiplier, max_risk), 2)

    def _get_raw_probs(self, X: pd.DataFrame):
        p_alpha = self.oracles['alpha'].predict_proba(X[self.oracles['alpha'].feature_names_in_])[0]
        p_beta = self.oracles['beta'].predict_proba(X[self.oracles['beta'].feature_names_in_])[0]
        p_gamma = self.oracles['gamma'].predict_proba(X[self.oracles['gamma'].feature_names_in_])[0]
        p_delta = self.oracles['delta'].predict_proba(X[self.oracles['delta'].feature_names_in_])[0]
        
        p_eps = np.clip(self.oracles['epsilon'].predict(X[self.oracles['epsilon'].feature_names_in_])[0], 1.0, 25.0)
        p_zet = np.clip(self.oracles['zeta'].predict(X[self.oracles['zeta'].feature_names_in_])[0], 0.5, 12.0)

        prob_o95_corn = 1.0 - poisson.cdf(9, p_eps)
        prob_o45_cards = 1.0 - poisson.cdf(4, p_zet)

        return {
            '1X': np.clip(p_alpha[2] + p_alpha[1], 0, 0.98), 'X2': np.clip(p_alpha[0] + p_alpha[1], 0, 0.98),
            'HT_1X': np.clip(p_delta[2] + p_delta[1], 0, 0.98),
            'O1.5': np.clip(p_beta[1] * 1.35, 0, 0.95), 'U3.5': np.clip(p_beta[0] * 1.30, 0, 0.95),
            'BTTS_Y': p_gamma[1], 'BTTS_N': p_gamma[0],
            'CORN_O8.5': np.clip(prob_o95_corn * 1.20, 0, 0.90),
            'CORN_U11.5': np.clip((1 - prob_o95_corn) * 1.25, 0, 0.90),
            'CARD_U5.5': np.clip((1 - prob_o45_cards) * 1.30, 0, 0.95),
            'CARD_O4.5': np.clip(prob_o45_cards * 1.20, 0, 0.90)
        }

    # =========================================================================
    # ROTA 1: VALIDAÇÃO DE CARRINHO (Cross-Game & SGP)
    # =========================================================================
    async def validate_cart(self, selections: list, risk_profile: str) -> dict:
        bankroll = await self.get_current_bankroll()
        if len(selections) > 5: return {"status": "error", "message": "Limite de 5 pernas para evitar variância destrutiva."}

        combined_odd = np.prod([float(s['odd']) for s in selections])
        match_ids = set([s['match_id'] for s in selections])
        
        if len(match_ids) == 1 and len(selections) == 2:
            combined_prob = self.copula.get_joint_probability(float(selections[0]['prob']), float(selections[1]['prob']), selections[0]['market'], selections[1]['market'])
        elif len(match_ids) == 1:
            combined_prob = np.prod([float(s['prob']) for s in selections]) * 1.15
        else:
            combined_prob = self.calculate_cross_game_probability([float(s['prob']) for s in selections])

        ev = (combined_prob * combined_odd) - 1.0
        
        # Em Moonshot (Loteria), nós ignoramos o EV negativo porque o prêmio é colossal e a stake é troco
        if ev <= 0 and risk_profile != 'MOONSHOT': 
            return {"status": "rejected", "ev": round(ev*100, 2), "message": "Aposta com EV Negativo bloqueada."}

        stake = self.calculate_stake(bankroll, combined_prob, combined_odd, risk_profile)
        return {
            "status": "approved", "combined_odd": round(combined_odd, 2),
            "combined_probability_pct": round(combined_prob * 100, 2),
            "expected_value_pct": round(ev * 100, 2), "recommended_stake_brl": stake, "risk_profile": risk_profile
        }

    # =========================================================================
    # ROTA 2: AS 20 NARRATIVAS (Auto-Builder Por Partida)
    # =========================================================================
    async def generate_auto_sgp(self, match_id: int) -> dict:
        ctx = await self.get_match_context(match_id)
        if ctx is None: return {"status": "error", "message": "Matriz indisponível."}
        
        bankroll = await self.get_current_bankroll()
        probs = self._get_raw_probs(pd.DataFrame([dict(ctx)]))

        d_elo, d_mkt_res, d_pts = ctx.get('delta_elo', 0), ctx.get('delta_market_respect', 0), ctx.get('delta_pontos', 0)
        h_xg_mic, a_xg_mic = ctx.get('home_xg_for_ewma_micro', 0), ctx.get('away_xg_for_ewma_micro', 0)
        h_xg_mac, a_xg_mac = ctx.get('home_xg_for_ewma_macro', 0), ctx.get('away_xg_for_ewma_macro', 0)
        h_def_f, a_def_f = ctx.get('home_fraudulent_defense', 0), ctx.get('away_fraudulent_defense', 0)
        h_att_f, a_att_f = ctx.get('home_fraudulent_attack', 0), ctx.get('away_fraudulent_attack', 0)
        h_tens, a_tens = ctx.get('home_tension_index', 0), ctx.get('away_tension_index', 0)
        h_aggr, a_aggr = ctx.get('home_aggression_ewma', 0), ctx.get('away_aggression_ewma', 0)
        h_cs_streak, h_rest = ctx.get('home_clean_sheet_streak', 0), ctx.get('home_rest_days', 7)
        a_winless = ctx.get('away_winless_streak', 0)

        valid_scripts = {'CONSERVATIVE': [], 'MODERATE': [], 'AGGRESSIVE': []}

        def try_script(condition, name, cat, id1, id2, corr_p, corr_o, risk_prof):
            if condition:
                p1, p2 = probs[id1], probs[id2]
                joint_p = np.clip(p1 * p2 * corr_p, 0, min(p1, p2))
                sgp_odd = max((1/p1 * 1.05) * (1/p2 * 1.06) * corr_o, 1.01)

                if risk_prof == 'CONSERVATIVE' and (joint_p < 0.65 or sgp_odd < 1.30 or sgp_odd > 1.65): return
                if risk_prof == 'MODERATE' and (joint_p < 0.35 or sgp_odd < 1.66 or sgp_odd > 2.99): return
                if risk_prof == 'AGGRESSIVE' and (joint_p < 0.10 or sgp_odd < 3.00): return

                stake = self.calculate_stake(bankroll, joint_p, sgp_odd, risk_prof)
                if stake > 0:
                    valid_scripts[risk_prof].append({
                        'blueprint': name, 'category': cat, 'risk_profile': risk_prof,
                        'legs': f"{id1} + {id2}", 'target_odd': round(sgp_odd, 2), 
                        'combined_probability_pct': round(joint_p * 100, 2), 'recommended_stake_brl': stake,
                        'match_id': match_id, 'p1': p1, 'p2': p2
                    })

        # BLOCO 1: DOMÍNIO E CONTROLE (Conservador)
        try_script(d_elo > 120 and h_def_f == 0 and a_xg_mac < 1.0, "O Asfixiamento", "Controle", '1X', 'U3.5', 1.15, 0.85, 'CONSERVATIVE')
        try_script(d_elo < -150 and h_tens > 0.80 and h_aggr > 12.0, "Síndrome de Golias", "Controle", 'X2', 'U3.5', 1.15, 0.85, 'CONSERVATIVE')
        try_script(h_xg_mic > 1.6 and a_def_f == 0 and a_aggr < 9.5, "Cerco de Escanteios", "Controle", '1X', 'CORN_O8.5', 1.05, 0.95, 'CONSERVATIVE')
        try_script((h_xg_mic - a_xg_mic) > 0.80 and d_mkt_res > 0.15 and h_att_f == 0, "Blitzkrieg de 1ºT", "Controle", 'HT_1X', 'O1.5', 1.20, 0.80, 'CONSERVATIVE')
        try_script(d_elo > 200 and a_xg_mac < 0.8, "Domínio Absoluto", "Controle", '1X', 'BTTS_N', 1.30, 0.80, 'CONSERVATIVE')

        # BLOCO 2: CAOS E TROCAÇÃO (Moderado)
        try_script(h_xg_mic > 1.4 and a_xg_mic > 1.2 and h_def_f == 1 and a_def_f == 1, "O Caos Controlado", "Caos", 'O1.5', 'CORN_O8.5', 1.05, 0.95, 'MODERATE')
        try_script(h_tens > 0.85 and a_tens > 0.85 and abs(d_pts) < 4, "Desespero Mútuo", "Caos", 'BTTS_Y', 'O1.5', 1.40, 0.65, 'MODERATE')
        try_script(d_elo > 100 and h_def_f == 1 and a_xg_mic > 1.2, "A Falsa Fortaleza", "Caos", 'BTTS_Y', 'O1.5', 1.40, 0.65, 'MODERATE')
        try_script(d_elo < -100 and a_aggr > 11.5 and a_xg_mic > 1.5, "Máquina de Transição", "Caos", 'X2', 'O1.5', 1.15, 0.85, 'MODERATE')
        try_script(d_elo > 150 and h_def_f == 1 and a_xg_mic > 1.3, "A Zebra Morde de Volta", "Caos", 'X2', 'BTTS_Y', 1.40, 0.70, 'AGGRESSIVE')

        # BLOCO 3: TRINCHEIRA E ESTERILIDADE (Conservador/Moderado)
        try_script((h_xg_mac + a_xg_mac) < 2.1 and h_tens < 0.6, "A Trincheira", "Esterilidade", 'U3.5', 'CARD_U5.5', 1.05, 0.95, 'CONSERVATIVE')
        try_script(h_att_f == 1 and a_att_f == 1, "A Seca Crônica", "Esterilidade", 'U3.5', 'BTTS_N', 1.35, 0.70, 'MODERATE')
        try_script(h_tens < 0.20 and a_tens < 0.20, "Pacto Não Agressão", "Esterilidade", 'U3.5', 'CARD_U5.5', 1.05, 0.95, 'CONSERVATIVE')
        try_script(-100 < d_elo < 0 and h_cs_streak >= 2 and ctx.get('home_xg_against_ewma_micro', 0) < 0.85, "Armadilha Visitante", "Esterilidade", '1X', 'U3.5', 1.15, 0.85, 'CONSERVATIVE')
        try_script(abs(d_elo) < 50 and h_xg_mic < 1.1 and a_xg_mic < 1.1, "O Jogo de Xadrez", "Esterilidade", 'HT_1X', 'U3.5', 1.15, 0.85, 'CONSERVATIVE')

        # BLOCO 4: VALOR OCULTO INSTITUCIONAL (Agressivo / Cisnes Negros)
        try_script(d_elo > 50 and h_def_f == 1 and h_att_f == 1 and a_def_f == 0, "O Falso Favorito", "Assimetria", 'X2', 'U3.5', 1.15, 0.85, 'AGGRESSIVE')
        try_script(h_xg_mac < 1.0 and h_xg_mic > 1.6 and a_def_f == 1, "Efeito Novo Técnico", "Assimetria", '1X', 'O1.5', 1.15, 0.85, 'MODERATE')
        try_script(a_winless > 4 and a_xg_mic < 0.70 and h_def_f == 0, "Colapso Underdog", "Assimetria", 'HT_1X', 'BTTS_N', 1.15, 0.85, 'CONSERVATIVE')
        try_script(abs(d_elo) < 50 and h_tens > 0.85 and h_aggr > 13.0 and a_aggr > 13.0, "O Matadouro (Faltas)", "Assimetria", 'BTTS_Y', 'CARD_O4.5', 1.10, 0.85, 'AGGRESSIVE')
        try_script(d_elo > 150 and h_rest <= 3 and a_tens > 0.7, "Exaustão Continental", "Assimetria", 'X2', 'CARD_O4.5', 1.15, 0.80, 'AGGRESSIVE')

        recommended_tickets = []
        for risk, scripts in valid_scripts.items():
            if scripts:
                best = max(scripts, key=lambda x: x['combined_probability_pct'])
                recommended_tickets.append(best)

        return {
            "match_id": match_id,
            "status": "success" if recommended_tickets else "no_value_found",
            "recommended_tickets": recommended_tickets
        }

    # =========================================================================
    # ROTA 3: MOONSHOT / ALAVANCAGEM (Multi-Game High Odds Accumulator)
    # =========================================================================
    async def generate_moonshot_parlay(self, match_ids: list) -> dict:
        """
        Caça as narrativas Agressivas em múltiplos jogos e as combina num único bilhete lotérico.
        Alavancagem brutal (Odds de 10.0 até 1000.0+).
        """
        bankroll = await self.get_current_bankroll()
        moonshot_legs = []
        combined_odd = 1.0
        combined_prob = 1.0

        for m_id in match_ids:
            sgp_data = await self.generate_auto_sgp(m_id)
            if sgp_data['status'] == 'success':
                # Filtra apenas o bilhete AGGRESSIVE deste jogo
                agg_ticket = next((t for t in sgp_data['recommended_tickets'] if t['risk_profile'] == 'AGGRESSIVE'), None)
                if agg_ticket:
                    moonshot_legs.append(agg_ticket)
                    combined_odd *= agg_ticket['target_odd']
                    combined_prob *= (agg_ticket['combined_probability_pct'] / 100)
            
            # Trava matemática para não virar doação de dinheiro às casas de apostas (> 6 pernas agressivas)
            if len(moonshot_legs) >= 6: break

        if len(moonshot_legs) < 2:
            return {"status": "rejected", "message": "Jogos insuficientes com perfil agressivo para montar alavancagem."}

        # Aposta de Troco: 0.1% a 0.5% da banca
        stake = self.calculate_stake(bankroll, combined_prob, combined_odd, 'MOONSHOT')

        return {
            "status": "approved",
            "blueprint": "ALAVANCAGEM: KAMIKAZE ACCUMULATOR",
            "risk_profile": "MOONSHOT",
            "combined_odd": round(combined_odd, 2),
            "combined_probability_pct": round(combined_prob * 100, 4),
            "recommended_stake_brl": stake,
            "legs": moonshot_legs
        }

if __name__ == "__main__":
    import asyncio
    import json
    
    async def test():
        service = SGPService()
        print("--- TESTE SINGLE SGP ---")
        res1 = await service.generate_auto_sgp(1)
        print(json.dumps(res1, indent=4, ensure_ascii=False))
        
        print("\n--- TESTE MOONSHOT PARLAY (IDs 1, 2, 3) ---")
        res2 = await service.generate_moonshot_parlay([1, 2, 3])
        print(json.dumps(res2, indent=4, ensure_ascii=False))

    asyncio.run(test())