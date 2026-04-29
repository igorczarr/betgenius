// betgenius-backend/src/server.js
require('dotenv').config();
const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const Redis = require('ioredis');
const helmet = require('helmet');
const cors = require('cors');
const { createProxyMiddleware } = require('http-proxy-middleware');

// =====================================================================
// BETGENIUS HFT - HYBRID GATEWAY (NODE.JS BFF)
// A Medula Espinhal entre o Cérebro Python (Porta 8000) e a Interface Vue.js
// =====================================================================

const app = express();

// 1. Blindagem de Segurança (CORS e Headers)
app.use(helmet()); 
// Aceitamos conexões do Vue.js de desenvolvimento (5173) ou Vercel em produção
const allowedOrigins = process.env.FRONTEND_URL 
    ? process.env.FRONTEND_URL.split(',') 
    : ['http://localhost:5173', 'https://betgenius-pi.vercel.app'];

app.use(cors({ 
    origin: allowedOrigins, 
    credentials: true 
}));

// =====================================================================
// 2. PROXY REVERSO (O Pulo do Gato Institucional)
// =====================================================================
const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://127.0.0.1:8000';

app.use('/api/v1', createProxyMiddleware({ 
    target: PYTHON_API_URL, 
    changeOrigin: true,
    // 🛑 A CURA DO 404: Impede o Express de decapitar o /api/v1
    // Ele vai pegar a URL original exata (ex: /api/v1/system/config) e mandar para o Python.
    pathRewrite: (path, req) => {
        return req.originalUrl; 
    },
    onProxyReq: (proxyReq, req, res) => {
        // Auditoria visual clara no terminal do Node
        console.log(`[PROXY] 🔄 Disparando: ${req.method} ${req.originalUrl} -> Cérebro Python`);
    },
    onError: (err, req, res) => {
        console.error(`[PROXY ERROR] Falha de comunicação: ${err.message}`);
        // Retorna 502 se o Python ainda estiver a ligar
        res.status(502).json({ error: "Aguardando motores quantitativos iniciarem..." });
    }
}));

// Importante: O Parser de JSON deve ficar DEPOIS do proxyMiddleware na cadeia do Express
// para não consumir o body da requisição antes do Proxy tentar lê-lo.
app.use(express.json({ limit: '50mb' })); 
app.use(express.urlencoded({ limit: '50mb', extended: true }));

const server = http.createServer(app);

// =====================================================================
// 3. CONFIGURAÇÃO DO WEBSOCKET S-TIER (SOCKET.IO)
// =====================================================================
const io = new Server(server, {
    cors: {
        origin: allowedOrigins, 
        methods: ['GET', 'POST', 'PUT', 'DELETE'],
        credentials: true
    },
    // Otimizações para HFT (Baixa latência, forçando websocket nativo)
    transports: ['websocket'],
    allowUpgrades: false,
    pingInterval: 10000,
    pingTimeout: 5000
});

// =====================================================================
// 4. CONEXÃO COM O MESSAGE BROKER (REDIS PUB/SUB)
// =====================================================================

// Tratamento S-Tier para a sua string do Upstash
const rawRedisUrl = process.env.REDIS_URL || 'redis://localhost:6379';

// Removemos o comando "redis-cli --tls -u " caso ele esteja na string, deixando apenas a URL
const cleanRedisUrl = rawRedisUrl.replace('redis-cli --tls -u ', '').trim();

const redisSubscriber = new Redis(cleanRedisUrl, {
    // Configurações para Upstash/Cloud
    maxRetriesPerRequest: null, 
    // Ativa TLS/SSL se a string contiver 'tls' ou a URL começar com 'rediss'
    tls: (rawRedisUrl.includes('--tls') || cleanRedisUrl.startsWith('rediss')) ? {} : undefined,
    retryStrategy(times) {
        const delay = Math.min(times * 50, 2000);
        return delay;
    }
});

redisSubscriber.on('connect', () => {
    console.log('📡 [GATEWAY] Conectado ao Redis HFT (Upstash) com TLS.');
});

redisSubscriber.on('error', (err) => {
    // Evita o crash do servidor se o Upstash demorar a responder
    console.warn(`⚠️ [GATEWAY] Redis Status: ${err.message}`);
});

// Inscrição nos Canais (Missões 1 e 2 do Python)
const HFT_CHANNELS = [
    'betgenius:stream:opportunities', 
    'betgenius:stream:market_updates',
    'betgenius:stream:props_updates', 
    'betgenius:stream:sentiment_alerts'
];

redisSubscriber.subscribe(...HFT_CHANNELS, (err, count) => {
    if (err) {
        console.error('❌ Erro na subscrição HFT:', err.message);
    } else {
        console.log(`⚡ [GATEWAY] Escutando ${count} canais HFT via Upstash.`);
    }
});

// =====================================================================
// 5. O MOTOR DE BROADCASTING (REDIS -> VUE.JS)
// =====================================================================
redisSubscriber.on('message', (channel, message) => {
    try {
        const payload = JSON.parse(message);

        // Roteamento inteligente de eventos para o Front-End
        switch (channel) {
            case 'betgenius:stream:opportunities':
                io.emit('NEW_ALPHA_OPPORTUNITY', payload);
                console.log(`🔥 [BROADCAST] Oportunidade +EV disparada para UI.`);
                break;

            case 'betgenius:stream:market_updates':
                io.emit('MARKET_TICK', payload);
                break;

            case 'betgenius:stream:props_updates':
                io.emit('PROPS_TICK', payload);
                break;

            case 'betgenius:stream:sentiment_alerts':
                io.emit('MARKET_SENTIMENT_ALERT', payload);
                console.log(`🚨 [BROADCAST] Alerta de Sentimento/Drop de Odd enviado.`);
                break;

            default:
                console.warn(`Canal não mapeado: ${channel}`);
        }
    } catch (error) {
        console.error('Erro ao fazer parse da mensagem do Broker:', error);
    }
});

// =====================================================================
// 6. GESTÃO DE CLIENTES VUE.JS
// =====================================================================
let connectedClients = 0;

io.on('connection', (socket) => {
    connectedClients++;
    console.log(`🟢 Terminal Operacional Conectado [ID: ${socket.id}]. Terminais Ativos: ${connectedClients}`);

    socket.on('REQUEST_LATEST_SNAPSHOT', async (gameId) => {
        console.log(`[REQUEST] Cliente ${socket.id} solicitou snapshot do jogo ${gameId}`);
        // Se necessário, o Node pode fazer um fetch no Python aqui e devolver o snapshot
    });

    socket.on('disconnect', () => {
        connectedClients--;
        console.log(`🔴 Terminal Desconectado [ID: ${socket.id}]. Terminais Ativos: ${connectedClients}`);
    });
});

// =====================================================================
// INICIALIZAÇÃO DO SERVIDOR (PORTA 3000)
// =====================================================================
// O Vue.js aponta o axios e o socket.io para a porta 3000. 
// O Node.js na porta 3000 envia as chamadas REST para a porta 8000 (Python).
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log(`==================================================================`);
    console.log(`🚀 BETGENIUS NODE.JS GATEWAY S-TIER INICIADO`);
    console.log(`✅ OUVINDO NA PORTA: ${PORT}`);
    console.log(`🔄 REDIRECIONANDO CHAMADAS REST PARA O PYTHON: ${PYTHON_API_URL}`);
    console.log(`==================================================================`);
});