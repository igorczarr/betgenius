// betgenius-backend/src/controllers/ticketController.js
const { runPythonScript } = require('../services/pythonRunner');

exports.buildTicket = async (req, res) => {
    try {
        const { match_id, target_odd, risk_profile } = req.body;

        // Validação de Segurança
        if (!match_id) {
            return res.status(400).json({ error: "O ID da partida (match_id) é obrigatório." });
        }

        console.log(`🛠️ [TICKET-CONTROLLER] Iniciando forjamento para Partida: ${match_id} | Odd Alvo: ${target_odd}`);

        // Aciona o script Python, passando os argumentos
        // Nota: O pythonRunner retorna uma Promise com o JSON parseado
        const result = await runPythonScript('sgp_builder.py', [
            match_id.toString(), 
            (target_odd || 2.0).toString(), 
            (risk_profile || 'moderado').toString()
        ]);

        // Retorna a Matriz Alpha processada para o Vue.js
        return res.status(200).json(result);

    } catch (error) {
        console.error("❌ [TICKET-CONTROLLER] Erro fatal:", error.message);
        return res.status(500).json({ 
            error: "Falha interna no motor de bilhetes S-Tier.",
            details: error.message
        });
    }
};