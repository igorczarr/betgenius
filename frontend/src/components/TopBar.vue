<template>
  <header class="bg-panel-dark border-b border-gray-700 p-4 shadow-lg">
    <div class="container mx-auto flex justify-between items-center">
      
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 bg-bet-green rounded flex items-center justify-center font-bold text-bg-dark">
          BG
        </div>
        <h1 class="text-xl font-bold tracking-wider text-white">BET<span class="text-bet-green">GENIUS</span> <span class="text-xs text-gray-400 font-normal border border-gray-600 px-1 rounded">PRO</span></h1>
      </div>

      <div class="flex gap-6">
        
        <div class="flex flex-col items-end">
          <span class="text-xs text-gray-400 uppercase tracking-widest">Jogos Mapeados (Hoje)</span>
          <span v-if="isLoading" class="w-10 h-6 bg-gray-700 animate-pulse rounded mt-1"></span>
          <span v-else class="text-lg font-bold text-white">{{ stats.mappedGames }}</span>
        </div>

        <div class="flex flex-col items-end border-l border-gray-600 pl-6">
          <span class="text-xs text-gray-400 uppercase tracking-widest">Oportunidades (+EV)</span>
          <span v-if="isLoading" class="w-10 h-6 bg-gray-700 animate-pulse rounded mt-1"></span>
          <span v-else class="text-lg font-bold flex items-center gap-1" :class="stats.evOpportunities > 0 ? 'text-yellow-400' : 'text-gray-500'">
            <span v-if="stats.evOpportunities > 0" class="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></span> 
            {{ stats.evOpportunities }}
          </span>
        </div>

        <div class="flex flex-col items-end border-l border-gray-600 pl-6">
          <span class="text-xs text-gray-400 uppercase tracking-widest">Lucro Diário</span>
          <span v-if="isLoading" class="w-20 h-6 bg-gray-700 animate-pulse rounded mt-1"></span>
          <span v-else class="text-lg font-bold" :class="stats.dailyProfit >= 0 ? 'text-bet-green' : 'text-red-500'">
            {{ stats.dailyProfit >= 0 ? '+' : '' }} {{ formatCurrency(stats.dailyProfit) }}
          </span>
        </div>

        <div class="flex flex-col items-end border-l border-gray-600 pl-6">
          <span class="text-xs text-gray-400 uppercase tracking-widest">Banca Atual</span>
          <span v-if="isLoading" class="w-24 h-6 bg-gray-700 animate-pulse rounded mt-1"></span>
          <span v-else class="text-lg font-bold text-white">{{ formatCurrency(stats.currentBankroll) }}</span>
        </div>

      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import axios from 'axios';

// Estado Reativo S-Tier
const isLoading = ref(true);
const stats = ref({
  mappedGames: 0,
  evOpportunities: 0,
  dailyProfit: 0.0,
  currentBankroll: 0.0
});

let pollingInterval;

// Formatador Nativo de Moeda (BRL)
const formatCurrency = (value) => {
  return new Intl.NumberFormat('pt-BR', { 
    style: 'currency', 
    currency: 'BRL' 
  }).format(value);
};

// Função para buscar a pulsação do sistema no Backend
const fetchSystemHeartbeat = async () => {
  try {
    // Apontando para o futuro endpoint do nosso Node.js
    const res = await axios.get('http://localhost:8000/api/v1/system/heartbeat');
    stats.value = res.data;
  } catch (error) {
    console.error("❌ Falha de comunicação com o Backend (Heartbeat):", error);
    // Para não quebrar a UI enquanto você não liga o backend, os números ficarão congelados
  } finally {
    isLoading.value = false;
  }
};

// Ciclo de Vida do Componente
onMounted(() => {
  // Chamada imediata na primeira vez que abre a tela
  fetchSystemHeartbeat();
  
  // Atualiza os dados a cada 60 segundos (Polling)
  pollingInterval = setInterval(fetchSystemHeartbeat, 60000);
});

onUnmounted(() => {
  // Limpa a memória quando o componente for destruído
  clearInterval(pollingInterval);
});
</script>