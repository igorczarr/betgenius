// betgenius-frontend/src/services/apiClient.js
import axios from 'axios';

// Aponta para a porta padrão do FastAPI (Geralmente 8000)
const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export default {
  // 1. DADOS FINANCEIROS (BANCA)
  async getWallet() {
    try {
      const response = await apiClient.get('/wallet');
      return response.data; // Retorna: { balance, total_pnl, recent_trades }
    } catch (error) {
      console.error("Erro ao buscar carteira:", error);
      throw error;
    }
  },

  // 2. RADAR DE JOGOS DO DIA
  async getTodaysMatches() {
    try {
      const response = await apiClient.get('/matrix/today');
      return response.data.matches;
    } catch (error) {
      console.error("Erro ao buscar jogos do dia:", error);
      return [];
    }
  },

  // 3. TENDÊNCIAS E SEQUÊNCIAS (STREAKS)
  async getStreaks() {
    try {
      const response = await apiClient.get('/streaks');
      return response.data.streaks;
    } catch (error) {
      console.error("Erro ao buscar sequências:", error);
      return [];
    }
  },

  // 4. REGISTRAR UMA APOSTA (Dispara o Bankroll Manager no Python)
  async placeBet(matchId, ticker, jogo, mercado, selecao, odd, stake) {
    try {
      const response = await apiClient.post('/wallet/bet', {
        match_id: matchId,
        ticker: ticker,
        jogo: jogo,
        mercado: mercado,
        selecao: selecao,
        odd: odd,
        stake: stake
      });
      return response.data; // Retorna status success
    } catch (error) {
      console.error("Ordem rejeitada pela API:", error.response?.data || error);
      throw error;
    }
  }
};