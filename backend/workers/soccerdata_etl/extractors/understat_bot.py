# betgenius-backend/workers/soccerdata_etl/extractors/understat_bot.py

import pandas as pd
import soccerdata as sd
import logging
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

class UnderstatExtractor:
    """
    Minerador de Micro-Eventos e PPDA (Passes Per Defensive Action).
    Focado nas 5 Grandes Ligas (Big 5).
    Extrai coordenadas X/Y de chutes e métricas de pressão defensiva.
    """
    def __init__(self, target_date=None):
        self.season = config.ALL_SEASONS[-1]
        self.target_date = target_date if target_date else (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # O Understat SÓ suporta as Big 5 (Ligue 1, Premier League, La Liga, Serie A, Bundesliga)
        # Filtramos nossas ligas ativas contra a lista suportada por eles para evitar crash.
        UNDERSTAT_SUPPORTED = [
            "ENG-Premier League", "ESP-La Liga", "ITA-Serie A", 
            "GER-Bundesliga", "FRA-Ligue 1"
        ]
        
        if config.DEBUG_MODE:
            leagues_to_check = config.TEST_LEAGUES
        else:
            leagues_to_check = list(config.COMPETITIONS.values())
            
        # Intersecção: Pega apenas as ligas do nosso config que o Understat suporta
        self.valid_leagues = [L for L in leagues_to_check if L in UNDERSTAT_SUPPORTED]
        
        if not self.valid_leagues:
            logger.warning("⚠️ Nenhuma liga válida para o Understat na configuração atual.")
        else:
            logger.info(f"🔬 [UNDERSTAT] Inicializado para as ligas: {self.valid_leagues}")
            self.understat = sd.Understat(leagues=self.valid_leagues, seasons=self.season)

    def get_team_match_metrics(self) -> pd.DataFrame:
        """
        Extrai o NPxG (Non-Penalty xG), PPDA (Pressão) e Deep Completions.
        Essas métricas são ouro puro para a Alpha Matrix.
        """
        if not self.valid_leagues: return pd.DataFrame()
        
        logger.info(f"🛡️ Baixando métricas de Pressão e NPxG para a data {self.target_date}...")
        
        try:
            df = self.understat.read_team_match_stats()
            df = df.reset_index()
            
            # Ajusta a data para fazer o filtro do dia alvo
            df['date_str'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            daily_stats = df[df['date_str'] == self.target_date].copy()
            
            if daily_stats.empty:
                logger.info(f"Nenhum jogo no Understat para {self.target_date}.")
                return pd.DataFrame()
            
            # Filtra apenas o Néctar
            cols_to_keep = [
                'league', 'season', 'date_str', 'home_team', 'away_team',
                'home_np_xg', 'away_np_xg', 
                'home_ppda', 'away_ppda', 
                'home_deep_completions', 'away_deep_completions'
            ]
            
            clean_stats = daily_stats[cols_to_keep]
            logger.info(f"✅ Métricas avançadas de time extraídas ({len(clean_stats)} partidas).")
            return clean_stats
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair Team Metrics no Understat: {e}")
            return pd.DataFrame()

    def get_shot_events(self) -> pd.DataFrame:
        """
        Extrai CADA CHUTE dado nos jogos do dia.
        Contém a coordenada X/Y, minuto, jogador e a probabilidade de gol (xG) daquele chute exato.
        """
        if not self.valid_leagues: return pd.DataFrame()
        
        logger.info(f"🎯 Extraindo Coordenadas de Chutes (Eventos)...")
        
        try:
            # Atenção: Isso baixa os eventos da temporada inteira e o Pandas filtra.
            # Graças ao cache do soccerdata, a segunda execução será super rápida.
            df = self.understat.read_shot_events()
            df = df.reset_index()
            
            df['date_str'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            daily_shots = df[df['date_str'] == self.target_date].copy()
            
            if daily_shots.empty:
                return pd.DataFrame()
                
            cols_to_keep = [
                'league', 'game', 'minute', 'team', 'player', 
                'xg', 'location_x', 'location_y', 'body_part', 'situation', 'result'
            ]
            
            clean_shots = daily_shots[cols_to_keep]
            logger.info(f"✅ Mapeados {len(clean_shots)} chutes individuais no dia.")
            return clean_shots
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair Eventos de Chute: {e}")
            return pd.DataFrame()

# =========================================================
# TESTE ISOLADO
# =========================================================
if __name__ == "__main__":
    bot = UnderstatExtractor(target_date="2024-05-12") # Data da PL
    
    metrics = bot.get_team_match_metrics()
    if not metrics.empty:
        print("\n--- MÉTRICAS DE PRESSÃO (PPDA) E NPxG ---")
        print(metrics[['home_team', 'away_team', 'home_ppda', 'away_ppda', 'home_np_xg']].head())
    
    shots = bot.get_shot_events()
    if not shots.empty:
        print("\n--- COORDENADAS DE CHUTES (AMOSTRA) ---")
        print(shots.head())