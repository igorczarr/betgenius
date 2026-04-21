// backend/src/controllers/matchCenterController.js
const db = require('../config/db');

/**
 * Funções Auxiliares para transformar dados brutos no formato S-Tier do Vue.js
 */
const calcularForma = (jogos, teamId) => {
    return jogos.map(j => {
        if (j.home_goals === j.away_goals) return 'D';
        if (j.home_team_id === teamId) return j.home_goals > j.away_goals ? 'W' : 'L';
        return j.away_goals > j.home_goals ? 'W' : 'L';
    }).slice(0, 5); // Retorna os últimos 5 [ 'W', 'W', 'D', 'L', 'W' ]
};

const formatarHistorico = (jogosH2H, homeId) => {
    return jogosH2H.map(j => {
        let win = 'empate';
        if (j.home_goals > j.away_goals) win = j.home_team_id === homeId ? 'casa' : 'fora';
        else if (j.away_goals > j.home_goals) win = j.away_team_id === homeId ? 'casa' : 'fora';

        return {
            data: new Date(j.match_date).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' }),
            casa: j.home_name,
            placar: `${j.home_goals} - ${j.away_goals}`,
            fora: j.away_name,
            win: win
        };
    });
};

const formatarPlayerProps = (players, homeName, awayName) => {
    const props = { chutes: [], gols: [], assists: [], faltas: [], cartoes: [] };

    players.forEach(p => {
        const teamName = p.team_id === p.home_team_id ? homeName : awayName;
        // Proxy para WAR (Wins Above Replacement) baseado em xG + Assists
        const impactWar = ((Number(p.xg_per_90) + (Number(p.assists) * 0.1)) / 2).toFixed(2);

        const baseObj = {
            nome: p.player_name,
            time: teamName,
            war: impactWar,
            prob: (Number(p.xg_per_90) * 100).toFixed(0), // Estimativa de probabilidade
            fair: (1 / (Number(p.xg_per_90) || 0.1)).toFixed(2)
        };

        if (Number(p.shots_per_90) > 1.5) props.chutes.push({ ...baseObj, prob: (Number(p.shots_per_90) * 20).toFixed(0) });
        if (Number(p.xg_per_90) > 0.2) props.gols.push(baseObj);
        if (Number(p.assists) > 0) props.assists.push({ ...baseObj, prob: (Number(p.assists) * 10).toFixed(0) });
        if (Number(p.fouls_committed) > 10) props.faltas.push({ ...baseObj, prob: 99 });
    });

    // Ordena os arrays para exibir os mais perigosos no topo
    ['chutes', 'gols', 'assists', 'faltas'].forEach(k => {
        props[k] = props[k].sort((a, b) => b.war - a.war).slice(0, 10);
    });

    return props;
};

