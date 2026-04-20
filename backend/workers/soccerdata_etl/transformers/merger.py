# betgenius-backend/workers/soccerdata_etl/transformers/merger.py

import pandas as pd
import logging

logger = logging.getLogger(__name__)

class DataMerger:
    """
    O Transformador (Fase 'Transform' do ETL).
    Centraliza todas as planilhas extraídas em Super Tabelas.
    A padronização de nomenclatura do soccerdata já nos salva de 90% dos conflitos aqui.
    """
    
    def create_alpha_matrix(self, fbref_df, odds_df, elo_df, understat_df):
        """Funde todos os dados de partidas em uma Super Tabela de Jogo."""
        if fbref_df.empty: 
            return pd.DataFrame()

        logger.info("🧪 [MERGER] Iniciando fusão da Alpha Matrix (Partidas)...")

        # 1. Base: Calendário FBref
        master_df = fbref_df.copy()
        # O soccerdata retorna o índice assim: ['league', 'season', 'game']
        # Vamos resetar para trabalhar com as colunas livremente
        if 'game' in master_df.index.names:
            master_df = master_df.reset_index()

        # 2. Odds de Fechamento (MatchHistory/OddsPortal)
        if not odds_df.empty:
            if 'game' in odds_df.index.names:
                odds_df = odds_df.reset_index()
            
            # Cruzamos pela data exata e nome do time da casa
            # O soccerdata padroniza os nomes dos times em todos os seus módulos!
            master_df = pd.merge(
                master_df, odds_df[['date_str', 'home_team', 'PSCH', 'PSCD', 'PSCA']], 
                on=['date_str', 'home_team'], how='left'
            )

        # 3. Power Rating (ClubElo)
        if not elo_df.empty:
            # Elo Casa
            master_df = pd.merge(master_df, elo_df[['team', 'elo']], left_on='home_team', right_on='team', how='left')
            master_df = master_df.rename(columns={'elo': 'home_elo'}).drop('team', axis=1)
            # Elo Fora
            master_df = pd.merge(master_df, elo_df[['team', 'elo']], left_on='away_team', right_on='team', how='left')
            master_df = master_df.rename(columns={'elo': 'away_elo'}).drop('team', axis=1)

        # 4. Métricas Táticas (Understat)
        if not understat_df.empty:
            if 'game' in understat_df.index.names:
                understat_df = understat_df.reset_index()
                
            understat_cols = ['date_str', 'home_team', 'home_np_xg', 'away_np_xg', 'home_ppda', 'away_ppda']
            # Verifica se as colunas existem antes do merge
            existing_u_cols = [c for c in understat_cols if c in understat_df.columns]
            
            master_df = pd.merge(master_df, understat_df[existing_u_cols], on=['date_str', 'home_team'], how='left')

        logger.info(f"✅ [MERGER] Alpha Matrix consolidada: {len(master_df)} jogos.")
        return master_df

    def create_player_stats(self, fbref_players, sofifa_players):
        """Funde KPIs reais (Gols/xG) com Atributos de Video Game (Alternative Data)."""
        if fbref_players.empty: 
            return pd.DataFrame()

        logger.info("🧪 [MERGER] Iniciando fusão de KPIs de Jogadores (FBref + SoFIFA)...")
        
        master_players = fbref_players.copy()
        if 'player' in master_players.index.names:
            master_players = master_players.reset_index()

        if not sofifa_players.empty:
            if 'player' in sofifa_players.index.names:
                sofifa_players = sofifa_players.reset_index()
                
            # Sofifa e FBref podem divergir nos nomes. 
            # O merge aqui é 'left' para não perdermos o dado principal do FBref.
            # O fuzzy matching pesado ficará a cargo do Loader ao salvar no banco.
            sofifa_cols = ['player', 'team', 'Overall rating', 'Potential', 'Sprint speed', 'Finishing']
            existing_s_cols = [c for c in sofifa_cols if c in sofifa_players.columns]
            
            master_players = pd.merge(master_players, sofifa_players[existing_s_cols], on=['player', 'team'], how='left')
            
        logger.info(f"✅ [MERGER] Tabela de Jogadores consolidada: {len(master_players)} atletas.")
        return master_players