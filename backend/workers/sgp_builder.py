# betgenius-backend/workers/sgp_builder.py
import asyncio
import logging
import pandas as pd
import numpy as np
import joblib
import sys
from pathlib import Path

# Adiciona o backend ao path para importações
sys.path.append(str(Path(__file__).parent.parent))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SGP-BUILDER] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class SGPBuilder:
    """
    O Motor de Correlação e Construtor de Bilhetes (Same Game Parlay).
    Analisa a Alpha Matrix, extrai as probabilidades e monta os bilhetes
    usando as Blueprints de Elite (Conservador, Moderado, Kamikaze).
    """
    def __init__(self):
        self.models_dir = Path(__file__).parent / "models"
        self.xgb_model_path = self.models_dir / "xgb_match_odds.joblib"
        self.model = None

    def _load_oracles(self):
        """Carrega os cérebros preditivos (XGBoost)."""
        if self.xgb_model_path.exists():
            self.model = joblib.load(self.xgb_model_path)
            logger.info("🧠 Oráculo XGBoost carregado com sucesso.")
        else:
            logger.warning("⚠️ Modelo XGBoost não encontrado. O sistema operará usando Heurísticas Quantitativas da Alpha Matrix.")

    async def get_match_context(self, match_id: int) -> pd.Series:
        """Puxa a linha exata da Alpha Matrix com os tensores da partida."""
        await db.connect()
        async with db.pool.acquire() as conn:
            query = f"SELECT * FROM core.alpha_matrix WHERE match_id = {match_id}"
            record = await conn.fetchrow(query)
        await db.disconnect()
        
        if not record: return None
        return pd.Series(dict(record))

    def _calculate_correlated_odd(self, legs: list, correlation_type: str) -> float:
        """
        A Matemática do Sindicato: Combinação de Odds Correlacionadas.
        Se os eventos se ajudam (Correlação Positiva), a Odd final é menor que a simples multiplicação.
        Se os eventos se opõem (Correlação Negativa), a Odd explode.
        """
        raw_odd = np.prod([leg['odd'] for leg in legs])
        
        if correlation_type == 'strong_positive':
            discount = 0.75 # A casa corta 25% da odd por serem muito correlacionados
            return round(raw_odd * discount, 2)
        elif correlation_type == 'mild_positive':
            discount = 0.90
            return round(raw_odd * discount, 2)
        elif correlation_type == 'negative_hidden':
            premium = 1.30 # A casa acha que não vai bater e infla a odd (A Assimetria)
            return round(raw_odd * premium, 2)
        
        return round(raw_odd, 2)

    def _sanity_check(self, legs: list) -> bool:
        """O Filtro de Sanidade: Impede suicídio matemático."""
        markets = [leg['market'] for leg in legs]
        
        if 'Under 1.5 Gols' in markets and 'Ambas Marcam (Sim)' in markets:
            return False
        if 'Under 2.5 Gols' in markets and 'Over 3.5 Gols' in markets:
            return False
        # Limite de Asian: Não colocar DNB e Handicap Asiático no mesmo bilhete
        asian_lines = [m for m in markets if 'DNB' in m or 'Handicap' in m]
        if len(asian_lines) > 1:
            return False
            
        return True

    def build_conservative_ticket(self, ctx: pd.Series):
        """BLUEPRINT 1.1: Proteção de Capital (Asfixiamento Estéril). Winrate Alvo: 65%+"""
        legs = []
        
        # Gatilhos da Matriz Alpha
        favoritism = ctx['delta_elo'] > 100
        fraudulent_attacks = ctx['home_xg_for_ewma_macro'] < 1.1 and ctx['away_xg_for_ewma_macro'] < 1.1
        
        if favoritism and fraudulent_attacks:
            # Seleção 1: O Escudo (Empate Anula)
            legs.append({'market': 'Mandante Empate Anula (DNB)', 'odd': 1.35, 'rationale': 'Forte Delta Elo'})
            # Seleção 2: O Asfixiamento (Under Gols)
            legs.append({'market': 'Under 3.5 Gols', 'odd': 1.30, 'rationale': 'Ambos com xG Macro Baixo'})
            
            final_odd = self._calculate_correlated_odd(legs, 'mild_positive')
            return {
                'profile': 'Conservador', 'blueprint': 'Asfixiamento Estéril', 
                'legs': legs, 'target_odd': final_odd, 'ev_rationale': 'Mercado superestima gols em jogos de favorito estéril.'
            }
        return None

    def build_moderate_ticket(self, ctx: pd.Series):
        """BLUEPRINT 2.2: Moderado (O Derby do Desespero). Winrate Alvo: 35%+"""
        legs = []
        
        # Gatilhos: Ambos com alta tensão (lutando pra não cair/título) e alta agressividade
        high_tension = ctx['home_tension_index'] > 0.8 and ctx['away_tension_index'] > 0.8
        high_aggression = ctx['home_aggression_ewma'] > 12.0 and ctx['away_aggression_ewma'] > 12.0
        
        if high_tension and high_aggression:
            legs.append({'market': 'Mais de 4.5 Cartões', 'odd': 1.55, 'rationale': 'Tensão Mútua Extrema'})
            legs.append({'market': 'Ambas Marcam (Sim)', 'odd': 1.70, 'rationale': 'Desespero força transições abertas'})
            legs.append({'market': 'Mais de 8.5 Escanteios', 'odd': 1.40, 'rationale': 'Jogo vertical e faltoso'})
            
            final_odd = self._calculate_correlated_odd(legs, 'strong_positive')
            return {
                'profile': 'Moderado', 'blueprint': 'Derby do Desespero', 
                'legs': legs, 'target_odd': final_odd, 'ev_rationale': 'Correlação de caos ignorada pelo algoritmo base da casa.'
            }
        return None

    def build_aggressive_ticket(self, ctx: pd.Series):
        """BLUEPRINT 3.1: Kamikaze (O Tombamento do Rei / Cisne Negro). Winrate Alvo: 8%+"""
        legs = []
        
        # Gatilhos: Favorito (Away) esgotado fisicamente. Zebra (Home) com a corda no pescoço.
        exhausted_favorite = ctx['delta_elo'] < -150 and ctx['away_rest_days'] < 4
        desperate_underdog = ctx['home_tension_index'] > 0.90
        
        if exhausted_favorite and desperate_underdog:
            # A casa paga uma fortuna para a Zebra não ser goleada, e mais ainda pro Favorito bater
            legs.append({'market': 'Mandante Handicap Asiático +1.5', 'odd': 1.85, 'rationale': 'Zebra motivada em casa'})
            legs.append({'market': 'Visitante Recebe Mais Cartões', 'odd': 2.50, 'rationale': 'Favorito fadigado comete faltas táticas'})
            legs.append({'market': 'Under 2.5 Gols', 'odd': 1.95, 'rationale': 'Falta de perna do Favorito trava o placar'})
            
            final_odd = self._calculate_correlated_odd(legs, 'negative_hidden')
            return {
                'profile': 'Agressivo (Cisne Negro)', 'blueprint': 'O Tombamento do Rei', 
                'legs': legs, 'target_odd': final_odd, 'ev_rationale': 'Assimetria Oculta. Favorito cansado não goleia, apenas administra e comete faltas.'
            }
        return None

    async def generate_sgp(self, match_id: int):
        self._load_oracles()
        logger.info(f"🔍 Escaneando Matriz Alpha para a Partida ID: {match_id}")
        
        ctx = await self.get_match_context(match_id)
        if ctx is None:
            logger.error("❌ Partida não encontrada na Alpha Matrix.")
            return

        # Tenta encaixar a partida nas Plantas Baixas (Blueprints)
        tickets = []
        
        t1 = self.build_conservative_ticket(ctx)
        if t1 and self._sanity_check(t1['legs']): tickets.append(t1)
            
        t2 = self.build_moderate_ticket(ctx)
        if t2 and self._sanity_check(t2['legs']): tickets.append(t2)
            
        t3 = self.build_aggressive_ticket(ctx)
        if t3 and self._sanity_check(t3['legs']): tickets.append(t3)
        
        # Monta o Payload JSON para o Node.js
        payload = {
            "match_id": match_id,
            "status": "success" if tickets else "no_value_found",
            "recommended_tickets": tickets
        }
        
        # IMPORTANTE: O Node.js está escutando o stdout. 
        # Imprimimos o JSON puro para que a Regex do pythonRunner.js o capture.
        import json
        print(json.dumps(payload, ensure_ascii=False))

if __name__ == "__main__":
    import sys
    builder = SGPBuilder()
    
    # Captura o ID do jogo que o Node.js enviou. Se não enviar, usa 1 como fallback.
    match_id_alvo = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    
    asyncio.run(builder.generate_sgp(match_id_alvo))