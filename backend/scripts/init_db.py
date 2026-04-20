# betgenius-backend/scripts/init_db.py
import asyncio
import logging
import sys
from pathlib import Path

# Garante que o script consiga ler a pasta 'core'
sys.path.append(str(Path(__file__).parent.parent))
from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [DB-INIT] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# =================================================================================
# BETGENIUS HFT - DATABASE ARCHITECTURE (DDL)
# =================================================================================
SCHEMA_DDL = """
-- 1. DOMÍNIO: AUTH (Segurança S-Tier)
CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE IF NOT EXISTS auth.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'analyst' CHECK (role IN ('admin', 'quant', 'analyst')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS auth.sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    jwt_token TEXT NOT NULL,
    ip_address VARCHAR(45),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON auth.sessions(user_id);

-- 2. DOMÍNIO: CORE (Dicionários, Entidades e O Motor de Nomes)
CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE IF NOT EXISTS core.leagues (
    id SERIAL PRIMARY KEY,
    sport_key VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    tier SMALLINT NOT NULL CHECK (tier IN (1, 2, 3)),
    country VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS core.teams (
    id SERIAL PRIMARY KEY,
    canonical_name VARCHAR(150) UNIQUE NOT NULL,
    league_id INTEGER REFERENCES core.leagues(id),
    country VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS core.team_aliases (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES core.teams(id) ON DELETE CASCADE,
    alias_name VARCHAR(150) UNIQUE NOT NULL,
    bookmaker_source VARCHAR(50),
    confidence_score NUMERIC(5,2) DEFAULT 100.0
);

CREATE TABLE IF NOT EXISTS core.referees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) UNIQUE NOT NULL,
    league_id INTEGER REFERENCES core.leagues(id),
    matches_reffed INTEGER DEFAULT 0,
    avg_yellow_cards NUMERIC(5,2) DEFAULT 0.0,
    avg_red_cards NUMERIC(5,2) DEFAULT 0.0,
    avg_fouls_called NUMERIC(5,2) DEFAULT 0.0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS core.matches_history (
    id VARCHAR(100) PRIMARY KEY,
    league_id INTEGER REFERENCES core.leagues(id),
    home_team_id INTEGER REFERENCES core.teams(id),
    away_team_id INTEGER REFERENCES core.teams(id),
    referee_id INTEGER REFERENCES core.referees(id),
    kickoff_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) DEFAULT 'PRE-MATCH',
    home_score SMALLINT,
    away_score SMALLINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_matches_time ON core.matches_history(kickoff_time);
CREATE INDEX IF NOT EXISTS idx_matches_teams ON core.matches_history(home_team_id, away_team_id);

-- 3. DOMÍNIO: FBREF_SQUAD (As Estatísticas Coletivas)
CREATE SCHEMA IF NOT EXISTS fbref_squad;

CREATE TABLE IF NOT EXISTS fbref_squad.standings_wages (
    team_id INTEGER REFERENCES core.teams(id),
    season VARCHAR(20) NOT NULL,
    rank_pos SMALLINT,
    matches_played SMALLINT DEFAULT 0,
    wins SMALLINT, draws SMALLINT, losses SMALLINT,
    goals_for SMALLINT, goals_against SMALLINT,
    pts SMALLINT,
    pts_per_match NUMERIC(5,2),
    attendance INTEGER,
    wage_bill_annual NUMERIC(15,2),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (team_id, season)
);

CREATE TABLE IF NOT EXISTS fbref_squad.advanced_general (
    team_id INTEGER REFERENCES core.teams(id),
    season VARCHAR(20) NOT NULL,
    avg_age NUMERIC(4,1),
    possession_pct NUMERIC(5,2),
    xg_for NUMERIC(5,2),
    npxg_for NUMERIC(5,2),
    xag NUMERIC(5,2),
    npxg_plus_xag NUMERIC(5,2),
    prgc NUMERIC(6,2),
    prgp NUMERIC(6,2),
    PRIMARY KEY (team_id, season)
);

CREATE TABLE IF NOT EXISTS fbref_squad.offensive_metrics (
    team_id INTEGER REFERENCES core.teams(id),
    season VARCHAR(20) NOT NULL,
    shots_90 NUMERIC(5,2),
    sot_90 NUMERIC(5,2),
    sot_pct NUMERIC(5,2),
    goals_per_shot NUMERIC(5,2),
    avg_shot_distance NUMERIC(5,2),
    goals_minus_xg NUMERIC(5,2),
    PRIMARY KEY (team_id, season)
);

CREATE TABLE IF NOT EXISTS fbref_squad.defensive_metrics (
    team_id INTEGER REFERENCES core.teams(id),
    season VARCHAR(20) NOT NULL,
    ga_90 NUMERIC(5,2),
    sot_against NUMERIC(5,2),
    save_pct NUMERIC(5,2),
    clean_sheet_pct NUMERIC(5,2),
    psxg NUMERIC(5,2),
    PRIMARY KEY (team_id, season)
);

CREATE TABLE IF NOT EXISTS fbref_squad.misc_metrics (
    team_id INTEGER REFERENCES core.teams(id),
    season VARCHAR(20) NOT NULL,
    yellow_cards SMALLINT,
    red_cards SMALLINT,
    fouls_committed SMALLINT,
    fouls_drawn SMALLINT,
    crosses SMALLINT,
    tackles_won SMALLINT,
    pk_won SMALLINT,
    aerials_won_pct NUMERIC(5,2),
    PRIMARY KEY (team_id, season)
);

-- ---------------------------------------------------------------------------------
-- 4. DOMÍNIO: FBREF_PLAYER (Métricas de Jogadores Isoladas em Tabelas - Data Marts)
-- ---------------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS fbref_player;

-- TABELA 1: Gols
CREATE TABLE IF NOT EXISTS fbref_player.metric_goals (
    player_name VARCHAR(150) NOT NULL,
    team_id INTEGER REFERENCES core.teams(id) ON DELETE CASCADE,
    quantity SMALLINT DEFAULT 0,
    season VARCHAR(20) NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_name, team_id, season)
);

-- TABELA 2: Assistências
CREATE TABLE IF NOT EXISTS fbref_player.metric_assists (
    player_name VARCHAR(150) NOT NULL,
    team_id INTEGER REFERENCES core.teams(id) ON DELETE CASCADE,
    quantity SMALLINT DEFAULT 0,
    season VARCHAR(20) NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_name, team_id, season)
);

-- TABELA 3: Gols + Assistências
CREATE TABLE IF NOT EXISTS fbref_player.metric_goals_assists (
    player_name VARCHAR(150) NOT NULL,
    team_id INTEGER REFERENCES core.teams(id) ON DELETE CASCADE,
    quantity SMALLINT DEFAULT 0,
    season VARCHAR(20) NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_name, team_id, season)
);

-- TABELA 4: Expected Goals p/ 90 min (xG/90)
CREATE TABLE IF NOT EXISTS fbref_player.metric_xg_90 (
    player_name VARCHAR(150) NOT NULL,
    team_id INTEGER REFERENCES core.teams(id) ON DELETE CASCADE,
    quantity NUMERIC(5,2) DEFAULT 0.0,
    season VARCHAR(20) NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_name, team_id, season)
);

-- TABELA 5: Chutes p/ 90 min (Shots/90)
CREATE TABLE IF NOT EXISTS fbref_player.metric_shots_90 (
    player_name VARCHAR(150) NOT NULL,
    team_id INTEGER REFERENCES core.teams(id) ON DELETE CASCADE,
    quantity NUMERIC(5,2) DEFAULT 0.0,
    season VARCHAR(20) NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_name, team_id, season)
);

-- TABELA 6: Faltas Cometidas
CREATE TABLE IF NOT EXISTS fbref_player.metric_fouls_committed (
    player_name VARCHAR(150) NOT NULL,
    team_id INTEGER REFERENCES core.teams(id) ON DELETE CASCADE,
    quantity SMALLINT DEFAULT 0,
    season VARCHAR(20) NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_name, team_id, season)
);

-- TABELA 7: Faltas Sofridas
CREATE TABLE IF NOT EXISTS fbref_player.metric_fouls_drawn (
    player_name VARCHAR(150) NOT NULL,
    team_id INTEGER REFERENCES core.teams(id) ON DELETE CASCADE,
    quantity SMALLINT DEFAULT 0,
    season VARCHAR(20) NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_name, team_id, season)
);

-- TABELA 8: Cartões Amarelos
CREATE TABLE IF NOT EXISTS fbref_player.metric_yellow_cards (
    player_name VARCHAR(150) NOT NULL,
    team_id INTEGER REFERENCES core.teams(id) ON DELETE CASCADE,
    quantity SMALLINT DEFAULT 0,
    season VARCHAR(20) NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (player_name, team_id, season)
);

-- 5. DOMÍNIO: QUANT_ML (A Feature Store da Regressão Logística)
CREATE SCHEMA IF NOT EXISTS quant_ml;

CREATE TABLE IF NOT EXISTS quant_ml.feature_store (
    match_id VARCHAR(100) PRIMARY KEY REFERENCES core.matches_history(id) ON DELETE CASCADE,
    
    rodada SMALLINT,
    pos_tabela_home SMALLINT,
    pos_tabela_away SMALLINT,
    
    avg_9_goals_home NUMERIC(5,2),
    avg_9_goals_conc_home NUMERIC(5,2),
    avg_9_goals_away NUMERIC(5,2),
    avg_9_goals_conc_away NUMERIC(5,2),
    
    avg_9_over25_home NUMERIC(5,2),
    avg_9_over25_away NUMERIC(5,2),
    
    avg_9_win_home NUMERIC(5,2),
    avg_9_win_away NUMERIC(5,2),
    
    avg_9_btts_home NUMERIC(5,2),
    avg_9_btts_away NUMERIC(5,2),
    
    implicity_prob_home NUMERIC(5,2),
    implicity_prob_draw NUMERIC(5,2),
    implicity_prob_away NUMERIC(5,2),
    
    target_home_win SMALLINT CHECK (target_home_win IN (0, 1)),
    target_draw SMALLINT CHECK (target_draw IN (0, 1)),
    target_away_win SMALLINT CHECK (target_away_win IN (0, 1)),
    target_over_15 SMALLINT CHECK (target_over_15 IN (0, 1)),
    target_over_25 SMALLINT CHECK (target_over_25 IN (0, 1)),
    target_over_35 SMALLINT CHECK (target_over_35 IN (0, 1)),
    target_btts SMALLINT CHECK (target_btts IN (0, 1)),
    
    is_processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_feature_unprocessed ON quant_ml.feature_store(is_processed) WHERE is_processed = FALSE;
"""

async def initialize_database():
    """Conecta ao PostgreSQL, cria a estrutura e fecha a conexão."""
    logger.info("🏗️ Iniciando a construção da infraestrutura do banco de dados (Neon.tech)...")
    await db.connect()
    
    try:
        # Pega uma conexão do pool e executa o bloco DDL massivo
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(SCHEMA_DDL)
                logger.info("✅ Estrutura Dimensional criada com sucesso!")
                logger.info("🛡️ Domínio fbref_player particionado em 8 tabelas isoladas para leitura rápida.")
    except Exception as e:
        logger.error(f"❌ Falha ao erguer a infraestrutura: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(initialize_database())