# betgenius-backend/workers/api_integrations/clubelo_historical_updater.py

import sys
import os
import io

# =====================================================================
# FIX DEFINITIVO DE UNICODE PARA WINDOWS/LINUX
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
from pathlib import Path
from datetime import datetime
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import soccerdata as sd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from core.database import db
from engine.entity_resolution import entity_resolver

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [CLUB-ELO-UPDATER] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class ClubEloDailyUpdater:
    """
    Sincronizador Institucional de Elo (Atualização Diária).
    Puxa a fotografia de Força Global dos times europeus para o dia atual
    e atualiza a tabela 'team_current_elo' consumida pela nossa IA.
    """
    def __init__(self):
        self.today_date = datetime.now().strftime('%Y-%m-%d')

    def _flatten_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty: return pd.DataFrame()
        df = df.reset_index()
        df.columns = [str(col).lower().strip() for col in df.columns]
        return df

    async def run(self):
        logger.info("=========================================================")
        logger.info(f"🔄 INICIANDO ATUALIZAÇÃO DO ELO GLOBAL: {self.today_date}")
        logger.info("=========================================================")
        
        await db.connect()
        await entity_resolver.load_mappings_from_db()
        
        try:
            # soccerdata ClubElo consome arquivos CSV estáticos diretos do criador
            elo_api = sd.ClubElo()
            
            logger.info(f"📡 Baixando Snapshot de Elo Oficial do dia...")
            df_snapshot = self._flatten_columns(elo_api.read_by_date(self.today_date))
            
            club_col = next((c for c in df_snapshot.columns if 'club' in c or 'team' in c), None)
            elo_col = next((c for c in df_snapshot.columns if 'elo' in c), None)
            
            if not club_col or not elo_col:
                logger.error("❌ Colunas do ClubElo não identificadas na API. Abortando.")
                return
                
            df_snapshot = df_snapshot.dropna(subset=[club_col, elo_col])
            logger.info(f"✅ Download concluído: {len(df_snapshot)} clubes no index global.")

            async with db.pool.acquire() as conn:
                # Garante que a tabela existe
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS core.team_current_elo (
                        team_id INTEGER PRIMARY KEY,
                        current_elo NUMERIC(10, 2),
                        games_played INTEGER DEFAULT 0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                logger.info("🔍 Aplicando Resolução de Entidades S-Tier e injetando no Banco...")
                
                updated_count = 0
                async with conn.transaction():
                    for _, row in df_snapshot.iterrows():
                        raw_club_name = str(row[club_col])
                        elo_value = float(row[elo_col])
                        
                        # Usa a nossa camada NLP para resolver "Man United" -> "Manchester United"
                        canonical_name = await entity_resolver.normalize_name(raw_club_name)
                        
                        if not canonical_name: continue
                        
                        # Descobre o ID interno do nosso banco de dados
                        team_id = await conn.fetchval("SELECT id FROM core.teams WHERE canonical_name = $1", canonical_name)
                        
                        if team_id:
                            # Proteção Cirúrgica de UPSERT (Se existe atualiza, se não, insere)
                            record_exists = await conn.fetchval("SELECT team_id FROM core.team_current_elo WHERE team_id = $1", team_id)
                            
                            if record_exists:
                                await conn.execute("""
                                    UPDATE core.team_current_elo 
                                    SET current_elo = $1, last_updated = NOW() 
                                    WHERE team_id = $2
                                """, elo_value, team_id)
                            else:
                                await conn.execute("""
                                    INSERT INTO core.team_current_elo (team_id, current_elo, last_updated) 
                                    VALUES ($1, $2, NOW())
                                """, team_id, elo_value)
                                
                            updated_count += 1

                logger.info(f"🏆 SISTEMA ATUALIZADO: {updated_count} equipes tiveram o Elo recalibrado para a rodada de hoje.")

        except Exception as e:
            logger.error(f"❌ Falha Crítica no Updater Diário: {e}")
        finally:
            await db.disconnect()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(ClubEloDailyUpdater().run())