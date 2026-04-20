# betgenius-backend/workers/feature_engineering/matrix_builder.py

import asyncio
import logging
import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# =====================================================================
# BLINDAGEM DE ENCODING PARA WINDOWS E .ENV
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [MATRIX-BUILDER] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class QuantMLBuilder:
    """
    O Liquidificador S-Tier.
    Funde todas as dimensões, calcula a Classificação Histórica (Standings)
    sem data-leakage, e forja a 'quant_ml.feature_store' para o XGBoost.
    """

    async def initialize_schema(self, conn):
        # Proteção e apontamento para o schema correto de ML
        await conn.execute("CREATE SCHEMA IF NOT EXISTS quant_ml;")
        await conn.execute("DROP TABLE IF EXISTS quant_ml.feature_store CASCADE;")
        # A tabela será recriada nativamente pelo Pandas na gravação

    def _calculate_standings_and_points(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula Rodada, Pontos e Classificação ANTES da bola rolar.
        Prevenção 100% contra Data Leakage.
        """
        logger.info("📊 Mapeando Dinâmica de Campeonato (Pontos, Saldo de Gols e Posição)...")
        
        # 1. Calcula os pontos e saldo ganhos na partida
        df['home_pts_earned'] = np.where(df['home_goals'] > df['away_goals'], 3, np.where(df['home_goals'] == df['away_goals'], 1, 0))
        df['away_pts_earned'] = np.where(df['away_goals'] > df['home_goals'], 3, np.where(df['home_goals'] == df['away_goals'], 1, 0))
        
        df['home_gd_earned'] = df['home_goals'] - df['away_goals']
        df['away_gd_earned'] = df['away_goals'] - df['home_goals']

        # 2. Desmembra o df para a visão "Por Time"
        home_df = df[['match_id', 'match_date', 'sport_key', 'season', 'home_team_id', 'home_pts_earned', 'home_gd_earned']].copy()
        home_df.columns = ['match_id', 'date', 'league', 'season', 'team_id', 'pts_earned', 'gd_earned']
        home_df['is_home'] = 1

        away_df = df[['match_id', 'match_date', 'sport_key', 'season', 'away_team_id', 'away_pts_earned', 'away_gd_earned']].copy()
        away_df.columns = ['match_id', 'date', 'league', 'season', 'team_id', 'pts_earned', 'gd_earned']
        away_df['is_home'] = 0

        # Junta e ordena cronologicamente
        teams_timeline = pd.concat([home_df, away_df]).sort_values(by=['date', 'match_id']).reset_index(drop=True)

        # 3. O SEGREDO: shift(1) garante que somamos os pontos ATÉ o jogo passado!
        # fillna(0) para o primeiro jogo do campeonato.
        grouped = teams_timeline.groupby(['league', 'season', 'team_id'])
        
        teams_timeline['cum_pts'] = grouped['pts_earned'].transform(lambda x: x.shift(1).cumsum().fillna(0))
        teams_timeline['cum_gd'] = grouped['gd_earned'].transform(lambda x: x.shift(1).cumsum().fillna(0))
        
        # A Rodada é simplesmente a contagem cumulativa de jogos + 1 (pois cumcount começa em 0)
        teams_timeline['rodada'] = grouped.cumcount() + 1

        # 4. Cálculo de Classificação (Posição na Tabela)
        # Ordenamos pelo desempenho ATÉ a rodada atual
        teams_timeline.sort_values(by=['league', 'season', 'rodada', 'cum_pts', 'cum_gd'], 
                                   ascending=[True, True, True, False, False], inplace=True)
        
        # Atribui a posição no campeonato (1º, 2º, 3º...)
        teams_timeline['pos_tabela'] = teams_timeline.groupby(['league', 'season', 'rodada']).cumcount() + 1

        # 5. Retorna as métricas para o DataFrame original em Home e Away
        home_feats = teams_timeline[teams_timeline['is_home'] == 1][['match_id', 'rodada', 'cum_pts', 'pos_tabela']]
        home_feats.columns = ['match_id', 'rodada', 'home_pts_before', 'pos_tabela_home']

        away_feats = teams_timeline[teams_timeline['is_home'] == 0][['match_id', 'cum_pts', 'pos_tabela']]
        away_feats.columns = ['match_id', 'away_pts_before', 'pos_tabela_away']

        df = df.merge(home_feats, on='match_id', how='left')
        df = df.merge(away_feats, on='match_id', how='left')

        # Limpa as colunas auxiliares
        df.drop(columns=['home_pts_earned', 'away_pts_earned', 'home_gd_earned', 'away_gd_earned'], inplace=True)
        return df

    async def build_matrix(self):
        logger.info("[INIT] INICIANDO QUANT ML BUILDER: Forjando a Tabela Definitiva (Feature Store).")
        await db.connect()
        
        async with db.pool.acquire() as conn:
            await self.initialize_schema(conn)
            
            logger.info("📥 Executando Super-JOIN interdimensional no Data Warehouse...")
            
            # NOTA: O JOIN abaixo pressupõe que as tabelas de engenharia de features 
            # (match_temporal_features, match_psychology_features) já foram populadas.
            # Se você ainda não rodou os outros motores de engenharia, o JOIN retornará vazio.
            # Estamos usando LEFT JOIN baseando na matches_history para não perdermos dados se uma tabela estiver vazia.
            
            query = """
                SELECT 
                    -- IDENTIFICADORES E DADOS BASE
                    m.id as match_id, m.sport_key, m.season, m.match_date, 
                    m.home_team_id, m.away_team_id, m.home_goals, m.away_goals,
                    m.closing_odd_home, m.closing_odd_draw, m.closing_odd_away,
                    m.xg_home, m.xg_away,
                    
                    -- DIMENSÃO: ELO CRU E PPDA (Da nova Alpha Matrix crua)
                    am.home_elo_before, am.away_elo_before, am.home_ppda, am.away_ppda,
                    
                    -- DIMENSÃO: PEDIGREE E RIQUEZA
                    hp.league_tier, hp.avg_wage_percentile as home_wage_pct, ap.avg_wage_percentile as away_wage_pct,
                    
                    -- DIMENSÃO: TEMPORAL (Se Existir)
                    t.home_rest_days, t.away_rest_days,
                    t.home_xg_for_ewma_micro, t.home_xg_against_ewma_micro,
                    t.away_xg_for_ewma_micro, t.away_xg_against_ewma_micro,
                    
                    -- DIMENSÃO: PSICOLOGIA E FRAUDES (Se Existir)
                    p.home_win_streak, p.home_winless_streak, p.home_clean_sheet_streak,
                    p.home_fraudulent_defense, p.home_fraudulent_attack,
                    p.away_win_streak, p.away_winless_streak, p.away_clean_sheet_streak,
                    p.away_fraudulent_defense, p.away_fraudulent_attack,
                    
                    -- DIMENSÃO: MARKET RESPECT (Se Existir)
                    mk.home_market_respect, mk.away_market_respect
                    
                FROM core.matches_history m
                LEFT JOIN core.alpha_matrix am ON m.id = am.match_id
                LEFT JOIN core.team_pedigree hp ON m.home_team_id = hp.team_id
                LEFT JOIN core.team_pedigree ap ON m.away_team_id = ap.team_id
                LEFT JOIN core.match_temporal_features t ON m.id = t.match_id
                LEFT JOIN core.match_psychology_features p ON m.id = p.match_id
                LEFT JOIN core.match_market_features mk ON m.id = mk.match_id
                
                WHERE m.closing_odd_home > 0 AND m.closing_odd_away > 0
                AND m.home_goals IS NOT NULL AND m.away_goals IS NOT NULL
                ORDER BY m.match_date ASC
            """
            
            matches = await conn.fetch(query)
            if not matches:
                logger.error("❌ O Super-JOIN retornou vazio. Garanta que o Backfill carregou as Odds e os Gols.")
                await db.disconnect()
                return

            df = pd.DataFrame([dict(m) for m in matches])
            logger.info(f"🧬 Tensor Bruto extraído: {df.shape[0]} jogos e {df.shape[1]} features originais.")

            # ==========================================
            # ENGENHARIA DE PONTOS E TABELA (NOVA FUNÇÃO)
            # ==========================================
            df = self._calculate_standings_and_points(df)

            # ==========================================
            # ENGENHARIA DE DELTAS (DIFERENCIAIS)
            # ==========================================
            logger.info("📐 Calculando Diferenciais Numéricos (Deltas)...")
            
            # Garantimos que None (Nulos do Left Join) sejam 0 para a matemática não quebrar
            df = df.fillna(0)

            df['delta_elo'] = df['home_elo_before'] - df['away_elo_before']
            df['delta_wage_pct'] = df['home_wage_pct'] - df['away_wage_pct']
            df['delta_pontos'] = df['home_pts_before'] - df['away_pts_before']
            df['delta_posicao'] = df['pos_tabela_away'] - df['pos_tabela_home'] # Invertido, pois pos 1 é melhor que 20

            # Diferença de Respeito do Mercado
            df['delta_market_respect'] = df['home_market_respect'] - df['away_market_respect']

            # ==========================================
            # TARGET ENGINEERING (As Respostas para a IA)
            # ==========================================
            logger.info("🎯 Gerando Variáveis Alvo (Targets) para Classificação Binária...")
            
            df['target_home_win'] = (df['home_goals'] > df['away_goals']).astype(int)
            df['target_draw'] = (df['home_goals'] == df['away_goals']).astype(int)
            df['target_away_win'] = (df['home_goals'] < df['away_goals']).astype(int)
            
            df['total_goals'] = df['home_goals'] + df['away_goals']
            df['target_over_15'] = (df['total_goals'] > 1.5).astype(int)
            df['target_over_25'] = (df['total_goals'] > 2.5).astype(int)
            df['target_over_35'] = (df['total_goals'] > 3.5).astype(int)
            df['target_btts'] = ((df['home_goals'] > 0) & (df['away_goals'] > 0)).astype(int)

            bool_cols = [c for c in df.columns if 'fraudulent' in c]
            for col in bool_cols:
                df[col] = df[col].astype(int)

            # Define flag se o jogo já foi processado pelo modelo (para o pipeline em real-time futuramente)
            df['is_processed'] = True

            # ==========================================
            # SALVAMENTO NA QUANT_ML.FEATURE_STORE
            # ==========================================
            logger.info(f"💾 Injetando Machine Learning Matrix ({df.shape[1]} colunas) no Data Warehouse...")
            
            columns_to_save = list(df.columns)
            records_to_insert = [tuple(x) for x in df.to_numpy()]
            
            create_cols = []
            for col in columns_to_save:
                if 'match_id' in col: create_cols.append(f"{col} VARCHAR(50) PRIMARY KEY") # Casting para VARCHAR pro seu schema
                elif 'date' in col: create_cols.append(f"{col} DATE")
                elif 'sport_key' in col or 'season' in col: create_cols.append(f"{col} VARCHAR(50)")
                elif 'target_' in col or 'pos_tabela' in col or 'rodada' in col or df[col].dtype in ['int32', 'int64', 'bool']: 
                    create_cols.append(f"{col} SMALLINT")
                else: 
                    create_cols.append(f"{col} NUMERIC(8,4)")
                    
            create_stmt = f"CREATE TABLE quant_ml.feature_store ({', '.join(create_cols)}, created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW());"
            await conn.execute(create_stmt)
            
            await conn.copy_records_to_table(
                'feature_store', schema_name='quant_ml',
                records=records_to_insert,
                columns=columns_to_save
            )

        await db.disconnect()
        logger.info("[DONE] LIQUIDIFICADOR CONCLUÍDO. A 'quant_ml.feature_store' está viva e pronta para o Scikit-Learn/XGBoost.")

if __name__ == "__main__":
    builder = QuantMLBuilder()
    asyncio.run(builder.build_matrix())