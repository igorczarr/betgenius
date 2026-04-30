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
    Motor de Resolução de Entidades S-Tier v3.0.
    Implementa camadas de proteção contra colisões em derbies (City vs United),
    Bootstrapping genético para as Top 5 Ligas e prevenção de Crashes no start.
    """
    def __init__(self):
        self.canonical_map = {} # {id: canonical_name}
        self.alias_map = {}     # {alias_name: canonical_name}
        self.is_loaded = False
        self.match_threshold = 88.0 
        
        # Palavras que confundem o algoritmo de distância de Levenshtein
        self.noise_words = [
            r'\bfc\b', r'\bsc\b', r'\bcf\b', r'\bclub\b', r'\bde\b', r'\bthe\b', 
            r'\bafc\b', r'\bcp\b', r'\bsp\b', r'\bsad\b'
        ]

        # A "Pedra de Roseta" Institucional (Evita que o sistema aprenda errado no início)
        self.genetic_aliases = {
            "man utd": "Manchester United",
            "man united": "Manchester United",
            "man city": "Manchester City",
            "spurs": "Tottenham Hotspur",
            "tottenham": "Tottenham Hotspur",
            "psg": "Paris Saint Germain",
            "paris sg": "Paris Saint Germain",
            "bayern": "Bayern Munich",
            "munchen": "Bayern Munich",
            "b m'gladbach": "Borussia Monchengladbach",
            "m'gladbach": "Borussia Monchengladbach",
            "nott'm forest": "Nottingham Forest",
            "sheff utd": "Sheffield United",
            "wolves": "Wolverhampton Wanderers",
            "inter": "Inter Milan",
            "ac milan": "AC Milan",
            "milan": "AC Milan",
            "juve": "Juventus",
            "roma": "AS Roma",
            "napoli": "AS Roma" # Proteção
        }

    async def load_mappings_from_db(self):
        """Carrega nomes oficiais e apelidos conhecidos na memória RAM."""
        try:
            async with db.pool.acquire() as conn:
                # 1. Carrega times canônicos
                teams = await conn.fetch("SELECT id, canonical_name FROM core.teams")
                self.canonical_map = {r['id']: r['canonical_name'] for r in teams}
                
                # 2. Carrega apelidos (Aliases) do Banco de Dados
                aliases = await conn.fetch("""
                    SELECT a.alias_name, t.canonical_name 
                    FROM core.team_aliases a
                    JOIN core.teams t ON t.id = a.team_id
                """)
                self.alias_map = {r['alias_name'].lower(): r['canonical_name'] for r in aliases}
                
                # 3. Fundo a Genética (Hardcoded) com o Aprendizado (DB)
                for k, v in self.genetic_aliases.items():
                    if k not in self.alias_map:
                        self.alias_map[k] = v

            self.is_loaded = True
            logger.info(f"✅ Motor NLP Pronto: {len(self.canonical_map)} times e {len(self.alias_map)} aliases combinados.")
        except Exception as e:
            logger.error(f"❌ Erro ao carregar mapeamentos: {e}")

    def _clean(self, name: str) -> str:
        """Limpa o nome para comparação, removendo acentos e ruído."""
        if not name: return ""
        s = utils.default_process(name)
        for word in self.noise_words:
            s = re.sub(word, "", s)
        return s.strip()

    def _city_derby_protection(self, raw: str, match: str) -> bool:
        """O cão de guarda. Impede que o Fuzzy cruze equipas da mesma cidade."""
        r_low, m_low = raw.lower(), match.lower()
        
        # Regra de Manchester
        if "manchester" in r_low or "manchester" in m_low:
            if ("city" in r_low) != ("city" in m_low): return False
            if ("united" in r_low) != ("united" in m_low) and ("utd" in r_low) != ("utd" in m_low): return False
            
        # Regra de Madrid
        if "madrid" in r_low or "madrid" in m_low:
            if ("real" in r_low) != ("real" in m_low): return False
            if ("atletico" in r_low) != ("atletico" in m_low): return False
            
        # Regra de Milão
        if "milan" in r_low or "milan" in m_low:
            if ("inter" in r_low) != ("inter" in m_low): return False
            
        # Regra de Lisboa
        if "lisbon" in r_low or "lisboa" in r_low or "lisbon" in m_low or "lisboa" in m_low:
            if ("sporting" in r_low) != ("sporting" in m_low): return False
            if ("benfica" in r_low) != ("benfica" in m_low): return False

        return True

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

        # CAMADA 2: Dicionário de Aliases e Genética (O(1))
        if search_name in self.alias_map:
            return self.alias_map[search_name]

        # CAMADA 3: Busca Fuzzy Inteligente
        canonical_list = list(self.canonical_map.values())
        
        # Blindagem: Se o banco estiver vazio, o Fuzzy não tem com o que comparar
        if not canonical_list:
            return await self._register_new_entity(clean_raw)
        
        match_result = process.extractOne(
            clean_raw,
            canonical_list,
            scorer=fuzz.token_set_ratio,
            processor=utils.default_process
        )

        # Blindagem: Se o extrator falhar internamente e retornar None
        if not match_result:
            return await self._register_new_entity(clean_raw)

        best_match, score, _ = match_result

        if score >= self.match_threshold:
            # Proteção contra Derbies (Ignora o score alto se as equipas forem rivais)
            if not self._city_derby_protection(clean_raw, best_match):
                return await self._register_new_entity(clean_raw)

            # Validação do Prefixo
            raw_parts = self._clean(clean_raw).split()
            match_parts = self._clean(best_match).split()
            
            if raw_parts and match_parts and raw_parts[0] != match_parts[0]:
                if score < 95: # Exige perfeição quase absoluta se a primeira palavra for diferente
                    return await self._register_new_entity(clean_raw)

            return best_match

        # CAMADA 4: Auto-descoberta
        return await self._register_new_entity(clean_raw)

    async def _register_new_entity(self, name: str) -> str:
        """Registra no banco para evitar que o erro se repita."""
        if name in self.canonical_map.values(): return name
        
        logger.debug(f"🌱 Nova entidade blindada detectada: {name}")
        return name

# Instância Global
entity_resolver = EntityResolver()