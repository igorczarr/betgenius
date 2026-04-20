// betgenius-backend/controllers/settlementController.js

const pool = require('../config/db');

/**
 * Avaliador de Perna Única (Single Leg Evaluator).
 * Entende Moneyline, Double Chance, DNB, Handicaps, Over/Under e BTTS.
 */
const evaluateSingleLeg = (legString, homeGoals, awayGoals) => {
    const leg = legString.toLowerCase().trim();
    const totalGoals = homeGoals + awayGoals;
    const diff = homeGoals - awayGoals; // Positivo = Casa vence. Negativo = Visitante vence.

    // 1. MATCH ODDS (1X2) & MONEYLINE
    if (['home win', 'casa vence', '1', 'home ml', 'mandante', 'ah -0.5 home', 'home -0.5'].includes(leg)) return diff > 0 ? 'WON' : 'LOST';
    if (['away win', 'visitante vence', '2', 'away ml', 'visitante', 'ah -0.5 away', 'away -0.5'].includes(leg)) return diff < 0 ? 'WON' : 'LOST';
    if (['draw', 'empate', 'x'].includes(leg)) return diff === 0 ? 'WON' : 'LOST';

    // 2. DOUBLE CHANCE
    if (['1x', 'casa ou empate', 'home or draw', 'ah +0.5 home', 'home +0.5'].includes(leg)) return diff >= 0 ? 'WON' : 'LOST';
    if (['x2', 'visitante ou empate', 'away or draw', 'ah +0.5 away', 'away +0.5'].includes(leg)) return diff <= 0 ? 'WON' : 'LOST';
    if (['12', 'casa ou visitante', 'home or away'].includes(leg)) return diff !== 0 ? 'WON' : 'LOST';

    // 3. DRAW NO BET (DNB) / ASIAN HANDICAP 0.0
    if (leg.includes('dnb home') || leg.includes('empate anula casa') || leg.includes('ah 0.0 home') || leg.includes('home ah +0.0')) {
        if (diff > 0) return 'WON';
        if (diff === 0) return 'REFUNDED';
        return 'LOST';
    }
    if (leg.includes('dnb away') || leg.includes('empate anula visitante') || leg.includes('ah 0.0 away') || leg.includes('away ah +0.0')) {
        if (diff < 0) return 'WON';
        if (diff === 0) return 'REFUNDED';
        return 'LOST';
    }

    // 4. ASIAN HANDICAPS (-1.0, -1.5, +1.0, +1.5)
    if (leg.includes('home -1.5') || leg.includes('ah -1.5 home')) return diff >= 2 ? 'WON' : 'LOST';
    if (leg.includes('away -1.5') || leg.includes('ah -1.5 away')) return diff <= -2 ? 'WON' : 'LOST';
    
    if (leg.includes('home -1.0') || leg.includes('ah -1.0 home')) {
        if (diff >= 2) return 'WON';
        if (diff === 1) return 'REFUNDED';
        return 'LOST';
    }
    if (leg.includes('away -1.0') || leg.includes('ah -1.0 away')) {
        if (diff <= -2) return 'WON';
        if (diff === -1) return 'REFUNDED';
        return 'LOST';
    }

    // 5. OVER / UNDER GOLS (Regex Inteligente)
    const overMatch = leg.match(/(?:over|mais de)\s*(\d+\.?\d*)/);
    if (overMatch) return totalGoals > parseFloat(overMatch[1]) ? 'WON' : 'LOST';

    const underMatch = leg.match(/(?:under|menos de)\s*(\d+\.?\d*)/);
    if (underMatch) return totalGoals < parseFloat(underMatch[1]) ? 'WON' : 'LOST';

    // 6. BTTS (Ambas Marcam)
    if (leg.includes('btts') || leg.includes('ambas marcam')) {
        if (leg.includes('no') || leg.includes('não') || leg.includes('nao')) {
            return (homeGoals === 0 || awayGoals === 0) ? 'WON' : 'LOST';
        }
        return (homeGoals > 0 && awayGoals > 0) ? 'WON' : 'LOST';
    }

    // Perna não reconhecida
    return 'UNKNOWN';
};

/**
 * Avaliador Mestre de SGP (Same Game Parlay) e Combinadas
 */
