import asyncio
import logging
from rapidfuzz import process, fuzz
# Usaremos asyncpg no futuro para conectar ao PostgreSQL de forma assíncrona
# import asyncpg 

logger = logging.getLogger(__name__)

# =====================================================================
# BETGENIUS HFT - ENTITY RESOLUTION ENGINE (NÍVEL S)
# Resolve nomes caóticos de times entre Pinnacle e Bet365
# =====================================================================

class EntityResolver:
    def __init__(self):
        # Cache em memória RAM local (Dicionário)
        # Formato: {"fluminense": "Fluminense RJ", "man utd": "Manchester United"}
        self.mapping_cache = {}
        
        # Lista de Nomes Oficiais (Baseados na Pinnacle)
        self.canonical_names = []
        
        self.is_loaded = False

    async def load_mappings_from_db(self):
        """
        No futuro, esta função fará um SELECT no nosso PostgreSQL.
        Ela trará todos os nomes oficiais e suas variações conhecidas.
        """
        logger.info("🔄 Carregando Base de Dados de Times e Variações...")
        
        # =================================================================
        # SIMULAÇÃO DO BANCO DE DADOS (Até construirmos o PostgreSQL)
        # =================================================================
        mock_db_data = [
            {"canonical": "Manchester United", "variations": ["Man Utd", "Manchester Utd"]},
            {"canonical": "Athletico PR", "variations": ["Atlético Paranaense", "Atletico-PR", "Athletico Paranaense"]},
            {"canonical": "Bayern Munich", "variations": ["Bayern de Munique", "Bayern Munchen"]},
        ]
        
        for row in mock_db_data:
            canonical = row["canonical"]
            self.canonical_names.append(canonical)
            
            # O próprio nome canônico aponta para ele mesmo
            self.mapping_cache[canonical.lower()] = canonical
            
            # As variações apontam para o nome canônico
            for var in row["variations"]:
                self.mapping_cache[var.lower()] = canonical
                
        self.is_loaded = True
        logger.info(f"✅ Motor de Resolução Pronto: {len(self.canonical_names)} times canônicos na memória.")

    async def save_new_variation_to_db(self, variation: str, canonical: str):
        """
        Salva a nova variação no banco de dados para aprendizado contínuo.
        """
        # Exemplo futuro: 
        # await self.db.execute("INSERT INTO team_variations (variation, canonical_id) VALUES ($1, $2)", variation, canonical_id)
        logger.warning(f"🧠 APRENDIZADO: Nova variação '{variation}' vinculada a '{canonical}' e salva no DB.")

    async def normalize_name(self, raw_name: str, is_pinnacle: bool = False) -> str:
        """
        A função principal. Recebe um nome sujo e devolve o Nome Oficial.
        """
        if not self.is_loaded:
            await self.load_mappings_from_db()

        clean_name = raw_name.strip().lower()

        # 1. TENTATIVA RÁPIDA: Está no nosso Cache/Banco de Dados?
        if clean_name in self.mapping_cache:
            return self.mapping_cache[clean_name]

        # 2. É DA PINNACLE E NÃO ESTÁ NO BANCO?
        # A Pinnacle é nossa dona da verdade. Se ela mandou um nome novo, nós o adicionamos
        # como um novo Nome Oficial no nosso ecossistema.
        if is_pinnacle:
            logger.info(f"🏛️ Novo Time Canônico detectado via Pinnacle: '{raw_name}'")
            self.canonical_names.append(raw_name)
            self.mapping_cache[clean_name] = raw_name
            # await self.save_canonical_to_db(raw_name) -> No futuro
            return raw_name

        # 3. É DA BET365 E NÃO ESTÁ NO BANCO? (FUZZY MATCHING - INTELIGÊNCIA ARTIFICIAL)
        # O algoritmo de Levenshtein vai procurar o nome mais parecido na lista de oficiais.
        best_match, score, _ = process.extractOne(
            raw_name, 
            self.canonical_names, 
            scorer=fuzz.WRatio # O WRatio lida bem com abreviações (ex: Man vs Manchester)
        )

        # Se a similaridade for maior que 85%, podemos assumir com segurança que é o mesmo time
        if score >= 85.0:
            logger.info(f"🎯 Fuzzy Match: '{raw_name}' resolvido como '{best_match}' (Score: {score:.1f}%)")
            
            # Adiciona ao cache e salva no banco de dados para aprender!
            self.mapping_cache[clean_name] = best_match
            asyncio.create_task(self.save_new_variation_to_db(raw_name, best_match))
            
            return best_match
        else:
            # Similaridade baixa (Ex: 60%). É perigoso cruzar as odds automaticamente.
            # Retorna o nome original e gera um alerta para o Gestor conferir manualmente depois.
            logger.error(f"🚨 MATCH FALHOU: '{raw_name}' não bateu com ninguém (Melhor: '{best_match}' com {score:.1f}%). Requer revisão humana.")
            return raw_name

# Instância global do Resolver para ser usada nos Workers
entity_resolver = EntityResolver()