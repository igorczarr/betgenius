<template>
  <div data-theme="institutional-dark" class="app-master-wrapper h-screen w-screen overflow-hidden bg-[#0b0f19] m-0 p-0 absolute inset-0">
    
    <div class="ambient-bg">
      <div class="ambient-orb ambient-orb-1"></div>
      <div class="ambient-orb ambient-orb-2"></div>
    </div>
    
    <ViewLogin v-if="!usuarioLogado" @do-login="fazerLogin" />

    <div v-else class="app-master-layout h-full w-full flex overflow-hidden relative z-10">
    
      <AppSidebar 
        :aba-ativa="abaAtiva"
        @update:aba-ativa="mudarAba"
        @openSearch="toggleCommandPalette"
        @logout="fazerLogout"
      />

      <main class="flex-1 w-full h-full flex flex-col relative overflow-hidden bg-radial-gradient transition-all duration-300 pt-[60px]" :class="{ 'pr-[340px]': !watchlistCollapsed && !isMobile }">
        
        <div class="w-full bg-black/60 border-b border-white/5 overflow-hidden flex items-center h-8 shrink-0 relative z-40 shadow-sm">
          <div class="bg-[#121927] text-white text-[9px] font-bold uppercase tracking-widest px-3 h-full flex items-center shrink-0 z-10 border-r border-white/10 shadow-[5px_0_15px_rgba(0,0,0,0.8)]">
            <Radio :size="10" class="mr-1.5 text-red-500 animate-pulse" /> Live Feed
          </div>
          <div class="flex-1 overflow-hidden relative flex items-center h-full mask-edges">
            <div class="animate-marquee whitespace-nowrap text-[10px] font-mono text-gray-400 flex items-center gap-12">
              <span v-for="(alert, index) in liveAlerts" :key="index" v-html="formatAlert(alert)"></span>
              <span v-if="liveAlerts.length === 0">Monitorando assimetrias de mercado na infraestrutura S-Tier...</span>
            </div>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto custom-scrollbar p-6 relative z-10 w-full h-full">
          <transition name="fade" mode="out-in">
            <template v-if="abaAtiva === 'radar'"><ViewRadar class="w-full h-full min-h-full" /></template>
            <template v-else-if="abaAtiva === 'match-center'"><ViewMatchCenter class="w-full h-full min-h-full" /></template>
            <template v-else-if="abaAtiva === 'banca'"><ViewGestaoFundo class="w-full h-full min-h-full" /></template>
            <template v-else-if="abaAtiva === 'backtest'"><ViewBacktestEngine class="w-full h-full min-h-full" /></template>
            <template v-else-if="abaAtiva === 'sentimento'"><ViewHypeSentimento class="w-full h-full min-h-full" /></template>
            <template v-else-if="abaAtiva === 'config'"><ViewConfig class="w-full h-full min-h-full" /></template>
          </transition>
        </div>

        <div class="absolute bottom-[100px] right-8 z-[90]">
          <transition name="slide-up">
            <div v-show="ticketAberto" class="mb-4 w-[360px] shadow-[0_30px_60px_rgba(0,0,0,0.8)] origin-bottom-right rounded-2xl overflow-hidden border border-gray-700/50">
              <WidgetSmartTicket />
            </div>
          </transition>
          
          <button @click="ticketAberto = !ticketAberto" class="fab-btn ml-auto w-14 h-14 rounded-full flex items-center justify-center transition-all duration-300 relative group border border-white/10 shadow-[0_10px_30px_rgba(0,0,0,0.8)]">
            <span class="absolute inset-0 rounded-full animate-ping opacity-20 bg-bet-primary group-hover:opacity-40"></span>
            <X v-if="ticketAberto" :size="24" class="text-black relative z-10" />
            <Receipt v-else :size="24" class="text-black relative z-10" />
          </button>
        </div>
      </main>

      <aside class="fixed right-0 top-[60px] h-[calc(100vh-60px)] bg-gradient-to-b from-[#121927]/95 to-[#0f1523]/95 backdrop-blur-xl border-l border-white/10 z-40 transition-all duration-300 flex flex-col shadow-[-20px_0_50px_rgba(0,0,0,0.6)]" 
             :class="watchlistCollapsed ? 'translate-x-full w-[340px]' : 'translate-x-0 w-[340px]'">
        
        <div class="p-5 border-b border-white/5 flex items-center justify-between bg-black/20 shadow-md shrink-0 relative overflow-hidden">
           <div class="absolute -right-10 -top-10 w-32 h-32 bg-[#10B981]/10 rounded-full blur-[30px] pointer-events-none"></div>
           <div class="flex items-center gap-3 relative z-10">
              <div class="w-8 h-8 rounded-xl bg-[#10B981]/10 border border-[#10B981]/30 flex items-center justify-center shadow-[0_0_10px_rgba(16,185,129,0.15)]">
                <div class="w-2 h-2 bg-[#10B981] rounded-full animate-pulse shadow-[0_0_8px_#10B981]"></div>
              </div>
              <div class="flex flex-col">
                <span class="text-xs uppercase font-bold text-white tracking-widest font-mono drop-shadow-md">Watchlist</span>
                <span class="text-[8px] text-gray-400 uppercase tracking-widest mt-0.5">Radar e Streaks</span>
              </div>
           </div>
        </div>

        <div class="flex-1 overflow-y-auto custom-scrollbar p-5 flex flex-col gap-4">
          <div class="bg-black/30 border border-white/5 rounded-2xl flex-1 flex flex-col overflow-hidden shadow-inner relative">
             <WidgetLateralDireito class="w-full h-full" />
          </div>
        </div>
      </aside>

      <button @click="watchlistCollapsed = !watchlistCollapsed" 
              class="fixed right-0 top-1/2 -translate-y-1/2 w-6 h-20 bg-gradient-to-b from-[#121927] to-[#0f1523] border border-r-0 border-white/10 rounded-l-xl flex items-center justify-center z-50 text-gray-500 hover:text-white hover:bg-black transition-all shadow-[-8px_0_20px_rgba(0,0,0,0.5)] hidden xl:flex hover:w-8 group">
        <ChevronLeft v-if="watchlistCollapsed" size="16" class="group-hover:scale-110 transition-transform" />
        <ChevronRight v-else size="16" class="group-hover:scale-110 transition-transform" />
      </button>

      <transition name="fade">
        <div v-if="isCommandOpen" class="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-md flex items-start justify-center pt-[15vh]" @click.self="toggleCommandPalette">
          <div class="w-full max-w-2xl mx-4 bg-[#121927] border border-white/10 rounded-2xl shadow-[0_30px_60px_rgba(0,0,0,0.9)] overflow-hidden scale-up-center">
            <div class="flex items-center p-5 border-b border-white/10 bg-black/20">
              <Search :size="22" class="text-bet-primary mr-4" />
              <input type="text" ref="searchInput" class="bg-transparent border-none text-white text-lg w-full focus:outline-none placeholder-gray-500 font-mono" placeholder="Comando global..." />
              <span class="text-[10px] text-gray-400 font-mono bg-white/5 px-2 py-1 rounded ml-3 border border-white/10">ESC</span>
            </div>
            <div class="p-2">
              <div class="text-[10px] text-gray-500 uppercase tracking-widest p-2 font-bold">Ações Rápidas</div>
              <div class="p-3 hover:bg-white/5 rounded-lg cursor-pointer flex items-center gap-3 text-gray-300 transition-colors" @click="mudarAba('match-center'); isCommandOpen = false;">
                <LayoutDashboard :size="16" class="text-bet-primary"/> Ir para Match Center
              </div>
              <div class="p-3 hover:bg-white/5 rounded-lg cursor-pointer flex items-center gap-3 text-gray-300 transition-colors" @click="mudarAba('sentimento'); isCommandOpen = false;">
                <Zap :size="16" class="text-yellow-500"/> Ver Steamers (Hype Engine)
              </div>
            </div>
          </div>
        </div>
      </transition>

    </div>
  </div>
