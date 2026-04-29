# betgenius-backend/workers/historical_results_ingester.py
import asyncio
import httpx
import pandas as pd
from io import StringIO
import logging
import sys
from pathlib import Path

# Adiciona o backend ao path para importações
sys.path.append(str(Path(__file__).parent.parent))

from core.database import db
from engine.entity_resolution import entity_resolver

logging.basicConfig(level=logging.INFO, format="%(asctime)s [MATCH-INGESTER] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class HistoricalResultsIngester:
    """
    Motor de Ingestão de Partidas Históricas S-Tier.
    Devora arquivos CSV, lida com Ligas Elite (Temporadas) e Extras (Master CSVs),
    normaliza nomes, imputa médias em dados faltantes e injeta Closing Odds (1x2, O/U, BTTS) e Árbitros no Data Warehouse.
    """
    def __init__(self):
        self.start_year = 25 # 2015
           # 2023
        
        # Mapa Global: Vincula nossas chaves internas aos códigos do football-data.co.uk
        self.league_map = {
            # TIER 1
            "soccer_epl": "E0",
            "soccer_spain_la_liga": "SP1",
            "soccer_italy_serie_a": "I1",
            "soccer_germany_bundesliga": "D1",
            "soccer_uefa_champs_league": None,
            
            # TIER 2
            "soccer_france_ligue_one": "F1",
            "soccer_netherlands_eredivisie": "N1",
            "soccer_portugal_primeira_liga": "P1",
            "soccer_brazil_campeonato": "BRA",
            "soccer_usa_mls": "USA",
            
            # TIER 3
            "soccer_brazil_serie_b": None,
            "soccer_sweden_allsvenskan": "SWE",
            "soccer_norway_eliteserien": "NOR",
            "soccer_denmark_superliga": "DNK",
            "soccer_japan_j_league": "JPN",
            
            # CONTINENTAIS & SELEÇÕES
            "soccer_uefa_europa_league": None,
            "soccer_conmebol_libertadores": None,
            "soccer_conmebol_sudamericana": None,
            "soccer_fifa_world_cup": None,
            "soccer_conmebol_copa_america": None,
            "soccer_uefa_euro_qualifications": None,
            "soccer_uefa_nations_league": None
        }
        
        self.extra_leagues = ["BRA", "USA", "SWE", "NOR", "DNK", "JPN"]

    def _build_url(self, code: str, year: int) -> str:
        """Gera a URL correta baseada no tipo de liga."""
        if code in self.extra_leagues:
            return f"https://www.football-data.co.uk/new/{code}.csv"
        else:
            season_str = f"{year:02d}{year+1:02d}"
            return f"https://www.football-data.co.uk/mmz4281/{season_str}/{code}.csv"

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Peneira as colunas relevantes, padroniza e imputa médias S-Tier."""
        df = df.dropna(subset=['Date', 'HomeTeam', 'AwayTeam'])
        
        # Colunas Alvo (incluindo O/U, BTTS, Referee)
        # Notas do FB-Data: B365>2.5 (Over), B365<2.5 (Under), B365G (BTTS Sim), B365N (BTTS Não)
        target_cols = [
            'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR', 'Referee',
            'HS', 'AS', 'HST', 'AST', 'HF', 'AF', 'HC', 'AC', 'HY', 'AY', 'HR', 'AR',
            'PSCH', 'PSCD', 'PSCA', # Pinnacle Closing 1X2
            'B365H', 'B365D', 'B365A', # Bet365 Backup 1X2
            'PC>2.5', 'PC<2.5', 'P>2.5', 'P<2.5', 'B365>2.5', 'B365<2.5', # Over/Under 2.5 (Pinnacle/Bet365)
            'B365G', 'B365N' # Ambos Marcam (BTTS) Bet365
        ]
        
        available_cols = [col for col in target_cols if col in df.columns]
        df_clean = df[available_cols].copy()
        
        # Padronização de Data
        df_clean['Date'] = pd.to_datetime(df_clean['Date'], dayfirst=True, errors='coerce')
        df_clean = df_clean.dropna(subset=['Date'])
        
        # Motor S-Tier de Imputação por Média (Numeric Columns Only)
        numeric_cols = df_clean.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_cols:
            if df_clean[col].isnull().any():
                # Calcula a média da coluna desconsiderando os NaNs
                col_mean = df_clean[col].mean()
                # Se a média também for NaN (coluna inteira vazia), imputa 0.0
                if pd.isna(col_mean): col_mean = 0.0
                # Preenche os buracos com a média calculada
                df_clean[col] = df_clean[col].fillna(col_mean)
                logger.debug(f"Imputando média {col_mean:.2f} na coluna {col}")

        # Colunas de texto que sobrarem (como Referee) preenchemos com 'Desconhecido'
        df_clean = df_clean.fillna('Desconhecido')
        
        return df_clean

    async def auto_register_team(self, conn, canonical_name: str, sport_key: str) -> int:
        """Busca ou cadastra o time no banco central core.teams."""
        league_id = await conn.fetchval("SELECT id FROM core.leagues WHERE sport_key = $1", sport_key)
        team_id = await conn.fetchval("SELECT id FROM core.teams WHERE canonical_name = $1", canonical_name)
        if not team_id:
            team_id = await conn.fetchval(
                "INSERT INTO core.teams (canonical_name, league_id) VALUES ($1, $2) RETURNING id",
                canonical_name, league_id
            )
            logger.info(f"🆕 NOVO TIME REGISTRADO (Fixtures): '{canonical_name}'")
        return team_id

    async def process_season(self, sport_key: str, code: str, year: int, client: httpx.AsyncClient):
        """Processa o arquivo CSV, lida com transação e salva no Postgres."""
        if not code: return

        if code in self.extra_leagues and year != self.start_year:
            return
            
        url = self._build_url(code, year)
        
        try:
            response = await client.get(url, timeout=20.0)
            if response.status_code != 200:
                logger.warning(f"CSV não encontrado para {sport_key} - URL: {url}")
                return
                
            df = pd.read_csv(StringIO(response.text))
            df = self._clean_dataframe(df)
            if df.empty: return
            
        except Exception as e:
            logger.error(f"Falha ao processar CSV {sport_key}: {e}")
            return

        saved_matches = 0

        async with db.pool.acquire() as conn:
            async with conn.transaction():
                for index, row in df.iterrows():
                    match_date = row['Date'].date()
                    
                    if code in self.extra_leagues:
                        season_label = str(match_date.year)
                        if match_date.year < 2015: continue 
                    else:
                        season_label = f"20{year:02d}-20{year+1:02d}"
                    
                    raw_home = str(row['HomeTeam'])
                    raw_away = str(row['AwayTeam'])
                    referee = str(row.get('Referee', 'Desconhecido'))
                    
                    home_canonical = await entity_resolver.normalize_name(raw_home, is_pinnacle=False)
                    away_canonical = await entity_resolver.normalize_name(raw_away, is_pinnacle=False)
                    
                    home_id = await self.auto_register_team(conn, home_canonical, sport_key)
                    away_id = await self.auto_register_team(conn, away_canonical, sport_key)
                    
                    if not home_id or not away_id: continue

                    def get_val(cols_list, default=0.0):
                        for col in cols_list:
                            if col in df.columns and pd.notna(row[col]) and row[col] != 'Desconhecido':
                                return float(row[col])
                        return default

                    # 1X2 Odds (Prioriza Pinnacle Fechamento, depois Bet365)
                    odd_h = get_val(['PSCH', 'B365H'])
                    odd_d = get_val(['PSCD', 'B365D'])
                    odd_a = get_val(['PSCA', 'B365A'])

                    # O/U 2.5 Odds (Prioriza Pinnacle Closing, Pinnacle Open, Bet365)
                    odd_over25 = get_val(['PC>2.5', 'P>2.5', 'B365>2.5'])
                    odd_under25 = get_val(['PC<2.5', 'P<2.5', 'B365<2.5'])

                    # BTTS Odds
                    odd_btts_yes = get_val(['B365G'])
                    odd_btts_no = get_val(['B365N'])

                    await conn.execute("""
                        INSERT INTO core.matches_history 
                        (sport_key, season, match_date, home_team_id, away_team_id, 
                         home_goals, away_goals, match_result, referee,
                         home_shots_target, away_shots_target, home_corners, away_corners,
                         home_fouls, away_fouls, home_yellow, away_yellow, home_red, away_red,
                         closing_odd_home, closing_odd_draw, closing_odd_away,
                         odd_over_25, odd_under_25, odd_btts_yes, odd_btts_no)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26)
                        ON CONFLICT (match_date, home_team_id, away_team_id) DO UPDATE SET
                            home_goals=EXCLUDED.home_goals, away_goals=EXCLUDED.away_goals, match_result=EXCLUDED.match_result,
                            referee=EXCLUDED.referee, home_shots_target=EXCLUDED.home_shots_target,
                            closing_odd_home=EXCLUDED.closing_odd_home, odd_over_25=EXCLUDED.odd_over_25, 
                            odd_under_25=EXCLUDED.odd_under_25, odd_btts_yes=EXCLUDED.odd_btts_yes
                    """, 
                    sport_key, season_label, match_date, home_id, away_id,
                    int(get_val(['FTHG'])), int(get_val(['FTAG'])), str(row.get('FTR', '')), referee,
                    int(get_val(['HST'])), int(get_val(['AST'])), int(get_val(['HC'])), int(get_val(['AC'])),
                    int(get_val(['HF'])), int(get_val(['AF'])), int(get_val(['HY'])), int(get_val(['AY'])), int(get_val(['HR'])), int(get_val(['AR'])),
                    odd_h, odd_d, odd_a, odd_over25, odd_under25, odd_btts_yes, odd_btts_no)
                    
                    saved_matches += 1

        logger.info(f"✅ {sport_key}: {saved_matches} jogos injetados com Odds e Referee.")

    async def run_ingestion(self):
        logger.info("🚀 INICIANDO INGESTOR DE RESULTADOS HISTÓRICOS (Etapa 1: Data Fusion)")
        await db.connect()
        await entity_resolver.load_mappings_from_db()
        
        async with db.pool.acquire() as conn:
            # Purga a tabela antiga com o esquema corrompido ou legado
            await conn.execute("DROP TABLE IF EXISTS core.matches_history CASCADE;")
            
            # Recria a tabela suportando os novos mercados S-Tier
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS core.matches_history (
                    id SERIAL PRIMARY KEY,
                    sport_key VARCHAR(50),
                    season VARCHAR(20),
                    match_date DATE,
                    home_team_id INTEGER REFERENCES core.teams(id),
                    away_team_id INTEGER REFERENCES core.teams(id),
                    home_goals INTEGER,
                    away_goals INTEGER,
                    match_result VARCHAR(5),
                    referee VARCHAR(100),
                    home_shots_target INTEGER,
                    away_shots_target INTEGER,
                    home_corners INTEGER,
                    away_corners INTEGER,
                    home_fouls INTEGER,
                    away_fouls INTEGER,
                    home_yellow INTEGER,
                    away_yellow INTEGER,
                    home_red INTEGER,
                    away_red INTEGER,
                    closing_odd_home NUMERIC(10,3),
                    closing_odd_draw NUMERIC(10,3),
                    closing_odd_away NUMERIC(10,3),
                    odd_over_25 NUMERIC(10,3) DEFAULT 0.0,
                    odd_under_25 NUMERIC(10,3) DEFAULT 0.0,
                    odd_btts_yes NUMERIC(10,3) DEFAULT 0.0,
                    odd_btts_no NUMERIC(10,3) DEFAULT 0.0,
                    xg_home NUMERIC(10,2) DEFAULT 0.0,
                    xg_away NUMERIC(10,2) DEFAULT 0.0,
                    attendance INTEGER DEFAULT 0,
                    UNIQUE(match_date, home_team_id, away_team_id)
                );
            """)
        
        async with httpx.AsyncClient() as client:
            for year in range(self.start_year, self.end_year + 1):
                logger.info(f"\n================= [ TEMPORADA 20{year:02d}-20{year+1:02d} ] =================")
                for sport_key, code in self.league_map.items():
                    await self.process_season(sport_key, code, year, client)
                    
        await db.disconnect()
        logger.info("🏆 INGESTÃO CONCLUÍDA. Partidas Históricas S-Tier consolidadas no Postgres.")

if __name__ == "__main__":
    ingester = HistoricalResultsIngester()
    asyncio.run(ingester.run_ingestion())