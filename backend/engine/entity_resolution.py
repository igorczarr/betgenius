# betgenius-backend/engine/entity_resolution.py
import logging
from rapidfuzz import process, fuzz
import sys
from pathlib import Path

# Garante que o Python ache a pasta core
sys.path.append(str(Path(__file__).parent.parent))
from core.database import db

logger = logging.getLogger(__name__)

class EntityResolver:
    """
    Motor de Resolução de Entidades S-Tier.
    Conecta-se ao PostgreSQL real. Compara nomes caóticos com a nossa base oficial.
    Possui Modo de Auto-Descoberta: se a inteligência artificial não achar similaridade,
    ele batiza o time como uma nova entidade no ecossistema.
    """
    def __init__(self):
        self.canonical_names = []
        self.is_loaded = False
        self.match_threshold = 85.0 # Precisão mínima exigida de 85%

    async def load_mappings_from_db(self):
        logger.info("🔄 Carregando times do Data Warehouse...")
        try:
            # Puxa a lista real dos 459 times que você já tem no banco
            rows = await db.pool.fetch("SELECT canonical_name FROM core.teams")
            self.canonical_names = [r['canonical_name'] for r in rows]
            self.is_loaded = True
            logger.info(f"✅ Motor NLP Pronto: {len(self.canonical_names)} times canônicos na memória.")
        except Exception as e:
            logger.warning(f"Aviso ao carregar times (Banco offline ou vazio?): {e}")

    async def normalize_name(self, raw_name: str, is_pinnacle: bool = False) -> str:
        if not raw_name or str(raw_name).strip() == 'nan':
            return None

        if not self.is_loaded:
            await self.load_mappings_from_db()

        clean_name = raw_name.strip()

        # 1. Busca Exata (O(1) - Super rápido)
        if clean_name in self.canonical_names:
            return clean_name

        # 2. Busca Fuzzy (NLP - RapidFuzz)
        if self.canonical_names:
            best_match, score, _ = process.extractOne(
                clean_name, 
                self.canonical_names, 
                scorer=fuzz.WRatio
            )

            # Se a similaridade for alta, corrige o nome torto para o nome oficial
            if score >= self.match_threshold:
                return best_match

        # 3. MODO AUTO-DESCOBERTA (O Segredo da Escalabilidade)
        # O time não está no banco e não tem nome parecido? Então é um time novo (Ex: um time que acabou de subir da Série B).
        # Nós o aceitamos e deixamos o Worker (Ingester) fazer o INSERT INTO core.teams.
        logger.debug(f"🌱 Auto-Descoberta NLP: '{clean_name}' registrado como nova entidade.")
        self.canonical_names.append(clean_name)
        return clean_name

# Instância global do Resolver para ser usada em todos os Workers
entity_resolver = EntityResolver()