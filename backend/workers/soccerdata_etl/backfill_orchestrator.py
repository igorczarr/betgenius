# betgenius-backend/workers/soccerdata_etl/backfill_orchestrator.py

import sys
import os
from pathlib import Path
import asyncio
import logging
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    print(f"CRITICO: Arquivo .env nao encontrado no caminho: {ENV_PATH}")
    sys.exit(1)

file_handler = logging.FileHandler("etl_10_years_backfill.log", encoding="utf-8")
console_handler = logging.StreamHandler(sys.stdout)
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)

import config
from extractors.fbref_bot import FBrefExtractor
from extractors.odds_bot import OddsExtractor
from extractors.clubelo_bot import ClubEloExtractor
from extractors.understat_bot import UnderstatExtractor
from transformers.merger import DataMerger
from loaders.pg_loader import PostgresLoader

def get_season_string(date_obj):
    year = date_obj.year
    if date_obj.month < 7:
        return f"{str(year - 1)[-2:]}{str(year)[-2:]}"
    else:
        return f"{str(year)[-2:]}{str(year + 1)[-2:]}"

async def backfill_historical_data(start_date_str, end_date_str):
    logger.info(f"[INIT] INICIANDO DUMP HISTÓRICO: {start_date_str} até {end_date_str}")
    
    merger = DataMerger()
    loader = PostgresLoader()
    
    await loader.connect()

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    delta = timedelta(days=1)
    current_date = start_date

    while current_date <= end_date:
        target_str = current_date.strftime("%Y-%m-%d")
        correct_season = get_season_string(current_date)
        config.ALL_SEASONS = [correct_season]
        
        logger.info(f"[PROCESSANDO] Data: {target_str} (Temporada Alvo: {correct_season})")
        
        try:
            fbref = FBrefExtractor(target_date=target_str)
            odds = OddsExtractor(target_date=target_str)
            elo = ClubEloExtractor(target_date=target_str)
            understat = UnderstatExtractor(target_date=target_str)

            df_fbref_games = await asyncio.to_thread(fbref.get_daily_schedule)
            
            if df_fbref_games.empty:
                current_date += delta
                continue

            df_elo = await asyncio.to_thread(elo.get_global_ratings)
            df_odds = await asyncio.to_thread(odds.get_closing_lines)
            df_understat = await asyncio.to_thread(understat.get_team_match_metrics)

            alpha_matrix = merger.create_alpha_matrix(df_fbref_games, df_odds, df_elo, df_understat)
            
            if not alpha_matrix.empty:
                await loader.upsert_alpha_matrix(alpha_matrix)

        except Exception as e:
            logger.error(f"  -> [ERRO] Falha na data {target_str}: {e}")

        current_date += delta

    await loader.close()
    logger.info("[DONE] BASE DE DADOS PREENCHIDA COM SUCESSO.")

if __name__ == "__main__":
    # ===============================================================
    # O MOTOR DO TEMPO (AGOSTO/2015 ATÉ HOJE)
    # ===============================================================
    DATA_INICIO = "2015-08-01" 
    DATA_FIM = datetime.now().strftime("%Y-%m-%d")
    
    # IMPORTANTE: Este processo pode levar horas/dias dependendo da sua internet.
    # Você pode parar com CTRL+C e alterar a DATA_INICIO para continuar de onde parou.
    asyncio.run(backfill_historical_data(DATA_INICIO, DATA_FIM))