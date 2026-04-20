<template>
  <WidgetCard titulo="Ticket Builder (SGP & Accumulators)">
    <template #icone>
      <Award :size="16" class="text-yellow-500" />
    </template>
    
    <div class="flex flex-col xl:flex-row gap-6">
      
      <div class="w-full xl:w-2/3 flex flex-col gap-4">
        <h3 class="text-xs font-bold text-gray-400 uppercase tracking-widest border-b border-white/10 pb-2">Oportunidades Mapeadas (+EV)</h3>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 overflow-y-auto max-h-[500px] custom-scrollbar pr-2">
          <div 
            v-for="(pick, index) in goldPicks" 
            :key="index" 
            @click="toggleSelection(pick)"
            :class="[
              'p-4 rounded-xl relative overflow-hidden group border transition-all cursor-pointer select-none',
              isSelected(pick) ? 'border-yellow-500 bg-yellow-500/10 shadow-[0_0_20px_rgba(234,179,8,0.2)]' : 'border-white/10 bg-black/20 hover:border-yellow-500/50'
            ]"
          >
            <div class="absolute top-0 right-0 bg-yellow-500/20 text-yellow-500 text-[10px] font-bold px-2 py-1 rounded-bl-lg font-mono">
              EV +{{ pick.ev }}%
            </div>

            <span class="text-[10px] text-gray-500 font-mono uppercase tracking-widest block mb-1">{{ pick.liga }}</span>
            <h4 class="text-sm font-bold text-white mb-3">{{ pick.home_team }} vs {{ pick.away_team }}</h4>
            
            <div class="flex justify-between items-end">
              <div>
                <span class="text-[10px] text-gray-500 block uppercase">Mercado</span>
                <span class="text-xs font-bold text-yellow-400">{{ pick.mercado }}</span>
              </div>
              <div class="text-right">
                <span class="text-[10px] text-gray-500 block uppercase">Odd / IA Conf.</span>
                <span class="text-sm font-mono font-bold text-white">
                  {{ pick.odd.toFixed(2) }} 
                  <span class="text-[#10B981] text-[10px] ml-1">{{ pick.confianca }}%</span>
                </span>
              </div>
            </div>

            <div v-if="isSelected(pick)" class="absolute inset-0 flex items-center justify-center bg-yellow-500/5 backdrop-blur-[1px]">
              <CheckCircle2 class="text-yellow-500" :size="32" />
            </div>
          </div>

          <div v-if="goldPicks.length === 0 && !isLoading" class="col-span-full py-10 text-center opacity-40">
            <FlaskConical size="40" class="mx-auto mb-3 text-gray-500" />
            <p class="text-xs uppercase tracking-[0.2em] font-bold">IA analisando mercados em busca de assimetrias...</p>
          </div>
        </div>
      </div>

      <div class="w-full xl:w-1/3 bg-black/40 border border-white/10 rounded-xl p-4 flex flex-col h-full shadow-inner">
        <h3 class="text-xs font-bold text-gray-400 uppercase tracking-widest border-b border-white/10 pb-2 mb-4 flex justify-between">
          <span>Seu Bilhete (Bet Slip)</span>
          <span class="text-yellow-500">{{ selectedPicks.length }} Seleções</span>
        </h3>

        <div class="flex flex-col gap-2 flex-1 overflow-y-auto custom-scrollbar pr-1 min-h-[150px]">
          <div v-for="pick in selectedPicks" :key="'slip'+pick.match_id" class="bg-[#121927] border border-white/5 p-2 rounded flex justify-between items-center group">
            <div class="flex flex-col truncate pr-2">
              <span class="text-[10px] font-bold text-white truncate">{{ pick.home_team }} v {{ pick.away_team }}</span>
              <span class="text-[9px] text-gray-400">{{ pick.mercado }}</span>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-xs font-mono font-bold text-yellow-400">{{ pick.odd.toFixed(2) }}</span>
              <button @click="toggleSelection(pick)" class="text-gray-600 hover:text-red-400 transition-colors"><X size="14"/></button>
            </div>
          </div>
          
          <div v-if="selectedPicks.length === 0" class="flex-1 flex items-center justify-center text-[10px] text-gray-600 font-mono uppercase tracking-widest text-center px-4">
            Selecione mercados ao lado para montar seu bilhete simples ou SGP.
          </div>
        </div>

        <div class="mt-4 pt-4 border-t border-white/10 flex flex-col gap-3">
          <div class="flex justify-between items-center">
            <span class="text-[10px] text-gray-400 uppercase tracking-widest">Odd Combinada</span>
            <span class="text-xl font-mono font-bold text-white">{{ combinedMetrics.odd.toFixed(2) }}</span>
          </div>
          
          <div class="flex justify-between items-center">
            <span class="text-[10px] text-gray-400 uppercase tracking-widest">EV Combinado (SGP)</span>
            <span class="text-sm font-mono font-bold" :class="combinedMetrics.ev > 0 ? 'text-[#10B981]' : 'text-red-400'">
              {{ combinedMetrics.ev > 0 ? '+' : '' }}{{ combinedMetrics.ev.toFixed(2) }}%
            </span>
          </div>

          <div class="flex justify-between items-center bg-yellow-500/10 border border-yellow-500/30 p-2 rounded">
            <span class="text-[10px] text-yellow-500 uppercase tracking-widest font-bold">Kelly Stake (Recomendada)</span>
            <span class="text-lg font-mono font-bold text-yellow-400">{{ combinedMetrics.kellyStake.toFixed(2) }}u</span>
          </div>

          <button 
            @click="executeTicket" 
            :disabled="selectedPicks.length === 0 || isExecuting"
            class="w-full bg-[#10B981] text-black py-3 text-xs font-bold uppercase tracking-widest rounded hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-[0_0_15px_rgba(16,185,129,0.3)] flex items-center justify-center gap-2 mt-2"
          >
            <Play v-if="!isExecuting" size="14" strokeWidth="3"/>
            <Loader2 v-else size="14" class="animate-spin" />
            {{ isExecuting ? 'Conectando à Bet365...' : 'Executar Aposta (Bet365)' }}
          </button>
        </div>

      </div>
    </div>
  </WidgetCard>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { Award, Play, CheckCircle2, Loader2, FlaskConical, X } from 'lucide-vue-next';
