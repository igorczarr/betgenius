# betgenius-backend/brain/2c_model_gamma.py

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
from sklearn.metrics import accuracy_score, log_loss
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

class GammaOracle:
    """
    O Oráculo Gama (Ambas Marcam / BTTS).
    Classificador Binário treinado para identificar simetria ofensiva
    e colapsos defensivos mútuos.
    """
    def __init__(self):
        self.data_vault_path = Path(__file__).parent / "data_vault" / "purified_tensors.parquet"
        self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # Arsenal Focado em Trocação (BTTS exige que os dois ataquem e falhem)
        self.features = [
            'delta_elo', 'delta_tension', 'delta_market_respect',
            'delta_xg_micro', 'delta_xg_macro',
            'home_xg_for_ewma_micro', 'home_xg_against_ewma_micro',
            'away_xg_for_ewma_micro', 'away_xg_against_ewma_micro',
            'home_xg_for_ewma_macro', 'away_xg_for_ewma_macro',
            'home_aggression_ewma', 'away_aggression_ewma', 
            'home_clean_sheet_streak', 'away_clean_sheet_streak',
            'home_fraudulent_defense', 'home_fraudulent_attack',
            'away_fraudulent_defense', 'away_fraudulent_attack'
        ]

    def train_and_evaluate(self):
        if not self.data_vault_path.exists():
            logger.error("❌ Data Vault não encontrado. Rode o 1_data_sanitizer.py.")
            sys.exit(1)
            
        logger.info("==================================================================")
        logger.info(" ⚔️ INICIANDO FORJA DO ORÁCULO GAMA (AMBAS MARCAM - BTTS) ")
        logger.info("==================================================================")

        df = pd.read_parquet(self.data_vault_path)
        
        # Filtro de Qualidade: Ignorar lixo absoluto sem histórico
        df = df[df['home_elo_before'] > 100].copy()
        
        logger.info(f"📂 Matriz Carregada: {len(df)} jogos históricos disponíveis.")

        # Ordenação Cronológica Obrigatória
        df = df.sort_values('match_date').reset_index(drop=True)
        
        # TIME-SERIES SPLIT: 80% Treino, 20% Teste Cego
        split_idx = int(len(df) * 0.80)
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:].reset_index(drop=True)
        
        X_train = train_df[self.features]
        # Alvo Binário: 1 = BTTS Sim, 0 = BTTS Não
        y_train = train_df['target_btts'] 
        
        X_test = test_df[self.features]
        y_test = test_df['target_btts']

        logger.info(f"⏳ Treinando com o Passado: {len(X_train)} jogos...")
        
        # O CÉREBRO: Otimizado para identificar padrões de falha mútua
        model = xgb.XGBClassifier(
            objective='binary:logistic',
            eval_metric='logloss',
            n_estimators=450,
            learning_rate=0.015,
            max_depth=4,         
            min_child_weight=4,  
            subsample=0.85,
            colsample_bytree=0.85,
            reg_alpha=0.5,      
            reg_lambda=2.0,     # Amarras leves para evitar Overconfidence no BTTS
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)

        joblib.dump(model, self.models_dir / "gamma_oracle_btts.joblib")
        logger.info("✅ Oráculo Gama Treinado e Preso no Cofre.")

        logger.info(f"\n⚡ Iniciando Auditoria Preditiva no Teste Cego ({len(X_test)} jogos)...")
        
        # Matriz: [Prob_BTTS_No, Prob_BTTS_Yes]
        preds_proba = model.predict_proba(X_test)
        prob_yes = preds_proba[:, 1]
        
        preds_class = np.where(prob_yes > 0.50, 1, 0)
        
        acc = accuracy_score(y_test, preds_class)
        loss = log_loss(y_test, preds_proba)

        # Análise de Calibração (High Confidence > 58%)
        max_probs = np.max(preds_proba, axis=1)
        high_conf_mask = max_probs >= 0.58
        high_conf_acc = accuracy_score(y_test[high_conf_mask], preds_class[high_conf_mask]) if np.any(high_conf_mask) else 0.0
        high_conf_volume = np.sum(high_conf_mask)

        yes_mask = (preds_class == 1)
        no_mask = (preds_class == 0)

        acc_yes = accuracy_score(y_test[yes_mask], preds_class[yes_mask]) if np.any(yes_mask) else 0.0
        acc_no = accuracy_score(y_test[no_mask], preds_class[no_mask]) if np.any(no_mask) else 0.0

        logger.info("\n================= [ BOLETIM DO ORÁCULO GAMA (BTTS) ] =================")
        logger.info(f"🎯 Acurácia Global (Seca): {acc * 100:.2f}%")
        logger.info(f"📉 Log-Loss (Qualidade da Probabilidade): {loss:.4f}")
        logger.info("----------------------------------------------------------------------")
        logger.info(f"🔥 Acurácia em Alta Confiança (>58% prob): {high_conf_acc * 100:.2f}% (em {high_conf_volume} jogos)")
        logger.info("----------------------------------------------------------------------")
        logger.info("📊 WIN-RATE POR CLASSE (Onde a IA atirou):")
        logger.info(f"   ⚽ BTTS SIM: {acc_yes * 100:.1f}% de acerto (Volume: {np.sum(yes_mask)})")
        logger.info(f"   🛡️ BTTS NÃO: {acc_no * 100:.1f}% de acerto (Volume: {np.sum(no_mask)})")
        logger.info("======================================================================\n")

if __name__ == "__main__":
    GammaOracle().train_and_evaluate()