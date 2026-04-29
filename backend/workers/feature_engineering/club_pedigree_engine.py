# betgenius-backend/workers/feature_engineering/club_pedigree_engine.py
import sys
import os
import io

# FIX DEFINITIVO DE UNICODE PARA WINDOWS
if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except AttributeError:
        pass

import asyncio
import logging
import math
from pathlib import Path

# Adiciona o backend ao path para importações absolutas
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [GLOBAL-ELO] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class GlobalEloEngine:
    """
    Motor S-Tier de Força Global (Rolling Bayesian Elo).
    Mantém a Força (Elo) das equipes atualizada com base nos jogos recentes.
    """
    def __init__(self):
        self.TIER_BASE_ELO = {
            1: 1500.0, 
            2: 1350.0, 
            3: 1200.0  
        }
        self.FINANCIAL_BOOST_MAX = 100.0 
        self.HOME_ADVANTAGE = 60.0
        self.K_BURN_IN = 40.0 
        self.K_STANDARD = 20.0 

    def _get_league_tier(self, sport_key: str) -> int:
        tier_1 = ['soccer_epl', 'soccer_spain_la_liga', 'soccer_italy_serie_a', 'soccer_germany_bundesliga', 'soccer_uefa_champs_league']
        tier_2 = ['soccer_france_ligue_one', 'soccer_netherlands_eredivisie', 'soccer_portugal_primeira_liga', 'soccer_brazil_campeonato', 'soccer_usa_mls']
        tier_3 = ['soccer_brazil_serie_b', 'soccer_sweden_allsvenskan', 'soccer_norway_eliteserien', 'soccer_denmark_superliga', 'soccer_japan_j_league']
        
        if sport_key in tier_1: return 1
        if sport_key in tier_2: return 2
        if sport_key in tier_3: return 3
        return 2

    def _calculate_expected_score(self, rating_a: float, rating_b: float) -> float:
        return 1.0 / (1.0 + math.pow(10.0, (rating_b - rating_a) / 400.0))

    def _calculate_margin_multiplier(self, goals_a: int, goals_b: int) -> float:
        margin = abs(goals_a - goals_b)
        if margin <= 1: return 1.0
        elif margin == 2: return 1.5
        else: return (11.0 + float(margin)) / 8.0

    async def _get_or_create_team_elo(self, conn, team_id: int) -> tuple:
        """Busca o Elo atual e jogos jogados de um time. Se for novo, inicializa baseado na força da liga."""
        record = await conn.fetchrow("SELECT current_elo, games_played FROM core.team_current_elo WHERE team_id = $1", team_id)
        if record:
            return float(record['current_elo']), int(record['games_played'])
            
        # O time é novato na base (ex: subiu de divisão ou é uma equipe nova do banco)
        team_data = await conn.fetchrow("""
            SELECT l.sport_key, COALESCE(p.avg_wage_percentile, 0.5) as wage_pct 
            FROM core.teams t
            JOIN core.leagues l ON t.league_id = l.id
            LEFT JOIN core.team_pedigree p ON t.id = p.team_id
            WHERE t.id = $1
        """, team_id)
        
        if not team_data:
            return 1200.0, 0 # Fallback extremo
            
        sport_key = team_data['sport_key']
        wage_pct = float(team_data['wage_pct'])
        
        tier = self._get_league_tier(sport_key)
        base_elo = self.TIER_BASE_ELO[tier]
        boost = (self.FINANCIAL_BOOST_MAX * wage_pct) if wage_pct != 0.5 else 0.0
        starting_elo = base_elo + boost
        
        await conn.execute("""
            INSERT INTO core.team_current_elo (team_id, current_elo, games_played) 
            VALUES ($1, $2, 0) ON CONFLICT DO NOTHING
        """, team_id, starting_elo)
        
        return starting_elo, 0

    async def run_daily_update(self):
        logger.info("=========================================================")
        logger.info("🔄 ELO ENGINE: ATUALIZAÇÃO DIÁRIA DE FORÇA")
        logger.info("=========================================================")
        
        await db.connect()
        
        async with db.pool.acquire() as conn:
            # Seleciona apenas os jogos FINALIZADOS que ainda NÃO estão na tabela match_elo_history
            logger.info("📥 Buscando jogos liquidados aguardando recalibração de Elo...")
            matches = await conn.fetch("""
                SELECT m.id, m.match_date, m.home_team_id, m.away_team_id, m.home_goals, m.away_goals 
                FROM core.matches_history m 
                LEFT JOIN core.match_elo_history e ON m.id = e.match_id
                WHERE m.home_goals IS NOT NULL AND m.away_goals IS NOT NULL 
                AND m.status = 'FINISHED'
                AND e.match_id IS NULL
                ORDER BY m.match_date ASC, m.id ASC
            """)
            
            if not matches:
                logger.info("⏸️ Nenhum jogo pendente. O Elo global já está perfeitamente atualizado.")
                await db.disconnect()
                return

            logger.info(f"⚙️ {len(matches)} jogos novos encontrados. Processando matemática Bayesiana...")
            
            async with conn.transaction():
                history_records = []
                for match in matches:
                    m_id = match['id']
                    home_id = match['home_team_id']
                    away_id = match['away_team_id']
                    hg = int(match['home_goals'])
                    ag = int(match['away_goals'])
                    
                    home_elo_before, home_games = await self._get_or_create_team_elo(conn, home_id)
                    away_elo_before, away_games = await self._get_or_create_team_elo(conn, away_id)
                    
                    home_elo_adjusted = home_elo_before + self.HOME_ADVANTAGE
                    
                    expected_home = self._calculate_expected_score(home_elo_adjusted, away_elo_before)
                    expected_away = 1.0 - expected_home
                    
                    if hg > ag: actual_home, actual_away = 1.0, 0.0
                    elif hg < ag: actual_home, actual_away = 0.0, 1.0
                    else: actual_home, actual_away = 0.5, 0.5
                    
                    margin_mult = self._calculate_margin_multiplier(hg, ag)
                    
                    k_home = self.K_BURN_IN if home_games < 30 else self.K_STANDARD
                    k_away = self.K_BURN_IN if away_games < 30 else self.K_STANDARD
                    
                    home_elo_change = k_home * margin_mult * (actual_home - expected_home)
                    away_elo_change = k_away * margin_mult * (actual_away - expected_away)
                    
                    home_elo_after = home_elo_before + home_elo_change
                    away_elo_after = away_elo_before + away_elo_change
                    
                    # 1. Registra o histórico da partida para alimentar a Matrix da IA depois
                    history_records.append((
                        m_id, 
                        round(home_elo_before, 2), round(away_elo_before, 2), 
                        round(home_elo_after, 2), round(away_elo_after, 2)
                    ))
                    
                    # 2. Atualiza a Força Global da Equipe (Current Elo)
                    await conn.execute("UPDATE core.team_current_elo SET current_elo = $1, games_played = $2, last_updated = NOW() WHERE team_id = $3", home_elo_after, home_games + 1, home_id)
                    await conn.execute("UPDATE core.team_current_elo SET current_elo = $1, games_played = $2, last_updated = NOW() WHERE team_id = $3", away_elo_after, away_games + 1, away_id)
                
                # Injeção em Massa do Histórico
                await conn.executemany("""
                    INSERT INTO core.match_elo_history (match_id, home_elo_before, away_elo_before, home_elo_after, away_elo_after)
                    VALUES ($1, $2, $3, $4, $5)
                """, history_records)
            
        await db.disconnect()
        logger.info(f"=== SUCESSO: {len(matches)} jogos atualizaram o Pedigree Elo do sistema ===")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(GlobalEloEngine().run_daily_update())