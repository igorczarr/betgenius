# betgenius-backend/brain/2a_model_alpha.py

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

class AlphaOracle:
    """
    O Oráculo Sênior. 
    100% focado em Previsão Pura e Acurácia (Win-Rate).
    Ignora finanças, odds e margens. Foco no estado da arte preditivo.
    """
    def __init__(self):
        self.data_vault_path = Path(__file__).parent / "data_vault" / "purified_tensors.parquet"
        self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # Arsenal Preditivo Absoluto (Zero Vazamento de Dados Futuros)
        self.features = [
            'delta_elo', 'delta_wage_pct', 'delta_pontos', 'delta_posicao', 
            'delta_market_respect', 'delta_tension', 
            'delta_xg_micro', 'delta_xg_macro',
            'home_elo_before', 'away_elo_before',
            'home_pts_before', 'away_pts_before',
            'pos_tabela_home', 'pos_tabela_away',
            'home_xg_for_ewma_micro', 'home_xg_against_ewma_micro',
            'away_xg_for_ewma_micro', 'away_xg_against_ewma_micro',
            'home_xg_for_ewma_macro', 'away_xg_for_ewma_macro',
            'home_aggression_ewma', 'away_aggression_ewma', 
            'home_win_streak', 'home_winless_streak', 'home_clean_sheet_streak',
            'away_win_streak', 'away_winless_streak', 'away_clean_sheet_streak',
            'home_fraudulent_defense', 'home_fraudulent_attack',
            'away_fraudulent_defense', 'away_fraudulent_attack'
        ]

    def train_and_evaluate(self):
        if not self.data_vault_path.exists():
            logger.error("❌ Data Vault não encontrado. Rode o 1_data_sanitizer.py.")
            sys.exit(1)
            
        logger.info("==================================================================")
        logger.info(" 🧠 INICIANDO FORJA DO ORÁCULO ALPHA (PREDIÇÃO PURA 1X2) ")
        logger.info("==================================================================")

        df = pd.read_parquet(self.data_vault_path)
        
        # Filtro Básico de Sanidade (Elimina apenas lixo absoluto, mantém o volume)
        df = df[df['home_elo_before'] > 100].copy()
        
        logger.info(f"📂 Matriz Carregada: {len(df)} jogos históricos disponíveis.")

        # PREVENÇÃO DE VAZAMENTO DE DADOS: Ordenação Cronológica Estrita
        df = df.sort_values('match_date').reset_index(drop=True)
        
        # TIME-SERIES SPLIT: 80% Treino, 20% Teste
        split_idx = int(len(df) * 0.80)
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:].reset_index(drop=True)
        
        X_train = train_df[self.features]
        y_train = train_df['target_match_result'] # 0: Away, 1: Draw, 2: Home
        
        X_test = test_df[self.features]
        y_test = test_df['target_match_result']

        logger.info(f"⏳ Treinando com o Passado: {len(X_train)} jogos...")
        logger.info(f"🔮 Testando com o Futuro: {len(X_test)} jogos...")
        
        # O CÉREBRO: Otimizado para Acurácia (Sem medo)
        model = xgb.XGBClassifier(
            objective='multi:softprob',
            num_class=3,
            eval_metric='mlogloss',
            n_estimators=600,
            learning_rate=0.01,
            max_depth=5,         
            min_child_weight=3,  
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,      
            reg_lambda=1.0,     
            random_state=42,
            n_jobs=-1
        )
        
        # O XGBoost é treinado permitindo lidar nativamente com NaNs!
        model.fit(X_train, y_train)

        joblib.dump(model, self.models_dir / "alpha_oracle_1x2.joblib")
        logger.info("✅ Oráculo Treinado e Preso no Cofre.")

        logger.info(f"\n⚡ Iniciando Auditoria Preditiva no Teste Cego (20% Recente)...")
        
        # Previsão das Probabilidades (A Matriz Pura)
        preds_proba = model.predict_proba(X_test)
        
        # A escolha do Oráculo (A classe com maior probabilidade)
        preds_class = np.argmax(preds_proba, axis=1)
        
        # Métricas Globais
        acc = accuracy_score(y_test, preds_class)
        loss = log_loss(y_test, preds_proba)

        # Análise de Calibração (High Confidence Win-Rate)
        # Quão bom o modelo é quando ele tem "certeza"? (>60% de probabilidade)
        high_conf_mask = np.max(preds_proba, axis=1) >= 0.60
        high_conf_acc = accuracy_score(y_test[high_conf_mask], preds_class[high_conf_mask]) if np.any(high_conf_mask) else 0.0
        high_conf_volume = np.sum(high_conf_mask)

        # Acurácia por Classe (Visitante, Empate, Mandante)
        home_mask = (preds_class == 2)
        away_mask = (preds_class == 0)
        draw_mask = (preds_class == 1)

        acc_home = accuracy_score(y_test[home_mask], preds_class[home_mask]) if np.any(home_mask) else 0.0
        acc_away = accuracy_score(y_test[away_mask], preds_class[away_mask]) if np.any(away_mask) else 0.0
        acc_draw = accuracy_score(y_test[draw_mask], preds_class[draw_mask]) if np.any(draw_mask) else 0.0

        logger.info("\n================= [ BOLETIM DO ORÁCULO SÊNIOR ] =================")
        logger.info(f"🎯 Acurácia Global (Win-Rate Base): {acc * 100:.2f}%")
        logger.info(f"📉 Log-Loss (Qualidade da Probabilidade): {loss:.4f}")
        logger.info("-----------------------------------------------------------------")
        logger.info(f"🔥 Acurácia em Alta Confiança (>60% prob): {high_conf_acc * 100:.2f}% (em {high_conf_volume} jogos)")
        logger.info("-----------------------------------------------------------------")
        logger.info("📊 WIN-RATE POR MERCADO (Apenas os palpites da máquina):")
        logger.info(f"   🏠 Mandante (Home): {acc_home * 100:.1f}% de acerto (Volume: {np.sum(home_mask)})")
        logger.info(f"   ✈️ Visitante (Away): {acc_away * 100:.1f}% de acerto (Volume: {np.sum(away_mask)})")
        logger.info(f"   🤝 Empate (Draw): {acc_draw * 100:.1f}% de acerto (Volume: {np.sum(draw_mask)})")
        logger.info("=================================================================\n")

if __name__ == "__main__":
    AlphaOracle().train_and_evaluate()