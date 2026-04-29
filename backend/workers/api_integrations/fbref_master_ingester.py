# betgenius-backend/workers/api_integrations/fbref_master_ingester.py

import sys
import os
import io
import asyncio
import logging
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import warnings

# ==============================================================================
# 1. BLINDAGEM NUCLEAR E DESATIVAÇÃO DE EMOJIS (WINDOWS SAFE)
# ==============================================================================
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

class SafeWindowsFormatter(logging.Formatter):
    def format(self, record):
        try:
            return super().format(record)
        except Exception:
            record.msg = str(record.msg).encode('ascii', 'ignore').decode('ascii')
            return super().format(record)

# ==============================================================================
# 2. INJEÇÃO FÍSICA DE LIGAS (Hack S-Tier no SoccerData)
# ==============================================================================
sd_config_dir = Path.home() / "soccerdata" / "config"
sd_config_dir.mkdir(parents=True, exist_ok=True)
league_dict_path = sd_config_dir / "league_dict.json"

custom_leagues = {
    "FBref": {
        "NED-Eredivisie": "23", "POR-Primeira Liga": "32", "BRA-Série A": "24",
        "USA-Major League Soccer": "22", "BRA-Série B": "38", "SWE-Allsvenskan": "29",
        "NOR-Eliteserien": "28", "DEN-Superliga": "50", "JPN-J1 League": "40"
    }
}

existing_leagues = {}
if league_dict_path.exists():
    try:
        with open(league_dict_path, "r", encoding="utf-8") as f:
            existing_leagues = json.load(f)
    except: pass

if "FBref" not in existing_leagues:
    existing_leagues["FBref"] = {}
existing_leagues["FBref"].update(custom_leagues["FBref"])

with open(league_dict_path, "w", encoding="utf-8") as f:
    json.dump(existing_leagues, f, indent=4)

# ==============================================================================
# 3. IMPORTAÇÕES DA APLICAÇÃO
# ==============================================================================
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)
import soccerdata as sd

logging.root.handlers = []
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(SafeWindowsFormatter("%(asctime)s [MASTER-INGESTER] %(levelname)s: %(message)s"))
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)
logger = logging.getLogger(__name__)

logging.getLogger("soccerdata").setLevel(logging.CRITICAL)

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.database import db
from engine.entity_resolution import entity_resolver