exports.getMatchCenter = async (req, res) => {
    try {
        const { matchId } = req.params;

        // 1. DISPARO ASSÍNCRONO PARALELO (S-Tier Performance)
        const [
            matchResult, h2hResult, homeFormResult, awayFormResult, 
            teamStatsResult, playerStatsResult, oddsResult
        ] = await Promise.all([
            // A. Dados base da partida
            db.query(`
                SELECT m.*, th.canonical_name as home_name, ta.canonical_name as away_name 
                FROM core.matches_history m
                JOIN core.teams th ON m.home_team_id = th.id
                JOIN core.teams ta ON m.away_team_id = ta.id
                WHERE m.id = $1
            `, [matchId]),

            // B. Head-to-Head (Últimos 10 jogos entre eles)
            db.query(`
                SELECT m.*, th.canonical_name as home_name, ta.canonical_name as away_name 
                FROM core.matches_history m
                JOIN core.teams th ON m.home_team_id = th.id
                JOIN core.teams ta ON m.away_team_id = ta.id
                WHERE ((m.home_team_id = (SELECT home_team_id FROM core.matches_history WHERE id = $1) AND m.away_team_id = (SELECT away_team_id FROM core.matches_history WHERE id = $1))
                   OR  (m.home_team_id = (SELECT away_team_id FROM core.matches_history WHERE id = $1) AND m.away_team_id = (SELECT home_team_id FROM core.matches_history WHERE id = $1)))
                  AND m.status = 'FINISHED'
                ORDER BY m.match_date DESC LIMIT 10
            `, [matchId]),

            // C. Últimos 5 jogos do Mandante (Overall)
            db.query(`
                SELECT m.* FROM core.matches_history m
                WHERE (m.home_team_id = (SELECT home_team_id FROM core.matches_history WHERE id = $1) OR m.away_team_id = (SELECT home_team_id FROM core.matches_history WHERE id = $1))
                  AND m.status = 'FINISHED' ORDER BY m.match_date DESC LIMIT 5
            `, [matchId]),

            // D. Últimos 5 jogos do Visitante (Overall)
            db.query(`
                SELECT m.* FROM core.matches_history m
                WHERE (m.home_team_id = (SELECT away_team_id FROM core.matches_history WHERE id = $1) OR m.away_team_id = (SELECT away_team_id FROM core.matches_history WHERE id = $1))
                  AND m.status = 'FINISHED' ORDER BY m.match_date DESC LIMIT 5
            `, [matchId]),

            // E. Estatísticas Coletivas FBref (Ofensivas, Defensivas, Avançadas)
            db.query(`
                SELECT 'ofensiva' as tipo, o.* FROM fbref_squad.offensive o WHERE team_id IN (SELECT home_team_id FROM core.matches_history WHERE id = $1 UNION SELECT away_team_id FROM core.matches_history WHERE id = $1) AND split_type = 'ALL'
                UNION ALL
                SELECT 'defensiva' as tipo, d.* FROM fbref_squad.defensive d WHERE team_id IN (SELECT home_team_id FROM core.matches_history WHERE id = $1 UNION SELECT away_team_id FROM core.matches_history WHERE id = $1) AND split_type = 'ALL'
                UNION ALL
                SELECT 'avancada' as tipo, a.* FROM fbref_squad.advanced a WHERE team_id IN (SELECT home_team_id FROM core.matches_history WHERE id = $1 UNION SELECT away_team_id FROM core.matches_history WHERE id = $1) AND split_type = 'ALL'
            `, [matchId]),

            // F. Estatísticas Individuais FBref (Player Props)
            db.query(`
                SELECT p.*, (SELECT home_team_id FROM core.matches_history WHERE id = $1) as home_team_id
                FROM fbref_player.comprehensive_stats p 
                WHERE team_id IN (SELECT home_team_id FROM core.matches_history WHERE id = $1 UNION SELECT away_team_id FROM core.matches_history WHERE id = $1)
                ORDER BY xg_per_90 DESC LIMIT 40
            `, [matchId]),

            // G. Mercados de Apostas +EV da Bet365 / Pinnacle
            db.query(`SELECT * FROM core.market_odds WHERE match_id = $1 AND ev_pct > 0 ORDER BY ev_pct DESC`, [matchId]),

            // Adicione isso à super-query do seu matchCenterController.js
            db.query(`SELECT prob_home, prob_draw, prob_away, ev_home, ev_away, is_value_bet 
                FROM quant_ml.predictions WHERE match_id = $1`, [matchId])
        ]);

        if (matchResult.rows.length === 0) {
            return res.status(404).json({ error: "Partida não encontrada no Data Warehouse." });
        }

        const match = matchResult.rows[0];
        const hId = match.home_team_id;
        const aId = match.away_team_id;

        // 2. DISSECANDO ESTATÍSTICAS COLETIVAS (FBREF)
        const teamStats = teamStatsResult.rows;
        const getStat = (tipo, team_id, field) => {
            const row = teamStats.find(t => t.tipo === tipo && t.team_id === team_id);
            return row ? Number(row[field]) : 0;
        };

        const fbrefOfensivas = [
            { nome: "xG Criado", casa: getStat('ofensiva', hId, 'xg_for'), fora: getStat('ofensiva', aId, 'xg_for'), sufixo: "", desc: "Gols Esperados Totais" },
            { nome: "Chutes no Alvo", casa: getStat('ofensiva', hId, 'shots_on_target'), fora: getStat('ofensiva', aId, 'shots_on_target'), sufixo: "", desc: "Precisão do ataque" },
            { nome: "Ações de Gol (GCA)", casa: getStat('ofensiva', hId, 'goal_creating_actions'), fora: getStat('ofensiva', aId, 'goal_creating_actions'), sufixo: "", desc: "Criação direta de gols" }
        ];

        const fbrefDefensivas = [
            { nome: "xG Concedido", casa: getStat('defensiva', hId, 'xg_against'), fora: getStat('defensiva', aId, 'xg_against'), sufixo: "", desc: "Fragilidade defensiva" },
            { nome: "Desarmes", casa: getStat('defensiva', hId, 'tackles_won'), fora: getStat('defensiva', aId, 'tackles_won'), sufixo: "", desc: "Tackles bem sucedidos" },
            { nome: "Interceptações", casa: getStat('defensiva', hId, 'interceptions'), fora: getStat('defensiva', aId, 'interceptions'), sufixo: "", desc: "Leitura de jogo" }
        ];

        const fbrefAvancadas = [
            { nome: "Posse de Bola", casa: getStat('avancada', hId, 'possession_pct'), fora: getStat('avancada', aId, 'possession_pct'), sufixo: "%", desc: "Controle de jogo" },
            { nome: "Toques na Área", casa: getStat('avancada', hId, 'touches_att_pen'), fora: getStat('avancada', aId, 'touches_att_pen'), sufixo: "", desc: "Infiltração profunda" }
        ];

        // 3. CONSTRUÇÃO DO JSON FINAL (Formatado para o Vue.js)
        const responseData = {
            partida: {
                casa: match.home_name,
                fora: match.away_name,
                corCasa: "#EF4444", // Pode ser dinâmico no futuro
                corFora: "#3B82F6",
                placarCasa: match.home_goals !== null ? match.home_goals : "-",
                placarFora: match.away_goals !== null ? match.away_goals : "-",
                xgCasa: match.xg_home ? match.xg_home : "-",
                xgFora: match.xg_away ? match.xg_away : "-",
                isLive: match.status === 'IN_PROGRESS',
                tempo: match.status === 'FINISHED' ? 90 : 0,
                hora: new Date(match.match_date).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
                
                formCasa: calcularForma(homeFormResult.rows, hId),
                formFora: calcularForma(awayFormResult.rows, aId),
                
                historico: formatarHistorico(h2hResult.rows, hId),
                
                stats: {
                    pts: 0, pts_j: 0, pts_f: 0, pts_jf: 0, // Espaço para tabela de Standings futura
                    win: 0, win_f: 0, avg_g: 0, avg_gc: 0, avg_gf: 0, avg_gcf: 0,
                    over: 0, over_f: 0, btts: 0, btts_f: 0, pos: getStat('avancada', hId, 'possession_pct'), pos_f: getStat('avancada', aId, 'possession_pct')
                },
                
                arbitro: match.referee || "TBD",
                arb_amarelos: "-", 
                arb_vermelhos: "-", 
                clima: "Desconhecido", 
                temp: "-",
                
                indFormCasa: [], // Formatar individualmente se necessário
                indFormFora: [],
                
                fbrefOfensivas,
                fbrefDefensivas,
                fbrefAvancadas,
                fbrefVariadas: [],
                gameState: [], // Opcional: Popular com dados de minutos da SportsData
                
                // Formata os mercados mapeados pelo TheOdds API
                mercados: oddsResult.rows.map(o => ({
                    categoria: o.categoria,
                    nome: o.nome_mercado,
                    ev: Number(o.ev_pct).toFixed(1),
                    prob: (100 / Number(o.fair_odd)).toFixed(1),
                    fair: Number(o.fair_odd).toFixed(2),
                    openOdd: Number(o.opening_odd).toFixed(2),
                    bookie: Number(o.current_odd).toFixed(2),
                    casaNome: o.bookmaker.toUpperCase()
                }))
            },
            playerProps: formatarPlayerProps(playerStatsResult.rows, match.home_name, match.away_name)
        };

        return res.status(200).json(responseData);

    } catch (error) {
        console.error("❌ [MATCH-CENTER-CONTROLLER] Erro ao processar partida:", error);
        return res.status(500).json({ error: "Falha ao gerar o Match Center." });
    }
};