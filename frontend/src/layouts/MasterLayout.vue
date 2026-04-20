<template>
  <div class="app-master-layout">
    
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
              <span class="font-mono text-bet-primary text-xl flex items-center gap-2">
                <div class="pulse-dot"></div> 12
              </span>
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
          <div class="p-3 hover:bg-white/5 rounded-lg cursor-pointer flex items-center gap-3 text-gray-300" @click="router.push('/match-center'); isCommandOpen = false;">
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
import { Search, LayoutDashboard, Zap } from 'lucide-vue-next'; 

const router = useRouter();

// Lógica do Command Palette
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
</script>

<style scoped>
/* HUD Estilos */
.top-nav-glass { 
  background: rgba(18, 25, 39, 0.85); 
  backdrop-filter: blur(24px); 
}

.pulse-dot { 
  width: 10px; 
  height: 10px; 
  background: var(--bet-primary); 
  border-radius: 50%; 
  animation: pulse 2s infinite; 
  box-shadow: 0 0 10px var(--bet-primary); 
}

.text-muted { color: var(--text-muted); }
.text-success { color: #10B981; }

.bg-radial-gradient { 
  background: radial-gradient(circle at top center, rgba(37, 50, 76, 0.3) 0%, var(--bg-app) 70%); 
}

.fade-in-up {
  animation: fadeInUp 0.4s ease-out;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Transições de página */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>