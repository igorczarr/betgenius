<template>
  <WidgetCard titulo="Steamers (Smart Money & Drops)">
    <template #icone>
      <Zap :size="16" class="text-yellow-500" />
    </template>
    <template #acoes>
      <span class="text-[10px] text-[#10B981] font-mono flex items-center gap-1.5 bg-[#10B981]/10 border border-[#10B981]/20 px-2 py-1 rounded shadow-inner">
        <span class="relative flex h-1.5 w-1.5">
          <span v-if="!isLoading" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#10B981] opacity-75"></span>
          <span class="relative inline-flex rounded-full h-1.5 w-1.5" :class="isLoading ? 'bg-gray-500' : 'bg-[#10B981]'"></span>
        </span>
        {{ isLoading && steamers.length === 0 ? 'CONECTANDO...' : 'AO VIVO' }}
      </span>
    </template>

    <div class="flex flex-col gap-3 overflow-y-auto custom-scrollbar h-full pr-1">
      
      <template v-if="isLoading && steamers.length === 0">
        <div v-for="i in 4" :key="'skel'+i" class="p-3 rounded-lg border border-white/5 bg-white/[0.02] animate-pulse">
          <div class="flex justify-between items-center mb-3">
            <div class="h-4 w-32 bg-gray-700 rounded"></div>
            <div class="h-4 w-10 bg-gray-700 rounded"></div>
          </div>
          <div class="flex justify-between items-center">
            <div class="h-3 w-20 bg-gray-800 rounded"></div>
            <div class="h-4 w-24 bg-gray-700 rounded"></div>
          </div>
        </div>
      </template>

      <template v-else>
        <div v-for="steam in steamers" :key="steam.id" class="p-3 rounded-lg border border-white/5 bg-black/20 hover:bg-white/5 hover:border-blue-500/30 transition-colors group cursor-default shadow-sm">
          
          <div class="flex justify-between items-center mb-2">
            <span class="text-xs font-bold text-white truncate pr-2">{{ steam.jogo }}</span>
            <span class="text-[10px] bg-red-500/10 text-red-400 border border-red-500/20 px-1.5 py-0.5 rounded font-mono font-bold shadow-inner">
              {{ steam.drop }}%
            </span>
          </div>
          
          <div class="flex justify-between items-center">
            <span class="text-[10px] text-gray-400 uppercase tracking-wider truncate max-w-[120px]">{{ steam.mercado }}</span>
            <div class="flex items-center gap-2 font-mono text-sm">
              <span class="text-gray-500 line-through decoration-red-500/50 text-[11px]">{{ parseFloat(steam.oddAntiga).toFixed(2) }}</span>
              <ArrowRight :size="12" class="text-gray-600" />
              <span class="text-blue-400 font-bold drop-shadow-[0_0_5px_rgba(59,130,246,0.3)]">{{ parseFloat(steam.oddNova).toFixed(2) }}</span>
            </div>
          </div>

        </div>

        <div v-if="steamers.length === 0" class="flex flex-col items-center justify-center py-8 opacity-50 text-center">
          <Zap size="24" class="text-gray-500 mb-2" />
          <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold px-4">
            Nenhuma movimentação brusca de mercado (Drop > 10%) nas últimas horas.
          </span>
        </div>
      </template>

    </div>
  </WidgetCard>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { Zap, ArrowRight } from 'lucide-vue-next';
import axios from 'axios';
import WidgetCard from './WidgetCard.vue';

const steamers = ref([]);
const isLoading = ref(true);
let pollingInterval;

const fetchSteamers = async () => {
  try {
    const res = await axios.get('http://localhost:8000/api/v1/quant/steamers');
    steamers.value = res.data;
  } catch (error) {
    console.error("❌ Erro ao buscar Steamers (Odds Drops):", error);
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  fetchSteamers();
  // Polling a cada 20 segundos (Mercado de apostas é volátil)
  pollingInterval = setInterval(fetchSteamers, 20000);
});

onUnmounted(() => {
  clearInterval(pollingInterval);
});
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 3px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
</style>