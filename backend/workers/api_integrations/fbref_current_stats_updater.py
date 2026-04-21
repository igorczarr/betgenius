# betgenius-backend/workers/api_integrations/fbref_current_stats_updater.py
import asyncio
import logging
import soccerdata as sd
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# Adiciona o backend ao path para importações absolutas
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.database import db
from engine.entity_resolution import entity_resolver

logging.basicConfig(level=logging.INFO, format="%(asctime)s [STATS-UPDATER] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class CurrentSeasonStatsUpdater:
    """
    Motor S-Tier de Performance (Current Season).
    Usa o SoccerData para extrair métricas Coletivas (Ofensivas/Defensivas/Posse) 
    e Individuais (xG/90, Chutes/90, Faltas, Cartões) da temporada em andamento.
    """
    def __init__(self):
        # Ligas que usam Master CSVs no Football-Data
        self.extra_leagues = ["BRA", "USA", "SWE", "NOR", "DNK", "JPN"]
        
        # Mapeamento estrito do SoccerData (Exigência da biblioteca para o FBref)
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
            
            # CONTINENTAIS E COPAS
            "soccer_uefa_europa_league": "INT-Europa League",
            "soccer_conmebol_libertadores": "INT-Copa Libertadores",
            "soccer_conmebol_sudamericana": "INT-Copa Sudamericana",
            
            # INTERNACIONAIS (SELEÇÕES)
            "soccer_fifa_world_cup": "INT-World Cup",
            "soccer_conmebol_copa_america": "INT-Copa América",
            "soccer_uefa_euro_qualifications": "INT-European Championship",
            "soccer_uefa_nations_league": "INT-UEFA Nations League"
        }

    def _get_season_string(self) -> str:
        """Determina a string da temporada atual para o SoccerData."""
        now = datetime.now()
        if now.month < 7:
            # Primeiro semestre: A Europa está na temporada que começou no ano passado
            return f"{str(now.year - 1)[-2:]}{str(now.year)[-2:]}"
        else:
            # Segundo semestre: A Europa começou a temporada nova
            return f"{str(now.year)[-2:]}{str(now.year + 1)[-2:]}"

    def _get_brazil_season(self) -> str:
        """Série A usa o ano civil cheio."""
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

    async def _ensure_schemas(self, conn):
        """Garante que a infraestrutura S-Tier das tabelas de estatísticas exista."""
        await conn.execute("CREATE SCHEMA IF NOT EXISTS fbref_squad;")
        await conn.execute("CREATE SCHEMA IF NOT EXISTS fbref_player;")
        
        # Tabelas de Equipe
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS fbref_squad.standings_wages (
                team_id INTEGER, season VARCHAR(10), pts INTEGER, wins INTEGER, wage_bill_annual NUMERIC,
                UNIQUE(team_id, season)
            );
            CREATE TABLE IF NOT EXISTS fbref_squad.advanced_general (
                team_id INTEGER, season VARCHAR(10), possession_pct NUMERIC, xg_for NUMERIC, xga_against NUMERIC,
                UNIQUE(team_id, season)
            );
        """)
        
        # Tabelas de Jogadores (Métricas individuais mapeadas pelo Vue.js)
        metrics = ["goals", "assists", "goals_assists", "xg_90", "shots_90", "fouls_committed", "fouls_drawn", "yellow_cards"]
        for metric in metrics:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS fbref_player.metric_{metric} (
                    player_name VARCHAR(100), team_id INTEGER, season VARCHAR(10), quantity NUMERIC, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(player_name, team_id, season)
                );
            """)

    def _safe_extract(self, df, idx, keywords, is_float=True):
        """Varre as colunas achatadas procurando por palavras-chave (Ex: 'expected_xg' ou 'per 90_xg')."""
        for col in df.columns:
            col_lower = str(col).lower()
            if any(kw in col_lower for kw in keywords):
                val = df.at[idx, col]
                try:
                    return float(val) if is_float else int(float(val))
                except:
                    pass
        return 0.0 if is_float else 0

    async def process_league(self, sport_key: str, sd_league: str, season_str: str):
        logger.info(f"📡 Buscando {sd_league} ({season_str}) no SoccerData...")
        
        try:
            # O no_cache=True garante que pegaremos os dados atualizados de hoje
            fbref = sd.FBref(leagues=sd_league, seasons=season_str, no_cache=True)
            
            # 1. Extração de Equipes
            df_team_std = fbref.read_team_season_stats(stat_type='standard').reset_index()
            # Achatamento de MultiIndex (Padrão do SoccerData)
            df_team_std.columns = ['_'.join(str(c) for c in col).strip() for col in df_team_std.columns.values]
            
            # 2. Extração de Jogadores (Standard, Shooting, Misc)
            df_play_std = fbref.read_player_season_stats(stat_type='standard').reset_index()
            df_play_std.columns = ['_'.join(str(c) for c in col).strip() for col in df_play_std.columns.values]
            
            df_play_sht = fbref.read_player_season_stats(stat_type='shooting').reset_index()
            df_play_sht.columns = ['_'.join(str(c) for c in col).strip() for col in df_play_sht.columns.values]
            
            df_play_msc = fbref.read_player_season_stats(stat_type='misc').reset_index()
            df_play_msc.columns = ['_'.join(str(c) for c in col).strip() for col in df_play_msc.columns.values]

            async with db.pool.acquire() as conn:
                async with conn.transaction():
                    await self._ensure_schemas(conn)
                    
                    team_cache = {}
                    
                    # ==========================================
                    # UPSERT: ESTATÍSTICAS DE EQUIPE
                    # ==========================================
                    for idx, row in df_team_std.iterrows():
                        raw_team = self._safe_extract(df_team_std, idx, ['team', 'squad'], is_float=False)
                        if not raw_team or raw_team == 0: continue
                        
                        canonical = await entity_resolver.normalize_name(str(raw_team), False)
                        team_id = await self.auto_register_team(conn, canonical, sport_key)
                        if not team_id: continue
                        
                        team_cache[str(raw_team)] = team_id

                        pts = self._safe_extract(df_team_std, idx, ['pts', 'points'], False)
                        wins = self._safe_extract(df_team_std, idx, ['w', 'wins'], False)
                        poss = self._safe_extract(df_team_std, idx, ['poss', 'possession'])
                        xg_for = self._safe_extract(df_team_std, idx, ['xg', 'expected_xg'])
                        xga_against = self._safe_extract(df_team_std, idx, ['xga', 'expected_xga'])

                        await conn.execute("""
                            INSERT INTO fbref_squad.standings_wages (team_id, season, pts, wins) VALUES ($1, $2, $3, $4)
                            ON CONFLICT (team_id, season) DO UPDATE SET pts=EXCLUDED.pts, wins=EXCLUDED.wins
                        """, team_id, season_str, pts, wins)

                        await conn.execute("""
                            INSERT INTO fbref_squad.advanced_general (team_id, season, possession_pct, xg_for, xga_against) VALUES ($1, $2, $3, $4, $5)
                            ON CONFLICT (team_id, season) DO UPDATE SET possession_pct=EXCLUDED.possession_pct, xg_for=EXCLUDED.xg_for, xga_against=EXCLUDED.xga_against
                        """, team_id, season_str, poss, xg_for, xga_against)

                    # ==========================================
                    # UPSERT: ESTATÍSTICAS DE JOGADORES (PROPS)
                    # ==========================================
                    saved_players = 0
                    for idx, row in df_play_std.iterrows():
                        player_name = str(self._safe_extract(df_play_std, idx, ['player', 'name'], False)).strip()
                        raw_team = str(self._safe_extract(df_play_std, idx, ['team', 'squad'], False)).strip()
                        
                        if not player_name or not raw_team: continue
                        
                        # Acha o ID do time via cache
                        team_id = next((t_id for name, t_id in team_cache.items() if name.lower() in raw_team.lower()), None)
                        if not team_id: continue

                        # Standard Stats
                        goals = int(self._safe_extract(df_play_std, idx, ['gls', 'performance_gls'], False))
                        asts = int(self._safe_extract(df_play_std, idx, ['ast', 'performance_ast'], False))
                        xg90 = self._safe_extract(df_play_std, idx, ['xg', 'per 90_xg'])
                        
                        # Shooting Stats (Cruza o DF de chutes procurando o mesmo jogador)
                        sh90 = 0.0
                        sht_row = df_play_sht[df_play_sht.astype(str).apply(lambda x: player_name in x.values, axis=1)]
                        if not sht_row.empty:
                            sh90 = self._safe_extract(df_play_sht, sht_row.index[0], ['sh/90', 'standard_sh/90'])

                        # Misc Stats (Faltas, Cartões)
                        fls, fld, crdy = 0, 0, 0
                        msc_row = df_play_msc[df_play_msc.astype(str).apply(lambda x: player_name in x.values, axis=1)]
                        if not msc_row.empty:
                            m_idx = msc_row.index[0]
                            fls = int(self._safe_extract(df_play_msc, m_idx, ['fls', 'performance_fls'], False))
                            fld = int(self._safe_extract(df_play_msc, m_idx, ['fld', 'performance_fld'], False))
                            crdy = int(self._safe_extract(df_play_msc, m_idx, ['crd', 'performance_crdy'], False))

                        queries = [
                            ("fbref_player.metric_goals", goals),
                            ("fbref_player.metric_assists", asts),
                            ("fbref_player.metric_goals_assists", goals + asts),
                            ("fbref_player.metric_xg_90", xg90),
                            ("fbref_player.metric_shots_90", sh90),
                            ("fbref_player.metric_fouls_committed", fls),
                            ("fbref_player.metric_fouls_drawn", fld),
                            ("fbref_player.metric_yellow_cards", crdy),
                        ]
                        
                        for table_name, value in queries:
                            await conn.execute(f"""
                                INSERT INTO {table_name} (player_name, team_id, season, quantity) VALUES ($1, $2, $3, $4)
                                ON CONFLICT (player_name, team_id, season) DO UPDATE SET quantity=EXCLUDED.quantity, last_updated=CURRENT_TIMESTAMP
                            """, player_name, team_id, season_str, value)
                            
                        saved_players += 1
                        
            logger.info(f"✅ {sd_league}: {len(team_cache)} equipes e {saved_players} registros de jogadores extraídos e consolidados.")

        except Exception as e:
            logger.error(f"Falha ao processar {sd_league} via SoccerData: {e}")

    async def run(self):
        logger.info("🚀 INICIANDO ATUALIZADOR DE PERFORMANCE (CURRENT SEASON) S-TIER")
        await db.connect()
        await entity_resolver.load_mappings_from_db()
        
        eur_season = self._get_season_string()
        bra_season = self._get_brazil_season()
        
        for sport_key, sd_league in self.sd_leagues.items():
            season_str = bra_season if 'brazil' in sport_key else eur_season
            await self.process_league(sport_key, sd_league, season_str)
            
        await db.disconnect()
        logger.info("🏆 Atualização de Dados Individuais e Avançados Concluída!")

if __name__ == "__main__":
    updater = CurrentSeasonStatsUpdater()
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(updater.run())