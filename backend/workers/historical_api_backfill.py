import sys
import os
import io
import json
import hashlib
import asyncio
import logging
import httpx
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# --- CONFIGURAÇÃO DE AMBIENTE E ENCODING ---
if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except AttributeError:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / '.env')
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [LEVIATHAN-BACKFILL] %(message)s")
logger = logging.getLogger(__name__)

class ApiKeyPool:
    def __init__(self):
        self.keys = [
            os.getenv("API_FOOTBALL_KEY"),
            os.getenv("API_FOOTBALL_KEY_2"),
            os.getenv("API_FOOTBALL_KEY_3")
        ]
        self.keys = [k for k in self.keys if k]
        self.current_idx = 0
        self.total_requests = 0

    def get_current_key(self):
        return self.keys[self.current_idx]

    def rotate(self):
        if len(self.keys) > 1:
            self.current_idx = (self.current_idx + 1) % len(self.keys)
            logger.warning(f"🔄 Rotação de chave: Usando agora a chave índice {self.current_idx}")
            return True
        return False

class HistoricalAPIBackfill:
    def __init__(self):
        self.key_pool = ApiKeyPool()
        self.base_url = "https://v3.football.api-sports.io"
        self.MAX_TOTAL_REQUESTS = 180  # aumentei pra usar múltiplas chaves

        self.state_file = Path(__file__).parent / "backfill_state.json"
        self.state = self._load_state()

        self.TARGET_LEAGUES = {
            15: "soccer_fifa_world_cup",
            4: "soccer_uefa_euro",
            9: "soccer_copa_america",
            2: "soccer_uefa_champs_league",
            3: "soccer_uefa_europa_league",
            13: "soccer_conmebol_copa_libertadores",
            11: "soccer_conmebol_copa_sudamericana",
            45: "soccer_england_fa_cup",
            73: "soccer_brazil_copa_do_brasil",
            81: "soccer_germany_dfb_pokal",
            137: "soccer_italy_coppa_italia",
            143: "soccer_spain_copa_del_rey",
            7: "soccer_afc_asian_cup",
            6: "soccer_caf_afcon",
            22: "soccer_concacaf_gold_cup"
        }

        self.START_YEAR = 2014
        self.END_YEAR = 2024

    def _load_state(self):
        if self.state_file.exists():
            return json.load(open(self.state_file, 'r'))
        return {}

    def _save_state(self):
        json.dump(self.state, open(self.state_file, 'w'), indent=4)

    def _generate_match_hash(self, date_str, home, away):
        raw = f"{date_str}_{home}_{away}".lower().replace(" ", "")
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    async def _fetch_season(self, client, league_id, season):
        if self.key_pool.total_requests >= self.MAX_TOTAL_REQUESTS:
            return "LIMIT_REACHED"

        headers = {
            "x-rapidapi-host": "v3.football.api-sports.io",
            "x-rapidapi-key": self.key_pool.get_current_key()
        }

        try:
            resp = await client.get(
                f"{self.base_url}/fixtures",
                headers=headers,
                params={"league": league_id, "season": season},
                timeout=20.0
            )

            self.key_pool.total_requests += 1

            if resp.status_code == 200:
                data = resp.json()

                if data.get('errors') and 'requests' in str(data['errors']).lower():
                    if self.key_pool.rotate():
                        return await self._fetch_season(client, league_id, season)
                    return "LIMIT_REACHED"

                return data.get('response', [])

            elif resp.status_code in [429, 403]:
                if self.key_pool.rotate():
                    return await self._fetch_season(client, league_id, season)
                return "LIMIT_REACHED"

        except Exception as e:
            logger.error(f"Erro na Liga {league_id} ({season}): {e}")

        return []

    async def _get_or_create_team(self, conn, team_name, sport_key):
        t_id = await conn.fetchval(
            "SELECT id FROM core.teams WHERE canonical_name = $1", team_name
        )

        if not t_id:
            l_id = await conn.fetchval(
                "SELECT id FROM core.leagues WHERE sport_key = $1", sport_key
            )

            if not l_id:
                l_id = await conn.fetchval(
                    "INSERT INTO core.leagues (sport_key, name, tier) VALUES ($1, $1, 1) RETURNING id",
                    sport_key
                )

            t_id = await conn.fetchval(
                "INSERT INTO core.teams (canonical_name, league_id) VALUES ($1, $2) RETURNING id",
                team_name, l_id
            )

        return t_id

    async def run(self):
        logger.info("🌍 Iniciando Operação Leviatã 2.0...")
        await db.connect()

        async with httpx.AsyncClient() as client:
            for year in range(self.START_YEAR, self.END_YEAR + 1):
                for l_id, s_key in self.TARGET_LEAGUES.items():

                    state_key = f"{l_id}_{year}"
                    if self.state.get(state_key):
                        continue

                    data = await self._fetch_season(client, l_id, year)

                    if data == "LIMIT_REACHED":
                        logger.warning("🛑 Limite diário de segurança atingido. A guardar progresso...")
                        self._save_state()
                        await db.disconnect()
                        return

                    if data:
                        fixtures = [
                            f for f in data
                            if f['fixture']['status']['short'] in ['FT', 'AET', 'PEN']
                        ]
                        fixtures.sort(key=lambda x: x['fixture']['date'])

                        async with db.pool.acquire() as conn:
                            async with conn.transaction():

                                for fix in fixtures:
                                    date_str = fix['fixture']['date'][:10]
                                    h_name = fix['teams']['home']['name']
                                    a_name = fix['teams']['away']['name']
                                    h_goals = fix['goals']['home']
                                    a_goals = fix['goals']['away']

                                    h_id = await self._get_or_create_team(conn, h_name, s_key)
                                    a_id = await self._get_or_create_team(conn, a_name, s_key)

                                    m_hash = self._generate_match_hash(date_str, h_name, a_name)

                                    await conn.execute("""
                                        INSERT INTO core.matches_history 
                                        (match_hash, sport_key, season, match_date, start_time, 
                                                       home_team_id, away_team_id, status, home_goals, away_goals, match_result)
                                        VALUES ($1, $2, $3, $4, $5, $6, $7, 'FINISHED', $8, $9, $10)
                                        ON CONFLICT (match_hash) DO NOTHING
                                    """,
                                        m_hash,
                                        s_key,
                                        str(year),
                                        datetime.strptime(date_str, "%Y-%m-%d").date(),
                                        datetime.fromisoformat(fix['fixture']['date']).replace(tzinfo=None),
                                        h_id,
                                        a_id,
                                        h_goals,
                                        a_goals,
                                        'W' if h_goals > a_goals else ('L' if h_goals < a_goals else 'D')
                                    )

                        self.state[state_key] = True
                        self._save_state()

                        logger.info(f"✅ Liga {s_key} | Ano {year} injetada com sucesso.")

                        await asyncio.sleep(1)

        await db.disconnect()
        logger.info("🏁 Backfill concluído.")


if __name__ == "__main__":
    asyncio.run(HistoricalAPIBackfill().run())