# betgenius-backend/workers/api_integrations/theodds_watcher.py
import sys
import os
import io

# 1. FIX DEFINITIVO DE UNICODE PARA WINDOWS
if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except AttributeError:
        pass

import asyncio
import logging
import httpx
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.database import db
from engine.entity_resolution import entity_resolver
from workers.fbref.config.fbref_map import LEAGUE_CONFIG

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [LIQUIDITY-SNIPER] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class KeyLoadBalancer:
    """Motor de Rotação de Chaves para Evasão de Rate Limits."""
    def __init__(self):
        pool_str = os.getenv("ODDS_API_KEY_POOL", "")
        if not pool_str:
            logger.critical("ODDS_API_KEY_POOL não encontrado no .env!")
            sys.exit(1)
        
        self.keys = [k.strip() for k in pool_str.split(",") if k.strip()]
        self.current_index = 0
        logger.info(f"🔑 Load Balancer armado com {len(self.keys)} munições (Chaves API).")

    def get_key(self) -> str:
        return self.keys[self.current_index]

    def rotate(self):
        self.current_index = (self.current_index + 1) % len(self.keys)
        logger.warning(f"🔄 Cartucho vazio. Rotacionando para chave de API oculta...")


class TheOddsWatcher:
    """
    Sniper de Liquidez S-Tier (A Malandragem Institucional).
    Compara a Pinnacle (Sharp) com a Bet365 (Soft) nas próximas 48h.
    Detecta atrasos de mercado e quedas bruscas de Smart Money.
    """
    def __init__(self):
        self.balancer = KeyLoadBalancer()
        self.base_url = "https://api.the-odds-api.com/v4/sports"
        
        # O SEGREDO: Buscamos a casa Afiada (Pinnacle) e a nossa casa alvo (Bet365)
        self.bookmakers = "pinnacle,bet365" 
        
        # Mercados de alta liquidez e Player Props
        self.markets = "h2h,totals,spreads,player_goal_scorer" 
        
        self.drop_threshold = 0.05 # Queda de 5% = Steam Move
        self.sharp_edge_threshold = 1.04 # Se a Bet365 pagar 4% a mais que a Pinnacle, disparamos alerta

    async def _ensure_schema(self, conn):
        await conn.execute("""
            ALTER TABLE core.market_odds 
            ADD COLUMN IF NOT EXISTS opening_odd DECIMAL(5,2),
            ADD COLUMN IF NOT EXISTS heavy_drop_alert BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS sharp_edge_alert BOOLEAN DEFAULT FALSE;
        """)

    async def fetch_odds_for_league(self, sport_key: str, client: httpx.AsyncClient):
        """Busca odds apenas para jogos nas próximas 48 horas para não queimar cota com jogos mortos."""
        url = f"{self.base_url}/{sport_key}/odds/"
        
        now = datetime.now(timezone.utc)
        # Formato exigido pela TheOdds API: YYYY-MM-DDTHH:MM:SSZ
        time_from = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        time_to = (now + timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        for attempt in range(len(self.balancer.keys)):
            params = {
                "apiKey": self.balancer.get_key(),
                "regions": "eu,uk", 
                "markets": self.markets,
                "bookmakers": self.bookmakers,
                "oddsFormat": "decimal",
                "commenceTimeFrom": time_from,
                "commenceTimeTo": time_to
            }
            
            try:
                response = await client.get(url, params=params, timeout=15.0)
                
                if response.status_code == 200:
                    return response.json()
                    
                elif response.status_code in [401, 429]: 
                    logger.warning(f"⚠️ Rate Limit atingido ({response.status_code}). Puxando nova chave...")
                    self.balancer.rotate()
                    continue
                else:
                    logger.error(f"Erro da API {response.status_code}: {response.text}")
                    return None
                    
            except Exception as e:
                logger.error(f"Timeout na TheOddsAPI em {sport_key}: {e}")
                return None
                
        return None

    def _extract_market_outcomes(self, bookmakers_data: list, target_bookie: str, market_key: str):
        """Busca um mercado específico de uma casa específica dentro do JSON complexo."""
        for b in bookmakers_data:
            if b.get("key") == target_bookie:
                for m in b.get("markets", []):
                    if m.get("key") == market_key:
                        return m.get("outcomes", [])
        return []

    async def process_match_odds(self, match_data: dict, sport_key: str, conn):
        raw_home = match_data.get("home_team")
        raw_away = match_data.get("away_team")
        
        home_canonical = await entity_resolver.normalize_name(raw_home, is_pinnacle=False)
        away_canonical = await entity_resolver.normalize_name(raw_away, is_pinnacle=False)
        
        match_id = await conn.fetchval("""
            SELECT m.id FROM core.matches_history m
            JOIN core.teams th ON m.home_team_id = th.id
            JOIN core.teams ta ON m.away_team_id = ta.id
            WHERE th.canonical_name = $1 AND ta.canonical_name = $2
            AND m.status = 'SCHEDULED'
        """, home_canonical, away_canonical)
        
        if not match_id: return

        bookies = match_data.get("bookmakers", [])
        if not bookies: return
        
        # A Mágica Acontece Aqui: Analisamos mercado por mercado
        for market_key in self.markets.split(','):
            pin_outcomes = self._extract_market_outcomes(bookies, "pinnacle", market_key)
            b365_outcomes = self._extract_market_outcomes(bookies, "bet365", market_key)
            
            # Precisamos das odds da Bet365 para operar, a Pinnacle é apenas nosso "Oráculo"
            for b365_out in b365_outcomes:
                nome_mercado = b365_out.get("name")
                if market_key == "totals":
                    nome_mercado = f"O/U {b365_out.get('point')} - {b365_out.get('name')}"
                elif market_key == "spreads":
                    nome_mercado = f"AH {b365_out.get('point')} {b365_out.get('name')}"
                elif market_key == "player_goal_scorer":
                    nome_mercado = f"Marcador: {b365_out.get('description')} - {b365_out.get('name')}"

                new_b365_price = float(b365_out.get("price", 0.0))
                if new_b365_price <= 1.0: continue

                # 1. Busca o preço paralelo da Pinnacle para identificar se a Bet365 está "atrasada"
                sharp_price = 0.0
                for pin_out in pin_outcomes:
                    # Checagem complexa de nome/ponto para casar os mercados entre as casas
                    if pin_out.get("name") == b365_out.get("name") and pin_out.get("point") == b365_out.get("point") and pin_out.get("description") == b365_out.get("description"):
                        sharp_price = float(pin_out.get("price", 0.0))
                        break

                sharp_edge = False
                # A Bet365 está pagando significativamente melhor que a Pinnacle? (Alpha puro)
                if sharp_price > 1.0 and new_b365_price > (sharp_price * self.sharp_edge_threshold):
                    sharp_edge = True
                    logger.info(f"💎 SHARP EDGE (ERRO DE CASA)! {home_canonical} vs {away_canonical} | {nome_mercado} | B365: {new_b365_price} | PIN: {sharp_price}")

                # 2. Busca o estado histórico na nossa base (Para detectar Drops de Smart Money)
                odd_record = await conn.fetchrow("""
                    SELECT id, current_odd, opening_odd 
                    FROM core.market_odds 
                    WHERE match_id = $1 AND categoria = $2 AND nome_mercado = $3 AND bookmaker = 'bet365'
                """, match_id, market_key, nome_mercado)

                heavy_drop = False
                opening_odd = new_b365_price

                if odd_record:
                    old_price = float(odd_record['current_odd'])
                    opening_odd = float(odd_record['opening_odd']) if odd_record['opening_odd'] else old_price
                    
                    if old_price > 0 and ((old_price - new_b365_price) / old_price) >= self.drop_threshold:
                        heavy_drop = True
                        logger.info(f"📉 STEAM MOVE (QUEDA LIVRE)! {home_canonical} vs {away_canonical} | {nome_mercado}: {old_price} -> {new_b365_price}")

                    await conn.execute("""
                        UPDATE core.market_odds 
                        SET current_odd = $1, heavy_drop_alert = $2, sharp_edge_alert = $3, updated_at = NOW()
                        WHERE id = $4
                    """, new_b365_price, heavy_drop, sharp_edge, odd_record['id'])
                else:
                    await conn.execute("""
                        INSERT INTO core.market_odds 
                        (match_id, categoria, nome_mercado, bookmaker, current_odd, opening_odd, heavy_drop_alert, sharp_edge_alert)
                        VALUES ($1, $2, $3, 'bet365', $4, $5, $6, $7)
                    """, match_id, market_key, nome_mercado, new_b365_price, opening_odd, heavy_drop, sharp_edge)

    async def run_watcher(self):
        logger.info("=== INICIANDO SNIPER DE LIQUIDEZ (PINNACLE vs BET365) ===")
        await db.connect()
        await entity_resolver.load_mappings_from_db()
        
        async with db.pool.acquire() as conn:
            await self._ensure_schema(conn)
        
        async with httpx.AsyncClient() as client:
            for sport_key in LEAGUE_CONFIG.keys():
                logger.info(f"Rastreando Anomalias em: {sport_key} (Próximas 48h)...")
                league_odds = await self.fetch_odds_for_league(sport_key, client)
                
                if not league_odds: continue
                    
                async with db.pool.acquire() as conn:
                    async with conn.transaction():
                        for match_data in league_odds:
                            await self.process_match_odds(match_data, sport_key, conn)
                
                await asyncio.sleep(1.5)

        await db.disconnect()
        logger.info("=== VARREDURA DE ANOMALIAS CONCLUÍDA ===")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(TheOddsWatcher().run_watcher())