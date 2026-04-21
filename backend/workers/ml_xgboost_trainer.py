# betgenius-backend/workers/ml_xgboost_trainer.py

import asyncio
import logging
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import accuracy_score, log_loss, classification_report
import joblib
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# =====================================================================
# BLINDAGEM DE ENCODING E CARREGAMENTO DO .ENV
# =====================================================================
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ML-TRAINER] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class XGBoostTrainer:
    """
    Motor S-Tier de Machine Learning (XGBoost).
    Treina o modelo para o mercado 1X2 (Match Odds) usando Time-Series Split
    para prevenir vazamento de dados do futuro.
    """
    def __init__(self):
        self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # O Arsenal de Variáveis S-Tier (Total: 25 Colunas)
        self.features = [
            'delta_elo', 'delta_wage_pct', 
            'delta_pontos', 'delta_posicao', 
            'home_rest_days', 'away_rest_days', 
            'home_xg_for_ewma_micro', 'home_xg_against_ewma_micro',
            'away_xg_for_ewma_micro', 'away_xg_against_ewma_micro',
            'home_xg_for_ewma_macro', 'away_xg_for_ewma_macro',
            'home_aggression_ewma', 'away_aggression_ewma', 
            'home_win_streak', 'home_winless_streak', 'away_win_streak', 'away_winless_streak',
            'home_tension_index', 'away_tension_index', 
            'home_fraudulent_defense', 'home_fraudulent_attack',
            'away_fraudulent_defense', 'away_fraudulent_attack',
            'delta_market_respect' # O que o Dinheiro Asiático pensa
        ]

    async def load_feature_store(self) -> pd.DataFrame:
        """Puxa o Tensor Supremo do Banco de Dados (Schema correto: quant_ml.feature_store)."""
        logger.info("📡 Conectando ao Data Warehouse para extração...")
        await db.connect()
        df = pd.DataFrame()
        try:
            async with db.pool.acquire() as conn:
                # Puxamos ordenado por data! Fundamental para ML em esportes.
                query = "SELECT * FROM quant_ml.feature_store ORDER BY date ASC"
                records = await conn.fetch(query)
                if records:
                    df = pd.DataFrame([dict(r) for r in records])
                    logger.info(f"🧬 Dados Brutos extraídos: {len(df)} partidas históricas.")
                else:
                    logger.error("❌ A feature_store está vazia no banco de dados.")
        except Exception as e:
            logger.error(f"❌ Erro ao baixar dados do banco: {e}")
        finally:
            await db.disconnect()
            
        return df

    def prepare_data(self, df: pd.DataFrame):
        """Prepara o Target Multi-Classe (0 = Away Win, 1 = Draw, 2 = Home Win)."""
        logger.info("📐 Estruturando Tensores para o XGBoost...")
        
        # Cria a variável alvo consolidada para o XGBoost Multi-classe
        conditions = [
            (df['home_goals'] > df['away_goals']),
            (df['home_goals'] == df['away_goals']),
            (df['home_goals'] < df['away_goals'])
        ]
        choices = [2, 1, 0] # 2: Home, 1: Draw, 0: Away
        df['target_1x2'] = np.select(conditions, choices, default=-1)
        
        # Remove lixo matemático e jogos cancelados
        df = df[df['target_1x2'] != -1]

        # ==========================================
        # INTERVENÇÃO DE ARQUITETO: ENGENHARIA DE DELTAS
        # Recriamos os diferenciais absolutos que o XGBoost exige a partir dos dados em banco
        # ==========================================
        df['delta_elo'] = pd.to_numeric(df['home_elo_before'], errors='coerce') - pd.to_numeric(df['away_elo_before'], errors='coerce')
        df['delta_wage_pct'] = pd.to_numeric(df['home_wage_pct'], errors='coerce') - pd.to_numeric(df['away_wage_pct'], errors='coerce')
        df['delta_pontos'] = pd.to_numeric(df['home_pts_before'], errors='coerce') - pd.to_numeric(df['away_pts_before'], errors='coerce')
        df['delta_posicao'] = pd.to_numeric(df['pos_tabela_away'], errors='coerce') - pd.to_numeric(df['pos_tabela_home'], errors='coerce') # Posição 1 é melhor que 20
        df['delta_market_respect'] = pd.to_numeric(df['home_market_respect'], errors='coerce') - pd.to_numeric(df['away_market_respect'], errors='coerce')
        
        # Garante que todos os tipos da lista de features são numéricos
        for col in self.features:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        # O XGBoost lida bem com NaNs, mas vamos zerar qualquer lixo extremo
        df[self.features] = df[self.features].fillna(0)
        
        # Time-Series Split (Treina no Passado, Testa no Futuro)
        # Vamos pegar os primeiros 80% dos jogos cronologicamente para treino
        split_idx = int(len(df) * 0.8)
        
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:]
        
        X_train = train_df[self.features]
        y_train = train_df['target_1x2']
        X_test = test_df[self.features]
        y_test = test_df['target_1x2']
        
        # Passando as odds de fechamento para a simulação de lucro na avaliação
        self.test_odds_home = pd.to_numeric(test_df['closing_odd_home'], errors='coerce').fillna(1.0)
        self.test_odds_away = pd.to_numeric(test_df['closing_odd_away'], errors='coerce').fillna(1.0)
        self.test_odds_draw = pd.to_numeric(test_df['closing_odd_draw'], errors='coerce').fillna(1.0)
        
        logger.info(f"📊 Treinando com {len(X_train)} jogos do passado.")
        logger.info(f"🔮 Testando cegamente em {len(X_test)} jogos do futuro.")
        
        return X_train, X_test, y_train, y_test

    def train_and_evaluate(self, X_train, X_test, y_train, y_test):
        logger.info("🧠 Treinando Rede XGBoost (Gradient Boosting Trees)...")
        
        # Hiperparâmetros configurados para evitar Overfitting (decorar resultados)
        model = xgb.XGBClassifier(
            objective='multi:softprob',
            num_class=3,
            n_estimators=150,
            learning_rate=0.05,
            max_depth=4,         # Árvores curtas = generalização melhor
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric='mlogloss',
            random_state=42
        )
        
        model.fit(X_train, y_train)
        
        # Previsões
        preds_class = model.predict(X_test)
        preds_proba = model.predict_proba(X_test)
        
        # Métricas de Sindicato
        acc = accuracy_score(y_test, preds_class)
        loss = log_loss(y_test, preds_proba)
        
        logger.info("\n================= [ RESULTADOS DO TESTE CEGO ] =================")
        logger.info(f"🎯 Acurácia Bruta: {acc:.2%}")
        logger.info(f"📉 Log Loss (Incerteza): {loss:.4f} (Quanto menor, mais confiança nas odds)")
        
        # Para evitar bug visual se a rede prever apenas Vitórias (ignorar zebras e empates)
        try:
            report = classification_report(y_test, preds_class, target_names=["Away", "Draw", "Home"], zero_division=0)
            logger.info("\nRelatório por Classe:\n" + report)
        except Exception:
            logger.warning("Relatório por classe indisponível (Amostra pequena).")
            
        # ==========================================
        # SIMULAÇÃO DE FUNDO DE INVESTIMENTO (+EV)
        # ==========================================
        logger.info("💰 Simulando Operações Value Betting no Mercado de Fechamento...")
        
        prob_away = preds_proba[:, 0]
        prob_draw = preds_proba[:, 1]
        prob_home = preds_proba[:, 2]
        
        ev_home = (prob_home * self.test_odds_home.values) - 1.0
        ev_away = (prob_away * self.test_odds_away.values) - 1.0
        
        # Estratégia de Sniper: Só aposta se o Edge for maior que 10% (0.10) e menor que 100% (evitar lixo estatístico)
        EDGE_THRESHOLD = 0.10
        MAX_EDGE = 1.00
        
        profit = 0.0
        bets_placed = 0
        
        for i in range(len(y_test)):
            target = y_test.iloc[i]
            
            # Operação a Favor do Mandante
            if EDGE_THRESHOLD < ev_home[i] < MAX_EDGE:
                bets_placed += 1
                if target == 2: profit += (self.test_odds_home.values[i] - 1.0)
                else: profit -= 1.0
                
            # Operação a Favor do Visitante
            if EDGE_THRESHOLD < ev_away[i] < MAX_EDGE:
                bets_placed += 1
                if target == 0: profit += (self.test_odds_away.values[i] - 1.0)
                else: profit -= 1.0
                
        roi = (profit / bets_placed) * 100 if bets_placed > 0 else 0.0
        
        logger.info(f"   -> Total de Apostas Sniper: {bets_placed}")
        logger.info(f"   -> Lucro/Prejuízo Líquido: {profit:.2f} Unidades")
        logger.info(f"   -> Retorno sobre o Investimento (ROI): {roi:.2f}%\n")
        
        # Salvando o Modelo
        model_path = self.models_dir / "xgb_match_odds.joblib"
        joblib.dump(model, model_path)
        logger.info(f"💾 Cérebro Predito salvo com sucesso em: {model_path}")
        
        # Imprime a Importância das Variáveis (Feature Importance)
        importances = model.feature_importances_
        feature_importance_df = pd.DataFrame({'Feature': self.features, 'Importance': importances})
        feature_importance_df = feature_importance_df.sort_values(by='Importance', ascending=False).head(5)
        logger.info("\n🏆 Top 5 Variáveis Mais Importantes para a IA:")
        for idx, row in feature_importance_df.iterrows():
            logger.info(f" -> {row['Feature']}: {row['Importance']:.2%}")
        
        return model

    async def run(self):
        df = await self.load_feature_store()
        if df.empty:
            return
            
        X_train, X_test, y_train, y_test = self.prepare_data(df)
        if len(X_train) < 50:
            logger.warning("⚠️ Você tem muito poucos jogos no banco para um treinamento válido.")
            
        self.train_and_evaluate(X_train, X_test, y_train, y_test)

if __name__ == "__main__":
    trainer = XGBoostTrainer()
    asyncio.run(trainer.run())