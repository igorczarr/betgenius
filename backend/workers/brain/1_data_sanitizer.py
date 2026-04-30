# betgenius-backend/workers/brain/1_data_sanitizer.py
import sys
import os
import asyncio
import logging
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# =====================================================================
# BLINDAGEM DE ENCODING E CONFIGURAÇÃO
# =====================================================================
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

pd.set_option('future.no_silent_downcasting', True)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SANITIZER] %(message)s")
logger = logging.getLogger(__name__)

class DataSanitizer:
    """
    Guardião do Cérebro Preditivo S-Tier (Genesis Update).
    Puxa a Feature Store Master, integra as Odds de Fechamento da Pinnacle,
    garante a qualidade absoluta dos dados e gera os Tensores Puros (Parquet).
    """
    def __init__(self):
        self.output_dir = Path(__file__).parent / "data_vault"
        self.output_dir.mkdir(exist_ok=True)

    async def extract_raw_data(self):
        """
        Extrai todos os Tensores da Feature Store, juntando os Targets Reais 
        (Gols em casa/fora) e os Fatos do Mercado (Closing Odds).
        """
        logger.info("📡 Extraindo Feature Store Master e Targets do Banco de Dados...")
        await db.connect()
        df = pd.DataFrame()
        try:
            # Selecionamos todas as colunas valiosas da feature_store e os resultados de matches_history
            query = """
                SELECT 
                    f.*, 
                    m.home_goals, m.away_goals, m.match_date, m.sport_key,
                    m.closing_odd_home, m.closing_odd_draw, m.closing_odd_away,
                    m.pin_odd_home, m.pin_odd_draw, m.pin_odd_away,
                    m.odd_over_25, m.odd_under_25,
                    m.odd_btts_yes, m.odd_btts_no
                FROM quant_ml.feature_store f
                JOIN core.matches_history m ON f.match_id = m.id
                WHERE m.status = 'FINISHED'
                ORDER BY m.match_date ASC
            """
            async with db.pool.acquire() as conn:
                records = await conn.fetch(query)
                if records:
                    df = pd.DataFrame([dict(r) for r in records])
        except Exception as e:
            logger.error(f"Erro na extração: {e}")
        finally:
            await db.disconnect()
            
        return df

    def heal_and_engineer(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica a lógica Quant de verificação de qualidade dos tensores.
        """
        logger.info(f"🩺 Iniciando Verificação de Qualidade em {len(df)} partidas...")

        # 1. Filtro Vital: Só queremos jogos que terminaram e têm placar validado
        df = df[df['home_goals'].notna() & df['away_goals'].notna()].copy()

        # 2. Conversão de Tipos Absoluta para os Tensores
        text_cols = ['sport_key', 'season', 'match_date', 'ht_result']
        numeric_cols = [c for c in df.columns if c not in text_cols]
        
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 3. TRATAMENTO DE EXPECTATIVA DE MERCADO E EXTREMOS
        logger.info("📐 Limpando ruídos de Odds vazias ou nulas...")
        
        # Se a Pinnacle ou a Bet365 não mandou odd, usamos uma Odd Padrão Neutra (3.00) 
        # em vez de dropar a linha, para não perder o jogo na avaliação de features táticas.
        odds_columns = [
            'closing_odd_home', 'closing_odd_draw', 'closing_odd_away',
            'pin_odd_home', 'pin_odd_draw', 'pin_odd_away',
            'odd_over_25', 'odd_under_25', 'odd_btts_yes', 'odd_btts_no'
        ]
        
        for odd_col in odds_columns:
            if odd_col in df.columns:
                mask = (df[odd_col].isna()) | (df[odd_col] <= 1.0)
                df.loc[mask, odd_col] = 3.00 # Neutral Value

        # 4. FillNA Final: Qualquer delta obscuro ou número de escanteios vazio vira zero
        df = df.fillna(0.0).infer_objects(copy=False)

        logger.info("✅ Dados processados. A Matriz de Tensores Puros está pronta para o Modelo.")
        return df

    def save_vault(self, df: pd.DataFrame):
        """Salva os tensores purificados fisicamente (Parquet)."""
        vault_path = self.output_dir / "purified_tensors.parquet"
        df.to_parquet(vault_path, index=False)
        logger.info(f"💾 Cofre de Dados Fechado: {vault_path} ({len(df)} jogos, {len(df.columns)} features puras)")

    async def run(self):
        df_raw = await self.extract_raw_data()
        if df_raw.empty:
            logger.error("Sem dados no DB para forjar os Tensores.")
            return
        df_clean = self.heal_and_engineer(df_raw)
        self.save_vault(df_clean)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(DataSanitizer().run())