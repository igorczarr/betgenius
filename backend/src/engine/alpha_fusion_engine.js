// backend/src/engine/alpha_fusion_engine.js
const db = require('../config/db');

class AlphaFusionEngine {
    /**
     * Motor Quantitativo S-Tier (Distribuição de Poisson & Value Betting).
     * Calcula as Probabilidades Reais baseadas no xG Histórico e compara com as Odds da Bet365.
     */

    // ========================================================================
    // 🧮 MÓDULO MATEMÁTICO (POISSON APROXIMADO)
    // ========================================================================
    static calculatePoissonProbability(lambda, k) {
        // P(x=k) = (e^(-lambda) * lambda^k) / k!
        let factorial = 1;
        for (let i = 1; i <= k; i++) factorial *= i;
        return (Math.exp(-lambda) * Math.pow(lambda, k)) / factorial;
    }

    static simulateMatch(xgHome, xgAway) {
        let homeWinProb = 0;
        let drawProb = 0;
        let awayWinProb = 0;
        let over25Prob = 0;
        let bttsYesProb = 0;

        // Simulamos placares de 0x0 até 5x5
        for (let h = 0; h <= 5; h++) {
            for (let a = 0; a <= 5; a++) {
                const prob = this.calculatePoissonProbability(xgHome, h) * this.calculatePoissonProbability(xgAway, a);
                
                if (h > a) homeWinProb += prob;
                else if (a > h) awayWinProb += prob;
                else drawProb += prob;

                if ((h + a) > 2.5) over25Prob += prob;
                if (h > 0 && a > 0) bttsYesProb += prob;
            }
        }

        return {
            homeWin: homeWinProb,
            draw: drawProb,
            awayWin: awayWinProb,
            over25: over25Prob,
            under25: 1 - over25Prob,
            bttsYes: bttsYesProb,
            bttsNo: 1 - bttsYesProb
        };
    }

    static calculateEV(trueProb, marketOdd) {
        if (!marketOdd || marketOdd <= 1.0) return 0;
        const ev = ((trueProb * marketOdd) - 1) * 100;
        return Number(ev.toFixed(2));
    }

    static getFairOdd(trueProb) {
        if (trueProb <= 0) return 0;
        return Number((1 / trueProb).toFixed(2));
    }

