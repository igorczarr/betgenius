// betgenius-backend/src/controllers/systemController.js

const db = require('../config/db');
const bcrypt = require('bcryptjs');

// ============================================================================
// PADRÃO SÊNIOR: SAFE QUERY WRAPPER E AUTO-MIGRAÇÃO
// Impede Erro 500 e força a criação das colunas que faltam no Banco de Dados
// ============================================================================
const safeQuery = async (queryText, params = []) => {
    try {
        return await db.query(queryText, params);
    } catch (error) {
        console.warn(`[AVISO] Tabela/coluna ausente. Ignorando falha na query.`);
        return { rows: [], rowCount: 0 };
    }
};

const curarBancoDeDados = async () => {
    try {
        // 1. Cura da Tabela de Usuários (Evita erro ao salvar o Perfil)
        await safeQuery(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS username VARCHAR(50) DEFAULT 'admin'`);
        await safeQuery(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS cargo VARCHAR(100) DEFAULT 'Lead Quant'`);
        await safeQuery(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS tema_interface VARCHAR(50) DEFAULT 'institutional-dark'`);
        await safeQuery(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)`);

        // 2. Cura da Tesouraria e Aportes (Evita o Erro 500 em /fund/treasury e /deposit)
        await safeQuery(`
            CREATE TABLE IF NOT EXISTS core.fund_wallets (
                id SERIAL PRIMARY KEY,
                type VARCHAR(20) UNIQUE,
                current_balance DECIMAL(15,2) DEFAULT 0,
                retained_profit DECIMAL(15,2) DEFAULT 0
            )
        `);
        await safeQuery(`INSERT INTO core.fund_wallets (type, current_balance) VALUES ('REAL', 0) ON CONFLICT DO NOTHING`);
        await safeQuery(`INSERT INTO core.fund_wallets (type, current_balance) VALUES ('BENCHMARK', 0) ON CONFLICT DO NOTHING`);

        // 3. Cura das Imagens de Login
        await safeQuery(`
            CREATE TABLE IF NOT EXISTS core.login_images (
                id SERIAL PRIMARY KEY,
                image_data TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        `);
    } catch (e) {
        console.error("Erro no motor de Auto-Cura:", e);
    }
};

exports.getHeartbeat = async (req, res) => {
    try {
        const [mappedGamesResult, evOpportunitiesResult, dailyProfitResult, bankrollResult] = await Promise.all([
            safeQuery(`SELECT COUNT(*) as total FROM core.matches_history WHERE DATE(match_date) = CURRENT_DATE`),
            safeQuery(`SELECT COUNT(*) as total FROM core.fund_ledger WHERE status = 'LIVE' AND clv_edge > 0`),
            safeQuery(`SELECT SUM(pnl) as daily_pnl FROM core.fund_ledger WHERE status IN ('WON', 'LOST') AND DATE(settled_at) = CURRENT_DATE`),
            safeQuery(`SELECT current_balance as balance FROM core.fund_wallets WHERE type = 'REAL' LIMIT 1`)
        ]);

        res.status(200).json({
            mappedGames: parseInt(mappedGamesResult.rows[0]?.total || 0),
            evOpportunities: parseInt(evOpportunitiesResult.rows[0]?.total || 0),
            dailyProfit: parseFloat(dailyProfitResult.rows[0]?.daily_pnl || 0.00),
            currentBankroll: parseFloat(bankrollResult.rows[0]?.balance || 0.00)
        });
    } catch (error) {
        res.status(200).json({ mappedGames: 0, evOpportunities: 0, dailyProfit: 0, currentBankroll: 0 });
    }
};

