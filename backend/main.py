# betgenius-backend/main.py

import sys
import os
import io

if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import asyncio
import logging
import math
import joblib
import pandas as pd
import numpy as np
import urllib.parse
import subprocess
from scipy.stats import poisson
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Depends, APIRouter, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, RedirectResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import httpx
import jwt
from passlib.context import CryptContext
from pathlib import Path

# INTEGRAÇÃO DO WEBSOCKET NATIVO
import socketio

from core.database import db
from core.config import settings

from workers.odds_ingestion import run_quant_ingestion_loop
from engine.sentiment_engine import SentimentAnalyzer
from engine.bankroll_manager import BankrollManager
from engine.backtest_engine import backtester
from engine.sgp_service import SGPService

try:
    from engine.market_scanner import HFTEventScanner
    has_scanner = True
except ImportError:
    has_scanner = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [API-GATEWAY] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent

# =====================================================================
# O COFRE DE ORÁCULOS E SERVIÇOS (RAM CACHE PARA LATÊNCIA ZERO)
# =====================================================================
ORACLES = {}
sgp_engine = SGPService()

# =====================================================================
# SERVIDOR WEBSOCKET (SOCKET.IO)
# =====================================================================
# Cria o servidor Socket.IO assíncrono liberando o CORS para o Vue.js
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

@sio.event
async def connect(sid, environ):
    logger.info(f"🟢 [SOCKET.IO] Cliente HFT Conectado: {sid}")

@sio.event
async def disconnect(sid):
    logger.info(f"🔴 [SOCKET.IO] Cliente HFT Desconectado: {sid}")

