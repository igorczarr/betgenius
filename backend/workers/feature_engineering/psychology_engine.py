# betgenius-backend/workers/feature_engineering/psychology_engine.py

import asyncio
import logging
import pandas as pd
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# =====================================================================
# BLINDAGEM DE ENCODING PARA WINDOWS E .ENV
# =====================================================================
if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [PSYCHO-ENGINE] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class PsychologyEngine:
    """
    Motor S-Tier de Análise Comportamental e Fraudes Estatísticas (Rolling Update).
    Calcula Streaks do passado e PROJETA para o futuro.
    Alimenta o ViewMatchCenter antes do apito inicial.
    """

    async def initialize_schema(self, conn):
        logger.info("🛠️ Validando Schema Psicológico...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS core.match_psychology_features (
                match_id INTEGER PRIMARY KEY REFERENCES core.matches_history(id) ON DELETE CASCADE,
                
                home_win_streak INTEGER,
                home_winless_streak INTEGER,
                home_clean_sheet_streak INTEGER,
                home_scoring_streak INTEGER,
                home_fraudulent_defense BOOLEAN,
                home_fraudulent_attack BOOLEAN,
                
                away_win_streak INTEGER,
                away_winless_streak INTEGER,
                away_clean_sheet_streak INTEGER,
                away_scoring_streak INTEGER,
                away_fraudulent_defense BOOLEAN,
                away_fraudulent_attack BOOLEAN
            );
        """)
        # Removido o TRUNCATE. O passado agora é intocável.

    def _build_team_perspective_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Desmembra o jogo para criar uma linha do tempo única por equipe."""
        # Home Perspective
        df_home = df[['match_id', 'match_date', 'status', 'home_team_id', 'home_goals', 'away_goals', 
                      'home_xg_against_ewma_micro', 'home_xg_for_ewma_macro']].copy()
        df_home.columns = ['match_id', 'date', 'status', 'team_id', 'goals_for', 'goals_against', 'xg_against_micro', 'xg_for_macro']
        df_home['is_home'] = 1

        # Away Perspective
        df_away = df[['match_id', 'match_date', 'status', 'away_team_id', 'away_goals', 'home_goals',
                      'away_xg_against_ewma_micro', 'away_xg_for_ewma_macro']].copy()
        df_away.columns = ['match_id', 'date', 'status', 'team_id', 'goals_for', 'goals_against', 'xg_against_micro', 'xg_for_macro']
        df_away['is_home'] = 0

        # Junta e ordena estritamente cronológico
        df_teams = pd.concat([df_home, df_away], ignore_index=True)
        df_teams['date'] = pd.to_datetime(df_teams['date'])
        df_teams = df_teams.sort_values(by=['team_id', 'date', 'match_id']).reset_index(drop=True)
        
        # Converte as EWMA táticas. Não preenche com zero ainda para permitir o Forward Fill.
        df_teams['xg_against_micro'] = pd.to_numeric(df_teams['xg_against_micro'], errors='coerce')
        df_teams['xg_for_macro'] = pd.to_numeric(df_teams['xg_for_macro'], errors='coerce')
        
        return df_teams

    def _calculate_streaks_and_frauds(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula os contadores no Passado e projeta o Momentum para o Futuro."""
        
        # 1. Projeta o Desempenho Tático para os jogos do futuro
        df['xg_against_micro'] = df.groupby('team_id')['xg_against_micro'].ffill().fillna(0.0)
        df['xg_for_macro'] = df.groupby('team_id')['xg_for_macro'].ffill().fillna(0.0)

        # 2. Isola os jogos finalizados para calcular o que de fato aconteceu
        df_fin = df[df['status'] == 'FINISHED'].copy()
        
        df_fin['is_win'] = df_fin['goals_for'] > df_fin['goals_against']
        df_fin['is_winless'] = df_fin['goals_for'] <= df_fin['goals_against']
        df_fin['is_clean_sheet'] = df_fin['goals_against'] == 0
        df_fin['is_scoring'] = df_fin['goals_for'] > 0

        # Função mágica vetorial para contar sequências no Pandas
        def count_streak(series):
            return series.astype(int) * (series.groupby((~series).cumsum()).cumcount() + 1)

        df_fin['win_streak_post'] = count_streak(df_fin['is_win'])
        df_fin['winless_streak_post'] = count_streak(df_fin['is_winless'])
        df_fin['clean_sheet_streak_post'] = count_streak(df_fin['is_clean_sheet'])
        df_fin['scoring_streak_post'] = count_streak(df_fin['is_scoring'])

        # 3. Junta as contagens pós-jogo com o DataFrame total (que inclui SCHEDULED)
        df = df.merge(
            df_fin[['match_id', 'team_id', 'win_streak_post', 'winless_streak_post', 'clean_sheet_streak_post', 'scoring_streak_post']], 
            on=['match_id', 'team_id'], 
            how='left'
        )

        # 4. A MÁGICA DA PROJEÇÃO: O Shift(1) desloca o resultado de ontem para o jogo de hoje.
        # O ffill() faz com que o jogo SCHEDULED herde exatamente a streak de ontem.
        df['win_streak'] = df.groupby('team_id')['win_streak_post'].shift(1).ffill().fillna(0).astype(int)
        df['winless_streak'] = df.groupby('team_id')['winless_streak_post'].shift(1).ffill().fillna(0).astype(int)
        df['clean_sheet_streak'] = df.groupby('team_id')['clean_sheet_streak_post'].shift(1).ffill().fillna(0).astype(int)
        df['scoring_streak'] = df.groupby('team_id')['scoring_streak_post'].shift(1).ffill().fillna(0).astype(int)

        # 5. DETECÇÃO DE FRAUDE ESTATÍSTICA (A Inteligência)
        # Calculada ANTES do jogo, combinando as Streaks deslocadas com a Tática
        df['fraudulent_defense'] = (df['clean_sheet_streak'] >= 3) & (df['xg_against_micro'] > 1.1)
        df['fraudulent_attack'] = (df['scoring_streak'] >= 3) & (df['xg_for_macro'] < 0.9)

        return df

    async def run_psychology_engine(self):
        logger.info("[INIT] INICIANDO PSYCHO ENGINE: Projeção de Bolhas de Mercado.")
        await db.connect()
        
        async with db.pool.acquire() as conn:
            await self.initialize_schema(conn)
            
            logger.info("📥 Extraindo Linha do Tempo (Passado e Futuro)...")
            
            # ATUALIZADO: Pega FINISHED para construir memória e SCHEDULED para injetar a previsão
            query = """
                SELECT m.id as match_id, m.match_date, m.status, 
                       m.home_team_id, m.away_team_id, m.home_goals, m.away_goals,
                       t.home_xg_against_ewma_micro, t.home_xg_for_ewma_macro,
                       t.away_xg_against_ewma_micro, t.away_xg_for_ewma_macro
                FROM core.matches_history m
                LEFT JOIN core.match_temporal_features t ON m.id = t.match_id
                WHERE m.status IN ('FINISHED', 'SCHEDULED')
                ORDER BY m.match_date ASC, m.id ASC
            """
            matches = await conn.fetch(query)
            
            if not matches:
                logger.warning("⚠️ Banco vazio. Abortando Psycho Engine.")
                await db.disconnect()
                return

            df = pd.DataFrame([dict(m) for m in matches])

            logger.info("🧬 Calculando Streaks e Fraudes Temporais...")
            df_teams = self._build_team_perspective_df(df)
            df_features = self._calculate_streaks_and_frauds(df_teams)

            logger.info("🔄 Isolando janela recente e futura para o UPSERT...")
            
            # Filtro S-Tier: Só atualiza os últimos 7 dias e os jogos que vão acontecer.
            # Isso impede que o sistema derreta tentando reescrever anos de história diariamente.
            ##cutoff_date = pd.Timestamp(datetime.now().date() - timedelta(days=7))
            # CÓDIGO NOVO S-TIER (Adicione em todos os 4 engines):
            is_genesis = os.getenv("GENESIS_MODE", "False") == "True"
            if is_genesis:
                logger.warning("⚠️ MODO GÊNESIS ATIVADO: Processando toda a história do futebol...")
                cutoff_date = pd.Timestamp('2010-01-01')
            else:
                cutoff_date = pd.Timestamp(datetime.now().date() - timedelta(days=7))
                
            df_to_update = df_features[df_features['date'] >= cutoff_date]

            home_feats = df_to_update[df_to_update['is_home'] == 1].set_index('match_id')
            away_feats = df_to_update[df_to_update['is_home'] == 0].set_index('match_id')

            records_to_insert = []
            valid_match_ids = df_to_update['match_id'].unique()
            
            for match_id in valid_match_ids:
                if match_id in home_feats.index and match_id in away_feats.index:
                    h = home_feats.loc[match_id]
                    a = away_feats.loc[match_id]
                    
                    h_val = h.iloc[0] if isinstance(h, pd.DataFrame) else h
                    a_val = a.iloc[0] if isinstance(a, pd.DataFrame) else a
                    
                    records_to_insert.append((
                        int(match_id),
                        int(h_val['win_streak']), int(h_val['winless_streak']), 
                        int(h_val['clean_sheet_streak']), int(h_val['scoring_streak']),
                        bool(h_val['fraudulent_defense']), bool(h_val['fraudulent_attack']),
                        
                        int(a_val['win_streak']), int(a_val['winless_streak']), 
                        int(a_val['clean_sheet_streak']), int(a_val['scoring_streak']),
                        bool(a_val['fraudulent_defense']), bool(a_val['fraudulent_attack'])
                    ))

            if records_to_insert:
                logger.info(f"💾 Injetando {len(records_to_insert)} perfis psicológicos no Data Warehouse...")
                try:
                    await conn.executemany("""
                        INSERT INTO core.match_psychology_features (
                            match_id, 
                            home_win_streak, home_winless_streak, home_clean_sheet_streak, home_scoring_streak, home_fraudulent_defense, home_fraudulent_attack,
                            away_win_streak, away_winless_streak, away_clean_sheet_streak, away_scoring_streak, away_fraudulent_defense, away_fraudulent_attack
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                        ON CONFLICT (match_id) DO UPDATE SET
                            home_win_streak = EXCLUDED.home_win_streak,
                            home_winless_streak = EXCLUDED.home_winless_streak,
                            home_clean_sheet_streak = EXCLUDED.home_clean_sheet_streak,
                            home_scoring_streak = EXCLUDED.home_scoring_streak,
                            home_fraudulent_defense = EXCLUDED.home_fraudulent_defense,
                            home_fraudulent_attack = EXCLUDED.home_fraudulent_attack,
                            away_win_streak = EXCLUDED.away_win_streak,
                            away_winless_streak = EXCLUDED.away_winless_streak,
                            away_clean_sheet_streak = EXCLUDED.away_clean_sheet_streak,
                            away_scoring_streak = EXCLUDED.away_scoring_streak,
                            away_fraudulent_defense = EXCLUDED.away_fraudulent_defense,
                            away_fraudulent_attack = EXCLUDED.away_fraudulent_attack;
                    """, records_to_insert)
                except Exception as e:
                    logger.error(f"❌ Erro Crítico durante UPSERT no Postgres: {e}")
            else:
                logger.info("ℹ️ Nenhuma sequência psicológica precisou de atualização hoje.")

        await db.disconnect()
        logger.info("[DONE] PSYCHO ENGINE CONCLUÍDO. As Bolhas de Mercado estão expostas para hoje.")

if __name__ == "__main__":
    engine = PsychologyEngine()
    asyncio.run(engine.run_psychology_engine())