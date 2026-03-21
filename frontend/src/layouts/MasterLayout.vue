<template>
  <div class="app-master-layout" :class="{ 'mobile-menu-open': isMobileMenuOpen }">
    
    <div class="mobile-header lg:hidden flex bg-sidebar p-4 justify-between items-center border-b border-soft z-[1001]">
      <div class="flex items-center gap-2">
        <img src="../assets/images/logo.png" alt="Logo" class="h-6" />
        <span class="font-mono text-lg font-bold text-white">BET<span class="text-bet-primary">GENIUS</span></span>
      </div>
      <button @click="isMobileMenuOpen = !isMobileMenuOpen"><Menu size="24" class="text-white" /></button>
    </div>

    <aside class="desktop-sidebar shadow-2xl z-50 shrink-0" :class="{ collapsed: sidebarCollapsed }">
      <div class="flex items-center justify-center relative mb-6 min-h-[48px]">
        <img src="../assets/images/logo.png" alt="BetGenius" class="object-contain transition-all duration-500" :class="sidebarCollapsed ? 'h-8' : 'h-10'" />
        <button class="toggle-btn hidden lg:flex" @click="sidebarCollapsed = !sidebarCollapsed">
          <ChevronRight v-if="sidebarCollapsed" :size="16" />
          <ChevronLeft v-else :size="16" />
        </button>
      </div>

      <div class="user-badge mb-4 transition-all" :class="sidebarCollapsed ? 'justify-center p-2' : 'p-3'">
        <div class="sidebar-avatar shrink-0"><User :size="18" color="var(--bet-primary)" /></div>
        <div class="flex flex-col overflow-hidden" v-show="!sidebarCollapsed">
          <span class="text-[10px] text-muted font-bold uppercase tracking-wider">Gestor de Risco</span>
          <span class="font-mono truncate text-sm text-white leading-tight">Igor C.</span>
        </div>
      </div>

      <div class="channel-group mt-2">
        <div class="text-[10px] uppercase font-bold tracking-widest mb-4 mt-5 text-white/30 pl-2"><span v-show="!sidebarCollapsed">Módulos</span></div>
        
        <router-link to="/" class="nav-item group" active-class="active">
          <Target :size="18" class="text-gray-500 group-hover:text-white transition-colors" /> 
          <span class="nav-text" v-show="!sidebarCollapsed">Radar (+EV)</span>
        </router-link>
        
        <router-link to="/match-center" class="nav-item group" active-class="active">
          <LayoutDashboard :size="18" class="text-gray-500 group-hover:text-white transition-colors" /> 
          <span class="nav-text" v-show="!sidebarCollapsed">Match Center</span>
        </router-link>
      </div>

      <div class="mt-auto flex flex-col gap-4 items-center">
         <div class="nav-item text-danger w-full justify-center group" @click="fazerLogout">
           <LogOut :size="18" class="group-hover:scale-110 transition-transform" /> 
           <span class="nav-text" v-show="!sidebarCollapsed">Sair</span>
         </div>
      </div>
    </aside>

    <main class="flex-1 flex flex-col relative overflow-hidden bg-radial-gradient h-full">
      
      <header class="top-nav-glass w-full z-40 border-b border-gray-800/50 shrink-0">
        <div class="flex justify-between items-center w-full px-8 py-5">
          <div class="flex gap-10">
            <div class="flex flex-col">
              <span class="text-[10px] text-muted uppercase tracking-widest font-bold mb-1">Jogos Mapeados</span>
              <span class="font-mono text-white text-xl">247</span>
            </div>
            <div class="flex flex-col">
              <span class="text-[10px] text-bet-primary uppercase tracking-widest font-bold mb-1 flex items-center gap-1">
                <Search :size="10"/> Oportunidades
              </span>
              <span class="font-mono text-bet-primary text-xl flex items-center gap-2"><div class="pulse-dot"></div> 12</span>
            </div>
          </div>
          
          <div class="hidden lg:flex items-center gap-2 bg-black/20 border border-white/10 px-4 py-2 rounded-full cursor-pointer hover:bg-black/40 transition-colors" @click="toggleCommandPalette">
            <Search :size="14" class="text-muted" />
            <span class="text-xs text-muted">Buscar mercado ou time...</span>
            <span class="text-[10px] bg-white/10 text-white px-2 py-0.5 rounded ml-2 font-mono">Ctrl K</span>
          </div>

          <div class="flex gap-10">
            <div class="flex flex-col items-end">
              <span class="text-[10px] text-muted uppercase tracking-widest font-bold mb-1">Lucro Diário</span>
              <span class="font-mono text-success text-xl animate-pulse">+ R$ 420,50</span>
            </div>
            <div class="flex flex-col items-end">
              <span class="text-[10px] text-muted uppercase tracking-widest font-bold mb-1">Banca Total</span>
              <span class="font-mono text-white text-xl">R$ 200.420,50</span>
            </div>
          </div>
        </div>
      </header>

      <div class="flex-1 overflow-hidden relative">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>

    </main>

    <div v-if="isCommandOpen" class="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-md flex items-start justify-center pt-[10vh]" @click.self="toggleCommandPalette">
      <div class="w-full max-w-2xl bg-surface border border-white/10 rounded-2xl shadow-2xl overflow-hidden fade-in-up">
        <div class="flex items-center p-4 border-b border-white/10">
          <Search :size="20" class="text-bet-primary mr-3" />
          <input type="text" class="bg-transparent border-none text-white text-lg w-full focus:outline-none placeholder-gray-500 font-mono" placeholder="O que você deseja operar?" autofocus ref="searchInput" />
          <span class="text-[10px] text-gray-500 font-mono bg-white/5 px-2 py-1 rounded">ESC</span>
        </div>
        <div class="p-2">
          <div class="text-[10px] text-gray-500 uppercase tracking-widest p-2">Ações Rápidas</div>
          <div class="p-3 hover:bg-white/5 rounded-lg cursor-pointer flex items-center gap-3 text-gray-300">
            <LayoutDashboard :size="16" class="text-bet-primary"/> Ir para Match Center
          </div>
          <div class="p-3 hover:bg-white/5 rounded-lg cursor-pointer flex items-center gap-3 text-gray-300">
            <Zap :size="16" class="text-warning"/> Ver Steamers (Dinheiro Inteligente)
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import { Menu, X, ChevronLeft, ChevronRight, Target, LayoutDashboard, LogOut, User, Search, Zap } from 'lucide-vue-next'; 

