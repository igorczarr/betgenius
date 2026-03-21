<template>
  <WidgetCard titulo="Scanner de Valor (+EV)">
    
    <template #icone>
      <Crosshair :size="16" color="var(--bet-green)" />
    </template>

    <template #acoes>
      <button class="bg-gray-800 hover:bg-gray-700 text-xs text-white px-3 py-1 rounded border border-gray-600 transition-colors">
        Exportar Dados
      </button>
    </template>

    <div class="w-full overflow-x-auto">
      <table class="w-full text-left border-collapse">
        <thead>
          <tr class="border-b border-gray-800 text-xs text-gray-400 uppercase tracking-wider font-mono">
            <th class="pb-3 font-medium">Partida</th>
            <th class="pb-3 font-medium">Mercado</th>
            <th class="pb-3 font-medium text-center">Prob. IA</th>
            <th class="pb-3 font-medium text-center">Odd Justa</th>
            <th class="pb-3 font-medium text-center">Odd Casa</th>
            <th class="pb-3 font-medium text-center">EV (%)</th>
            <th class="pb-3 font-medium text-right">Ação</th>
          </tr>
        </thead>
        <tbody class="text-sm">
          
          <tr v-for="opp in oportunidadesMock" :key="opp.id" 
              class="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors group">
            
            <td class="py-3">
              <div class="font-bold text-gray-200">{{ opp.jogo }}</div>
              <div class="text-[10px] text-gray-500 font-mono">{{ opp.liga }} • {{ opp.hora }}</div>
            </td>
            
            <td class="py-3">
              <span class="bg-gray-800 text-gray-300 text-xs px-2 py-1 rounded border border-gray-700">
                {{ opp.mercado }}
              </span>
            </td>
            
            <td class="py-3 text-center font-mono font-bold" style="color: var(--bet-green);">
              {{ opp.probabilidade }}%
            </td>
            
            <td class="py-3 text-center font-mono text-gray-400">
              {{ opp.oddJusta }}
            </td>
            
            <td class="py-3 text-center font-mono font-bold text-white">
              <span class="bg-green-900/30 border border-green-800 px-2 py-1 rounded text-green-400">
                {{ opp.oddCasa }}
              </span>
            </td>
            
            <td class="py-3 text-center font-mono font-bold text-yellow-400">
              +{{ opp.ev }}%
            </td>
            
            <td class="py-3 text-right">
              <button class="bg-gray-800 hover:bg-bet-green hover:text-black text-gray-400 px-3 py-1.5 rounded transition-colors">
                <Plus :size="16" />
              </button>
            </td>

          </tr>

        </tbody>
      </table>
    </div>

  </WidgetCard>
</template>

<script setup>
import { Crosshair, Plus } from 'lucide-vue-next';
import WidgetCard from './WidgetCard.vue';

// Nossos cálculos matemáticos de regressão refletidos aqui na simulação
const oportunidadesMock = [
  { id: 1, jogo: "Man. City vs Inter", liga: "CHAMPIONS", hora: "16:00", mercado: "Over 1.5 Gols", probabilidade: 88, oddJusta: "1.13", oddCasa: "1.32", ev: "16.8" },
  { id: 2, jogo: "Brighton vs Luton", liga: "PREMIER", hora: "11:00", mercado: "Casa Vence", probabilidade: 82, oddJusta: "1.21", oddCasa: "1.40", ev: "15.7" },
  { id: 3, jogo: "Girona vs Almeria", liga: "LA LIGA", hora: "14:30", mercado: "Handicap Asiático -1.0", probabilidade: 75, oddJusta: "1.33", oddCasa: "1.55", ev: "16.5" },
];
</script>