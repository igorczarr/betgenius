<template>
  <div class="h-full flex flex-col bg-[#0b0f19] border-l border-white/5 relative">
    
    <div class="p-4 border-b border-white/5 shrink-0 bg-black/20 z-10 relative">
      <div class="flex p-1 rounded-lg bg-black/40 border border-white/10 shadow-inner">
        <button 
          @click="abaAtual = 'jogos'"
          class="flex-1 py-1.5 text-[11px] uppercase tracking-wider font-bold rounded transition-all duration-300"
          :class="abaAtual === 'jogos' ? 'bg-blue-500/20 text-blue-400 shadow-sm' : 'text-gray-500 hover:text-gray-300'"
        >
          <CalendarDays :size="14" class="inline mb-0.5 mr-1"/> Jogos do Dia
        </button>
        <button 
          @click="abaAtual = 'streaks'"
          class="flex-1 py-1.5 text-[11px] uppercase tracking-wider font-bold rounded transition-all duration-300"
          :class="abaAtual === 'streaks' ? 'bg-orange-500/20 text-orange-400 shadow-sm' : 'text-gray-500 hover:text-gray-300'"
        >
          <Flame :size="14" class="inline mb-0.5 mr-1"/> Streaks
        </button>
      </div>
      
      <div class="mt-3 relative h-[32px] overflow-hidden">
        <transition name="slide-fade">
          <select 
            v-if="abaAtual === 'jogos'" 
            v-model="filtroLiga" 
            class="absolute top-0 w-full bg-black/50 text-xs text-gray-300 border border-white/10 rounded px-3 py-1.5 outline-none focus:border-blue-500 transition-colors cursor-pointer"
          >
            <option value="ALL">Todas as Ligas</option>
            <option v-for="liga in ligasDisponiveis" :key="liga" :value="liga">{{ liga }}</option>
          </select>
          
          <select 
            v-else-if="abaAtual === 'streaks'" 
            v-model="filtroStreak" 
            class="absolute top-0 w-full bg-black/50 text-xs text-gray-300 border border-white/10 rounded px-3 py-1.5 outline-none focus:border-orange-500 transition-colors cursor-pointer"
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
        </transition>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto custom-scrollbar p-4 flex flex-col gap-3 relative">
      
      <template v-if="isLoading">
        <div v-for="i in 6" :key="'sk'+i" class="h-[72px] rounded-xl border border-white/5 bg-white/[0.02] animate-pulse"></div>
      </template>

      <transition-group v-else-if="abaAtual === 'jogos'" name="list" tag="div" class="flex flex-col gap-3">
        <div v-for="jogo in jogosFiltrados" :key="'j'+jogo.id" 
             @click="abrirMatchCenter(jogo)"
             class="p-3 rounded-xl border border-white/5 bg-[#121927] transition-all cursor-pointer group hover:border-blue-500/40 hover:bg-blue-500/10 hover:-translate-y-0.5 relative overflow-hidden shadow-sm hover:shadow-[0_5px_15px_rgba(59,130,246,0.15)]">
          
          <div class="absolute left-0 top-0 w-1 h-full bg-gradient-to-b from-blue-400 to-blue-600 opacity-0 group-hover:opacity-100 transition-opacity"></div>
          
          <div class="flex justify-between items-center mb-1.5">
            <span class="text-[9px] font-mono tracking-widest uppercase text-blue-400/80 group-hover:text-blue-400 transition-colors">
              {{ jogo.campeonato }}
            </span>
            <div class="flex items-center gap-2">
              <span v-if="jogo.status === 'IN_PROGRESS'" class="flex items-center gap-1 text-[9px] font-bold text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded animate-pulse"><div class="w-1.5 h-1.5 bg-red-500 rounded-full"></div> LIVE</span>
              <span class="text-[10px] font-mono text-gray-500">{{ formatTime(jogo.data) }}</span>
            </div>
          </div>
          
          <div class="font-bold text-sm text-white flex justify-between items-center pl-1">
            <span class="truncate pr-2 group-hover:text-white transition-colors">{{ jogo.casa }} <span class="text-gray-600 text-[10px] mx-1.5 font-normal">vs</span> {{ jogo.fora }}</span>
            <button class="w-6 h-6 rounded-full bg-white/5 flex items-center justify-center text-gray-500 group-hover:bg-blue-500 group-hover:text-white transition-all transform group-hover:rotate-90">
              <Plus :size="14" strokeWidth="3"/>
            </button>
          </div>
        </div>
        
        <div v-if="jogosFiltrados.length === 0" class="flex flex-col items-center justify-center h-full py-10 opacity-50">
          <CalendarDays size="32" class="text-gray-500 mb-3" />
          <span class="text-xs text-gray-400 font-mono uppercase tracking-widest text-center">Nenhum evento <br>na grade hoje.</span>
        </div>
      </transition-group>

      <transition-group v-else-if="abaAtual === 'streaks'" name="list" tag="div" class="flex flex-col gap-3">
        <div v-for="(streak, i) in streaksFiltradas" :key="'s'+i" 
             @click="abrirScreenerPopup(streak)"
             class="p-3.5 rounded-xl border border-white/5 bg-black/20 flex flex-col gap-2 transition-all duration-300 cursor-pointer group relative overflow-hidden shadow-sm hover:shadow-[0_8px_20px_rgba(249,115,22,0.15)] hover:-translate-y-0.5"
             :style="`border-left-color: ${streak.cor}40; border-left-width: 3px;`">
          
          <div class="absolute right-0 top-0 h-full w-24 bg-gradient-to-l from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" :style="`--tw-gradient-from: ${streak.cor}15;`"></div>
          
          <div class="flex justify-between items-start">
            <span class="text-[9px] font-mono tracking-widest uppercase py-0.5 px-2 rounded font-bold border transition-colors group-hover:bg-opacity-30"
                  :style="{ color: streak.cor, backgroundColor: streak.cor + '15', borderColor: streak.cor + '30' }">
              {{ streak.tipo }}
            </span>
            <div class="flex items-center gap-1.5">
               <span class="text-[9px] text-gray-500 font-mono">ODD</span>
               <span class="text-xs font-mono font-bold text-white bg-[#121927] px-2 py-0.5 rounded border border-white/10 group-hover:border-white/30 transition-colors">{{ streak.odd }}</span>
            </div>
          </div>
          
          <div class="font-bold text-[13px] text-white truncate mt-1">
            {{ streak.equipe }} <span class="text-gray-500 font-normal text-xs ml-1">vs {{ streak.adversario }}</span>
          </div>
          
          <div class="flex justify-between items-center mt-1.5">
             <div class="text-[10px] text-gray-400 font-mono flex items-center gap-1.5 bg-black/40 px-2.5 py-1 rounded w-fit border border-white/5">
                <TrendingUp :size="12" :color="streak.cor" /> <span class="text-white">{{ streak.jogos }}</span> JOGOS SEGUIDOS
             </div>
             <span class="text-[10px] font-mono font-bold px-2 py-1 rounded" :class="streak.ev > 0 ? 'text-[#10B981] bg-[#10B981]/10 border border-[#10B981]/20' : 'text-gray-400 border border-white/5 bg-white/5'">{{ streak.ev > 0 ? '+' : ''}}{{ streak.ev }}% EV</span>
          </div>
        </div>
        
        <div v-if="streaksFiltradas.length === 0" class="flex flex-col items-center justify-center h-full py-10 opacity-50">
          <Flame size="32" class="text-gray-500 mb-3" />
          <span class="text-xs text-gray-400 font-mono uppercase tracking-widest text-center">Nenhuma anomalia <br>detectada.</span>
        </div>
      </transition-group>

    </div>

    <transition name="modal-fade">
      <div v-if="streakScreenerOpen" class="fixed inset-0 z-[100] flex items-center justify-center px-4">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm transition-opacity" @click="streakScreenerOpen = false"></div>
        
        <div class="relative w-full max-w-md bg-gradient-to-br from-[#121927] to-[#0a0f16] border border-white/10 rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.8)] flex flex-col overflow-hidden transform transition-transform"
             :style="`border-top-color: ${streakAtiva?.cor}; border-top-width: 3px;`">
             
          <div class="absolute -right-20 -top-20 w-48 h-48 rounded-full blur-[80px] pointer-events-none opacity-20" :style="`background-color: ${streakAtiva?.cor}`"></div>

          <div class="flex justify-between items-center p-4 border-b border-white/5 relative z-10">
            <div class="flex items-center gap-3">
               <div class="w-8 h-8 rounded bg-white/5 flex items-center justify-center border border-white/10" :style="`color: ${streakAtiva?.cor}`">
                  <Activity size="16" />
               </div>
               <div class="flex flex-col">
                 <span class="text-[10px] font-mono uppercase font-bold tracking-widest" :style="`color: ${streakAtiva?.cor}`">Alpha Screener</span>
                 <span class="text-xs font-bold text-white">Auditoria Quantitativa</span>
               </div>
            </div>
            <button @click="streakScreenerOpen = false" class="text-gray-500 hover:text-white bg-black/40 p-2 rounded-lg transition-colors border border-white/5 hover:bg-white/10">
              <X size="16" />
            </button>
          </div>

          <div v-if="streakAtiva" class="flex flex-col gap-5 p-6 relative z-10 overflow-y-auto max-h-[70vh] custom-scrollbar">
            
            <div class="bg-black/30 border border-white/5 p-4 rounded-xl flex flex-col gap-1.5 text-center relative overflow-hidden shadow-inner">
               <span class="text-xs text-gray-400 font-mono">{{ streakAtiva.equipe }} vs {{ streakAtiva.adversario }}</span>
               <span class="text-2xl font-black text-white uppercase tracking-wider drop-shadow-md" :style="{ color: streakAtiva.cor }">{{ streakAtiva.tipo }}</span>
               <div class="mt-2 inline-flex items-center justify-center gap-2 bg-white/5 border border-white/10 w-fit mx-auto px-3 py-1 rounded-full">
                 <Flame size="12" :color="streakAtiva.cor" />
                 <span class="text-[10px] text-gray-300 font-mono uppercase tracking-widest font-bold">{{ streakAtiva.jogos }} Jogos Consecutivos</span>
               </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
               <div class="bg-black/30 border border-white/5 p-4 rounded-xl flex flex-col items-center justify-center">
                  <span class="text-[9px] text-gray-500 uppercase font-bold tracking-widest mb-1">Odd Mercado</span>
                  <span class="text-2xl font-mono text-white font-bold">{{ streakAtiva.odd }}</span>
               </div>
               <div class="border p-4 rounded-xl flex flex-col items-center justify-center relative overflow-hidden"
                    :style="`background-color: ${streakAtiva.cor}10; border-color: ${streakAtiva.cor}40; color: ${streakAtiva.cor}`">
                  <span class="text-[9px] uppercase font-bold tracking-widest relative z-10 mb-1">Fair Odd (Modelo)</span>
                  <span class="text-2xl font-mono font-bold relative z-10 drop-shadow-[0_0_8px_currentColor]">{{ streakAtiva.fair_odd }}</span>
               </div>
            </div>

            <div class="bg-black/30 border border-white/5 p-5 rounded-xl flex flex-col gap-4">
               <span class="text-[10px] text-gray-400 uppercase font-bold tracking-widest flex items-center gap-2 border-b border-white/5 pb-2">
                 <BarChart2 size="14" class="text-blue-400"/> Métricas Avançadas (Últimos 5)
               </span>
               
               <div class="flex flex-col gap-1.5">
                 <div class="flex justify-between text-[10px] font-mono text-gray-400">
                    <span>Expected Goals (xG) Gerado</span>
                    <span class="font-bold text-white">{{ streakAtiva.xg_gerado }}</span>
                 </div>
                 <div class="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden shadow-inner border border-white/5">
                    <div class="h-full bg-blue-500 transition-all duration-1000" :style="`width: ${(streakAtiva.xg_gerado / 3) * 100}%`"></div>
                 </div>
               </div>

               <div class="flex flex-col gap-1.5">
                 <div class="flex justify-between text-[10px] font-mono text-gray-400">
                    <span>Expected Goals (xGA) Sofrido</span>
                    <span class="font-bold text-white">{{ streakAtiva.xg_sofrido }}</span>
                 </div>
                 <div class="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden shadow-inner border border-white/5">
                    <div class="h-full bg-red-500 transition-all duration-1000" :style="`width: ${(streakAtiva.xg_sofrido / 3) * 100}%`"></div>
                 </div>
               </div>

               <div class="flex flex-col gap-1.5">
                 <div class="flex justify-between text-[10px] font-mono text-gray-400">
                    <span>Posse no Terço Final</span>
                    <span class="font-bold text-white">{{ streakAtiva.posse_final_pct }}%</span>
                 </div>
                 <div class="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden shadow-inner border border-white/5">
                    <div class="h-full bg-purple-500 transition-all duration-1000" :style="`width: ${streakAtiva.posse_final_pct}%`"></div>
                 </div>
               </div>
            </div>

            <div class="mt-2 flex flex-col gap-3">
               <div class="flex items-start gap-3 bg-[#0a0f16] p-4 rounded-xl border border-white/10 shadow-inner">
                  <Cpu size="16" class="text-bet-primary mt-0.5 shrink-0"/>
                  <span class="text-[11px] text-gray-300 font-mono leading-relaxed">{{ streakAtiva.insight }}</span>
               </div>
               
               <button v-if="parseFloat(streakAtiva.ev) > 0" class="w-full py-4 bg-[#10B981] text-black font-bold uppercase tracking-widest text-[11px] rounded-xl flex items-center justify-center gap-2 hover:bg-white transition-all hover:scale-[1.02] shadow-[0_5px_20px_rgba(16,185,129,0.3)]">
                  <Target size="16" strokeWidth="3"/> Aprovar Ordem (+{{streakAtiva.ev}}% EV)
               </button>
               <button v-else class="w-full py-4 bg-red-500/10 text-red-400 border border-red-500/30 font-bold uppercase tracking-widest text-[11px] rounded-xl flex items-center justify-center gap-2 cursor-not-allowed">
                  <X size="16" strokeWidth="3"/> Sem Valor (+EV Inexistente)
               </button>
            </div>

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
// CONFIG E ESTADO GLOBAL (PORTA 8000 HFT)
// ==========================================
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const globalState = inject('globalState');
// Injeta a função para mudar de aba no parent (App.vue)
const changeGlobalTab = inject('changeGlobalTab', () => { console.warn("changeGlobalTab não injetado") });

