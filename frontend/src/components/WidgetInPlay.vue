<template>
  <WidgetCard titulo="In-Play Scout (Radar Ao Vivo)">
    <template #icone>
      <Activity :size="16" class="text-red-500 animate-pulse" />
    </template>
    <template #acoes>
      <div class="flex items-center gap-1.5">
        <span class="relative flex h-2 w-2">
          <span v-if="!isLoading" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-2 w-2" :class="isLoading ? 'bg-gray-500' : 'bg-red-500'"></span>
        </span>
        <span class="text-[9px] text-gray-400 uppercase tracking-widest font-bold">{{ isLoading && liveMatches.length === 0 ? 'Conectando...' : 'Live Sync' }}</span>
      </div>
    </template>

    <div class="flex flex-col gap-4 overflow-y-auto custom-scrollbar h-full pr-1">
      
      <template v-if="isLoading && liveMatches.length === 0">
        <div v-for="i in 3" :key="'skel'+i" class="p-3 rounded-lg bg-black/20 border border-gray-800 animate-pulse">
          <div class="flex justify-between items-center mb-3">
            <div class="flex items-center gap-2">
              <div class="w-6 h-4 bg-gray-700 rounded"></div>
              <div class="w-32 h-4 bg-gray-700 rounded"></div>
            </div>
            <div class="w-16 h-5 bg-gray-700 rounded"></div>
          </div>
          <div class="w-full h-1.5 bg-gray-800 rounded-full mb-2"></div>
        </div>
      </template>

      <template v-else>
        <div v-for="jogo in liveMatches" :key="jogo.match_id" class="p-3 rounded-lg bg-black/40 border border-gray-800 hover:border-red-500/30 transition-colors group">
          
          <div class="flex justify-between items-center mb-2">
            <div class="flex items-center gap-2">
              <span class="text-xs font-mono font-bold text-red-500 group-hover:animate-pulse">{{ jogo.tempo }}'</span>
              <span class="text-xs font-bold text-white truncate max-w-[150px] md:max-w-[200px]">
                {{ jogo.casa }} <span class="text-yellow-400 mx-1">{{ jogo.placarCasa }}x{{ jogo.placarFora }}</span> {{ jogo.fora }}
              </span>
            </div>
            
            <button class="text-[9px] bg-blue-500/10 text-blue-400 border border-blue-500/30 px-2 py-1 rounded font-bold uppercase tracking-wider hover:bg-blue-500 hover:text-white transition-all shadow-[0_0_10px_rgba(59,130,246,0.1)] truncate max-w-[80px] md:max-w-[120px]">
              {{ jogo.sugestao }}
            </button>
          </div>

          <div class="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden flex shadow-inner">
            <div class="h-full bg-blue-500 transition-all duration-500 ease-out" :style="{ width: jogo.pressaoCasa + '%' }"></div>
            <div class="h-full bg-gray-600 transition-all duration-500 ease-out" :style="{ width: jogo.pressaoFora + '%' }"></div>
          </div>
          
          <div class="flex justify-between mt-1">
            <span class="text-[9px] text-blue-400 font-mono">Pressão: {{ jogo.pressaoCasa }}%</span>
            <span class="text-[9px] text-gray-500 font-mono">{{ jogo.pressaoFora }}%</span>
          </div>

        </div>

        <div v-if="liveMatches.length === 0" class="flex flex-col items-center justify-center h-32 opacity-40">
          <Activity size="30" class="text-gray-500 mb-2" />
          <p class="text-[10px] text-gray-400 uppercase tracking-widest font-bold text-center px-4">
            Nenhuma anomalia Ao Vivo detectada no momento.
          </p>
        </div>
      </template>

    </div>
  </WidgetCard>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { Activity } from 'lucide-vue-next';
import axios from 'axios';
import WidgetCard from './WidgetCard.vue';

const liveMatches = ref([]);
const isLoading = ref(true);
let pollingInterval;

const fetchLiveMatches = async () => {
  try {
    const res = await axios.get('http://localhost:8000/api/v1/quant/live-scout');
    liveMatches.value = res.data;
  } catch (error) {
    console.error("❌ Falha ao buscar In-Play Scout:", error);
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  fetchLiveMatches();
  // Live Data exige atualização agressiva: a cada 15 segundos
  pollingInterval = setInterval(fetchLiveMatches, 15000);
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