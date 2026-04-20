# betgenius-backend/core/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# =====================================================================
# BETGENIUS HFT - CONFIGURATION & ENVIRONMENT MANAGER
# =====================================================================

# 1. Rastreamento Absoluto (Imune a erros de terminal)
# Pega o caminho deste arquivo (config.py), volta uma pasta (core), volta outra (backend)
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

# Força o carregamento exato daquele arquivo .env
load_dotenv(dotenv_path=ENV_PATH)

class Settings:
    # CHAVES DA API
    ODDS_API_KEY: str = os.getenv("ODDS_API_KEY")
    
    # Se usar o esquema de Pool, pega a string separada por vírgulas e transforma em Lista
    _pool_str = os.getenv("ODDS_API_KEY_POOL", "")
    ODDS_API_KEY_POOL: list = [k.strip() for k in _pool_str.split(",") if k.strip()]

    # BANCO DE DADOS E MEMÓRIA
    POSTGRES_URL: str = os.getenv("POSTGRES_URL")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    def __init__(self):
        # Validações de Segurança (Fail-Fast)
        if not self.ODDS_API_KEY and not self.ODDS_API_KEY_POOL:
            raise ValueError(f"❌ CRÍTICO: Nenhuma ODDS_API_KEY encontrada! Verifique o arquivo em: {ENV_PATH}")
        
        if not self.POSTGRES_URL:
            raise ValueError(f"❌ CRÍTICO: Nenhuma POSTGRES_URL encontrada! Verifique o arquivo em: {ENV_PATH}")

# Instância global
settings = Settings()