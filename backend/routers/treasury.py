# betgenius-backend/routers/treasury.py

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.database import db
from engine.bankroll_manager import BankrollManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/fund", tags=["Fund & Treasury"])

# =====================================================================
# SCHEMAS DE DADOS
# =====================================================================
class CartSelection(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    market: str
    odd: float
    prob: float

class ExecutionRequest(BaseModel):
    risk_profile: str
    stake_brl: float
    total_odd: float
    bookmaker: str
    selections: List[CartSelection]

class PlaceBetReq(BaseModel):
    match_id: Optional[int]
    jogo: str
    mercado: str
    odd_placed: float
    stake_amount: float
    clv_edge: float

class DepositReq(BaseModel):
    amount: float
    target: str = Field(default="REAL")

# =====================================================================
# ROTA 1: DASHBOARD FINANCEIRO E DE RISCO
# =====================================================================
@router.get("/dashboard")
async def fund_dashboard(mode: str = 'REAL'):
    """Retorna a saúde financeira do Fundo, Turnover e AUM."""
    try:
        async with db.pool.acquire() as conn:
            wallet = await conn.fetchrow("SELECT id, balance, total_invested FROM core.fund_wallets WHERE type = 'REAL' LIMIT 1")
            if not wallet: 
                return {}
            
            exposure = await conn.fetchval("SELECT SUM(stake_amount) FROM core.fund_ledger WHERE status = 'PENDING'") or 0.0
            perf = await conn.fetchrow("SELECT SUM(stake_amount) as turnover, SUM(pnl) as profit, COUNT(*) as total_bets FROM core.fund_ledger WHERE status IN ('WON', 'LOST', 'PARTIAL_WON')")
            
            turnover = float(perf['turnover'] or 0)
            profit = float(perf['profit'] or 0)
            yield_pct = (profit / turnover) * 100 if turnover > 0 else 0.0
            aum = float(wallet['balance']) + float(exposure)
            
            ledger = await conn.fetch("""
                SELECT ticker, TO_CHAR(placed_at, 'DD Mon, HH24:MI') as hora, 
                       jogo, mercado, odd_placed as odd, stake_amount as stake, 
                       pnl, status, clv_edge as clv 
                FROM core.fund_ledger 
                ORDER BY placed_at DESC LIMIT 15
            """)

        return {
            "statsBanca": {
                "exposicao": f"R$ {float(exposure):.2f}", 
                "exposicaoPct": f"{(float(exposure)/aum*100) if aum>0 else 0:.1f}", 
                "yield": f"{yield_pct:+.2f}", 
                "aum": f"R$ {aum:.2f}"
            },
            "statsPerformance": {
                "zScore": "2.1", 
                "turnover": f"R$ {turnover:.2f}", 
                "roi": f"{(profit/float(wallet['total_invested'])*100) if float(wallet['total_invested'])>0 else 0:.1f}%", 
                "clvRate": "Tracked"
            },
            "statsRisco": {
                "drawdownAtual": "0.0%", 
                "drawdownMax": "Tracking...", 
                "riscoRuinaPct": "0.01%", 
                "riscoRuinaGauge": 5, 
                "sharpe": "Aguarde", 
                "badRun": "-"
            },
            "statsAlocacao": {
                "exposicaoPct": (float(exposure)/aum*100) if aum>0 else 0, 
                "exposicaoValor": f"R$ {float(exposure):.2f}", 
                "kellyMult": "0.25 (1/4)", 
                "unidade": f"R$ {aum*0.01:.2f}", 
                "maxBet": "3.0u"
            },
            "edgeMercado": [], 
            "ledgerOperacoes": [dict(l) for l in ledger]
        }
    except Exception as e:
        logger.error(f"Erro no Fund Dashboard: {e}")
        return {}

# =====================================================================
# ROTA 2: EXTRATO COMPLETO (Treasury)
# =====================================================================
@router.get("/treasury")
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
    except Exception as e:
        logger.error(f"Erro na Treasury: {e}")
        return {"banca_real": 0, "banca_bench": 0, "lucro_retido": 0}

# =====================================================================
# ROTA 3: REGISTRO DE APOSTA SIMPLES
# =====================================================================
@router.post("/place-bet")
async def place_fund_bet(req: PlaceBetReq):
    manager = BankrollManager()
    success = await manager.place_bet(
        req.match_id or 0, "SGP", req.jogo, req.mercado, 
        req.mercado, req.odd_placed, req.stake_amount, req.clv_edge
    )
    if not success: 
        raise HTTPException(400, "Saldo insuficiente ou erro ao registrar aposta.")
    return {"success": True, "message": "Aposta registrada com sucesso no Livro-Razão."}

# =====================================================================
# ROTA 4: EXECUÇÃO DE APOSTAS MÚLTIPLAS / SGP
# =====================================================================
@router.post("/execute")
async def execute_ticket(req: ExecutionRequest):
    try:
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                is_multi = len(set([s.match_id for s in req.selections])) > 1
                mercado_nome = "Multi-Game Parlay" if is_multi else "Same Game Parlay"
                
                ticket_id = await conn.fetchval("""
                    INSERT INTO core.fund_ledger 
                    (placed_at, stake_amount, odd_placed, pnl, status, bookmaker, jogo, mercado)
                    VALUES (NOW(), $1, $2, 0.0, 'PENDING', $3, $4, $5)
                    RETURNING id
                """, req.stake_brl, req.total_odd, req.bookmaker, mercado_nome, req.risk_profile)

                for sel in req.selections:
                    await conn.execute("""
                        INSERT INTO core.fund_ledger_legs (ticket_id, match_id, market, odd, status)
                        VALUES ($1, $2, $3, $4, 'PENDING')
                    """, ticket_id, sel.match_id, sel.market, sel.odd)

        # Geração do Link Dinâmico da Casa de Apostas
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
            "message": "Aposta SGP registrada com sucesso.",
            "action_url": deep_link
        }
    except Exception as e:
        logger.error(f"Erro ao executar aposta SGP: {e}")
        raise HTTPException(status_code=500, detail="Falha ao liquidar aposta no Ledger.")

