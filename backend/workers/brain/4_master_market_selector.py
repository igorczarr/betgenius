# betgenius-backend/brain/4_master_market_selector.py

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
import joblib
from scipy.stats import poisson
from pathlib import Path
from dotenv import load_dotenv

pd.set_option('future.no_silent_downcasting', True)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

class MasterMarketSelector:
    def __init__(self):
        self.data_vault_path = Path(__file__).parent / "data_vault" / "purified_tensors.parquet"
        self.models_dir = Path(__file__).parent / "models"
        self.model_h_path = self.models_dir / "poisson_home.joblib"
        self.model_a_path = self.models_dir / "poisson_away.joblib"
        self.RHO = -0.13 

        self.features = [
            'delta_elo', 'delta_wage_pct', 'delta_pontos', 'delta_posicao', 
            'delta_xg_micro', 'delta_xg_macro', 'delta_aggression',
            'home_rest_days', 'away_rest_days', 'home_aggression_ewma', 'away_aggression_ewma', 
            'home_win_streak', 'home_winless_streak', 'away_win_streak', 'away_winless_streak',
            'home_tension_index', 'away_tension_index', 
            'home_fraudulent_defense', 'home_fraudulent_attack',
            'away_fraudulent_defense', 'away_fraudulent_attack'
        ]

    def _load_data_and_models(self):
        if not self.data_vault_path.exists() or not self.model_h_path.exists():
            logger.error("❌ Cofre ou Modelos não encontrados!")
            sys.exit(1)
        df = pd.read_parquet(self.data_vault_path)
        model_h = joblib.load(self.model_h_path)
        model_a = joblib.load(self.model_a_path)
        return df, model_h, model_a

    def apply_dixon_coles(self, i, j, lambda_h, lambda_a):
        if i == 0 and j == 0: return 1.0 - (lambda_h * lambda_a * self.RHO)
        elif i == 0 and j == 1: return 1.0 + (lambda_h * self.RHO)
        elif i == 1 and j == 0: return 1.0 + (lambda_a * self.RHO)
        elif i == 1 and j == 1: return 1.0 - self.RHO
        else: return 1.0

    def generate_all_probabilities(self, lambda_h, lambda_a):
        n = len(lambda_h)
        prob_h, prob_d, prob_a = np.zeros(n), np.zeros(n), np.zeros(n)
        prob_o25, prob_u25 = np.zeros(n), np.zeros(n)
        prob_btts_y, prob_btts_n = np.zeros(n), np.zeros(n)

        for i in range(8):
            for j in range(8):
                p_raw = poisson.pmf(i, lambda_h) * poisson.pmf(j, lambda_a)
                p_adj = np.clip(p_raw * self.apply_dixon_coles(i, j, lambda_h, lambda_a), 0, 1)

                if i > j: prob_h += p_adj
                elif i < j: prob_a += p_adj
                else: prob_d += p_adj

                if (i + j) > 2.5: prob_o25 += p_adj
                else: prob_u25 += p_adj

                if i > 0 and j > 0: prob_btts_y += p_adj
                else: prob_btts_n += p_adj

        t_1x2 = prob_h + prob_d + prob_a
        prob_h, prob_d, prob_a = prob_h/t_1x2, prob_d/t_1x2, prob_a/t_1x2
        
        t_ou = prob_o25 + prob_u25
        prob_o25, prob_u25 = prob_o25/t_ou, prob_u25/t_ou
        
        t_btts = prob_btts_y + prob_btts_n
        prob_btts_y, prob_btts_n = prob_btts_y/t_btts, prob_btts_n/t_btts

        return {
            'HOME': prob_h, 'DRAW': prob_d, 'AWAY': prob_a,
            'O25': prob_o25, 'U25': prob_u25,
            'BTTS_Y': prob_btts_y, 'BTTS_N': prob_btts_n
        }

    def remove_margin_2way(self, odd_1, odd_2):
        margin = (1.0/odd_1) + (1.0/odd_2)
        true_prob_1 = (1.0/odd_1)/margin
        true_prob_2 = (1.0/odd_2)/margin
        return 1.0/true_prob_1, 1.0/true_prob_2

    def remove_margin_3way(self, odd_1, odd_x, odd_2):
        margin = (1.0/odd_1) + (1.0/odd_x) + (1.0/odd_2)
        true_prob_1 = (1.0/odd_1)/margin
        true_prob_x = (1.0/odd_x)/margin
        true_prob_2 = (1.0/odd_2)/margin
        return 1.0/true_prob_1, 1.0/true_prob_x, 1.0/true_prob_2

    def _safe_get_odds(self, df: pd.DataFrame, col_name: str) -> np.ndarray:
        # A CURA: Se a odd não existe, retorna 0.0 para falhar no if odd > 1.0
        if col_name in df.columns:
            return pd.to_numeric(df[col_name], errors='coerce').fillna(0.0).values
        else:
            return np.zeros(len(df))

    def run_master_selector(self):
        logger.info("🧠 Inicializando Master Market Selector (Pure Alpha Test)...")
        df, model_h, model_a = self._load_data_and_models()

        split_idx = int(len(df) * 0.90)
        test_df = df.iloc[split_idx:].copy()
        X_test = test_df[self.features]
        
        logger.info(f"🔮 Analisando Matriz Multi-Mercado para {len(X_test)} jogos...")

        lambda_h = np.clip(model_h.predict(X_test), 0.1, 4.0)
        lambda_a = np.clip(model_a.predict(X_test), 0.1, 4.0)

        probs = self.generate_all_probabilities(lambda_h, lambda_a)

        o_h = self._safe_get_odds(test_df, 'closing_odd_home')
        o_d = self._safe_get_odds(test_df, 'closing_odd_draw')
        o_a = self._safe_get_odds(test_df, 'closing_odd_away')
        o_o25 = self._safe_get_odds(test_df, 'odd_over_25')
        o_u25 = self._safe_get_odds(test_df, 'odd_under_25')
        o_bttsy = self._safe_get_odds(test_df, 'odd_btts_yes')
        o_bttsn = self._safe_get_odds(test_df, 'odd_btts_no')

        real_goals_h = test_df['home_goals'].values
        real_goals_a = test_df['away_goals'].values
        match_ids = test_df['match_id'].values
        
        real_1x2 = np.where(real_goals_h > real_goals_a, 'HOME', np.where(real_goals_h < real_goals_a, 'AWAY', 'DRAW'))
        real_ou = np.where((real_goals_h + real_goals_a) > 2.5, 'O25', 'U25')
        real_btts = np.where((real_goals_h > 0) & (real_goals_a > 0), 'BTTS_Y', 'BTTS_N')

        profit = 0.0
        total_bets = 0
        market_stats = {'1X2': 0, 'O/U': 0, 'BTTS': 0}

        # Filtros de Operação
        MIN_EDGE = 0.02 
        MAX_EDGE = 0.35
        MIN_PROB = 0.35

        logger.info("⚔️ Simulando Batalha Multi-Mercado (EV Contra a True Odd Exchange)...\n")

        for i in range(len(test_df)):
            market_options = []
            
            # Formatação base para o log da Matrix (Se quisermos debugar)
            log_str = f"MatchID {match_ids[i]} | Lambdas [{lambda_h[i]:.2f} x {lambda_a[i]:.2f}] | "

            # 1X2
            if o_h[i] > 1.0 and o_d[i] > 1.0 and o_a[i] > 1.0:
                t_h, t_d, t_a = self.remove_margin_3way(o_h[i], o_d[i], o_a[i])
                
                ev_h = (probs['HOME'][i] * t_h) - 1.0
                if MIN_EDGE < ev_h < MAX_EDGE and probs['HOME'][i] >= MIN_PROB:
                    market_options.append({'market': '1X2', 'sel': 'HOME', 'ev': ev_h, 'odd': t_h, 'won': real_1x2[i] == 'HOME'})
                    
                ev_a = (probs['AWAY'][i] * t_a) - 1.0
                if MIN_EDGE < ev_a < MAX_EDGE and probs['AWAY'][i] >= MIN_PROB:
                    market_options.append({'market': '1X2', 'sel': 'AWAY', 'ev': ev_a, 'odd': t_a, 'won': real_1x2[i] == 'AWAY'})

            # OVER/UNDER 2.5
            if o_o25[i] > 1.0 and o_u25[i] > 1.0:
                t_o25, t_u25 = self.remove_margin_2way(o_o25[i], o_u25[i])
                
                ev_o25 = (probs['O25'][i] * t_o25) - 1.0
                if MIN_EDGE < ev_o25 < MAX_EDGE and probs['O25'][i] >= MIN_PROB:
                    market_options.append({'market': 'O/U', 'sel': 'O25', 'ev': ev_o25, 'odd': t_o25, 'won': real_ou[i] == 'O25'})
                    
                ev_u25 = (probs['U25'][i] * t_u25) - 1.0
                if MIN_EDGE < ev_u25 < MAX_EDGE and probs['U25'][i] >= MIN_PROB:
                    market_options.append({'market': 'O/U', 'sel': 'U25', 'ev': ev_u25, 'odd': t_u25, 'won': real_ou[i] == 'U25'})

            # BTTS
            if o_bttsy[i] > 1.0 and o_bttsn[i] > 1.0:
                t_by, t_bn = self.remove_margin_2way(o_bttsy[i], o_bttsn[i])
                
                ev_by = (probs['BTTS_Y'][i] * t_by) - 1.0
                if MIN_EDGE < ev_by < MAX_EDGE and probs['BTTS_Y'][i] >= MIN_PROB:
                    market_options.append({'market': 'BTTS', 'sel': 'BTTS_Y', 'ev': ev_by, 'odd': t_by, 'won': real_btts[i] == 'BTTS_Y'})
                    
                ev_bn = (probs['BTTS_N'][i] * t_bn) - 1.0
                if MIN_EDGE < ev_bn < MAX_EDGE and probs['BTTS_N'][i] >= MIN_PROB:
                    market_options.append({'market': 'BTTS', 'sel': 'BTTS_N', 'ev': ev_bn, 'odd': t_bn, 'won': real_btts[i] == 'BTTS_N'})

            # O MESTRE ESCOLHE A MELHOR ARMA PARA ESTE JOGO
            if market_options:
                best_bet = max(market_options, key=lambda x: x['ev'])
                total_bets += 1
                market_stats[best_bet['market']] += 1
                
                # Exibe o Raio-X do Jogo (A Matrix)
                prob_str = f"H:{probs['HOME'][i]:.1%} D:{probs['DRAW'][i]:.1%} A:{probs['AWAY'][i]:.1%} | O25:{probs['O25'][i]:.1%} BTTS:{probs['BTTS_Y'][i]:.1%}"
                res_str = "✅ WON " if best_bet['won'] else "❌ LOST"
                logger.info(f"{log_str}{prob_str} -> BET: [{best_bet['sel']}] EV: +{best_bet['ev']*100:.1f}% @ {best_bet['odd']:.2f} -> {res_str}")

                if best_bet['won']:
                    profit += (best_bet['odd'] - 1.0)
                else:
                    profit -= 1.0

        roi = (profit / total_bets) * 100 if total_bets > 0 else 0.0

        logger.info("\n================= [ RELATÓRIO DO MASTER SELECTOR ] =================")
        logger.info(f"🎯 Total de Jogos Analisados no Teste Cego: {len(test_df)}")
        logger.info(f"🔫 Entradas Filtradas Sniper: {total_bets} Apostas")
        logger.info(f"   -> 1X2: {market_stats['1X2']} | O/U: {market_stats['O/U']} | BTTS: {market_stats['BTTS']}")
        logger.info(f"💵 Lucro/Prejuízo Líquido (Base True Odds): {profit:.2f} Unidades")
        
        if roi > 0: logger.info(f"🟢 RETORNO PREDITIVO (ROI): +{roi:.2f}%")
        else: logger.info(f"🔴 RETORNO PREDITIVO (ROI): {roi:.2f}%")
        logger.info("====================================================================\n")

if __name__ == "__main__":
    MasterMarketSelector().run_master_selector()