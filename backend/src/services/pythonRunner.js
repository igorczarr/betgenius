// betgenius-backend/src/services/pythonRunner.js
const { spawn } = require('child_process');
const path = require('path');

/**
 * Subprocess Manager S-Tier.
 * Executa scripts Python, gerencia timeouts, captura logs e extrai o Payload JSON.
 * * @param {string} scriptName - O nome do arquivo Python (ex: 'sgp_builder.py')
 * @param {Array} args - Argumentos para passar para o Python (ex: ['1', '2.50', 'moderado'])
 * @param {number} timeoutMs - Tempo máximo de execução antes de matar o processo (Padrão: 30s)
 * @returns {Promise<Object>} - Retorna o Objeto JSON parseado com os bilhetes ou dados.
 */
const runPythonScript = (scriptName, args = [], timeoutMs = 30000) => {
    return new Promise((resolve, reject) => {
        // 1. Resolve Caminhos e Ambientes
        // Sobe duas pastas para sair de src/services e entrar na pasta workers
        const scriptPath = path.join(__dirname, '../../workers', scriptName);
        
        // Define o executável do Python. Se você usa ambiente virtual (Anaconda/Venv), 
        // pode definir a variável PYTHON_PATH no .env. Se não, ele usa o padrão do SO.
        const pythonExecutable = process.env.PYTHON_PATH || 'python';

        console.log(`⚙️ [PYTHON-RUNNER] Iniciando: ${pythonExecutable} ${scriptName} [Args: ${args.join(', ')}]`);

        // 2. Cria o Subprocesso (The Child)
        const pythonProcess = spawn(pythonExecutable, [scriptPath, ...args]);

        let outputData = '';
        let errorData = '';

        // 3. Captura a Saída (STDOUT)
        pythonProcess.stdout.on('data', (data) => {
            outputData += data.toString();
        });

        // 4. Captura Erros e Logs Críticos (STDERR)
        pythonProcess.stderr.on('data', (data) => {
            errorData += data.toString();
        });

        // 5. Sistema de Autodestruição (Timeout Preventivo)
        // Se o XGBoost ou o Pandas travarem, não podemos deixar o Node esperando para sempre.
        const timer = setTimeout(() => {
            pythonProcess.kill('SIGKILL');
            reject(new Error(`[TIMEOUT] O script ${scriptName} demorou mais de ${timeoutMs}ms e foi aniquilado.`));
        }, timeoutMs);

        // 6. Finalização do Processo
        pythonProcess.on('close', (code) => {
            clearTimeout(timer); // Cancela a autodestruição

            // Se o código não for 0, o Python crashou (ex: Erro de sintaxe, Falta de Memória)
            if (code !== 0) {
                console.error(`❌ [PYTHON-RUNNER] Crash no script ${scriptName} (Code ${code})`);
                console.error(`Detalhes do Python:\n${errorData}`);
                return reject(new Error(`Motor Python falhou. Detalhes nos logs do servidor.`));
            }

            // 7. O Extrator de Ouro (Regex de JSON)
            // O Python frequentemente imprime logs ("Carregando Matrix...", "Oráculo Iniciado").
            // O Node não liga para texto humano. Ele quer o Payload. Nós usamos Regex para caçar o último bloco JSON.
            try {
                // Procura por blocos que começam e terminam com {} ou []
                const jsonMatches = outputData.match(/\{[\s\S]*\}|\[[\s\S]*\]/g);
                
                if (jsonMatches && jsonMatches.length > 0) {
                    // Pega o último bloco JSON encontrado na saída (geralmente o payload final)
                    const lastJsonString = jsonMatches[jsonMatches.length - 1];
                    const payload = JSON.parse(lastJsonString);
                    resolve(payload);
                } else {
                    // Se não achou JSON, devolve o texto cru (Modo Debug)
                    console.warn(`⚠️ [PYTHON-RUNNER] Nenhum JSON detectado. Retornando texto bruto.`);
                    resolve({ status: "success", raw_output: outputData.trim() });
                }
            } catch (err) {
                console.error(`❌ [PYTHON-RUNNER] Falha ao fazer parse do JSON.`);
                console.error(`Saída bruta recebida:\n${outputData}`);
                reject(new Error(`O Python retornou um formato ilegível para a API.`));
            }
        });
    });
};

module.exports = { runPythonScript };