# betgenius-backend/workers/soccerdata_etl/extractors/clubelo_bot.py

import pandas as pd
import soccerdata as sd
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ClubEloExtractor:
    """
    Minerador de Força Relativa (Power Rating).
    Usa o ClubElo para baixar a pontuação exata de todos os times do mundo
    na data especificada.
    """
    def __init__(self, target_date=None):
        self.target_date = target_date if target_date else (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        self.elo = sd.ClubElo()

    def get_global_ratings(self) -> pd.DataFrame:
        logger.info(f"📈 [ELO-BOT] Baixando Power Ratings Globais para a data: {self.target_date}...")
        
        try:
            df = self.elo.read_by_date(self.target_date)
            df = df.reset_index()
            
            # Extrai O MÁXIMO da tabela Elo:
            # 'team' (nome limpo), 'elo' (pontuação de força atual), 'rank' (posição no mundo)
            cols_to_keep = ['team', 'country', 'level', 'elo', 'rank']
            
            # Limpa e foca no que importa
            clean_elo_df = df[cols_to_keep].copy()
            
            logger.info(f"✅ ELO Ratings extraídos. ({len(clean_elo_df)} times rankeados no mundo).")
            return clean_elo_df
            
        except Exception as e:
            logger.error(f"❌ Falha ao extrair ClubElo: {e}")
            return pd.DataFrame()