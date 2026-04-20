# betgenius-backend/workers/soccerdata_etl/orchestrator.py

import asyncio
import logging
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import os
from datetime import datetime, timedelta

# Importa as peças do nosso quebra-cabeça
from extractors.fbref_bot import FBrefExtractor
from extractors.odds_bot import OddsExtractor
from extractors.clubelo_bot import ClubEloExtractor
from extractors.understat_bot import UnderstatExtractor
from extractors.sofifa_bot import SoFIFAExtractor
from extractors.whoscored_bot import WhoScoredExtractor # <--- ADICIONADO
from transformers.merger import DataMerger
from loaders.pg_loader import PostgresLoader

# Setup de Logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s [ORCHESTRATOR] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

async def run_pipeline(target_date=None):
    if not target_date:
        target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    logger.info(f"🚀 INICIANDO USINA DE DADOS | DATA ALVO: {target_date}")

    # 1. INSTANCIA EXTRATORES
    fbref = FBrefExtractor(target_date=target_date)
    odds = OddsExtractor(target_date=target_date)
    elo = ClubEloExtractor(target_date=target_date)
    understat = UnderstatExtractor(target_date=target_date)
    sofifa = SoFIFAExtractor()
    whoscored = WhoScoredExtractor(target_date=target_date) # <--- ADICIONADO
    
    # 2. INSTANCIA TRANSFORMADOR E LOADER
    merger = DataMerger()
    loader = PostgresLoader()

    try:
        # --- ETAPA: EXTRAÇÃO ---
        # Usamos asyncio.to_thread() para não bloquear o Event Loop principal.
        # Rodamos sequencialmente para evitar que o SQLite nativo do soccerdata dê erro de "database is locked".
        logger.info("📡 Iniciando Fase de Extração...")
        df_fbref_games = await asyncio.to_thread(fbref.get_daily_schedule)
        df_fbref_players = await asyncio.to_thread(fbref.get_player_leaders_kpis)
        df_elo = await asyncio.to_thread(elo.get_global_ratings)
        
        df_odds = await asyncio.to_thread(odds.get_closing_lines)
        df_understat = await asyncio.to_thread(understat.get_team_match_metrics)
        df_sofifa_players = await asyncio.to_thread(sofifa.get_player_ratings)
        df_ws_missing = await asyncio.to_thread(whoscored.get_missing_players) # <--- ADICIONADO

        # --- ETAPA: TRANSFORMAÇÃO ---
        logger.info("🔄 Iniciando Fase de Transformação (Merger)...")
        alpha_matrix = merger.create_alpha_matrix(df_fbref_games, df_odds, df_elo, df_understat)
        player_kpis = merger.create_player_stats(df_fbref_players, df_sofifa_players)

        # --- ETAPA: CARREGAMENTO ---
        logger.info("💾 Iniciando Fase de Carregamento (Loader)...")
        await loader.connect()
        
        if not alpha_matrix.empty:
            await loader.upsert_alpha_matrix(alpha_matrix)
        
        if not player_kpis.empty:
            await loader.upsert_player_kpis(player_kpis)

        # <--- ADICIONADO: Envia a tabela de Lesionados para o banco
        if not df_ws_missing.empty:
            await loader.upsert_missing_players(df_ws_missing)

        await loader.close()
        logger.info("🏆 PIPELINE CONCLUÍDO COM SUCESSO. DADOS NO COFRE.")

    except Exception as e:
        logger.error(f"❌ FALHA CRÍTICA NO PIPELINE: {e}")
        if loader.pool:
            await loader.close()

if __name__ == "__main__":
    # Para testes ou rodadas manuais, ele pega "ontem" automaticamente
    asyncio.run(run_pipeline())