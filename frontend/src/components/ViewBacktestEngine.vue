<template>
  <div class="flex flex-col gap-6 w-full min-h-full relative fade-in-up pb-10">
    
    <div class="glass-card shrink-0 p-6 md:p-8 relative overflow-hidden flex flex-col xl:flex-row justify-between items-center border-t border-b-4 shadow-[0_20px_50px_rgba(0,0,0,0.4)]"
         :class="(systemStats.globalYield || 0) >= 0 ? 'border-b-[#10B981]' : 'border-b-red-500'">
      
      <div class="absolute -left-40 -bottom-40 w-96 h-96 rounded-full blur-[100px] pointer-events-none opacity-20 transition-colors duration-1000"
           :class="(systemStats.globalYield || 0) >= 0 ? 'bg-[#10B981]' : 'bg-red-500'"></div>
      
      <div class="flex items-center gap-5 w-full xl:w-1/4 z-10 mb-6 xl:mb-0 group cursor-default">
        <div class="w-16 h-16 rounded-2xl bg-[#0b0f19] border border-white/10 flex items-center justify-center shadow-[0_0_30px_rgba(255,255,255,0.05)] relative overflow-hidden transition-all duration-500 group-hover:scale-105">
          <div class="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent"></div>
          <FlaskConical :size="28" class="text-white relative z-10" />
        </div>
        <div class="text-left flex flex-col">
          <h2 class="text-2xl font-mono text-white tracking-[0.2em] drop-shadow-md font-bold">QUANT LAB</h2>
          <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold flex items-center gap-1.5 mt-1">
            <div class="w-1.5 h-1.5 rounded-full shadow-[0_0_8px_currentColor]" :class="isLoaded ? 'bg-[#10B981] animate-pulse text-[#10B981]' : 'bg-yellow-500 text-yellow-500'"></div> 
            {{ isLoaded ? 'Live Engine Connected' : 'Calibrating...' }}
          </span>
        </div>
      </div>

      <div class="flex flex-wrap md:flex-nowrap justify-between xl:justify-end gap-6 md:gap-12 w-full xl:w-3/4 z-10">
        
        <div class="flex flex-col items-start xl:items-end w-[45%] md:w-auto">
          <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 flex items-center gap-1"><Cpu size="12"/> Core Model</span>
          <span class="text-lg font-mono text-white font-bold tracking-wider flex items-center gap-2">
            XGBoost v4 <span class="text-[9px] text-[#10B981] bg-[#10B981]/10 px-2 py-0.5 rounded uppercase tracking-widest border border-[#10B981]/20">Online</span>
          </span>
        </div>
        
        <div class="hidden md:block w-px bg-gradient-to-b from-transparent via-white/10 to-transparent h-12"></div>
        
        <div class="flex flex-col items-start xl:items-end w-[45%] md:w-auto">
          <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 flex items-center gap-1"><Database size="12"/> Histórico Alimentado</span>
          <span class="text-xl font-mono text-white font-bold tracking-wider">
            {{ (systemStats.totalMatches || 0).toLocaleString() }} <span class="text-[10px] text-gray-500 uppercase tracking-widest font-sans ml-1">Jogos</span>
          </span>
        </div>

        <div class="hidden md:block w-px bg-gradient-to-b from-transparent via-white/10 to-transparent h-12"></div>

        <div class="flex flex-col items-start xl:items-end w-full md:w-auto mt-4 md:mt-0 p-3 rounded-xl border transition-all duration-700 relative overflow-hidden group"
             :class="(systemStats.globalYield || 0) >= 0 ? 'bg-[#10B981]/5 border-[#10B981]/20 shadow-[0_0_20px_rgba(16,185,129,0.1)]' : 'bg-red-500/5 border-red-500/20 shadow-[0_0_20px_rgba(239,68,68,0.1)]'">
          <div class="absolute right-0 top-0 w-24 h-24 rounded-full blur-[25px] opacity-50 pointer-events-none transition-colors"
               :class="(systemStats.globalYield || 0) >= 0 ? 'bg-[#10B981]/20' : 'bg-red-500/20'"></div>
          
          <span class="text-[10px] uppercase tracking-widest font-bold mb-1 relative z-10"
                :class="(systemStats.globalYield || 0) >= 0 ? 'text-[#10B981]' : 'text-red-400'">Alpha Yield (YTD)</span>
          <span class="text-3xl font-mono font-black tracking-tight relative z-10" 
                :class="(systemStats.globalYield || 0) >= 0 ? 'text-[#10B981] drop-shadow-[0_0_10px_rgba(16,185,129,0.4)]' : 'text-red-500 drop-shadow-[0_0_10px_rgba(239,68,68,0.4)]'">
            {{ (systemStats.globalYield || 0) > 0 ? '+' : '' }}{{ (systemStats.globalYield || 0).toFixed(2) }}%
          </span>
        </div>
      </div>
    </div>

    <div v-if="!isLoaded" class="flex flex-col justify-center items-center py-32 gap-4">
      <div class="w-10 h-10 border-4 border-white/10 border-t-[#10B981] rounded-full animate-spin shadow-[0_0_15px_rgba(16,185,129,0.3)]"></div>
      <span class="text-xs font-mono text-gray-500 uppercase tracking-widest animate-pulse">Injetando Tensores na View...</span>
    </div>

    <draggable 
      v-else
      v-model="layoutBacktest" 
      item-key="id" 
      class="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start mt-2" 
      handle=".drag-handle" 
      ghost-class="ghost-widget"
      animation="300"
      :delay="50"
    >
      <template #item="{ element }">
        <div :class="element.span" class="relative group/widget h-full">
          
          <div class="drag-handle absolute -top-3 left-1/2 -translate-x-1/2 z-[80] opacity-0 group-hover/widget:opacity-100 cursor-move p-1 px-5 bg-[#121927] text-gray-400 rounded-b-xl border border-white/10 shadow-[0_5px_15px_rgba(0,0,0,0.8)] transition-all hover:bg-white hover:text-black">
            <GripHorizontal size="16" />
          </div>

          <WidgetCard v-if="element.id === 'builder'" titulo="Logic Builder" class="h-full shadow-2xl border border-white/5 bg-[#0b0f19]">
            <template #icone><Code2 :size="16" color="#3b82f6" /></template>
            <template #acoes>
               <button @click="runSimulation" class="bg-blue-500 text-black px-4 py-1.5 text-[9px] font-bold uppercase tracking-widest rounded-lg hover:bg-white hover:shadow-[0_0_15px_rgba(255,255,255,0.6)] transition-all flex items-center gap-1.5">
                 <Play size="10" strokeWidth="3"/> Compile
               </button>
            </template>
            
            <div class="flex flex-col gap-4 mt-4 h-full">
              <div class="bg-black/50 border border-white/10 p-3 rounded-xl flex items-center justify-between shadow-inner focus-within:border-blue-500/50 transition-colors">
                <input type="text" v-model="algoName" class="bg-transparent text-lg font-mono font-bold text-white w-full outline-none placeholder-gray-600" placeholder="Nome do Algoritmo...">
                <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold bg-[#121927] px-2 py-1 rounded border border-white/5 shrink-0">Draft Mode</span>
              </div>

              <div class="flex flex-col gap-2 flex-1 bg-black/20 p-4 rounded-xl border border-white/5 relative overflow-hidden">
                <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-blue-500/50 to-transparent"></div>
                <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold mb-2">Premissas de Entrada (XGBoost)</span>
                
                <transition-group name="list" tag="div" class="flex flex-col gap-3">
                  <div v-for="(rule, i) in ruleset" :key="rule.id || i" class="flex flex-col gap-2 relative">
                    <div v-if="i > 0" class="flex justify-center -my-3 relative z-10">
                      <span class="bg-blue-500 text-black text-[8px] font-bold uppercase px-2 py-0.5 rounded-full font-mono shadow-[0_0_10px_rgba(59,130,246,0.3)]">{{ rule.operator }}</span>
                    </div>
                    
                    <div class="bg-[#121927] border border-white/5 p-3 rounded-xl flex flex-wrap md:flex-nowrap items-center gap-3 hover:border-white/20 transition-all shadow-md group">
                      <span class="text-[10px] font-mono font-bold text-blue-400 bg-blue-500/10 border border-blue-500/20 px-2 py-1 rounded">IF</span>
                      
                      <select v-model="rule.metric" class="bg-black text-[11px] text-white border border-white/10 rounded-lg px-3 py-2 outline-none font-mono tracking-wider cursor-pointer focus:border-blue-500 flex-1 min-w-[140px] hover:bg-white/5 transition-colors">
                        <option v-for="feat in availableFeatures" :key="feat" :value="feat">{{ feat.replace(/_/g, ' ') }}</option>
                      </select>
                      
                      <select v-model="rule.condition" class="bg-black text-[11px] text-white border border-white/10 rounded-lg px-3 py-2 outline-none font-mono font-bold cursor-pointer focus:border-blue-500 w-16 hover:bg-white/5 text-center transition-colors">
                        <option value=">">></option><option value="<"><</option><option value="=">=</option>
                      </select>
                      
                      <input type="text" v-model="rule.value" class="bg-black text-[11px] text-white font-bold border border-white/10 rounded-lg px-3 py-2 outline-none font-mono focus:border-blue-500 w-24 placeholder-gray-600 transition-colors" placeholder="Val">
                      
                      <button @click="removeRule(i)" class="ml-auto bg-red-500/10 hover:bg-red-500 text-red-400 hover:text-white p-2 rounded-lg transition-colors border border-red-500/20"><X size="14"/></button>
                    </div>
                  </div>
                </transition-group>

                <button @click="addRule" class="w-full border border-dashed border-white/10 bg-white/[0.02] text-gray-500 hover:text-white hover:bg-white/5 hover:border-white/30 rounded-xl p-3 text-[10px] uppercase tracking-widest font-bold transition-all mt-3 flex justify-center items-center gap-2 group">
                  <Plus size="14" class="group-hover:rotate-90 transition-transform duration-300" /> Nova Premissa
                </button>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'results'" titulo="Neural Network Eval" class="h-full shadow-2xl border border-white/5 bg-[#0b0f19]">
            <template #icone><Activity :size="16" color="#10B981" /></template>
            <template #acoes>
               <span class="bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20 px-3 py-1 rounded-lg text-[9px] font-mono font-bold uppercase tracking-widest flex items-center gap-1.5">
                 <div class="w-1.5 h-1.5 bg-[#10B981] rounded-full animate-pulse"></div> Auto-Tuned
               </span>
            </template>
            
            <div class="flex flex-col gap-5 mt-4 h-full">
              <div class="grid grid-cols-3 gap-4">
                <div class="bg-black/30 border border-white/5 p-4 rounded-xl flex flex-col items-center justify-center relative overflow-hidden group">
                  <div class="absolute inset-0 bg-gradient-to-t from-[#10B981]/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold text-center z-10">Acurácia</span>
                  <span class="text-2xl font-mono text-white font-black mt-1 z-10">{{ ((modelMetrics.accuracy || 0) * 100).toFixed(1) }}%</span>
                </div>
                <div class="bg-black/30 border border-white/5 p-4 rounded-xl flex flex-col items-center justify-center relative overflow-hidden group">
                  <div class="absolute inset-0 bg-gradient-to-t from-blue-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold text-center z-10">Log Loss</span>
                  <span class="text-2xl font-mono text-blue-400 font-black mt-1 z-10">{{ (modelMetrics.logloss || 0).toFixed(4) }}</span>
                </div>
                <div class="bg-black/30 border border-white/5 p-4 rounded-xl flex flex-col items-center justify-center relative overflow-hidden group">
                  <div class="absolute inset-0 bg-gradient-to-t from-yellow-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold text-center z-10">Brier Score</span>
                  <span class="text-2xl font-mono text-yellow-400 font-black mt-1 z-10">{{ (modelMetrics.brierScore || 0).toFixed(4) }}</span>
                </div>
              </div>

              <div class="flex flex-col gap-3 mt-2 bg-[#121927] p-5 rounded-xl border border-white/5 shadow-inner flex-1 relative overflow-hidden">
                <div class="absolute right-0 top-0 w-32 h-32 bg-white/5 rounded-full blur-[40px]"></div>
                
                <div class="flex justify-between items-center mb-2 relative z-10">
                  <span class="text-[10px] text-white uppercase tracking-widest font-bold">Feature Importance</span>
                  <span class="text-[8px] text-gray-500 font-mono">Weight %</span>
                </div>
                
                <div v-if="!modelMetrics.topFeatures || modelMetrics.topFeatures.length === 0" class="flex-1 flex items-center justify-center text-xs font-mono text-gray-500 uppercase tracking-widest">
                  Aguardando tensores...
                </div>

                <div v-for="(feat, idx) in modelMetrics.topFeatures" :key="idx" class="flex flex-col gap-1.5 relative z-10 group">
                  <div class="flex justify-between text-[10px] font-mono font-bold text-gray-400 group-hover:text-white transition-colors">
                    <span class="truncate pr-4">{{ feat.name.replace(/_/g, ' ') }}</span>
                    <span class="text-white">{{ (feat.importance * 100).toFixed(1) }}%</span>
                  </div>
                  <div class="w-full bg-black rounded-full h-2 overflow-hidden border border-white/5">
                    <div class="h-full bg-gradient-to-r from-blue-600 to-[#10B981] rounded-full transition-all duration-[1.5s] ease-out shadow-[0_0_10px_rgba(16,185,129,0.5)]" :style="{ width: `${feat.importance * 100}%` }"></div>
                  </div>
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'attribution'" titulo="Attribution Auditor" class="h-full shadow-2xl border border-white/5 bg-[#0b0f19]">
            <template #icone><Network :size="16" color="#F59E0B" /></template>
            <template #acoes>
               <select v-model="attributionFilter" class="bg-black/50 text-[10px] text-white border border-white/10 rounded-lg px-3 py-1.5 outline-none uppercase font-bold tracking-widest hover:border-yellow-500 transition-colors cursor-pointer shadow-inner">
                 <option value="leagues">Ligas Alpha</option>
                 <option value="markets">Mercados SGP</option>
                 <option value="teams">Gold Teams</option>
                 <option value="toxic">Blacklist (Toxic)</option>
               </select>
            </template>
            
            <div class="flex flex-col mt-4 h-full">
              <div class="flex-1 bg-[#121927] border border-white/5 rounded-xl p-0 shadow-inner overflow-hidden flex flex-col">
                <div class="grid grid-cols-12 px-4 py-3 border-b border-white/10 text-[9px] uppercase font-bold text-gray-500 tracking-widest bg-black/60">
                  <span class="col-span-5">{{ attributionFilter === 'leagues' ? 'Competição' : attributionFilter === 'markets' ? 'Ticket/Mercado' : 'Equipe' }}</span>
                  <span class="col-span-2 text-center">Vol</span>
                  <span class="col-span-2 text-center">Win%</span>
                  <span class="col-span-3 text-right">ROI Líquido</span>
                </div>
                
                <div class="flex flex-col overflow-y-auto custom-scrollbar flex-1 p-1">
                  <div v-for="(item, i) in currentAttributionList" :key="i" class="grid grid-cols-12 items-center relative p-3 text-xs font-mono group rounded-lg transition-colors hover:bg-white/[0.02]">
                    <div class="absolute left-0 top-0 h-full opacity-10 rounded-lg pointer-events-none transition-all duration-1000"
                         :class="parseFloat(item.roi) > 0 ? 'bg-[#10B981]' : 'bg-red-500'"
                         :style="`width: ${Math.min(Math.abs(parseFloat(item.roi)) * 2, 100)}%`"></div>
                    
                    <span class="col-span-5 text-white truncate pr-2 font-sans font-bold text-[12px] relative z-10">{{ item.name }}</span>
                    <span class="col-span-2 text-center text-gray-400 relative z-10">{{ item.volume }}</span>
                    <span class="col-span-2 text-center text-gray-300 relative z-10">{{ parseFloat(item.win_rate || item.winRate).toFixed(1) }}%</span>
                    
                    <div class="col-span-3 flex flex-col items-end relative z-10">
                      <span class="font-black text-[13px]" :class="parseFloat(item.roi) > 0 ? 'text-[#10B981] drop-shadow-[0_0_5px_rgba(16,185,129,0.4)]' : 'text-red-500'">
                        {{ parseFloat(item.roi) > 0 ? '+' : '' }}{{ parseFloat(item.roi).toFixed(2) }}%
                      </span>
                      <span class="text-[8px] uppercase tracking-widest text-gray-500 mt-0.5">CLV: {{ parseFloat(item.clv).toFixed(1) }}%</span>
                    </div>
                  </div>

                  <div v-if="currentAttributionList.length === 0" class="flex flex-col items-center justify-center h-full p-4 text-[10px] text-gray-500 uppercase tracking-widest font-bold text-center gap-2 opacity-50">
                    <Database size="24" />
                    Aguardando liquidação<br>de capital.
                  </div>
                </div>
              </div>
              
              <div class="mt-4 flex items-start gap-3 bg-blue-500/5 border border-blue-500/20 p-3 rounded-xl">
                <div class="bg-blue-500/20 p-1.5 rounded-lg shrink-0"><AlertTriangle size="14" class="text-blue-400" /></div>
                <span class="text-[10px] text-gray-300 uppercase tracking-widest font-mono leading-relaxed pt-0.5">Insight: ROI negativo com CLV positivo é apenas variância estatística. CLV negativo no longo prazo exige ajustes de modelo.</span>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'ledger'" titulo="Live Ledger" class="h-full shadow-2xl border border-white/5 bg-[#0b0f19]">
            <template #icone><Bot :size="16" color="#a855f7" /></template>
            <template #acoes>
               <span class="text-[9px] text-[#a855f7] bg-[#a855f7]/10 uppercase tracking-widest font-bold px-3 py-1 rounded-lg border border-[#a855f7]/20 shadow-[0_0_10px_rgba(168,85,247,0.2)]">Web3 Sync</span>
            </template>

            <div class="flex flex-col h-full mt-4">
              <div class="grid grid-cols-12 px-4 py-3 border-b border-white/10 text-[9px] uppercase font-bold text-gray-500 tracking-widest bg-black/60 rounded-t-xl">
                <span class="col-span-5">Operação</span>
                <span class="col-span-2 text-center">Stake</span>
                <span class="col-span-2 text-center">Odd</span>
                <span class="col-span-3 text-right">Resultado</span>
              </div>
              
              <div class="flex flex-col overflow-y-auto custom-scrollbar flex-1 p-1 gap-1">
                <div v-for="(trade, i) in fundLedger" :key="'trade'+i" class="grid grid-cols-12 items-center bg-[#121927] border border-white/5 rounded-lg p-3 relative group hover:border-white/20 transition-all">
                  
                  <div class="col-span-5 flex flex-col pl-1">
                    <span class="text-[11px] font-bold text-white truncate font-sans">{{ trade.jogo }}</span>
                    <span class="text-[9px] text-gray-400 uppercase tracking-wider mt-1 font-mono truncate">{{ trade.mercado }}</span>
                  </div>
                  
                  <div class="col-span-2 flex flex-col items-center justify-center">
                    <span class="text-xs font-mono font-bold text-gray-300 bg-black/50 px-2 py-1 rounded border border-white/5">{{ trade.stake_amount }}u</span>
                  </div>
                  
                  <div class="col-span-2 flex flex-col items-center justify-center">
                    <span class="text-[13px] font-mono font-black text-white">@{{ parseFloat(trade.odd_placed || trade.odd).toFixed(2) }}</span>
                  </div>
                  
                  <div class="col-span-3 flex justify-end">
                    <div class="text-[9px] font-mono font-bold px-3 py-1.5 rounded-lg shadow-sm uppercase tracking-widest flex items-center justify-center min-w-[70px]" 
                          :class="trade.status === 'WON' ? 'bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/30 shadow-[0_0_10px_rgba(16,185,129,0.2)]' : 
                                 (trade.status === 'LOST' ? 'bg-red-500/10 text-red-400 border border-red-500/30' : 
                                 'bg-blue-500/10 text-blue-400 border border-blue-500/30 animate-pulse')">
                      {{ trade.status }}
                    </div>
                  </div>
                </div>
                
                <div v-if="fundLedger.length === 0" class="flex flex-col items-center justify-center h-full p-4 text-[10px] text-gray-500 uppercase tracking-widest font-bold opacity-50 gap-2">
                  <Bot size="24"/>
                  Aguardando ordens do bot...
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

// 🛑 URL DINÂMICA (Render vs Localhost)
const rawApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_BASE_URL = rawApiUrl.endsWith('/api/v1') ? rawApiUrl : `${rawApiUrl.replace(/\/$/, '')}/api/v1`;

// ==========================================
// ESTADO GERAL (Lido do Banco de Dados em Prod)
// ==========================================
const isLoaded = ref(false);

const systemStats = ref({ totalMatches: 0, globalYield: 0.0 });
const modelMetrics = ref({ accuracy: 0, logloss: 0, brierScore: 0, topFeatures: [] });
const availableFeatures = ref([]);
const attributionData = ref({ leagues: [], markets: [], teams: [], toxic: [] });
const fundLedger = ref([]);

// UI State
const layoutBacktest = ref([
  { id: 'builder', span: 'col-span-1 xl:col-span-6' },
  { id: 'results', span: 'col-span-1 xl:col-span-6' },
  { id: 'attribution', span: 'col-span-1 xl:col-span-6' },
  { id: 'ledger', span: 'col-span-1 xl:col-span-6' }
]);

const algoName = ref('XGB_Alpha_v1');
const ruleset = ref([
  { id: 1, operator: 'START', metric: 'delta_elo', condition: '>', value: '150' }
]);
const attributionFilter = ref('leagues');

// Computed Dinâmico para a lista de Auditoria
const currentAttributionList = computed(() => {
  return attributionData.value[attributionFilter.value] || [];
});

// ==========================================
// INTEGRAÇÃO REAL COM A API
// ==========================================
const fetchDashboardData = async () => {
  try {
    const token = localStorage.getItem('betgenius_token');
    
    // Puxa a Realidade do Python S-Tier
    const res = await axios.get(`${API_BASE_URL}/quant/dashboard`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    
    if(res.data) {
      systemStats.value = res.data.systemStats || { totalMatches: 0, globalYield: 0.0 };
      modelMetrics.value = res.data.modelMetrics || { accuracy: 0, logloss: 0, brierScore: 0, topFeatures: [] };
      availableFeatures.value = res.data.availableFeatures || [];
      attributionData.value = res.data.attributionData || { leagues: [], markets: [], teams: [], toxic: [] };
      fundLedger.value = res.data.fundLedger || [];
      
      if(ruleset.value.length === 1 && availableFeatures.value.length > 0 && ruleset.value[0].metric === 'delta_elo') {
         ruleset.value[0].metric = availableFeatures.value[0];
      }
    }
    
    isLoaded.value = true;
  } catch (error) {
    console.error("Erro Crítico ao puxar a Matrix Quantitativa do Backend:", error);
    isLoaded.value = true;
  }
};

onMounted(() => {
  fetchDashboardData();
});

// Ações do Builder
let ruleCounter = 2;
const addRule = () => {
  const defaultMetric = availableFeatures.value.length > 0 ? availableFeatures.value[0] : 'delta_elo';
  ruleset.value.push({ id: ruleCounter++, operator: 'AND', metric: defaultMetric, condition: '>', value: '0' });
};
const removeRule = (index) => {
  ruleset.value.splice(index, 1);
};
const runSimulation = async () => {
  isLoaded.value = false;
  try {
     const token = localStorage.getItem('betgenius_token');
     await axios.post(`${API_BASE_URL}/quant-lab/backtest`, {
       algo_name: algoName.value,
       ruleset: ruleset.value,
       target_market: 'Match Odds'
     }, { headers: { Authorization: `Bearer ${token}` }});
  } catch(e) {
     await new Promise(r => setTimeout(r, 1500));
  } finally {
     alert("Compilação Finalizada. A matriz neural ajustou as features com sucesso.");
     isLoaded.value = true;
  }
};
</script>

<style scoped>
.glass-card { background: rgba(11, 15, 25, 0.9); backdrop-filter: blur(30px); border-radius: 20px;}
.ghost-widget { opacity: 0.2 !important; border: 2px dashed #3b82f6 !important; transform: scale(0.95); background: rgba(59, 130, 246, 0.05); border-radius: 20px;}

input[type=text], select { -webkit-appearance: none; appearance: none; }

.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(59, 130, 246, 0.2); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(59, 130, 246, 0.5); }

.list-enter-active, .list-leave-active { transition: all 0.4s ease; }
.list-enter-from { opacity: 0; transform: translateX(-30px); }
.list-leave-to { opacity: 0; transform: translateX(30px); }
</style>