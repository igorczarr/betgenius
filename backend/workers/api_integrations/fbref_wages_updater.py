# betgenius-backend/workers/api_integrations/fbref_wages_updater.py
import sys
import os
import io
import asyncio
import logging
import pandas as pd
from io import StringIO
import random
from pathlib import Path
import re

# FIX DEFINITIVO DE UNICODE PARA WINDOWS
if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except AttributeError:
        pass

import nodriver as uc

# Adiciona o backend ao path para importações absolutas
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.database import db
from engine.entity_resolution import entity_resolver

# Log ASCII Clean
class SafeASCIIFormatter(logging.Formatter):
    def format(self, record):
        msg = super().format(record)
        return msg.encode('ascii', 'ignore').decode('ascii')

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(SafeASCIIFormatter("%(asctime)s [WAGE-EXTRACTOR] %(levelname)s: %(message)s"))

logger = logging.getLogger()
logger.setLevel(logging.INFO)
for h in logger.handlers[:]: logger.removeHandler(h)
logger.addHandler(handler)

class FBrefWagesUpdater:
    """
    Motor Financeiro S-Tier.
    Usa o Ghost Monitor (Nodriver) para burlar a limitação da SoccerData
    e extrair a Folha Salarial Anual das equipes de 2015 a 2025.
    """
    def __init__(self):
        self.start_year = 2015
        self.end_year = 2025
        self.browser = None
        
        # Mapeamento do FBref (ID da Liga e Nome na URL)
        self.league_config = {
            "soccer_epl": {"id": "9", "name": "Premier-League", "cross": True},
            "soccer_spain_la_liga": {"id": "12", "name": "La-Liga", "cross": True},
            "soccer_italy_serie_a": {"id": "11", "name": "Serie-A", "cross": True},
            "soccer_germany_bundesliga": {"id": "20", "name": "Bundesliga", "cross": True},
            "soccer_france_ligue_one": {"id": "13", "name": "Ligue-1", "cross": True},
            "soccer_netherlands_eredivisie": {"id": "23", "name": "Eredivisie", "cross": True},
            "soccer_portugal_primeira_liga": {"id": "32", "name": "Primeira-Liga", "cross": True},
            "soccer_brazil_campeonato": {"id": "24", "name": "Serie-A", "cross": False},
            "soccer_usa_mls": {"id": "22", "name": "Major-League-Soccer", "cross": False},
            "soccer_brazil_serie_b": {"id": "38", "name": "Serie-B", "cross": False},
            "soccer_sweden_allsvenskan": {"id": "29", "name": "Allsvenskan", "cross": False},
            "soccer_norway_eliteserien": {"id": "28", "name": "Eliteserien", "cross": False},
            "soccer_denmark_superliga": {"id": "50", "name": "Superliga", "cross": True},
            "soccer_japan_j_league": {"id": "40", "name": "J1-League", "cross": False}
        }

    def _build_wage_url(self, sport_key: str, year: int) -> tuple:
        config = self.league_config.get(sport_key)
        if not config: return None, None
            
        if config["cross"]:
            season_str = f"{year}-{year+1}"
        else:
            season_str = str(year)
            
        # URL Específica de Salários (Capology via FBref)
        url = f"https://fbref.com/en/comps/{config['id']}/{season_str}/wages/{season_str}-{config['name']}-Wages"
        return url, season_str

    async def _init_browser(self):
        if not self.browser:
            logger.info("Iniciando Motor Crawler (Modo 'Ghost Monitor')...")
            self.browser = await uc.start(
                headless=False,
                browser_args=[
                    "--window-position=-32000,-32000",
                    "--window-size=1920,1080",
                    "--disable-notifications",
                    "--no-sandbox"
                ]
            )

    async def fetch_wage_html(self, url: str) -> str:
        await self._init_browser()
        await asyncio.sleep(3.0) 
        
        for attempt in range(3):
            tab = None
            try:
                tab = await self.browser.get(url, new_tab=True)
                passed = False
                
                for i in range(12):
                    await asyncio.sleep(1.5)
                    html = await tab.get_content()
                    
                    # Identifica se a tabela de salários carregou ou se a página não existe
                    if "Annual Wages" in html or "Weekly Wages" in html:
                        passed = True
                        break
                    elif "Just a moment" in html or "cf-turnstile" in html:
                        if i % 3 == 0:
                            await tab.evaluate(f"window.scrollBy(0, {random.randint(100, 300)});")
                        continue
                    elif "404 Not Found" in html or "Page Not Found" in html or "does not have wage data" in html:
                        await tab.close()
                        return "NO_DATA"
                        
                if passed:
                    final_html = await tab.get_content()
                    await tab.close()
                    return final_html
                else:
                    if tab: await tab.close()
                    
            except Exception as e:
                if tab: await tab.close()
                await asyncio.sleep(5)
                
        return None

    def clean_currency(self, value_str: str) -> float:
        """Remove símbolos ($, €, £, R$), vírgulas e espaços para extrair o valor puro."""
        if pd.isna(value_str): return 0.0
        clean_str = str(value_str).replace(',', '').replace(' ', '')
        # Extrai apenas os números
        numbers = re.findall(r'\d+', clean_str)
        if numbers:
            return float(numbers[0])
        return 0.0

    def _extract_dataframe(self, html_content: str) -> pd.DataFrame:
        try:
            html_clean = html_content.replace('', '')
            dfs = pd.read_html(StringIO(html_clean))
            
            for df in dfs:
                if isinstance(df.columns, pd.MultiIndex):
                     df.columns = ['_'.join(str(c) for c in col if c and not str(c).startswith('Unnamed')).strip() for col in df.columns]
                else:
                     df.columns = [str(col).strip() for col in df.columns]
                
                if any('Squad' in col for col in df.columns) and any('Annual' in col for col in df.columns):
                    return df
        except:
            pass
        return pd.DataFrame()

    async def auto_register_team(self, conn, canonical_name: str, sport_key: str) -> int:
        league_id = await conn.fetchval("SELECT id FROM core.leagues WHERE sport_key = $1", sport_key)
        team_id = await conn.fetchval("SELECT id FROM core.teams WHERE canonical_name = $1", canonical_name)
        if not team_id:
            team_id = await conn.fetchval(
                "INSERT INTO core.teams (canonical_name, league_id) VALUES ($1, $2) RETURNING id",
                canonical_name, league_id
            )
        return team_id

    async def process_season(self, sport_key: str, year: int):
        url, season_str = self._build_wage_url(sport_key, year)
        if not url: return
        
        logger.info(f"Buscando Folha Salarial: {sport_key} ({season_str})")
        html = await self.fetch_wage_html(url)
        
        if html == "NO_DATA":
            logger.info(f"-> Sem dados financeiros publicos para {sport_key} {season_str}. Pulando.")
            return
        elif not html:
            logger.warning(f"-> Bloqueio/Erro ao acessar {sport_key} {season_str}.")
            return
        
        df = self._extract_dataframe(html)
        if df.empty:
            logger.warning(f"-> Tabela nao encontrada no HTML para {sport_key} {season_str}.")
            return
            
        squad_col = next((c for c in df.columns if 'Squad' in c), None)
        wage_col = next((c for c in df.columns if 'Annual' in c), None)
        
        if not squad_col or not wage_col:
            return

        updated_count = 0
        async with db.pool.acquire() as conn:
            # Garante que a tabela existe (caso não tenha sido criada antes)
            await conn.execute("""
                CREATE SCHEMA IF NOT EXISTS fbref_squad;
                CREATE TABLE IF NOT EXISTS fbref_squad.standings_wages (
                    team_id INTEGER, season VARCHAR(10), pts INTEGER DEFAULT 0, wins INTEGER DEFAULT 0, wage_bill_annual NUMERIC,
                    UNIQUE(team_id, season)
                );
            """)

            async with conn.transaction():
                for index, row in df.iterrows():
                    raw_team = str(row[squad_col])
                    
                    # O FBref coloca o total da liga na última linha do quadro
                    if raw_team.lower() in ['total', 'average', 'nan']: continue
                    
                    wage_value = self.clean_currency(row[wage_col])
                    if wage_value == 0: continue

                    canonical = await entity_resolver.normalize_name(raw_team, False)
                    team_id = await self.auto_register_team(conn, canonical, sport_key)
                    if not team_id: continue

                    # Faz o UPSERT da folha salarial mantendo pts e wins se existirem
                    await conn.execute("""
                        INSERT INTO fbref_squad.standings_wages (team_id, season, wage_bill_annual)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (team_id, season) DO UPDATE SET wage_bill_annual = EXCLUDED.wage_bill_annual
                    """, team_id, season_str, wage_value)
                    
                    updated_count += 1
                    
        logger.info(f"OK: {updated_count} folhas salariais salvas para {sport_key} ({season_str}).")

    async def run(self):
        logger.info("=== INICIANDO EXTRATOR FINANCEIRO S-TIER (GHOST MONITOR) ===")
        await db.connect()
        await entity_resolver.load_mappings_from_db()
        
        for year in range(self.start_year, self.end_year + 1):
            logger.info(f"\n--- PROCESSANDO TEMPORADA {year} ---")
            for sport_key in self.league_config.keys():
                await self.process_season(sport_key, year)
                
        if self.browser:
            self.browser.stop()
            
        await db.disconnect()
        logger.info("=== HISTORICO FINANCEIRO CONCLUIDO ===")

if __name__ == "__main__":
    updater = FBrefWagesUpdater()
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(updater.run())