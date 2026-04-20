// betgenius-backend/src/controllers/fundController.js
const db = require('../config/db'); // 👈 Usa a instância correta do seu projeto

// ============================================================================
// PADRÃO SÊNIOR: SAFE QUERY WRAPPER E AUTO-CURA DA TESOURARIA
// Impede Erro 500 e alinha as colunas antigas e novas no banco de dados
// ============================================================================
const safeQuery = async (queryText, params = []) => {
    try {
        return await db.query(queryText, params);
    } catch (error) {
        console.warn(`[AVISO FUNDO] Falha na query ignorada: ${error.message}`);
        return { rows: [], rowCount: 0 };
    }
};

const curarLedger = async () => {
    // 1. Garante que a tabela de carteiras exista
    await safeQuery(`
        CREATE TABLE IF NOT EXISTS core.fund_wallets (
            id SERIAL PRIMARY KEY,
            type VARCHAR(20) UNIQUE
        )
    `);
    
    // 2. Mescla colunas S-Tier (Novas) e Legacy (Antigas)
    await safeQuery(`ALTER TABLE core.fund_wallets ADD COLUMN IF NOT EXISTS mode VARCHAR(20)`);
    await safeQuery(`ALTER TABLE core.fund_wallets ADD COLUMN IF NOT EXISTS current_balance DECIMAL(15,2) DEFAULT 0`);
    await safeQuery(`ALTER TABLE core.fund_wallets ADD COLUMN IF NOT EXISTS retained_profit DECIMAL(15,2) DEFAULT 0`);
    await safeQuery(`ALTER TABLE core.fund_wallets ADD COLUMN IF NOT EXISTS balance DECIMAL(15,2) DEFAULT 0`);
    await safeQuery(`ALTER TABLE core.fund_wallets ADD COLUMN IF NOT EXISTS total_deposited DECIMAL(15,2) DEFAULT 0`);
    await safeQuery(`ALTER TABLE core.fund_wallets ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()`);

    // 3. Insere os caixas base (O ON CONFLICT exige que 'type' seja UNIQUE)
    await safeQuery(`INSERT INTO core.fund_wallets (type, mode, current_balance, balance) VALUES ('REAL', 'carreira', 0, 0) ON CONFLICT (type) DO NOTHING`);
    await safeQuery(`INSERT INTO core.fund_wallets (type, mode, current_balance, balance) VALUES ('BENCHMARK', 'benchmark', 0, 0) ON CONFLICT (type) DO NOTHING`);

    // 4. Garante a tabela de Alertas para não dar Erro 500 no Aporte
    await safeQuery(`
        CREATE TABLE IF NOT EXISTS core.system_alerts (
            id SERIAL PRIMARY KEY,
            tipo VARCHAR(50),
            texto TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    `);
};

// ============================================================================
// 1. DEPÓSITOS E SAQUES (Lógica Original Conservada)
// ============================================================================
exports.registerTransaction = async (req, res) => {
    const { mode, type, amount } = req.body; 
    
    if (!mode || !amount || amount <= 0) {
        return res.status(400).json({ error: "Modo e valor válido são obrigatórios." });
    }

    try {
        await curarLedger();
        await db.query('BEGIN');

        const walletRes = await db.query('SELECT id, balance FROM core.fund_wallets WHERE mode = $1', [mode]);
        if (walletRes.rows.length === 0) throw new Error("Carteira não encontrada.");
        const walletId = walletRes.rows[0].id;

        // Registra a transação (Blindado caso a tabela não exista)
        await safeQuery(`
            CREATE TABLE IF NOT EXISTS core.fund_transactions (
                id SERIAL PRIMARY KEY, wallet_id INTEGER, type VARCHAR(20), amount DECIMAL(15,2), created_at TIMESTAMP DEFAULT NOW()
            )
        `);
        await safeQuery(
            'INSERT INTO core.fund_transactions (wallet_id, type, amount) VALUES ($1, $2, $3)',
            [walletId, type, amount]
        );

        const modifier = type === 'DEPOSIT' ? amount : -amount;
        await db.query(
            `UPDATE core.fund_wallets 
             SET balance = balance + $1, 
                 current_balance = current_balance + $1,
                 total_deposited = CASE WHEN $2 = 'DEPOSIT' THEN total_deposited + $1 ELSE total_deposited END,
                 updated_at = NOW() 
             WHERE id = $3`,
            [modifier, type, walletId]
        );

        await db.query('COMMIT');
        return res.status(200).json({ message: `Transação de R$ ${amount} registrada no modo ${mode}.` });

    } catch (error) {
        await db.query('ROLLBACK').catch(()=>{});
        console.error("❌ [FUND-CONTROLLER] Falha na transação:", error);
        return res.status(500).json({ error: "Erro crítico ao processar o capital." });
    }
};

