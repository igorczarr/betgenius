// betgenius-backend/src/controllers/matchController.js
const db = require('../config/db');

exports.getMatchCenterData = async (req, res) => {
    const matchId = req.params.id;

    try {
        console.log(`📊 [MATCH-CONTROLLER] Extraindo dados para a Partida ID: ${matchId}`);

        // O Super-SELECT: Puxa dados da partida, da Matriz Alpha e Temporais
        const query = `
            SELECT 
                m.home_team_id, m.away_team_id, m.match_date, m.sport_key,
                m.closing_odd_home, m.closing_odd_draw, m.closing_odd_away,
                a.home_elo_before, a.away_elo_before,
                a.home_xg_for_ewma_micro, a.away_xg_for_ewma_micro,
                a.home_xg_against_ewma_micro, a.away_xg_against_ewma_micro,
                a.home_tension_index, a.away_tension_index,
                a.home_aggression_ewma, a.away_aggression_ewma,
                a.home_market_respect, a.away_market_respect
            FROM core.matches_history m
            LEFT JOIN core.alpha_matrix a ON m.id = a.match_id
            WHERE m.id = $1
        `;
        
        const { rows } = await db.query(query, [matchId]);

        if (rows.length === 0) {
            return res.status(404).json({ error: "Partida não encontrada no Data Warehouse." });
        }

        const data = rows[0];

        // Hack S-Tier de Identidade Visual: Gerar cores dinâmicas baseadas no nome para manter o visual rico
        const getTeamColor = (id, isHome) => isHome ? '#10B981' : '#3B82F6'; 

        // Montagem do Payload Exato que o Vue.js (ViewMatchCenter.vue) espera
        const payload = {
            partida: {
                // Para produção, aqui faríamos um JOIN com a tabela de times para pegar o nome real.
                // Por ora, mapeamos os IDs ou strings curtas que temos.
                casa: `Team ${data.home_team_id}`, 
                fora: `Team ${data.away_team_id}`,
                posCasa: Math.ceil(Math.random() * 10), // Mock visual
                posFora: Math.ceil(Math.random() * 10),
                corCasa: getTeamColor(data.home_team_id, true),
                corFora: getTeamColor(data.away_team_id, false),
                placarCasa: "-", placarFora: "-",
                
                // Os dados de xG REAIS extraídos da nossa Matriz Alpha
                xgCasa: data.home_xg_for_ewma_micro ? Number(data.home_xg_for_ewma_micro).toFixed(2) : "0.00",
                xgFora: data.away_xg_for_ewma_micro ? Number(data.away_xg_for_ewma_micro).toFixed(2) : "0.00",
                
                isLive: false, 
                tempo: 0, 
                hora: new Date(data.match_date).toLocaleTimeString('pt-BR', {hour: '2-digit', minute:'2-digit'}),
                
                formCasa: ['W', 'D', 'W', 'W', 'L'], // Simularemos isso na próxima etapa do Crawler
                formFora: ['L', 'W', 'D', 'L', 'L'],
                
                historico: [], 
                
                // FBref Real (Traduzido da Alpha Matrix)
                fbrefOfensivas: [
                    { nome: "xG (Expected Goals)", casa: Number(data.home_xg_for_ewma_micro || 0).toFixed(2), fora: Number(data.away_xg_for_ewma_micro || 0).toFixed(2), sufixo: "", desc: "Qualidade das chances criadas (Últimos 5J)" },
                    { nome: "Market Respect", casa: Number(data.home_market_respect * 100 || 0).toFixed(1), fora: Number(data.away_market_respect * 100 || 0).toFixed(1), sufixo: "%", desc: "Respeito do Dinheiro Inteligente (Pinnacle)" }
                ],
                fbrefDefensivas: [
                    { nome: "xGA (xG Sofrido)", casa: Number(data.home_xg_against_ewma_micro || 0).toFixed(2), fora: Number(data.away_xg_against_ewma_micro || 0).toFixed(2), sufixo: "", desc: "Fragilidade defensiva recente" },
                    { nome: "Agressividade", casa: Number(data.home_aggression_ewma || 0).toFixed(1), fora: Number(data.away_aggression_ewma || 0).toFixed(1), sufixo: "", desc: "Índice de Faltas e Cartões" }
                ],
                fbrefAvancadas: [
                    { nome: "Elo Rating", casa: Math.round(data.home_elo_before || 1500), fora: Math.round(data.away_elo_before || 1500), sufixo: "", desc: "Poder Histórico Global" },
                    { nome: "Tension Index", casa: Number(data.home_tension_index * 100 || 0).toFixed(0), fora: Number(data.away_tension_index * 100 || 0).toFixed(0), sufixo: "%", desc: "Desespero vs Férias (Classificação)" }
                ],
                fbrefVariadas: [],
                gameState: [],
                
                // Mercados (Lendo as Closing Odds reais do banco)
                mercados: [
                    { nome: "Mandante (1X2)", categoria: "match_odds", prob: "-", fair: "-", bookie: Number(data.closing_odd_home).toFixed(2), openOdd: "-", ev: "0.0", casaNome: "Pinnacle" },
                    { nome: "Visitante (1X2)", categoria: "match_odds", prob: "-", fair: "-", bookie: Number(data.closing_odd_away).toFixed(2), openOdd: "-", ev: "0.0", casaNome: "Pinnacle" },
                ]
            },
            playerProps: { chutes: [], gols: [], assists: [], faltas: [] }
        };

        return res.status(200).json(payload);

    } catch (error) {
        console.error("❌ [MATCH-CONTROLLER] Falha na montagem de dados:", error);
        return res.status(500).json({ error: "Falha na leitura S-Tier do Banco de Dados." });
    }
};

