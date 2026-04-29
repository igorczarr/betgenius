# betgenius-backend/workers/api_integrations/soccerdata_odds_baseline.py
import sys
import os
import io
import logging

# ==============================================================================
# 1. BLINDAGEM NUCLEAR GLOBAL (DEVE FICAR NO TOPO, ANTES DE QUALQUER IMPORT)
# ==============================================================================
if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

class SafeWindowsFormatter(logging.Formatter):
    """Garante que nenhum log no sistema inteiro quebre por causa de caracteres."""
    def format(self, record):
        try:
            return super().format(record)
        except Exception:
            record.msg = str(record.msg).encode('ascii', 'ignore').decode('ascii')
            return super().format(record)

# Sequestramos o Root Logger e expurgamos todos os handlers antigos
logging.root.handlers = []
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(SafeWindowsFormatter("%(asctime)s [ODDS-BATEDOR] %(levelname)s: %(message)s"))
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# ==============================================================================
# 2. IMPORTAÇÕES DA APLICAÇÃO
# ==============================================================================
import asyncio
import pandas as pd
from pathlib import Path
from datetime import datetime
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)
import soccerdata as sd

sys.path.append(str(Path(__file__).parent.parent.parent))

from core.database import db
from engine.entity_resolution import entity_resolver

class SoccerDataOddsBaseline:
    """
    Batedor Híbrido S-Tier.
    1. Passado: Preenche buracos de resultados (Gols, Chutes, Cantos, Cartões).
    2. Futuro: Captura Odds de Abertura (1X2, O/U, Handicap Asiático).
    """
    def __init__(self):
        # Mapeamento Global - Football-Data.co.uk Codes para Soccerdata
        self.leagues = {
            "ENG-Premier League": "E0", "ENG-Championship": "E1", "ENG-League 1": "E2", "ENG-League 2": "E3", "ENG-National League": "EC",
            "SCO-Premier League": "SC0", "SCO-Championship": "SC1", "SCO-League 1": "SC2", "SCO-League 2": "SC3",
            "GER-Bundesliga": "D1", "GER-Bundesliga 2": "D2",
            "ITA-Serie A": "I1", "ITA-Serie B": "I2",
            "ESP-La Liga": "SP1", "ESP-La Liga 2": "SP2",
            "FRA-Ligue 1": "F1", "FRA-Ligue 2": "F2",
            "NED-Eredivisie": "N1", "BEL-Eredivisie": "B1", "POR-Primeira Liga": "P1",
            "TUR-Super Lig": "T1", "GRE-Super Lig": "G1",
            "ARG-Primera Division": "ARG", "AUT-Bundesliga": "AUT", "BRA-Campeonato": "BRA",
            "CHN-Super League": "CHN", "DEN-Superliga": "DNK", "FIN-Veikkausliiga": "FIN",
            "IRL-Premier Division": "IRL", "JPN-J League": "JPN", "MEX-Liga MX": "MEX",
            "NOR-Eliteserien": "NOR", "POL-Ekstraklasa": "POL", "ROU-Liga 1": "ROU",
            "RUS-Premier League": "RUS", "SWE-Allsvenskan": "SWE", "SUI-Allsvenskan": "SWZ",
            "USA-MLS": "USA"
        }

    def _get_season_string(self) -> str:
        now = datetime.now()
        return f"{str(now.year - 1)[-2:]}{str(now.year)[-2:]}" if now.month < 7 else f"{str(now.year)[-2:]}{str(now.year + 1)[-2:]}"

    async def _process_market(self, conn, match_id: int, categoria: str, nome_mercado: str, odd: float):
        if pd.isna(odd) or odd <= 1.0: return
        
        await conn.execute("""
            INSERT INTO core.market_odds 
            (match_id, categoria, nome_mercado, bookmaker, current_odd, opening_odd, heavy_drop_alert)
            VALUES ($1, $2, $3, 'bet365', $4, $4, FALSE)
            ON CONFLICT DO NOTHING
        """, match_id, categoria, nome_mercado, float(odd))

    async def process_league_data(self, sd_league_name: str, season_str: str):
        logger.info(f"Buscando Dados (Passado e Futuro) para {sd_league_name}...")
        try:
            mh = sd.MatchHistory(leagues=sd_league_name, seasons=season_str, no_cache=True)
            df = mh.read_games().reset_index()
            
            if df.empty: return
            
            df['date_parsed'] = pd.to_datetime(df['date'])
            today = pd.Timestamp(datetime.now().date())
            
            df_past = df[df['date_parsed'] < today]
            df_future = df[df['date_parsed'] >= today]

            async with db.pool.acquire() as conn:
                async with conn.transaction():
                    
                    # ==============================================================
                    # 1. LIQUIDAÇÃO DO PASSADO (Redundância de Resultados)
                    # ==============================================================
                    settled_count = 0
                    if not df_past.empty:
                        for _, row in df_past.iterrows():
                            # Se não houver gols no CSV, o jogo provavelmente foi adiado ou abandonado
                            if pd.isna(row.get('FTHG')) or pd.isna(row.get('FTAG')): continue
                            
                            h_canon = await entity_resolver.normalize_name(str(row.get('home_team', '')))
                            a_canon = await entity_resolver.normalize_name(str(row.get('away_team', '')))
                            
                            match_id = await conn.fetchval("""
                                SELECT m.id FROM core.matches_history m
                                JOIN core.teams th ON m.home_team_id = th.id
                                JOIN core.teams ta ON m.away_team_id = ta.id
                                WHERE th.canonical_name = $1 AND ta.canonical_name = $2 
                                AND m.status != 'FINISHED'
                            """, h_canon, a_canon)
                            
                            if match_id:
                                # Coalesce para herdar 0 caso a estatística não exista na liga menor
                                h_goals = int(row.get('FTHG', 0))
                                a_goals = int(row.get('FTAG', 0))
                                ht_hg = int(row.get('HTHG', 0)) if pd.notna(row.get('HTHG')) else None
                                ht_ag = int(row.get('HTAG', 0)) if pd.notna(row.get('HTAG')) else None
                                result = 'H' if h_goals > a_goals else ('A' if a_goals > h_goals else 'D')
                                
                                await conn.execute("""
                                    UPDATE core.matches_history SET 
                                        home_goals = $1, away_goals = $2, match_result = $3,
                                        ht_home_goals = COALESCE($4, ht_home_goals), ht_away_goals = COALESCE($5, ht_away_goals),
                                        home_shots = COALESCE($6, home_shots), away_shots = COALESCE($7, away_shots),
                                        home_shots_target = COALESCE($8, home_shots_target), away_shots_target = COALESCE($9, away_shots_target),
                                        home_corners = COALESCE($10, home_corners), away_corners = COALESCE($11, away_corners),
                                        home_fouls = COALESCE($12, home_fouls), away_fouls = COALESCE($13, away_fouls),
                                        home_yellow = COALESCE($14, home_yellow), away_yellow = COALESCE($15, away_yellow),
                                        home_red = COALESCE($16, home_red), away_red = COALESCE($17, away_red),
                                        status = 'FINISHED'
                                    WHERE id = $18
                                """, 
                                h_goals, a_goals, result, ht_hg, ht_ag,
                                int(row.get('HS', 0)) if pd.notna(row.get('HS')) else None, int(row.get('AS', 0)) if pd.notna(row.get('AS')) else None,
                                int(row.get('HST', 0)) if pd.notna(row.get('HST')) else None, int(row.get('AST', 0)) if pd.notna(row.get('AST')) else None,
                                int(row.get('HC', 0)) if pd.notna(row.get('HC')) else None, int(row.get('AC', 0)) if pd.notna(row.get('AC')) else None,
                                int(row.get('HF', 0)) if pd.notna(row.get('HF')) else None, int(row.get('AF', 0)) if pd.notna(row.get('AF')) else None,
                                int(row.get('HY', 0)) if pd.notna(row.get('HY')) else None, int(row.get('AY', 0)) if pd.notna(row.get('AY')) else None,
                                int(row.get('HR', 0)) if pd.notna(row.get('HR')) else None, int(row.get('AR', 0)) if pd.notna(row.get('AR')) else None,
                                match_id)
                                settled_count += 1
                                
                    if settled_count > 0:
                        logger.info(f"✔️  {settled_count} jogos do passado de {sd_league_name} foram liquidados.")

                    # ==============================================================
                    # 2. ABERTURA DO FUTURO (Odds 1X2, O/U e Asian Handicap)
                    # ==============================================================
                    odds_count = 0
                    if not df_future.empty:
                        for _, row in df_future.iterrows():
                            h_canon = await entity_resolver.normalize_name(str(row.get('home_team', '')))
                            a_canon = await entity_resolver.normalize_name(str(row.get('away_team', '')))
                            
                            match_id = await conn.fetchval("""
                                SELECT m.id FROM core.matches_history m
                                JOIN core.teams th ON m.home_team_id = th.id
                                JOIN core.teams ta ON m.away_team_id = ta.id
                                WHERE th.canonical_name = $1 AND ta.canonical_name = $2 AND m.status = 'SCHEDULED'
                            """, h_canon, a_canon)
                            
                            if not match_id: continue

                            # 1X2 e Totais (Base)
                            await self._process_market(conn, match_id, 'h2h', '1', row.get('B365H', 0))
                            await self._process_market(conn, match_id, 'h2h', 'x', row.get('B365D', 0))
                            await self._process_market(conn, match_id, 'h2h', '2', row.get('B365A', 0))
                            await self._process_market(conn, match_id, 'totals', 'Over/Under 2.5 - Over', row.get('B365>2.5', 0))
                            await self._process_market(conn, match_id, 'totals', 'Over/Under 2.5 - Under', row.get('B365<2.5', 0))

                            # Asian Handicap (O segredo institucional)
                            # AHh = A linha do Handicap (Ex: -0.5, +1.25)
                            ah_line = row.get('AHh')
                            if pd.notna(ah_line):
                                await self._process_market(conn, match_id, 'spreads', f"AH {ah_line} - home", row.get('B365AHH', 0))
                                await self._process_market(conn, match_id, 'spreads', f"AH {ah_line} - away", row.get('B365AHA', 0))

                            odds_count += 1
                            
                    if odds_count > 0:
                        logger.info(f"✔️  {odds_count} jogos do futuro de {sd_league_name} ganharam Odds de Abertura.")

        except Exception as e:
            clean_error = str(e).encode('ascii', 'ignore').decode('ascii')
            logger.warning(f"Ignorado: Nao foi possivel processar a liga {sd_league_name}. Detalhe: {clean_error[:50]}")

    async def run(self):
        logger.info("=== INICIANDO BATEDOR GLOBAL (LIQUIDAÇÃO E ODDS) ===")
        await db.connect()
        await entity_resolver.load_mappings_from_db()
        
        season_str = self._get_season_string()
        
        for sd_league_name in self.leagues.keys():
            await self.process_league_data(sd_league_name, season_str)
            await asyncio.sleep(1) 
            
        await db.disconnect()
        logger.info("=== BATEDOR FINALIZADO ===")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(SoccerDataOddsBaseline().run())