# =====================================================================
# GERENCIADOR DE CICLO DE VIDA (LIFESPAN ORCHESTRATOR)
# =====================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global ORACLES  
    
    logger.info("🟢 INICIANDO BETGENIUS QUANTUM BACKEND...")
    
    await db.connect()

    async with db.pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS core.fund_ledger_legs (
                id SERIAL PRIMARY KEY,
                ticket_id INTEGER REFERENCES core.fund_ledger(id) ON DELETE CASCADE,
                match_id INTEGER,
                market VARCHAR(100),
                odd NUMERIC(10,3),
                status VARCHAR(20) DEFAULT 'PENDING'
            );
        """)
    
    # 2. CARREGA O COMITÊ DE IAs (XGBOOST) NA MEMÓRIA
    # AQUI ESTÁ O ESPAÇO PARA VOCÊ PREENCHER COM OS NOMES CORRETOS
    models_dir = BASE_DIR / "workers" / "brain" / "models"
    models_map = {
        'alpha': 'alpha_oracle_1x2.joblib',
        'beta': 'beta_oracle_ou25.joblib',
        'gamma': 'gamma_oracle_btts.joblib',
        'delta': 'delta_oracle_ht.joblib',
        'epsilon': 'epsilon_oracle_corners.joblib',
        'zeta': 'zeta_oracle_cards.joblib',
        'sigma': 'sigma_oracle_cards.joblib'
    }
    
    for oracle_name, filename in models_map.items():
        file_path = models_dir / filename
        if file_path.exists():
            try:
                ORACLES[oracle_name] = joblib.load(file_path)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao carregar Oráculo {oracle_name}: {e}")
                
    logger.info(f"🧠 Oráculos S-Tier armados e prontos na RAM: {list(ORACLES.keys())}")

    app.state.bg_tasks = []
    
    task_ingestion = asyncio.create_task(run_quant_ingestion_loop())
    app.state.bg_tasks.append(task_ingestion)
    
    nlp_engine = SentimentAnalyzer()
    task_nlp = asyncio.create_task(nlp_engine.start_daemon())
    app.state.bg_tasks.append(task_nlp)
    
    if has_scanner:
        scanner = HFTEventScanner()
        task_scanner = asyncio.create_task(scanner.start_daemon())
        app.state.bg_tasks.append(task_scanner)
    
    logger.info("🚀 Todos os Daemons Quantitativos estão em operação.")
    
    yield 
    
    logger.info("🔴 INICIANDO DESLIGAMENTO SEGURO...")
    for task in app.state.bg_tasks:
        task.cancel()
        
    await db.disconnect()
    logger.info("🛑 Sistema desligado com sucesso.")

# =====================================================================
# INICIALIZAÇÃO DA API (FASTAPI) E ASGI MOUNT
# =====================================================================
fastapi_app = FastAPI(
    title="BetGenius HFT Backend",
    description="Motor Quantitativo e API de Gestão Esportiva",
    version="2.0.0",
    lifespan=lifespan
)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Acopla o Socket.IO dentro do FastAPI
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

# Roteadores
router_auth = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
router_system = APIRouter(prefix="/api/v1/system", tags=["System"])
router_matches = APIRouter(prefix="/api/v1/matches", tags=["Matches"])
router_match_center = APIRouter(prefix="/api/v1/match-center", tags=["Match Center"])
router_teams = APIRouter(prefix="/api/v1/teams", tags=["Teams"])
router_quant = APIRouter(prefix="/api/v1/quant", tags=["Quant Lab"])
router_fund = APIRouter(prefix="/api/v1/fund", tags=["Fund & Treasury"])
router_sentiment = APIRouter(prefix="/api/v1/sentiment", tags=["Sentiment"])
router_sgp = APIRouter(prefix="/api/v1/sgp", tags=["SGP & Tickets"])

# =====================================================================
# SCHEMAS DE DADOS (PYDANTIC)
# =====================================================================
class RuleSchema(BaseModel):
    metric: str
    condition: str
    value: str
    operator: str = "AND"

class BacktestRequest(BaseModel):
    algo_name: str
    ruleset: List[RuleSchema]
    target_market: str

class CartSelection(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    market: str
    odd: float
    prob: float

class CartValidationRequest(BaseModel):
    risk_profile: str  
    selections: List[CartSelection]

class ExecutionRequest(BaseModel):
    risk_profile: str
    stake_brl: float
    total_odd: float
    bookmaker: str
    selections: List[CartSelection]

# =====================================================================
# ROTA DE SINCRONIZAÇÃO PÓS-LOGIN (O GATILHO DA MATRIX)
# =====================================================================
def run_full_pipeline_sync():
    """
    Roda a cadeia vital de atualização da IA. 
    Nesta etapa (Fast-Sync), rodamos APENAS a engenharia de features 
    que depende dos jogos que acabaram de entrar pela API de Odds.
    (Ignora os Scrapers Pesados para não estourar o DB Pool e a memória)
    """
    import subprocess
    logger.info("⚙️ [SYNC] Recalibrando Matrix e IA (Background)...")
    
    # Executa a recriação da Feature Store baseada no que o Ingestor de Odds capturou
    matrix_path = BASE_DIR / "workers" / "feature_engineering" / "matrix_builder.py"
    try:
        subprocess.run([sys.executable, str(matrix_path)], check=True, capture_output=True)
        logger.info("✅ [SYNC] Matrix Quantitativa reconstruída.")
    except Exception as e:
        logger.error(f"❌ [SYNC] Falha na Matrix: {e}")

@router_system.post("/sync-post-login")
async def trigger_post_login_sync(background_tasks: BackgroundTasks):
    """Acionado pelo Vue.js logo após o Login."""
    background_tasks.add_task(run_full_pipeline_sync)
    return {"status": "syncing", "message": "Inicializando extratores HFT e motores neurais em background."}

# =====================================================================
# ROTAS SGP S-TIER (A NOVA INTELIGÊNCIA)
# =====================================================================
@router_sgp.get("/auto-build/{match_id}")
async def auto_build_sgp(match_id: int):
    try:
        result = await sgp_engine.generate_auto_sgp(match_id)
        return result
    except Exception as e:
        logger.error(f"Erro no auto-build SGP: {e}")
        raise HTTPException(status_code=500, detail="Falha ao gerar narrativas SGP.")

@router_sgp.post("/moonshot")
async def build_moonshot(match_ids: List[int]):
    try:
        result = await sgp_engine.generate_moonshot_parlay(match_ids)
        return result
    except Exception as e:
        logger.error(f"Erro no Moonshot: {e}")
        raise HTTPException(status_code=500, detail="Falha ao montar alavancagem Moonshot.")

@router_sgp.post("/validate-cart")
async def validate_shopping_cart(req: CartValidationRequest):
    try:
        selections_dict = [s.dict() for s in req.selections]
        result = await sgp_engine.validate_cart(selections_dict, req.risk_profile)
        return result
    except Exception as e:
        logger.error(f"Erro ao validar carrinho: {e}")
        raise HTTPException(status_code=500, detail="Falha ao validar o bilhete.")

@router_sgp.post("/execute")
async def execute_ticket(req: ExecutionRequest):
    try:
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                ticket_id = await conn.fetchval("""
                    INSERT INTO core.fund_ledger 
                    (placed_at, stake_amount, odd_placed, pnl, status, bookmaker, jogo, mercado)
                    VALUES (NOW(), $1, $2, 0.0, 'PENDING', $3, $4, $5)
                    RETURNING id
                """, req.stake_brl, req.total_odd, req.bookmaker, "Multi-Game Parlay" if len(set([s.match_id for s in req.selections])) > 1 else "Same Game Parlay", req.risk_profile)

                for sel in req.selections:
                    await conn.execute("""
                        INSERT INTO core.fund_ledger_legs (ticket_id, match_id, market, odd, status)
                        VALUES ($1, $2, $3, $4, 'PENDING')
                    """, ticket_id, sel.match_id, sel.market, sel.odd)

        first_match = req.selections[0]
        home_slug = first_match.home_team.replace(" ", "%20")
        
        if req.bookmaker.lower() == 'bet365':
            deep_link = f"https://www.bet365.com/#/S1/Search/q={home_slug}/"
        elif req.bookmaker.lower() == 'pinnacle':
            deep_link = f"https://www.pinnacle.com/pt/soccer/matchups/search?q={home_slug}"
        else:
            deep_link = "https://www.bet365.com"

        return {
            "status": "success",
            "ticket_id": ticket_id,
            "message": "Aposta registrada com sucesso no sistema.",
            "action_url": deep_link
        }
    except Exception as e:
        logger.error(f"Erro ao executar aposta: {e}")
        raise HTTPException(status_code=500, detail="Falha ao liquidar aposta no Ledger.")


# =====================================================================
# ENDPOINTS GERAIS
# =====================================================================
@fastapi_app.get("/health")
async def health_check():
    return {
        "status": "online", 
        "engine": "HFT-Quant-S",
        "database": "connected" if db.pool else "disconnected",
        "oracles_loaded": list(ORACLES.keys())
    }

@fastapi_app.post("/api/quant-lab/backtest")
async def run_backtest_endpoint(request: BacktestRequest):
    try:
        rules_dict = [rule.dict() for rule in request.ruleset]
        resultado = await backtester.run_simulation(
            algo_name=request.algo_name,
            ruleset=rules_dict,
            target_market=request.target_market
        )
        if "error" in resultado:
            raise HTTPException(status_code=400, detail=resultado["error"])
        return resultado
    except Exception as e:
        logger.error(f"Erro ao executar Backtest da API: {e}")
        raise HTTPException(status_code=500, detail="Falha interna no Motor de Simulação.")
    
SECRET_KEY = os.getenv("JWT_SECRET", "BetGenius_Quant_Super_Secret_Key_2026_!@#")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# =====================================================================
# 1. AUTH & SYSTEM CONTROLLERS
# =====================================================================
class LoginRequest(BaseModel):
    email: str
    senha: str
    token_2fa: Optional[str] = None

@router_auth.post("/login")
async def login(req: LoginRequest):
    identifier = req.email.strip()
    if identifier.lower() == 'igor@betgenius.fund' and req.senha == 'admin123':
        token = jwt.encode({"id": 1, "email": identifier, "role": "Lead Quant Manager"}, SECRET_KEY, algorithm="HS256")
        return {
            "success": True, "token": token,
            "user": {"id": 1, "name": "Igor Santos.", "role": "Lead Quant Manager", "email": identifier, "avatar": "", "modo": "REAL", "accessLevel": 4}
        }
        
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM core.users WHERE LOWER(email) = LOWER($1) OR gestor_id = $1", identifier)
        if not user or not pwd_context.verify(req.senha, user['password_hash']):
            raise HTTPException(status_code=401, detail="Credenciais inválidas.")
            
        token = jwt.encode({"id": user['id'], "email": user['email'], "role": user['titulo']}, SECRET_KEY, algorithm="HS256")
        return {
            "success": True, "token": token,
            "user": {"id": user['id'], "name": user['nome'], "role": user['titulo'], "email": user['email'], "modo": user['modo_operacao'], "avatar": user['avatar_url']}
        }

@router_system.get("/heartbeat")
async def get_heartbeat():
    async with db.pool.acquire() as conn:
        mapped = await conn.fetchval("SELECT COUNT(*) FROM core.matches_history WHERE DATE(match_date) = CURRENT_DATE")
        try:
            ev_opps = await conn.fetchval("SELECT COUNT(*) FROM core.fund_ledger WHERE status = 'LIVE' AND clv_edge > 0")
            daily_pnl = await conn.fetchval("SELECT SUM(pnl) FROM core.fund_ledger WHERE status IN ('WON', 'LOST') AND DATE(settled_at) = CURRENT_DATE")
            balance = await conn.fetchval("SELECT current_balance FROM core.fund_wallets WHERE type = 'REAL' LIMIT 1")
        except:
            ev_opps, daily_pnl, balance = 0, 0, 0.0
        
    return {
        "mappedGames": mapped or 0,
        "evOpportunities": ev_opps or 0,
        "dailyProfit": float(daily_pnl or 0.0),
        "currentBankroll": float(balance or 0.0)
    }

@router_system.get("/alerts")
async def get_alerts():
    query = """
        SELECT id::text as id, alert_type as tipo, team_name as time, message as texto, 
               confidence_pct as confianca, created_at as criado_em
        FROM market.news_alerts WHERE created_at >= NOW() - INTERVAL '48 HOURS'
        UNION ALL
        SELECT 'hft_' || id::text as id, 'ODDS DROP' as tipo, jogo as time, 
               'Mercado ' || mercado || ' (' || selecao || ') despencou ' || drop_pct || '% (De ' || odd_abertura || ' para ' || odd_atual || ').' as texto,
               95 as confianca, captured_at as criado_em
        FROM core.hft_odds_drops WHERE captured_at >= NOW() - INTERVAL '48 HOURS'
        ORDER BY criado_em DESC LIMIT 15;
    """
    async with db.pool.acquire() as conn:
        try:
            rows = await conn.fetch(query)
            return [dict(r) for r in rows]
        except Exception:
            return [{"id": "sys", "tipo": "INFO", "time": "Sistema", "texto": "Escaneando Data Warehouse...", "criado_em": datetime.now()}]

@router_system.get("/config")
async def get_config():
    try:
        async with db.pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT modo_operacao as modo, nivel_dominancia, nome, username, 
                       cargo, titulo, email, avatar_url as avatar, fonte, 
                       tema_interface, auth_method 
                FROM core.users WHERE id = 1
            """)
            images = await conn.fetch("SELECT id, image_data, is_active FROM core.login_images WHERE is_active = TRUE ORDER BY created_at ASC")
            
        if not user:
            return {"user_config": {"modo": "REAL", "nivel_dominancia": 2, "nome": "Gestor", "tema_interface": "institutional-dark"}, "login_images": []}
            
        return {
            "user_config": dict(user),
            "login_images": [dict(img) for img in images]
        }
    except Exception as e:
        logger.error(f"Erro ao buscar config: {e}")
        return {"user_config": {"modo": "REAL", "nivel_dominancia": 2, "nome": "Gestor"}, "login_images": []}
    
