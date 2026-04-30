# betgenius-backend/routers/auth.py

import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import jwt
import pyotp
from passlib.context import CryptContext
from core.database import db

# Configurações JWT
SECRET_KEY = os.environ.get("JWT_SECRET", "BetGenius_Quant_Super_Secret_Key_2026_!@#")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 Dias

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])

# =====================================================================
# SCHEMAS
# =====================================================================
class LoginRequest(BaseModel):
    email: str
    senha: Optional[str] = None
    token_2fa: Optional[str] = None

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# =====================================================================
# ROTA DE LOGIN HÍBRIDO S-TIER
# =====================================================================
@router.post("/login")
async def login_institucional(req: LoginRequest):
    identifier = req.email.strip()
    
    # Bypass para Conta Super Admin Fixa
    if identifier.lower() == 'igor@betgenius.fund' and req.senha == 'admin123':
        token = create_access_token({"sub": "1", "email": identifier, "role": "Lead Quant Manager"})
        return {
            "success": True, "token": token,
            "user": {"id": 1, "name": "Igor Santos.", "role": "Lead Quant Manager", "email": identifier, "avatar": "", "modo": "REAL", "accessLevel": 4}
        }
        
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow("""
            SELECT id, nome, role, modo_operacao as modo, avatar_url as avatar, 
                   password_hash, auth_mode, totp_secret, titulo, email
            FROM core.users 
            WHERE (LOWER(email) = LOWER($1) OR gestor_id = $1) AND account_status = 'ACTIVE'
        """, identifier)

        if not user:
            raise HTTPException(status_code=401, detail="Credenciais inválidas ou Acesso Negado.")

        # FLUXO 1: PASSWORDLESS (GOOGLE AUTHENTICATOR)
        if user['auth_mode'] == 'authenticator':
            if not req.senha and not req.token_2fa:
                raise HTTPException(status_code=401, detail="Token do Authenticator exigido para este usuário.")
            
            codigo_fornecido = req.token_2fa or req.senha
            if not user['totp_secret']:
                raise HTTPException(status_code=500, detail="Erro Crítico: Cofre TOTP não configurado.")

            totp = pyotp.TOTP(user['totp_secret'])
            if not totp.verify(codigo_fornecido):
                raise HTTPException(status_code=401, detail="Token Authenticator expirado ou inválido.")
                
        # FLUXO 2: SENHA TRADICIONAL
        else:
            if not req.senha:
                raise HTTPException(status_code=401, detail="Senha exigida para este usuário.")
            
            # Verificação com BCrypt (ou direto para fins de legado se o hash for plain text)
            try:
                valid = pwd_context.verify(req.senha, user['password_hash'])
            except Exception:
                valid = (req.senha == user['password_hash'])
                
            if not valid:
                raise HTTPException(status_code=401, detail="Credenciais inválidas ou Acesso Negado.")

        token = create_access_token(data={"sub": str(user['id']), "email": user['email'], "role": user['titulo']})
        await conn.execute("UPDATE core.users SET last_login_at = CURRENT_TIMESTAMP WHERE id = $1", user['id'])

        return {
            "success": True,
            "token": token,
            "user": {
                "id": user['id'],
                "name": user['nome'],
                "role": user['titulo'] or user['role'],
                "avatar": user['avatar'],
                "modo": user['modo']
            }
        }