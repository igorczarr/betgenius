# betgenius-backend/workers/feature_engineering/matrix_builder.py

import asyncio
import logging
import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [MATRIX-BUILDER] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class QuantMLBuilder:
    """
    O Liquidificador S-Tier.
    Funde todas as dimensões (Elo, Psicologia, Tensão, Mercado, Temporal), 
    calcula Deltas e forja a 'quant_ml.feature_store' para o XGBoost.
    """

    async def initialize_schema(self, conn):
        await conn.execute("CREATE SCHEMA IF NOT EXISTS quant_ml;")
        await conn.execute("DROP TABLE IF EXISTS quant_ml.feature_store CASCADE;")

    def _calculate_standings_and_points(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("📊 Mapeando Dinâmica de Campeonato (Pontos e Posição)...")
        
        df['home_pts_earned'] = np.where(df['home_goals'] > df['away_goals'], 3, np.where(df['home_goals'] == df['away_goals'], 1, 0))
        df['away_pts_earned'] = np.where(df['away_goals'] > df['home_goals'], 3, np.where(df['home_goals'] == df['away_goals'], 1, 0))
        df['home_gd_earned'] = df['home_goals'] - df['away_goals']
        df['away_gd_earned'] = df['away_goals'] - df['home_goals']

        home_df = df[['match_id', 'match_date', 'sport_key', 'season', 'home_team_id', 'home_pts_earned', 'home_gd_earned']].copy()
        home_df.columns = ['match_id', 'date', 'league', 'season', 'team_id', 'pts_earned', 'gd_earned']
        home_df['is_home'] = 1

        away_df = df[['match_id', 'match_date', 'sport_key', 'season', 'away_team_id', 'away_pts_earned', 'away_gd_earned']].copy()
        away_df.columns = ['match_id', 'date', 'league', 'season', 'team_id', 'pts_earned', 'gd_earned']
        away_df['is_home'] = 0

        teams_timeline = pd.concat([home_df, away_df]).sort_values(by=['date', 'match_id']).reset_index(drop=True)
        grouped = teams_timeline.groupby(['league', 'season', 'team_id'])
        
        teams_timeline['cum_pts'] = grouped['pts_earned'].transform(lambda x: x.shift(1).cumsum().fillna(0))
        teams_timeline['cum_gd'] = grouped['gd_earned'].transform(lambda x: x.shift(1).cumsum().fillna(0))
        teams_timeline['rodada'] = grouped.cumcount() + 1

        teams_timeline.sort_values(by=['league', 'season', 'rodada', 'cum_pts', 'cum_gd'], 
                                   ascending=[True, True, True, False, False], inplace=True)
        
        teams_timeline['pos_tabela'] = teams_timeline.groupby(['league', 'season', 'rodada']).cumcount() + 1

        home_feats = teams_timeline[teams_timeline['is_home'] == 1][['match_id', 'rodada', 'cum_pts', 'pos_tabela']]
        home_feats.columns = ['match_id', 'rodada', 'home_pts_before', 'pos_tabela_home']

        away_feats = teams_timeline[teams_timeline['is_home'] == 0][['match_id', 'cum_pts', 'pos_tabela']]
        away_feats.columns = ['match_id', 'away_pts_before', 'pos_tabela_away']

        df = df.merge(home_feats, on='match_id', how='left')
        df = df.merge(away_feats, on='match_id', how='left')

        df.drop(columns=['home_pts_earned', 'away_pts_earned', 'home_gd_earned', 'away_gd_earned'], inplace=True)
        return df

    async def build_matrix(self):
        logger.info("[INIT] INICIANDO QUANT ML BUILDER: Forjando a Tabela Definitiva.")
        await db.connect()
        
        async with db.pool.acquire() as conn:
            await self.initialize_schema(conn)
            
            logger.info("📥 Executando Super-JOIN interdimensional no Data Warehouse...")
            
            query = """
                SELECT 
                    -- DADOS BASE
                    m.id as match_id, m.sport_key, m.season, m.match_date, 
                    m.home_team_id, m.away_team_id, m.home_goals, m.away_goals,
                    m.closing_odd_home, m.closing_odd_draw, m.closing_odd_away,
                    
                    -- DIMENSÃO: ELO CRU (Ajustado para a tabela nova)
                    eh.home_elo_before, eh.away_elo_before,
                    
                    -- DIMENSÃO: PEDIGREE E RIQUEZA
                    hp.league_tier, hp.avg_wage_percentile as home_wage_pct, ap.avg_wage_percentile as away_wage_pct,
                    
                    -- DIMENSÃO: TEMPORAL
                    t.home_rest_days, t.away_rest_days,
                    t.home_xg_for_ewma_micro, t.home_xg_against_ewma_micro,
                    t.away_xg_for_ewma_micro, t.away_xg_against_ewma_micro,
                    t.home_xg_for_ewma_macro, t.away_xg_for_ewma_macro,
                    t.home_aggression_ewma, t.away_aggression_ewma,
                    
                    -- DIMENSÃO: PSICOLOGIA E FRAUDES
                    p.home_win_streak, p.home_winless_streak, p.home_clean_sheet_streak,
                    p.home_fraudulent_defense, p.home_fraudulent_attack,
                    p.away_win_streak, p.away_winless_streak, p.away_clean_sheet_streak,
                    p.away_fraudulent_defense, p.away_fraudulent_attack,
                    
                    -- DIMENSÃO: MARKET RESPECT
                    mk.home_market_respect, mk.away_market_respect,

                    -- DIMENSÃO: TENSÃO (Adicionado!)
                    tn.home_tension_index, tn.away_tension_index
                    
                FROM core.matches_history m
                LEFT JOIN core.match_elo_history eh ON m.id = eh.match_id
                LEFT JOIN core.team_pedigree hp ON m.home_team_id = hp.team_id
                LEFT JOIN core.team_pedigree ap ON m.away_team_id = ap.team_id
                LEFT JOIN core.match_temporal_features t ON m.id = t.match_id
                LEFT JOIN core.match_psychology_features p ON m.id = p.match_id
                LEFT JOIN core.match_market_features mk ON m.id = mk.match_id
                LEFT JOIN core.match_tension_features tn ON m.id = tn.match_id
                
                WHERE m.closing_odd_home > 0 AND m.closing_odd_away > 0
                AND m.home_goals IS NOT NULL AND m.away_goals IS NOT NULL
                ORDER BY m.match_date ASC
            """
            
            matches = await conn.fetch(query)
            if not matches:
                logger.error("❌ O Super-JOIN retornou vazio.")
                await db.disconnect()
                return

            df = pd.DataFrame([dict(m) for m in matches])
            logger.info(f"🧬 Tensor Bruto extraído: {df.shape[0]} jogos e {df.shape[1]} features originais.")

            df = self._calculate_standings_and_points(df)

            logger.info("📐 Calculando Diferenciais Numéricos (Deltas)...")
            df = df.fillna(0)

            df['delta_elo'] = df['home_elo_before'] - df['away_elo_before']
            df['delta_wage_pct'] = df['home_wage_pct'] - df['away_wage_pct']
            df['delta_pontos'] = df['home_pts_before'] - df['away_pts_before']
            df['delta_posicao'] = df['pos_tabela_away'] - df['pos_tabela_home']
            df['delta_market_respect'] = df['home_market_respect'] - df['away_market_respect']
            df['delta_tension'] = df['home_tension_index'] - df['away_tension_index']

            logger.info("🎯 Gerando Variáveis Alvo (Targets)...")
            
            # Para Multi-classe (0 = Away, 1 = Draw, 2 = Home) - Formato exigido pelo XGBoost
            def get_target(row):
                if row['home_goals'] > row['away_goals']: return 2
                elif row['home_goals'] < row['away_goals']: return 0
                return 1
            
            df['target_match_result'] = df.apply(get_target, axis=1)
            
            # Secundários
            df['total_goals'] = df['home_goals'] + df['away_goals']
            df['target_over_25'] = (df['total_goals'] > 2.5).astype(int)
            df['target_btts'] = ((df['home_goals'] > 0) & (df['away_goals'] > 0)).astype(int)

            bool_cols = [c for c in df.columns if 'fraudulent' in c]
            for col in bool_cols: df[col] = df[col].astype(int)

            logger.info(f"💾 Injetando Machine Learning Matrix ({df.shape[1]} colunas)...")
            
            columns_to_save = list(df.columns)
            records_to_insert = [tuple(x) for x in df.to_numpy()]
            
            create_cols = []
            for col in columns_to_save:
                if 'match_id' in col: create_cols.append(f"{col} VARCHAR(50) PRIMARY KEY") 
                elif 'date' in col: create_cols.append(f"{col} DATE")
                elif 'sport_key' in col or 'season' in col: create_cols.append(f"{col} VARCHAR(50)")
                elif 'target_' in col or 'pos_tabela' in col or 'rodada' in col or df[col].dtype in ['int32', 'int64', 'bool']: 
                    create_cols.append(f"{col} SMALLINT")
                else: 
                    create_cols.append(f"{col} NUMERIC(8,4)")
                    
            create_stmt = f"CREATE TABLE quant_ml.feature_store ({', '.join(create_cols)});"
            await conn.execute(create_stmt)
            
            await conn.copy_records_to_table(
                'feature_store', schema_name='quant_ml',
                records=records_to_insert, columns=columns_to_save
            )

        await db.disconnect()
        logger.info("[DONE] A 'quant_ml.feature_store' está viva e pronta para o XGBoost.")

if __name__ == "__main__":
    builder = QuantMLBuilder()
    asyncio.run(builder.build_matrix())