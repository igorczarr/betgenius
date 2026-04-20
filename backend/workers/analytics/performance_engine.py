# betgenius-backend/workers/analytics/performance_engine.py

import asyncio
import logging
import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# =====================================================================
# BLINDAGEM DE ENCODING PARA WINDOWS E CARREGAMENTO DO .ENV
# =====================================================================
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)
sys.path.append(str(BASE_DIR))

from core.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [PERFORMANCE-ENGINE] %(message)s")
logger = logging.getLogger(__name__)

class PerformanceEngine:
    """
    O Auditor Forense do Fundo Quantitativo S-Tier.
    Analisa Ligas, Times, SGP (Same Game Parlays), Faixas de Odds e a métrica sagrada: CLV.
    """

    async def get_fund_ledger_data(self) -> pd.DataFrame:
        """Puxa o histórico de operações com JOINs para enriquecer os dados."""
        logger.info("📡 Extraindo o Livro-Razão (Ledger) e cruzando com o Data Lake...")
        await db.connect()
        
        # Cruzamos o ledger com a matches_history e teams para ter os nomes reais
        query = """
            SELECT 
                fl.id, fl.match_id, fl.ticker, fl.jogo, fl.mercado, 
                fl.status, fl.odd_placed, fl.stake_amount, fl.pnl, fl.clv_edge,
                m.sport_key as league_key,
                th.canonical_name as home_team,
                ta.canonical_name as away_team
            FROM core.fund_ledger fl
            LEFT JOIN core.matches_history m ON fl.match_id = m.id
            LEFT JOIN core.teams th ON m.home_team_id = th.id
            LEFT JOIN core.teams ta ON m.away_team_id = ta.id
            WHERE fl.status IN ('WON', 'LOST', 'REFUNDED')
        """
        
        async with db.pool.acquire() as conn:
            records = await conn.fetch(query)
            
        await db.disconnect()
        
        if not records:
            logger.warning("⚠️ O Livro-Razão está vazio ou sem operações finalizadas.")
            return pd.DataFrame()
            
        df = pd.DataFrame([dict(r) for r in records])
        
        # Sanitização Financeira
        for col in ['stake_amount', 'pnl', 'clv_edge', 'odd_placed']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        # Classificação de Odds (Buckets) para descobrir a faixa de risco ideal
        bins = [1.0, 1.5, 2.0, 3.0, 5.0, 10.0, 100.0]
        labels = ['1.01-1.50 (Favoritaço)', '1.51-2.00 (Favorito)', '2.01-3.00 (Equilibrado)', 
                  '3.01-5.00 (Zebra Leve)', '5.01-10.00 (Zebra)', '10.00+ (Loteria)']
        df['odd_range'] = pd.cut(df['odd_placed'], bins=bins, labels=labels)
        
        return df

    def analyze_dimension(self, df: pd.DataFrame, group_col: str, min_bets: int = 5) -> pd.DataFrame:
        """Motor genérico de agregação S-Tier (Calcula PnL, Win Rate, ROI e CLV)."""
        df_resolved = df[df['status'].isin(['WON', 'LOST'])]
        
        if df_resolved.empty: return pd.DataFrame()

        grouped = df_resolved.groupby(group_col).agg(
            Volume=('id', 'count'),
            Wins=('status', lambda x: (x == 'WON').sum()),
            Stake_Total=('stake_amount', 'sum'),
            PnL=('pnl', 'sum'),
            Avg_Odd=('odd_placed', 'mean'),
            Avg_CLV=('clv_edge', 'mean') # O quanto batemos a Pinnacle em média
        ).reset_index()

        grouped = grouped[grouped['Volume'] >= min_bets] # Filtro de Variância
        if grouped.empty: return pd.DataFrame()

        grouped['WinRate(%)'] = (grouped['Wins'] / grouped['Volume']) * 100
        grouped['ROI(%)'] = (grouped['PnL'] / grouped['Stake_Total']) * 100

        # Formatação profissional
        grouped = grouped.sort_values(by='ROI(%)', ascending=False)
        grouped['WinRate(%)'] = grouped['WinRate(%)'].round(2)
        grouped['ROI(%)'] = grouped['ROI(%)'].round(2)
        grouped['Avg_Odd'] = grouped['Avg_Odd'].round(2)
        grouped['Avg_CLV'] = grouped['Avg_CLV'].round(4)
        grouped['PnL'] = grouped['PnL'].round(2)
        
        return grouped

    def analyze_teams(self, df: pd.DataFrame, min_bets: int = 5) -> pd.DataFrame:
        """Desmembra os jogos para analisar a lucratividade envolvendo times específicos."""
        # Duplica as linhas para Home e Away para contar a presença do time no ticket
        df_home = df[['home_team', 'status', 'stake_amount', 'pnl', 'clv_edge', 'odd_placed', 'id']].copy()
        df_home.rename(columns={'home_team': 'Team'}, inplace=True)
        
        df_away = df[['away_team', 'status', 'stake_amount', 'pnl', 'clv_edge', 'odd_placed', 'id']].copy()
        df_away.rename(columns={'away_team': 'Team'}, inplace=True)
        
        df_teams = pd.concat([df_home, df_away], ignore_index=True)
        # Remove nulos e times não identificados
        df_teams = df_teams[df_teams['Team'].notna()]
        
        return self.analyze_dimension(df_teams, 'Team', min_bets)

    async def run_audit(self):
        df = await self.get_fund_ledger_data()
        if df.empty: return

        print("\n" + "="*80)
        print("🏆 RELATÓRIO DE ATRIBUIÇÃO DE PERFORMANCE (QUANT AUDIT) 🏆")
        print("="*80)

        # 1. Análise por Ligas
        if 'league_key' in df.columns:
            leagues = self.analyze_dimension(df, 'league_key', min_bets=3)
            if not leagues.empty:
                print("\n🌍 TOP LIGAS (Eficiência da IA por País):")
                print(leagues[['league_key', 'Volume', 'WinRate(%)', 'Avg_CLV', 'ROI(%)', 'PnL']].head(5).to_string(index=False))

        # 2. Análise por Mercados e SGP
        if 'mercado' in df.columns:
            markets = self.analyze_dimension(df, 'mercado', min_bets=3)
            if not markets.empty:
                print("\n🛒 MERCADOS E SGP (Match Odds vs Bet Builders):")
                print(markets[['mercado', 'Volume', 'WinRate(%)', 'Avg_Odd', 'ROI(%)']].head(5).to_string(index=False))

        # 3. Análise por Faixa de Odds (Onde o modelo é mais preciso?)
        if 'odd_range' in df.columns:
            odds_analysis = self.analyze_dimension(df, 'odd_range', min_bets=2)
            if not odds_analysis.empty:
                print("\n🎯 ZONAS DE PRECIFICAÇÃO (Atuação por Faixa de Odd):")
                print(odds_analysis[['odd_range', 'Volume', 'WinRate(%)', 'Avg_CLV', 'ROI(%)']].to_string(index=False))

        # 4. Análise por Times (Quem nos dá mais dinheiro?)
        teams = self.analyze_teams(df, min_bets=3)
        if not teams.empty:
            print("\n🛡️ TIMES MAIS LUCRATIVOS (Em jogos envolvendo estas equipes):")
            print(teams[['Team', 'Volume', 'WinRate(%)', 'ROI(%)', 'PnL']].head(5).to_string(index=False))
            print("\n☠️ TIMES MAIS TÓXICOS (Blacklist Recomendada):")
            print(teams[['Team', 'Volume', 'WinRate(%)', 'ROI(%)', 'PnL']].tail(5).to_string(index=False))

        print("\n" + "="*80)
        print("💡 INSIGHT QUANTITATIVO:")
        print("Se o [Avg_CLV] for positivo mas o [ROI(%)] for negativo, mantenha a estratégia (é apenas Variância).")
        print("Se o [Avg_CLV] for negativo, a IA está precificando mal. Adicione essa liga/time na Blacklist.")
        print("="*80 + "\n")

if __name__ == "__main__":
    auditor = PerformanceEngine()
    asyncio.run(auditor.run_audit())