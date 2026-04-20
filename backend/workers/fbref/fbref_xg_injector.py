# betgenius-backend/workers/fbref/fbref_xg_injector.py
import asyncio
import logging
import nodriver as uc
import pandas as pd
from io import StringIO
import random
import sys
from pathlib import Path

# Adiciona o backend ao path para importações
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.database import db
from engine.entity_resolution import entity_resolver
from workers.fbref.config.fbref_map import LEAGUE_CONFIG

logging.basicConfig(level=logging.INFO, format="%(asctime)s [XG-INJECTOR] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class FBrefFixturesInjector:
    """
    Injetor S-Tier (Data Fusion - Etapa 2).
    Abre o Calendário Histórico do FBref, extrai Público, Árbitro e xG (quando existir)
    e faz um UPDATE cirúrgico na nossa tabela core.matches_history, fundindo com as Odds.
    """
    def __init__(self):
        self.start_year = 2015
        self.end_year = 2023
        self.browser = None

    def _build_schedule_url(self, sport_key: str, year: int) -> tuple:
        config = LEAGUE_CONFIG.get(sport_key)
        if not config: return None, None
            
        if config["cross_year"]:
            season_str = f"{year}-{year+1}"
        else:
            season_str = str(year)
            
        # A URL secreta que contém todos os jogos, públicos e árbitros do ano numa tacada só
        url = f"https://fbref.com/en/comps/{config['id']}/{season_str}/schedule/{season_str}-{config['name']}-Scores-and-Fixtures"
        return url, season_str

    async def _init_browser(self):
        if not self.browser:
            logger.info("🛡️ Iniciando Motor Crawler (Modo 'Ghost Monitor')...")
            self.browser = await uc.start(
                headless=False,
                browser_args=[
                    "--window-position=-32000,-32000", # Invisível para o usuário
                    "--window-size=1920,1080",
                    "--disable-notifications",
                    "--no-sandbox"
                ]
            )

    async def fetch_schedule_html(self, url: str) -> str:
        await self._init_browser()
        await asyncio.sleep(4.5) # Respeito ao Rate Limit
        
        for attempt in range(3):
            tab = None
            try:
                tab = await self.browser.get(url, new_tab=True)
                passed = False
                
                for i in range(15):
                    await asyncio.sleep(2.0)
                    html = await tab.get_content()
                    
                    # A tabela de calendário sempre tem a coluna "Referee" e "Attendance"
                    if "Referee" in html and "Attendance" in html:
                        passed = True
                        break
                    elif "Just a moment" in html or "cf-turnstile" in html:
                        if i % 3 == 0:
                            logger.info("🛡️ CF WAF detectado. Injetando biometria sintética...")
                            await tab.evaluate(f"window.scrollBy(0, {random.randint(100, 300)});")
                        continue
                    elif "404 Not Found" in html or "Page Not Found" in html:
                        logger.debug(f"Página 404: {url}")
                        await tab.close()
                        return None
                        
                if passed:
                    final_html = await tab.get_content()
                    await tab.close()
                    return final_html
                else:
                    if tab: await tab.close()
                    
            except Exception as e:
                logger.error(f"Falha em {url}: {e}")
                if tab: await tab.close()
                await asyncio.sleep(5)
                
        return None

    def _extract_dataframe(self, html_content: str) -> pd.DataFrame:
        """Limpa o HTML e puxa a tabela de calendário."""
        try:
            # Pega todas as tabelas, tentamos achar a que tem as colunas chaves
            dfs = pd.read_html(StringIO(html_content))
            for df in dfs:
                if 'Home' in df.columns and 'Away' in df.columns and 'Date' in df.columns:
                    return df
        except Exception:
            pass
        return pd.DataFrame()

    async def process_season(self, sport_key: str, year: int):
        url, season_str = self._build_schedule_url(sport_key, year)
        if not url: return
        
        logger.info(f"🕰️ Alvo: {sport_key} ({season_str}) - Extraindo xG, Público e Árbitros...")
        html = await self.fetch_schedule_html(url)
        
        if not html: return
        
        df = self._extract_dataframe(html)
        if df.empty:
            logger.warning(f"Tabela de calendário não encontrada no HTML para {sport_key} {season_str}")
            return
            
        # Filtra apenas jogos que já aconteceram (Tem data e mandante/visitante preenchidos)
        df = df.dropna(subset=['Date', 'Home', 'Away'])
        
        updated_count = 0

        async with db.pool.acquire() as conn:
            async with conn.transaction():
                for index, row in df.iterrows():
                    try:
                        # Se o jogo não aconteceu, 'Score' está vazio no FBref
                        if 'Score' in df.columns and pd.isna(row['Score']): continue
                        
                        match_date = pd.to_datetime(row['Date']).date()
                        raw_home = str(row['Home'])
                        raw_away = str(row['Away'])
                        
                        # NLP Cruzamento: Isso garante que o 'Arsenal' daqui é o mesmo 'Arsenal' das Odds
                        home_id = await conn.fetchval("SELECT id FROM core.teams WHERE canonical_name = $1", 
                                                      await entity_resolver.normalize_name(raw_home, is_pinnacle=False))
                        away_id = await conn.fetchval("SELECT id FROM core.teams WHERE canonical_name = $1", 
                                                      await entity_resolver.normalize_name(raw_away, is_pinnacle=False))
                                                      
                        if not home_id or not away_id: continue

                        # Extração de Público (Limpando vírgulas)
                        attendance = 0
                        if 'Attendance' in df.columns and not pd.isna(row['Attendance']):
                            att_str = str(row['Attendance']).replace(',', '').replace('.', '')
                            if att_str.isdigit(): attendance = int(att_str)
                            
                        # Extração do Árbitro
                        referee = ""
                        if 'Referee' in df.columns and not pd.isna(row['Referee']):
                            referee = str(row['Referee']).strip()
                            
                        # Extração do xG (Se a coluna existir)
                        xg_home, xg_away = 0.0, 0.0
                        if 'xG' in df.columns:
                            # O FBref às vezes tem duas colunas xG (uma pro Home, outra pro Away)
                            # O Pandas nomeia colunas duplicadas como xG e xG.1
                            xg_cols = [c for c in df.columns if 'xG' in c]
                            if len(xg_cols) >= 2:
                                val_h = row[xg_cols[0]]
                                val_a = row[xg_cols[1]]
                                xg_home = float(val_h) if pd.notna(val_h) else 0.0
                                xg_away = float(val_a) if pd.notna(val_a) else 0.0

                        # A MÁGICA: O UPDATE CIRÚRGICO
                        # Nós achamos o jogo exato pela Data, Mandante e Visitante
                        result = await conn.execute("""
                            UPDATE core.matches_history 
                            SET xg_home = $1, xg_away = $2, attendance = $3, referee = $4
                            WHERE match_date = $5 AND home_team_id = $6 AND away_team_id = $7
                        """, xg_home, xg_away, attendance, referee, match_date, home_id, away_id)
                        
                        # Verifica se alguma linha foi realmente atualizada
                        if result == "UPDATE 1":
                            updated_count += 1
                            
                    except Exception as e:
                        continue
                        
        logger.info(f"✅ {sport_key}: {updated_count} partidas fundidas com sucesso (xG, Árbitro, Público).")

    async def run_injector(self):
        logger.info("🚀 INICIANDO INJETOR DE ESTATÍSTICAS DO FBREF (Data Fusion - Etapa 2)")
        await db.connect()
        await entity_resolver.load_mappings_from_db()
        
        for year in range(self.start_year, self.end_year + 1):
            logger.info(f"\n================= [ INJEÇÃO: TEMPORADA {year} ] =================")
            for sport_key in LEAGUE_CONFIG.keys():
                await self.process_season(sport_key, year)
                
        if self.browser:
            self.browser.stop()
            
        await db.disconnect()
        logger.info("🏆 FUSÃO DE DADOS CONCLUÍDA. O Banco de Dados é agora um oráculo completo.")

if __name__ == "__main__":
    injector = FBrefFixturesInjector()
    # Corrige política de loop no Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(injector.run_injector())