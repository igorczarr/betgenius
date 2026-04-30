# betgenius-backend/workers/odds_ingestion.py

import sys
import os
import io
import asyncio
import httpx
import redis.asyncio as redis
import json
import logging
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

# FIX DE ENCODING PARA WINDOWS
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

sys.path.append(str(Path(__file__).parent.parent))
from core.config import settings
from engine.entity_resolution import entity_resolver
from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [QUANT-WORKER] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

# Fallback robusto do Redis
raw_redis_url = getattr(settings, 'REDIS_URL', None) or os.getenv("REDIS_URL")
if not raw_redis_url or not raw_redis_url.startswith(("redis://", "rediss://", "unix://")):
    REDIS_URL = "redis://localhost:6379"
    logger.warning(f"⚠️ REDIS_URL ausente ou inválida. Assumindo fallback: {REDIS_URL}")
else:
    REDIS_URL = raw_redis_url

BASE_URL = "https://api.the-odds-api.com/v4/sports"
TARGET_BOOKMAKERS = "pinnacle,bet365" 

class APILoadBalancer:
    def __init__(self, keys: list):
        if not keys:
            raise ValueError("CRÍTICO: Nenhuma chave de API encontrada no pool!")
        self.keys = keys
        self.total_keys = len(keys)
        self.current_idx = 0
        self.quotas = {k: 500 for k in keys}
        self.dead_keys = set()
        logger.info(f"🛡️ Load Balancer (The Odds API) Ativado: {self.total_keys} chaves.")

    def get_active_key(self) -> str:
        if len(self.dead_keys) == self.total_keys:
            raise SystemError("💀 TODAS AS CHAVES ESTÃO MORTAS/ESGOTADAS.")
        return self.keys[self.current_idx]

    def update_quota(self, key: str, remaining: int):
        self.quotas[key] = remaining
        if remaining <= 10 and key not in self.dead_keys:
            logger.warning(f"⚠️ Chave esgotada. Retirando do pool ativo.")
            self.dead_keys.add(key)
            self.rotate_key(reason="Cota esgotada")

    def rotate_key(self, reason="Rotação tática"):
        old_idx = self.current_idx
        for _ in range(self.total_keys):
            self.current_idx = (self.current_idx + 1) % self.total_keys
            if self.keys[self.current_idx] not in self.dead_keys:
                logger.warning(f"🔄 ROTAÇÃO [Idx {old_idx} -> {self.current_idx}]. Motivo: {reason}")
                return
        raise SystemError("💀 Nenhuma chave viva restante no pool durante a rotação.")

    def get_global_quota(self) -> int:
        return sum(q for k, q in self.quotas.items() if k not in self.dead_keys)

# =====================================================================
# FALLBACK POOL PARA API-FOOTBALL
# =====================================================================
class APIFootballBalancer:
    def __init__(self):
        keys = [
            os.getenv("API_FOOTBALL_KEY"),
            os.getenv("API_FOOTBALL_KEY_2"),
            os.getenv("API_FOOTBALL_KEY_3"),
            os.getenv("API_FOOTBALL_KEY_4")
        ]
        self.keys = [k for k in keys if k and k.strip()]
        self.current_idx = 0

    def get_active_headers(self) -> dict:
        if not self.keys: return None
        return {
            "x-rapidapi-host": os.getenv("API_FOOTBALL_HOST", "v3.football.api-sports.io"),
            "x-rapidapi-key": self.keys[self.current_idx]
        }

    def rotate_key(self):
        if self.keys:
            self.current_idx = (self.current_idx + 1) % len(self.keys)
            logger.warning("🔄 Rotação de Chave da API-Football acionada.")

key_pool = APILoadBalancer(settings.ODDS_API_KEY_POOL)
af_pool = APIFootballBalancer()

# Mapeamento Reverso para o Fallback da API-Football
SPORT_TO_APIF = {
    "soccer_epl": 39, "soccer_spain_la_liga": 140, "soccer_italy_serie_a": 135,
    "soccer_germany_bundesliga": 78, "soccer_france_ligue_one": 61,
    "soccer_uefa_champs_league": 2, "soccer_conmebol_copa_libertadores": 13,
    "soccer_brazil_campeonato": 71, "soccer_usa_mls": 253,
    "soccer_efl_champ": 40, "soccer_spain_segunda_division": 141, 
    "soccer_italy_serie_b": 136, "soccer_portugal_primeira_liga": 94, 
    "soccer_netherlands_eredivisie": 88, "soccer_brazil_serie_b": 72
}

