<template>
  <div data-theme="institutional-dark" class="app-master-wrapper">
    
    <div class="ambient-bg">
      <div class="ambient-orb ambient-orb-1"></div>
      <div class="ambient-orb ambient-orb-2"></div>
    </div>
    
    <div v-if="!usuarioLogado" class="login-wrapper relative z-10">
      <div class="login-orb orb-1"></div>
      <div class="login-orb orb-2"></div>
      
      <div class="glass-login-panel scale-up-center">
        <div class="mb-6 flex justify-center">
          <img src="./assets/images/logo.png" alt="BetGenius" class="h-24 object-contain drop-shadow-2xl" />
        </div>
        <h1 class="font-mono login-title">BETGENIUS</h1>
        <p class="login-subtitle uppercase tracking-widest text-xs">Paga o que é meu, Bethânia!</p>
        
        <form @submit.prevent="fazerLogin" style="width: 100%; margin-top: 30px;">
          <input type="email" class="glass-input-premium" placeholder="ID Institucional (E-mail)" v-model="email" required />
          <input type="password" class="glass-input-premium" placeholder="Chave de Acesso" v-model="senha" required />
          
          <button type="submit" class="btn-neon-green" style="width: 100%; margin-top: 15px;">
            Executar Login
          </button>
        </form>
      </div>
    </div>

    <div v-else class="app-master-layout relative z-10" :class="{ 'mobile-menu-open': isMobileMenuOpen }">
      
      <div class="mobile-header">
        <div style="display: flex; align-items: center; gap: 10px;">
          <img src="./assets/images/logo.png" alt="Logo" class="h-6" />
          <span class="font-mono" style="font-size: 18px; font-weight: bold; color: white;">BET<span style="color: var(--bet-primary)">GENIUS</span></span>
        </div>
        <button class="mobile-menu-btn" @click="isMobileMenuOpen = !isMobileMenuOpen">
          <Menu v-if="!isMobileMenuOpen" :size="24" color="white" />
          <X v-else :size="24" color="white" />
        </button>
      </div>

      <aside class="desktop-sidebar shadow-[20px_0_50px_rgba(0,0,0,0.5)] z-50 shrink-0" :class="{ collapsed: sidebarCollapsed }">
        <div class="flex items-center justify-center relative mb-6 min-h-[48px]">
          <img src="./assets/images/logo.png" alt="BetGenius" class="object-contain transition-all duration-500" :class="sidebarCollapsed ? 'h-8' : 'h-10'" />
          <button class="toggle-btn desktop-only" @click="sidebarCollapsed = !sidebarCollapsed">
            <ChevronRight v-if="sidebarCollapsed" :size="16" />
            <ChevronLeft v-else :size="16" />
          </button>
        </div>

        <div class="user-badge mb-4 transition-all" :class="sidebarCollapsed ? 'justify-center p-2' : 'p-3'">
          <div class="sidebar-avatar shrink-0"><User :size="18" color="var(--bet-primary)" /></div>
          <div style="display: flex; flex-direction: column; overflow: hidden;" v-show="!sidebarCollapsed">
            <span style="font-size: 10px; color: var(--text-muted); font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Gestor de Risco</span>
            <span class="font-mono truncate" style="font-size: 14px; color: white; line-height: 1.2;">{{ usuarioLogado.name }}</span>
          </div>
        </div>

        <div class="channel-group mt-2">
          <div class="nav-section-title"><span v-show="!sidebarCollapsed">Módulos Operacionais</span></div>
          
          <div class="nav-item group" :class="{ active: abaAtiva === 'radar' }" @click="mudarAba('radar')">
            <Target :size="18" :class="abaAtiva === 'radar' ? 'text-bet-primary' : 'text-gray-500 group-hover:text-white transition-colors'" />
            <span class="nav-text" v-show="!sidebarCollapsed">Radar HFT</span>
          </div>
          <div class="nav-item group" :class="{ active: abaAtiva === 'match-center' }" @click="mudarAba('match-center')">
            <LayoutDashboard :size="18" :class="abaAtiva === 'match-center' ? 'text-bet-primary' : 'text-gray-500 group-hover:text-white transition-colors'" />
            <span class="nav-text" v-show="!sidebarCollapsed">Match Center</span>
          </div>
          <div class="nav-item group" :class="{ active: abaAtiva === 'banca' }" @click="mudarAba('banca')">
            <DollarSign :size="18" :class="abaAtiva === 'banca' ? 'text-bet-primary' : 'text-gray-500 group-hover:text-white transition-colors'" />
            <span class="nav-text" v-show="!sidebarCollapsed">Gestão de Fundo</span>
          </div>
          <div class="nav-item group" :class="{ active: abaAtiva === 'backtest' }" @click="mudarAba('backtest')">
            <FlaskConical :size="18" :class="abaAtiva === 'backtest' ? 'text-bet-primary' : 'text-gray-500 group-hover:text-white transition-colors'" />
            <span class="nav-text" v-show="!sidebarCollapsed">Quant Lab</span>
          </div>
          <div class="nav-item group" :class="{ active: abaAtiva === 'sentimento' }" @click="mudarAba('sentimento')">
            <TrendingUp :size="18" :class="abaAtiva === 'sentimento' ? 'text-bet-primary' : 'text-gray-500 group-hover:text-white transition-colors'" />
            <span class="nav-text" v-show="!sidebarCollapsed">Sentiment Engine</span>
          </div>
        </div>

        <div style="margin-top: auto; display: flex; flex-direction: column; width: 100%;">
          <div class="nav-section-title mb-2"><span v-show="!sidebarCollapsed">Integrações</span></div>
          
          <div class="nav-item group cursor-pointer" :class="{ 'active': isMatchSelectorOpen }" @click="isMatchSelectorOpen = true">
            <Trophy :size="18" :class="isMatchSelectorOpen ? 'text-bet-primary' : 'text-gray-500 group-hover:text-white transition-colors'" />
            <span class="nav-text" v-show="!sidebarCollapsed">Seletor Global de Jogos</span>
          </div>

          <div class="h-px bg-white/5 w-full my-4"></div>

          <div class="nav-item text-danger w-full group cursor-pointer" @click="fazerLogout">
            <LogOut :size="18" class="group-hover:scale-110 transition-transform" />
            <span class="nav-text" v-show="!sidebarCollapsed">Encerrar Sessão</span>
          </div>
        </div>
      </aside>

      <main class="flex-1 flex flex-col relative overflow-hidden bg-radial-gradient h-full transition-all duration-300" :class="{ 'pr-[320px]': !watchlistCollapsed && !isMobile }">
        
        <div class="w-full bg-black/60 border-b border-white/5 overflow-hidden flex items-center h-7 shrink-0 relative z-50">
          <div class="bg-[#121927] text-white text-[9px] font-bold uppercase tracking-widest px-3 h-full flex items-center shrink-0 z-10 border-r border-white/10 shadow-[5px_0_15px_rgba(0,0,0,0.8)]">
            <Radio :size="10" class="mr-1.5 text-red-500 animate-pulse" /> Live Feed
          </div>
          <div class="flex-1 overflow-hidden relative flex items-center h-full mask-edges">
            <div class="animate-marquee whitespace-nowrap text-[10px] font-mono text-gray-400 flex items-center gap-12">
              <span><strong class="text-red-400">⚠️ [ASIAN DROP]</strong> Chelsea AH -1.0 despencou de 2.05 para 1.82 (Pinnacle)</span>
              <span><strong class="text-[#10B981]">💡 [VALUE ALERT]</strong> Over 2.5 Gols no Arsenal atingiu +8.5% EV</span>
              <span><strong class="text-yellow-400">🔥 [STEAMER]</strong> R$ 2.4M injetados na vitória do Real Madrid nos últimos 10 min</span>
              <span><strong class="text-bet-primary">⏱️ [LATE INFO]</strong> K. De Bruyne confirmado fora; Linhas ajustando.</span>
              <span><strong class="text-red-400">⚠️ [ASIAN DROP]</strong> Chelsea AH -1.0 despencou de 2.05 para 1.82 (Pinnacle)</span>
              <span><strong class="text-[#10B981]">💡 [VALUE ALERT]</strong> Over 2.5 Gols no Arsenal atingiu +8.5% EV</span>
            </div>
          </div>
        </div>

        <header class="top-nav-glass w-full z-40 border-b border-gray-800/50 shrink-0 shadow-sm">
          <div class="flex justify-between items-center w-full px-8 py-3">
            
            <div class="flex gap-10 items-center">
              <div class="hud-metric">
                <span class="label">Matches Tracking</span>
                <span class="value text-white text-lg">247</span>
              </div>
              <div class="hud-metric">
                <span class="label text-bet-primary">Open Opps (+EV)</span>
                <span class="value flex-center-row gap-2 text-bet-primary">
                  <div class="pulse-dot"></div> <span class="text-lg">12</span>
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
                <span class="value text-[#10B981] text-lg drop-shadow-[0_0_8px_rgba(16,185,129,0.3)]">+ R$ 420,50</span>
              </div>
              <div class="hud-metric items-end">
                <span class="label">AUM Total</span>
                <span class="value font-mono text-white text-lg">R$ 200.420</span>
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
          </transition>
        </div>

        <div class="absolute bottom-8 right-8 z-[90]">
          <transition name="slide-up">
            <div v-show="ticketAberto" class="mb-4 w-[360px] shadow-[0_30px_60px_rgba(0,0,0,0.8)] origin-bottom-right rounded-2xl overflow-hidden border border-gray-700/50">
              <WidgetSmartTicket />
            </div>
          </transition>
          
          <button 
            @click="ticketAberto = !ticketAberto"
            class="fab-btn ml-auto w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300 relative group"
          >
            <span class="absolute inset-0 rounded-full animate-ping opacity-20 bg-bet-primary group-hover:opacity-40"></span>
            <X v-if="ticketAberto" :size="28" class="text-black relative z-10" />
            <Receipt v-else :size="28" class="text-black relative z-10" />
            
            <div v-show="!ticketAberto && globalState.ticketCount > 0" class="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold w-6 h-6 flex items-center justify-center rounded-full border-2 border-[#1b2539] z-20 shadow-md">
              {{ globalState.ticketCount }}
            </div>
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
                <span class="text-[8px] text-gray-400 uppercase tracking-widest mt-0.5">Monitoramento Ativo</span>
              </div>
           </div>
           
           <span class="text-[9px] text-[#10B981] font-mono bg-[#10B981]/10 px-2 py-1 rounded-md border border-[#10B981]/20 shadow-inner flex items-center gap-1.5 relative z-10">
             <Activity size="10" /> Sync
           </span>
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
              <input type="text" ref="searchInput" class="bg-transparent border-none text-white text-lg w-full focus:outline-none placeholder-gray-500 font-mono" placeholder="O que você deseja operar ou acessar?" />
              <span class="text-[10px] text-gray-400 font-mono bg-white/5 px-2 py-1 rounded ml-3 shadow-inner">ESC</span>
            </div>
            <div class="p-3">
              <div class="text-[10px] text-gray-500 uppercase tracking-widest p-2 mb-1">Ações Globais Rápidas</div>
              <div @click="mudarAba('match-center'); toggleCommandPalette()" class="p-3 hover:bg-white/5 rounded-xl cursor-pointer flex items-center justify-between group transition-colors">
                <div class="flex items-center gap-3 text-gray-300 group-hover:text-white">
                  <LayoutDashboard :size="18" class="text-bet-primary"/> Acessar Match Center (Análise Profunda)
                </div>
                <ChevronRight :size="16" class="text-gray-600 group-hover:text-white" />
              </div>
              <div @click="ticketAberto = true; toggleCommandPalette()" class="p-3 hover:bg-white/5 rounded-xl cursor-pointer flex items-center justify-between group transition-colors mt-1">
                <div class="flex items-center gap-3 text-gray-300 group-hover:text-white">
                  <Receipt :size="18" class="text-bet-primary"/> Abrir Smart Ticket Global
                </div>
                <ChevronRight :size="16" class="text-gray-600 group-hover:text-white" />
              </div>
            </div>
          </div>
        </div>
      </transition>

      <transition name="slide-right">
        <div v-if="isMatchSelectorOpen" class="fixed inset-y-0 right-0 w-[350px] bg-[#0f1523]/95 backdrop-blur-2xl border-l border-white/10 z-[9999] shadow-[-20px_0_50px_rgba(0,0,0,0.8)] flex flex-col">
          <div class="p-6 border-b border-white/10 flex justify-between items-center bg-black/40 shadow-inner">
            <div class="flex items-center gap-3">
              <Trophy class="text-bet-primary" size="22" />
              <h3 class="font-mono text-white text-lg tracking-wider">Laboratório</h3>
            </div>
            <button @click="isMatchSelectorOpen = false" class="text-gray-500 hover:text-white bg-white/5 hover:bg-white/10 p-1.5 rounded transition-colors"><X size="20" /></button>
          </div>
          
          <div class="p-5 flex-1 overflow-y-auto custom-scrollbar flex flex-col gap-4">
            <div class="flex flex-col gap-2">
              <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold border-b border-white/5 pb-1">Premier League</span>
              <div class="p-3 bg-bet-primary/10 border border-bet-primary/50 rounded-xl cursor-pointer relative overflow-hidden shadow-[0_0_15px_rgba(140,199,255,0.1)] hover:bg-bet-primary/20 transition-colors" @click="isMatchSelectorOpen = false; mudarAba('match-center')">
                <div class="absolute top-0 left-0 w-1.5 h-full bg-bet-primary"></div>
                <div class="flex justify-between items-center ml-2">
                  <span class="text-white font-bold text-sm tracking-wide">Arsenal <span class="text-gray-600 mx-1">v</span> Liverpool</span>
                  <span class="text-[9px] bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded font-bold animate-pulse border border-red-500/20">68' LIVE</span>
                </div>
                <span class="text-[10px] text-bet-primary mt-1.5 block ml-2 font-mono">» Analisando agora</span>
              </div>

              <div @click="isMatchSelectorOpen = false; mudarAba('match-center')" class="p-3 bg-black/30 border border-white/5 hover:border-white/20 rounded-xl cursor-pointer transition-colors group">
                <div class="flex justify-between items-center">
                  <span class="text-gray-400 group-hover:text-white font-bold text-sm tracking-wide transition-colors">Man City <span class="text-gray-700 mx-1">v</span> Chelsea</span>
                  <span class="text-[10px] text-gray-600 font-mono">16:00</span>
                </div>
                <span class="text-[9px] text-bet-warning mt-1.5 block uppercase tracking-widest font-bold">Hype Anômalo Detectado</span>
              </div>
            </div>
          </div>
        </div>
      </transition>
      <div v-if="isMatchSelectorOpen" class="fixed inset-0 bg-black/70 z-[9990] backdrop-blur-sm" @click="isMatchSelectorOpen = false"></div>

    </div>
  </div>
