<template>
  <WidgetCard titulo="In-Play Scout (Ao Vivo)">
    <template #icone>
      <Activity :size="16" color="#EF4444" />
    </template>

    <div class="flex flex-col gap-4">
      <div v-for="jogo in inplayMock" :key="jogo.id" class="p-3 rounded-lg bg-black/20 border border-gray-800">
        
        <div class="flex justify-between items-center mb-2">
          <div class="flex items-center gap-2">
            <span class="text-xs font-mono font-bold text-red-500 animate-pulse">{{ jogo.tempo }}'</span>
            <span class="text-xs font-bold text-white">{{ jogo.casa }} {{ jogo.placarCasa }}x{{ jogo.placarFora }} {{ jogo.fora }}</span>
          </div>
          <button class="text-[10px] bg-[#8cc7ff]/10 text-[#8cc7ff] px-2 py-1 rounded font-bold uppercase tracking-wider hover:bg-[#8cc7ff]/20 transition-colors">
            {{ jogo.sugestao }}
          </button>
        </div>

        <div class="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden flex">
          <div class="h-full bg-bet-primary" :style="{ width: jogo.pressaoCasa + '%' }"></div>
          <div class="h-full bg-gray-600" :style="{ width: jogo.pressaoFora + '%' }"></div>
        </div>
        <div class="flex justify-between mt-1">
          <span class="text-[9px] text-gray-500 font-mono">Pressão: {{ jogo.pressaoCasa }}%</span>
          <span class="text-[9px] text-gray-500 font-mono">{{ jogo.pressaoFora }}%</span>
        </div>

      </div>
    </div>
  </WidgetCard>
</template>

<script setup>
import { Activity } from 'lucide-vue-next';
import WidgetCard from './WidgetCard.vue';

const inplayMock = [
  { id: 1, tempo: "72", casa: "Arsenal", fora: "Everton", placarCasa: 0, placarFora: 0, pressaoCasa: 85, pressaoFora: 15, sugestao: "Back Arsenal" },
  { id: 2, tempo: "35", casa: "Girona", fora: "Getafe", placarCasa: 0, placarFora: 1, pressaoCasa: 70, pressaoFora: 30, sugestao: "Over 1.5 HT" },
];
</script>