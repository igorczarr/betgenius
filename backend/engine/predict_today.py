# betgenius-backend/engine/predict_today.py
import sys
import os
import io
import asyncio
import logging
import pandas as pd
import joblib
from pathlib import Path
from dotenv import load_dotenv

# =====================================================================
# BLINDAGEM DE ENCODING PARA WINDOWS
# =====================================================================
if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except AttributeError:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [INFERENCE-ENGINE] %(message)s", handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

class DailyPredictor:
    """
    Motor de Inferência S-Tier.
    Lê os jogos do dia, aciona o modelo XGBoost pré-treinado e 
    identifica as Assimetrias de Valor (+EV) contra as casas de apostas.
    """
    def __init__(self):
        self.model_path = BASE_DIR / "engine" / "models" / "xgb_match_odds.joblib"
        
        # AS EXATAS 25 COLUNAS USADAS NO TREINAMENTO (Nenhuma a mais, nenhuma a menos)
        self.features = [
            'delta_elo', 'delta_wage_pct', 'delta_pontos', 'delta_posicao', 
            'home_rest_days', 'away_rest_days', 
            'home_xg_for_ewma_micro', 'home_xg_against_ewma_micro',
            'away_xg_for_ewma_micro', 'away_xg_against_ewma_micro',
            'home_xg_for_ewma_macro', 'away_xg_for_ewma_macro',
            'home_aggression_ewma', 'away_aggression_ewma', 
            'home_win_streak', 'home_winless_streak', 'away_win_streak', 'away_winless_streak',
            'home_tension_index', 'away_tension_index', 
            'home_fraudulent_defense', 'home_fraudulent_attack',
            'away_fraudulent_defense', 'away_fraudulent_attack',
            'delta_market_respect'
        ]

    async def run_predictions(self):
        logger.info("🚀 INICIANDO INFERÊNCIA DIÁRIA (XGBOOST)...")
        
        if not self.model_path.exists():
            logger.error(f"❌ Cérebro do modelo não encontrado em {self.model_path}. Rode o treinamento primeiro.")
            return

        logger.info("🧠 Carregando matriz sináptica (Modelo XGBoost)...")
        model = joblib.load(self.model_path)
        
        await db.connect()
        
        try:
            async with db.pool.acquire() as conn:
                # Busca os jogos agendados para HOJE ou AMANHÃ que já tenham features na Store
                query = """
                    SELECT f.*, m.closing_odd_home, m.closing_odd_away 
                    FROM quant_ml.feature_store f
                    JOIN core.matches_history m ON f.match_id::int = m.id
                    WHERE m.status = 'SCHEDULED' 
                    AND m.match_date >= CURRENT_DATE 
                    AND m.match_date < CURRENT_DATE + INTERVAL '2 days'
                """
                records = await conn.fetch(query)
                
                if not records:
                    logger.warning("⚠️ Nenhum jogo futuro (próximas 48h) encontrado na Feature Store. Aguardando novos jogos...")
                    return
                    
                df = pd.DataFrame([dict(r) for r in records])
                
                # Formatação rigorosa para evitar crashes no XGBoost
                for col in self.features:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                    
                X_pred = df[self.features]
                
                logger.info(f"🔮 Analisando {len(df)} partidas. Extraindo probabilidades implícitas...")
                
                # Predição Multi-Classe (0=Away, 1=Draw, 2=Home)
                probs = model.predict_proba(X_pred)
                
                df['prob_away'] = probs[:, 0]
                df['prob_draw'] = probs[:, 1]
                df['prob_home'] = probs[:, 2]
                
                logger.info("📐 Cruzando probabilidades da IA com as Odds do Mercado (Cálculo de EV)...")
                # Tratamento de fallback para odds nulas
                df['closing_odd_home'] = pd.to_numeric(df['closing_odd_home'], errors='coerce').fillna(1.0)
                df['closing_odd_away'] = pd.to_numeric(df['closing_odd_away'], errors='coerce').fillna(1.0)
                
                # Cálculo da Assimetria (Expected Value)
                df['ev_home'] = (df['prob_home'] * df['closing_odd_home']) - 1.0
                df['ev_away'] = (df['prob_away'] * df['closing_odd_away']) - 1.0
                
                # Estratégia de Filtragem: Edge real precisa ser maior que 5% e menor que 100% (para ignorar lixo matemático)
                df['is_value_bet'] = ((df['ev_home'] > 0.05) & (df['ev_home'] < 1.0)) | ((df['ev_away'] > 0.05) & (df['ev_away'] < 1.0))
                
                records_to_insert = []
                value_bets_count = 0
                
                for _, row in df.iterrows():
                    if row['is_value_bet']:
                        value_bets_count += 1
                        
                    records_to_insert.append((
                        int(row['match_id']),
                        round(row['prob_home'], 4), round(row['prob_draw'], 4), round(row['prob_away'], 4),
                        round(row['ev_home'], 4), round(row['ev_away'], 4),
                        bool(row['is_value_bet'])
                    ))
                    
                logger.info(f"💾 Salvando {len(records_to_insert)} previsões. Foram detectadas {value_bets_count} oportunidades de Valor (+EV).")
                
                # Upsert de Alta Performance
                await conn.executemany("""
                    INSERT INTO quant_ml.predictions 
                    (match_id, prob_home, prob_draw, prob_away, ev_home, ev_away, is_value_bet, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                    ON CONFLICT (match_id) DO UPDATE SET
                        prob_home=EXCLUDED.prob_home, prob_draw=EXCLUDED.prob_draw, prob_away=EXCLUDED.prob_away,
                        ev_home=EXCLUDED.ev_home, ev_away=EXCLUDED.ev_away, is_value_bet=EXCLUDED.is_value_bet, updated_at=NOW()
                """, records_to_insert)

        except Exception as e:
            logger.error(f"❌ Falha Crítica na Inferência: {e}")
        finally:
            await db.disconnect()
            logger.info("✅ PROCESSO DE INFERÊNCIA FINALIZADO.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(DailyPredictor().run_predictions())