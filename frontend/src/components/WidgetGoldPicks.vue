<template>
  <div class="fixed right-6 bottom-6 z-50 flex flex-col items-end pointer-events-none">
    
    <Transition name="bounce">
      <button 
        v-if="!isOpen" 
        @click="togglePanel"
        class="pointer-events-auto relative flex items-center justify-center w-14 h-14 bg-[#0a0f16]/90 backdrop-blur-md border border-[#10B981]/40 rounded-full shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:bg-[#10B981]/10 transition-all duration-300 group"
      >
        <Receipt :size="24" class="text-[#10B981] group-hover:scale-110 transition-transform duration-300" />
        
        <span v-if="selections.length > 0" class="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-[#10B981] text-black text-[10px] font-bold border-2 border-[#0a0f16]">
          {{ selections.length }}
        </span>
      </button>
    </Transition>

    <Transition name="slide-up">
      <div v-if="isOpen" class="pointer-events-auto w-[360px] max-h-[600px] flex flex-col bg-[#0a0f16]/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl shadow-black/50 overflow-hidden">
        
        <div class="flex justify-between items-center p-4 border-b border-white/5 bg-gradient-to-r from-white/[0.02] to-transparent">
          <div class="flex items-center gap-2">
            <div class="p-1.5 bg-[#10B981]/20 rounded-md">
              <Terminal :size="16" class="text-[#10B981]" />
            </div>
            <h3 class="text-sm font-bold text-white uppercase tracking-widest">Ticket Builder</h3>
          </div>
          <button @click="togglePanel" class="text-gray-500 hover:text-white transition-colors">
            <Minimize2 :size="18" />
          </button>
        </div>

        <div class="p-3 border-b border-white/5 bg-black/20">
          <div class="flex p-1 rounded-lg bg-black/40 border border-white/10 shadow-inner">
            <button 
              v-for="risk in riskProfiles" :key="risk.id"
              @click="changeRisk(risk.id)"
              class="flex-1 py-1.5 text-[10px] uppercase tracking-wider font-bold rounded transition-colors text-center"
              :class="activeRisk === risk.id ? risk.activeClass : 'text-gray-500 hover:text-gray-300'"
            >
              {{ risk.label }}
            </button>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto custom-scrollbar p-3 flex flex-col gap-2 min-h-[200px]">
          
          <template v-if="isLoading">
            <div v-for="i in 3" :key="'skel'+i" class="h-[68px] rounded-lg border border-white/5 bg-white/[0.02] animate-pulse"></div>
          </template>

          <template v-else>
            <div v-for="(leg, index) in selections" :key="index" 
                 class="p-3 rounded-lg border border-white/5 bg-gradient-to-br from-white/[0.03] to-transparent group relative hover:border-[#10B981]/30 transition-all duration-300">
              
              <div class="flex justify-between items-start mb-1.5">
                <span class="text-xs font-bold text-white truncate pr-2 leading-tight">{{ leg.jogo || `${leg.home_team} v ${leg.away_team}` }}</span>
                <span class="text-xs font-mono font-bold text-[#10B981]">{{ Number(leg.odd).toFixed(2) }}</span>
              </div>
              
              <div class="flex justify-between items-center">
                <span class="text-[10px] text-gray-400 uppercase tracking-wider truncate max-w-[80%]">{{ leg.mercado || leg.market }}</span>
                <button @click="removeLeg(index)" class="text-gray-600 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100">
                  <XCircle :size="14" />
                </button>
              </div>
            </div>

            <div v-if="selections.length === 0" class="flex-1 flex flex-col items-center justify-center py-8 opacity-50 text-center">
              <Crosshair size="32" class="text-gray-500 mb-3 opacity-50"/>
              <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold px-4 leading-relaxed">
                Adicione mercados no painel ao lado ou use a IA para gerar um bilhete.
              </span>
            </div>
          </template>
        </div>

        <div class="px-3 pb-3">
          <button 
            @click="generateAutoTicket"
            :disabled="isLoading"
            class="w-full py-2.5 rounded-lg border border-dashed border-white/20 text-gray-400 text-[10px] font-bold uppercase tracking-widest hover:border-[#10B981] hover:text-[#10B981] hover:bg-[#10B981]/5 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <Wand2 v-if="!isLoading" :size="14" /> 
            <Loader2 v-else :size="14" class="animate-spin" /> 
            Auto-Build ({{ activeRiskLabel }})
          </button>
        </div>

        <div class="p-4 bg-gradient-to-t from-black/80 to-transparent border-t border-white/10">
          <div class="flex justify-between items-center mb-1">
            <span class="text-[10px] text-gray-400 uppercase tracking-widest">Odd Combinada (Justa)</span>
            <span class="text-xs font-mono text-white">{{ validationData.combined_odd.toFixed(2) }}</span>
          </div>
          
          <div class="flex justify-between items-center mb-1">
            <span class="text-[10px] text-gray-400 uppercase tracking-widest">EV Combinado</span>
            <span class="text-xs font-mono" :class="validationData.expected_value_pct > 0 ? 'text-[#10B981]' : 'text-red-400'">
              {{ validationData.expected_value_pct > 0 ? '+' : '' }}{{ validationData.expected_value_pct.toFixed(1) }}%
            </span>
          </div>

          <div class="flex justify-between items-end mb-4">
            <span class="text-[10px] text-gray-400 uppercase tracking-widest">Stake Recomendada (R$)</span>
            <span class="text-xl font-mono font-bold text-white">R$ {{ validationData.recommended_stake_brl.toFixed(2) }}</span>
          </div>

          <button 
            @click="executeTicket"
            :disabled="selections.length === 0 || isExecuting || validationData.recommended_stake_brl <= 0"
            class="w-full bg-[#10B981] text-black font-bold uppercase tracking-widest py-3 rounded-lg shadow-[0_4px_20px_rgba(16,185,129,0.2)] flex justify-center items-center gap-2 hover:bg-white hover:scale-[1.02] transition-all disabled:opacity-30 disabled:hover:scale-100 disabled:cursor-not-allowed"
          >
            <Zap v-if="!isExecuting" :size="16" />
            <Loader2 v-else :size="16" class="animate-spin" />
            {{ isExecuting ? 'Liquidando Ordem...' : 'Executar Ordem' }}
          </button>
        </div>

      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { Receipt, XCircle, Wand2, Terminal, Minimize2, Crosshair, Zap, Loader2 } from 'lucide-vue-next';