const evaluateMarket = (marketString, homeGoals, awayGoals) => {
    // Se a string vier suja (ex: "SGP: Home Win + Over 2.5"), limpa a tag inicial
    const cleanMarket = marketString.replace(/sgp:|bilhete:|combinada:/gi, '').trim();

    // O separador universal (quebra o bilhete em pernas no sinal de +, virgula, "and" ou "e")
    const separators = /\+| e | and |,|&/i;
    const legs = cleanMarket.split(separators).map(l => l.trim()).filter(l => l.length > 0);

    let hasRefund = false;

    // Avalia cada perna do bilhete de forma isolada
    for (const leg of legs) {
        const legStatus = evaluateSingleLeg(leg, homeGoals, awayGoals);
        
        if (legStatus === 'UNKNOWN') {
            console.warn(`[PARSER WARNING] Não entendi a regra: "${leg}" no bilhete "${marketString}"`);
            return 'MANUAL_REVIEW';
        }
        if (legStatus === 'LOST') {
            // Em qualquer múltipla, um red destrói o bilhete inteiro. Não precisa checar o resto.
            return 'LOST'; 
        }
        if (legStatus === 'REFUNDED') {
            hasRefund = true;
        }
    }

    // Se chegou aqui, nenhuma perna foi LOST. 
    if (hasRefund) {
        // Se é aposta simples e devolveu (Ex: DNB) -> Reembolsa
        if (legs.length === 1) return 'REFUNDED';
        
        // Se for um SGP com 1 perna devolvida, a casa de aposta recalcula a odd final.
        // Como o nosso banco de dados não armazena a odd individual de cada perna da múltipla, 
        // não podemos calcular o valor novo da aposta sozinhos de forma segura. Vai para revisão manual.
        return 'MANUAL_REVIEW_SGP_REFUND';
    }

    return 'WON'; // Todas as pernas deram Green
};

exports.runSettlement = async (req, res) => {
    console.log("⚙️ [SETTLE ENGINE] Iniciando varredura e liquidação de apostas...");
    const client = await pool.connect();

    try {
        await client.query('BEGIN');

        // 1. Busca todas as apostas pendentes (LIVE) cujos jogos já terminaram na matches_history
        const pendingBetsQuery = `
            SELECT 
                fl.id as bet_id, 
                fl.wallet_id, 
                fl.mercado, 
                fl.stake_amount, 
                fl.odd_placed,
                m.home_goals, 
                m.away_goals
            FROM core.fund_ledger fl
            JOIN core.matches_history m ON fl.match_id = m.id
            WHERE fl.status = 'LIVE' 
            AND m.status = 'FINISHED'
            AND m.home_goals IS NOT NULL 
            AND m.away_goals IS NOT NULL;
        `;
        const { rows: pendingBets } = await client.query(pendingBetsQuery);

        if (pendingBets.length === 0) {
            await client.query('ROLLBACK');
            console.log("ℹ️ [SETTLE ENGINE] O Livro-Razão está em dia. Nenhuma aposta pendente.");
            return res.status(200).json({ message: "O Livro-Razão está em dia. Nenhuma aposta pendente." });
        }

        let settledCount = 0;
        let totalProfit = 0;
        let manualReviews = 0;

        // 2. Processa cada aposta pendente contra o resultado oficial
        for (const bet of pendingBets) {
            const status = evaluateMarket(bet.mercado, bet.home_goals, bet.away_goals);
            
            if (status.includes('MANUAL_REVIEW')) {
                manualReviews++;
                // Atualizamos para MANUAL_REVIEW para que o admin resolva pela interface
                await client.query('UPDATE core.fund_ledger SET status = $1 WHERE id = $2', [status, bet.bet_id]);
                continue;
            }

            let pnl = 0.0;
            let amountToReturnToWallet = 0.0;

            if (status === 'WON') {
                pnl = (bet.stake_amount * bet.odd_placed) - bet.stake_amount;
                amountToReturnToWallet = bet.stake_amount + pnl;
            } 
            else if (status === 'LOST') {
                pnl = -bet.stake_amount;
                amountToReturnToWallet = 0.0;
            } 
            else if (status === 'REFUNDED') {
                pnl = 0.0; 
                amountToReturnToWallet = bet.stake_amount; // Devolve apenas a Stake intacta
            }

            // A. Grava o Veredito no Livro-Razão
            await client.query(`
                UPDATE core.fund_ledger 
                SET status = $1, pnl = $2, settled_at = NOW() 
                WHERE id = $3
            `, [status, pnl, bet.bet_id]);

            // B. Repassa os fundos para a Banca do Fundo
            if (amountToReturnToWallet > 0) {
                await client.query(`
                    UPDATE core.fund_wallets 
                    SET balance = balance + $1, 
                        total_deposited = total_deposited + $2, 
                        updated_at = NOW()
                    WHERE id = $3
                `, [amountToReturnToWallet, pnl, bet.wallet_id]); 
            }

            settledCount++;
            totalProfit += pnl;
        }

        await client.query('COMMIT');
        
        console.log(`✅ [SETTLE ENGINE] Liquidação finalizada. Resolved: ${settledCount} | Manual Review: ${manualReviews} | PnL do Lote: ${totalProfit.toFixed(2)}u`);
        
        res.status(200).json({ 
            success: true, 
            settled_bets: settledCount,
            manual_reviews: manualReviews,
            batch_pnl: parseFloat(totalProfit.toFixed(2))
        });

    } catch (error) {
        await client.query('ROLLBACK');
        console.error("❌ Erro Crítico na Liquidação Financeira:", error);
        res.status(500).json({ error: "Falha na Engine de Liquidação do Fundo." });
    } finally {
        client.release();
    }
};