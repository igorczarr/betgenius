<template>
  <div class="fixed inset-0 w-full h-full bg-[#0b0f19] flex flex-col overflow-hidden m-0 p-0">
    
    <AppNavigation 
      :abaAtiva="abaAtiva" 
      @update:abaAtiva="navegarPara" 
      @openSearch="toggleCommandPalette"
      @logout="fazerLogout"
    />

    <main class="flex-1 w-full h-full flex flex-col relative overflow-hidden bg-radial-gradient pt-20 pb-28">
      
      <div class="flex-1 w-full h-full overflow-hidden relative">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" class="w-full h-full max-w-none" />
          </transition>
        </router-view>
      </div>

    </main>

    <div v-if="isCommandOpen" class="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-md flex items-start justify-center pt-[10vh]" @click.self="toggleCommandPalette">
      <div class="w-full max-w-2xl mx-4 bg-[#121927] border border-white/10 rounded-2xl shadow-[0_30px_60px_rgba(0,0,0,0.9)] overflow-hidden fade-in-up">
        <div class="flex items-center p-4 border-b border-white/10">
          <Search :size="20" class="text-bet-primary mr-3" />
          <input type="text" class="bg-transparent border-none text-white text-lg w-full focus:outline-none placeholder-gray-500 font-mono" placeholder="O que você deseja operar?" autofocus ref="searchInput" />
          <span class="text-[10px] text-gray-500 font-mono bg-white/5 px-2 py-1 rounded border border-white/10">ESC</span>
        </div>
        <div class="p-2">
          <div class="text-[10px] text-gray-500 uppercase tracking-widest p-2 font-bold">Ações Rápidas</div>
          <div class="p-3 hover:bg-white/5 rounded-lg cursor-pointer flex items-center gap-3 text-gray-300 transition-colors" @click="router.push('/match-center'); isCommandOpen = false;">
            <LayoutDashboard :size="16" class="text-bet-primary"/> Ir para Match Center
          </div>
          <div class="p-3 hover:bg-white/5 rounded-lg cursor-pointer flex items-center gap-3 text-gray-300 transition-colors">
            <Zap :size="16" class="text-yellow-500"/> Ver Steamers (Dinheiro Inteligente)
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { Search, LayoutDashboard, Zap } from 'lucide-vue-next'; 

// Importa a nova navegação S-Tier mantendo o nome do arquivo original
import AppNavigation from '../components/AppSidebar.vue'; 

const router = useRouter();
const route = useRoute();

// Sincroniza a aba ativa do Dock Flutuante com a URL atual
const abaAtiva = computed(() => {
  return route.name || 'radar';
});

// Transforma o clique no Dock em navegação real
const navegarPara = (id) => {
  if (id === 'radar') {
    router.push('/');
  } else {
    router.push(`/${id}`);
  }
};

const fazerLogout = () => {
  localStorage.removeItem('betgenius_token');
  localStorage.removeItem('betgenius_user');
  router.push('/login');
};

// ==========================================
// Lógica Intacta do Command Palette
// ==========================================
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
/* Background e Layout Geral */
.bg-radial-gradient { 
  background: radial-gradient(circle at top center, rgba(140, 199, 255, 0.05) 0%, transparent 70%); 
}

.fade-in-up {
  animation: fadeInUp 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

/* Transições de página perfeitas (Out-In) */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.fade-enter-from { opacity: 0; transform: translateY(10px); }
.fade-leave-to { opacity: 0; transform: translateY(-10px); }
</style>