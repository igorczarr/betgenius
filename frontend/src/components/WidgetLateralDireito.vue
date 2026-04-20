<template>
  <div class="h-full flex flex-col bg-[#0b0f19] border-l border-white/5 relative">
    
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
  <option value="GOLS_MARCADOS">Gols Marcados (+0.5)</option>
  <option value="GOLS_SOFRIDOS">Gols Sofridos Defesa</option>
  <option value="VITORIAS">Apenas Vitórias</option>
  <option value="DERROTAS">Apenas Derrotas</option>
  <option value="JEJUM">Jejum (Sem Vencer)</option>
  <option value="INVICTO">Invicto (Sem Perder)</option>
  <option value="AMBOS_MARCAM">Ambos Marcam (BTTS)</option>
  <option value="VITORIA_ESMAGADORA">Amasse (Vence por 2+)</option>
</select>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto custom-scrollbar p-4 flex flex-col gap-3 relative">
      
      <template v-if="isLoading">
        <div v-for="i in 5" :key="'sk'+i" class="h-16 rounded-xl border border-white/5 bg-white/[0.02] animate-pulse"></div>
      </template>

      <template v-else-if="abaAtual === 'jogos'">
        <div v-for="jogo in jogosFiltrados" :key="'j'+jogo.id" 
             @click="abrirMatchCenter(jogo)"
             class="p-3 rounded-xl border border-white/5 bg-white/[0.02] transition-all cursor-pointer group hover:border-blue-500/50 hover:bg-blue-500/5 relative overflow-hidden">
          <div class="absolute left-0 top-0 w-1 h-full bg-blue-500 opacity-0 group-hover:opacity-100 transition-opacity"></div>
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
             @click="abrirScreenerPopup(streak)"
             class="p-3 rounded-xl border border-white/5 bg-black/20 flex flex-col gap-2 hover:border-orange-500/30 hover:bg-white/5 transition-colors cursor-pointer group relative overflow-hidden">
          <div class="absolute right-0 top-0 h-full w-16 bg-gradient-to-l from-orange-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
          
          <div class="flex justify-between items-start">
            <span class="text-[9px] font-mono tracking-widest uppercase py-0.5 px-2 rounded font-bold border"
                  :style="{ color: streak.cor, backgroundColor: streak.cor + '15', borderColor: streak.cor + '30' }">
              {{ streak.tipo }}
            </span>
            <div class="flex items-center gap-1.5">
               <span class="text-[9px] text-gray-400 font-mono">ODD</span>
               <span class="text-xs font-mono font-bold text-white bg-[#121927] px-2 py-0.5 rounded border border-white/10">{{ streak.odd }}</span>
            </div>
          </div>
          
          <div class="font-bold text-sm text-white truncate mt-1">
            {{ streak.equipe }} <span class="text-gray-500 font-normal text-xs ml-1">vs {{ streak.adversario }}</span>
          </div>
          
          <div class="flex justify-between items-center mt-1">
             <div class="text-[10px] text-gray-400 font-mono flex items-center gap-1.5 bg-black/40 px-2 py-1 rounded w-fit">
                <TrendingUp :size="12" :color="streak.cor" /> {{ streak.jogos }} JOGOS SEGUIDOS
             </div>
             <span class="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded" :class="streak.ev > 0 ? 'text-[#10B981] bg-[#10B981]/10 border border-[#10B981]/20' : 'text-gray-400 border border-white/5'">{{ streak.ev > 0 ? '+' : ''}}{{ streak.ev }}% EV</span>
          </div>
        </div>
        <div v-if="streaksFiltradas.length === 0" class="text-center text-xs text-gray-500 py-10 font-mono uppercase tracking-widest">Nenhum streak ativo.</div>
      </template>

    </div>

    <transition name="fade">
      <div v-if="streakScreenerOpen" class="absolute inset-0 z-50 bg-[#0b0f19]/95 backdrop-blur-md flex flex-col p-4 border-l border-orange-500/50">
         <div class="flex justify-between items-center mb-4 pb-3 border-b border-white/10">
            <div class="flex items-center gap-2">
               <div class="w-8 h-8 rounded bg-orange-500/10 flex items-center justify-center border border-orange-500/30">
                  <Activity size="16" class="text-orange-500" />
               </div>
               <div class="flex flex-col">
                 <span class="text-[10px] text-orange-500 font-mono uppercase font-bold tracking-widest">Alpha Screener</span>
                 <span class="text-xs font-bold text-white">Validação de Streak</span>
               </div>
            </div>
            <button @click="streakScreenerOpen = false" class="text-gray-500 hover:text-white bg-black/40 p-1.5 rounded transition-colors"><X size="16" /></button>
         </div>

         <div v-if="streakAtiva" class="flex flex-col gap-4 overflow-y-auto custom-scrollbar flex-1 pb-4">
            
            <div class="bg-black/30 border border-white/5 p-3 rounded-xl flex flex-col gap-1 text-center relative overflow-hidden">
               <span class="text-xs text-gray-400 font-mono">{{ streakAtiva.equipe }} vs {{ streakAtiva.adversario }}</span>
               <span class="text-lg font-bold text-white uppercase tracking-wider" :style="{ color: streakAtiva.cor }">{{ streakAtiva.tipo }}</span>
               <span class="text-[10px] text-gray-500 font-mono uppercase tracking-widest">Frequência: {{ streakAtiva.jogos }} Jogos Consecutivos</span>
            </div>

            <div class="grid grid-cols-2 gap-3">
               <div class="bg-black/30 border border-white/5 p-3 rounded-lg flex flex-col">
                  <span class="text-[9px] text-gray-500 uppercase font-bold tracking-widest">Odd Casa (Mercado)</span>
                  <span class="text-xl font-mono text-white mt-1">{{ streakAtiva.odd }}</span>
               </div>
               <div class="bg-[#10B981]/10 border border-[#10B981]/30 p-3 rounded-lg flex flex-col relative overflow-hidden">
                  <span class="text-[9px] text-[#10B981] uppercase font-bold tracking-widest relative z-10">Fair Odd (Modelo)</span>
                  <span class="text-xl font-mono text-[#10B981] mt-1 font-bold relative z-10">{{ streakAtiva.fair_odd }}</span>
               </div>
            </div>

            <div class="bg-black/30 border border-white/5 p-4 rounded-xl flex flex-col gap-3">
               <span class="text-[10px] text-gray-400 uppercase font-bold tracking-widest flex items-center gap-1.5 border-b border-white/5 pb-2">
                 <BarChart2 size="12"/> Métricas Avançadas (Últimos 5)
               </span>
               
               <div class="flex flex-col gap-1">
                 <div class="flex justify-between text-[10px] font-mono text-gray-300">
                    <span>Expected Goals (xG) Gerado</span>
                    <span class="font-bold text-white">{{ streakAtiva.xg_gerado }}</span>
                 </div>
                 <div class="w-full h-1.5 bg-gray-800 rounded flex overflow-hidden">
                    <div class="h-full bg-blue-500" :style="`width: ${(streakAtiva.xg_gerado / 3) * 100}%`"></div>
                 </div>
               </div>

               <div class="flex flex-col gap-1">
                 <div class="flex justify-between text-[10px] font-mono text-gray-300">
                    <span>Expected Goals (xGA) Sofrido</span>
                    <span class="font-bold text-white">{{ streakAtiva.xg_sofrido }}</span>
                 </div>
                 <div class="w-full h-1.5 bg-gray-800 rounded flex overflow-hidden">
                    <div class="h-full bg-red-500" :style="`width: ${(streakAtiva.xg_sofrido / 3) * 100}%`"></div>
                 </div>
               </div>

               <div class="flex flex-col gap-1 mt-1">
                 <div class="flex justify-between text-[10px] font-mono text-gray-300">
                    <span>Posse no Terço Final</span>
                    <span class="font-bold text-white">{{ streakAtiva.posse_final_pct }}%</span>
                 </div>
                 <div class="w-full h-1.5 bg-gray-800 rounded flex overflow-hidden">
                    <div class="h-full bg-purple-500" :style="`width: ${streakAtiva.posse_final_pct}%`"></div>
                 </div>
               </div>
            </div>

            <div class="mt-auto pt-2 flex flex-col gap-3">
               <div class="flex items-start gap-2 bg-black/50 p-3 rounded border border-gray-800 shadow-inner">
                  <Cpu size="14" class="text-bet-primary mt-0.5 shrink-0"/>
                  <span class="text-[10px] text-gray-300 font-mono leading-relaxed">{{ streakAtiva.insight }}</span>
               </div>
               
               <button v-if="streakAtiva.ev > 0" class="w-full py-3 bg-[#10B981] text-black font-bold uppercase tracking-widest text-[10px] rounded-lg flex items-center justify-center gap-2 hover:bg-white transition-colors shadow-[0_0_15px_rgba(16,185,129,0.3)]">
                  <Target size="14" strokeWidth="3"/> Aprovar Entrada (+{{streakAtiva.ev}}% EV)
               </button>
               <button v-else class="w-full py-3 bg-red-500/10 text-red-500 border border-red-500/30 font-bold uppercase tracking-widest text-[10px] rounded-lg flex items-center justify-center gap-2 cursor-not-allowed">
                  <X size="14" strokeWidth="3"/> Pular (Sem Valor Matemático)
               </button>
            </div>

         </div>
      </div>
    </transition>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue';
