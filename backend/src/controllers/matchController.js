// backend/src/controllers/matchController.js
const db = require('../config/db');

exports.getMatchCenterData = async (req, res) => {
    const matchId = req.params.id;

    try {
        console.log(`📊 [MATCH-CONTROLLER] Extraindo dados REAIS para a Partida ID: ${matchId}`);

        // 1. O Super-SELECT: Puxa dados da partida, nomes reais e a Matriz Alpha
        const matchQuery = `
            SELECT 
                m.id, m.match_date, m.status, m.current_minute,
                m.home_goals, m.away_goals, 
                th.canonical_name as casa, ta.canonical_name as fora,
                th.color_primary as cor_casa, ta.color_primary as cor_fora,
                a.home_elo_before, a.away_elo_before,
                a.home_xg_for_ewma_micro as xg_home, a.away_xg_for_ewma_micro as xg_away,
                a.home_xg_against_ewma_micro as xga_home, a.away_xg_against_ewma_micro as xga_away,
                a.home_tension_index, a.away_tension_index,
                a.home_aggression_ewma, a.away_aggression_ewma,
                a.home_market_respect, a.away_market_respect
            FROM core.matches_history m
            JOIN core.teams th ON m.home_team_id = th.id
            JOIN core.teams ta ON m.away_team_id = ta.id
            LEFT JOIN core.alpha_matrix a ON m.id = a.match_id
            WHERE m.id = $1
        `;
        
        const { rows: matchRows } = await db.query(matchQuery, [matchId]);

        if (matchRows.length === 0) {
            return res.status(404).json({ error: "Partida não encontrada no Data Warehouse." });
        }

        const data = matchRows[0];

        // 2. Busca Mercados e Odds REAIS do Banco
        const oddsQuery = `SELECT * FROM core.market_odds WHERE match_id = $1 ORDER BY ev_pct DESC`;
        const { rows: oddsRows } = await db.query(oddsQuery, [matchId]);
        
        const mercados = oddsRows.map(odd => ({
            categoria: odd.categoria,
            nome: odd.nome_mercado,
            prob: odd.probabilidade_ia ? Number(odd.probabilidade_ia).toFixed(1) : "-",
            fair: odd.fair_odd ? Number(odd.fair_odd).toFixed(2) : "-",
            openOdd: odd.open_odd ? Number(odd.open_odd).toFixed(2) : "-",
            bookie: Number(odd.current_odd).toFixed(2),
            ev: odd.ev_pct ? Number(odd.ev_pct).toFixed(1) : "0.0",
            casaNome: odd.bookmaker
        }));

        // 3. Busca Player Props REAIS do Banco
        const propsQuery = `SELECT * FROM core.player_props WHERE match_id = $1`;
        const { rows: propsRows } = await db.query(propsQuery, [matchId]);
        
        const playerProps = { chutes: [], gols: [], escanteios: [], cartoes: [] };
        propsRows.forEach(p => {
            const propObj = { 
                nome: p.jogador_nome, time: p.equipe, linha: p.linha,
                prob: p.probabilidade_ia, war: p.win_above_replacement, 
                fair: p.fair_odd, odd: p.bookie_odd 
            };
            if (p.categoria === 'chutes') playerProps.chutes.push(propObj);
            else if (p.categoria === 'gols') playerProps.gols.push(propObj);
            else if (p.categoria === 'escanteios') playerProps.escanteios.push(propObj);
            else if (p.categoria === 'cartoes') playerProps.cartoes.push(propObj);
        });

        // 4. Montagem do Payload Exato que o Vue.js (ViewMatchCenter.vue) espera
        const payload = {
            partida: {
                id: data.id,
                casa: data.casa,
                fora: data.fora,
                posCasa: "-", posFora: "-", // Preenchimento futuro via API externa
                corCasa: data.cor_casa || '#10B981',
                corFora: data.cor_fora || '#3B82F6',
                placarCasa: data.home_goals ?? "-",
                placarFora: data.away_goals ?? "-",
                xgCasa: data.xg_home ? Number(data.xg_home).toFixed(2) : "0.00",
                xgFora: data.xg_away ? Number(data.xg_away).toFixed(2) : "0.00",
                isLive: data.status === 'LIVE',
                tempo: data.current_minute || 0,
                hora: new Date(data.match_date).toLocaleTimeString('pt-BR', {hour: '2-digit', minute:'2-digit'}),
                formCasa: [], formFora: [], historico: [],
                
                fbrefOfensivas: [
                    { nome: "xG (Expected Goals)", casa: Number(data.xg_home || 0).toFixed(2), fora: Number(data.xg_away || 0).toFixed(2), sufixo: "", desc: "Qualidade das chances" },
                    { nome: "Market Respect", casa: Number((data.home_market_respect || 0) * 100).toFixed(1), fora: Number((data.away_market_respect || 0) * 100).toFixed(1), sufixo: "%", desc: "Volume Sharp Pinnacle" }
                ],
                fbrefDefensivas: [
                    { nome: "xGA (xG Sofrido)", casa: Number(data.xga_home || 0).toFixed(2), fora: Number(data.xga_away || 0).toFixed(2), sufixo: "", desc: "Fragilidade defensiva" },
                    { nome: "Agressividade", casa: Number(data.home_aggression_ewma || 0).toFixed(1), fora: Number(data.away_aggression_ewma || 0).toFixed(1), sufixo: "", desc: "Índice de Faltas e Cartões" }
                ],
                fbrefAvancadas: [
                    { nome: "Elo Rating", casa: Math.round(data.home_elo_before || 1500), fora: Math.round(data.away_elo_before || 1500), sufixo: "", desc: "Poder Histórico Global" },
                    { nome: "Tension Index", casa: Number((data.home_tension_index || 0) * 100).toFixed(0), fora: Number((data.away_tension_index || 0) * 100).toFixed(0), sufixo: "%", desc: "Desespero vs Férias" }
                ],
                fbrefVariadas: [], gameState: [],
                mercados: mercados
            },
            playerProps
        };

        return res.status(200).json(payload);

    } catch (error) {
        console.error("❌ [MATCH-CONTROLLER] Falha na montagem de dados:", error);
        return res.status(500).json({ error: "Falha na leitura S-Tier do Banco de Dados." });
    }
};

exports.getTodayMatches = async (req, res) => {
    try {
        // Buscamos apenas os jogos onde a data bate com o dia atual.
        const query = `
            SELECT 
                m.id,
                m.sport_key as campeonato,
                m.match_date as data,
                th.canonical_name as casa,
                ta.canonical_name as fora,
                m.status
            FROM core.matches_history m
            JOIN core.teams th ON m.home_team_id = th.id
            JOIN core.teams ta ON m.away_team_id = ta.id
            WHERE DATE(m.match_date) = CURRENT_DATE
            ORDER BY m.match_date ASC;
        `;
        
        // FIX: Usando db.query (A variável global definida na linha 2)
        const { rows } = await db.query(query);

        res.status(200).json(rows);
    } catch (error) {
        console.error("❌ Erro ao buscar jogos do dia:", error);
        res.status(500).json({ error: "Falha ao extrair o cronograma do Data Warehouse." });
    }
};