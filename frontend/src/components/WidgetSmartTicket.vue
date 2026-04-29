<template>
  <div class="flex flex-col h-full bg-[#0b0f19] text-white overflow-hidden animate-fade-in">
    
    <div class="p-5 border-b border-white/5 bg-black/20 flex justify-between items-center shrink-0">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-[#10B981]/10 border border-[#10B981]/30 flex items-center justify-center shadow-[0_0_15px_rgba(16,185,129,0.1)]">
          <Receipt :size="20" class="text-[#10B981]" />
        </div>
        <div>
          <h3 class="text-sm font-black font-mono tracking-widest uppercase">Smart Builder</h3>
          <span class="text-[9px] text-gray-500 uppercase font-bold tracking-tighter">Auto-SGP Orchestrator</span>
        </div>
      </div>

      <div class="flex p-1 rounded-xl bg-black/40 border border-white/10 shadow-inner">
        <button v-for="risk in ['conservador', 'moderado', 'agressivo']" :key="risk"
          @click="changeRisk(risk)"
          class="px-3 py-1.5 text-[9px] uppercase tracking-widest font-black rounded-lg transition-all duration-300"
          :class="riscoAtual === risk ? riskClasses[risk] : 'text-gray-500 hover:text-gray-300'">
          {{ risk.substring(0,3) }}
        </button>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto custom-scrollbar p-4 flex flex-col gap-3">
      
      <div v-if="isLoading" class="flex flex-col gap-3">
        <div v-for="i in 3" :key="'sk'+i" class="h-20 rounded-2xl border border-white/5 bg-white/[0.02] animate-pulse"></div>
      </div>

      <template v-else>
        <transition-group name="list-complete">
          <div v-for="(selecao, index) in bilhete" :key="selecao.jogo + index" 
               class="p-4 rounded-2xl border border-white/5 bg-[#121927] group relative hover:border-[#10B981]/40 transition-all duration-300 shadow-lg hover:shadow-[0_10px_20px_rgba(0,0,0,0.3)]">
            
            <div class="flex justify-between items-start mb-2">
              <div class="flex flex-col max-w-[75%]">
                <span class="text-[11px] font-bold text-white truncate leading-tight">{{ selecao.jogo }}</span>
                <span class="text-[9px] text-[#10B981] font-mono mt-1 uppercase tracking-widest">{{ selecao.mercado }}</span>
              </div>
              <span class="text-sm font-mono font-black text-white bg-black/40 px-2 py-1 rounded-lg border border-white/5 shadow-inner">
                @{{ selecao.odd.toFixed(2) }}
              </span>
            </div>
            
            <div class="flex flex-col gap-1 mt-3">
              <div class="flex justify-between text-[8px] uppercase font-bold text-gray-500 tracking-widest">
                <span>IA Confidence</span>
                <span class="text-white">{{ selecao.confianca }}%</span>
              </div>
              <div class="w-full h-1 bg-black rounded-full overflow-hidden border border-white/5">
                <div class="h-full bg-gradient-to-r from-blue-500 to-[#10B981] transition-all duration-1000" :style="`width: ${selecao.confianca}%`"></div>
              </div>
            </div>

            <button @click="removeLeg(index)" class="absolute -top-2 -right-2 bg-red-500 text-white p-1 rounded-full opacity-0 group-hover:opacity-100 transition-all shadow-lg hover:scale-110">
              <X :size="12" strokeWidth="3" />
            </button>
          </div>
        </transition-group>

        <div v-if="bilhete.length === 0" class="flex-1 flex flex-col items-center justify-center py-10 opacity-30 text-center gap-4">
          <div class="w-20 h-20 rounded-full border-2 border-dashed border-gray-600 flex items-center justify-center">
            <Wand2 size="32" class="text-gray-500"/>
          </div>
          <span class="text-[10px] text-gray-400 uppercase tracking-[0.2em] font-black px-10">
            Aguardando Parâmetros para Composição de SGP
          </span>
        </div>
      </template>

      <button 
        @click="generateAutoTicket"
        :disabled="isLoading"
        class="w-full py-4 rounded-2xl border-2 border-dashed border-white/10 text-gray-500 text-[10px] font-black uppercase tracking-[0.3em] hover:border-[#10B981]/50 hover:text-[#10B981] hover:bg-[#10B981]/5 transition-all flex items-center justify-center gap-3 mt-2 disabled:opacity-50 group"
      >
        <Sparkles v-if="!isLoading" :size="16" class="group-hover:rotate-12 transition-transform" /> 
        <Loader2 v-else :size="16" class="animate-spin" /> 
        Gerar Alpha Ticket
      </button>
    </div>

    <div class="p-6 border-t border-white/10 bg-black/40 backdrop-blur-xl shrink-0">
      <div class="flex justify-between items-center mb-2">
        <span class="text-[10px] text-gray-500 uppercase font-black tracking-widest">Probabilidade Combinada</span>
        <div class="flex items-center gap-2">
           <span class="text-sm font-mono font-bold text-white">{{ ticketStats.prob.toFixed(1) }}%</span>
           <div class="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
        </div>
      </div>
      
      <div class="flex justify-between items-end mb-6">
        <span class="text-[10px] text-gray-500 uppercase font-black tracking-widest">Odd Alvo Acumulada</span>
        <span class="text-4xl font-mono font-black text-white drop-shadow-[0_0_15px_rgba(255,255,255,0.2)]">
          <span class="text-[#10B981]">@</span>{{ ticketStats.odd.toFixed(2) }}
        </span>
      </div>

      <button 
        @click="executeTicket"
        :disabled="bilhete.length === 0 || isExecuting"
        class="w-full relative overflow-hidden group/btn bg-[#10B981] text-black font-black uppercase tracking-[0.2em] text-xs py-5 rounded-2xl shadow-[0_10px_40px_rgba(16,185,129,0.3)] transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-20 disabled:grayscale disabled:cursor-not-allowed"
      >
        <div class="absolute inset-0 bg-white/20 translate-y-full group-hover/btn:translate-y-0 transition-transform duration-300"></div>
        <div class="relative z-10 flex justify-center items-center gap-3">
          <Zap v-if="!isExecuting" :size="18" fill="currentColor" />
          <Loader2 v-else :size="18" class="animate-spin" />
          {{ isExecuting ? 'Transmitindo Ordem...' : 'Executar no Ledger' }}
        </div>
      </button>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { Receipt, X, Wand2, Zap, Loader2, Sparkles, TrendingUp, Info } from 'lucide-vue-next';
import axios from 'axios';

// 🛑 A CURA DA ROTA (Render vs Localhost S-Tier)
const rawApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_BASE_URL = rawApiUrl.endsWith('/api/v1') ? rawApiUrl : `${rawApiUrl.replace(/\/$/, '')}/api/v1`;

const riscoAtual = ref('moderado');
const bilhete = ref([]);
const isLoading = ref(false);
const isExecuting = ref(false);

const riskClasses = {
  'conservador': 'bg-[#10B981]/20 text-[#10B981] shadow-[0_0_10px_rgba(16,185,129,0.2)] border border-[#10B981]/30',
  'moderado': 'bg-blue-500/20 text-blue-400 shadow-[0_0_10px_rgba(59,130,246,0.2)] border border-blue-500/30',
  'agressivo': 'bg-red-500/20 text-red-400 shadow-[0_0_10px_rgba(239,68,68,0.2)] border border-red-500/30'
};

const ticketStats = computed(() => {
  if (bilhete.value.length === 0) return { odd: 0.00, prob: 0.0 };
  const oddFinal = bilhete.value.reduce((acc, b) => acc * b.odd, 1);
  const probFinal = bilhete.value.reduce((acc, b) => acc * (b.confianca / 100), 1) * 100;
  return { odd: oddFinal, prob: probFinal };
});

const removeLeg = (index) => { bilhete.value.splice(index, 1); };

const changeRisk = (risk) => {
  riscoAtual.value = risk;
  generateAutoTicket();
};

const generateAutoTicket = async () => {
  isLoading.value = true;
  try {
    const token = localStorage.getItem('betgenius_token');
    const res = await axios.post(`${API_BASE_URL}/quant/auto-builder`, 
      { riskProfile: riscoAtual.value },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    bilhete.value = res.data.selecoes;
  } catch (error) {
    console.error("Erro ao gerar Auto-Ticket:", error);
  } finally {
    isLoading.value = false;
  }
};

const executeTicket = async () => {
  if (bilhete.value.length === 0) return;
  isExecuting.value = true;
  try {
    const token = localStorage.getItem('betgenius_token');
    let stake = riscoAtual.value === 'conservador' ? 2.0 : (riscoAtual.value === 'agressivo' ? 0.5 : 1.0);

    const mercadoComposto = "SGP: " + bilhete.value.map(b => b.mercado).join(" + ");
    const jogoComposto = "Múltipla: " + bilhete.value.map(b => b.jogo.split('vs')[0].trim()).join(" / ");

    await axios.post(`${API_BASE_URL}/fund/place-bet`, {
      match_id: 0,
      jogo: jogoComposto,
      mercado: mercadoComposto,
      odd_placed: ticketStats.value.odd,
      stake_amount: stake,
      clv_edge: 4.5
    }, { headers: { Authorization: `Bearer ${token}` } });

    alert("ORDEM TRANSMITIDA: Ticket registrado no Livro-Razão S-Tier.");
    bilhete.value = [];
  } catch (error) {
    alert("FALHA NA TRANSMISSÃO: Verifique a liquidez e o token de acesso.");
  } finally {
    isExecuting.value = false;
  }
};
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.05); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(16, 185, 129, 0.3); }

/* Animations */
.list-complete-enter-active, .list-complete-leave-active { transition: all 0.5s ease; }
.list-complete-enter-from { opacity: 0; transform: translateY(30px); }
.list-complete-leave-to { opacity: 0; transform: scale(0.9); }

.animate-fade-in { animation: fadeIn 0.4s ease-out; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
</style>