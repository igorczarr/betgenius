# betgenius-backend/workers/feature_engineering/matrix_builder.py

import asyncio
import logging
import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Suprime o FutureWarning do Pandas 3.0
pd.set_option('future.no_silent_downcasting', True)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [MATRIX-BUILDER] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class QuantMLBuilder:
    """
    O Liquidificador S-Tier (Rolling Update).
    Funde todas as dimensões, calcula Deltas e forja a 'quant_ml.feature_store'.
    Prepara os dados do passado (Treino) e injeta o futuro (Inferência).
    """

    async def initialize_schema(self, conn):
        await conn.execute("CREATE SCHEMA IF NOT EXISTS quant_ml;")
        # Removido o DROP TABLE CASCADE para permitir o Upsert Contínuo.

    def _calculate_standings_and_points(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("📊 Mapeando Dinâmica de Campeonato (Pontos e Posição)...")
        
        # Só ganha pontos e saldo se o jogo JÁ FOI FINALIZADO
        finished = df['status'] == 'FINISHED'
        
        df['home_pts_earned'] = np.where(finished & (df['home_goals'] > df['away_goals']), 3, np.where(finished & (df['home_goals'] == df['away_goals']), 1, 0))
        df['away_pts_earned'] = np.where(finished & (df['away_goals'] > df['home_goals']), 3, np.where(finished & (df['home_goals'] == df['away_goals']), 1, 0))
        
        df['home_gd_earned'] = np.where(finished, df['home_goals'] - df['away_goals'], 0)
        df['away_gd_earned'] = np.where(finished, df['away_goals'] - df['home_goals'], 0)

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
        logger.info("[INIT] INICIANDO QUANT ML BUILDER: Forjando a Feature Store.")
        await db.connect()
        
        async with db.pool.acquire() as conn:
            await self.initialize_schema(conn)
            
            logger.info("📥 Executando Super-JOIN interdimensional no Data Warehouse...")
            
            # ATUALIZADO: Inclui SCHEDULED e protege os Nulos
            query = """
                SELECT 
                    -- DADOS BASE
                    m.id as match_id, m.sport_key, m.season, m.match_date, m.status,
                    m.home_team_id, m.away_team_id, m.home_goals, m.away_goals,
                    m.ht_home_goals, m.ht_away_goals, m.ht_result,
                    
                    -- FÍSICA DO JOGO
                    m.home_shots, m.away_shots, m.home_shots_target, m.away_shots_target,
                    m.home_corners, m.away_corners, 
                    m.home_yellow, m.away_yellow, m.home_red, m.away_red,
                    
                    -- ODDS BET365 E PINNACLE
                    m.closing_odd_home, m.closing_odd_draw, m.closing_odd_away,
                    m.odd_over_25, m.odd_under_25, m.odd_btts_yes, m.odd_btts_no,
                    m.pin_odd_home, m.pin_odd_draw, m.pin_odd_away,
                    m.pin_closing_home, m.pin_closing_draw, m.pin_closing_away,
                    
                    -- ASIAN HANDICAP
                    m.ah_line, m.pin_ah_home, m.pin_ah_away, 
                    m.pin_closing_ah_home, m.pin_closing_ah_away,
                    
                    -- DIMENSÃO: ELO CRU
                    eh.home_elo_before, eh.away_elo_before,
                    
                    -- DIMENSÃO: PEDIGREE E RIQUEZA
                    hp.league_tier, hp.avg_wage_percentile as home_wage_pct, ap.avg_wage_percentile as away_wage_pct,
                    
                    -- DIMENSÃO: TEMPORAL (XG e Aggression)
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

                    -- DIMENSÃO: TENSÃO
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
                AND m.status IN ('FINISHED', 'SCHEDULED')
                ORDER BY m.match_date ASC
            """
            
            matches = await conn.fetch(query)
            if not matches:
                logger.error("❌ O Super-JOIN retornou vazio.")
                await db.disconnect()
                return

            df = pd.DataFrame([dict(m) for m in matches])
            logger.info(f"🧬 Tensor Bruto extraído: {df.shape[0]} jogos processados.")

            df = self._calculate_standings_and_points(df)

            logger.info("📐 Calculando Diferenciais Numéricos (Deltas)...")
            df = df.fillna(0).infer_objects(copy=False)

            df['delta_elo'] = df['home_elo_before'] - df['away_elo_before']
            df['delta_wage_pct'] = df['home_wage_pct'] - df['away_wage_pct']
            df['delta_pontos'] = df['home_pts_before'] - df['away_pts_before']
            df['delta_posicao'] = df['pos_tabela_away'] - df['pos_tabela_home']
            df['delta_market_respect'] = df['home_market_respect'] - df['away_market_respect']
            df['delta_tension'] = df['home_tension_index'] - df['away_tension_index']
            df['delta_xg_micro'] = df['home_xg_for_ewma_micro'] - df['away_xg_for_ewma_micro']
            df['delta_xg_macro'] = df['home_xg_for_ewma_macro'] - df['away_xg_for_ewma_macro']

            logger.info("🎯 Gerando Variáveis Alvo (Targets) - Escondendo o Futuro...")
            finished = df['status'] == 'FINISHED'
            
            df['target_match_result'] = np.where(finished, np.where(df['home_goals'] > df['away_goals'], 2, np.where(df['home_goals'] < df['away_goals'], 0, 1)), -1)
            df['target_ht_result'] = np.where(finished, np.where(df['ht_home_goals'] > df['ht_away_goals'], 2, np.where(df['ht_home_goals'] < df['ht_away_goals'], 0, 1)), -1)
            df['total_goals'] = df['home_goals'] + df['away_goals']
            df['target_over_25'] = np.where(finished, (df['total_goals'] > 2.5).astype(int), -1)
            df['target_btts'] = np.where(finished, ((df['home_goals'] > 0) & (df['away_goals'] > 0)).astype(int), -1)

            df['target_total_corners'] = np.where(finished, df['home_corners'] + df['away_corners'], -1)
            df['target_total_shots'] = np.where(finished, df['home_shots'] + df['away_shots'], -1)
            df['target_total_cards'] = np.where(finished, df['home_yellow'] + df['away_yellow'] + (df['home_red'] * 2) + (df['away_red'] * 2), -1)

            bool_cols = [c for c in df.columns if 'fraudulent' in c]
            for col in bool_cols: df[col] = df[col].astype(int)

            logger.info(f"💾 Injetando Machine Learning Matrix ({df.shape[1]} colunas)...")
            
            # Filtro para atualizar apenas dados dos últimos 7 dias e futuro
            cutoff_date = pd.Timestamp(datetime.now().date() - timedelta(days=7))
            df['match_date_pd'] = pd.to_datetime(df['match_date'])
            df_to_save = df[df['match_date_pd'] >= cutoff_date].copy()
            df_to_save.drop(columns=['match_date_pd', 'status', 'total_goals'], inplace=True, errors='ignore')
            
            columns_to_save = list(df_to_save.columns)
            
            # 1. Cria a Tabela se não existir
            create_cols = []
            for col in columns_to_save:
                if col == 'match_id': create_cols.append(f"{col} INTEGER PRIMARY KEY")
                elif 'date' in col: create_cols.append(f"{col} DATE")
                elif 'sport_key' in col or 'season' in col or col == 'ht_result': create_cols.append(f"{col} VARCHAR(50)")
                elif 'target_' in col or 'pos_tabela' in col or 'rodada' in col: create_cols.append(f"{col} SMALLINT")
                else: create_cols.append(f"{col} NUMERIC(8,4)")
                    
            create_stmt = f"CREATE TABLE IF NOT EXISTS quant_ml.feature_store ({', '.join(create_cols)});"
            await conn.execute(create_stmt)

            # 2. Formata os dados para UPSERT
            records_to_upsert = []
            for _, row in df_to_save.iterrows():
                record = []
                for col in columns_to_save:
                    val = row[col]
                    if col == 'match_id': record.append(int(val))
                    elif 'date' in col:
                        if isinstance(val, pd.Timestamp): record.append(val.date())
                        elif isinstance(val, str): record.append(pd.to_datetime(val).date())
                        else: record.append(val)
                    elif 'sport_key' in col or 'season' in col or col == 'ht_result': record.append(str(val))
                    elif 'target_' in col or 'pos_tabela' in col or 'rodada' in col: record.append(int(val))
                    else: record.append(float(val))
                records_to_upsert.append(tuple(record))

            if records_to_upsert:
                # Constroi a Query de UPSERT Dinâmica
                cols_str = ", ".join(columns_to_save)
                vals_str = ", ".join([f"${i+1}" for i in range(len(columns_to_save))])
                updates_str = ", ".join([f"{c} = EXCLUDED.{c}" for c in columns_to_save if c != 'match_id'])
                
                upsert_query = f"""
                    INSERT INTO quant_ml.feature_store ({cols_str}) 
                    VALUES ({vals_str})
                    ON CONFLICT (match_id) DO UPDATE SET {updates_str};
                """
                
                try:
                    await conn.executemany(upsert_query, records_to_upsert)
                    logger.info(f"✅ UPSERT executado com sucesso em {len(records_to_upsert)} jogos ativos/futuros.")
                except Exception as e:
                    logger.error(f"❌ Falha no UPSERT da Feature Store: {e}")
            else:
                logger.info("ℹ️ Nenhuma nova feature precisou ser gravada hoje.")

        await db.disconnect()
        logger.info("[DONE] A 'quant_ml.feature_store' está atualizada e pronta para Inferência.")

if __name__ == "__main__":
    builder = QuantMLBuilder()
    asyncio.run(builder.build_matrix())