# betgenius-backend/workers/odds_sniper.py
import asyncio
import aiohttp
import asyncpg
import redis.asyncio as redis
import os
import json
import base64
import logging
from datetime import datetime
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [HFT-SNIPER] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class PinnacleOddsSniper:
    """
    Robô HFT de Nível Institucional.
    Monitora a API da Pinnacle a cada 5 segundos. Mantém um cache em memória das Odds.
    Se a Odd de fechamento (Closing Line) despencar além do limite, acusa 'Smart Money'
    e dispara o evento direto para a tela do Gestor via Redis.
    """
    
    def __init__(self):
        # Limite Quantitativo: Se a odd cair mais de 8% em segundos, é dinheiro institucional.
        self.DROP_THRESHOLD_PCT = 0.08 
        
        # Conexões
        self.db_pool = None
        self.redis_client = None
        
        # Cache em memória ultrarrápido: { event_id_selection: last_odd }
        self.odds_memory_cache = {}
        self.fixtures_cache = {} # Para traduzir IDs em Nomes de Times (Ex: 12345 -> Arsenal x Liverpool)

        # Autenticação Oficial Pinnacle API v1
        client_id = os.getenv("PINNACLE_CLIENT_ID", "YOUR_CLIENT_ID")
        password = os.getenv("PINNACLE_PASSWORD", "YOUR_PASSWORD")
        credentials = f"{client_id}:{password}"
        self.auth_token = base64.b64encode(credentials.encode()).decode('utf-8')
        
        self.headers = {
            "Authorization": f"Basic {self.auth_token}",
            "Accept": "application/json"
        }
        # Esporte 29 = Futebol (Soccer)
        self.api_odds_url = "https://api.pinnacle.com/v1/odds?sportId=29"
        self.api_fixtures_url = "https://api.pinnacle.com/v1/fixtures?sportId=29"

    async def connect_infrastructure(self):
        """Estabelece as pontes TCP com o Banco e o Message Broker."""
        db_url = os.getenv("DATABASE_URL")
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        self.db_pool = await asyncpg.create_pool(db_url)
        self.redis_client = await redis.from_url(redis_url)
        logger.info("⚡ Infraestrutura Conectada: PostgreSQL (Neon) & Redis Pub/Sub Prontos.")

    async def update_fixtures_cache(self, session):
        """Baixa o calendário para sabermos quem está jogando (ID -> Nome)."""
        try:
            async with session.get(self.api_fixtures_url, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    for league in data.get("league", []):
                        for event in league.get("events", []):
                            evt_id = event["id"]
                            home = event["home"]
                            away = event["away"]
                            self.fixtures_cache[evt_id] = f"{home} x {away}"
        except Exception as e:
            logger.error(f"Erro ao mapear Fixtures: {e}")

    async def process_odds_delta(self, session):
        """O Coração do Algoritmo. Varre o livro de ofertas buscando anomalias."""
        try:
            async with session.get(self.api_odds_url, headers=self.headers) as response:
                if response.status != 200:
                    logger.warning(f"Pinnacle API Rate Limit ou Auth Error: {response.status}")
                    return

                data = await response.json()
                
                # Para evitar bloquear a Thread Principal, processamos rápido
                for league in data.get("leagues", []):
                    for event in league.get("events", []):
                        evt_id = event["id"]
                        
                        # Extrai o Mercado Match Odds (Period 0 = Jogo Completo)
                        periods = event.get("periods", [])
                        if not periods: continue
                        
                        match_odds = periods[0].get("moneyline")
                        if not match_odds: continue
                        
                        # Monitora a Odd do Mandante
                        await self._check_edge(evt_id, "Match Odds", "Casa", match_odds.get("home"))
                        # Monitora a Odd do Visitante
                        await self._check_edge(evt_id, "Match Odds", "Fora", match_odds.get("away"))

        except asyncio.TimeoutError:
            logger.warning("Pinnacle API Timeout.")
        except Exception as e:
            logger.error(f"Falha Crítica no Processamento de Odds: {e}")

    async def _check_edge(self, event_id, market, selection, current_odd):
        """Verifica a diferença (Delta) entre a odd passada e a atual."""
        if current_odd is None or current_odd <= 1.0: return
        
        cache_key = f"{event_id}_{market}_{selection}"
        old_odd = self.odds_memory_cache.get(cache_key)

        if old_odd is None:
            # Primeira vez vendo essa linha, apenas registra no cache
            self.odds_memory_cache[cache_key] = current_odd
            return

        # Calcula o Drop
        if current_odd < old_odd:
            drop_pct = (old_odd - current_odd) / old_odd
            
            # Se a queda for gigante, o Sindicato entrou no mercado.
            if drop_pct >= self.DROP_THRESHOLD_PCT:
                jogo_nome = self.fixtures_cache.get(event_id, f"Event {event_id}")
                time_foco = jogo_nome.split(' x ')[0] if selection == "Casa" else jogo_nome.split(' x ')[1]
                
                logger.warning(f"🚨 STEAMER DETECTADO: {jogo_nome} | {selection} caiu de {old_odd} para {current_odd} (-{drop_pct:.1%})")
                
                # 1. Salva no Banco de Dados para Histórico
                await self._save_to_db(event_id, jogo_nome, market, selection, old_odd, current_odd, drop_pct)
                
                # 2. Dispara pro Vue.js via Redis (A tela pisca na hora)
                await self._broadcast_to_frontend(jogo_nome, time_foco, old_odd, current_odd, drop_pct)
        
        # Atualiza a memória com a nova odd
        self.odds_memory_cache[cache_key] = current_odd

    async def _save_to_db(self, evt_id, jogo, mercado, selecao, old, current, drop_pct):
        urgency = "HIGH_URGENCY" if drop_pct > 0.12 else "MEDIUM"
        query = """
            INSERT INTO core.hft_odds_drops 
            (event_id, jogo, mercado, selecao, odd_abertura, odd_atual, drop_pct, volume_status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(query, str(evt_id), jogo, mercado, selecao, old, current, round(drop_pct*100, 2), urgency)
        except Exception as e:
            logger.error(f"Erro DB: {e}")

    async def _broadcast_to_frontend(self, jogo, time_foco, old_odd, current_odd, drop_pct):
        """Molda o JSON exatamente como o Vue.js (ViewSentiment) espera receber no socket."""
        
        # 1. Alerta de Notícia / Radar
        payload_news = {
            "tipo": "odd_drop",
            "data": {
                "time": time_foco,
                "tempo": "Agora",
                "tipo": "odd",
                "texto": f"Odd {time_foco} despencou de {old_odd} para {current_odd} (-{drop_pct:.1%})",
                "fonte": "Pinnacle HFT",
                "confianca": 98 if drop_pct > 0.10 else 85
            }
        }

        # 2. Alerta de Smart Money Flow (Preenchendo o Gráfico de Barras do Vue)
        # Se a odd despencou, o Smart Money (volume) está esmagando esse lado
        is_home = time_foco in jogo.split(' x ')[0]
        payload_money = {
            "tipo": "money_flow",
            "data": {
                "jogo": jogo,
                "mercado": f"Moneyline ({time_foco})",
                # O Público joga nos dois lados. Os Sharps jogam massivamente onde a odd caiu.
                "ticketCasa": 50 if is_home else 30,
                "ticketEmpate": 20,
                "ticketFora": 30 if is_home else 50,
                "moneyCasa": 85 if is_home else 10,
                "moneyEmpate": 5,
                "moneyFora": 10 if is_home else 85,
                "edge": 1 # 1 = Smart Action (Verde no Vue)
            }
        }

        # Publica na veia espinhal (O Node.js está escutando esse canal)
        await self.redis_client.publish('betgenius:stream:sentiment_alerts', json.dumps(payload_news))
        await self.redis_client.publish('betgenius:stream:sentiment_alerts', json.dumps(payload_money))

    async def run(self):
        await self.connect_infrastructure()
        
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            logger.info("📡 Baixando Tabela de Fixtures Inicial...")
            await self.update_fixtures_cache(session)
            
            logger.info("🎯 HFT Sniper Ativado. Patrulhando o Livro de Ofertas Pinnacle a cada 8 segundos...")
            while True:
                await self.process_odds_delta(session)
                
                # Delay de 8s para não tomar ban por Rate Limit da Pinnacle.
                # Sindicatos compram uma linha dedicada da Pinnacle para HFT de 1s, 
                # mas na API B2B normal, 8s é o limite seguro.
                await asyncio.sleep(8) 

if __name__ == "__main__":
    sniper = PinnacleOddsSniper()
    try:
        asyncio.run(sniper.run())
    except KeyboardInterrupt:
        logger.info("Sniper desligado com sucesso.")