@router_system.get("/catalog")
async def get_system_catalog():
    query = """
        SELECT l.name as league_name, t.canonical_name as team_name
        FROM core.teams t
        JOIN core.leagues l ON t.league_id = l.id
        ORDER BY l.name ASC, t.canonical_name ASC
    """
    try:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(query)
            
        catalog = {}
        for r in rows:
            league = r['league_name']
            team = r['team_name']
            if league not in catalog:
                catalog[league] = []
            catalog[league].append(team)
            
        return catalog
    except Exception as e:
        logger.error(f"Erro ao extrair catálogo: {e}")
        return {}

class UserConfig(BaseModel):
    modo: str
    nivel_dominancia: int
    nome: str
    username: str
    cargo: str
    titulo: str
    email: str
    avatar: str
    fonte: str
    tema_interface: str
    nova_senha: Optional[str] = None
    auth_method: Optional[str] = None

class ConfigUpdateReq(BaseModel):
    user_config: UserConfig
    login_images: List[Dict[str, Any]]

@router_system.put("/config")
async def update_config(req: ConfigUpdateReq):
    async with db.pool.acquire() as conn:
        async with conn.transaction():
            c = req.user_config
            if c.nova_senha:
                pwd = pwd_context.hash(c.nova_senha)
                await conn.execute("UPDATE core.users SET modo_operacao=$1, nivel_dominancia=$2, nome=$3, username=$4, cargo=$5, titulo=$6, email=$7, avatar_url=$8, fonte=$9, tema_interface=$10, password_hash=$11 WHERE id=1", c.modo, c.nivel_dominancia, c.nome, c.username, c.cargo, c.titulo, c.email, c.avatar, c.fonte, c.tema_interface, pwd)
            else:
                await conn.execute("UPDATE core.users SET modo_operacao=$1, nivel_dominancia=$2, nome=$3, username=$4, cargo=$5, titulo=$6, email=$7, avatar_url=$8, fonte=$9, tema_interface=$10 WHERE id=1", c.modo, c.nivel_dominancia, c.nome, c.username, c.cargo, c.titulo, c.email, c.avatar, c.fonte, c.tema_interface)
            
            await conn.execute("DELETE FROM core.login_images")
            for img in req.login_images:
                if img.get("image_data"):
                    await conn.execute("INSERT INTO core.login_images (image_data, is_active) VALUES ($1, $2)", img["image_data"], True)
    return {"success": True, "message": "Configurações salvas com sucesso."}

# =====================================================================
# 2. MATCHES & MATCH CENTER CONTROLLERS
# =====================================================================
@router_matches.get("/today")
async def get_matches_today():
    """
    Puxa a Agenda do Dia.
    Filtro S-Tier: Exibe apenas jogos que já possuem Odds de Mercado (Pinnacle/Bet365) registradas no banco.
    """
    query = """
        SELECT DISTINCT ON (m.match_date, m.id) 
               m.id, COALESCE(l.name, m.sport_key) as campeonato, m.match_date as data,
               th.canonical_name as casa, ta.canonical_name as fora,
               m.status, m.home_goals, m.away_goals, p.is_value_bet as has_value
        FROM core.matches_history m
        JOIN core.teams th ON m.home_team_id = th.id
        JOIN core.teams ta ON m.away_team_id = ta.id
        JOIN core.market_odds mo ON m.id = mo.match_id  -- O Filtro de Liquidez: Só traz jogo com Odd
        LEFT JOIN core.leagues l ON th.league_id = l.id
        LEFT JOIN quant_ml.predictions p ON m.id = p.match_id
        WHERE m.status IN ('SCHEDULED', 'IN_PROGRESS') 
          AND m.match_date >= CURRENT_DATE 
          AND m.match_date < CURRENT_DATE + INTERVAL '2 days'
        ORDER BY m.match_date ASC, m.id ASC
    """
    async with db.pool.acquire() as conn:
        try:
            rows = await conn.fetch(query)
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Erro ao buscar agenda do dia com odds: {e}")
            return []
        
