# betgenius-backend/brain/2d_model_delta_ht.py

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

# Suprime os avisos inofensivos de downcasting do Pandas
pd.set_option('future.no_silent_downcasting', True)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [MODEL-DELTA] %(message)s")
logger = logging.getLogger(__name__)

class DeltaOracle:
    """
    O Oráculo Delta (Especialista em Half-Time 1X2).
    Foco Institucional: Encontrar times 'Coelho' (Explosão inicial) 
    e times 'Diesel' (Lentos no 1º tempo) explorando as falhas das casas de apostas.
    """
    def __init__(self):
        self.data_vault_path = Path(__file__).parent / "data_vault" / "purified_tensors.parquet"
        self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # O ARSENAL: Foco em Agressividade, Caos Micro e Tensão
        self.features = [
            'delta_elo', 'delta_wage_pct', 'delta_pontos', 'delta_posicao', 
            'delta_market_respect', 'delta_tension', 
            'delta_xg_micro', 'delta_xg_macro',
            'home_xg_for_ewma_micro', 'away_xg_for_ewma_micro',
            'home_xg_against_ewma_micro', 'away_xg_against_ewma_micro',
            'home_aggression_ewma', 'away_aggression_ewma', 
            'home_fraudulent_defense', 'away_fraudulent_defense',
            'home_fraudulent_attack', 'away_fraudulent_attack',
            'home_win_streak', 'away_win_streak'
        ]

    def train_and_evaluate(self):
        if not self.data_vault_path.exists():
            logger.error("❌ Data Vault não encontrado. Rode o 1_data_sanitizer.py.")
            sys.exit(1)
            
        logger.info("==================================================================")
        logger.info(" ⏱️ INICIANDO FORJA DO ORÁCULO DELTA (HALF-TIME 1X2 SÊNIOR) ")
        logger.info("==================================================================")

        df = pd.read_parquet(self.data_vault_path)
        
        # FILTRO DE SANIDADE: Ignora lixo absoluto e garante que há dados de HT
        initial_len = len(df)
        df = df[(df['home_elo_before'] > 100) & (df['ht_home_goals'].notna()) & (df['ht_away_goals'].notna())].copy()
        
        logger.info(f"📂 Matriz Carregada: {len(df)} jogos de Elite disponíveis (Descartados {initial_len - len(df)}).")

        # ORDENAÇÃO CRONOLÓGICA (Prevenção Absoluta de Data Leakage)
        df = df.sort_values('match_date').reset_index(drop=True)
        
        # TIME-SERIES SPLIT: 80% Treino (Aprender), 20% Teste (Lucrar)
        split_idx = int(len(df) * 0.80)
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:].reset_index(drop=True)
        
        X_train = train_df[self.features]
        # Target HT: 0 (Away Vence o 1ºT), 1 (Empate no 1ºT), 2 (Home Vence o 1ºT)
        y_train = train_df['target_ht_result'] 
        
        X_test = test_df[self.features]
        y_test = test_df['target_ht_result']

        logger.info(f"⏳ Treinando Padrões Iniciais de Jogo: {len(X_train)} partidas...")
        
        # O CÉREBRO MULTI-CLASSE (Agressivo, mas calculado para o caos dos 45 minutos)
        model = xgb.XGBClassifier(
            objective='multi:softprob',
            num_class=3,
            eval_metric='mlogloss',
            n_estimators=500,
            learning_rate=0.015,
            max_depth=5,          # Suficiente para cruzar xG Micro com Tensão
            min_child_weight=3,   
            subsample=0.85,
            colsample_bytree=0.85,
            reg_alpha=0.5,        # L1: Remove ruídos estatísticos
            reg_lambda=1.5,       # L2: Impede o modelo de ficar overconfident no HT
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)

        joblib.dump(model, self.models_dir / "delta_oracle_ht.joblib")
        logger.info("✅ Oráculo Delta (Half-Time) Treinado e Preso no Cofre.")

        logger.info(f"\n⚡ Iniciando Auditoria Preditiva no Teste Cego ({len(X_test)} jogos)...")
        
        # [Prob_Away_HT, Prob_Draw_HT, Prob_Home_HT]
        preds_proba = model.predict_proba(X_test)
        preds_class = np.argmax(preds_proba, axis=1)
        
        # MÉTRICAS GLOBAIS
        acc = accuracy_score(y_test, preds_class)
        loss = log_loss(y_test, preds_proba)

        # CALIBRAÇÃO DE ALTA CONFIANÇA (O Machado de Execução)
        # Em HT, o Empate domina. Se o modelo tiver > 55% de chance em algo, ele achou uma mina de ouro.
        high_conf_mask = np.max(preds_proba, axis=1) >= 0.55
        high_conf_acc = accuracy_score(y_test[high_conf_mask], preds_class[high_conf_mask]) if np.any(high_conf_mask) else 0.0
        high_conf_volume = np.sum(high_conf_mask)

        # Acurácia por Classe (Como o modelo se sai em cada palpite)
        home_mask = (preds_class == 2)
        away_mask = (preds_class == 0)
        draw_mask = (preds_class == 1)

        acc_home = accuracy_score(y_test[home_mask], preds_class[home_mask]) if np.any(home_mask) else 0.0
        acc_away = accuracy_score(y_test[away_mask], preds_class[away_mask]) if np.any(away_mask) else 0.0
        acc_draw = accuracy_score(y_test[draw_mask], preds_class[draw_mask]) if np.any(draw_mask) else 0.0

        logger.info("\n================= [ BOLETIM DO ORÁCULO DELTA (HT SÊNIOR) ] =================")
        logger.info(f"🎯 Acurácia Global (45 Minutos): {acc * 100:.2f}%")
        logger.info(f"📉 Log-Loss (Qualidade da Probabilidade): {loss:.4f}")
        logger.info("----------------------------------------------------------------------------")
        logger.info(f"🔥 ACURÁCIA EM ALTA CONFIANÇA (>55% prob): {high_conf_acc * 100:.2f}% (em {high_conf_volume} jogos)")
        logger.info("----------------------------------------------------------------------------")
        logger.info("📊 WIN-RATE POR MERCADO (Onde a IA decidiu atirar):")
        logger.info(f"   🏠 Mandante Vence o 1ºT: {acc_home * 100:.1f}% de acerto (Volume: {np.sum(home_mask)})")
        logger.info(f"   ✈️ Visitante Vence o 1ºT: {acc_away * 100:.1f}% de acerto (Volume: {np.sum(away_mask)})")
        logger.info(f"   🤝 Empate no 1ºT: {acc_draw * 100:.1f}% de acerto (Volume: {np.sum(draw_mask)})")
        logger.info("============================================================================\n")

if __name__ == "__main__":
    DeltaOracle().train_and_evaluate()