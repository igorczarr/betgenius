<template>
  <WidgetCard titulo="Gold Picks (Confiança IA > 85%)">
    <template #icone>
      <Award :size="16" color="var(--bet-warning)" />
    </template>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div v-for="(pick, index) in goldPicksMock" :key="index" class="p-4 rounded-xl relative overflow-hidden group border border-yellow-500/30 bg-gradient-to-br from-yellow-500/5 to-transparent">
        
        <div class="absolute top-0 right-0 bg-yellow-500/20 text-yellow-500 text-[10px] font-bold px-2 py-1 rounded-bl-lg font-mono">
          EV +{{ pick.ev }}%
        </div>

        <span class="text-[10px] text-gray-400 font-mono uppercase tracking-widest block mb-1">{{ pick.liga }}</span>
        <h4 class="text-sm font-bold text-white mb-3">{{ pick.jogo }}</h4>
        
        <div class="flex justify-between items-end">
          <div>
            <span class="text-[10px] text-gray-500 block uppercase">Mercado IA</span>
            <span class="text-xs font-bold text-yellow-400">{{ pick.mercado }}</span>
          </div>
          <div class="text-right">
            <span class="text-[10px] text-gray-500 block uppercase">Odd / Stake</span>
            <span class="text-sm font-mono font-bold text-white">{{ pick.odd }} <span class="text-gray-500 text-[10px]">({{ pick.stake }}u)</span></span>
          </div>
        </div>

      </div>
    </div>
  </WidgetCard>
</template>

<script setup>
import { Award } from 'lucide-vue-next';
import WidgetCard from './WidgetCard.vue';

const goldPicksMock = [
  { liga: "Champions League", jogo: "Man City vs Inter", mercado: "Man City AH -1.0", ev: "16.8", odd: "1.95", stake: "2" },
  { liga: "Premier League", jogo: "Aston Villa vs Spurs", mercado: "Over 2.5 Gols", ev: "14.2", odd: "1.72", stake: "1.5" },
  { liga: "La Liga", jogo: "Atl. Madrid vs Betis", mercado: "Casa Vence", ev: "12.5", odd: "1.65", stake: "1" },
];
</script>