import axios from 'axios';
import WidgetCard from './WidgetCard.vue';

const goldPicks = ref([]);
const selectedPicks = ref([]);
const isLoading = ref(true);
const isExecuting = ref(false);

// Verifica se a pick já está no bilhete
const isSelected = (pick) => selectedPicks.value.some(p => p.match_id === pick.match_id);

// Adiciona/Remove do bilhete
const toggleSelection = (pick) => {
  const index = selectedPicks.value.findIndex(p => p.match_id === pick.match_id);
  if (index > -1) selectedPicks.value.splice(index, 1);
  else selectedPicks.value.push(pick);
};

// ==========================================
// MOTOR MATEMÁTICO: ODD COMBINADA, EV E KELLY
// ==========================================
const combinedMetrics = computed(() => {
  if (selectedPicks.value.length === 0) return { odd: 0, ev: 0, kellyStake: 0 };

  // 1. Odd Combinada (Produto das odds)
  // *Nota: Em SGP reais, a Bet365 aplica um desconto de correlação. Aqui faremos a matemática pura.
  const combinedOdd = selectedPicks.value.reduce((acc, pick) => acc * pick.odd, 1);

  // 2. Probabilidade Implícita e Probabilidade IA Combinadas
  const combinedAIProb = selectedPicks.value.reduce((acc, pick) => acc * (pick.confianca / 100), 1);
  
  // 3. EV Combinado = (Probabilidade Real * Odd Oferecida) - 1
  const combinedEV = ((combinedAIProb * combinedOdd) - 1) * 100;

  // 4. Critério de Kelly (Fração)
  // f = (bp - q) / b
  // b = Odd decimal - 1 (Lucro líquido)
  // p = probabilidade da IA
  // q = 1 - probabilidade da IA
  let kellyFraction = 0;
  if (combinedEV > 0) {
    const b = combinedOdd - 1;
    const p = combinedAIProb;
    const q = 1 - p;
    const fullKelly = (b * p - q) / b;
    
    // Aplicamos Kelly/4 (Conservador para proteção de banca quantitativa)
    // O resultado é um multiplicador (ex: 0.02 = 2% da banca = 2 units)
    kellyFraction = Math.max(0, (fullKelly / 4) * 100); 
  }

  return {
    odd: combinedOdd,
    ev: combinedEV,
    kellyStake: kellyFraction
  };
});

// ==========================================
// INTEGRAÇÃO COM BACKEND
// ==========================================
const fetchGoldPicks = async () => {
  try {
    isLoading.value = true;
    const res = await axios.get('http://localhost:8000/api/v1/quant/gold-picks');
    goldPicks.value = res.data;
  } catch (error) {
    console.error("Erro ao carregar Picks da IA:", error);
  } finally {
    isLoading.value = false;
  }
};

// Executa o bilhete empacotado no Node.js
const executeTicket = async () => {
  try {
    isExecuting.value = true;
    
    // O Payload perfeito contendo o bilhete inteiro e os cálculos
    const payload = {
      type: selectedPicks.value.length > 1 ? 'SGP/ACCUMULATOR' : 'SINGLE',
      selections: selectedPicks.value,
      combined_odd: combinedMetrics.value.odd,
      expected_value: combinedMetrics.value.ev,
      stake_amount: combinedMetrics.value.kellyStake
    };

    await axios.post('http://localhost:8000/api/v1/fund/execute-ticket', payload);
    
    alert(`Sucesso! Ticket executado no sistema. A ordem de compra foi enviada.`);
    selectedPicks.value = [];
    await fetchGoldPicks();
  } catch (error) {
    alert(error.response?.data?.error || "Erro na execução da aposta.");
  } finally {
    isExecuting.value = false;
  }
};

onMounted(fetchGoldPicks);
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 3px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
</style>