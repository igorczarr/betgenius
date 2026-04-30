# betgenius-backend/workers/brain/2d_model_delta_ht.py

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

# Suprime os avisos inofensivos de downcasting do Pandas
pd.set_option('future.no_silent_downcasting', True)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

class DeltaOracle:
    """
    O Oráculo Delta (Especialista em Half-Time).
    Foco Institucional: Identifica ineficiências na primeira metade do jogo.
    Treina dois modelos simultâneos: HT 1X2 e HT Over/Under 1.5 Gols.
    Utiliza Walk-Forward Validation e Gestão de Risco HFT (Kelly Criterion).
    """
    def __init__(self):
        self.data_vault_path = Path(__file__).parent / "data_vault" / "purified_tensors.parquet"
        self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # O ARSENAL: Foco na matriz construída (Tensão, Agressividade, xG e Odds de Abertura)
        # pin_odd_home/away medem a força de mercado sem vazar o fechamento
        self.features = [
            'delta_elo', 'delta_wage_pct', 'delta_pontos', 'delta_posicao', 
            'delta_market_respect', 'delta_tension', 
            'delta_xg_micro', 'delta_xg_macro',
            'home_xg_for_ewma_micro', 'away_xg_for_ewma_micro',
            'home_xg_against_ewma_micro', 'away_xg_against_ewma_micro',
            'home_aggression_ewma', 'away_aggression_ewma', 
            'home_fraudulent_defense', 'away_fraudulent_defense',
            'home_fraudulent_attack', 'away_fraudulent_attack',
            'home_win_streak', 'away_win_streak',
            ##'home_rest_days', 'away_rest_days',
            'pin_odd_home', 'pin_odd_away' # Abertura Pinnacle: O Respeito Institucional
        ]
        
        # Gestão de Risco HFT e Execution Engine
        self.MIN_EV_THRESHOLD = 0.05   # Edge mínimo exigido de 5%
        self.INITIAL_BANKROLL = 10000.0
        self.KELLY_FRACTION = 0.15     # Fração de Kelly para amortecer a variância
        self.MAX_STAKE_PCT = 0.05      # Teto máximo de 5% da banca por aposta

    def prepare_targets(self, df):
        # Target 1: HT 1X2 (0 = Away, 1 = Draw, 2 = Home)
        conditions_1x2 = [
            (df['ht_home_goals'] < df['ht_away_goals']),
            (df['ht_home_goals'] == df['ht_away_goals']),
            (df['ht_home_goals'] > df['ht_away_goals'])
        ]
        df['target_ht_1x2'] = np.select(conditions_1x2, [0, 1, 2], default=1)
        
        # Target 2: HT Over/Under (Consideramos a linha asiática padrão HT de 1.5 gols)
        # 0 = Under 1.5 HT | 1 = Over 1.5 HT
        ht_total_goals = df['ht_home_goals'] + df['ht_away_goals']
        df['target_ht_ou15'] = (ht_total_goals > 1.5).astype(int)
        
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
        logger.info(" ⏱️ INICIANDO FORJA DO ORÁCULO DELTA (HT 1X2 & HT O/U 1.5 + KELLY) ")
        logger.info("==================================================================")

        df = pd.read_parquet(self.data_vault_path)
        
        # FILTRO DE SANIDADE: Garante que há dados de HT e ranking válido
        initial_len = len(df)
        df = df[(df['home_elo_before'] > 100) & (df['ht_home_goals'].notna()) & (df['ht_away_goals'].notna())].copy()
        logger.info(f"📂 Matriz Carregada: {len(df)} jogos de Elite disponíveis (Descartados {initial_len - len(df)}).")

        df = self.prepare_targets(df)

        # ORDENAÇÃO CRONOLÓGICA (Prevenção Absoluta de Data Leakage)
        df = df.sort_values('match_date').reset_index(drop=True)
        
        # Fallback de segurança para features da Matriz
        for col in self.features:
            if col not in df.columns:
                logger.warning(f"⚠️ Feature ausente gerada como Zero: {col}")
                df[col] = 0.0

        logger.info("⏳ Iniciando Walk-Forward Validation (Time Series Split) para ambos os Modelos...")

        tscv = TimeSeriesSplit(n_splits=4)
        
        out_of_sample_preds_1x2 = []
        out_of_sample_preds_ou = []
        
        fold = 1
        for train_index, test_index in tscv.split(df):
            logger.info(f"   └ Processando Fold Temporal {fold}/4...")
            
            calib_size = int(len(train_index) * 0.20)
            pure_train_idx = train_index[:-calib_size]
            calib_idx = train_index[-calib_size:]

            X_train = df.iloc[pure_train_idx][self.features]
            X_calib = df.iloc[calib_idx][self.features]
            X_test  = df.iloc[test_index][self.features]

            # ==========================================================
            # MODELO 1: HT 1X2
            # ==========================================================
            y_train_1x2 = df.iloc[pure_train_idx]['target_ht_1x2']
            y_calib_1x2 = df.iloc[calib_idx]['target_ht_1x2']
            y_test_1x2  = df.iloc[test_index]['target_ht_1x2']
            
            base_model_1x2 = xgb.XGBClassifier(
                objective='multi:softprob', num_class=3, eval_metric='mlogloss',
                n_estimators=350, learning_rate=0.02, max_depth=4, min_child_weight=4,
                subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1
            )
            base_model_1x2.fit(X_train, y_train_1x2)
            
            calibrated_1x2 = CalibratedClassifierCV(estimator=base_model_1x2, method='isotonic', cv='prefit')
            calibrated_1x2.fit(X_calib, y_calib_1x2)
            
            preds_1x2 = calibrated_1x2.predict_proba(X_test)
            for i, match_idx in enumerate(test_index):
                out_of_sample_preds_1x2.append({
                    'match_id': df.iloc[match_idx]['match_id'],
                    'prob_away': preds_1x2[i][0],
                    'prob_draw': preds_1x2[i][1],
                    'prob_home': preds_1x2[i][2],
                    'actual_result': y_test_1x2.iloc[i],
                    # Recupera as odds do DF (Caso existam na base consolidada, caso contrário 0)
                    'odd_ht_home': df.iloc[match_idx].get('odd_ht_home', 0),
                    'odd_ht_away': df.iloc[match_idx].get('odd_ht_away', 0)
                })

            if fold == 4:
                joblib.dump(calibrated_1x2, self.models_dir / "delta_oracle_ht_1x2.joblib")

            # ==========================================================
            # MODELO 2: HT OVER/UNDER 1.5
            # ==========================================================
            y_train_ou = df.iloc[pure_train_idx]['target_ht_ou15']
            y_calib_ou = df.iloc[calib_idx]['target_ht_ou15']
            y_test_ou  = df.iloc[test_index]['target_ht_ou15']
            
            base_model_ou = xgb.XGBClassifier(
                objective='binary:logistic', eval_metric='logloss',
                n_estimators=350, learning_rate=0.02, max_depth=4, min_child_weight=4,
                subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1
            )
            base_model_ou.fit(X_train, y_train_ou)
            
            calibrated_ou = CalibratedClassifierCV(estimator=base_model_ou, method='isotonic', cv='prefit')
            calibrated_ou.fit(X_calib, y_calib_ou)
            
            preds_ou = calibrated_ou.predict_proba(X_test)
            for i, match_idx in enumerate(test_index):
                out_of_sample_preds_ou.append({
                    'match_id': df.iloc[match_idx]['match_id'],
                    'prob_under': preds_ou[i][0],
                    'prob_over': preds_ou[i][1],
                    'actual_result': y_test_ou.iloc[i],
                    'odd_ht_over_15': df.iloc[match_idx].get('odd_ht_over_15', 0),
                    'odd_ht_under_15': df.iloc[match_idx].get('odd_ht_under_15', 0)
                })

            if fold == 4:
                joblib.dump(calibrated_ou, self.models_dir / "delta_oracle_ht_ou.joblib")

            fold += 1

        logger.info("✅ Oráculos Delta (HT 1X2 e HT O/U) Calibrados. Iniciando Execution Engine Financeiro...")

        # ==========================================================
        # AUDITORIA E BACKTEST FINANCEIRO (KELLY CRITERION)
        # ==========================================================
        bankroll_1x2 = self.INITIAL_BANKROLL
        bankroll_1x2_history = [bankroll_1x2]
        trades_1x2 = []

        bankroll_ou = self.INITIAL_BANKROLL
        bankroll_ou_history = [bankroll_ou]
        trades_ou = []

        # ---- BACKTEST 1X2 HT ----
        for pred in out_of_sample_preds_1x2:
            odd_h = pred['odd_ht_home']
            odd_a = pred['odd_ht_away']
            
            if pd.isna(odd_h) or pd.isna(odd_a) or odd_h <= 1.0 or odd_a <= 1.0:
                continue
                
            ev_home = (pred['prob_home'] * odd_h) - 1.0
            ev_away = (pred['prob_away'] * odd_a) - 1.0
            
            placed_bet = False
            profit = 0.0

            if ev_home >= self.MIN_EV_THRESHOLD and ev_home > ev_away:
                kelly_pct = (ev_home / (odd_h - 1.0)) * self.KELLY_FRACTION
                stake = min(bankroll_1x2 * kelly_pct, bankroll_1x2 * self.MAX_STAKE_PCT)
                
                profit = stake * (odd_h - 1.0) if pred['actual_result'] == 2 else -stake
                placed_bet = True

            elif ev_away >= self.MIN_EV_THRESHOLD:
                kelly_pct = (ev_away / (odd_a - 1.0)) * self.KELLY_FRACTION
                stake = min(bankroll_1x2 * kelly_pct, bankroll_1x2 * self.MAX_STAKE_PCT)
                
                profit = stake * (odd_a - 1.0) if pred['actual_result'] == 0 else -stake
                placed_bet = True

            if placed_bet:
                bankroll_1x2 += profit
                bankroll_1x2_history.append(bankroll_1x2)
                trades_1x2.append(profit)

        # ---- BACKTEST OVER/UNDER 1.5 HT ----
        for pred in out_of_sample_preds_ou:
            odd_o = pred['odd_ht_over_15']
            odd_u = pred['odd_ht_under_15']
            
            if pd.isna(odd_o) or pd.isna(odd_u) or odd_o <= 1.0 or odd_u <= 1.0:
                continue
                
            ev_over = (pred['prob_over'] * odd_o) - 1.0
            ev_under = (pred['prob_under'] * odd_u) - 1.0
            
            placed_bet = False
            profit = 0.0

            if ev_over >= self.MIN_EV_THRESHOLD and ev_over > ev_under:
                kelly_pct = (ev_over / (odd_o - 1.0)) * self.KELLY_FRACTION
                stake = min(bankroll_ou * kelly_pct, bankroll_ou * self.MAX_STAKE_PCT)
                
                profit = stake * (odd_o - 1.0) if pred['actual_result'] == 1 else -stake
                placed_bet = True

            elif ev_under >= self.MIN_EV_THRESHOLD:
                kelly_pct = (ev_under / (odd_u - 1.0)) * self.KELLY_FRACTION
                stake = min(bankroll_ou * kelly_pct, bankroll_ou * self.MAX_STAKE_PCT)
                
                profit = stake * (odd_u - 1.0) if pred['actual_result'] == 0 else -stake
                placed_bet = True

            if placed_bet:
                bankroll_ou += profit
                bankroll_ou_history.append(bankroll_ou)
                trades_ou.append(profit)

        # Métricas de Resumo HT 1x2
        bets_1x2 = len(trades_1x2)
        roi_1x2 = ((bankroll_1x2 - self.INITIAL_BANKROLL) / self.INITIAL_BANKROLL * 100) if bets_1x2 > 0 else 0.0
        max_dd_1x2 = self.calculate_drawdown(bankroll_1x2_history)
        
        # Métricas de Resumo HT O/U 1.5
        bets_ou = len(trades_ou)
        roi_ou = ((bankroll_ou - self.INITIAL_BANKROLL) / self.INITIAL_BANKROLL * 100) if bets_ou > 0 else 0.0
        max_dd_ou = self.calculate_drawdown(bankroll_ou_history)

        logger.info("\n================= [ RELATÓRIO DO FUNDO QUANTITATIVO (DELTA HT) ] =================")
        logger.info(f"💰 BACKTEST FINANCEIRO (Walk-Forward + Kelly Criterion):")
        
        if bets_1x2 == 0 and bets_ou == 0:
            logger.warning(f"   ⚠️ Nenhuma Odd de HT encontrada no histórico consolidado. ROI omitido.")
            logger.warning(f"   (Para simular lucro real no Delta, o Sanitizer deve injetar 'odd_ht_home', 'odd_ht_over_15', etc.)")
        else:
            if bets_1x2 > 0:
                logger.info(f"   [HT 1X2] Operações: {bets_1x2} | PnL: R$ {(bankroll_1x2 - self.INITIAL_BANKROLL):.2f} | YIELD: {roi_1x2:.2f}% | Max DD: {max_dd_1x2*100:.2f}%")
            if bets_ou > 0:
                logger.info(f"   [HT O/U] Operações: {bets_ou}  | PnL: R$ {(bankroll_ou - self.INITIAL_BANKROLL):.2f}  | YIELD: {roi_ou:.2f}% | Max DD: {max_dd_ou*100:.2f}%")
                
        logger.info("==================================================================================\n")

if __name__ == "__main__":
    DeltaOracle().train_and_evaluate()