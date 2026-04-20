<template>
  <WidgetCard titulo="Radar de Streaks (Anomalias)">
    
    <template #icone>
      <Flame :size="16" class="text-orange-500 animate-pulse" />
    </template>

    <template #acoes>
      <select 
        v-model="filtroAtual" 
        :disabled="isLoading"
        class="bg-black/50 text-xs text-gray-300 border border-white/10 rounded px-2 py-1 outline-none focus:border-orange-500 transition-colors cursor-pointer"
      >
        <option value="ALL">Top Streaks (Todas)</option>
        <option v-for="tipo in tiposDisponiveis" :key="tipo" :value="tipo">
          {{ tipo }}
        </option>
      </select>
    </template>

    <div class="flex flex-col gap-3 overflow-y-auto custom-scrollbar h-full pr-1">
      
      <template v-if="isLoading">
        <div v-for="i in 4" :key="'skel'+i" class="p-4 rounded-xl border border-white/5 bg-white/[0.02] animate-pulse flex items-center justify-between">
          <div>
            <div class="flex gap-2 mb-2">
              <div class="w-20 h-5 bg-gray-700 rounded"></div>
              <div class="w-16 h-5 bg-gray-700 rounded"></div>
            </div>
            <div class="w-40 h-4 bg-gray-700 rounded"></div>
          </div>
          <div class="w-12 h-10 bg-gray-700 rounded-lg"></div>
        </div>
      </template>

      <template v-else>
        <div v-for="streak in streaksFiltradas" :key="streak.equipe + streak.tipo" 
             class="p-4 rounded-xl border transition-all flex items-center justify-between group bg-white/[0.02] border-white/5 hover:bg-black/40 hover:border-orange-500/30">
          
          <div>
            <div class="flex items-center gap-2 mb-2">
              <span class="text-[10px] font-mono tracking-widest uppercase py-0.5 px-2 rounded font-bold border"
                    :style="{ color: streak.cor, backgroundColor: streak.cor + '15', borderColor: streak.cor + '30' }">
                {{ streak.tipo }}
              </span>
              <span class="text-[10px] text-gray-400 font-mono flex items-center gap-1 bg-black/40 px-2 py-0.5 rounded border border-white/5">
                 <TrendingUp :size="12" :color="streak.cor" /> {{ streak.jogos }} JOGOS
              </span>
            </div>
            
            <div class="font-bold text-sm text-white flex items-center gap-2">
              {{ streak.equipe }} 
              <span class="text-gray-500 text-[10px] font-normal uppercase tracking-widest bg-white/5 px-1.5 rounded">vs {{ streak.adversario }}</span>
            </div>
          </div>

          <button @click="adicionarAoBilhete(streak)" class="w-12 h-10 rounded-lg flex flex-col items-center justify-center transition-all border border-white/10 bg-black/20 group-hover:border-orange-500 group-hover:bg-orange-500/10 cursor-pointer shadow-sm">
            <span class="text-xs font-mono font-bold text-gray-300 group-hover:text-orange-400 transition-colors">
              {{ streak.odd }}
            </span>
          </button>

        </div>

        <div v-if="streaksFiltradas.length === 0" class="flex flex-col items-center justify-center py-8 opacity-40">
          <Flame size="30" class="text-gray-500 mb-2" />
          <p class="text-[10px] uppercase tracking-widest font-bold text-center px-4">
            Nenhuma sequência ativa para este filtro.
          </p>
        </div>
      </template>

    </div>
  </WidgetCard>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { Flame, TrendingUp } from 'lucide-vue-next';
import axios from 'axios';
import WidgetCard from './WidgetCard.vue';

const streaks = ref([]);
const isLoading = ref(true);
const filtroAtual = ref('ALL');

// ==========================================
// COMPUTAÇÃO E FILTROS DINÂMICOS
// ==========================================

// Lê todos os tipos de streaks que vieram do banco (ex: "VITÓRIAS SEGUIDAS", "JEJUM") 
// e cria as opções do <select> dinamicamente.
const tiposDisponiveis = computed(() => {
  const tipos = new Set(streaks.value.map(s => s.tipo));
  return Array.from(tipos).sort();
});

const streaksFiltradas = computed(() => {
  if (filtroAtual.value === 'ALL') return streaks.value;
  return streaks.value.filter(s => s.tipo === filtroAtual.value);
});

// ==========================================
// INTEGRAÇÃO COM BACKEND
// ==========================================
const fetchStreaks = async () => {
  try {
    isLoading.value = true;
    // Reutilizando o endpoint de alta performance que já construímos
    const res = await axios.get('http://localhost:8000/api/v1/quant/top-streaks');
    streaks.value = res.data;
  } catch (error) {
    console.error("❌ Falha ao buscar dados do Radar de Streaks:", error);
  } finally {
    isLoading.value = false;
  }
};

const adicionarAoBilhete = (streak) => {
  console.log("Streak selecionado para aposta:", streak);
  alert(`Oportunidade de Odd ${streak.odd} no jogo ${streak.equipe} v ${streak.adversario} enviada para o Ticket Builder!`);
};

onMounted(fetchStreaks);
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 3px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
</style>