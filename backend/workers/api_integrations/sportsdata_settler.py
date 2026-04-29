# betgenius-backend/workers/api_integrations/sportsdata_settler.py

import asyncio
import logging
import httpx
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Adiciona o backend ao path para importações absolutas
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.database import db
from engine.entity_resolution import entity_resolver

# Importamos o BankrollManager para fazer a liquidação do capital no final
from engine.bankroll_manager import BankrollManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SPORTSDATA-SETTLER] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class SportsDataSettler:
    """
    Motor de Liquidação S-Tier.
    Consome a SportsDataIO de forma hiper-eficiente (ByDate) para salvar cota.
    Extrai o Box Score final, calcula o xG Sintético, liquida as partidas no Data Warehouse
    e fecha o caixa das operações abertas no fund_ledger.
    """
    def __init__(self):
        self.api_key = os.getenv("SPORTSDATA_API_KEY", "")
        if not self.api_key:
            logger.critical("🚨 SPORTSDATA_API_KEY não encontrado no .env!")
            sys.exit(1)
            
        # Endpoints hiper-eficientes (1 chamada = Todos os jogos do dia globalmente)
        self.base_url_scores = "https://api.sportsdata.io/v4/soccer/scores/json/GamesByDate"
        self.base_url_stats = "https://api.sportsdata.io/v4/soccer/stats/json/TeamGameStatsByDate"

    def _calculate_synthetic_xg(self, shots_on_target: int, corners: int, dangerous_attacks: int) -> float:
        """
        Cálculo Quantitativo (Proxy): Estima o xG baseado em volume de pressão real.
        Pesos baseados em regressão de Poisson padrão de mercado.
        """
        xg = (shots_on_target * 0.28) + (corners * 0.05) + (dangerous_attacks * 0.015)
        return round(max(0.0, xg), 2)

    async def fetch_data_by_date(self, target_date: str, client: httpx.AsyncClient):
        """Busca Placares e Estatísticas do dia inteiro consumindo apenas 2 de cota."""
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        
        try:
            # 1. Busca os Placares (Scores & Status)
            logger.info(f"📡 Buscando Box Scores Globais para {target_date}...")
            resp_scores = await client.get(f"{self.base_url_scores}/{target_date}", headers=headers, timeout=20.0)
            
            # 2. Busca as Estatísticas Táticas (Chutes, Faltas, Cartões)
            logger.info(f"📡 Buscando Táticas Globais (Team Stats) para {target_date}...")
            resp_stats = await client.get(f"{self.base_url_stats}/{target_date}", headers=headers, timeout=20.0)
            
            if resp_scores.status_code == 200 and resp_stats.status_code == 200:
                return resp_scores.json(), resp_stats.json()
            else:
                logger.error(f"❌ Erro na API. Scores: {resp_scores.status_code} | Stats: {resp_stats.status_code}")
                return [], []
                
        except Exception as e:
            logger.error(f"Falha de conexão com a SportsDataIO: {e}")
            return [], []

    def _merge_game_data(self, games: list, team_stats: list) -> list:
        """Funde o JSON de Placares com o JSON de Estatísticas na memória (Evita for loop no banco)."""
        merged_games = []
        
        # Indexa as estatísticas pelo GameId e TeamId para busca O(1)
        stats_dict = {}
        for stat in team_stats:
            game_id = stat.get("GameId")
            team_id = stat.get("TeamId")
            if game_id not in stats_dict:
                stats_dict[game_id] = {}
            stats_dict[game_id][team_id] = stat

        for game in games:
            # Pula jogos cancelados ou adiados
            status = game.get("Status")
            if status not in ["Closed", "Final", "F/PEN", "F/AET"]:
                continue
                
            game_id = game.get("GameId")
            home_team_id = game.get("HomeTeamId")
            away_team_id = game.get("AwayTeamId")
            
            # Agrupa os dados do jogo com as estatísticas dos dois times
            match_data = {
                "date": game.get("Day", "").split("T")[0],
                "home_team": game.get("HomeTeamName"),
                "away_team": game.get("AwayTeamName"),
                "home_goals": game.get("HomeTeamScore", 0),
                "away_goals": game.get("AwayTeamScore", 0),
                "home_stats": stats_dict.get(game_id, {}).get(home_team_id, {}),
                "away_stats": stats_dict.get(game_id, {}).get(away_team_id, {})
            }
            merged_games.append(match_data)
            
        return merged_games

    async def settle_matches(self, target_date: str):
        """O Coração do Liquidante. Funde, normaliza os nomes e atualiza o banco de dados."""
        await db.connect()
        await entity_resolver.load_mappings_from_db()
        
        async with httpx.AsyncClient() as client:
            games_raw, stats_raw = await self.fetch_data_by_date(target_date, client)
            
        if not games_raw:
            logger.warning(f"Nenhum dado retornado para a data {target_date}.")
            await db.disconnect()
            return
            
        matches_to_settle = self._merge_game_data(games_raw, stats_raw)
        logger.info(f"📊 {len(matches_to_settle)} partidas fechadas encontradas no mundo. Filtrando Matrix...")

        settled_count = 0
        
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                for match in matches_to_settle:
                    raw_home = match['home_team']
                    raw_away = match['away_team']
                    if not raw_home or not raw_away: continue
                    
                    # 1. Resolução NLP
                    home_canonical = await entity_resolver.normalize_name(raw_home, False)
                    away_canonical = await entity_resolver.normalize_name(raw_away, False)
                    
                    # 2. Busca o jogo pendente no banco
                    query = """
                        SELECT m.id 
                        FROM core.matches_history m
                        JOIN core.teams th ON m.home_team_id = th.id
                        JOIN core.teams ta ON m.away_team_id = ta.id
                        WHERE th.canonical_name = $1 AND ta.canonical_name = $2 
                        AND m.match_date = $3 AND m.status != 'FINISHED'
                    """
                    match_id = await conn.fetchval(query, home_canonical, away_canonical, datetime.strptime(match['date'], "%Y-%m-%d").date())
                    
                    if not match_id:
                        continue # Jogo de liga que não monitoramos ou já liquidado
                        
                    # 3. Extração das Estatísticas S-Tier
                    hs = match['home_stats']
                    ast = match['away_stats']
                    
                    h_shots_on_target = hs.get("ShotsOnGoal", 0) or 0
                    a_shots_on_target = ast.get("ShotsOnGoal", 0) or 0
                    
                    h_corners = hs.get("Corners", 0) or 0
                    a_corners = ast.get("Corners", 0) or 0
                    
                    h_da = hs.get("DangerousAttacks", 0) or 0
                    a_da = ast.get("DangerousAttacks", 0) or 0
                    
                    # Motor de xG Sintético
                    xg_home = self._calculate_synthetic_xg(h_shots_on_target, h_corners, h_da)
                    xg_away = self._calculate_synthetic_xg(a_shots_on_target, a_corners, a_da)
                    
                    h_goals = match['home_goals']
                    a_goals = match['away_goals']
                    result = 'H' if h_goals > a_goals else ('A' if a_goals > h_goals else 'D')
                    
                    # 4. UPDATE Cirúrgico de Liquidação
                    # Usamos COALESCE no xg para NÃO sobrescrever o xG do FBref (se ele já existir)
                    await conn.execute("""
                        UPDATE core.matches_history 
                        SET home_goals = $1, away_goals = $2, match_result = $3,
                            home_shots_target = $4, away_shots_target = $5,
                            home_corners = $6, away_corners = $7,
                            home_fouls = $8, away_fouls = $9,
                            home_yellow = $10, away_yellow = $11,
                            home_red = $12, away_red = $13,
                            xg_home = COALESCE(xg_home, $14), xg_away = COALESCE(xg_away, $15),
                            status = 'FINISHED'
                        WHERE id = $16
                    """, 
                    h_goals, a_goals, result,
                    h_shots_on_target, a_shots_on_target,
                    h_corners, a_corners,
                    hs.get("Fouls", 0) or 0, ast.get("Fouls", 0) or 0,
                    hs.get("YellowCards", 0) or 0, ast.get("YellowCards", 0) or 0,
                    hs.get("RedCards", 0) or 0, ast.get("RedCards", 0) or 0,
                    xg_home, xg_away,
                    match_id)
                    
                    settled_count += 1
                    
        logger.info(f"🏆 BOX SCORES CONCLUÍDOS: {settled_count} partidas convertidas para FINISHED.")
        
        # 5. O FECHAMENTO DO CAIXA (Liquidação do Ledger)
        logger.info("💼 Acionando o Bankroll Manager para liquidar operações abertas no fundo...")
        try:
            manager = BankrollManager()
            await manager.settle_pending_bets()
            logger.info("✅ Capital liquidado e saldo atualizado no Banco de Dados.")
        except Exception as e:
            logger.error(f"Erro ao liquidar o Ledger: {e}")

        await db.disconnect()

if __name__ == "__main__":
    settler = SportsDataSettler()
    
    # Executa a liquidação dos jogos de ONTEM (Garante que todos os jogos da meia noite terminaram)
    ontem = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(settler.settle_matches(ontem))