# =====================================================================
# ROTA 5: LIQUIDAÇÃO DE APOSTAS (Settlement)
# =====================================================================
@router.post("/run-settlement")
async def run_settlement():
    manager = BankrollManager()
    await manager.settle_pending_bets()
    return {"success": True, "message": "Liquidação de operações pendentes concluída com sucesso."}

# =====================================================================
# ROTA 6: APORTES FINANCEIROS (Deposit)
# =====================================================================
@router.post("/deposit")
async def make_deposit(req: DepositReq):
    if req.amount <= 0: 
        raise HTTPException(400, "O aporte deve ser maior que zero.")
        
    try:
        async with db.pool.acquire() as conn:
            # 1. Tenta garantir a existência da coluna total_invested de forma segura
            await conn.execute("ALTER TABLE core.fund_wallets ADD COLUMN IF NOT EXISTS total_invested NUMERIC DEFAULT 0;")
            
            # 2. Localiza a carteira baseada no target (REAL ou BENCHMARK)
            wallet = await conn.fetchrow("SELECT id FROM core.fund_wallets WHERE type = $1 LIMIT 1", req.target)
            
            # 3. Se a carteira não existir, cria a genesis wallet
            if not wallet: 
                await conn.execute("""
                    INSERT INTO core.fund_wallets (type, current_balance, total_invested) 
                    VALUES ($1, $2, $2)
                """, req.target, req.amount)
            else: 
                # Se existir, injeta o capital
                await conn.execute("""
                    UPDATE core.fund_wallets 
                    SET current_balance = COALESCE(current_balance, 0) + $1, 
                        total_invested = COALESCE(total_invested, 0) + $1 
                    WHERE id = $2
                """, req.amount, wallet['id'])
                
        return {"success": True, "message": f"Aporte de R$ {req.amount} registrado com sucesso na carteira {req.target}."}
    except Exception as e:
        logger.error(f"Falha Crítica no Ledger durante aporte: {e}")
        raise HTTPException(500, "Falha crítica no Livro-Razão (Ledger).")