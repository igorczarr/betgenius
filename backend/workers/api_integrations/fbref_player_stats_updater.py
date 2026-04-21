# betgenius-backend/workers/api_integrations/fbref_player_stats_updater.py
import sys
import io
import os
import json
from pathlib import Path

# 1. FIX DEFINITIVO DE UNICODE PARA WINDOWS
if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except AttributeError:
        pass

# 2. INJEÇÃO FÍSICA DE LIGAS (Hack S-Tier no SoccerData)
# Garante que a biblioteca reconheça todas as nossas ligas antes de carregar
sd_config_dir = Path.home() / "soccerdata" / "config"
sd_config_dir.mkdir(parents=True, exist_ok=True)
league_dict_path = sd_config_dir / "league_dict.json"

custom_leagues = {
    "FBref": {
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
}

existing_leagues = {}
if league_dict_path.exists():
    try:
        with open(league_dict_path, "r", encoding="utf-8") as f:
            existing_leagues = json.load(f)
    except:
        pass

if "FBref" not in existing_leagues:
    existing_leagues["FBref"] = {}
existing_leagues["FBref"].update(custom_leagues["FBref"])

with open(league_dict_path, "w", encoding="utf-8") as f:
    json.dump(existing_leagues, f, indent=4)

# AGORA IMPORTAMOS O RESTANTE
import asyncio
import logging
import pandas as pd
from datetime import datetime
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import soccerdata as sd

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.database import db
from engine.entity_resolution import entity_resolver

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [PLAYER-STATS] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class FBrefPlayerStatsUpdater:
    def __init__(self):
        self.sd_leagues = {
            "soccer_epl": "ENG-Premier League",
            "soccer_spain_la_liga": "ESP-La Liga",
            "soccer_italy_serie_a": "ITA-Serie A",
            "soccer_germany_bundesliga": "GER-Bundesliga",
            "soccer_uefa_champs_league": "INT-Champions League",
            "soccer_france_ligue_one": "FRA-Ligue 1",
            "soccer_netherlands_eredivisie": "NED-Eredivisie",
            "soccer_portugal_primeira_liga": "POR-Primeira Liga",
            "soccer_brazil_campeonato": "BRA-Série A",
            "soccer_usa_mls": "USA-Major League Soccer",
            "soccer_brazil_serie_b": "BRA-Série B",
            "soccer_sweden_allsvenskan": "SWE-Allsvenskan",
            "soccer_norway_eliteserien": "NOR-Eliteserien",
            "soccer_denmark_superliga": "DEN-Superliga",
            "soccer_japan_j_league": "JPN-J1 League",
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
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(str(c).lower() for c in col if c and not str(c).startswith('unnamed')).strip() for col in df.columns.values]
        else:
            df.columns = [str(col).lower().strip() for col in df.columns]
        return df

    def _extract_val(self, row, keywords, is_float=True):
        for col in row.index:
            if any(kw in str(col) for kw in keywords):
                val = row[col]
                try:
                    return float(val) if is_float else int(float(val))
                except:
                    pass
        return 0.0 if is_float else 0

    async def process_league(self, sport_key: str, sd_league: str, season_str: str):
        logger.info(f"Processando Data Marts de Jogadores: {sd_league} ({season_str})")
        
        try:
            # Mantemos o cache ATIVADO. Isso evita requisições desnecessárias para ligas que você já baixou
            fbref = sd.FBref(leagues=sd_league, seasons=season_str)
            
            df_std = self._flatten_columns(fbref.read_player_season_stats(stat_type='standard'))
            if df_std.empty:
                logger.warning(f"Nenhum dado retornado para {sd_league}.")
                return

            df_sht = self._flatten_columns(fbref.read_player_season_stats(stat_type='shooting'))
            df_msc = self._flatten_columns(fbref.read_player_season_stats(stat_type='misc'))

            players_dict = {}
            team_cache = {}
            
            team_col = next((c for c in df_std.columns if 'team' in c or 'squad' in c), None)
            player_col = next((c for c in df_std.columns if 'player' in c or 'name' in c), None)
            
            if not team_col or not player_col:
                return

            for idx, row in df_std.iterrows():
                p_name = str(row[player_col]).strip()
                t_name = str(row[team_col]).strip()
                if not p_name or not t_name or p_name == 'nan': continue
                
                key = f"{t_name}_{p_name}"
                mins = self._extract_val(row, ['min', 'minutes'], False)
                if mins == 0: continue 

                players_dict[key] = {
                    'player_name': p_name, 'raw_team': t_name, 'minutes': mins,
                    'goals': self._extract_val(row, ['gls', 'performance_gls'], False),
                    'assists': self._extract_val(row, ['ast', 'performance_ast'], False),
                    'xg_90': self._extract_val(row, ['xg/90', 'expected_xg/90', 'per 90_xg']),
                    'shots_90': 0.0, 'fls': 0, 'fld': 0, 'crdy': 0, 'crdr': 0
                }

            if not df_sht.empty:
                sht_p_col = next((c for c in df_sht.columns if 'player' in c), None)
                sht_t_col = next((c for c in df_sht.columns if 'team' in c or 'squad' in c), None)
                if sht_p_col and sht_t_col:
                    for idx, row in df_sht.iterrows():
                        key = f"{str(row[sht_t_col]).strip()}_{str(row[sht_p_col]).strip()}"
                        if key in players_dict:
                            players_dict[key]['shots_90'] = self._extract_val(row, ['sh/90', 'standard_sh/90'])

            if not df_msc.empty:
                msc_p_col = next((c for c in df_msc.columns if 'player' in c), None)
                msc_t_col = next((c for c in df_msc.columns if 'team' in c or 'squad' in c), None)
                if msc_p_col and msc_t_col:
                    for idx, row in df_msc.iterrows():
                        key = f"{str(row[msc_t_col]).strip()}_{str(row[msc_p_col]).strip()}"
                        if key in players_dict:
                            players_dict[key]['fls'] = self._extract_val(row, ['fls', 'performance_fls'], False)
                            players_dict[key]['fld'] = self._extract_val(row, ['fld', 'performance_fld'], False)
                            players_dict[key]['crdy'] = self._extract_val(row, ['crdy', 'performance_crdy'], False)
                            players_dict[key]['crdr'] = self._extract_val(row, ['crdr', 'performance_crdr'], False)

            async with db.pool.acquire() as conn:
                async with conn.transaction():
                    saved = 0
                    for key, pdata in players_dict.items():
                        raw_team = pdata['raw_team']
                        if raw_team not in team_cache:
                            canonical = await entity_resolver.normalize_name(raw_team, False)
                            t_id = await self.auto_register_team(conn, canonical, sport_key)
                            team_cache[raw_team] = t_id
                            
                        team_id = team_cache.get(raw_team)
                        if not team_id: continue

                        goals, asts = pdata['goals'], pdata['assists']
                        
                        await conn.execute("""
                            INSERT INTO fbref_player.comprehensive_stats 
                            (player_name, team_id, season, minutes_played, goals, assists, goals_plus_assists, 
                             shots_per_90, xg_per_90, fouls_committed, fouls_drawn, yellow_cards, red_cards)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                            ON CONFLICT (player_name, team_id, season) DO UPDATE SET
                                minutes_played=EXCLUDED.minutes_played, goals=EXCLUDED.goals, assists=EXCLUDED.assists,
                                goals_plus_assists=EXCLUDED.goals_plus_assists, shots_per_90=EXCLUDED.shots_per_90,
                                xg_per_90=EXCLUDED.xg_per_90, fouls_committed=EXCLUDED.fouls_committed,
                                fouls_drawn=EXCLUDED.fouls_drawn, yellow_cards=EXCLUDED.yellow_cards, red_cards=EXCLUDED.red_cards,
                                last_updated=CURRENT_TIMESTAMP
                        """, pdata['player_name'], team_id, season_str, pdata['minutes'], goals, asts, (goals + asts),
                             pdata['shots_90'], pdata['xg_90'], pdata['fls'], pdata['fld'], pdata['crdy'], pdata['crdr'])
                        saved += 1
                        
            logger.info(f"✅ SUCESSO: {sd_league} - {saved} jogadores processados.")

        except Exception as e:
            logger.warning(f"⚠️ BLOCKED (Cloudflare): Acesso ao FBref falhou para {sd_league}. O script tentará a próxima liga após um longo descanso.")

    async def run(self):
        logger.info("=== INICIANDO PLAYER PROPS UPDATER ===")
        await db.connect()
        await entity_resolver.load_mappings_from_db()
        
        eur_season = self._get_season_string()
        bra_season = self._get_brazil_season()
        
        for sport_key, sd_league in self.sd_leagues.items():
            is_full_year = any(x in sport_key for x in ['brazil', 'conmebol', 'mls', 'sweden', 'norway', 'japan'])
            season_str = bra_season if is_full_year else eur_season
            
            await self.process_league(sport_key, sd_league, season_str)
            
            # PAUSA PROFUNDA DE 15 SEGUNDOS: Evita que a Cloudflare bana seu IP
            logger.info("Pausa evasiva de segurança (15s)...")
            await asyncio.sleep(15)
            
        await db.disconnect()
        logger.info("=== PROCESSO DE JOGADORES FINALIZADO ===")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(FBrefPlayerStatsUpdater().run())