<template>
  <div data-theme="institutional-dark" class="app-master-wrapper h-screen w-screen overflow-hidden m-0 p-0 absolute inset-0 font-sans">
    
    <div class="absolute inset-0 bg-[#060a12] z-0 overflow-hidden">
      <div class="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-[#10B981] rounded-full mix-blend-screen filter blur-[150px] opacity-10 animate-blob"></div>
      <div class="absolute top-[20%] right-[-10%] w-[50%] h-[50%] bg-[#3B82F6] rounded-full mix-blend-screen filter blur-[150px] opacity-10 animate-blob animation-delay-2000"></div>
      <div class="absolute bottom-[-20%] left-[20%] w-[50%] h-[50%] bg-[#a855f7] rounded-full mix-blend-screen filter blur-[150px] opacity-10 animate-blob animation-delay-4000"></div>
      
      <div class="absolute inset-0 bg-matrix-grid opacity-[0.03] pointer-events-none"></div>
      
      <div class="data-flow-container absolute inset-0 opacity-20">
        <div class="data-particle" v-for="i in 15" :key="`dp-${i}`" :style="getParticleStyle(i)"></div>
      </div>
      
      <div class="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,#060a12_100%)] opacity-80 pointer-events-none"></div>
    </div>
    
    <ViewLogin v-if="!usuarioLogado" @do-login="fazerLogin" class="relative z-20" />

    <div v-else class="app-master-layout h-full w-full flex overflow-hidden relative z-10">
    
      <AppSidebar 
        :aba-ativa="abaAtiva"
        @update:aba-ativa="mudarAba"
        @openSearch="toggleCommandPalette"
        @logout="fazerLogout"
      />

      <main class="flex-1 w-full h-full flex flex-col relative overflow-hidden transition-all duration-500 pt-[60px]" :class="{ 'pr-[340px]': !watchlistCollapsed && !isMobile }">
        
        <div class="w-full bg-black/40 backdrop-blur-md border-b border-white/5 overflow-hidden flex items-center h-8 shrink-0 relative z-40 shadow-[0_4px_30px_rgba(0,0,0,0.5)]">
          <div class="absolute bottom-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-[#10B981]/20 to-transparent"></div>
          
          <div class="bg-gradient-to-r from-[#060a12] to-[#0f1523] text-white text-[9px] font-bold uppercase tracking-[0.2em] px-4 h-full flex items-center shrink-0 z-20 border-r border-white/5 shadow-[10px_0_20px_rgba(0,0,0,0.8)]">
            <Radio :size="10" class="mr-2 text-[#10B981] animate-pulse" /> Live Feed
          </div>
          
          <div class="flex-1 overflow-hidden relative flex items-center h-full mask-edges z-10">
            <div class="animate-marquee whitespace-nowrap text-[10px] font-mono text-gray-400 flex items-center gap-16">
              <span v-for="(alert, index) in liveAlerts" :key="index" v-html="formatAlert(alert)" class="hover:text-white transition-colors cursor-default"></span>
              <span v-if="liveAlerts.length === 0" class="text-gray-500">Monitorando assimetrias de mercado na infraestrutura S-Tier...</span>
            </div>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto custom-scrollbar p-6 pb-32 relative z-10 w-full h-full scroll-smooth">
          <transition name="fade-scale" mode="out-in">
            <template v-if="abaAtiva === 'radar'"><ViewRadar class="w-full h-full min-h-full" /></template>
            <template v-else-if="abaAtiva === 'match-center'"><ViewMatchCenter class="w-full h-full min-h-full" /></template>
            <template v-else-if="abaAtiva === 'banca'"><ViewGestaoFundo class="w-full h-full min-h-full" /></template>
            <template v-else-if="abaAtiva === 'backtest'"><ViewBacktestEngine class="w-full h-full min-h-full" /></template>
            <template v-else-if="abaAtiva === 'sentimento'"><ViewHypeSentimento class="w-full h-full min-h-full" /></template>
            <template v-else-if="abaAtiva === 'config'"><ViewConfig class="w-full h-full min-h-full" /></template>
          </transition>
        </div>

        <div class="absolute bottom-8 right-8 z-[90] flex flex-col items-end gap-4">
          <transition name="slide-up">
            <div v-show="ticketAberto" class="w-[360px] shadow-[0_30px_60px_rgba(0,0,0,0.9)] origin-bottom-right rounded-2xl overflow-hidden border border-white/10 bg-[#0b0f19]/95 backdrop-blur-3xl">
              <WidgetSmartTicket />
            </div>
          </transition>
          
          <button @click="ticketAberto = !ticketAberto" class="w-12 h-12 rounded-full flex items-center justify-center transition-all duration-500 relative group bg-black/40 backdrop-blur-xl border border-white/10 text-gray-400 hover:text-white shadow-[0_10px_30px_rgba(0,0,0,0.5)] hover:border-[#10B981]/50 hover:shadow-[0_0_20px_rgba(16,185,129,0.2)] hover:-translate-y-1">
            <X v-if="ticketAberto" :size="20" class="relative z-10 transition-transform duration-300 rotate-90 group-hover:rotate-0" />
            <Receipt v-else :size="20" class="relative z-10 transition-transform duration-300 group-hover:scale-110" />
          </button>
        </div>
      </main>

      <aside class="fixed right-0 top-[60px] h-[calc(100vh-60px)] bg-gradient-to-b from-[#060a12]/95 to-[#0f1523]/95 backdrop-blur-2xl border-l border-white/5 z-40 transition-all duration-500 flex flex-col shadow-[-30px_0_60px_rgba(0,0,0,0.8)]" 
             :class="watchlistCollapsed ? 'translate-x-full w-[340px]' : 'translate-x-0 w-[340px]'">
        
        <div class="p-5 border-b border-white/5 flex items-center justify-between bg-black/20 shrink-0 relative overflow-hidden">
           <div class="absolute -right-10 -top-10 w-32 h-32 bg-[#10B981]/10 rounded-full blur-[40px] pointer-events-none"></div>
           <div class="flex items-center gap-3 relative z-10">
              <div class="w-8 h-8 rounded-xl bg-[#10B981]/10 border border-[#10B981]/30 flex items-center justify-center shadow-[0_0_15px_rgba(16,185,129,0.1)]">
                <div class="w-1.5 h-1.5 bg-[#10B981] rounded-full animate-pulse shadow-[0_0_8px_#10B981]"></div>
              </div>
              <div class="flex flex-col">
                <span class="text-xs uppercase font-bold text-white tracking-[0.2em] font-mono drop-shadow-md">Watchlist</span>
                <span class="text-[8px] text-gray-500 uppercase tracking-widest mt-0.5">Radar e Streaks</span>
              </div>
           </div>
        </div>

        <div class="flex-1 overflow-y-auto custom-scrollbar p-5 flex flex-col gap-4">
          <div class="bg-black/20 border border-white/5 rounded-2xl flex-1 flex flex-col overflow-hidden shadow-inner relative">
             <WidgetLateralDireito class="w-full h-full" />
          </div>
        </div>
      </aside>

      <button @click="watchlistCollapsed = !watchlistCollapsed" 
              class="fixed right-0 top-1/2 -translate-y-1/2 w-5 h-24 bg-black/40 backdrop-blur-md border border-r-0 border-white/10 rounded-l-xl flex items-center justify-center z-50 text-gray-500 hover:text-white hover:bg-black/80 hover:w-8 hover:border-[#10B981]/50 transition-all duration-300 shadow-[-10px_0_30px_rgba(0,0,0,0.5)] hidden xl:flex group">
        <ChevronLeft v-if="watchlistCollapsed" size="14" class="group-hover:scale-125 transition-transform" />
        <ChevronRight v-else size="14" class="group-hover:scale-125 transition-transform" />
      </button>

      <transition name="fade-backdrop">
        <div v-if="isCommandOpen" class="fixed inset-0 z-[9999] bg-black/60 backdrop-blur-[8px] flex items-start justify-center pt-[15vh]" @click.self="toggleCommandPalette">
          <div class="w-full max-w-2xl mx-4 bg-[#0b0f19]/90 backdrop-blur-3xl border border-white/10 rounded-2xl shadow-[0_40px_100px_rgba(0,0,0,0.9)] overflow-hidden scale-up-center relative">
            <div class="absolute inset-0 bg-gradient-to-b from-[#10B981]/5 to-transparent pointer-events-none"></div>
            
            <div class="flex items-center p-5 border-b border-white/10 bg-black/40 relative z-10">
              <Search :size="22" class="text-[#10B981] mr-4" />
              <input type="text" ref="searchInput" class="bg-transparent border-none text-white text-lg w-full focus:outline-none placeholder-gray-600 font-mono" placeholder="Comando global..." />
              <span class="text-[9px] text-gray-400 font-mono bg-white/5 px-2 py-1 rounded-md ml-3 border border-white/10 uppercase font-bold tracking-widest shadow-inner">ESC</span>
            </div>
            
            <div class="p-3 relative z-10 bg-[#121927]/50">
              <div class="text-[9px] text-gray-500 uppercase tracking-widest p-2 font-bold mb-1">Ações Rápidas</div>
              <div class="p-4 hover:bg-white/[0.04] rounded-xl cursor-pointer flex items-center gap-4 text-gray-300 transition-all hover:translate-x-1 group" @click="mudarAba('match-center'); isCommandOpen = false;">
                <div class="bg-black/50 p-2 rounded-lg border border-white/5 group-hover:border-[#10B981]/30 transition-colors"><LayoutDashboard :size="16" class="text-[#10B981]"/></div>
                <span class="font-mono text-sm">Ir para Match Center</span>
              </div>
              <div class="p-4 hover:bg-white/[0.04] rounded-xl cursor-pointer flex items-center gap-4 text-gray-300 transition-all hover:translate-x-1 group" @click="mudarAba('sentimento'); isCommandOpen = false;">
                <div class="bg-black/50 p-2 rounded-lg border border-white/5 group-hover:border-yellow-500/30 transition-colors"><Zap :size="16" class="text-yellow-500"/></div>
                <span class="font-mono text-sm">Ver Steamers (Hype Engine)</span>
              </div>
            </div>
          </div>
        </div>
      </transition>

    </div>
  </div>