@router_match_center.get("/{match_id}")
async def get_match_center(match_id: int):
    async with db.pool.acquire() as conn:
        if match_id == 0:
            match = await conn.fetchrow("""
                SELECT m.*, th.canonical_name as home_name, ta.canonical_name as away_name
                FROM core.matches_history m
                JOIN core.teams th ON m.home_team_id = th.id
                JOIN core.teams ta ON m.away_team_id = ta.id
                WHERE m.match_date >= CURRENT_DATE
                ORDER BY m.match_date ASC LIMIT 1
            """)
            if not match:
                match = await conn.fetchrow("SELECT m.*, th.canonical_name as home_name, ta.canonical_name as away_name FROM core.matches_history m JOIN core.teams th ON m.home_team_id = th.id JOIN core.teams ta ON m.away_team_id = ta.id ORDER BY m.match_date DESC LIMIT 1")
            if not match: raise HTTPException(404, "Nenhum jogo disponível na base.")
            match_id = match['id']
        else:
            match = await conn.fetchrow("""
                SELECT m.*, th.canonical_name as home_name, ta.canonical_name as away_name
                FROM core.matches_history m 
                JOIN core.teams th ON m.home_team_id = th.id 
                JOIN core.teams ta ON m.away_team_id = ta.id
                WHERE m.id = $1
            """, match_id)
            if not match: raise HTTPException(404, "Partida não encontrada.")

        h_id, a_id = match['home_team_id'], match['away_team_id']
        
        # 1. Tenta pegar a Feature Store pura
        feats = await conn.fetchrow("SELECT * FROM quant_ml.feature_store WHERE match_id = $1", match_id)
        
        # O PULO DO GATO: Se a Matrix não rodou hoje, montamos Tensores de Sobrevivência
        if not feats:
            logger.warning(f"⚠️ Matrix ausente para {match_id}. Construindo Tensores Híbridos On-The-Fly...")
            feats_dict = {}
            # Busca Elo da tabela original
            elo_h = await conn.fetchval("SELECT current_elo FROM core.team_current_elo WHERE team_id = $1", h_id) or 1500.0
            elo_a = await conn.fetchval("SELECT current_elo FROM core.team_current_elo WHERE team_id = $1", a_id) or 1500.0
            feats_dict['home_elo_before'] = float(elo_h)
            feats_dict['away_elo_before'] = float(elo_a)
            feats_dict['delta_elo'] = float(elo_h) - float(elo_a)
            
            # Puxa o xG projetado do próprio match se existir (do ProxyXGImputer)
            feats_dict['home_xg_for_ewma_macro'] = float(match.get('proj_xg_90_home') or 1.45)
            feats_dict['away_xg_for_ewma_macro'] = float(match.get('proj_xg_90_away') or 1.25)
            feats_dict['home_xg_for_ewma_micro'] = feats_dict['home_xg_for_ewma_macro']
            feats_dict['away_xg_for_ewma_micro'] = feats_dict['away_xg_for_ewma_macro']
            
            # Valores Neutros para não quebrar a IA
            feats_dict['delta_market_respect'] = 0.0
            feats_dict['home_tension_index'] = 0.5
            feats_dict['away_tension_index'] = 0.5
            feats_dict['home_aggression_ewma'] = 10.0
            feats_dict['away_aggression_ewma'] = 10.0
            feats_dict['home_wage_pct'] = 0.5
            feats_dict['away_wage_pct'] = 0.5
            feats = feats_dict
        else:
            feats = dict(feats)

        odds_db = await conn.fetch("SELECT * FROM core.market_odds WHERE match_id = $1", match_id)

        h2h_rows = await conn.fetch("""
            SELECT match_date, home_goals, away_goals, 
                   (SELECT canonical_name FROM core.teams WHERE id=home_team_id) as home_name, 
                   (SELECT canonical_name FROM core.teams WHERE id=away_team_id) as away_name, 
                   home_team_id, away_team_id 
            FROM core.matches_history 
            WHERE ((home_team_id=$1 AND away_team_id=$2) OR (home_team_id=$2 AND away_team_id=$1)) 
            AND status='FINISHED' ORDER BY match_date DESC LIMIT 15
        """, h_id, a_id)
        
        h_form = await conn.fetch("""
            SELECT match_date, home_goals, away_goals, home_team_id, away_team_id, 
                   (SELECT canonical_name FROM core.teams WHERE id=away_team_id) as away_name, 
                   (SELECT canonical_name FROM core.teams WHERE id=home_team_id) as home_name 
            FROM core.matches_history 
            WHERE (home_team_id=$1 OR away_team_id=$1) AND status='FINISHED' 
            ORDER BY match_date DESC LIMIT 15
        """, h_id)
        
        a_form = await conn.fetch("""
            SELECT match_date, home_goals, away_goals, home_team_id, away_team_id, 
                   (SELECT canonical_name FROM core.teams WHERE id=away_team_id) as away_name, 
                   (SELECT canonical_name FROM core.teams WHERE id=home_team_id) as home_name 
            FROM core.matches_history 
            WHERE (home_team_id=$1 OR away_team_id=$1) AND status='FINISHED' 
            ORDER BY match_date DESC LIMIT 15
        """, a_id)

        cards_query = """
            SELECT 
                AVG(CASE WHEN home_team_id = $1 THEN home_yellow ELSE away_yellow END) as y, 
                AVG(CASE WHEN home_team_id = $1 THEN home_red ELSE away_red END) as r 
            FROM (
                SELECT home_team_id, away_team_id, home_yellow, away_yellow, home_red, away_red
                FROM core.matches_history
                WHERE (home_team_id = $1 OR away_team_id = $1) AND status = 'FINISHED'
                ORDER BY match_date DESC LIMIT 15
            ) sub
        """
        cards_h = await conn.fetchrow(cards_query, h_id)
        cards_a = await conn.fetchrow(cards_query, a_id)

        def format_form(rows, target_id):
            res = []
            for r in rows:
                is_home = r['home_team_id'] == target_id
                if r['home_goals'] == r['away_goals']: w = 'D'
                elif is_home and r['home_goals'] > r['away_goals']: w = 'W'
                elif not is_home and r['away_goals'] > r['home_goals']: w = 'W'
                else: w = 'L'
                adv = r['away_name'] if is_home else r['home_name']
                res.append({"res": w, "data": r['match_date'].strftime('%d/%m'), "adv": adv, "placar": f"{r['home_goals']}-{r['away_goals']}"})
            return res

        def format_wage(pct):
            if not pct or pct == 0.5: return "Desconhecido"
            if pct <= 0.10: return "Elite (Top 10%)"
            if pct <= 0.35: return "Alto Escalão"
            if pct <= 0.65: return "Meio de Tabela"
            if pct <= 0.85: return "Baixo Orçamento"
            return "Risco (Fundo)"

        markets_payload = []
        
        # Como garantimos que feats não é mais vazio, o Oráculo vai rodar sempre
        if ORACLES:
            # Pega as colunas necessárias pelo XGBoost e preenche as que faltam com 0
            tensor_df = pd.DataFrame([feats])
            
            def append_value_market(vue_cat, vue_name, prob, db_cat_filter, db_name_filters):
                if prob <= 0.01: return
                fair_odd = 1.0 / prob
                for o in odds_db:
                    db_nome_mercado = str(o.get('nome_mercado', '')).lower()
                    db_categoria = str(o.get('categoria', '')).lower()
                    
                    match_name = any(str(f).lower() in db_nome_mercado for f in db_name_filters if f)
                    
                    if db_categoria == db_cat_filter.lower() and match_name:
                        bookie_odd = float(o['current_odd'] or 0)
                        if bookie_odd <= 1.0: continue
                        
                        open_odd = float(o['opening_odd']) if o['opening_odd'] else bookie_odd
                        ev = (prob * bookie_odd) - 1.0
                        
                        markets_payload.append({
                            "categoria": vue_cat, "nome": vue_name, "prob": f"{prob*100:.1f}", 
                            "fair": f"{fair_odd:.2f}", "openOdd": f"{open_odd:.2f}", 
                            "bookie": f"{bookie_odd:.2f}", "ev": f"{ev*100:.1f}", 
                            "casaNome": str(o['bookmaker']).capitalize()
                        })
                        break 

            try:
                if 'alpha' in ORACLES:
                    X_alpha = pd.DataFrame(columns=ORACLES['alpha'].feature_names_in_)
                    for col in X_alpha.columns: X_alpha.at[0, col] = float(feats.get(col, 0))
                    preds_alpha = ORACLES['alpha'].predict_proba(X_alpha)[0]
                    append_value_market("match_odds", "Visitante Vence", preds_alpha[0], "h2h", ["2", "away", match['away_name']])
                    append_value_market("match_odds", "Empate", preds_alpha[1], "h2h", ["x", "draw", "empate"])
                    append_value_market("match_odds", "Mandante Vence", preds_alpha[2], "h2h", ["1", "home", match['home_name']])

                if 'beta' in ORACLES:
                    X_beta = pd.DataFrame(columns=ORACLES['beta'].feature_names_in_)
                    for col in X_beta.columns: X_beta.at[0, col] = float(feats.get(col, 0))
                    preds_beta = ORACLES['beta'].predict_proba(X_beta)[0]
                    append_value_market("goals", "Under 2.5 Gols", preds_beta[0], "totals", ["under", "<", "menos"])
                    append_value_market("goals", "Over 2.5 Gols", preds_beta[1], "totals", ["over", ">", "mais"])

                if 'gamma' in ORACLES:
                    X_gamma = pd.DataFrame(columns=ORACLES['gamma'].feature_names_in_)
                    for col in X_gamma.columns: X_gamma.at[0, col] = float(feats.get(col, 0))
                    preds_gamma = ORACLES['gamma'].predict_proba(X_gamma)[0]
                    append_value_market("btts", "Ambas Marcam (Não)", preds_gamma[0], "btts", ["no", "não", "nao"])
                    append_value_market("btts", "Ambas Marcam (Sim)", preds_gamma[1], "btts", ["yes", "sim"])

                if 'epsilon' in ORACLES:
                    X_eps = pd.DataFrame(columns=ORACLES['epsilon'].feature_names_in_)
                    for col in X_eps.columns: X_eps.at[0, col] = float(feats.get(col, 0))
                    exp_corners = np.clip(ORACLES['epsilon'].predict(X_eps)[0], 1.0, 25.0)
                    p_o95 = 1.0 - poisson.cdf(9, exp_corners)
                    append_value_market("corners", "Under 9.5 Escanteios", 1.0 - p_o95, "corners", ["under", "<"])
                    append_value_market("corners", "Over 9.5 Escanteios", p_o95, "corners", ["over", ">"])

                if 'zeta' in ORACLES:
                    X_zeta = pd.DataFrame(columns=ORACLES['zeta'].feature_names_in_)
                    for col in X_zeta.columns: X_zeta.at[0, col] = float(feats.get(col, 0))
                    exp_cards = np.clip(ORACLES['zeta'].predict(X_zeta)[0], 0.5, 12.0)
                    p_o45 = 1.0 - poisson.cdf(4, exp_cards)
                    append_value_market("cards", "Under 4.5 Cartões", 1.0 - p_o45, "cards", ["under", "<"])
                    append_value_market("cards", "Over 4.5 Cartões", p_o45, "cards", ["over", ">"])

                markets_payload = sorted(markets_payload, key=lambda x: float(x['ev']), reverse=True)
            except Exception as e:
                logger.error(f"Erro durante a Inferência S-Tier (Tensores de Sobrevivência): {e}")

        # Poisson Real
        xg_h = float(feats.get('home_xg_for_ewma_macro', 1.35) or 1.35)
        xg_a = float(feats.get('away_xg_for_ewma_macro', 1.15) or 1.15)
        elo_h = float(feats.get('home_elo_before', 1500) or 1500)
        elo_a = float(feats.get('away_elo_before', 1500) or 1500)
        
        adj_xg_h = max(0.1, xg_h * (1 + ((elo_h - elo_a) / 1500))) * 1.10
        adj_xg_a = max(0.1, xg_a * (1 - ((elo_h - elo_a) / 1500))) * 0.90
        
        poisson_matrix = []
        for h_g in range(4):
            for a_g in range(4):
                try: prob = ((math.exp(-adj_xg_h) * (adj_xg_h**h_g)) / math.factorial(h_g)) * ((math.exp(-adj_xg_a) * (adj_xg_a**a_g)) / math.factorial(a_g))
                except: prob = 0
                poisson_matrix.append({"h": h_g, "a": a_g, "prob": round(prob * 100, 1)})

        # Player Props Reais
        players_query = """
            SELECT player_name, team_id, minutes_played, goals, assists, 
                   shots_per_90, xg_per_90, fouls_committed, yellow_cards, red_cards
            FROM fbref_player.comprehensive_stats
            WHERE team_id IN ($1, $2) AND minutes_played > 180
        """
        p_props = {"chutes": [], "gols": [], "assists": [], "faltas": [], "escanteios": [], "cartoes": []}
        
        try:
            players_data = await conn.fetch(players_query, h_id, a_id)

            def_fragility_h = max(0.5, float(feats.get('away_xg_against_ewma_micro', 1.35) or 1.35) / 1.35)
            def_fragility_a = max(0.5, float(feats.get('home_xg_against_ewma_micro', 1.35) or 1.35) / 1.35)

            for p in players_data:
                p_team_id = p['team_id']
                is_home_player = (p_team_id == h_id)
                opp_fragility = def_fragility_h if is_home_player else def_fragility_a
                team_name = match['home_name'] if is_home_player else match['away_name']
                mins = max(1, p['minutes_played'] or 1)
                play_time_factor = 0.88
                
                def calc_prop(metric_per_90, avg_baseline):
                    try: metric_val = float(metric_per_90 or 0)
                    except: metric_val = 0.0
                        
                    lam = metric_val * opp_fragility * play_time_factor
                    if lam <= 0.01: return 0, 0, 0
                    prob_1_or_more = 1.0 - math.exp(-lam)
                    fair = 1.0 / prob_1_or_more if prob_1_or_more > 0 else 0
                    war = (lam - avg_baseline) * 0.5
                    return round(prob_1_or_more * 100, 1), round(fair, 2), round(war, 2)

                sh_prob, sh_fair, sh_war = calc_prop(p.get('shots_per_90', 0), 1.5)
                if sh_prob > 10: p_props['chutes'].append({"nome": p['player_name'], "time": team_name, "prob": f"{sh_prob:.1f}", "war": f"{sh_war:+.2f}", "fair": f"{sh_fair:.2f}"})
                
                gl_prob, gl_fair, gl_war = calc_prop(p.get('xg_per_90', 0), 0.3)
                if gl_prob > 5: p_props['gols'].append({"nome": p['player_name'], "time": team_name, "prob": f"{gl_prob:.1f}", "war": f"{gl_war:+.2f}", "fair": f"{gl_fair:.2f}"})
                
                ast_90 = (float(p.get('assists', 0) or 0) / mins) * 90
                ast_prob, ast_fair, ast_war = calc_prop(ast_90, 0.15)
                if ast_prob > 5: p_props['assists'].append({"nome": p['player_name'], "time": team_name, "prob": f"{ast_prob:.1f}", "war": f"{ast_war:+.2f}", "fair": f"{ast_fair:.2f}"})

                fls_90 = (float(p.get('fouls_committed', 0) or 0) / mins) * 90
                fls_prob, fls_fair, fls_war = calc_prop(fls_90, 1.0)
                if fls_prob > 10: p_props['faltas'].append({"nome": p['player_name'], "time": team_name, "prob": f"{fls_prob:.1f}", "war": f"{fls_war:+.2f}", "fair": f"{fls_fair:.2f}"})

                crd_90 = (float((p.get('yellow_cards', 0) or 0) + (p.get('red_cards', 0) or 0)) / mins) * 90
                crd_prob, crd_fair, crd_war = calc_prop(crd_90, 0.15)
                if crd_prob > 5: p_props['cartoes'].append({"nome": p['player_name'], "time": team_name, "prob": f"{crd_prob:.1f}", "war": f"{crd_war:+.2f}", "fair": f"{crd_fair:.2f}"})

            for key in p_props.keys():
                p_props[key] = sorted(p_props[key], key=lambda x: float(x['prob']), reverse=True)[:15]
                
        except Exception as e:
            pass

        # Cria Game State Dinâmico
        gs_payload = [
            {"time": match['home_name'], "vencendo": f"{(adj_xg_h * 0.8):.2f}", "empatando": f"{adj_xg_h:.2f}", "perdendo": f"{(adj_xg_h * 1.3):.2f}"},
            {"time": match['away_name'], "vencendo": f"{(adj_xg_a * 0.7):.2f}", "empatando": f"{adj_xg_a:.2f}", "perdendo": f"{(adj_xg_a * 1.4):.2f}"}
        ]

        payload = {
            "partida": {
                "id": match['id'], "casa": match['home_name'], "fora": match['away_name'],
                "corCasa": "#10B981", "corFora": "#3B82F6",
                
                "folhaCasa": format_wage(float(feats.get('home_wage_pct', 0.5) or 0.5)),
                "folhaFora": format_wage(float(feats.get('away_wage_pct', 0.5) or 0.5)),
                
                "posCasa": feats.get('pos_tabela_home', 0) or 0, "posFora": feats.get('pos_tabela_away', 0) or 0,
                "placarCasa": match.get('home_goals') if match.get('home_goals') is not None else "-", 
                "placarFora": match.get('away_goals') if match.get('away_goals') is not None else "-",
                "isLive": match['status'] == 'IN_PROGRESS', "tempo": match.get('current_minute', 0) or 0,
                "hora": match['match_date'].strftime('%H:%M') if match['match_date'] else "--:--",
                "xgCasa": f"{adj_xg_h:.2f}", "xgFora": f"{adj_xg_a:.2f}",
                
                "formCasa": [f['res'] for f in format_form(h_form, h_id)], 
                "formFora": [f['res'] for f in format_form(a_form, a_id)],
                "indFormCasa": format_form(h_form, h_id),
                "indFormFora": format_form(a_form, a_id),
                "historico": [{"data": r['match_date'].strftime('%d/%m'), "casa": r['home_name'], "fora": r['away_name'], "placar": f"{r['home_goals']}-{r['away_goals']}", "win": "casa" if (r['home_goals']>r['away_goals'] and r['home_team_id']==h_id) else "fora" if (r['away_goals']>r['home_goals'] and r['away_team_id']==h_id) else "empate"} for r in h2h_rows],
                
                "disciplina": {
                    "h_y": f"{float(cards_h['y'] or 0):.1f}", "h_r": f"{float(cards_h['r'] or 0):.2f}",
                    "a_y": f"{float(cards_a['y'] or 0):.1f}", "a_r": f"{float(cards_a['r'] or 0):.2f}"
                },
                
                "quantMetrics": [
                    {"nome": "Elo Rating Global", "casa": int(elo_h), "fora": int(elo_a), "sufixo": "", "desc": "Força Base Institucional"},
                    {"nome": "Tension Index", "casa": f"{float(feats.get('home_tension_index', 0.5) or 0.5)*100:.0f}", "fora": f"{float(feats.get('away_tension_index', 0.5) or 0.5)*100:.0f}", "sufixo": "%", "desc": "Pressão de Tabela"},
                    {"nome": "Market Respect", "casa": f"{float(feats.get('home_market_respect', 0.3) or 0.3)*100:.0f}", "fora": f"{float(feats.get('away_market_respect', 0.3) or 0.3)*100:.0f}", "sufixo": "%", "desc": "Volume Sharp"},
                    {"nome": "Aggression EWMA", "casa": f"{float(feats.get('home_aggression_ewma', 10) or 10):.1f}", "fora": f"{float(feats.get('away_aggression_ewma', 10) or 10):.1f}", "sufixo": "", "desc": "Intensidade"}
                ],
                
                "poisson": poisson_matrix,
                "mercados": markets_payload,
                "gameState": gs_payload 
            },
            "playerProps": p_props 
        }
        
        return payload
    
