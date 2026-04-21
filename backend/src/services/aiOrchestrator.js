// backend/src/services/aiOrchestrator.js
const { spawn } = require('child_process');
const path = require('path');

const runPythonScript = (scriptName) => {
    return new Promise((resolve, reject) => {
        // Aponta dinamicamente para o script na pasta workers/engine
        const scriptPath = path.resolve(__dirname, '../../', scriptName);
        console.log(`[AI-ORCHESTRATOR] 🚀 Acionando Motor Python: ${scriptName}`);

        // Roda o Python como um sub-processo
        const pythonProcess = spawn('python', [scriptPath]);

        pythonProcess.stdout.on('data', (data) => {
            console.log(`[${scriptName}] ${data.toString().trim()}`);
        });

        pythonProcess.stderr.on('data', (data) => {
            console.error(`[ERROR - ${scriptName}] ${data.toString().trim()}`);
        });

        pythonProcess.on('close', (code) => {
            if (code === 0) {
                console.log(`[AI-ORCHESTRATOR] ✅ Script ${scriptName} finalizado com sucesso.`);
                resolve();
            } else {
                console.log(`[AI-ORCHESTRATOR] ❌ Script ${scriptName} falhou com código ${code}.`);
                reject(new Error(`Falha no script ${scriptName}`));
            }
        });
    });
};

/**
 * Executa o Pipeline Diário Completo:
 * 1. Constrói as Features atuais.
 * 2. Faz as previsões da IA.
 */
const runDailyAI = async () => {
    try {
        console.log("=================================================");
        console.log("🦾 INICIANDO O CÉREBRO DA BETGENIUS (DAILY PIPELINE)");
        console.log("=================================================");
        
        // 1. Atualiza a feature_store (Calcula o Elo de ontem, EWMA, Tensão, etc)
        await runPythonScript('workers/feature_engineering/feature_orchestrator.py');
        
        // 2. Faz as predições para os jogos de hoje
        await runPythonScript('engine/predict_today.py');

        console.log("=================================================");
        console.log("🏆 PREDIÇÕES GERADAS! MATCH CENTER PRONTO PARA OPERAR.");
        console.log("=================================================");

    } catch (error) {
        console.error("[AI-ORCHESTRATOR] 🚨 FALHA CRÍTICA NO PIPELINE:", error);
    }
};

module.exports = {
    runDailyAI
};