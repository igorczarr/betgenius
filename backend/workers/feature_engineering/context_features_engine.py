# betgenius-backend/workers/feature_engineering/context_features_engine.py

import sys
import os

if sys.platform == "win32":
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
import math
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

pd.set_option('future.no_silent_downcasting', True)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [CONTEXT-ENGINE] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class ContextFeaturesEngine:
    """
    Motor S-Tier de Features de Contexto (Psicologia, Mercado e Dinâmica de Campeonato).
    Utiliza Difficulty-Adjusted Momentum (Elo), xPts (Expected Points) e Fraude Avançada.
    """

    async def initialize_schema(self, conn):
        logger.info("🛠️ Validando Schema de Contexto...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS core.match_context_features (
                match_id INTEGER PRIMARY KEY REFERENCES core.matches_history(id) ON DELETE CASCADE,
                home_win_streak NUMERIC(5, 2),
                away_win_streak NUMERIC(5, 2),
                home_winless_streak NUMERIC(5, 2),
                away_winless_streak NUMERIC(5, 2),
                home_fraudulent_defense NUMERIC(5, 2),
                away_fraudulent_defense NUMERIC(5, 2),
                home_fraudulent_attack NUMERIC(5, 2),
                away_fraudulent_attack NUMERIC(5, 2),
                home_tension_index NUMERIC(5, 2),
                away_tension_index NUMERIC(5, 2),
                home_market_respect NUMERIC(5, 2),
                away_market_respect NUMERIC(5, 2),
                home_pts_before NUMERIC(5, 2),
                away_pts_before NUMERIC(5, 2),
                pos_tabela_home INTEGER,
                pos_tabela_away INTEGER
            );
        """)

    def _calculate_xpts(self, xgf: float, xga: float) -> float:
        """
        Calcula os Pontos Esperados (xPts) usando a Expectativa Pitagórica adaptada.
        Isto reflete quantos pontos a equipa "merecia" ganhar com base na qualidade das chances.
        """
        if pd.isna(xgf) or pd.isna(xga): return 1.0 # Neutro
        xgf = max(0.01, xgf)
        xga = max(0.01, xga)
        
        # Expoente ajustado para futebol (normalmente entre 1.2 e 1.7)
        exp = 1.3 
        prob_win = (xgf**exp) / ((xgf**exp) + (xga**exp))
        prob_loss = (xga**exp) / ((xgf**exp) + (xga**exp))
        prob_draw = 1.0 - (prob_win + prob_loss)
        
        # P(Draw) raramente é menor que 20% em jogos normais, aplicamos um alisamento
        if prob_draw < 0.20:
            prob_draw = 0.20
            remaining = 1.0 - prob_draw
            total_prob = prob_win + prob_loss
            prob_win = (prob_win / total_prob) * remaining
            prob_loss = (prob_loss / total_prob) * remaining
            
        return (prob_win * 3) + (prob_draw * 1)

    def _build_context_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Processa as dinâmicas de forma rigorosamente cronológica, 
        aplicando ELO aos Streaks e xPts à detecção de Fraude.
        """
        df['match_date'] = pd.to_datetime(df['match_date'])
        df = df.sort_values(by=['match_date', 'match_id']).reset_index(drop=True)

        logger.info("🧠 Calculando Dinâmicas Quantitativas (Difficulty-Adjusted Momentum e xPts)...")
        
        league_standings = {}
        
        # Estruturas para a Matemática S-Tier
        context_memory = {
            'momentum_positivo': {}, # Streaks de vitória ponderados por ELO
            'momentum_negativo': {}, # Streaks sem vitória ponderados
            'xpts_diff': {},         # Diferença entre Pontos Reais e xPts
            'atk_fraud': {},         # Fraude específica de ataque (Golos - xGF)
            'def_fraud': {}          # Fraude específica de defesa (xGA - Golos)
        }

        context_records = []

        for index, row in df.iterrows():
            m_id = row['match_id']
            h_id = row['home_team_id']
            a_id = row['away_team_id']
            season = str(row['season'])
            league = str(row['sport_key'])
            status = row['status']
            
            elo_h = float(row.get('home_elo_before') or 1500.0)
            elo_a = float(row.get('away_elo_before') or 1500.0)
            
            # --- 1. GESTÃO DE CLASSIFICAÇÃO (TENSÃO) ---
            league_key = f"{league}_{season}"
            if league_key not in league_standings:
                league_standings[league_key] = {}
                
            standings = league_standings[league_key]
            
            if h_id not in standings: standings[h_id] = {'pts': 0, 'matches': 0}
            if a_id not in standings: standings[a_id] = {'pts': 0, 'matches': 0}

            h_pts_before = standings[h_id]['pts']
            a_pts_before = standings[a_id]['pts']
            
            sorted_teams = sorted(standings.keys(), key=lambda x: standings[x]['pts'], reverse=True)
            try:
                pos_h = sorted_teams.index(h_id) + 1 if standings[h_id]['matches'] > 0 else 0
                pos_a = sorted_teams.index(a_id) + 1 if standings[a_id]['matches'] > 0 else 0
            except ValueError:
                pos_h, pos_a = 0, 0

            progress_factor = min(1.0, max(0.1, standings[h_id]['matches'] / 38.0))
            h_tension = 0.5 + (0.5 if pos_h > 15 else (-0.2 if pos_h < 5 else 0.0)) * progress_factor
            a_tension = 0.5 + (0.5 if pos_a > 15 else (-0.2 if pos_a < 5 else 0.0)) * progress_factor

            # --- 2. GESTÃO DE MOMENTUM (Difficulty-Adjusted) ---
            h_win_streak = context_memory['momentum_positivo'].get(h_id, 0.0)
            a_win_streak = context_memory['momentum_positivo'].get(a_id, 0.0)
            h_winless_streak = context_memory['momentum_negativo'].get(h_id, 0.0)
            a_winless_streak = context_memory['momentum_negativo'].get(a_id, 0.0)

            # Fraudes separadas por setores com suavização (EWMA de memória curta)
            h_fraud_atk = context_memory['atk_fraud'].get(h_id, 0.0)
            a_fraud_atk = context_memory['atk_fraud'].get(a_id, 0.0)
            h_fraud_def = context_memory['def_fraud'].get(h_id, 0.0)
            a_fraud_def = context_memory['def_fraud'].get(a_id, 0.0)

            # --- 3. MARKET RESPECT (Odds de Abertura) ---
            pin_h = float(row.get('pin_odd_home') or 2.80)
            pin_a = float(row.get('pin_odd_away') or 2.80)
            
            prob_h_open = (1.0 / pin_h) if pin_h > 1.0 else 0.35
            prob_a_open = (1.0 / pin_a) if pin_a > 1.0 else 0.35

            # Salva o Tensor para Injeção (Decadência diária do Momentum)
            context_records.append({
                'match_id': m_id,
                'home_win_streak': round(float(h_win_streak), 2),
                'away_win_streak': round(float(a_win_streak), 2),
                'home_winless_streak': round(float(h_winless_streak), 2),
                'away_winless_streak': round(float(a_winless_streak), 2),
                'home_fraudulent_defense': round(float(h_fraud_def), 2),
                'away_fraudulent_defense': round(float(a_fraud_def), 2),
                'home_fraudulent_attack': round(float(h_fraud_atk), 2),
                'away_fraudulent_attack': round(float(a_fraud_atk), 2),
                'home_tension_index': round(float(h_tension), 2),
                'away_tension_index': round(float(a_tension), 2),
                'home_market_respect': round(float(prob_h_open), 2),
                'away_market_respect': round(float(prob_a_open), 2),
                'home_pts_before': h_pts_before,
                'away_pts_before': a_pts_before,
                'pos_tabela_home': pos_h,
                'pos_tabela_away': pos_a
            })

            # --- ATUALIZA A MEMÓRIA PARA O PRÓXIMO JOGO (MATEMÁTICA AVANÇADA) ---
            if status == 'FINISHED':
                hg = float(row.get('home_goals') or 0)
                ag = float(row.get('away_goals') or 0)
                xgh = float(row.get('xg_home') or 0)
                xga = float(row.get('xg_away') or 0)

                # 1. PONTUAÇÃO REAL vs XPTS
                standings[h_id]['matches'] += 1
                standings[a_id]['matches'] += 1
                
                h_xpts = self._calculate_xpts(xgh, xga)
                a_xpts = self._calculate_xpts(xga, xgh)
                
                real_pts_h = 3 if hg > ag else (1 if hg == ag else 0)
                real_pts_a = 3 if ag > hg else (1 if ag == hg else 0)
                
                standings[h_id]['pts'] += real_pts_h
                standings[a_id]['pts'] += real_pts_a

                # 2. DIFFICULTY-ADJUSTED MOMENTUM
                # Se vencer, o impulso é ponderado pelo ELO do adversário.
                momentum_decay = 0.85 # As equipas esquecem o passado ao longo das semanas
                
                if real_pts_h == 3:
                    context_memory['momentum_positivo'][h_id] = (context_memory['momentum_positivo'].get(h_id, 0) * momentum_decay) + (elo_a / 1000.0)
                    context_memory['momentum_negativo'][h_id] = 0.0
                elif real_pts_h == 1:
                    # Empate anula vitórias e perdas extremas
                    context_memory['momentum_positivo'][h_id] = context_memory['momentum_positivo'].get(h_id, 0) * 0.5
                    context_memory['momentum_negativo'][h_id] = context_memory['momentum_negativo'].get(h_id, 0) * 0.5
                else:
                    context_memory['momentum_positivo'][h_id] = 0.0
                    context_memory['momentum_negativo'][h_id] = (context_memory['momentum_negativo'].get(h_id, 0) * momentum_decay) + (1500.0 / max(1, elo_a))

                if real_pts_a == 3:
                    context_memory['momentum_positivo'][a_id] = (context_memory['momentum_positivo'].get(a_id, 0) * momentum_decay) + (elo_h / 1000.0)
                    context_memory['momentum_negativo'][a_id] = 0.0
                elif real_pts_a == 1:
                    context_memory['momentum_positivo'][a_id] = context_memory['momentum_positivo'].get(a_id, 0) * 0.5
                    context_memory['momentum_negativo'][a_id] = context_memory['momentum_negativo'].get(a_id, 0) * 0.5
                else:
                    context_memory['momentum_positivo'][a_id] = 0.0
                    context_memory['momentum_negativo'][a_id] = (context_memory['momentum_negativo'].get(a_id, 0) * momentum_decay) + (1500.0 / max(1, elo_h))

                # 3. CÁLCULO DE FRAUDE (EWMA SUAVE)
                # Ataque Fraudulento: Golos que não deveria ter marcado
                atk_fraud_h = hg - xgh
                atk_fraud_a = ag - xga
                # Defesa Fraudulenta: Golos que deveria ter sofrido e não sofreu
                def_fraud_h = xga - ag
                def_fraud_a = xgh - hg

                context_memory['atk_fraud'][h_id] = (context_memory['atk_fraud'].get(h_id, 0) * 0.7) + (atk_fraud_h * 0.3)
                context_memory['atk_fraud'][a_id] = (context_memory['atk_fraud'].get(a_id, 0) * 0.7) + (atk_fraud_a * 0.3)
                
                context_memory['def_fraud'][h_id] = (context_memory['def_fraud'].get(h_id, 0) * 0.7) + (def_fraud_h * 0.3)
                context_memory['def_fraud'][a_id] = (context_memory['def_fraud'].get(a_id, 0) * 0.7) + (def_fraud_a * 0.3)

        return pd.DataFrame(context_records)

    async def run_context_engine(self):
        logger.info("[INIT] INICIANDO CONTEXT ENGINE: Psicologia e xPts (Pitagórico).")
        await db.connect()
        
        async with db.pool.acquire() as conn:
            await self.initialize_schema(conn)
            
            logger.info("📥 Extraindo Matriz Base...")
            
            # ATUALIZAÇÃO S-TIER: Removido JOIN desnecessário e adicionado o ELO Histórico (Necessário para o Momentum)
            query = """
                SELECT m.id as match_id, m.match_date, m.status, m.sport_key, m.season,
                       m.home_team_id, m.away_team_id, m.home_goals, m.away_goals,
                       m.xg_home, m.xg_away,
                       m.pin_odd_home, m.pin_odd_away,
                       e.home_elo_before, e.away_elo_before
                FROM core.matches_history m
                LEFT JOIN core.match_elo_history e ON m.id = e.match_id
                WHERE m.status IN ('FINISHED', 'SCHEDULED')
                ORDER BY m.match_date ASC, m.id ASC
            """
            matches = await conn.fetch(query)
            
            if not matches:
                logger.error("❌ Histórico vazio. Abortando Context Engine.")
                await db.disconnect()
                return

            df = pd.DataFrame([dict(m) for m in matches])

            logger.info("🧬 Simulando Dinâmicas Quantitativas em Memória...")
            df_context = self._build_context_features(df)

            is_genesis = os.getenv("GENESIS_MODE", "False") == "True"
            if is_genesis:
                logger.warning("⚠️ MODO GÊNESIS ATIVADO: Gravando TODO o contexto histórico.")
                cutoff_date = pd.Timestamp('2010-01-01')
            else:
                cutoff_date = pd.Timestamp(datetime.now().date() - timedelta(days=7))
                
            df_context = df_context.merge(df[['match_id', 'match_date']], on='match_id', how='left')
            df_to_update = df_context[df_context['match_date'] >= cutoff_date]

            records_to_upsert = df_to_update.drop(columns=['match_date']).to_dict(orient='records')
            
            tuple_records = [
                (
                    r['match_id'], r['home_win_streak'], r['away_win_streak'],
                    r['home_winless_streak'], r['away_winless_streak'],
                    r['home_fraudulent_defense'], r['away_fraudulent_defense'],
                    r['home_fraudulent_attack'], r['away_fraudulent_attack'],
                    r['home_tension_index'], r['away_tension_index'],
                    r['home_market_respect'], r['away_market_respect'],
                    r['home_pts_before'], r['away_pts_before'],
                    r['pos_tabela_home'], r['pos_tabela_away']
                ) for r in records_to_upsert
            ]

            if tuple_records:
                batch_size = 10000
                total_batches = (len(tuple_records) // batch_size) + 1
                logger.info(f"💾 Projetando {len(tuple_records)} tensores de contexto S-Tier no Banco em {total_batches} lotes...")
                
                upsert_query = """
                    INSERT INTO core.match_context_features (
                        match_id, home_win_streak, away_win_streak,
                        home_winless_streak, away_winless_streak,
                        home_fraudulent_defense, away_fraudulent_defense,
                        home_fraudulent_attack, away_fraudulent_attack,
                        home_tension_index, away_tension_index,
                        home_market_respect, away_market_respect,
                        home_pts_before, away_pts_before,
                        pos_tabela_home, pos_tabela_away
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                    ON CONFLICT (match_id) DO UPDATE SET
                        home_win_streak = EXCLUDED.home_win_streak,
                        away_win_streak = EXCLUDED.away_win_streak,
                        home_winless_streak = EXCLUDED.home_winless_streak,
                        away_winless_streak = EXCLUDED.away_winless_streak,
                        home_fraudulent_defense = EXCLUDED.home_fraudulent_defense,
                        away_fraudulent_defense = EXCLUDED.away_fraudulent_defense,
                        home_fraudulent_attack = EXCLUDED.home_fraudulent_attack,
                        away_fraudulent_attack = EXCLUDED.away_fraudulent_attack,
                        home_tension_index = EXCLUDED.home_tension_index,
                        away_tension_index = EXCLUDED.away_tension_index,
                        home_market_respect = EXCLUDED.home_market_respect,
                        away_market_respect = EXCLUDED.away_market_respect,
                        home_pts_before = EXCLUDED.home_pts_before,
                        away_pts_before = EXCLUDED.away_pts_before,
                        pos_tabela_home = EXCLUDED.pos_tabela_home,
                        pos_tabela_away = EXCLUDED.pos_tabela_away;
                """
                
                try:
                    for i in range(0, len(tuple_records), batch_size):
                        batch = tuple_records[i:i + batch_size]
                        await conn.executemany(upsert_query, batch)
                        logger.info(f"   └ Lote de Contexto {(i//batch_size)+1}/{total_batches} concluído.")
                except Exception as e:
                    logger.error(f"❌ Falha ao realizar UPSERT contextual no banco: {e}")
            else:
                logger.info("ℹ️ Nenhuma métrica de contexto precisou ser atualizada hoje.")

        await db.disconnect()
        logger.info("[DONE] MÁQUINA DE CONTEXTO CONCLUÍDA. O Motor Psicológico está a operar.")

if __name__ == "__main__":
    engine = ContextFeaturesEngine()
    asyncio.run(engine.run_context_engine())