// betgenius-backend/src/controllers/teamController.js

exports.getShield = async (req, res) => {
    const teamName = req.params.teamName;
    
    if (!teamName) {
        return res.status(400).send("Nome do time ausente");
    }

    try {
        // =================================================================
        // 1. TENTATIVA PRIMÁRIA: API OFICIAL DE ESCUDOS
        // =================================================================
        // Se você usa uma API própria (ou API-Football, Sportmonks), altere a URL aqui.
        // Abaixo, implementei um exemplo 100% funcional usando TheSportsDB (grátis):
        const apiUrl = `https://www.thesportsdb.com/api/v1/json/1/searchteams.php?t=${encodeURIComponent(teamName)}`;
        
        // Node.js 18+ possui fetch nativo. Se usar versão antiga, importe o 'axios'.
        const response = await fetch(apiUrl);
        
        if (response.ok) {
            const data = await response.json();
            
            // Valida se a API encontrou o time e se ele possui a imagem (badge/logo)
            if (data.teams && data.teams.length > 0 && data.teams[0].strTeamBadge) {
                const officialShieldUrl = data.teams[0].strTeamBadge;
                
                // Redireciona o Vue.js para o escudo oficial
                return res.redirect(officialShieldUrl);
            }
        }

        // Se a API retornou 200 mas o time não existe lá, lançamos um erro 
        // proposital para pular para o bloco catch e ativar o Fallback.
        throw new Error("Escudo oficial não encontrado na base de dados.");

    } catch (error) {
        // =================================================================
        // 2. FALLBACK S-TIER: GERADOR DE INICIAIS
        // =================================================================
        // Ocultamos o console.error em produção para não poluir os logs
        // console.log(`[SHIELD API] Fallback ativado para o time: ${teamName}`);

        const words = teamName.trim().split(' ');
        let initials = '';
        if (words.length >= 2) {
            initials = (words[0][0] + words[1][0]).toUpperCase();
        } else {
            initials = teamName.substring(0, 2).toUpperCase();
        }

        // Cores da Identidade Visual da BetGenius
        const bgColor = "121927"; // Fundo escuro do painel
        const textColor = "10B981"; // Verde neon do +EV

        const fallbackUrl = `https://ui-avatars.com/api/?name=${initials}&background=${bgColor}&color=${textColor}&size=128&bold=true&format=svg`;

        // Redireciona o Vue.js para o escudo gerado matematicamente
        return res.redirect(fallbackUrl);
    }
};