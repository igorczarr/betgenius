# betgenius-backend/brain/2e_model_epsilon_corners.py

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

class EpsilonOracle:
    """
    O Oráculo Épsilon (Especialista em Escanteios / Corners).
    Regressor de Poisson que lê a Pressão e a Física do jogo
    para prever a soma total de cantos e achar valor no Over 9.5.
    """
    def __init__(self):
        self.data_vault_path = Path(__file__).parent / "data_vault" / "purified_tensors.parquet"
        self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # O ARSENAL: Foco em Volume Ofensivo e Tensão (Gera bolas rebatidas)
        self.features = [
            'delta_elo', 'delta_tension', 
            'delta_xg_micro', 'delta_xg_macro',
            'home_xg_for_ewma_micro', 'away_xg_for_ewma_micro',
            'home_xg_for_ewma_macro', 'away_xg_for_ewma_macro',
            'home_aggression_ewma', 'away_aggression_ewma', 
            'home_fraudulent_defense', 'away_fraudulent_defense',
            'home_market_respect', 'away_market_respect'
        ]

    def train_and_evaluate(self):
        if not self.data_vault_path.exists():
            logger.error("❌ Data Vault não encontrado. Rode o 1_data_sanitizer.py.")
            sys.exit(1)
            
        logger.info("==================================================================")
        logger.info(" 📐 INICIANDO FORJA DO ORÁCULO ÉPSILON (FÍSICA: ESCANTEIOS) ")
        logger.info("==================================================================")

        df = pd.read_parquet(self.data_vault_path)
        
        # Filtro de Sanidade: Precisamos de jogos que registraram escanteios
        initial_len = len(df)
        df = df[(df['home_elo_before'] > 100) & (df['target_total_corners'] > 0)].copy()
        
        logger.info(f"📂 Matriz Carregada: {len(df)} jogos físicos disponíveis (Descartados {initial_len - len(df)} sem dados de cantos).")

        # Ordenação Cronológica Estrita
        df = df.sort_values('match_date').reset_index(drop=True)
        
        # TIME-SERIES SPLIT: 80% Treino, 20% Teste
        split_idx = int(len(df) * 0.80)
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:].reset_index(drop=True)
        
        X_train = train_df[self.features]
        # Target: Soma de Escanteios
        y_train = train_df['target_total_corners'] 
        
        X_test = test_df[self.features]
        y_test_exact = test_df['target_total_corners']
        
        # Criamos o Target de Classificação para Avaliação (Over 9.5 Corners = 10 ou mais)
        y_test_over95 = (y_test_exact > 9.5).astype(int)

        logger.info(f"⏳ Treinando a Física do Passado: {len(X_train)} partidas...")
        
        # O CÉREBRO: Poisson Regressor (Ideal para contagem de eventos discretos como escanteios)
        model = xgb.XGBRegressor(
            objective='count:poisson',
            n_estimators=450,
            learning_rate=0.015,
            max_depth=4,         
            min_child_weight=5,  
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.5,      
            reg_lambda=2.0,     
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)

        joblib.dump(model, self.models_dir / "epsilon_oracle_corners.joblib")
        logger.info("✅ Oráculo Épsilon (Escanteios) Treinado e Preso no Cofre.")

        logger.info(f"\n⚡ Iniciando Auditoria Preditiva no Teste Cego ({len(X_test)} jogos)...")
        
        # Previsão da Média Exata de Escanteios (Ex: 10.4 cantos)
        expected_corners = np.clip(model.predict(X_test), 1.0, 25.0)
        
        # MATEMÁTICA DE SINDICATO: Poisson CDF
        # A chance de sair ATÉ 9 escanteios (Under 9.5)
        prob_under_95 = poisson.cdf(9, expected_corners)
        # A chance de sair 10 ou MAIS escanteios (Over 9.5)
        prob_over_95 = 1.0 - prob_under_95
        
        preds_proba = np.column_stack((prob_under_95, prob_over_95))
        preds_class = np.argmax(preds_proba, axis=1) # 0 = Under, 1 = Over
        
        # MÉTRICAS
        mae = mean_absolute_error(y_test_exact, expected_corners)
        acc = accuracy_score(y_test_over95, preds_class)
        loss = log_loss(y_test_over95, preds_proba)

        # CALIBRAÇÃO: Como ele lida com a pressão da Alta Confiança no Mercado de Cantos? (> 58%)
        max_probs = np.max(preds_proba, axis=1)
        high_conf_mask = max_probs >= 0.58
        high_conf_acc = accuracy_score(y_test_over95[high_conf_mask], preds_class[high_conf_mask]) if np.any(high_conf_mask) else 0.0
        high_conf_volume = np.sum(high_conf_mask)

        over_mask = (preds_class == 1)
        under_mask = (preds_class == 0)

        acc_over = accuracy_score(y_test_over95[over_mask], preds_class[over_mask]) if np.any(over_mask) else 0.0
        acc_under = accuracy_score(y_test_over95[under_mask], preds_class[under_mask]) if np.any(under_mask) else 0.0

        logger.info("\n================= [ BOLETIM DO ORÁCULO ÉPSILON (ESCANTEIOS) ] =================")
        logger.info(f"🎯 Erro Absoluto Médio (MAE): Erra por {mae:.2f} escanteios por jogo")
        logger.info(f"🎯 Acurácia Global (Over/Under 9.5): {acc * 100:.2f}%")
        logger.info(f"📉 Log-Loss: {loss:.4f}")
        logger.info("-------------------------------------------------------------------------------")
        logger.info(f"🔥 ACURÁCIA EM ALTA CONFIANÇA (>58% prob): {high_conf_acc * 100:.2f}% (em {high_conf_volume} jogos)")
        logger.info("-------------------------------------------------------------------------------")
        logger.info("📊 WIN-RATE POR MERCADO (Onde a IA decidiu atirar):")
        logger.info(f"   🚩 OVER 9.5 CANTOS:  {acc_over * 100:.1f}% de acerto (Volume: {np.sum(over_mask)})")
        logger.info(f"   🛑 UNDER 9.5 CANTOS: {acc_under * 100:.1f}% de acerto (Volume: {np.sum(under_mask)})")
        logger.info("===============================================================================\n")

if __name__ == "__main__":
    EpsilonOracle().train_and_evaluate()