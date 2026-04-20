import json
import logging
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# =====================================================================
# BETGENIUS HFT - REDIS LIVE STATE MANAGER (ETAPA 1.3)
# Responsável por controle de estado em RAM (Deltas) e Pub/Sub
# =====================================================================

class RedisStateManager:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.odds_ttl = 180   # 3 minutos para Match Odds
        self.props_ttl = 300  # 5 minutos para Player Props

    async def update_live_odds(self, sport_key: str, game_id: str, new_payload: dict):
        """
        Injeta odds macro na memória, verificando se houve mudança real (Delta).
        """
        redis_key = f"betgenius:live_odds:{sport_key}:{game_id}"
        
        # 1. Puxa o estado do milissegundo passado
        old_state_str = await self.redis.get(redis_key)
        
        if old_state_str:
            old_state = json.loads(old_state_str)
            
            # 2. DETECÇÃO DE DELTA (Omitimos I/O desnecessário se nada mudou)
            if self._has_market_changed(old_state, new_payload):
                # Substitui a velha pela nova na RAM
                await self.redis.set(redis_key, json.dumps(new_payload), ex=self.odds_ttl)
                
                # 3. PUB/SUB: Avisa o ecossistema que houve movimento na linha!
                # O Node.js escutará este canal na Missão 3.
                event_message = json.dumps({"event": "ODDS_UPDATED", "game_id": game_id, "sport": sport_key})
                await self.redis.publish("betgenius:stream:market_updates", event_message)
                
        else:
            # É a primeira vez que vemos este jogo no radar. Salva direto.
            await self.redis.set(redis_key, json.dumps(new_payload), ex=self.odds_ttl)
            
            event_message = json.dumps({"event": "NEW_MATCH_DETECTED", "game_id": game_id, "sport": sport_key})
            await self.redis.publish("betgenius:stream:market_updates", event_message)

    async def update_live_props(self, sport_key: str, event_id: str, new_payload: dict):
        """
        Injeta Player Props na memória RAM.
        """
        redis_key = f"betgenius:live_props:{sport_key}:{event_id}"
        await self.redis.set(redis_key, json.dumps(new_payload), ex=self.props_ttl)
        
        # Publica evento específico de Props
        event_message = json.dumps({"event": "PROPS_UPDATED", "game_id": event_id})
        await self.redis.publish("betgenius:stream:props_updates", event_message)

    def _has_market_changed(self, old_state: dict, new_state: dict) -> bool:
        """
        Compara o Payload antigo com o novo.
        (Nesta etapa inicial, comparamos a data de atualização dos bookmakers.
        Na Missão 2, injetaremos a matemática aqui para detectar o Drop de 5%).
        """
        # Extrai os timestamps da Pinnacle e Bet365 do payload complexo da The Odds API
        old_books = {b['key']: b['last_update'] for b in old_state.get('bookmakers', [])}
        new_books = {b['key']: b['last_update'] for b in new_state.get('bookmakers', [])}
        
        # Se a data de atualização de alguma casa mudou, a odd se moveu.
        return old_books != new_books