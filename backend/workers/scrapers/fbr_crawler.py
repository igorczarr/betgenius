# betgenius-backend/workers/scrapers/fbr_crawler.py

import sys
import os
import io
import logging

# BLINDAGEM NUCLEAR E DESATIVAÇÃO DE EMOJIS
if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"
    os.environ["TERM"] = "dumb"
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

class ASCIILogFormatter(logging.Formatter):
    def format(self, record):
        try: return super().format(record)
        except Exception:
            record.msg = str(record.msg).encode('ascii', 'ignore').decode('ascii')
            return super().format(record)

# Importações Nativas
import asyncio
import functools
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import warnings
import cloudscraper

warnings.simplefilter(action='ignore', category=FutureWarning)

logging.root.handlers = []
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(ASCIILogFormatter("%(asctime)s [FBR-CRAWLER] %(levelname)s: %(message)s"))
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.database import db
from workers.scrapers.config.scraping_config import ScrapingConfig

class FBrefPureCrawler:
    """
    Crawler Sênior Bypass-Cloudflare.
    Zero dependência de bibliotecas de terceiros como SoccerData.
    Utiliza Cloudscraper para forjar TLS Fingerprint de um Chrome real.
    """
    
    def __init__(self, backfill_mode=True):
        self.target_year = datetime.now().year
        self.backfill_mode = backfill_mode
        self.delay_between_leagues = 6.0 
        
        # Criação do Motor de Bypass
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )

    async def _save_to_quarantine(self, matches_df: pd.DataFrame, league_code: str):
        if matches_df.empty: return

        async with db.pool.acquire() as conn:
            query = """
                INSERT INTO core.staging_fbr_matches 
                (league_url, match_date, raw_home_team, raw_away_team, 
                 home_goals, away_goals, xg_home, xg_away, referee, fusion_status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'PENDING')
                ON CONFLICT (match_date, raw_home_team, raw_away_team) 
                DO UPDATE SET 
                    xg_home = EXCLUDED.xg_home,
                    xg_away = EXCLUDED.xg_away,
                    referee = EXCLUDED.referee,
                    home_goals = EXCLUDED.home_goals,
                    away_goals = EXCLUDED.away_goals,
                    fusion_status = 'PENDING'
            """
            
            records = []
            for _, row in matches_df.iterrows():
                try:
                    h_goals = int(row['home_goals']) if pd.notna(row.get('home_goals')) else None
                    a_goals = int(row['away_goals']) if pd.notna(row.get('away_goals')) else None
                    xg_h = float(row['home_xg']) if 'home_xg' in row and pd.notna(row.get('home_xg')) else 0.0
                    xg_a = float(row['away_xg']) if 'away_xg' in row and pd.notna(row.get('away_xg')) else 0.0
                    ref = str(row['referee']).strip() if 'referee' in row and pd.notna(row.get('referee')) else "Desconhecido"

                    records.append((
                        f"fbref://{league_code}",
                        row['date'].date(),
                        str(row.get('home_team', 'Unknown')).strip(),
                        str(row.get('away_team', 'Unknown')).strip(),
                        h_goals, a_goals, xg_h, xg_a, ref
                    ))
                except Exception:
                    continue 

            if records:
                await conn.executemany(query, records)
                logger.info(f"   └─ SUCESSO: {len(records)} jogos extraídos e guardados na Quarentena.")

    def _parse_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpa as anomalias do FBref (AET, Pênaltis) e foca na matemática."""
        if 'score' not in df.columns: return df
            
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

    def _fetch_url_sync(self, url: str) -> str:
        """Faz a requisição síncrona com bypass de Cloudflare."""
        response = self.scraper.get(url, timeout=30.0)
        if response.status_code == 403:
            raise PermissionError("403 Forbidden: O Cloudflare bloqueou o Cloudscraper. Tente renovar seu IP.")
        if response.status_code == 429:
            raise ConnectionError("429 Too Many Requests: Limite de taxa do FBref atingido.")
        response.raise_for_status()
        return response.text

    async def process_league(self, league_code: str):
        fbr_id = ScrapingConfig.LEAGUE_REGISTRY[league_code]['fbr_id']
        is_calendar = ScrapingConfig.LEAGUE_REGISTRY[league_code]['calendar_year']
        
        if self.backfill_mode:
            ano_base = datetime.now().year
            mes_base = datetime.now().month
            start_y = ano_base - 1 if (not is_calendar and mes_base < 8) else ano_base
            janela_inicio = datetime(year=start_y, month=1 if is_calendar else 7, day=1).date()
        else:
            janela_inicio = (datetime.now() - timedelta(days=15)).date()

        # Construção inteligente de URL
        if is_calendar:
            url_season = str(start_y)
        else:
            url_season = f"{start_y}-{start_y+1}"
            
        url = f"https://fbref.com/en/comps/{fbr_id}/{url_season}/schedule/"
        logger.info(f"📡 Patrulhando: {league_code} -> {url}")
        
        try:
            loop = asyncio.get_event_loop()
            html_content = await loop.run_in_executor(None, self._fetch_url_sync, url)
            
            # Converte o HTML para um ficheiro de memória e entrega ao Pandas
            html_io = io.StringIO(html_content)
            tables = await loop.run_in_executor(None, functools.partial(pd.read_html, html_io))
            
            if not tables:
                logger.warning(f"⚠️ {league_code}: HTML sem tabelas.")
                return
                
            df = tables[0]
            
            # Mapemaneto flexível de Colunas
            rename_map = {'Date': 'date', 'Home': 'home_team', 'Away': 'away_team', 'Score': 'score', 'Referee': 'referee'}
            xg_count = 0
            for col in df.columns:
                col_str = str(col).strip()
                if col_str == 'xG':
                    if xg_count == 0:
                        rename_map[col] = 'home_xg'
                        xg_count += 1
                    else:
                        rename_map[col] = 'away_xg'
            
            df = df.rename(columns=rename_map)
            df.columns = [str(c).lower() for c in df.columns]
            
            if 'date' not in df.columns: return

            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df = df.dropna(subset=['date'])

            if 'home_goals' not in df.columns:
                df = self._parse_scores(df)

            if 'home_goals' not in df.columns: 
                logger.info(f"ℹ️ {league_code}: Sem placares processáveis.")
                return

            finished_matches = df[
                (df['date'].dt.date >= janela_inicio) & 
                (df['date'].dt.date <= datetime.now().date()) &
                (df['home_goals'].notna())
            ].copy()

            if not finished_matches.empty:
                await self._save_to_quarantine(finished_matches, league_code)
            else:
                logger.info(f"ℹ️ {league_code}: Sem novos jogos na janela.")

        except PermissionError as pe:
            logger.error(f"❌ {pe}")
            # Se tomamos 403, dormimos 30 segundos para o WAF esquecer o nosso IP
            await asyncio.sleep(30)
        except ConnectionError as ce:
            logger.error(f"❌ {ce}")
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"❌ Erro de processamento em {league_code}: {str(e)[:100]}")

    async def run(self):
        logger.info("==================================================================")
        mode_str = "BACKFILL HISTÓRICO" if self.backfill_mode else "ATUALIZAÇÃO DIÁRIA"
        logger.info(f" 🥷 INICIANDO FBREF CLOUDSCRAPER ENGINE - MODO: {mode_str} ")
        logger.info("==================================================================")
        
        await db.connect()
        leagues = ScrapingConfig.get_all_active_leagues()
        
        for code in leagues:
            await self.process_league(code)
            # O Segredo da Longevidade: 1 Request a cada 6 segundos. Garantia contra bans.
            await asyncio.sleep(self.delay_between_leagues)

        await db.disconnect()
        logger.info("🏆 EXTRAÇÃO FBREF PURA CONCLUÍDA. Dados aguardando Fusão.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(FBrefPureCrawler(backfill_mode=True).run())