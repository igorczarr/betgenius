# betgenius-backend/workers/brain/2c_model_gamma.py

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

class GammaOracle:
    """
    O Oráculo Gama (Ambas Marcam / BTTS) - Nível Institucional HFT.
    Procura assimetrias defensivas e calibra as probabilidades para encontrar EV puro.
    Utiliza Walk-Forward Validation, Gestão de Banca Kelly e lê as Odds de Abertura (Market Respect).
    """
    def __init__(self):
        self.data_vault_path = Path(__file__).parent / "data_vault" / "purified_tensors.parquet"
        self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # O CÉREBRO: Features focadas em Vulnerabilidade Mútua
        # INCLUI pin_odd_home/away (Abertura) como proxy da força institucional das equipas
        self.features = [
            'delta_elo', 'delta_wage_pct', 'delta_pontos', 'delta_posicao', 
            'delta_market_respect', 'delta_tension', 
            'delta_xg_micro', 'delta_xg_macro',
            'home_xg_for_ewma_micro', 'home_xg_against_ewma_micro',
            'away_xg_for_ewma_micro', 'away_xg_against_ewma_micro',
            'home_xg_for_ewma_macro', 'away_xg_for_ewma_macro',
            'home_aggression_ewma', 'away_aggression_ewma', 
            'home_win_streak', 'away_win_streak', 'home_winless_streak', 'away_winless_streak',
            'home_fraudulent_defense', 'home_fraudulent_attack',
            'away_fraudulent_defense', 'away_fraudulent_attack',
            ##'home_rest_days', 'away_rest_days',
            'pin_odd_home', 'pin_odd_away' # Abertura Pinnacle: O termómetro do mercado
        ]
        
        # GESTÃO DE RISCO E EXECUÇÃO
        self.MIN_EV_THRESHOLD = 0.04   # 4% Edge (Margem apertada no BTTS)
        self.INITIAL_BANKROLL = 10000.0
        self.KELLY_FRACTION = 0.15     # Kelly Conservador (Mitigação de Variância)
        self.MAX_STAKE_PCT = 0.05      # Teto máximo de 5% por aposta

    def prepare_target(self, df):
        # Target: 1 = BTTS SIM (Ambas Marcam), 0 = BTTS NÃO
        df['target_btts'] = ((df['home_goals'] > 0) & (df['away_goals'] > 0)).astype(int)
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
        logger.info(" ⚔️ INICIANDO FORJA DO ORÁCULO GAMA (BTTS + KELLY EV) ")
        logger.info("==================================================================")

        df = pd.read_parquet(self.data_vault_path)
        df = self.prepare_target(df)
        
        # Filtro de Sanidade: Apenas jogos validados e com histórico
        df = df[df['home_elo_before'] > 100].copy()

        # PREVENÇÃO DE VAZAMENTO: Ordenação Cronológica Estrita
        df = df.sort_values('match_date').reset_index(drop=True)
        
        # Blindagem de Features Ausentes
        for col in self.features:
            if col not in df.columns:
                logger.warning(f"⚠️ Feature ausente gerada como Zero: {col}")
                df[col] = 0.0

        logger.info(f"📂 Matriz Carregada: {len(df)} jogos.")
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

            X_train, y_train = df.iloc[pure_train_idx][self.features], df.iloc[pure_train_idx]['target_btts']
            X_calib, y_calib = df.iloc[calib_idx][self.features], df.iloc[calib_idx]['target_btts']
            X_test, y_test = df.iloc[test_index][self.features], df.iloc[test_index]['target_btts']

            # 1. O CÉREBRO BASE (XGBoost)
            base_model = xgb.XGBClassifier(
                objective='binary:logistic',
                eval_metric='logloss',
                n_estimators=450,
                learning_rate=0.02, 
                max_depth=4,         
                min_child_weight=4,  
                subsample=0.85,
                colsample_bytree=0.85,
                reg_alpha=0.2,
                reg_lambda=1.5,
                random_state=42,
                n_jobs=-1
            )
            base_model.fit(X_train, y_train)

            # 2. CALIBRAÇÃO ISOTÔNICA
            calibrated_model = CalibratedClassifierCV(estimator=base_model, method='isotonic', cv='prefit')
            calibrated_model.fit(X_calib, y_calib)

            # Guarda previsões OOS
            preds = calibrated_model.predict_proba(X_test)
            for i, match_idx in enumerate(test_index):
                out_of_sample_preds.append({
                    'match_id': df.iloc[match_idx]['match_id'],
                    'prob_no': preds[i][0],
                    'prob_yes': preds[i][1],
                    'actual_result': y_test.iloc[i],
                    # Recupera as odds de fechamento para avaliação financeira (Closing Odds)
                    'odd_btts_yes': df.iloc[match_idx].get('odd_btts_yes', 0),
                    'odd_btts_no': df.iloc[match_idx].get('odd_btts_no', 0)
                })
            
            # Salva o último modelo em produção
            if fold == 4:
                joblib.dump(calibrated_model, self.models_dir / "gamma_oracle_btts.joblib")
            
            fold += 1

        logger.info("✅ Oráculo Gama Treinado. Iniciando Execution Engine Financeiro...")

        # =================================================================
        # EXECUTION ENGINE (BACKTEST FINANCEIRO COM KELLY CRITERION)
        # =================================================================
        bankroll = self.INITIAL_BANKROLL
        bankroll_history = [bankroll]
        trades = []

        for pred in out_of_sample_preds:
            prob_y = pred['prob_yes']
            prob_n = pred['prob_no']
            
            odd_y = pred['odd_btts_yes']
            odd_n = pred['odd_btts_no']
            
            # Pula os jogos sem odds mapeadas
            if pd.isna(odd_y) or pd.isna(odd_n) or odd_y <= 1.0 or odd_n <= 1.0:
                continue
                
            ev_yes = (prob_y * odd_y) - 1.0
            ev_no = (prob_n * odd_n) - 1.0
            
            placed_bet = False
            profit = 0.0

            # Aposta no BTTS SIM
            if ev_yes >= self.MIN_EV_THRESHOLD and ev_yes > ev_no:
                kelly_pct = (ev_yes / (odd_y - 1.0)) * self.KELLY_FRACTION
                stake = min(bankroll * kelly_pct, bankroll * self.MAX_STAKE_PCT)
                
                profit = stake * (odd_y - 1.0) if pred['actual_result'] == 1 else -stake
                placed_bet = True

            # Aposta no BTTS NÃO
            elif ev_no >= self.MIN_EV_THRESHOLD:
                kelly_pct = (ev_no / (odd_n - 1.0)) * self.KELLY_FRACTION
                stake = min(bankroll * kelly_pct, bankroll * self.MAX_STAKE_PCT)
                
                profit = stake * (odd_n - 1.0) if pred['actual_result'] == 0 else -stake
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
        
        # Sharpe Ratio Anualizado Simples
        trades_array = np.array(trades)
        mean_trade = np.mean(trades_array) if total_bets > 0 else 0
        std_trade = np.std(trades_array) if total_bets > 0 else 1
        sharpe_ratio = (mean_trade / std_trade) * np.sqrt(total_bets) if std_trade > 0 else 0

        logger.info("\n================= [ RELATÓRIO DO FUNDO QUANTITATIVO (GAMMA) ] =================")
        logger.info(f"📊 VALIDAÇÃO TEMPORAL (Walk-Forward):")
        logger.info(f"   └ Banco Inicial: R$ {self.INITIAL_BANKROLL:.2f}")
        logger.info(f"   └ Operações Realizadas: {total_bets} (Filtro > {self.MIN_EV_THRESHOLD*100}% EV)")
        logger.info(f"   └ Win-Rate do Modelo: {win_rate:.1f}%")
        logger.info("-------------------------------------------------------------------------------")
        logger.info(f"📈 MÉTRICAS DE RISCO & RETORNO:")
        logger.info(f"   └ Banco Final: R$ {bankroll:.2f}")
        logger.info(f"   └ Lucro Líquido (PnL): R$ {(bankroll - self.INITIAL_BANKROLL):.2f}")
        logger.info(f"   └ Max Drawdown: {max_dd * 100:.2f}% (Risco de Ruína)")
        logger.info(f"   └ Sharpe Ratio: {sharpe_ratio:.2f}")
        
        if roi_pct > 0:
            logger.info(f"   🚀 CRESCIMENTO DO FUNDO (ROI Acumulado): +{roi_pct:.2f}% (Máquina BTTS!)")
        else:
            logger.info(f"   🩸 DÉFICIT DO FUNDO (ROI Acumulado): {roi_pct:.2f}% (Cuidado: Mercado Eficiente)")
        logger.info("===============================================================================\n")

if __name__ == "__main__":
    GammaOracle().train_and_evaluate()