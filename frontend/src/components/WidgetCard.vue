<template>
  <div v-if="isMaximized" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-[9998]" @click="toggleMaximize"></div>

  <div 
    class="glass-widget flex flex-col transition-all duration-300 ease-in-out border border-white/5"
    :class="{
      'fixed inset-6 z-[9999] shadow-[0_30px_60px_rgba(0,0,0,0.8)]': isMaximized,
      'min-h-[380px] h-full': !isMaximized && !isMinimized,
      'h-auto min-h-0': isMinimized
    }"
  >
    <div class="px-5 py-4 flex justify-between items-center border-b border-white/10 bg-black/40 rounded-t-2xl select-none">
      
      <h3 @dblclick="toggleMaximize" class="drag-handle cursor-move font-bold text-sm uppercase tracking-wider flex items-center gap-2 text-white hover:text-blue-400 transition-colors">
        <slot name="icone"></slot>
        {{ titulo }}
      </h3>
      
      <div class="flex gap-3 items-center">
        <div v-show="!isMinimized" class="flex items-center gap-2">
          <slot name="acoes"></slot>
        </div>
        
        <div class="flex items-center gap-1 border-l border-white/10 pl-3">
          <button @click="toggleMinimize" class="text-gray-500 hover:text-white p-1 rounded transition-colors" :title="isMinimized ? 'Expandir' : 'Minimizar'">
            <ChevronDown v-if="isMinimized" :size="16" />
            <ChevronUp v-else :size="16" />
          </button>
          
          <button @click="toggleMaximize" class="text-gray-500 hover:text-white p-1 rounded transition-colors" :title="isMaximized ? 'Restaurar' : 'Maximizar tela cheia'">
            <Minimize2 v-if="isMaximized" :size="16" />
            <Maximize2 v-else :size="16" />
          </button>
        </div>
      </div>

    </div>
    
    <div v-show="!isMinimized" class="p-5 flex-1 overflow-y-auto custom-scrollbar">
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { ChevronUp, ChevronDown, Maximize2, Minimize2 } from 'lucide-vue-next';

defineProps({
  titulo: { type: String, required: true }
});

// O "Cérebro" do componente que guarda o estado geométrico dele na tela
const isMinimized = ref(false);
const isMaximized = ref(false);

const toggleMinimize = () => {
  if (isMaximized.value) isMaximized.value = false; // Tira do maximizado se for minimizar
  isMinimized.value = !isMinimized.value;
};

const toggleMaximize = () => {
  if (isMinimized.value) isMinimized.value = false; // Tira do minimizado se for maximizar
  isMaximized.value = !isMaximized.value;
};
</script>

<style scoped>
.glass-widget { 
  background: rgba(18, 25, 39, 0.85); 
  backdrop-filter: blur(20px); 
  border-radius: 16px;
}

/* Scrollbar S-Tier para não poluir tabelas de dados */
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(59, 130, 246, 0.5); }
</style>