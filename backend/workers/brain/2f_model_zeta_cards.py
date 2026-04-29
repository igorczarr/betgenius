# betgenius-backend/brain/2f_model_zeta_cards.py

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

class ZetaOracle:
    """
    O Oráculo Zeta (Especialista em Cartões).
    Lê a Tensão do jogo e a Agressividade histórica para prever 
    a linha asiática padrão de Over/Under 4.5 Cartões.
    """
    def __init__(self):
        self.data_vault_path = Path(__file__).parent / "data_vault" / "purified_tensors.parquet"
        self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # O ARSENAL: Foco extremo em Tensão, Faltas (Aggression) e Diferença de Força
        self.features = [
            'delta_elo', 'delta_tension', 
            'delta_market_respect',
            'home_aggression_ewma', 'away_aggression_ewma', 
            'home_xg_for_ewma_micro', 'away_xg_for_ewma_micro', # Pressão gera faltas da defesa
            'home_fraudulent_defense', 'away_fraudulent_defense',
            'delta_posicao', 'delta_pontos' # Jogos de "Desespero" na tabela geram mais cartões
        ]

    def train_and_evaluate(self):
        if not self.data_vault_path.exists():
            logger.error("❌ Data Vault não encontrado. Rode o 1_data_sanitizer.py.")
            sys.exit(1)
            
        logger.info("==================================================================")
        logger.info(" 🟨 INICIANDO FORJA DO ORÁCULO ZETA (CARTÕES / BOOKING POINTS) ")
        logger.info("==================================================================")

        df = pd.read_parquet(self.data_vault_path)
        
        # Filtro de Sanidade: Jogos válidos e com contagem de cartões mapeada
        initial_len = len(df)
        df = df[(df['home_elo_before'] > 100) & (df['target_total_cards'] >= 0)].copy()
        
        logger.info(f"📂 Matriz Carregada: {len(df)} jogos tensos disponíveis (Descartados {initial_len - len(df)}).")

        df = df.sort_values('match_date').reset_index(drop=True)
        
        # TIME-SERIES SPLIT: 80% Treino, 20% Teste
        split_idx = int(len(df) * 0.80)
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:].reset_index(drop=True)
        
        X_train = train_df[self.features]
        # Target: Total de Cartões (Amarelo=1, Vermelho=2)
        y_train = train_df['target_total_cards'] 
        
        X_test = test_df[self.features]
        y_test_exact = test_df['target_total_cards']
        
        # A Linha Ouro das Casas de Apostas para Cartões é 4.5
        # Vamos testar a acurácia do modelo contra a linha de Over 4.5 Cartões (5 ou mais)
        y_test_over45 = (y_test_exact > 4.5).astype(int)

        logger.info(f"⏳ Analisando a Violência do Passado: {len(X_train)} partidas...")
        
        # O CÉREBRO: Poisson Regressor
        model = xgb.XGBRegressor(
            objective='count:poisson',
            n_estimators=450,
            learning_rate=0.015,
            max_depth=4,         
            min_child_weight=4,  
            subsample=0.85,
            colsample_bytree=0.85,
            reg_alpha=0.5,      
            reg_lambda=1.5,     
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)

        joblib.dump(model, self.models_dir / "zeta_oracle_cards.joblib")
        logger.info("✅ Oráculo Zeta (Cartões) Treinado e Preso no Cofre.")

        logger.info(f"\n⚡ Iniciando Auditoria Preditiva no Teste Cego ({len(X_test)} jogos)...")
        
        # Previsão da Média Exata de Cartões (Ex: 4.8 cartões)
        expected_cards = np.clip(model.predict(X_test), 0.5, 12.0)
        
        # MATEMÁTICA DE SINDICATO: Poisson CDF
        # A chance de sair ATÉ 4 cartões (Under 4.5)
        prob_under_45 = poisson.cdf(4, expected_cards)
        prob_over_45 = 1.0 - prob_under_45
        
        preds_proba = np.column_stack((prob_under_45, prob_over_45))
        preds_class = np.argmax(preds_proba, axis=1) # 0 = Under, 1 = Over
        
        mae = mean_absolute_error(y_test_exact, expected_cards)
        acc = accuracy_score(y_test_over45, preds_class)
        loss = log_loss(y_test_over45, preds_proba)

        # Calibração de Alta Confiança (Filtro Sniper > 58%)
        max_probs = np.max(preds_proba, axis=1)
        high_conf_mask = max_probs >= 0.58
        high_conf_acc = accuracy_score(y_test_over45[high_conf_mask], preds_class[high_conf_mask]) if np.any(high_conf_mask) else 0.0
        high_conf_volume = np.sum(high_conf_mask)

        over_mask = (preds_class == 1)
        under_mask = (preds_class == 0)

        acc_over = accuracy_score(y_test_over45[over_mask], preds_class[over_mask]) if np.any(over_mask) else 0.0
        acc_under = accuracy_score(y_test_over45[under_mask], preds_class[under_mask]) if np.any(under_mask) else 0.0

        logger.info("\n================= [ BOLETIM DO ORÁCULO ZETA (CARTÕES) ] =================")
        logger.info(f"🎯 Erro Absoluto Médio (MAE): Erra por {mae:.2f} cartões por jogo")
        logger.info(f"🎯 Acurácia Global (Over/Under 4.5): {acc * 100:.2f}%")
        logger.info(f"📉 Log-Loss: {loss:.4f}")
        logger.info("-------------------------------------------------------------------------")
        logger.info(f"🔥 ACURÁCIA EM ALTA CONFIANÇA (>58% prob): {high_conf_acc * 100:.2f}% (em {high_conf_volume} jogos)")
        logger.info("-------------------------------------------------------------------------")
        logger.info("📊 WIN-RATE POR MERCADO (Onde a IA decidiu atirar):")
        logger.info(f"   🟨 OVER 4.5 CARTÕES:  {acc_over * 100:.1f}% de acerto (Volume: {np.sum(over_mask)})")
        logger.info(f"   🟩 UNDER 4.5 CARTÕES: {acc_under * 100:.1f}% de acerto (Volume: {np.sum(under_mask)})")
        logger.info("=========================================================================\n")

if __name__ == "__main__":
    ZetaOracle().train_and_evaluate()