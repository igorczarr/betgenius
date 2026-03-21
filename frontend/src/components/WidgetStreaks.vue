<template>
  <WidgetCard titulo="Radar de Streaks">
    
    <template #icone>
      <Flame :size="16" color="var(--bet-warning)" />
    </template>

    <template #acoes>
      <select class="glass-input-premium mb-0 py-1 px-3 text-xs" style="min-width: 120px; padding: 6px 12px; height: auto;">
        <option>Top Streaks (Todas)</option>
        <option>Over 2.5 Gols</option>
        <option>Vitórias Seguidas</option>
        <option>Ambas Marcam (BTTS)</option>
      </select>
    </template>

    <div class="flex flex-col gap-3">
      
      <div v-for="streak in streaksMock" :key="streak.id" 
           class="p-4 rounded-xl border flex items-center justify-between"
           style="border-color: var(--border-soft); background: rgba(255,255,255,0.02);">
        
        <div>
          <div class="flex items-center gap-2 mb-2">
            <span class="text-[10px] font-mono tracking-widest uppercase py-1 px-2 rounded font-bold"
                  :style="{ color: streak.cor, backgroundColor: streak.cor + '20' }">
              {{ streak.tipo }}
            </span>
            <span class="text-[10px] text-gray-400 font-mono flex items-center gap-1">
               <TrendingUp :size="12" /> {{ streak.jogos }} JOGOS
            </span>
          </div>
          
          <div class="font-bold text-sm text-white">
            {{ streak.equipe }} <span style="color: var(--text-muted); font-size: 11px; font-weight: normal;">vs {{ streak.adversario }}</span>
          </div>
        </div>

        <button class="w-12 h-10 rounded-lg flex flex-col items-center justify-center transition-all border cursor-pointer group"
                style="background: transparent; border-color: rgba(255,255,255,0.1);"
                onmouseover="this.style.borderColor='var(--bet-green)';"
                onmouseout="this.style.borderColor='rgba(255,255,255,0.1)';">
          <span class="text-xs font-mono font-bold text-gray-300 group-hover:text-green-400 transition-colors">
            {{ streak.odd }}
          </span>
        </button>

      </div>

    </div>
  </WidgetCard>
</template>

<script setup>
import { Flame, TrendingUp } from 'lucide-vue-next';
import WidgetCard from './WidgetCard.vue';

// Base de Dados Simulada (Machine Learning / Extrator apontará as anomalias aqui)
const streaksMock = [
  { id: 1, equipe: "B. Leverkusen", adversario: "Köln", tipo: "INVENCIBILIDADE", jogos: 32, odd: "1.18", cor: "#10B981" }, // Verde
  { id: 2, equipe: "PSV Eindhoven", adversario: "Ajax", tipo: "OVER 2.5", jogos: 11, odd: "1.45", cor: "#F59E0B" }, // Laranja/Amarelo
  { id: 3, equipe: "Sheffield Utd", adversario: "Arsenal", tipo: "SOFREU GOL", jogos: 24, odd: "1.05", cor: "#EF4444" }, // Vermelho
  { id: 4, equipe: "Aston Villa", adversario: "Spurs", tipo: "BTTS (AMBAS)", jogos: 8, odd: "1.52", cor: "#8B5CF6" }, // Roxo
];
</script>