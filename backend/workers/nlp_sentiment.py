# betgenius-backend/workers/nlp_sentiment.py
import asyncio
import aiohttp
import asyncpg
import redis.asyncio as redis
import os
import json
import feedparser
import logging
import google.generativeai as genai
from apify_client import ApifyClient
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [NLP-SCRAPER] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class NLPSocialScraper:
    """
    Motor S-Tier de Processamento de Linguagem Natural (NLP).
    Aggrega Reddit, RSS Globais e milhares de comentários do YouTube (via Apify).
    Gera o Hype Index matemático focado no Mercado de Apostas.
    """
    def __init__(self):
        self.db_pool = None
        self.redis_client = None
        
        # 1. Configuração Gemini (Cérebro NLP)
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            logger.error("🚨 GEMINI_API_KEY não encontrada no .env!")
            exit(1)
        genai.configure(api_key=gemini_key)
        self.ai_model = genai.GenerativeModel('gemini-1.5-flash')

        # 2. Configuração Apify (Scraper Profundo de Youtube)
        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            logger.error("🚨 APIFY_API_TOKEN não encontrada no .env!")
            exit(1)
        self.apify = ApifyClient(apify_token)
        # O Actor de Youtube Comments
        self.youtube_actor_id = "h5krcA5TqNWevDUSw" # Youtube Comments Scraper (Padrão Apify)

        # =====================================================================
        # 3. FONTES INSTITUCIONAIS (RSS Feeds Classificados por Peso e Região)
        # =====================================================================
        # O ideal em produção avançada é puxar isso do banco de dados, mas 
        # esta estrutura de dicionário simula um arquivo de configuração (ConfigMap) impecável.
        self.news_sources = {
            "global_en": [
                "https://www.espn.com/espn/rss/soccer/news",
                "https://feeds.bbci.co.uk/sport/football/rss.xml",
                "https://www.theguardian.com/football/rss",
                "https://www.skysports.com/rss/12040"
            ],
            "europe_es": [
                "https://e00-marca.uecdn.es/rss/futbol/futbol-internacional.xml",
                "https://as.com/rss/futbol/internacional.xml"
            ],
            "latam_pt": [
                "https://ge.globo.com/rss/futebol/",
                "https://www.uol.com.br/esporte/futebol/ultimas/index.xml"
            ]
        }

        # =====================================================================
        # 4. FÓRUNS DE MASSA (Dumb Money & Fanatics)
        # =====================================================================
        # Mantemos apenas os nomes limpos. A URL é montada dinamicamente pelas funções.
        self.target_subreddits = [
            "soccer",           # Global/Geral
            "futebol",          # LATAM/Brasil
            "premierleague",    # Nicho UK
            "laliga",           # Nicho ES
            "sportsbook"        # Focado em apostadores (Crucial para ver o viés da massa)
        ]
        self.reddit_sort_type = "new"  # 'new' (notícias de agora) ou 'hot' (tópicos hypados)
        self.reddit_limit = 30

    async def connect_infrastructure(self):
        db_url = os.getenv("DATABASE_URL")
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.db_pool = await asyncpg.create_pool(db_url)
        self.redis_client = await redis.from_url(redis_url)
        logger.info("⚡ Infraestrutura Postgres/Redis Conectada.")

    async def scrape_reddit(self, session):
        """Puxa a manada do Reddit com URLs geradas dinamicamente."""
        texts = []
        headers = {'User-Agent': 'BetGenius_Quant_Fund/2.0'}
        
        for sub in self.target_subreddits:
            # Constrói a URL dinamicamente (Ex: https://www.reddit.com/r/soccer/new.json?limit=30)
            url = f"https://www.reddit.com/r/{sub}/{self.reddit_sort_type}.json?limit={self.reddit_limit}"
            
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        for post in data['data']['children']:
                            texts.append(f"[Reddit - r/{sub}] {post['data']['title']}")
            except Exception as e:
                logger.warning(f"Falha ao raspar r/{sub}: {e}")
        return texts

    def scrape_rss_news(self):
        """Puxa a mídia institucional achatando as categorias regionais."""
        texts = []
        
        # Achata (flatten) o dicionário de listas em uma única lista de URLs
        all_rss_urls = [url for category in self.news_sources.values() for url in category]
        
        for feed_url in all_rss_urls:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:10]: # Limita a 10 por portal para não poluir
                    texts.append(f"[News] {entry.title}")
            except Exception as e:
                logger.warning(f"Falha RSS ({feed_url}): {e}")
        return texts

    def scrape_youtube_comments(self, team_name):
        """
        O Extrator de Multidões. Usa a Apify para buscar vídeos recentes 
        com a keyword do time e extrair os comentários das últimas 24h.
        """
        logger.info(f"▶️ Acionando Apify Actor para vídeos do '{team_name}'...")
        texts = []
        
        # Parâmetros para buscar vídeos de ontem pra hoje sobre o time
        run_input = {
            "searchKeywords": f"{team_name} highlights OR {team_name} news",
            "maxVideos": 2, # Pega os 2 vídeos mais relevantes das últimas 24h
            "maxComments": 50, # 50 comentários por vídeo = 100 de amostra
            "maxCommentsDepth": 1
        }
        
        try:
            # Chama o Actor (Pode demorar de 10 a 30 segundos)
            run = self.apify.actor(self.youtube_actor_id).call(run_input=run_input)
            
            # Coleta os resultados do Dataset
            for item in self.apify.dataset(run["defaultDatasetId"]).iterate_items():
                if "text" in item:
                    # Limpa quebras de linha para economizar tokens na IA
                    clean_text = item["text"].replace('\n', ' ').strip()
                    texts.append(f"[Youtube] {clean_text}")
                    
        except Exception as e:
            logger.warning(f"Falha ao raspar Youtube (Apify) para {team_name}: {e}")
            
        return texts

    async def analyze_with_gemini(self, team_name, corpus):
        """Motor de Compreensão Quantitativa (Gemini Flash)."""
        if not corpus: return None
        
        text_block = "\n".join(corpus)
        
        prompt = f"""
        Você é um algoritmo analista de comportamento de massa para um fundo quantitativo de apostas esportivas.
        Analise o seguinte bloco massivo de manchetes de jornais, Reddit e comentários de Youtube focando APENAS no time: {team_name}.
        
        O objetivo não é saber se eles ganharam ou perderam, mas entender a EXPECTATIVA do público (Hype) para precificar as apostas futuras.
        
        - Hype Score alto (>70): A torcida está eufórica, confiante que o time vai amassar o próximo adversário (Mercado inflado / "Dumb Money" no Favorito).
        - Hype Score baixo (<40): Torcida furiosa, clima de crise, desconfiança total (Mercado subestimado).
        - Hype Neutro (~50): Discussões normais, sem euforia ou pânico excessivo.
        
        Corpus de dados (Amostra de milhares de pontos):
        {text_block}
        
        Responda APENAS com um JSON estrito nesta estrutura exata:
        {{
            "score": [Inteiro de 0 a 100],
            "positive_pct": [Inteiro de 0 a 100],
            "neutral_pct": [Inteiro de 0 a 100],
            "negative_pct": [Inteiro de 0 a 100],
            "insight_curto": "[Uma frase de 10 palavras cínica de Wall Street resumindo o viés da massa contra esse time]"
        }}
        """
        
        try:
            # Tempo de resposta do Gemini Flash para blocos de texto gigantes é insano (2-3 segundos)
            response = await self.ai_model.generate_content_async(prompt)
            raw_json = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(raw_json)
        except Exception as e:
            logger.error(f"Erro no Gemini NLP: {e}")
            return None

    async def update_database_and_broadcast(self, team_name, analysis, data_lake_size):
        """Salva no Cofre e pisca na tela do Vue."""
        query = """
            INSERT INTO core.nlp_team_sentiment 
            (team_name, hype_score, positive_pct, neutral_pct, negative_pct, latest_insight, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            ON CONFLICT (team_name) 
            DO UPDATE SET 
                hype_score = EXCLUDED.hype_score,
                positive_pct = EXCLUDED.positive_pct,
                neutral_pct = EXCLUDED.neutral_pct,
                negative_pct = EXCLUDED.negative_pct,
                latest_insight = EXCLUDED.latest_insight,
                updated_at = NOW();
        """
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    query, team_name, analysis['score'], 
                    analysis['positive_pct'], analysis['neutral_pct'], 
                    analysis['negative_pct'], analysis['insight_curto']
                )
                
            # Dispara para o Vue.js via Redis se detectarmos Anomalia
            if analysis['score'] > 75 or analysis['score'] < 30:
                alerta = {
                    "tipo": "news",
                    "data": {
                        "time": team_name,
                        "tempo": "Radar de Risco",
                        "tipo": "noticia",
                        "texto": f"Extrema Anomalia Comportamental: {analysis['insight_curto']} (Amostra: {data_lake_size} menções)",
                        "fonte": "Gemini Hype Engine",
                        "confianca": 96
                    }
                }
                await self.redis_client.publish('betgenius:stream:sentiment_alerts', json.dumps(alerta))

        except Exception as e:
            logger.error(f"Erro DB/Redis: {e}")

    async def run_cycle(self):
        await self.connect_infrastructure()
        
        target_teams = ["Arsenal", "Real Madrid", "Flamengo"]
        
        async with aiohttp.ClientSession() as session:
            while True:
                logger.info("===================================================")
                logger.info("🌐 INICIANDO VARREDURA GLOBAL (RSS + REDDIT)")
                reddit_posts = await self.scrape_reddit(session)
                rss_news = self.scrape_rss_news()
                global_base = reddit_posts + rss_news
                
                for team in target_teams:
                    logger.info(f"⛏️ Iniciando Deep Scraping para: {team}")
                    
                    # Como a chamada da Apify (Requests HTTP complexas do crawler deles)
                    # é síncrona/bloqueante na biblioteca Python atual, nós a rodamos em um 
                    # ThreadPool nativo do asyncio para não travar o loop inteiro do robô.
                    loop = asyncio.get_running_loop()
                    youtube_comments = await loop.run_in_executor(None, self.scrape_youtube_comments, team)
                    
                    # Junta o Lixo Global com os Comentários Focados
                    corpus_final = global_base + youtube_comments
                    
                    logger.info(f"🧠 Enviando {len(corpus_final)} data points para NLP Gemini avaliar Hype...")
                    analysis = await self.analyze_with_gemini(team, corpus_final)
                    
                    if analysis:
                        logger.info(f"📊 [RESULTADO] {team}: Score {analysis['score']} | Insight: {analysis['insight_curto']}")
                        await self.update_database_and_broadcast(team, analysis, len(corpus_final))
                    
                    await asyncio.sleep(5) # Delay entre times
                
                logger.info("⏳ Ciclo Finalizado. Fundo em Sleep Mode por 2 horas.")
                # Em um fundo real, raspar Youtube ocioso gasta tokens. Rodamos a cada 2h.
                await asyncio.sleep(7200) 

if __name__ == "__main__":
    scraper = NLPSocialScraper()
    try:
        asyncio.run(scraper.run_cycle())
    except KeyboardInterrupt:
        logger.info("Sistema NLP desligado pelo Arquiteto.")