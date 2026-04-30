# betgenius-backend/workers/brain/2a_model_alpha.py

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

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

class AlphaOracle:
    """
    O Oráculo Sênior (Nível Institucional). 
    Foco absoluto em Valor Esperado (EV), Closing Line Value (CLV),
    Critério de Kelly e Walk-Forward Validation.
    """
    def __init__(self):
        self.data_vault_path = Path(__file__).parent / "data_vault" / "purified_tensors.parquet"
        self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # O ARSENAL: Integração total das dimensões Elo, Temporal, Contexto e Mercado Inicial
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
            'pin_odd_home', 'pin_odd_away' # Abertura (Opening Line) atua como Feature
        ]
        
        # GESTÃO DE RISCO (Execution Engine)
        self.MIN_EV_THRESHOLD = 0.04   # 4% de Edge mínimo
        self.INITIAL_BANKROLL = 10000.0
        self.KELLY_FRACTION = 0.15     # Kelly Fracionado (Segurança Institucional)
        self.MAX_STAKE_PCT = 0.05      # Aposta máxima de 5% da banca

    def prepare_target(self, df):
        conditions = [
            (df['home_goals'] < df['away_goals']),
            (df['home_goals'] == df['away_goals']),
            (df['home_goals'] > df['away_goals'])
        ]
        df['target_match_result'] = np.select(conditions, [0, 1, 2], default=1)
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
        logger.info(" 🧠 INICIANDO FORJA DO ORÁCULO ALPHA (WALK-FORWARD & KELLY EV) ")
        logger.info("==================================================================")

        df = pd.read_parquet(self.data_vault_path)
        df = self.prepare_target(df)
        
        # Filtro de Sanidade
        df = df[df['home_elo_before'] > 100].copy()
        
        # Ordenação Cronológica Estrita (Impedir Leakage)
        df = df.sort_values('match_date').reset_index(drop=True)
        
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
            
            # Sub-split do train para a Calibração Isotônica (últimos 20% do treino)
            calib_size = int(len(train_index) * 0.20)
            pure_train_idx = train_index[:-calib_size]
            calib_idx = train_index[-calib_size:]

            X_train, y_train = df.iloc[pure_train_idx][self.features], df.iloc[pure_train_idx]['target_match_result']
            X_calib, y_calib = df.iloc[calib_idx][self.features], df.iloc[calib_idx]['target_match_result']
            X_test, y_test = df.iloc[test_index][self.features], df.iloc[test_index]['target_match_result']

            base_model = xgb.XGBClassifier(
                objective='multi:softprob',
                num_class=3,
                eval_metric='mlogloss',
                n_estimators=400,
                learning_rate=0.02,
                max_depth=4,         
                min_child_weight=4,  
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,      
                reg_lambda=1.0,     
                random_state=42,
                n_jobs=-1
            )
            base_model.fit(X_train, y_train)

            calibrated_model = CalibratedClassifierCV(estimator=base_model, method='isotonic', cv='prefit')
            calibrated_model.fit(X_calib, y_calib)

            # Guarda previsões Out-Of-Sample para o Backtest Financeiro
            preds = calibrated_model.predict_proba(X_test)
            for i, match_idx in enumerate(test_index):
                out_of_sample_preds.append({
                    'match_id': df.iloc[match_idx]['match_id'],
                    'prob_away': preds[i][0],
                    'prob_draw': preds[i][1],
                    'prob_home': preds[i][2],
                    'actual_result': y_test.iloc[i],
                    'closing_odd_home': df.iloc[match_idx].get('closing_odd_home', 0),
                    'closing_odd_away': df.iloc[match_idx].get('closing_odd_away', 0),
                    'pin_odd_home': df.iloc[match_idx].get('pin_odd_home', 0), # Opening Line
                    'pin_odd_away': df.iloc[match_idx].get('pin_odd_away', 0)
                })
            
            # Salva o último modelo treinado para produção
            if fold == 4:
                joblib.dump(calibrated_model, self.models_dir / "alpha_oracle_1x2.joblib")
            
            fold += 1

        logger.info("✅ Oráculo Treinado. Iniciando Execution Engine Financeiro...")

        # =================================================================
        # EXECUTION ENGINE (BACKTEST FINANCEIRO COM KELLY CRITERION)
        # =================================================================
        bankroll = self.INITIAL_BANKROLL
        bankroll_history = [bankroll]
        trades = []
        clv_beaten = 0

        for pred in out_of_sample_preds:
            prob_h = pred['prob_home']
            prob_a = pred['prob_away']
            
            # ATENÇÃO: As casas liquidam pelas CLOSING ODDS. É aqui que medimos lucro.
            odd_h = pred['closing_odd_home']
            odd_a = pred['closing_odd_away']
            
            if pd.isna(odd_h) or pd.isna(odd_a) or odd_h <= 1.0 or odd_a <= 1.0:
                continue
                
            ev_home = (prob_h * odd_h) - 1.0
            ev_away = (prob_a * odd_a) - 1.0
            
            placed_bet = False
            stake = 0.0
            profit = 0.0

            # Lógica HFT: Aposta no lado de maior EV (se superar o threshold)
            if ev_home >= self.MIN_EV_THRESHOLD and ev_home > ev_away:
                kelly_pct = (ev_home / (odd_h - 1.0)) * self.KELLY_FRACTION
                stake = min(bankroll * kelly_pct, bankroll * self.MAX_STAKE_PCT)
                
                if pred['actual_result'] == 2:
                    profit = stake * (odd_h - 1.0)
                else:
                    profit = -stake
                
                placed_bet = True
                # Mede se vencemos o Closing Line usando o Opening Line
                if pred['pin_odd_home'] > odd_h: clv_beaten += 1

            elif ev_away >= self.MIN_EV_THRESHOLD:
                kelly_pct = (ev_away / (odd_a - 1.0)) * self.KELLY_FRACTION
                stake = min(bankroll * kelly_pct, bankroll * self.MAX_STAKE_PCT)
                
                if pred['actual_result'] == 0:
                    profit = stake * (odd_a - 1.0)
                else:
                    profit = -stake
                
                placed_bet = True
                if pred['pin_odd_away'] > odd_a: clv_beaten += 1

            if placed_bet:
                bankroll += profit
                bankroll_history.append(bankroll)
                trades.append(profit)

        # CÁLCULO DE MÉTRICAS INSTITUCIONAIS
        total_bets = len(trades)
        winning_bets = sum(1 for t in trades if t > 0)
        win_rate = (winning_bets / total_bets * 100) if total_bets > 0 else 0.0
        
        total_turnover = sum(abs(t) if t < 0 else (t / (odd_h - 1.0) if 'odd_h' in locals() else t) for t in trades) # Aproximação de volume
        roi_pct = ((bankroll - self.INITIAL_BANKROLL) / self.INITIAL_BANKROLL) * 100
        
        max_dd = self.calculate_drawdown(bankroll_history)
        
        # Sharpe Ratio Anualizado Simples (Assumindo Risk-Free Rate = 0)
        trades_array = np.array(trades)
        mean_trade = np.mean(trades_array) if total_bets > 0 else 0
        std_trade = np.std(trades_array) if total_bets > 0 else 1
        sharpe_ratio = (mean_trade / std_trade) * np.sqrt(total_bets) if std_trade > 0 else 0

        logger.info("\n================= [ RELATÓRIO DO FUNDO QUANTITATIVO (ALPHA) ] =================")
        logger.info(f"📊 VALIDAÇÃO TEMPORAL (Walk-Forward):")
        logger.info(f"   └ Banco Inicial: R$ {self.INITIAL_BANKROLL:.2f}")
        logger.info(f"   └ Operações Realizadas: {total_bets} (Filtro > {self.MIN_EV_THRESHOLD*100}% EV)")
        logger.info(f"   └ Win-Rate do Modelo: {win_rate:.1f}%")
        logger.info(f"   └ CLV Beaten Rate (Batidas na Linha de Abertura): {(clv_beaten/total_bets*100) if total_bets > 0 else 0:.1f}%")
        logger.info("-------------------------------------------------------------------------------")
        logger.info(f"📈 MÉTRICAS DE RISCO & RETORNO:")
        logger.info(f"   └ Banco Final: R$ {bankroll:.2f}")
        logger.info(f"   └ Lucro Líquido (PnL): R$ {(bankroll - self.INITIAL_BANKROLL):.2f}")
        logger.info(f"   └ Max Drawdown: {max_dd * 100:.2f}% (Risco de Ruína)")
        logger.info(f"   └ Sharpe Ratio: {sharpe_ratio:.2f} (Alvo Institucional > 2.0)")
        
        if roi_pct > 0:
            logger.info(f"   🚀 CRESCIMENTO DO FUNDO (ROI Acumulado): +{roi_pct:.2f}%")
        else:
            logger.info(f"   🩸 DÉFICIT DO FUNDO (ROI Acumulado): {roi_pct:.2f}%")
        logger.info("===============================================================================\n")

if __name__ == "__main__":
    AlphaOracle().train_and_evaluate()