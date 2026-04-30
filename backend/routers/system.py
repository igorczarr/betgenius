# betgenius-backend/routers/system.py

import os
import sys
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import pyotp
from passlib.context import CryptContext

from core.database import db

router = APIRouter(prefix="/api/v1/system", tags=["System"])
logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
BASE_DIR = Path(__file__).resolve().parent.parent if 'Path' in globals() else None

# =====================================================================
# SCHEMAS
# =====================================================================
class TOTPSetupRequest(BaseModel):
    user_id: int

class TOTPVerifyRequest(BaseModel):
    user_id: int
    totp_code: str

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

class ProfileUpdateReq(BaseModel):
    cover_url: Optional[str] = None
    time_coracao: Optional[str] = None

# =====================================================================
# HEALTH E HEARTBEAT
# =====================================================================
@router.get("/health")
async def health_check():
    return {
        "status": "online", 
        "engine": "HFT-Quant-S",
        "database": "connected" if db.pool else "disconnected"
    }

@router.get("/heartbeat")
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

@router.get("/alerts")
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

# =====================================================================
# TOTP / 2FA CONFIGURATION
# =====================================================================
@router.post("/setup-authenticator")
async def gerar_chave_authenticator(req: TOTPSetupRequest):
    novo_secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(novo_secret).provisioning_uri(name="Gestor Quantitativo", issuer_name="BetGenius S-Tier")
    return {"temp_secret": novo_secret, "qr_code_uri": uri, "manual_entry_key": novo_secret}

@router.post("/verify-and-enable-authenticator")
async def ativar_authenticator(req: TOTPVerifyRequest, temp_secret: str):
    totp = pyotp.TOTP(temp_secret)
    if totp.verify(req.totp_code):
        async with db.pool.acquire() as conn:
            await conn.execute("UPDATE core.users SET totp_secret = $1, auth_mode = 'authenticator' WHERE id = $2", temp_secret, req.user_id)
        return {"success": True, "message": "Authenticator vinculado."}
    raise HTTPException(status_code=400, detail="Código inválido. Tente novamente.")

@router.post("/disable-authenticator")
async def desativar_authenticator(req: dict):
    user_id = req.get('user_id', 1) 
    async with db.pool.acquire() as conn:
        await conn.execute("UPDATE core.users SET totp_secret = NULL, auth_mode = 'password' WHERE id = $1", user_id)
    return {"success": True, "message": "Authenticator desativado."}

# =====================================================================
# CONFIG & PROFILE (Gamification)
# =====================================================================
@router.get("/config")
async def get_config():
    try:
        async with db.pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT modo_operacao as modo, nivel_dominancia, nome, username, 
                       cargo, titulo, email, avatar_url as avatar, fonte, 
                       tema_interface, auth_mode as auth_method 
                FROM core.users WHERE id = 1
            """)
            images = await conn.fetch("SELECT id, image_data, is_active FROM core.login_images WHERE is_active = TRUE ORDER BY created_at ASC")
            
        if not user:
            return {"user_config": {"modo": "REAL", "nivel_dominancia": 2, "nome": "Gestor", "tema_interface": "institutional-dark"}, "login_images": []}
        return {"user_config": dict(user), "login_images": [dict(img) for img in images]}
    except Exception as e:
        logger.error(f"Erro ao buscar config: {e}")
        return {"user_config": {"modo": "REAL", "nivel_dominancia": 2}, "login_images": []}

@router.put("/config")
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
    return {"success": True, "message": "Configurações salvas."}

@router.get("/profile")
async def get_user_profile_stats():
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow("SELECT cover_url, time_coracao, last_tilt_date FROM core.users WHERE id = 1")
        
        highlight = await conn.fetchrow("""
            SELECT jogo, mercado, odd_placed, pnl, placed_at 
            FROM core.fund_ledger 
            WHERE status = 'WON' ORDER BY pnl DESC, odd_placed DESC LIMIT 1
        """)
        
        recent_bets = await conn.fetch("SELECT status FROM core.fund_ledger WHERE status IN ('WON', 'LOST') ORDER BY settled_at DESC LIMIT 20")
        win_streak = 0
        for b in recent_bets:
            if b['status'] == 'WON': win_streak += 1
            else: break
            
        last_bad_league = await conn.fetchval("""
            SELECT placed_at FROM core.fund_ledger 
            WHERE jogo ILIKE '%Serie B%' OR jogo ILIKE '%Championship%' 
            ORDER BY placed_at DESC LIMIT 1
        """)
        
        now = datetime.now()
        last_tilt = user['last_tilt_date'] if user and user['last_tilt_date'] else now
        days_without_tilt = (now - last_tilt).days
        days_without_serie_b = (now - last_bad_league).days if last_bad_league else 99

        return {
            "cover_url": user['cover_url'] if user else None,
            "time_coracao": user['time_coracao'] if user else None,
            "gamification": {
                "win_streak": win_streak,
                "days_without_tilt": days_without_tilt,
                "days_without_serie_b": days_without_serie_b,
                "highlight": {
                    "jogo": highlight['jogo'] if highlight else "Aguardando Operação...",
                    "mercado": highlight['mercado'] if highlight else "-",
                    "odd": float(highlight['odd_placed']) if highlight else 0.0,
                    "pnl": float(highlight['pnl']) if highlight else 0.0,
                    "data": highlight['placed_at'].strftime("%d/%m/%Y") if highlight else "-"
                } if highlight else None
            }
        }

@router.post("/profile/update")
async def update_user_profile(req: ProfileUpdateReq):
    async with db.pool.acquire() as conn:
        if req.cover_url is not None:
            await conn.execute("UPDATE core.users SET cover_url = $1 WHERE id = 1", req.cover_url)
        if req.time_coracao is not None:
            await conn.execute("UPDATE core.users SET time_coracao = $1 WHERE id = 1", req.time_coracao)
    return {"success": True}

@router.post("/profile/reset-tilt")
async def reset_user_tilt():
    async with db.pool.acquire() as conn:
        await conn.execute("UPDATE core.users SET last_tilt_date = CURRENT_TIMESTAMP WHERE id = 1")
    return {"success": True, "message": "Contador de Tilt resetado."} 

@router.get("/catalog")
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

# =====================================================================
# SYNC BACKGROUND TASK
# =====================================================================
def run_full_pipeline_sync():
    import subprocess
    logger.info("⚙️ [SYNC] Recalibrando Matrix e IA (Background)...")
    matrix_path = Path(__file__).resolve().parent.parent / "workers" / "feature_engineering" / "matrix_builder.py"
    try:
        subprocess.run([sys.executable, str(matrix_path)], check=True, capture_output=True)
        logger.info("✅ [SYNC] Matrix Quantitativa reconstruída.")
    except Exception as e:
        logger.error(f"❌ [SYNC] Falha na Matrix: {e}")

@router.post("/sync-post-login")
async def trigger_post_login_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_full_pipeline_sync)
    return {"status": "syncing", "message": "Inicializando extratores HFT e motores neurais em background."}