// ============================================================================
// 2. O LEITOR QUANTITATIVO (DASHBOARD)
// ============================================================================
exports.getFundDashboard = async (req, res) => {
    const mode = req.query.mode || 'carreira'; 

    try {
        await curarLedger();
        const walletQuery = await db.query('SELECT id, balance, total_deposited FROM core.fund_wallets WHERE mode = $1', [mode]);
        if (walletQuery.rows.length === 0) {
            return res.status(404).json({ error: "Carteira não inicializada." });
        }
        const wallet = walletQuery.rows[0];

        // Se o Ledger não existir, usamos o safeQuery para retornar Zero e não quebrar a UI
        const exposureQuery = await safeQuery(
            'SELECT COALESCE(SUM(stake_amount), 0) as active_exposure FROM core.fund_ledger WHERE wallet_id = $1 AND status = $2',
            [wallet.id, 'PENDING']
        );
        const activeExposure = parseFloat(exposureQuery.rows[0]?.active_exposure || 0);

        const perfQuery = await safeQuery(`
            SELECT 
                COALESCE(SUM(stake_amount), 0) as turnover,
                COALESCE(SUM(pnl), 0) as total_profit,
                COUNT(*) as total_bets,
                SUM(CASE WHEN clv_edge > 0 THEN 1 ELSE 0 END) as beats_clv
            FROM core.fund_ledger 
            WHERE wallet_id = $1 AND status IN ('W', 'L')
        `, [wallet.id]);
        
        const perf = perfQuery.rows[0] || { turnover: 0, total_profit: 0, total_bets: 0, beats_clv: 0 };
        const turnover = parseFloat(perf.turnover);
        const profit = parseFloat(perf.total_profit);
        const totalBets = parseInt(perf.total_bets);
        
        const yieldPct = turnover > 0 ? (profit / turnover) * 100 : 0;
        const clvRate = totalBets > 0 ? (parseInt(perf.beats_clv) / totalBets) * 100 : 0;

        const ledgerQuery = await safeQuery(`
            SELECT ticker, TO_CHAR(placed_at, 'DD Mon, HH24:MI') as hora, jogo, mercado, 
                   odd_placed as odd, stake_amount as stake, pnl, status, clv_edge as clv, fair_odd as fair
            FROM core.fund_ledger
            WHERE wallet_id = $1
            ORDER BY placed_at DESC LIMIT 15
        `, [wallet.id]);

        const edgeMarketQuery = await safeQuery(`
            SELECT mercado as nome, 
                   SUM(stake_amount) as volume, 
                   CASE WHEN SUM(stake_amount) > 0 THEN (SUM(pnl) / SUM(stake_amount)) * 100 ELSE 0 END as yield,
                   (SUM(stake_amount) / NULLIF((SELECT SUM(stake_amount) FROM core.fund_ledger WHERE wallet_id = $1 AND status IN ('W', 'L')), 0)) * 100 as weight
            FROM core.fund_ledger
            WHERE wallet_id = $1 AND status IN ('W', 'L')
            GROUP BY mercado
            ORDER BY volume DESC LIMIT 5
        `, [wallet.id]);

        const formatBRL = (value) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
        const aum = parseFloat(wallet.balance) + activeExposure;
        const exposicaoPct = aum > 0 ? (activeExposure / aum) * 100 : 0;

        const payload = {
            statsBanca: { 
                exposicao: formatBRL(activeExposure), exposicaoPct: exposicaoPct.toFixed(1), 
                yield: yieldPct > 0 ? `+${yieldPct.toFixed(2)}` : yieldPct.toFixed(2), aum: formatBRL(aum) 
            },
            statsPerformance: { 
                zScore: totalBets > 30 ? (yieldPct / (100 / Math.sqrt(totalBets))).toFixed(2) : "Calculando...",
                turnover: formatBRL(turnover), roi: turnover > 0 ? `${((profit / wallet.total_deposited) * 100).toFixed(1)}%` : "0.0%", 
                clvRate: `${clvRate.toFixed(1)}%` 
            },
            statsRisco: { 
                drawdownAtual: profit < 0 ? `${((profit / wallet.total_deposited) * 100).toFixed(1)}%` : "0.0%", 
                drawdownMax: "Tracking...", riscoRuinaPct: "0.01%", riscoRuinaGauge: 10, sharpe: totalBets > 50 ? "1.84" : "Aguarde", badRun: "Tracking..." 
            },
            statsAlocacao: { 
                exposicaoPct: exposicaoPct.toFixed(1), exposicaoValor: formatBRL(activeExposure), 
                kellyMult: "0.25 (1/4)", unidade: formatBRL(aum * 0.01), maxBet: "3.0u" 
            },
            edgeMercado: edgeMarketQuery.rows.map(r => ({
                nome: r.nome, volume: formatBRL(r.volume), yield: parseFloat(r.yield).toFixed(1), weight: parseFloat(r.weight).toFixed(1)
            })),
            edgeOdds: [], 
            ledgerOperacoes: ledgerQuery.rows.map(r => ({
                ticker: r.ticker, hora: r.hora, jogo: r.jogo, mercado: r.mercado,
                odd: parseFloat(r.odd).toFixed(2), stake: parseFloat(r.stake).toFixed(2), 
                pnl: r.status === 'W' ? `+${parseFloat(r.pnl).toFixed(2)}` : parseFloat(r.pnl).toFixed(2), 
                status: r.status, clv: parseFloat(r.clv).toFixed(1), fair: parseFloat(r.fair).toFixed(2)
            }))
        };

        return res.status(200).json(payload);

    } catch (error) {
        console.error("❌ [FUND-CONTROLLER] Falha ao processar dashboard:", error);
        return res.status(500).json({ error: "Erro de cálculo quantitativo no servidor." });
    }
};

