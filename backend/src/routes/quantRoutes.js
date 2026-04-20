// betgenius-backend/routes/quantRoutes.js

const express = require('express');
const router = express.Router();
const quantController = require('../controllers/quantController');

// Middleware de Autenticação (Se você já tiver um, coloque aqui)
// const authMiddleware = require('../middlewares/auth');

// Rota principal da Dashboard do Quant Lab
router.get('/dashboard', quantController.getDashboardData);

module.exports = router;