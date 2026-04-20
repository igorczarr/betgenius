# betgenius-backend/engine/market_scanner.py
import asyncio
import json
import logging
import redis.asyncio as redis
import sys
from pathlib import Path
from datetime import datetime

# Importa o módulo central e o motor matemático de precisão
sys.path.append(str(Path(__file__).parent.parent))
from core.config import settings
from engine.math_models import pricer

# =====================================================================
# BETGENIUS HFT - VALUE SCANNER & OPPORTUNITY GENERATOR (NÍVEL S)
# Arquitetura Event-Driven (Pub/Sub) para latência de microssegundos
# =====================================================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s [EV-SCANNER] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

REDIS_URL = settings.REDIS_URL
MIN_EV_THRESHOLD = 2.0  # Só aceitamos operações com >= 2% de EV

class HFTEventScanner:
    def __init__(self):
        self.redis = None
        self.pubsub = None

    async def connect(self):
        """Estabelece conexão com o Redis e prepara o canal de escuta."""
        self.redis = await redis.from_url(REDIS_URL)
        self.pubsub = self.redis.pubsub()
        # Inscreve-se no canal exato onde o StateManager da Etapa 1.3 grita
        await self.pubsub.subscribe("betgenius:stream:market_updates")
        logger.info("📡 HFT Scanner conectado. Aguardando gatilhos via Pub/Sub...")

    def _extract_market_data(self, bookmakers: list, target_bookie: str, market_key: str = 'h2h') -> tuple:
        """
        O(N) Otimizado: Extrai as odds e as labels em uma única passagem pelo JSON.
        Evita os múltiplos loops aninhados do código antigo.
        """
        for b in bookmakers:
            if b['key'] == target_bookie:
                for m in b.get('markets', []):
                    if m['key'] == market_key:
                        odds = [outcome['price'] for outcome in m['outcomes']]
                        labels = [outcome['name'] for outcome in m['outcomes']]
                        return odds, labels
        return None, None

    async def process_event(self, sport: str, game_id: str):
        """
        Engatilha o Motor Matemático APENAS para o jogo que sofreu alteração.
        """
        redis_key = f"betgenius:live_odds:{sport}:{game_id}"
        payload_str = await self.redis.get(redis_key)
        
        if not payload_str:
            return

        try:
            data = json.loads(payload_str)
            bookmakers = data.get('bookmakers', [])
            
            # Extração Otimizada
            pin_odds, labels = self._extract_market_data(bookmakers, 'pinnacle', 'h2h')
            bet365_odds, _ = self._extract_market_data(bookmakers, 'bet365', 'h2h')

            if not pin_odds or not bet365_odds or not labels:
                return # Falta liquidez em uma das pontas

            # 1. MOTOR MATEMÁTICO: O Padrão Ouro (Power Method)
            pricing = pricer.remove_vig_power_method(pin_odds)
            if not pricing: 
                return

            opportunities = []
            
            # 2. CAÇA À ANOMALIA: Percorre cada seleção (Home, Draw, Away)
            for i in range(len(labels)):
                target_prob = pricing.true_probs[i]
                fair_odd = pricing.fair_odds[i]
                soft_odd = bet365_odds[i]
                selection_name = labels[i]

                # Invoca o Avaliador de Oportunidades com Tipagem Estrita
                opp_result = pricer.evaluate_opportunity(target_prob, soft_odd)
                
                if opp_result.is_value and opp_result.expected_value >= MIN_EV_THRESHOLD:
                    
                    # Formata o Payload EXATAMENTE como o Vue.js Front-End espera
                    opp = {
                        "hora": datetime.now().strftime("%H:%M:%S"),
                        "jogo": f"{data['home_team']} x {data['away_team']}",
                        "mercado": f"Vencedor: {selection_name}",
                        "pinOpen": "N/A", # Será injetado pelo tracker de histórico futuro
                        "pinClose": round(pin_odds[i], 2),
                        "trueOdd": round(fair_odd, 2),
                        "softOdd": round(soft_odd, 2),
                        "bookie": "Bet365",
                        "ev": round(opp_result.expected_value, 2),
                        "kelly": round(opp_result.kelly_stake_pct, 2),
                        "sport": sport
                    }
                    opportunities.append(opp)

            # 3. DISPARO DO ALERTA (Grita para o Front-End Node.js)
            for opp in opportunities:
                logger.info(f"🔥 ALPHA: {opp['jogo']} | {opp['mercado']} | +{opp['ev']}% EV | Fair: {opp['trueOdd']} vs B365: {opp['softOdd']}")
                
                # Salva o estado da oportunidade para exibição rápida no painel
                safe_label = labels[i].replace(' ','_')
                opp_key = f"betgenius:opportunities:{game_id}_{safe_label}"
                await self.redis.set(opp_key, json.dumps(opp), ex=180) # TTL de 3 min
                
                # Publica no canal que o Gateway Node.js vai escutar
                await self.redis.publish("betgenius:stream:opportunities", json.dumps(opp))

        except Exception as e:
            logger.error(f"Erro na varredura quantitativa do jogo {game_id}: {e}")

    async def start_daemon(self):
        """
        O Loop de Escuta (Listen Loop).
        Não bloqueia CPU. Aguarda passivamente mensagens do Redis.
        """
        await self.connect()
        
        async for message in self.pubsub.listen():
            if message['type'] == 'message':
                try:
                    # Desempacota a mensagem do State Manager (Etapa 1.3)
                    event_data = json.loads(message['data'])
                    game_id = event_data.get("game_id")
                    sport = event_data.get("sport")
                    
                    # Se for um evento de atualização de odds, joga para o Scanner analisar
                    if event_data.get("event") in ["ODDS_UPDATED", "NEW_MATCH_DETECTED"]:
                        # Cria uma Task não-bloqueante para analisar este jogo em microssegundos
                        asyncio.create_task(self.process_event(sport, game_id))
                        
                except Exception as e:
                    logger.error(f"Erro ao processar mensagem do Pub/Sub: {e}")

if __name__ == "__main__":
    scanner = HFTEventScanner()
    try:
        asyncio.run(scanner.start_daemon())
    except KeyboardInterrupt:
        logger.info("🛑 Scanner HFT desligado.")