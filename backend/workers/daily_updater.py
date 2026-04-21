# betgenius-backend/workers/daily_updater.py
import asyncio
import logging
import httpx
import soccerdata as sd
import sys
import pandas as pd
from io import StringIO
from pathlib import Path
from datetime import datetime, timedelta
import re

# Adiciona o backend ao path para importações absolutas
sys.path.append(str(Path(__file__).parent.parent))

from core.database import db
from engine.entity_resolution import entity_resolver
from workers.fbref.config.fbref_map import LEAGUE_CONFIG

logging.basicConfig(level=logging.INFO, format="%(asctime)s [DAILY-UPDATER] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class ContinuousUpdater:
    """
    Motor de Manutenção S-Tier (Data Fusion - Etapa 3).
    Sincroniza os jogos recentes e futuros fundindo dados do Football-Data (Odds, Stats)
    com dados do FBref/SoccerData (xG, Árbitro, Escalações Futuras).
    Abrange Tiers 1, 2, 3 e Competições Internacionais.
    """
    def __init__(self):
        # Ligas que usam Master CSVs no Football-Data
        self.extra_leagues = ["BRA", "USA", "SWE", "NOR", "DNK", "JPN"]
        
        # Mapeamento estrito do SoccerData (Exigência da biblioteca para o FBref)
        self.sd_leagues = {
            # TIER 1
            "soccer_epl": "ENG-Premier League",
            "soccer_spain_la_liga": "ESP-La Liga",
            "soccer_italy_serie_a": "ITA-Serie A",
            "soccer_germany_bundesliga": "GER-Bundesliga",
            "soccer_uefa_champs_league": "INT-Champions League",
            
            # TIER 2
            "soccer_france_ligue_one": "FRA-Ligue 1",
            "soccer_netherlands_eredivisie": "NED-Eredivisie",
            "soccer_portugal_primeira_liga": "POR-Primeira Liga",
            "soccer_brazil_campeonato": "BRA-Série A",
            "soccer_usa_mls": "USA-Major League Soccer",
            
            # TIER 3
            "soccer_brazil_serie_b": "BRA-Série B",
            "soccer_sweden_allsvenskan": "SWE-Allsvenskan",
            "soccer_norway_eliteserien": "NOR-Eliteserien",
            "soccer_denmark_superliga": "DEN-Superliga",
            "soccer_japan_j_league": "JPN-J1 League",
            
            # CONTINENTAIS E COPAS
            "soccer_uefa_europa_league": "INT-Europa League",
            "soccer_conmebol_libertadores": "INT-Copa Libertadores",
            "soccer_conmebol_sudamericana": "INT-Copa Sudamericana",
            
            # INTERNACIONAIS (SELEÇÕES)
            "soccer_fifa_world_cup": "INT-World Cup",
            "soccer_conmebol_copa_america": "INT-Copa América",
            "soccer_uefa_euro_qualifications": "INT-European Championship",
            "soccer_uefa_nations_league": "INT-UEFA Nations League"
        }

    async def auto_register_team(self, conn, canonical_name: str, sport_key: str) -> int:
        """Busca ou cadastra um time novo na Matrix."""
        league_id = await conn.fetchval("SELECT id FROM core.leagues WHERE sport_key = $1", sport_key)
        team_id = await conn.fetchval("SELECT id FROM core.teams WHERE canonical_name = $1", canonical_name)
        if not team_id:
            team_id = await conn.fetchval(
                "INSERT INTO core.teams (canonical_name, league_id) VALUES ($1, $2) RETURNING id",
                canonical_name, league_id
            )
            logger.info(f"🆕 TIME IDENTIFICADO E REGISTRADO: '{canonical_name}'")
        return team_id

    def _get_fd_url_and_season(self, sport_key: str) -> tuple:
        """Calcula inteligentemente a URL e a Temporada atual para o Football-Data."""
        config = LEAGUE_CONFIG.get(sport_key)
        if not config: return None, None
        
        code = config.get("fd_code")
        if not code: return None, None # Pula copas que não têm CSV de odds diárias
        
        now = datetime.now()
        if code in self.extra_leagues:
            return f"https://www.football-data.co.uk/new/{code}.csv", str(now.year)
        else:
            if config["cross_year"]:
                # Se estamos antes de Julho, a temporada começou no ano anterior
                start_y = now.year - 1 if now.month < 7 else now.year
                season_path = f"{str(start_y)[-2:]}{str(start_y+1)[-2:]}"
                season_label = f"20{season_path[:2]}-20{season_path[2:]}"
            else:
                season_path = str(now.year)
                season_label = str(now.year)
            return f"https://www.football-data.co.uk/mmz4281/{season_path}/{code}.csv", season_label

    def _clean_fd_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpa o CSV do Football-Data e faz a imputação de médias em buracos."""
        df = df.dropna(subset=['Date', 'HomeTeam', 'AwayTeam'])
        target_cols = [
            'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR',
            'HS', 'AS', 'HST', 'AST', 'HF', 'AF', 'HC', 'AC', 'HY', 'AY', 'HR', 'AR',
            'PSCH', 'PSCD', 'PSCA', 'B365H', 'B365D', 'B365A',
            'PC>2.5', 'PC<2.5', 'P>2.5', 'P<2.5', 'B365>2.5', 'B365<2.5',
            'B365G', 'B365N'
        ]
        available_cols = [col for col in target_cols if col in df.columns]
        df_clean = df[available_cols].copy()
        
        df_clean['Date'] = pd.to_datetime(df_clean['Date'], dayfirst=True, errors='coerce')
        df_clean = df_clean.dropna(subset=['Date'])

        numeric_cols = df_clean.select_dtypes(include=['float64', 'int64']).columns
        for col in numeric_cols:
            if df_clean[col].isnull().any():
                col_mean = df_clean[col].mean()
                if pd.isna(col_mean): col_mean = 0.0
                df_clean[col] = df_clean[col].fillna(col_mean)
                
        return df_clean

    async def _update_football_data(self, client: httpx.AsyncClient, janela_inicio: datetime.date):
        """Passo 1: Injeta Odds, Cantos, Chutes e Cartões dos jogos recém-terminados."""
        logger.info("📡 PASSO 1: Sincronizando Odds e Stats Finais (Football-Data)...")
        
        for sport_key in LEAGUE_CONFIG.keys():
            url, season_label = self._get_fd_url_and_season(sport_key)
            if not url: continue
            
            try:
                response = await client.get(url, timeout=15.0)
                if response.status_code != 200: continue
                
                df = pd.read_csv(StringIO(response.text))
                df = self._clean_fd_dataframe(df)
                
                # Filtra apenas os jogos recentes
                df = df[df['Date'].dt.date >= janela_inicio]
                if df.empty: continue
                
                saved = 0
                async with db.pool.acquire() as conn:
                    async with conn.transaction():
                        for _, row in df.iterrows():
                            match_date = row['Date'].date()
                            home_id = await self.auto_register_team(conn, await entity_resolver.normalize_name(str(row['HomeTeam']), False), sport_key)
                            away_id = await self.auto_register_team(conn, await entity_resolver.normalize_name(str(row['AwayTeam']), False), sport_key)
                            if not home_id or not away_id: continue

                            def get_val(cols, default=0.0):
                                for c in cols:
                                    if c in df.columns and pd.notna(row[c]): return float(row[c])
                                return default

                            odd_h = get_val(['PSCH', 'B365H'])
                            odd_d = get_val(['PSCD', 'B365D'])
                            odd_a = get_val(['PSCA', 'B365A'])
                            odd_o25 = get_val(['PC>2.5', 'P>2.5', 'B365>2.5'])
                            odd_u25 = get_val(['PC<2.5', 'P<2.5', 'B365<2.5'])
                            odd_btts_y = get_val(['B365G'])
                            odd_btts_n = get_val(['B365N'])

                            await conn.execute("""
                                INSERT INTO core.matches_history 
                                (sport_key, season, match_date, home_team_id, away_team_id, home_goals, away_goals, match_result, 
                                 home_shots_target, away_shots_target, home_corners, away_corners, home_fouls, away_fouls, 
                                 home_yellow, away_yellow, home_red, away_red, closing_odd_home, closing_odd_draw, closing_odd_away, 
                                 odd_over_25, odd_under_25, odd_btts_yes, odd_btts_no, status)
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, 'FINISHED')
                                ON CONFLICT (match_date, home_team_id, away_team_id) DO UPDATE SET
                                    home_goals=EXCLUDED.home_goals, away_goals=EXCLUDED.away_goals, match_result=EXCLUDED.match_result,
                                    home_shots_target=EXCLUDED.home_shots_target, away_shots_target=EXCLUDED.away_shots_target,
                                    home_corners=EXCLUDED.home_corners, away_corners=EXCLUDED.away_corners,
                                    home_fouls=EXCLUDED.home_fouls, away_fouls=EXCLUDED.away_fouls,
                                    home_yellow=EXCLUDED.home_yellow, away_yellow=EXCLUDED.away_yellow,
                                    home_red=EXCLUDED.home_red, away_red=EXCLUDED.away_red,
                                    closing_odd_home=EXCLUDED.closing_odd_home, closing_odd_draw=EXCLUDED.closing_odd_draw, closing_odd_away=EXCLUDED.closing_odd_away,
                                    odd_over_25=EXCLUDED.odd_over_25, odd_under_25=EXCLUDED.odd_under_25,
                                    odd_btts_yes=EXCLUDED.odd_btts_yes, odd_btts_no=EXCLUDED.odd_btts_no, status='FINISHED'
                            """, sport_key, season_label, match_date, home_id, away_id, int(get_val(['FTHG'])), int(get_val(['FTAG'])), str(row.get('FTR', '')),
                               int(get_val(['HST'])), int(get_val(['AST'])), int(get_val(['HC'])), int(get_val(['AC'])),
                               int(get_val(['HF'])), int(get_val(['AF'])), int(get_val(['HY'])), int(get_val(['AY'])), int(get_val(['HR'])), int(get_val(['AR'])),
                               odd_h, odd_d, odd_a, odd_o25, odd_u25, odd_btts_y, odd_btts_n)
                            saved += 1
                            
                if saved > 0: logger.info(f"✅ {sport_key}: {saved} jogos finalizados injetados.")
            except Exception as e:
                logger.error(f"Falha no FD para {sport_key}: {e}")

    async def _update_fbref_soccerdata(self, janela_inicio: datetime.date, janela_fim: datetime.date):
        """Passo 2: Injeta xG, Árbitro e Agenda Jogos Futuros."""
        logger.info("📡 PASSO 2: Sincronizando xG, Árbitros e Agendamentos Futuros (SoccerData)...")
        
        for sport_key, sd_league_name in self.sd_leagues.items():
            config = LEAGUE_CONFIG.get(sport_key)
            if not config: continue
            
            now = datetime.now()
            if config["cross_year"]:
                start_y = now.year - 1 if now.month < 7 else now.year
                season_id = f"{str(start_y)[-2:]}{str(start_y+1)[-2:]}"
                season_label = f"20{season_id[:2]}-20{season_id[2:]}"
            else:
                season_id = str(now.year)
                season_label = str(now.year)

            try:
                # O parâmetro no_cache=True obriga a baixar o arquivo fresquinho
                fbref = sd.FBref(leagues=sd_league_name, seasons=season_id, no_cache=True)
                schedule = fbref.read_schedule()
                if schedule.empty: continue
                
                schedule = schedule.reset_index()
                if 'date' not in schedule.columns: continue
                schedule['date'] = pd.to_datetime(schedule['date'], errors='coerce')
                schedule = schedule.dropna(subset=['date'])
                
                df_filtered = schedule[(schedule['date'].dt.date >= janela_inicio) & (schedule['date'].dt.date <= janela_fim)]
                if df_filtered.empty: continue

                saved = 0
                async with db.pool.acquire() as conn:
                    async with conn.transaction():
                        for _, row in df_filtered.iterrows():
                            match_date = row['date'].date()
                            raw_home = str(row.get('home_team', '')).strip()
                            raw_away = str(row.get('away_team', '')).strip()
                            if not raw_home or not raw_away: continue
                            
                            home_id = await self.auto_register_team(conn, await entity_resolver.normalize_name(raw_home, False), sport_key)
                            away_id = await self.auto_register_team(conn, await entity_resolver.normalize_name(raw_away, False), sport_key)
                            if not home_id or not away_id: continue

                            h_goals = int(row['home_goals']) if 'home_goals' in row and pd.notna(row['home_goals']) else None
                            a_goals = int(row['away_goals']) if 'away_goals' in row and pd.notna(row['away_goals']) else None
                            xg_home = float(row['home_xg']) if 'home_xg' in row and pd.notna(row['home_xg']) else 0.0
                            xg_away = float(row['away_xg']) if 'away_xg' in row and pd.notna(row['away_xg']) else 0.0
                            attendance = int(row['attendance']) if 'attendance' in row and pd.notna(row['attendance']) else 0
                            referee = str(row['referee']) if 'referee' in row and pd.notna(row['referee']) else 'Desconhecido'

                            status = 'FINISHED' if h_goals is not None else 'SCHEDULED'
                            match_result = 'H' if (h_goals is not None and h_goals > a_goals) else ('A' if (h_goals is not None and a_goals > h_goals) else ('D' if h_goals is not None else None))

                            # UPSERT INTELIGENTE: Atualiza xG e Referee. Não sobrescreve as Odds do Passo 1.
                            await conn.execute("""
                                INSERT INTO core.matches_history 
                                (sport_key, season, match_date, home_team_id, away_team_id, home_goals, away_goals, match_result, xg_home, xg_away, attendance, referee, status)
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                                ON CONFLICT (match_date, home_team_id, away_team_id) DO UPDATE SET
                                    xg_home = EXCLUDED.xg_home,
                                    xg_away = EXCLUDED.xg_away,
                                    attendance = EXCLUDED.attendance,
                                    referee = EXCLUDED.referee,
                                    home_goals = COALESCE(EXCLUDED.home_goals, core.matches_history.home_goals),
                                    away_goals = COALESCE(EXCLUDED.away_goals, core.matches_history.away_goals),
                                    match_result = COALESCE(EXCLUDED.match_result, core.matches_history.match_result),
                                    status = CASE WHEN EXCLUDED.home_goals IS NOT NULL THEN 'FINISHED' ELSE core.matches_history.status END
                            """, sport_key, season_label, match_date, home_id, away_id, h_goals, a_goals, match_result, xg_home, xg_away, attendance, referee, status)
                            saved += 1
                            
                if saved > 0: logger.info(f"✅ {sd_league_name}: {saved} jogos atualizados ou agendados (Puxou FBref).")

            except Exception as e:
                # Falha silenciosa para não derrubar o worker inteiro caso uma liga ou copa esteja fora do ar
                logger.debug(f"Aviso no SoccerData para {sd_league_name} (pode não haver rodada na semana): {e}")

    async def run_update(self):
        logger.info("🚀 INICIANDO ATUALIZADOR CONTÍNUO S-TIER (FUSÃO DE DADOS)")
        await db.connect()
        await entity_resolver.load_mappings_from_db()
        
        hoje = datetime.now().date()
        janela_inicio = hoje - timedelta(days=4) # Jogos dos últimos 4 dias
        janela_fim = hoje + timedelta(days=7)    # Agendamento dos próximos 7 dias
        
        async with httpx.AsyncClient() as client:
            await self._update_football_data(client, janela_inicio)
            
        await self._update_fbref_soccerdata(janela_inicio, janela_fim)

        await db.disconnect()
        logger.info("🏆 SINCRONIZAÇÃO DIÁRIA CONCLUÍDA.")

if __name__ == "__main__":
    updater = ContinuousUpdater()
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(updater.run_update())