// betgenius-backend/src/routes/index.js
const express = require('express');
const router = express.Router();

// =====================================================================
// IMPORTAÇÃO DE CONTROLADORES (CORRIGIDA)
// =====================================================================
const ticketController = require('../controllers/ticketController');
const teamController = require('../controllers/teamController');
const matchController = require('../controllers/matchController');
const sentimentController = require('../controllers/sentimentController');
const fundController = require('../controllers/fundController');
const systemController = require('../controllers/systemController');
const quantController = require('../controllers/quantController');
const settlementController = require('../controllers/settlementController');
const authController = require('../controllers/authController');
const matchCenterController = require('../controllers/matchCenterController'); // <-- FIX: '../' em vez de './'

// =====================================================================
// HEALTHCHECK & SISTEMA BASE (TOPBAR E CONFIGS)
// =====================================================================
router.post('/auth/login', authController.login);
router.get('/health', (req, res) => { res.json({ status: "S-Tier API Online" }); });

// Ticker e Heartbeat da Placa-Mãe (App.vue)
router.get('/system/heartbeat', systemController.getHeartbeat);
router.get('/system/alerts', systemController.getAlerts);

// Centro de Comando (ViewConfig.vue)
router.get('/system/config', systemController.getConfig);
router.put('/system/config', systemController.updateConfig);


// =====================================================================
// MATCH CENTER & RADAR ESPORTIVO
// =====================================================================
router.get('/matches/today', matchController.getTodayMatches);
router.get('/teams/shield/:teamName', teamController.getShield);

// ROTA S-TIER: Apontando diretamente para o nosso novo construtor de JSON pesado
router.get('/match-center/:matchId', matchCenterController.getMatchCenter);


// =====================================================================
// QUANTITATIVO (IA, HFT, STREAKS & STEAMERS)
// =====================================================================
router.get('/quant/dashboard', quantController.getDashboardData);
router.get('/quant/gold-picks', quantController.getGoldPicks);
router.get('/quant/live-scout', quantController.getLiveScout);
router.get('/quant/top-streaks', quantController.getTopStreaks);
router.get('/quant/steamers', quantController.getSteamers);
router.post('/quant/auto-builder', quantController.getAutoTicketBuilder);


// =====================================================================
// OPERAÇÕES FINANCEIRAS E TESOURARIA
// =====================================================================
// Dashboard Financeira Clássica
router.get('/fund/dashboard', fundController.getFundDashboard);

// Apostas e Bilhetes
router.post('/build-ticket', ticketController.buildTicket);
router.post('/fund/place-bet', fundController.placeBet);

// Liquidação (Settle Engine)
router.post('/fund/run-settlement', settlementController.runSettlement);

// Tesouraria S-Tier (ViewConfig.vue)
router.get('/fund/treasury', fundController.getTreasury);
router.post('/fund/deposit', fundController.registerDeposit);
router.post('/fund/dividend', fundController.liquidateDividend);


// =====================================================================
// SENTIMENTO E HYPE
// =====================================================================
router.get('/sentiment/dashboard', sentimentController.getDashboardData);

module.exports = router;