# =====================================================================
# MATRIZ DE ROTAÇÃO S-TIER
# =====================================================================
TIERED_LEAGUES = {
    1: [
        "soccer_epl", "soccer_spain_la_liga", "soccer_italy_serie_a", 
        "soccer_germany_bundesliga", "soccer_france_ligue_one",
        "soccer_uefa_champs_league", "soccer_conmebol_copa_libertadores",
        "soccer_brazil_campeonato", "soccer_usa_mls"
    ],
    2: [
        "soccer_efl_champ", "soccer_spain_segunda_division", "soccer_italy_serie_b", 
        "soccer_germany_bundesliga2", "soccer_france_ligue_two",
        "soccer_portugal_primeira_liga", "soccer_netherlands_eredivisie",
        "soccer_turkey_super_league", "soccer_belgium_first_div",
        "soccer_brazil_serie_b", "soccer_uefa_europa_league", 
        "soccer_conmebol_copa_sudamericana", "soccer_argentina_primera_division"
    ],
    3: [
        "soccer_uefa_europa_conference_league", "soccer_greece_super_league", 
        "soccer_norway_eliteserien", "soccer_sweden_allsvenskan", "soccer_austria_bundesliga", 
        "soccer_china_superleague", "soccer_denmark_superliga", "soccer_finland_veikkausliiga", 
        "soccer_ireland_premier_division", "soccer_japan_j_league", "soccer_mexico_ligamx", 
        "soccer_poland_ekstraklasa", "soccer_romania_liga1", "soccer_switzerland_superleague"
    ]
}

semaphore = asyncio.Semaphore(5) 

async def _make_request(client: httpx.AsyncClient, url: str, params: dict, max_retries=3):
    backoff_time = 2.0
    for attempt in range(max_retries):
        current_key = key_pool.get_active_key()
        params["apiKey"] = current_key
        try:
            response = await client.get(url, params=params, timeout=12.0)
            
            if response.status_code == 200:
                remaining = int(response.headers.get('x-requests-remaining', 0))
                key_pool.update_quota(current_key, remaining)
                return response.json()
                
            elif response.status_code == 422:
                if params["markets"] != "h2h,totals,spreads":
                    logger.debug(f"422 Recebido. Fazendo downgrade de mercados para a URL: {url}")
                    params["markets"] = "h2h,totals,spreads" 
                    continue 
                else:
                    return None
                    
            elif response.status_code == 429:
                logger.warning(f"⚠️ Rate Limit (429). Pausa tática de {backoff_time}s...")
                await asyncio.sleep(backoff_time)
                backoff_time *= 2
                key_pool.rotate_key(reason="Evadindo Rate Limit")
                continue
                
            elif response.status_code == 401:
                key_pool.update_quota(current_key, 0)
                continue
                
            elif response.status_code == 404:
                return None
                
        except httpx.RequestError as e:
            await asyncio.sleep(backoff_time)
            
    return None

async def auto_register_team(conn, canonical_name: str, sport_key: str) -> int:
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

