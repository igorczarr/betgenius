# betgenius-backend/workers/brain/2f_model_zeta_cards.py

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

class ZetaOracle:
    """
    O Oráculo Zeta (Cartões / Booking Points).
    Nível Institucional: Abandona o Poisson (devido à alta variância emocional) e adota
    Calibração Isotónica num Classificador Binário contra a linha asiática de 4.5.
    Focado em ROI (Valor Esperado), Walk-Forward Validation e Kelly Criterion.
    """
    def __init__(self):
        self.data_vault_path = Path(__file__).parent / "data_vault" / "purified_tensors.parquet"
        self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # O ARSENAL: Foco extremo em Tensão, Faltas (Aggression), Fadiga e Contexto de Mercado
        self.features = [
            'delta_elo', 'delta_wage_pct', 'delta_pontos', 'delta_posicao', 
            'delta_market_respect', 'delta_tension', 
            'home_aggression_ewma', 'away_aggression_ewma', 
            'home_xg_for_ewma_micro', 'away_xg_for_ewma_micro', # Pressão gera faltas da defesa
            'home_fraudulent_defense', 'away_fraudulent_defense',
            ##'home_rest_days', 'away_rest_days', # Pernas cansadas chegam atrasadas à bola
            'pin_odd_home', 'pin_odd_away' # Indica se é um jogo de "David vs Golias"
        ]
        
        # Gestão de Risco HFT (Cartões têm maior margem da casa, exigimos EV rigoroso)
        self.MIN_EV_THRESHOLD = 0.05   # Edge mínimo exigido de 5%
        self.INITIAL_BANKROLL = 10000.0
        self.KELLY_FRACTION = 0.15     # Fração do Kelly para controlar variância alta (cartões)
        self.MAX_STAKE_PCT = 0.05      # Teto máximo de 5% da banca por aposta

    def prepare_target(self, df):
        # A Linha Ouro Asiática para Cartões é 4.5
        # Target: 0 = Under 4.5 Cartões, 1 = Over 4.5 Cartões (5 ou mais)
        df['target_ou_45_cards'] = (df['target_total_cards'] > 4.5).astype(int)
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
        logger.info(" 🟨 INICIANDO FORJA DO ORÁCULO ZETA (CARTÕES O/U 4.5 + KELLY EV) ")
        logger.info("==================================================================")

        df = pd.read_parquet(self.data_vault_path)
        
        # Filtro de Sanidade: Apenas jogos válidos onde cartões foram registados e elo validado
        initial_len = len(df)
        df = df[(df['home_elo_before'] > 100) & (df['target_total_cards'] >= 0)].copy()
        logger.info(f"📂 Matriz Carregada: {len(df)} jogos tensos disponíveis (Descartados {initial_len - len(df)}).")

        df = self.prepare_target(df)

        # ORDENAÇÃO CRONOLÓGICA (Prevenção Absoluta de Data Leakage)
        df = df.sort_values('match_date').reset_index(drop=True)
        
        # Blindagem de Features Ausentes
        for col in self.features:
            if col not in df.columns:
                logger.warning(f"⚠️ Feature ausente gerada como Zero: {col}")
                df[col] = 0.0

        logger.info("⏳ Iniciando Walk-Forward Validation (Adaptação a Mudanças de Arbitragem e VAR)...")

        tscv = TimeSeriesSplit(n_splits=4)
        out_of_sample_preds = []
        
        fold = 1
        for train_index, test_index in tscv.split(df):
            logger.info(f"   └ Processando Fold Temporal {fold}/4...")
            
            calib_size = int(len(train_index) * 0.20)
            pure_train_idx = train_index[:-calib_size]
            calib_idx = train_index[-calib_size:]

            X_train, y_train = df.iloc[pure_train_idx][self.features], df.iloc[pure_train_idx]['target_ou_45_cards']
            X_calib, y_calib = df.iloc[calib_idx][self.features], df.iloc[calib_idx]['target_ou_45_cards']
            X_test, y_test = df.iloc[test_index][self.features], df.iloc[test_index]['target_ou_45_cards']

            # 1. O CÉREBRO BASE (Classificador Binário)
            base_model = xgb.XGBClassifier(
                objective='binary:logistic',
                eval_metric='logloss',
                n_estimators=400,
                learning_rate=0.015,
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

            # 2. CALIBRAÇÃO ISOTÓNICA (Removendo o viés de overconfidence)
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
                    # Recupera as odds para backtest (Necessário extrai-las no Sanitizer)
                    'odd_cards_over_45': df.iloc[match_idx].get('odd_cards_over_45', 0),
                    'odd_cards_under_45': df.iloc[match_idx].get('odd_cards_under_45', 0)
                })
            
            # Salva o último modelo em produção
            if fold == 4:
                joblib.dump(calibrated_model, self.models_dir / "zeta_oracle_cards.joblib")
            
            fold += 1

        logger.info("✅ Oráculo Zeta Treinado. Iniciando Execution Engine Financeiro...")

        # =================================================================
        # EXECUTION ENGINE (BACKTEST FINANCEIRO COM KELLY CRITERION)
        # =================================================================
        bankroll = self.INITIAL_BANKROLL
        bankroll_history = [bankroll]
        trades = []

        for pred in out_of_sample_preds:
            prob_o = pred['prob_over']
            prob_u = pred['prob_under']
            
            odd_o45 = pred['odd_cards_over_45']
            odd_u45 = pred['odd_cards_under_45']
            
            if pd.isna(odd_o45) or pd.isna(odd_u45) or odd_o45 <= 1.0 or odd_u45 <= 1.0:
                continue
                
            ev_over = (prob_o * odd_o45) - 1.0
            ev_under = (prob_u * odd_u45) - 1.0
            
            placed_bet = False
            profit = 0.0

            # Aposta no OVER 4.5 Cartões
            if ev_over >= self.MIN_EV_THRESHOLD and ev_over > ev_under:
                kelly_pct = (ev_over / (odd_o45 - 1.0)) * self.KELLY_FRACTION
                stake = min(bankroll * kelly_pct, bankroll * self.MAX_STAKE_PCT)
                
                profit = stake * (odd_o45 - 1.0) if pred['actual_result'] == 1 else -stake
                placed_bet = True

            # Aposta no UNDER 4.5 Cartões
            elif ev_under >= self.MIN_EV_THRESHOLD:
                kelly_pct = (ev_under / (odd_u45 - 1.0)) * self.KELLY_FRACTION
                stake = min(bankroll * kelly_pct, bankroll * self.MAX_STAKE_PCT)
                
                profit = stake * (odd_u45 - 1.0) if pred['actual_result'] == 0 else -stake
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

        logger.info("\n================= [ RELATÓRIO DO FUNDO QUANTITATIVO (ZETA) ] =================")
        logger.info(f"📊 VALIDAÇÃO TEMPORAL (Walk-Forward):")
        
        if total_bets == 0:
            logger.warning(f"   ⚠️ Nenhuma Odd de Cartões ('odd_cards_over_45') encontrada no histórico. ROI Omitido.")
            logger.warning(f"   (A matriz de predições funciona, mas para simular lucro inclua as odds no DB)")
        else:
            logger.info(f"   └ Banco Inicial: R$ {self.INITIAL_BANKROLL:.2f}")
            logger.info(f"   └ Operações Realizadas: {total_bets} (Filtro > {self.MIN_EV_THRESHOLD*100}% EV)")
            logger.info(f"   └ Win-Rate do Modelo: {win_rate:.1f}%")
            logger.info("------------------------------------------------------------------------------")
            logger.info(f"📈 MÉTRICAS DE RISCO & RETORNO:")
            logger.info(f"   └ Banco Final: R$ {bankroll:.2f}")
            logger.info(f"   └ Lucro Líquido (PnL): R$ {(bankroll - self.INITIAL_BANKROLL):.2f}")
            logger.info(f"   └ Max Drawdown: {max_dd * 100:.2f}% (Risco de Ruína)")
            logger.info(f"   └ Sharpe Ratio: {sharpe_ratio:.2f}")
            
            if roi_pct > 0:
                logger.info(f"   🚀 CRESCIMENTO DO FUNDO (ROI Acumulado): +{roi_pct:.2f}% (Máquina Institucional!)")
            else:
                logger.info(f"   🩸 DÉFICIT DO FUNDO (ROI Acumulado): {roi_pct:.2f}%")
        logger.info("==============================================================================\n")

if __name__ == "__main__":
    ZetaOracle().train_and_evaluate()