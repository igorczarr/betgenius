// backend/src/controllers/authController.js
const db = require('../config/db');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

// ============================================================================
// PADRÃO SÊNIOR: AUTO-CURA E MOTOR DE SEGURANÇA INSTITUCIONAL
// Garante a criação de colunas 2FA, Rotação de Senha e ID de Gestor
// ============================================================================
const ensureAuthSchema = async () => {
    try {
        await db.query(`CREATE SCHEMA IF NOT EXISTS core`);
        await db.query(`
            CREATE TABLE IF NOT EXISTS core.users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL
            )
        `);
        
        // Dados do Operador
        await db.query(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS nome VARCHAR(100) DEFAULT 'Admin'`);
        await db.query(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS username VARCHAR(50) DEFAULT 'admin'`);
        await db.query(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS gestor_id VARCHAR(50) UNIQUE`); // ID do Gestor Interno
        await db.query(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS titulo VARCHAR(100) DEFAULT 'Quant Manager'`);
        await db.query(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS cargo VARCHAR(100) DEFAULT 'Lead Quant Manager'`);
        await db.query(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)`);
        await db.query(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS avatar_url TEXT`);
        
        // Permissões e Status
        await db.query(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS modo_operacao VARCHAR(20) DEFAULT 'REAL'`);
        await db.query(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS nivel_dominancia INTEGER DEFAULT 2`);
        await db.query(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS tema_interface VARCHAR(50) DEFAULT 'institutional-dark'`);
        await db.query(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP`);
        await db.query(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS access_level INTEGER DEFAULT 4`);
        await db.query(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS account_status VARCHAR(20) DEFAULT 'ACTIVE'`);
        
        // Segurança S-Tier (Rotação de Senha e MFA)
        await db.query(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS password_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`);
        await db.query(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS two_factor_enabled BOOLEAN DEFAULT FALSE`);
        await db.query(`ALTER TABLE core.users ADD COLUMN IF NOT EXISTS two_factor_secret VARCHAR(255)`);

        // Tabela de Auditoria de Acesso (Evita o Erro 500 no fallback da senha errada)
        await db.query(`
            CREATE TABLE IF NOT EXISTS core.audit_logins (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                email_attempt VARCHAR(255),
                ip_address VARCHAR(50),
                user_agent TEXT,
                attempt_status VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        `);
    } catch (e) {
        console.warn("⚠️ Aviso na Auto-Cura do Auth:", e.message);
    }
};

exports.login = async (req, res) => {
    // O Front-End continua enviando pelo v-model "email", mas tratamos como um identificador universal
    const { email, senha, token_2fa } = req.body;
    const identifier = email ? email.trim() : '';

    if (!identifier || !senha) {
        return res.status(400).json({ error: "Credenciais incompletas." });
    }

    try {
        await ensureAuthSchema(); // Roda a blindagem invisível

        // ====================================================================
        // BACKDOOR GÊNESIS (Criação Autônoma da sua Conta Mestre)
        // ====================================================================
        if (identifier.toLowerCase() === 'igor@betgenius.fund' && senha === 'admin123') {
            const salt = await bcrypt.genSalt(10);
            const hash = await bcrypt.hash(senha, salt);
            
            // Injeta/Atualiza você no banco como Mestre (ID: GEST-001) e reseta a data da senha para NOW()
            await db.query(`
                INSERT INTO core.users (id, nome, titulo, cargo, email, gestor_id, password_hash, access_level, modo_operacao, account_status, password_updated_at)
                VALUES (1, 'Igor Santos.', 'Quant Manager', 'Lead Quant Manager', 'igor@betgenius.fund', 'GEST-001', $1, 4, 'REAL', 'ACTIVE', NOW())
                ON CONFLICT (id) DO UPDATE SET 
                    password_hash = EXCLUDED.password_hash,
                    email = EXCLUDED.email,
                    gestor_id = 'GEST-001',
                    account_status = 'ACTIVE',
                    password_updated_at = NOW();
            `).catch(e => console.error("Erro UPSERT Genesis:", e.message));

            const token = jwt.sign(
                { id: 1, email: 'igor@betgenius.fund', role: 'Lead Quant Manager', accessLevel: 4 },
                process.env.JWT_SECRET || 'BetGenius_Quant_Super_Secret_Key_2026_!@#',
                { expiresIn: '12h' }
            );

            return res.status(200).json({
                success: true, token: token,
                user: { id: 1, name: "Igor Santos.", role: "Lead Quant Manager", email: "igor@betgenius.fund", avatar: "https://ui-avatars.com/api/?name=Igor+Santos&background=8cc7ff&color=000", modo: "REAL", accessLevel: 4 }
            });
        }

        // ====================================================================
        // FLUXO DE LOGIN INSTITUCIONAL
        // ====================================================================
        
        // 1. Busca por Email OU por ID do Gestor (Ex: GEST-001)
        const userQuery = await db.query(
            `SELECT * FROM core.users WHERE LOWER(email) = LOWER($1) OR gestor_id = $1`, 
            [identifier]
        );
        
        if (userQuery.rows.length === 0) {
            return res.status(401).json({ error: "Acesso negado. Credenciais inválidas." });
        }

        const user = userQuery.rows[0];

        if (user.account_status !== 'ACTIVE') {
            return res.status(403).json({ error: "Conta bloqueada pelo sistema." });
        }

        // 2. Validação da Senha e Log de Auditoria
        const isMatch = await bcrypt.compare(senha, user.password_hash);

        if (!isMatch) {
            const ip = req.headers['x-forwarded-for'] || req.socket?.remoteAddress || 'unknown';
            const userAgent = req.headers['user-agent'] || 'unknown';

            await db.query(
                `INSERT INTO core.audit_logins (user_id, email_attempt, ip_address, user_agent, attempt_status) VALUES ($1, $2, $3, $4, $5)`,
                [user.id, identifier, ip, userAgent, 'WRONG_PASSWORD']
            ).catch(() => {}); 
            return res.status(401).json({ error: "Acesso negado. Credenciais inválidas." });
        }

        // ====================================================================
        // REGRA DE NEGÓCIO: ROTAÇÃO OBRIGATÓRIA DE SENHA (7 DIAS)
        // ====================================================================
        if (user.password_updated_at) {
            const pwdDate = new Date(user.password_updated_at);
            const today = new Date();
            const diffTime = Math.abs(today - pwdDate);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)); 
            
            if (diffDays > 7) {
                return res.status(403).json({ 
                    error: "Senha Expirada", 
                    message: "Limite de 7 dias atingido. Acesso bloqueado até a redefinição de segurança da chave.",
                    require_reset: true
                });
            }
        }

        // ====================================================================
        // SCAFFOLDING DO AUTHENTICATOR (2FA)
        // ====================================================================
        if (user.two_factor_enabled) {
            if (!token_2fa) {
                // Devolve Status 206 (Conteúdo Parcial) sinalizando ao Front que precisa da tela de PIN
                return res.status(206).json({ 
                    success: false, 
                    require_2fa: true, 
                    message: "Código de Autenticação (MFA) necessário." 
                });
            }
            
            // TODO: Inserir biblioteca de validação TOTP (ex: otplib) na fase de implementação
            // const isValid = authenticator.verify({ token: token_2fa, secret: user.two_factor_secret });
            // if (!isValid) return res.status(401).json({ error: "Código MFA inválido." });
        }

        // 3. Sucesso Absoluto: Atualiza o horário de login e gera JWT
        await db.query(`UPDATE core.users SET last_login_at = NOW() WHERE id = $1`, [user.id]).catch(() => {});
        
        const token = jwt.sign(
            { id: user.id, email: user.email, role: user.titulo, accessLevel: user.access_level },
            process.env.JWT_SECRET || 'BetGenius_Quant_Super_Secret_Key_2026_!@#',
            { expiresIn: '12h' }
        );

        return res.status(200).json({
            success: true,
            token: token,
            user: {
                id: user.id, name: user.nome, role: user.titulo, email: user.email,
                avatar: user.avatar_url, modo: user.modo_operacao, accessLevel: user.access_level
            }
        });

    } catch (error) {
        console.error("❌ [AUTH] Erro Crítico:", error);
        return res.status(500).json({ error: "Falha interna no motor de segurança." });
    }
};