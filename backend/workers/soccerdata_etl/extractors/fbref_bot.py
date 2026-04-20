# betgenius-backend/workers/soccerdata_etl/extractors/fbref_bot.py

import pandas as pd
import soccerdata as sd
import logging
from datetime import datetime, timedelta
import sys
import os

# Adiciona o diretório pai ao path para importar o config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

class FBrefExtractor:
    """
    Minerador Especializado do FBref.
    Usa o SoccerData para puxar as tabelas massivas, cruzar as estatísticas 
    avançadas dos times e filtrar os KPIs dos jogadores.
    """
    def __init__(self, target_date=None):
        # Define as ligas com base no modo de operação (Debug vs Produção)
        if config.DEBUG_MODE:
            self.leagues = config.TEST_LEAGUES
            logger.info(f"🧪 [FBREF] Modo DEBUG Ativado. Focando em: {self.leagues}")
        else:
            self.leagues = list(config.COMPETITIONS.values())
            logger.info(f"🌍 [FBREF] Modo PRODUÇÃO. Focando em {len(self.leagues)} competições.")

        # Pega a temporada atual baseada no config (ex: '2324' ou '2425')
        self.season = config.ALL_SEASONS[-1] 
        
        # Define a data alvo (Padrão: ontem)
        if target_date:
            self.target_date = target_date
        else:
            self.target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
        # Instancia o motor do SoccerData uma única vez para otimizar o cache
        self.fbref = sd.FBref(leagues=self.leagues, seasons=self.season)

    def get_daily_schedule(self) -> pd.DataFrame:
        logger.info(f"📅 Buscando calendário para a data: {self.target_date}")
        try:
            schedule = self.fbref.read_schedule()
            if schedule.empty:
                return pd.DataFrame()
                
            schedule = schedule.reset_index()
            schedule['date_str'] = pd.to_datetime(schedule['date']).dt.strftime('%Y-%m-%d')
            daily_games = schedule[schedule['date_str'] == self.target_date].copy()
            
            # BLINDAGEM: Só tenta limpar se as colunas de gols vieram no DataFrame
            if 'home_goals' in daily_games.columns and 'away_goals' in daily_games.columns:
                daily_games = daily_games.dropna(subset=['home_goals', 'away_goals'])
            
            return daily_games
        except Exception as e:
            logger.error(f"❌ Falha ao buscar calendário: {e}")
            return pd.DataFrame()

    def get_advanced_team_stats(self) -> pd.DataFrame:
        """
        O Alquimista de Times: Baixa os relatórios Standard, Shooting, Defense, etc.,
        e funde todos eles em uma 'Super Tabela' do time na temporada.
        """
        logger.info(f"📈 Baixando Estatísticas Avançadas de Times ({len(config.TEAM_STATS_TYPES)} relatórios)...")
        
        super_df = pd.DataFrame()
        
        for stat_type in config.TEAM_STATS_TYPES:
            try:
                logger.info(f"  -> Processando relatório: {stat_type.upper()}")
                df = self.fbref.read_team_season_stats(stat_type=stat_type)
                df = df.reset_index()
                
                # Achatando o MultiIndex de colunas (Se o FBref retornar colunas duplas)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = ['_'.join(str(c).strip() for c in col if c).strip() for col in df.columns.values]
                
                # O índice base para fazer o cruzamento (JOIN) é a Liga, Temporada e Time
                join_keys = ['league', 'season', 'team']
                
                if super_df.empty:
                    super_df = df
                else:
                    # Faz o merge para colar as colunas novas do lado das antigas
                    super_df = pd.merge(super_df, df, on=join_keys, how='left', suffixes=('', f'_{stat_type}'))
                    
            except Exception as e:
                logger.warning(f"⚠️ Aviso ao processar {stat_type}: {e}. Pulando este relatório.")
                
        logger.info(f"✅ Super Tabela de Times gerada. Dimensões: {super_df.shape}")
        return super_df

    def get_player_leaders_kpis(self) -> pd.DataFrame:
        """
        O Caçador de Talentos: Baixa os relatórios de Jogadores e filtra 
        pelos KPIs vitais (Gols, xG, Faltas, Cartões) que configuramos.
        """
        logger.info("🏃‍♂️ Puxando KPIs dos jogadores (Standard e Misc)...")
        
        try:
            # 1. Puxa os dados ofensivos básicos (Gols, Assists, xG)
            df_std = self.fbref.read_player_season_stats(stat_type="standard")
            df_std = df_std.reset_index()
            if isinstance(df_std.columns, pd.MultiIndex):
                df_std.columns = ['_'.join(str(c).strip() for c in col if c).strip() for col in df_std.columns.values]

            # 2. Puxa os dados disciplinares/faltas (Misc)
            df_misc = self.fbref.read_player_season_stats(stat_type="misc")
            df_misc = df_misc.reset_index()
            if isinstance(df_misc.columns, pd.MultiIndex):
                df_misc.columns = ['_'.join(str(c).strip() for c in col if c).strip() for col in df_misc.columns.values]

            # 3. Funde as duas planilhas
            join_keys = ['league', 'season', 'team', 'player']
            super_players = pd.merge(df_std, df_misc, on=join_keys, how='left')

            # 4. Limpa e renomeia pelas diretrizes do config.py
            # Nós mapeamos as colunas baseadas nos termos prováveis que o soccerdata cospe.
            # Nota: Esses mapeamentos exatos dependem da estrutura que o pandas achata, 
            # fizemos um De-Para defensivo aqui.
            columns_to_keep = join_keys.copy()
            rename_map = {}
            
            for kpi_pt, kpi_eng in config.PLAYER_KPI_TARGETS.items():
                # Tenta achar a coluna achada que contém o termo alvo (ex: 'Performance_Gls')
                matching_cols = [c for c in super_players.columns if kpi_eng.lower() in c.lower() or c.lower() == kpi_eng.lower()]
                if matching_cols:
                    target_col = matching_cols[0]
                    columns_to_keep.append(target_col)
                    rename_map[target_col] = kpi_pt

            # Isola apenas o que importa pro Fundo Quantitativo
            final_players_df = super_players[columns_to_keep].rename(columns=rename_map)
            
            logger.info(f"✅ Tabela de Jogadores Isolada. KPIs Mapeados: {list(rename_map.values())}")
            return final_players_df

        except Exception as e:
            logger.error(f"❌ Falha Crítica ao puxar KPIs de jogadores: {e}")
            return pd.DataFrame()

# =========================================================
# TESTE ISOLADO (Se executar este arquivo diretamente)
# =========================================================
if __name__ == "__main__":
    bot = FBrefExtractor(target_date="2024-05-12") # Data fixa para teste
    
    # 1. Puxar as partidas
    jogos = bot.get_daily_schedule()
    print("\n--- JOGOS DA DATA ---")
    print(jogos[['home_team', 'away_team', 'home_goals', 'away_goals']].head())
    
    # 2. Puxar Times Avançados
    times = bot.get_advanced_team_stats()
    print(f"\n--- TIMES (SUPER TABELA) ---")
    print(f"Colunas extraídas: {len(times.columns)}")
    
    # 3. Puxar KPIs Jogadores
    jogadores = bot.get_player_leaders_kpis()
    print("\n--- JOGADORES (LÍDERES) ---")
    print(jogadores.head())