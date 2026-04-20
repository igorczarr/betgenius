# betgenius-backend/core/database.py
import asyncpg
import logging
from core.config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Gerenciador de Pool de Conexões Assíncronas para PostgreSQL (Neon.tech).
    Garante máxima performance reaproveitando conexões no nível da máquina.
    """
    def __init__(self):
        self.pool = None

    async def connect(self):
        if not self.pool:
            try:
                # O Neon.tech usa PGBouncer nativamente, então mantemos o pool otimizado
                self.pool = await asyncpg.create_pool(
                    dsn=settings.POSTGRES_URL,
                    min_size=5,
                    max_size=20,
                    command_timeout=60,
                )
                logger.info("🗄️ [DB] Connection Pool estabelecido com PostgreSQL (Neon.tech).")
            except Exception as e:
                logger.critical(f"❌ [DB] Falha crítica ao conectar ao PostgreSQL: {e}")
                raise e

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            logger.info("🗄️ [DB] Connection Pool encerrado com segurança.")

# Instância Singleton para todo o ecossistema importar
db = DatabaseManager()