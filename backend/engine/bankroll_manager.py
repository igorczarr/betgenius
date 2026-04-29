# betgenius-backend/engine/bankroll_manager.py

import sys
import os
import asyncio
import logging
import ast
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))
from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [BANKROLL-MANAGER] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class BankrollManager:
    """
    O Tesoureiro S-Tier do Fundo.
    Liquida apostas simples e SGP (Same Game Parlays) analisando perna a perna.
    Gerencia devoluções (Pushes) em mercados asiáticos e DNB.
    """
    def __init__(self):
        self.initial_capital = 5000.00 

    async def initialize_schema(self, conn):
        logger.info("🛠️ Validando Schema Financeiro (Cofre S-Tier)...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS core.fund_wallet (
                id SERIAL PRIMARY KEY,
                balance NUMERIC(12, 2) NOT NULL,
                total_invested NUMERIC(12, 2) DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS core.fund_ledger (
                id SERIAL PRIMARY KEY,
                match_id INTEGER REFERENCES core.matches_history(id),
                ticker VARCHAR(50), 
                jogo VARCHAR(150),
                mercado VARCHAR(50), -- Agora suporta 'SGP'
                selecao VARCHAR(255), -- Ex: "['1X', 'O1.5']"
                odd_placed NUMERIC(6, 2),
                stake_amount NUMERIC(10, 2),
                pnl NUMERIC(10, 2) DEFAULT 0.0,
                clv_edge NUMERIC(5, 4) DEFAULT 0.0,
                status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, WON, LOST, REFUNDED, PARTIAL_WON
                placed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                settled_at TIMESTAMP
            );
        """)
        
        wallet_exists = await conn.fetchval("SELECT id FROM core.fund_wallet LIMIT 1")
        if not wallet_exists:
            await conn.execute("INSERT INTO core.fund_wallet (balance) VALUES ($1)", self.initial_capital)
            logger.info(f"🏦 Capital Semente Injetado: R$ {self.initial_capital:.2f}")

    async def place_bet(self, match_id: int, ticker: str, jogo: str, mercado: str, selecao: str, odd: float, stake: float, clv: float = 0.0):
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                current_balance = await conn.fetchval("SELECT balance FROM core.fund_wallet FOR UPDATE")
                if current_balance < stake:
                    logger.warning(f"❌ Saldo Insuficiente para apostar R$ {stake} em {jogo}.")
                    return False

                new_balance = current_balance - stake
                await conn.execute("UPDATE core.fund_wallet SET balance = $1, last_updated = NOW()", new_balance)

                await conn.execute("""
                    INSERT INTO core.fund_ledger (match_id, ticker, jogo, mercado, selecao, odd_placed, stake_amount, clv_edge)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, match_id, ticker, jogo, mercado, str(selecao), odd, stake, clv)

                logger.info(f"💸 Ordem Executada: {jogo} | {selecao} @ {odd} | Stake: R$ {stake:.2f} | Saldo: R$ {new_balance:.2f}")
                return True

    def _resolve_leg(self, leg_id: str, h_goals: int, a_goals: int, ht_h: int, ht_a: int, corners: int, cards: int) -> str:
        """
        Analisa o resultado de uma única seleção (Perna) de uma aposta.
        Retorna: 'WON', 'LOST' ou 'REFUND' (Devolvida/Void)
        """
        t_goals = h_goals + a_goals
        
        # 1X2 Simples e Dupla Chance
        if leg_id == '1X': return 'WON' if h_goals >= a_goals else 'LOST'
        if leg_id == 'X2': return 'WON' if a_goals >= h_goals else 'LOST'
        if leg_id == 'HOME': return 'WON' if h_goals > a_goals else 'LOST'
        if leg_id == 'AWAY': return 'WON' if h_goals < a_goals else 'LOST'
        if leg_id == 'DRAW': return 'WON' if h_goals == a_goals else 'LOST'
        
        # Draw No Bet (DNB) - Empate Anula
        if leg_id == 'HOME_DNB': 
            if h_goals > a_goals: return 'WON'
            if h_goals == a_goals: return 'REFUND'
            return 'LOST'
        if leg_id == 'AWAY_DNB': 
            if a_goals > h_goals: return 'WON'
            if a_goals == h_goals: return 'REFUND'
            return 'LOST'

        # Half-Time
        if leg_id == 'HT_1X': return 'WON' if ht_h >= ht_a else 'LOST'
        
        # Over/Under Gols (Asiático exato gera REFUND)
        if leg_id == 'O1.5': return 'WON' if t_goals > 1.5 else 'LOST'
        if leg_id == 'U3.5': return 'WON' if t_goals < 3.5 else 'LOST'
        if leg_id == 'O2.0':
            if t_goals > 2: return 'WON'
            if t_goals == 2: return 'REFUND'
            return 'LOST'
            
        # BTTS
        if leg_id == 'BTTS_Y': return 'WON' if h_goals > 0 and a_goals > 0 else 'LOST'
        if leg_id == 'BTTS_N': return 'WON' if h_goals == 0 or a_goals == 0 else 'LOST'
        
        # Corners e Cards
        if leg_id == 'CORN_O8.5': return 'WON' if corners > 8.5 else 'LOST'
        if leg_id == 'CORN_U11.5': return 'WON' if corners < 11.5 else 'LOST'
        if leg_id == 'CARD_U5.5': return 'WON' if cards < 5.5 else 'LOST'
        
        # Handicap Asiático (Exemplos Básicos)
        if leg_id == 'AH_HOME_+1.0':
            if h_goals - a_goals > -1: return 'WON'
            if h_goals - a_goals == -1: return 'REFUND'
            return 'LOST'

        logger.warning(f"⚠️ Seleção desconhecida: {leg_id}. Assumindo LOST.")
        return 'LOST'

    def _resolve_sgp_ticket(self, selecoes_str: str, odd_inicial: float, h_goals: int, a_goals: int, ht_h: int, ht_a: int, corners: int, cards: int) -> tuple:
        """
        Liquida um bilhete SGP ou aposta simples.
        Retorna: (Status_Final, Odd_Recalculada)
        """
        # Se for string no formato lista "['1X', 'O1.5']", extrai as pernas
        try:
            if selecoes_str.startswith('['):
                legs = ast.literal_eval(selecoes_str)
            else:
                # Se for aposta simples ("HOME"), transforma numa lista de 1 perna
                legs = [selecoes_str]
        except:
            legs = [selecoes_str]

        won_count = 0
        refund_count = 0
        total_legs = len(legs)

        for leg in legs:
            res = self._resolve_leg(leg.strip("[]'\" "), h_goals, a_goals, ht_h, ht_a, corners, cards)
            if res == 'LOST':
                # Se 1 perna num SGP perder, a aposta inteira é perdida
                return 'LOST', 0.0
            elif res == 'WON':
                won_count += 1
            elif res == 'REFUND':
                refund_count += 1

        if refund_count == total_legs:
            # Tudo foi devolvido
            return 'REFUNDED', 1.0

        if won_count == total_legs:
            # SGP Completo Venceu
            return 'WON', odd_inicial

        if won_count > 0 and refund_count > 0:
            # Parte ganhou, parte foi devolvida (Ode recalculated fallback rule)
            # Para SGP Asiático, as casas dividem a odd proporcionalmente. 
            # Num cálculo simples quantitativo: a odd final cai baseado nas pernas perdidas no push.
            odd_reduzida = max(1.0, odd_inicial * (won_count / total_legs))
            return 'PARTIAL_WON', odd_reduzida
            
        return 'LOST', 0.0

    async def settle_pending_bets(self):
        logger.info("⚖️ Iniciando processo de Liquidação (Settlement) S-Tier...")
        await db.connect()
        
        async with db.pool.acquire() as conn:
            await self.initialize_schema(conn)
            
            # Busca todas as apostas PENDING onde o jogo tem status FINISHED
            query = """
                SELECT l.id, l.match_id, l.mercado, l.selecao, l.odd_placed, l.stake_amount, l.jogo,
                       m.home_goals, m.away_goals, m.ht_home_goals, m.ht_away_goals,
                       m.home_corners, m.away_corners, m.home_yellow, m.away_yellow, m.home_red, m.away_red
                FROM core.fund_ledger l
                JOIN core.matches_history m ON l.match_id = m.id
                WHERE l.status = 'PENDING' AND m.status = 'FINISHED'
            """
            pending_bets = await conn.fetch(query)
            
            if not pending_bets:
                logger.info("ℹ️ Nenhuma aposta finalizada aguardando liquidação.")
                await db.disconnect()
                return

            settled_won = 0
            settled_lost = 0
            settled_refunds = 0
            profit_loss = 0.0

            async with conn.transaction():
                current_balance = await conn.fetchval("SELECT balance FROM core.fund_wallet FOR UPDATE")
                
                for bet in pending_bets:
                    bet_id = bet['id']
                    stake = float(bet['stake_amount'])
                    odd_original = float(bet['odd_placed'])
                    
                    h_g = int(bet['home_goals'])
                    a_g = int(bet['away_goals'])
                    ht_h = int(bet['ht_home_goals']) if bet['ht_home_goals'] else 0
                    ht_a = int(bet['ht_away_goals']) if bet['ht_away_goals'] else 0
                    corners = (bet['home_corners'] or 0) + (bet['away_corners'] or 0)
                    cards = (bet['home_yellow'] or 0) + (bet['away_yellow'] or 0) + ((bet['home_red'] or 0) * 2) + ((bet['away_red'] or 0) * 2)
                    
                    status, odd_final = self._resolve_sgp_ticket(bet['selecao'], odd_original, h_g, a_g, ht_h, ht_a, corners, cards)
                    
                    pnl = 0.0
                    if status == 'WON' or status == 'PARTIAL_WON':
                        pnl = stake * (odd_final - 1.0)
                        current_balance += (stake + pnl) 
                        settled_won += 1
                        logger.info(f"✅ {status}: {bet['jogo']} | Odd: {odd_final:.2f} | Lucro: R$ {pnl:.2f}")
                        
                    elif status == 'REFUNDED':
                        current_balance += stake # Apenas devolve a stake
                        settled_refunds += 1
                        logger.info(f"🔄 REFUND: {bet['jogo']} | Stake R$ {stake:.2f} devolvida.")
                        
                    elif status == 'LOST':
                        pnl = -stake 
                        settled_lost += 1
                        logger.info(f"❌ LOST: {bet['jogo']} | Prejuízo: R$ {pnl:.2f}")

                    profit_loss += pnl

                    await conn.execute("""
                        UPDATE core.fund_ledger 
                        SET status = $1, pnl = $2, odd_placed = $3, settled_at = NOW() 
                        WHERE id = $4
                    """, status, pnl, odd_final, bet_id)

                await conn.execute("UPDATE core.fund_wallet SET balance = $1, last_updated = NOW()", current_balance)
                
            logger.info("=========================================================")
            logger.info(f"📜 RELATÓRIO BANCÁRIO S-TIER (SGP & SIMPLES)")
            logger.info(f"  └ Acertos: {settled_won} | Pushes/Voids: {settled_refunds} | Erros: {settled_lost}")
            logger.info(f"  └ PnL Líquido da Sessão: R$ {profit_loss:.2f}")
            logger.info(f"  └ CAIXA FINAL DO FUNDO: R$ {current_balance:.2f}")
            logger.info("=========================================================")

        await db.disconnect()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(BankrollManager().settle_pending_bets())