const router = useRouter();
const sidebarCollapsed = ref(false);
const isMobileMenuOpen = ref(false);

// Command Palette Lógica
const isCommandOpen = ref(false);
const searchInput = ref(null);

const toggleCommandPalette = () => {
  isCommandOpen.value = !isCommandOpen.value;
  if (isCommandOpen.value) {
    nextTick(() => searchInput.value?.focus());
  }
};

const handleKeydown = (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    toggleCommandPalette();
  }
  if (e.key === 'Escape' && isCommandOpen.value) {
    isCommandOpen.value = false;
  }
};

onMounted(() => { window.addEventListener('keydown', handleKeydown); });
onUnmounted(() => { window.removeEventListener('keydown', handleKeydown); });

const fazerLogout = () => {
  localStorage.removeItem('betgenius_user');
  router.push('/login');
};
</script>

<style scoped>
/* Estilos extraídos do App.vue para focar na Sidebar e HUD */
.desktop-sidebar { width: 260px; background: var(--bg-sidebar); display: flex; flex-direction: column; padding: 30px 20px; transition: 0.3s ease-in-out; border-right: 1px solid var(--border-soft); height: 100vh; overflow-y: auto; overflow-x: hidden; }
.desktop-sidebar.collapsed { width: 85px; align-items: center; padding: 30px 10px; }
.user-badge { display: flex; align-items: center; gap: 12px; background: rgba(0,0,0,0.2); border: 1px solid var(--border-soft); border-radius: 12px; }
.sidebar-avatar { width: 36px; height: 36px; border-radius: 10px; background: rgba(140, 199, 255, 0.1); display: flex; justify-content: center; align-items: center; border: 1px solid rgba(140, 199, 255, 0.2); }
.toggle-btn { position: absolute; right: -30px; top: 10px; background: var(--bg-sidebar); border: 1px solid var(--border-soft); color: var(--text-muted); width: 28px; height: 28px; border-radius: 50%; display: flex; justify-content: center; align-items: center; cursor: pointer; z-index: 101; transition: 0.2s; }
.toggle-btn:hover { color: #000; background: var(--bet-primary); border-color: var(--bet-primary); }
.nav-item { padding: 14px 15px; border-radius: 12px; margin-bottom: 5px; color: var(--text-muted); display: flex; align-items: center; gap: 14px; cursor: pointer; font-weight: 600; font-size: 14px; transition: all 0.2s ease; border: 1px solid transparent; }
.nav-item:hover { background: rgba(140, 199, 255, 0.05); border-color: rgba(140, 199, 255, 0.1); }
.nav-item.active { background: rgba(140, 199, 255, 0.1); color: white; border-color: var(--border-soft); box-shadow: inset 3px 0 0 var(--bet-primary); }
.nav-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.top-nav-glass { background: rgba(18, 25, 39, 0.85); backdrop-filter: blur(24px); }
.pulse-dot { width: 10px; height: 10px; background: var(--bet-primary); border-radius: 50%; animation: pulse 2s infinite; box-shadow: 0 0 10px var(--bet-primary); }
.text-muted { color: var(--text-muted); }
.bg-sidebar { background: var(--bg-sidebar); }
.border-soft { border-color: var(--border-soft); }
.bg-radial-gradient { background: radial-gradient(circle at top center, rgba(37, 50, 76, 0.3) 0%, var(--bg-app) 70%); }
@media (max-width: 1024px) {
  .desktop-sidebar { position: fixed; transform: translateX(-100%); z-index: 1000; height: 100%; }
  .app-master-layout.mobile-menu-open .desktop-sidebar { transform: translateX(0); }
  .desktop-only { display: none !important; }
}
</style>