# betgenius-backend/engine/data_fusion.py

import sys
import os
import io
import logging

if sys.platform == 'win32':
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

class ASCIILogFormatter(logging.Formatter):
    def format(self, record):
        try: return super().format(record)
        except Exception:
            record.msg = str(record.msg).encode('ascii', 'ignore').decode('ascii')
            return super().format(record)

logging.root.handlers = []
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(ASCIILogFormatter("%(asctime)s [DATA-FUSION] %(levelname)s: %(message)s"))
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

import asyncio
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from core.database import db
from engine.entity_resolution import entity_resolver

class DataFusionEngine:
    """
    O Juiz Final da Informação.
    Lê as zonas de quarentena (Staging), cruza as entidades (Times), 
    valida a integridade (Placares) e forja o registro definitivo na Tabela Core.
    """
    def __init__(self):
        self.pending_bex = []
        self.pending_fbr = []

    async def _fetch_pending_data(self, conn):
        """Puxa todos os registros que estão aguardando fusão nas duas frentes."""
        self.pending_bex = await conn.fetch("SELECT * FROM core.staging_bex_matches WHERE fusion_status = 'PENDING'")
        self.pending_fbr = await conn.fetch("SELECT * FROM core.staging_fbr_matches WHERE fusion_status = 'PENDING'")
        logger.info(f"📥 Encontrados na Quarentena: {len(self.pending_bex)} BEX (Odds) | {len(self.pending_fbr)} FBR (Stats)")

    async def _mark_status(self, conn, table: str, record_id: int, status: str):
        await conn.execute(f"UPDATE {table} SET fusion_status = $1 WHERE id = $2", status, record_id)

    async def execute_fusion_cycle(self):
        logger.info("==================================================================")
        logger.info(" 🧬 INICIANDO CICLO DE FUSÃO DE DADOS (STAGING -> CORE) ")
        logger.info("==================================================================")

        await db.connect()
        await entity_resolver.load_mappings_from_db()

        async with db.pool.acquire() as conn:
            await self._fetch_pending_data(conn)
            
            if not self.pending_bex or not self.pending_fbr:
                logger.info("⏸️ Não há dados suficientes nas duas pontas para iniciar cruzamento.")
                await db.disconnect()
                return

            fusions_success = 0
            fusions_failed = 0

            # Pre-cache de entidades resolvidos do FBref para busca super rápida na memória (HFT style)
            fbr_dict = {}
            for f_row in self.pending_fbr:
                f_h_canon = await entity_resolver.normalize_name(f_row['raw_home_team'], is_pinnacle=False)
                f_a_canon = await entity_resolver.normalize_name(f_row['raw_away_team'], is_pinnacle=False)
                key = f"{f_row['match_date']}_{f_h_canon}_{f_a_canon}"
                fbr_dict[key] = f_row

            async with conn.transaction():
                for b_row in self.pending_bex:
                    # 1. Resolução de Entidade do BetExplorer
                    b_h_canon = await entity_resolver.normalize_name(b_row['raw_home_team'], is_pinnacle=False)
                    b_a_canon = await entity_resolver.normalize_name(b_row['raw_away_team'], is_pinnacle=False)
                    
                    search_key = f"{b_row['match_date']}_{b_h_canon}_{b_a_canon}"
                    
                    # 2. Busca o irmão perdido no FBref
                    if search_key in fbr_dict:
                        f_row = fbr_dict[search_key]
                        
                        # 3. A TRAVA DE SEGURANÇA MÁXIMA (Validação de Placar)
                        if b_row['home_goals'] == f_row['home_goals'] and b_row['away_goals'] == f_row['away_goals']:
                            
                            # Descobrimos os IDs oficiais no banco de dados
                            h_id = await conn.fetchval("SELECT id FROM core.teams WHERE canonical_name = $1", b_h_canon)
                            a_id = await conn.fetchval("SELECT id FROM core.teams WHERE canonical_name = $1", b_a_canon)
                            
                            if not h_id or not a_id:
                                await self._mark_status(conn, 'core.staging_bex_matches', b_row['id'], 'NO_TEAM_ID')
                                continue

                            # 4. A FUSÃO (Atualiza a Core Table mesclando Odds + Stats)
                            # Nota: O DailyUpdater já pode ter criado a linha 'SCHEDULED'. Aqui nós finalizamos ela.
                            await conn.execute("""
                                UPDATE core.matches_history SET 
                                    home_goals = $1, away_goals = $2,
                                    ht_home_goals = $3, ht_away_goals = $4,
                                    xg_home = $5, xg_away = $6,
                                    home_shots = $7, away_shots = $8,
                                    home_shots_target = $9, away_shots_target = $10,
                                    home_corners = $11, away_corners = $12,
                                    home_yellow = $13, away_yellow = $14,
                                    home_red = $15, away_red = $16,
                                    home_fouls = $17, away_fouls = $18,
                                    referee = $19,
                                    closing_odd_home = $20, closing_odd_draw = $21, closing_odd_away = $22,
                                    odd_over_25 = $23, odd_under_25 = $24,
                                    ah_line = $25, pin_closing_ah_home = $26, pin_closing_ah_away = $27,
                                    status = 'FINISHED',
                                    match_result = CASE WHEN $1 > $2 THEN 'H' WHEN $2 > $1 THEN 'A' ELSE 'D' END
                                WHERE match_date = $28 AND home_team_id = $29 AND away_team_id = $30
                            """, 
                            b_row['home_goals'], b_row['away_goals'], 
                            b_row['ht_home_goals'], b_row['ht_away_goals'],
                            f_row['xg_home'], f_row['xg_away'],
                            f_row['home_shots'], f_row['away_shots'],
                            f_row['home_shots_target'], f_row['away_shots_target'],
                            f_row['home_corners'], f_row['away_corners'],
                            f_row['home_yellow'], f_row['away_yellow'],
                            f_row['home_red'], f_row['away_red'],
                            f_row['home_fouls'], f_row['away_fouls'],
                            f_row['referee'],
                            b_row['odd_1_closing'], b_row['odd_x_closing'], b_row['odd_2_closing'],
                            b_row['odd_over_25_closing'], b_row['odd_under_25_closing'],
                            b_row['ah_line'], b_row['odd_ah_home_closing'], b_row['odd_ah_away_closing'],
                            b_row['match_date'], h_id, a_id)

                            # 5. Sucesso! Libera os registros da quarentena
                            await self._mark_status(conn, 'core.staging_bex_matches', b_row['id'], 'MATCHED')
                            await self._mark_status(conn, 'core.staging_fbr_matches', f_row['id'], 'MATCHED')
                            fusions_success += 1

                        else:
                            # Alarme de Discrepância: Placar diferente entre BEX e FBR
                            logger.error(f"🚨 DISCREPÂNCIA DE PLACAR: {b_h_canon} v {b_a_canon} ({b_row['match_date']}). BEX={b_row['home_goals']}x{b_row['away_goals']} | FBR={f_row['home_goals']}x{f_row['away_goals']}")
                            await self._mark_status(conn, 'core.staging_bex_matches', b_row['id'], 'MISMATCH_SCORE')
                            await self._mark_status(conn, 'core.staging_fbr_matches', f_row['id'], 'MISMATCH_SCORE')
                            fusions_failed += 1

            logger.info(f"✅ Fusões com Sucesso: {fusions_success} partidas seladas.")
            if fusions_failed > 0:
                logger.warning(f"⚠️ Fusões Abortadas: {fusions_failed} partidas com erros de integridade isoladas na quarentena.")

        await db.disconnect()
        logger.info("==================================================================")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(DataFusionEngine().execute_fusion_cycle())