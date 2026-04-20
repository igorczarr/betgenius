# betgenius-backend/workers/value_scanner.py
import asyncio
import logging
import pandas as pd
import numpy as np
import joblib
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [VALUE-SCANNER] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class ValueScanner:
    """
    O Gatilho S-Tier (HFT Expected Value Engine).
    Cruza as predições do Oráculo (XGBoost) com as Odds em tempo real.
    Gera alertas de apostas EV+ com gestão de banca embutida (Kelly Criterion).
    """
    def __init__(self):
        self.models_dir = Path(__file__).parent / "models"
        self.xgb_model_path = self.models_dir / "xgb_match_odds.joblib"
        self.model = None
        
        # O limite mínimo para valer a pena o risco (Sindicatos operam acima de 3% a 5%)
        self.MIN_EV_THRESHOLD = 0.03 

    def _load_model(self):
        if self.xgb_model_path.exists():
            self.model = joblib.load(self.xgb_model_path)
        else:
            logger.error("🛑 Oráculo XGBoost não encontrado. Rode a Etapa 1 de Treinamento primeiro.")
            sys.exit(1)

    async def get_upcoming_match_context(self, match_id: int) -> pd.DataFrame:
        """Busca as features (Alpha Matrix) do jogo que está prestes a acontecer."""
        await db.connect()
        async with db.pool.acquire() as conn:
            query = f"SELECT * FROM core.alpha_matrix WHERE match_id = {match_id}"
            record = await conn.fetchrow(query)
        await db.disconnect()
        
        if not record: return None
        return pd.DataFrame([dict(record)])

    def _calculate_ev(self, prob: float, odd: float) -> float:
        """EV = (Probabilidade * Odd) - 1"""
        return (prob * odd) - 1.0

    def _calculate_kelly_stake(self, prob: float, odd: float, kelly_multiplier: float = 0.25) -> float:
        """
        Calcula a % da banca a ser apostada.
        O Quarter Kelly (0.25) é o padrão ouro de fundos quants para diluir o risco de ruína.
        """
        if odd <= 1.0: return 0.0
        b = odd - 1.0
        q = 1.0 - prob
        kelly_fraction = ((b * prob) - q) / b
        
        # Aplica o fator de conservadorismo (Quarter Kelly) e garante que não seja negativo
        suggested_stake = max(0.0, kelly_fraction * kelly_multiplier)
        return suggested_stake

    def scan_for_value(self, df_context: pd.DataFrame, live_odds: dict) -> dict:
        """Faz a predição e varre os mercados procurando assimetrias."""
        
        # As colunas exatas que o modelo usou no treinamento
        features = [
            'delta_elo', 'delta_wage_pct', 
            'home_rest_days', 'away_rest_days', 'delta_rest_days',
            'home_xg_for_ewma_micro', 'home_xg_against_ewma_micro',
            'away_xg_for_ewma_micro', 'away_xg_against_ewma_micro',
            'delta_xg_micro', 'delta_xg_macro',
            'home_aggression_ewma', 'away_aggression_ewma', 'delta_aggression',
            'home_win_streak', 'home_winless_streak', 'away_win_streak', 'away_winless_streak',
            'home_tension_index', 'away_tension_index', 'delta_tension',
            'home_fraudulent_defense', 'home_fraudulent_attack',
            'away_fraudulent_defense', 'away_fraudulent_attack',
            'closing_odd_home', 'closing_odd_draw', 'closing_odd_away'
        ]
        
        X = df_context[features]
        
        # predict_proba retorna as porcentagens brutas do modelo
        # Importante: A ordem das classes no nosso treino foi [0: Away, 1: Draw, 2: Home]
        probabilities = self.model.predict_proba(X)[0]
        prob_away, prob_draw, prob_home = probabilities[0], probabilities[1], probabilities[2]
        
        logger.info(f"📊 True Odds do Oráculo: Home {prob_home:.1%} | Draw {prob_draw:.1%} | Away {prob_away:.1%}")
        
        opportunities = []
        
        # Mapeamento do Mercado
        markets = [
            {'name': 'Home Win', 'prob': prob_home, 'live_odd': live_odds.get('home', 0)},
            {'name': 'Draw', 'prob': prob_draw, 'live_odd': live_odds.get('draw', 0)},
            {'name': 'Away Win', 'prob': prob_away, 'live_odd': live_odds.get('away', 0)}
        ]
        
        for m in markets:
            if m['live_odd'] <= 1.0: continue
                
            ev = self._calculate_ev(m['prob'], m['live_odd'])
            
            if ev > self.MIN_EV_THRESHOLD:
                true_odd = 1.0 / m['prob']
                stake_pct = self._calculate_kelly_stake(m['prob'], m['live_odd'])
                
                opp = {
                    "market": m['name'],
                    "bookmaker_odd": m['live_odd'],
                    "true_odd": round(true_odd, 2),
                    "model_probability_pct": round(m['prob'] * 100, 2),
                    "expected_value_pct": round(ev * 100, 2),
                    "suggested_bankroll_stake_pct": round(stake_pct * 100, 2),
                    "status": "🚨 +EV ALERT"
                }
                opportunities.append(opp)
                
        # Monta o Payload JSON para o Front-End Vue.js
        payload = {
            "match_id": int(df_context.iloc[0]['match_id']),
            "timestamp": pd.Timestamp.utcnow().isoformat(),
            "signals": opportunities
        }
        
        return payload

    async def execute_scan(self, match_id: int, live_odds_mock: dict):
        self._load_model()
        logger.info(f"🔎 Analisando partida ID: {match_id} contra as linhas ao vivo...")
        
        df_ctx = await self.get_upcoming_match_context(match_id)
        if df_ctx is None or df_ctx.empty:
            logger.error("❌ Partida não encontrada no Data Warehouse.")
            return

        payload = self.scan_for_value(df_ctx, live_odds_mock)
        
        if payload['signals']:
            logger.info("\n💰 OPORTUNIDADES ENCONTRADAS (Payload para Vue.js):")
            print(json.dumps(payload, indent=4, ensure_ascii=False))
        else:
            logger.warning("🚫 Nenhum valor encontrado nas linhas ao vivo. O mercado está eficiente. NÃO APOSTE.")

if __name__ == "__main__":
    scanner = ValueScanner()
    
    # SIMULAÇÃO: O nosso robô de live odds pegou isso da Pinnacle agora mesmo
    # Troque o MATCH_ID_TESTE por um ID real da sua Alpha Matrix
    MATCH_ID_TESTE = 1 
    
    # Imaginando que o mercado está oferecendo 1.45 pro Mandante
    LIVE_ODDS = {
        'home': 1.45,
        'draw': 4.20,
        'away': 6.50
    }
    
    asyncio.run(scanner.execute_scan(MATCH_ID_TESTE, LIVE_ODDS))