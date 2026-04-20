# betgenius-backend/workers/feature_engineering/psychology_engine.py

import asyncio
import logging
import pandas as pd
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# =====================================================================
# BLINDAGEM DE ENCODING PARA WINDOWS E CARREGAMENTO DO .ENV
# =====================================================================
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [PSYCHO-ENGINE] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class PsychologyEngine:
    """
    Motor S-Tier de Análise Comportamental e Detecção de Fraudes Estatísticas.
    Calcula sequências (Streaks) e cruza com a métrica de Desempenho (xG EWMA)
    para identificar times supervalorizados ou subvalorizados pelo mercado.
    """

    async def initialize_schema(self, conn):
        logger.info("🛠️ Preparando Schema Psicológico...")
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
        await conn.execute("TRUNCATE TABLE core.match_psychology_features CASCADE;")

    def _build_team_perspective_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Desmembra o jogo para criar uma linha do tempo única por equipe."""
        # Home Perspective
        df_home = df[['match_id', 'match_date', 'home_team_id', 'home_goals', 'away_goals', 
                      'home_xg_against_ewma_micro', 'home_xg_for_ewma_macro']].copy()
        df_home.columns = ['match_id', 'date', 'team_id', 'goals_for', 'goals_against', 'xg_against_micro', 'xg_for_macro']
        df_home['is_home'] = 1

        # Away Perspective
        df_away = df[['match_id', 'match_date', 'away_team_id', 'away_goals', 'home_goals',
                      'away_xg_against_ewma_micro', 'away_xg_for_ewma_macro']].copy()
        df_away.columns = ['match_id', 'date', 'team_id', 'goals_for', 'goals_against', 'xg_against_micro', 'xg_for_macro']
        df_away['is_home'] = 0

        # Junta e ordena cronologicamente
        df_teams = pd.concat([df_home, df_away], ignore_index=True)
        df_teams = df_teams.sort_values(by=['team_id', 'date']).reset_index(drop=True)
        
        # Garante que os números são tratáveis (para quando o LEFT JOIN retornar nulo)
        df_teams['xg_against_micro'] = pd.to_numeric(df_teams['xg_against_micro'], errors='coerce').fillna(0.0)
        df_teams['xg_for_macro'] = pd.to_numeric(df_teams['xg_for_macro'], errors='coerce').fillna(0.0)
        
        return df_teams

    def _calculate_streaks_and_frauds(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula os contadores usando funções vetoriais de alta performance do Pandas."""
        
        # 1. Cria as condições booleanas do jogo que acabou de acontecer
        df['is_win'] = df['goals_for'] > df['goals_against']
        df['is_winless'] = df['goals_for'] <= df['goals_against']
        df['is_clean_sheet'] = df['goals_against'] == 0
        df['is_scoring'] = df['goals_for'] > 0

        # 2. Função mágica S-Tier para contar sequências (Zera quando a condição é Falsa)
        def count_streak(series):
            return series.groupby((~series).cumsum()).cumcount()

        # Calcula a sequência EXATAMENTE APÓS o jogo
        df['win_streak_post'] = df.groupby('team_id')['is_win'].transform(count_streak)
        df['winless_streak_post'] = df.groupby('team_id')['is_winless'].transform(count_streak)
        df['clean_sheet_streak_post'] = df.groupby('team_id')['is_clean_sheet'].transform(count_streak)
        df['scoring_streak_post'] = df.groupby('team_id')['is_scoring'].transform(count_streak)

        # 3. PROTEÇÃO ANTI-DATA LEAKAGE (O .shift(1))
        # O que nos importa é a sequência que o time tinha ANTES do apito inicial.
        cols_to_shift = ['win_streak_post', 'winless_streak_post', 'clean_sheet_streak_post', 'scoring_streak_post']
        for col in cols_to_shift:
            new_col = col.replace('_post', '')
            df[new_col] = df.groupby('team_id')[col].shift(1).fillna(0).astype(int)

        # 4. A DETECÇÃO DE FRAUDE (A Inteligência do Sindicato)
        # Fraude Defensiva: Pelo menos 3 jogos sem tomar gol, mas sofrendo mais de 1.1 xG de média (Sorte pura/Goleiro herói)
        df['fraudulent_defense'] = (df['clean_sheet_streak'] >= 3) & (df['xg_against_micro'] > 1.1)
        
        # Fraude Ofensiva: Pelo menos 3 jogos marcando gol, mas criando menos de 0.9 xG de média (Eficiência insustentável)
        df['fraudulent_attack'] = (df['scoring_streak'] >= 3) & (df['xg_for_macro'] < 0.9)

        return df

    async def run_psychology_engine(self):
        logger.info("[INIT] INICIANDO PSYCHO ENGINE: Caçando Bolhas de Mercado e Sequências.")
        await db.connect()
        
        async with db.pool.acquire() as conn:
            await self.initialize_schema(conn)
            
            logger.info("📥 Cruzando Resultados Históricos com os Tensores Temporais (xG EWMA)...")
            
            # LEFT JOIN protege contra ausência de dados na temporal_features
            # O WHERE filtra jogos futuros ou cancelados
            query = """
                SELECT m.id as match_id, m.match_date, m.home_team_id, m.away_team_id, m.home_goals, m.away_goals,
                       t.home_xg_against_ewma_micro, t.home_xg_for_ewma_macro,
                       t.away_xg_against_ewma_micro, t.away_xg_for_ewma_macro
                FROM core.matches_history m
                LEFT JOIN core.match_temporal_features t ON m.id = t.match_id
                WHERE m.home_goals IS NOT NULL AND m.away_goals IS NOT NULL
                ORDER BY m.match_date ASC, m.id ASC
            """
            matches = await conn.fetch(query)
            
            if not matches:
                logger.warning("⚠️ Banco histórico vazio ou sem gols registrados. Abortando.")
                await db.disconnect()
                return

            df = pd.DataFrame([dict(m) for m in matches])

            logger.info("🧬 Isolando Times e Calculando Streaks Psicológicas...")
            df_teams = self._build_team_perspective_df(df)
            df_features = self._calculate_streaks_and_frauds(df_teams)

            logger.info("🔄 Recombinando Tensores para injeção (Home/Away)...")
            home_feats = df_features[df_features['is_home'] == 1].set_index('match_id')
            away_feats = df_features[df_features['is_home'] == 0].set_index('match_id')

            records_to_insert = []
            valid_match_ids = df_features['match_id'].unique()
            
            for match_id in valid_match_ids:
                if match_id in home_feats.index and match_id in away_feats.index:
                    h = home_feats.loc[match_id]
                    a = away_feats.loc[match_id]
                    
                    # Extração segura dos valores (evitando erro de Series vs Float)
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

            logger.info("💾 Injetando Dimensão Psicológica no Data Warehouse (Copy)...")
            try:
                await conn.copy_records_to_table(
                    'match_psychology_features', schema_name='core',
                    records=records_to_insert,
                    columns=[
                        'match_id', 
                        'home_win_streak', 'home_winless_streak', 'home_clean_sheet_streak', 'home_scoring_streak', 'home_fraudulent_defense', 'home_fraudulent_attack',
                        'away_win_streak', 'away_winless_streak', 'away_clean_sheet_streak', 'away_scoring_streak', 'away_fraudulent_defense', 'away_fraudulent_attack'
                    ]
                )
            except Exception as e:
                logger.error(f"❌ Erro ao gravar dados no PostgreSQL: {e}")

        await db.disconnect()
        logger.info("[DONE] PSYCHO ENGINE CONCLUÍDO. As bolhas do mercado estão expostas.")

if __name__ == "__main__":
    engine = PsychologyEngine()
    asyncio.run(engine.run_psychology_engine())