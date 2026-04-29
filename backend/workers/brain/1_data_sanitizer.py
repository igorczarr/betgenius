# betgenius-backend/brain/1_data_sanitizer.py
import sys
import os
import io

# Blindagem
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
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

pd.set_option('future.no_silent_downcasting', True)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SANITIZER] %(message)s")
logger = logging.getLogger(__name__)

class DataSanitizer:
    """
    Guardião do Cérebro Preditivo.
    Puxa a Feature Store, identifica anomalias (como xG = 0.0), 
    aplica Imputação Bayesiana/Média Global e cria os tensores puros.
    """
    def __init__(self):
        self.output_dir = Path(__file__).parent / "data_vault"
        self.output_dir.mkdir(exist_ok=True)
        
        # O xG Médio Global do Futebol (usado como fallback para times sem dados)
        self.GLOBAL_XG_MEAN = 1.35
        self.GLOBAL_AGGRESSION_MEAN = 11.5

    async def extract_raw_data(self):
        logger.info("📡 Extraindo Feature Store bruta do Banco de Dados...")
        await db.connect()
        df = pd.DataFrame()
        try:
            async with db.pool.acquire() as conn:
                records = await conn.fetch("SELECT * FROM quant_ml.feature_store ORDER BY match_date ASC")
                if records:
                    df = pd.DataFrame([dict(r) for r in records])
        finally:
            await db.disconnect()
        return df

    def heal_and_engineer(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info(f"🩺 Iniciando Cirurgia de Dados em {len(df)} partidas...")

        # 1. Filtro Vital: Só queremos jogos que terminaram e têm placar
        df = df[df['home_goals'].notna() & df['away_goals'].notna()].copy()

        # 2. Conversão de Tipos Absoluta
        numeric_cols = [c for c in df.columns if c not in ['match_id', 'sport_key', 'season', 'match_date']]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 3. A CURA DOS DADOS (O problema do xG = 0.20)
        # Se o EWMA for menor que 0.30, é matematicamente quase impossível numa média longa. É falha de dados.
        xg_columns = [
            'home_xg_for_ewma_micro', 'home_xg_against_ewma_micro',
            'away_xg_for_ewma_micro', 'away_xg_against_ewma_micro',
            'home_xg_for_ewma_macro', 'away_xg_for_ewma_macro'
        ]
        for col in xg_columns:
            # Substitui lixo (0.00 ou próximo a isso) pela média histórica aceitável
            mask = df[col] < 0.30
            df.loc[mask, col] = np.nan
            # Preenche com a média do campeonato ou média global
            df[col] = df[col].fillna(df.groupby('sport_key')[col].transform('mean'))
            df[col] = df[col].fillna(self.GLOBAL_XG_MEAN)

        agg_cols = ['home_aggression_ewma', 'away_aggression_ewma']
        for col in agg_cols:
            mask = df[col] < 3.0
            df.loc[mask, col] = np.nan
            df[col] = df[col].fillna(self.GLOBAL_AGGRESSION_MEAN)

        # 4. ENGENHARIA DE DELTAS (Agora com dados limpos)
        logger.info("📐 Criando Diferenciais Numéricos (Deltas Puros)...")
        df['delta_elo'] = df['home_elo_before'] - df['away_elo_before']
        df['delta_pontos'] = df['home_pts_before'] - df['away_pts_before']
        df['delta_posicao'] = df['pos_tabela_away'] - df['pos_tabela_home']
        
        # Deltas de xG curados
        df['delta_xg_micro'] = df['home_xg_for_ewma_micro'] - df['away_xg_for_ewma_micro']
        df['delta_xg_macro'] = df['home_xg_for_ewma_macro'] - df['away_xg_for_ewma_macro']
        df['delta_aggression'] = df['home_aggression_ewma'] - df['away_aggression_ewma']

        # Garante que não existem NaNs soltos
        df = df.fillna(0).infer_objects(copy=False)

        # Remove jogos amadores / erros de raspagem de odds
        df = df[(df['closing_odd_home'] > 1.0) & (df['closing_odd_away'] > 1.0)]

        logger.info("✅ Dados higienizados. A anomalia do xG foi neutralizada.")
        return df

    def save_vault(self, df: pd.DataFrame):
        """Salva os tensores purificados fisicamente para acelerar os treinos seguintes."""
        # Usa Parquet para eficiência e preservação estrita de tipagem
        vault_path = self.output_dir / "purified_tensors.parquet"
        df.to_parquet(vault_path, index=False)
        logger.info(f"💾 Cofre de Dados fechado: {vault_path} ({len(df)} jogos, {len(df.columns)} features)")

    async def run(self):
        df_raw = await self.extract_raw_data()
        if df_raw.empty:
            logger.error("Sem dados no DB.")
            return
        df_clean = self.heal_and_engineer(df_raw)
        self.save_vault(df_clean)

if __name__ == "__main__":
    asyncio.run(DataSanitizer().run())