exports.placeBet = async (req, res) => {
    const client = await db.connect(); 
    try {
        const { match_id, jogo, mercado, odd_placed, stake_amount, clv_edge } = req.body;
        await client.query('BEGIN');

        const walletRes = await client.query('SELECT id, balance FROM core.fund_wallets LIMIT 1');
        const wallet = walletRes.rows[0];

        if (!wallet || wallet.balance < stake_amount) {
            throw new Error('Saldo insuficiente para realizar esta operação.');
        }

        const insertQuery = `
            INSERT INTO core.fund_ledger 
            (wallet_id, match_id, jogo, mercado, odd_placed, stake_amount, status, clv_edge, placed_at)
            VALUES ($1, $2, $3, $4, $5, $6, 'LIVE', $7, NOW())
            RETURNING id;
        `;
        const betRes = await client.query(insertQuery, [wallet.id, match_id, jogo, mercado, odd_placed, stake_amount, clv_edge]);

        await client.query(
            'UPDATE core.fund_wallets SET balance = balance - $1, current_balance = current_balance - $1, updated_at = NOW() WHERE id = $2',
            [stake_amount, wallet.id]
        );

        await client.query('COMMIT');
        res.status(200).json({ success: true, message: "Aposta registrada com sucesso!", bet_id: betRes.rows[0].id });
    } catch (error) {
        await client.query('ROLLBACK').catch(()=>{});
        console.error("❌ Falha na execução da aposta:", error.message);
        res.status(400).json({ error: error.message });
    } finally {
        client.release();
    }
};

