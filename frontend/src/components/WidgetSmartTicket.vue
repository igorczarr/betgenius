<template>
  <WidgetCard titulo="Smart Ticket Builder (Auto-SGP)">
    
    <template #icone>
      <Receipt :size="16" class="text-[#10B981]" />
    </template>

    <template #acoes>
      <div class="flex p-1 rounded-lg bg-black/40 border border-white/10 shadow-inner">
        <button 
          @click="changeRisk('conservador')"
          class="px-3 py-1 text-[10px] uppercase tracking-wider font-bold rounded transition-colors"
          :class="riscoAtual === 'conservador' ? 'bg-[#10B981]/20 text-[#10B981]' : 'text-gray-500 hover:text-gray-300'"
        >Seguro</button>
        <button 
          @click="changeRisk('moderado')"
          class="px-3 py-1 text-[10px] uppercase tracking-wider font-bold rounded transition-colors"
          :class="riscoAtual === 'moderado' ? 'bg-yellow-500/20 text-yellow-400' : 'text-gray-500 hover:text-gray-300'"
        >Mod</button>
        <button 
          @click="changeRisk('agressivo')"
          class="px-3 py-1 text-[10px] uppercase tracking-wider font-bold rounded transition-colors"
          :class="riscoAtual === 'agressivo' ? 'bg-red-500/20 text-red-400' : 'text-gray-500 hover:text-gray-300'"
        >Agr</button>
      </div>
    </template>

    <div class="flex flex-col h-full justify-between">
      
      <div class="flex-1 overflow-y-auto custom-scrollbar pr-1 mb-4 flex flex-col gap-2">
        
        <template v-if="isLoading">
          <div v-for="i in 3" :key="'skel'+i" class="h-16 rounded-lg border border-white/5 bg-white/[0.02] animate-pulse"></div>
        </template>

        <template v-else>
          <div v-for="(selecao, index) in bilhete" :key="index" 
               class="p-3 rounded-lg border border-white/5 bg-white/[0.02] group relative hover:border-[#10B981]/30 transition-colors">
            
            <div class="flex justify-between items-start mb-1">
              <span class="text-xs font-bold text-white truncate pr-2">{{ selecao.jogo }}</span>
              <span class="text-xs font-mono font-bold text-[#10B981]">{{ selecao.odd.toFixed(2) }}</span>
            </div>
            
            <div class="flex justify-between items-center">
              <span class="text-[10px] text-gray-400 uppercase tracking-wider">{{ selecao.mercado }}</span>
              <button @click="removeLeg(index)" class="text-gray-600 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100">
                <XCircle :size="14" />
              </button>
            </div>
          </div>

          <div v-if="bilhete.length === 0" class="flex-1 flex flex-col items-center justify-center py-6 opacity-50 text-center">
            <Receipt size="30" class="text-gray-500 mb-2"/>
            <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold px-4">
              Nenhuma aposta. Clique em "Gerar" para a IA montar um bilhete {{ riscoAtual }}.
            </span>
          </div>
        </template>

        <button 
          @click="generateAutoTicket"
          :disabled="isLoading"
          class="w-full py-2 rounded-lg border border-dashed border-gray-700 text-gray-500 text-xs font-bold uppercase tracking-wider hover:border-[#10B981] hover:text-[#10B981] transition-colors flex items-center justify-center gap-2 mt-1 disabled:opacity-50"
        >
          <Wand2 v-if="!isLoading" :size="14" /> 
          <Loader2 v-else :size="14" class="animate-spin" /> 
          Gerar Bilhete {{ riscoAtual }}
        </button>
      </div>

      <div class="pt-4 border-t border-white/10">
        <div class="flex justify-between items-center mb-1">
          <span class="text-xs text-gray-400 uppercase tracking-widest">Probabilidade Combinada</span>
          <span class="text-sm font-mono text-white">{{ ticketStats.prob.toFixed(1) }}%</span>
        </div>
        <div class="flex justify-between items-end mb-4">
          <span class="text-xs text-gray-400 uppercase tracking-widest">Odd Alvo</span>
          <span class="text-2xl font-mono font-bold text-[#10B981]">{{ ticketStats.odd.toFixed(2) }}</span>
        </div>

        <button 
          @click="executeTicket"
          :disabled="bilhete.length === 0 || isExecuting"
          class="w-full bg-[#10B981] text-black font-bold uppercase tracking-widest py-3 rounded shadow-[0_4px_15px_rgba(16,185,129,0.15)] flex justify-center items-center gap-2 hover:bg-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <ExternalLink v-if="!isExecuting" :size="16" />
          <Loader2 v-else :size="16" class="animate-spin" />
          {{ isExecuting ? 'Enviando Ordem...' : 'Executar no Fundo (Ledger)' }}
        </button>
      </div>

    </div>
  </WidgetCard>
