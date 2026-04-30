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
    O Liquidificador S-Tier (Genesis & Rolling Update).
    Funde todas as dimensões (Elo, Temporal, Contexto), calcula Deltas 
    e forja a 'quant_ml.feature_store'.
    """

    async def initialize_schema(self, conn):
        await conn.execute("CREATE SCHEMA IF NOT EXISTS quant_ml;")

    async def build_matrix(self):
        logger.info("[INIT] INICIANDO QUANT ML BUILDER: Forjando a Feature Store Histórica e Projetada.")
        await db.connect()
        
        try:
            async with db.pool.acquire() as conn:
                await self.initialize_schema(conn)
                
                logger.info("📥 Executando Super-JOIN interdimensional no Data Warehouse...")
                
                # A SINFONIA QUANTITATIVA: Trazemos todas as dimensões, agora com xG Shot e Momentum.
                # Removido: home_rest_days e away_rest_days por falta de profundidade de plantel.
                query = """
                    SELECT 
                        -- 1. DADOS BASE
                        m.id as match_id, m.sport_key, m.season, m.match_date, m.status,
                        m.home_team_id, m.away_team_id, m.home_goals, m.away_goals,
                        m.ht_home_goals, m.ht_away_goals, m.ht_result,
                        
                        -- 2. FÍSICA DO JOGO (Para curar NaNs de xG)
                        m.home_shots, m.away_shots, m.home_shots_target, m.away_shots_target,
                        m.home_corners, m.away_corners, 
                        m.home_yellow, m.away_yellow, m.home_red, m.away_red,
                        
                        -- 2.1 xG S-TIER (Bayesian, Shot & Momentum)
                        m.xg_shot_home, m.xg_shot_away, 
                        m.xg_momentum_home, m.xg_momentum_away,
                        m.proj_xg_shot_home, m.proj_xg_shot_away,
                        
                        -- 3. ODDS E MERCADO
                        m.closing_odd_home, m.closing_odd_draw, m.closing_odd_away,
                        m.odd_over_25, m.odd_under_25, m.odd_btts_yes, m.odd_btts_no,
                        m.pin_odd_home, m.pin_odd_draw, m.pin_odd_away,
                        m.pin_closing_home, m.pin_closing_draw, m.pin_closing_away,
                        
                        -- 4. O ELO GLOBAL (Motor 1)
                        eh.home_elo_before, eh.away_elo_before,
                        
                        -- 5. PEDIGREE E FOLHA SALARIAL
                        hp.league_tier, 
                        hp.avg_wage_percentile as home_wage_pct, 
                        ap.avg_wage_percentile as away_wage_pct,
                        
                        -- 6. O MOTOR TEMPORAL E TÁTICO (Motor 2)
                        t.home_xg_for_ewma_micro, t.home_xg_against_ewma_micro,
                        t.away_xg_for_ewma_micro, t.away_xg_against_ewma_micro,
                        t.home_xg_for_ewma_macro, t.away_xg_for_ewma_macro,
                        t.home_aggression_ewma, t.away_aggression_ewma,
                        
                        -- 7. O MOTOR DE CONTEXTO E PSICOLOGIA (Motor 3)
                        c.home_win_streak, c.away_win_streak,
                        c.home_winless_streak, c.away_winless_streak,
                        c.home_fraudulent_defense, c.away_fraudulent_defense,
                        c.home_fraudulent_attack, c.away_fraudulent_attack,
                        c.home_tension_index, c.away_tension_index,
                        c.home_market_respect, c.away_market_respect,
                        c.home_pts_before, c.away_pts_before,
                        c.pos_tabela_home, c.pos_tabela_away
                        
                    FROM core.matches_history m
                    LEFT JOIN core.match_elo_history eh ON m.id = eh.match_id
                    LEFT JOIN core.team_pedigree hp ON m.home_team_id = hp.team_id
                    LEFT JOIN core.team_pedigree ap ON m.away_team_id = ap.team_id
                    LEFT JOIN core.match_temporal_features t ON m.id = t.match_id
                    LEFT JOIN core.match_context_features c ON m.id = c.match_id
                    WHERE m.status IN ('FINISHED', 'SCHEDULED')
                    ORDER BY m.match_date ASC
                """
                
                matches = await conn.fetch(query)
                if not matches:
                    logger.error("❌ O Super-JOIN retornou vazio.")
                    return

                df = pd.DataFrame([dict(m) for m in matches])
                logger.info(f"🧬 Tensor Bruto extraído: {df.shape[0]} jogos processados. Conectado aos 3 Motores.")

                logger.info("📐 Calculando Diferenciais Numéricos S-Tier (Deltas)...")
                
                # Trata as novas métricas de xG, usando o xG Preditivo se o real não existir (SCHEDULED vs FINISHED)
                df['xg_shot_home_eff'] = df['xg_shot_home'].fillna(df['proj_xg_shot_home'])
                df['xg_shot_away_eff'] = df['xg_shot_away'].fillna(df['proj_xg_shot_away'])
                
                # Previne erros matemáticos com Nulos (Fallback para os valores baseados na nossa arquitetura)
                df = df.fillna({
                    'home_elo_before': 1500.0, 'away_elo_before': 1500.0,
                    'home_wage_pct': 0.5, 'away_wage_pct': 0.5,
                    'home_xg_for_ewma_micro': 1.35, 'away_xg_for_ewma_micro': 1.35,
                    'home_xg_for_ewma_macro': 1.35, 'away_xg_for_ewma_macro': 1.35,
                    'home_tension_index': 0.5, 'away_tension_index': 0.5,
                    'home_market_respect': 0.35, 'away_market_respect': 0.35,
                    'xg_shot_home_eff': 0.1, 'xg_shot_away_eff': 0.1,
                    'xg_momentum_home': 0.0, 'xg_momentum_away': 0.0
                }).infer_objects(copy=False)

                # OS DELTAS: É AQUI QUE O ALGORITMO APRENDE A COMPARAR AS EQUIPAS
                df['delta_elo'] = df['home_elo_before'] - df['away_elo_before']
                df['delta_wage_pct'] = df['home_wage_pct'] - df['away_wage_pct']
                df['delta_pontos'] = df['home_pts_before'] - df['away_pts_before']
                df['delta_posicao'] = df['pos_tabela_away'] - df['pos_tabela_home']
                df['delta_market_respect'] = df['home_market_respect'] - df['away_market_respect']
                df['delta_tension'] = df['home_tension_index'] - df['away_tension_index']
                df['delta_xg_micro'] = df['home_xg_for_ewma_micro'] - df['away_xg_for_ewma_micro']
                df['delta_xg_macro'] = df['home_xg_for_ewma_macro'] - df['away_xg_for_ewma_macro']
                
                # DELTAS DE xG AVANÇADOS (Novo Padrão S-Tier)
                df['delta_xg_shot_eff'] = df['xg_shot_home_eff'] - df['xg_shot_away_eff']
                df['delta_xg_momentum'] = df['xg_momentum_home'] - df['xg_momentum_away']

                logger.info("🎯 Gerando Variáveis Alvo (Targets) para Machine Learning...")
                finished = df['status'] == 'FINISHED'
                
                # Prepara o Target para 1X2, Golos e BTTS (Para o Alpha, Beta e Gamma)
                df['target_match_result'] = np.where(finished, np.where(df['home_goals'] > df['away_goals'], 2, np.where(df['home_goals'] < df['away_goals'], 0, 1)), -1)
                df['target_ht_result'] = np.where(finished, np.where(df['ht_home_goals'] > df['ht_away_goals'], 2, np.where(df['ht_home_goals'] < df['ht_away_goals'], 0, 1)), -1)
                
                # Golos e Derivados
                df['total_goals'] = df['home_goals'] + df['away_goals']
                df['target_over_25'] = np.where(finished, (df['total_goals'] > 2.5).astype(int), -1)
                df['target_btts'] = np.where(finished, ((df['home_goals'] > 0) & (df['away_goals'] > 0)).astype(int), -1)
                
                # Eventos para Props
                df['target_total_corners'] = np.where(finished, df['home_corners'] + df['away_corners'], -1)
                df['target_total_shots'] = np.where(finished, df['home_shots'] + df['away_shots'], -1)
                df['target_total_cards'] = np.where(finished, df['home_yellow'] + df['away_yellow'] + (df['home_red'] * 2) + (df['away_red'] * 2), -1)

                # =========================================================
                # 🛡️ BLINDAGEM S-TIER: O Escudo Anti "God-Edge"
                # Remove Odds corrompidas ou surreais que destroem o Kelly Criterion
                # =========================================================
                logger.info("🛡️ Aplicando Escudo Anti God-Edge nas Odds de Mercado...")
                odds_cols = [
                    'closing_odd_home', 'closing_odd_draw', 'closing_odd_away',
                    'odd_over_25', 'odd_under_25', 'odd_btts_yes', 'odd_btts_no',
                    'pin_odd_home', 'pin_odd_draw', 'pin_odd_away',
                    'pin_closing_home', 'pin_closing_draw', 'pin_closing_away'
                ]
                for odd_col in odds_cols:
                    if odd_col in df.columns:
                        # Se a odd for menor que 1.05 (impossível) ou maior que 25.0 (irreal / lotaria), neutraliza para 0.0
                        df[odd_col] = np.where((df[odd_col] < 1.05) | (df[odd_col] > 25.0), 0.0, df[odd_col])

                # Garante que não existem nulos remanescentes (as odds bloqueadas ficam a 0.0 e são ignoradas pelos Oráculos)
                df = df.fillna(0.0)

                # Limpeza de features em excesso
                cols_to_drop = ['xg_shot_home', 'xg_shot_away', 'proj_xg_shot_home', 'proj_xg_shot_away']
                df = df.drop(columns=cols_to_drop, errors='ignore')

                # =========================================================
                # MODO GÊNESIS SEGURO (DYNAMIC SCHEMA EVOLUTION)
                # =========================================================
                is_genesis = os.getenv("GENESIS_MODE", "False") == "True"
                if is_genesis:
                    logger.warning("⚠️ MODO GÊNESIS ATIVADO: Atualização massiva ativada (Sem apagar a tabela).")
                    cutoff_date = pd.Timestamp('2010-01-01')
                    # O COMANDO DESTRUTIVO (DROP/TRUNCATE) FOI BANIDO DESTA ARQUITETURA.
                else:
                    cutoff_date = pd.Timestamp(datetime.now().date() - timedelta(days=7))
                
                df['match_date_pd'] = pd.to_datetime(df['match_date'])
                df_to_save = df[df['match_date_pd'] >= cutoff_date].copy()
                df_to_save.drop(columns=['match_date_pd', 'status', 'total_goals'], inplace=True, errors='ignore')
                
                columns_to_save = list(df_to_save.columns)
                
                # 1. Cria a Tabela Dinamicamente
                create_cols = []
                for col in columns_to_save:
                    if col == 'match_id': create_cols.append(f"{col} INTEGER PRIMARY KEY")
                    elif 'date' in col: create_cols.append(f"{col} DATE")
                    elif 'sport_key' in col or 'season' in col or col == 'ht_result': create_cols.append(f"{col} VARCHAR(50)")
                    elif 'target_' in col or 'pos_tabela' in col or 'rodada' in col or 'days' in col: create_cols.append(f"{col} SMALLINT")
                    else: create_cols.append(f"{col} NUMERIC(8,4)")
                        
                create_stmt = f"CREATE TABLE IF NOT EXISTS quant_ml.feature_store ({', '.join(create_cols)});"
                await conn.execute(create_stmt)

                # =====================================================================
                # DYNAMIC SCHEMA EVOLUTION
                # =====================================================================
                logger.info("🛡️ Sincronizando Schema dinamicamente para adicionar novas colunas...")
                for col in columns_to_save:
                    if col == 'match_id': continue
                    
                    if 'date' in col: col_type = "DATE"
                    elif 'sport_key' in col or 'season' in col or col == 'ht_result': col_type = "VARCHAR(50)"
                    elif 'target_' in col or 'pos_tabela' in col or 'rodada' in col or 'days' in col: col_type = "SMALLINT"
                    else: col_type = "NUMERIC(8,4)"
                    
                    try:
                        await conn.execute(f"ALTER TABLE quant_ml.feature_store ADD COLUMN IF NOT EXISTS {col} {col_type};")
                    except Exception as e:
                        logger.error(f"Erro ao adicionar coluna {col}: {e}")
                # =====================================================================

                # 2. Prepara o UPSERT
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
                        elif 'target_' in col or 'pos_tabela' in col or 'rodada' in col or 'days' in col: record.append(int(val))
                        else: record.append(float(val))
                    records_to_upsert.append(tuple(record))

                # 3. CHUNKING: Injeta na Matriz Final
                if records_to_upsert:
                    cols_str = ", ".join(columns_to_save)
                    vals_str = ", ".join([f"${i+1}" for i in range(len(columns_to_save))])
                    updates_str = ", ".join([f"{c} = EXCLUDED.{c}" for c in columns_to_save if c != 'match_id'])
                    
                    upsert_query = f"""
                        INSERT INTO quant_ml.feature_store ({cols_str}) 
                        VALUES ({vals_str})
                        ON CONFLICT (match_id) DO UPDATE SET {updates_str};
                    """
                    
                    batch_size = 10000
                    total_batches = (len(records_to_upsert) // batch_size) + 1
                    
                    logger.info(f"💾 Guardando a Feature Store: {len(records_to_upsert)} Tensores em {total_batches} Blocos.")
                    
                    for i in range(0, len(records_to_upsert), batch_size):
                        batch = records_to_upsert[i:i + batch_size]
                        try:
                            await conn.executemany(upsert_query, batch)
                            logger.info(f"   └ Bloco {(i//batch_size)+1}/{total_batches} Integrado à Matriz.")
                        except Exception as e:
                            logger.error(f"❌ Falha Crítica no Lote {(i//batch_size)+1}: {e}")
                    
                    logger.info("✅ LIQUIDIFICADOR CONCLUÍDO. A Base para a Inteligência Artificial está pronta.")
                else:
                    logger.info("ℹ️ Nenhuma nova feature precisou ser gravada.")

        finally:
            await db.disconnect()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    builder = QuantMLBuilder()
    asyncio.run(builder.build_matrix())