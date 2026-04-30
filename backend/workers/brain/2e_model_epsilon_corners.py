# betgenius-backend/workers/brain/2e_model_epsilon_corners.py

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
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import TimeSeriesSplit
import joblib
from pathlib import Path
from dotenv import load_dotenv

pd.set_option('future.no_silent_downcasting', True)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

class EpsilonOracle:
    """
    O Oráculo Épsilon (Especialista em Escanteios / Corners) - Nível Institucional HFT.
    Utiliza Calibração Isotónica, Walk-Forward Validation e Kelly Criterion
    para encontrar EV+ nas linhas asiáticas de Over/Under 9.5.
    """
    def __init__(self):
        self.data_vault_path = Path(__file__).parent / "data_vault" / "purified_tensors.parquet"
        self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # O CÉREBRO: Foco em Volume Ofensivo (xG), Agressividade e Tensão
        # Removemos data leaks (como chutes do próprio jogo) e usamos as EWMAs e as Odds de Abertura.
        self.features = [
            'delta_elo', 'delta_wage_pct', 'delta_pontos', 'delta_posicao', 
            'delta_market_respect', 'delta_tension', 
            'delta_xg_micro', 'delta_xg_macro',
            'home_xg_for_ewma_micro', 'home_xg_against_ewma_micro',
            'away_xg_for_ewma_micro', 'away_xg_against_ewma_micro',
            'home_xg_for_ewma_macro', 'away_xg_for_ewma_macro',
            'home_aggression_ewma', 'away_aggression_ewma', 
            'home_win_streak', 'away_win_streak', 'home_winless_streak', 'away_winless_streak',
            'home_fraudulent_defense', 'away_fraudulent_defense',
            ##'home_rest_days', 'away_rest_days',
            'pin_odd_home', 'pin_odd_away' # Abertura Pinnacle: Reflete o favoritismo do jogo
        ]
        
        # GESTÃO DE RISCO E EXECUÇÃO
        self.MIN_EV_THRESHOLD = 0.05   # Edge mínimo exigido de 5%
        self.INITIAL_BANKROLL = 10000.0
        self.KELLY_FRACTION = 0.15     # Fração do Kelly para controlar a variância de escanteios
        self.MAX_STAKE_PCT = 0.05      # Teto máximo de 5% da banca por aposta

    def prepare_target(self, df):
        # Target: 0 = Under 9.5 Corners, 1 = Over 9.5 Corners
        df['target_ou_95_corners'] = (df['target_total_corners'] > 9.5).astype(int)
        return df

    def calculate_drawdown(self, bankroll_history):
        peak = bankroll_history[0]
        max_dd = 0.0
        for value in bankroll_history:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
        return max_dd

    def train_and_evaluate(self):
        if not self.data_vault_path.exists():
            logger.error("❌ Data Vault não encontrado. Rode o 1_data_sanitizer.py.")
            sys.exit(1)
            
        logger.info("==================================================================")
        logger.info(" 📐 INICIANDO FORJA DO ORÁCULO ÉPSILON (CANTOS O/U 9.5 + KELLY EV) ")
        logger.info("==================================================================")

        df = pd.read_parquet(self.data_vault_path)
        
        # Filtro de Sanidade: Precisamos de jogos que registraram escanteios e Elo válido
        initial_len = len(df)
        df = df[(df['home_elo_before'] > 100) & (df['target_total_corners'] > 0)].copy()
        logger.info(f"📂 Matriz Carregada: {len(df)} jogos físicos disponíveis (Descartados {initial_len - len(df)}).")

        df = self.prepare_target(df)

        # ORDENAÇÃO CRONOLÓGICA (Prevenção Absoluta de Data Leakage)
        df = df.sort_values('match_date').reset_index(drop=True)
        
        # Blindagem de Features Ausentes
        for col in self.features:
            if col not in df.columns:
                logger.warning(f"⚠️ Feature ausente gerada como Zero: {col}")
                df[col] = 0.0

        logger.info("⏳ Iniciando Walk-Forward Validation (Simulação do Mundo Real)...")

        # Configuração do Walk-Forward
        tscv = TimeSeriesSplit(n_splits=4)
        out_of_sample_preds = []
        
        fold = 1
        for train_index, test_index in tscv.split(df):
            logger.info(f"   └ Processando Fold Temporal {fold}/4...")
            
            calib_size = int(len(train_index) * 0.20)
            pure_train_idx = train_index[:-calib_size]
            calib_idx = train_index[-calib_size:]

            X_train, y_train = df.iloc[pure_train_idx][self.features], df.iloc[pure_train_idx]['target_ou_95_corners']
            X_calib, y_calib = df.iloc[calib_idx][self.features], df.iloc[calib_idx]['target_ou_95_corners']
            X_test, y_test = df.iloc[test_index][self.features], df.iloc[test_index]['target_ou_95_corners']

            # 1. O CÉREBRO BASE (Classificador Binário)
            base_model = xgb.XGBClassifier(
                objective='binary:logistic',
                eval_metric='logloss',
                n_estimators=400,
                learning_rate=0.02,
                max_depth=4,         
                min_child_weight=5,  
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=42,
                n_jobs=-1
            )
            base_model.fit(X_train, y_train)

            # 2. CALIBRAÇÃO ISOTÓNICA
            calibrated_model = CalibratedClassifierCV(estimator=base_model, method='isotonic', cv='prefit')
            calibrated_model.fit(X_calib, y_calib)

            # Guarda previsões OOS
            preds = calibrated_model.predict_proba(X_test)
            for i, match_idx in enumerate(test_index):
                out_of_sample_preds.append({
                    'match_id': df.iloc[match_idx]['match_id'],
                    'prob_under': preds[i][0],
                    'prob_over': preds[i][1],
                    'actual_result': y_test.iloc[i],
                    # Recupera as odds de cantos (garanta que estas colunas existem no banco/sanitizer)
                    'odd_corners_over_95': df.iloc[match_idx].get('odd_corners_over_95', 0),
                    'odd_corners_under_95': df.iloc[match_idx].get('odd_corners_under_95', 0)
                })
            
            # Salva o último modelo em produção
            if fold == 4:
                joblib.dump(calibrated_model, self.models_dir / "epsilon_oracle_corners.joblib")
            
            fold += 1

        logger.info("✅ Oráculo Épsilon Treinado. Iniciando Execution Engine Financeiro...")

        # =================================================================
        # EXECUTION ENGINE (BACKTEST FINANCEIRO COM KELLY CRITERION)
        # =================================================================
        bankroll = self.INITIAL_BANKROLL
        bankroll_history = [bankroll]
        trades = []

        for pred in out_of_sample_preds:
            prob_o = pred['prob_over']
            prob_u = pred['prob_under']
            
            odd_o95 = pred['odd_corners_over_95']
            odd_u95 = pred['odd_corners_under_95']
            
            if pd.isna(odd_o95) or pd.isna(odd_u95) or odd_o95 <= 1.0 or odd_u95 <= 1.0:
                continue
                
            ev_over = (prob_o * odd_o95) - 1.0
            ev_under = (prob_u * odd_u95) - 1.0
            
            placed_bet = False
            profit = 0.0

            # Aposta no OVER 9.5
            if ev_over >= self.MIN_EV_THRESHOLD and ev_over > ev_under:
                kelly_pct = (ev_over / (odd_o95 - 1.0)) * self.KELLY_FRACTION
                stake = min(bankroll * kelly_pct, bankroll * self.MAX_STAKE_PCT)
                
                profit = stake * (odd_o95 - 1.0) if pred['actual_result'] == 1 else -stake
                placed_bet = True

            # Aposta no UNDER 9.5
            elif ev_under >= self.MIN_EV_THRESHOLD:
                kelly_pct = (ev_under / (odd_u95 - 1.0)) * self.KELLY_FRACTION
                stake = min(bankroll * kelly_pct, bankroll * self.MAX_STAKE_PCT)
                
                profit = stake * (odd_u95 - 1.0) if pred['actual_result'] == 0 else -stake
                placed_bet = True

            if placed_bet:
                bankroll += profit
                bankroll_history.append(bankroll)
                trades.append(profit)

        # CÁLCULO DE MÉTRICAS INSTITUCIONAIS
        total_bets = len(trades)
        winning_bets = sum(1 for t in trades if t > 0)
        win_rate = (winning_bets / total_bets * 100) if total_bets > 0 else 0.0
        
        roi_pct = ((bankroll - self.INITIAL_BANKROLL) / self.INITIAL_BANKROLL) * 100
        max_dd = self.calculate_drawdown(bankroll_history)
        
        # Sharpe Ratio
        trades_array = np.array(trades)
        mean_trade = np.mean(trades_array) if total_bets > 0 else 0
        std_trade = np.std(trades_array) if total_bets > 0 else 1
        sharpe_ratio = (mean_trade / std_trade) * np.sqrt(total_bets) if std_trade > 0 else 0

        logger.info("\n================= [ RELATÓRIO DO FUNDO QUANTITATIVO (EPSILON) ] =================")
        logger.info(f"📊 VALIDAÇÃO TEMPORAL (Walk-Forward):")
        
        if total_bets == 0:
            logger.warning(f"   ⚠️ Nenhuma Odd de Escanteios ('odd_corners_over_95') encontrada no histórico. ROI Omitido.")
            logger.warning(f"   (Assegure-se de que o Data Sanitizer extrai as odds de cantos para simular lucro)")
        else:
            logger.info(f"   └ Banco Inicial: R$ {self.INITIAL_BANKROLL:.2f}")
            logger.info(f"   └ Operações Realizadas: {total_bets} (Filtro > {self.MIN_EV_THRESHOLD*100}% EV)")
            logger.info(f"   └ Win-Rate do Modelo: {win_rate:.1f}%")
            logger.info("---------------------------------------------------------------------------------")
            logger.info(f"📈 MÉTRICAS DE RISCO & RETORNO:")
            logger.info(f"   └ Banco Final: R$ {bankroll:.2f}")
            logger.info(f"   └ Lucro Líquido (PnL): R$ {(bankroll - self.INITIAL_BANKROLL):.2f}")
            logger.info(f"   └ Max Drawdown: {max_dd * 100:.2f}% (Risco de Ruína)")
            logger.info(f"   └ Sharpe Ratio: {sharpe_ratio:.2f}")
            
            if roi_pct > 0:
                logger.info(f"   🚀 CRESCIMENTO DO FUNDO (ROI Acumulado): +{roi_pct:.2f}% (Máquina de Cantos!)")
            else:
                logger.info(f"   🩸 DÉFICIT DO FUNDO (ROI Acumulado): {roi_pct:.2f}% (Mercado muito eficiente)")
        logger.info("=================================================================================\n")

if __name__ == "__main__":
    EpsilonOracle().train_and_evaluate()