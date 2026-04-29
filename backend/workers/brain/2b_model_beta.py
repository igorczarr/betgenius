# betgenius-backend/brain/2b_model_beta.py

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
from sklearn.metrics import accuracy_score, log_loss, classification_report
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

class BetaOracle:
    """
    O Oráculo Beta (Over/Under 2.5) - Nível HFT.
    Abandona a regressão contínua. Age como um Classificador Binário Direto.
    Otimizado para encontrar o Caos (Over) ou a Ordem (Under).
    """
    def __init__(self):
        self.data_vault_path = Path(__file__).parent / "data_vault" / "purified_tensors.parquet"
        self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # Arsenal com foco em Agressividade, Caos e Falhas Defensivas
        self.features = [
            'delta_elo', 'delta_wage_pct', 'delta_pontos', 'delta_posicao', 
            'delta_market_respect', 'delta_tension', 
            'delta_xg_micro', 'delta_xg_macro',
            'home_xg_for_ewma_micro', 'home_xg_against_ewma_micro',
            'away_xg_for_ewma_micro', 'away_xg_against_ewma_micro',
            'home_aggression_ewma', 'away_aggression_ewma', 
            'home_clean_sheet_streak', 'away_clean_sheet_streak',
            'home_fraudulent_defense', 'home_fraudulent_attack',
            'away_fraudulent_defense', 'away_fraudulent_attack'
        ]

    def train_and_evaluate(self):
        if not self.data_vault_path.exists():
            logger.error("❌ Data Vault não encontrado.")
            sys.exit(1)
            
        logger.info("==================================================================")
        logger.info(" ⚽ INICIANDO FORJA DO ORÁCULO BETA (OVER/UNDER BINARY CLASSIFIER)")
        logger.info("==================================================================")

        df = pd.read_parquet(self.data_vault_path)
        
        # Filtro de Sanidade Base
        df = df[df['home_elo_before'] > 100].copy()
        
        logger.info(f"📂 Matriz Carregada: {len(df)} jogos históricos disponíveis.")

        # Ordenação Cronológica (Zero Vazamento)
        df = df.sort_values('match_date').reset_index(drop=True)
        
        # TIME-SERIES SPLIT: 80% Treino, 20% Teste Cego
        split_idx = int(len(df) * 0.80)
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:].reset_index(drop=True)
        
        X_train = train_df[self.features]
        # 🚨 O ALVO AGORA É BINÁRIO: 1 (Over 2.5) ou 0 (Under 2.5)
        y_train = train_df['target_over_25'] 
        
        X_test = test_df[self.features]
        y_test = test_df['target_over_25']

        logger.info(f"⏳ Treinando com o Caos do Passado: {len(X_train)} jogos...")
        
        # O CÉREBRO: Classificador Logístico
        model = xgb.XGBClassifier(
            objective='binary:logistic',
            eval_metric='logloss',
            n_estimators=500,
            learning_rate=0.015,
            max_depth=5,         # Mais profundidade para cruzar xG com Fraude Defensiva
            min_child_weight=3,  
            subsample=0.85,
            colsample_bytree=0.85,
            reg_alpha=0.1,      
            reg_lambda=1.0,     
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)

        joblib.dump(model, self.models_dir / "beta_oracle_ou25.joblib")
        logger.info("✅ Oráculo Beta (Binary) Treinado e Preso no Cofre.")

        logger.info(f"\n⚡ Iniciando Auditoria Preditiva no Teste Cego ({len(X_test)} jogos)...")
        
        # Retorna [Probabilidade_Under, Probabilidade_Over]
        preds_proba = model.predict_proba(X_test)
        prob_over = preds_proba[:, 1] 
        
        # Escolha Seca (Threshold 50%)
        preds_class = np.where(prob_over > 0.50, 1, 0)
        
        # Métricas Globais
        acc = accuracy_score(y_test, preds_class)
        loss = log_loss(y_test, preds_proba)

        # Análise de Calibração (High Confidence)
        # Quão bom ele é quando tem convicção? (>60% de chance para Over ou Under)
        max_probs = np.max(preds_proba, axis=1)
        high_conf_mask = max_probs >= 0.60
        high_conf_acc = accuracy_score(y_test[high_conf_mask], preds_class[high_conf_mask]) if np.any(high_conf_mask) else 0.0
        high_conf_volume = np.sum(high_conf_mask)

        over_mask = (preds_class == 1)
        under_mask = (preds_class == 0)

        acc_over = accuracy_score(y_test[over_mask], preds_class[over_mask]) if np.any(over_mask) else 0.0
        acc_under = accuracy_score(y_test[under_mask], preds_class[under_mask]) if np.any(under_mask) else 0.0

        logger.info("\n================= [ BOLETIM DO ORÁCULO BETA (BINÁRIO) ] =================")
        logger.info(f"🎯 Acurácia Global (Seca): {acc * 100:.2f}%")
        logger.info(f"📉 Log-Loss (Qualidade da Probabilidade): {loss:.4f}")
        logger.info("-----------------------------------------------------------------------")
        logger.info(f"🔥 Acurácia em Alta Confiança (>60% prob): {high_conf_acc * 100:.2f}% (em {high_conf_volume} jogos)")
        logger.info("-----------------------------------------------------------------------")
        logger.info("📊 WIN-RATE POR CLASSE (Onde a IA decidiu atirar):")
        logger.info(f"   📈 OVER 2.5:  {acc_over * 100:.1f}% de acerto (Volume: {np.sum(over_mask)})")
        logger.info(f"   📉 UNDER 2.5: {acc_under * 100:.1f}% de acerto (Volume: {np.sum(under_mask)})")
        logger.info("=========================================================================\n")

if __name__ == "__main__":
    BetaOracle().train_and_evaluate()