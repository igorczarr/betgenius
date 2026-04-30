# betgenius-backend/engine/poisson_model.py
import logging
import asyncio
import numpy as np
from scipy.stats import poisson
from typing import Dict, Any
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from core.config import settings
from core.database import db

logger = logging.getLogger(__name__)

class PredictivePoissonEngine:
    def __init__(self, max_goals: int = 6):
        self.max_goals = max_goals
        self.goals_range = np.arange(self.max_goals + 1)
        self.i_grid, self.j_grid = np.meshgrid(self.goals_range, self.goals_range, indexing='ij')
        self.total_goals_grid = self.i_grid + self.j_grid

    @staticmethod
    def project_xg(home_attack: float, away_defense: float, home_advantage: float, league_avg: float) -> float:
        return home_attack * away_defense * home_advantage * league_avg

    @staticmethod
    def update_team_ratings(actual_goals: int, projected_xg: float, current_attack: float, current_defense: float, learning_rate: float = 0.05) -> tuple:
        error = actual_goals - projected_xg
        new_attack = current_attack + (learning_rate * error)
        new_defense = current_defense - (learning_rate * error * 0.5) 
        return max(0.1, new_attack), max(0.1, new_defense) 

    async def fetch_xg_from_db(self, home_team: str, away_team: str) -> tuple:
        """
        S-TIER: Vai à Feature Store buscar as médias móveis de chutes reais das equipas
        calculadas pelo nosso motor de Time-Travel.
        """
        logger.info(f"🗄️ Consultando Cérebro Quant (Feature Store) para: {home_team} vs {away_team}")
        
        # Puxa o último estado conhecido da equipa da Casa e de Fora
        query = """
            SELECT f.h_xg_for_micro, f.h_xg_ag_micro, f.a_xg_for_micro, f.a_xg_ag_micro
            FROM quant_ml.feature_store f
            JOIN core.matches_history m ON f.match_id = m.id
            JOIN core.teams th ON m.home_team_id = th.id
            JOIN core.teams ta ON m.away_team_id = ta.id
            WHERE th.canonical_name = $1 AND ta.canonical_name = $2
            ORDER BY m.match_date DESC LIMIT 1
        """
        
        await db.connect()
        async with db.pool.acquire() as conn:
            stats = await conn.fetchrow(query, home_team, away_team)
            
        if not stats:
            logger.warning("Falta de dados na Feature Store. Usando fallback Bayesiano.")
            return 1.35, 1.15

        # Cruzamos o Ataque da Casa contra a Defesa do Visitante e vice-versa
        home_expected_xg = ((float(stats['h_xg_for_micro']) + float(stats['a_xg_ag_micro'])) / 2) * 1.10
        away_expected_xg = ((float(stats['a_xg_for_micro']) + float(stats['h_xg_ag_micro'])) / 2) * 0.90

        return round(home_expected_xg, 2), round(away_expected_xg, 2)

    def generate_matrix(self, home_xg: float, away_xg: float, rho: float = -0.05) -> Dict[str, Any]:
        if home_xg <= 0 or away_xg <= 0:
            return None

        home_pmf = poisson.pmf(self.goals_range, home_xg)
        away_pmf = poisson.pmf(self.goals_range, away_xg)
        prob_matrix = np.outer(home_pmf, away_pmf)

        prob_matrix[0, 0] *= max(0, 1 - home_xg * away_xg * rho)
        prob_matrix[1, 0] *= max(0, 1 + home_xg * rho)
        prob_matrix[0, 1] *= max(0, 1 + away_xg * rho)
        prob_matrix[1, 1] *= max(0, 1 - rho)
        
        prob_matrix /= np.sum(prob_matrix)
        return self._extract_market_probabilities(prob_matrix)

    def _extract_market_probabilities(self, prob_matrix: np.ndarray) -> Dict[str, Any]:
        max_idx = np.unravel_index(np.argmax(prob_matrix), prob_matrix.shape)
        most_likely_score = f"{max_idx[0]} - {max_idx[1]}"

        home_win_prob = np.tril(prob_matrix, -1).sum() 
        draw_prob = np.trace(prob_matrix).sum()        
        away_win_prob = np.triu(prob_matrix, 1).sum()  

        over_2_5_mask = self.total_goals_grid > 2
        over_2_5_prob = prob_matrix[over_2_5_mask].sum()
        btts_prob = np.sum(prob_matrix[1:, 1:])

        matrix_export = np.round(prob_matrix * 100, 2).tolist()

        return {
            "heatmap_matrix": matrix_export,
            "most_likely_score": most_likely_score,
            "match_odds_probs": {
                "home": round(home_win_prob * 100, 2),
                "draw": round(draw_prob * 100, 2),
                "away": round(away_win_prob * 100, 2)
            },
            "over_2_5_prob": round(over_2_5_prob * 100, 2),
            "btts_prob": round(btts_prob * 100, 2)
        }

    async def analyze_match_value(self, home_team: str, away_team: str, live_soft_odds: dict):
        home_xg, away_xg = await self.fetch_xg_from_db(home_team, away_team)
        logger.info(f"📊 xG Consolidado Calculado: {home_team} ({home_xg}) x ({away_xg}) {away_team}")

        poisson_data = self.generate_matrix(home_xg, away_xg)
        if not poisson_data: return None

        opportunities = []
        true_prob_over = poisson_data["over_2_5_prob"] / 100.0 
        soft_odd_over = live_soft_odds.get("over_2_5")

        if soft_odd_over:
            ev_over = (true_prob_over * soft_odd_over) - 1.0
            if ev_over > 0.02: 
                opportunities.append({
                    "mercado": "Over 2.5 Gols",
                    "fair_odd": round(1 / true_prob_over, 2),
                    "soft_odd": soft_odd_over,
                    "ev_percent": round(ev_over * 100, 2)
                })

        return {
            "match": f"{home_team} x {away_team}",
            "model_data": poisson_data,
            "opportunities": opportunities
        }

ml_poisson_engine = PredictivePoissonEngine()