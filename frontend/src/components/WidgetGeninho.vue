<template>
  <WidgetCard titulo="Geninho Intel (Live Alerts)">
    <template #icone>
      <Radio :size="16" class="text-blue-400 animate-pulse" />
    </template>
    <template #acoes>
      <div class="flex items-center gap-1.5">
        <span class="relative flex h-2 w-2">
          <span v-if="!isLoading" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-2 w-2" :class="isLoading ? 'bg-gray-500' : 'bg-red-500'"></span>
        </span>
        <span class="text-[9px] text-gray-400 uppercase tracking-widest font-bold">{{ isLoading ? 'Conectando...' : 'Radar Ativo' }}</span>
      </div>
    </template>

    <div class="relative border-l border-white/10 ml-3 pl-4 flex flex-col gap-5 mt-2 h-full overflow-y-auto custom-scrollbar pr-2">
      
      <template v-if="isLoading && alertas.length === 0">
        <div v-for="i in 4" :key="'skel'+i" class="relative animate-pulse">
          <div class="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full border-2 border-gray-800 bg-gray-700"></div>
          <div class="h-2 w-16 bg-gray-700 rounded mb-2"></div>
          <div class="h-8 w-full bg-gray-800/50 rounded"></div>
        </div>
      </template>

      <template v-else>
        <div v-for="alerta in alertas" :key="alerta.id" class="relative group">
          <div class="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full border-2 border-[#0b0f19] shadow-[0_0_8px_currentColor] transition-transform group-hover:scale-125" 
               :style="{ color: getAlertColor(alerta.tipo), backgroundColor: getAlertColor(alerta.tipo) }"></div>
          
          <div class="flex items-center justify-between gap-2 mb-1">
            <div class="flex items-center gap-2">
              <span class="text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded bg-black/40 border border-white/5" 
                    :style="{ color: getAlertColor(alerta.tipo) }">
                {{ alerta.tipo }}
              </span>
              <span class="text-[9px] text-gray-500 font-mono font-bold">{{ formatTimeAgo(alerta.criado_em) }}</span>
            </div>
            <span v-if="alerta.confianca" class="text-[8px] text-gray-600 font-mono tracking-widest uppercase">
              Conf: {{ alerta.confianca }}%
            </span>
          </div>
          
          <p class="text-[11px] text-gray-300 leading-relaxed font-mono">
            <strong class="text-white font-sans tracking-wide">{{ alerta.time }}:</strong> {{ alerta.texto }}
          </p>
        </div>

        <div v-if="alertas.length === 0" class="flex flex-col items-center justify-center h-32 opacity-50">
          <Radio size="24" class="text-gray-500 mb-2" />
          <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Nenhuma anomalia detectada</span>
        </div>
      </template>

    </div>
  </WidgetCard>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { Radio } from 'lucide-vue-next';
import axios from 'axios';
import WidgetCard from './WidgetCard.vue';

// Estado
const alertas = ref([]);
const isLoading = ref(true);
let pollingInterval;

// Mapa de Cores Semânticas
const getAlertColor = (tipo) => {
  const t = tipo.toUpperCase();
  if (t.includes('CRÍTICO') || t.includes('LESÃO')) return '#EF4444'; // Red
  if (t.includes('ODDS DROP') || t.includes('MERCADO')) return '#F59E0B'; // Amber/Orange
  if (t.includes('CLIMA') || t.includes('SISTEMA')) return '#3B82F6'; // Blue
  if (t.includes('TÁTICA') || t.includes('ESCALAÇÃO')) return '#A855F7'; // Purple
  return '#10B981'; // Green (Oportunidades Padrão)
};

// Parser de Tempo Relativo (Ex: "Há 5 min")
const formatTimeAgo = (dateString) => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);

  if (diffMins < 1) return 'Agora mesmo';
  if (diffMins < 60) return `Há ${diffMins} min`;
  if (diffHours < 24) return `Há ${diffHours} h`;
  return 'Há +1 dia';
};

const fetchAlerts = async () => {
  try {
    const res = await axios.get('http://localhost:8000/api/v1/system/alerts');
    alertas.value = res.data;
  } catch (error) {
    console.error("❌ Falha ao buscar Intel Alerts:", error);
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  fetchAlerts();
  // Radar varre o banco a cada 30 segundos
  pollingInterval = setInterval(fetchAlerts, 30000);
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