# betgenius-backend/routers/sgp_tipster.py

import logging
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Importa a Inteligência do Motor SGP
from engine.sgp_service import SGPService

logger = logging.getLogger(__name__)

# O Router agrupa todas as lógicas de montagem e validação de bilhetes (Tipster Inteligente)
router = APIRouter(prefix="/api/v1/sgp", tags=["SGP & Tickets"])

# Instancia o Motor Quantitativo de Parlays na memória
sgp_engine = SGPService()

# =====================================================================
# SCHEMAS DE DADOS PARA VALIDAÇÃO
# =====================================================================
class CartSelection(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    market: str
    odd: float
    prob: float

class CartValidationRequest(BaseModel):
    risk_profile: str  # Ex: 'CONSERVATIVE', 'MODERATE', 'AGGRESSIVE'
    selections: List[CartSelection]


# =====================================================================
# ROTA 1: AUTO-BUILD (Construtor de Cenários de Jogo Único)
# =====================================================================
@router.get("/auto-build/{match_id}")
async def auto_build_sgp(match_id: int):
    """
    Motor S-Tier: Analisa o Match ID e cruza os tensores de 1X2, Gols e Cantos 
    para gerar bilhetes correlacionados (Same Game Parlays) com Expected Value Positivo (+EV).
    """
    try:
        # A chamada ao engine processa as matrizes de Poisson e gera as narrativas
        result = await sgp_engine.generate_auto_sgp(match_id)
        return result
    except Exception as e:
        logger.error(f"Erro Crítico no Auto-Build SGP para o jogo {match_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Falha na matriz matemática ao gerar narrativas SGP. Verifique os tensores do jogo."
        )


# =====================================================================
# ROTA 2: MOONSHOT (Alavancagem / Bilhetes de Variância Elevada)
# =====================================================================
@router.post("/moonshot")
async def build_moonshot(match_ids: List[int]):
    """
    Estratégia de Alto Risco / Alto Retorno (Tails Event).
    Pega em múltiplos jogos e cruza as seleções mais extremas de cada um
    para criar um bilhete de cotação altíssima visando alavancagem de micro-stakes.
    """
    if not match_ids:
        raise HTTPException(status_code=400, detail="É necessário enviar pelo menos um Match ID.")
        
    try:
        result = await sgp_engine.generate_moonshot_parlay(match_ids)
        return result
    except Exception as e:
        logger.error(f"Erro Crítico no Motor de Moonshot para os jogos {match_ids}: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Falha ao montar alavancagem Moonshot. Verifique a liquidez das odds das partidas selecionadas."
        )


# =====================================================================
# ROTA 3: CART VALIDATOR (O Filtro de Risco do Carrinho)
# =====================================================================
@router.post("/validate-cart")
async def validate_shopping_cart(req: CartValidationRequest):
    """
    O Inspetor Chefe. Antes da Tesouraria executar a aposta, esta rota
    lê o carrinho de compras do usuário e verifica se as seleções combinadas
    respeitam os limites do perfil de risco (Kelly Criterion Múltiplo).
    """
    if not req.selections:
        return {"status": "error", "message": "O carrinho está vazio."}
        
    try:
        # Converte os objetos Pydantic num dicionário para o motor legado processar
        selections_dict = [s.dict() for s in req.selections]
        
        # Analisa a correlação e a Odd Justa (Fair Odd) do bilhete completo
        result = await sgp_engine.validate_cart(selections_dict, req.risk_profile)
        
        return result
        
    except Exception as e:
        logger.error(f"Erro ao validar carrinho de apostas: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Falha interna ao calcular o Risco do Carrinho (Cart Validator)."
        )