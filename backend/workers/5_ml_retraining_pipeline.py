# betgenius-backend/workers/5_ml_retraining_pipeline.py

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
import joblib
import subprocess
from sklearn.metrics import log_loss, mean_absolute_error
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

pd.set_option('future.no_silent_downcasting', True)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

class ContinuousEvolutionPipeline:
    """
    O Orquestrador de Evolução (Champion vs. Challenger).
    Retreina o comitê de Oráculos continuamente, testando as novas IAs (Challengers)
    contra as IAs em produção (Champions). O modelo só é atualizado se a precisão aumentar.
    """
    def __init__(self):
        self.data_vault_path = BASE_DIR / "brain" / "data_vault" / "purified_tensors.parquet"
        self.models_dir = BASE_DIR / "brain" / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # Mapeamento Genético dos Oráculos (Garante que não haverá erro de features)
        self.oracles_dna = {
            'Alpha (1X2)': {
                'file': 'alpha_classifier_1x2.joblib', 'type': 'classifier_multi', 'target': 'target_match_result',
                'features': ['delta_elo', 'delta_wage_pct', 'delta_pontos', 'delta_posicao', 'delta_market_respect', 'delta_tension', 'delta_xg_micro', 'delta_xg_macro', 'home_elo_before', 'away_elo_before', 'home_pts_before', 'away_pts_before', 'pos_tabela_home', 'pos_tabela_away', 'home_xg_for_ewma_micro', 'home_xg_against_ewma_micro', 'away_xg_for_ewma_micro', 'away_xg_against_ewma_micro', 'home_xg_for_ewma_macro', 'away_xg_for_ewma_macro', 'home_aggression_ewma', 'away_aggression_ewma', 'home_win_streak', 'home_winless_streak', 'home_clean_sheet_streak', 'away_win_streak', 'away_winless_streak', 'away_clean_sheet_streak', 'home_fraudulent_defense', 'home_fraudulent_attack', 'away_fraudulent_defense', 'away_fraudulent_attack']
            },
            'Beta (Gols)': {
                'file': 'beta_oracle_ou25.joblib', 'type': 'classifier_binary', 'target': 'target_over_25',
                'features': ['delta_elo', 'delta_tension', 'delta_market_respect', 'delta_xg_micro', 'delta_xg_macro', 'home_xg_for_ewma_micro', 'home_xg_against_ewma_micro', 'away_xg_for_ewma_micro', 'away_xg_against_ewma_micro', 'home_xg_for_ewma_macro', 'away_xg_for_ewma_macro', 'home_aggression_ewma', 'away_aggression_ewma', 'home_clean_sheet_streak', 'away_clean_sheet_streak', 'home_fraudulent_defense', 'home_fraudulent_attack', 'away_fraudulent_defense', 'away_fraudulent_attack']
            },
            'Gamma (BTTS)': {
                'file': 'gamma_oracle_btts.joblib', 'type': 'classifier_binary', 'target': 'target_btts',
                'features': ['delta_elo', 'delta_tension', 'delta_market_respect', 'delta_xg_micro', 'delta_xg_macro', 'home_xg_for_ewma_micro', 'home_xg_against_ewma_micro', 'away_xg_for_ewma_micro', 'away_xg_against_ewma_micro', 'home_xg_for_ewma_macro', 'away_xg_for_ewma_macro', 'home_aggression_ewma', 'away_aggression_ewma', 'home_clean_sheet_streak', 'away_clean_sheet_streak', 'home_fraudulent_defense', 'home_fraudulent_attack', 'away_fraudulent_defense', 'away_fraudulent_attack']
            },
            'Delta (HT)': {
                'file': 'delta_oracle_ht.joblib', 'type': 'classifier_multi', 'target': 'target_ht_result',
                'features': ['delta_elo', 'delta_wage_pct', 'delta_market_respect', 'delta_tension', 'delta_xg_micro', 'home_xg_for_ewma_micro', 'away_xg_for_ewma_micro', 'home_aggression_ewma', 'away_aggression_ewma', 'home_fraudulent_defense', 'away_fraudulent_defense', 'home_win_streak', 'away_win_streak']
            },
            'Epsilon (Cantos)': {
                'file': 'epsilon_oracle_corners.joblib', 'type': 'regressor_poisson', 'target': 'target_total_corners',
                'features': ['delta_elo', 'delta_tension', 'delta_xg_micro', 'delta_xg_macro', 'home_xg_for_ewma_micro', 'away_xg_for_ewma_micro', 'home_xg_for_ewma_macro', 'away_xg_for_ewma_macro', 'home_aggression_ewma', 'away_aggression_ewma', 'home_fraudulent_defense', 'away_fraudulent_defense', 'home_market_respect', 'away_market_respect']
            },
            'Zeta (Cartões)': {
                'file': 'zeta_oracle_cards.joblib', 'type': 'regressor_poisson', 'target': 'target_total_cards',
                'features': ['delta_elo', 'delta_tension', 'delta_market_respect', 'home_aggression_ewma', 'away_aggression_ewma', 'home_xg_for_ewma_micro', 'away_xg_for_ewma_micro', 'home_fraudulent_defense', 'away_fraudulent_defense', 'delta_posicao', 'delta_pontos']
            },
            'Sigma (Chutes)': {
                'file': 'sigma_oracle_shots.joblib', 'type': 'regressor_poisson', 'target': 'target_total_shots',
                'features': ['delta_elo', 'delta_tension', 'delta_market_respect', 'delta_xg_micro', 'delta_xg_macro', 'home_xg_for_ewma_micro', 'away_xg_for_ewma_micro', 'home_xg_against_ewma_micro', 'away_xg_against_ewma_micro', 'home_xg_for_ewma_macro', 'away_xg_for_ewma_macro', 'home_aggression_ewma', 'away_aggression_ewma', 'home_fraudulent_defense', 'away_fraudulent_defense', 'home_fraudulent_attack', 'away_fraudulent_attack', 'delta_posicao', 'delta_pontos']
            }
        }

    def _run_sub_process(self, script_path):
        """Dispara a extração de dados do DB e aguarda."""
        logger.info(f"⏳ Executando Módulo Externo: {script_path.name}...")
        try:
            subprocess.run([sys.executable, str(script_path)], check=True, capture_output=True, text=True)
            logger.info(f"✅ Módulo {script_path.name} concluído.")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Falha Crítica no módulo {script_path.name}:\n{e.stderr}")
            sys.exit(1)

    def _create_challenger_model(self, m_type):
        """Cria uma nova IA (Challenger) com hiperparâmetros que favorecem aprendizado recente."""
        if m_type == 'classifier_multi':
            return xgb.XGBClassifier(objective='multi:softprob', eval_metric='mlogloss', n_estimators=500, learning_rate=0.015, max_depth=5, min_child_weight=3, subsample=0.85, colsample_bytree=0.85, random_state=42, n_jobs=-1)
        elif m_type == 'classifier_binary':
            return xgb.XGBClassifier(objective='binary:logistic', eval_metric='logloss', n_estimators=450, learning_rate=0.015, max_depth=4, min_child_weight=4, subsample=0.85, colsample_bytree=0.85, random_state=42, n_jobs=-1)
        elif m_type == 'regressor_poisson':
            return xgb.XGBRegressor(objective='count:poisson', n_estimators=450, learning_rate=0.015, max_depth=4, min_child_weight=5, subsample=0.85, colsample_bytree=0.85, random_state=42, n_jobs=-1)
        return None

    def execute_evolution_cycle(self):
        logger.info("==================================================================")
        logger.info(f" 🧬 INICIANDO CICLO DE EVOLUÇÃO CONTÍNUA - {datetime.now().strftime('%Y-%m-%d')} ")
        logger.info("==================================================================")

        # 1. ATUALIZAÇÃO DA MATRIX (Coleta de Novos Jogos e Resultados)
        logger.info("📥 FASE 1: Extração e Higienização do Mercado...")
        matrix_builder = BASE_DIR / "workers" / "feature_engineering" / "matrix_builder.py"
        sanitizer = BASE_DIR / "brain" / "1_data_sanitizer.py"
        
        self._run_sub_process(matrix_builder)
        self._run_sub_process(sanitizer)

        if not self.data_vault_path.exists():
            logger.error("❌ Cofre de dados não encontrado após higienização.")
            return

        df = pd.read_parquet(self.data_vault_path)
        df = df[df['home_elo_before'] > 100].sort_values('match_date').reset_index(drop=True)

        # 2. SEPARAÇÃO DA ARENA (Os últimos 45 dias são o Teste de Vida ou Morte)
        arena_cutoff = df['match_date'].max() - pd.Timedelta(days=45)
        train_df = df[df['match_date'] <= arena_cutoff].copy()
        arena_df = df[df['match_date'] > arena_cutoff].copy()

        logger.info(f"🏟️ FASE 2: Arena de Combate Definida.")
        logger.info(f"   -> Treino (Histórico): {len(train_df)} partidas.")
        logger.info(f"   -> Arena (Últimos 45 dias): {len(arena_df)} partidas para avaliação.")
        logger.info("------------------------------------------------------------------")

        oracles_updated = 0

        # 3. O TORNEIO (Champion vs Challenger)
        for oracle_name, dna in self.oracles_dna.items():
            logger.info(f"⚔️ Testando Mutações no Oráculo: {oracle_name}")
            
            model_path = self.models_dir / dna['file']
            target = dna['target']
            features = dna['features']
            
            # Filtro de sanidade de alvo nulo (Ex: Jogos que não tiveram cantos registrados)
            valid_train = train_df[train_df[target].notna() & (train_df[target] >= 0)]
            valid_arena = arena_df[arena_df[target].notna() & (arena_df[target] >= 0)]
            
            if len(valid_arena) < 50:
                logger.info(f"   -> Ignorado: Arena pequena demais para validação segura ({len(valid_arena)} jogos).")
                continue

            X_train, y_train = valid_train[features], valid_train[target]
            X_arena, y_arena = valid_arena[features], valid_arena[target]

            # Treinando a nova Inteligência Artificial
            challenger = self._create_challenger_model(dna['type'])
            challenger.fit(X_train, y_train)

            # Avaliando o Desafiante
            if 'classifier' in dna['type']:
                preds_chal = challenger.predict_proba(X_arena)
                loss_chal = log_loss(y_arena, preds_chal)
            else:
                preds_chal = challenger.predict(X_arena)
                loss_chal = mean_absolute_error(y_arena, preds_chal) # Para regressores, usamos MAE

            # Avaliando o Campeão Atual (Se ele existir)
            replace_model = False
            if model_path.exists():
                try:
                    champion = joblib.load(model_path)
                    if 'classifier' in dna['type']:
                        preds_champ = champion.predict_proba(X_arena)
                        loss_champ = log_loss(y_arena, preds_champ)
                    else:
                        preds_champ = champion.predict(X_arena)
                        loss_champ = mean_absolute_error(y_arena, preds_champ)

                    # A Decisão do Sindicato: O Desafiante comete menos erros?
                    if loss_chal < loss_champ:
                        logger.info(f"   🟢 EVOLUÇÃO ALCANÇADA! Desafiante superou o Campeão.")
                        logger.info(f"      Loss Antiga: {loss_champ:.4f} | Loss Nova: {loss_chal:.4f}")
                        replace_model = True
                    else:
                        logger.info(f"   🛡️ CAMPEÃO RETÉM O TÍTULO. Modelo antigo ainda lê melhor o mercado atual.")
                        logger.info(f"      Loss Antiga: {loss_champ:.4f} | Loss Nova: {loss_chal:.4f}")
                except Exception as e:
                    logger.warning(f"   ⚠️ Campeão corrompido ou incompatível. Forçando substituição.")
                    replace_model = True
            else:
                logger.info(f"   🆕 Nenhum modelo anterior encontrado. Instalando Primeira Geração.")
                replace_model = True

            # O Veredito
            if replace_model:
                joblib.dump(challenger, model_path)
                oracles_updated += 1
            logger.info("   " + "-"*60)

        logger.info("==================================================================")
        logger.info(f" 🏆 CICLO CONCLUÍDO. Oráculos Atualizados: {oracles_updated}/7 ")
        logger.info(" A Fábrica de SGPs está operando com a Inteligência Suprema do Mercado.")
        logger.info("==================================================================\n")

if __name__ == "__main__":
    ContinuousEvolutionPipeline().execute_evolution_cycle()