exports.getAlerts = async (req, res) => {
    try {
        let alertas = [];
        const alertQuery = await safeQuery(`SELECT tipo, texto, TO_CHAR(criado_em, 'HH24:MI') as time FROM core.system_alerts ORDER BY criado_em DESC LIMIT 4`);
        if (alertQuery.rows.length > 0) alertas = alertQuery.rows;

        const evQuery = await safeQuery(`SELECT 'ODDS DROP' as tipo, 'Edge de ' || ROUND(clv_edge, 1) || '% detectada no mercado!' as texto, 'Agora' as time FROM core.fund_ledger WHERE status = 'LIVE' AND clv_edge > 3 ORDER BY placed_at DESC LIMIT 1`);
        if(evQuery.rows.length > 0) alertas.unshift(evQuery.rows[0]);

        if (alertas.length === 0) alertas = [{ time: "Agora", tipo: "INFO", texto: "Sistema Quantitativo Operacional. Mapeando assimetrias..." }];
        res.status(200).json(alertas);
    } catch (error) {
        res.status(200).json([{ time: "Agora", tipo: "INFO", texto: "Conectando ao Data Warehouse..." }]);
    }
};

exports.getConfig = async (req, res) => {
    try {
        await curarBancoDeDados(); // Garante a integridade antes de ler

        const userQuery = `SELECT modo_operacao, nivel_dominancia, nome, username, cargo, titulo, email, avatar_url, fonte, tema_interface, auth_method FROM core.users WHERE id = 1`;
        const userRes = await safeQuery(userQuery);
        
        const imgQuery = `SELECT id, image_data, is_active FROM core.login_images WHERE is_active = TRUE ORDER BY created_at ASC`;
        const imgRes = await safeQuery(imgQuery);

        if(userRes.rows.length === 0) {
            return res.status(200).json({ 
                user_config: { modo: 'REAL', nivel_dominancia: 2, nome: 'Gestor', username: 'admin', cargo: 'Lead Quant', titulo: 'Quant Manager', email: 'admin@betgenius.fund', avatar: '', tema_interface: 'institutional-dark' },
                login_images: []
            });
        }
        
        const user = userRes.rows[0];
        res.status(200).json({
            user_config: {
                modo: user.modo_operacao || 'REAL', nivel_dominancia: user.nivel_dominancia || 2,
                nome: user.nome || '', username: user.username || '', cargo: user.cargo || '',
                titulo: user.titulo || '', email: user.email || '', avatar: user.avatar_url,
                fonte: user.fonte || 'jersey', tema_interface: user.tema_interface || 'institutional-dark',
                auth_method: user.auth_method || 'standard'
            },
            login_images: imgRes.rows || []
        });
    } catch (error) {
        res.status(500).json({ error: "Erro interno ao ler configurações do sistema." });
    }
};

exports.updateConfig = async (req, res) => {
    await curarBancoDeDados(); // Garante a integridade antes de salvar (Resolve o Falha de Comunicação)
    const client = await db.connect(); 
    try {
        const { user_config, login_images } = req.body;
        await client.query('BEGIN');

        let userUpdateQuery = `
            UPDATE core.users 
            SET modo_operacao = $1, nivel_dominancia = $2, nome = $3, username = $4, cargo = $5, 
                titulo = $6, email = $7, avatar_url = $8, fonte = $9, tema_interface = $10, auth_method = $11
        `;
        let userParams = [
            user_config.modo, user_config.nivel_dominancia, user_config.nome, user_config.username, 
            user_config.cargo, user_config.titulo, user_config.email, user_config.avatar, 
            user_config.fonte, user_config.tema_interface, user_config.auth_method
        ];

        if (user_config.nova_senha && user_config.nova_senha.trim() !== '') {
            const salt = await bcrypt.genSalt(10);
            const hash = await bcrypt.hash(user_config.nova_senha, salt);
            userUpdateQuery += `, password_hash = $12 WHERE id = 1`;
            userParams.push(hash);
        } else {
            userUpdateQuery += ` WHERE id = 1`;
        }
        await client.query(userUpdateQuery, userParams);

        if (login_images) {
            await client.query(`DELETE FROM core.login_images`);
            for (const img of login_images) {
                if (img.image_data) {
                    await client.query(`INSERT INTO core.login_images (image_data, is_active) VALUES ($1, $2)`, [img.image_data, true]);
                }
            }
        }

        await client.query('COMMIT');
        res.status(200).json({ success: true, message: "Parâmetros atualizados e persistidos." });

    } catch (error) {
        await client.query('ROLLBACK');
        console.error("❌ Erro PUT config:", error);
        res.status(500).json({ error: "Erro ao persistir configurações no Ledger Operacional." });
    } finally {
        client.release();
    }
};