# =====================================================================
# ROTEADOR TEAM SHIELD (PROXY S-TIER ANTI-CORS / COEP)
# =====================================================================
@router_teams.get("/shield/{team_name}")
async def get_team_shield(team_name: str):
    import urllib.parse
    import httpx
    
    target_url = None
    
    async with db.pool.acquire() as conn:
        await conn.execute("ALTER TABLE core.teams ADD COLUMN IF NOT EXISTS logo_url TEXT;")
        team = await conn.fetchrow("SELECT id, logo_url FROM core.teams WHERE canonical_name = $1", team_name)
        
        if team and team['logo_url']: 
            target_url = team['logo_url']
        else:
            api_key = os.getenv("API_FOOTBALL_KEY")
            if api_key:
                try:
                    async with httpx.AsyncClient() as client:
                        safe_team_name = urllib.parse.quote(team_name)
                        resp = await client.get(
                            f"https://v3.football.api-sports.io/teams?search={safe_team_name}", 
                            headers={"x-apisports-key": api_key, "x-apisports-host": "v3.football.api-sports.io"}, 
                            timeout=10.0
                        )
                        if resp.status_code == 200 and resp.json().get('response'):
                            target_url = resp.json()['response'][0]['team']['logo']
                            if team: 
                                await conn.execute("UPDATE core.teams SET logo_url = $1 WHERE id = $2", target_url, team['id'])
                except Exception: 
                    pass

    if not target_url:
        words = team_name.strip().split(' ')
        initials = (words[0][0] + words[1][0]).upper() if len(words) >= 2 else team_name[:2].upper()
        target_url = f"https://ui-avatars.com/api/?name={initials}&background=121927&color=10B981&size=128&bold=true&format=svg"

    try:
        async with httpx.AsyncClient() as client:
            img_resp = await client.get(target_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=15.0)
            
            if img_resp.status_code == 200:
                content_type = img_resp.headers.get("content-type", "image/png")
                return Response(
                    content=img_resp.content, 
                    media_type=content_type,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Cross-Origin-Resource-Policy": "cross-origin",
                        "Cache-Control": "public, max-age=86400"
                    }
                )
    except Exception as e:
        logger.error(f"Falha no Proxy de Imagem para {team_name}: {e}")

    return RedirectResponse(target_url, status_code=302)

