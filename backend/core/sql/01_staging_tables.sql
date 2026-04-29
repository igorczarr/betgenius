-- ==============================================================================
-- 1. TABELA DE QUARENTENA: BETEXPLORER (O Mestre das Odds e Placar)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS core.staging_bex_matches (
    id SERIAL PRIMARY KEY,
    league_url VARCHAR(255) NOT NULL,          -- Ex: /football/brazil/serie-a/
    match_date DATE NOT NULL,                  -- Data da partida
    raw_home_team VARCHAR(150) NOT NULL,       -- Nome exatamente como veio do BEX
    raw_away_team VARCHAR(150) NOT NULL,
    
    -- Resultados Finais (FT) e Parciais (HT)
    home_goals INT,
    away_goals INT,
    ht_home_goals INT,
    ht_away_goals INT,
    
    -- Closing Odds da Pinnacle (A "Verdade" do Mercado)
    odd_1_closing DECIMAL(6,3),
    odd_x_closing DECIMAL(6,3),
    odd_2_closing DECIMAL(6,3),
    odd_over_25_closing DECIMAL(6,3),
    odd_under_25_closing DECIMAL(6,3),
    
    -- Gestão de Estado
    fusion_status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, MATCHED, ERROR
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Evita duplicidade se rodarmos o scraper duas vezes no mesmo dia
    UNIQUE (match_date, raw_home_team, raw_away_team)
);

CREATE INDEX IF NOT EXISTS idx_bex_date_status ON core.staging_bex_matches(match_date, fusion_status);

-- ==============================================================================
-- 2. TABELA DE QUARENTENA: FBREF (O Mestre da Física do Jogo)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS core.staging_fbr_matches (
    id SERIAL PRIMARY KEY,
    league_url VARCHAR(255) NOT NULL,          -- Identificador da liga no FBref
    match_date DATE NOT NULL,
    raw_home_team VARCHAR(150) NOT NULL,       -- Nome exatamente como veio do FBref
    raw_away_team VARCHAR(150) NOT NULL,
    
    -- Placares (Usado apenas como chave de verificação de segurança na fusão)
    home_goals INT,
    away_goals INT,
    
    -- A Física Bruta (O Diferencial do nosso Fundo)
    xg_home DECIMAL(4,2),
    xg_away DECIMAL(4,2),
    home_shots INT,
    away_shots INT,
    home_shots_target INT,
    away_shots_target INT,
    home_corners INT,
    away_corners INT,
    home_yellow INT,
    away_yellow INT,
    home_red INT,
    away_red INT,
    home_fouls INT,
    away_fouls INT,
    referee VARCHAR(100),
    
    -- Gestão de Estado
    fusion_status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, MATCHED, ERROR
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE (match_date, raw_home_team, raw_away_team)
);

CREATE INDEX IF NOT EXISTS idx_fbr_date_status ON core.staging_fbr_matches(match_date, fusion_status);

-- ==============================================================================
-- 3. EXPANSÃO DA TABELA CORE (Preparação para os novos dados)
-- ==============================================================================
-- Garantindo que a tabela oficial tenha o campo de Árbitro se ainda não tiver
ALTER TABLE core.matches_history ADD COLUMN IF NOT EXISTS referee VARCHAR(100) DEFAULT 'Desconhecido';