# betgenius-backend/workers/feature_engineering/tension_index_engine.py

import asyncio
import logging
import pandas as pd
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [TENSION-ENGINE] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class TensionIndexEngine:
    """
    Motor S-Tier de Simulação Psicológica (Tension Index 2.0).
    Baseado em Teoria dos Jogos e Comportamento de Fim de Temporada.
    Avalia a distância para Título, Vagas Continentais e Rebaixamento.
    Projeta o nível de desespero ou "Modo Férias" para os jogos futuros.
    """

    async def initialize_schema(self, conn):
        logger.info("🛠️ Validando Schema de Tensão Psicológica...")
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
        # TRUNCATE removido para permitir UPSERT contínuo

    def _calculate_advanced_tension(self, current_points: int, games_played: int, max_games: int, all_pts: list) -> float:
        """
        O Algoritmo Acadêmico de Tensão.
        0.05 = Modo Praia (Férias) | 1.0 = Desespero Absoluto (Do or Die).
        """
        games_remaining = max_games - games_played
        
        # Se a base não tem dados da liga ou a temporada acabou
        if games_remaining <= 0 or not all_pts:
            return 0.0

        # Início de temporada (primeiros 25%): Fase de conhecimento, tensão neutra
        if games_played < (max_games * 0.25):
            return 0.5 

        max_possible_points = games_remaining * 3
        num_teams = len(all_pts)

        # Mapeamento Tático da Tabela
        leader_pts = all_pts[0]
        # Aproximação de Vaga Continental (Top 4)
        continental_pts = all_pts[3] if num_teams >= 4 else all_pts[0] 
        # Linha de Corte do Rebaixamento (Assume Z3 ou Z4 dependendo da liga, média N-4)
        relegation_cutoff = all_pts[max(0, num_teams - 4)] 

        # Distâncias (Gaps) Absolutas
        gap_title = abs(leader_pts - current_points)
        gap_continental = abs(continental_pts - current_points)
        gap_relegation = abs(current_points - relegation_cutoff)

        # Fatores de Urgência (0 a 1). Só existe tensão se o objetivo for matematicamente alcançável/arriscado.
        t_title = max(0.0, 1.0 - (gap_title / (max_possible_points + 1))) if gap_title <= max_possible_points else 0.0
        t_cont = max(0.0, 1.0 - (gap_continental / (max_possible_points + 1))) if gap_continental <= max_possible_points else 0.0
        t_releg = max(0.0, 1.0 - (gap_relegation / (max_possible_points + 1))) if gap_relegation <= max_possible_points else 0.0

        # Viés Comportamental: Desespero contra o rebaixamento pesa mais na psique humana
        t_releg = min(1.0, t_releg * 1.25)

        # Detecção de "Modo Férias"
        if t_title == 0.0 and t_cont == 0.0 and t_releg == 0.0:
            raw_tension = 0.05 # O time não briga por absolutamente mais nada
        else:
            raw_tension = max(t_title, t_cont, t_releg)

        # O Efeito Funil: A curva de tensão é exponencial no final da temporada
        urgency_multiplier = (games_played / max_games) ** 2 

        final_tension = raw_tension * urgency_multiplier
        
        return round(max(0.05, min(1.0, final_tension)), 4)

    async def run_tension_simulator(self):
        logger.info("[INIT] INICIANDO TENSION ENGINE: O Tabelião Virtual de Assimetrias.")
        await db.connect()
        
        async with db.pool.acquire() as conn:
            await self.initialize_schema(conn)
            
            logger.info("📥 Carregando o Multiverso de Ligas (Passado e Presente)...")
            
            # Puxa FINISHED (para montar a tabela) e SCHEDULED (para extrair a tensão pré-jogo)
            query = """
                SELECT id as match_id, sport_key, season, match_date, status,
                       home_team_id, away_team_id, home_goals, away_goals
                FROM core.matches_history
                WHERE status IN ('FINISHED', 'SCHEDULED')
                ORDER BY sport_key ASC, season ASC, match_date ASC, id ASC
            """
            matches = await conn.fetch(query)
            if not matches:
                logger.error("❌ Nenhuma partida encontrada. Banco vazio.")
                await db.disconnect()
                return

            df = pd.DataFrame([dict(m) for m in matches])
            df['match_date'] = pd.to_datetime(df['match_date'])
            
            def get_result(row):
                if row['status'] != 'FINISHED': return None
                if row['home_goals'] > row['away_goals']: return 'H'
                if row['home_goals'] < row['away_goals']: return 'A'
                return 'D'
            df['match_result'] = df.apply(get_result, axis=1)
            
            records_to_upsert = []
            
            logger.info(f"🧬 Simulando Tabelas Dinâmicas para {len(df)} partidas...")
            grouped = df.groupby(['sport_key', 'season'])
            
            # Isolamos a data limite para o UPSERT (Atualiza apenas o recente e o futuro)
            cutoff_date = pd.Timestamp(datetime.now().date() - timedelta(days=7))
            
            for (sport_key, season), group in grouped:
                standings = {}
                unique_teams = set(group['home_team_id']).union(set(group['away_team_id']))
                num_teams = len(unique_teams)
                
                # Ignora torneios curtos ou fases de grupos de copas
                max_games = (num_teams - 1) * 2 
                if max_games < 10 or len(group) < (num_teams * 2): 
                    continue

                for _, match in group.iterrows():
                    m_id = match['match_id']
                    h_id = match['home_team_id']
                    a_id = match['away_team_id']
                    status = match['status']
                    result = match['match_result']
                    m_date = match['match_date']
                    
                    if h_id not in standings: standings[h_id] = {'pts': 0, 'games': 0}
                    if a_id not in standings: standings[a_id] = {'pts': 0, 'games': 0}
                    
                    h_pts_before = standings[h_id]['pts']
                    a_pts_before = standings[a_id]['pts']
                    h_games = standings[h_id]['games']
                    a_games = standings[a_id]['games']
                    
                    all_pts = sorted([t['pts'] for t in standings.values()], reverse=True)

                    # Calcula a tensão baseado no que os times precisam NAQUELE INSTANTE
                    h_tension = self._calculate_advanced_tension(h_pts_before, h_games, max_games, all_pts)
                    a_tension = self._calculate_advanced_tension(a_pts_before, a_games, max_games, all_pts)
                    
                    # Filtro de I/O: Só salva na memória os jogos recentes e futuros
                    if m_date >= cutoff_date:
                        records_to_upsert.append((
                            int(m_id), int(h_pts_before), int(a_pts_before), 
                            int(h_games), int(a_games), float(h_tension), float(a_tension)
                        ))
                    
                    # A MÁGICA: Só atualiza a tabela de classificação se o jogo JÁ ACONTECEU
                    if status == 'FINISHED' and result is not None:
                        standings[h_id]['games'] += 1
                        standings[a_id]['games'] += 1
                        
                        if result == 'H':
                            standings[h_id]['pts'] += 3
                        elif result == 'A':
                            standings[a_id]['pts'] += 3
                        else:
                            standings[h_id]['pts'] += 1
                            standings[a_id]['pts'] += 1

            if records_to_upsert:
                logger.info(f"💾 Projetando {len(records_to_upsert)} espectros de Tensão Psicológica no Banco (UPSERT)...")
                try:
                    await conn.executemany("""
                        INSERT INTO core.match_tension_features (
                            match_id, home_points_before, away_points_before, 
                            home_games_played, away_games_played, 
                            home_tension_index, away_tension_index
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (match_id) DO UPDATE SET
                            home_points_before = EXCLUDED.home_points_before,
                            away_points_before = EXCLUDED.away_points_before,
                            home_games_played = EXCLUDED.home_games_played,
                            away_games_played = EXCLUDED.away_games_played,
                            home_tension_index = EXCLUDED.home_tension_index,
                            away_tension_index = EXCLUDED.away_tension_index;
                    """, records_to_upsert)
                except Exception as e:
                    logger.error(f"❌ Erro Crítico durante o UPSERT no Postgres: {e}")
            else:
                logger.info("ℹ️ Nenhum dado de Tensão precisou ser atualizado hoje.")

        await db.disconnect()
        logger.info("[DONE] TENSION ENGINE CONCLUÍDO. Holiday Mode e Desespero estão calibrados.")

if __name__ == "__main__":
    engine = TensionIndexEngine()
    asyncio.run(engine.run_tension_simulator())