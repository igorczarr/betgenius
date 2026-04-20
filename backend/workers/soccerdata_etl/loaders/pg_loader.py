# betgenius-backend/workers/soccerdata_etl/loaders/pg_loader.py

import asyncpg
import pandas as pd
import logging
import os
import sys
from rapidfuzz import process, fuzz

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

class PostgresLoader:
    def __init__(self):
        self.db_url = os.getenv("POSTGRES_URL")
        self.pool = None
        self.team_map = {}

    async def connect(self):
        import asyncio
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.pool = await asyncpg.create_pool(self.db_url, min_size=2, max_size=10, command_timeout=60)
                logger.info("🔌 [LOADER] Conectado ao PostgreSQL.")
                await self._load_team_dictionary()
                return
            except Exception as e:
                logger.warning(f"⚠️ [LOADER] Tentativa {attempt + 1}/{max_retries} falhou: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                else:
                    raise e

    async def close(self):
        if self.pool:
            await self.pool.close()
            logger.info("🔌 [LOADER] Desconectado do PostgreSQL.")

    async def _load_team_dictionary(self):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, canonical_name FROM core.teams")
            self.team_map = {row['canonical_name']: row['id'] for row in rows}
            aliases = await conn.fetch("SELECT team_id, alias_name FROM core.team_aliases")
            for row in aliases:
                self.team_map[row['alias_name']] = row['team_id']

    def _resolve_team_id(self, team_name_str):
        if not team_name_str or pd.isna(team_name_str): return None
        if team_name_str in self.team_map: return self.team_map[team_name_str]
        
        nomes = list(self.team_map.keys())
        match = process.extractOne(team_name_str, nomes, scorer=fuzz.WRatio)
        if match and match[1] > 85:
            self.team_map[team_name_str] = self.team_map[match[0]] 
            return self.team_map[match[0]]
        return None

    async def upsert_alpha_matrix(self, df: pd.DataFrame):
        if df.empty: return

        logger.info(f"📥 [LOADER] Injetando {len(df)} partidas no Banco de Dados...")

        # EXATAMENTE ALINHADO COM SEU SCHEMA
        query_match = """
            INSERT INTO core.matches_history 
            (match_date, home_team_id, away_team_id, home_goals, away_goals, 
             closing_odd_home, closing_odd_draw, closing_odd_away, xg_home, xg_away, status, season)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ON CONFLICT ON CONSTRAINT unique_match_date_teams 
            DO UPDATE SET 
                home_goals = EXCLUDED.home_goals,
                away_goals = EXCLUDED.away_goals,
                closing_odd_home = EXCLUDED.closing_odd_home,
                closing_odd_draw = EXCLUDED.closing_odd_draw,
                closing_odd_away = EXCLUDED.closing_odd_away,
                xg_home = EXCLUDED.xg_home,
                xg_away = EXCLUDED.xg_away,
                status = EXCLUDED.status,
                season = EXCLUDED.season
            RETURNING id;
        """

        query_alpha = """
            INSERT INTO core.alpha_matrix 
            (match_id, home_elo_before, away_elo_before, home_ppda, away_ppda)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (match_id) 
            DO UPDATE SET
                home_elo_before = EXCLUDED.home_elo_before,
                away_elo_before = EXCLUDED.away_elo_before,
                home_ppda = EXCLUDED.home_ppda,
                away_ppda = EXCLUDED.away_ppda;
        """

        df = df.where(pd.notnull(df), None)

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                sucesso = 0
                for _, row in df.iterrows():
                    h_id = self._resolve_team_id(row.get('home_team'))
                    a_id = self._resolve_team_id(row.get('away_team'))
                    if not h_id or not a_id: continue
                        
                    try:
                        match_id = await conn.fetchval(
                            query_match,
                            pd.to_datetime(row['date_str']).date(), 
                            h_id, 
                            a_id,
                            int(row.get('home_goals', 0) or 0),
                            int(row.get('away_goals', 0) or 0),
                            float(row.get('PSCH', 0.0) or 0.0), 
                            float(row.get('PSCD', 0.0) or 0.0), 
                            float(row.get('PSCA', 0.0) or 0.0), 
                            float(row.get('home_xg', 0.0) or 0.0),
                            float(row.get('away_xg', 0.0) or 0.0),
                            'FINISHED',
                            str(row.get('season', ''))
                        )

                        if match_id:
                            await conn.execute(
                                query_alpha,
                                match_id,
                                float(row.get('home_elo', 1500) or 1500),
                                float(row.get('away_elo', 1500) or 1500),
                                float(row.get('home_ppda', 0.0) or 0.0),
                                float(row.get('away_ppda', 0.0) or 0.0)
                            )
                            sucesso += 1
                    except Exception as e:
                        logger.error(f"Erro BD Jogo ID {h_id}x{a_id}: {e}")
                        
        logger.info(f"[LOADER] {sucesso} jogos sincronizados.")