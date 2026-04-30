# betgenius-backend/workers/feature_engineering/proxy_xg_imputer.py
import sys
import os
import io
import asyncio
import logging
import math
from collections import deque
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ADVANCED-PROXY-XG] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def safe_int(val, default=0):
    try:
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default

def safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default

class AdvancedProxyXGImputer:
    """
    Motor S-Tier de xG Proxy (Nível StatsBomb/Opta).
    Utiliza uma Abordagem Bayesiana cruzando o 'Prior' (Força Dixon-Coles e Elo)
    com a 'Evidence' (Volume de jogo, Modulador de Qualidade de Remate e Estado de Jogo/Cartões).
    """
    def __init__(self):
        self.WINDOW = 9 
        self.BASE_XG_DEFAULT = 1.35 
        self.BASE_SHOTS_DEFAULT = 4.0 
        
        self.team_xg_for = {}
        self.team_xg_against = {}
        self.team_shots_for = {} 
        self.league_season_stats = {} 

    async def _ensure_advanced_schema(self, conn):
        logger.info("🛠️ Validando Schema de xG Preditivo e Momentum...")
        await conn.execute("""
            ALTER TABLE core.matches_history 
            ADD COLUMN IF NOT EXISTS xg_home NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS xg_away NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS xg_home_1h NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS xg_away_1h NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS xg_home_2h NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS xg_away_2h NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS proj_xg_90_home NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS proj_xg_90_away NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS proj_xg_1h_home NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS proj_xg_1h_away NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS proj_xg_shot_home NUMERIC(5,3),
            ADD COLUMN IF NOT EXISTS proj_xg_shot_away NUMERIC(5,3),
            -- Novas métricas avançadas
            ADD COLUMN IF NOT EXISTS xg_shot_home NUMERIC(5,3),
            ADD COLUMN IF NOT EXISTS xg_shot_away NUMERIC(5,3),
            ADD COLUMN IF NOT EXISTS xg_momentum_home NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS xg_momentum_away NUMERIC(5,2);
        """)

    def _init_team_memory(self, team_id: int):
        if team_id not in self.team_xg_for:
            self.team_xg_for[team_id] = deque(maxlen=self.WINDOW)
            self.team_xg_against[team_id] = deque(maxlen=self.WINDOW)
            self.team_shots_for[team_id] = deque(maxlen=self.WINDOW)

    def _update_league_stats(self, league: str, season: str, xg_h: float, xg_a: float):
        key = f"{league}_{season}"
        if key not in self.league_season_stats:
            self.league_season_stats[key] = {'total_xg': 0.0, 'matches': 0}
        self.league_season_stats[key]['total_xg'] += (xg_h + xg_a)
        self.league_season_stats[key]['matches'] += 2

    def _get_league_avg(self, league: str, season: str) -> float:
        key = f"{league}_{season}"
        stats = self.league_season_stats.get(key)
        if not stats or stats['matches'] == 0: return self.BASE_XG_DEFAULT
        return stats['total_xg'] / stats['matches']

    def _get_team_metric(self, team_id: int, metric_deque: dict, league_avg: float) -> float:
        history = metric_deque.get(team_id, [])
        games_played = len(history)
        if games_played == 0: return league_avg
            
        real_sum = sum(history)
        padding_needed = self.WINDOW - games_played
        smoothed_avg = (real_sum + (padding_needed * league_avg)) / self.WINDOW
        return smoothed_avg

    def calculate_bayesian_xg(self, atk_id: int, def_id: int, league: str, season: str, 
                              elo_atk: float, elo_def: float, is_home: bool,
                              total_shots: int = None, shots_on_target: int = None, 
                              corners: int = None, red_cards_atk: int = 0, red_cards_def: int = 0) -> tuple:
        """
        Matemática Avançada de xG. Retorna (xG Total, xG/Shot).
        """
        league_avg = self._get_league_avg(league, season)
        
        team_atk_avg = self._get_team_metric(atk_id, self.team_xg_for, league_avg)
        team_def_avg = self._get_team_metric(def_id, self.team_xg_against, league_avg)
        
        base_expectation = league_avg * (team_atk_avg / league_avg) * (team_def_avg / league_avg)
        elo_multiplier = max(0.5, min(1.8, 1.0 + ((elo_atk - elo_def) / 1000.0)))
        home_adv = 1.12 if is_home else 0.88
        
        dixon_xg_prior = base_expectation * elo_multiplier * home_adv
        
        if total_shots is None and shots_on_target is None and corners is None:
            # Para jogos futuros, assumimos xG/Shot médio baseado no prior
            expected_shots = self._get_team_metric(atk_id, self.team_shots_for, self.BASE_SHOTS_DEFAULT)
            expected_xg = round(max(0.05, min(5.0, dixon_xg_prior)), 2)
            expected_xg_shot = expected_xg / expected_shots if expected_shots > 0 else 0.10
            return expected_xg, round(min(1.0, expected_xg_shot), 3)

        total_shots = max(0, total_shots)
        sot = max(0, shots_on_target)
        cor = max(0, corners)
        total_shots = max(total_shots, sot)
        shots_off_target = total_shots - sot

        q_factor = max(0.70, min(1.30, 1.0 + ((elo_atk - elo_def) / 1500.0)))

        game_state_mult = 1.0
        if red_cards_atk > 0: game_state_mult *= 0.75
        if red_cards_def > 0: game_state_mult *= 1.30

        evidence_xg = q_factor * game_state_mult * (
            (sot * 0.28) + 
            (shots_off_target * 0.035) + 
            (cor * 0.03)
        )
        
        if total_shots > 5:
            final_xg = (evidence_xg * 0.85) + (dixon_xg_prior * 0.15)
        elif total_shots > 0:
            final_xg = (evidence_xg * 0.60) + (dixon_xg_prior * 0.40)
        else:
            final_xg = dixon_xg_prior * 0.50
            
        final_xg = round(max(0.01, min(6.0, final_xg)), 2)
        
        # Calcular xG por remate (Eficiência de Finalização)
        xg_shot = final_xg / total_shots if total_shots > 0 else 0.0
        xg_shot = round(min(1.0, xg_shot), 3)

        return final_xg, xg_shot

    def distribute_momentum_xg(self, total_xg: float, ht_goals: int = None, ft_goals: int = None) -> tuple:
        """
        Distribui o xG e calcula o momentum.
        """
        ratio_1h = 0.45
        if ht_goals is not None and ft_goals is not None:
            goals_2h = max(0, ft_goals - ht_goals)
            
            if ht_goals > 0 and goals_2h == 0:
                ratio_1h += 0.15 
            elif ht_goals == 0 and goals_2h > 0:
                ratio_1h -= 0.10 
            elif ht_goals > 0 and goals_2h > 0:
                ratio_1h += 0.05 
                
            ratio_1h = max(0.20, min(0.80, ratio_1h))
        
        xg_1h = round(total_xg * ratio_1h, 2)
        xg_2h = round(total_xg - xg_1h, 2)
        
        # Momentum simplificado baseado na distribuição do xG
        momentum = xg_2h - xg_1h 
        
        return xg_1h, xg_2h, round(momentum, 2)

    async def run_imputation(self):
        logger.info("=========================================================")
        logger.info("🩺 INICIANDO MOTOR PREDITIVO S-TIER: BAYESIAN XG & MOMENTUM")
        logger.info("=========================================================")
        
        await db.connect()
        is_genesis = os.getenv("GENESIS_MODE", "False") == "True"
        
        try:
            async with db.pool.acquire() as conn:
                await self._ensure_advanced_schema(conn)
                
                if is_genesis:
                    logger.warning("⚠️ MODO GÊNESIS ATIVADO: Reconstrução Total e Forçada da Memória de xG.")

                logger.info("📥 Extraindo Matriz Cronológica incluindo Estado de Jogo (Cartões)...")
                query = """
                    SELECT m.id, m.match_date, m.sport_key, m.season, m.status,
                           m.home_team_id, m.away_team_id, 
                           m.home_goals, m.away_goals, m.ht_home_goals, m.ht_away_goals,
                           m.home_shots, m.away_shots, 
                           m.home_shots_target, m.away_shots_target, m.home_corners, m.away_corners,
                           m.home_red, m.away_red,
                           e.home_elo_before, e.away_elo_before
                    FROM core.matches_history m
                    LEFT JOIN core.match_elo_history e ON m.id = e.match_id
                    WHERE m.status IN ('FINISHED', 'SCHEDULED')
                    ORDER BY m.match_date ASC, m.id ASC
                """
                matches = await conn.fetch(query)
                
                if not matches:
                    logger.warning("Banco de dados vazio.")
                    return

                records_to_update_finished = []
                records_to_update_scheduled = []
                logger.info(f"🧬 Simulando Matriz Temporal Avançada para {len(matches)} partidas...")

                for row in matches:
                    m_id = row['id']
                    h_id = row['home_team_id']
                    a_id = row['away_team_id']
                    status = row['status']
                    sport_key = row['sport_key']
                    season = row['season']
                    
                    elo_h = safe_float(row['home_elo_before'], 1500.0)
                    elo_a = safe_float(row['away_elo_before'], 1500.0)

                    self._init_team_memory(h_id)
                    self._init_team_memory(a_id)

                    if status == 'FINISHED':
                        h_tot_shots = safe_int(row['home_shots'])
                        a_tot_shots = safe_int(row['away_shots'])
                        h_sot = safe_int(row['home_shots_target'])
                        a_sot = safe_int(row['away_shots_target'])
                        h_cor = safe_int(row['home_corners'])
                        a_cor = safe_int(row['away_corners'])
                        h_red = safe_int(row['home_red'])
                        a_red = safe_int(row['away_red'])
                        
                        ft_hg = safe_int(row['home_goals'])
                        ft_ag = safe_int(row['away_goals'])
                        ht_hg = safe_int(row['ht_home_goals'], default=(ft_hg // 2))
                        ht_ag = safe_int(row['ht_away_goals'], default=(ft_ag // 2))

                        xg_h, xg_shot_h = self.calculate_bayesian_xg(h_id, a_id, sport_key, season, elo_h, elo_a, True, 
                                                          h_tot_shots, h_sot, h_cor, h_red, a_red)
                        xg_a, xg_shot_a = self.calculate_bayesian_xg(a_id, h_id, sport_key, season, elo_a, elo_h, False, 
                                                          a_tot_shots, a_sot, a_cor, a_red, h_red)

                        h_1h, h_2h, mom_h = self.distribute_momentum_xg(xg_h, ht_hg, ft_hg)
                        a_1h, a_2h, mom_a = self.distribute_momentum_xg(xg_a, ht_ag, ft_ag)

                        self.team_xg_for[h_id].append(xg_h)
                        self.team_xg_against[h_id].append(xg_a)
                        self.team_shots_for[h_id].append(h_sot) 

                        self.team_xg_for[a_id].append(xg_a)
                        self.team_xg_against[a_id].append(xg_h)
                        self.team_shots_for[a_id].append(a_sot)

                        self._update_league_stats(sport_key, season, xg_h, xg_a)

                        records_to_update_finished.append((
                            m_id, float(xg_h), float(xg_a), float(h_1h), float(h_2h), float(a_1h), float(a_2h),
                            float(xg_shot_h), float(xg_shot_a), float(mom_h), float(mom_a)
                        ))

                    elif status == 'SCHEDULED':
                        proj_xg_h, proj_xg_shot_h = self.calculate_bayesian_xg(h_id, a_id, sport_key, season, elo_h, elo_a, True)
                        proj_xg_a, proj_xg_shot_a = self.calculate_bayesian_xg(a_id, h_id, sport_key, season, elo_a, elo_h, False)

                        proj_1h_h, _, _ = self.distribute_momentum_xg(proj_xg_h)
                        proj_1h_a, _, _ = self.distribute_momentum_xg(proj_xg_a)

                        records_to_update_scheduled.append((
                            m_id, float(proj_xg_h), float(proj_xg_a), float(proj_1h_h), float(proj_1h_a), 
                            float(proj_xg_shot_h), float(proj_xg_shot_a)
                        ))

                batch_size = 5000 
                
                if records_to_update_finished:
                    total_batches = (len(records_to_update_finished) // batch_size) + 1
                    logger.info(f"💉 Injetando {len(records_to_update_finished)} partidas do PASSADO em {total_batches} blocos...")
                    
                    query_update_finished = """
                        UPDATE core.matches_history 
                        SET xg_home = $2, xg_away = $3, xg_home_1h = $4, xg_home_2h = $5, xg_away_1h = $6, xg_away_2h = $7,
                            xg_shot_home = $8, xg_shot_away = $9, xg_momentum_home = $10, xg_momentum_away = $11
                        WHERE id = $1
                    """
                    for i in range(0, len(records_to_update_finished), batch_size):
                        await conn.executemany(query_update_finished, records_to_update_finished[i:i + batch_size])
                        logger.info(f"   └ Lote Passado {(i//batch_size)+1}/{total_batches} concluído.")

                if records_to_update_scheduled:
                    total_batches = (len(records_to_update_scheduled) // batch_size) + 1
                    logger.info(f"🔮 Projetando {len(records_to_update_scheduled)} partidas do FUTURO em {total_batches} blocos...")
                    
                    query_update_scheduled = """
                        UPDATE core.matches_history 
                        SET proj_xg_90_home = $2, proj_xg_90_away = $3, proj_xg_1h_home = $4, proj_xg_1h_away = $5,
                            proj_xg_shot_home = $6, proj_xg_shot_away = $7
                        WHERE id = $1
                    """
                    for i in range(0, len(records_to_update_scheduled), batch_size):
                        await conn.executemany(query_update_scheduled, records_to_update_scheduled[i:i + batch_size])
                        logger.info(f"   └ Lote Futuro {(i//batch_size)+1}/{total_batches} concluído.")
                        
                logger.info("✅ PIPELINE DE XG BAYESIANO CONCLUÍDO COM SUCESSO E DADOS GRAVADOS!")

        except Exception as e:
            logger.error(f"❌ Erro Crítico durante a Matriz Preditiva de xG: {e}")
        finally:
            await db.disconnect()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    imputer = AdvancedProxyXGImputer()
    asyncio.run(imputer.run_imputation())