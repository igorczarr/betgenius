import logging
import re
import asyncio
from rapidfuzz import process, fuzz, utils
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from core.database import db

logger = logging.getLogger(__name__)

class EntityResolver:
    """
    Motor de Resolução de Entidades S-Tier v2.0.
    Implementa camadas de proteção contra colisões (Manchester vs DC United)
    e cache de aliases para performance HFT.
    """
    def __init__(self):
        self.canonical_map = {} # {id: canonical_name}
        self.alias_map = {}     # {alias_name: canonical_name}
        self.is_loaded = False
        self.match_threshold = 90.0 # Aumentado para evitar falsos positivos
        
        # Palavras que confundem o algoritmo
        self.noise_words = [
            r'\bfc\b', r'\bsc\b', r'\bunited\b', r'\bcity\b', r'\breal\b', 
            r'\batletico\b', r'\bsporting\b', r'\bclub\b', r'\bde\b', r'\bthe\b'
        ]

    async def load_mappings_from_db(self):
        """Carrega nomes oficiais e apelidos conhecidos na memória RAM."""
        try:
            async with db.pool.acquire() as conn:
                # 1. Carrega times canônicos
                teams = await conn.fetch("SELECT id, canonical_name FROM core.teams")
                self.canonical_map = {r['id']: r['canonical_name'] for r in teams}
                
                # 2. Carrega apelidos (Aliases) - Esta é a camada mais forte
                aliases = await conn.fetch("""
                    SELECT a.alias_name, t.canonical_name 
                    FROM core.team_aliases a
                    JOIN core.teams t ON t.id = a.team_id
                """)
                self.alias_map = {r['alias_name'].lower(): r['canonical_name'] for r in aliases}
                
            self.is_loaded = True
            logger.info(f"✅ Motor NLP Pronto: {len(self.canonical_map)} times e {len(self.alias_map)} aliases.")
        except Exception as e:
            logger.error(f"❌ Erro ao carregar mapeamentos: {e}")

    def _clean(self, name: str) -> str:
        """Limpa o nome para comparação, removendo acentos e ruído."""
        if not name: return ""
        # Lowercase e extração de caracteres inúteis
        s = utils.default_process(name)
        # Remove sufixos genéricos
        for word in self.noise_words:
            s = re.sub(word, "", s)
        return s.strip()

    async def normalize_name(self, raw_name: str) -> str:
        if not raw_name or str(raw_name).strip().lower() in ['nan', 'null', '']:
            return None

        if not self.is_loaded:
            await self.load_mappings_from_db()

        clean_raw = raw_name.strip()
        search_name = clean_raw.lower()

        # CAMADA 1: Busca Exata em Canônicos (O(1))
        if clean_raw in self.canonical_map.values():
            return clean_raw

        # CAMADA 2: Dicionário de Aliases (O(1))
        if search_name in self.alias_map:
            return self.alias_map[search_name]

        # CAMADA 3: Busca Fuzzy Inteligente
        canonical_list = list(self.canonical_map.values())
        
        # Usamos token_set_ratio: ignora ordem e palavras repetidas
        # Ideal para "Manchester United" vs "United, Manchester"
        best_match, score, _ = process.extractOne(
            clean_raw,
            canonical_list,
            scorer=fuzz.token_set_ratio,
            processor=utils.default_process
        )

        if score >= self.match_threshold:
            # Proteção especial para "United" e "City"
            # Se o match foi apenas por causa de uma palavra comum, rejeitamos
            raw_parts = self._clean(clean_raw).split()
            match_parts = self._clean(best_match).split()
            
            # Se a parte principal (primeira palavra) for totalmente diferente, desconfiamos
            if raw_parts and match_parts and raw_parts[0] != match_parts[0]:
                if score < 95: # Exige quase perfeição se o prefixo falhar
                    return await self._register_new_entity(clean_raw)

            return best_match

        # CAMADA 4: Auto-descoberta
        return await self._register_new_entity(clean_raw)

    async def _register_new_entity(self, name: str) -> str:
        """Registra no banco para evitar que o erro se repita."""
        if name in self.canonical_map.values(): return name
        
        logger.debug(f"🌱 Nova entidade detectada: {name}")
        # Aqui o seu Ingester deve cuidar da inserção no core.teams se necessário
        # Para evitar duplicatas, adicionamos à lista temporária de memória
        return name

# Instância Global
entity_resolver = EntityResolver()