# betgenius-backend/workers/api_integrations/fbref_team_stats_updater.py
import sys
import os
import io
import asyncio
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime
import warnings

# Força o ambiente Windows a lidar melhor com caracteres especiais
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

warnings.simplefilter(action='ignore', category=FutureWarning)

import soccerdata as sd
import soccerdata._config as sd_config

# ==============================================================================
# MONKEY PATCHING: Injetamos os IDs oficias do FBref na memória
# ==============================================================================
custom_fbref_leagues = {
    "NED-Eredivisie": "23",
    "POR-Primeira Liga": "32",
    "BRA-Série A": "24",
    "USA-Major League Soccer": "22",
    "BRA-Série B": "38",
    "SWE-Allsvenskan": "29",
    "NOR-Eliteserien": "28",
    "DEN-Superliga": "50",
    "JPN-J1 League": "40",
    "INT-Champions League": "8",
    "INT-Europa League": "19",
    "INT-Copa Libertadores": "14",
    "INT-Copa Sudamericana": "54",
    "INT-World Cup": "1",
    "INT-Copa América": "685",
    "INT-European Championship": "676",
    "INT-UEFA Nations League": "683"
}
if "FBref" not in sd_config.LEAGUE_DICT:
    sd_config.LEAGUE_DICT["FBref"] = {}
sd_config.LEAGUE_DICT["FBref"].update(custom_fbref_leagues)

sys.path.append(str(Path(__file__).parent.parent.parent))
from core.database import db
from engine.entity_resolution import entity_resolver

# ==============================================================================
# FILTRO ANTI-CRASH PARA EMOJIS NO WINDOWS CONDA
# ==============================================================================
class SafeASCIIFormatter(logging.Formatter):
    def format(self, record):
        msg = super().format(record)
        # Substitui caracteres que o Windows CP1252 não suporta por um "?" ou ignora
        return msg.encode('ascii', 'ignore').decode('ascii')

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(SafeASCIIFormatter("%(asctime)s [TEAM-STATS] %(levelname)s: %(message)s"))

logger = logging.getLogger() # Pega o root logger para interceptar até os do db.py
logger.setLevel(logging.INFO)
for h in logger.handlers[:]: logger.removeHandler(h)
logger.addHandler(handler)


