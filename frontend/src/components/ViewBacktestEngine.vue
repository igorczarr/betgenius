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
            <div class="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse shadow-[0_0_8px_#3b82f6]"></div> Backtesting Engine
          </span>
        </div>
      </div>

      <div class="flex flex-wrap md:flex-nowrap justify-between xl:justify-end gap-6 md:gap-12 w-full xl:w-3/4 z-10">
        <div class="flex flex-col items-start xl:items-end w-[45%] md:w-auto">
          <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 flex items-center gap-1"><Cpu size="12"/> Bots Ativos (Live)</span>
          <span class="text-lg font-mono text-white">03 <span class="text-[10px] text-gray-500 bg-white/5 px-1.5 py-0.5 rounded ml-1">Executando</span></span>
        </div>
        
        <div class="hidden md:block w-px bg-gradient-to-b from-transparent via-white/10 to-transparent h-12"></div>
        
        <div class="flex flex-col items-start xl:items-end w-[45%] md:w-auto">
          <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 flex items-center gap-1"><Database size="12"/> Dataset Histórico</span>
          <span class="text-xl font-mono text-white font-bold">142.5k <span class="text-[10px] text-gray-500 bg-black/40 px-1.5 py-0.5 rounded border border-white/5 ml-1">Partidas</span></span>
        </div>

        <div class="hidden md:block w-px bg-gradient-to-b from-transparent via-white/10 to-transparent h-12"></div>

        <div class="flex flex-col items-start xl:items-end w-full md:w-auto mt-4 md:mt-0 bg-black/30 p-3 rounded-lg border border-white/5 shadow-inner">
          <span class="text-[10px] text-[#10B981] uppercase tracking-widest font-bold mb-1">Global Algo Yield (YTD)</span>
          <span class="text-3xl font-mono text-[#10B981] font-bold drop-shadow-[0_0_15px_rgba(16,185,129,0.3)] tracking-tight">+11.4%</span>
        </div>
      </div>
    </div>

    <draggable 
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

          <WidgetCard v-if="element.id === 'builder'" titulo="Algorithm Builder (Regras Lógicas)" class="h-full shadow-[0_15px_40px_rgba(0,0,0,0.3)] border-t-2 border-blue-500">
            <template #icone><Code2 :size="16" color="#3b82f6" /></template>
            <template #acoes>
               <button class="bg-[#10B981] text-black px-3 py-1 text-[9px] font-bold uppercase tracking-widest rounded hover:bg-white transition-colors shadow-[0_0_10px_rgba(16,185,129,0.4)] flex items-center gap-1.5"><Play size="10" strokeWidth="3"/> Run Backtest</button>
            </template>
            
            <div class="flex flex-col gap-3 mt-3 h-full">
              <div class="bg-black/20 border border-white/5 p-3 rounded-lg flex items-center justify-between shadow-inner">
                <input type="text" v-model="algoName" class="bg-transparent text-lg font-mono font-bold text-white w-full outline-none focus:border-b focus:border-blue-500 transition-all placeholder-gray-600" placeholder="Nome do Algoritmo...">
                <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold bg-[#121927] px-2 py-1 rounded border border-white/5">v1.0.4 - Draft</span>
              </div>

              <div class="flex flex-col gap-2 flex-1 mt-2">
                <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold border-b border-white/10 pb-1 mb-1">Condições de Entrada (Entry Rules)</span>
                
                <div v-for="(rule, i) in ruleset" :key="'rule'+i" class="flex flex-col gap-2">
                  <div v-if="i > 0" class="flex justify-center -my-2 relative z-10">
                    <span class="bg-blue-500/20 text-blue-400 border border-blue-500/30 text-[8px] font-bold uppercase px-2 py-0.5 rounded-full font-mono">{{ rule.operator }}</span>
                  </div>
                  <div class="bg-[#121927] border border-white/5 p-3 rounded-lg flex items-center gap-3 hover:border-blue-500/30 transition-colors group">
                    <span class="text-[10px] font-mono text-gray-500 bg-black/50 px-2 py-1 rounded">IF</span>
                    
                    <select v-model="rule.metric" class="bg-black text-[10px] text-white border border-gray-700 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer focus:border-blue-500 w-1/3">
                      <option value="asian_drop">Asian Line Drop (%)</option>
                      <option value="xg_diff">xG Difference (HT)</option>
                      <option value="z_score">Z-Score Value</option>
                    </select>
                    
                    <select v-model="rule.condition" class="bg-black text-[10px] text-white border border-gray-700 rounded px-2 py-1 outline-none font-mono cursor-pointer focus:border-blue-500 w-1/6">
                      <option value=">">></option><option value="<"><</option><option value="=">=</option>
                    </select>
                    
                    <input type="text" v-model="rule.value" class="bg-black text-[10px] text-white border border-gray-700 rounded px-2 py-1 outline-none font-mono focus:border-blue-500 w-1/4" placeholder="Valor">
                    
                    <button class="ml-auto text-gray-600 hover:text-red-400 transition-colors"><X size="14"/></button>
                  </div>
                </div>

                <button class="border border-dashed border-white/20 bg-white/5 text-gray-400 hover:text-white hover:bg-white/10 hover:border-white/40 rounded-lg p-2 text-[10px] uppercase tracking-widest font-bold transition-all mt-2 flex justify-center items-center gap-2">
                  <Plus size="12" /> Adicionar Regra
                </button>
              </div>

              <div class="bg-black/40 border border-white/5 p-3 rounded-lg mt-auto flex justify-between items-center shadow-inner">
                <div class="flex flex-col">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold mb-0.5">Ação do Algoritmo</span>
                  <span class="text-xs font-mono font-bold text-[#10B981]">Apostar no Favorito (Handicap)</span>
                </div>
                <div class="flex flex-col items-end">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold mb-0.5">Stake Base</span>
                  <span class="text-xs font-mono font-bold text-white">Kelly / 4</span>
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'results'" titulo="Simulation Results (Últimos 3 Anos)" class="h-full shadow-[0_15px_40px_rgba(0,0,0,0.3)]">
            <template #icone><LineChart :size="16" color="#10B981" /></template>
            <template #acoes>
               <span class="bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/30 px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase tracking-widest flex items-center gap-1.5"><CheckCircle2 size="10"/> Modelo Lucrativo</span>
            </template>
            
            <div class="flex flex-col gap-4 mt-3 h-full">
              <div class="grid grid-cols-4 gap-3">
                <div class="bg-black/20 border border-white/5 p-3 rounded-xl flex flex-col items-center justify-center">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold text-center">Net Profit (PnL)</span>
                  <span class="text-xl font-mono text-[#10B981] font-bold mt-1 drop-shadow-[0_0_5px_currentColor]">+18.4k u</span>
                </div>
                <div class="bg-black/20 border border-white/5 p-3 rounded-xl flex flex-col items-center justify-center">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold text-center">Yield Real</span>
                  <span class="text-xl font-mono text-white font-bold mt-1">+6.2%</span>
                </div>
                <div class="bg-black/20 border border-white/5 p-3 rounded-xl flex flex-col items-center justify-center">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold text-center">Max Drawdown</span>
                  <span class="text-xl font-mono text-red-400 font-bold mt-1">-8.5%</span>
                </div>
                <div class="bg-black/20 border border-white/5 p-3 rounded-xl flex flex-col items-center justify-center">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold text-center">Sharpe Ratio</span>
                  <span class="text-xl font-mono text-blue-400 font-bold mt-1">2.14</span>
                </div>
              </div>

              <div class="flex-1 relative w-full min-h-[220px] bg-[#0b0f19] rounded-xl border border-white/5 overflow-hidden flex items-end pt-4 pr-4 shadow-inner">
                <div class="absolute left-2 top-4 text-[9px] font-mono text-gray-600">+20k u</div>
                <div class="absolute left-2 top-1/2 -translate-y-1/2 text-[9px] font-mono text-gray-600">+10k u</div>
                <div class="absolute left-2 bottom-6 text-[9px] font-mono text-gray-600">0</div>
                
                <div class="absolute inset-0 flex flex-col justify-between py-6 px-12 pointer-events-none opacity-20">
                  <div class="w-full h-px bg-gray-600"></div><div class="w-full h-px bg-gray-600"></div><div class="w-full h-px bg-gray-600"></div>
                </div>

                <svg viewBox="0 0 100 40" class="w-full h-full overflow-visible preserve-3d px-12" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="backtest-grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stop-color="#10B981" stop-opacity="0.2" />
                      <stop offset="100%" stop-color="#10B981" stop-opacity="0" />
                    </linearGradient>
                  </defs>
                  <polygon points="0,40 0,35 15,28 25,32 40,20 55,24 75,12 85,15 100,5 100,40" fill="url(#backtest-grad)" />
                  <polyline points="0,35 15,28 25,32 40,20 55,24 75,12 85,15 100,5" fill="none" stroke="#10B981" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linecap="round" stroke-linejoin="round" />
                  <circle cx="100" cy="5" r="1.5" fill="#fff" stroke="#10B981" stroke-width="1" class="animate-pulse" />
                </svg>

                <div class="absolute bottom-2 right-4 text-[8px] font-mono text-gray-500 uppercase tracking-widest">
                  Amostra: 1,842 Apostas | CLV Beat: 76%
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'hedge_matrix'" titulo="Portfolio Correlation (Hedge Matrix)" class="h-full shadow-[0_15px_40px_rgba(0,0,0,0.3)]">
            <template #icone><Network :size="16" color="#F59E0B" /></template>
            <template #acoes>
               <span class="text-[8px] text-gray-400 font-mono uppercase bg-black/50 px-2 py-0.5 rounded border border-white/10">Matriz de Sobreposição</span>
            </template>
            
            <div class="flex flex-col mt-4 h-full">
              <p class="text-[10px] text-gray-400 mb-3 leading-relaxed px-1">Identifique se seus robôs ativos estão apostando nos mesmos resultados (Sobreposição). <strong class="text-red-400">Vermelho = Alto Risco Simultâneo</strong>.</p>
              
              <div class="flex-1 bg-[#121927] border border-white/5 rounded-xl p-2 shadow-inner overflow-x-auto custom-scrollbar flex flex-col justify-center">
                <div class="min-w-[400px]">
                  <div class="grid grid-cols-4 gap-1 text-[9px] font-mono text-gray-500 font-bold mb-1 pl-[100px]">
                    <div class="text-center">Algo A (Asian)</div>
                    <div class="text-center">Algo B (Goals)</div>
                    <div class="text-center">Algo C (Props)</div>
                    <div class="text-center">Algo D (Late)</div>
                  </div>
                  
                  <div class="flex flex-col gap-1">
                    <div class="flex items-center gap-1">
                      <div class="w-[96px] text-[9px] font-mono text-gray-400 font-bold text-right pr-2">Algo A (Asian)</div>
                      <div class="grid grid-cols-4 gap-1 flex-1">
                        <div class="h-8 bg-gray-800 rounded"></div>
                        <div class="h-8 bg-yellow-500/40 rounded border border-yellow-500/50 flex items-center justify-center text-[10px] font-mono text-white font-bold">0.65</div>
                        <div class="h-8 bg-[#10B981]/20 rounded border border-[#10B981]/30 flex items-center justify-center text-[10px] font-mono text-white font-bold">0.12</div>
                        <div class="h-8 bg-red-500/60 rounded border border-red-500/50 flex items-center justify-center text-[10px] font-mono text-white font-bold shadow-[0_0_10px_rgba(239,68,68,0.3)]">0.88</div>
                      </div>
                    </div>
                    <div class="flex items-center gap-1">
                      <div class="w-[96px] text-[9px] font-mono text-gray-400 font-bold text-right pr-2">Algo B (Goals)</div>
                      <div class="grid grid-cols-4 gap-1 flex-1">
                        <div class="h-8 bg-yellow-500/40 rounded border border-yellow-500/50 flex items-center justify-center text-[10px] font-mono text-white font-bold">0.65</div>
                        <div class="h-8 bg-gray-800 rounded"></div>
                        <div class="h-8 bg-[#10B981]/20 rounded border border-[#10B981]/30 flex items-center justify-center text-[10px] font-mono text-white font-bold">0.24</div>
                        <div class="h-8 bg-yellow-500/20 rounded border border-yellow-500/30 flex items-center justify-center text-[10px] font-mono text-white font-bold">0.45</div>
                      </div>
                    </div>
                    <div class="flex items-center gap-1">
                      <div class="w-[96px] text-[9px] font-mono text-gray-400 font-bold text-right pr-2">Algo C (Props)</div>
                      <div class="grid grid-cols-4 gap-1 flex-1">
                        <div class="h-8 bg-[#10B981]/20 rounded border border-[#10B981]/30 flex items-center justify-center text-[10px] font-mono text-white font-bold">0.12</div>
                        <div class="h-8 bg-[#10B981]/20 rounded border border-[#10B981]/30 flex items-center justify-center text-[10px] font-mono text-white font-bold">0.24</div>
                        <div class="h-8 bg-gray-800 rounded"></div>
                        <div class="h-8 bg-[#10B981]/10 rounded border border-[#10B981]/20 flex items-center justify-center text-[10px] font-mono text-gray-400">0.05</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <div class="mt-3 flex items-center gap-2 bg-red-500/10 border border-red-500/20 p-2 rounded">
                <AlertTriangle size="12" class="text-red-400" />
                <span class="text-[9px] text-gray-300 uppercase tracking-widest font-mono">Alerta: Algo A e Algo D estão 88% correlacionados. Considere Hedge.</span>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'paper_trading'" titulo="Forward Testing (Paper Trading / Fantasma)" class="h-full shadow-[0_15px_40px_rgba(0,0,0,0.3)]">
            <template #icone><Bot :size="16" color="#a855f7" /></template>
            <template #acoes>
               <div class="flex items-center gap-2">
                 <span class="text-[9px] text-gray-400 uppercase tracking-widest font-bold">Modo Ghost</span>
                 <div class="w-8 h-4 bg-[#a855f7]/40 rounded-full relative cursor-pointer border border-[#a855f7]/50 shadow-inner">
                   <div class="absolute right-0.5 top-0.5 w-3 h-3 bg-white rounded-full shadow-sm"></div>
                 </div>
               </div>
            </template>

            <div class="flex flex-col h-full mt-3">
              <div class="grid grid-cols-12 px-3 pb-2 border-b border-white/10 text-[9px] uppercase font-bold text-gray-500 tracking-widest bg-black/30 rounded-t-lg pt-2">
                <span class="col-span-5">Entrada Simulada</span>
                <span class="col-span-2 text-center">Ghost Stake</span>
                <span class="col-span-3 text-center">Odd / EV</span>
                <span class="col-span-2 text-right pr-2">Status</span>
              </div>
              
              <div class="flex flex-col overflow-y-auto custom-scrollbar flex-1 pb-2">
                <div v-for="(trade, i) in paperTrades" :key="'pt'+i" class="grid grid-cols-12 items-center bg-black/10 even:bg-white/[0.02] border-b border-white/5 p-3 relative group">
                  <div class="absolute left-0 top-0 w-1 h-full bg-[#a855f7]"></div>
                  
                  <div class="col-span-5 flex flex-col pl-3">
                    <span class="text-xs font-bold text-white truncate">{{ trade.jogo }}</span>
                    <span class="text-[9px] text-[#a855f7] uppercase tracking-wider mt-0.5 font-mono truncate">{{ trade.mercado }}</span>
                  </div>
                  
                  <div class="col-span-2 flex flex-col items-center justify-center">
                    <span class="text-xs font-mono font-bold text-gray-300">{{ trade.stake }}u</span>
                  </div>
                  
                  <div class="col-span-3 flex flex-col items-center justify-center border-l border-white/5 pl-2">
                    <span class="text-sm font-mono font-bold text-white">{{ trade.odd }}</span>
                    <span class="text-[8px] text-[#10B981] font-bold uppercase tracking-widest mt-0.5">+{{ trade.ev }}% EV</span>
                  </div>
                  
                  <div class="col-span-2 flex justify-end pr-2">
                    <span class="text-[9px] font-mono font-bold px-2 py-0.5 rounded shadow-inner uppercase tracking-widest" :class="trade.status === 'W' ? 'bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/30' : (trade.status === 'L' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-blue-500/20 text-blue-400 border border-blue-500/30 animate-pulse')">
                      {{ trade.status === 'W' ? 'Win' : (trade.status === 'L' ? 'Loss' : 'Live') }}
                    </span>
                  </div>
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
import { ref } from 'vue';
import draggable from 'vuedraggable';
import { 
  GripHorizontal, FlaskConical, Cpu, Database, Code2, 
  Play, X, Plus, LineChart, CheckCircle2, Network, AlertTriangle, Bot
} from 'lucide-vue-next';

import WidgetCard from './WidgetCard.vue';

// ESTRUTURA DRAGGABLE DO BACKTEST ENGINE
const layoutBacktest = ref([
  { id: 'builder', span: 'col-span-1 xl:col-span-6' },
  { id: 'results', span: 'col-span-1 xl:col-span-6' },
  { id: 'hedge_matrix', span: 'col-span-1 xl:col-span-6' },
  { id: 'paper_trading', span: 'col-span-1 xl:col-span-6' }
]);

// ESTADOS DO BUILDER
const algoName = ref('Asian Drop Exploiter');
const ruleset = ref([
  { operator: 'START', metric: 'asian_drop', condition: '>', value: '5.0' },
  { operator: 'AND', metric: 'xg_diff', condition: '>', value: '0.8' }
]);

// ESTADOS DO PAPER TRADING (FANTASMA)
const paperTrades = ref([
  { jogo: "Milan x Inter", mercado: "Inter AH +0.0", stake: "1.5", odd: "1.92", ev: "6.4", status: "Live" },
  { jogo: "Sevilla x Betis", mercado: "Under 2.5 Gols", stake: "2.0", odd: "1.80", ev: "4.1", status: "W" },
  { jogo: "Arsenal x Chelsea", mercado: "Arsenal ML", stake: "1.0", odd: "2.15", ev: "5.5", status: "L" },
  { jogo: "Lazio x Roma", mercado: "BTTS - Sim", stake: "1.2", odd: "1.75", ev: "3.2", status: "W" },
]);
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