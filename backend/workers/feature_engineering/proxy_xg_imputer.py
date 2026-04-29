# betgenius-backend/workers/feature_engineering/proxy_xg_imputer.py
import sys
import os
import io
import asyncio
import logging
from collections import deque
from pathlib import Path
from dotenv import load_dotenv

# =====================================================================
# BLINDAGEM DE ENCODING PARA WINDOWS E .ENV
# =====================================================================
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

class AdvancedProxyXGImputer:
    """
    Imputação e Projeção S-Tier (Padrão Quant).
    1. Passado (FINISHED): Cura dados ausentes cruzando Elo com Fatos (Shots/Corners).
    2. Presente/Futuro (SCHEDULED): Projeta o xG/90, Momentum (1H/2H) e xG/Shot 
       baseado na memória tática móvel (últimos 9 jogos) da equipe.
    """
    def __init__(self):
        self.WINDOW = 9 # A Janela de Ouro do Futebol (Estabilização Tática)
        self.BASE_XG_DEFAULT = 1.35 
        self.BASE_SHOTS_DEFAULT = 4.0 # Média de chutes no alvo para base bayesiana
        
        self.LEAGUES_MVP = [
            'soccer_epl', 'soccer_spain_la_liga', 'soccer_italy_serie_a', 
            'soccer_germany_bundesliga', 'soccer_france_ligue_one'
        ]

        self.team_xg_for = {}
        self.team_xg_against = {}
        self.team_shots_for = {} # Nova memória para calcular a Qualidade do Chute (xG/Shot)
        self.league_season_stats = {} 

    async def _ensure_advanced_schema(self, conn):
        """Garante que a base suporta as métricas derivadas e as projeções do futuro."""
        logger.info("🛠️ Validando Schema de xG Preditivo e Momentum...")
        await conn.execute("""
            ALTER TABLE core.matches_history 
            -- Passado (Curado)
            ADD COLUMN IF NOT EXISTS xg_home_1h NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS xg_away_1h NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS xg_home_2h NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS xg_away_2h NUMERIC(5,2),
            -- Futuro (Projetado pelo Modelo para o ViewMatchCenter)
            ADD COLUMN IF NOT EXISTS proj_xg_90_home NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS proj_xg_90_away NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS proj_xg_1h_home NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS proj_xg_1h_away NUMERIC(5,2),
            ADD COLUMN IF NOT EXISTS proj_xg_shot_home NUMERIC(5,3),
            ADD COLUMN IF NOT EXISTS proj_xg_shot_away NUMERIC(5,3);
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
        """Puxa a média móvel. Se tiver poucos jogos, funde com a média da liga (Bayesian Padding)."""
        history = metric_deque.get(team_id, [])
        games_played = len(history)
        if games_played == 0: return league_avg
            
        real_sum = sum(history)
        padding_needed = self.WINDOW - games_played
        smoothed_avg = (real_sum + (padding_needed * league_avg)) / self.WINDOW
        return smoothed_avg

    def calculate_bayesian_xg(self, atk_id: int, def_id: int, league: str, season: str, 
                              elo_atk: float, elo_def: float, is_home: bool,
                              shots_on_target: int = None, corners: int = None) -> float:
        """
        Mistura a Força Teórica (Dixon-Coles + Elo) com a Produção Real (Shots/Corners).
        Se for jogo SCHEDULED, shots_on_target e corners serão None, devolvendo a Projeção Pura.
        """
        league_avg = self._get_league_avg(league, season)
        
        # 1. Priori (Teoria)
        team_atk_avg = self._get_team_metric(atk_id, self.team_xg_for, league_avg)
        team_def_avg = self._get_team_metric(def_id, self.team_xg_against, league_avg)
        
        expected_xg = league_avg * (team_atk_avg / league_avg) * (team_def_avg / league_avg)
        elo_multiplier = max(0.5, min(1.8, 1.0 + ((elo_atk - elo_def) / 1000.0)))
        dixon_xg = expected_xg * elo_multiplier * (1.12 if is_home else 0.88)
        
        # Se não temos dados reais (jogo do futuro/agendado), a expectativa É a realidade
        if shots_on_target is None and corners is None:
            return round(max(0.05, min(5.0, dixon_xg)), 2)

        # 2. Posteriori (Realidade) para jogos do passado
        stat_xg = (shots_on_target * 0.28) + (corners * 0.05) if (shots_on_target or corners) else 0.0
        
        if stat_xg > 0:
            final_xg = (stat_xg * 0.70) + (dixon_xg * 0.30)
        else:
            final_xg = dixon_xg
            
        return round(max(0.05, min(5.0, final_xg)), 2)

    def distribute_momentum_xg(self, total_xg: float, ht_goals: int = None, ft_goals: int = None) -> tuple:
        """
        Derivação de Momentum (1H/2H). 
        Se for jogo futuro (ht_goals = None), usa a proporção acadêmica estrita de 45%/55%.
        """
        ratio_1h = 0.45
        
        # Game State Adjustment (Apenas se o jogo já aconteceu)
        if ht_goals is not None and ft_goals is not None:
            goals_2h = ft_goals - ht_goals
            if ht_goals > 0 and goals_2h == 0:
                ratio_1h += 0.15 # Sentou no resultado
            elif ht_goals == 0 and goals_2h > 0:
                ratio_1h -= 0.10 # Acordou no 2º tempo
            elif ht_goals > 0 and goals_2h > 0:
                ratio_1h += 0.05 # Jogo muito aberto no 1º tempo
                
            ratio_1h = max(0.20, min(0.80, ratio_1h))
        
        xg_1h = round(total_xg * ratio_1h, 2)
        xg_2h = round(total_xg - xg_1h, 2)
        
        return xg_1h, xg_2h

    async def run_imputation(self):
        logger.info("=========================================================")
        logger.info("🩺 INICIANDO MOTOR PREDITIVO S-TIER: XG, MOMENTUM & XG/SHOT")
        logger.info("=========================================================")
        
        await db.connect()
        
        try:
            async with db.pool.acquire() as conn:
                await self._ensure_advanced_schema(conn)
                
                logger.info("🧹 Expurgo Inicial: Detectando xG estagnado ou nulo no Passado...")
                await conn.execute("UPDATE core.matches_history SET xg_home = NULL, xg_away = NULL WHERE xg_home <= 0.05 OR xg_away <= 0.05 AND status = 'FINISHED';")

                logger.info("📥 Extraindo Matriz Cronológica de Jogos (Passado e Futuro)...")
                
                # Buscamos FINISHED e SCHEDULED para que a memória se acumule e projete o futuro
                query = f"""
                    SELECT m.id, m.match_date, m.sport_key, m.season, m.status,
                           m.home_team_id, m.away_team_id, 
                           m.xg_home, m.xg_away, m.home_goals, m.away_goals,
                           m.ht_home_goals, m.ht_away_goals,
                           m.home_shots_target, m.away_shots_target, m.home_corners, m.away_corners,
                           e.home_elo_before, e.away_elo_before
                    FROM core.matches_history m
                    LEFT JOIN core.match_elo_history e ON m.id = e.match_id
                    WHERE m.status IN ('FINISHED', 'SCHEDULED')
                    AND m.sport_key = ANY($1::varchar[])
                    ORDER BY m.match_date ASC, m.id ASC
                """
                matches = await conn.fetch(query, self.LEAGUES_MVP)
                
                if not matches:
                    logger.warning("Banco de dados vazio para as Ligas MVP.")
                    return

                records_to_update_finished = []
                records_to_update_scheduled = []
                logger.info(f"🧬 Simulando Matriz Temporal de Extremos para {len(matches)} partidas...")

                for row in matches:
                    m_id = row['id']
                    h_id = row['home_team_id']
                    a_id = row['away_team_id']
                    status = row['status']
                    sport_key = row['sport_key']
                    season = row['season']
                    
                    elo_h = float(row['home_elo_before']) if row['home_elo_before'] else 1500.0
                    elo_a = float(row['away_elo_before']) if row['away_elo_before'] else 1500.0

                    self._init_team_memory(h_id)
                    self._init_team_memory(a_id)

                    # ========================================================
                    # A. TRATAMENTO DO PASSADO (FINISHED) - Cura os dados reais
                    # ========================================================
                    if status == 'FINISHED':
                        xg_h = float(row['xg_home']) if row['xg_home'] else None
                        xg_a = float(row['xg_away']) if row['xg_away'] else None
                        
                        h_sot = int(row['home_shots_target']) if row['home_shots_target'] else 0
                        a_sot = int(row['away_shots_target']) if row['away_shots_target'] else 0
                        h_cor = int(row['home_corners']) if row['home_corners'] else 0
                        a_cor = int(row['away_corners']) if row['away_corners'] else 0
                        
                        ht_hg = int(row['ht_home_goals']) if row['ht_home_goals'] is not None else (int(row['home_goals']) // 2)
                        ht_ag = int(row['ht_away_goals']) if row['ht_away_goals'] is not None else (int(row['away_goals']) // 2)
                        ft_hg = int(row['home_goals']) if row['home_goals'] is not None else 0
                        ft_ag = int(row['away_goals']) if row['away_goals'] is not None else 0

                        needs_update = False

                        if xg_h is None:
                            xg_h = self.calculate_bayesian_xg(h_id, a_id, sport_key, season, elo_h, elo_a, True, h_sot, h_cor)
                            needs_update = True
                        if xg_a is None:
                            xg_a = self.calculate_bayesian_xg(a_id, h_id, sport_key, season, elo_a, elo_h, False, a_sot, a_cor)
                            needs_update = True

                        h_1h, h_2h = self.distribute_momentum_xg(xg_h, ht_hg, ft_hg)
                        a_1h, a_2h = self.distribute_momentum_xg(xg_a, ht_ag, ft_ag)
                        needs_update = True 

                        # ATUALIZAÇÃO DA MEMÓRIA TEMPORAL (O Modelo Aprende)
                        self.team_xg_for[h_id].append(xg_h)
                        self.team_xg_against[h_id].append(xg_a)
                        self.team_shots_for[h_id].append(h_sot) # Memória de chutes

                        self.team_xg_for[a_id].append(xg_a)
                        self.team_xg_against[a_id].append(xg_h)
                        self.team_shots_for[a_id].append(a_sot) # Memória de chutes

                        self._update_league_stats(sport_key, season, xg_h, xg_a)

                        if needs_update:
                            records_to_update_finished.append((m_id, xg_h, xg_a, h_1h, h_2h, a_1h, a_2h))

                    # ========================================================
                    # B. TRATAMENTO DO FUTURO (SCHEDULED) - Projeta para a Tela
                    # ========================================================
                    elif status == 'SCHEDULED':
                        # 1. xG/90 (Projeção Total) - Enviamos None em shots/corners para acionar projeção pura
                        proj_xg_h = self.calculate_bayesian_xg(h_id, a_id, sport_key, season, elo_h, elo_a, True, None, None)
                        proj_xg_a = self.calculate_bayesian_xg(a_id, h_id, sport_key, season, elo_a, elo_h, False, None, None)

                        # 2. xG Momentum (Dinâmico para 1º Tempo) - Usamos a base teórica de 45%
                        proj_1h_h, _ = self.distribute_momentum_xg(proj_xg_h, None, None)
                        proj_1h_a, _ = self.distribute_momentum_xg(proj_xg_a, None, None)

                        # 3. Qualidade de Chute (xG / Shot) - Exigência Institucional
                        avg_shots_h = self._get_team_metric(h_id, self.team_shots_for, self.BASE_SHOTS_DEFAULT)
                        avg_shots_a = self._get_team_metric(a_id, self.team_shots_for, self.BASE_SHOTS_DEFAULT)
                        
                        proj_xg_shot_h = proj_xg_h / avg_shots_h if avg_shots_h > 0 else 0.10
                        proj_xg_shot_a = proj_xg_a / avg_shots_a if avg_shots_a > 0 else 0.10

                        records_to_update_scheduled.append((
                            m_id, 
                            proj_xg_h, proj_xg_a, 
                            proj_1h_h, proj_1h_a, 
                            round(min(1.0, proj_xg_shot_h), 3), round(min(1.0, proj_xg_shot_a), 3)
                        ))

                # ==================================================
                # INJEÇÃO DA CURA E DAS PROJEÇÕES NO DATA WAREHOUSE
                # ==================================================
                async with conn.transaction():
                    if records_to_update_finished:
                        logger.info(f"💉 Curando {len(records_to_update_finished)} partidas do PASSADO...")
                        await conn.executemany("""
                            UPDATE core.matches_history 
                            SET xg_home = $2, xg_away = $3,
                                xg_home_1h = $4, xg_home_2h = $5,
                                xg_away_1h = $6, xg_away_2h = $7
                            WHERE id = $1
                        """, records_to_update_finished)

                    if records_to_update_scheduled:
                        logger.info(f"🔮 Projetando xG Dinâmico, Momentum e xG/Shot para {len(records_to_update_scheduled)} partidas do FUTURO...")
                        await conn.executemany("""
                            UPDATE core.matches_history 
                            SET proj_xg_90_home = $2, proj_xg_90_away = $3,
                                proj_xg_1h_home = $4, proj_xg_1h_away = $5,
                                proj_xg_shot_home = $6, proj_xg_shot_away = $7
                            WHERE id = $1
                        """, records_to_update_scheduled)
                        
                logger.info("✅ PIPELINE PREDITIVO CONCLUÍDO! O ViewMatchCenter agora prevê o futuro.")

        except Exception as e:
            logger.error(f"❌ Erro Crítico durante a Matriz Preditiva de xG: {e}")
        finally:
            await db.disconnect()

if __name__ == "__main__":
    imputer = AdvancedProxyXGImputer()
    asyncio.run(imputer.run_imputation())