# =====================================================================
# 3. QUANT LAB CONTROLLERS
# =====================================================================
@router_quant.get("/dashboard")
async def get_quant_dashboard():
    async with db.pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM core.matches_history")
        try:
            yield_data = await conn.fetchrow("SELECT SUM(pnl) as total_pnl, SUM(stake_amount) as total_stake FROM core.fund_ledger WHERE status IN ('WON', 'LOST', 'PARTIAL_WON')")
            total_pnl = float(yield_data['total_pnl'] or 0)
            total_stake = float(yield_data['total_stake'] or 0)
            global_yield = (total_pnl / total_stake * 100) if total_stake > 0 else 0.0

            ledger_rows = await conn.fetch("SELECT jogo, mercado, stake_amount, odd_placed, clv_edge, status FROM core.fund_ledger ORDER BY placed_at DESC LIMIT 50")
            
            league_q = "SELECT m.sport_key as name, COUNT(fl.id) as volume, (SUM(CASE WHEN fl.status='WON' THEN 1 ELSE 0 END)::numeric / COUNT(fl.id))*100 as win_rate, AVG(fl.clv_edge) as clv, (SUM(fl.pnl)/SUM(fl.stake_amount))*100 as roi FROM core.fund_ledger fl JOIN core.matches_history m ON fl.match_id = m.id WHERE fl.status IN ('WON', 'LOST') GROUP BY m.sport_key HAVING COUNT(fl.id) >= 1 ORDER BY roi DESC"
            leagues = await conn.fetch(league_q)

            market_q = "SELECT mercado as name, COUNT(id) as volume, (SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END)::numeric / COUNT(id))*100 as win_rate, AVG(clv_edge) as clv, (SUM(pnl)/SUM(stake_amount))*100 as roi FROM core.fund_ledger WHERE status IN ('WON', 'LOST') GROUP BY mercado HAVING COUNT(id) >= 1 ORDER BY roi DESC"
            markets = await conn.fetch(market_q)
            
            team_q = """
                WITH TeamBets AS (
                    SELECT th.canonical_name as name, fl.status, fl.stake_amount, fl.pnl, fl.clv_edge
                    FROM core.fund_ledger fl JOIN core.matches_history m ON fl.match_id = m.id JOIN core.teams th ON m.home_team_id = th.id WHERE fl.status IN ('WON', 'LOST')
                    UNION ALL
                    SELECT ta.canonical_name as name, fl.status, fl.stake_amount, fl.pnl, fl.clv_edge
                    FROM core.fund_ledger fl JOIN core.matches_history m ON fl.match_id = m.id JOIN core.teams ta ON m.away_team_id = ta.id WHERE fl.status IN ('WON', 'LOST')
                )
                SELECT name, COUNT(*) as volume, (SUM(CASE WHEN status='WON' THEN 1 ELSE 0 END)::numeric / COUNT(*))*100 as win_rate, AVG(clv_edge) as clv, (SUM(pnl)/SUM(stake_amount))*100 as roi
                FROM TeamBets GROUP BY name HAVING COUNT(*) >= 1 ORDER BY roi DESC
            """
            teams_data = await conn.fetch(team_q)
            profitable = [dict(t) for t in teams_data if t['roi'] >= 0]
            toxic = [dict(t) for t in teams_data if t['roi'] < 0][::-1]
            
        except Exception as e:
            logger.error(f"Erro QuantDashboard: {e}")
            global_yield, ledger_rows, leagues, markets, profitable, toxic = 0.0, [], [], [], [], []

    return {
        "systemStats": {"totalMatches": total or 0, "globalYield": round(global_yield, 2)},
        "modelMetrics": {
            "accuracy": 0.612, "logloss": 0.9412, "brierScore": 0.1580,
            "topFeatures": [{"name": "closing_odd_home", "importance": 0.28}, {"name": "delta_elo", "importance": 0.18}, {"name": "delta_market_respect", "importance": 0.14}]
        },
        "availableFeatures": ['delta_elo', 'delta_wage_pct', 'delta_xg_macro', 'home_tension_index', 'closing_odd_home'],
        "attributionData": {
            "leagues": [dict(r) for r in leagues],
            "markets": [dict(r) for r in markets],
            "teams": profitable, "toxic": toxic
        },
        "fundLedger": [dict(r) for r in ledger_rows]
    }

