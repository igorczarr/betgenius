# betgenius-backend/workers/feature_engineering/temporal_features_engine.py

import sys
import os
import io

if sys.platform == "win32":
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
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Blindagem para logs limpos no Pandas 3.0+
pd.set_option('future.no_silent_downcasting', True)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [TEMPORAL-ENGINE] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class TemporalFeaturesEngine:
    """
    Motor S-Tier de Features Temporais (Rolling Update).
    Aplica EWMA (Médias Móveis) sobre xG e Agressividade no Passado,
    e projeta o Momentum Tático e a Fadiga (Rest Days) para os jogos do Futuro
    imputando as médias móveis nas lacunas de dados.
    """

    def __init__(self):
        self.MICRO_SPAN = 5   # Curto prazo (Momento atual / Últimos 5 jogos)
        self.MACRO_SPAN = 15  # Longo prazo (Força consolidada / Últimos 15 jogos)

    async def initialize_schema(self, conn):
        logger.info("🛠️ Validando Schema Temporal...")
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
        # TRUNCATE removido para permitir Rolling Updates.

    def _build_team_perspective_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transforma 1 jogo (Casa vs Fora) em 2 registros (Visão Casa, Visão Fora)."""
        
        # Visão Mandante
        df_home = df[['match_id', 'match_date', 'status', 'home_team_id', 'xg_home', 'xg_away', 
                      'home_fouls', 'home_yellow', 'home_red']].copy()
        df_home.columns = ['match_id', 'date', 'status', 'team_id', 'xg_for', 'xg_against', 
                           'fouls', 'yellow', 'red']
        df_home['is_home'] = 1

        # Visão Visitante
        df_away = df[['match_id', 'match_date', 'status', 'away_team_id', 'xg_away', 'xg_home', 
                      'away_fouls', 'away_yellow', 'away_red']].copy()
        df_away.columns = ['match_id', 'date', 'status', 'team_id', 'xg_for', 'xg_against', 
                           'fouls', 'yellow', 'red']
        df_away['is_home'] = 0

        # Une e ordena cronologicamente
        df_teams = pd.concat([df_home, df_away], ignore_index=True)
        df_teams['date'] = pd.to_datetime(df_teams['date'])
        df_teams = df_teams.sort_values(by=['team_id', 'date', 'match_id']).reset_index(drop=True)
        
        # BLINDAGEM QUANTITATIVA E IMPUTAÇÃO PREDITIVA:
        # Em vez de converter para NaN, nós preenchemos as lacunas do futuro (SCHEDULED) 
        # com a média móvel da própria equipe até aquele momento.
        stat_cols = ['xg_for', 'xg_against', 'fouls', 'yellow', 'red']
        
        for col in stat_cols:
            df_teams[col] = pd.to_numeric(df_teams[col], errors='coerce')
            
            # O pulo do gato: Substitui os valores nulos projetando o EWMA da equipe
            df_teams[col] = df_teams.groupby('team_id')[col].transform(
                lambda x: x.fillna(x.ewm(span=self.MICRO_SPAN, adjust=False, ignore_na=True).mean().shift(1))
            )
            # Fallback para o primeiro jogo da história (se a equipe não tiver jogos passados)
            df_teams[col] = df_teams[col].fillna(0)

        # Cria Agressividade (Faltas e Cartões) baseada nos dados reais ou na média projetada
        df_teams['aggression'] = df_teams['fouls'] + (df_teams['yellow'] * 2) + (df_teams['red'] * 5)

        return df_teams

    def _calculate_ewma_features(self, df_teams: pd.DataFrame) -> pd.DataFrame:
        """Aplica as Médias Móveis Exponenciais consolidadas."""
        
        grouped = df_teams.groupby('team_id')

        # 1. Cálculo do Rest Disadvantage (Fadiga Física)
        df_teams['rest_days'] = grouped['date'].diff().dt.days
        df_teams['rest_days'] = df_teams['rest_days'].fillna(7).clip(upper=15) 

        # 2. As Médias Móveis (O SHIFT 1 garante que o jogo de hoje só veja até ontem)
        df_teams['xg_for_ewma_micro'] = grouped['xg_for'].transform(lambda x: x.ewm(span=self.MICRO_SPAN, adjust=False).mean().shift(1))
        df_teams['xg_against_ewma_micro'] = grouped['xg_against'].transform(lambda x: x.ewm(span=self.MICRO_SPAN, adjust=False).mean().shift(1))
        
        df_teams['xg_for_ewma_macro'] = grouped['xg_for'].transform(lambda x: x.ewm(span=self.MACRO_SPAN, adjust=False).mean().shift(1))
        
        df_teams['aggression_ewma'] = grouped['aggression'].transform(lambda x: x.ewm(span=10, adjust=False).mean().shift(1))

        # 3. FORWARD FILL Secundário de Segurança
        df_teams['xg_for_ewma_micro'] = grouped['xg_for_ewma_micro'].ffill()
        df_teams['xg_against_ewma_micro'] = grouped['xg_against_ewma_micro'].ffill()
        df_teams['xg_for_ewma_macro'] = grouped['xg_for_ewma_macro'].ffill()
        df_teams['aggression_ewma'] = grouped['aggression_ewma'].ffill()

        # 4. Fallback Institucional (Bayesian Prior)
        df_teams = df_teams.fillna({
            'xg_for_ewma_micro': 1.35, 'xg_against_ewma_micro': 1.35, 
            'xg_for_ewma_macro': 1.35, 'aggression_ewma': 10.0
        })

        return df_teams

    async def run_temporal_engine(self):
        logger.info("[INIT] INICIANDO TEMPORAL ENGINE: Fadiga e EWMA Preditivo.")
        await db.connect()
        
        async with db.pool.acquire() as conn:
            await self.initialize_schema(conn)
            
            logger.info("📥 Extraindo Matriz de Jogos (Passado e Futuro)...")
            
            query = """
                SELECT id as match_id, match_date, status, home_team_id, away_team_id,
                       xg_home, xg_away, home_fouls, away_fouls, home_yellow, away_yellow, home_red, away_red
                FROM core.matches_history
                WHERE status IN ('FINISHED', 'SCHEDULED')
                ORDER BY match_date ASC, id ASC
            """
            matches = await conn.fetch(query)
            
            if not matches:
                logger.error("❌ Histórico vazio. Abortando Temporal Engine.")
                await db.disconnect()
                return

            df = pd.DataFrame([dict(m) for m in matches])

            logger.info("🧬 Isolando Linha do Tempo por Equipe com Imputação de Média...")
            df_teams = self._build_team_perspective_df(df)
            
            logger.info("📈 Computando EWMA e Projetando Fadiga para próximos jogos...")
            df_features = self._calculate_ewma_features(df_teams)

            logger.info("🔄 Recombinando Tensores...")
            
            # FILTRO DE OTIMIZAÇÃO: Atualizamos apenas a última semana e o futuro
            cutoff_date = pd.Timestamp(datetime.now().date() - timedelta(days=7))
            df_to_update = df_features[df_features['date'] >= cutoff_date]

            home_feats = df_to_update[df_to_update['is_home'] == 1].set_index('match_id')
            away_feats = df_to_update[df_to_update['is_home'] == 0].set_index('match_id')

            records_to_upsert = []
            valid_match_ids = df_to_update['match_id'].unique()
            
            for match_id in valid_match_ids:
                if match_id in home_feats.index and match_id in away_feats.index:
                    h = home_feats.loc[match_id]
                    a = away_feats.loc[match_id]
                    
                    h_val = h.iloc[0] if isinstance(h, pd.DataFrame) else h
                    a_val = a.iloc[0] if isinstance(a, pd.DataFrame) else a
                    
                    records_to_upsert.append((
                        int(match_id),
                        int(h_val['rest_days']), int(a_val['rest_days']),
                        round(float(h_val['xg_for_ewma_micro']), 2), round(float(h_val['xg_against_ewma_micro']), 2),
                        round(float(a_val['xg_for_ewma_micro']), 2), round(float(a_val['xg_against_ewma_micro']), 2),
                        round(float(h_val['xg_for_ewma_macro']), 2), round(float(a_val['xg_for_ewma_macro']), 2),
                        round(float(h_val['aggression_ewma']), 2), round(float(a_val['aggression_ewma']), 2)
                    ))

            if records_to_upsert:
                logger.info(f"💾 Projetando {len(records_to_upsert)} tensores temporais no Data Warehouse (UPSERT)...")
                try:
                    await conn.executemany("""
                        INSERT INTO core.match_temporal_features (
                            match_id, home_rest_days, away_rest_days, 
                            home_xg_for_ewma_micro, home_xg_against_ewma_micro,
                            away_xg_for_ewma_micro, away_xg_against_ewma_micro,
                            home_xg_for_ewma_macro, away_xg_for_ewma_macro,
                            home_aggression_ewma, away_aggression_ewma
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        ON CONFLICT (match_id) DO UPDATE SET
                            home_rest_days = EXCLUDED.home_rest_days,
                            away_rest_days = EXCLUDED.away_rest_days,
                            home_xg_for_ewma_micro = EXCLUDED.home_xg_for_ewma_micro,
                            home_xg_against_ewma_micro = EXCLUDED.home_xg_against_ewma_micro,
                            away_xg_for_ewma_micro = EXCLUDED.away_xg_for_ewma_micro,
                            away_xg_against_ewma_micro = EXCLUDED.away_xg_against_ewma_micro,
                            home_xg_for_ewma_macro = EXCLUDED.home_xg_for_ewma_macro,
                            away_xg_for_ewma_macro = EXCLUDED.away_xg_for_ewma_macro,
                            home_aggression_ewma = EXCLUDED.home_aggression_ewma,
                            away_aggression_ewma = EXCLUDED.away_aggression_ewma;
                    """, records_to_upsert)
                except Exception as e:
                    logger.error(f"❌ Falha ao realizar UPSERT temporal no banco: {e}")
            else:
                logger.info("ℹ️ Nenhuma métrica temporal precisou ser atualizada hoje.")

        await db.disconnect()
        logger.info("[DONE] MÁQUINA TEMPORAL PREDITIVA CONCLUÍDA. A Matriz Tática está projetada.")

if __name__ == "__main__":
    engine = TemporalFeaturesEngine()
    asyncio.run(engine.run_temporal_engine())