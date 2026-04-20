// betgenius-backend/routes/systemRoutes.js

const express = require('express');
const router = express.Router();
const systemController = require('../controllers/systemController');
const alertController = require('../controllers/alertController'); // <--- Adicione a importação

// Rota de pulsação (Heartbeat) - Usada pela TopBar
router.get('/heartbeat', systemController.getHeartbeat);

// Radar de Inteligência - Usada pelo Geninho Intel Widget
router.get('/alerts', alertController.getLiveAlerts); // <--- Adicione a rota

module.exports = router;