async def process_match_odds(conn, game: dict, redis_client):
    home_team_norm = await entity_resolver.normalize_name(game['home_team'])
    away_team_norm = await entity_resolver.normalize_name(game['away_team'])
    
    if not home_team_norm: home_team_norm = game['home_team']
    if not away_team_norm: away_team_norm = game['away_team']

    sport_key = game['sport_key']
    commence_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
    match_date = commence_time.date()

    match_id = await conn.fetchval("""
        SELECT m.id FROM core.matches_history m
        JOIN core.teams th ON m.home_team_id = th.id
        JOIN core.teams ta ON m.away_team_id = ta.id
        WHERE th.canonical_name = $1 AND ta.canonical_name = $2
        AND m.match_date >= CURRENT_DATE - INTERVAL '2 days'
        AND m.status = 'SCHEDULED'
    """, home_team_norm, away_team_norm)

    if not match_id:
        h_id = await auto_register_team(conn, home_team_norm, sport_key)
        a_id = await auto_register_team(conn, away_team_norm, sport_key)
        
        # CORREÇÃO CIRÚRGICA: Gerando o match_hash obrigatório
        hash_str = hashlib.sha256(f"{match_date}_{home_team_norm}_{away_team_norm}".lower().replace(" ", "").encode('utf-8')).hexdigest()
        
        match_id = await conn.fetchval("""
            INSERT INTO core.matches_history (match_hash, sport_key, match_date, home_team_id, away_team_id, status)
            VALUES ($1, $2, $3, $4, $5, 'SCHEDULED')
            ON CONFLICT (match_hash) DO NOTHING
            RETURNING id
        """, hash_str, sport_key, match_date, h_id, a_id)

        # Caso o DO NOTHING dispare (hash já existia mas não foi apanhado na query anterior), recuperamos o id
        if not match_id:
             match_id = await conn.fetchval("SELECT id FROM core.matches_history WHERE match_hash = $1", hash_str)

    # Se ainda assim não houver match_id válido, aborta de forma segura o preenchimento de odds deste jogo
    if not match_id:
        return

    for bookie in game.get('bookmakers', []):
        bookie_key = bookie['key']
        for market in bookie.get('markets', []):
            cat = market['key']
            for outcome in market.get('outcomes', []):
                name = outcome['name']
                price = float(outcome['price'])
                point = outcome.get('point', '')

                if cat in ['totals', 'spreads'] and point:
                    nome_mercado = f"{name} {point}"
                else:
                    nome_mercado = name
                    if name == game['home_team']: nome_mercado = "home"
                    elif name == game['away_team']: nome_mercado = "away"
                    elif name == "Draw": nome_mercado = "draw"
                    
                record = await conn.fetchrow("""
                    SELECT id, current_odd, opening_odd FROM core.market_odds 
                    WHERE match_id = $1 AND categoria = $2 AND nome_mercado = $3 AND bookmaker = $4
                """, match_id, cat, nome_mercado, bookie_key)

                if record:
                    old_odd = float(record['current_odd'])
                    if old_odd != price:
                        drop_pct = (old_odd - price) / old_odd if old_odd > 0 else 0
                        heavy_drop = drop_pct > 0.08 
                        
                        await conn.execute("""
                            UPDATE core.market_odds 
                            SET current_odd = $1, heavy_drop_alert = $2, updated_at = NOW() 
                            WHERE id = $3
                        """, price, heavy_drop, record['id'])
                        
                        if heavy_drop and bookie_key == 'pinnacle':
                            logger.warning(f"🚨 STEAMER DETECTADO: {home_team_norm} x {away_team_norm} | {cat} ({nome_mercado}) caiu para {price} (-{drop_pct:.1%})")
                            await conn.execute("""
                                INSERT INTO core.hft_odds_drops (event_id, jogo, mercado, selecao, odd_abertura, odd_atual, drop_pct)
                                VALUES ($1, $2, $3, $4, $5, $6, $7)
                            """, str(game['id']), f"{home_team_norm} x {away_team_norm}", cat, nome_mercado, old_odd, price, round(drop_pct*100, 2))
                else:
                    await conn.execute("""
                        INSERT INTO core.market_odds (match_id, categoria, nome_mercado, bookmaker, current_odd, opening_odd, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $5, NOW())
                    """, match_id, cat, nome_mercado, bookie_key, price)

