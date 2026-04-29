# betgenius-backend/workers/historical_backfill.py
import sys
import os
import io

# BLINDAGEM DE ENCODING
if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')
    except AttributeError:
        pass

import asyncio
import logging
import httpx
import pandas as pd
from io import StringIO
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db
from engine.entity_resolution import entity_resolver

# Desliga warnings inofensivos do Pandas sobre datas velhas para limpar nosso terminal
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [HISTORICAL-BACKFILL] %(message)s")
logger = logging.getLogger(__name__)

class HistoricalBackfill:
    """
    Motor S-Tier de Carga Histórica (Deep Extraction).
    Versão Otimizada com Local Caching e Bulk Inserts (Executemany).
    Corta o tempo de execução de 5 horas para alguns minutos.
    """
    def __init__(self):
        self.seasons = ['2526']
        
        self.main_leagues = [
            "E0", "E1", "E2", "E3", "EC", 
            "SC0", "SC1", "SC2", "SC3",   
            "D1", "D2",                   
            "I1", "I2",                   
            "SP1", "SP2",                 
            "F1", "F2",                   
            "N1", "B1", "P1", "T1", "G1"  
        ]
        self.extra_leagues = [
            "ARG", "AUT", "BRA", "CHN", "DNK", "FIN", 
            "IRL", "JPN", "MEX", "NOR", "POL", "ROU", 
            "RUS", "SWE", "SWZ", "USA"
        ]
        
        # O SEGREDO DO HFT: Cache de Memória RAM
        self.league_cache = {}
        self.team_cache = {}

    async def auto_register_team(self, conn, canonical_name: str, sport_key: str) -> int:
        # Se já conhecemos esse time, nem fala com o banco, devolve direto da RAM
        cache_key = f"{sport_key}_{canonical_name}"
        if cache_key in self.team_cache:
            return self.team_cache[cache_key]

        # Liga Cache
        league_id = self.league_cache.get(sport_key)
        if not league_id:
            league_id = await conn.fetchval("SELECT id FROM core.leagues WHERE sport_key = $1", sport_key)
            if not league_id:
                league_id = await conn.fetchval(
                    "INSERT INTO core.leagues (sport_key, name, country, tier) VALUES ($1, $2, $3, $4) RETURNING id",
                    sport_key, f"League {sport_key}", "Global", 1
                )
            self.league_cache[sport_key] = league_id

        # Time Cache
        team_id = await conn.fetchval("SELECT id FROM core.teams WHERE canonical_name = $1", canonical_name)
        if not team_id:
            team_id = await conn.fetchval(
                "INSERT INTO core.teams (canonical_name, league_id) VALUES ($1, $2) RETURNING id",
                canonical_name, league_id
            )
            
        self.team_cache[cache_key] = team_id
        return team_id

    def _clean_fd_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {'Home': 'HomeTeam', 'Away': 'AwayTeam', 'HG': 'FTHG', 'AG': 'FTAG', 'Res': 'FTR'}
        df = df.rename(columns=rename_map)
        
        if 'Date' not in df.columns or 'HomeTeam' not in df.columns or 'AwayTeam' not in df.columns:
            return pd.DataFrame()
            
        df = df.dropna(subset=['Date', 'HomeTeam', 'AwayTeam'])
        
        target_cols = [
            'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR',
            'HTHG', 'HTAG', 'HTR', 
            'HS', 'AS', 'HST', 'AST', 'HF', 'AF', 'HC', 'AC', 'HY', 'AY', 'HR', 'AR', 'Referee',
            'PSH', 'PSD', 'PSA', 'PSCH', 'PSCD', 'PSCA', 'B365H', 'B365D', 'B365A', 
            'P>2.5', 'P<2.5', 'PC>2.5', 'PC<2.5', 'B365>2.5', 'B365<2.5',
            'B365G', 'B365N',
            'AHh', 'PAHH', 'PAHA', 'PCAHH', 'PCAHA', 'B365AHH', 'B365AHA'
        ]
        available_cols = [col for col in target_cols if col in df.columns]
        df_clean = df[available_cols].copy()
        
        df_clean['Date'] = pd.to_datetime(df_clean['Date'], dayfirst=True, errors='coerce')
        df_clean = df_clean.dropna(subset=['Date'])
                
        return df_clean

    async def run_backfill(self):
        logger.info("=========================================================")
        logger.info("⏳ INICIANDO DEEP BACKFILL HFT (Turbo Mode - Memória Cache)")
        logger.info("=========================================================")
        
        await db.connect()
        await entity_resolver.load_mappings_from_db()
        
        async with httpx.AsyncClient(timeout=45.0) as client:
            all_codes = self.main_leagues + self.extra_leagues
            
            for code in all_codes:
                sport_key = f"soccer_code_{code.lower()}"
                
                urls_to_fetch = []
                if code in self.extra_leagues:
                    urls_to_fetch.append((f"https://www.football-data.co.uk/new/{code}.csv", "ALL_TIME"))
                else:
                    for s in self.seasons:
                        urls_to_fetch.append((f"https://www.football-data.co.uk/mmz4281/{s}/{code}.csv", f"20{s[:2]}-20{s[2:]}"))

                for url, season_label in urls_to_fetch:
                    try:
                        logger.info(f"📥 Puxando Arquivo: {code} | {season_label}")
                        response = await client.get(url)
                        if response.status_code != 200: continue
                        
                        df = pd.read_csv(StringIO(response.text), low_memory=False)
                        df = self._clean_fd_dataframe(df)
                        if df.empty: continue
                        
                        cutoff_date = pd.to_datetime('2015-07-01')
                        df = df[df['Date'] >= cutoff_date]
                        
                        records_to_insert = []
                        
                        async with db.pool.acquire() as conn:
                            # 1. Resolvemos todos os IDs iterando a base
                            for _, row in df.iterrows():
                                match_date = row['Date'].date()
                                
                                # FIX S-TIER APLICADO: Apenas 1 argumento passado para o NLP
                                h_name = await entity_resolver.normalize_name(str(row['HomeTeam']))
                                a_name = await entity_resolver.normalize_name(str(row['AwayTeam']))
                                
                                h_id = await self.auto_register_team(conn, h_name, sport_key)
                                a_id = await self.auto_register_team(conn, a_name, sport_key)
                                if not h_id or not a_id: continue

                                def get_val(cols, is_int=False):
                                    for c in cols:
                                        if c in df.columns and pd.notna(row[c]):
                                            val = float(row[c])
                                            return int(val) if is_int else val
                                    return None

                                def get_str(cols):
                                    for c in cols:
                                        if c in df.columns and pd.notna(row[c]):
                                            return str(row[c])
                                    return None

                                # 2. Empacotamos o dado na memória
                                records_to_insert.append((
                                    sport_key, season_label if season_label != "ALL_TIME" else str(match_date.year), match_date, h_id, a_id, 
                                    get_val(['FTHG'], True), get_val(['FTAG'], True), get_str(['FTR']),
                                    get_val(['HTHG'], True), get_val(['HTAG'], True), get_str(['HTR']),
                                    get_val(['HS'], True), get_val(['AS'], True), get_val(['HST'], True), get_val(['AST'], True), 
                                    get_val(['HC'], True), get_val(['AC'], True), get_val(['HF'], True), get_val(['AF'], True), 
                                    get_val(['HY'], True), get_val(['AY'], True), get_val(['HR'], True), get_val(['AR'], True),
                                    get_str(['Referee']),
                                    get_val(['B365H']), get_val(['B365D']), get_val(['B365A']), 
                                    get_val(['PSH']), get_val(['PSD']), get_val(['PSA']),       
                                    get_val(['PSCH']), get_val(['PSCD']), get_val(['PSCA']),    
                                    get_val(['B365>2.5', 'P>2.5', 'PC>2.5']), get_val(['B365<2.5', 'P<2.5', 'PC<2.5']), 
                                    get_val(['B365G']), get_val(['B365N']), 
                                    get_val(['AHh']), get_val(['PAHH', 'B365AHH']), get_val(['PAHA', 'B365AHA']), get_val(['PCAHH']), get_val(['PCAHA'])
                                ))

                            # 3. BULK INSERT (Disparo de Metralhadora SQL)
                            if records_to_insert:
                                query_insert = """
                                    INSERT INTO core.matches_history 
                                    (sport_key, season, match_date, home_team_id, away_team_id, 
                                     home_goals, away_goals, match_result, ht_home_goals, ht_away_goals, ht_result,
                                     home_shots, away_shots, home_shots_target, away_shots_target, 
                                     home_corners, away_corners, home_fouls, away_fouls, 
                                     home_yellow, away_yellow, home_red, away_red, referee,
                                     closing_odd_home, closing_odd_draw, closing_odd_away,
                                     pin_odd_home, pin_odd_draw, pin_odd_away,
                                     pin_closing_home, pin_closing_draw, pin_closing_away, 
                                     odd_over_25, odd_under_25, odd_btts_yes, odd_btts_no, 
                                     ah_line, pin_ah_home, pin_ah_away, pin_closing_ah_home, pin_closing_ah_away, status)
                                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, 
                                            $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, $33, 
                                            $34, $35, $36, $37, $38, $39, $40, $41, $42, 'FINISHED')
                                    ON CONFLICT (match_date, home_team_id, away_team_id) 
                                    DO UPDATE SET 
                                        ht_home_goals = EXCLUDED.ht_home_goals,
                                        ht_away_goals = EXCLUDED.ht_away_goals,
                                        ht_result = EXCLUDED.ht_result,
                                        home_shots = EXCLUDED.home_shots,
                                        away_shots = EXCLUDED.away_shots,
                                        referee = EXCLUDED.referee,
                                        pin_odd_home = EXCLUDED.pin_odd_home,
                                        pin_odd_draw = EXCLUDED.pin_odd_draw,
                                        pin_odd_away = EXCLUDED.pin_odd_away,
                                        pin_closing_home = EXCLUDED.pin_closing_home,
                                        pin_closing_draw = EXCLUDED.pin_closing_draw,
                                        pin_closing_away = EXCLUDED.pin_closing_away,
                                        ah_line = EXCLUDED.ah_line,
                                        pin_ah_home = EXCLUDED.pin_ah_home,
                                        pin_ah_away = EXCLUDED.pin_ah_away,
                                        pin_closing_ah_home = EXCLUDED.pin_closing_ah_home,
                                        pin_closing_ah_away = EXCLUDED.pin_closing_ah_away;
                                """
                                await conn.executemany(query_insert, records_to_insert)
                                logger.info(f"✅ Injetados/Atualizados {len(records_to_insert)} jogos.")

                    except Exception as e:
                        logger.error(f"Erro em {url}: {e}")

        await db.disconnect()
        logger.info("🏆 DEEP BACKFILL CONCLUÍDO. Base de Dados Pronta para o Comitê Especialista.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(HistoricalBackfill().run_backfill())