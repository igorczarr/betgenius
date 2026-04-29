# betgenius-backend/workers/sgp_builder.py
import asyncio
import logging
import pandas as pd
import numpy as np
import joblib
import sys
from pathlib import Path
from scipy.stats import norm

# Adiciona o backend ao path para importações
sys.path.append(str(Path(__file__).parent.parent))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SGP-BUILDER] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class SGPCopulaEngine:
    """
    Motor de Correlação Quantitativa (Gaussian Copula).
    Calcula a Probabilidade Conjunta P(A ∩ B) de eventos não-independentes no futebol.
    """
    def __init__(self):
        # Matriz de Correlação Institucional (Rho ρ)
        # Ex: Vitória do Mandante e Over Gols são positivamente correlacionados (ρ = 0.30)
        # Vitória e BTTS (Ambas Marcam) tem correlação leve (ρ = 0.15)
        self.correlation_matrix = {
            ('h2h_home', 'totals_over'): 0.30,
            ('h2h_home', 'totals_under'): -0.25,
            ('h2h_home', 'btts_yes'): 0.15,
            ('h2h_home', 'btts_no'): -0.10,
            ('h2h_away', 'totals_over'): 0.25,
            ('h2h_away', 'totals_under'): -0.20,
            ('totals_over', 'btts_yes'): 0.65, # Altamente correlacionado
            ('totals_under', 'btts_no'): 0.60
        }

    def get_joint_probability(self, prob_A: float, prob_B: float, type_A: str, type_B: str) -> float:
        """Calcula a probabilidade combinada usando uma Cópula Gaussiana Bivariada."""
        # Se as odds forem anômalas (prob > 1 ou < 0), retorna a independência básica
        if not (0 < prob_A < 1) or not (0 < prob_B < 1):
            return prob_A * prob_B

        # Busca o Rho (ρ) na matriz. Tenta as duas combinações.
        rho = self.correlation_matrix.get((type_A, type_B), self.correlation_matrix.get((type_B, type_A), 0.0))
        
        # Inversão da CDF (Probit)
        z_A = norm.ppf(prob_A)
        z_B = norm.ppf(prob_B)
        
        # Aproximação rápida para a integral dupla da distribuição normal bivariada
        joint_prob = prob_A * prob_B + rho * norm.pdf(z_A) * norm.pdf(z_B)
        
        return max(0.01, min(0.99, joint_prob))