import axios from 'axios';

// ==========================================
// ESTADO DO COMPONENTE
// ==========================================
const isOpen = ref(false);
const isLoading = ref(false);
const isExecuting = ref(false);
const selections = ref([]);

// Dados reativos validados pelo Backend
const validationData = ref({
  combined_odd: 0.0,
  combined_probability_pct: 0.0,
  expected_value_pct: 0.0,
  recommended_stake_brl: 0.0
});

// ==========================================
// PERFIS DE RISCO (MAPEAMENTO INSTITUCIONAL)
// ==========================================
const riskProfiles = [
  { id: 'CONSERVATIVE', label: 'Seguro', activeClass: 'bg-[#10B981]/20 text-[#10B981]', apiParam: 'conservador' },
  { id: 'MODERATE', label: 'Mod', activeClass: 'bg-yellow-500/20 text-yellow-400', apiParam: 'moderado' },
  { id: 'AGGRESSIVE', label: 'Agr', activeClass: 'bg-orange-500/20 text-orange-400', apiParam: 'agressivo' },
  { id: 'MOONSHOT', label: 'Moon', activeClass: 'bg-red-500/20 text-red-500 shadow-[0_0_10px_rgba(239,68,68,0.2)]', apiParam: 'agressivo' }
];

const activeRisk = ref('CONSERVATIVE');

const activeRiskLabel = computed(() => {
  return riskProfiles.find(r => r.id === activeRisk.value)?.label || '';
});

// ==========================================
// FUNÇÕES DE INTERFACE
// ==========================================
const togglePanel = () => {
  isOpen.value = !isOpen.value;
};

const changeRisk = (riskId) => {
  activeRisk.value = riskId;
  validateCart(); // Recalcula a Stake imediatamente se o perfil de risco mudar
};

const removeLeg = (index) => {
  selections.value.splice(index, 1);
};

// ==========================================
// INTEGRAÇÃO COM AS NOVAS ROTAS (API GATEWAY)
// ==========================================

