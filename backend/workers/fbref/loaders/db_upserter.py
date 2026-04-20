# betgenius-backend/workers/fbref/loaders/db_upserter.py
import logging
import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from core.database import db
from engine.entity_resolution import entity_resolver
from workers.fbref.extractors.fbref_parsers import FBrefParser

logger = logging.getLogger(__name__)

class FBrefDBUpserter:
    """Motor de Persistência S-Tier (Com Inteligência Anti-Prefixo e Proxy xG)."""

    @staticmethod
    async def auto_register_team(conn, canonical_name: str, sport_key: str) -> int:
        league_id = await conn.fetchval("SELECT id FROM core.leagues WHERE sport_key = $1", sport_key)
        team_id = await conn.fetchval("SELECT id FROM core.teams WHERE canonical_name = $1", canonical_name)
        if not team_id:
            team_id = await conn.fetchval(
                "INSERT INTO core.teams (canonical_name, league_id) VALUES ($1, $2) RETURNING id",
                canonical_name, league_id
            )
        return team_id

    @staticmethod
    async def process_squads_and_wages(sport_key: str, season: str, df_std: pd.DataFrame, df_wages: pd.DataFrame) -> dict:
        team_cache = {}
        saved_count = 0

        async with db.pool.acquire() as conn:
            async with conn.transaction():
                for index, row in df_std.iterrows():
                    raw_team = str(row.iloc[0]).strip()
                    canonical_name = await entity_resolver.normalize_name(raw_team, is_pinnacle=False)
                    team_id = await FBrefDBUpserter.auto_register_team(conn, canonical_name, sport_key)
                    if not team_id: continue
                    
                    team_cache[raw_team] = team_id

                    pts = FBrefParser.extract_safe_value(df_std, index, ['pts', 'points'], is_float=False)
                    wins = FBrefParser.extract_safe_value(df_std, index, ['w', 'wins'], is_float=False)
                    poss = FBrefParser.extract_safe_value(df_std, index, ['poss', 'possession'])
                    
                    # TENTATIVA 1: Busca o xG Oficial
                    xg = FBrefParser.extract_safe_value(df_std, index, ['xg', 'expected_xg'])
                    
                    # PROXY S-TIER: Se o xG não existe, usamos os Gols Reais como Proxy (Forte correlação no longo prazo)
                    if xg == 0.0:
                        xg = FBrefParser.extract_safe_value(df_std, index, ['gls', 'goals'])
                    
                    wage = 0.0
                    if df_wages is not None and not df_wages.empty:
                        wage_row = df_wages[df_wages.iloc[:, 0].str.contains(raw_team, case=False, na=False)]
                        if not wage_row.empty:
                            wage = FBrefParser.extract_safe_value(df_wages, wage_row.index[0], ['annual', 'wage'])

                    await conn.execute("""
                        INSERT INTO fbref_squad.standings_wages (team_id, season, pts, wins, wage_bill_annual)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (team_id, season) DO UPDATE SET
                            pts=EXCLUDED.pts, wins=EXCLUDED.wins, wage_bill_annual=EXCLUDED.wage_bill_annual
                    """, team_id, season, pts, wins, wage)

                    await conn.execute("""
                        INSERT INTO fbref_squad.advanced_general (team_id, season, possession_pct, xg_for)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (team_id, season) DO UPDATE SET
                            possession_pct=EXCLUDED.possession_pct, xg_for=EXCLUDED.xg_for
                    """, team_id, season, poss, xg)
                    
                    saved_count += 1
                    
        return team_cache

    @staticmethod
    async def process_players(season: str, df_play_std: pd.DataFrame, df_play_sht: pd.DataFrame, df_play_msc: pd.DataFrame, team_cache: dict):
        if df_play_std is None or df_play_std.empty: return
        
        # O FBref chama a coluna de jogador de 'Player'
        if 'Player' not in df_play_std.columns: return
        
        df_play_std = df_play_std.drop_duplicates(subset=['Player'], keep='first')
        saved_count = 0

        async with db.pool.acquire() as conn:
            async with conn.transaction():
                for index, row in df_play_std.iterrows():
                    player_name = str(row['Player']).strip()
                    raw_squad = str(row.get('Squad', '')).strip()
                    
                    # CORREÇÃO CRÍTICA: Busca inteligente ("eng Arsenal" -> "Arsenal")
                    team_id = None
                    for cached_name, t_id in team_cache.items():
                        if cached_name.lower() in raw_squad.lower():
                            team_id = t_id
                            break
                            
                    if not team_id: continue

                    goals = int(FBrefParser.extract_safe_value(df_play_std, index, ['gls', 'goals'], False))
                    asts = int(FBrefParser.extract_safe_value(df_play_std, index, ['ast', 'assists'], False))
                    
                    # TENTATIVA 1: Busca o xG90 Oficial
                    xg90 = FBrefParser.extract_safe_value(df_play_std, index, ['xg90', 'expected_xg90'])
                    
                    # PROXY S-TIER: Se não existe xG90, calculamos Proxy (Gols / 90 mins)
                    if xg90 == 0.0:
                        min90 = FBrefParser.extract_safe_value(df_play_std, index, ['90s'])
                        if min90 > 0:
                            xg90 = round(goals / min90, 2)
                        else:
                            xg90 = float(goals)
                    
                    shots90 = 0.0
                    if df_play_sht is not None and not df_play_sht.empty and 'Player' in df_play_sht.columns:
                        sht_row = df_play_sht[df_play_sht['Player'] == player_name]
                        if not sht_row.empty: 
                            shots90 = FBrefParser.extract_safe_value(df_play_sht, sht_row.index[0], ['sh/90', 'shots/90'])
                            
                    fls, fld, crdy = 0, 0, 0
                    if df_play_msc is not None and not df_play_msc.empty and 'Player' in df_play_msc.columns:
                        msc_row = df_play_msc[df_play_msc['Player'] == player_name]
                        if not msc_row.empty:
                            idx = msc_row.index[0]
                            fls = int(FBrefParser.extract_safe_value(df_play_msc, idx, ['fls', 'fouls'], False))
                            fld = int(FBrefParser.extract_safe_value(df_play_msc, idx, ['fld', 'fouls_drawn'], False))
                            crdy = int(FBrefParser.extract_safe_value(df_play_msc, idx, ['crdy', 'yellow_cards'], False))

                    queries = [
                        ("fbref_player.metric_goals", goals),
                        ("fbref_player.metric_assists", asts),
                        ("fbref_player.metric_goals_assists", goals + asts),
                        ("fbref_player.metric_xg_90", xg90),
                        ("fbref_player.metric_shots_90", shots90),
                        ("fbref_player.metric_fouls_committed", fls),
                        ("fbref_player.metric_fouls_drawn", fld),
                        ("fbref_player.metric_yellow_cards", crdy),
                    ]
                    
                    for table_name, value in queries:
                        await conn.execute(f"""
                            INSERT INTO {table_name} (player_name, team_id, season, quantity)
                            VALUES ($1, $2, $3, $4)
                            ON CONFLICT (player_name, team_id, season) DO UPDATE SET
                                quantity=EXCLUDED.quantity, last_updated=CURRENT_TIMESTAMP
                        """, player_name, team_id, season, value)
                        
                    saved_count += 1
                    
        logger.info(f"🏃‍♂️ Data Marts atualizados: {saved_count} jogadores salvos (Com Proxy xG aplicado).")