<template>
  <div data-theme="institutional-dark" class="app-master-wrapper">
    
    <div class="ambient-bg">
      <div class="ambient-orb ambient-orb-1"></div>
      <div class="ambient-orb ambient-orb-2"></div>
    </div>
    
    <ViewLogin v-if="!usuarioLogado" @do-login="fazerLogin" />

    <div v-else class="app-master-layout relative z-10" :class="{ 'mobile-menu-open': isMobileMenuOpen }">
    
      <AppSidebar 
        :usuario-logado="usuarioLogado"
        :aba-ativa="abaAtiva"
        @update:aba-ativa="mudarAba"
        @logout="fazerLogout"
      />

      <main class="flex-1 flex flex-col relative overflow-hidden bg-radial-gradient h-full transition-all duration-300" :class="{ 'pr-[320px]': !watchlistCollapsed && !isMobile }">
        
        <div class="w-full bg-black/60 border-b border-white/5 overflow-hidden flex items-center h-7 shrink-0 relative z-50">
          <div class="bg-[#121927] text-white text-[9px] font-bold uppercase tracking-widest px-3 h-full flex items-center shrink-0 z-10 border-r border-white/10 shadow-[5px_0_15px_rgba(0,0,0,0.8)]">
            <Radio :size="10" class="mr-1.5 text-red-500 animate-pulse" /> Live Feed
          </div>
          <div class="flex-1 overflow-hidden relative flex items-center h-full mask-edges">
            <div class="animate-marquee whitespace-nowrap text-[10px] font-mono text-gray-400 flex items-center gap-12">
              <span v-for="(alert, index) in liveAlerts" :key="index" v-html="formatAlert(alert)"></span>
              <span v-if="liveAlerts.length === 0">Monitorando assimetrias de mercado...</span>
            </div>
          </div>
        </div>

        <header class="top-nav-glass w-full z-40 border-b border-gray-800/50 shrink-0 shadow-sm">
          <div class="flex justify-between items-center w-full px-8 py-3">
            
            <div class="flex gap-10 items-center">
              <div class="hud-metric">
                <span class="label">Matches Tracking</span>
                <span class="value text-white text-lg font-mono">{{ systemStats.mappedGames }}</span>
              </div>
              <div class="hud-metric">
                <span class="label text-bet-primary">Open Opps (+EV)</span>
                <span class="value flex-center-row gap-2 text-bet-primary font-mono">
                  <div class="pulse-dot" v-if="systemStats.evOpportunities > 0"></div> 
                  <span class="text-lg">{{ systemStats.evOpportunities }}</span>
                </span>
              </div>
            </div>

            <div class="hidden lg:flex items-center gap-3 bg-black/30 border border-white/5 px-4 py-2 rounded-xl cursor-pointer hover:bg-black/50 hover:border-white/20 transition-all shadow-inner group" @click="toggleCommandPalette">
              <Search :size="14" class="text-gray-500 group-hover:text-white transition-colors" />
              <span class="text-xs text-gray-500 group-hover:text-gray-300 mr-4 font-mono">/buscar ativo, radar ou insight...</span>
              <div class="flex items-center gap-1">
                <span class="text-[9px] bg-white/5 text-gray-400 px-1.5 py-0.5 rounded font-mono shadow-sm border border-white/5">Ctrl</span>
                <span class="text-[9px] bg-white/5 text-gray-400 px-1.5 py-0.5 rounded font-mono shadow-sm border border-white/5">K</span>
              </div>
            </div>

            <div class="flex gap-10 items-center">
              <div class="hud-metric items-end">
                <span class="label">Daily PnL</span>
                <span class="value font-mono text-lg" :class="systemStats.dailyProfit >= 0 ? 'text-[#10B981] drop-shadow-[0_0_8px_rgba(16,185,129,0.3)]' : 'text-red-500'">
                  {{ systemStats.dailyProfit >= 0 ? '+' : '' }}{{ formatCurrency(systemStats.dailyProfit) }}
                </span>
              </div>
              <div class="hud-metric items-end">
                <span class="label">AUM Total (Bankroll)</span>
                <span class="value font-mono text-white text-lg">{{ formatCurrency(systemStats.currentBankroll) }}</span>
              </div>
            </div>

          </div>
        </header>

        <div class="flex-1 overflow-y-auto custom-scrollbar px-8 py-6 pb-28 relative z-10">
          <transition name="fade" mode="out-in">
            <template v-if="abaAtiva === 'radar'"><ViewRadar /></template>
            <template v-else-if="abaAtiva === 'match-center'"><ViewMatchCenter /></template>
            <template v-else-if="abaAtiva === 'banca'"><ViewGestaoFundo /></template>
            <template v-else-if="abaAtiva === 'backtest'"><ViewBacktestEngine /></template>
            <template v-else-if="abaAtiva === 'sentimento'"><ViewHypeSentimento /></template>
            <template v-else-if="abaAtiva === 'config'"><ViewConfig /></template>
          </transition>
        </div>

        <div class="absolute bottom-8 right-8 z-[90]">
          <transition name="slide-up">
            <div v-show="ticketAberto" class="mb-4 w-[360px] shadow-[0_30px_60px_rgba(0,0,0,0.8)] origin-bottom-right rounded-2xl overflow-hidden border border-gray-700/50">
              <WidgetSmartTicket />
            </div>
          </transition>
          
          <button @click="ticketAberto = !ticketAberto" class="fab-btn ml-auto w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300 relative group">
            <span class="absolute inset-0 rounded-full animate-ping opacity-20 bg-bet-primary group-hover:opacity-40"></span>
            <X v-if="ticketAberto" :size="28" class="text-black relative z-10" />
            <Receipt v-else :size="28" class="text-black relative z-10" />
          </button>
        </div>
      </main>

      <aside class="fixed right-0 top-[28px] h-[calc(100vh-28px)] bg-gradient-to-b from-[#121927]/95 to-[#0f1523]/95 backdrop-blur-xl border-l border-white/10 z-40 transition-all duration-300 flex flex-col shadow-[-20px_0_50px_rgba(0,0,0,0.6)] rounded-tl-2xl" 
             :class="watchlistCollapsed ? 'translate-x-full w-[340px]' : 'translate-x-0 w-[340px]'">
        
        <div class="p-5 border-b border-white/5 flex items-center justify-between bg-black/20 shadow-md shrink-0 rounded-tl-2xl relative overflow-hidden">
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
          <div class="w-full max-w-2xl bg-[#1e293b] border border-white/10 rounded-2xl shadow-[0_0_50px_rgba(0,0,0,0.8)] overflow-hidden scale-up-center">
            <div class="flex items-center p-5 border-b border-white/10 bg-black/20">
              <Search :size="22" class="text-bet-primary mr-4" />
              <input type="text" ref="searchInput" class="bg-transparent border-none text-white text-lg w-full focus:outline-none placeholder-gray-500 font-mono" placeholder="Comando global..." />
              <span class="text-[10px] text-gray-400 font-mono bg-white/5 px-2 py-1 rounded ml-3 shadow-inner">ESC</span>
            </div>
          </div>
        </div>
      </transition>

    </div>
  </div>