// 1. Rota de Validação Dinâmica S-Tier
const validateCart = async () => {
  if (selections.value.length === 0) {
    validationData.value = { combined_odd: 0, combined_probability_pct: 0, expected_value_pct: 0, recommended_stake_brl: 0 };
    return;
  }

  try {
    // Formata o array para o Pydantic do backend (CartValidationRequest)
    const payloadSelections = selections.value.map(s => ({
      match_id: s.match_id || 1,
      home_team: s.home_team || s.jogo.split(' v ')[0] || "Home",
      away_team: s.away_team || s.jogo.split(' v ')[1] || "Away",
      market: s.mercado || s.market,
      odd: s.odd,
      prob: s.prob || (s.confianca ? s.confianca / 100 : 0.5) // Fallback de prob se vier do auto-builder antigo
    }));

    const res = await axios.post('http://localhost:8000/api/v1/sgp/validate-cart', {
      risk_profile: activeRisk.value,
      selections: payloadSelections
    });

    if (res.data.status === 'error') {
      alert(res.data.message);
      selections.value.pop(); // Remove a última perna que causou o erro (Teto de variância)
    } else {
      validationData.value = res.data;
    }
  } catch (error) {
    console.error("Erro ao validar carrinho:", error);
  }
};

// Assiste mudanças no carrinho para re-validar em tempo real
watch(selections, () => {
  validateCart();
}, { deep: true });


// 2. Rota de Auto-Construção (O Cientista)
const generateAutoTicket = async () => {
  isLoading.value = true;
  selections.value = []; // Limpa carrinho atual
  
  try {
    const riskParam = riskProfiles.find(r => r.id === activeRisk.value).apiParam;
    
    // Bate na rota do main.py que varre a base procurando os EV+
    const res = await axios.post('http://localhost:8000/api/v1/quant/auto-builder', {
      riskProfile: riskParam
    });
    
    if (res.data.selecoes && res.data.selecoes.length > 0) {
      selections.value = res.data.selecoes;
      if(!isOpen.value) isOpen.value = true; // Abre o painel para o usuário ver a mágica
    } else {
      alert("Nenhum padrão tático de alto valor encontrado nas linhas atuais.");
    }
  } catch (error) {
    console.error("Erro ao invocar Auto-Builder:", error);
  } finally {
    isLoading.value = false;
  }
};

// 3. Rota de Execução (O Deep Link e o Ledger)
const executeTicket = async () => {
  isExecuting.value = true;
  try {
    const payloadSelections = selections.value.map(s => ({
      match_id: s.match_id || 1,
      home_team: s.home_team || s.jogo?.split(' Alpha ')[0] || "Equipe Casa",
      away_team: s.away_team || s.jogo?.split(' Target ')[0] || "Equipe Fora",
      market: s.mercado || s.market,
      odd: s.odd,
      prob: s.prob || (s.confianca ? s.confianca / 100 : 0.5)
    }));

    const res = await axios.post('http://localhost:8000/api/v1/sgp/execute', {
      risk_profile: activeRisk.value,
      stake_brl: validationData.value.recommended_stake_brl,
      total_odd: validationData.value.combined_odd,
      bookmaker: 'Pinnacle', // Poderia vir de um select na UI
      selections: payloadSelections
    });

    if (res.data.status === 'success') {
      // Abre a casa de apostas numa nova aba instantaneamente (Deep Link)
      window.open(res.data.action_url, '_blank');
      
      // Limpa a interface após o sucesso
      selections.value = [];
      isOpen.value = false;
    }
  } catch (error) {
    alert(error.response?.data?.detail || "Falha crítica ao liquidar ordem.");
  } finally {
    isExecuting.value = false;
  }
};
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(16, 185, 129, 0.2); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(16, 185, 129, 0.5); }

/* Animações S-Tier */
.bounce-enter-active { animation: bounce-in 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
.bounce-leave-active { animation: bounce-in 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) reverse; }
@keyframes bounce-in {
  0% { transform: scale(0); opacity: 0; }
  50% { transform: scale(1.1); }
  100% { transform: scale(1); opacity: 1; }
}

.slide-up-enter-active, .slide-up-leave-active {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  transform-origin: bottom right;
}
.slide-up-enter-from, .slide-up-leave-to {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}
</style>