</template>

<script setup>
import { ref, reactive, provide, onMounted, onUnmounted, nextTick } from 'vue';
import {
  Activity, Menu, X, ChevronLeft, ChevronRight, Target,
  LayoutDashboard, DollarSign, TrendingUp, LogOut, User,
  Receipt, Zap, Radio, Award, Search, Trophy, Globe, Clock, FlaskConical
} from 'lucide-vue-next';

// IMPORTAÇÕES FATORADAS DAS ABAS
import WidgetSmartTicket from './components/WidgetSmartTicket.vue';
import WidgetLateralDireito from './components/WidgetLateralDireito.vue';
import ViewRadar from './components/ViewRadar.vue'; 
import ViewMatchCenter from './components/ViewMatchCenter.vue'; 
import ViewGestaoFundo from './components/ViewGestaoFundo.vue';
import ViewHypeSentimento from './components/ViewHypeSentimento.vue';
import ViewBacktestEngine from './components/ViewBacktestEngine.vue';

// =========================================================
// O CÉREBRO DO SISTEMA (GLOBAL STATE MANAGEMENT NÍVEL S)
// =========================================================
// Em vez de Pinia, usamos a reatividade nativa do Vue 3 para criar 
// um Event Bus central. Todas as abas conversam com este objeto.
const globalState = reactive({
  ticketCount: 3,
  activeMatch: 'Arsenal x Liverpool',
  hypeFactorAlert: true,
  currentKellyLimit: 2.5, // % Max da banca recomendada no momento
});

