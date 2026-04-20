# betgenius-backend/workers/feature_engineering/club_pedigree_engine.py

import asyncio
import logging
import sys
import math
from pathlib import Path
from dotenv import load_dotenv

# Força o encoding UTF-8 no Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')

# Carrega o .env corretamente de qualquer lugar
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)

# Adiciona o backend ao path para importações absolutas
sys.path.append(str(BASE_DIR))

from core.database import db
# Ajuste do import do config do fbref para usar o que temos
from workers.fbref.config.fbref_map import LEAGUES_TIER_1, LEAGUES_TIER_2, LEAGUES_TIER_3

logging.basicConfig(level=logging.INFO, format="%(asctime)s [PEDIGREE-ENGINE] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class ClubPedigreeEngine:
    """
    Motor S-Tier de Hierarquia e Força Relativa (Bayesian Prior Elo).
    Define o peso da camisa cruzando Folha Salarial e Tiers de Liga, 
    garantindo que times de prateleiras diferentes jamais se cruzem artificialmente.
    """
    def __init__(self):
        # A Gravidade das Ligas (Priors)
        self.TIER_BASE_ELO = {
            1: 1500.0, # Elite Europeia
            2: 1350.0, # Ligas Fortes Fora do Eixo (Brasil, Holanda)
            3: 1200.0  # Ligas Periféricas e Segundas Divisões
        }
        self.FINANCIAL_BOOST_MAX = 150.0 # Bônus máximo de Elo para os times mais ricos da liga
        
        # Parâmetros Dinâmicos do Elo
        self.K_FACTOR = 20.0
        self.HOME_ADVANTAGE = 60.0

    async def initialize_schema(self, conn):
        """Prepara o terreno no Data Warehouse para a Matriz Alfa."""
        logger.info("🛠️ Preparando Schema do Pedigree (Tabelas de Força)...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS core.team_pedigree (
                team_id INTEGER PRIMARY KEY REFERENCES core.teams(id),
                league_tier INTEGER,
                avg_wage_percentile NUMERIC(5, 4),
                base_starting_elo NUMERIC(10, 2),
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS core.team_current_elo (
                team_id INTEGER PRIMARY KEY REFERENCES core.teams(id),
                current_elo NUMERIC(10, 2),
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS core.match_elo_history (
                match_id INTEGER PRIMARY KEY REFERENCES core.matches_history(id) ON DELETE CASCADE,
                home_elo_before NUMERIC(10, 2),
                away_elo_before NUMERIC(10, 2),
                home_elo_after NUMERIC(10, 2),
                away_elo_after NUMERIC(10, 2)
            );
        """)
        
        # Limpa as tabelas para recalcular do zero (sem dar truncate em matches_history!)
        await conn.execute("TRUNCATE TABLE core.team_pedigree CASCADE;")
        await conn.execute("TRUNCATE TABLE core.team_current_elo CASCADE;")
        await conn.execute("TRUNCATE TABLE core.match_elo_history CASCADE;")

    def _get_league_tier(self, sport_key: str) -> int:
        if sport_key in LEAGUES_TIER_1: return 1
        if sport_key in LEAGUES_TIER_2: return 2
        if sport_key in LEAGUES_TIER_3: return 3
        return 2 # Default seguro para copas e ligas desconhecidas

    def _calculate_expected_score(self, rating_a: float, rating_b: float) -> float:
        return 1.0 / (1.0 + math.pow(10.0, (rating_b - rating_a) / 400.0))

    def _calculate_margin_multiplier(self, goals_a: int, goals_b: int) -> float:
        margin = abs(goals_a - goals_b)
        if margin <= 1: return 1.0
        elif margin == 2: return 1.5
        else: return (11.0 + margin) / 8.0

    async def calculate_base_pedigree(self, conn) -> dict:
        """
        O Cérebro Financeiro: Lê os salários do FBref, calcula o percentil de riqueza
        de cada time e forja o Elo Inicial (Priors) baseado no Sangue Azul.
        Se os salários não estiverem disponíveis, assume o meio da tabela.
        """
        logger.info("🧬 Calculando Pedigree e Teto Financeiro dos Clubes...")
        
        query = """
            WITH TeamAverages AS (
                SELECT 
                    t.id as team_id,
                    l.sport_key,
                    AVG(sw.wage_bill_annual) as avg_wage
                FROM core.teams t
                JOIN core.leagues l ON t.league_id = l.id
                LEFT JOIN fbref_squad.standings_wages sw ON t.id = sw.team_id
                GROUP BY t.id, l.sport_key
            ),
            RankedTeams AS (
                SELECT 
                    team_id,
                    sport_key,
                    avg_wage,
                    CASE 
                        WHEN avg_wage IS NOT NULL THEN PERCENT_RANK() OVER(PARTITION BY sport_key ORDER BY avg_wage ASC)
                        ELSE NULL 
                    END as wage_percentile
                FROM TeamAverages
            )
            SELECT team_id, sport_key, COALESCE(wage_percentile, 0.5) as wage_percentile
            FROM RankedTeams;
        """
        
        teams_data = await conn.fetch(query)
        starting_elos = {}
        pedigree_records = []
        
        for t in teams_data:
            t_id = t['team_id']
            sport_key = t['sport_key']
            wage_pct = float(t['wage_percentile'])
            
            # Blindagem: se o banco retornou NaN, forçamos o valor neutro 0.5 (50% de bônus financeiro)
            if math.isnan(wage_pct): wage_pct = 0.5
                
            tier = self._get_league_tier(sport_key)
            base_elo = self.TIER_BASE_ELO[tier]
            
            starting_elo = base_elo + (self.FINANCIAL_BOOST_MAX * wage_pct)
            
            starting_elos[t_id] = starting_elo
            pedigree_records.append((t_id, tier, round(wage_pct, 4), round(starting_elo, 2)))
            
        await conn.executemany("""
            INSERT INTO core.team_pedigree (team_id, league_tier, avg_wage_percentile, base_starting_elo)
            VALUES ($1, $2, $3, $4)
        """, pedigree_records)
        
        return starting_elos

    async def run_time_travel(self):
        """Simula a história usando as Priors Bayesianas como ponto de partida."""
        logger.info("[INIT] INICIANDO MÁQUINA DO TEMPO: Dimensionando a Hierarquia Global")
        
        await db.connect()
        
        async with db.pool.acquire() as conn:
            await self.initialize_schema(conn)
            
            # 1. Gera a Hierarquia Justa
            elo_cache = await self.calculate_base_pedigree(conn)
            
            # 2. Puxa os Jogos Históricos (Blindado para ignorar jogos sem placar)
            logger.info("📥 Carregando histórico de confrontos para simulação termodinâmica...")
            matches = await conn.fetch("""
                SELECT id, match_date, home_team_id, away_team_id, home_goals, away_goals 
                FROM core.matches_history 
                WHERE home_goals IS NOT NULL AND away_goals IS NOT NULL
                ORDER BY match_date ASC, id ASC
            """)
            
            if not matches:
                logger.warning("⚠️ Nenhum jogo com placar encontrado na base 'matches_history'.")
                await db.disconnect()
                return

            history_records = []
            
            # 3. O Motor de Transferência de Pontos
            for match in matches:
                m_id = match['id']
                home_id = match['home_team_id']
                away_id = match['away_team_id']
                hg = int(match['home_goals'])
                ag = int(match['away_goals'])
                
                # Se um time novo (sem pedigree financeiro) aparecer, joga pro Tier 3
                if home_id not in elo_cache: elo_cache[home_id] = 1200.0
                if away_id not in elo_cache: elo_cache[away_id] = 1200.0
                
                home_elo_before = elo_cache[home_id]
                away_elo_before = elo_cache[away_id]
                
                home_elo_adjusted = home_elo_before + self.HOME_ADVANTAGE
                
                expected_home = self._calculate_expected_score(home_elo_adjusted, away_elo_before)
                expected_away = 1.0 - expected_home
                
                if hg > ag: actual_home, actual_away = 1.0, 0.0
                elif hg < ag: actual_home, actual_away = 0.0, 1.0
                else: actual_home, actual_away = 0.5, 0.5
                
                margin_mult = self._calculate_margin_multiplier(hg, ag)
                home_elo_change = self.K_FACTOR * margin_mult * (actual_home - expected_home)
                
                elo_cache[home_id] += home_elo_change
                elo_cache[away_id] -= home_elo_change
                
                history_records.append((
                    m_id, 
                    round(home_elo_before, 2), round(away_elo_before, 2), 
                    round(elo_cache[home_id], 2), round(elo_cache[away_id], 2)
                ))
            
            # 4. Gravação em Massa (Bulk Copy Ultra-Rápido)
            logger.info("💾 Gravando Tensores Temporais no Data Warehouse (Copy)...")
            await conn.copy_records_to_table(
                'match_elo_history', schema_name='core',
                records=history_records,
                columns=['match_id', 'home_elo_before', 'away_elo_before', 'home_elo_after', 'away_elo_after']
            )
            
            logger.info("💾 Atualizando o Elo Atual de cada clube...")
            current_elo_records = [(t_id, round(elo, 2)) for t_id, elo in elo_cache.items()]
            await conn.executemany("""
                INSERT INTO core.team_current_elo (team_id, current_elo) VALUES ($1, $2)
            """, current_elo_records)
            
        await db.disconnect()
        logger.info("[DONE] MATRIZ DE PEDIGREE CONCLUÍDA. Hierarquia Estabelecida.")

if __name__ == "__main__":
    engine = ClubPedigreeEngine()
    asyncio.run(engine.run_time_travel())