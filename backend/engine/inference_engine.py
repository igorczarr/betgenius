# betgenius-backend/engine/inference_engine.py

import sys
import os
import io

if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import asyncio
import logging
import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

pd.set_option('future.no_silent_downcasting', True)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db
import redis.asyncio as redis
from core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [INFERENCE-ENGINE] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

class MasterInferenceEngine:
    """
    O Diretor de Sindicato (Gestor de Oráculos).
    Carrega toda a frota de modelos XGBoost calibrados, extrai as features do presente,
    cruza com as odds ao vivo e dispara sinais de apostas +EV via Redis para o Dashboard.
    """
    def __init__(self):
        self.models_dir = BASE_DIR / "workers" / "brain" / "models"
        
        # Caminhos dos nossos modelos Institucionais
        self.models_paths = {
            "alpha_1x2": self.models_dir / "alpha_oracle_1x2.joblib",
            "beta_ou25": self.models_dir / "beta_oracle_ou25.joblib",
            "gamma_btts": self.models_dir / "gamma_oracle_btts.joblib",
            "delta_ht_1x2": self.models_dir / "delta_oracle_ht_1x2.joblib",
            "epsilon_corners": self.models_dir / "epsilon_oracle_corners.joblib",
            "sigma_shots": self.models_dir / "sigma_oracle_shots.joblib",
            "zeta_cards": self.models_dir / "zeta_oracle_cards.joblib"
        }
        self.models = {}
        self.redis_client = None

        # Parâmetros Estritos de Risco S-Tier
        self.MIN_EV_THRESHOLD = 0.05    # Edge mínimo para entrar na aposta (5%)
        self.MAX_EV_THRESHOLD = 0.40    # Acima de 40% geralmente é erro de linha da casa (não real)
        self.MIN_PROB_WIN = 0.35        # Evita atirar em zebras cegas
        self.KELLY_FRACTION = 0.25      # Quarter-Kelly para proteger o bankroll
        
        # A Assinatura de DNA idêntica aos treinamentos
        self.features = [
            'delta_elo', 'delta_pontos', 
            'delta_xg_micro', 'delta_shots',
            'is_missing_tactics', 
            'smart_money_home', 'smart_money_away', 
            'open_odd_h', 'open_odd_a' 
        ]

    async def connect(self):
        self.redis_client = await redis.from_url(settings.REDIS_URL)
        await db.connect()

    def _load_brains(self):
        """Carrega todos os modelos disponíveis na pasta."""
        logger.info("🧠 Acordando a frota de Oráculos XGBoost...")
        for name, path in self.models_paths.items():
            if path.exists():
                self.models[name] = joblib.load(path)
                logger.info(f"   [+] Oráculo {name} online e calibrado.")
            else:
                logger.warning(f"   [-] Oráculo {name} não encontrado. Mercado ignorado.")

    def _remove_overround_1x2(self, odd_h: float, odd_d: float, odd_a: float):
        """Remove a margem de lucro (Vig) da casa de apostas num mercado de 3 vias."""
        if odd_h <= 1.0 or odd_d <= 1.0 or odd_a <= 1.0: return 0.0, 0.0, 0.0
        margin = (1.0/odd_h) + (1.0/odd_d) + (1.0/odd_a)
        return (1.0/odd_h)/margin, (1.0/odd_d)/margin, (1.0/odd_a)/margin

    def _remove_overround_binary(self, odd_1: float, odd_2: float):
         """Remove a margem de lucro num mercado de 2 vias (Ex: Over/Under)."""
         if odd_1 <= 1.0 or odd_2 <= 1.0: return 0.0, 0.0
         margin = (1.0/odd_1) + (1.0/odd_2)
         return (1.0/odd_1)/margin, (1.0/odd_2)/margin

    def _calculate_kelly_stake(self, prob: float, odd: float) -> float:
        """Money Management Matemático Absoluto."""
        if odd <= 1.0: return 0.0
        b = odd - 1.0
        q = 1.0 - prob
        kelly_fraction = ((b * prob) - q) / b
        return max(0.0, kelly_fraction * self.KELLY_FRACTION)

    async def publish_signal(self, match_info, market_name, ev, prob, odd):
        """Prepara e envia o sinal +EV para o Redis (Dashboard)."""
        stake_pct = self._calculate_kelly_stake(prob, odd)
        
        payload = {
            "hora": datetime.now().strftime("%H:%M:%S"),
            "jogo": match_info['game'],
            "mercado": market_name,
            "trueOdd": round(1.0/prob, 2) if prob > 0 else 0,
            "softOdd": odd,
            "bookie": "Bet365", # Adaptar caso a odd venha de outra casa
            "ev": round(ev * 100, 2),
            "kelly": round(stake_pct * 100, 2),
            "sport": match_info['sport']
        }
        await self.redis_client.publish("betgenius:stream:opportunities", json.dumps(payload))
        print(f"🟢 [SINAL] -> {market_name} | EV: +{ev*100:.1f}% | Stake: {stake_pct*100:.2f}% | {match_info['game']}")

    async def scan_and_predict(self):
        print("\n" + "="*90)
        print(" 🌐 INICIANDO RADAR PANÓPTICO: O Motor Institucional de Sinais")
        print("="*90 + "\n")

        self._load_brains()
        if not self.models:
            logger.error("Nenhum modelo foi treinado. Execute os scripts na pasta 'brain/'.")
            return

        await self.connect()

        try:
            async with db.pool.acquire() as conn:
                # S-TIER: Precisamos buscar as odds ao vivo e as de abertura para montar as features
                query = """
                    SELECT 
                        f.*, 
                        th.canonical_name as home_team, ta.canonical_name as away_team, m.sport_key,
                        m.pin_odd_home as open_odd_h, m.pin_odd_away as open_odd_a,
                        m.pin_closing_home as close_odd_h, m.pin_closing_away as close_odd_a,
                        o_home.current_odd as live_odd_home, 
                        o_draw.current_odd as live_odd_draw, 
                        o_away.current_odd as live_odd_away
                    FROM quant_ml.feature_store f
                    JOIN core.matches_history m ON f.match_id = m.id
                    JOIN core.teams th ON m.home_team_id = th.id
                    JOIN core.teams ta ON m.away_team_id = ta.id
                    LEFT JOIN core.market_odds o_home ON m.id = o_home.match_id AND o_home.bookmaker = 'bet365' AND o_home.nome_mercado IN ('1', 'home')
                    LEFT JOIN core.market_odds o_draw ON m.id = o_draw.match_id AND o_draw.bookmaker = 'bet365' AND o_draw.nome_mercado IN ('x', 'draw')
                    LEFT JOIN core.market_odds o_away ON m.id = o_away.match_id AND o_away.bookmaker = 'bet365' AND o_away.nome_mercado IN ('2', 'away')
                    WHERE m.status = 'SCHEDULED' 
                    AND m.match_date >= CURRENT_DATE 
                    AND m.match_date <= CURRENT_DATE + INTERVAL '2 days'
                """
                records = await conn.fetch(query)

                if not records:
                    logger.warning("⚠️ Nenhum jogo futuro (com features) agendado para o Radar.")
                    return

                df = pd.DataFrame([dict(r) for r in records])
                logger.info(f"🔎 Analisando o mercado futuro: {len(df)} eventos encontrados.\n")

                # Reconstruindo a Feature Store exata usada no treino
                df['is_missing_tactics'] = (df['h_xg_for_micro'].isna() | (df['h_xg_for_micro'] <= 0.05)).astype(int)
                df['delta_elo'] = df['delta_elo'].fillna(0.0)
                df['delta_pontos'] = df['home_pts_before'] - df['away_pts_before']
                df['delta_xg_micro'] = np.where(df['is_missing_tactics'] == 1, 0.0, df['h_xg_for_micro'] - df['a_xg_for_micro'])
                df['delta_shots'] = np.where(df['is_missing_tactics'] == 1, 0.0, df['h_shots_for'] - df['a_shots_for'])
                
                # Contexto de Smart Money usando as odds de abertura e fechamento (ou abertura e live se não fechou)
                df['open_odd_h'] = df['open_odd_h'].fillna(2.80)
                df['open_odd_a'] = df['open_odd_a'].fillna(2.80)
                df['close_odd_h'] = df['close_odd_h'].fillna(df['live_odd_home']).fillna(2.80)
                df['close_odd_a'] = df['close_odd_a'].fillna(df['live_odd_away']).fillna(2.80)
                
                df['smart_money_home'] = df['open_odd_h'] / (df['close_odd_h'] + 0.01)
                df['smart_money_away'] = df['open_odd_a'] / (df['close_odd_a'] + 0.01)

                # Garante que as colunas existem
                for col in self.features:
                    if col not in df.columns: df[col] = 0.0
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

                X_pred = df[self.features]
                opportunities_found = 0

                # 1. PROCESSAR MERCADO ALPHA (1X2 MATCH ODDS)
                if "alpha_1x2" in self.models:
                    probs_1x2 = self.models["alpha_1x2"].predict_proba(X_pred)
                    
                    for i, row in df.iterrows():
                        odd_h = float(row.get('live_odd_home', 0) or 0)
                        odd_d = float(row.get('live_odd_draw', 0) or 0)
                        odd_a = float(row.get('live_odd_away', 0) or 0)

                        if odd_h > 1.0 and odd_d > 1.0 and odd_a > 1.0:
                            p_a, p_d, p_h = probs_1x2[i][0], probs_1x2[i][1], probs_1x2[i][2]
                            true_m_h, true_m_d, true_m_a = self._remove_overround_1x2(odd_h, odd_d, odd_a)

                            ev_h = (p_h * true_m_h) - 1.0
                            ev_a = (p_a * true_m_a) - 1.0

                            match_info = {"game": f"{row['home_team']} x {row['away_team']}", "sport": row['sport_key']}

                            if self.MIN_EV_THRESHOLD < ev_h < self.MAX_EV_THRESHOLD and p_h >= self.MIN_PROB_WIN:
                                await self.publish_signal(match_info, "Vencedor (Home)", ev_h, p_h, odd_h)
                                opportunities_found += 1
                                
                            elif self.MIN_EV_THRESHOLD < ev_a < self.MAX_EV_THRESHOLD and p_a >= self.MIN_PROB_WIN:
                                await self.publish_signal(match_info, "Vencedor (Away)", ev_a, p_a, odd_a)
                                opportunities_found += 1

                # (Futuramente você pode expandir aqui para iterar sobre os modelos Beta, Gamma, etc. 
                # basta ler as odds corretas do banco, exatamente como feito no bloco Alpha acima).

                print(f"\n🏆 RESUMO: {opportunities_found} Assimetrias Institucionais Disparadas pro Dashboard.\n")

        except Exception as e:
            logger.error(f"❌ Falha Crítica na Inferência Prequentiva: {e}")
        finally:
            await db.disconnect()
            if self.redis_client:
                await self.redis_client.aclose()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(MasterInferenceEngine().scan_and_predict())