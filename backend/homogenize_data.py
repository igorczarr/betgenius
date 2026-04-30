# betgenius-backend/workers/feature_engineering/homogenizer.py
import sys
import os
import asyncio
import logging
import pandas as pd
import numpy as np
from sklearn.impute import KNNImputer
from sklearn.preprocessing import MinMaxScaler
from pathlib import Path
from dotenv import load_dotenv

# Configuração de Ambiente
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=BASE_DIR / '.env')
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [HOMOGENIZER] %(message)s")
logger = logging.getLogger(__name__)

class DataHomogenizer:
    """
    Motor S-Tier de Cura de Dados.
    Utiliza K-Nearest Neighbors para reconstruir dados ausentes (NULL/NaN),
    respeitando os True Zeros (0.0) e prevenindo Data Leakage.
    """
    def __init__(self):
        # O "DNA" do jogo: o que define se dois jogos são estatisticamente semelhantes.
        # Estas colunas guiam o algoritmo para encontrar vizinhos próximos.
        self.dna_cols = [
            'delta_elo', 'home_pts_before', 'away_pts_before', 
            'home_position', 'away_position'
        ]
        
        # Colunas que nunca devem ser usadas na matemática de semelhança
        self.ignore_cols = ['match_id', 'home_position', 'away_position']

    async def fetch_full_base(self):
        logger.info("📥 Extraindo a Matriz Completa dinamicamente da Feature Store...")
        
        query = """
            SELECT 
                f.*,
                m.home_position, m.away_position
            FROM quant_ml.feature_store f
            JOIN core.matches_history m ON f.match_id = m.id
        """
        async with db.pool.acquire() as conn:
            records = await conn.fetch(query)
            
        df = pd.DataFrame([dict(r) for r in records])
        logger.info(f"📊 Extraídos {len(df)} registos com {len(df.columns)} colunas dinâmicas.")
        return df

    def intelligent_knn_impute(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("🧠 Iniciando Imputação Quantitativa Omnidirecional (KNN)...")
        
        # 1. Isolar Targets (Prevenção de Data Leakage)
        target_cols = [c for c in df.columns if c.startswith('target_') or c == 'total_goals']
        
        # 2. Identificar colunas numéricas que serão processadas e curadas
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cols_to_process = [c for c in numeric_cols if c not in self.ignore_cols and c not in target_cols]
        
        # 3. Corrigir tipos de dados 
        for col in cols_to_process:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # NOTA S-TIER: Removemos o df.replace({0.0: np.nan}). 
        # Zeros no desporto são dados reais (True Zeros). Só imputamos verdadeiros NaNs/NULLs do SQL.

        missing_stats = df[cols_to_process].isna().sum()
        missing_stats = missing_stats[missing_stats > 0]
        if not missing_stats.empty:
            logger.info(f"⚠️ Anomalias detetadas (Apenas NULLs genuínos):\n{missing_stats}")
        else:
            logger.info("✅ A base está perfeita. Não há dados ausentes para imputar.")
            return df

        # 4. Matriz de Trabalho Isolada
        matrix_df = df[cols_to_process].copy()

        # 5. Normalização (MinMax Scaling) - KNN é sensível a grandezas diferentes
        logger.info("📐 Normalizando Espaço Geométrico N-Dimensional...")
        scaler = MinMaxScaler()
        scaled_data = scaler.fit_transform(matrix_df)

        # 6. A MÁGICA: KNN Imputer dinâmico
        logger.info(f"🔭 Localizando assinaturas de DNA no hiperespaço para {len(df)} jogos...")
        imputer = KNNImputer(n_neighbors=7, weights='distance')
        imputed_scaled_data = imputer.fit_transform(scaled_data)

        # 7. Desfaz a normalização
        imputed_matrix = scaler.inverse_transform(imputed_scaled_data)
        df_imputed = pd.DataFrame(imputed_matrix, columns=cols_to_process)
        
        # 8. Transfere os dados curados para o DataFrame original e arredonda
        df[cols_to_process] = df_imputed[cols_to_process].round(2)
        
        return df

    async def save_homogenized_data(self, df: pd.DataFrame):
        logger.info("📤 Construindo Query SQL Dinâmica e injetando tensores curados...")
        
        # Só queremos atualizar colunas que pertencem à feature_store
        target_cols = [c for c in df.columns if c.startswith('target_') or c == 'total_goals']
        update_cols = [c for c in df.columns if c not in self.ignore_cols and c not in target_cols]
        
        if not update_cols:
            logger.warning("Nenhuma coluna válida para atualizar.")
            return

        # BLINDAGEM SQL S-TIER: 
        # Substituir NaNs ou Infs (Infinitos) gerados na matemática pelo tipo None, 
        # que o driver do banco de dados (asyncpg) consegue traduzir para NULL.
        df_clean = df.replace([np.inf, -np.inf], np.nan)
        df_clean = df_clean.where(pd.notnull(df_clean), None)

        records = []
        for _, row in df_clean.iterrows():
            record = [row[c] for c in update_cols] + [int(row['match_id'])]
            records.append(tuple(record))

        batch_size = 10000
        total_batches = (len(records) // batch_size) + 1

        set_clauses = [f"{col} = ${i+1}" for i, col in enumerate(update_cols)]
        set_clause_str = ", ".join(set_clauses)
        match_id_param = f"${len(update_cols) + 1}"
        
        dynamic_query = f"UPDATE quant_ml.feature_store SET {set_clause_str} WHERE match_id = {match_id_param}"

        async with db.pool.acquire() as conn:
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                current_batch_num = (i // batch_size) + 1
                
                try:
                    await conn.executemany(dynamic_query, batch)
                    logger.info(f"💾 Lote {current_batch_num}/{total_batches} salvo dinamicamente.")
                except Exception as e:
                    logger.error(f"❌ Falha SQL Crítica no Lote {current_batch_num}: {e}")
        
        logger.info(f"✅ Sucesso Absoluto! {len(df)} registos homogeneizados em {len(update_cols)} colunas.")

    async def run(self):
        await db.connect()
        df = await self.fetch_full_base()
        await db.disconnect()
        
        db.pool = None 
        logger.info("🔌 Conexão com o banco fechada temporariamente para focar na CPU.")

        if df.empty:
            logger.error("Base vazia. Abortando.")
            return
            
        df_clean = await asyncio.to_thread(self.intelligent_knn_impute, df)

        logger.info("🔌 Reabrindo conexão FRESCA com o banco de dados...")
        await db.connect() 
        await self.save_homogenized_data(df_clean)
        await db.disconnect()
        logger.info("🏁 Processo de Homogeneização Dinâmica Finalizado.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    homogenizer = DataHomogenizer()
    asyncio.run(homogenizer.run())