async def fetch_fallback_api_football(client, redis_client, sport_key):
    """Traduz as Odds da API-Football para o formato da The Odds API."""
    league_id = SPORT_TO_APIF.get(sport_key)
    if not league_id: return
    
    headers = af_pool.get_active_headers()
    if not headers: return
    
    hoje = datetime.now().strftime("%Y-%m-%d")
    url = "https://v3.football.api-sports.io/odds"
    
    try:
        resp = await client.get(url, headers=headers, params={"league": league_id, "season": "2024", "date": hoje, "bookmaker": 8}, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json().get("response", [])
            async with db.pool.acquire() as conn:
                for item in data:
                    h_name = item['fixture']['home']['name']
                    a_name = item['fixture']['away']['name']
                    
                    game = {
                        "id": f"fallback_{item['fixture']['id']}",
                        "sport_key": sport_key,
                        "home_team": h_name,
                        "away_team": a_name,
                        "commence_time": item['fixture']['date'],
                        "bookmakers": []
                    }
                    
                    bookie_data = {"key": "bet365", "markets": []}
                    
                    for bookie in item.get('bookmakers', []):
                        for bet in bookie.get('bets', []):
                            if bet['id'] == 1: 
                                outcomes = []
                                for val in bet['values']:
                                    name = "Draw" if val['value'] == "Draw" else (h_name if val['value'] == "Home" else a_name)
                                    outcomes.append({"name": name, "price": float(val['odd'])})
                                bookie_data['markets'].append({"key": "h2h", "outcomes": outcomes})
                                
                            elif bet['id'] == 5: 
                                outcomes = []
                                for val in bet['values']:
                                    if val['value'] == "Over 2.5": outcomes.append({"name": "Over", "price": float(val['odd']), "point": "2.5"})
                                    elif val['value'] == "Under 2.5": outcomes.append({"name": "Under", "price": float(val['odd']), "point": "2.5"})
                                if outcomes:
                                    bookie_data['markets'].append({"key": "totals", "outcomes": outcomes})
                                    
                    if bookie_data['markets']:
                        game['bookmakers'].append(bookie_data)
                        await process_match_odds(conn, game, redis_client)
                        
            if data:
                logger.info(f"✅ Fallback API-Football concluído com sucesso para {sport_key}.")
        elif resp.status_code in [403, 429]:
            af_pool.rotate_key()
    except Exception as e:
        logger.error(f"❌ Erro no fallback API-Football para {sport_key}: {e}")

async def fetch_league_markets(client, redis_client, sport_key):
    url = f"{BASE_URL}/{sport_key}/odds"
    
    # OTIMIZAÇÃO S-TIER: Limita a busca apenas às próximas 48 horas (Economiza ~80% da cota)
    now_utc = datetime.now(timezone.utc)
    from_time = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    to_time = (now_utc + timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    params = {
        "regions": "eu,uk,us",
        "markets": "h2h,totals,spreads,btts,h2h_halftime",
        "bookmakers": TARGET_BOOKMAKERS,
        "oddsFormat": "decimal",
        "commenceTimeFrom": from_time,
        "commenceTimeTo": to_time
    }

    async with semaphore:
        games = await _make_request(client, url, params)
        if not games:
            logger.warning(f"⚠️ The Odds API indisponível para {sport_key}. Acionando Fallback da API-Football...")
            await fetch_fallback_api_football(client, redis_client, sport_key)
            return
        
        async with db.pool.acquire() as conn:
            for game in games:
                await process_match_odds(conn, game, redis_client)
                
        logger.info(f"✅ {sport_key}: Matriz de Cotações (48h) atualizada.")

def calculate_adaptive_sleep():
    # OTIMIZAÇÃO MÁXIMA: Roda exatamente a cada 12 horas (43200 segundos), operando apenas 2x ao dia.
    return 43200

async def run_quant_ingestion_loop():
    redis_client = await redis.from_url(REDIS_URL)
    
    logger.info("🧠 Carregando Motor NLP de Resolução de Entidades...")
    await db.connect()
    await entity_resolver.load_mappings_from_db()
    
    logger.info("🚀 BetGenius Quant Ingestion Ativado.")
    logger.info(f"Monitorando Elite (T1): {len(TIERED_LEAGUES[1])} | Periféricas (T2): {len(TIERED_LEAGUES[2])}")

    limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
    
    cycle_count = 0
    
    async with httpx.AsyncClient(limits=limits) as client:
        while True:
            start_time = datetime.now()
            current_quota = key_pool.get_global_quota()
            
            target_leagues = TIERED_LEAGUES[1].copy()
            tier_msg = "Apenas Tier 1"
            
            if cycle_count % 6 == 0:
                target_leagues.extend(TIERED_LEAGUES[2])
                tier_msg = "Tier 1 + Tier 2 (Varredura Ampla)"
                
            logger.info(f"--- INICIANDO CICLO {cycle_count} [{tier_msg}] | QUOTA THE ODDS API: {current_quota} ---")
            
            tasks = [fetch_league_markets(client, redis_client, league) for league in target_leagues]
            await asyncio.gather(*tasks)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            sleep_time = calculate_adaptive_sleep()
            
            logger.info(f"🏁 Ciclo concluído em {elapsed:.2f}s")
            logger.info(f"⏳ Cota Restante: {key_pool.get_global_quota()}. Suspendendo por {sleep_time/3600:.1f} horas.\n")
            
            cycle_count += 1
            await asyncio.sleep(sleep_time)

if __name__ == "__main__":
    try:
        asyncio.run(run_quant_ingestion_loop())
    except KeyboardInterrupt:
        logger.info("🛑 Desligamento manual do Ingestion Worker.")
    except Exception as e:
        logger.critical(f"Falha fatal no Loop de Ingestão: {e}")