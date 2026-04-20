// backend/src/server.js
require('dotenv').config();
const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const Redis = require('ioredis');
const helmet = require('helmet');
const cors = require('cors');
// Importando o nosso executor de Python para rotas sob demanda
// const { runPythonScript } = require('./services/pythonRunner'); 

// =====================================================================
// BETGENIUS HFT - HYBRID GATEWAY (WEBSOCKETS + REST API)
// A Medula Espinhal entre o Cérebro Python (Redis) e a Interface Vue.js
// =====================================================================

const app = express();

// 1. Blindagem REST API (Middlewares)
app.use(helmet()); 
app.use(cors({ origin: process.env.FRONTEND_URL || "*" }));
app.use(express.json({ limit: '50mb' })); 
app.use(express.urlencoded({ limit: '50mb', extended: true }));

const server = http.createServer(app);

// 2. Configuração do Socket.io com Blindagem de CORS
const io = new Server(server, {
    cors: {
        origin: ['https://betgenius-pi.vercel.app/', 'http://localhost:5173'], 
        methods: ['GET', 'POST', 'PUT', 'DELETE'],
        credentials: true
    },
    // Otimizações para HFT (Baixa latência e pacotes comprimidos)
    transports: ['websocket'],
    allowUpgrades: false,
    pingInterval: 10000,
    pingTimeout: 5000
});

// 3. Conexão com o Message Broker (Redis Pub/Sub)
const redisSubscriber = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');

redisSubscriber.on('connect', () => {
    console.log('📡 [GATEWAY] Conectado ao Redis HFT Broker.');
});

redisSubscriber.on('error', (err) => {
    // Trocado para Warn para não crashar a API caso o Redis local esteja desligado
    console.warn('⚠️ [GATEWAY] Aviso: Redis offline. Sockets em stand-by.');
});

// 4. Inscrição nos Canais de Alta Frequência (Missões 1 e 2 do Python)
const HFT_CHANNELS = [
    'betgenius:stream:opportunities', // Alertas de +EV (Surebets, Asian Drops)
    'betgenius:stream:market_updates',// Mudanças de Odds em tempo real
    'betgenius:stream:props_updates', // Snipers de Jogadores
    'betgenius:stream:sentiment_alerts' // 👈 ADD: Canal de Sentimento NLP
];

redisSubscriber.subscribe(...HFT_CHANNELS, (err, count) => {
    if (err) {
        console.error('Falha ao se inscrever nos canais do Redis:', err);
    } else {
        console.log(`⚡ [GATEWAY] Escutando ${count} canais HFT simultaneamente.`);
    }
});

// =====================================================================
// O MOTOR DE BROADCASTING (PUB/SUB -> WEBSOCKETS)
// =====================================================================

redisSubscriber.on('message', (channel, message) => {
    try {
        const payload = JSON.parse(message);

        // Roteamento inteligente de eventos para o Front-End
        switch (channel) {
            case 'betgenius:stream:opportunities':
                io.emit('NEW_ALPHA_OPPORTUNITY', payload);
                console.log(`🔥 [BROADCAST] Oportunidade +EV disparada: ID ${payload.match_id || payload.jogo}`);
                break;

            case 'betgenius:stream:market_updates':
                io.emit('MARKET_TICK', payload);
                break;

            case 'betgenius:stream:props_updates':
                io.emit('PROPS_TICK', payload);
                break;

            case 'betgenius:stream:sentiment_alerts':
                // O Python Scraper manda a notícia pro Redis, o Node emite pro Vue.js
                io.emit('MARKET_SENTIMENT_ALERT', payload);
                console.log(`🚨 [SENTIMENT] Novo alerta de mercado disparado: ${payload.tipo}`);
                break;

            default:
                console.warn(`Canal não mapeado: ${channel}`);
        }
    } catch (error) {
        console.error('Erro ao fazer parse da mensagem do Broker:', error);
    }
});

// =====================================================================
// GESTÃO DE CLIENTES VUE.JS (FRONT-END)
// =====================================================================
let connectedClients = 0;

io.on('connection', (socket) => {
    connectedClients++;
    console.log(`🟢 Cliente conectado [ID: ${socket.id}]. Total: ${connectedClients}`);

    socket.on('REQUEST_LATEST_SNAPSHOT', async (gameId) => {
        console.log(`Cliente ${socket.id} solicitou snapshot do jogo ${gameId}`);
        // Lógica de snapshot futura
    });

    socket.on('disconnect', () => {
        connectedClients--;
        console.log(`🔴 Cliente desconectado [ID: ${socket.id}]. Total: ${connectedClients}`);
    });
});

// =====================================================================
// ROTAS REST API (API CENTRAL)
// =====================================================================
const apiRoutes = require('./routes/index');

// 👇 AJUSTE VITAL: Monta as rotas no prefixo /api/v1 exigido pelo Vue.js
app.use('/api/v1', apiRoutes);

// =====================================================================
// INICIALIZAÇÃO DO SERVIDOR
// =====================================================================
// 👇 AJUSTE VITAL: Escuta na porta 8000 para sincronizar com o Frontend
// O jeito certo para a nuvem:
const PORT = process.env.PORT || 8000;
server.listen(PORT, () => {
    console.log(`🚀 Motor S-Tier rodando na porta ${PORT}`);
});