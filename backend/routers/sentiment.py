# betgenius-backend/routers/sentiment.py

import logging
from fastapi import APIRouter
from core.database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sentiment", tags=["Sentiment & HFT Flow"])

# =====================================================================
# ROTA 1: DASHBOARD DE SENTIMENTO E HFT MONEY FLOW
# =====================================================================
@router.get("/dashboard")
async def get_sentiment_dashboard():
    """
    Motor S-Tier: Analisa o Hype, Sentimento de Rede e o Volume Financeiro (Money Flow).
    Extrai quedas drásticas de odds e análise NLP para encontrar 'Steamers'.
    """
    try:
        async with db.pool.acquire() as conn:
            # 1. Money Flow: Busca os drops de odds (Steamers) capturados hoje
            recent_drops = await conn.fetch("""
                SELECT jogo, mercado, odd_abertura, odd_atual, drop_pct, volume_status 
                FROM core.hft_odds_drops 
                ORDER BY captured_at DESC LIMIT 10
            """)
            
            # 2. Sentimento NLP Real das equipes (Notícias/Fóruns)
            nlp_stats = await conn.fetch("""
                SELECT team_name, hype_score, positive_pct, neutral_pct, negative_pct, latest_insight 
                FROM core.nlp_team_sentiment 
                ORDER BY updated_at DESC LIMIT 5
            """)
            
            # 3. Market Heat (Média móvel de tensão nas partidas do dia via Feature Store)
            heat_val = await conn.fetchval("""
                SELECT AVG(home_tension_index + away_tension_index) / 2 
                FROM quant_ml.feature_store 
                WHERE match_date = CURRENT_DATE
            """)
            market_heat = int((heat_val or 0.5) * 100)
            
        # Formata o Sentimento (NLP) para o Frontend
        nlp_formatted = []
        for n in nlp_stats:
            nlp_formatted.append({
                "time": n['team_name'], 
                "score": int(n['hype_score']), 
                "positive": int(n['positive_pct']), 
                "neutral": int(n['neutral_pct']), 
                "negative": int(n['negative_pct']),
                "insight": n['latest_insight']
            })

        # Formata o Fluxo de Dinheiro (HFT Drops) para o Frontend
        money_flow_formatted = []
        for d in recent_drops:
            # Simulação visual de ticket/money (Em produção real, virá da API da Exchange)
            is_home = True 
            money_flow_formatted.append({
                "jogo": d['jogo'], 
                "mercado": d['mercado'], 
                "edge": -float(d['drop_pct']), # Queda na Odd significa dinheiro a entrar (Smart Money)
                "ticketCasa": 70 if is_home else 30, 
                "ticketEmpate": 10, 
                "ticketFora": 20 if is_home else 60,
                "moneyCasa": 20 if is_home else 75, 
                "moneyEmpate": 5, 
                "moneyFora": 75 if is_home else 20
            })
            
        return {
            "statsMacro": {
                "socialVolume": "25.4k", # Poderá ser preenchido dinamicamente via Apify no futuro
                "alertasInst": str(len(recent_drops)), 
                "marketHeat": market_heat
            }, 
            "moneyFlowData": money_flow_formatted, 
            "nlpData": nlp_formatted, 
            "contrarianPicks": [], # Preenchido quando o XGBoost apontar contra a massa
            "newsScraperData": []  # Preenchido em tempo real pelo WebSocket
        }
    except Exception as e:
        logger.error(f"Erro ao gerar Dashboard de Sentimento: {e}")
        return {
            "statsMacro": {"socialVolume": "Analisando...", "alertasInst": "0", "marketHeat": 50}, 
            "moneyFlowData": [], 
            "nlpData": [], 
            "contrarianPicks": [], 
            "newsScraperData": []
        }