// (Mantenha os outros métodos que você já tinha, como getMatchCenterData)

exports.getTodayMatches = async (req, res) => {
    try {
        // Buscamos apenas os jogos onde a data bate com o dia atual.
        // O JOIN garante que traremos o nome "Arsenal" e não o ID "85"
        const query = `
            SELECT 
                m.id,
                m.sport_key as campeonato,
                m.match_date as data,
                th.canonical_name as casa,
                ta.canonical_name as fora
            FROM core.matches_history m
            JOIN core.teams th ON m.home_team_id = th.id
            JOIN core.teams ta ON m.away_team_id = ta.id
            WHERE DATE(m.match_date) = CURRENT_DATE
            ORDER BY m.match_date ASC;
        `;
        
        const { rows } = await pool.query(query);

        res.status(200).json(rows);
    } catch (error) {
        console.error("❌ Erro ao buscar jogos do dia:", error);
        res.status(500).json({ error: "Falha ao extrair o cronograma do Data Warehouse." });
    }
};

// Utilitário Matemático: Converte Probabilidade em Odd Justa (Fair Odd)
const getFairOdd = (probabilidadePercentual) => {
    if (probabilidadePercentual <= 0) return 0;
    return (100 / probabilidadePercentual).toFixed(2);
};

// Simulador de Precificação Quantitativa (Gera os mercados derivados)
const generateMarkets = (homeWinProb, drawProb, awayWinProb, expectedGoalsTotal) => {
    const mercados = [];
    const bookieMargin = 0.05; // 5% de margem da casa de aposta simulada (Juice)

    const addMarket = (categoria, nome, iaProb, bookieOddAjuste = 0) => {
        const fairOdd = parseFloat(getFairOdd(iaProb));
        // Simulamos a odd que a Pinnacle/Bet365 estaria oferecendo (ligeiramente desajustada para gerar EV)
        // Em produção, isso viria da sua tabela de odds em tempo real
        const bookieOdd = parseFloat((fairOdd * (1 - bookieMargin) + bookieOddAjuste).toFixed(2));
        const ev = (((iaProb / 100) * bookieOdd) - 1) * 100;

        mercados.push({
            categoria,
            nome,
            prob: iaProb.toFixed(1),
            fair: fairOdd.toFixed(2),
            openOdd: (bookieOdd * 0.95).toFixed(2), // Odd de abertura simulada
            bookie: bookieOdd.toFixed(2),
            ev: ev.toFixed(1),
            casaNome: 'Pinnacle' // Fonte da Odd
        });
    };

    // 1. Match Odds (1X2)
    addMarket('match_odds', 'Casa Vence (1)', homeWinProb, 0.15);
    addMarket('match_odds', 'Empate (X)', drawProb, -0.10);
    addMarket('match_odds', 'Visitante Vence (2)', awayWinProb, 0.05);

    // 2. Draw No Bet (Empate Anula)
    const dnbHomeProb = homeWinProb + (drawProb / 2);
    const dnbAwayProb = awayWinProb + (drawProb / 2);
    addMarket('dnb', 'DNB Casa (AH 0.0)', dnbHomeProb, 0.12);
    addMarket('dnb', 'DNB Visitante (AH 0.0)', dnbAwayProb, -0.05);

    // 3. Gols (Over / Under) - Baseado no xG Total
    // Se o xG esperado é 2.8, a probabilidade do Over 2.5 é alta.
    const over25Prob = expectedGoalsTotal > 2.5 ? 65 : 40; 
    addMarket('goals', 'Over 2.5 Gols', over25Prob, 0.20); // +EV forte
    addMarket('goals', 'Under 2.5 Gols', 100 - over25Prob, -0.15); // -EV
    addMarket('goals', 'Over 1.5 Gols', over25Prob + 20, 0.05);

    // 4. BTTS (Ambas Marcam)
    const bttsProb = (homeWinProb > 20 && awayWinProb > 20) ? 58 : 42;
    addMarket('btts', 'BTTS - Sim', bttsProb, 0.18);
    addMarket('btts', 'BTTS - Não', 100 - bttsProb, -0.10);

    // 5. Handicap Asiático (AH)
    addMarket('handicap', 'Casa AH -1.0', homeWinProb * 0.6, 0.25);
    addMarket('handicap', 'Visitante AH +1.0', 100 - (homeWinProb * 0.6), -0.05);

    // 6. Escanteios (Corners) - Derivado de pressão ofensiva
    addMarket('corners', 'Over 9.5 Escanteios', 52.5, 0.10);
    addMarket('corners', 'Casa Mais Escanteios', homeWinProb + 5, 0.15);

    // 7. Cartões (Cards)
    addMarket('cards', 'Over 4.5 Cartões', 60.0, 0.08);

    return mercados.sort((a, b) => b.ev - a.ev); // Ordena do maior +EV para o menor
};

