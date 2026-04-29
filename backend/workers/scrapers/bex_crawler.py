# betgenius-backend/workers/scrapers/bex_crawler.py

import sys
import os
import io
import logging

# 1. BLINDAGEM NUCLEAR DE ENCODING
if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

class ASCIILogFormatter(logging.Formatter):
    def format(self, record):
        try:
            return super().format(record)
        except Exception:
            record.msg = str(record.msg).encode('ascii', 'ignore').decode('ascii')
            return super().format(record)

logging.root.handlers = []
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(ASCIILogFormatter("%(asctime)s [BEX-CRAWLER] %(levelname)s: %(message)s"))
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

import asyncio
import httpx
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pathlib import Path
import random

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.database import db
from workers.scrapers.config.scraping_config import ScrapingConfig

class BetExplorerCrawler:
    """
    O Extrator Stealth do BetExplorer.
    Armado com Headers Avançados, isolamento de falhas por linha e parser numérico agressivo.
    """
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        self.semaphore = asyncio.Semaphore(2)

    def _parse_ht_score(self, title_text: str):
        if not title_text: return None, None
        match = re.search(r'\((?:\s*)?(\d+)\s*-\s*(\d+)', title_text)
        if match:
            return int(match.group(1)), int(match.group(2))
        return None, None

    async def _fetch_league_results(self, client: httpx.AsyncClient, league_code: str, year: int, janela_inicio: datetime.date):
        base_path = ScrapingConfig.LEAGUE_REGISTRY[league_code]["bex_path"]
        url = f"https://www.betexplorer.com/br/football/{base_path}/results/"
        
        logger.info(f"🔎 Patrulhando: {league_code} -> {url}")
        
        try:
            response = await client.get(url, headers=self.headers, timeout=20.0, follow_redirects=True)
            
            if len(response.url.path) < 15:
                logger.warning(f"⚠️ {league_code} redirecionada para a Home. URL raiz indisponível.")
                return []

            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', class_=re.compile(r'table-main'))
            if not table:
                logger.warning(f"⚠️ {league_code}: Tabela não encontrada (Página vazia ou Cloudflare).")
                return []

            matches_extracted = []
            current_date_str = None
            jogos_ignorados_por_data = 0

            for row in table.find_all('tr'):
                try: # O SEGREDOS: Isolar a falha na linha! Se uma quebrar, as outras sobrevivem.
                    
                    th_date = row.find('th')
                    if th_date and not row.find('a'): 
                        raw_date = th_date.text.strip().lower()
                        if 'hoje' in raw_date or 'today' in raw_date:
                            current_date_str = datetime.now().strftime("%d.%m.%Y")
                        elif 'ontem' in raw_date or 'yesterday' in raw_date:
                            current_date_str = (datetime.now() - timedelta(days=1)).strftime("%d.%m.%Y")
                        else:
                            nums = re.findall(r'\d{1,2}', raw_date)
                            if len(nums) >= 2:
                                d, m = nums[0], nums[1]
                                y_int = year
                                if datetime.now().month == 1 and int(m) == 12:
                                    y_int -= 1
                                current_date_str = f"{int(d):02d}.{int(m):02d}.{y_int}"
                        continue

                    if not current_date_str: continue

                    match_date = datetime.strptime(current_date_str, "%d.%m.%Y").date()

                    if match_date < janela_inicio:
                        jogos_ignorados_por_data += 1
                        continue 

                    # Parser de Times: Mais flexível
                    td_teams = row.find('td', class_=re.compile(r'h-text-left|table-main__tt'))
                    if not td_teams: continue
                    a_teams = td_teams.find('a')
                    if not a_teams: continue
                    
                    teams_str = a_teams.text.strip()
                    if '-' not in teams_str: continue
                    parts = teams_str.split('-', 1)
                    home_team, away_team = parts[0].strip(), parts[1].strip()

                    # Parser de Placar Blindado contra "AET" e "PEN"
                    td_score = row.find('td', class_=re.compile(r'h-text-center'))
                    ft_h, ft_a, ht_h, ht_a = None, None, None, None
                    
                    if td_score and td_score.find('a'):
                        score_a = td_score.find('a')
                        score_str = score_a.text.strip()
                        # Extrai APENAS os dois primeiros blocos de números que encontrar (ex: "2:1 PEN" -> 2 e 1)
                        score_match = re.search(r'(\d+)[^\d]+(\d+)', score_str)
                        if score_match:
                            ft_h = int(score_match.group(1))
                            ft_a = int(score_match.group(2))
                            ht_h, ht_a = self._parse_ht_score(score_a.get('title', ''))

                    # Parser de Odds
                    tds_odds = row.find_all('td', attrs={'data-odd': True})
                    odd_1, odd_x, odd_2 = None, None, None
                    if len(tds_odds) >= 3:
                        try:
                            odd_1 = float(tds_odds[0].get('data-odd'))
                            odd_x = float(tds_odds[1].get('data-odd'))
                            odd_2 = float(tds_odds[2].get('data-odd'))
                        except: pass

                    matches_extracted.append({
                        "league_url": url,
                        "match_date": match_date,
                        "raw_home_team": home_team,
                        "raw_away_team": away_team,
                        "home_goals": ft_h,
                        "away_goals": ft_a,
                        "ht_home_goals": ht_h,
                        "ht_away_goals": ht_a,
                        "odd_1_closing": odd_1,
                        "odd_x_closing": odd_x,
                        "odd_2_closing": odd_2
                    })
                except Exception as row_error:
                    # Se uma linha falhar, ele ignora silenciosamente e vai para o próximo jogo
                    continue

            if matches_extracted:
                logger.debug(f"{league_code}: Capturou {len(matches_extracted)} jogos recentes (Ignorou {jogos_ignorados_por_data} velhos).")
            return matches_extracted

        except Exception as e:
            logger.error(f"Erro em {url}: {str(e)[:100]}")
            return []

    async def _process_league(self, client: httpx.AsyncClient, league_code: str, year: int, janela_inicio: datetime.date):
        async with self.semaphore:
            await asyncio.sleep(random.uniform(1.0, 2.5))
            
            matches = await self._fetch_league_results(client, league_code, year, janela_inicio)
            if not matches: return

            async with db.pool.acquire() as conn:
                query = """
                    INSERT INTO core.staging_bex_matches 
                    (league_url, match_date, raw_home_team, raw_away_team, 
                     home_goals, away_goals, ht_home_goals, ht_away_goals, 
                     odd_1_closing, odd_x_closing, odd_2_closing)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (match_date, raw_home_team, raw_away_team) 
                    DO UPDATE SET 
                        home_goals = EXCLUDED.home_goals,
                        away_goals = EXCLUDED.away_goals,
                        ht_home_goals = EXCLUDED.ht_home_goals,
                        ht_away_goals = EXCLUDED.ht_away_goals,
                        odd_1_closing = EXCLUDED.odd_1_closing,
                        odd_x_closing = EXCLUDED.odd_x_closing,
                        odd_2_closing = EXCLUDED.odd_2_closing,
                        fusion_status = 'PENDING'
                """
                records = [
                    (m['league_url'], m['match_date'], m['raw_home_team'], m['raw_away_team'],
                     m['home_goals'], m['away_goals'], m['ht_home_goals'], m['ht_away_goals'],
                     m['odd_1_closing'], m['odd_x_closing'], m['odd_2_closing'])
                    for m in matches
                ]
                await conn.executemany(query, records)
                logger.info(f"✅ {league_code}: {len(records)} partidas inseridas na Quarentena (BEX).")

    async def run(self):
        logger.info("==================================================================")
        logger.info(" 🚀 INICIANDO BETEXPLORER CRAWLER (STAGE 1: QUARENTENA) ")
        logger.info("==================================================================")
        
        await db.connect()
        
        hoje = datetime.now()
        # Ampliamos a janela para 30 dias temporariamente para garantir que há jogos a capturar
        janela_inicio = (hoje - timedelta(days=30)).date()
        current_year = hoje.year
        
        leagues_to_scrape = ScrapingConfig.get_all_active_leagues()
        
        async with httpx.AsyncClient() as client:
            tasks = [self._process_league(client, code, current_year, janela_inicio) for code in leagues_to_scrape]
            await asyncio.gather(*tasks)

        await db.disconnect()
        logger.info("🏆 EXTRAÇÃO BETEXPLORER CONCLUÍDA. Dados aguardando Fusão.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(BetExplorerCrawler().run())