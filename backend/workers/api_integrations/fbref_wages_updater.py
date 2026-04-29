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
from curl_cffi import requests

# FIX DEFINITIVO DE UNICODE PARA WINDOWS
if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"
    os.environ["TERM"] = "dumb"
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Adiciona o backend ao path para importações absolutas
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.database import db
from engine.entity_resolution import entity_resolver

# Log ASCII Clean
class SafeASCIIFormatter(logging.Formatter):
    def format(self, record):
        try: return super().format(record)
        except Exception:
            record.msg = str(record.msg).encode('ascii', 'ignore').decode('ascii')
            return super().format(record)

logging.root.handlers = []
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(SafeASCIIFormatter("%(asctime)s [WAGE-EXTRACTOR] %(levelname)s: %(message)s"))
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)
logger = logging.getLogger(__name__)

class FBrefWagesUpdater:
    """
    Motor Financeiro S-Tier.
    Usa curl_cffi (impersonando o Chrome 120+) para burlar o Cloudflare e
    extrair a Folha Salarial Anual das equipes da temporada atual.
    """
    def __init__(self):
        # Mapeamento Direto do FBref (Sport Key -> ID, Nome URL, Cross-Year)
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

    def _fetch_url_sync(self, url: str) -> str:
        """Faz a requisição síncrona nativa com bypass de Cloudflare (curl_cffi)."""
        # Impersonate 'chrome120' resolve >90% dos bloqueios de TLS Fingerprinting atuais
        response = requests.get(url, impersonate="chrome120", timeout=30.0)
        
        if response.status_code == 403:
            raise PermissionError("403 Forbidden: O Cloudflare bloqueou a requisição.")
        if response.status_code == 429:
            raise ConnectionError("429 Too Many Requests: Limite de taxa atingido.")
        if response.status_code == 404:
            return "NO_DATA"
            
        if response.status_code != 200:
             raise ConnectionError(f"Erro HTTP {response.status_code}")
             
        return response.text

    def clean_currency(self, value_str: str) -> float:
        """Remove símbolos ($, €, £, R$), vírgulas e espaços para extrair o valor puro."""
        if pd.isna(value_str): return 0.0
        clean_str = str(value_str).replace(',', '').replace(' ', '')
        numbers = re.findall(r'\d+', clean_str)
        if numbers:
            return float(numbers[0])
        return 0.0

    def _flatten_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty: return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
             df.columns = ['_'.join(str(c).lower() for c in col if c and not str(c).startswith('unnamed')).strip() for col in df.columns]
        else:
             df.columns = [str(col).lower().strip() for col in df.columns]
        return df

    def _extract_dataframe(self, html_content: str) -> pd.DataFrame:
        try:
            html_clean = html_content.replace('', '')
            dfs = pd.read_html(StringIO(html_clean))
            
            for df in dfs:
                df = self._flatten_columns(df)
                if any('squad' in col or 'team' in col for col in df.columns) and any('annual' in col for col in df.columns):
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
        
        logger.info(f"📡 Buscando Folha Salarial: {sport_key} ({season_str})")
        
        try:
            loop = asyncio.get_event_loop()
            html = await loop.run_in_executor(None, self._fetch_url_sync, url)
            
            if html == "NO_DATA":
                logger.info(f" └─ 📭 Sem dados financeiros públicos para {sport_key} {season_str}. Pulando.")
                return
                
            df = self._extract_dataframe(html)
            
            if df is None or df.empty:
                logger.warning(f" └─ ⚠️ Tabela não encontrada no HTML para {sport_key} {season_str}.")
                return
                
            squad_col = next((c for c in df.columns if 'squad' in c or 'team' in c), None)
            wage_col = next((c for c in df.columns if 'annual' in c and 'wages' in c), None)
            if not wage_col:
                wage_col = next((c for c in df.columns if 'annual' in c), None)
            
            if not squad_col or not wage_col:
                logger.warning(" └─ ⚠️ Estrutura da tabela irreconhecível.")
                return

            updated_count = 0
            async with db.pool.acquire() as conn:
                await conn.execute("""
                    CREATE SCHEMA IF NOT EXISTS fbref_squad;
                    CREATE TABLE IF NOT EXISTS fbref_squad.standings_wages (
                        team_id INTEGER, season VARCHAR(10), pts INTEGER DEFAULT 0, wins INTEGER DEFAULT 0, wage_bill_annual NUMERIC,
                        UNIQUE(team_id, season)
                    );
                """)

                async with conn.transaction():
                    logger.info(f"📊 Registrando Folhas Extraídas para {sport_key} ({season_str}):")
                    for index, row in df.iterrows():
                        raw_team = str(row[squad_col])
                        
                        if raw_team.lower() in ['total', 'average', 'nan']: continue
                        
                        wage_value = self.clean_currency(row[wage_col])
                        if wage_value == 0: continue

                        canonical = await entity_resolver.normalize_name(raw_team, False)
                        team_id = await self.auto_register_team(conn, canonical, sport_key)
                        if not team_id: continue

                        # TELEMETRIA S-TIER
                        logger.info(f"   💸 {canonical}: {wage_value:,.2f}")

                        await conn.execute("""
                            INSERT INTO fbref_squad.standings_wages (team_id, season, wage_bill_annual)
                            VALUES ($1, $2, $3)
                            ON CONFLICT (team_id, season) DO UPDATE SET wage_bill_annual = EXCLUDED.wage_bill_annual
                        """, team_id, season_str, wage_value)
                        
                        updated_count += 1
                        
            if updated_count > 0:
                logger.info(f"✅ OK: {updated_count} folhas salariais consolidadas.\n")
            else:
                logger.info(f"ℹ️ Nenhum dado novo a salvar.\n")

        except Exception as e:
            logger.error(f"❌ Erro de extração em {sport_key}: {e}")
            await asyncio.sleep(5)

    async def run(self):
        from datetime import datetime
        
        logger.info("==================================================================")
        logger.info(" 💰 INICIANDO EXTRATOR FINANCEIRO S-TIER (TEMPORADA ATUAL) ")
        logger.info("==================================================================")
        await db.connect()
        await entity_resolver.load_mappings_from_db()
        
        now = datetime.now()
        
        for sport_key, config in self.league_config.items():
            is_cross = config["cross"]
            
            # Lógica inteligente de calendário
            if is_cross and now.month < 8:
                current_year = now.year - 1
            else:
                current_year = now.year
                
            await self.process_season(sport_key, current_year)
            # Respiro defensivo contra bans de IP do FBref
            await asyncio.sleep(random.uniform(3.0, 6.0)) 
                
        await db.disconnect()
        logger.info("=== EXTRAÇÃO FINANCEIRA CONCLUÍDA ===")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(FBrefWagesUpdater().run())