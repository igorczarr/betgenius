# betgenius-backend/workers/soccerdata_etl/extractors/sofifa_bot.py

import pandas as pd
import soccerdata as sd
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

class SoFIFAExtractor:
    """
    Minerador de Alternative Data (EA Sports FIFA Ratings).
    Extrai as notas gerais dos times (Ataque, Meio, Defesa) e 
    atributos microscópicos de jogadores (Velocidade, Agressão, Visão).
    """
    def __init__(self):
        if config.DEBUG_MODE:
            self.leagues = config.TEST_LEAGUES
            logger.info(f"🧪 [SOFIFA] Modo DEBUG. Focando em: {self.leagues}")
        else:
            self.leagues = list(config.COMPETITIONS.values())
            
        try:
            # versions="latest" garante que pegamos a nota atualizada da semana
            self.sofifa = sd.SoFIFA(leagues=self.leagues, versions="latest", no_cache=False)
        except Exception as e:
            logger.error(f"❌ [SOFIFA] Falha ao iniciar o motor: {e}")
            self.sofifa = None

    def get_team_ratings(self) -> pd.DataFrame:
        """
        Baixa o Rating Geral, Ataque, Meio-Campo e Defesa de cada time.
        Incluso: Velocidade de Construção, Pressão e Agressividade Tática.
        """
        if not self.sofifa: return pd.DataFrame()
        
        logger.info(f"🛡️ Baixando Ratings Táticos de Times no SoFIFA...")
        try:
            df = self.sofifa.read_team_ratings()
            df = df.reset_index()
            
            # Filtra os atributos táticos mais relevantes para Machine Learning
            cols_to_keep = [
                'league', 'team', 'overall', 'attack', 'midfield', 'defence',
                'build_up_speed', 'build_up_passing', 'chance_creation_crossing',
                'chance_creation_shooting', 'defence_pressure', 'defence_aggression',
                'starting_xi_average_age'
            ]
            
            # Garante que só pegaremos colunas que realmente vieram na requisição
            existing_cols = [c for c in cols_to_keep if c in df.columns]
            clean_team_ratings = df[existing_cols].copy()
            
            logger.info(f"✅ Ratings Táticos extraídos ({len(clean_team_ratings)} times mapeados).")
            return clean_team_ratings
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair Team Ratings no SoFIFA: {e}")
            return pd.DataFrame()

    def get_player_ratings(self) -> pd.DataFrame:
        """
        Baixa os atributos físicos e mentais individuais de cada jogador.
        Atenção: Operação pesada (Milhares de jogadores).
        """
        if not self.sofifa: return pd.DataFrame()
        
        logger.info(f"🏃‍♂️ Baixando Atributos Físicos e Mentais de Jogadores (Scouting)...")
        try:
            # Esta chamada varre os elencos de todos os times das ligas selecionadas
            df = self.sofifa.read_player_ratings()
            df = df.reset_index()
            
            # Seleciona os atributos que têm maior correlação com a performance real em campo
            kpis_to_keep = [
                'player', 'team', 'Overall rating', 'Potential', 
                'Sprint speed', 'Acceleration', 'Finishing', 'Shot power',
                'Vision', 'Short passing', 'Aggression', 'Stamina',
                'Standing tackle', 'Composure'
            ]
            
            existing_kpis = [c for c in kpis_to_keep if c in df.columns]
            clean_player_ratings = df[existing_kpis].copy()
            
            logger.info(f"✅ Atributos individuais extraídos ({len(clean_player_ratings)} jogadores escaneados).")
            return clean_player_ratings
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair Player Ratings no SoFIFA: {e}")
            return pd.DataFrame()

# =========================================================
# TESTE ISOLADO
# =========================================================
if __name__ == "__main__":
    bot = SoFIFAExtractor()
    
    # 1. Táticas dos Times
    team_ratings = bot.get_team_ratings()
    if not team_ratings.empty:
        print("\n--- RATING TÁTICO DOS TIMES (SOFIFA) ---")
        print(team_ratings[['team', 'overall', 'attack', 'defence', 'build_up_speed']].head())
    
    # 2. Atributos dos Jogadores
    player_ratings = bot.get_player_ratings()
    if not player_ratings.empty:
        print(f"\n--- ATRIBUTOS DE JOGADORES ({len(player_ratings)} encontrados) ---")
        print(player_ratings[['player', 'team', 'Overall rating', 'Sprint speed', 'Finishing']].head())