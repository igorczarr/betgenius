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
    Motor S-Tier de Força Global (Burn-in Bayesian Elo).
    Calcula a força de todas as equipes do mundo simultaneamente.
    Usa um Fator-K dinâmico para corrigir distorções rapidamente.
    """
    def __init__(self):
        # Hierarquia Global Base
        self.TIER_BASE_ELO = {
            1: 1500.0, # Elite (Premier League, La Liga, Serie A, Bundesliga, UCL)
            2: 1350.0, # Fortes (Brasil, Portugal, Holanda, França, MLS)
            3: 1200.0  # Periféricas (Série B, Suécia, Noruega, Dinamarca, Japão)
        }
        
        self.FINANCIAL_BOOST_MAX = 100.0 # Bônus reduzido para não distorcer ligas sem dados financeiros
        self.HOME_ADVANTAGE = 60.0
        
        # Parâmetros de Volatilidade
        self.K_BURN_IN = 40.0 # Volatilidade alta para os primeiros 30 jogos (Acelera a descoberta de força)
        self.K_STANDARD = 20.0 # Volatilidade padrão para times estabelecidos

    def _get_league_tier(self, sport_key: str) -> int:
        tier_1 = ['soccer_epl', 'soccer_spain_la_liga', 'soccer_italy_serie_a', 'soccer_germany_bundesliga', 'soccer_uefa_champs_league']
        tier_2 = ['soccer_france_ligue_one', 'soccer_netherlands_eredivisie', 'soccer_portugal_primeira_liga', 'soccer_brazil_campeonato', 'soccer_usa_mls']
        tier_3 = ['soccer_brazil_serie_b', 'soccer_sweden_allsvenskan', 'soccer_norway_eliteserien', 'soccer_denmark_superliga', 'soccer_japan_j_league']
        
        if sport_key in tier_1: return 1
        if sport_key in tier_2: return 2
        if sport_key in tier_3: return 3
        return 2 # Copas e Continentais herdam a força dos seus times

    def _calculate_expected_score(self, rating_a: float, rating_b: float) -> float:
        return 1.0 / (1.0 + math.pow(10.0, (rating_b - rating_a) / 400.0))

    def _calculate_margin_multiplier(self, goals_a: int, goals_b: int) -> float:
        margin = abs(goals_a - goals_b)
        if margin <= 1: return 1.0
        elif margin == 2: return 1.5
        else: return (11.0 + float(margin)) / 8.0

    async def initialize_schema(self, conn):
        logger.info("🛠️ Preparando Schema S-Tier de Elo Global...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS core.team_pedigree (
                team_id INTEGER PRIMARY KEY REFERENCES core.teams(id),
                league_tier INTEGER,
                avg_wage_percentile NUMERIC(5, 4),
                base_starting_elo NUMERIC(10, 2),
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS core.team_current_elo (
                team_id INTEGER PRIMARY KEY REFERENCES core.teams(id),
                current_elo NUMERIC(10, 2),
                games_played INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS core.match_elo_history (
                match_id INTEGER PRIMARY KEY REFERENCES core.matches_history(id) ON DELETE CASCADE,
                home_elo_before NUMERIC(10, 2),
                away_elo_before NUMERIC(10, 2),
                home_elo_after NUMERIC(10, 2),
                away_elo_after NUMERIC(10, 2)
            );
        """)
        
        await conn.execute("TRUNCATE TABLE core.team_pedigree CASCADE;")
        await conn.execute("TRUNCATE TABLE core.team_current_elo CASCADE;")
        await conn.execute("TRUNCATE TABLE core.match_elo_history CASCADE;")

    async def calculate_base_pedigree(self, conn) -> tuple:
        """
        Gera as Priors Iniciais. Protegido contra falta de tabelas de salário.
        Retorna o dicionário de Elos e o dicionário de contagem de jogos.
        """
        logger.info("🧬 Calculando DNA Financeiro e Tiers de Iniciação...")
        
        # Verifica se a tabela de salários existe (pode não existir em bases recém-criadas)
        has_wages = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'fbref_squad' AND table_name = 'standings_wages'
            );
        """)
        
        if has_wages:
            query = """
                WITH TeamAverages AS (
                    SELECT t.id as team_id, l.sport_key, AVG(sw.wage_bill_annual) as avg_wage
                    FROM core.teams t
                    JOIN core.leagues l ON t.league_id = l.id
                    LEFT JOIN fbref_squad.standings_wages sw ON t.id = sw.team_id
                    GROUP BY t.id, l.sport_key
                ),
                RankedTeams AS (
                    SELECT team_id, sport_key, avg_wage,
                        CASE WHEN avg_wage IS NOT NULL THEN PERCENT_RANK() OVER(PARTITION BY sport_key ORDER BY avg_wage ASC)
                        ELSE NULL END as wage_percentile
                    FROM TeamAverages
                )
                SELECT team_id, sport_key, COALESCE(wage_percentile, 0.5) as wage_percentile
                FROM RankedTeams;
            """
        else:
            query = """
                SELECT t.id as team_id, l.sport_key, 0.5 as wage_percentile
                FROM core.teams t JOIN core.leagues l ON t.league_id = l.id;
            """
            
        teams_data = await conn.fetch(query)
        elo_cache = {}
        games_played_cache = {}
        pedigree_records = []
        
        for t in teams_data:
            t_id = t['team_id']
            sport_key = t['sport_key']
            wage_pct = float(t['wage_percentile'])
            
            if math.isnan(wage_pct): wage_pct = 0.5
                
            tier = self._get_league_tier(sport_key)
            base_elo = self.TIER_BASE_ELO[tier]
            
            # Só dá boost se realmente tivermos confiança no salário (wage_pct diferente de 0.5 cravado)
            boost = (self.FINANCIAL_BOOST_MAX * wage_pct) if wage_pct != 0.5 else 0.0
            starting_elo = base_elo + boost
            
            elo_cache[t_id] = starting_elo
            games_played_cache[t_id] = 0
            pedigree_records.append((t_id, tier, round(wage_pct, 4), round(starting_elo, 2)))
            
        await conn.executemany("""
            INSERT INTO core.team_pedigree (team_id, league_tier, avg_wage_percentile, base_starting_elo)
            VALUES ($1, $2, $3, $4)
        """, pedigree_records)
        
        return elo_cache, games_played_cache

    async def run_time_travel(self):
        logger.info("=========================================================")
        logger.info("⏳ MÁQUINA DO TEMPO: GERANDO ELO GLOBAL (2015 - PRESENTE)")
        logger.info("=========================================================")
        
        await db.connect()
        
        async with db.pool.acquire() as conn:
            await self.initialize_schema(conn)
            elo_cache, games_cache = await self.calculate_base_pedigree(conn)
            
            logger.info("📥 Carregando histórico térmico de confrontos...")
            matches = await conn.fetch("""
                SELECT id, match_date, home_team_id, away_team_id, home_goals, away_goals 
                FROM core.matches_history 
                WHERE home_goals IS NOT NULL AND away_goals IS NOT NULL AND status = 'FINISHED'
                ORDER BY match_date ASC, id ASC
            """)
            
            if not matches:
                logger.warning("Nenhum jogo finalizado encontrado para simulação.")
                await db.disconnect()
                return

            history_records = []
            
            # O Motor Dinâmico
            for match in matches:
                m_id = match['id']
                home_id = match['home_team_id']
                away_id = match['away_team_id']
                hg = int(match['home_goals'])
                ag = int(match['away_goals'])
                
                # Descoberta Automática de times que surgiram durante o histórico
                if home_id not in elo_cache: 
                    elo_cache[home_id] = 1200.0
                    games_cache[home_id] = 0
                if away_id not in elo_cache: 
                    elo_cache[away_id] = 1200.0
                    games_cache[away_id] = 0
                
                home_elo_before = elo_cache[home_id]
                away_elo_before = elo_cache[away_id]
                
                home_elo_adjusted = home_elo_before + self.HOME_ADVANTAGE
                
                expected_home = self._calculate_expected_score(home_elo_adjusted, away_elo_before)
                expected_away = 1.0 - expected_home
                
                if hg > ag: actual_home, actual_away = 1.0, 0.0
                elif hg < ag: actual_home, actual_away = 0.0, 1.0
                else: actual_home, actual_away = 0.5, 0.5
                
                margin_mult = self._calculate_margin_multiplier(hg, ag)
                
                # A MÁGICA DA ISONOMIA: Burn-in K-Factor
                # Se o time é novo na base, a volatilidade é alta para achar a força real
                k_home = self.K_BURN_IN if games_cache[home_id] < 30 else self.K_STANDARD
                k_away = self.K_BURN_IN if games_cache[away_id] < 30 else self.K_STANDARD
                
                home_elo_change = k_home * margin_mult * (actual_home - expected_home)
                away_elo_change = k_away * margin_mult * (actual_away - expected_away)
                
                elo_cache[home_id] += home_elo_change
                elo_cache[away_id] += away_elo_change
                
                games_cache[home_id] += 1
                games_cache[away_id] += 1
                
                history_records.append((
                    m_id, 
                    round(home_elo_before, 2), round(away_elo_before, 2), 
                    round(elo_cache[home_id], 2), round(elo_cache[away_id], 2)
                ))
            
            logger.info(f"💾 Gravando tensores de {len(history_records)} partidas no Data Warehouse (Copy)...")
            await conn.copy_records_to_table(
                'match_elo_history', schema_name='core',
                records=history_records,
                columns=['match_id', 'home_elo_before', 'away_elo_before', 'home_elo_after', 'away_elo_after']
            )
            
            logger.info("💾 Consolidando o Elo atual de todas as equipes...")
            current_elo_records = [(t_id, round(elo, 2), games_cache[t_id]) for t_id, elo in elo_cache.items()]
            await conn.executemany("""
                INSERT INTO core.team_current_elo (team_id, current_elo, games_played) VALUES ($1, $2, $3)
            """, current_elo_records)
            
        await db.disconnect()
        logger.info("=== CALIBRAÇÃO GLOBAL FINALIZADA COM SUCESSO ===")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(GlobalEloEngine().run_time_travel())