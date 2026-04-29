# betgenius-backend/workers/feature_engineering/feature_orchestrator.py

import asyncio
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# =====================================================================
# BLINDAGEM DE ENCODING PARA WINDOWS E CARREGAMENTO DO .ENV
# =====================================================================
if sys.platform == "win32":
    import os
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        import sys
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [MASTER-ORCHESTRATOR] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

# =====================================================================
# IMPORTANDO O EXÉRCITO (DATA LAKE + FEATURE ENGINES)
# =====================================================================
# 1. Ingestores Base
from workers.api_integrations.soccerdata_odds_baseline import SoccerDataOddsBaseline
from workers.api_integrations.fbref_master_ingester import FBrefMasterIngester
from workers.api_integrations.clubelo_historical_updater import ClubEloDailyUpdater

# 2. Engenharia e Projeções
from workers.feature_engineering.club_pedigree_engine import GlobalEloEngine 
from workers.feature_engineering.proxy_xg_imputer import AdvancedProxyXGImputer
from workers.feature_engineering.temporal_features_engine import TemporalFeaturesEngine
from workers.feature_engineering.market_respect_engine import MarketRespectEngine
from workers.feature_engineering.psychology_engine import PsychologyEngine
from workers.feature_engineering.tension_index_engine import TensionIndexEngine
from workers.feature_engineering.matrix_builder import QuantMLBuilder

async def run_feature_pipeline():
    logger.info("=======================================================================")
    logger.info("🚀 INICIANDO MEGA-PIPELINE INSTITUCIONAL (EXTRAÇÃO -> IA -> MATRIX)")
    logger.info("=======================================================================")

    try:
        # ---------------------------------------------------------
        # STAGE 1: INGESTÃO DE DADOS (O COMBUSTÍVEL)
        # ---------------------------------------------------------
        logger.info("\n[STAGE 1/4] INGESTÃO DE DADOS EXTERNOS...")
        
        baseline_odds = SoccerDataOddsBaseline()
        await baseline_odds.run()
        
        fbref_ingester = FBrefMasterIngester()
        await fbref_ingester.run()
        
        clubelo = ClubEloDailyUpdater()
        await clubelo.run()

        # ---------------------------------------------------------
        # STAGE 2: PROCESSAMENTO BASE (FORÇA E EXPECTATIVA)
        # ---------------------------------------------------------
        logger.info("\n[STAGE 2/4] PROCESSAMENTO DE FORÇA E EXPECTATIVA (PRIORS)...")
        
        pedigree = GlobalEloEngine()
        await pedigree.run_daily_update() # Atualizado para o nome correto

        xg_imputer = AdvancedProxyXGImputer()
        await xg_imputer.run_imputation() # Fundamental rodar antes do Temporal para preencher buracos

        # ---------------------------------------------------------
        # STAGE 3: ENGENHARIA DE VARIÁVEIS AVANÇADAS (AS ASSIMETRIAS)
        # ---------------------------------------------------------
        logger.info("\n[STAGE 3/4] ENGENHARIA NEURAL E COMPORTAMENTAL...")
        
        temporal = TemporalFeaturesEngine()
        await temporal.run_temporal_engine()

        market = MarketRespectEngine()
        await market.run_market_engine()

        psycho = PsychologyEngine()
        await psycho.run_psychology_engine()

        tension = TensionIndexEngine()
        await tension.run_tension_simulator()

        # ---------------------------------------------------------
        # STAGE 4: COMPILAÇÃO DA FEATURE STORE
        # ---------------------------------------------------------
        logger.info("\n[STAGE 4/4] FORJANDO A ALPHA MATRIX (FEATURE STORE)...")
        
        matrix = QuantMLBuilder()
        await matrix.build_matrix()

        logger.info("=======================================================================")
        logger.info("🏆 PIPELINE SUPREMO CONCLUÍDO! O SEU FUNDO ESTÁ 100% SINCRONIZADO.")
        logger.info("=======================================================================")

    except Exception as e:
        logger.critical(f"❌ FALHA CATASTRÓFICA NO PIPELINE MESTRE: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run_feature_pipeline())