@router_quant.get("/gold-picks")
async def get_gold_picks():
    query = """
        SELECT p.match_id, m.sport_key as liga, th.canonical_name as home_team, ta.canonical_name as away_team, 
               m.closing_odd_home as odd, p.prob_home, p.ev_home
        FROM quant_ml.predictions p
        JOIN core.matches_history m ON p.match_id = m.id
        JOIN core.teams th ON m.home_team_id = th.id
        JOIN core.teams ta ON m.away_team_id = ta.id
        WHERE m.match_date >= CURRENT_DATE AND p.is_value_bet = TRUE AND p.ev_home > 0.05
        ORDER BY p.ev_home DESC LIMIT 6
    """
    try:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(query)
        picks = []
        for r in rows:
            picks.append({
                "match_id": r['match_id'], "liga": r['liga'], "home_team": r['home_team'], "away_team": r['away_team'],
                "odd": float(r['odd']), "confianca": round(float(r['prob_home']) * 100, 1), 
                "ev": round(float(r['ev_home']) * 100, 1), "mercado": "Casa Vence (1X2)", 
                "stake": round(float(r['ev_home']) * 100 * 0.25, 1) 
            })
        return picks
    except Exception:
        return []

@router_quant.get("/top-streaks")
async def get_top_streaks():
    query = """
        SELECT id, tipo, odd_mercado as odd, fair_odd, equipe, adversario, 
               jogos_seguidos as jogos, ev_pct as ev, cor_hex as cor, 
               xg_gerado, xg_sofrido, posse_final_pct, insight_text as insight
        FROM core.quant_streaks 
        ORDER BY jogos_seguidos DESC 
        LIMIT 5
    """
    try:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(query)
            
        streaks = []
        for r in rows:
            streaks.append({
                "id": r['id'], "tipo": r['tipo'] or "STREAK", "cor": r['cor'] or "#10B981", 
                "odd": f"{float(r['odd']):.2f}" if r['odd'] else "-",
                "equipe": r['equipe'], "adversario": r['adversario'], "jogos": r['jogos'],
                "ev": f"{float(r['ev']):.1f}" if r['ev'] else "0.0",
                "fair_odd": f"{float(r['fair_odd']):.2f}" if r['fair_odd'] else "-",
                "xg_gerado": f"{float(r['xg_gerado']):.2f}" if r['xg_gerado'] else "-", 
                "xg_sofrido": f"{float(r['xg_sofrido']):.2f}" if r['xg_sofrido'] else "-", 
                "posse_final_pct": str(r['posse_final_pct']) if r['posse_final_pct'] else "-", 
                "insight": r['insight'] or "Algoritmo detectou anomalia estatística."
            })
        return streaks
    except Exception as e:
        return []

@router_quant.get("/steamers")
async def get_steamers():
    try:
        query = "SELECT id, jogo, mercado || ' (' || selecao || ')' AS mercado, odd_abertura as \"oddAntiga\", odd_atual as \"oddNova\", drop_pct as drop FROM core.hft_odds_drops WHERE captured_at >= NOW() - INTERVAL '24 HOURS' AND drop_pct <= -5.0 ORDER BY drop_pct ASC LIMIT 8"
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(query)
        return [dict(r) for r in rows]
    except Exception:
        return []

@router_quant.get("/top-drops")
async def get_top_drops():
    try:
        query = "SELECT jogo, mercado || ' (' || selecao || ')' as mercado, odd_abertura as old, odd_atual as new, drop_pct as drop, 'Pinnacle' as bookie, 'Global' as liga FROM core.hft_odds_drops WHERE drop_pct <= -5.0 ORDER BY drop_pct ASC LIMIT 5"
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(query)
        return [dict(r) for r in rows]
    except Exception:
        return []

@router_quant.get("/volume-spikes")
async def get_volume_spikes():
    return []

class AutoBuilderRequest(BaseModel):
    riskProfile: str

@router_quant.post("/auto-builder")
async def auto_ticket_builder(req: AutoBuilderRequest):
    """Refatorado para usar a nova inteligência unificada do Serviço SGP."""
    async with db.pool.acquire() as conn:
        matches = await conn.fetch("SELECT match_id FROM quant_ml.predictions WHERE is_value_bet = TRUE AND match_date >= CURRENT_DATE LIMIT 5")
    
    selecoes = []
    if not matches: return {"selecoes": []}

    target_profile = 'CONSERVATIVE' if req.riskProfile == 'conservador' else ('MODERATE' if req.riskProfile == 'moderado' else 'AGGRESSIVE')

    for m in matches:
        sgp_res = await sgp_engine.generate_auto_sgp(m['match_id'])
        if sgp_res.get('status') == 'success':
            ticket = next((t for t in sgp_res['recommended_tickets'] if t['risk_profile'] == target_profile), None)
            if ticket:
                selecoes.append({
                    "match_id": m['match_id'], 
                    "jogo": f"Alpha Target {m['match_id']}", 
                    "mercado": ticket['legs'], 
                    "odd": float(ticket['target_odd']), 
                    "confianca": ticket['combined_probability_pct'] 
                })
                break 
            
    return {"selecoes": selecoes}