const abaAtual = ref('jogos');
const isLoading = ref(true);

const jogos = ref([]);
const streaks = ref([]);

const filtroLiga = ref('ALL');
const filtroStreak = ref('ALL');

// Estado do Modal (Popup S-Tier)
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
  if(globalState) {
     globalState.activeMatch = jogo;
  }
  changeGlobalTab('match-center');
};

const abrirScreenerPopup = (streak) => {
  streakAtiva.value = streak;
  streakScreenerOpen.value = true;
};

// ==========================================
// CONEXÃO COM O BACKEND 
// ==========================================
const fetchData = async () => {
  isLoading.value = true;
  try {
    const token = localStorage.getItem('betgenius_token');
    const opts = { headers: { Authorization: `Bearer ${token}` } };

    // Bate nas rotas reais da porta 8000 criadas no main.py
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
/* Scrollbar Stealth */
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.2); }

/* Animações de Transição S-Tier */
.list-enter-active,
.list-leave-active {
  transition: all 0.4s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(15px);
}

.slide-fade-enter-active { transition: all 0.3s ease-out; }
.slide-fade-leave-active { transition: all 0.2s cubic-bezier(1, 0.5, 0.8, 1); }
.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(-10px);
  opacity: 0;
}

/* Modal Popup Animation */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
.modal-fade-enter-active .transform {
  animation: modal-pop 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.modal-fade-leave-active .transform {
  animation: modal-pop 0.3s cubic-bezier(0.16, 1, 0.3, 1) reverse forwards;
}

@keyframes modal-pop {
  0% { transform: scale(0.95) translateY(20px); opacity: 0; }
  100% { transform: scale(1) translateY(0); opacity: 1; }
}
</style>