# betgenius-backend/engine/sentiment_engine.py
import asyncio
import json
import logging
import random
from datetime import datetime, timezone
import sys
from pathlib import Path

# Importações da Infraestrutura
sys.path.append(str(Path(__file__).parent.parent))
from core.database import db
from core.config import settings
import redis.asyncio as redis

logging.basicConfig(level=logging.INFO, format="%(asctime)s [NLP-ENGINE] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

# =====================================================================
# BETGENIUS HFT - NLP & SENTIMENT ENGINE (NÍVEL S)
# Rastreador de Hype, Lesões e Movimentos de Massa em Tempo Real
# =====================================================================

class SentimentAnalyzer:
    def __init__(self):
        self.redis = None
        self.keywords_injury = ['lesão', 'fora', 'desfalque', 'machucado', 'injury', 'out', 'misses']
        self.keywords_hype = ['amassou', 'destruiu', 'favoritaço', 'hype', 'unbeatable', 'invencível']
        self.keywords_trap = ['crise', 'demitido', 'tensão', 'briga', 'protesto']

    async def connect(self):
        self.redis = await redis.from_url(settings.REDIS_URL)
        await db.connect()
        logger.info("📡 NLP Engine conectado ao DB e ao Redis (Message Broker).")

    def _analyze_text(self, text: str) -> dict:
        """
        O CÉREBRO DA IA (Versão Algorítmica Leve):
        Analisa a string de notícia e categoriza o impacto.
        No futuro, podemos plugar a API da OpenAI/Gemini aqui.
        """
        text_lower = text.lower()
        
        # 1. Detecção de Tipo de Alerta
        alert_type = "noticia"
        if any(word in text_lower for word in self.keywords_injury):
            alert_type = "lesao"
        elif any(word in text_lower for word in self.keywords_trap):
            alert_type = "crise"

        # 2. Score de Sentimento (0 a 100) - Simulação baseada em palavras-chave
        # Em produção, usaríamos a biblioteca NLTK (VADER) ou LLM
        positive = random.randint(10, 40)
        negative = random.randint(10, 40)
        
        if alert_type == "lesao" or alert_type == "crise":
            negative += 40
        else:
            positive += 30
            
        neutral = 100 - (positive + negative)
        hype_score = positive + (neutral * 0.2) - (negative * 0.5)

        return {
            "alert_type": alert_type,
            "positive_pct": positive,
            "neutral_pct": neutral,
            "negative_pct": negative,
            "hype_score": max(0, min(100, int(hype_score))) # Trava entre 0 e 100
        }

    async def process_news_feed(self, team_name: str, news_text: str, source: str, confidence: float):
        """
        Ingere a notícia, passa pelo NLP, salva no PostgreSQL e dispara para o Vue.js.
        """
        # 1. Processamento de Linguagem Natural
        nlp_result = self._analyze_text(news_text)
        logger.info(f"🧠 NLP Processou: [{team_name}] - Score: {nlp_result['hype_score']} | Tipo: {nlp_result['alert_type']}")

        # 2. Tenta encontrar o ID do time no banco de dados para salvar corretamente
        team_id = None
        try:
            async with db.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT id FROM core.teams WHERE canonical_name = $1", team_name)
                if row:
                    team_id = row['id']
                    # Salva o alerta no Domínio de Mercado (PostgreSQL)
                    await conn.execute("""
                        INSERT INTO market.news_alerts 
                        (team_id, alert_type, content, source, confidence_pct, is_processed)
                        VALUES ($1, $2, $3, $4, $5, TRUE)
                    """, team_id, nlp_result['alert_type'], news_text, source, confidence)
        except Exception as e:
            logger.error(f"Erro ao salvar alerta no DB: {e}")

        # 3. Empacota o JSON no exato formato que o ViewRadar.vue espera
        payload = {
            "time": team_name,
            "tempo": "Agora",
            "tipo": nlp_result['alert_type'],
            "texto": news_text,
            "fonte": source,
            "confianca": confidence,
            # Dados extras para a aba de "Hype Index"
            "nlp_stats": {
                "score": nlp_result['hype_score'],
                "positive": nlp_result['positive_pct'],
                "neutral": nlp_result['neutral_pct'],
                "negative": nlp_result['negative_pct']
            }
        }

        # 4. PUBLICA NO REDIS (O Node.js vai escutar isso e jogar pro Front-End)
        # Usamos o canal genérico de oportunidades ou criamos um específico
        await self.redis.publish("betgenius:stream:opportunities", json.dumps({
            "event": "NEW_NLP_ALERT",
            "data": payload
        }))

    async def start_daemon(self):
        """
        O Loop de Varredura Infinita.
        Nesta etapa, simulamos a chegada de notícias via Webhooks/RSS.
        """
        await self.connect()
        logger.info("👁️ Motor NLP Ativo. Lendo feeds sociais e institucionais...")

        # Mock de notícias para testar o sistema end-to-end
        mock_feeds = [
            ("Real Madrid", "Ancelotti confirma que Vini Jr sentiu desconforto e é dúvida.", "Twitter (Tier 1)", 85.0),
            ("Arsenal", "Treino aberto mostra Saka treinando normalmente. Deve ser titular.", "Imprensa Inglesa", 95.0),
            ("Bayern", "Odd do Bayern despenca nas exchanges asiáticas após vazamento de escalação.", "Pinnacle API Drop", 100.0),
            ("Milan", "Protesto da torcida organizada no CT. Clima de extrema tensão.", "La Gazzetta", 80.0)
        ]

        while True:
            # Sorteia uma notícia a cada 15 segundos para simular fluxo de dados vivo
            feed = random.choice(mock_feeds)
            
            # Cria a task assíncrona para não travar o loop
            asyncio.create_task(self.process_news_feed(feed[0], feed[1], feed[2], feed[3]))
            
            await asyncio.sleep(15.0)

if __name__ == "__main__":
    nlp_engine = SentimentAnalyzer()
    try:
        asyncio.run(nlp_engine.start_daemon())
    except KeyboardInterrupt:
        logger.info("🛑 NLP Engine desligado.")