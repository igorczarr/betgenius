<template>
  <div v-if="isMaximized" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-[9998]" @click="toggleMaximize"></div>

  <div 
    class="glass-card flex flex-col bg-surface transition-all duration-300 ease-in-out"
    :class="{
      'fixed inset-6 z-[9999] shadow-2xl': isMaximized,
      'min-h-[380px] h-full': !isMaximized && !isMinimized,
      'h-auto min-h-0': isMinimized
    }"
  >
    <div class="px-5 py-4 flex justify-between items-center border-b border-gray-800/50 bg-black/20 select-none">
      
      <h3 @click="toggleMinimize" class="drag-handle cursor-move font-bold text-sm uppercase tracking-wider flex items-center gap-2 text-white hover:text-bet-primary transition-colors">
        <slot name="icone"></slot>
        {{ titulo }}
      </h3>
      
      <div class="flex gap-3 items-center">
        <div v-show="!isMinimized" class="flex items-center gap-2">
          <slot name="acoes"></slot>
        </div>
        
        <div class="flex items-center gap-1 border-l border-gray-700 pl-3">
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
    
    <div v-show="!isMinimized" class="p-5 flex-1 overflow-y-auto hide-scrollbar">
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

// O "Cérebro" do componente que guarda o estado dele na tela
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
.bg-surface { background: var(--bg-surface); }
.text-bet-green { color: var(--bet-green); }
</style>