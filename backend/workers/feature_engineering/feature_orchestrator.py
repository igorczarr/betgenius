# betgenius-backend/workers/feature_engineering/feature_orchestrator.py

import asyncio
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# =====================================================================
# BLINDAGEM DE ENCODING E AMBIENTE
# =====================================================================
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [FEATURE-ORCHESTRATOR] %(message)s")
logger = logging.getLogger(__name__)

# Importando o exército de motores
from workers.feature_engineering.club_pedigree_engine import ClubPedigreeEngine
from workers.feature_engineering.temporal_features_engine import TemporalFeaturesEngine
from workers.feature_engineering.market_respect_engine import MarketRespectEngine
from workers.feature_engineering.psychology_engine import PsychologyEngine
from workers.feature_engineering.tension_index_engine import TensionIndexEngine
from workers.feature_engineering.matrix_builder import QuantMLBuilder

async def run_feature_pipeline():
    logger.info("================================================================")
    logger.info("🚀 INICIANDO PIPELINE DE FEATURE ENGINEERING (DATA LAKE -> ML)")
    logger.info("================================================================")

    try:
        # 1. Base Matemática (Priors e Elo Contínuo)
        pedigree = ClubPedigreeEngine()
        await pedigree.run_time_travel()

        # 2. Desempenho e Fisiologia (xG, PPDA, Descanso)
        temporal = TemporalFeaturesEngine()
        await temporal.run_temporal_engine()

        # 3. Leitura do Smart Money (Pinnacle/Asiáticas)
        market = MarketRespectEngine()
        await market.run_market_engine()

        # 4. Comportamento e Fraudes Estatísticas
        psycho = PsychologyEngine()
        await psycho.run_psychology_engine()

        # 5. Assimetrias de Motivação (Férias vs Desespero)
        tension = TensionIndexEngine()
        await tension.run_tension_simulator()

        # 6. O Liquidificador Final (Alpha Matrix / Feature Store)
        matrix = QuantMLBuilder()
        await matrix.build_matrix()

        logger.info("================================================================")
        logger.info("🏆 PIPELINE CONCLUÍDO! A FEATURE STORE ESTÁ PRONTA PARA A INTELIGÊNCIA ARTIFICIAL.")
        logger.info("================================================================")

    except Exception as e:
        logger.error(f"❌ FALHA CATASTRÓFICA NO PIPELINE DE FEATURES: {e}")

if __name__ == "__main__":
    asyncio.run(run_feature_pipeline())