// Prover o estado global para que qualquer componente filho possa consumir (inject)
provide('globalState', globalState);
provide('openSmartTicket', () => { ticketAberto.value = true; });
provide('navigateToMatch', (matchName) => {
  globalState.activeMatch = matchName;
  abaAtiva.value = 'match-center';
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

// =========================================================
// ESTADO DE NAVEGAÇÃO E UI
// =========================================================
const usuarioLogado = ref(null);
const email = ref('');
const senha = ref('');
const ticketAberto = ref(false);
const sidebarCollapsed = ref(false);
const isMobileMenuOpen = ref(false);
const abaAtiva = ref('radar');
const isMatchSelectorOpen = ref(false);
const isCommandOpen = ref(false);
const searchInput = ref(null);
const watchlistCollapsed = ref(false); // Controle da nova Watchlist Global

// MÉTODOS DE LOGIN / NAVEGAÇÃO
const fazerLogin = () => {
  if(email.value && senha.value) { usuarioLogado.value = { name: "Igor Santos.", role: "Gestor Quant" }; }
};
const fazerLogout = () => {
  usuarioLogado.value = null; email.value = ''; senha.value = '';
};
const mudarAba = (aba) => {
  abaAtiva.value = aba; isMobileMenuOpen.value = false;
};

// MÉTODOS DO COMMAND PALETTE
const toggleCommandPalette = () => {
  isCommandOpen.value = !isCommandOpen.value;
  if (isCommandOpen.value) {
    nextTick(() => { searchInput.value?.focus(); });
  }
};

const handleKeydown = (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    toggleCommandPalette();
  }
  if (e.key === 'Escape') {
    if (isCommandOpen.value) isCommandOpen.value = false;
    if (isMatchSelectorOpen.value) isMatchSelectorOpen.value = false;
  }
};

const isMobile = ref(window.innerWidth < 1280);

onMounted(() => { 
  document.title = "BetGenius Pro | Terminal"; 
  window.addEventListener('keydown', handleKeydown);
  window.addEventListener('resize', () => { isMobile.value = window.innerWidth < 1280; });
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown);
  window.removeEventListener('resize', () => { isMobile.value = window.innerWidth < 1280; });
});
</script>