# ==============================================================================
# 4. MOTOR MESTRE DE INGESTÃO (SQUADS + PLAYERS)
# ==============================================================================
class FBrefMasterIngester:
    """
    O Colheitador Supremo (Focado no MVP Top 5 Ligas).
    Consolida as extrações estáticas acumuladas para popular as abas de Tática
    e Desempenho no Front-End.
    """
    def __init__(self):
        # FOCO NO MVP INSTITUCIONAL: Apenas Ligas de Elite da Europa
        self.sd_leagues = {
            "soccer_epl": "ENG-Premier League", 
            "soccer_spain_la_liga": "ESP-La Liga",
            "soccer_italy_serie_a": "ITA-Serie A", 
            "soccer_germany_bundesliga": "GER-Bundesliga",
            "soccer_france_ligue_one": "FRA-Ligue 1"
        }

    def _get_season_string(self) -> str:
        now = datetime.now()
        # Ano cruzado europeu
        return f"{str(now.year - 1)[-2:]}{str(now.year)[-2:]}" if now.month < 7 else f"{str(now.year)[-2:]}{str(now.year + 1)[-2:]}"

    async def auto_register_team(self, conn, canonical_name: str, sport_key: str) -> int:
        league_id = await conn.fetchval("SELECT id FROM core.leagues WHERE sport_key = $1", sport_key)
        if not league_id:
             league_id = await conn.fetchval("INSERT INTO core.leagues (sport_key, name, tier) VALUES ($1, $2, 1) RETURNING id", sport_key, sport_key)
        
        team_id = await conn.fetchval("SELECT id FROM core.teams WHERE canonical_name = $1", canonical_name)
        if not team_id:
            team_id = await conn.fetchval(
                "INSERT INTO core.teams (canonical_name, league_id) VALUES ($1, $2) RETURNING id",
                canonical_name, league_id
            )
        return team_id

    async def _ensure_schemas(self, conn):
        logger.info("🛠️ Validando Schemas de Equipes e Jogadores...")
        await conn.execute("CREATE SCHEMA IF NOT EXISTS fbref_squad;")
        await conn.execute("CREATE SCHEMA IF NOT EXISTS fbref_player;")
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS fbref_squad.standings_wages (team_id INTEGER, season VARCHAR(10), pts INTEGER, wins INTEGER, wage_bill_annual NUMERIC, UNIQUE(team_id, season));
            CREATE TABLE IF NOT EXISTS fbref_squad.advanced_general (team_id INTEGER, season VARCHAR(10), possession_pct NUMERIC, xg_for NUMERIC, xga_against NUMERIC, UNIQUE(team_id, season));
            CREATE TABLE IF NOT EXISTS fbref_squad.offensive (team_id INTEGER, season VARCHAR(10), split_type VARCHAR(10), goals_scored NUMERIC, xg_for NUMERIC, npxg_for NUMERIC, shots_total NUMERIC, shots_on_target NUMERIC, assists NUMERIC, UNIQUE(team_id, season, split_type));
            CREATE TABLE IF NOT EXISTS fbref_squad.defensive (team_id INTEGER, season VARCHAR(10), split_type VARCHAR(10), goals_conceded NUMERIC, xg_against NUMERIC, tackles_won NUMERIC, interceptions NUMERIC, UNIQUE(team_id, season, split_type));
            CREATE TABLE IF NOT EXISTS fbref_squad.advanced (team_id INTEGER, season VARCHAR(10), split_type VARCHAR(10), possession_pct NUMERIC, UNIQUE(team_id, season, split_type));
            CREATE TABLE IF NOT EXISTS fbref_squad.misc (team_id INTEGER, season VARCHAR(10), split_type VARCHAR(10), fouls_committed NUMERIC, fouls_drawn NUMERIC, yellow_cards NUMERIC, red_cards NUMERIC, UNIQUE(team_id, season, split_type));
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS fbref_player.comprehensive_stats (
                player_name VARCHAR(100), team_id INTEGER, season VARCHAR(10), minutes_played NUMERIC, goals NUMERIC, assists NUMERIC, goals_plus_assists NUMERIC, 
                shots_per_90 NUMERIC, xg_per_90 NUMERIC, fouls_committed NUMERIC, fouls_drawn NUMERIC, yellow_cards NUMERIC, red_cards NUMERIC, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(player_name, team_id, season)
            );
        """)
        
        metrics = ["goals", "assists", "goals_assists", "xg_90", "shots_90", "fouls_committed", "fouls_drawn", "yellow_cards"]
        for metric in metrics:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS fbref_player.metric_{metric} (
                    player_name VARCHAR(100), team_id INTEGER, season VARCHAR(10), quantity NUMERIC, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(player_name, team_id, season)
                );
            """)

    def _flatten_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty: return pd.DataFrame()
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(str(c).lower() for c in col if c and not str(c).startswith('unnamed')).strip() for col in df.columns.values]
        else:
            df.columns = [str(col).lower().strip() for col in df.columns]
        return df

    def _safe_extract(self, df, idx, keywords, is_float=True):
        for col in df.columns:
            if any(kw in str(col).lower() for kw in keywords):
                try: return float(df.at[idx, col]) if is_float else int(float(df.at[idx, col]))
                except: pass
        return 0.0 if is_float else 0

    def _extract_from_dfs(self, dfs: list, team_name: str, keywords: list, is_float=True):
        for df in dfs:
            if df.empty: continue
            team_col = next((c for c in df.columns if 'team' in c or 'squad' in c), None)
            if not team_col: continue
            
            row = df[df[team_col].astype(str).str.contains(team_name, case=False, na=False)]
            if row.empty: continue
            
            for col in df.columns:
                if any(kw in col for kw in keywords):
                    try: return float(row.iloc[0][col]) if is_float else int(float(row.iloc[0][col]))
                    except: pass
        return 0.0 if is_float else 0

    async def process_league(self, sport_key: str, sd_league: str, season_str: str):
        logger.info(f"📡 Master Download: {sd_league} ({season_str})")
        
        try:
            fbref = sd.FBref(leagues=sd_league, seasons=season_str)
            
            # --- 1. CARGA MASSIVA PARA MEMÓRIA RAM ---
            df_team_std = self._flatten_columns(fbref.read_team_season_stats(stat_type='standard'))
            df_team_sht = self._flatten_columns(fbref.read_team_season_stats(stat_type='shooting'))
            df_team_msc = self._flatten_columns(fbref.read_team_season_stats(stat_type='misc'))
            team_dfs = [df_team_std, df_team_sht, df_team_msc]
            
            df_play_std = self._flatten_columns(fbref.read_player_season_stats(stat_type='standard'))
            df_play_sht = self._flatten_columns(fbref.read_player_season_stats(stat_type='shooting'))
            df_play_msc = self._flatten_columns(fbref.read_player_season_stats(stat_type='misc'))

            if df_team_std.empty and df_play_std.empty:
                logger.warning(f"⚠️ {sd_league}: Nenhum dado retornado da API.")
                return

            # --- 2. PROCESSAMENTO E INSERÇÃO NO BANCO ---
            async with db.pool.acquire() as conn:
                async with conn.transaction():
                    await self._ensure_schemas(conn)
                    team_cache = {}
                    
                    # -----------------------------------------------------
                    # A) PROCESSAMENTO DE EQUIPES (SQUADS)
                    # -----------------------------------------------------
                    saved_teams = 0
                    team_col = next((c for c in df_team_std.columns if 'team' in c or 'squad' in c), None)
                    if team_col and not df_team_std.empty:
                        for raw_team in df_team_std[team_col].unique():
                            if pd.isna(raw_team): continue
                            
                            # CORREÇÃO CIRÚRGICA: Chamamos a NLP apenas com 1 argumento
                            canonical = await entity_resolver.normalize_name(str(raw_team))
                            
                            team_id = await self.auto_register_team(conn, canonical, sport_key)
                            if not team_id: continue
                            
                            team_cache[str(raw_team).lower()] = team_id

                            pts = self._extract_from_dfs(team_dfs, raw_team, ['pts', 'points'], False)
                            wins = self._extract_from_dfs(team_dfs, raw_team, ['w', 'wins'], False)
                            poss = self._extract_from_dfs(team_dfs, raw_team, ['poss', 'possession'])
                            xg_for = self._extract_from_dfs(team_dfs, raw_team, ['xg', 'expected_xg'])
                            xga = self._extract_from_dfs(team_dfs, raw_team, ['xga', 'expected_xga'])
                            goals = self._extract_from_dfs(team_dfs, raw_team, ['gls', 'performance_gls'], False)
                            npxg = self._extract_from_dfs(team_dfs, raw_team, ['npxg', 'expected_npxg'])
                            asts = self._extract_from_dfs(team_dfs, raw_team, ['ast', 'performance_ast'], False)
                            sh_tot = self._extract_from_dfs(team_dfs, raw_team, ['sh', 'standard_sh'], False)
                            sh_tar = self._extract_from_dfs(team_dfs, raw_team, ['sot', 'standard_sot'], False)
                            goals_c = self._extract_from_dfs(team_dfs, raw_team, ['gls_against', 'performance_gls_against'], False)
                            tklw = self._extract_from_dfs(team_dfs, raw_team, ['tklw', 'tackles_tklw'], False)
                            intc = self._extract_from_dfs(team_dfs, raw_team, ['int', 'interceptions'], False)
                            fls = self._extract_from_dfs(team_dfs, raw_team, ['fls', 'performance_fls'], False)
                            fld = self._extract_from_dfs(team_dfs, raw_team, ['fld', 'performance_fld'], False)
                            crdY = self._extract_from_dfs(team_dfs, raw_team, ['crdy', 'performance_crdy'], False)
                            crdR = self._extract_from_dfs(team_dfs, raw_team, ['crdr', 'performance_crdr'], False)

                            await conn.execute("INSERT INTO fbref_squad.standings_wages (team_id, season, pts, wins) VALUES ($1, $2, $3, $4) ON CONFLICT (team_id, season) DO UPDATE SET pts=EXCLUDED.pts, wins=EXCLUDED.wins", team_id, season_str, pts, wins)
                            await conn.execute("INSERT INTO fbref_squad.advanced_general (team_id, season, possession_pct, xg_for, xga_against) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (team_id, season) DO UPDATE SET possession_pct=EXCLUDED.possession_pct, xg_for=EXCLUDED.xg_for, xga_against=EXCLUDED.xga_against", team_id, season_str, poss, xg_for, xga)
                            await conn.execute("INSERT INTO fbref_squad.offensive (team_id, season, split_type, goals_scored, xg_for, npxg_for, shots_total, shots_on_target, assists) VALUES ($1, $2, 'ALL', $3, $4, $5, $6, $7, $8) ON CONFLICT (team_id, season, split_type) DO UPDATE SET goals_scored=EXCLUDED.goals_scored, xg_for=EXCLUDED.xg_for, npxg_for=EXCLUDED.npxg_for, shots_total=EXCLUDED.shots_total, shots_on_target=EXCLUDED.shots_on_target, assists=EXCLUDED.assists", team_id, season_str, goals, xg_for, npxg, sh_tot, sh_tar, asts)
                            await conn.execute("INSERT INTO fbref_squad.defensive (team_id, season, split_type, goals_conceded, xg_against, tackles_won, interceptions) VALUES ($1, $2, 'ALL', $3, $4, $5, $6) ON CONFLICT (team_id, season, split_type) DO UPDATE SET goals_conceded=EXCLUDED.goals_conceded, xg_against=EXCLUDED.xg_against, tackles_won=EXCLUDED.tackles_won, interceptions=EXCLUDED.interceptions", team_id, season_str, goals_c, xga, tklw, intc)
                            await conn.execute("INSERT INTO fbref_squad.advanced (team_id, season, split_type, possession_pct) VALUES ($1, $2, 'ALL', $3) ON CONFLICT (team_id, season, split_type) DO UPDATE SET possession_pct=EXCLUDED.possession_pct", team_id, season_str, poss)
                            await conn.execute("INSERT INTO fbref_squad.misc (team_id, season, split_type, fouls_committed, fouls_drawn, yellow_cards, red_cards) VALUES ($1, $2, 'ALL', $3, $4, $5, $6) ON CONFLICT (team_id, season, split_type) DO UPDATE SET fouls_committed=EXCLUDED.fouls_committed, fouls_drawn=EXCLUDED.fouls_drawn, yellow_cards=EXCLUDED.yellow_cards, red_cards=EXCLUDED.red_cards", team_id, season_str, fls, fld, crdY, crdR)
                            
                            saved_teams += 1

                    # -----------------------------------------------------
                    # B) PROCESSAMENTO DE JOGADORES (PLAYERS)
                    # -----------------------------------------------------
                    saved_players = 0
                    if not df_play_std.empty:
                        for idx, row in df_play_std.iterrows():
                            p_name = str(self._safe_extract(df_play_std, idx, ['player', 'name'], False)).strip()
                            raw_team = str(self._safe_extract(df_play_std, idx, ['team', 'squad'], False)).strip()
                            
                            if not p_name or not raw_team or p_name == 'nan': continue
                            
                            team_id = next((t_id for t_name, t_id in team_cache.items() if t_name in raw_team.lower()), None)
                            if not team_id: continue

                            mins = self._safe_extract(df_play_std, idx, ['min', 'minutes'], False)
                            if mins == 0: continue 

                            goals = int(self._safe_extract(df_play_std, idx, ['gls', 'performance_gls'], False))
                            asts = int(self._safe_extract(df_play_std, idx, ['ast', 'performance_ast'], False))
                            xg90 = self._safe_extract(df_play_std, idx, ['xg', 'per 90_xg'])
                            
                            sh90, p_fls, p_fld, p_crdy, p_crdr = 0.0, 0, 0, 0, 0
                            
                            if not df_play_sht.empty:
                                sht_row = df_play_sht[df_play_sht.astype(str).apply(lambda x: p_name in x.values, axis=1)]
                                if not sht_row.empty: sh90 = self._safe_extract(df_play_sht, sht_row.index[0], ['sh/90', 'standard_sh/90'])
                                
                            if not df_play_msc.empty:
                                msc_row = df_play_msc[df_play_msc.astype(str).apply(lambda x: p_name in x.values, axis=1)]
                                if not msc_row.empty:
                                    m_idx = msc_row.index[0]
                                    p_fls = int(self._safe_extract(df_play_msc, m_idx, ['fls', 'performance_fls'], False))
                                    p_fld = int(self._safe_extract(df_play_msc, m_idx, ['fld', 'performance_fld'], False))
                                    p_crdy = int(self._safe_extract(df_play_msc, m_idx, ['crdy', 'performance_crdy'], False))
                                    p_crdr = int(self._safe_extract(df_play_msc, m_idx, ['crdr', 'performance_crdr'], False))

                            await conn.execute("""
                                INSERT INTO fbref_player.comprehensive_stats 
                                (player_name, team_id, season, minutes_played, goals, assists, goals_plus_assists, shots_per_90, xg_per_90, fouls_committed, fouls_drawn, yellow_cards, red_cards)
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                                ON CONFLICT (player_name, team_id, season) DO UPDATE SET
                                    minutes_played=EXCLUDED.minutes_played, goals=EXCLUDED.goals, assists=EXCLUDED.assists, goals_plus_assists=EXCLUDED.goals_plus_assists, shots_per_90=EXCLUDED.shots_per_90,
                                    xg_per_90=EXCLUDED.xg_per_90, fouls_committed=EXCLUDED.fouls_committed, fouls_drawn=EXCLUDED.fouls_drawn, yellow_cards=EXCLUDED.yellow_cards, red_cards=EXCLUDED.red_cards, last_updated=CURRENT_TIMESTAMP
                            """, p_name, team_id, season_str, mins, goals, asts, (goals + asts), sh90, xg90, p_fls, p_fld, p_crdy, p_crdr)

                            metrics_data = [
                                ("metric_goals", goals), ("metric_assists", asts), ("metric_goals_assists", goals + asts),
                                ("metric_xg_90", xg90), ("metric_shots_90", sh90), ("metric_fouls_committed", p_fls),
                                ("metric_fouls_drawn", p_fld), ("metric_yellow_cards", p_crdy)
                            ]
                            for t_name, val in metrics_data:
                                await conn.execute(f"INSERT INTO fbref_player.{t_name} (player_name, team_id, season, quantity) VALUES ($1, $2, $3, $4) ON CONFLICT (player_name, team_id, season) DO UPDATE SET quantity=EXCLUDED.quantity, last_updated=CURRENT_TIMESTAMP", p_name, team_id, season_str, val)
                            
                            saved_players += 1
                            
                    logger.info(f"✅ {sd_league}: {saved_teams} equipes e {saved_players} jogadores atualizados.")

        except Exception as e:
            logger.warning(f"⚠️ Acesso bloqueado ou falha no parsing em {sd_league}: {str(e)[:100]}")

    async def run(self):
        logger.info("==================================================================")
        logger.info(" 🤖 INICIANDO FBREF MASTER INGESTER (FOCO NO MVP) ")
        logger.info("==================================================================")
        await db.connect()
        await entity_resolver.load_mappings_from_db()
        
        eur_season = self._get_season_string()
        
        for sport_key, sd_league in self.sd_leagues.items():
            await self.process_league(sport_key, sd_league, eur_season)
            logger.info("⏳ Resfriando conexão (10s)...")
            await asyncio.sleep(10)
            
        await db.disconnect()
        logger.info("🏆 MASTER INGESTER CONCLUÍDO. O Banco de Dados Global foi atualizado com sucesso.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(FBrefMasterIngester().run())