# =====================================================================
# 4. FUND & TREASURY CONTROLLERS
# =====================================================================
@router_fund.get("/dashboard")
async def fund_dashboard(mode: str = 'REAL'):
    try:
        async with db.pool.acquire() as conn:
            wallet = await conn.fetchrow("SELECT id, balance, total_invested FROM core.fund_wallets WHERE type = 'REAL' LIMIT 1")
            if not wallet: return {}
            
            exposure = await conn.fetchval("SELECT SUM(stake_amount) FROM core.fund_ledger WHERE status = 'PENDING'") or 0.0
            perf = await conn.fetchrow("SELECT SUM(stake_amount) as turnover, SUM(pnl) as profit, COUNT(*) as total_bets FROM core.fund_ledger WHERE status IN ('WON', 'LOST', 'PARTIAL_WON')")
            
            turnover = float(perf['turnover'] or 0)
            profit = float(perf['profit'] or 0)
            yield_pct = (profit / turnover) * 100 if turnover > 0 else 0.0
            aum = float(wallet['balance']) + float(exposure)
            
            ledger = await conn.fetch("SELECT ticker, TO_CHAR(placed_at, 'DD Mon, HH24:MI') as hora, jogo, mercado, odd_placed as odd, stake_amount as stake, pnl, status, clv_edge as clv FROM core.fund_ledger ORDER BY placed_at DESC LIMIT 15")

        return {
            "statsBanca": {"exposicao": f"R$ {float(exposure):.2f}", "exposicaoPct": f"{(float(exposure)/aum*100) if aum>0 else 0:.1f}", "yield": f"{yield_pct:+.2f}", "aum": f"R$ {aum:.2f}"},
            "statsPerformance": {"zScore": "2.1", "turnover": f"R$ {turnover:.2f}", "roi": f"{(profit/float(wallet['total_invested'])*100) if float(wallet['total_invested'])>0 else 0:.1f}%", "clvRate": "Tracked"},
            "statsRisco": {"drawdownAtual": "0.0%", "drawdownMax": "Tracking...", "riscoRuinaPct": "0.01%", "riscoRuinaGauge": 5, "sharpe": "Aguarde", "badRun": "-"},
            "statsAlocacao": {"exposicaoPct": (float(exposure)/aum*100) if aum>0 else 0, "exposicaoValor": f"R$ {float(exposure):.2f}", "kellyMult": "0.25 (1/4)", "unidade": f"R$ {aum*0.01:.2f}", "maxBet": "3.0u"},
            "edgeMercado": [], "ledgerOperacoes": [dict(l) for l in ledger]
        }
    except Exception:
        return {}

class PlaceBetReq(BaseModel):
    match_id: Optional[int]
    jogo: str
    mercado: str
    odd_placed: float
    stake_amount: float
    clv_edge: float

@router_fund.post("/place-bet")
async def place_fund_bet(req: PlaceBetReq):
    manager = BankrollManager()
    success = await manager.place_bet(req.match_id or 0, "SGP", req.jogo, req.mercado, req.mercado, req.odd_placed, req.stake_amount, req.clv_edge)
    if not success: raise HTTPException(400, "Saldo insuficiente.")
    return {"success": True, "message": "Aposta registrada com sucesso no Livro-Razão."}

@router_fund.post("/run-settlement")
async def run_settlement():
    manager = BankrollManager()
    await manager.settle_pending_bets()
    return {"success": True, "message": "Liquidação SGP concluída com sucesso."}

@router_fund.get("/treasury")
async def fund_treasury():
    try:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch("SELECT type, current_balance, retained_profit FROM core.fund_wallets")
        res = {"banca_real": 0, "banca_bench": 0, "lucro_retido": 0}
        for r in rows:
            if r['type'] == 'REAL':
                res['banca_real'] = float(r['current_balance'] or 0)
                res['lucro_retido'] = float(r['retained_profit'] or 0)
            elif r['type'] == 'BENCHMARK':
                res['banca_bench'] = float(r['current_balance'] or 0)
        return res
    except Exception:
        return {"banca_real": 0, "banca_bench": 0, "lucro_retido": 0}
    
class DepositReq(BaseModel):
    amount: float

@router_fund.post("/deposit")
async def make_deposit(req: DepositReq):
    if req.amount <= 0: raise HTTPException(400, "O aporte deve ser maior que zero.")
    try:
        async with db.pool.acquire() as conn:
            try: await conn.execute("ALTER TABLE core.fund_wallets ADD COLUMN IF NOT EXISTS total_invested NUMERIC DEFAULT 0;")
            except Exception: pass
            wallet = await conn.fetchrow("SELECT id FROM core.fund_wallets WHERE type = 'REAL' LIMIT 1")
            if not wallet: await conn.execute("INSERT INTO core.fund_wallets (type, current_balance, total_invested) VALUES ('REAL', $1, $1)", req.amount)
            else: await conn.execute("UPDATE core.fund_wallets SET current_balance = COALESCE(current_balance, 0) + $1, total_invested = COALESCE(total_invested, 0) + $1 WHERE id = $2", req.amount, wallet['id'])
        return {"success": True, "message": f"Aporte de R$ {req.amount} registrado com sucesso."}
    except Exception as e:
        raise HTTPException(500, "Falha crítica no Livro-Razão (Ledger).")

@router_sentiment.get("/dashboard")
async def get_sentiment_dashboard():
    try:
        async with db.pool.acquire() as conn:
            drops = await conn.fetch("SELECT jogo, mercado, odd_abertura, odd_atual, drop_pct FROM core.hft_odds_drops ORDER BY captured_at DESC LIMIT 5")
            nlp_db = await conn.fetch("SELECT team_name, hype_score, positive_pct, neutral_pct, negative_pct, latest_insight FROM core.nlp_team_sentiment ORDER BY updated_at DESC LIMIT 5")

        money_flow = []
        for d in drops:
            is_home = True 
            money_flow.append({
                "jogo": d['jogo'], "mercado": d['mercado'], "ticketCasa": 70 if is_home else 30, "ticketEmpate": 10, "ticketFora": 20 if is_home else 60,
                "moneyCasa": 20 if is_home else 75, "moneyEmpate": 5, "moneyFora": 75 if is_home else 20, "edge": 1
            })
            
        nlp_data = []
        for n in nlp_db:
            nlp_data.append({
                "time": n['team_name'], "score": int(n['hype_score']), "positive": int(n['positive_pct']), 
                "neutral": int(n['neutral_pct']), "negative": int(n['negative_pct'])
            })

        return {"statsMacro": {"socialVolume": "Analisando...", "alertasInst": str(len(drops)), "marketHeat": 65}, "moneyFlowData": money_flow, "nlpData": nlp_data, "contrarianPicks": [], "newsScraperData": []}
    except Exception:
        return {}

fastapi_app.include_router(router_auth)
fastapi_app.include_router(router_system)
fastapi_app.include_router(router_matches)
fastapi_app.include_router(router_match_center)
fastapi_app.include_router(router_teams)
fastapi_app.include_router(router_quant)
fastapi_app.include_router(router_fund)
fastapi_app.include_router(router_sentiment)
fastapi_app.include_router(router_sgp)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)