import { CalendarDays, Flame, Plus, TrendingUp, X, Activity, BarChart2, Cpu, Target } from 'lucide-vue-next';
import axios from 'axios';

// ==========================================
// CONFIG E ESTADO GLOBAL
// ==========================================
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const globalState = inject('globalState');
// Injeta a função para mudar de aba no parent (App.vue), se disponibilizado via Provide
const changeGlobalTab = inject('changeGlobalTab', () => { console.warn("changeGlobalTab não injetado pelo App.vue") });

const abaAtual = ref('jogos');
const isLoading = ref(true);

const jogos = ref([]);
const streaks = ref([]);

const filtroLiga = ref('ALL');
const filtroStreak = ref('ALL');

// Estado do Popup
const streakScreenerOpen = ref(false);
const streakAtiva = ref(null);

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
  return streaks.value.filter(s => s.tipo.toUpperCase().includes(filtroStreak.value));
});

const formatTime = (isoString) => {
  if (!isoString) return '00:00';
  const date = new Date(isoString);
  return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
};

// ==========================================
// AÇÕES DE NAVEGAÇÃO E UX
// ==========================================
const abrirMatchCenter = (jogo) => {
  // 1. Seta o jogo globalmente
  if(globalState) {
     globalState.activeMatch = jogo;
  }
  // 2. Manda a Placa-mãe trocar para a Aba 'match-center'
  changeGlobalTab('match-center');
};

const abrirScreenerPopup = (streak) => {
  streakAtiva.value = streak;
  streakScreenerOpen.value = true;
};

// ==========================================
// CONEXÃO COM O BACKEND (S-TIER)
// ==========================================
const fetchData = async () => {
  isLoading.value = true;
  try {
    const token = localStorage.getItem('betgenius_token');
    const opts = { headers: { Authorization: `Bearer ${token}` } };

    const [resJogos, resStreaks] = await Promise.all([
      axios.get(`${API_BASE_URL}/api/v1/matches/today`, opts).catch(()=>({data:[]})),
      axios.get(`${API_BASE_URL}/api/v1/quant/top-streaks`, opts).catch(()=>({data:[]}))
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