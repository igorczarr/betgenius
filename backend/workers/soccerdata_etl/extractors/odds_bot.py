# betgenius-backend/workers/soccerdata_etl/extractors/odds_bot.py

import pandas as pd
import soccerdata as sd
import logging
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

class OddsExtractor:
    """
    Minerador de Closing Lines (Odds de Fechamento).
    Usa o pacote MatchHistory para ler os CSVs do football-data.co.uk.
    Extrai as cotas da Pinnacle (PSCH, PSCD, PSCA) e Bet365 (B365H, B365D, B365A).
    """
    def __init__(self, target_date=None):
        if config.DEBUG_MODE:
            self.leagues = config.TEST_LEAGUES
        else:
            self.leagues = list(config.COMPETITIONS.values())

        self.season = config.ALL_SEASONS[-1]
        self.target_date = target_date if target_date else (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Inicia o motor
        self.history = sd.MatchHistory(leagues=self.leagues, seasons=self.season)

    def get_closing_lines(self) -> pd.DataFrame:
        """Extrai as cotações máximas e as cotações de fechamento da Pinnacle e B365."""
        logger.info(f"🏦 [ODDS-BOT] Baixando Histórico Financeiro para a temporada {self.season}...")
        
        try:
            df = self.history.read_games()
            df = df.reset_index()
            
            # Formata a data para filtrar apenas os jogos do dia alvo
            df['date_str'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            daily_odds = df[df['date_str'] == self.target_date].copy()
            
            if daily_odds.empty:
                logger.warning(f"⚠️ Nenhuma odd encontrada para a data {self.target_date}.")
                return pd.DataFrame()

            # ========================================================
            # EXTRAÇÃO MÁXIMA (O SEGREDO QUANTITATIVO)
            # ========================================================
            # Pinnacle Closing (S-Tier) -> PSCH, PSCD, PSCA
            # Bet365 Closing (Soft-Tier) -> B365H, B365D, B365A
            # Max Odds do Mercado (Para Caça de Bônus/Arbitragem) -> MaxH, MaxD, MaxA
            # Asian Handicap (Pinnacle) -> PSAH, PSAHD, PSAHA
            # ========================================================
            
            # Filtra apenas as colunas que realmente importam pro nosso banco de dados
            # Se uma liga menor não tiver Pinnacle (PSCH), o Pandas manterá como NaN, trataremos isso depois.
            cols_to_keep = ['league', 'season', 'date_str', 'home_team', 'away_team']
            target_odds = ['B365H', 'B365D', 'B365A', 'PSCH', 'PSCD', 'PSCA', 'MaxH', 'MaxD', 'MaxA', 'PSAH', 'PSAHA', 'PSAHD']
            
            # Adiciona apenas as colunas financeiras que existirem no DataFrame baixado
            for col in target_odds:
                if col in daily_odds.columns:
                    cols_to_keep.append(col)

            clean_odds_df = daily_odds[cols_to_keep]
            
            logger.info(f"✅ Odds de Fechamento extraídas. ({len(clean_odds_df)} partidas).")
            return clean_odds_df

        except Exception as e:
            logger.error(f"❌ Falha Crítica ao puxar Histórico de Odds: {e}")
            return pd.DataFrame()