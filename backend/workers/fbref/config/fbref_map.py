# betgenius-backend/workers/fbref/config/fbref_map.py

"""
=====================================================================
BETGENIUS HFT - GLOBAL NAVIGATION MAP (NÍVEL S)
Mapeamento Estático de IDs (FBref), Códigos (Football-Data) e Tiers
=====================================================================
"""

# =====================================================================
# 1. AGRUPAMENTOS POR TIER (Prioridade de Coleta)
# =====================================================================
LEAGUES_TIER_1 = [
    "soccer_epl", 
    "soccer_spain_la_liga", 
    "soccer_italy_serie_a", 
    "soccer_germany_bundesliga", 
    "soccer_uefa_champs_league"
]

LEAGUES_TIER_2 = [
    "soccer_france_ligue_one", 
    "soccer_netherlands_eredivisie",
    "soccer_portugal_primeira_liga", 
    "soccer_brazil_campeonato",
    "soccer_usa_mls"
]

LEAGUES_TIER_3 = [
    "soccer_brazil_serie_b", 
    "soccer_sweden_allsvenskan",
    "soccer_norway_eliteserien", 
    "soccer_denmark_superliga",
    "soccer_japan_j_league"
]

LEAGUES_INTL = [
    "soccer_uefa_europa_league",
    "soccer_conmebol_libertadores",
    "soccer_conmebol_sudamericana",
    "soccer_fifa_world_cup", 
    "soccer_conmebol_copa_america",
    "soccer_uefa_euro_qualifications",
    "soccer_uefa_nations_league"
]

# =====================================================================
# 2. CONFIGURAÇÃO MATEMÁTICA E ROTEAMENTO (A Única Fonte de Verdade)
# =====================================================================
# id: O código interno do FBref para a liga.
# name: O slug exato usado na URL do FBref.
# cross_year: Define se o calendário cruza o ano (Ex: 2023-2024 na Europa, ou só 2023 no Brasil).
# fd_code: Código do arquivo CSV no portal football-data.co.uk (None se não houver cobertura).
# =====================================================================
LEAGUE_CONFIG = {
    # TIER 1
    "soccer_epl": {"id": "9", "name": "Premier-League", "cross_year": True, "fd_code": "E0"},
    "soccer_spain_la_liga": {"id": "12", "name": "La-Liga", "cross_year": True, "fd_code": "SP1"},
    "soccer_italy_serie_a": {"id": "11", "name": "Serie-A", "cross_year": True, "fd_code": "I1"},
    "soccer_germany_bundesliga": {"id": "20", "name": "Bundesliga", "cross_year": True, "fd_code": "D1"},
    "soccer_uefa_champs_league": {"id": "8", "name": "Champions-League", "cross_year": True, "fd_code": None},
    
    # TIER 2
    "soccer_france_ligue_one": {"id": "13", "name": "Ligue-1", "cross_year": True, "fd_code": "F1"},
    "soccer_netherlands_eredivisie": {"id": "23", "name": "Eredivisie", "cross_year": True, "fd_code": "N1"},
    "soccer_portugal_primeira_liga": {"id": "32", "name": "Primeira-Liga", "cross_year": True, "fd_code": "P1"},
    "soccer_brazil_campeonato": {"id": "24", "name": "Serie-A", "cross_year": False, "fd_code": "BRA"},
    "soccer_usa_mls": {"id": "22", "name": "Major-League-Soccer", "cross_year": False, "fd_code": "USA"},
    
    # TIER 3
    "soccer_brazil_serie_b": {"id": "38", "name": "Serie-B", "cross_year": False, "fd_code": None},
    "soccer_sweden_allsvenskan": {"id": "29", "name": "Allsvenskan", "cross_year": False, "fd_code": "SWE"},
    "soccer_norway_eliteserien": {"id": "28", "name": "Eliteserien", "cross_year": False, "fd_code": "NOR"},
    "soccer_denmark_superliga": {"id": "50", "name": "Superliga", "cross_year": True, "fd_code": "DNK"},
    "soccer_japan_j_league": {"id": "40", "name": "J1-League", "cross_year": False, "fd_code": "JPN"},
    
    # CONTINENTAIS E COPAS
    "soccer_uefa_europa_league": {"id": "19", "name": "Europa-League", "cross_year": True, "fd_code": None},
    "soccer_conmebol_libertadores": {"id": "14", "name": "Copa-Libertadores", "cross_year": False, "fd_code": None},
    "soccer_conmebol_sudamericana": {"id": "106", "name": "Copa-Sudamericana", "cross_year": False, "fd_code": None},
    
    # INTERNACIONAIS (SELEÇÕES)
    "soccer_fifa_world_cup": {"id": "1", "name": "World-Cup", "cross_year": False, "fd_code": None},
    "soccer_conmebol_copa_america": {"id": "68", "name": "Copa-America", "cross_year": False, "fd_code": None},
    "soccer_uefa_euro_qualifications": {"id": "676", "name": "UEFA-Euro-Qualifying", "cross_year": False, "fd_code": None},
    "soccer_uefa_nations_league": {"id": "138", "name": "UEFA-Nations-League", "cross_year": True, "fd_code": None}
}

# Ligas que usam "Master CSVs" no Football-Data (Agrupam todos os anos em um arquivo só)
FD_EXTRA_LEAGUES = ["BRA", "USA", "SWE", "NOR", "DNK", "JPN"]

# =====================================================================
# 3. CAMUFLAGEM HTTP/2 (FINGERPRINTS DE NAVEGADORES)
# =====================================================================
USER_AGENTS = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Safari Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/124.0.0.0 Safari/537.36",
    # Firefox Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0"
]

def build_target_url(sport_key: str, year: int) -> tuple:
    """
    Constrói a URL cirúrgica para extração do FBref e a string da temporada.
    Retorna: (URL_completa, "Ano-Ano" ou "Ano")
    """
    config = LEAGUE_CONFIG.get(sport_key)
    if not config:
        raise ValueError(f"⚠️ Liga {sport_key} não está mapeada no fbref_map.py")
        
    if config["cross_year"]:
        season_str = f"{year}-{year+1}"
    else:
        season_str = str(year)
        
    url = f"https://fbref.com/en/comps/{config['id']}/{season_str}/{season_str}-{config['name']}-Stats"
    
    return url, season_str