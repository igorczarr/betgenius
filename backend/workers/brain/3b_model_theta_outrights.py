# betgenius-backend/workers/brain/3b_model_theta_outrights.py

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
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import GroupKFold
import joblib
from pathlib import Path
from dotenv import load_dotenv

pd.set_option('future.no_silent_downcasting', True)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [THETA-OUTRIGHTS] %(message)s")
logger = logging.getLogger(__name__)

class ThetaOracle:
    """
    O Oráculo Theta (Especialista em Mercados de Longo Prazo / Futures).
    Nível Institucional: Avalia a corrida pelo título (Ligas e Copas) usando 
    snapshots de meio de temporada cruzados com o xG Macro e o ELO.
    """
    def __init__(self):
        self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        # O ARSENAL MACRO: O que define um campeão?
        self.features = [
            'current_elo',             # Força global da equipa
            'league_tier',             # Dificuldade do campeonato
            'wage_percentile',         # Poder financeiro / Profundidade de plantel
            'season_progress_pct',     # % da temporada já concluída (ex: 0.70 = 70% jogado)
            'current_position',        # Posição na tabela no momento da análise
            'pts_behind_leader',       # Distância pontual para o 1º classificado
            'win_rate_current',        # Consistência
            'xg_macro_diff_p90',       # Qualidade subjacente (xG Criado - xG Sofrido por jogo)
            'fraudulent_points_p90'    # Pontos ganhos vs Pontos Merecidos (Sorte de campeão ou fraude em colapso?)
        ]
        
        # Gestão de Risco para Mercados Futuros (Capital Preso)
        self.MIN_EV_THRESHOLD = 0.12   # Exigimos 12% de Edge. O dinheiro fica preso muito tempo.
        self.INITIAL_BANKROLL = 10000.0
        self.KELLY_FRACTION = 0.10     # Conservador para mercados de longo prazo
        self.MAX_STAKE_PCT = 0.05      # Nunca imobilizar mais de 5% num único bilhete

    async def extract_and_build_snapshots(self):
        """
        Extrai o histórico da Feature Store e reconstrói Snapshots das equipas
        a cada 10 rodadas ou fases de copa para treinar o modelo.
        """
        logger.info("📡 Extraindo o DNA dos Campeões do Banco de Dados...")
        await db.connect()
        df_snaps = pd.DataFrame()
        
        try:
            # Esta query constrói o estado de todas as equipas no final de cada temporada
            # e cruza com quem realmente levantou a taça (target).
            query = """
                WITH team_season_matches AS (
                    SELECT 
                        m.sport_key, m.season, m.match_date, 
                        m.home_team_id AS team_id,
                        f.home_elo_before AS current_elo,
                        f.home_wage_pct AS wage_percentile,
                        hp.league_tier,
                        f.pos_tabela_home AS current_position,
                        f.home_pts_before AS current_pts,
                        f.home_xg_for_ewma_macro - f.home_xg_against_ewma_macro AS xg_macro_diff_p90,
                        (f.home_pts_before / GREATEST(f.pos_tabela_home, 1)) - (f.home_xg_for_ewma_macro * 3) AS fraudulent_points_p90,
                        ROW_NUMBER() OVER (PARTITION BY m.sport_key, m.season, m.home_team_id ORDER BY m.match_date DESC) as rn_desc,
                        COUNT(*) OVER (PARTITION BY m.sport_key, m.season, m.home_team_id) as total_games_played
                    FROM core.matches_history m
                    JOIN quant_ml.feature_store f ON m.id = f.match_id
                    LEFT JOIN core.team_pedigree hp ON m.home_team_id = hp.team_id
                    WHERE m.status = 'FINISHED'
                    
                    UNION ALL
                    
                    SELECT 
                        m.sport_key, m.season, m.match_date, 
                        m.away_team_id AS team_id,
                        f.away_elo_before AS current_elo,
                        f.away_wage_pct AS wage_percentile,
                        ap.league_tier,
                        f.pos_tabela_away AS current_position,
                        f.away_pts_before AS current_pts,
                        f.away_xg_for_ewma_macro - f.away_xg_against_ewma_macro AS xg_macro_diff_p90,
                        (f.away_pts_before / GREATEST(f.pos_tabela_away, 1)) - (f.away_xg_for_ewma_macro * 3) AS fraudulent_points_p90,
                        ROW_NUMBER() OVER (PARTITION BY m.sport_key, m.season, m.away_team_id ORDER BY m.match_date DESC) as rn_desc,
                        COUNT(*) OVER (PARTITION BY m.sport_key, m.season, m.away_team_id) as total_games_played
                    FROM core.matches_history m
                    JOIN quant_ml.feature_store f ON m.id = f.match_id
                    LEFT JOIN core.team_pedigree ap ON m.away_team_id = ap.team_id
                    WHERE m.status = 'FINISHED'
                ),
                league_winners AS (
                    -- A equipa que terminou em 1º na última rodada é considerada a campeã
                    SELECT sport_key, season, team_id
                    FROM team_season_matches
                    WHERE rn_desc = 1 AND current_position = 1
                ),
                max_points_per_season AS (
                    SELECT sport_key, season, match_date, MAX(current_pts) as leader_pts
                    FROM team_season_matches
                    GROUP BY sport_key, season, match_date
                )
                
                SELECT 
                    ts.sport_key, ts.season, ts.match_date, ts.team_id,
                    ts.current_elo, ts.league_tier, ts.wage_percentile,
                    ts.current_position, ts.current_pts, ts.xg_macro_diff_p90, ts.fraudulent_points_p90,
                    -- Engenharia de Progresso e Distância
                    (ts.total_games_played - ts.rn_desc)::float / GREATEST(ts.total_games_played, 1) AS season_progress_pct,
                    (ts.total_games_played - ts.rn_desc)::float / GREATEST(ts.total_games_played, 1) AS win_rate_current,
                    COALESCE(mp.leader_pts, 0) - ts.current_pts AS pts_behind_leader,
                    -- Target
                    CASE WHEN lw.team_id IS NOT NULL THEN 1 ELSE 0 END AS is_champion
                FROM team_season_matches ts
                LEFT JOIN league_winners lw ON ts.sport_key = lw.sport_key AND ts.season = lw.season AND ts.team_id = lw.team_id
                LEFT JOIN max_points_per_season mp ON ts.sport_key = mp.sport_key AND ts.season = mp.season AND ts.match_date = mp.match_date
                -- Vamos pegar snapshots a cada 5 rodadas para não inundar o modelo com dados redundantes
                WHERE ts.rn_desc % 5 = 0 OR ts.rn_desc = 1
                ORDER BY ts.sport_key, ts.season, ts.match_date ASC;
            """
            
            async with db.pool.acquire() as conn:
                records = await conn.fetch(query)
                if records:
                    df_snaps = pd.DataFrame([dict(r) for r in records])
        except Exception as e:
            logger.error(f"Erro ao forjar Snapshots de Temporada: {e}")
        finally:
            await db.disconnect()
            
        if df_snaps.empty:
            return df_snaps
            
        df_snaps = df_snaps.fillna(0.0)
        return df_snaps

    def train_and_evaluate(self, df):
        logger.info("==================================================================")
        logger.info(" 🏆 INICIANDO FORJA DO ORÁCULO THETA (OUTRIGHTS/CAMPEÕES + EV) ")
        logger.info("==================================================================")

        # Filtro: Ignorar as equipas no fundo da tabela que matematicamente já não têm chance
        df = df[df['pts_behind_leader'] <= 25].copy()
        
        logger.info(f"📂 Snapshots Temporais Carregados: {len(df)} registos de corridas pelo título.")

        # Validação Cruzada por Temporada (GroupKFold garante que não vazamos dados da mesma época)
        # O modelo treina em ligas/épocas inteiras e testa noutras épocas isoladas.
        df['group_id'] = df['sport_key'] + "_" + df['season']
        groups = df['group_id'].values
        
        X = df[self.features]
        y = df['is_champion']
        
        gkf = GroupKFold(n_splits=5)
        
        out_of_sample_preds = []
        fold = 1
        
        for train_idx, test_idx in gkf.split(X, y, groups=groups):
            logger.info(f"   └ Validando Épocas Ocultas - Fold {fold}/5...")
            
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
            
            # Calibração: Usamos os últimos 15% do treino para ancorar as odds
            calib_size = int(len(X_train) * 0.15)
            X_pure_train, y_pure_train = X_train[:-calib_size], y_train[:-calib_size]
            X_calib, y_calib = X_train[-calib_size:], y_train[-calib_size:]

            # 1. CÉREBRO BASE (XGBoost) - Altamente conservador para capturar tendências longas
            base_model = xgb.XGBClassifier(
                objective='binary:logistic',
                eval_metric='auc', # AUC é melhor para classes raras (só há 1 campeão por liga)
                n_estimators=300,
                learning_rate=0.01,
                max_depth=3,         
                min_child_weight=10, # Exige provas fortes para declarar alguém campeão
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=1.0,       # Punição pesada contra overfitting
                reg_lambda=3.0,
                scale_pos_weight=10, # Desbalanceamento: Existem muito mais perdedores do que vencedores
                random_state=42,
                n_jobs=-1
            )
            base_model.fit(X_pure_train, y_pure_train)

            # 2. CALIBRAÇÃO ISOTÓNICA
            # As previsões cruas do XGBoost em classes desbalanceadas são más. O Isotonic corrige isso.
            calibrated_model = CalibratedClassifierCV(estimator=base_model, method='isotonic', cv='prefit')
            calibrated_model.fit(X_calib, y_calib)

            preds_proba = calibrated_model.predict_proba(X_test)
            
            for i, idx in enumerate(test_idx):
                # Simulação da odd do mercado Outright (Na vida real, puxaríamos da API/Scraper)
                # Para equipas perto do líder, as odds rondam os 2.0 a 6.0
                simulated_odd = np.round(np.random.uniform(2.0, 8.0), 2) if df.iloc[idx]['pts_behind_leader'] < 6 else np.round(np.random.uniform(15.0, 50.0), 2)
                
                out_of_sample_preds.append({
                    'league_season': df.iloc[idx]['group_id'],
                    'team_id': df.iloc[idx]['team_id'],
                    'progress': df.iloc[idx]['season_progress_pct'],
                    'prob_champion': preds_proba[i][1],
                    'actual_champion': y_test.iloc[i],
                    'odd_outright': simulated_odd
                })

            if fold == 5:
                joblib.dump(calibrated_model, self.models_dir / "theta_oracle_outrights.joblib")
            fold += 1

        logger.info("✅ Oráculo Theta Treinado. Iniciando Auditoria de Portefólio a Longo Prazo...")

        # =================================================================
        # EXECUTION ENGINE (MERCADOS DE FUTUROS)
        # =================================================================
        bankroll = self.INITIAL_BANKROLL
        trades = []
        
        # Num mercado de futuros, nós investimos no início/meio da época e recebemos no fim.
        # Vamos simular o PnL assumindo que a banca roda livremente.
        for pred in out_of_sample_preds:
            # Só apostamos se a temporada tiver pelo menos 30% jogado (para haver dados reais)
            # e menos de 85% jogado (depois disso as odds são destruídas pelo mercado)
            if pred['progress'] < 0.30 or pred['progress'] > 0.85:
                continue
                
            prob = pred['prob_champion']
            odd = pred['odd_outright']
            
            ev = (prob * odd) - 1.0
            
            if ev >= self.MIN_EV_THRESHOLD:
                kelly_pct = (ev / (odd - 1.0)) * self.KELLY_FRACTION
                stake = min(bankroll * kelly_pct, bankroll * self.MAX_STAKE_PCT)
                
                if pred['actual_champion'] == 1:
                    profit = stake * (odd - 1.0)
                else:
                    profit = -stake
                
                bankroll += profit
                trades.append(profit)

        total_bets = len(trades)
        winning_bets = sum(1 for t in trades if t > 0)
        win_rate = (winning_bets / total_bets * 100) if total_bets > 0 else 0.0
        roi_pct = ((bankroll - self.INITIAL_BANKROLL) / self.INITIAL_BANKROLL) * 100

        # Sharpe Ratio (Avaliação do risco face à flutuação longa)
        trades_array = np.array(trades)
        mean_trade = np.mean(trades_array) if total_bets > 0 else 0
        std_trade = np.std(trades_array) if total_bets > 0 else 1
        sharpe_ratio = (mean_trade / std_trade) * np.sqrt(total_bets) if std_trade > 0 else 0

        logger.info("\n================= [ RELATÓRIO DO FUNDO QUANTITATIVO (THETA) ] =================")
        logger.info(f"📊 VALIDAÇÃO DE PORTFÓLIO LONGO PRAZO (Outrights/Futures):")
        logger.info(f"   └ Banco Inicial: R$ {self.INITIAL_BANKROLL:.2f}")
        logger.info(f"   └ Operações Abertas: {total_bets} (Filtro rigoroso > {self.MIN_EV_THRESHOLD*100}% EV)")
        logger.info(f"   └ Win-Rate (Acerto do Campeão): {win_rate:.1f}%")
        logger.info("-------------------------------------------------------------------------------")
        logger.info(f"📈 MÉTRICAS DE RISCO & RETORNO (Custo de Oportunidade Ponderado):")
        logger.info(f"   └ Banco Final: R$ {bankroll:.2f}")
        logger.info(f"   └ Lucro Líquido (PnL): R$ {(bankroll - self.INITIAL_BANKROLL):.2f}")
        logger.info(f"   └ Sharpe Ratio: {sharpe_ratio:.2f}")
        
        if roi_pct > 0:
            logger.info(f"   🚀 CRESCIMENTO DO FUNDO (ROI Acumulado): +{roi_pct:.2f}% (Títulos Garantidos!)")
        else:
            logger.info(f"   🩸 DÉFICIT DO FUNDO (ROI Acumulado): {roi_pct:.2f}% (Variação imprevisível da liga)")
        logger.info("===============================================================================\n")

if __name__ == "__main__":
    import asyncio
    
    async def run_theta():
        oracle = ThetaOracle()
        df = await oracle.extract_and_build_snapshots()
        if not df.empty:
            oracle.train_and_evaluate(df)
        else:
            logger.error("Sem dados históricos suficientes para mapear as corridas pelo título.")
            
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run_theta())