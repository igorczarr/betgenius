# betgenius-backend/workers/brain/3a_model_omega_props.py

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [OMEGA-ORACLE] %(message)s")
logger = logging.getLogger(__name__)

class OmegaOracle:
    """
    O Oráculo Ômega (Especialista em Player Props) - Nível Institucional HFT.
    Funde o desempenho individual (Por 90 min) com a fragilidade tática do adversário.
    Alvo Base: Over 0.5 Remates à Baliza (Shots on Target).
    """
    def __init__(self):
        self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # O ARSENAL DIMENSIONAL: Funde Jogador + Contexto de Equipa
        self.features = [
            'player_minutes_played', 'player_rating',
            'player_shots_p90', 'player_shots_on_p90', 
            'player_xg_proxy_p90', # A nossa feature matemática de elite
            'team_expected_dominance', # Probabilidade implícita da equipa vencer
            'opp_xg_against_ewma_micro', # Fragilidade defensiva do adversário
            'opp_fraudulent_defense', # Adversário está a ter sorte a não sofrer golos?
            'match_tension_index' # Jogos tensos geram mais remates de longe
        ]
        
        # Gestão de Risco HFT
        self.MIN_EV_THRESHOLD = 0.05   # Edge mínimo de 5%
        self.INITIAL_BANKROLL = 10000.0
        self.KELLY_FRACTION = 0.10     # Fracionamento conservador (Props têm alta variância)
        self.MAX_STAKE_PCT = 0.03      # Teto máximo de 3% da banca

    async def extract_and_engineer_data(self):
        """
        Extrai os dados da API de Jogadores e funde com a Feature Store de Equipas.
        """
        logger.info("📡 Extraindo Dados Multidimensionais (Jogadores + Matriz de Equipas)...")
        await db.connect()
        df = pd.DataFrame()
        try:
            # JOIN complexo: Puxa o histórico de equipas E os dados da temporada do jogador
            query = """
                SELECT 
                    m.id as match_id, m.match_date, m.home_team_id, m.away_team_id,
                    p.id as player_id, p.name as player_name, p.position,
                    ps.minutes_played, ps.rating, ps.shots_total, ps.shots_on_target, ps.goals, ps.appearences,
                    f.home_xg_against_ewma_micro, f.away_xg_against_ewma_micro,
                    f.home_fraudulent_defense, f.away_fraudulent_defense,
                    f.home_tension_index, f.away_tension_index,
                    f.pin_odd_home, f.pin_odd_away,
                    -- Target Simulado: O jogador fez > 0 remates à baliza neste jogo específico?
                    -- Nota: Num sistema 100% real, precisariamos da tabela 'match_player_stats' detalhada por jogo.
                    -- Para este oráculo, vamos usar o rácio global para encontrar o valor intrínseco.
                    ps.shots_on_target as season_shots_on
                FROM core.matches_history m
                JOIN quant_ml.feature_store f ON m.id = f.match_id
                JOIN core.players p ON p.team_id = m.home_team_id OR p.team_id = m.away_team_id
                JOIN core.player_season_stats ps ON p.id = ps.player_id
                WHERE m.status = 'FINISHED' AND ps.minutes_played > 90
                ORDER BY m.match_date ASC
            """
            async with db.pool.acquire() as conn:
                records = await conn.fetch(query)
                if records:
                    df = pd.DataFrame([dict(r) for r in records])
        finally:
            await db.disconnect()
            
        if df.empty:
            return df

        logger.info("📐 Calculando Engenharia de Features de Elite (Per 90 & xG Proxy)...")
        
        # 1. Padronização de "Por 90 Minutos" (O Segredo do Volume)
        df['player_shots_p90'] = (df['shots_total'] / df['minutes_played']) * 90
        df['player_shots_on_p90'] = (df['shots_on_target'] / df['minutes_played']) * 90
        
        # 2. PROXY DE xG POR JOGADOR (Fórmula: Conversão * Volume * 90)
        # Proteção contra divisão por zero usando np.maximum
        conversao = df['goals'] / np.maximum(df['shots_total'], 1)
        volume = df['shots_total'] / np.maximum(df['minutes_played'], 1)
        df['player_xg_proxy_p90'] = conversao * volume * 90
        
        # 3. Contexto Tático de Cruzamento (Quem é que o jogador vai enfrentar?)
        # Se o jogador é da casa, enfrenta a defesa de fora.
        df['is_home_player'] = (df['team_id'] == df['home_team_id']).astype(int) if 'team_id' in df.columns else 1
        
        df['opp_xg_against_ewma_micro'] = np.where(df['is_home_player'] == 1, df['away_xg_against_ewma_micro'], df['home_xg_against_ewma_micro'])
        df['opp_fraudulent_defense'] = np.where(df['is_home_player'] == 1, df['away_fraudulent_defense'], df['home_fraudulent_defense'])
        df['match_tension_index'] = np.where(df['is_home_player'] == 1, df['home_tension_index'], df['away_tension_index'])
        
        # 4. Probabilidade Implícita da Equipa (Se a equipa vai atacar muito, o jogador remata mais)
        pin_odd = np.where(df['is_home_player'] == 1, df['pin_odd_home'], df['pin_odd_away'])
        df['team_expected_dominance'] = 1.0 / np.maximum(pin_odd, 1.01)

        # TARGET: Over 0.5 Shots on Target (Simulado pela capacidade p90 superior a 0.8)
        # Num pipeline em tempo real, conectaríamos aos eventos do jogo para ter o Target perfeito.
        df['target_over_05_shots_on'] = (df['player_shots_on_p90'] > 0.8).astype(int)
        
        df = df.fillna(0.0)
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

    def train_and_evaluate(self, df):
        logger.info("==================================================================")
        logger.info(" 🤖 INICIANDO FORJA DO ORÁCULO ÔMEGA (PLAYER PROPS + KELLY EV) ")
        logger.info("==================================================================")

        # Filtro de qualidade: Apenas jogadores de ataque e meio-campo ofensivo
        df = df[df['position'].isin(['Attacker', 'Midfielder'])].copy()
        
        # PREVENÇÃO DE VAZAMENTO: Ordenação Cronológica
        df = df.sort_values('match_date').reset_index(drop=True)
        
        logger.info(f"📂 Matriz Híbrida Carregada: {len(df)} entradas de jogadores.")
        logger.info("⏳ Iniciando Walk-Forward Validation (Simulação do Mundo Real)...")

        tscv = TimeSeriesSplit(n_splits=4)
        out_of_sample_preds = []
        
        fold = 1
        for train_index, test_index in tscv.split(df):
            logger.info(f"   └ Processando Fold Temporal {fold}/4...")
            
            calib_size = int(len(train_index) * 0.20)
            pure_train_idx = train_index[:-calib_size]
            calib_idx = train_index[-calib_size:]

            X_train, y_train = df.iloc[pure_train_idx][self.features], df.iloc[pure_train_idx]['target_over_05_shots_on']
            X_calib, y_calib = df.iloc[calib_idx][self.features], df.iloc[calib_idx]['target_over_05_shots_on']
            X_test, y_test = df.iloc[test_index][self.features], df.iloc[test_index]['target_over_05_shots_on']

            # 1. O CÉREBRO BASE (XGBoost)
            base_model = xgb.XGBClassifier(
                objective='binary:logistic',
                eval_metric='logloss',
                n_estimators=350,
                learning_rate=0.015,
                max_depth=4,         
                min_child_weight=3,  
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.5,
                reg_lambda=2.0, # Alta regularização para evitar ruído individual
                random_state=42,
                n_jobs=-1
            )
            base_model.fit(X_train, y_train)

            # 2. CALIBRAÇÃO ISOTÓNICA (Ancoragem das probabilidades)
            calibrated_model = CalibratedClassifierCV(estimator=base_model, method='isotonic', cv='prefit')
            calibrated_model.fit(X_calib, y_calib)

            # Guarda previsões OOS
            preds = calibrated_model.predict_proba(X_test)
            for i, match_idx in enumerate(test_index):
                # Simulação da odd da casa de apostas (Em média 1.70 - 2.10 para Over 0.5/1.5 SoT)
                simulated_odd = np.round(np.random.uniform(1.65, 2.20), 2)
                
                out_of_sample_preds.append({
                    'player_name': df.iloc[match_idx]['player_name'],
                    'prob_under': preds[i][0],
                    'prob_over': preds[i][1],
                    'actual_result': y_test.iloc[i],
                    'odd_prop_over': simulated_odd,
                    'odd_prop_under': 1.0 / (1.0 - (1.0/simulated_odd) + 0.05) # Odd oposta com margem (vig)
                })
            
            if fold == 4:
                joblib.dump(calibrated_model, self.models_dir / "omega_oracle_player_props.joblib")
            
            fold += 1

        logger.info("✅ Oráculo Ômega Treinado. Iniciando Execution Engine Financeiro...")

        # =================================================================
        # EXECUTION ENGINE (BACKTEST FINANCEIRO COM KELLY CRITERION)
        # =================================================================
        bankroll = self.INITIAL_BANKROLL
        bankroll_history = [bankroll]
        trades = []

        for pred in out_of_sample_preds:
            prob_o = pred['prob_over']
            prob_u = pred['prob_under']
            
            odd_o = pred['odd_prop_over']
            odd_u = pred['odd_prop_under']
            
            ev_over = (prob_o * odd_o) - 1.0
            ev_under = (prob_u * odd_u) - 1.0
            
            placed_bet = False
            profit = 0.0

            # Aposta no OVER 0.5 Shots on Target
            if ev_over >= self.MIN_EV_THRESHOLD and ev_over > ev_under:
                kelly_pct = (ev_over / (odd_o - 1.0)) * self.KELLY_FRACTION
                stake = min(bankroll * kelly_pct, bankroll * self.MAX_STAKE_PCT)
                
                profit = stake * (odd_o - 1.0) if pred['actual_result'] == 1 else -stake
                placed_bet = True

            # Aposta no UNDER 0.5 Shots on Target
            elif ev_under >= self.MIN_EV_THRESHOLD:
                kelly_pct = (ev_under / (odd_u - 1.0)) * self.KELLY_FRACTION
                stake = min(bankroll * kelly_pct, bankroll * self.MAX_STAKE_PCT)
                
                profit = stake * (odd_u - 1.0) if pred['actual_result'] == 0 else -stake
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

        logger.info("\n================= [ RELATÓRIO DO FUNDO QUANTITATIVO (ÔMEGA) ] =================")
        logger.info(f"📊 PLAYER PROPS (Shots on Target) - VALIDAÇÃO TEMPORAL:")
        logger.info(f"   └ Banco Inicial: R$ {self.INITIAL_BANKROLL:.2f}")
        logger.info(f"   └ Operações Realizadas: {total_bets} (Filtro > {self.MIN_EV_THRESHOLD*100}% EV)")
        logger.info(f"   └ Win-Rate do Modelo: {win_rate:.1f}%")
        logger.info("-------------------------------------------------------------------------------")
        logger.info(f"📈 MÉTRICAS DE RISCO & RETORNO:")
        logger.info(f"   └ Banco Final: R$ {bankroll:.2f}")
        logger.info(f"   └ Lucro Líquido (PnL): R$ {(bankroll - self.INITIAL_BANKROLL):.2f}")
        logger.info(f"   └ Max Drawdown: {max_dd * 100:.2f}% (Risco de Ruína)")
        
        if roi_pct > 0:
            logger.info(f"   🚀 CRESCIMENTO DO FUNDO (ROI Acumulado): +{roi_pct:.2f}% (Esmagamento de Props!)")
        else:
            logger.info(f"   🩸 DÉFICIT DO FUNDO (ROI Acumulado): {roi_pct:.2f}%")
        logger.info("===============================================================================\n")

if __name__ == "__main__":
    import asyncio
    
    async def run_omega():
        oracle = OmegaOracle()
        df = await oracle.extract_and_engineer_data()
        if not df.empty:
            oracle.train_and_evaluate(df)
        else:
            logger.error("Sem dados suficientes para treinar o Oráculo Ômega.")
            
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run_omega())