</template>

<script setup>
import { ref, reactive, provide, onMounted, onUnmounted, nextTick } from 'vue';
import axios from 'axios';
import { io } from 'socket.io-client';
import { Menu, X, ChevronLeft, ChevronRight, Receipt, Radio, Search } from 'lucide-vue-next';

// IMPORTAÇÕES
import ViewLogin from './components/ViewLogin.vue';
import AppSidebar from './components/AppSidebar.vue';
import WidgetSmartTicket from './components/WidgetSmartTicket.vue';
import WidgetLateralDireito from './components/WidgetLateralDireito.vue';

// VIEWS PRINCIPAIS
import ViewRadar from './components/ViewRadar.vue'; 
import ViewMatchCenter from './components/ViewMatchCenter.vue'; 
import ViewGestaoFundo from './components/ViewGestaoFundo.vue';
import ViewHypeSentimento from './components/ViewHypeSentimento.vue';
import ViewBacktestEngine from './components/ViewBacktestEngine.vue';
import ViewConfig from './components/ViewConfig.vue';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8000';

// ==========================================
// 1. DECLARAÇÃO DE ESTADOS (STATE)
// ==========================================
const globalState = reactive({ activeMatch: null, uiMode: 'REAL' });
const usuarioLogado = ref(null);
const ticketAberto = ref(false);
const isMobileMenuOpen = ref(false);
const abaAtiva = ref('radar');
const isCommandOpen = ref(false);
const searchInput = ref(null);
const watchlistCollapsed = ref(false);
const isMobile = ref(false);

const systemStats = ref({ mappedGames: 0, evOpportunities: 0, dailyProfit: 0.0, currentBankroll: 0.0 });
const liveAlerts = ref([]);
let pollingInterval;

