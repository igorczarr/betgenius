# betgenius-backend/workers/api_football_master.py

import sys
import os
import io
import asyncio
import httpx
import redis.asyncio as redis
import json
import logging
import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from dotenv import load_dotenv

# BLINDAGEM DE ENCODING PARA WINDOWS
if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except AttributeError:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db
from engine.entity_resolution import entity_resolver
from workers.feature_engineering.matrix_builder import QuantMLBuilder 
from engine.bankroll_manager import BankrollManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [API-FOOTBALL-MASTER] %(message)s")
logger = logging.getLogger(__name__)

# Fallback Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

class APIFootballBalancer:
    """Load Balancer de Chaves da API-Football S-Tier"""
    def __init__(self):
        keys = [
            os.getenv("API_FOOTBALL_KEY"),
            os.getenv("API_FOOTBALL_KEY_2"),
            os.getenv("API_FOOTBALL_KEY_3"),
            os.getenv("API_FOOTBALL_KEY_4")
        ]
        self.keys = [k for k in keys if k and k.strip()]
        if not self.keys:
            logger.critical("🛑 Nenhuma chave da API-Football configurada. Abortando.")
            sys.exit(1)
        
        self.total_keys = len(self.keys)
        self.current_idx = 0
        self.dead_keys = set()
        logger.info(f"🛡️ Load Balancer Ativado. {self.total_keys} chaves prontas para combate.")

    def get_active_headers(self) -> dict:
        if len(self.dead_keys) == self.total_keys:
            logger.critical("💀 TODAS AS CHAVES DA API-FOOTBALL ESTÃO ESGOTADAS HOJE.")
            # Reinicia as chaves mortas se virou o dia
            self.dead_keys.clear() 
            
        current_key = self.keys[self.current_idx]
        return {
            "x-rapidapi-host": os.getenv("API_FOOTBALL_HOST", "v3.football.api-sports.io"),
            "x-rapidapi-key": current_key
        }

    def rotate_key(self):
        self.dead_keys.add(self.keys[self.current_idx])
        for _ in range(self.total_keys):
            self.current_idx = (self.current_idx + 1) % self.total_keys
            if self.keys[self.current_idx] not in self.dead_keys:
                logger.warning(f"🔄 Rotação de Chave da API efetuada (Index: {self.current_idx}).")
                return

