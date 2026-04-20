# betgenius-backend/workers/soccerdata_etl/extractors/whoscored_bot.py

import pandas as pd
import soccerdata as sd
import logging
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

class WhoScoredExtractor:
    """
    Minerador de Dados Atômicos da Opta (via WhoScored).
    Extrai Lesões/Suspensões (Missing Players) e o Event Stream completo
    (cada passe, desarme e chute com coordenadas no campo).
    """
    def __init__(self, target_date=None):
        self.season = config.ALL_SEASONS[-1]
        self.target_date = target_date if target_date else (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        if config.DEBUG_MODE:
            self.leagues = config.TEST_LEAGUES
            logger.info(f"🧪 [WHOSCORED] Modo DEBUG Ativado. Focando em: {self.leagues}")
        else:
            # Em produção, você adicionará as 25 ligas no config.py
            self.leagues = list(config.COMPETITIONS.values())
            
        try:
            # O WhoScored bane IPs rápido. Se você tiver um proxy (ex: BrightData),
            # instancie assim: proxy="http://user:pass@proxy.com:8000"
            self.ws = sd.WhoScored(leagues=self.leagues, seasons=self.season, no_cache=False)
        except Exception as e:
            logger.error(f"❌ [WHOSCORED] Falha ao iniciar (Possível ban de IP/Incapsula): {e}")
            self.ws = None

    def get_missing_players(self) -> pd.DataFrame:
        """
        A Mina de Ouro do Edge: Baixa a lista de lesionados e suspensos 
        dos jogos da rodada atual.
        """
        if not self.ws: return pd.DataFrame()
        
        logger.info(f"🚑 Baixando lista de Jogadores Lesionados/Suspensos...")
        try:
            # Puxa o calendário e filtra jogos que vão acontecer ou acabaram de acontecer
            df_schedule = self.ws.read_schedule()
            df_schedule = df_schedule.reset_index()
            
            df_schedule['date_str'] = pd.to_datetime(df_schedule['date']).dt.strftime('%Y-%m-%d')
            target_games = df_schedule[df_schedule['date_str'] == self.target_date]
            
            if target_games.empty:
                logger.info(f"Nenhum jogo agendado no WhoScored para {self.target_date}.")
                return pd.DataFrame()

            # Pega os IDs dos jogos alvo para não raspar a temporada inteira atoa
            game_ids = target_games['game_id'].tolist()
            
            # Raspa os desfalques apenas dos jogos do dia
            missing_df = self.ws.read_missing_players(match_id=game_ids)
            missing_df = missing_df.reset_index()
            
            logger.info(f"✅ Foram encontrados {len(missing_df)} desfalques mapeados para os jogos selecionados.")
            return missing_df
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair Missing Players: {e}")
            return pd.DataFrame()

    def get_opta_events(self) -> pd.DataFrame:
        """
        O Nível Atômico: Baixa cada ação (passe, desarme, drible) do jogo.
        Cuidado: Um único jogo pode retornar mais de 1.500 linhas.
        """
        if not self.ws: return pd.DataFrame()
        
        logger.info(f"📡 Baixando Data Feed da Opta (Eventos por Milissegundo)...")
        try:
            df_schedule = self.ws.read_schedule()
            df_schedule = df_schedule.reset_index()
            
            df_schedule['date_str'] = pd.to_datetime(df_schedule['date']).dt.strftime('%Y-%m-%d')
            target_games = df_schedule[df_schedule['date_str'] == self.target_date]
            
            if target_games.empty:
                return pd.DataFrame()

            game_ids = target_games['game_id'].tolist()
            
            # output_fmt="events" nos dá o DataFrame achatado padrão Opta
            events_df = self.ws.read_events(match_id=game_ids, output_fmt="events")
            events_df = events_df.reset_index()
            
            logger.info(f"✅ Event Feed baixado com sucesso. Total de ações extraídas: {len(events_df)}")
            return events_df
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair Eventos da Opta: {e}")
            return pd.DataFrame()

# =========================================================
# TESTE ISOLADO
# =========================================================
if __name__ == "__main__":
    # Teste para a data fixa
    bot = WhoScoredExtractor(target_date="2024-05-12")
    
    lesoes = bot.get_missing_players()
    if not lesoes.empty:
        print("\n--- DESFALQUES (LESÕES E SUSPENSÕES) ---")
        print(lesoes[['game', 'team', 'player', 'reason', 'status']].head(10))
    
    eventos = bot.get_opta_events()
    if not eventos.empty:
        print(f"\n--- OPTA EVENT FEED ({len(eventos)} ações mapeadas) ---")
        print(eventos[['game', 'minute', 'team', 'player', 'type', 'outcome_type']].head(15))