// ==========================================
// 2. DECLARAÇÃO DE FUNÇÕES (FUNCTIONS)
// ==========================================
const mudarAba = (aba) => { 
  abaAtiva.value = aba; 
  isMobileMenuOpen.value = false; 
};

const formatCurrency = (value) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);

const formatAlert = (alert) => {
  let colorClass = 'text-gray-400';
  let tag = '[SYSTEM]';
  if(alert.tipo.includes('CRÍTICO')) { colorClass = 'text-red-400'; tag = '⚠️ [CRÍTICO]'; }
  if(alert.tipo.includes('ODDS DROP')) { colorClass = 'text-yellow-400'; tag = '🔥 [STEAMER]'; }
  return `<strong class="${colorClass}">${tag}</strong> ${alert.time}: ${alert.texto}`;
};

const restaurarSessao = async () => {
  const token = localStorage.getItem('betgenius_token');
  if (!token) return;

  try {
    const response = await axios.get(`${API_BASE_URL}/api/v1/system/config`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    
    const conf = response.data.user_config;
    
    usuarioLogado.value = {
      name: conf.nome || "Admin",
      role: conf.cargo || "Lead Quant Manager",
      avatar: conf.avatar || "https://ui-avatars.com/api/?name=Admin&background=8cc7ff&color=000"
    };
    globalState.uiMode = conf.modo;

    const wrapper = document.querySelector('.app-master-wrapper');
    if (wrapper && conf.tema_interface) {
        wrapper.setAttribute('data-theme', conf.tema_interface);
    }
  } catch (error) {
    console.warn("Sessão expirada ou banco inacessível.");
  }
};

const fazerLogin = async (credenciais) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/v1/auth/login`, {
      email: credenciais.email,
      senha: credenciais.senha
    });

    if (response.data.success) {
      const data = response.data;
      localStorage.setItem('betgenius_token', data.token);
      
      usuarioLogado.value = {
        name: data.user.nome || "Admin",
        role: data.user.role || "Lead Quant Manager",
        avatar: data.user.avatar || "https://ui-avatars.com/api/?name=Admin&background=8cc7ff&color=000"
      };
      
      globalState.uiMode = data.user.modo;
      restaurarSessao();
    }
  } catch (error) {
    console.error("Falha no login", error);
    const msg = error.response?.data?.error || "Servidor offline ou inacessível.";
    alert(`[Acesso Negado] ${msg}`);
  }
};

const fazerLogout = () => { 
  localStorage.removeItem('betgenius_token');
  usuarioLogado.value = null; 
};

const fetchHeartbeat = async () => {
  try { const res = await axios.get(`${API_BASE_URL}/api/v1/system/heartbeat`); systemStats.value = res.data; } catch (e) { }
};

const fetchAlerts = async () => {
  try { const res = await axios.get(`${API_BASE_URL}/api/v1/system/alerts`); liveAlerts.value = res.data; } catch (e) { }
};

const toggleCommandPalette = () => {
  isCommandOpen.value = !isCommandOpen.value;
  if (isCommandOpen.value) { nextTick(() => { searchInput.value?.focus(); }); }
};

const handleKeydown = (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); toggleCommandPalette(); }
  if (e.key === 'Escape' && isCommandOpen.value) isCommandOpen.value = false;
};

// ==========================================
// 3. DEPENDENCY INJECTION (PROVIDE)
// CIRURGIA SÊNIOR: Os provides devem vir DEPOIS que as variáveis e funções foram declaradas
// ==========================================
provide('globalState', globalState);
provide('openSmartTicket', () => { ticketAberto.value = true; });
provide('changeGlobalTab', mudarAba);

// ==========================================
// 4. CICLO DE VIDA (LIFECYCLE)
// ==========================================
onMounted(() => { 
  document.title = "BetGenius Pro | Quant Terminal"; 
  isMobile.value = window.innerWidth < 1280;
  window.addEventListener('keydown', handleKeydown);
  window.addEventListener('resize', () => { isMobile.value = window.innerWidth < 1280; });
  
  restaurarSessao();

  fetchHeartbeat(); 
  fetchAlerts();
  pollingInterval = setInterval(() => { fetchHeartbeat(); fetchAlerts(); }, 60000);

  try {
      const socket = io(GATEWAY_URL, { transports: ['websocket'] });
      socket.on('connect', () => console.log('HFT WebSocket Conectado!'));
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
  --bg-app: #0f1523; 
  --bg-surface: #1e293b;
  --bg-sidebar: #172033;
  --bet-primary: #8cc7ff;
  --bet-secondary: #4f97c2;
  --text-main: #f8fafc;
  --text-muted: #94a3b8;
  --border-soft: rgba(140, 199, 255, 0.1);
}

body { background: var(--bg-app); color: var(--text-main); font-family: 'Poppins', sans-serif; margin: 0; padding: 0; overflow-x: hidden; }

.font-mono { font-family: 'Lemon Milk', sans-serif; letter-spacing: 1px; }
.font-jersey { font-family: 'Bebas Neue', sans-serif; letter-spacing: 2px; }

.text-bet-primary { color: var(--bet-primary) !important; }
.bg-bet-primary { background-color: var(--bet-primary) !important; }
.flex-center-row { display: flex; align-items: center; justify-content: center; }

.ambient-bg { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 0; overflow: hidden; pointer-events: none; }
.ambient-orb { position: absolute; border-radius: 50%; filter: blur(140px); opacity: 0.15; animation: floatOrb 25s infinite alternate cubic-bezier(0.4, 0, 0.2, 1); }
.ambient-orb-1 { width: 80vw; height: 80vh; background: var(--bet-primary); top: -20vh; left: -10vw; }
.ambient-orb-2 { width: 60vw; height: 60vh; background: var(--bet-secondary); bottom: -10vh; right: -10vw; animation-delay: -10s; }
@keyframes floatOrb { 0% { transform: translate(0, 0) scale(1); } 100% { transform: translate(5%, 5%) scale(1.2); } }

.custom-scrollbar::-webkit-scrollbar { width: 6px; height: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(140, 199, 255, 0.2); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(140, 199, 255, 0.4); }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.slide-up-enter-active, .slide-up-leave-active { transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
.slide-up-enter-from, .slide-up-leave-to { opacity: 0; transform: translateY(20px) scale(0.95); }
.scale-up-center { animation: scaleUp 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes scaleUp { from { opacity: 0; transform: scale(0.9); } to { opacity: 1; transform: scale(1); } }

@keyframes marquee { 0% { transform: translateX(10%); } 100% { transform: translateX(-100%); } }
.animate-marquee { display: inline-block; animation: marquee 40s linear infinite; will-change: transform; }
.animate-marquee:hover { animation-play-state: paused; }
.mask-edges { mask-image: linear-gradient(to right, transparent, black 5%, black 95%, transparent); -webkit-mask-image: linear-gradient(to right, transparent, black 5%, black 95%, transparent); }

.app-master-wrapper { display: flex; height: 100vh; width: 100vw; overflow: hidden; }
.app-master-layout { display: flex; width: 100%; height: 100%; overflow: hidden; }
.bg-radial-gradient { background: radial-gradient(circle at top center, rgba(37, 50, 76, 0.2) 0%, transparent 80%); }

.btn-neon-green { background: var(--bet-primary); color: #000; border: none; cursor: pointer; transition: all 0.3s ease; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 4px 20px rgba(140, 199, 255, 0.3); border-radius: 12px; }
.btn-neon-green:hover:not(:disabled) { transform: translateY(-3px); box-shadow: 0 8px 25px rgba(140, 199, 255, 0.5); }
.glass-input-premium { width: 100%; padding: 16px 20px; border-radius: 12px; border: 1px solid var(--border-soft); background: rgba(0,0,0,0.2); font-size: 14px; color: var(--text-main); transition: 0.3s; }
.glass-input-premium:focus { outline: none; border-color: var(--bet-primary); background: rgba(0,0,0,0.4); box-shadow: 0 0 0 3px rgba(140, 199, 255, 0.1); }
.fab-btn { background: var(--bet-primary); box-shadow: 0 10px 25px rgba(140, 199, 255, 0.4); }
.fab-btn:hover { transform: scale(1.05) translateY(-5px); box-shadow: 0 15px 35px rgba(140, 199, 255, 0.6); }

.top-nav-glass { background: rgba(15, 21, 35, 0.6); backdrop-filter: blur(24px); }
.hud-metric { display: flex; flex-direction: column; }
.hud-metric .label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; font-weight: 700; margin-bottom: 4px; }
.pulse-dot { width: 10px; height: 10px; background: var(--bet-primary); border-radius: 50%; animation: pulse 2s infinite; box-shadow: 0 0 10px var(--bet-primary); }

@media (max-width: 1024px) {
  .mobile-header { display: flex; background: var(--bg-sidebar); padding: 15px 25px; justify-content: space-between; border-bottom: 1px solid var(--border-soft); z-index: 1001; }
}
</style>