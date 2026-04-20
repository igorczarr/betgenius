# betgenius-backend/workers/feature_engineering/market_respect_engine.py

import asyncio
import logging
import pandas as pd
import sys
from pathlib import Path
from dotenv import load_dotenv

# =====================================================================
# BLINDAGEM MÁXIMA DE ENCODING PARA WINDOWS E CARREGAMENTO DE VARIÁVEIS
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [MARKET-RESPECT] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class MarketRespectEngine:
    """
    Motor S-Tier de Leitura de Sindicatos (Pinnacle Implied Probability).
    Converte as Odds de Fechamento do passado em Probabilidades Implícitas
    e calcula a Média Móvel Exponencial (EWMA) para medir o 'Respeito do Mercado'.
    """

    def __init__(self):
        self.SPAN = 10 # Janela de 10 jogos para entender a tendência de mercado

    async def initialize_schema(self, conn):
        logger.info("🛠️ Preparando Schema do Mercado (Market Respect)...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS core.match_market_features (
                match_id INTEGER PRIMARY KEY REFERENCES core.matches_history(id) ON DELETE CASCADE,
                home_market_respect NUMERIC(5, 4),
                away_market_respect NUMERIC(5, 4)
            );
        """)
        await conn.execute("TRUNCATE TABLE core.match_market_features CASCADE;")

    def _build_perspective_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Desmembra o jogo para criar a linha do tempo do Respeito de Mercado por equipe."""
        
        # Garante que as colunas numéricas são lidas corretamente como float (Evita erro de tipo Decimal)
        df['closing_odd_home'] = pd.to_numeric(df['closing_odd_home'], errors='coerce')
        df['closing_odd_away'] = pd.to_numeric(df['closing_odd_away'], errors='coerce')

        # Filtra jogos que não têm odds registradas ou odds inválidas (para não dividir por zero)
        df = df[(df['closing_odd_home'] > 1.0) & (df['closing_odd_away'] > 1.0)].copy()

        # Calcula a Probabilidade Implícita Pura
        df['implied_prob_home'] = 1.0 / df['closing_odd_home']
        df['implied_prob_away'] = 1.0 / df['closing_odd_away']

        # Visão Mandante
        df_home = df[['id', 'match_date', 'home_team_id', 'implied_prob_home']].copy()
        df_home.columns = ['match_id', 'date', 'team_id', 'implied_prob']
        df_home['is_home'] = 1

        # Visão Visitante
        df_away = df[['id', 'match_date', 'away_team_id', 'implied_prob_away']].copy()
        df_away.columns = ['match_id', 'date', 'team_id', 'implied_prob']
        df_away['is_home'] = 0

        # Concatena e ordena a linha do tempo
        df_teams = pd.concat([df_home, df_away], ignore_index=True)
        df_teams = df_teams.sort_values(by=['team_id', 'date']).reset_index(drop=True)
        
        return df_teams

    def _calculate_ewma_respect(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica o Decaimento Exponencial com a blindagem do Shift(1)"""
        
        # Agrupa pelo time e calcula o EWMA das probabilidades
        # O SHIFT(1) garante que o respeito de HOJE é baseado no que o mercado achava até ONTEM
        df['market_respect_ewma'] = df.groupby('team_id')['implied_prob']\
                                      .transform(lambda x: x.ewm(span=self.SPAN, adjust=False).mean().shift(1))

        # Para o primeiro jogo da história do time, assumimos que o mercado o via como "Mediano" (1/3 de chance = 0.3333)
        df['market_respect_ewma'] = df['market_respect_ewma'].fillna(0.3333)

        return df

    async def run_market_engine(self):
        logger.info("[INIT] INICIANDO MARKET RESPECT ENGINE: Decodificando o Dinheiro Inteligente.")
        await db.connect()
        
        async with db.pool.acquire() as conn:
            await self.initialize_schema(conn)
            
            logger.info("📥 Extraindo Odds de Fechamento da Pinnacle (Histórico)...")
            query = """
                SELECT id, match_date, home_team_id, away_team_id, 
                       closing_odd_home, closing_odd_away
                FROM core.matches_history
                WHERE closing_odd_home IS NOT NULL AND closing_odd_away IS NOT NULL
                ORDER BY match_date ASC, id ASC
            """
            matches = await conn.fetch(query)
            
            if not matches:
                logger.warning("⚠️ Banco histórico vazio ou sem odds registradas. Abortando Market Respect.")
                await db.disconnect()
                return

            df = pd.DataFrame([dict(m) for m in matches])

            logger.info(f"🧬 Calculando Probabilidades Implícitas para {len(df)} partidas...")
            df_teams = self._build_perspective_df(df)
            df_features = self._calculate_ewma_respect(df_teams)

            logger.info("🔄 Recombinando Tensores para injeção (Home/Away)...")
            home_feats = df_features[df_features['is_home'] == 1].set_index('match_id')
            away_feats = df_features[df_features['is_home'] == 0].set_index('match_id')

            records_to_insert = []
            valid_match_ids = df_features['match_id'].unique()
            
            for match_id in valid_match_ids:
                if match_id in home_feats.index and match_id in away_feats.index:
                    h = home_feats.loc[match_id]
                    a = away_feats.loc[match_id]
                    
                    # Usa isinstance para lidar com jogos raros onde o Pandas duplica os índices
                    h_val = float(h['market_respect_ewma'].iloc[0]) if isinstance(h, pd.DataFrame) else float(h['market_respect_ewma'])
                    a_val = float(a['market_respect_ewma'].iloc[0]) if isinstance(a, pd.DataFrame) else float(a['market_respect_ewma'])
                    
                    records_to_insert.append((
                        int(match_id),
                        round(h_val, 4),
                        round(a_val, 4)
                    ))

            logger.info("💾 Injetando Espectro do Mercado no Data Warehouse (Copy)...")
            try:
                await conn.copy_records_to_table(
                    'match_market_features', schema_name='core',
                    records=records_to_insert,
                    columns=['match_id', 'home_market_respect', 'away_market_respect']
                )
            except Exception as e:
                logger.error(f"❌ Erro Crítico ao copiar records para o Postgres: {e}")

        await db.disconnect()
        logger.info("[DONE] MARKET RESPECT CONCLUÍDO. O modelo agora enxerga a alma das Casas de Apostas.")

if __name__ == "__main__":
    engine = MarketRespectEngine()
    asyncio.run(engine.run_market_engine())