class APIFootballMaster:
    """Orquestrador Central: Fixtures, Lineups, Players e Live Tracking"""
    def __init__(self):
        self.base_url = "https://v3.football.api-sports.io"
        self.key_pool = APIFootballBalancer()
        self.brt_tz = ZoneInfo("America/Sao_Paulo")
        
        # Mapeamento do ID da API-Football para o nosso sport_key quantitativo
        self.TIER_1_LEAGUES = {39: "soccer_epl", 140: "soccer_spain_la_liga", 135: "soccer_italy_serie_a", 78: "soccer_germany_bundesliga", 61: "soccer_france_ligue_one", 2: "soccer_uefa_champs_league", 13: "soccer_conmebol_copa_libertadores", 71: "soccer_brazil_campeonato", 253: "soccer_usa_mls"}
        self.TIER_2_LEAGUES = {40: "soccer_efl_champ", 141: "soccer_spain_segunda_division", 136: "soccer_italy_serie_b", 79: "soccer_germany_bundesliga2", 62: "soccer_france_ligue_two", 94: "soccer_portugal_primeira_liga", 88: "soccer_netherlands_eredivisie", 203: "soccer_turkey_super_league", 144: "soccer_belgium_first_div", 72: "soccer_brazil_serie_b", 3: "soccer_uefa_europa_league", 11: "soccer_conmebol_copa_sudamericana", 128: "soccer_argentina_primera_division"}
        self.TIER_3_LEAGUES = {848: "soccer_uefa_europa_conference_league", 197: "soccer_greece_super_league", 103: "soccer_norway_eliteserien", 113: "soccer_sweden_allsvenskan", 218: "soccer_austria_bundesliga", 169: "soccer_china_superleague", 119: "soccer_denmark_superliga", 235: "soccer_russia_premier_league", 262: "soccer_mexico_ligamx", 98: "soccer_japan_j_league", 106: "soccer_poland_ekstraklasa", 283: "soccer_romania_liga1", 207: "soccer_switzerland_superleague"}
        self.NATIONAL_TEAMS = {15: "soccer_fifa_world_cup", 4: "soccer_uefa_euro", 9: "soccer_copa_america", 5: "soccer_uefa_nations_league"}

        # Combina tudo para acesso rápido
        self.ALL_LEAGUES = {**self.TIER_1_LEAGUES, **self.TIER_2_LEAGUES, **self.TIER_3_LEAGUES, **self.NATIONAL_TEAMS}

    async def initialize_schema(self, conn):
        # Garante que temos a coluna api_fixture_id vital para o Live Tracking
        await conn.execute("""
            ALTER TABLE core.matches_history 
            ADD COLUMN IF NOT EXISTS api_fixture_id INTEGER UNIQUE;
        """)

    async def _make_request(self, client: httpx.AsyncClient, endpoint: str, params: dict):
        for _ in range(3):
            headers = self.key_pool.get_active_headers()
            try:
                resp = await client.get(f"{self.base_url}{endpoint}", headers=headers, params=params, timeout=15.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('errors') and 'requests' in str(data.get('errors')).lower():
                        self.key_pool.rotate_key()
                        continue
                    return data['response']
                elif resp.status_code in [403, 429]:
                    self.key_pool.rotate_key()
            except httpx.RequestError as e:
                await asyncio.sleep(2)
        return []

    async def get_or_create_team(self, conn, team_name: str, sport_key: str) -> int:
        try:
            norm_name = await entity_resolver.normalize_name(team_name)
        except Exception:
            norm_name = team_name
            
        league_id = await conn.fetchval("SELECT id FROM core.leagues WHERE sport_key = $1", sport_key)
        if not league_id:
            league_id = await conn.fetchval("INSERT INTO core.leagues (sport_key, tier) VALUES ($1, 2) RETURNING id", sport_key)
            
        t_id = await conn.fetchval("SELECT id FROM core.teams WHERE canonical_name = $1", norm_name)
        if not t_id:
            t_id = await conn.fetchval("INSERT INTO core.teams (canonical_name, league_id) VALUES ($1, $2) RETURNING id", norm_name, league_id)
        return t_id

    def extract_stats(self, statistics_list, team_id_api):
        stats = {"shots": 0, "shots_target": 0, "corners": 0, "fouls": 0, "yellow": 0, "red": 0}
        if not statistics_list: return stats
        
        for team_data in statistics_list:
            if team_data['team']['id'] == team_id_api:
                for stat in team_data['statistics']:
                    val = stat['value']
                    if val is None: val = 0
                    if isinstance(val, str) and '%' in val: val = int(val.replace('%', ''))
                    else: val = int(val)
                    
                    t = stat['type']
                    if t == 'Total Shots': stats['shots'] = val
                    elif t == 'Shots on Goal': stats['shots_target'] = val
                    elif t == 'Corner Kicks': stats['corners'] = val
                    elif t == 'Fouls': stats['fouls'] = val
                    elif t == 'Yellow Cards': stats['yellow'] = val
                    elif t == 'Red Cards': stats['red'] = val
                break
        return stats

    # =====================================================================
    # TASK 1: DAILY SYNC (Fixture + Stats de Ontem)
    # =====================================================================
    async def task_daily_sync(self, client):
        agora = datetime.now(self.brt_tz)
        hoje_str = agora.strftime("%Y-%m-%d")
        ontem_str = (agora - timedelta(days=1)).strftime("%Y-%m-%d")
        
        logger.info(f"📅 [DAILY SYNC] Mapeando Fixtures: Hoje ({hoje_str}) e Ontem ({ontem_str})")
        
        fixtures_hoje = await self._make_request(client, "/fixtures", {"date": hoje_str})
        fixtures_ontem = await self._make_request(client, "/fixtures", {"date": ontem_str})
        all_fixtures = fixtures_hoje + fixtures_ontem

        count_upsert = 0
        async with db.pool.acquire() as conn:
            for fix in all_fixtures:
                league_id = fix['league']['id']
                if league_id not in self.ALL_LEAGUES: continue
                
                api_id = fix['fixture']['id']
                sport_key = self.ALL_LEAGUES[league_id]
                referee = fix['fixture']['referee'] or "Unknown"
                status_short = fix['fixture']['status']['short']
                status = 'FINISHED' if status_short in ['FT', 'AET', 'PEN'] else ('IN_PROGRESS' if status_short in ['1H', 'HT', '2H', 'ET'] else 'SCHEDULED')
                
                h_name = fix['teams']['home']['name']
                a_name = fix['teams']['away']['name']
                match_date_utc = datetime.fromisoformat(fix['fixture']['date'])
                match_date_brt = match_date_utc.astimezone(self.brt_tz)
                
                h_id = await self.get_or_create_team(conn, h_name, sport_key)
                a_id = await self.get_or_create_team(conn, a_name, sport_key)
                hash_str = hashlib.sha256(f"{match_date_brt.date()}_{h_name}_{a_name}".lower().replace(" ", "").encode('utf-8')).hexdigest()
                
                await conn.execute("""
                    INSERT INTO core.matches_history 
                    (match_hash, api_fixture_id, sport_key, season, match_date, start_time, home_team_id, away_team_id, status, referee)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (match_hash) DO UPDATE SET 
                        api_fixture_id = EXCLUDED.api_fixture_id, status = EXCLUDED.status, referee = EXCLUDED.referee;
                """, hash_str, api_id, sport_key, str(fix['league']['season']), match_date_brt.date(), match_date_brt.replace(tzinfo=None), h_id, a_id, status, referee)
                count_upsert += 1

            pending_ids = await conn.fetch("""
                SELECT api_fixture_id FROM core.matches_history
                WHERE status = 'FINISHED' AND home_goals IS NULL AND api_fixture_id IS NOT NULL
                LIMIT 60
            """)
            
            if pending_ids:
                api_ids = [str(r['api_fixture_id']) for r in pending_ids]
                for i in range(0, len(api_ids), 20):
                    chunk = "-".join(api_ids[i:i+20])
                    logger.info(f"📊 [DAILY SYNC] Baixando Estatísticas de {len(api_ids[i:i+20])} jogos finalizados...")
                    
                    chunk_res = await self._make_request(client, "/fixtures", {"ids": chunk})
                    for cf in chunk_res:
                        goals_h = cf['goals']['home']
                        goals_a = cf['goals']['away']
                        ht_h = cf['score']['halftime']['home']
                        ht_a = cf['score']['halftime']['away']
                        
                        s_h = self.extract_stats(cf.get('statistics', []), cf['teams']['home']['id'])
                        s_a = self.extract_stats(cf.get('statistics', []), cf['teams']['away']['id'])
                        
                        res = 'W' if goals_h > goals_a else ('L' if goals_h < goals_a else 'D')
                        ht_res = 'W' if ht_h > ht_a else ('L' if ht_h < ht_a else 'D')

                        await conn.execute("""
                            UPDATE core.matches_history SET
                                home_goals=$2, away_goals=$3, match_result=$4,
                                ht_home_goals=$5, ht_away_goals=$6, ht_result=$7,
                                home_shots=$8, away_shots=$9, home_shots_target=$10, away_shots_target=$11,
                                home_corners=$12, away_corners=$13, home_fouls=$14, away_fouls=$15,
                                home_yellow=$16, away_yellow=$17, home_red=$18, away_red=$19
                            WHERE api_fixture_id = $1
                        """, cf['fixture']['id'], goals_h, goals_a, res, ht_h, ht_a, ht_res,
                             s_h['shots'], s_a['shots'], s_h['shots_target'], s_a['shots_target'],
                             s_h['corners'], s_a['corners'], s_h['fouls'], s_a['fouls'],
                             s_h['yellow'], s_a['yellow'], s_h['red'], s_a['red'])
                             
                logger.info("🧠 Acionando Motor XGBoost (QuantMLBuilder) após Injeção Pós-Jogo...")
                await QuantMLBuilder().build_matrix()
                
                logger.info("💼 Acionando o Bankroll Manager para liquidar operações abertas no fundo...")
                try:
                    manager = BankrollManager()
                    await manager.settle_pending_bets()
                    logger.info("✅ Capital liquidado e saldo atualizado no Banco de Dados.")
                except Exception as e:
                    logger.error(f"Erro ao liquidar o Ledger: {e}")

    # =====================================================================
    # TASK 2: LINEUPS (45 Minutos Pré-Jogo Tier 1)
    # =====================================================================
    async def task_lineups(self, client):
        tier1_sports = tuple(self.TIER_1_LEAGUES.values())
        async with db.pool.acquire() as conn:
            upcoming = await conn.fetch("""
                SELECT m.api_fixture_id, m.id as match_id, m.home_team_id, m.away_team_id
                FROM core.matches_history m
                LEFT JOIN core.match_lineups l ON m.id = l.match_id
                WHERE m.status = 'SCHEDULED' 
                AND m.start_time BETWEEN NOW() AND NOW() + INTERVAL '50 minutes'
                AND m.sport_key IN (SELECT unnest($1::text[]))
                AND l.match_id IS NULL
            """, tier1_sports)

            for gm in upcoming:
                api_id = gm['api_fixture_id']
                logger.info(f"📋 [LINEUPS] Extraindo escalação do Jogo ID {api_id} (Tier 1)...")
                lineups = await self._make_request(client, "/fixtures/lineups", {"fixture": api_id})
                
                for team_l in lineups:
                    t_id_db = gm['home_team_id'] if team_l['team']['id'] == lineups[0]['team']['id'] else gm['away_team_id']
                    form = team_l.get('formation', 'Unknown')
                    coach = team_l.get('coach', {}).get('name', 'Unknown')
                    start_xi = json.dumps(team_l.get('startXI', []))
                    subs = json.dumps(team_l.get('substitutes', []))

                    await conn.execute("""
                        INSERT INTO core.match_lineups (match_id, team_id, formation, coach_name, starting_xi, substitutes)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (match_id, team_id) DO NOTHING;
                    """, gm['match_id'], t_id_db, form, coach, start_xi, subs)

    # =====================================================================
    # TASK 3: IN-PLAY TRACKING (On-Demand via Redis)
    # =====================================================================
    async def task_live_daemon(self, client, redis_client):
        active_str = await redis_client.get("quant:live_tracking_ids")
        if not active_str: return
        live_ids = json.loads(active_str)
        if not live_ids: return

        chunks = [live_ids[i:i+20] for i in range(0, len(live_ids), 20)]
        async with db.pool.acquire() as conn:
            for chunk in chunks:
                ids_param = "-".join(map(str, chunk))
                live_data = await self._make_request(client, "/fixtures", {"ids": ids_param})
                
                for fix in live_data:
                    m_api_id = fix['fixture']['id']
                    status = fix['fixture']['status']['short']
                    
                    if status in ['FT', 'AET', 'PEN', 'CANC', 'PSTP']:
                        live_ids.remove(m_api_id) if m_api_id in live_ids else None
                        continue
                        
                    minute = fix['fixture']['status']['elapsed'] or 0
                    g_h = fix['goals']['home'] or 0
                    g_a = fix['goals']['away'] or 0
                    
                    st_h = self.extract_stats(fix.get('statistics', []), fix['teams']['home']['id'])
                    st_a = self.extract_stats(fix.get('statistics', []), fix['teams']['away']['id'])
                    
                    s_h_total = st_h['shots']
                    s_a_total = st_a['shots']
                    s_h_on = st_h['shots_target']
                    s_a_on = st_a['shots_target']
                    c_h = st_h['corners']
                    c_a = st_a['corners']
                    
                    momentum_h = (s_h_on * 2.5) + ((s_h_total - s_h_on) * 1.0) + (c_h * 1.5)
                    momentum_a = (s_a_on * 2.5) + ((s_a_total - s_a_on) * 1.0) + (c_a * 1.5)
                    momentum_index = momentum_h - momentum_a
                    
                    last_event = "Em andamento"
                    if fix.get('events'): last_event = fix['events'][-1]['detail']

                    db_match_id = await conn.fetchval("SELECT id FROM core.matches_history WHERE api_fixture_id = $1", m_api_id)
                    if db_match_id:
                        await conn.execute("""
                            INSERT INTO core.live_match_tracking 
                            (match_id, match_minute, status_short, home_score, away_score, 
                             home_shots_target_live, away_shots_target_live, home_corners_live, away_corners_live,
                             momentum_index, last_event, last_updated)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW())
                            ON CONFLICT (match_id) DO UPDATE SET
                                match_minute = EXCLUDED.match_minute, status_short = EXCLUDED.status_short,
                                home_score = EXCLUDED.home_score, away_score = EXCLUDED.away_score,
                                home_shots_target_live = EXCLUDED.home_shots_target_live,
                                away_shots_target_live = EXCLUDED.away_shots_target_live,
                                home_corners_live = EXCLUDED.home_corners_live,
                                away_corners_live = EXCLUDED.away_corners_live,
                                momentum_index = EXCLUDED.momentum_index,
                                last_event = EXCLUDED.last_event, last_updated = NOW();
                        """, db_match_id, minute, status, g_h, g_a, s_h_on, s_a_on, c_h, c_a, round(momentum_index, 2), last_event)
        
        await redis_client.set("quant:live_tracking_ids", json.dumps(live_ids))

    # =====================================================================
    # TASK 4: WEEKLY PLAYERS & INJURIES (Terças e Sextas)
    # =====================================================================
    async def task_weekly_players(self, client):
        agora = datetime.now(self.brt_tz)
        logger.info(f"🧬 [WEEKLY ROSTER] Atualizando Banco de Jogadores e Lesões...")
        
        season = str(agora.year if agora.month > 6 else agora.year - 1)
        
        # Vamos rotacionar: Terças puxa Tier 1, Sextas puxa Tier 2
        target_leagues = self.TIER_1_LEAGUES if agora.weekday() == 1 else self.TIER_2_LEAGUES
        
        async with db.pool.acquire() as conn:
            for api_league_id, sport_key in target_leagues.items():
                # 1. Busca Lesões
                logger.info(f"🏥 Buscando lesões para {sport_key}...")
                injuries = await self._make_request(client, "/injuries", {"league": api_league_id, "season": season})
                for inj in injuries:
                    team_name = inj['team']['name']
                    player_name = inj['player']['name']
                    player_id_api = inj['player']['id']
                    reason = inj['player']['reason']
                    t_type = inj['player']['type']
                    expected_return = inj.get('player', {}).get('expected_return', 'Unknown')
                    fixture_id = inj['fixture']['id']
                    
                    t_id = await self.get_or_create_team(conn, team_name, sport_key)
                    
                    await conn.execute("""
                        INSERT INTO core.players (id, name, team_id) VALUES ($1, $2, $3) ON CONFLICT (id) DO NOTHING
                    """, player_id_api, player_name, t_id)
                    
                    await conn.execute("""
                        INSERT INTO core.team_injuries (player_id, team_id, fixture_id, player_name, type, reason, expected_return, status)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, 'Active')
                    """, player_id_api, t_id, fixture_id, player_name, t_type, reason, expected_return)

                # 2. Busca Player Stats Consolidado
                logger.info(f"🏃 Buscando Stats Consolidadas de Jogadores para {sport_key}...")
                page = 1
                while True:
                    players_data = await self._make_request(client, "/players", {"league": api_league_id, "season": season, "page": page})
                    if not players_data: break
                    
                    for p in players_data:
                        player_info = p['player']
                        p_id = player_info['id']
                        p_name = player_info['name']
                        
                        stats = next((s for s in p['statistics'] if s['league']['id'] == api_league_id), None)
                        if not stats: continue
                        
                        t_name = stats['team']['name']
                        t_id = await self.get_or_create_team(conn, t_name, sport_key)
                        
                        pos = stats['games']['position']
                        rating = float(stats['games']['rating'] or 0)
                        apps = stats['games']['appearences'] or 0
                        mins = stats['games']['minutes'] or 0
                        goals = stats['goals']['total'] or 0
                        assists = stats['goals']['assists'] or 0
                        shots = stats['shots']['total'] or 0
                        shots_on = stats['shots']['on'] or 0
                        passes_acc = float(stats['passes']['accuracy'] or 0)
                        tackles = stats['tackles']['total'] or 0
                        interceptions = stats['tackles']['interceptions'] or 0
                        fouls_c = stats['fouls']['committed'] or 0
                        fouls_d = stats['fouls']['drawn'] or 0
                        yel = stats['cards']['yellow'] or 0
                        red = stats['cards']['red'] or 0
                        
                        await conn.execute("""
                            INSERT INTO core.players (id, name, firstname, lastname, age, nationality, height, weight, photo, team_id, position)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                            ON CONFLICT (id) DO UPDATE SET team_id = EXCLUDED.team_id, position = EXCLUDED.position
                        """, p_id, p_name, player_info.get('firstname'), player_info.get('lastname'), player_info.get('age'), player_info.get('nationality'), player_info.get('height'), player_info.get('weight'), player_info.get('photo'), t_id, pos)
                        
                        l_id_db = await conn.fetchval("SELECT id FROM core.leagues WHERE sport_key = $1", sport_key)
                        
                        await conn.execute("""
                            INSERT INTO core.player_season_stats 
                            (player_id, league_id, season, rating, appearences, minutes_played, goals, assists, shots_total, shots_on_target, passes_accuracy, tackles, interceptions, fouls_committed, fouls_drawn, yellow_cards, red_cards)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                            ON CONFLICT (player_id, league_id, season) DO UPDATE SET
                                rating = EXCLUDED.rating, appearences = EXCLUDED.appearences, minutes_played = EXCLUDED.minutes_played, goals = EXCLUDED.goals, assists = EXCLUDED.assists, shots_total = EXCLUDED.shots_total, shots_on_target = EXCLUDED.shots_on_target, passes_accuracy = EXCLUDED.passes_accuracy, tackles = EXCLUDED.tackles, interceptions = EXCLUDED.interceptions, fouls_committed = EXCLUDED.fouls_committed, fouls_drawn = EXCLUDED.fouls_drawn, yellow_cards = EXCLUDED.yellow_cards, red_cards = EXCLUDED.red_cards, last_updated = NOW()
                        """, p_id, l_id_db, season, rating, apps, mins, goals, assists, shots, shots_on, passes_acc, tackles, interceptions, fouls_c, fouls_d, yel, red)
                        
                    if len(players_data) < 20:
                        break
                    page += 1
                    await asyncio.sleep(1.5) # Anti-Rate Limit de Segurança

    # =====================================================================
    # ORQUESTRADOR CENTRAL (Scheduler)
    # =====================================================================
    async def run_daemon(self):
        logger.info("🚀 API-FOOTBALL MASTER DAEMON INICIADO.")
        await db.connect()
        await entity_resolver.load_mappings_from_db()
        redis_client = await redis.from_url(REDIS_URL)
        
        async with db.pool.acquire() as conn:
            await self.initialize_schema(conn)

        limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
        async with httpx.AsyncClient(limits=limits) as client:
            last_daily_sync = None
            last_weekly_sync = None
            
            while True:
                agora = datetime.now(self.brt_tz)
                
                # 1. DAILY SYNC (Roda às 02:XX AM)
                if agora.hour == 2 and (not last_daily_sync or last_daily_sync.date() < agora.date()):
                    await self.task_daily_sync(client)
                    last_daily_sync = agora
                
                # 2. LINEUPS (Roda a cada ciclo de 5 mins)
                if agora.minute % 5 == 0:
                    await self.task_lineups(client)
                
                # 3. LIVE DAEMON (On-Demand. Roda a cada 2 minutos contínuos se houver ids)
                if agora.minute % 2 == 0:
                    await self.task_live_daemon(client, redis_client)
                    
                # 4. WEEKLY PLAYERS & INJURIES (Roda Terças e Sextas às 03:00 AM)
                if agora.weekday() in [1, 4] and agora.hour == 3 and (not last_weekly_sync or last_weekly_sync.date() < agora.date()):
                    await self.task_weekly_players(client)
                    last_weekly_sync = agora

                # Pausa para economizar CPU
                await asyncio.sleep(60)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    master = APIFootballMaster()
    try:
        asyncio.run(master.run_daemon())
    except KeyboardInterrupt:
        logger.info("🛑 Daemon encerrado pelo operador.")