</template>

<script setup>
import { ref, computed } from 'vue';
import { Receipt, XCircle, Wand2, ExternalLink, Loader2 } from 'lucide-vue-next';
// import axios from 'axios';
import WidgetCard from './WidgetCard.vue';

const riscoAtual = ref('conservador');
const bilhete = ref([]);
const isLoading = ref(false);
const isExecuting = ref(false);

// Matemática do Bilhete
const ticketStats = computed(() => {
  if (bilhete.value.length === 0) return { odd: 0.00, prob: 0.0 };
  const oddFinal = bilhete.value.reduce((acc, b) => acc * b.odd, 1);
  const probFinal = bilhete.value.reduce((acc, b) => acc * (b.confianca / 100), 1) * 100;
  return { odd: oddFinal, prob: probFinal };
});

const removeLeg = (index) => {
  bilhete.value.splice(index, 1);
};

const changeRisk = (risk) => {
  riscoAtual.value = risk;
  generateAutoTicket();
};

// ==========================================
// CONEXÃO COM A API NODE.JS
// ==========================================
const generateAutoTicket = async () => {
  isLoading.value = true;
  try {
    const res = await axios.post('http://localhost:8000/api/v1/quant/auto-builder', {
      riskProfile: riscoAtual.value
    });
    bilhete.value = res.data.selecoes;
  } catch (error) {
    console.error("Erro ao gerar Auto-Ticket:", error);
  } finally {
    isLoading.value = false;
  }
};

const executeTicket = async () => {
  isExecuting.value = true;
  try {
    // Calculamos o Stake baseado no risco atual (ex: 2u conservador, 1u moderado, 0.5u agressivo)
    let stake = 1.0;
    if (riscoAtual.value === 'conservador') stake = 2.0;
    if (riscoAtual.value === 'agressivo') stake = 0.5;

    // Converte as múltiplas pernas em um único nome composto para o Banco de Dados
    const mercadoComposto = "SGP: " + bilhete.value.map(b => b.mercado).join(" + ");
    const jogoComposto = "Combinada (" + bilhete.value.length + " Pernas)";

    // Reutiliza a rota de "place-bet" que construímos na etapa anterior
    await axios.post('http://localhost:8000/api/v1/fund/place-bet', {
      match_id: null, // SGP Multi-jogo não tem ID único
      jogo: jogoComposto,
      mercado: mercadoComposto,
      odd_placed: ticketStats.value.odd,
      stake_amount: stake,
      clv_edge: 5.0 // Edge simulado (Na vida real, precisaríamos enviar o EV combinado calculado)
    });

    alert("✅ Ticket Múltiplo executado e salvo no Livro-Razão!");
    bilhete.value = []; // Limpa o bilhete após sucesso
  } catch (error) {
    alert(error.response?.data?.error || "Erro na execução da aposta múltipla.");
  } finally {
    isExecuting.value = false;
  }
};
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 3px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
</style>