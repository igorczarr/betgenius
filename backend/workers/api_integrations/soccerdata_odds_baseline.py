# betgenius-backend/workers/api_integrations/soccerdata_odds_baseline.py
import sys
import os
import io

# Blindagem de Encoding para Windows
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
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import soccerdata as sd

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.database import db
from engine.entity_resolution import entity_resolver

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [ODDS-BATEDOR] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class SoccerDataOddsBaseline:
    """
    Batedor de Linhas Iniciais.
    Usa o MatchHistory (football-data.co.uk) para capturar as Odds de Abertura (1X2, O/U) 
    dos próximos jogos, poupando a cota da The Odds API.
    """
    def __init__(self):
        self.leagues = {
            "soccer_epl": "ENG-Premier League",
            "soccer_spain_la_liga": "ESP-La Liga",
            "soccer_italy_serie_a": "ITA-Serie A",
            "soccer_germany_bundesliga": "GER-Bundesliga",
            "soccer_france_ligue_one": "FRA-Ligue 1",
            "soccer_portugal_primeira_liga": "POR-Primeira Liga",
            "soccer_netherlands_eredivisie": "NED-Eredivisie"
            # football-data.co.uk foca majoritariamente em ligas nacionais europeias.
        }

    def _get_season_string(self) -> str:
        now = datetime.now()
        return f"{str(now.year - 1)[-2:]}{str(now.year)[-2:]}" if now.month < 7 else f"{str(now.year)[-2:]}{str(now.year + 1)[-2:]}"

    async def _process_market(self, conn, match_id: int, categoria: str, nome_mercado: str, odd: float):
        if pd.isna(odd) or odd <= 1.0: return
        
        # Insere a Odd de Abertura se o mercado não existir. Se existir, não sobrescreve a current_odd (que pode estar sendo gerida pelo The Odds API)
        await conn.execute("""
            INSERT INTO core.market_odds 
            (match_id, categoria, nome_mercado, bookmaker, current_odd, opening_odd, heavy_drop_alert)
            VALUES ($1, $2, $3, 'bet365', $4, $4, FALSE)
            ON CONFLICT DO NOTHING
        """, match_id, categoria, nome_mercado, float(odd))

    async def process_upcoming_odds(self, sport_key: str, sd_league: str, season_str: str):
        logger.info(f"📡 Buscando Odds de Abertura para {sd_league}...")
        try:
            # MatchHistory é a fonte de Odds pré-jogo do soccerdata
            mh = sd.MatchHistory(leagues=sd_league, seasons=season_str, no_cache=True)
            df = mh.read_games().reset_index()
            
            if df.empty: return
            
            # 1. Filtra apenas jogos que ainda vão acontecer (Futuro)
            df['date_parsed'] = pd.to_datetime(df['date'])
            df_future = df[df['date_parsed'] >= pd.Timestamp(datetime.now().date())]
            
            if df_future.empty:
                logger.info(f"Nenhum jogo futuro com odds disponível no momento para {sd_league}.")
                return

            async with db.pool.acquire() as conn:
                async with conn.transaction():
                    saved = 0
                    for _, row in df_future.iterrows():
                        home_canonical = await entity_resolver.normalize_name(str(row.get('home_team', '')), False)
                        away_canonical = await entity_resolver.normalize_name(str(row.get('away_team', '')), False)
                        
                        # Acha a partida agendada no nosso banco
                        match_id = await conn.fetchval("""
                            SELECT m.id FROM core.matches_history m
                            JOIN core.teams th ON m.home_team_id = th.id
                            JOIN core.teams ta ON m.away_team_id = ta.id
                            WHERE th.canonical_name = $1 AND ta.canonical_name = $2 AND m.status = 'SCHEDULED'
                        """, home_canonical, away_canonical)
                        
                        if not match_id: continue

                        # 2. Extração Segura das Odds da Bet365 (B365) e Pinnacle (PS) que vêm no CSV
                        # Mercado: Match Odds (1X2)
                        await self._process_market(conn, match_id, 'h2h', '1', row.get('B365H'))
                        await self._process_market(conn, match_id, 'h2h', 'x', row.get('B365D'))
                        await self._process_market(conn, match_id, 'h2h', '2', row.get('B365A'))
                        
                        # Mercado: Gols (Over/Under 2.5)
                        await self._process_market(conn, match_id, 'totals', 'Over/Under 2.5 - Over', row.get('B365>2.5'))
                        await self._process_market(conn, match_id, 'totals', 'Over/Under 2.5 - Under', row.get('B365<2.5'))

                        saved += 1
                        
            logger.info(f"✅ {saved} jogos de {sd_league} preenchidos com Baseline Odds.")

        except Exception as e:
            logger.warning(f"⚠️ Aviso ao processar Odds para {sd_league}: {e}")

    async def run(self):
        logger.info("=== INICIANDO BATEDOR DE ODDS (SOCCERDATA) ===")
        await db.connect()
        await entity_resolver.load_mappings_from_db()
        
        season_str = self._get_season_string()
        
        for sport_key, sd_league in self.leagues.items():
            await self.process_upcoming_odds(sport_key, sd_league, season_str)
            await asyncio.sleep(2)
            
        await db.disconnect()
        logger.info("=== BATEDOR FINALIZADO. Cota API Preservada ===")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(SoccerDataOddsBaseline().run())