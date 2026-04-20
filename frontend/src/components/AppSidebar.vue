<template>
  <aside class="desktop-sidebar shadow-[20px_0_50px_rgba(0,0,0,0.5)] z-50 shrink-0" :class="{ collapsed: sidebarCollapsed }">
    
    <div class="flex items-center justify-center relative mb-6 min-h-[48px] transition-all duration-300">
      <template v-if="!sidebarCollapsed">
        <img src="../assets/images/logo.png" alt="BetGenius" class="h-10 object-contain drop-shadow-[0_0_10px_rgba(140,199,255,0.3)]" @error="fallbackLogo = true" v-if="!fallbackLogo" />
        <span v-else class="font-jersey text-3xl text-white tracking-widest truncate drop-shadow-md">BET<span class="text-bet-primary">GENIUS</span></span>
      </template>
      
      <template v-else>
        <span class="font-jersey text-3xl text-white tracking-widest drop-shadow-md">B<span class="text-bet-primary">G</span></span>
      </template>
      
      <button class="toggle-btn desktop-only" @click="sidebarCollapsed = !sidebarCollapsed">
        <ChevronRight v-if="sidebarCollapsed" :size="16" />
        <ChevronLeft v-else :size="16" />
      </button>
    </div>

    <div class="user-badge mb-4 transition-all" :class="sidebarCollapsed ? 'justify-center p-2' : 'p-3'">
      <div class="sidebar-avatar shrink-0 overflow-hidden border-2" :style="{ borderColor: usuarioLogado?.avatar ? 'var(--bet-primary)' : 'rgba(140, 199, 255, 0.2)' }">
        <img v-if="usuarioLogado?.avatar" :src="usuarioLogado.avatar" alt="Avatar" class="w-full h-full object-cover" />
        <User v-else :size="18" class="text-bet-primary" />
      </div>
      
      <div class="flex flex-col overflow-hidden" v-show="!sidebarCollapsed">
        <span class="text-[10px] text-gray-400 font-bold uppercase tracking-wider">{{ saudacao }},</span>
        <span class="font-mono text-sm text-white truncate leading-tight">{{ usuarioLogado?.name || 'Chefe' }}</span>
        <span class="text-[9px] text-bet-primary mt-0.5">{{ usuarioLogado?.role || 'Operador' }}</span>
      </div>
    </div>

    <div class="channel-group mt-2">
      <div class="nav-section-title"><span v-show="!sidebarCollapsed">Módulos Operacionais</span></div>
      
      <div 
        v-for="item in menuItems" 
        :key="item.id"
        class="nav-item group" 
        :class="{ active: abaAtiva === item.id }" 
        @click="$emit('update:abaAtiva', item.id)"
      >
        <component :is="item.icon" :size="18" :class="abaAtiva === item.id ? 'text-bet-primary' : 'text-gray-500 group-hover:text-white transition-colors'" />
        <span class="nav-text" v-show="!sidebarCollapsed">{{ item.label }}</span>
      </div>
    </div>

    <div class="mt-auto flex flex-col w-full">
      <div class="nav-section-title mb-2"><span v-show="!sidebarCollapsed">Sistema</span></div>
      
      <div class="nav-item group cursor-pointer" :class="{ active: abaAtiva === 'config' }" @click="$emit('update:abaAtiva', 'config')">
        <Settings :size="18" :class="abaAtiva === 'config' ? 'text-bet-primary' : 'text-gray-500 group-hover:text-white transition-colors'" />
        <span class="nav-text" v-show="!sidebarCollapsed">Ajustes & Chaves API</span>
      </div>

      <div class="h-px bg-white/5 w-full my-4"></div>

      <div class="nav-item text-red-500 w-full group cursor-pointer hover:bg-red-500/10 hover:border-red-500/20 transition-all" @click="$emit('logout')">
        <LogOut :size="18" class="group-hover:scale-110 transition-transform text-red-500" />
        <span class="nav-text text-red-500 font-bold" v-show="!sidebarCollapsed">Encerrar Sessão</span>
      </div>
    </div>

  </aside>
</template>

<script setup>
import { ref, computed } from 'vue';
import { 
  ChevronLeft, ChevronRight, User, Settings, LogOut, 
  Target, LayoutDashboard, DollarSign, FlaskConical, TrendingUp 
} from 'lucide-vue-next';

const props = defineProps({
  usuarioLogado: { type: Object, required: true },
  abaAtiva: { type: String, required: true }
});

defineEmits(['update:abaAtiva', 'logout']);

const sidebarCollapsed = ref(false);
const fallbackLogo = ref(false); // Caso a imagem logo.png não exista, cai pro texto.

// Lógica humana para a saudação
const saudacao = computed(() => {
  const hora = new Date().getHours();
  if (hora < 12) return 'Bom dia';
  if (hora < 18) return 'Boa tarde';
  return 'Boa noite';
});

const menuItems = [
  { id: 'radar', label: 'Radar HFT', icon: Target },
  { id: 'match-center', label: 'Match Center', icon: LayoutDashboard },
  { id: 'banca', label: 'Gestão de Fundo', icon: DollarSign },
  { id: 'backtest', label: 'Quant Lab', icon: FlaskConical },
  { id: 'sentimento', label: 'Sentiment Engine', icon: TrendingUp }
];
</script>

<style scoped>
.desktop-sidebar { width: 260px; background: rgba(23, 32, 51, 0.85); backdrop-filter: blur(20px); display: flex; flex-direction: column; padding: 30px 20px; transition: 0.3s ease-in-out; border-right: 1px solid var(--border-soft); height: 100vh; }
.desktop-sidebar.collapsed { width: 85px; align-items: center; padding: 30px 10px; }
.user-badge { display: flex; align-items: center; gap: 12px; background: rgba(0,0,0,0.2); border: 1px solid var(--border-soft); border-radius: 12px; }
.sidebar-avatar { width: 36px; height: 36px; border-radius: 10px; background: rgba(140, 199, 255, 0.1); display: flex; justify-content: center; align-items: center; }
.toggle-btn { position: absolute; right: -30px; top: 10px; background: var(--bg-sidebar); border: 1px solid var(--border-soft); color: var(--text-muted); width: 28px; height: 28px; border-radius: 50%; display: flex; justify-content: center; align-items: center; cursor: pointer; z-index: 101; transition: 0.2s; }
.toggle-btn:hover { color: #000; background: var(--bet-primary); border-color: var(--bet-primary); }
.nav-section-title { font-size: 10px; text-transform: uppercase; font-weight: 800; letter-spacing: 1.5px; margin-bottom: 15px; margin-top: 20px; color: rgba(255,255,255,0.3); padding-left: 10px; }
.nav-item { padding: 14px 15px; border-radius: 12px; margin-bottom: 5px; color: var(--text-muted); display: flex; align-items: center; gap: 14px; cursor: pointer; font-weight: 600; font-size: 14px; transition: all 0.2s ease; border: 1px solid transparent; }
.nav-item:hover { background: rgba(140, 199, 255, 0.05); border-color: rgba(140, 199, 255, 0.1); }
.nav-item.active { background: rgba(140, 199, 255, 0.1); color: white; border-color: var(--border-soft); box-shadow: inset 3px 0 0 var(--bet-primary); }
.nav-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

@media (max-width: 1024px) {
  .desktop-sidebar { position: fixed; transform: translateX(-100%); z-index: 1000; height: 100%; }
  .desktop-only { display: none !important; }
}
</style>