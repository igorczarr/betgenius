# betgenius-backend/workers/feature_engineering/temporal_features_engine.py

import asyncio
import logging
import pandas as pd
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# =====================================================================
# BLINDAGEM DE ENCODING PARA WINDOWS E CARREGAMENTO DO .ENV
# =====================================================================
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [TEMPORAL-ENGINE] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class TemporalFeaturesEngine:
    """
    Motor S-Tier de Features Temporais (EWMA e Física).
    Desmembra os jogos, calcula o Proxy xG, aplica Médias Móveis Exponenciais (Micro e Macro)
    e rastreia a Fadiga (Dias de Descanso) sem vazamento de dados (Lookahead Bias).
    """

    def __init__(self):
        self.MICRO_SPAN = 5   # Curto prazo (Momento atual / Últimos 5 jogos)
        self.MACRO_SPAN = 15  # Longo prazo (Força consolidada / Últimos 15 jogos)

    async def initialize_schema(self, conn):
        logger.info("🛠️ Preparando Schema Temporal...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS core.match_temporal_features (
                match_id INTEGER PRIMARY KEY REFERENCES core.matches_history(id) ON DELETE CASCADE,
                home_rest_days INTEGER,
                away_rest_days INTEGER,
                home_xg_for_ewma_micro NUMERIC(5, 2),
                home_xg_against_ewma_micro NUMERIC(5, 2),
                away_xg_for_ewma_micro NUMERIC(5, 2),
                away_xg_against_ewma_micro NUMERIC(5, 2),
                home_xg_for_ewma_macro NUMERIC(5, 2),
                away_xg_for_ewma_macro NUMERIC(5, 2),
                home_aggression_ewma NUMERIC(5, 2),
                away_aggression_ewma NUMERIC(5, 2)
            );
        """)
        await conn.execute("TRUNCATE TABLE core.match_temporal_features CASCADE;")

    def _build_team_perspective_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transforma 1 jogo (Casa vs Fora) em 2 registros (Visão Casa, Visão Fora)."""
        
        # Visão Mandante
        df_home = df[['match_id', 'match_date', 'home_team_id', 'home_shots_target', 'home_corners', 
                      'home_fouls', 'home_yellow', 'home_red', 'away_shots_target', 'away_corners']].copy()
        df_home.columns = ['match_id', 'date', 'team_id', 'shots_target_for', 'corners_for', 
                           'fouls', 'yellow', 'red', 'shots_target_against', 'corners_against']
        df_home['is_home'] = 1

        # Visão Visitante
        df_away = df[['match_id', 'match_date', 'away_team_id', 'away_shots_target', 'away_corners', 
                      'away_fouls', 'away_yellow', 'away_red', 'home_shots_target', 'home_corners']].copy()
        df_away.columns = ['match_id', 'date', 'team_id', 'shots_target_for', 'corners_for', 
                           'fouls', 'yellow', 'red', 'shots_target_against', 'corners_against']
        df_away['is_home'] = 0

        # Une e ordena cronologicamente
        df_teams = pd.concat([df_home, df_away], ignore_index=True).sort_values(by=['team_id', 'date'])
        
        # BLINDAGEM MATEMÁTICA: Garante que os campos são numéricos (trata NaNs de jogos sem stats)
        stat_cols = ['shots_target_for', 'corners_for', 'fouls', 'yellow', 'red', 'shots_target_against', 'corners_against']
        for col in stat_cols:
            df_teams[col] = pd.to_numeric(df_teams[col], errors='coerce').fillna(0)

        # Cria as Métricas Base do Jogo Atual
        df_teams['proxy_xg_for'] = (df_teams['shots_target_for'] * 0.35) + (df_teams['corners_for'] * 0.05)
        df_teams['proxy_xg_against'] = (df_teams['shots_target_against'] * 0.35) + (df_teams['corners_against'] * 0.05)
        df_teams['aggression'] = df_teams['fouls'] + (df_teams['yellow'] * 2) + (df_teams['red'] * 5)

        return df_teams

    def _calculate_ewma_features(self, df_teams: pd.DataFrame) -> pd.DataFrame:
        """Aplica as Médias Móveis Exponenciais e Proteção de Data Leakage."""
        
        # 1. Cálculo do Rest Disadvantage (Fadiga Física)
        df_teams['rest_days'] = df_teams.groupby('team_id')['date'].diff().dt.days
        df_teams['rest_days'] = df_teams['rest_days'].fillna(7).clip(upper=15) 

        # 2. As Médias Móveis (O SHIFT 1 garante proteção contra Leakage)
        grouped = df_teams.groupby('team_id')
        
        # MICRO (Span 5 - Momento Atual)
        df_teams['xg_for_ewma_micro'] = grouped['proxy_xg_for'].transform(lambda x: x.ewm(span=self.MICRO_SPAN, adjust=False).mean().shift(1))
        df_teams['xg_against_ewma_micro'] = grouped['proxy_xg_against'].transform(lambda x: x.ewm(span=self.MICRO_SPAN, adjust=False).mean().shift(1))
        
        # MACRO (Span 15 - Consistência Tática)
        df_teams['xg_for_ewma_macro'] = grouped['proxy_xg_for'].transform(lambda x: x.ewm(span=self.MACRO_SPAN, adjust=False).mean().shift(1))
        
        # AGGRESSION (Span 10 - Comportamento Disciplinar)
        df_teams['aggression_ewma'] = grouped['aggression'].transform(lambda x: x.ewm(span=10, adjust=False).mean().shift(1))

        # Valores base para o jogo número 1 da história de cada time
        df_teams = df_teams.fillna({
            'xg_for_ewma_micro': 1.0, 'xg_against_ewma_micro': 1.0, 
            'xg_for_ewma_macro': 1.0, 'aggression_ewma': 10.0
        })

        return df_teams

    async def run_temporal_engine(self):
        logger.info("[INIT] INICIANDO TEMPORAL ENGINE: Construindo Matriz de Desempenho e Fadiga.")
        await db.connect()
        
        async with db.pool.acquire() as conn:
            await self.initialize_schema(conn)
            
            logger.info("📥 Extraindo histórico completo do Data Warehouse...")
            
            # Filtro Vital: Exclui jogos não iniciados ou que não têm estatísticas mínimas de partida
            query = """
                SELECT id as match_id, match_date, home_team_id, away_team_id,
                       home_shots_target, away_shots_target, home_corners, away_corners,
                       home_fouls, away_fouls, home_yellow, away_yellow, home_red, away_red
                FROM core.matches_history
                WHERE home_shots_target IS NOT NULL AND away_shots_target IS NOT NULL
                ORDER BY match_date ASC, id ASC
            """
            matches = await conn.fetch(query)
            
            if not matches:
                logger.error("❌ Histórico vazio ou sem estatísticas (Chutes/Faltas). Abortando Temporal Engine.")
                await db.disconnect()
                return

            df = pd.DataFrame([dict(m) for m in matches])
            df['match_date'] = pd.to_datetime(df['match_date'])

            logger.info("🧬 Transformando Perspectivas (Home/Away Split)...")
            df_teams = self._build_team_perspective_df(df)
            
            logger.info("📈 Calculando Médias Móveis Exponenciais (EWMA) e Dias de Descanso...")
            df_features = self._calculate_ewma_features(df_teams)

            logger.info("🔄 Recombinando Tensores para injeção...")
            home_feats = df_features[df_features['is_home'] == 1].set_index('match_id')
            away_feats = df_features[df_features['is_home'] == 0].set_index('match_id')

            records_to_insert = []
            valid_match_ids = df_features['match_id'].unique()
            
            for match_id in valid_match_ids:
                if match_id in home_feats.index and match_id in away_feats.index:
                    h = home_feats.loc[match_id]
                    a = away_feats.loc[match_id]
                    
                    # Proteção contra índices duplicados no Pandas
                    h_val = h.iloc[0] if isinstance(h, pd.DataFrame) else h
                    a_val = a.iloc[0] if isinstance(a, pd.DataFrame) else a
                    
                    records_to_insert.append((
                        int(match_id),
                        int(h_val['rest_days']), int(a_val['rest_days']),
                        round(float(h_val['xg_for_ewma_micro']), 2), round(float(h_val['xg_against_ewma_micro']), 2),
                        round(float(a_val['xg_for_ewma_micro']), 2), round(float(a_val['xg_against_ewma_micro']), 2),
                        round(float(h_val['xg_for_ewma_macro']), 2), round(float(a_val['xg_for_ewma_macro']), 2),
                        round(float(h_val['aggression_ewma']), 2), round(float(a_val['aggression_ewma']), 2)
                    ))

            logger.info("💾 Salvando Tensores no PostgreSQL (Copy)...")
            try:
                await conn.copy_records_to_table(
                    'match_temporal_features', schema_name='core',
                    records=records_to_insert,
                    columns=[
                        'match_id', 'home_rest_days', 'away_rest_days', 
                        'home_xg_for_ewma_micro', 'home_xg_against_ewma_micro',
                        'away_xg_for_ewma_micro', 'away_xg_against_ewma_micro',
                        'home_xg_for_ewma_macro', 'away_xg_for_ewma_macro',
                        'home_aggression_ewma', 'away_aggression_ewma'
                    ]
                )
            except Exception as e:
                logger.error(f"❌ Falha ao gravar tensores no banco: {e}")

        await db.disconnect()
        logger.info("[DONE] MÁQUINA TEMPORAL CONCLUÍDA. As Mentes dos Clubes foram mapeadas.")

if __name__ == "__main__":
    engine = TemporalFeaturesEngine()
    asyncio.run(engine.run_temporal_engine())