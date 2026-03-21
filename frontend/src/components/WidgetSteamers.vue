<template>
  <WidgetCard titulo="Steamers (Smart Money)">
    <template #icone>
      <Zap :size="16" color="var(--bet-warning)" />
    </template>
    <template #acoes>
      <span class="text-[10px] text-green-400 font-mono flex items-center gap-1 bg-green-400/10 px-2 py-1 rounded">
        <div class="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse"></div> AO VIVO
      </span>
    </template>

    <div class="flex flex-col gap-3">
      <div v-for="steam in steamersMock" :key="steam.id" class="p-3 rounded-lg border border-gray-700/50 bg-black/20 hover:border-[#8cc7ff]/50 transition-colors group">
        <div class="flex justify-between items-center mb-2">
          <span class="text-xs font-bold text-white">{{ steam.jogo }}</span>
          <span class="text-[10px] bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded font-mono font-bold">{{ steam.drop }}%</span>
        </div>
        <div class="flex justify-between items-center">
          <span class="text-[10px] text-gray-400 uppercase tracking-wider">{{ steam.mercado }}</span>
          <div class="flex items-center gap-2 font-mono text-sm">
            <span class="text-gray-500 line-through decoration-red-500/50">{{ steam.oddAntiga }}</span>
            <ArrowRight :size="12" class="text-gray-600" />
            <span class="text-bet-primary font-bold">{{ steam.oddNova }}</span>
          </div>
        </div>
      </div>
    </div>
  </WidgetCard>
</template>

<script setup>
import { Zap, ArrowRight } from 'lucide-vue-next';
import WidgetCard from './WidgetCard.vue';

const steamersMock = [
  { id: 1, jogo: "Boca Jrs vs River", mercado: "Under 2.5", oddAntiga: "1.90", oddNova: "1.65", drop: "-13" },
  { id: 2, jogo: "Milan vs Napoli", mercado: "Napoli AH +0.5", oddAntiga: "2.10", oddNova: "1.82", drop: "-13" },
  { id: 3, jogo: "Chelsea vs Fulham", mercado: "Ambas Marcam: Não", oddAntiga: "1.95", oddNova: "1.78", drop: "-8" },
];
</script>