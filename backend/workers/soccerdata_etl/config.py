# betgenius-backend/workers/soccerdata_etl/config.py

import os
from datetime import datetime

# =====================================================================
# 1. CONFIGURAÇÕES DE DIRETÓRIO (STORAGE)
# =====================================================================
BASE_DIR = os.getcwd()
CACHE_DIR = os.path.join(BASE_DIR, "soccerdata_cache")

# Garante que a pasta de cache exista para evitar bans de IP
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Configurações globais para a lib soccerdata
SOCCERDATA_CONFIG = {
    "data_dir": CACHE_DIR,
    "no_cache": False,
    "no_store": False
}

# =====================================================================
# 2. LINHA DO TEMPO (HISTÓRICO S-TIER)
# =====================================================================
# Gera as temporadas desde 2015-2016 até a atual.
# Formato soccerdata: '1516', '1617', ... '2425'
def generate_seasons():
    current_year = datetime.now().year
    # Se estivemos após Julho, a temporada atual é a 202X-202X+1
    end_year = current_year if datetime.now().month < 7 else current_year + 1
    
    seasons = []
    for year in range(2015, end_year):
        start = str(year)[2:]
        end = str(year + 1)[2:]
        seasons.append(f"{start}{end}")
    return seasons

ALL_SEASONS = generate_seasons()

# =====================================================================
# 3. MAPA DE COMPETIÇÕES (A ÚNICA FONTE DE VERDADE)
# =====================================================================
# Traduz as chaves internas da BetGenius para o identificador do SoccerData.
# Resolvemos aqui o problema das Copas Internacionais (Prefixo INT-).
COMPETITIONS = {
    # TIER 1 - LIGAS NACIONAIS
    "soccer_epl": "ENG-Premier League",
    "soccer_spain_la_liga": "ESP-La Liga",
    "soccer_italy_serie_a": "ITA-Serie A",
    "soccer_germany_bundesliga": "GER-Bundesliga",
    
    # TIER 2
    "soccer_france_ligue_one": "FRA-Ligue 1",
    "soccer_netherlands_eredivisie": "NED-Eredivisie",
    "soccer_portugal_primeira_liga": "POR-Primeira Liga",
    "soccer_brazil_campeonato": "BRA-Serie A",
    "soccer_usa_mls": "USA-Major League Soccer",
    
    # TIER 3
    "soccer_brazil_serie_b": "BRA-Serie B",
    "soccer_sweden_allsvenskan": "SWE-Allsvenskan",
    "soccer_norway_eliteserien": "NOR-Eliteserien",
    "soccer_denmark_superliga": "DEN-Superliga",
    "soccer_japan_j_league": "JPN-J1 League",

    # CONTINENTAIS E COPAS (RESOLVIDO: Padrão Internacional)
    "soccer_uefa_champs_league": "INT-Champions League",
    "soccer_uefa_europa_league": "INT-Europa League",
    "soccer_conmebol_libertadores": "INT-Copa Libertadores",
    "soccer_conmebol_sudamericana": "INT-Copa Sudamericana",
    
    # SELEÇÕES
    "soccer_fifa_world_cup": "INT-World Cup",
    "soccer_conmebol_copa_america": "INT-Copa America",
    "soccer_uefa_euro": "INT-European Championship",
    "soccer_uefa_nations_league": "INT-UEFA Nations League",

    "soccer_eng_championship": "ENG-Championship",
    "soccer_eng_league_one": "ENG-League One",
    "soccer_eng_league_two": "ENG-League Two",
    "soccer_eng_fa_cup": "ENG-FA Cup",
    "soccer_eng_league_cup": "ENG-EFL Cup",
    "soccer_bel_jupiler": "BEL-Jupiler Pro League",
    "soccer_ger_2_bundesliga": "GER-2. Bundesliga",
}

# =====================================================================
# 4. MATRIZ DE EXTRAÇÃO (TEAM & PLAYER DATA)
# =====================================================================

# Quais relatórios de TIMES queremos baixar do FBref?
TEAM_STATS_TYPES = [
    "standard",      # Stats básicos + Advanced stats (xG, xGA)
    "shooting",      # Finalizações e precisão
    "defense",       # Desarmes, interceptações, pressões
    "keepers",       # Stats de goleiros
    "keepers_adv",   # Advanced Goalkeeping (Crucial para xG clean)
    "possession",    # Toques, dribles, carregadas
    "misc",          # Faltas, cartões, aéreos
    "wages"          # Salários (Se disponível para a liga)
]

# Quais campos de LÍDERES INDIVIDUAIS queremos focar?
# Nota: O robô baixará o dataset de jogadores e filtraremos estes KPIs.
PLAYER_KPI_TARGETS = {
    "gols": "goals",
    "assistencias": "assists",
    "gols_90": "goals_per90",
    "xg_90": "xg_per90",
    "faltas_cometidas": "fouls",
    "faltas_sofridas": "fouled",
    "cartoes_amarelos": "cards_yellow"
}

# =====================================================================
# 5. PRIORIZAÇÃO (MODO TESTE)
# =====================================================================
# Ative isto para testar o pipeline apenas com uma liga antes do dump total.
DEBUG_MODE = True
TEST_LEAGUES = ["ENG-Premier League"] # Apenas Premier League para validar