exports.getMatchCenterData = async (req, res) => {
    try {
        const { id } = req.params;

        // 1. Busca os dados reais do Data Lake
        const matchQuery = `
            SELECT 
                m.id, m.match_date, m.status, m.current_minute,
                m.home_goals, m.away_goals, m.xg_home, m.xg_away,
                th.canonical_name as casa, ta.canonical_name as fora,
                th.color_primary as cor_casa, ta.color_primary as cor_fora,
                fs.target_home_win, fs.target_draw, fs.target_away_win
            FROM core.matches_history m
            JOIN core.teams th ON m.home_team_id = th.id
            JOIN core.teams ta ON m.away_team_id = ta.id
            LEFT JOIN quant_ml.feature_store fs ON m.id::varchar = fs.match_id
            WHERE m.id = $1
        `;
        const { rows } = await pool.query(matchQuery, [id]);

        if (rows.length === 0) {
            return res.status(404).json({ error: "Partida não encontrada." });
        }

        const match = rows[0];

        // Se o modelo ML ainda não rodou para esse jogo, usamos probabilidades base seguras
        const probHome = match.target_home_win ? 55 : 45;
        const probDraw = match.target_draw ? 25 : 25;
        const probAway = match.target_away_win ? 20 : 30;
        const expectedGoals = parseFloat(match.xg_home || 1.5) + parseFloat(match.xg_away || 1.0);

        // 2. Gera a Árvore Completa de Mercados +EV
        const mercadosComplexos = generateMarkets(probHome, probDraw, probAway, expectedGoals);

        // 3. Formata os Player Props (Player Props geralmente vêm de uma API terceira ou scraper próprio)
        const playerProps = {
            chutes: [
                { nome: "Haaland", time: match.casa, prob: 78, war: 0.45, fair: "1.28" },
                { nome: "Saka", time: match.fora, prob: 62, war: 0.31, fair: "1.61" }
            ],
            gols: [
                { nome: "Haaland", time: match.casa, prob: 52, war: 0.55, fair: "1.92" }
            ],
            escanteios: [ // Props de time
                { nome: "Casa Total Corners Over 5.5", time: match.casa, prob: 58, war: 0.12, fair: "1.72" }
            ],
            cartoes: [
                { nome: "Rodri", time: match.fora, prob: 25, war: -0.05, fair: "4.00" }
            ]
        };

        // 4. Constrói o objeto 'partida' que o Vue.js espera
        const responseData = {
            partida: {
                id: match.id,
                casa: match.casa,
                fora: match.fora,
                corCasa: match.cor_casa || "#3B82F6",
                corFora: match.cor_fora || "#EF4444",
                placarCasa: match.home_goals ?? 0,
                placarFora: match.away_goals ?? 0,
                xgCasa: parseFloat(match.xg_home || 0).toFixed(2),
                xgFora: parseFloat(match.xg_away || 0).toFixed(2),
                isLive: match.status === 'LIVE',
                tempo: match.current_minute || 0,
                hora: new Date(match.match_date).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
                mercados: mercadosComplexos,
                
                // Mocks visuais para as abas secundárias que não afetam as apostas (H2H, Clima)
                posCasa: 2, posFora: 5,
                formCasa: ['W','W','D','W','L'], formFora: ['L','D','W','W','W'],
                arbitro: "Michael Oliver", arb_amarelos: "4.2", arb_vermelhos: "0.15", clima: "Limpo", temp: "18",
                historico: [], indFormCasa: [], indFormFora: [],
                gameState: [], fbrefAvancadas: []
            },
            playerProps
        };

        res.status(200).json(responseData);
    } catch (error) {
        console.error("❌ Erro no Match Center:", error);
        res.status(500).json({ error: "Falha ao carregar Raio-X do jogo." });
    }
};