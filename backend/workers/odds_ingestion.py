# betgenius-backend/workers/odds_ingestion.py
import asyncio
import httpx
import redis.asyncio as redis
import json
import logging
from datetime import datetime, timezone
import sys
from pathlib import Path

# Importa o módulo central de segurança
sys.path.append(str(Path(__file__).parent.parent))
from core.config import settings
from engine.entity_resolution import entity_resolver
from core.state_manager import RedisStateManager

# =====================================================================
# BETGENIUS HFT INGESTION WORKER - DISTRIBUTED KEY POOLING (NÍVEL S)
# Extração Institucional com Gestão Assimétrica de Cotas e Exchanges
# =====================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [QUANT-WORKER] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

REDIS_URL = settings.REDIS_URL
BASE_URL = "https://api.the-odds-api.com/v4/sports"

# A Malandragem S-Tier: Sharp (Pinnacle) + Soft (Bet365) + P2P Exchange (Betfair)
TARGET_BOOKMAKERS = "pinnacle,bet365,betfair_ex_eu" 

# =====================================================================
# O CÉREBRO DE ROTAÇÃO DE CHAVES (LOAD BALANCER 2.0)
# =====================================================================
class APILoadBalancer:
    def __init__(self, keys: list):
        if not keys:
            raise ValueError("CRÍTICO: Nenhuma chave de API encontrada no pool!")
        self.keys = keys
        self.total_keys = len(keys)
        self.current_idx = 0
        self.quotas = {k: 500 for k in keys} # Potencial inicial assumido
        self.dead_keys = set()
        logger.info(f"🛡️ Load Balancer Ativado: {self.total_keys} chaves. Potencial: {self.get_global_quota()} reqs.")

    def get_active_key(self) -> str:
        # Se todas as chaves morreram, o sistema entra em modo de hibernação forçada
        if len(self.dead_keys) == self.total_keys:
            raise SystemError("💀 TODAS AS CHAVES ESTÃO MORTAS/ESGOTADAS. Intervenção manual necessária.")
        return self.keys[self.current_idx]

    def update_quota(self, key: str, remaining: int):
        self.quotas[key] = remaining
        # Margem de segurança de 10 requisições
        if remaining <= 10 and key not in self.dead_keys:
            logger.warning(f"⚠️ Chave esgotada ({remaining} restantes). Retirando do pool ativo.")
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

key_pool = APILoadBalancer(settings.ODDS_API_KEY_POOL)

# =====================================================================
# CURADORIA DE LIGAS (O ARSENAL DE WALL STREET)
# =====================================================================
LEAGUES_TIER_1 = [
    "soccer_epl", "soccer_spain_la_liga", "soccer_italy_serie_a", 
    "soccer_germany_bundesliga", "soccer_uefa_champs_league"
]
LEAGUES_TIER_2 = [
    "soccer_france_ligue_one", "soccer_netherlands_eredivisie",
    "soccer_portugal_primeira_liga", "soccer_brazil_campeonato",
    "soccer_usa_mls"
]
LEAGUES_TIER_3 = [
    "soccer_brazil_serie_b", "soccer_sweden_allsvenskan",
    "soccer_norway_eliteserien", "soccer_denmark_superliga",
    "soccer_japan_j_league"
]

# NOVO: Pacote Institucional Internacional (Preparação Copa do Mundo)
LEAGUES_INTL = [
    "soccer_fifa_world_cup", 
    "soccer_conmebol_copa_america",
    "soccer_uefa_euro_qualifications",
    "soccer_uefa_nations_league"
]

ALL_LEAGUES = LEAGUES_TIER_1 + LEAGUES_TIER_2 + LEAGUES_TIER_3 + LEAGUES_INTL

# Maximiza chamadas sem acionar as defesas anti-DDoS da API (Rate limit costuma ser 10/sec)
semaphore = asyncio.Semaphore(5) 

