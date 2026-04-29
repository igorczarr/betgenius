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
    Motor HFT de Extração de Valor (Smart Money Engine).
    Supera a eficiência das Big 5 Ligas cruzando EV puro com Contexto Situacional (Vetos).
    Aplica Kelly Criterion Dinâmico baseado em Tensão e Variância.
    """
    def __init__(self):
        self.models_dir = Path(__file__).parent / "brain" / "models"
        
        # Limites Base de EV (Ajustáveis pelo Contexto)
        self.BASE_EV_THRESHOLD = 0.04 # Exige 4% de borda pura para mercados populares
        self.CONTRARIAN_EV_THRESHOLD = 0.025 # Aceita apenas 2.5% de borda se for contra o público (Under/Zebra)

        self.oracles = {}
        self._load_oracles()

    def _load_oracles(self):
        """Carrega a Suíte Completa de Inteligência Artificial."""
        try:
            self.oracles['alpha'] = joblib.load(self.models_dir / "alpha_classifier_1x2.joblib")
            self.oracles['beta'] = joblib.load(self.models_dir / "beta_oracle_ou25.joblib")
            self.oracles['gamma'] = joblib.load(self.models_dir / "gamma_oracle_btts.joblib")
            logger.info("🧠 Suíte de Oráculos carregada e pronta para inferência.")
        except Exception as e:
            logger.warning(f"⚠️ Alguns Oráculos não foram encontrados. O Scanner operará com o que estiver disponível: {e}")

    async def get_match_context(self, match_id: int) -> pd.DataFrame:
        """Puxa a Feature Store pronta para inferência."""
        await db.connect()
        async with db.pool.acquire() as conn:
            query = f"SELECT * FROM quant_ml.feature_store WHERE match_id = {match_id}"
            record = await conn.fetchrow(query)
        
        if not record: return None
        return pd.DataFrame([dict(record)])

    async def get_live_market_odds(self, match_id: int) -> dict:
        """Puxa as odds reais e frescas do banco."""
        live_odds = {}
        async with db.pool.acquire() as conn:
            query = f"SELECT categoria, nome_mercado, current_odd FROM core.market_odds WHERE match_id = {match_id}"
            records = await conn.fetch(query)
            for r in records:
                key = f"{r['categoria']}_{r['nome_mercado']}"
                live_odds[key] = float(r['current_odd'])
        return live_odds

    def _calculate_ev(self, prob: float, odd: float) -> float:
        """EV = (Probabilidade * Odd) - 1"""
        return (prob * odd) - 1.0

    def _calculate_dynamic_kelly(self, prob: float, odd: float, ctx: pd.Series) -> float:
        """
        Kelly Criterion ajustado pelo 'Game State' e Tensão.
        Dilui o risco matematicamente se o jogo for um caos tático.
        """
        if odd <= 1.0: return 0.0
        
        b = odd - 1.0
        q = 1.0 - prob
        full_kelly = ((b * prob) - q) / b
        
        if full_kelly <= 0: return 0.0
        
        # A Mágica Institucional: Ajuste do Multiplicador de Kelly
        # O padrão é 1/4 (0.25). Mas se o jogo é de alto risco, cortamos para 1/8 (0.125)
        tension_h = float(ctx.get('home_tension_index', 0.5))
        tension_a = float(ctx.get('away_tension_index', 0.5))
        aggression = float(ctx.get('home_aggression_ewma', 10.0)) + float(ctx.get('away_aggression_ewma', 10.0))
        
        is_chaotic = (tension_h > 0.85 and tension_a > 0.85) or aggression > 26.0
        
        kelly_multiplier = 0.125 if is_chaotic else 0.25
        
        return round(full_kelly * kelly_multiplier, 4)

    def _apply_situational_veto(self, market: str, ev: float, ctx: pd.Series) -> tuple:
        """
        O Filtro do Tipster. 
        Veta apostas que têm EV+ matemático, mas falham no teste da realidade tática/física.
        Retorna (bool_aprovado, string_motivo).
        """
        # Exemplo 1: Vetar Favorito (Home Win) se ele estiver exausto ou com ataque fraudulento
        if market == 'Home Win':
            if ctx.get('delta_rest_days', 0) < -3:
                return False, "VETO: Mandante sofre de fadiga severa (>3 dias de desvantagem)."
            if ctx.get('home_fraudulent_attack', 0) == 1:
                return False, "VETO: O ataque do mandante é uma anomalia estatística (Fraude)."
                
        # Exemplo 2: Vetar Over 2.5 se os dois times estão em "Modo Férias"
        if market == 'Over 2.5':
            if ctx.get('home_tension_index', 1.0) < 0.2 and ctx.get('away_tension_index', 1.0) < 0.2:
                return False, "VETO: Ambos os times sem ambição no campeonato (Risco de jogo morto)."
                
        # Exemplo 3: O Prêmio Contrariano
        # Reduzimos o EV exigido se estamos indo contra o viés do público (Under ou Zebra)
        threshold = self.CONTRARIAN_EV_THRESHOLD if market in ['Under 2.5', 'Away Win', 'Draw'] else self.BASE_EV_THRESHOLD
        
        if ev < threshold:
            return False, f"EV insuficiente. Exigido: {threshold*100:.1f}%, Encontrado: {ev*100:.1f}%"
            
        return True, "Aprovado pelos Filtros Situacionais."

    def scan_for_value(self, df_context: pd.DataFrame, live_odds: dict) -> dict:
        """Processa a inferência multimodelo e varre os mercados ao vivo."""
        ctx = df_context.iloc[0]
        match_id = int(ctx['match_id'])
        opportunities = []

        # ============================================================
        # 1. INFERÊNCIA DO ORÁCULO (Machine Learning)
        # ============================================================
        preds = {}
        
        try:
            # 1X2 (Alpha)
            if 'alpha' in self.oracles:
                features_1x2 = self.oracles['alpha'].feature_names_in_
                prob_1x2 = self.oracles['alpha'].predict_proba(df_context[features_1x2])[0]
                preds['Away Win'] = prob_1x2[0]
                preds['Draw'] = prob_1x2[1]
                preds['Home Win'] = prob_1x2[2]

            # Over/Under (Beta)
            if 'beta' in self.oracles:
                features_ou = self.oracles['beta'].feature_names_in_
                prob_ou = self.oracles['beta'].predict_proba(df_context[features_ou])[0]
                preds['Under 2.5'] = prob_ou[0]
                preds['Over 2.5'] = prob_ou[1]
                
            # BTTS (Gamma)
            if 'gamma' in self.oracles:
                features_btts = self.oracles['gamma'].feature_names_in_
                prob_btts = self.oracles['gamma'].predict_proba(df_context[features_btts])[0]
                preds['BTTS No'] = prob_btts[0]
                preds['BTTS Yes'] = prob_btts[1]
                
        except Exception as e:
            logger.error(f"Falha na inferência dos Oráculos: {e}")
            return {"match_id": match_id, "status": "error", "signals": []}

        # ============================================================
        # 2. MAPEAMENTO DE MERCADO (Odds Reais)
        # ============================================================
        market_map = {
            'Home Win': live_odds.get('h2h_home', 0),
            'Draw': live_odds.get('h2h_draw', 0),
            'Away Win': live_odds.get('h2h_away', 0),
            'Over 2.5': live_odds.get('totals_Over/Under 2.5 - Over', 0),
            'Under 2.5': live_odds.get('totals_Over/Under 2.5 - Under', 0),
            'BTTS Yes': live_odds.get('btts_Yes', live_odds.get('btts_yes', 0)),
            'BTTS No': live_odds.get('btts_No', live_odds.get('btts_no', 0))
        }

        # ============================================================
        # 3. ESCANEAMENTO E AVALIAÇÃO DE VALOR
        # ============================================================
        for market_name, prob in preds.items():
            odd = market_map.get(market_name, 0)
            if odd <= 1.05: continue # Ignora odds esmagadas ou fechadas
                
            ev = self._calculate_ev(prob, odd)
            
            # Filtro 1: Tem Valor Teórico Mínimo? (> 0)
            if ev > 0:
                # Filtro 2: O Tipster Aprova? (Situational Vetoes)
                is_approved, rationale = self._apply_situational_veto(market_name, ev, ctx)
                
                if is_approved:
                    true_odd = 1.0 / prob
                    stake_pct = self._calculate_dynamic_kelly(prob, odd, ctx)
                    
                    if stake_pct > 0:
                        opportunities.append({
                            "market": market_name,
                            "bookmaker_odd": odd,
                            "true_odd": round(true_odd, 2),
                            "model_probability_pct": round(prob * 100, 2),
                            "expected_value_pct": round(ev * 100, 2),
                            "suggested_bankroll_stake_pct": round(stake_pct * 100, 2),
                            "rationale": rationale,
                            "status": "💎 CONFIRMED ALPHA"
                        })

        # Ordena as oportunidades pelo maior EV
        opportunities = sorted(opportunities, key=lambda x: x['expected_value_pct'], reverse=True)

        payload = {
            "match_id": match_id,
            "timestamp": pd.Timestamp.utcnow().isoformat(),
            "status": "success" if opportunities else "no_value_found",
            "signals": opportunities
        }
        
        return payload

    async def execute_scan(self, match_id: int) -> dict:
        """Função chamada pelo FastAPI para avaliar um jogo em tempo real."""
        logger.info(f"🔎 Acionando Value Scanner para a Partida ID: {match_id}...")
        
        df_ctx = await self.get_match_context(match_id)
        if df_ctx is None or df_ctx.empty:
            return {"match_id": match_id, "status": "error", "message": "Matriz indisponível."}

        live_odds = await self.get_live_market_odds(match_id)
        if not live_odds:
            return {"match_id": match_id, "status": "no_odds", "message": "Mercados fechados."}

        payload = self.scan_for_value(df_ctx, live_odds)
        await db.disconnect()
        
        return payload

if __name__ == "__main__":
    scanner = ValueScanner()
    # Teste de Inicialização Local
    resultado = asyncio.run(scanner.execute_scan(1))
    import json
    print(json.dumps(resultado, indent=4, ensure_ascii=False))