</template>

<script setup>
import { ref, reactive, provide, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import axios from 'axios';
import { io } from 'socket.io-client';
import { Search, LayoutDashboard, Zap, Radio, X, Receipt, ChevronLeft, ChevronRight } from 'lucide-vue-next'; 

import ViewLogin from './components/ViewLogin.vue';
import AppSidebar from './components/AppSidebar.vue'; 
import WidgetSmartTicket from './components/WidgetSmartTicket.vue';
import WidgetLateralDireito from './components/WidgetLateralDireito.vue';

import ViewRadar from './components/ViewRadar.vue'; 
import ViewMatchCenter from './components/ViewMatchCenter.vue'; 
import ViewGestaoFundo from './components/ViewGestaoFundo.vue';
import ViewHypeSentimento from './components/ViewHypeSentimento.vue';
import ViewBacktestEngine from './components/ViewBacktestEngine.vue';
import ViewConfig from './components/ViewConfig.vue';

const rawApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_BASE_URL = rawApiUrl.endsWith('/api/v1') ? rawApiUrl : `${rawApiUrl.replace(/\/$/, '')}/api/v1`;
const GATEWAY_URL = (import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8000').replace(/\/$/, '');

const globalState = reactive({ activeMatch: null, uiMode: 'REAL' });
const usuarioLogado = ref(null);
const ticketAberto = ref(false);
const abaAtiva = ref('radar');
const isCommandOpen = ref(false);
const searchInput = ref(null);
const watchlistCollapsed = ref(false);
const isMobile = ref(false);
const liveAlerts = ref([]);
const systemStats = ref({ mappedGames: 0, evOpportunities: 0, dailyProfit: 0.0, currentBankroll: 0.0 });
let pollingInterval;

const router = useRouter();
const route = useRoute();

const abaTitulos = {
  'radar': 'Radar',
  'match-center': 'Match Center',
  'banca': 'Gestão de Fundo',
  'backtest': 'Backtest Engine',
  'sentimento': 'Hype Sentimento',
  'config': 'Configurações'
};

const atualizarTituloAba = (aba) => {
  const titulo = abaTitulos[aba] || 'Home';
  document.title = `BetGenius | ${titulo}`;
};

const mudarAba = (aba) => { 
  abaAtiva.value = aba; 
};

watch(abaAtiva, (newAba) => {
  atualizarTituloAba(newAba);
});

// Geração de estilos aleatórios mas controlados para as partículas
const getParticleStyle = (index) => {
  const left = Math.random() * 100;
  const duration = 15 + Math.random() * 20;
  const delay = Math.random() * 10;
  const size = 1 + Math.random() * 2;
  const opacity = 0.2 + Math.random() * 0.5;
  
  return {
    left: `${left}%`,
    width: `${size}px`,
    height: `${size * 10}px`,
    animationDuration: `${duration}s`,
    animationDelay: `${delay}s`,
    opacity: opacity
  };
};

const formatAlert = (alert) => {
  let colorClass = 'text-gray-400';
  let tag = '[SYSTEM]';
  if(alert.tipo && alert.tipo.includes('CRÍTICO')) { colorClass = 'text-red-400 drop-shadow-[0_0_5px_rgba(239,68,68,0.5)]'; tag = '⚠️ [CRÍTICO]'; }
  if(alert.tipo && alert.tipo.includes('ODDS DROP')) { colorClass = 'text-yellow-400 drop-shadow-[0_0_5px_rgba(250,204,21,0.5)]'; tag = '🔥 [STEAMER]'; }
  return `<strong class="${colorClass}">${tag}</strong> ${alert.time || 'Agora'}: <span class="text-gray-300 ml-1">${alert.texto}</span>`;
};

const restaurarSessao = async () => {
  const token = localStorage.getItem('betgenius_token');
  if (!token) return;
  try {
    const response = await axios.get(`${API_BASE_URL}/system/config`, { headers: { Authorization: `Bearer ${token}` } });
    if (response.data && response.data.user_config) {
      const conf = response.data.user_config;
      usuarioLogado.value = { name: conf.nome || "Gestor", role: conf.cargo || "Quant", avatar: conf.avatar || "" };
      globalState.uiMode = conf.modo || 'REAL';
    }
  } catch (error) {
    console.warn("Sessão inicial com Fallback.");
    usuarioLogado.value = { name: "Gestor", role: "Quant", avatar: "" };
  }
};

const fazerLogin = async (credenciais) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/auth/login`, { email: credenciais.email, senha: credenciais.senha });
    if (response.data.success) {
      localStorage.setItem('betgenius_token', response.data.token);
      usuarioLogado.value = { name: response.data.user.name, role: response.data.user.role, avatar: response.data.user.avatar };
      globalState.uiMode = response.data.user.modo;
      
      axios.post(`${API_BASE_URL}/system/sync-post-login`).catch(e => console.error("Sync Error", e));
    }
  } catch (error) {
    alert(`[Acesso Negado] Servidor offline ou inacessível.`);
  }
};

const fazerLogout = () => { 
  localStorage.removeItem('betgenius_token');
  usuarioLogado.value = null; 
};

const fetchLiveFeed = async () => {
  try { 
    const token = localStorage.getItem('betgenius_token');
    const res = await axios.get(`${API_BASE_URL}/system/alerts`, { headers: { Authorization: `Bearer ${token}` }}); 
    const formatted = [];
    (res.data || []).slice(0,5).forEach(a => {
      const time = a.criado_em ? new Date(a.criado_em).toLocaleTimeString('pt-BR', {hour: '2-digit', minute:'2-digit'}) : 'Agora';
      formatted.push({ tipo: a.tipo, time: time, texto: a.texto });
    });
    liveAlerts.value = formatted;
  } catch (e) { }
};

const fetchHeartbeat = async () => {
  try { const res = await axios.get(`${API_BASE_URL}/system/heartbeat`); systemStats.value = res.data; } catch (e) { }
};

const toggleCommandPalette = () => {
  isCommandOpen.value = !isCommandOpen.value;
  if (isCommandOpen.value) { nextTick(() => { searchInput.value?.focus(); }); }
};

const handleKeydown = (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); toggleCommandPalette(); }
  if (e.key === 'Escape' && isCommandOpen.value) isCommandOpen.value = false;
};

provide('globalState', globalState);
provide('openSmartTicket', () => { ticketAberto.value = true; });
provide('changeGlobalTab', mudarAba);

onMounted(() => { 
  isMobile.value = window.innerWidth < 1280;
  window.addEventListener('keydown', handleKeydown);
  window.addEventListener('resize', () => { isMobile.value = window.innerWidth < 1280; });
  
  atualizarTituloAba(abaAtiva.value);
  restaurarSessao();
  fetchHeartbeat(); 
  fetchLiveFeed();
  pollingInterval = setInterval(() => { fetchHeartbeat(); fetchLiveFeed(); }, 60000);

  try {
      const socket = io(GATEWAY_URL, { transports: ['websocket'] });
      socket.on('MARKET_SENTIMENT_ALERT', (payload) => {
          liveAlerts.value.unshift({ time: "Agora", tipo: payload.tipo || 'INFO', texto: payload.texto || 'Alerta HFT' });
      });
  } catch (err) {
      console.log('Websocket offline. Operando via Polling.');
  }
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown);
  window.removeEventListener('resize', () => { isMobile.value = window.innerWidth < 1280; });
  clearInterval(pollingInterval);
});
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap');

@font-face { font-family: 'Lemon Milk'; src: url('./assets/fonts/LemonMilk.otf') format('opentype'); font-weight: normal; }
@font-face { font-family: 'Poppins'; src: url('./assets/fonts/Poppins-Regular.ttf') format('truetype'); font-weight: 400; }
@font-face { font-family: 'Poppins'; src: url('./assets/fonts/Poppins-Bold.ttf') format('truetype'); font-weight: 700; }

*, *::before, *::after { box-sizing: border-box; }

:root {
  --bg-app: #060a12; 
  --bet-primary: #10B981;
  --text-main: #f8fafc;
  --text-muted: #94a3b8;
}

body { background: var(--bg-app); color: var(--text-main); font-family: 'Poppins', sans-serif; margin: 0; padding: 0; overflow-x: hidden; width: 100vw; height: 100vh; }

.font-mono { font-family: 'Lemon Milk', sans-serif; letter-spacing: 1px; }
.font-jersey { font-family: 'Bebas Neue', sans-serif; letter-spacing: 2px; }

/* ======== NOVO BACKGROUND DINÂMICO S-TIER ======== */
.bg-matrix-grid {
  background-image: linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
  linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  background-position: center center;
}

@keyframes blob {
  0% { transform: translate(0px, 0px) scale(1); }
  33% { transform: translate(30px, -50px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
  100% { transform: translate(0px, 0px) scale(1); }
}
.animate-blob { animation: blob 20s infinite alternate; }
.animation-delay-2000 { animation-delay: 2s; }
.animation-delay-4000 { animation-delay: 4s; }

.data-flow-container {
  overflow: hidden;
}

.data-particle {
  position: absolute;
  bottom: -10%;
  background: linear-gradient(to top, rgba(16,185,129,0), rgba(16,185,129,0.8), rgba(255,255,255,0.8));
  border-radius: 4px;
  animation: dataFlow linear infinite;
  box-shadow: 0 0 10px rgba(16,185,129,0.5);
}

@keyframes dataFlow {
  0% { transform: translateY(0); opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { transform: translateY(-120vh); opacity: 0; }
}
/* ================================================== */

/* Scrollbar S-Tier */
.custom-scrollbar::-webkit-scrollbar { width: 4px; height: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(16, 185, 129, 0.5); }

/* Transitions */
.fade-scale-enter-active, .fade-scale-leave-active { transition: opacity 0.4s ease, transform 0.4s ease; }
.fade-scale-enter-from, .fade-scale-leave-to { opacity: 0; transform: scale(0.98); }
.slide-up-enter-active, .slide-up-leave-active { transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
.slide-up-enter-from, .slide-up-leave-to { opacity: 0; transform: translateY(20px) scale(0.95); }
.scale-up-center { animation: scaleUp 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes scaleUp { from { opacity: 0; transform: scale(0.95) translateY(10px); } to { opacity: 1; transform: scale(1) translateY(0); } }
.fade-backdrop-enter-active, .fade-backdrop-leave-active { transition: opacity 0.3s ease; }
.fade-backdrop-enter-from, .fade-backdrop-leave-to { opacity: 0; }

@keyframes marquee { 0% { transform: translateX(100vw); } 100% { transform: translateX(-100%); } }
.animate-marquee { display: inline-block; animation: marquee 35s linear infinite; will-change: transform; padding-right: 50vw;}
.animate-marquee:hover { animation-play-state: paused; }
.mask-edges { mask-image: linear-gradient(to right, transparent, black 10%, black 90%, transparent); -webkit-mask-image: linear-gradient(to right, transparent, black 10%, black 90%, transparent); }

/* Globals */
.app-master-wrapper { display: flex; height: 100vh; width: 100vw; overflow: hidden; }
.app-master-layout { display: flex; width: 100%; height: 100%; overflow: hidden; }
</style>