class FBrefTeamStatsUpdater:
    def __init__(self):
        self.sd_leagues = {
            # TIER 1
            "soccer_epl": "ENG-Premier League",
            "soccer_spain_la_liga": "ESP-La Liga",
            "soccer_italy_serie_a": "ITA-Serie A",
            "soccer_germany_bundesliga": "GER-Bundesliga",
            "soccer_uefa_champs_league": "INT-Champions League",
            
            # TIER 2
            "soccer_france_ligue_one": "FRA-Ligue 1",
            "soccer_netherlands_eredivisie": "NED-Eredivisie",
            "soccer_portugal_primeira_liga": "POR-Primeira Liga",
            "soccer_brazil_campeonato": "BRA-Série A",
            "soccer_usa_mls": "USA-Major League Soccer",
            
            # TIER 3
            "soccer_brazil_serie_b": "BRA-Série B",
            "soccer_sweden_allsvenskan": "SWE-Allsvenskan",
            "soccer_norway_eliteserien": "NOR-Eliteserien",
            "soccer_denmark_superliga": "DEN-Superliga",
            "soccer_japan_j_league": "JPN-J1 League",
            
            # CONTINENTAIS & SELEÇÕES
            "soccer_uefa_europa_league": "INT-Europa League",
            "soccer_conmebol_libertadores": "INT-Copa Libertadores",
            "soccer_conmebol_sudamericana": "INT-Copa Sudamericana",
            "soccer_fifa_world_cup": "INT-World Cup",
            "soccer_conmebol_copa_america": "INT-Copa América",
            "soccer_uefa_euro_qualifications": "INT-European Championship",
            "soccer_uefa_nations_league": "INT-UEFA Nations League"
        }

    def _get_season_string(self) -> str:
        now = datetime.now()
        if now.month < 7:
            return f"{str(now.year - 1)[-2:]}{str(now.year)[-2:]}"
        return f"{str(now.year)[-2:]}{str(now.year + 1)[-2:]}"

    def _get_brazil_season(self) -> str:
        return str(datetime.now().year)

    async def auto_register_team(self, conn, canonical_name: str, sport_key: str) -> int:
        league_id = await conn.fetchval("SELECT id FROM core.leagues WHERE sport_key = $1", sport_key)
        team_id = await conn.fetchval("SELECT id FROM core.teams WHERE canonical_name = $1", canonical_name)
        if not team_id:
            team_id = await conn.fetchval(
                "INSERT INTO core.teams (canonical_name, league_id) VALUES ($1, $2) RETURNING id",
                canonical_name, league_id
            )
        return team_id

    def _flatten_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(str(c).lower() for c in col if c and not str(c).startswith('unnamed')).strip() for col in df.columns.values]
        else:
            df.columns = [str(col).lower().strip() for col in df.columns]
        return df

    def _extract_from_dfs(self, dfs: list, team_name: str, keywords: list, is_float=True):
        for df in dfs:
            if df.empty: continue
            team_col = next((c for c in df.columns if 'team' in c or 'squad' in c), None)
            if not team_col: continue
            
            row = df[df[team_col].astype(str).str.contains(team_name, case=False, na=False)]
            if row.empty: continue
            
            for col in df.columns:
                if any(kw in col for kw in keywords):
                    val = row.iloc[0][col]
                    try:
                        return float(val) if is_float else int(float(val))
                    except:
                        pass
        return 0.0 if is_float else 0

    async def process_league(self, sport_key: str, sd_league: str, season_str: str):
        logger.info(f"Iniciando: {sd_league} ({season_str})")
        
        try:
            # REMOVIDO: no_cache=True. Agora usamos cache local para poupar requests.
            fbref = sd.FBref(leagues=sd_league, seasons=season_str)
            
            df_std = self._flatten_columns(fbref.read_team_season_stats(stat_type='standard').reset_index())
            df_sht = self._flatten_columns(fbref.read_team_season_stats(stat_type='shooting').reset_index())
            df_msc = self._flatten_columns(fbref.read_team_season_stats(stat_type='misc').reset_index())
            
            dfs = [df_std, df_sht, df_msc]
            
            if df_std.empty:
                logger.warning(f"Tabela vazia para {sd_league}.")
                return

            async with db.pool.acquire() as conn:
                async with conn.transaction():
                    team_col = next((c for c in df_std.columns if 'team' in c or 'squad' in c), None)
                    if not team_col: return
                    
                    saved = 0
                    for raw_team in df_std[team_col].unique():
                        if pd.isna(raw_team): continue
                        
                        canonical = await entity_resolver.normalize_name(str(raw_team), False)
                        team_id = await self.auto_register_team(conn, canonical, sport_key)
                        if not team_id: continue

                        goals = self._extract_from_dfs(dfs, raw_team, ['gls', 'performance_gls'], False)
                        xg_for = self._extract_from_dfs(dfs, raw_team, ['xg', 'expected_xg'])
                        npxg_for = self._extract_from_dfs(dfs, raw_team, ['npxg', 'expected_npxg'])
                        assists = self._extract_from_dfs(dfs, raw_team, ['ast', 'performance_ast'], False)
                        sh_tot = self._extract_from_dfs(dfs, raw_team, ['sh', 'standard_sh'], False)
                        sh_tar = self._extract_from_dfs(dfs, raw_team, ['sot', 'standard_sot'], False)

                        await conn.execute("""
                            INSERT INTO fbref_squad.offensive (team_id, season, split_type, goals_scored, xg_for, npxg_for, shots_total, shots_on_target, assists)
                            VALUES ($1, $2, 'ALL', $3, $4, $5, $6, $7, $8)
                            ON CONFLICT (team_id, season, split_type) DO UPDATE SET
                                goals_scored=EXCLUDED.goals_scored, xg_for=EXCLUDED.xg_for, npxg_for=EXCLUDED.npxg_for,
                                shots_total=EXCLUDED.shots_total, shots_on_target=EXCLUDED.shots_on_target, assists=EXCLUDED.assists
                        """, team_id, season_str, goals, xg_for, npxg_for, sh_tot, sh_tar, assists)

                        goals_conc = self._extract_from_dfs(dfs, raw_team, ['gls_against', 'performance_gls_against'], False)
                        xga = self._extract_from_dfs(dfs, raw_team, ['xga', 'expected_xga'])
                        tklw = self._extract_from_dfs(dfs, raw_team, ['tklw', 'tackles_tklw'], False)
                        intc = self._extract_from_dfs(dfs, raw_team, ['int', 'interceptions'], False)

                        await conn.execute("""
                            INSERT INTO fbref_squad.defensive (team_id, season, split_type, goals_conceded, xg_against, tackles_won, interceptions)
                            VALUES ($1, $2, 'ALL', $3, $4, $5, $6)
                            ON CONFLICT (team_id, season, split_type) DO UPDATE SET
                                goals_conceded=EXCLUDED.goals_conceded, xg_against=EXCLUDED.xg_against,
                                tackles_won=EXCLUDED.tackles_won, interceptions=EXCLUDED.interceptions
                        """, team_id, season_str, goals_conc, xga, tklw, intc)

                        poss = self._extract_from_dfs(dfs, raw_team, ['poss', 'possession'])
                        fls = self._extract_from_dfs(dfs, raw_team, ['fls', 'performance_fls'], False)
                        fld = self._extract_from_dfs(dfs, raw_team, ['fld', 'performance_fld'], False)
                        crdY = self._extract_from_dfs(dfs, raw_team, ['crdy', 'performance_crdy'], False)
                        crdR = self._extract_from_dfs(dfs, raw_team, ['crdr', 'performance_crdr'], False)

                        await conn.execute("""
                            INSERT INTO fbref_squad.advanced (team_id, season, split_type, possession_pct)
                            VALUES ($1, $2, 'ALL', $3)
                            ON CONFLICT (team_id, season, split_type) DO UPDATE SET possession_pct=EXCLUDED.possession_pct
                        """, team_id, season_str, poss)

                        await conn.execute("""
                            INSERT INTO fbref_squad.misc (team_id, season, split_type, fouls_committed, fouls_drawn, yellow_cards, red_cards)
                            VALUES ($1, $2, 'ALL', $3, $4, $5, $6)
                            ON CONFLICT (team_id, season, split_type) DO UPDATE SET
                                fouls_committed=EXCLUDED.fouls_committed, fouls_drawn=EXCLUDED.fouls_drawn,
                                yellow_cards=EXCLUDED.yellow_cards, red_cards=EXCLUDED.red_cards
                        """, team_id, season_str, fls, fld, crdY, crdR)
                        
                        saved += 1
                        
            logger.info(f"OK: {sd_league} ({saved} equipes salvas).")

        except Exception as e:
            logger.warning(f"BLOCKED: Acesso ao {sd_league} falhou (Cloudflare/Timeout). O script prosseguira para a proxima liga.")

    async def run(self):
        logger.info("=== INICIANDO SQUADS UPDATER ===")
        await db.connect()
        await entity_resolver.load_mappings_from_db()
        
        eur_season = self._get_season_string()
        bra_season = self._get_brazil_season()
        
        for sport_key, sd_league in self.sd_leagues.items():
            is_full_year = any(x in sport_key for x in ['brazil', 'conmebol', 'mls', 'sweden', 'norway', 'japan'])
            season_str = bra_season if is_full_year else eur_season
            
            await self.process_league(sport_key, sd_league, season_str)
            await asyncio.sleep(5)
            
        await db.disconnect()
        logger.info("=== PROCESSO FINALIZADO ===")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(FBrefTeamStatsUpdater().run())