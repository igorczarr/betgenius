# betgenius-backend/workers/feature_engineering/tension_index_engine.py

import asyncio
import logging
import pandas as pd
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# =====================================================================
# BLINDAGEM DE ENCODING PARA WINDOWS E CARREGAMENTO DO .ENV
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [TENSION-ENGINE] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class TensionIndexEngine:
    """
    Motor S-Tier de Simulação de Pressão Psicológica (Tension Index).
    Reconstrói a tabela de classificação jogo a jogo desde 2015 para calcular
    a distância matemática para o título, para o rebaixamento e o "Modo Férias".
    """

    async def initialize_schema(self, conn):
        logger.info("🛠️ Preparando Schema de Tensão Psicológica...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS core.match_tension_features (
                match_id INTEGER PRIMARY KEY REFERENCES core.matches_history(id) ON DELETE CASCADE,
                home_points_before INTEGER,
                away_points_before INTEGER,
                home_games_played INTEGER,
                away_games_played INTEGER,
                home_tension_index NUMERIC(5, 4),
                away_tension_index NUMERIC(5, 4)
            );
        """)
        await conn.execute("TRUNCATE TABLE core.match_tension_features CASCADE;")

    def _calculate_tension(self, current_points: int, games_played: int, max_games: int, leader_pts: int, drop_zone_pts: int) -> float:
        """O Algoritmo de Tensão: 0.0 (Férias) a 1.0 (Desespero)."""
        games_remaining = max_games - games_played
        
        # Início de temporada (menos de 25% dos jogos): a tensão é neutra de disputa (0.5)
        if games_played < (max_games * 0.25):
            return 0.5
            
        if games_remaining == 0:
            return 0.0

        max_possible_points = games_remaining * 3
        
        gap_to_title = max(0, leader_pts - current_points)
        gap_to_relegation = max(0, current_points - drop_zone_pts)
        
        title_tension = 0.0
        if gap_to_title <= max_possible_points:
            title_tension = 1.0 - (gap_to_title / (max_possible_points + 1))
            
        relegation_tension = 0.0
        if gap_to_relegation <= max_possible_points:
            relegation_tension = 1.0 - (gap_to_relegation / (max_possible_points + 1))
            relegation_tension = min(1.0, relegation_tension * 1.2) # Desespero pesa mais

        raw_tension = max(title_tension, relegation_tension)
        season_progress = games_played / max_games
        final_tension = raw_tension * season_progress
        
        return round(final_tension, 4)

    async def run_tension_simulator(self):
        logger.info("[INIT] INICIANDO TENSION ENGINE: O Tabelião Virtual das Assimetrias.")
        await db.connect()
        
        async with db.pool.acquire() as conn:
            await self.initialize_schema(conn)
            
            logger.info("📥 Carregando o Multiverso de Ligas (Pontos Corridos)...")
            
            # FILTRO SEGURO: Pegamos apenas jogos passados (onde home_goals existe)
            # Para evitar recalcular copas, limitamos a analise a ligas que têm mais de 10 jogos por rodada histórica
            query = """
                SELECT id as match_id, sport_key, season, match_date, 
                       home_team_id, away_team_id, home_goals, away_goals
                FROM core.matches_history
                WHERE home_goals IS NOT NULL AND away_goals IS NOT NULL
                ORDER BY sport_key ASC, season ASC, match_date ASC, id ASC
            """
            matches = await conn.fetch(query)
            if not matches:
                logger.error("❌ Nenhuma partida com placar finalizado encontrada. Banco vazio.")
                await db.disconnect()
                return

            df = pd.DataFrame([dict(m) for m in matches])
            
            # Recalculamos o resultado para garantir que é exato (H, D, A)
            def get_result(row):
                if row['home_goals'] > row['away_goals']: return 'H'
                if row['home_goals'] < row['away_goals']: return 'A'
                return 'D'
            df['match_result'] = df.apply(get_result, axis=1)
            
            records_to_insert = []
            
            logger.info(f"🧬 Simulando Tabelas de Classificação para {len(df)} partidas...")
            grouped = df.groupby(['sport_key', 'season'])
            
            for (sport_key, season), group in grouped:
                standings = {}
                unique_teams = set(group['home_team_id']).union(set(group['away_team_id']))
                num_teams = len(unique_teams)
                
                # A mágica que pula Copas (Torneios curtos): Se os times não jogam entre si pelo menos turno e returno, ignora.
                max_games = (num_teams - 1) * 2 
                if max_games < 10 or len(group) < (num_teams * 2): 
                    continue

                relegation_rank = max(1, num_teams - 3)

                for _, match in group.iterrows():
                    m_id = match['match_id']
                    h_id = match['home_team_id']
                    a_id = match['away_team_id']
                    result = match['match_result']
                    
                    if h_id not in standings: standings[h_id] = {'pts': 0, 'games': 0}
                    if a_id not in standings: standings[a_id] = {'pts': 0, 'games': 0}
                    
                    h_pts_before = standings[h_id]['pts']
                    a_pts_before = standings[a_id]['pts']
                    h_games = standings[h_id]['games']
                    a_games = standings[a_id]['games']
                    
                    all_pts = sorted([t['pts'] for t in standings.values()], reverse=True)
                    leader_pts = all_pts[0] if all_pts else 0
                    
                    drop_zone_pts = 0
                    if len(all_pts) >= num_teams:
                        drop_zone_pts = all_pts[relegation_rank] if relegation_rank < len(all_pts) else 0

                    h_tension = self._calculate_tension(h_pts_before, h_games, max_games, leader_pts, drop_zone_pts)
                    a_tension = self._calculate_tension(a_pts_before, a_games, max_games, leader_pts, drop_zone_pts)
                    
                    records_to_insert.append((
                        m_id, h_pts_before, a_pts_before, h_games, a_games, h_tension, a_tension
                    ))
                    
                    # Atualiza a tabela PÓS-jogo
                    standings[h_id]['games'] += 1
                    standings[a_id]['games'] += 1
                    
                    if result == 'H':
                        standings[h_id]['pts'] += 3
                    elif result == 'A':
                        standings[a_id]['pts'] += 3
                    else:
                        standings[h_id]['pts'] += 1
                        standings[a_id]['pts'] += 1

            logger.info("💾 Injetando Índice de Tensão (Holiday Mode vs Desperation) no Banco (Copy)...")
            try:
                await conn.copy_records_to_table(
                    'match_tension_features', schema_name='core',
                    records=records_to_insert,
                    columns=[
                        'match_id', 'home_points_before', 'away_points_before', 
                        'home_games_played', 'away_games_played', 
                        'home_tension_index', 'away_tension_index'
                    ]
                )
            except Exception as e:
                logger.error(f"❌ Erro Crítico ao copiar records para o Postgres: {e}")

        await db.disconnect()
        logger.info("[DONE] TENSION ENGINE CONCLUÍDO. O estado psicológico de campeonato foi mapeado.")

if __name__ == "__main__":
    engine = TensionIndexEngine()
    asyncio.run(engine.run_tension_simulator())