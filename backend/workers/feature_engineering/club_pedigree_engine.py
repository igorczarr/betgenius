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
from dotenv import load_dotenv

# Adiciona o backend ao path para importações absolutas
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
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
    Motor S-Tier de Força Global (Advanced Margin of Victory Elo) - IN-MEMORY EDITION.
    Baseado na metodologia Clubelo e FiveThirtyEight (SPI).
    Processa 150.000 jogos em segundos sem estourar o banco de dados.
    """
    def __init__(self):
        # Base inicial calibrada por Tiers
        self.TIER_BASE_ELO = {
            1: 1500.0, 
            2: 1350.0, 
            3: 1200.0  
        }
        self.FINANCIAL_BOOST_MAX = 100.0 
        self.K_BURN_IN = 40.0 
        
        # Mapeamento de K-Factor por Tier (Importância do Torneio)
        self.TIER_K_FACTOR = {
            1: 30.0, # Champions League, Premier League (Alta fidelidade tática)
            2: 20.0, # Ligas periféricas de 1ª divisão
            3: 15.0  # Ligas de acesso e divisões inferiores (Maior ruído)
        }

    def _get_league_tier(self, sport_key: str) -> int:
        tier_1 = ['soccer_epl', 'soccer_spain_la_liga', 'soccer_italy_serie_a', 'soccer_germany_bundesliga', 'soccer_uefa_champs_league', 'soccer_fifa_world_cup', 'soccer_uefa_euro', 'soccer_copa_america']
        tier_2 = ['soccer_france_ligue_one', 'soccer_netherlands_eredivisie', 'soccer_portugal_primeira_liga', 'soccer_brazil_campeonato', 'soccer_usa_mls', 'soccer_conmebol_copa_libertadores', 'soccer_uefa_europa_league']
        tier_3 = ['soccer_brazil_serie_b', 'soccer_sweden_allsvenskan', 'soccer_norway_eliteserien', 'soccer_denmark_superliga', 'soccer_japan_j_league', 'soccer_conmebol_copa_sudamericana']
        
        if sport_key in tier_1: return 1
        if sport_key in tier_2: return 2
        if sport_key in tier_3: return 3
        return 2

    def _get_home_advantage(self, sport_key: str) -> float:
        """HFA Dinâmico. Competições sul-americanas têm HFA notoriamente maior."""
        if 'conmebol' in sport_key or 'brazil' in sport_key:
            return 75.0
        elif 'fifa' in sport_key or 'euro' in sport_key:
            return 0.0 # Campo neutro em fases finais de seleções
        return 60.0 # Padrão europeu

    def _calculate_expected_score(self, rating_a: float, rating_b: float) -> float:
        """Curva logística padrão do Elo (Probabilidade de Vitória)."""
        return 1.0 / (1.0 + math.pow(10.0, (rating_b - rating_a) / 400.0))

    def _calculate_advanced_mov_multiplier(self, goals_winner: int, goals_loser: int, elo_winner: float, elo_loser: float) -> float:
        """
        Multiplicador de Margem de Vitória (Autocorrigível).
        Goleadas de zebras valem exponencialmente mais do que goleadas de favoritos absolutos.
        """
        margin = abs(goals_winner - goals_loser)
        if margin <= 1: 
            return 1.0
            
        elo_diff = elo_winner - elo_loser
        
        # Fórmula Clubelo / 538 Hybrid
        # MoV = ln(margin + 1) * (2.2 / (delta_elo * 0.001 + 2.2))
        multiplier = math.log(margin + 1) * (2.2 / ((elo_diff * 0.001) + 2.2))
        
        # Proteção contra valores bizarros em assimetrias extremas
        return max(1.0, min(5.0, multiplier))

    async def run_daily_update(self):
        logger.info("=========================================================")
        logger.info("🔄 ELO ENGINE: ATUALIZAÇÃO S-TIER DE FORÇA ESTRUTURAL")
        logger.info("=========================================================")
        
        await db.connect()
        
        is_genesis = os.getenv("GENESIS_MODE", "False") == "True"
        
        async with db.pool.acquire() as conn:
            if is_genesis:
                logger.warning("⚠️ MODO GÊNESIS ATIVADO: Resetando Histórico de Elo.")
                await conn.execute("TRUNCATE TABLE core.match_elo_history RESTART IDENTITY CASCADE;")
                await conn.execute("TRUNCATE TABLE core.team_current_elo RESTART IDENTITY CASCADE;")
            
            logger.info("📥 Extraindo todos os jogos finalizados aguardando cálculo...")
            matches = await conn.fetch("""
                SELECT m.id, m.match_date, m.sport_key, m.home_team_id, m.away_team_id, m.home_goals, m.away_goals 
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

            logger.info(f"⚙️ Construindo estado de {len(matches)} partidas na Memória RAM...")

            # 1. Carrega o Pedigree Financeiro de Todas as Equipas de uma vez
            pedigree_data = await conn.fetch("""
                SELECT t.id as team_id, l.sport_key, COALESCE(p.avg_wage_percentile, 0.5) as wage_pct 
                FROM core.teams t
                JOIN core.leagues l ON t.league_id = l.id
                LEFT JOIN core.team_pedigree p ON t.id = p.team_id
            """)
            pedigree_map = {r['team_id']: {'sport_key': r['sport_key'], 'wage_pct': float(r['wage_pct'])} for r in pedigree_data}

            # 2. Carrega o Elo Atual (Se não for genesis)
            team_state = {}
            if not is_genesis:
                existing_elos = await conn.fetch("SELECT team_id, current_elo, games_played FROM core.team_current_elo")
                for r in existing_elos:
                    team_state[r['team_id']] = {'elo': float(r['current_elo']), 'games': r['games_played']}

            def get_team_elo(t_id):
                if t_id in team_state:
                    return team_state[t_id]['elo'], team_state[t_id]['games']
                
                # Se for novato, calcula o Elo Base na hora
                p_data = pedigree_map.get(t_id, {'sport_key': 'unknown', 'wage_pct': 0.5})
                tier = self._get_league_tier(p_data['sport_key'])
                base_elo = self.TIER_BASE_ELO.get(tier, 1350.0)
                boost = self.FINANCIAL_BOOST_MAX * p_data['wage_pct'] if p_data['wage_pct'] != 0.5 else 0.0
                starting_elo = base_elo + boost
                team_state[t_id] = {'elo': starting_elo, 'games': 0}
                return starting_elo, 0

            # 3. Processamento Sequencial In-Memory
            history_records = []
            
            for match in matches:
                m_id = match['id']
                sport_key = match['sport_key']
                home_id = match['home_team_id']
                away_id = match['away_team_id']
                hg = int(match['home_goals'])
                ag = int(match['away_goals'])
                
                home_elo_before, home_games = get_team_elo(home_id)
                away_elo_before, away_games = get_team_elo(away_id)
                
                # HFA Dinâmico
                hfa = self._get_home_advantage(sport_key)
                home_elo_adjusted = home_elo_before + hfa
                
                expected_home = self._calculate_expected_score(home_elo_adjusted, away_elo_before)
                expected_away = 1.0 - expected_home
                
                # Identifica quem ganhou e o elo do vencedor para o MoV
                if hg > ag: 
                    actual_home, actual_away = 1.0, 0.0
                    elo_winner, elo_loser = home_elo_adjusted, away_elo_before
                elif hg < ag: 
                    actual_home, actual_away = 0.0, 1.0
                    elo_winner, elo_loser = away_elo_before, home_elo_adjusted
                else: 
                    actual_home, actual_away = 0.5, 0.5
                    elo_winner, elo_loser = home_elo_adjusted, away_elo_before # Em empate, o favorito é penalizado de qualquer forma
                
                # Multiplicador Autocorrigível de Margem (MoV)
                margin_mult = self._calculate_advanced_mov_multiplier(max(hg, ag), min(hg, ag), elo_winner, elo_loser)
                
                # K-Factor Dinâmico
                tier = self._get_league_tier(sport_key)
                k_standard = self.TIER_K_FACTOR.get(tier, 20.0)
                
                k_home = self.K_BURN_IN if home_games < 30 else k_standard
                k_away = self.K_BURN_IN if away_games < 30 else k_standard
                
                home_elo_change = k_home * margin_mult * (actual_home - expected_home)
                away_elo_change = k_away * margin_mult * (actual_away - expected_away)
                
                home_elo_after = home_elo_before + home_elo_change
                away_elo_after = away_elo_before + away_elo_change
                
                # Atualiza a Memória RAM
                team_state[home_id]['elo'] = home_elo_after
                team_state[home_id]['games'] += 1
                team_state[away_id]['elo'] = away_elo_after
                team_state[away_id]['games'] += 1
                
                history_records.append((
                    m_id, 
                    round(home_elo_before, 2), round(away_elo_before, 2), 
                    round(home_elo_after, 2), round(away_elo_after, 2)
                ))

            # 4. Injeção Final no Banco (Lotes de 10.000 para ser rápido)
            logger.info("💾 Matemática Bayesiana concluída. Injetando histórico no Banco em lotes...")
            
            batch_size = 10000
            for i in range(0, len(history_records), batch_size):
                batch = history_records[i:i + batch_size]
                await conn.executemany("""
                    INSERT INTO core.match_elo_history (match_id, home_elo_before, away_elo_before, home_elo_after, away_elo_after)
                    VALUES ($1, $2, $3, $4, $5)
                """, batch)

            logger.info("💾 Atualizando Força Global Atual das Equipes...")
            team_records = [(t_id, state['elo'], state['games']) for t_id, state in team_state.items()]
            
            await conn.executemany("""
                INSERT INTO core.team_current_elo (team_id, current_elo, games_played, last_updated) 
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (team_id) DO UPDATE SET 
                    current_elo = EXCLUDED.current_elo, 
                    games_played = EXCLUDED.games_played, 
                    last_updated = NOW();
            """, team_records)
            
        await db.disconnect()
        logger.info(f"=== SUCESSO: O Pedigree Elo de {len(team_records)} equipas foi forjado ===")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(GlobalEloEngine().run_daily_update())