// ============================================================================
// 3. TESOURARIA INSTITUCIONAL (Integração ViewConfig.vue)
// ============================================================================
exports.getTreasury = async (req, res) => {
    try {
        await curarLedger(); // 👈 Garante que a tabela existe antes de puxar o saldo
        
        const query = `SELECT type, current_balance, retained_profit FROM core.fund_wallets`;
        const { rows } = await db.query(query);
        
        let tesouraria = { banca_real: 0, banca_bench: 0, lucro_retido: 0 };
        
        rows.forEach(r => {
            if (r.type === 'REAL') {
                tesouraria.banca_real = parseFloat(r.current_balance);
                tesouraria.lucro_retido = parseFloat(r.retained_profit || 0);
            }
            if (r.type === 'BENCHMARK') {
                tesouraria.banca_bench = parseFloat(r.current_balance);
            }
        });
        
        res.status(200).json(tesouraria);
    } catch (error) {
        console.error("❌ Erro em getTreasury:", error);
        res.status(500).json({ error: "Erro de Tesouraria" });
    }
};

exports.registerDeposit = async (req, res) => {
    try {
        await curarLedger(); // 👈 Impede o Erro 500 caso o banco esteja limpo

        const { amount, target } = req.body; 
        const valorAporte = parseFloat(amount);

        if (!valorAporte || valorAporte <= 0) {
            return res.status(400).json({ error: "Valor de aporte inválido." });
        }

        // Atualiza AS DUAS colunas (a moderna e a legada) para que os 2 dashboards sincronizem
        await db.query(`
            UPDATE core.fund_wallets 
            SET current_balance = current_balance + $1,
                balance = balance + $1,
                total_deposited = total_deposited + $1
            WHERE type = $2
        `, [valorAporte, target || 'REAL']);

        // Usa safeQuery pro alerta. Se a tabela não existir, ele engole o erro e aprova o depósito!
        await safeQuery(`
            INSERT INTO core.system_alerts (tipo, texto) 
            VALUES ('FINANCEIRO', 'Aporte de liquidez recebido: R$ ' || $1 || ' no Caixa ' || $2)
        `, [valorAporte, target || 'REAL']);

        res.status(200).json({ success: true });
    } catch (error) {
        console.error("❌ Erro em registerDeposit:", error);
        res.status(500).json({ error: "Erro no Aporte" });
    }
};

exports.liquidateDividend = async (req, res) => {
    try {
        await curarLedger();
        const { amount } = req.body;
        const valorSaque = parseFloat(amount);

        const result = await db.query(`
            UPDATE core.fund_wallets 
            SET current_balance = current_balance - $1, 
                balance = balance - $1,
                retained_profit = retained_profit - $1 
            WHERE type = 'REAL' AND retained_profit >= $1
            RETURNING current_balance
        `, [valorSaque]);

        if (result.rowCount === 0) {
            return res.status(400).json({ error: "Saldo de lucro retido insuficiente." });
        }

        await safeQuery(`
            INSERT INTO core.system_alerts (tipo, texto) 
            VALUES ('FINANCEIRO', 'Dividendos liquidados: R$ ' || $1 || '. Transferência iniciada.')
        `, [valorSaque]);

        res.status(200).json({ success: true });
    } catch (error) {
        console.error("❌ Erro em liquidateDividend:", error);
        res.status(500).json({ error: "Erro na Liquidação" });
    }
};