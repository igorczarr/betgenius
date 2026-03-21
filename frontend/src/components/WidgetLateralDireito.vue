<template>
  <div class="h-full flex flex-col bg-surface border-l" style="border-color: var(--border-soft);">
    
    <div class="p-4 border-b shrink-0" style="border-color: var(--border-soft); background: rgba(0,0,0,0.15);">
      <div class="flex p-1 rounded-lg" style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-soft);">
        <button 
          @click="abaAtual = 'jogos'"
          class="flex-1 py-1.5 text-[11px] uppercase tracking-wider font-bold rounded transition-colors"
          :class="abaAtual === 'jogos' ? 'bg-[#8cc7ff]/10 text-[#8cc7ff]' : 'text-gray-500 hover:text-gray-300'"
        >
          <CalendarDays :size="14" class="inline mb-0.5 mr-1"/> Jogos do Dia
        </button>
        <button 
          @click="abaAtual = 'streaks'"
          class="flex-1 py-1.5 text-[11px] uppercase tracking-wider font-bold rounded transition-colors"
          :class="abaAtual === 'streaks' ? 'bg-[#8cc7ff]/10 text-[#8cc7ff]' : 'text-gray-500 hover:text-gray-300'"
        >
          <Flame :size="14" class="inline mb-0.5 mr-1"/> Streaks
        </button>
      </div>
      
      <div class="mt-3">
        <select class="glass-input-premium mb-0 py-1.5 px-3 text-xs w-full" style="padding: 6px 12px; height: auto;">
          <option v-if="abaAtual === 'jogos'">Todas as Ligas</option>
          <option v-if="abaAtual === 'jogos'">Premier League</option>
          <option v-if="abaAtual === 'streaks'">Top Streaks (Geral)</option>
          <option v-if="abaAtual === 'streaks'">Apenas Over 2.5</option>
        </select>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto hide-scrollbar p-4 flex flex-col gap-3">
      
      <template v-if="abaAtual === 'jogos'">
        <div v-for="jogo in jogosMock" :key="'j'+jogo.id" 
             class="p-3 rounded-xl border transition-all cursor-pointer group hover:border-[#8cc7ff]"
             style="border-color: var(--border-soft); background: rgba(255,255,255,0.02);">
          <span class="text-[10px] font-mono tracking-widest uppercase mb-1 block text-[#8cc7ff]">
            {{ jogo.campeonato }} • {{ jogo.hora }}
          </span>
          <div class="font-bold text-sm text-white flex justify-between items-center">
            <span>{{ jogo.casa }} <span class="text-gray-500 text-[10px] mx-1">VS</span> {{ jogo.fora }}</span>
            <button class="text-gray-500 hover:text-[#8cc7ff] transition-colors"><Plus :size="16"/></button>
          </div>
        </div>
      </template>

      <template v-if="abaAtual === 'streaks'">
        <div v-for="streak in streaksMock" :key="'s'+streak.id" 
             class="p-3 rounded-xl border flex flex-col gap-2"
             style="border-color: var(--border-soft); background: rgba(255,255,255,0.02);">
          <div class="flex justify-between items-start">
            <span class="text-[10px] font-mono tracking-widest uppercase py-0.5 px-1.5 rounded font-bold"
                  :style="{ color: streak.cor, backgroundColor: streak.cor + '20' }">
              {{ streak.tipo }}
            </span>
            <span class="text-xs font-mono font-bold text-gray-300">{{ streak.odd }}</span>
          </div>
          <div class="font-bold text-sm text-white">
            {{ streak.equipe }} <span class="text-gray-500 font-normal text-xs">vs {{ streak.adversario }}</span>
          </div>
          <div class="text-[10px] text-gray-400 font-mono flex items-center gap-1">
             <TrendingUp :size="12" /> {{ streak.jogos }} JOGOS CONSECUTIVOS
          </div>
        </div>
      </template>

    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { CalendarDays, Flame, Plus, TrendingUp } from 'lucide-vue-next';

const abaAtual = ref('jogos'); // Começa mostrando a aba de jogos

const jogosMock = [
  { id: 1, campeonato: "Premier League", hora: "16:00", casa: "Arsenal", fora: "Liverpool" },
  { id: 2, campeonato: "Brasileirão", hora: "21:30", casa: "Flamengo", fora: "Palmeiras" },
  { id: 3, campeonato: "La Liga", hora: "17:00", casa: "Real Madrid", fora: "Sevilla" },
  { id: 4, campeonato: "Bundesliga", hora: "15:45", casa: "B. Munique", fora: "Dortmund" },
  { id: 5, campeonato: "Serie A TIM", hora: "16:45", casa: "Juventus", fora: "Milan" }
];

const streaksMock = [
  { id: 1, equipe: "B. Leverkusen", adversario: "Köln", tipo: "INVENCIBILIDADE", jogos: 32, odd: "1.18", cor: "#8cc7ff" },
  { id: 2, equipe: "PSV Eindhoven", adversario: "Ajax", tipo: "OVER 2.5", jogos: 11, odd: "1.45", cor: "#F59E0B" },
  { id: 3, equipe: "Sheffield Utd", adversario: "Arsenal", tipo: "SOFREU GOL", jogos: 24, odd: "1.05", cor: "#EF4444" },
];
</script>

<style scoped>
.bg-surface { background: var(--bg-surface); }
</style>