# betgenius-backend/main.py

import sys
import os
import asyncio
import logging
import joblib
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio

# BLINDAGEM DE ENCODING PARA WINDOWS
if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from core.database import db
from workers.odds_ingestion import run_quant_ingestion_loop
from engine.sentiment_engine import SentimentAnalyzer

try:
    from engine.market_scanner import HFTEventScanner
    has_scanner = True
except ImportError:
    has_scanner = False

# IMPORTAÇÃO DOS NOSSOS NOVOS MÓDULOS (ROUTERS)
from routers import auth, system, match_center, quant_lab, treasury, sentiment, sgp_tipster

logging.basicConfig(level=logging.INFO, format="%(asctime)s [API-GATEWAY] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent

# SERVIDOR WEBSOCKET
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

@sio.event
async def connect(sid, environ):
    logger.info(f"🟢 [SOCKET.IO] Cliente HFT Conectado: {sid}")

@sio.event
async def disconnect(sid):
    logger.info(f"🔴 [SOCKET.IO] Cliente HFT Desconectado: {sid}")

# GERENCIADOR DE CICLO DE VIDA (LIFESPAN)
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🟢 INICIANDO BETGENIUS QUANTUM BACKEND...")
    await db.connect()

    # CARREGA OS ORÁCULOS NA MEMÓRIA DO APP (Acessível em todas as rotas via request.app.state.oracles)
    app.state.oracles = {}
    models_dir = BASE_DIR / "workers" / "brain" / "models"
    models_map = {
        'alpha': 'alpha_oracle_1x2.joblib',
        'beta': 'beta_oracle_ou25.joblib',
        'gamma': 'gamma_oracle_btts.joblib',
        'delta': 'delta_oracle_ht_1x2.joblib',
        'epsilon': 'epsilon_oracle_corners.joblib',
        'zeta': 'zeta_oracle_cards.joblib',
        'sigma': 'sigma_oracle_shots.joblib'
    }
    
    for oracle_name, filename in models_map.items():
        file_path = models_dir / filename
        if file_path.exists():
            try:
                app.state.oracles[oracle_name] = joblib.load(file_path)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao carregar Oráculo {oracle_name}: {e}")
                
    logger.info(f"🧠 Oráculos S-Tier armados na RAM: {list(app.state.oracles.keys())}")

    # INICIA DAEMONS EM BACKGROUND
    app.state.bg_tasks = []
    app.state.bg_tasks.append(asyncio.create_task(run_quant_ingestion_loop()))
    
    nlp_engine = SentimentAnalyzer()
    app.state.bg_tasks.append(asyncio.create_task(nlp_engine.start_daemon()))
    
    if has_scanner:
        scanner = HFTEventScanner()
        app.state.bg_tasks.append(asyncio.create_task(scanner.start_daemon()))
    
    logger.info("🚀 Todos os Daemons Quantitativos estão em operação.")
    yield 
    
    logger.info("🔴 INICIANDO DESLIGAMENTO SEGURO...")
    for task in app.state.bg_tasks:
        task.cancel()
    await db.disconnect()
    logger.info("🛑 Sistema desligado com sucesso.")

# INICIALIZAÇÃO DA API (FASTAPI)
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

# ACOPLAMENTO DOS MICROSSERVIÇOS (ROUTERS)
fastapi_app.include_router(auth.router)
fastapi_app.include_router(system.router)
fastapi_app.include_router(match_center.router)
fastapi_app.include_router(quant_lab.router)
fastapi_app.include_router(treasury.router)
fastapi_app.include_router(sentiment.router)
fastapi_app.include_router(sgp_tipster.router)

# MONTAGEM FINAL DO APP COM SOCKET.IO
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)