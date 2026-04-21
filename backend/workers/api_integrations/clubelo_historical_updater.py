# betgenius-backend/workers/api_integrations/clubelo_historical_updater.py
import sys
import os
import io

# FIX DEFINITIVO DE UNICODE PARA WINDOWS
if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except AttributeError:
        pass

import asyncio
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
from rapidfuzz import process, fuzz
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import soccerdata as sd

sys.path.append(str(Path(__file__).parent.parent.parent))
from core.database import db

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [CLUB-ELO] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class ClubEloHistoricalUpdater:
    """
    Motor Quantitativo de Rating (Feature Store).
    Cruza as entidades do banco com o ClubElo e ingere a evolução
    matemática de força das equipes europeias desde 2015.
    """
    def __init__(self):
        self.start_date = '2015-01-01'

    def _flatten_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty: return pd.DataFrame()
        df = df.reset_index()
        df.columns = [str(col).lower().strip() for col in df.columns]
        return df

    async def run(self):
        logger.info("=== INICIANDO MOTOR DE CLUB ELO (HISTÓRICO) ===")
        await db.connect()
        
        try:
            elo_api = sd.ClubElo()
            
            # 1. Puxa a lista de hoje para conhecer os nomes oficiais usados pelo ClubElo
            logger.info("📡 Baixando dicionário global de entidades do ClubElo...")
            df_today = self._flatten_columns(elo_api.read_by_date())
            
            # ClubElo geralmente usa 'club' ou 'team'
            club_col = next((c for c in df_today.columns if 'club' in c or 'team' in c), None)
            if not club_col:
                logger.error("❌ Formato do ClubElo mudou. Abortando.")
                await db.disconnect()
                return
                
            clubelo_official_names = df_today[club_col].dropna().unique().tolist()
            logger.info(f"✅ {len(clubelo_official_names)} clubes europeus encontrados na API.")

            # 2. Busca os times do nosso banco
            db_teams = await db.pool.fetch("SELECT id, canonical_name FROM core.teams")
            
            async with db.pool.acquire() as conn:
                for team in db_teams:
                    team_id = team['id']
                    team_name = team['canonical_name']
                    
                    # 3. Fuzzy Match S-Tier
                    match_result = process.extractOne(team_name, clubelo_official_names, scorer=fuzz.WRatio)
                    
                    if not match_result: continue
                    best_match, score, _ = match_result
                    
                    # Como o ClubElo é só Europa, usamos um limiar alto para não cruzar o "Flamengo" com o "Flamengo de Pefine" de Portugal
                    if score >= 88.0:
                        logger.info(f"🔍 {team_name} matched com '{best_match}' (Score: {score:.1f}%). Baixando histórico...")
                        
                        try:
                            # 4. Baixa a vida inteira do time
                            df_hist = self._flatten_columns(elo_api.read_team_history(best_match))
                            
                            if df_hist.empty: continue
                            
                            # Filtra apenas registros de 2015 em diante
                            from_col = next((c for c in df_hist.columns if 'from' in c), None)
                            to_col = next((c for c in df_hist.columns if 'to' in c), None)
                            elo_col = next((c for c in df_hist.columns if 'elo' in c), None)
                            
                            if not from_col or not to_col or not elo_col: continue
                            
                            df_hist[from_col] = pd.to_datetime(df_hist[from_col])
                            df_hist = df_hist[df_hist[from_col] >= pd.to_datetime(self.start_date)]
                            
                            # 5. Bulk Insert Otimizado
                            records = []
                            for _, row in df_hist.iterrows():
                                records.append((
                                    team_id, 
                                    best_match,
                                    row[from_col].date(),
                                    pd.to_datetime(row[to_col]).date(),
                                    float(row[elo_col])
                                ))
                                
                            await conn.executemany("""
                                INSERT INTO core.team_elo_history (team_id, clubelo_name, valid_from, valid_to, elo)
                                VALUES ($1, $2, $3, $4, $5)
                                ON CONFLICT (team_id, valid_from) DO UPDATE SET elo = EXCLUDED.elo, valid_to = EXCLUDED.valid_to
                            """, records)
                            
                            logger.info(f"✅ Histórico salvo: {len(records)} ranges de Elo inseridos para {team_name}.")
                            
                            # Pausa leve por respeito ao servidor do api.clubelo.com (Eles são em formato CSV raiz)
                            await asyncio.sleep(1.0)
                            
                        except Exception as e:
                            logger.error(f"❌ Erro ao baixar histórico de {best_match}: {e}")

        except Exception as e:
            logger.error(f"❌ Falha Crítica no Motor Elo: {e}")
            
        await db.disconnect()
        logger.info("=== PROCESSO DE HISTÓRICO ELO FINALIZADO ===")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(ClubEloHistoricalUpdater().run())