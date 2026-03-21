<template>
  <WidgetCard titulo="Jogos Mapeados (Hoje)">
    
    <template #icone>
      <CalendarDays :size="16" color="var(--bet-green)" />
    </template>

    <template #acoes>
      <select class="glass-input-premium mb-0 py-1 px-3 text-xs" style="min-width: 140px; padding: 6px 12px; height: auto;">
        <option>Todas as Ligas</option>
        <option>Premier League</option>
        <option>Brasileirão Série A</option>
        <option>La Liga</option>
      </select>
    </template>

    <div class="flex flex-col gap-3">
      
      <div v-for="jogo in jogosMock" :key="jogo.id" 
           class="p-4 rounded-xl border transition-all cursor-pointer group flex items-center justify-between"
           style="border-color: var(--border-soft); background: rgba(255,255,255,0.02);"
           onmouseover="this.style.borderColor='var(--bet-green)'; this.style.background='rgba(16, 185, 129, 0.05)';"
           onmouseout="this.style.borderColor='var(--border-soft)'; this.style.background='rgba(255,255,255,0.02)';">
        
        <div>
          <span class="text-[10px] font-mono tracking-widest uppercase mb-1 block" style="color: var(--bet-green);">
            {{ jogo.campeonato }} • {{ jogo.hora }}
          </span>
          <div class="font-bold text-sm text-white flex items-center gap-2">
            {{ jogo.casa }} <span style="color: var(--text-muted); font-size: 10px;">VS</span> {{ jogo.fora }}
          </div>
        </div>

        <button class="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
                style="background: rgba(255,255,255,0.05); color: var(--text-muted);"
                onmouseover="this.style.background='var(--bet-green)'; this.style.color='#000';"
                onmouseout="this.style.background='rgba(255,255,255,0.05)'; this.style.color='var(--text-muted)';">
          <Plus :size="18" />
        </button>

      </div>

    </div>
  </WidgetCard>
</template>

<script setup>
import { CalendarDays, Plus } from 'lucide-vue-next';
import WidgetCard from './WidgetCard.vue';

// Nossos dados simulados (No futuro, o Banco de Dados preencherá isso)
const jogosMock = [
  { id: 1, campeonato: "Premier League", hora: "16:00", casa: "Arsenal", fora: "Liverpool" },
  { id: 2, campeonato: "Brasileirão", hora: "21:30", casa: "Flamengo", fora: "Palmeiras" },
  { id: 3, campeonato: "La Liga", hora: "17:00", casa: "Real Madrid", fora: "Sevilla" },
  { id: 4, campeonato: "Bundesliga", hora: "15:45", casa: "B. Munique", fora: "Dortmund" },
  { id: 5, campeonato: "Serie A TIM", hora: "16:45", casa: "Juventus", fora: "Milan" }
];
</script>