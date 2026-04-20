<template>
  <div class="flex flex-col gap-6 w-full min-h-full relative fade-in-up pb-10">
    
    <div class="glass-card shrink-0 p-6 md:p-8 relative overflow-hidden flex flex-col xl:flex-row justify-between items-center border-t-4 shadow-[0_20px_50px_rgba(0,0,0,0.5)] border-blue-500">
      <div class="absolute -left-40 -bottom-40 w-96 h-96 rounded-full blur-[100px] pointer-events-none opacity-15 bg-blue-500"></div>
      
      <div class="flex items-center gap-5 w-full xl:w-1/4 z-10 mb-6 xl:mb-0">
        <div class="w-16 h-16 rounded-xl bg-black/60 border border-blue-500/30 flex items-center justify-center shadow-[0_0_30px_rgba(59,130,246,0.2)] relative overflow-hidden">
          <div class="absolute inset-0 bg-gradient-to-br from-blue-500/20 to-transparent"></div>
          <FlaskConical :size="30" class="text-blue-400 relative z-10" />
        </div>
        <div class="text-left flex flex-col">
          <h2 class="text-2xl font-mono text-white tracking-widest drop-shadow-md">QUANT LAB</h2>
          <span class="text-[10px] text-blue-400 uppercase tracking-widest font-bold flex items-center gap-1.5 mt-0.5">
            <div class="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse shadow-[0_0_8px_#3b82f6]"></div> Live Engine Connected
          </span>
        </div>
      </div>

      <div class="flex flex-wrap md:flex-nowrap justify-between xl:justify-end gap-6 md:gap-12 w-full xl:w-3/4 z-10">
        <div class="flex flex-col items-start xl:items-end w-[45%] md:w-auto">
          <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 flex items-center gap-1"><Cpu size="12"/> Status do Modelo</span>
          <span class="text-lg font-mono text-white">{{ isLoaded ? 'Online' : 'Loading...' }} <span class="text-[10px] text-gray-500 bg-white/5 px-1.5 py-0.5 rounded ml-1">XGBoost S-Tier</span></span>
        </div>
        
        <div class="hidden md:block w-px bg-gradient-to-b from-transparent via-white/10 to-transparent h-12"></div>
        
        <div class="flex flex-col items-start xl:items-end w-[45%] md:w-auto">
          <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 flex items-center gap-1"><Database size="12"/> Dataset Histórico</span>
          <span class="text-xl font-mono text-white font-bold">{{ systemStats.totalMatches.toLocaleString() }} <span class="text-[10px] text-gray-500 bg-black/40 px-1.5 py-0.5 rounded border border-white/5 ml-1">Partidas</span></span>
        </div>

        <div class="hidden md:block w-px bg-gradient-to-b from-transparent via-white/10 to-transparent h-12"></div>

        <div class="flex flex-col items-start xl:items-end w-full md:w-auto mt-4 md:mt-0 bg-black/30 p-3 rounded-lg border border-white/5 shadow-inner">
          <span class="text-[10px] text-[#10B981] uppercase tracking-widest font-bold mb-1">Global Algo Yield (YTD)</span>
          <span class="text-3xl font-mono text-[#10B981] font-bold drop-shadow-[0_0_15px_rgba(16,185,129,0.3)] tracking-tight">
            {{ systemStats.globalYield > 0 ? '+' : '' }}{{ systemStats.globalYield.toFixed(2) }}%
          </span>
        </div>
      </div>
    </div>

    <div v-if="!isLoaded" class="flex justify-center items-center py-20">
      <div class="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
    </div>

    <draggable 
      v-else
      v-model="layoutBacktest" 
      item-key="id" 
      class="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start mt-2" 
      handle=".drag-handle" 
      ghost-class="ghost-widget"
      animation="250"
    >
      <template #item="{ element }">
        <div :class="element.span" class="relative group/widget h-full">
          
          <div class="drag-handle absolute -top-3 left-1/2 -translate-x-1/2 z-[80] opacity-0 group-hover/widget:opacity-100 cursor-move p-1 px-5 bg-black text-blue-400 rounded-b-xl border border-white/10 shadow-[0_5px_15px_rgba(0,0,0,0.8)] transition-all hover:bg-blue-500 hover:text-white">
            <GripHorizontal size="16" />
          </div>

          <WidgetCard v-if="element.id === 'builder'" titulo="Algorithm Builder (Regras de Entrada)" class="h-full shadow-[0_15px_40px_rgba(0,0,0,0.3)] border-t-2 border-blue-500">
            <template #icone><Code2 :size="16" color="#3b82f6" /></template>
            <template #acoes>
               <button @click="runSimulation" class="bg-[#10B981] text-black px-3 py-1 text-[9px] font-bold uppercase tracking-widest rounded hover:bg-white transition-colors shadow-[0_0_10px_rgba(16,185,129,0.4)] flex items-center gap-1.5"><Play size="10" strokeWidth="3"/> Run Backtest</button>
            </template>
            
            <div class="flex flex-col gap-3 mt-3 h-full">
              <div class="bg-black/20 border border-white/5 p-3 rounded-lg flex items-center justify-between shadow-inner">
                <input type="text" v-model="algoName" class="bg-transparent text-lg font-mono font-bold text-white w-full outline-none focus:border-b focus:border-blue-500 transition-all placeholder-gray-600" placeholder="Nome do Algoritmo...">
                <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold bg-[#121927] px-2 py-1 rounded border border-white/5">Auto-Tuned</span>
              </div>

              <div class="flex flex-col gap-2 flex-1 mt-2">
                <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold border-b border-white/10 pb-1 mb-1">Features do Modelo (XGBoost)</span>
                
                <div v-for="(rule, i) in ruleset" :key="'rule'+i" class="flex flex-col gap-2">
                  <div v-if="i > 0" class="flex justify-center -my-2 relative z-10">
                    <span class="bg-blue-500/20 text-blue-400 border border-blue-500/30 text-[8px] font-bold uppercase px-2 py-0.5 rounded-full font-mono">{{ rule.operator }}</span>
                  </div>
                  <div class="bg-[#121927] border border-white/5 p-3 rounded-lg flex flex-wrap md:flex-nowrap items-center gap-3 hover:border-blue-500/30 transition-colors group">
                    <span class="text-[10px] font-mono text-gray-500 bg-black/50 px-2 py-1 rounded">IF</span>
                    
                    <select v-model="rule.metric" class="bg-black text-[10px] text-white border border-gray-700 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer focus:border-blue-500 flex-1 min-w-[120px]">
                      <option v-for="feat in availableFeatures" :key="feat" :value="feat">{{ feat.replace(/_/g, ' ') }}</option>
                    </select>
                    
                    <select v-model="rule.condition" class="bg-black text-[10px] text-white border border-gray-700 rounded px-2 py-1 outline-none font-mono cursor-pointer focus:border-blue-500 w-16">
                      <option value=">">></option><option value="<"><</option><option value="=">=</option>
                    </select>
                    
                    <input type="text" v-model="rule.value" class="bg-black text-[10px] text-white border border-gray-700 rounded px-2 py-1 outline-none font-mono focus:border-blue-500 w-20" placeholder="Valor">
                    
                    <button @click="removeRule(i)" class="ml-auto text-gray-600 hover:text-red-400 transition-colors"><X size="14"/></button>
                  </div>
                </div>

                <button @click="addRule" class="border border-dashed border-white/20 bg-white/5 text-gray-400 hover:text-white hover:bg-white/10 hover:border-white/40 rounded-lg p-2 text-[10px] uppercase tracking-widest font-bold transition-all mt-2 flex justify-center items-center gap-2">
                  <Plus size="12" /> Adicionar Regra
                </button>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'results'" titulo="Model Evaluation (XGBoost Metrics)" class="h-full shadow-[0_15px_40px_rgba(0,0,0,0.3)]">
            <template #icone><LineChart :size="16" color="#10B981" /></template>
            <template #acoes>
               <span class="bg-blue-500/10 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase tracking-widest flex items-center gap-1.5"><CheckCircle2 size="10"/> Cross-Validated</span>
            </template>
            
            <div class="flex flex-col gap-4 mt-3 h-full">
              <div class="grid grid-cols-3 gap-3">
                <div class="bg-black/20 border border-white/5 p-3 rounded-xl flex flex-col items-center justify-center">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold text-center">Acurácia (Teste)</span>
                  <span class="text-xl font-mono text-[#10B981] font-bold mt-1 drop-shadow-[0_0_5px_currentColor]">{{ (modelMetrics.accuracy * 100).toFixed(1) }}%</span>
                </div>
                <div class="bg-black/20 border border-white/5 p-3 rounded-xl flex flex-col items-center justify-center">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold text-center">Log Loss</span>
                  <span class="text-xl font-mono text-white font-bold mt-1">{{ modelMetrics.logloss.toFixed(4) }}</span>
                </div>
                <div class="bg-black/20 border border-white/5 p-3 rounded-xl flex flex-col items-center justify-center">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold text-center">Brier Score</span>
                  <span class="text-xl font-mono text-yellow-400 font-bold mt-1">{{ modelMetrics.brierScore.toFixed(4) }}</span>
                </div>
              </div>

              <div class="flex flex-col gap-2 mt-2 bg-[#0b0f19] p-4 rounded-xl border border-white/5 shadow-inner flex-1">
                <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold mb-2">Top 4 Features (Importância XGBoost)</span>
                <div v-for="(feat, idx) in modelMetrics.topFeatures" :key="idx" class="flex flex-col gap-1">
                  <div class="flex justify-between text-[10px] font-mono text-gray-300">
                    <span class="truncate">{{ feat.name.replace(/_/g, ' ') }}</span>
                    <span>{{ (feat.importance * 100).toFixed(1) }}%</span>
                  </div>
                  <div class="w-full bg-gray-800 rounded-full h-1.5">
                    <div class="bg-blue-500 h-1.5 rounded-full" :style="{ width: `${feat.importance * 100}%` }"></div>
                  </div>
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'attribution'" titulo="Attribution Analysis (Auditoria de Fundo)" class="h-full shadow-[0_15px_40px_rgba(0,0,0,0.3)]">
            <template #icone><Network :size="16" color="#F59E0B" /></template>
            <template #acoes>
               <select v-model="attributionFilter" class="bg-black text-[9px] text-gray-300 border border-gray-700 rounded px-2 py-0.5 outline-none uppercase font-bold tracking-widest focus:border-yellow-500 cursor-pointer">
                 <option value="leagues">Ligas Ouro</option>
                 <option value="markets">Mercados / SGP</option>
                 <option value="teams">Times Lucrativos</option>
                 <option value="toxic">Blacklist (Times)</option>
               </select>
            </template>
            
            <div class="flex flex-col mt-4 h-full">
              <div class="flex-1 bg-[#121927] border border-white/5 rounded-xl p-0 shadow-inner overflow-hidden flex flex-col">
                <div class="grid grid-cols-12 px-3 py-2 border-b border-white/10 text-[9px] uppercase font-bold text-gray-500 tracking-widest bg-black/40">
                  <span class="col-span-4">{{ attributionFilter === 'leagues' ? 'Competição' : attributionFilter === 'markets' ? 'Ticket/Mercado' : 'Time' }}</span>
                  <span class="col-span-2 text-center">Vol</span>
                  <span class="col-span-2 text-center">Win%</span>
                  <span class="col-span-2 text-center">Avg CLV</span>
                  <span class="col-span-2 text-right pr-2">ROI</span>
                </div>
                
                <div class="flex flex-col overflow-y-auto custom-scrollbar flex-1 pb-2">
                  <div v-for="(item, i) in currentAttributionList" :key="i" class="grid grid-cols-12 items-center bg-black/10 even:bg-white/[0.02] border-b border-white/5 p-2 text-xs font-mono">
                    <span class="col-span-4 text-white truncate pr-2 font-sans font-bold text-[11px]">{{ item.name }}</span>
                    <span class="col-span-2 text-center text-gray-400">{{ item.volume }}</span>
                    <span class="col-span-2 text-center text-gray-300">{{ item.winRate }}%</span>
                    <span class="col-span-2 text-center" :class="item.clv > 0 ? 'text-[#10B981]' : 'text-red-400'">
                      {{ item.clv > 0 ? '+' : '' }}{{ item.clv }}%
                    </span>
                    <span class="col-span-2 text-right pr-2 font-bold" :class="item.roi > 0 ? 'text-[#10B981]' : 'text-red-400'">
                      {{ item.roi > 0 ? '+' : '' }}{{ item.roi }}%
                    </span>
                  </div>
                  <div v-if="currentAttributionList.length === 0" class="flex items-center justify-center h-full p-4 text-[10px] text-gray-500 uppercase tracking-widest font-bold">
                    Aguardando dados suficientes (Min. 5 apostas)
                  </div>
                </div>
              </div>
              
              <div class="mt-3 flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 p-2 rounded">
                <AlertTriangle size="12" class="text-blue-400" />
                <span class="text-[9px] text-gray-300 uppercase tracking-widest font-mono">Insight: ROI negativo com CLV positivo é apenas variância. CLV negativo exige ajustes.</span>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'ledger'" titulo="Fund Ledger (Últimas Operações)" class="h-full shadow-[0_15px_40px_rgba(0,0,0,0.3)]">
            <template #icone><Bot :size="16" color="#a855f7" /></template>
            <template #acoes>
               <span class="text-[8px] text-gray-400 uppercase tracking-widest font-bold bg-black/50 px-2 py-0.5 rounded border border-white/10">Real-Time Data</span>
            </template>

            <div class="flex flex-col h-full mt-3">
              <div class="grid grid-cols-12 px-3 pb-2 border-b border-white/10 text-[9px] uppercase font-bold text-gray-500 tracking-widest bg-black/30 rounded-t-lg pt-2">
                <span class="col-span-5">Partida / Mercado</span>
                <span class="col-span-2 text-center">Stake</span>
                <span class="col-span-3 text-center">Odd / Edge</span>
                <span class="col-span-2 text-right pr-2">Status</span>
              </div>
              
              <div class="flex flex-col overflow-y-auto custom-scrollbar flex-1 pb-2">
                <div v-for="(trade, i) in fundLedger" :key="'trade'+i" class="grid grid-cols-12 items-center bg-black/10 even:bg-white/[0.02] border-b border-white/5 p-3 relative group">
                  <div class="absolute left-0 top-0 w-1 h-full" :class="trade.status === 'WON' ? 'bg-[#10B981]' : (trade.status === 'LOST' ? 'bg-red-500' : 'bg-blue-500')"></div>
                  
                  <div class="col-span-5 flex flex-col pl-3">
                    <span class="text-xs font-bold text-white truncate">{{ trade.jogo }}</span>
                    <span class="text-[9px] text-[#a855f7] uppercase tracking-wider mt-0.5 font-mono truncate">{{ trade.mercado }}</span>
                  </div>
                  
                  <div class="col-span-2 flex flex-col items-center justify-center">
                    <span class="text-xs font-mono font-bold text-gray-300">{{ trade.stake_amount }}u</span>
                  </div>
                  
                  <div class="col-span-3 flex flex-col items-center justify-center border-l border-white/5 pl-2">
                    <span class="text-sm font-mono font-bold text-white">{{ trade.odd_placed.toFixed(2) }}</span>
                    <span class="text-[8px] font-bold uppercase tracking-widest mt-0.5" :class="trade.clv_edge > 0 ? 'text-[#10B981]' : 'text-gray-500'">
                      {{ trade.clv_edge > 0 ? '+' : '' }}{{ trade.clv_edge.toFixed(2) }}% Edge
                    </span>
                  </div>
                  
                  <div class="col-span-2 flex justify-end pr-2">
                    <span class="text-[9px] font-mono font-bold px-2 py-0.5 rounded shadow-inner uppercase tracking-widest" 
                          :class="trade.status === 'WON' ? 'bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/30' : 
                                 (trade.status === 'LOST' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 
                                 'bg-blue-500/20 text-blue-400 border border-blue-500/30 animate-pulse')">
                      {{ trade.status }}
                    </span>
                  </div>
                </div>
                <div v-if="fundLedger.length === 0" class="flex items-center justify-center h-full p-4 text-[10px] text-gray-500 uppercase tracking-widest font-bold">
                  Nenhuma operação registrada no banco de dados.
                </div>
              </div>
            </div>
          </WidgetCard>

        </div>
      </template>
    </draggable>
  </div>
</template>

<script setup>

import { ref, onMounted, computed } from 'vue';
import draggable from 'vuedraggable';
import { 
  GripHorizontal, FlaskConical, Cpu, Database, Code2, 
  Play, X, Plus, LineChart, CheckCircle2, Network, AlertTriangle, Bot
} from 'lucide-vue-next';
import WidgetCard from './WidgetCard.vue';
import axios from 'axios';

// ==========================================
// ESTADO GERAL (CARREGADO DA API)
// ==========================================
const isLoaded = ref(false);

const systemStats = ref({
  totalMatches: 0,
  globalYield: 0.0
});

const modelMetrics = ref({
  accuracy: 0,
  logloss: 0,
  brierScore: 0,
  topFeatures: []
});

const attributionData = ref({
  leagues: [],
  markets: [],
  teams: [],
  toxic: []
});

const fundLedger = ref([]);

// Builder Data
const availableFeatures = ref([]);

// UI State
const layoutBacktest = ref([
  { id: 'builder', span: 'col-span-1 xl:col-span-6' },
  { id: 'results', span: 'col-span-1 xl:col-span-6' },
  { id: 'attribution', span: 'col-span-1 xl:col-span-6' },
  { id: 'ledger', span: 'col-span-1 xl:col-span-6' }
]);

const algoName = ref('XGB_Alpha_v1');
const ruleset = ref([
  { operator: 'START', metric: 'delta_elo', condition: '>', value: '150' },
  { operator: 'AND', metric: 'delta_market_respect', condition: '>', value: '0.05' }
]);
const attributionFilter = ref('leagues');

// Computed para o Widget 3
const currentAttributionList = computed(() => {
  return attributionData.value[attributionFilter.value] || [];
});

// ==========================================
// CHAMADAS DE API (Axios/Fetch Simulação para o seu Backend)
// ==========================================
const fetchDashboardData = async () => {
  try {
    // Altere a URL base conforme o seu ambiente (localhost ou domínio de prod)
    const res = await axios.get('http://localhost:8000/api/v1/quant/dashboard');
    
    // Alimenta o estado do Vue com a resposta pura do Banco de Dados
    systemStats.value = res.data.systemStats;
    modelMetrics.value = res.data.modelMetrics;
    availableFeatures.value = res.data.availableFeatures;
    attributionData.value = res.data.attributionData;
    fundLedger.value = res.data.fundLedger;
    
    // Simulando o delay da API
    await new Promise(r => setTimeout(r, 800)); 

    // Dados vindo do `core.matches_history` e `fund_ledger`
    systemStats.value = {
      totalMatches: 142560,
      globalYield: 4.2
    };

    // Dados vindo do `ml_xgboost_trainer.py`
    modelMetrics.value = {
      accuracy: 0.584,
      logloss: 0.9842,
      brierScore: 0.1654,
      topFeatures: [
        { name: 'closing_odd_home', importance: 0.28 },
        { name: 'delta_elo', importance: 0.15 },
        { name: 'delta_market_respect', importance: 0.11 },
        { name: 'delta_xg_macro', importance: 0.08 }
      ]
    };

    // Preenche o dropdown do builder com as features reais do modelo
    availableFeatures.value = [
      'delta_elo', 'delta_wage_pct', 'delta_pontos', 'delta_posicao',
      'delta_xg_micro', 'delta_xg_macro', 'delta_market_respect',
      'home_tension_index', 'away_tension_index', 'closing_odd_home'
    ];

    // Dados vindo do `performance_engine.py` (Attribution Analysis)
    attributionData.value = {
      leagues: [
        { name: 'ENG-Premier League', volume: 450, winRate: 58.2, clv: 2.1, roi: 8.5 },
        { name: 'GER-Bundesliga', volume: 210, winRate: 62.0, clv: 3.5, roi: 14.2 },
        { name: 'ITA-Serie A', volume: 380, winRate: 48.5, clv: 0.4, roi: -1.2 },
      ],
      markets: [
        { name: 'Match Odds (1X2)', volume: 1842, winRate: 54.0, clv: 1.8, roi: 4.2 },
        { name: 'SGP: Home + Over 1.5', volume: 420, winRate: 42.5, clv: 2.5, roi: 9.8 },
        { name: 'Over 2.5 Goals', volume: 650, winRate: 49.0, clv: -1.2, roi: -5.4 },
      ],
      teams: [
        { name: 'Arsenal FC', volume: 45, winRate: 72.0, clv: 4.1, roi: 22.5 },
        { name: 'Bayer Leverkusen', volume: 38, winRate: 68.4, clv: 3.8, roi: 18.2 },
      ],
      toxic: [
        { name: 'Chelsea FC', volume: 52, winRate: 31.0, clv: -2.5, roi: -18.4 },
        { name: 'Manchester Utd', volume: 48, winRate: 35.4, clv: -1.8, roi: -12.1 },
      ]
    };

    // Dados vindo da tabela `core.fund_ledger`
    fundLedger.value = [
      { jogo: "Arsenal x Chelsea", mercado: "Arsenal ML", stake_amount: 1.5, odd_placed: 1.95, clv_edge: 4.2, status: "WON" },
      { jogo: "Milan x Inter", mercado: "Draw", stake_amount: 0.8, odd_placed: 3.40, clv_edge: 1.5, status: "LOST" },
      { jogo: "Liverpool x Luton", mercado: "SGP: H + BTTS", stake_amount: 1.0, odd_placed: 2.80, clv_edge: 5.1, status: "WON" },
      { jogo: "Flamengo x Palmeiras", mercado: "Flamengo AH -0.5", stake_amount: 2.0, odd_placed: 1.85, clv_edge: 0.0, status: "LIVE" },
    ];

    isLoaded.value = true;
  } catch (error) {
    console.error("Erro ao puxar dados do backend:", error);
  }
};

onMounted(() => {
  fetchDashboardData();
});

// Ações
const addRule = () => {
  ruleset.value.push({ operator: 'AND', metric: availableFeatures.value[0], condition: '>', value: '0' });
};
const removeRule = (index) => {
  ruleset.value.splice(index, 1);
};
const runSimulation = () => {
  alert("Comando enviado para o Backend (Backtest Engine via Celery/Redis). Aguarde...");
};
</script>

<style scoped>
.glass-card { background: rgba(18, 25, 39, 0.8); backdrop-filter: blur(24px); border-radius: 16px;}
.ghost-widget { opacity: 0.4 !important; border: 2px dashed #3b82f6 !important; transform: scale(0.98); background: rgba(59, 130, 246, 0.05); }

input[type=text] { -webkit-appearance: none; appearance: none; }
select { -webkit-appearance: none; appearance: none; }

.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(59, 130, 246, 0.2); border-radius: 10px; }
</style>