# betgenius-backend/master_orchestrator.py

import subprocess
import sys
import time
import logging
from pathlib import Path

# Configuração do Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [ORCHESTRATOR] 🎩 %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

class MasterOrchestrator:
    """
    O Diretor de Operações do Fundo Quantitativo.
    Executa o DAG (Grafo Direcionado Acíclico) na ordem matemática perfeita.
    """
    def __init__(self):
        # A Ordem Absoluta de Execução
        self.pipeline = [
            # --- CAMADA 1: Fundações ---
            ("Global Elo Engine", "workers/feature_engineering/club_pedigree_engine.py"),
            ("Advanced Proxy xG", "workers/feature_engineering/proxy_xg_imputer.py"),
            
            # --- CAMADA 2: Derivadas Temporais e Psicológicas ---
            ("Temporal EWMA Engine", "workers/feature_engineering/temporal_features_engine.py"),
            ("Psychology & Frauds Engine", "workers/feature_engineering/psychology_engine.py"),
            ("Tension Index Engine", "workers/feature_engineering/tension_index_engine.py"),
            ("Market Respect Engine", "workers/feature_engineering/market_respect_engine.py"),
            ("Context Consolidator", "workers/feature_engineering/context_features_engine.py"),
            
            # --- CAMADA 3: Fusão e Cura Quantitativa ---
            ("Matrix Builder (Super JOIN)", "workers/feature_engineering/matrix_builder.py"),
            ("Data Homogenizer (KNN Imputer)", "homogenize_data.py"), # Ajuste o caminho se ele estiver noutra pasta
            ("Data Sanitizer (Parquet Vault)", "workers/brain/1_data_sanitizer.py"),
            
            # --- CAMADA 4: Treino dos Oráculos ---
            ("Alpha Oracle (1X2)", "workers/brain/2a_model_alpha.py"),
            ("Beta Oracle (O/U 2.5)", "workers/brain/2b_model_beta.py"),
            ("Gamma Oracle (BTTS)", "workers/brain/2c_model_gamma.py"),
            ("Delta Oracle (HT)", "workers/brain/2d_model_delta_ht.py"),
            ("Epsilon Oracle (Corners)", "workers/brain/2e_model_epsilon_corners.py"),
            ("Zeta Oracle (Cards)", "workers/brain/2f_model_zeta_cards.py"),
            ("Sigma Oracle (Shots)", "workers/brain/2g_model_sigma_shots.py"),
            ("Omega Oracle (Player Props)", "workers/brain/3a_model_omega_props.py"),
            ("Theta Oracle (Outrights)", "workers/brain/3b_model_theta_outrights.py"),
            
            # --- CAMADA 5: Produção HFT ---
            ##("Master Inference Engine", "engine/inference_engine.py")
        ]

    def _run_script(self, name: str, script_path: str) -> bool:
        """Executa um script em subprocesso isolado para garantir limpeza de memória RAM e DB."""
        full_path = BASE_DIR / script_path
        
        if not full_path.exists():
            logger.error(f"❌ ARQUIVO NÃO ENCONTRADO: {full_path}")
            return False

        logger.info(f"▶️ INICIANDO: {name}...")
        start_time = time.time()
        
        try:
            # Executa como um comando terminal independente. Ex: "python workers/..."
            result = subprocess.run(
                [sys.executable, str(full_path)], 
                check=True, 
                text=True, 
                capture_output=False # Mostra os logs diretamente no terminal em tempo real
            )
            elapsed_time = time.time() - start_time
            logger.info(f"✅ CONCLUÍDO: {name} (Tempo: {elapsed_time:.2f}s)\n")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"💀 FALHA CRÍTICA no módulo {name}. O Pipeline foi abortado para proteger a integridade dos dados.")
            logger.error(f"Código de erro: {e.returncode}")
            return False

    def run_pipeline(self):
        logger.info("=" * 80)
        logger.info(" 🚀 INICIANDO PIPELINE MONOLÍTICO DE INTELIGÊNCIA ARTIFICIAL ")
        logger.info("=" * 80)
        
        total_start_time = time.time()
        
        for name, script_path in self.pipeline:
            # Pausa breve para arrefecimento de I/O do disco e Banco de Dados
            time.sleep(1) 
            
            success = self._run_script(name, script_path)
            if not success:
                logger.error("🛑 PIPELINE INTERROMPIDO.")
                sys.exit(1)
                
        total_elapsed = time.time() - total_start_time
        logger.info("=" * 80)
        logger.info(f" 🏆 SUCESSO TOTAL! Pipeline executado sem falhas em {total_elapsed / 60:.2f} minutos.")
        logger.info("=" * 80)

if __name__ == "__main__":
    orchestrator = MasterOrchestrator()
    orchestrator.run_pipeline()