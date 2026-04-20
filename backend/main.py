# betgenius-backend/main.py
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

# Importações de Infraestrutura
from core.database import db
from core.config import settings

# Importações dos Motores (Daemons e Workers)
from workers.odds_ingestion import run_quant_ingestion_loop
from engine.sentiment_engine import SentimentAnalyzer
from engine.backtest_engine import backtester

# Tratamento de importação caso o scanner ainda esteja sendo ajustado
try:
    from engine.market_scanner import HFTEventScanner
    has_scanner = True
except ImportError:
    has_scanner = False

logger = logging.getLogger(__name__)

# =====================================================================
# GERENCIADOR DE CICLO DE VIDA (LIFESPAN ORCHESTRATOR)
# =====================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Controla o que liga e desliga junto com o servidor.
    Evita vazamento de memória e conexões zumbis no banco de dados.
    """
    logger.info("🟢 INICIANDO BETGENIUS QUANTUM BACKEND...")
    
    # 1. Conecta ao Banco de Dados (Neon.tech PostgreSQL)
    await db.connect()
    
    # 2. Inicia os Processos Pesados em Background (Daemons)
    app.state.bg_tasks = []
    
    # -> Motor de Ingestão de Odds
    task_ingestion = asyncio.create_task(run_quant_ingestion_loop())
    app.state.bg_tasks.append(task_ingestion)
    
    # -> Motor de Sentimento (NLP)
    nlp_engine = SentimentAnalyzer()
    task_nlp = asyncio.create_task(nlp_engine.start_daemon())
    app.state.bg_tasks.append(task_nlp)
    
    # -> Motor de Anomalias de Mercado (Se existir)
    if has_scanner:
        scanner = HFTEventScanner()
        task_scanner = asyncio.create_task(scanner.start_daemon())
        app.state.bg_tasks.append(task_scanner)
    
    logger.info("🚀 Todos os Daemons Quantitativos estão em operação.")
    
    yield # O servidor fica rodando aqui
    
    # 3. Desligamento Seguro (Graceful Shutdown)
    logger.info("🔴 INICIANDO DESLIGAMENTO SEGURO...")
    for task in app.state.bg_tasks:
        task.cancel()
        
    await db.disconnect()
    logger.info("🛑 Sistema desligado com sucesso.")

# =====================================================================
# INICIALIZAÇÃO DA API (FASTAPI)
# =====================================================================
app = FastAPI(
    title="BetGenius HFT Backend",
    description="Motor Quantitativo e API de Gestão Esportiva",
    version="2.0.0",
    lifespan=lifespan
)

# Blindagem de CORS (Crucial para o Vue.js conseguir acessar a API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Em produção, substitua pelo link do seu Vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# =====================================================================
# ROTAS DA API (ENDPOINTS REST)
# =====================================================================

@app.get("/health")
async def health_check():
    """Rota de verificação de status do servidor e banco de dados."""
    return {
        "status": "online", 
        "engine": "HFT-Quant-S",
        "database": "connected" if db.pool else "disconnected"
    }

@app.post("/api/quant-lab/backtest")
async def run_backtest_endpoint(request: BacktestRequest):
    """
    Endpoint consumido pela aba 'Quant Lab' do Vue.js.
    Recebe as regras visuais, executa no banco histórico em C++ (NumPy) e devolve o gráfico.
    """
    try:
        # Converte as regras do Pydantic para dicionários que o backtester entende
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