# =====================================================================
# TÚNEL BLINDADO (COM EXPONENTIAL BACKOFF)
# =====================================================================
async def _make_request(client: httpx.AsyncClient, url: str, params: dict, max_retries=3):
    backoff_time = 2.0
    
    for attempt in range(max_retries):
        current_key = key_pool.get_active_key()
        params["apiKey"] = current_key
        
        try:
            # timeout mais agressivo para não prender o pipeline
            response = await client.get(url, params=params, timeout=12.0)
            
            if response.status_code == 200:
                remaining = int(response.headers.get('x-requests-remaining', 0))
                key_pool.update_quota(current_key, remaining)
                return response.json()
                
            elif response.status_code == 429: # Too Many Requests
                logger.warning(f"⚠️ Rate Limit (429). Pausa tática de {backoff_time}s...")
                await asyncio.sleep(backoff_time)
                backoff_time *= 2 # Exponential Backoff (Malandragem S-Tier)
                key_pool.rotate_key(reason="Evadindo bloqueio por Rate Limit")
                continue
                
            elif response.status_code == 401: # Unauthorized/Esgotada
                logger.error(f"❌ Chave rejeitada (401). Queimando chave do pool.")
                key_pool.update_quota(current_key, 0)
                continue
                
            elif response.status_code == 404: # Esporte não existente no momento
                # Silencia o log de erro para ligas que estão fora de temporada (ex: Copa do Mundo fora de época)
                logger.debug(f"Liga inativa ou fora de temporada: {url}")
                return None
                
            else:
                logger.error(f"HTTP {response.status_code}: {response.text}")
                return None
                
        except httpx.RequestError as e:
            logger.error(f"Falha de Rede no alvo {url}: {e}")
            await asyncio.sleep(backoff_time)
            
    return None

# =====================================================================
# OS WORKERS DE ALTA EFICIÊNCIA
# =====================================================================
async def fetch_player_props(client, redis_client, sport_key, event_id, match_name):
    """
    NARROWBAND SNIPER: Extremamente caro em cota. Só acionado momentos antes do jogo.
    """
    if key_pool.get_global_quota() < 300:
        return # Economiza cota vital
        
    prop_markets = "player_goal_scorer,player_shots_on_target" # Reduzido para focar no mais líquido
    url = f"{BASE_URL}/{sport_key}/events/{event_id}/odds"
    params = {
        "regions": "eu,uk",
        "markets": prop_markets,
        "bookmakers": TARGET_BOOKMAKERS,
        "oddsFormat": "decimal"
    }

    async with semaphore:
        event_data = await _make_request(client, url, params)
        if event_data:
            state_manager = RedisStateManager(redis_client)
            await state_manager.update_live_props(sport_key, event_id, event_data)
            logger.info(f"🎯 Props Extraídos: {match_name}")

async def fetch_league_markets(client, redis_client, sport_key, tier):
    """
    BROADBAND SCANNER COM GESTÃO ASSIMÉTRICA DE CUSTOS
    """
    # A Sacada do Multiplicador: The Odds API cobra 1 crédito POR MERCADO.
    # Tiers 1 e Seleções ganham a varredura completa (3 créditos por chamada).
    # Tiers 2 e 3 buscam apenas H2H e Over/Under (2 créditos por chamada).
    if tier == 1 or sport_key in LEAGUES_INTL:
        markets = "h2h,spreads,totals"
    else:
        markets = "h2h,totals"
        
    url = f"{BASE_URL}/{sport_key}/odds"
    params = {
        "regions": "eu,uk",
        "markets": markets,
        "bookmakers": TARGET_BOOKMAKERS,
        "oddsFormat": "decimal"
    }

    async with semaphore:
        games = await _make_request(client, url, params)
        if not games: return
        
        valid_games_count = 0
        state_manager = RedisStateManager(redis_client)
        
        for game in games:
            game_id = game['id']
            
            # Normalização de nomes usando IA (A espinha dorsal de dados limpos)
            home_team_norm = await entity_resolver.normalize_name(game['home_team'], is_pinnacle=True)
            away_team_norm = await entity_resolver.normalize_name(game['away_team'], is_pinnacle=True)
            match_name = f"{home_team_norm} x {away_team_norm}"
            
            payload = {
                "id": game_id,
                "sport": sport_key,
                "tier": tier,
                "home_team": home_team_norm,
                "away_team": away_team_norm,
                "commence_time": game['commence_time'],
                "bookmakers": game['bookmakers'],
                "last_update": datetime.now(timezone.utc).isoformat()
            }
            
            # Persiste no Redis
            await state_manager.update_live_odds(sport_key, game_id, payload)
            valid_games_count += 1

            # Lógica JIT para Player Props (Apenas para Tiers de Elite e Seleções)
            try:
                game_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
                hours_to_kickoff = (game_time - datetime.now(timezone.utc)).total_seconds() / 3600
                
                # Só atira o Sniper se o jogo for de Elite e estiver a < 3 horas do início
                if (tier == 1 or sport_key in LEAGUES_INTL) and 0 < hours_to_kickoff <= 3.0:
                    asyncio.create_task(fetch_player_props(client, redis_client, sport_key, game_id, match_name))
            except Exception as e:
                pass
                
        if valid_games_count > 0:
            logger.info(f"✅ {sport_key}: {valid_games_count} jogos processados.")

