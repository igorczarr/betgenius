# betgenius-backend/brain/2g_model_sigma_shots.py

import sys
import os

if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import logging
import pandas as pd
import numpy as np
import xgboost as xgb
from scipy.stats import poisson
from sklearn.metrics import accuracy_score, log_loss, mean_absolute_error
import joblib
from pathlib import Path
from dotenv import load_dotenv

pd.set_option('future.no_silent_downcasting', True)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

class SigmaOracle:
    """
    O Oráculo Sigma (Especialista em Volume de Finalizações / Shots).
    Mapeia o xG, a agressividade e a postura tática para prever o 
    bombardeio total da partida e esmagar a linha de Over/Under 24.5 Chutes.
    """
    def __init__(self):
        self.data_vault_path = Path(__file__).parent / "data_vault" / "purified_tensors.parquet"
        self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # O ARSENAL: Foco massivo em Criação Ofensiva (xG) e Defesas Vazadas
        self.features = [
            'delta_elo', 'delta_tension', 'delta_market_respect',
            'delta_xg_micro', 'delta_xg_macro',
            'home_xg_for_ewma_micro', 'away_xg_for_ewma_micro',
            'home_xg_against_ewma_micro', 'away_xg_against_ewma_micro',
            'home_xg_for_ewma_macro', 'away_xg_for_ewma_macro',
            'home_aggression_ewma', 'away_aggression_ewma', 
            'home_fraudulent_defense', 'away_fraudulent_defense',
            'home_fraudulent_attack', 'away_fraudulent_attack',
            'delta_posicao', 'delta_pontos' # Desespero na tabela gera chutes de fora da área
        ]

    def train_and_evaluate(self):
        if not self.data_vault_path.exists():
            logger.error("❌ Data Vault não encontrado. Rode o 1_data_sanitizer.py.")
            sys.exit(1)
            
        logger.info("==================================================================")
        logger.info(" 🎯 INICIANDO FORJA DO ORÁCULO SIGMA (FÍSICA: CHUTES TOTAIS) ")
        logger.info("==================================================================")

        df = pd.read_parquet(self.data_vault_path)
        
        # Filtro de Sanidade: Apenas jogos válidos e com contagem de chutes registrada
        initial_len = len(df)
        df = df[(df['home_elo_before'] > 100) & (df['target_total_shots'] > 0)].copy()
        
        logger.info(f"📂 Matriz Carregada: {len(df)} jogos mapeados (Descartados {initial_len - len(df)} sem dados de chutes).")

        df = df.sort_values('match_date').reset_index(drop=True)
        
        # TIME-SERIES SPLIT: 80% Treino, 20% Teste
        split_idx = int(len(df) * 0.80)
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:].reset_index(drop=True)
        
        X_train = train_df[self.features]
        # Target: Total de Finalizações na Partida
        y_train = train_df['target_total_shots'] 
        
        X_test = test_df[self.features]
        y_test_exact = test_df['target_total_shots']
        
        # A Linha Ouro Asiática para Chutes costuma ser 24.5
        # 24 ou menos = Under / 25 ou mais = Over
        y_test_over245 = (y_test_exact > 24.5).astype(int)

        logger.info(f"⏳ Calibrando a Artilharia do Passado: {len(X_train)} partidas...")
        
        # O CÉREBRO: Poisson Regressor
        model = xgb.XGBRegressor(
            objective='count:poisson',
            n_estimators=450,
            learning_rate=0.015,
            max_depth=4,         
            min_child_weight=5,  
            subsample=0.85,
            colsample_bytree=0.85,
            reg_alpha=0.5,      
            reg_lambda=1.5,     
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)

        joblib.dump(model, self.models_dir / "sigma_oracle_shots.joblib")
        logger.info("✅ Oráculo Sigma (Chutes) Treinado e Preso no Cofre.")

        logger.info(f"\n⚡ Iniciando Auditoria Preditiva no Teste Cego ({len(X_test)} jogos)...")
        
        # Previsão da Média Exata de Chutes (Ex: 26.8 chutes)
        expected_shots = np.clip(model.predict(X_test), 5.0, 50.0)
        
        # MATEMÁTICA DE SINDICATO: Poisson CDF
        # A chance de sair ATÉ 24 chutes (Under 24.5)
        prob_under_245 = poisson.cdf(24, expected_shots)
        prob_over_245 = 1.0 - prob_under_245
        
        preds_proba = np.column_stack((prob_under_245, prob_over_245))
        preds_class = np.argmax(preds_proba, axis=1) # 0 = Under, 1 = Over
        
        mae = mean_absolute_error(y_test_exact, expected_shots)
        acc = accuracy_score(y_test_over245, preds_class)
        loss = log_loss(y_test_over245, preds_proba)

        # Calibração de Alta Confiança (Filtro Sniper > 58%)
        max_probs = np.max(preds_proba, axis=1)
        high_conf_mask = max_probs >= 0.58
        high_conf_acc = accuracy_score(y_test_over245[high_conf_mask], preds_class[high_conf_mask]) if np.any(high_conf_mask) else 0.0
        high_conf_volume = np.sum(high_conf_mask)

        over_mask = (preds_class == 1)
        under_mask = (preds_class == 0)

        acc_over = accuracy_score(y_test_over245[over_mask], preds_class[over_mask]) if np.any(over_mask) else 0.0
        acc_under = accuracy_score(y_test_over245[under_mask], preds_class[under_mask]) if np.any(under_mask) else 0.0

        logger.info("\n================= [ BOLETIM DO ORÁCULO SIGMA (CHUTES) ] =================")
        logger.info(f"🎯 Erro Absoluto Médio (MAE): Erra por {mae:.2f} chutes por jogo")
        logger.info(f"🎯 Acurácia Global (Over/Under 24.5): {acc * 100:.2f}%")
        logger.info(f"📉 Log-Loss: {loss:.4f}")
        logger.info("-------------------------------------------------------------------------")
        logger.info(f"🔥 ACURÁCIA EM ALTA CONFIANÇA (>58% prob): {high_conf_acc * 100:.2f}% (em {high_conf_volume} jogos)")
        logger.info("-------------------------------------------------------------------------")
        logger.info("📊 WIN-RATE POR MERCADO (Onde a IA decidiu atirar):")
        logger.info(f"   🎯 OVER 24.5 CHUTES:  {acc_over * 100:.1f}% de acerto (Volume: {np.sum(over_mask)})")
        logger.info(f"   🛡️ UNDER 24.5 CHUTES: {acc_under * 100:.1f}% de acerto (Volume: {np.sum(under_mask)})")
        logger.info("=========================================================================\n")

if __name__ == "__main__":
    SigmaOracle().train_and_evaluate()