class SGPBuilder:
    """
    O Motor de Execução SGP (Microserviço Backend).
    Cruza as Blueprints com as Odds Reais do momento (Market Odds).
    """
    def __init__(self):
        self.copula = SGPCopulaEngine()
        self.models_dir = Path(__file__).parent / "models"
        self.xgb_model_path = self.models_dir / "xgb_match_odds.joblib"
        self.model = None

    def _load_oracles(self):
        if self.xgb_model_path.exists():
            self.model = joblib.load(self.xgb_model_path)
        else:
            logger.warning("⚠️ Oráculo XGBoost ausente. Usando apenas a Heurística Preditiva.")

    async def get_match_context(self, match_id: int) -> pd.Series:
        """Lê a Feature Store S-Tier (A nova base atualizada)."""
        await db.connect()
        async with db.pool.acquire() as conn:
            query = f"SELECT * FROM quant_ml.feature_store WHERE match_id = {match_id}"
            record = await conn.fetchrow(query)
        if not record: return None
        return pd.Series(dict(record))

    async def get_live_market_odds(self, match_id: int) -> dict:
        """Puxa o cardápio de odds reais que o ingestor gravou nos últimos milissegundos."""
        live_odds = {}
        await db.connect()
        async with db.pool.acquire() as conn:
            query = f"SELECT categoria, nome_mercado, current_odd FROM core.market_odds WHERE match_id = {match_id}"
            records = await conn.fetch(query)
            
            for r in records:
                key = f"{r['categoria']}_{r['nome_mercado']}"
                live_odds[key] = float(r['current_odd'])
                
        return live_odds

    def _calculate_fair_sgp_odd(self, legs: list) -> float:
        """
        Substitui os descontos fixos por Matemática Pura.
        Converte as odds de volta para probabilidade, aplica a Cópula e devolve a Odd Justa.
        """
        if len(legs) == 2:
            p_A = 1.0 / legs[0]['odd']
            p_B = 1.0 / legs[1]['odd']
            
            # Mapeamento tático para a Matriz de Correlação
            type_A = self._map_market_type(legs[0]['internal_id'])
            type_B = self._map_market_type(legs[1]['internal_id'])
            
            joint_p = self.copula.get_joint_probability(p_A, p_B, type_A, type_B)
            # A casa de apostas sempre aplica uma margem (Juice) de ~7% no SGP
            fair_odd = (1.0 / joint_p) * 0.93 
            return round(fair_odd, 2)
            
        # Para SGPs com 3 ou mais pernas, multiplicamos as independentes e aplicamos juice bruto
        raw_odd = np.prod([leg['odd'] for leg in legs])
        return round(raw_odd * 0.85, 2)

    def _map_market_type(self, internal_id: str) -> str:
        """Traduz o ID do banco para o domínio da Matriz de Correlação."""
        if 'h2h_home' in internal_id: return 'h2h_home'
        if 'h2h_away' in internal_id: return 'h2h_away'
        if 'totals_Over' in internal_id: return 'totals_over'
        if 'totals_Under' in internal_id: return 'totals_under'
        if 'btts' in internal_id and 'yes' in internal_id: return 'btts_yes'
        if 'btts' in internal_id and 'no' in internal_id: return 'btts_no'
        return 'independent'

    def _sanity_check(self, legs: list) -> bool:
        """O Filtro de Sanidade: Impede suicídio matemático."""
        markets = [leg['internal_id'] for leg in legs]
        
        # Lógica conflitante absurda
        if any('Under' in m for m in markets) and any('btts_yes' in m for m in markets):
            return False
            
        return True

    def build_conservative_ticket(self, ctx: pd.Series, live_odds: dict):
        """BLUEPRINT 1.1: Proteção de Capital (Requer Odds Reais)."""
        legs = []
        
        # 1. Verifica se os gatilhos matemáticos bateram
        favoritism = ctx['delta_elo'] > 100
        fraudulent_attacks = ctx['home_xg_for_ewma_macro'] < 1.1 and ctx['away_xg_for_ewma_macro'] < 1.1
        
        if favoritism and fraudulent_attacks:
            # 2. Busca a Odd Real do Mercado (Fallback para 1.0 se a casa fechou o mercado)
            odd_home = live_odds.get('h2h_home', 0)
            odd_under = live_odds.get('totals_Over/Under 3.5 - Under', 0)
            
            # Só monta o bilhete se a casa de aposta estiver oferecendo as linhas
            if odd_home > 1.10 and odd_under > 1.10:
                legs.append({'market': 'Vitória do Mandante', 'internal_id': 'h2h_home', 'odd': odd_home, 'rationale': 'Forte Delta Elo'})
                legs.append({'market': 'Menos de 3.5 Gols', 'internal_id': 'totals_Under', 'odd': odd_under, 'rationale': 'Ataques Ineficientes (xG < 1.1)'})
                
                final_odd = self._calculate_fair_sgp_odd(legs)
                return {
                    'profile': 'Conservador', 'blueprint': 'O Asfixiamento', 
                    'legs': legs, 'target_odd': final_odd, 
                    'ev_rationale': 'Sinergia Preditiva: Mandante amassa, mas falta poder de fogo geral.'
                }
        return None

    def build_moderate_ticket(self, ctx: pd.Series, live_odds: dict):
        """BLUEPRINT 2.2: Moderado (O Derby do Desespero)."""
        legs = []
        
        high_tension = ctx['home_tension_index'] > 0.8 and ctx['away_tension_index'] > 0.8
        
        if high_tension:
            odd_btts = live_odds.get('btts_Yes', live_odds.get('btts_yes', 0))
            odd_over = live_odds.get('totals_Over/Under 2.5 - Over', 0)
            
            if odd_btts > 1.20 and odd_over > 1.20:
                legs.append({'market': 'Ambas as Equipes Marcam (Sim)', 'internal_id': 'btts_yes', 'odd': odd_btts, 'rationale': 'Desespero força transições'})
                legs.append({'market': 'Mais de 2.5 Gols', 'internal_id': 'totals_Over', 'odd': odd_over, 'rationale': 'Jogo aberto por tensão na tabela'})
                
                final_odd = self._calculate_fair_sgp_odd(legs)
                return {
                    'profile': 'Moderado', 'blueprint': 'Derby do Desespero', 
                    'legs': legs, 'target_odd': final_odd, 
                    'ev_rationale': 'O fator sobrevivência força a ruptura das linhas táticas base.'
                }
        return None

    async def generate_sgp(self, match_id: int) -> dict:
        """Função Principal: Chamada pelo FastAPI (main.py) para o Front-End."""
        self._load_oracles()
        logger.info(f"🔍 Escaneando Feature Store e Odds ao Vivo para a Partida ID: {match_id}")
        
        ctx = await self.get_match_context(match_id)
        if ctx is None:
            return {"match_id": match_id, "status": "error", "message": "Partida ausente na Matrix"}
            
        live_odds = await self.get_live_market_odds(match_id)
        if not live_odds:
            logger.warning("Nenhuma Odd capturada para este jogo. Abortando SGP.")
            return {"match_id": match_id, "status": "no_odds", "recommended_tickets": []}

        tickets = []
        
        t1 = self.build_conservative_ticket(ctx, live_odds)
        if t1 and self._sanity_check(t1['legs']): tickets.append(t1)
            
        t2 = self.build_moderate_ticket(ctx, live_odds)
        if t2 and self._sanity_check(t2['legs']): tickets.append(t2)
        
        payload = {
            "match_id": match_id,
            "status": "success" if tickets else "no_value_found",
            "recommended_tickets": tickets
        }
        
        # Devolvemos um DICT puro. O FastAPI (main.py) transformará isso na resposta HTTP.
        return payload

if __name__ == "__main__":
    # Teste local para garantir que o pipeline não quebrou
    builder = SGPBuilder()
    resultado = asyncio.run(builder.generate_sgp(1)) # ID 1 de teste
    import json
    print(json.dumps(resultado, indent=4, ensure_ascii=False))