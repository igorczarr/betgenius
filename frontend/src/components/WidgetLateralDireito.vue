<template>
  <div class="h-full flex flex-col bg-[#0b0f19] border-l border-white/5">
    
    <div class="p-4 border-b border-white/5 shrink-0 bg-black/20">
      <div class="flex p-1 rounded-lg bg-black/40 border border-white/10 shadow-inner">
        <button 
          @click="abaAtual = 'jogos'"
          class="flex-1 py-1.5 text-[11px] uppercase tracking-wider font-bold rounded transition-colors"
          :class="abaAtual === 'jogos' ? 'bg-blue-500/20 text-blue-400 shadow-sm' : 'text-gray-500 hover:text-gray-300'"
        >
          <CalendarDays :size="14" class="inline mb-0.5 mr-1"/> Jogos do Dia
        </button>
        <button 
          @click="abaAtual = 'streaks'"
          class="flex-1 py-1.5 text-[11px] uppercase tracking-wider font-bold rounded transition-colors"
          :class="abaAtual === 'streaks' ? 'bg-orange-500/20 text-orange-400 shadow-sm' : 'text-gray-500 hover:text-gray-300'"
        >
          <Flame :size="14" class="inline mb-0.5 mr-1"/> Streaks
        </button>
      </div>
      
      <div class="mt-3">
        <select 
          v-if="abaAtual === 'jogos'" 
          v-model="filtroLiga" 
          class="w-full bg-black/50 text-xs text-gray-300 border border-white/10 rounded px-3 py-1.5 outline-none focus:border-blue-500 transition-colors cursor-pointer"
        >
          <option value="ALL">Todas as Ligas</option>
          <option v-for="liga in ligasDisponiveis" :key="liga" :value="liga">{{ liga }}</option>
        </select>
        
        <select 
          v-if="abaAtual === 'streaks'" 
          v-model="filtroStreak" 
          class="w-full bg-black/50 text-xs text-gray-300 border border-white/10 rounded px-3 py-1.5 outline-none focus:border-orange-500 transition-colors cursor-pointer"
        >
          <option value="ALL">Top Streaks (Geral)</option>
          <option value="VITÓRIAS">Apenas Vitórias</option>
          <option value="JEJUM">Jejum (Sem Vencer)</option>
          <option value="DEFESA">Clean Sheets (Defesa)</option>
        </select>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto custom-scrollbar p-4 flex flex-col gap-3">
      
      <template v-if="isLoading">
        <div v-for="i in 5" :key="'sk'+i" class="h-16 rounded-xl border border-white/5 bg-white/[0.02] animate-pulse"></div>
      </template>

      <template v-else-if="abaAtual === 'jogos'">
        <div v-for="jogo in jogosFiltrados" :key="'j'+jogo.id" 
             @click="abrirMatchCenter(jogo.id)"
             class="p-3 rounded-xl border border-white/5 bg-white/[0.02] transition-all cursor-pointer group hover:border-blue-500/50 hover:bg-blue-500/5">
          <span class="text-[10px] font-mono tracking-widest uppercase mb-1 block text-blue-400">
            {{ jogo.campeonato }} • {{ formatTime(jogo.data) }}
          </span>
          <div class="font-bold text-sm text-white flex justify-between items-center">
            <span class="truncate pr-2">{{ jogo.casa }} <span class="text-gray-600 text-[10px] mx-1">V</span> {{ jogo.fora }}</span>
            <button class="text-gray-600 group-hover:text-blue-400 transition-colors"><Plus :size="16"/></button>
          </div>
        </div>
        <div v-if="jogosFiltrados.length === 0" class="text-center text-xs text-gray-500 py-10 font-mono uppercase tracking-widest">Nenhum jogo encontrado.</div>
      </template>

      <template v-else-if="abaAtual === 'streaks'">
        <div v-for="(streak, i) in streaksFiltradas" :key="'s'+i" 
             class="p-3 rounded-xl border border-white/5 bg-black/20 flex flex-col gap-2 hover:bg-white/5 transition-colors cursor-default">
          <div class="flex justify-between items-start">
            <span class="text-[9px] font-mono tracking-widest uppercase py-0.5 px-2 rounded font-bold border"
                  :style="{ color: streak.cor, backgroundColor: streak.cor + '15', borderColor: streak.cor + '30' }">
              {{ streak.tipo }}
            </span>
            <span class="text-xs font-mono font-bold text-white bg-[#121927] px-2 py-0.5 rounded border border-white/10">{{ streak.odd }}</span>
          </div>
          <div class="font-bold text-sm text-white truncate mt-1">
            {{ streak.equipe }} <span class="text-gray-500 font-normal text-xs ml-1">vs {{ streak.adversario }}</span>
          </div>
          <div class="text-[10px] text-gray-400 font-mono flex items-center gap-1.5 mt-1 bg-black/40 px-2 py-1 rounded w-fit">
             <TrendingUp :size="12" :color="streak.cor" /> {{ streak.jogos }} JOGOS SEGUIDOS
          </div>
        </div>
        <div v-if="streaksFiltradas.length === 0" class="text-center text-xs text-gray-500 py-10 font-mono uppercase tracking-widest">Nenhum streak ativo.</div>
      </template>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { CalendarDays, Flame, Plus, TrendingUp } from 'lucide-vue-next';
import axios from 'axios';


const abaAtual = ref('jogos');
const isLoading = ref(true);

const jogos = ref([]);
const streaks = ref([]);

const filtroLiga = ref('ALL');
const filtroStreak = ref('ALL');

// ==========================================
// LÓGICA DE FILTRAGEM
// ==========================================
const ligasDisponiveis = computed(() => {
  return Array.from(new Set(jogos.value.map(j => j.campeonato))).sort();
});

const jogosFiltrados = computed(() => {
  if (filtroLiga.value === 'ALL') return jogos.value;
  return jogos.value.filter(j => j.campeonato === filtroLiga.value);
});

const streaksFiltradas = computed(() => {
  if (filtroStreak.value === 'ALL') return streaks.value;
  return streaks.value.filter(s => s.tipo.includes(filtroStreak.value));
});

const formatTime = (isoString) => {
  const date = new Date(isoString);
  return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
};

const abrirMatchCenter = (id) => {
  console.log(`Navegando para o Match ID: ${id}`);
  // router.push(`/match-center/${id}`);
};

// ==========================================
// CONEXÃO COM O BACKEND
// ==========================================
const fetchData = async () => {
  isLoading.value = true;
  try {
    const [resJogos, resStreaks] = await Promise.all([
      axios.get('http://localhost:8000/api/v1/matches/today'),
      axios.get('http://localhost:8000/api/v1/quant/top-streaks')
    ]);
    
    jogos.value = resJogos.data;
    streaks.value = resStreaks.data;
  } catch (error) {
    console.error("Erro ao carregar Sidebar Tracker:", error);
  } finally {
    isLoading.value = false;
  }
};

onMounted(fetchData);
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 3px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
</style>