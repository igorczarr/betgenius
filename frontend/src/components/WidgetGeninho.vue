<template>
  <WidgetCard titulo="Geninho Intel (Alertas)">
    <template #icone>
      <Radio :size="16" color="var(--bet-primary)" />
    </template>

    <div class="relative border-l border-gray-700 ml-3 pl-4 flex flex-col gap-5 mt-2">
      <div v-for="alerta in alertasMock" :key="alerta.id" class="relative">
        <div class="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full border-2 border-surface" :style="{ backgroundColor: alerta.cor }"></div>
        
        <div class="flex items-center gap-2 mb-1">
          <span class="text-[10px] font-bold uppercase tracking-wider" :style="{ color: alerta.cor }">{{ alerta.tipo }}</span>
          <span class="text-[9px] text-gray-500 font-mono">{{ alerta.tempo }}</span>
        </div>
        <p class="text-xs text-gray-300 leading-relaxed">
          <strong class="text-white">{{ alerta.time }}:</strong> {{ alerta.texto }}
        </p>
      </div>
    </div>
  </WidgetCard>
</template>

<script setup>
import { Radio } from 'lucide-vue-next';
import WidgetCard from './WidgetCard.vue';

const alertasMock = [
  { id: 1, tipo: "CRÍTICO", tempo: "Há 2 min", time: "Man City", texto: "Haaland não desceu do ônibus. Provável corte por lesão. Risco alto para mercado de gols.", cor: "#EF4444" },
  { id: 2, tipo: "CLIMA", tempo: "Há 14 min", time: "B. Munique", texto: "Forte tempestade de neve confirmada em Munique. Tendência pesada para Under.", cor: "#8cc7ff" },
  { id: 3, tipo: "ESCALAÇÃO", tempo: "Há 28 min", time: "Real Madrid", texto: "Ancelotti poupando Vini Jr e Bellingham. Linha de AH -1.5 perdeu valor.", cor: "#F59E0B" },
];
</script>