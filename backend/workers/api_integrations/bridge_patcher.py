# betgenius-backend/workers/api_integrations/bridge_patcher.py

import sys
import os
import io

# =====================================================================
# BLINDAGEM NUCLEAR DE ENCODING (PARA WINDOWS CP1252)
# =====================================================================
if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import warnings
import cloudscraper
from bs4 import BeautifulSoup

warnings.simplefilter(action='ignore', category=FutureWarning)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from core.database import db
from engine.entity_resolution import entity_resolver

from workers.feature_engineering.club_pedigree_engine import GlobalEloEngine
from workers.feature_engineering.proxy_xg_imputer import AdvancedProxyXGImputer

# =====================================================================
# CUSTOM LOGGER PARA IMPEDIR O CRASH COM EMOJIS NO WINDOWS
# =====================================================================
class SafeWindowsFormatter(logging.Formatter):
    def format(self, record):
        try:
            return super().format(record)
        except Exception:
            record.msg = str(record.msg).encode('ascii', 'ignore').decode('ascii')
            return super().format(record)

logging.root.handlers = []
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(SafeWindowsFormatter("%(asctime)s [BRIDGE-PATCHER] %(levelname)s: %(message)s"))
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

class HistoricalBridgePatcher:
    """
    Motor S-Tier para Fechar Buracos Temporais.
    Extrai a temporada atual do FBref através de web scraping puro (Cloudscraper + Pandas),
    ignorando bibliotecas instáveis de terceiros, e faz o Upsert na base principal.
    """
    def __init__(self):
        # Mapeamento do FBREF (Liga -> ID da Liga no FBref)
        self.leagues = {
            "ENG-Premier League": {"sport_key": "soccer_epl", "fbr_id": "9"}, 
            "GER-Bundesliga": {"sport_key": "soccer_germany_bundesliga", "fbr_id": "20"}, 
            "ITA-Serie A": {"sport_key": "soccer_italy_serie_a", "fbr_id": "11"}, 
            "ESP-La Liga": {"sport_key": "soccer_spain_la_liga", "fbr_id": "12"}, 
            "FRA-Ligue 1": {"sport_key": "soccer_france_ligue_one", "fbr_id": "13"}
        }
        
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )

    def _get_current_season_string(self) -> str:
        """Pega a temporada europeia atual no formato FBref (Ex: 2025-2026)"""
        now = datetime.now()
        if now.month < 7:
            return f"{now.year - 1}-{now.year}"
        return f"{now.year}-{now.year + 1}"
        
    def _get_short_season_string(self) -> str:
         now = datetime.now()
         if now.month < 7:
             return f"{str(now.year - 1)[-2:]}{str(now.year)[-2:]}"
         return f"{str(now.year)[-2:]}{str(now.year + 1)[-2:]}"

    def _fetch_url_sync(self, url: str) -> str:
        response = self.scraper.get(url, timeout=30.0)
        if response.status_code == 403:
            raise PermissionError("403 Forbidden: Cloudflare bloqueou o request.")
        if response.status_code == 429:
            raise ConnectionError("429 Too Many Requests: Limite de taxa.")
        response.raise_for_status()
        return response.text

    def _parse_fbref_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """Processa a coluna de placar (Score) bruta do FBref"""
        if 'score' not in df.columns: return df
        
        # Limpa AET e Pênaltis
        df['clean_score'] = df['score'].astype(str).str.replace(r'[a-zA-Z\(\)\s]', '', regex=True)
        df['clean_score'] = df['clean_score'].str.replace('–', '-').str.replace('—', '-')
        split_scores = df['clean_score'].str.split('-', expand=True)
        
        if split_scores.shape[1] >= 2:
            df['home_goals'] = pd.to_numeric(split_scores[0], errors='coerce')
            df['away_goals'] = pd.to_numeric(split_scores[1], errors='coerce')
        else:
            df['home_goals'] = np.nan
            df['away_goals'] = np.nan
        return df

    async def _upsert_match(self, conn, match_data: dict):
        """Insere o jogo no banco usando os dados da Schedule do FBref."""
        h_canon = await entity_resolver.normalize_name(str(match_data.get('home_team', '')))
        a_canon = await entity_resolver.normalize_name(str(match_data.get('away_team', '')))

        if not h_canon or not a_canon: return

        league_id = await conn.fetchval("SELECT id FROM core.leagues WHERE sport_key = $1", match_data['sport_key'])
        if not league_id: return

        h_id = await conn.fetchval("SELECT id FROM core.teams WHERE canonical_name = $1", h_canon)
        if not h_id:
            h_id = await conn.fetchval("INSERT INTO core.teams (canonical_name, league_id) VALUES ($1, $2) RETURNING id", h_canon, league_id)

        a_id = await conn.fetchval("SELECT id FROM core.teams WHERE canonical_name = $1", a_canon)
        if not a_id:
            a_id = await conn.fetchval("INSERT INTO core.teams (canonical_name, league_id) VALUES ($1, $2) RETURNING id", a_canon, league_id)

        # Trata Resultados
        h_g = match_data.get('home_goals')
        a_g = match_data.get('away_goals')
        
        if pd.isna(h_g) or pd.isna(a_g): 
            status = 'SCHEDULED'
            result = None
            h_g, a_g = None, None
        else:
            status = 'FINISHED'
            h_g, a_g = int(h_g), int(a_g)
            if h_g > a_g: result = 'H'
            elif a_g > h_g: result = 'A'
            else: result = 'D'

        await conn.execute("""
            INSERT INTO core.matches_history (
                sport_key, season, match_date, home_team_id, away_team_id, status,
                home_goals, away_goals, match_result, xg_home, xg_away, referee
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
            )
            ON CONFLICT (match_date, home_team_id, away_team_id) DO UPDATE SET
                status = EXCLUDED.status,
                home_goals = COALESCE(core.matches_history.home_goals, EXCLUDED.home_goals),
                away_goals = COALESCE(core.matches_history.away_goals, EXCLUDED.away_goals),
                match_result = COALESCE(core.matches_history.match_result, EXCLUDED.match_result),
                xg_home = COALESCE(core.matches_history.xg_home, EXCLUDED.xg_home),
                xg_away = COALESCE(core.matches_history.xg_away, EXCLUDED.xg_away)
        """, 
            match_data['sport_key'], match_data['season'], match_data['date'], h_id, a_id, status,
            h_g, a_g, result, 
            float(match_data.get('xg', 0)) if pd.notna(match_data.get('xg')) else None,
            float(match_data.get('xg_away', 0)) if pd.notna(match_data.get('xg_away')) else None,
            str(match_data.get('referee', ''))[:100] if pd.notna(match_data.get('referee')) else None
        )

    async def execute_patch(self):
        logger.info("=======================================================================")
        logger.info(" 🛠️ INICIANDO BRIDGE PATCHER: RECUPERANDO A TEMPORADA ATUAL (FBREF)")
        logger.info("=======================================================================")
        
        await db.connect()
        await entity_resolver.load_mappings_from_db()
        season_url_str = self._get_current_season_string()
        season_short_str = self._get_short_season_string()
        
        logger.info(f"📅 Temporada Alvo: {season_url_str}")

        total_inserted = 0
        async with db.pool.acquire() as conn:
            for fbref_name, info in self.leagues.items():
                sport_key = info["sport_key"]
                fbr_id = info["fbr_id"]
                url = f"https://fbref.com/en/comps/{fbr_id}/{season_url_str}/schedule/"
                
                logger.info(f"📡 Baixando Agenda Completa para {fbref_name} ({url})...")
                try:
                    loop = asyncio.get_event_loop()
                    html_content = await loop.run_in_executor(None, self._fetch_url_sync, url)
                    
                    html_io = io.StringIO(html_content)
                    tables = await loop.run_in_executor(None, pd.read_html, html_io)
                    
                    if not tables:
                        logger.warning(f"⚠️ Sem dados estruturados para {fbref_name}.")
                        continue
                        
                    df = tables[0]
                    
                    # Padroniza nomes das colunas
                    df.columns = [str(c).lower().strip() for c in df.columns]
                    rename_map = {'date': 'date', 'home': 'home_team', 'away': 'away_team', 'score': 'score', 'referee': 'referee'}
                    
                    # Localiza as colunas de xG do FBref (A primeira é Home, a segunda é Away)
                    xg_count = 0
                    for col in df.columns:
                        if col == 'xg':
                            if xg_count == 0:
                                rename_map[col] = 'xg' # Home xG
                                xg_count += 1
                            else:
                                rename_map[col] = 'xg_away' # Away xG

                    df = df.rename(columns=rename_map)
                    
                    if 'date' not in df.columns or 'home_team' not in df.columns:
                        logger.warning(f"Formato da tabela incorreto para {fbref_name}")
                        continue
                        
                    df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce').dt.date
                    df = df.dropna(subset=['date_parsed']).sort_values(by='date_parsed')
                    
                    df = self._parse_fbref_score(df)
                    
                    logger.info(f"🔍 {len(df)} partidas lidas. Validando e Injetando no Banco...")
                    
                    async with conn.transaction():
                        for _, row in df.iterrows():
                            # Se não for uma linha de jogo válida, pula
                            if pd.isna(row.get('home_team')) or pd.isna(row.get('away_team')): continue
                            
                            match_data = row.to_dict()
                            match_data['sport_key'] = sport_key
                            match_data['season'] = season_short_str
                            match_data['date'] = match_data['date_parsed']
                            
                            await self._upsert_match(conn, match_data)
                            total_inserted += 1
                            
                    logger.info(f"✅ {fbref_name} processada com sucesso.")
                    await asyncio.sleep(5) # Rate limit protection
                            
                except Exception as e:
                    logger.error(f"❌ Falha ao processar a liga {fbref_name}: {e}")

        logger.info(f"✅ Download Concluído. {total_inserted} partidas analisadas e injetadas.")

        # 2. RECALIBRAÇÃO DA MATRIX
        logger.info("\n⚙️ ACIONANDO RECALIBRAÇÃO (ELO E XG SINTÉTICO)...")
        
        logger.info("-> 1. Reconstruindo a Base de Força (Bayesian Elo)...")
        elo_engine = GlobalEloEngine()
        await elo_engine.run_daily_update()

        logger.info("-> 2. Imputando xG Faltante e Momentum Tático...")
        xg_imputer = AdvancedProxyXGImputer()
        await xg_imputer.run_imputation()

        await db.disconnect()
        logger.info("=======================================================================")
        logger.info(" 🏆 THE BRIDGE IS BUILT! A base de dados agora possui o histórico contínuo.")
        logger.info(" Por favor, execute o 'feature_orchestrator.py' logo a seguir para gerar as EWMAs.")
        logger.info("=======================================================================")

if __name__ == "__main__":
    patcher = HistoricalBridgePatcher()
    asyncio.run(patcher.execute_patch())