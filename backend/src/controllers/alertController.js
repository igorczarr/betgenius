// betgenius-backend/controllers/alertController.js

const pool = require('../config/db');

exports.getLiveAlerts = async (req, res) => {
    try {
        // Buscamos os alertas de mercado e unimos com os Drops de Odds de Alta Frequência (HFT)
        // Usamos um UNION ALL para combinar as duas fontes de inteligência em uma única timeline
        const query = `
            SELECT 
                id::text as id, 
                alert_type as tipo, 
                team_name as time, 
                message as texto, 
                confidence as confianca, 
                created_at as criado_em
            FROM core.market_alerts
            WHERE created_at >= NOW() - INTERVAL '48 HOURS'

            UNION ALL

            SELECT 
                'hft_' || id::text as id, 
                'ODDS DROP' as tipo, 
                jogo as time, 
                'A linha do mercado ' || mercado || ' (' || selecao || ') despencou ' || drop_pct || '% (De ' || odd_abertura || ' para ' || odd_atual || '). Fonte: ' || fonte as texto,
                95 as confianca,
                captured_at as criado_em
            FROM core.hft_odds_drops
            WHERE captured_at >= NOW() - INTERVAL '48 HOURS'

            ORDER BY criado_em DESC
            LIMIT 15;
        `;

        const { rows } = await pool.query(query);

        res.status(200).json(rows);
    } catch (error) {
        console.error("❌ Erro ao buscar Intel Alerts:", error);
        res.status(500).json({ error: "Falha ao ler o Radar de Alertas." });
    }
};