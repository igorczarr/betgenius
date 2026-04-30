# betgenius-backend/workers/historical_backfill.py
import sys
import os
import io
import hashlib
import asyncio
import logging
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# BLINDAGEM DE ENCODING
if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore')
    except AttributeError:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db
from engine.entity_resolution import entity_resolver

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")
pd.set_option('future.no_silent_downcasting', True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [QUANT-ETL] %(message)s")
logger = logging.getLogger(__name__)

class HistoricalBackfill:
    """
    Motor S-Tier de Carga Histórica e Feature Engineering Monolítico.
    """
    def __init__(self):
        # FIX: Processando apenas o arquivo faltante
        self.files_to_process = [
            BASE_DIR / 'workers' / 'new_leagues_data.xlsx'
        ]
        
        self.league_cache = {}
        self.team_cache = {}
        
        self.SPAN_MICRO = 5
        self.universe_state = {}
        self.tactical_memory = {}
        self.league_baselines = {}

    async def initialize_schema(self, conn):
        logger.info("🛠️ Validando Schema S-Tier no Banco de Dados...")
        
        await conn.execute("CREATE SCHEMA IF NOT EXISTS core;")
        await conn.execute("CREATE SCHEMA IF NOT EXISTS quant_ml;")
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS core.leagues (
                id SERIAL PRIMARY KEY, sport_key VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100), country VARCHAR(50), tier INTEGER DEFAULT 1, active BOOLEAN DEFAULT TRUE
            );
            CREATE TABLE IF NOT EXISTS core.teams (
                id SERIAL PRIMARY KEY, canonical_name VARCHAR(100) UNIQUE NOT NULL,
                league_id INTEGER REFERENCES core.leagues(id), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS core.team_aliases (
                id SERIAL PRIMARY KEY, team_id INTEGER REFERENCES core.teams(id),
                alias_name VARCHAR(100) UNIQUE NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS core.matches_history (
                id SERIAL PRIMARY KEY, match_hash VARCHAR(64) UNIQUE NOT NULL,
                sport_key VARCHAR(50), season VARCHAR(20), match_date DATE, start_time TIMESTAMP,
                home_team_id INTEGER REFERENCES core.teams(id), away_team_id INTEGER REFERENCES core.teams(id),
                round_num INTEGER DEFAULT 1, context VARCHAR(50) DEFAULT 'Regular Season',
                home_position INTEGER DEFAULT 0, away_position INTEGER DEFAULT 0,
                home_goals INTEGER, away_goals INTEGER, match_result VARCHAR(10),
                ht_home_goals INTEGER, ht_away_goals INTEGER, ht_result VARCHAR(10),
                home_shots INTEGER, away_shots INTEGER, home_shots_target INTEGER, away_shots_target INTEGER,
                home_corners INTEGER, away_corners INTEGER, home_fouls INTEGER, away_fouls INTEGER,
                home_yellow INTEGER, away_yellow INTEGER, home_red INTEGER, away_red INTEGER, referee VARCHAR(100),
                closing_odd_home NUMERIC(6,2), closing_odd_draw NUMERIC(6,2), closing_odd_away NUMERIC(6,2),
                pin_odd_home NUMERIC(6,2), pin_odd_draw NUMERIC(6,2), pin_odd_away NUMERIC(6,2),
                pin_closing_home NUMERIC(6,2), pin_closing_draw NUMERIC(6,2), pin_closing_away NUMERIC(6,2),
                odd_over_25 NUMERIC(6,2), odd_under_25 NUMERIC(6,2), odd_btts_yes NUMERIC(6,2), odd_btts_no NUMERIC(6,2),
                ah_line NUMERIC(6,2), pin_ah_home NUMERIC(6,2), pin_ah_away NUMERIC(6,2), pin_closing_ah_home NUMERIC(6,2), pin_closing_ah_away NUMERIC(6,2),
                status VARCHAR(20) DEFAULT 'SCHEDULED', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_match_hash ON core.matches_history(match_hash);
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS quant_ml.feature_store (
                match_id INTEGER PRIMARY KEY REFERENCES core.matches_history(id) ON DELETE CASCADE,
                delta_elo NUMERIC(8,2), home_pts_before INTEGER, away_pts_before INTEGER,
                home_form VARCHAR(10), away_form VARCHAR(10),
                h_xg_for_micro NUMERIC(5,2), h_xg_ag_micro NUMERIC(5,2),
                a_xg_for_micro NUMERIC(5,2), a_xg_ag_micro NUMERIC(5,2),
                h_shots_for NUMERIC(5,2), a_shots_for NUMERIC(5,2)
            );
        """)

    def _generate_match_hash(self, date_str, home, away):
        raw = f"{date_str}_{home}_{away}".lower().replace(" ", "")
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()
        
    async def safe_normalize(self, team_name):
        try:
            return await entity_resolver.normalize_name(team_name)
        except Exception:
            return team_name

    async def auto_register_team(self, conn, canonical_name: str, sport_key: str) -> int:
        cache_key = f"{sport_key}_{canonical_name}"
        if cache_key in self.team_cache:
            return self.team_cache[cache_key]

        league_id = self.league_cache.get(sport_key)
        if not league_id:
            league_id = await conn.fetchval("SELECT id FROM core.leagues WHERE sport_key = $1", sport_key)
            if not league_id:
                league_id = await conn.fetchval("INSERT INTO core.leagues (sport_key, name, tier) VALUES ($1, $2, $3) RETURNING id", sport_key, sport_key, 1)
            self.league_cache[sport_key] = league_id

        team_id = await conn.fetchval("SELECT id FROM core.teams WHERE canonical_name = $1", canonical_name)
        if not team_id:
            team_id = await conn.fetchval("INSERT INTO core.teams (canonical_name, league_id) VALUES ($1, $2) RETURNING id", canonical_name, league_id)
            
        self.team_cache[cache_key] = team_id
        return team_id

    def _init_team_tactics(self, team, default_xg=1.2, default_shots=4.0):
        if team not in self.tactical_memory:
            self.tactical_memory[team] = {
                'xg_for_micro': default_xg, 'xg_ag_micro': default_xg,
                'shots_for': default_shots, 'elo': 1500.0
            }

    def _update_ewma(self, current, new_val, span):
        alpha = 2.0 / (span + 1.0)
        return (new_val * alpha) + (current * (1.0 - alpha))

    def _get_result_char(self, hg, ag):
        if hg > ag: return 'W'
        if hg < ag: return 'L'
        return 'D'

    def _calculate_base_features(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("⚙️ Iniciando Simulação do Universo (Time-Travel)...")
        
        # FIX: Ordenação cronológica estrita do mais antigo para o mais recente globalmente
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.sort_values(by=['Date', 'Div']).reset_index(drop=True)
        
        for div, group in df.groupby('Div'):
            # FIX: Blindagem contra a ausência da coluna HST nas planilhas obscuras
            if 'HST' in group.columns:
                avg_shots = pd.to_numeric(group['HST'], errors='coerce').mean()
            else:
                avg_shots = 4.0
            self.league_baselines[div] = {'xg_base': 1.35, 'shots_base': avg_shots if pd.notna(avg_shots) else 4.0}

        enhanced_rows = []
        for index, row in df.iterrows():
            div = row['Div']
            season = str(row['Season'])
            home = str(row['HomeTeam'])
            away = str(row['AwayTeam'])
            league_season_key = f"{div}_{season}"
            
            if league_season_key not in self.universe_state:
                self.universe_state[league_season_key] = {}
                
            state = self.universe_state[league_season_key]
            if home not in state: state[home] = {'pts':0, 'gd':0, 'gf':0, 'matches':0, 'form': []}
            if away not in state: state[away] = {'pts':0, 'gd':0, 'gf':0, 'matches':0, 'form': []}
            
            baseline = self.league_baselines.get(div, {'xg_base': 1.35, 'shots_base': 4.0})
            self._init_team_tactics(home, baseline['xg_base'], baseline['shots_base'])
            self._init_team_tactics(away, baseline['xg_base'], baseline['shots_base'])
            
            current_round = max(state[home]['matches'], state[away]['matches']) + 1
            
            sorted_table = sorted(state.keys(), key=lambda t: (state[t]['pts'], state[t]['gd'], state[t]['gf']), reverse=True)
            home_pos = sorted_table.index(home) + 1 if state[home]['matches'] > 0 else 0
            away_pos = sorted_table.index(away) + 1 if state[away]['matches'] > 0 else 0
            
            home_tactics = self.tactical_memory[home]
            away_tactics = self.tactical_memory[away]
            
            delta_elo = home_tactics['elo'] - away_tactics['elo']
            home_form_str = "".join(state[home]['form'][-5:])
            away_form_str = "".join(state[away]['form'][-5:])
            
            row_dict = row.to_dict()
            row_dict['Round'] = current_round
            row_dict['Context'] = 'Regular Season'
            row_dict['HomePosition'] = home_pos
            row_dict['AwayPosition'] = away_pos
            row_dict['delta_elo'] = delta_elo
            row_dict['home_pts_before'] = state[home]['pts']
            row_dict['away_pts_before'] = state[away]['pts']
            row_dict['home_form'] = home_form_str
            row_dict['away_form'] = away_form_str
            row_dict['h_xg_for_micro'] = home_tactics['xg_for_micro']
            row_dict['h_xg_ag_micro'] = home_tactics['xg_ag_micro']
            row_dict['a_xg_for_micro'] = away_tactics['xg_for_micro']
            row_dict['a_xg_ag_micro'] = away_tactics['xg_ag_micro']
            row_dict['h_shots_for'] = home_tactics['shots_for']
            row_dict['a_shots_for'] = away_tactics['shots_for']
            enhanced_rows.append(row_dict)

            hg = pd.to_numeric(row.get('FTHG', 0), errors='coerce')
            ag = pd.to_numeric(row.get('FTAG', 0), errors='coerce')
            hg = 0 if pd.isna(hg) else hg
            ag = 0 if pd.isna(ag) else ag
            
            h_shots = pd.to_numeric(row.get('HST', 0), errors='coerce') if 'HST' in row else 0
            a_shots = pd.to_numeric(row.get('AST', 0), errors='coerce') if 'AST' in row else 0
            h_shots = 0 if pd.isna(h_shots) else h_shots
            a_shots = 0 if pd.isna(a_shots) else a_shots
            
            state[home]['matches'] += 1
            state[away]['matches'] += 1
            state[home]['gf'] += hg
            state[away]['gf'] += ag
            state[home]['gd'] += (hg - ag)
            state[away]['gd'] += (ag - hg)
            
            res_h = self._get_result_char(hg, ag)
            res_a = self._get_result_char(ag, hg)
            state[home]['form'].append(res_h)
            state[away]['form'].append(res_a)
            
            if res_h == 'W': state[home]['pts'] += 3
            elif res_a == 'W': state[away]['pts'] += 3
            else:
                state[home]['pts'] += 1
                state[away]['pts'] += 1
                
            proxy_xg_h = h_shots * 0.3
            proxy_xg_a = a_shots * 0.3
            
            self.tactical_memory[home]['xg_for_micro'] = self._update_ewma(home_tactics['xg_for_micro'], proxy_xg_h, self.SPAN_MICRO)
            self.tactical_memory[home]['xg_ag_micro'] = self._update_ewma(home_tactics['xg_ag_micro'], proxy_xg_a, self.SPAN_MICRO)
            self.tactical_memory[home]['shots_for'] = self._update_ewma(home_tactics['shots_for'], h_shots, self.SPAN_MICRO)
            
            self.tactical_memory[away]['xg_for_micro'] = self._update_ewma(away_tactics['xg_for_micro'], proxy_xg_a, self.SPAN_MICRO)
            self.tactical_memory[away]['xg_ag_micro'] = self._update_ewma(away_tactics['xg_ag_micro'], proxy_xg_h, self.SPAN_MICRO)
            self.tactical_memory[away]['shots_for'] = self._update_ewma(away_tactics['shots_for'], a_shots, self.SPAN_MICRO)
            
            expected_h = 1.0 / (1.0 + 10.0 ** ((away_tactics['elo'] - home_tactics['elo']) / 400.0))
            actual_h = 1.0 if res_h == 'W' else (0.0 if res_h == 'L' else 0.5)
            elo_shift = 20.0 * (actual_h - expected_h)
            self.tactical_memory[home]['elo'] += elo_shift
            self.tactical_memory[away]['elo'] -= elo_shift

        return pd.DataFrame(enhanced_rows)

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {'Home': 'HomeTeam', 'Away': 'AwayTeam', 'HG': 'FTHG', 'AG': 'FTAG', 'Res': 'FTR', 'League': 'Div'}
        df = df.rename(columns=rename_map)
        if 'Date' not in df.columns or 'HomeTeam' not in df.columns or 'AwayTeam' not in df.columns:
            return pd.DataFrame()
        df = df.dropna(subset=['Date', 'HomeTeam', 'AwayTeam'])
        
        if 'Season' not in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df['Season'] = df['Date'].dt.year.astype(str)
        else:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            
        if 'Div' not in df.columns: df['Div'] = 'GLOBAL'
        df = df.dropna(subset=['Date'])
        return df

    async def run_backfill(self):
        logger.info("=========================================================")
        logger.info("⏳ INICIANDO ETL S-TIER: NO FUTURE LEAKAGE")
        logger.info("=========================================================")
        
        await db.connect()
        async with db.pool.acquire() as conn:
            await self.initialize_schema(conn)
        
        try:
            await entity_resolver.load_mappings_from_db()
        except Exception as e:
            logger.warning(f"Aviso NLP: {e}. Rodando sem Aliases.")

        for file_path in self.files_to_process:
            if not file_path.exists():
                logger.error(f"❌ Arquivo não encontrado: {file_path}")
                continue
                
            logger.info(f"📥 Lendo e Higienizando TODAS as Abas de: {file_path.name}")
            try:
                engine_type = 'openpyxl' if file_path.suffix == '.xlsx' else 'xlrd'
                dict_dfs = pd.read_excel(file_path, sheet_name=None, engine=engine_type)
                
                all_sheets_df = []
                for sheet_name, df_sheet in dict_dfs.items():
                    if not df_sheet.empty:
                        if 'Div' not in df_sheet.columns and 'League' not in df_sheet.columns:
                            df_sheet['Div'] = sheet_name.upper()
                        all_sheets_df.append(df_sheet)
                
                df = pd.concat(all_sheets_df, ignore_index=True) if all_sheets_df else pd.DataFrame()

            except Exception as e:
                logger.error(f"Erro ao ler excel {file_path.name}: {e}")
                continue
                
            df = self._clean_dataframe(df)
            if df.empty: continue
            
            df = self._calculate_base_features(df)
            
            records_history = []
            records_features = []
            
            async with db.pool.acquire() as conn:
                logger.info("🧠 Resolvendo IDs e Preparando Batch de Injeção...")
                
                for index, row in df.iterrows():
                    match_date = row['Date'].date()
                    season = str(row['Season'])
                    sport_key = str(row['Div']).upper()
                    
                    raw_home = str(row['HomeTeam'])
                    raw_away = str(row['AwayTeam'])
                    
                    h_name = await self.safe_normalize(raw_home)
                    a_name = await self.safe_normalize(raw_away)
                    
                    h_id = await self.auto_register_team(conn, h_name, sport_key)
                    a_id = await self.auto_register_team(conn, a_name, sport_key)
                    if not h_id or not a_id: continue

                    m_hash = self._generate_match_hash(str(match_date), h_name, a_name)

                    def get_val(col, is_int=False):
                        if col in df.columns and pd.notna(row[col]):
                            try:
                                val = float(row[col])
                                return int(val) if is_int else val
                            except ValueError: pass
                        return None
                    
                    def get_str(col):
                        if col in df.columns and pd.notna(row[col]): return str(row[col])
                        return None

                    hist_record = (
                        m_hash, sport_key, season, match_date, h_id, a_id, 
                        get_val('Round', True), get_str('Context'),
                        get_val('HomePosition', True), get_val('AwayPosition', True),
                        get_val('FTHG', True), get_val('FTAG', True), get_str('FTR'),
                        get_val('HTHG', True), get_val('HTAG', True), get_str('HTR'),
                        get_val('HS', True), get_val('AS', True), get_val('HST', True), get_val('AST', True), 
                        get_val('HC', True), get_val('AC', True), get_val('HF', True), get_val('AF', True), 
                        get_val('HY', True), get_val('AY', True), get_val('HR', True), get_val('AR', True),
                        get_str('Referee'),
                        get_val('B365H'), get_val('B365D'), get_val('B365A'), 
                        get_val('PSH'), get_val('PSD'), get_val('PSA'),       
                        get_val('PSCH'), get_val('PSCD'), get_val('PSCA'),    
                        None, None, None, None, 
                        get_val('AHh'), get_val('PAHH'), get_val('PAHA'), get_val('PCAHH'), get_val('PCAHA'),
                        'FINISHED' 
                    )
                    records_history.append(hist_record)
                    
                    feat_record = (
                        m_hash,
                        get_val('delta_elo'), get_val('home_pts_before', True), get_val('away_pts_before', True),
                        get_str('home_form'), get_str('away_form'),
                        get_val('h_xg_for_micro'), get_val('h_xg_ag_micro'), get_val('a_xg_for_micro'), get_val('a_xg_ag_micro'),
                        get_val('h_shots_for'), get_val('a_shots_for')
                    )
                    records_features.append(feat_record)

                if records_history:
                    logger.info(f"⚡ Disparando UPSERT massivo: {len(records_history)} jogos para a Base Primária...")
                    
                    query_history = """
                        INSERT INTO core.matches_history 
                        (match_hash, sport_key, season, match_date, home_team_id, away_team_id, 
                         round_num, context, home_position, away_position,
                         home_goals, away_goals, match_result, ht_home_goals, ht_away_goals, ht_result,
                         home_shots, away_shots, home_shots_target, away_shots_target, 
                         home_corners, away_corners, home_fouls, away_fouls, 
                         home_yellow, away_yellow, home_red, away_red, referee,
                         closing_odd_home, closing_odd_draw, closing_odd_away,
                         pin_odd_home, pin_odd_draw, pin_odd_away,
                         pin_closing_home, pin_closing_draw, pin_closing_away, 
                         odd_over_25, odd_under_25, odd_btts_yes, odd_btts_no, 
                         ah_line, pin_ah_home, pin_ah_away, pin_closing_ah_home, pin_closing_ah_away, status)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 
                                $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, 
                                $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, 
                                $31, $32, $33, $34, $35, $36, $37, $38, $39, $40, 
                                $41, $42, $43, $44, $45, $46, $47, $48)
                        ON CONFLICT (match_hash) DO UPDATE SET round_num = EXCLUDED.round_num
                        RETURNING id, match_hash;
                    """
                    
                    inserted_map = {}
                    async with conn.transaction():
                        for h_rec in records_history:
                            res_id = await conn.fetchval(query_history, *h_rec)
                            if res_id:
                                inserted_map[h_rec[0]] = res_id
                                
                    logger.info("🧠 Preenchendo a Feature Store S-Tier...")
                    
                    final_features = []
                    for f_rec in records_features:
                        m_hash = f_rec[0]
                        real_id = inserted_map.get(m_hash)
                        if real_id:
                            final_features.append((real_id,) + f_rec[1:])
                            
                    if final_features:
                        query_features = """
                            INSERT INTO quant_ml.feature_store 
                            (match_id, delta_elo, home_pts_before, away_pts_before, home_form, away_form,
                             h_xg_for_micro, h_xg_ag_micro, a_xg_for_micro, a_xg_ag_micro, h_shots_for, a_shots_for)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                            ON CONFLICT (match_id) DO UPDATE SET
                                delta_elo = EXCLUDED.delta_elo,
                                h_xg_for_micro = EXCLUDED.h_xg_for_micro,
                                a_xg_for_micro = EXCLUDED.a_xg_for_micro;
                        """
                        await conn.executemany(query_features, final_features)

        await db.disconnect()
        logger.info("🏆 PIPELINE CONCLUÍDO. Base Primária e Cérebro Quântico operacionais.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(HistoricalBackfill().run_backfill())