# =====================================================================
# GESTÃO DE CADÊNCIA (ADAPTIVE SLEEP)
# =====================================================================
def calculate_adaptive_sleep():
    """
    Otimiza a janela de extração baseada na cota restante para não estourar no meio do mês.
    """
    total_quota = key_pool.get_global_quota()
    
    if total_quota > 5000: return 600   # 10 mins (Muito seguro)
    elif total_quota > 2000: return 1200  # 20 mins (Normal)
    elif total_quota > 500: return 3600   # 1 hora (Defensivo)
    else: return 14400 # 4 horas (Modo Sobrevivência)

# =====================================================================
# O MOTOR CENTRAL
# =====================================================================
async def run_quant_ingestion_loop():
    redis_client = await redis.from_url(REDIS_URL)
    
    logger.info("🧠 Carregando Motor NLP de Resolução de Entidades...")
    await entity_resolver.load_mappings_from_db()
    
    logger.info("🚀 BetGenius Quant Ingestion Ativado.")
    logger.info(f"Monitorando {len(ALL_LEAGUES)} Ligas (Incluindo Seleções Internacionais).")

    # Limits agressivos para suportar a malha de conexões sem estourar Sockets do SO
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
    
    async with httpx.AsyncClient(limits=limits) as client:
        while True:
            start_time = datetime.now()
            current_quota = key_pool.get_global_quota()
            logger.info(f"--- INICIANDO CICLO DE VARREDURA | QUOTA GLOBAL: {current_quota} ---")
            
            tasks = []
            
            # Para economizar cota, podemos desativar o Tier 3 em momentos de crise
            if current_quota > 1000:
                for league in LEAGUES_TIER_3: tasks.append(fetch_league_markets(client, redis_client, league, 3))
            
            for league in LEAGUES_TIER_2: tasks.append(fetch_league_markets(client, redis_client, league, 2))
            for league in LEAGUES_TIER_1: tasks.append(fetch_league_markets(client, redis_client, league, 1))
            for league in LEAGUES_INTL: tasks.append(fetch_league_markets(client, redis_client, league, 0)) # Tier 0 = Seleções
            
            # Roda todas as requisições em paralelo respeitando o semáforo
            await asyncio.gather(*tasks)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            sleep_time = calculate_adaptive_sleep()
            
            logger.info(f"🏁 Ciclo concluído em {elapsed:.2f}s")
            logger.info(f"⏳ Cota Restante: {key_pool.get_global_quota()}. Suspendendo por {sleep_time/60:.1f} minutos.\n")
            
            await asyncio.sleep(sleep_time)

if __name__ == "__main__":
    try:
        asyncio.run(run_quant_ingestion_loop())
    except KeyboardInterrupt:
        logger.info("🛑 Desligamento manual do Ingestion Worker.")
    except Exception as e:
        logger.critical(f"Falha fatal no Loop de Ingestão: {e}")