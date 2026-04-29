# betgenius-backend/workers/scrapers/config/scraping_config.py

"""
=============================================================================
 ⚙️ CENTRAL DE COMANDO DE SCRAPING (GLOBAL REGISTRY)
=============================================================================
"""

from typing import Dict, Any
from datetime import datetime

class ScrapingConfig:
    
    BEX_TARGET_COLS = [
        "match_date", "home_team", "away_team", 
        "ft_home_goals", "ft_away_goals", "ht_home_goals", "ht_away_goals",
        "odd_1_closing", "odd_x_closing", "odd_2_closing",
        "odd_over_25_closing", "odd_under_25_closing",
        "odd_ah_home_closing", "odd_ah_away_closing", "ah_line"
    ]

    FBR_TARGET_COLS = [
        "match_date", "home_team", "away_team",
        "xg_home", "xg_away", "shots_home", "shots_away",
        "shots_target_home", "shots_target_away", "corners_home", "corners_away",
        "yellow_cards_home", "yellow_cards_away", "red_cards_home", "red_cards_away",
        "fouls_home", "fouls_away", "referee"
    ]

    # O REGISTRO UNIVERSAL DE LIGAS (BEX Path + FBR Name + FBR ID)
    LEAGUE_REGISTRY: Dict[str, Dict[str, Any]] = {
        # === TIER 1: BIG 5 EUROPE ===
        "ENG_PR":  {"bex_path": "england/premier-league", "fbr_name": "ENG-Premier League", "fbr_id": "9", "calendar_year": False},
        "ESP_PR":  {"bex_path": "spain/laliga", "fbr_name": "ESP-La Liga", "fbr_id": "12", "calendar_year": False},
        "GER_BU":  {"bex_path": "germany/bundesliga", "fbr_name": "GER-Bundesliga", "fbr_id": "20", "calendar_year": False},
        "ITA_SA":  {"bex_path": "italy/serie-a", "fbr_name": "ITA-Serie A", "fbr_id": "11", "calendar_year": False},
        "FRA_L1":  {"bex_path": "france/ligue-1", "fbr_name": "FRA-Ligue 1", "fbr_id": "13", "calendar_year": False},

        # === TIER 2: EUROPE SECONDARY ===
        "ENG_CH":  {"bex_path": "england/championship", "fbr_name": "ENG-Championship", "fbr_id": "10", "calendar_year": False},
        "ITA_SB":  {"bex_path": "italy/serie-b", "fbr_name": "ITA-Serie B", "fbr_id": "18", "calendar_year": False},
        "GER_B2":  {"bex_path": "germany/2-bundesliga", "fbr_name": "GER-2. Bundesliga", "fbr_id": "33", "calendar_year": False},
        "ESP_S2":  {"bex_path": "spain/laliga2", "fbr_name": "ESP-Segunda División", "fbr_id": "17", "calendar_year": False},
        "POR_PR":  {"bex_path": "portugal/liga-portugal", "fbr_name": "POR-Primeira Liga", "fbr_id": "32", "calendar_year": False},
        "NED_ER":  {"bex_path": "netherlands/eredivisie", "fbr_name": "NED-Eredivisie", "fbr_id": "23", "calendar_year": False},
        "TUR_SL":  {"bex_path": "turkey/super-lig", "fbr_name": "TUR-Süper Lig", "fbr_id": "26", "calendar_year": False},
        "BEL_PL":  {"bex_path": "belgium/jupiler-pro-league", "fbr_name": "BEL-Belgian Pro League", "fbr_id": "37", "calendar_year": False},
        "GRE_SL":  {"bex_path": "greece/super-league", "fbr_name": "GRE-Super League Greece", "fbr_id": "27", "calendar_year": False},
        "SCO_PR":  {"bex_path": "scotland/premiership", "fbr_name": "SCO-Scottish Premiership", "fbr_id": "4", "calendar_year": False},
        "RUS_PR":  {"bex_path": "russia/premier-league", "fbr_name": "RUS-Russian Premier League", "fbr_id": "30", "calendar_year": False},

        # === TIER 3: AMÉRICAS ===
        "BRA_SA":  {"bex_path": "brazil/serie-a", "fbr_name": "BRA-Campeonato Brasileiro Série A", "fbr_id": "24", "calendar_year": True},
        "BRA_SB":  {"bex_path": "brazil/serie-b", "fbr_name": "BRA-Campeonato Brasileiro Série B", "fbr_id": "38", "calendar_year": True},
        "ARG_LP":  {"bex_path": "argentina/liga-profesional", "fbr_name": "ARG-Liga Profesional de Fútbol", "fbr_id": "21", "calendar_year": True},
        "COL_PA":  {"bex_path": "colombia/primera-a", "fbr_name": "COL-Categoría Primera A", "fbr_id": "41", "calendar_year": True},
        "CHI_PD":  {"bex_path": "chile/primera-division", "fbr_name": "CHI-Liga de Primera", "fbr_id": "35", "calendar_year": True},
        "URU_PD":  {"bex_path": "uruguay/primera-division", "fbr_name": "URU-Liga AUF Uruguaya", "fbr_id": "46", "calendar_year": True},
        "MEX_LM":  {"bex_path": "mexico/liga-mx", "fbr_name": "MEX-Liga MX", "fbr_id": "31", "calendar_year": False},
        "USA_MLS": {"bex_path": "usa/mls", "fbr_name": "USA-Major League Soccer", "fbr_id": "22", "calendar_year": True},

        # === TIER 4: ÁSIA & NÓRDICOS ===
        "JPN_J1":  {"bex_path": "japan/j1-league", "fbr_name": "JPN-J1 League", "fbr_id": "40", "calendar_year": True},
        "KOR_K1":  {"bex_path": "south-korea/k-league-1", "fbr_name": "KOR-K League 1", "fbr_id": "55", "calendar_year": True},
        "CHN_SL":  {"bex_path": "china/super-league", "fbr_name": "CHN-Chinese Super League", "fbr_id": "42", "calendar_year": True},
        "AUS_AL":  {"bex_path": "australia/a-league", "fbr_name": "AUS-A-League Men", "fbr_id": "65", "calendar_year": False},
        "SWE_AL":  {"bex_path": "sweden/allsvenskan", "fbr_name": "SWE-Allsvenskan", "fbr_id": "29", "calendar_year": True},
        "NOR_EL":  {"bex_path": "norway/eliteserien", "fbr_name": "NOR-Eliteserien", "fbr_id": "28", "calendar_year": True},
        "DEN_SL":  {"bex_path": "denmark/superliga", "fbr_name": "DEN-Danish Superliga", "fbr_id": "50", "calendar_year": False},

        # === TIER 5: COPAS INTERNACIONAIS ===
        "INT_UCL": {"bex_path": "europe/champions-league", "fbr_name": "INT-UEFA Champions League", "fbr_id": "8", "calendar_year": False},
        "INT_UEL": {"bex_path": "europe/europa-league", "fbr_name": "INT-UEFA Europa League", "fbr_id": "19", "calendar_year": False},
        "INT_UEC": {"bex_path": "europe/europa-conference-league", "fbr_name": "INT-UEFA Conference League", "fbr_id": "882", "calendar_year": False},
        "INT_LIB": {"bex_path": "south-america/copa-libertadores", "fbr_name": "INT-Copa Libertadores", "fbr_id": "14", "calendar_year": True},
        "INT_SUD": {"bex_path": "south-america/copa-sudamericana", "fbr_name": "INT-Copa Sudamericana", "fbr_id": "54", "calendar_year": True},

        # === TIER 6: SELEÇÕES ===
        "NAT_WC":  {"bex_path": "world/world-cup", "fbr_name": "INT-FIFA World Cup", "fbr_id": "1", "calendar_year": True},
        "NAT_EUR": {"bex_path": "europe/euro", "fbr_name": "INT-UEFA European Championship", "fbr_id": "676", "calendar_year": True},
        "NAT_CPA": {"bex_path": "south-america/copa-america", "fbr_name": "INT-Copa América", "fbr_id": "685", "calendar_year": True},
        "NAT_UNL": {"bex_path": "europe/uefa-nations-league", "fbr_name": "INT-UEFA Nations League", "fbr_id": "683", "calendar_year": False},
    }

    @classmethod
    def get_bex_url(cls, league_code: str, year: int) -> str:
        if league_code not in cls.LEAGUE_REGISTRY: return ""
        info = cls.LEAGUE_REGISTRY[league_code]
        base_path = info["bex_path"]
        if info["calendar_year"]:
            season_str = str(year)
        else:
            current_month = datetime.now().month
            start_y = year - 1 if current_month < 7 else year
            season_str = f"{start_y}-{start_y+1}"
        return f"https://www.betexplorer.com/football/{base_path}-{season_str}/results/"

    @classmethod
    def get_fbref_params(cls, league_code: str, year: int) -> Dict[str, str]:
        if league_code not in cls.LEAGUE_REGISTRY:
            raise ValueError(f"Liga {league_code} não registrada.")
        info = cls.LEAGUE_REGISTRY[league_code]
        if info["calendar_year"]:
            season_str = str(year)
        else:
            current_month = datetime.now().month
            start_y = year - 1 if current_month < 8 else year
            season_str = f"{str(start_y)[-2:]}{str(start_y+1)[-2:]}"
        return {
            "league": info["fbr_name"],
            "season": season_str
        }

    @classmethod
    def get_all_active_leagues(cls) -> list:
        return list(cls.LEAGUE_REGISTRY.keys())