</template>

<script setup>
import { ref, reactive, provide, onMounted, onUnmounted, nextTick, computed } from 'vue';
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

// 🛑 A CURA DAS PORTAS: O Gateway e a API passam estritamente pelo Node.js
const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:3000/api/v1').replace(/\/$/, '');
const GATEWAY_URL = (import.meta.env.VITE_GATEWAY_URL || 'http://localhost:3000').replace(/\/$/, '');

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

const mudarAba = (aba) => { abaAtiva.value = aba; };
const formatCurrency = (value) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);

const formatAlert = (alert) => {
  let colorClass = 'text-gray-400';
  let tag = '[SYSTEM]';
  if(alert.tipo && alert.tipo.includes('CRÍTICO')) { colorClass = 'text-red-400'; tag = '⚠️ [CRÍTICO]'; }
  if(alert.tipo && alert.tipo.includes('ODDS DROP')) { colorClass = 'text-yellow-400'; tag = '🔥 [STEAMER]'; }
  return `<strong class="${colorClass}">${tag}</strong> ${alert.time || 'Agora'}: ${alert.texto}`;
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
  
  restaurarSessao();
  fetchHeartbeat(); 
  fetchLiveFeed();
  pollingInterval = setInterval(() => { fetchHeartbeat(); fetchLiveFeed(); }, 60000);

  try {
      const socket = io(GATEWAY_URL, { transports: ['websocket'] });
      socket.on('connect', () => console.log('HFT WebSocket Conectado no Node (3000)!'));
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
  --bg-app: #0b0f19; 
  --bet-primary: #10B981; /* Verde Institucional Ajustado */
  --text-main: #f8fafc;
  --text-muted: #94a3b8;
}

body { background: var(--bg-app); color: var(--text-main); font-family: 'Poppins', sans-serif; margin: 0; padding: 0; overflow-x: hidden; width: 100vw; height: 100vh; }

.font-mono { font-family: 'Lemon Milk', sans-serif; letter-spacing: 1px; }
.font-jersey { font-family: 'Bebas Neue', sans-serif; letter-spacing: 2px; }
.text-bet-primary { color: var(--bet-primary) !important; }
.bg-bet-primary { background-color: var(--bet-primary) !important; }

/* Ambient Orbs */
.ambient-bg { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 0; overflow: hidden; pointer-events: none; }
.ambient-orb { position: absolute; border-radius: 50%; filter: blur(140px); opacity: 0.10; animation: floatOrb 25s infinite alternate cubic-bezier(0.4, 0, 0.2, 1); }
.ambient-orb-1 { width: 80vw; height: 80vh; background: var(--bet-primary); top: -20vh; left: -10vw; }
.ambient-orb-2 { width: 60vw; height: 60vh; background: #3B82F6; bottom: -10vh; right: -10vw; animation-delay: -10s; }
@keyframes floatOrb { 0% { transform: translate(0, 0) scale(1); } 100% { transform: translate(5%, 5%) scale(1.2); } }

/* Scrollbar S-Tier */
.custom-scrollbar::-webkit-scrollbar { width: 6px; height: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(16, 185, 129, 0.4); }

/* Transitions */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.slide-up-enter-active, .slide-up-leave-active { transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
.slide-up-enter-from, .slide-up-leave-to { opacity: 0; transform: translateY(20px) scale(0.95); }
.scale-up-center { animation: scaleUp 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes scaleUp { from { opacity: 0; transform: scale(0.95) translateY(10px); } to { opacity: 1; transform: scale(1) translateY(0); } }

/* Marquee Live Feed */
@keyframes marquee { 0% { transform: translateX(10%); } 100% { transform: translateX(-100%); } }
.animate-marquee { display: inline-block; animation: marquee 40s linear infinite; will-change: transform; }
.animate-marquee:hover { animation-play-state: paused; }
.mask-edges { mask-image: linear-gradient(to right, transparent, black 5%, black 95%, transparent); -webkit-mask-image: linear-gradient(to right, transparent, black 5%, black 95%, transparent); }

/* Globals */
.app-master-wrapper { display: flex; height: 100vh; width: 100vw; overflow: hidden; }
.app-master-layout { display: flex; width: 100%; height: 100%; overflow: hidden; }
.bg-radial-gradient { background: radial-gradient(circle at top center, rgba(16, 185, 129, 0.05) 0%, transparent 80%); }

.fab-btn { background: var(--bet-primary); }
.fab-btn:hover { transform: scale(1.05) translateY(-5px); }
</style>