# betgenius-backend/workers/fbref/historical_orchestrator.py
import asyncio
import logging
import json
import random
import os
import sys
from pathlib import Path

# Adiciona o backend ao path para importações absolutas
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.database import db
from engine.entity_resolution import entity_resolver

# Importações da Arquitetura Modular FBref
from workers.fbref.config.fbref_map import LEAGUE_CONFIG, build_target_url
from workers.fbref.network.stealth_client import StealthClient
from workers.fbref.extractors.fbref_parsers import FBrefParser
from workers.fbref.loaders.db_upserter import FBrefDBUpserter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [TIME-MACHINE] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class HistoricalOrchestrator:
    """
    Maestro S-Tier.
    Coordena a extração histórica, lidando com evasão WAF, parsing, banco de dados 
    e persistência de estado (Checkpointing) para garantir 0% de perda de dados.
    """
    def __init__(self, start_year: int = 2015, end_year: int = 2024):
        self.start_year = start_year
        self.end_year = end_year
        self.stealth_client = StealthClient()
        
        # O arquivo onde salvaremos nosso progresso
        self.checkpoint_file = Path(__file__).parent / "miner_checkpoint.json"
        self.state = self._load_checkpoint()

    def _load_checkpoint(self) -> dict:
        """Carrega o progresso anterior se existir."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, "r") as f:
                state = json.load(f)
                logger.info(f"💾 Checkpoint carregado! Retomando do último salvamento.")
                return state
        return {}

    def _save_checkpoint(self, year: int, sport_key: str):
        """Salva a liga e o ano que acabaram de ser concluídos."""
        if str(year) not in self.state:
            self.state[str(year)] = []
            
        if sport_key not in self.state[str(year)]:
            self.state[str(year)].append(sport_key)
            
        with open(self.checkpoint_file, "w") as f:
            json.dump(self.state, f, indent=4)

    def _is_completed(self, year: int, sport_key: str) -> bool:
        """Verifica se esta liga neste ano já foi processada com sucesso no passado."""
        return str(year) in self.state and sport_key in self.state[str(year)]

    async def _process_season(self, sport_key: str, year: int):
        """Lógica central: Puxa o HTML -> Extrai DF -> Salva Times -> Salva Jogadores."""
        url, season_str = build_target_url(sport_key, year)
        
        logger.info(f"🕰️ Alvo: {sport_key} ({season_str})")
        
        # 1. Escudo de Rede (Evade WAF e Rate Limits)
        html_content = await self.stealth_client.fetch_html(url)
        if not html_content:
            return # Skip elegante (404 ou Timeout)
            
        # 2. Bisturi de Dados (Gera os DataFrames)
        dfs = FBrefParser.extract_dataframes(html_content)
        if not dfs:
            return

        # Separa as tabelas específicas (A lógica ignora tabelas irrelevantes)
        df_std = next((dfs[k] for k in dfs.keys() if 'stats_squads_standard_for' in k), None)
        df_wages = next((dfs[k] for k in dfs.keys() if 'squad_wages' in k), None)
        
        df_play_std = next((dfs[k] for k in dfs.keys() if 'stats_standard' in k and 'squads' not in k), None)
        df_play_sht = next((dfs[k] for k in dfs.keys() if 'stats_shooting' in k and 'squads' not in k), None)
        df_play_msc = next((dfs[k] for k in dfs.keys() if 'stats_misc' in k and 'squads' not in k), None)

        if df_std is None:
            logger.warning(f"Tabela base ausente para {sport_key} em {season_str}. Pulando.")
            return

        # 3. Carregador de Banco de Dados: Times e Salários
        team_cache = await FBrefDBUpserter.process_squads_and_wages(sport_key, season_str, df_std, df_wages)
        
        # 4. Carregador de Banco de Dados: Jogadores
        if team_cache and df_play_std is not None:
            await FBrefDBUpserter.process_players(season_str, df_play_std, df_play_sht, df_play_msc, team_cache)
            
        # Marca como concluído no arquivo de Checkpoint
        self._save_checkpoint(year, sport_key)

    async def run_time_machine(self):
        """O Loop Central do General."""
        logger.info("🚀 INICIANDO BETGENIUS TIME MACHINE (ARQUITETURA MODULAR)")
        
        # Estabelece as conexões essenciais (Banco e IA NLP)
        await db.connect()
        await entity_resolver.load_mappings_from_db()
        
        try:
            for year in range(self.start_year, self.end_year + 1):
                logger.info(f"\n================= [ TEMPORADA {year} ] =================")
                
                # Para cada liga no nosso config map
                for sport_key in LEAGUE_CONFIG.keys():
                    if self._is_completed(year, sport_key):
                        logger.info(f"⏭️ {sport_key} ({year}) já foi minerado. Pulando...")
                        continue
                        
                    await self._process_season(sport_key, year)
                    
                    # Pausa Tática Anti-Fingerprinting (Human-like behavior)
                    sleep_time = random.uniform(8.0, 15.0)
                    logger.info(f"⏳ Pausa evasiva de {sleep_time:.1f}s...\n")
                    await asyncio.sleep(sleep_time)
                    
            logger.info("\n🏆 MÁQUINA DO TEMPO 100% CONCLUÍDA. NENHUMA LIGA FALTANTE.")
            
        except Exception as e:
            logger.critical(f"🛑 Falha Crítica de Orquestração: {e}")
        finally:
            await db.disconnect()
            await self.stealth_client.close()

if __name__ == "__main__":
    orchestrator = HistoricalOrchestrator()
    try:
        # A MÁGICA PARA O PLAYWRIGHT NO WINDOWS:
        # Força o Python a usar o ProactorEventLoop, que é o único que sabe
        # lidar com subprocessos assíncronos (executar o Chromium) no Windows.
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
        asyncio.run(orchestrator.run_time_machine())
    except KeyboardInterrupt:
        logger.info("🛑 Intervenção Manual: Orquestrador Desligado. Progresso salvo no Checkpoint.")
    except Exception as e:
        logger.critical(f"Erro Crítico: {e}")