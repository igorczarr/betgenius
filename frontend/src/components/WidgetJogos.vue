<template>
  <WidgetCard titulo="Jogos Mapeados (Hoje)">
    
    <template #icone>
      <CalendarDays :size="16" class="text-[#10B981]" />
    </template>

    <template #acoes>
      <select 
        v-model="selectedLeague" 
        class="bg-black/50 text-xs text-gray-300 border border-white/10 rounded px-2 py-1 outline-none focus:border-[#10B981] transition-colors cursor-pointer"
        :disabled="isLoading"
      >
        <option value="ALL">Todas as Ligas</option>
        <option v-for="liga in availableLeagues" :key="liga" :value="liga">
          {{ liga }}
        </option>
      </select>
    </template>

    <div class="flex flex-col gap-3 overflow-y-auto custom-scrollbar h-full pr-1">
      
      <template v-if="isLoading">
        <div v-for="i in 5" :key="'skel'+i" class="p-4 rounded-xl border border-white/5 bg-white/[0.02] animate-pulse flex justify-between items-center">
          <div>
            <div class="w-24 h-3 bg-gray-700 rounded mb-2"></div>
            <div class="w-40 h-4 bg-gray-700 rounded"></div>
          </div>
          <div class="w-8 h-8 rounded-lg bg-gray-700"></div>
        </div>
      </template>

      <template v-else>
        <div 
          v-for="jogo in filteredMatches" 
          :key="jogo.id" 
          @click="openMatchCenter(jogo.id)"
          class="p-4 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-[#10B981]/5 hover:border-[#10B981]/50 transition-all cursor-pointer group flex items-center justify-between"
        >
          <div>
            <span class="text-[10px] font-mono tracking-widest uppercase mb-1 block text-[#10B981]">
              {{ jogo.campeonato }} • {{ formatTime(jogo.data) }}
            </span>
            <div class="font-bold text-sm text-white flex items-center gap-2">
              {{ jogo.casa }} <span class="text-gray-500 text-[10px]">VS</span> {{ jogo.fora }}
            </div>
          </div>

          <button class="w-8 h-8 rounded-lg flex items-center justify-center transition-all bg-white/5 text-gray-500 group-hover:bg-[#10B981] group-hover:text-black">
            <Plus :size="18" />
          </button>
        </div>

        <div v-if="filteredMatches.length === 0" class="flex flex-col items-center justify-center py-8 opacity-40">
          <CalendarDays size="30" class="text-gray-500 mb-2" />
          <p class="text-[10px] uppercase tracking-widest font-bold text-center px-4">
            Nenhum jogo encontrado para este filtro.
          </p>
        </div>
      </template>

    </div>
  </WidgetCard>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { CalendarDays, Plus } from 'lucide-vue-next';
import axios from 'axios';
import WidgetCard from './WidgetCard.vue';

const matches = ref([]);
const isLoading = ref(true);
const selectedLeague = ref('ALL');

// Puxa as ligas únicas diretamente do array de jogos para popular o Select dinamicamente
const availableLeagues = computed(() => {
  const leagues = new Set(matches.value.map(m => m.campeonato));
  return Array.from(leagues).sort();
});

// Filtra os jogos com base no Select
const filteredMatches = computed(() => {
  if (selectedLeague.value === 'ALL') return matches.value;
  return matches.value.filter(m => m.campeonato === selectedLeague.value);
});

// Formata a data ISO para HH:MM local
const formatTime = (isoString) => {
  const date = new Date(isoString);
  return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
};

// Carrega os dados da API
const fetchTodayMatches = async () => {
  try {
    const res = await axios.get('http://localhost:8000/api/v1/matches/today');
    matches.value = res.data;
  } catch (error) {
    console.error("❌ Falha ao buscar jogos de hoje:", error);
  } finally {
    isLoading.value = false;
  }
};

// Redirecionamento S-Tier (Abre o Raio-X do jogo)
const openMatchCenter = (matchId) => {
  // Se você usar Vue Router: router.push(`/match-center/${matchId}`)
  console.log(`Abrindo o MatchCenter para o Jogo ID: ${matchId}`);
  alert(`Redirecionando para análise profunda do jogo ${matchId}...`);
};

onMounted(fetchTodayMatches);
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 3px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
</style>