<style>
/* ========================================== */
/* BETGENIUS DESIGN SYSTEM INSTITUCIONAL      */
/* ========================================== */

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
  --shadow-ambient: 0 15px 40px rgba(0,0,0,0.5);
}

body {
  background: var(--bg-app);
  color: var(--text-main);
  font-family: 'Poppins', sans-serif;
  margin: 0;
  padding: 0;
  overflow-x: hidden;
}

.font-mono { font-family: 'Lemon Milk', sans-serif; letter-spacing: 1px; }

/* UTILS E CORES */
.text-bet-primary { color: var(--bet-primary) !important; }
.bg-bet-primary { background-color: var(--bet-primary) !important; }
.text-success { color: var(--bet-primary) !important; }
.text-danger { color: #EF4444 !important; }
.text-warning { color: #F59E0B !important; }
.flex-center-row { display: flex; align-items: center; justify-content: center; }

/* ESTILOS DO DRAGGABLE NÍVEL S */
.ghost-widget {
  opacity: 0.3 !important;
  border: 2px dashed var(--bet-primary) !important;
  background: rgba(140, 199, 255, 0.05) !important;
  transform: scale(0.98);
}
.drag-vertical, .drag-horizontal {
  backdrop-filter: blur(8px);
}

/* FUNDO ANIMADO PREMIUM (Orbes lentos) */
.ambient-bg { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 0; overflow: hidden; pointer-events: none; }
.ambient-orb { position: absolute; border-radius: 50%; filter: blur(140px); opacity: 0.15; animation: floatOrb 25s infinite alternate cubic-bezier(0.4, 0, 0.2, 1); }
.ambient-orb-1 { width: 80vw; height: 80vh; background: var(--bet-primary); top: -20vh; left: -10vw; }
.ambient-orb-2 { width: 60vw; height: 60vh; background: var(--bet-secondary); bottom: -10vh; right: -10vw; animation-delay: -10s; }
@keyframes floatOrb { 0% { transform: translate(0, 0) scale(1); } 100% { transform: translate(5%, 5%) scale(1.2); } }

/* SCROLLBAR CUSTOMIZADA PARA O MIOLO */
.custom-scrollbar::-webkit-scrollbar { width: 6px; height: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(140, 199, 255, 0.2); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(140, 199, 255, 0.4); }
.hide-scrollbar::-webkit-scrollbar { display: none; }
.hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }

/* ANIMAÇÕES GLOBAIS */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.slide-up-enter-active, .slide-up-leave-active { transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
.slide-up-enter-from, .slide-up-leave-to { opacity: 0; transform: translateY(20px) scale(0.95); }
.fade-in-up { animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
@keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
.scale-up-center { animation: scaleUp 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes scaleUp { from { opacity: 0; transform: scale(0.9); } to { opacity: 1; transform: scale(1); } }

/* Live Ticker Marquee Animation */
@keyframes marquee { 0% { transform: translateX(50%); } 100% { transform: translateX(-100%); } }
.animate-marquee { display: inline-block; animation: marquee 40s linear infinite; will-change: transform; }
.animate-marquee:hover { animation-play-state: paused; }
.mask-edges { mask-image: linear-gradient(to right, transparent, black 5%, black 95%, transparent); -webkit-mask-image: linear-gradient(to right, transparent, black 5%, black 95%, transparent); }

/* ESTRUTURA GERAL */
.app-master-wrapper { display: flex; height: 100vh; width: 100vw; overflow: hidden; }
.app-master-layout { display: flex; width: 100%; height: 100%; overflow: hidden; }
.bg-radial-gradient { background: radial-gradient(circle at top center, rgba(37, 50, 76, 0.2) 0%, transparent 80%); }

/* WIDGETS E LOGIN PANELS */
.glass-card { background: rgba(30, 41, 59, 0.7); border-radius: 16px; box-shadow: var(--shadow-ambient); border: 1px solid var(--border-soft); backdrop-filter: blur(16px); }

/* BOTOES E INPUTS */
.btn-neon-green { background: var(--bet-primary); color: #000; border: none; font-family: 'Lemon Milk', sans-serif; cursor: pointer; transition: all 0.3s ease; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 4px 20px rgba(140, 199, 255, 0.3); padding: 16px 30px; border-radius: 12px; font-size: 15px; }
.btn-neon-green:hover:not(:disabled) { transform: translateY(-3px); box-shadow: 0 8px 25px rgba(140, 199, 255, 0.5); }
.glass-input-premium { width: 100%; padding: 16px 20px; border-radius: 12px; border: 1px solid var(--border-soft); background: rgba(0,0,0,0.2); font-size: 14px; color: var(--text-main); margin-bottom: 15px; transition: 0.3s; font-family: 'Poppins', sans-serif; }
.glass-input-premium:focus { outline: none; border-color: var(--bet-primary); background: rgba(0,0,0,0.4); box-shadow: 0 0 0 3px rgba(140, 199, 255, 0.1); }
.fab-btn { background: var(--bet-primary); box-shadow: 0 10px 25px rgba(140, 199, 255, 0.4); }
.fab-btn:hover { transform: scale(1.05) translateY(-5px); box-shadow: 0 15px 35px rgba(140, 199, 255, 0.6); }

/* LOGIN VIEW */
.login-wrapper { position: relative; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; overflow: hidden; background: transparent; }
.login-orb { position: absolute; border-radius: 50%; filter: blur(120px); opacity: 0.2; }
.orb-1 { width: 600px; height: 600px; background: var(--bet-primary); top: -200px; left: -100px; }
.orb-2 { width: 500px; height: 500px; background: var(--bet-secondary); bottom: -150px; right: -100px; }
.glass-login-panel { background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(40px); border: 1px solid rgba(140, 199, 255, 0.15); padding: 50px 40px; border-radius: 24px; width: 100%; max-width: 420px; text-align: center; position: relative; z-index: 10; box-shadow: 0 40px 80px rgba(0,0,0,0.8); }
.login-title { color: var(--text-main); font-size: 36px; margin: 0 0 5px 0; }
.login-subtitle { color: var(--bet-primary); margin-bottom: 30px; font-weight: 600; opacity: 0.8;}

/* SIDEBAR E TOPNAV */
.desktop-sidebar { width: 260px; background: rgba(23, 32, 51, 0.85); backdrop-filter: blur(20px); display: flex; flex-direction: column; padding: 30px 20px; transition: 0.3s ease-in-out; border-right: 1px solid var(--border-soft); height: 100vh; overflow-y: auto; overflow-x: hidden; }
.desktop-sidebar.collapsed { width: 85px; align-items: center; padding: 30px 10px; }
.user-badge { display: flex; align-items: center; gap: 12px; background: rgba(0,0,0,0.2); border: 1px solid var(--border-soft); border-radius: 12px; }
.sidebar-avatar { width: 36px; height: 36px; border-radius: 10px; background: rgba(140, 199, 255, 0.1); display: flex; justify-content: center; align-items: center; border: 1px solid rgba(140, 199, 255, 0.2); }
.toggle-btn { position: absolute; right: -30px; top: 10px; background: var(--bg-sidebar); border: 1px solid var(--border-soft); color: var(--text-muted); width: 28px; height: 28px; border-radius: 50%; display: flex; justify-content: center; align-items: center; cursor: pointer; z-index: 101; transition: 0.2s; }
.toggle-btn:hover { color: #000; background: var(--bet-primary); border-color: var(--bet-primary); }
.nav-section-title { font-size: 10px; text-transform: uppercase; font-weight: 800; letter-spacing: 1.5px; margin-bottom: 15px; margin-top: 20px; color: rgba(255,255,255,0.3); padding-left: 10px; }
.nav-item { padding: 14px 15px; border-radius: 12px; margin-bottom: 5px; color: var(--text-muted); display: flex; align-items: center; gap: 14px; cursor: pointer; font-weight: 600; font-size: 14px; transition: all 0.2s ease; border: 1px solid transparent; }
.nav-item:hover { background: rgba(140, 199, 255, 0.05); border-color: rgba(140, 199, 255, 0.1); }
.nav-item.active { background: rgba(140, 199, 255, 0.1); color: white; border-color: var(--border-soft); box-shadow: inset 3px 0 0 var(--bet-primary); }
.top-nav-glass { background: rgba(15, 21, 35, 0.6); backdrop-filter: blur(24px); }
.hud-metric { display: flex; flex-direction: column; }
.hud-metric .label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; font-weight: 700; margin-bottom: 4px; }
.pulse-dot { width: 10px; height: 10px; background: var(--bet-primary); border-radius: 50%; animation: pulse 2s infinite; box-shadow: 0 0 10px var(--bet-primary); }
.nav-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
@keyframes pulse { 0% { transform: scale(0.95); opacity: 1; } 50% { transform: scale(1.2); opacity: 0.8; } 100% { transform: scale(0.95); opacity: 1; } }

/* Gaveta Match Selector Slide */
.slide-right-enter-active, .slide-right-leave-active { transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
.slide-right-enter-from, .slide-right-leave-to { transform: translateX(100%); }

/* MOBILE */
.mobile-header { display: none; }
@media (max-width: 1024px) {
  .desktop-sidebar { position: fixed; transform: translateX(-100%); z-index: 1000; height: 100%; }
  .app-master-layout.mobile-menu-open .desktop-sidebar { transform: translateX(0); }
  .mobile-header { display: flex; background: var(--bg-sidebar); padding: 15px 25px; justify-content: space-between; border-bottom: 1px solid var(--border-soft); z-index: 1001; }
  .desktop-only { display: none !important; }
}
</style>