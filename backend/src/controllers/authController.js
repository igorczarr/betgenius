// backend/src/controllers/authController.js
const db = require('../config/db');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

exports.login = async (req, res) => {
    const { email, senha } = req.body;

    // Normaliza o email para minúsculo
    const normalizedEmail = email ? email.toLowerCase() : '';

    if (!normalizedEmail || !senha) {
        return res.status(400).json({ error: "Credenciais incompletas." });
    }

    try {
        // 👇 BACKDOOR DE ENGENHARIA (Apenas para o dono do sistema entrar agora)
        if (normalizedEmail === 'igor@betgenius.fund' && senha === 'admin123') {
            // Emite o token diretamente sem depender do banco por agora
            const jwt = require('jsonwebtoken');
            const token = jwt.sign(
                { id: 1, email: normalizedEmail, role: 'Lead Quant Manager', accessLevel: 4 },
                process.env.JWT_SECRET || 'BetGenius_Quant_Super_Secret_Key_2026_!@#',
                { expiresIn: '12h' }
            );

            return res.status(200).json({
                success: true,
                token: token,
                user: {
                    id: 1, name: "Igor Santos.", role: "Lead Quant Manager", email: normalizedEmail,
                    avatar: "https://ui-avatars.com/api/?name=Igor+Santos&background=8cc7ff&color=000", 
                    modo: "REAL", accessLevel: 4
                }
            });
        }

        // 1. Busca o usuário recém-garantido no banco
        const userQuery = await db.query(`SELECT * FROM core.users WHERE email = $1`, [email]);
        
        if (userQuery.rows.length === 0) {
            return res.status(401).json({ error: "Acesso negado. Credenciais inválidas." });
        }

        const user = userQuery.rows[0];

        if (user.account_status !== 'ACTIVE') {
            return res.status(403).json({ error: "Conta bloqueada pelo sistema." });
        }

        // 2. Validação da Senha
        const isMatch = await bcrypt.compare(senha, user.password_hash);

        if (!isMatch) {
            // Tenta auditar a falha silenciosamente
            await db.query(
                `INSERT INTO core.audit_logins (user_id, email_attempt, ip_address, user_agent, attempt_status) VALUES ($1, $2, $3, $4, $5)`,
                [user.id, email, ip, userAgent, 'WRONG_PASSWORD']
            ).catch(() => {}); 
            return res.status(401).json({ error: "Acesso negado. Credenciais inválidas." });
        }

        // 3. Sucesso: Atualiza o login e gera o Token JWT
        await db.query(`UPDATE core.users SET last_login_at = NOW() WHERE id = $1`, [user.id]).catch(() => {});
        
        const token = jwt.sign(
            { id: user.id, email: user.email, role: user.titulo, accessLevel: user.access_level },
            process.env.JWT_SECRET || 'BetGenius_Quant_Super_Secret_Key_2026_!@#',
            { expiresIn: '12h' }
        );

        // Retorna para o Vue.js liberar a Placa-Mãe
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