    // ========================================================================
    // 📊 MÓDULO DE FUSÃO DE DADOS (DB -> VUE.JS)
    // ========================================================================
    static async generateAlphaCards() {
        try {
            // 1. Busca os jogos agendados pros próximos dias e calcula o xG Médio recente das equipes
            const queryJogos = `
                WITH TeamForm AS (
                    SELECT 
                        home_team_id as team_id, AVG(xg_home) as avg_xg_for, AVG(xg_away) as avg_xg_against
                    FROM core.matches_history
                    WHERE status = 'FINISHED' AND match_date >= CURRENT_DATE - INTERVAL '60 days'
                    GROUP BY home_team_id
                    UNION ALL
                    SELECT 
                        away_team_id as team_id, AVG(xg_away) as avg_xg_for, AVG(xg_home) as avg_xg_against
                    FROM core.matches_history
                    WHERE status = 'FINISHED' AND match_date >= CURRENT_DATE - INTERVAL '60 days'
                    GROUP BY away_team_id
                ),
                AggregatedForm AS (
                    SELECT team_id, AVG(avg_xg_for) as expected_gf, AVG(avg_xg_against) as expected_ga
                    FROM TeamForm GROUP BY team_id
                )
                SELECT 
                    m.id as match_id, m.sport_key, m.match_date, 
                    th.canonical_name as casa, ta.canonical_name as fora,
                    COALESCE(fh.expected_gf, 1.2) as home_xg_for,
                    COALESCE(fh.expected_ga, 1.0) as home_xg_against,
                    COALESCE(fa.expected_gf, 1.1) as away_xg_for,
                    COALESCE(fa.expected_ga, 1.3) as away_xg_against
                FROM core.matches_history m
                JOIN core.teams th ON m.home_team_id = th.id
                JOIN core.teams ta ON m.away_team_id = ta.id
                LEFT JOIN AggregatedForm fh ON th.id = fh.team_id
                LEFT JOIN AggregatedForm fa ON ta.id = fa.team_id
                WHERE m.status = 'SCHEDULED' AND m.match_date >= CURRENT_DATE AND m.match_date <= CURRENT_DATE + INTERVAL '3 days'
            `;

            const { rows: upcomingMatches } = await db.query(queryJogos);
            const alphaOpportunities = [];

            for (const match of upcomingMatches) {
                // Cálculo de Força de Ataque vs Defesa
                const matchXgHome = (match.home_xg_for + match.away_xg_against) / 2;
                const matchXgAway = (match.away_xg_for + match.home_xg_against) / 2;

                // Roda o Modelo de Poisson
                const trueProbs = this.simulateMatch(matchXgHome, matchXgAway);

                // 2. Busca as Odds em Tempo Real do TheOdds Watcher
                const queryOdds = `SELECT * FROM core.market_odds WHERE match_id = $1`;
                const { rows: marketOdds } = await db.query(queryOdds, [match.match_id]);

                const mercadosProcessados = [];

                marketOdds.forEach(odd => {
                    let probReal = 0;
                    
                    // Mapeia o nome do mercado do banco para a nossa probabilidade calculada
                    const nome = odd.nome_mercado.toLowerCase();
                    if (nome.includes('home') || nome === '1') probReal = trueProbs.homeWin;
                    else if (nome.includes('draw') || nome === 'x') probReal = trueProbs.draw;
                    else if (nome.includes('away') || nome === '2') probReal = trueProbs.awayWin;
                    else if (nome.includes('over 2.5')) probReal = trueProbs.over25;
                    else if (nome.includes('under 2.5')) probReal = trueProbs.under25;
                    else if (nome === 'yes' && odd.categoria === 'btts') probReal = trueProbs.bttsYes;
                    else if (nome === 'no' && odd.categoria === 'btts') probReal = trueProbs.bttsNo;

                    if (probReal > 0) {
                        const ev = this.calculateEV(probReal, odd.current_odd);
                        const fairOdd = this.getFairOdd(probReal);

                        // Só envia para o frontend se for EV Positivo OU se teve Heavy Drop (Alerta)
                        if (ev > 2.0 || odd.heavy_drop_alert) {
                            mercadosProcessados.push({
                                id: odd.id,
                                categoria: odd.categoria,
                                selecao: odd.nome_mercado,
                                odd_atual: Number(odd.current_odd).toFixed(2),
                                odd_justa: fairOdd.toFixed(2),
                                odd_abertura: odd.opening_odd ? Number(odd.opening_odd).toFixed(2) : "-",
                                ev_pct: ev,
                                alerta_drop: odd.heavy_drop_alert
                            });
                        }
                        
                        // Atualiza silenciosamente a Odd Justa e o EV no banco para auditoria futura
                        db.query(`UPDATE core.market_odds SET fair_odd = $1, ev_pct = $2 WHERE id = $3`, 
                                [fairOdd, ev, odd.id]).catch(() => {});
                    }
                });

                if (mercadosProcessados.length > 0) {
                    alphaOpportunities.push({
                        match_id: match.match_id,
                        data: match.match_date,
                        liga: match.sport_key.split('_').pop().toUpperCase(),
                        casa: match.casa,
                        fora: match.fora,
                        oportunidades: mercadosProcessados.sort((a, b) => b.ev_pct - a.ev_pct)
                    });
                }
            }

            return alphaOpportunities;

        } catch (error) {
            console.error("❌ [ALPHA-ENGINE] Falha Crítica na Fusão Quantitativa:", error);
            throw error;
        }
    }
}

module.exports = AlphaFusionEngine;