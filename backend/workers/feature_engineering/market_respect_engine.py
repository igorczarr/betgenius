# betgenius-backend/workers/feature_engineering/market_respect_engine.py
import sys
import os
import io
import asyncio
import logging
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [MARKET-RESPECT] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class MarketRespectEngine:
    """
    Motor S-Tier de Leitura de Sindicatos (Rolling Update).
    Mantém o histórico intacto e atualiza apenas jogos recentes e futuros.
    Projeta o EWMA para os jogos 'SCHEDULED' para alimentar o ViewMatchCenter.
    """

    def __init__(self):
        self.SPAN = 10 # Janela de 10 jogos para entender a tendência de mercado

    async def initialize_schema(self, conn):
        logger.info("🛠️ Validando Schema do Mercado (Market Respect)...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS core.match_market_features (
                match_id INTEGER PRIMARY KEY REFERENCES core.matches_history(id) ON DELETE CASCADE,
                home_market_respect NUMERIC(5, 4),
                away_market_respect NUMERIC(5, 4)
            );
        """)
        # AQUI FOI REMOVIDO O TRUNCATE. Nós agora conservamos a base!

    def _build_perspective_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Desmembra o jogo para criar a linha do tempo do Respeito de Mercado por equipe."""
        
        df['closing_odd_home'] = pd.to_numeric(df['closing_odd_home'], errors='coerce')
        df['closing_odd_away'] = pd.to_numeric(df['closing_odd_away'], errors='coerce')

        # Calcula a Probabilidade Implícita Pura (Apenas onde existe Odd justa)
        df['implied_prob_home'] = None
        df['implied_prob_away'] = None
        
        valid_home = df['closing_odd_home'] > 1.0
        valid_away = df['closing_odd_away'] > 1.0
        
        df.loc[valid_home, 'implied_prob_home'] = 1.0 / df.loc[valid_home, 'closing_odd_home']
        df.loc[valid_away, 'implied_prob_away'] = 1.0 / df.loc[valid_away, 'closing_odd_away']

        # Visão Mandante
        df_home = df[['id', 'match_date', 'home_team_id', 'implied_prob_home']].copy()
        df_home.columns = ['match_id', 'date', 'team_id', 'implied_prob']
        df_home['is_home'] = 1

        # Visão Visitante
        df_away = df[['id', 'match_date', 'away_team_id', 'implied_prob_away']].copy()
        df_away.columns = ['match_id', 'date', 'team_id', 'implied_prob']
        df_away['is_home'] = 0

        # Concatena e ordena a linha do tempo (Passado -> Futuro)
        df_teams = pd.concat([df_home, df_away], ignore_index=True)
        df_teams['date'] = pd.to_datetime(df_teams['date'])
        df_teams = df_teams.sort_values(by=['team_id', 'date', 'match_id']).reset_index(drop=True)
        
        return df_teams

    def _calculate_ewma_respect(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica o Decaimento Exponencial com projeção para o futuro."""
        
        # O SHIFT(1) garante que o respeito de HOJE é baseado no que o mercado achava até ONTEM
        # O ignore_na=True faz com que os jogos SCHEDULED não quebrem a matemática
        df['market_respect_ewma'] = df.groupby('team_id')['implied_prob']\
                                      .transform(lambda x: x.ewm(span=self.SPAN, adjust=False, ignore_na=True).mean().shift(1))

        # A MÁGICA PARA O FRONT-END: Forward Fill. 
        # Os jogos SCHEDULED herdam o respeito do último jogo finalizado da equipe!
        df['market_respect_ewma'] = df.groupby('team_id')['market_respect_ewma'].ffill()

        # Para o primeiro jogo da história do time, assumimos que o mercado o via como "Mediano" (33%)
        df['market_respect_ewma'] = df['market_respect_ewma'].fillna(0.3333)

        return df

    async def run_market_engine(self):
        logger.info("[INIT] INICIANDO MARKET RESPECT ENGINE: Atualização Contínua.")
        await db.connect()
        
        async with db.pool.acquire() as conn:
            await self.initialize_schema(conn)
            
            logger.info("📥 Extraindo histórico completo para recalibrar as médias móveis...")
            # Pegamos TODOS os jogos para o Pandas fazer a matemática perfeita
            query = """
                SELECT id, match_date, home_team_id, away_team_id, 
                       closing_odd_home, closing_odd_away, status
                FROM core.matches_history
                ORDER BY match_date ASC, id ASC
            """
            matches = await conn.fetch(query)
            
            if not matches:
                logger.warning("⚠️ Banco vazio. Abortando Market Respect.")
                await db.disconnect()
                return

            df = pd.DataFrame([dict(m) for m in matches])

            logger.info(f"🧬 Computando Probabilidades e projetando o futuro para {len(df)} partidas...")
            df_teams = self._build_perspective_df(df)
            df_features = self._calculate_ewma_respect(df_teams)

            logger.info("🔄 Isolando apenas os jogos recentes e futuros para o UPSERT...")
            
            # Filtro S-Tier: Só vamos escrever no banco os jogos dos últimos 7 dias e do futuro.
            # Isso evita travar o PostgreSQL tentando reescrever 20.000 linhas do passado todos os dias.
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

            records_to_upsert = []
            valid_match_ids = df_to_update['match_id'].unique()
            
            for match_id in valid_match_ids:
                if match_id in home_feats.index and match_id in away_feats.index:
                    h = home_feats.loc[match_id]
                    a = away_feats.loc[match_id]
                    
                    h_val = float(h['market_respect_ewma'].iloc[0]) if isinstance(h, pd.DataFrame) else float(h['market_respect_ewma'])
                    a_val = float(a['market_respect_ewma'].iloc[0]) if isinstance(a, pd.DataFrame) else float(a['market_respect_ewma'])
                    
                    records_to_upsert.append((
                        int(match_id),
                        round(h_val, 4),
                        round(a_val, 4)
                    ))

            if records_to_upsert:
                logger.info(f"💾 Atualizando {len(records_to_upsert)} jogos ativos no Data Warehouse...")
                try:
                    await conn.executemany("""
                        INSERT INTO core.match_market_features (match_id, home_market_respect, away_market_respect)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (match_id) DO UPDATE SET 
                            home_market_respect = EXCLUDED.home_market_respect,
                            away_market_respect = EXCLUDED.away_market_respect;
                    """, records_to_upsert)
                except Exception as e:
                    logger.error(f"❌ Erro Crítico durante UPSERT no Postgres: {e}")
            else:
                logger.info("ℹ️ Nenhum jogo recente precisou de atualização.")

        await db.disconnect()
        logger.info("[DONE] MARKET RESPECT ATUALIZADO. ViewMatchCenter abastecido com sucesso.")

if __name__ == "__main__":
    engine = MarketRespectEngine()
    asyncio.run(engine.run_market_engine())