<template>
  <WidgetCard titulo="Smart Ticket Builder">
    
    <template #icone>
      <Receipt :size="16" color="var(--bet-green)" />
    </template>

    <template #acoes>
      <div class="flex p-1 rounded-lg" style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-soft);">
        <button 
          @click="riscoAtual = 'conservador'"
          class="px-3 py-1 text-[10px] uppercase tracking-wider font-bold rounded transition-colors"
          :class="riscoAtual === 'conservador' ? 'bg-green-600/20 text-green-400' : 'text-gray-500 hover:text-gray-300'"
        >Seguro</button>
        <button 
          @click="riscoAtual = 'moderado'"
          class="px-3 py-1 text-[10px] uppercase tracking-wider font-bold rounded transition-colors"
          :class="riscoAtual === 'moderado' ? 'bg-yellow-600/20 text-yellow-400' : 'text-gray-500 hover:text-gray-300'"
        >Mod</button>
        <button 
          @click="riscoAtual = 'agressivo'"
          class="px-3 py-1 text-[10px] uppercase tracking-wider font-bold rounded transition-colors"
          :class="riscoAtual === 'agressivo' ? 'bg-red-600/20 text-red-400' : 'text-gray-500 hover:text-gray-300'"
        >Agr</button>
      </div>
    </template>

    <div class="flex flex-col h-full justify-between">
      
      <div class="flex-1 overflow-y-auto hide-scrollbar pr-1 mb-4 flex flex-col gap-2">
        
        <div v-for="(selecao, index) in bilheteMock" :key="index" 
             class="p-3 rounded-lg border group relative"
             style="border-color: var(--border-soft); background: rgba(255,255,255,0.02);">
          
          <div class="flex justify-between items-start mb-1">
            <span class="text-xs font-bold text-white">{{ selecao.jogo }}</span>
            <span class="text-xs font-mono font-bold" style="color: var(--bet-green);">{{ selecao.odd }}</span>
          </div>
          
          <div class="flex justify-between items-center">
            <span class="text-[10px] text-gray-400 uppercase tracking-wider">{{ selecao.mercado }}</span>
            <button class="text-gray-600 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100">
              <XCircle :size="14" />
            </button>
          </div>
        </div>

        <button class="w-full py-2 rounded-lg border border-dashed border-gray-700 text-gray-500 text-xs font-bold uppercase tracking-wider hover:border-gray-500 hover:text-gray-300 transition-colors flex items-center justify-center gap-2 mt-1">
          <Plus :size="14" /> Adicionar Mercado
        </button>
      </div>

      <div class="pt-4 border-t" style="border-color: var(--border-soft);">
        <div class="flex justify-between items-center mb-1">
          <span class="text-xs text-gray-400 uppercase tracking-widest">Prob. Combinada</span>
          <span class="text-sm font-mono text-white">61.4%</span>
        </div>
        <div class="flex justify-between items-end mb-4">
          <span class="text-xs text-gray-400 uppercase tracking-widest">Odd Alvo</span>
          <span class="text-2xl font-mono font-bold" style="color: var(--bet-green);">1.84</span>
        </div>

        <button class="btn-neon-green w-full py-3" style="font-size: 14px; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.15);">
          <ExternalLink :size="16" style="margin-right: 8px;" />
          Executar na Broker
        </button>
      </div>

    </div>
  </WidgetCard>
</template>

<script setup>
import { ref } from 'vue';
import { Receipt, XCircle, Plus, ExternalLink } from 'lucide-vue-next';
import WidgetCard from './WidgetCard.vue';

// Controle do perfil de risco do bilhete
const riscoAtual = ref('conservador');

// Dados simulados das "pernas" do nosso bilhete de odd 1.84
const bilheteMock = [
  { jogo: "Arsenal vs Liverpool", mercado: "Over 1.5 Gols", odd: "1.22" },
  { jogo: "Flamengo vs Palmeiras", mercado: "Dupla Chance (1X)", odd: "1.28" },
  { jogo: "Real Madrid vs Sevilla", mercado: "Casa Vence", odd: "1.18" }
];
</script>