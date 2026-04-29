<template>
  <div class="flex flex-col gap-6 w-full h-full relative fade-in-up pb-10">
    
    <div class="glass-card shrink-0 p-6 md:p-8 relative overflow-hidden flex flex-col xl:flex-row justify-between items-center border-t-4 shadow-[0_20px_50px_rgba(0,0,0,0.5)] border-[#10B981]">
      <div class="absolute -right-40 -top-40 w-96 h-96 rounded-full blur-[100px] pointer-events-none opacity-10 bg-[#10B981]"></div>
      
      <div class="flex items-center gap-5 w-full xl:w-1/4 z-10 mb-6 xl:mb-0">
        <div class="w-16 h-16 rounded-xl bg-black/60 border border-[#10B981]/30 flex items-center justify-center shadow-[0_0_30px_rgba(16,185,129,0.15)] relative overflow-hidden">
          <div class="absolute inset-0 bg-gradient-to-br from-[#10B981]/20 to-transparent"></div>
          <Wallet :size="30" class="text-[#10B981] relative z-10" />
        </div>
        <div class="text-left flex flex-col">
          <h2 class="text-2xl font-mono text-white tracking-widest drop-shadow-md">ALPHA FUND</h2>
          <span class="text-[10px] text-[#10B981] uppercase tracking-widest font-bold flex items-center gap-1.5 mt-0.5">
            <div class="w-1.5 h-1.5 bg-[#10B981] rounded-full animate-pulse shadow-[0_0_8px_#10B981]"></div> AUM Real Management
          </span>
        </div>
      </div>

      <div class="flex flex-wrap md:flex-nowrap justify-between xl:justify-end items-center gap-6 md:gap-12 w-full xl:w-3/4 z-10">
        
        <div class="flex flex-col items-start xl:items-end w-[45%] md:w-auto">
          <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 flex items-center gap-1"><Activity size="12"/> Exposição Ativa</span>
          <span class="text-lg font-mono text-white">{{ statsBanca.exposicao }} <span class="text-[10px] text-gray-500 bg-white/5 px-1.5 py-0.5 rounded ml-1">{{ statsBanca.exposicaoPct }}%</span></span>
        </div>
        
        <div class="hidden md:block w-px bg-gradient-to-b from-transparent via-white/10 to-transparent h-12"></div>
        
        <div class="flex flex-col items-start xl:items-end w-[45%] md:w-auto">
          <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 flex items-center gap-1"><Target size="12"/> Yield (Global)</span>
          <span class="text-xl font-mono text-white font-bold" :class="parseFloat(statsBanca.yield) >= 0 ? 'text-[#10B981]' : 'text-red-500'">
            {{ statsBanca.yield }}% 
          </span>
        </div>

        <div class="hidden md:block w-px bg-gradient-to-b from-transparent via-white/10 to-transparent h-12"></div>

        <div class="flex items-center gap-4 w-full md:w-auto mt-4 md:mt-0 bg-black/30 p-4 rounded-xl border border-white/5 shadow-inner">
          <div class="flex flex-col items-end">
            <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold mb-1">AUM (Bankroll)</span>
            <span class="text-2xl font-mono text-white font-bold drop-shadow-[0_0_15px_rgba(255,255,255,0.2)] tracking-tight">{{ statsBanca.aum }}</span>
          </div>
          <button @click="showAporteModal = true" class="w-10 h-10 bg-[#10B981]/10 hover:bg-[#10B981] border border-[#10B981]/30 rounded-lg flex items-center justify-center text-[#10B981] hover:text-black transition-all shadow-[0_0_15px_rgba(16,185,129,0.15)] group" title="Injetar Capital">
            <Plus :size="20" class="group-hover:scale-125 transition-transform" />
          </button>
        </div>

      </div>
    </div>

    <draggable 
      v-model="layoutBanca" 
      item-key="id" 
      class="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start mt-2" 
      handle=".drag-handle" 
      ghost-class="ghost-widget"
      animation="250"
    >
      <template #item="{ element }">
        <div :class="element.span" class="relative group/widget h-full">
          
          <div class="drag-handle absolute -top-3 left-1/2 -translate-x-1/2 z-[80] opacity-0 group-hover/widget:opacity-100 cursor-move p-1 px-5 bg-black text-[#10B981] rounded-b-xl border border-white/10 shadow-[0_5px_15px_rgba(0,0,0,0.8)] transition-all hover:bg-[#10B981] hover:text-black">
            <GripHorizontal size="16" />
          </div>

          <WidgetCard v-if="element.id === 'equity'" titulo="Performance vs Expected Value (CLV)" class="h-full">
            <template #icone><LineChart :size="16" color="#10B981" /></template>
            <template #acoes>
              <select class="bg-black/40 text-[10px] text-white border border-white/10 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-[#10B981]">
                <option>YTD (Year to Date)</option>
                <option>All Time</option>
              </select>
            </template>
            
            <div class="flex flex-col gap-4 mt-4 h-full">
              <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <div class="bg-black/20 border border-white/5 p-3 rounded-xl flex flex-col">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">Z-Score (Significância)</span>
                  <span class="text-xl font-mono text-[#10B981] font-bold mt-1">{{ statsPerformance.zScore }}</span>
                </div>
                <div class="bg-black/20 border border-white/5 p-3 rounded-xl flex flex-col">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">Turnover (Volume)</span>
                  <span class="text-xl font-mono text-white font-bold mt-1">{{ statsPerformance.turnover }}</span>
                </div>
                <div class="bg-black/20 border border-white/5 p-3 rounded-xl flex flex-col">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">ROI Ponderado</span>
                  <span class="text-xl font-mono text-[#10B981] font-bold mt-1">{{ statsPerformance.roi }}</span>
                </div>
                <div class="bg-black/20 border border-white/5 p-3 rounded-xl flex flex-col">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">CLV Beating Rate</span>
                  <span class="text-xl font-mono text-yellow-500 font-bold mt-1">{{ statsPerformance.clvRate }}</span>
                </div>
              </div>

              <div class="flex-1 relative w-full min-h-[220px] bg-[#0b0f19] rounded-xl border border-white/5 overflow-hidden flex items-end pt-4 pr-4 shadow-inner">
                <div class="absolute inset-0 flex flex-col justify-between py-6 px-12 pointer-events-none opacity-20">
                  <div class="w-full h-px bg-gray-600"></div><div class="w-full h-px bg-gray-600"></div><div class="w-full h-px bg-gray-600"></div>
                </div>
                <svg viewBox="0 0 100 40" class="w-full h-full overflow-visible preserve-3d px-12" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="equity-grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stop-color="#10B981" stop-opacity="0.2" />
                      <stop offset="100%" stop-color="#10B981" stop-opacity="0" />
                    </linearGradient>
                  </defs>
                  <polygon points="0,40 0,35 10,34 20,28 30,29 40,22 50,25 60,16 70,17 80,10 90,12 100,4 100,40" fill="url(#equity-grad)" />
                  <polyline points="0,35 10,34 20,28 30,29 40,22 50,25 60,16 70,17 80,10 90,12 100,4" fill="none" stroke="#10B981" stroke-width="2" vector-effect="non-scaling-stroke" />
                  <circle cx="100" cy="4" r="1.5" fill="#fff" stroke="#10B981" stroke-width="1" class="animate-pulse" />
                </svg>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'risco'" titulo="Risk Management & Ruin" class="h-full">
            <template #icone><ShieldAlert :size="16" color="#EF4444" /></template>
            <div class="flex flex-col gap-4 mt-2 h-full">
              <div class="bg-[#121927] border border-white/5 p-4 rounded-xl flex flex-col relative overflow-hidden shadow-inner">
                <div class="absolute top-0 right-0 w-32 h-32 bg-red-500/10 rounded-full blur-2xl"></div>
                <div class="flex justify-between items-start mb-4">
                  <div class="flex flex-col">
                    <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold flex items-center gap-1"><TrendingDown size="12" class="text-red-500"/> Current Drawdown</span>
                    <span class="text-2xl font-mono text-red-400 font-bold drop-shadow-md">{{ statsRisco.drawdownAtual }}</span>
                  </div>
                </div>
                <div class="w-full flex flex-col gap-1">
                  <div class="flex justify-between text-[8px] uppercase tracking-widest font-mono text-gray-500 mb-0.5">
                    <span>Seguro</span><span>Perigo</span><span>Ruína</span>
                  </div>
                  <div class="w-full h-2 bg-gray-800 rounded-full overflow-hidden flex">
                    <div class="h-full bg-red-500 shadow-[0_0_10px_#EF4444] transition-all duration-1000" style="width: 5%"></div>
                  </div>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-3 mt-auto">
                <div class="bg-black/30 border border-white/5 p-3 rounded-lg flex flex-col gap-1">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">Max Drawdown</span>
                  <span class="text-xl font-mono text-white font-bold">{{ statsRisco.drawdownMax }}</span>
                </div>
                <div class="bg-black/30 border border-white/5 p-3 rounded-lg flex flex-col gap-1">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">Sharpe Ratio</span>
                  <span class="text-xl font-mono text-yellow-500 font-bold">{{ statsRisco.sharpe }}</span>
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'atribuicao'" titulo="Edge Attribution" class="h-full">
            <template #icone><PieChart :size="16" color="#3B82F6" /></template>
            <div class="flex flex-col h-full mt-4">
              <div class="flex flex-col gap-3 flex-1">
                <div class="grid grid-cols-12 text-[9px] uppercase tracking-widest font-bold text-gray-500 border-b border-white/10 pb-2">
                  <span class="col-span-6">Mercado Foco</span>
                  <span class="col-span-3 text-center">Yield</span>
                  <span class="col-span-3 text-right">Weight</span>
                </div>
                <div v-if="edgeMercado.length === 0" class="text-center py-4 text-gray-500 text-[9px] uppercase font-mono">Sem dados processados.</div>
                <div v-for="(edge, i) in edgeMercado" :key="'em'+i" class="grid grid-cols-12 items-center py-2 border-b border-white/5 group">
                  <span class="col-span-6 text-xs font-bold text-white group-hover:text-[#3B82F6] transition-colors truncate">{{ edge.nome }}</span>
                  <div class="col-span-3 flex justify-center">
                    <span class="text-xs font-mono font-bold px-1.5 py-0.5 rounded border" :class="edge.yield > 0 ? 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/30' : 'bg-red-500/10 text-red-500 border-red-500/30'">{{ edge.yield > 0 ? '+' : ''}}{{ edge.yield }}%</span>
                  </div>
                  <div class="col-span-3 flex items-center justify-end gap-2">
                    <span class="text-[9px] text-gray-500 font-mono">{{ edge.weight }}%</span>
                  </div>
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'alocacao'" titulo="Capital Allocation & Sizing" class="h-full">
            <template #icone><Crosshair :size="16" color="#F59E0B" /></template>
            <div class="flex flex-col gap-4 mt-2 h-full">
              <div class="flex gap-4 items-center bg-black/20 p-4 rounded-xl border border-white/5 shadow-inner">
                <div class="w-16 h-16 rounded-full border-[6px] border-gray-800 flex items-center justify-center transform -rotate-45 shadow-lg relative">
                   <div class="absolute inset-[-6px] rounded-full border-[6px] border-transparent border-t-[#F59E0B] border-r-[#F59E0B] transition-all duration-1000" :style="`transform: rotate(${(statsAlocacao.exposicaoPct / 100) * 360}deg)`"></div>
                   <span class="text-[10px] font-mono font-bold text-white transform rotate-45">{{ statsAlocacao.exposicaoPct.toFixed(1) }}%</span>
                </div>
                <div class="flex flex-col">
                  <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1">Exposição Atual da Banca</span>
                  <span class="text-sm font-mono text-gray-300">{{ statsAlocacao.exposicaoValor }} alocados.</span>
                </div>
              </div>
              <div class="flex flex-col gap-2 mt-auto">
                <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold border-b border-white/5 pb-1">Diretrizes (Kelly Criterion)</span>
                <div class="flex justify-between items-center bg-black/30 p-2.5 rounded-lg border border-white/5">
                  <span class="text-xs font-bold text-white">Kelly Fracionado</span>
                  <span class="text-sm font-mono text-yellow-500 font-bold">{{ statsAlocacao.kellyMult }}</span>
                </div>
                <div class="flex justify-between items-center bg-black/30 p-2.5 rounded-lg border border-white/5">
                  <span class="text-xs font-bold text-white">Unidade Padrão (1u)</span>
                  <span class="text-sm font-mono text-white font-bold">{{ statsAlocacao.unidade }}</span>
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'ledger'" titulo="Ledger de Operações Executadas" class="h-full min-h-[350px]">
            <template #icone><LayoutList :size="16" color="var(--text-muted)" /></template>
            <div class="flex flex-col h-full mt-2">
              <div class="grid grid-cols-12 px-4 pb-2 border-b border-white/10 text-[9px] uppercase font-bold text-gray-500 tracking-widest bg-black/30 rounded-t-lg pt-3">
                <span class="col-span-2">Ticker / Hora</span>
                <span class="col-span-4">Ativo (Jogo / Mercado)</span>
                <span class="col-span-1 text-center">Odd</span>
                <span class="col-span-2 text-center">CLV Edge</span>
                <span class="col-span-1 text-center">Stake</span>
                <span class="col-span-2 text-right pr-2">Status / PnL</span>
              </div>
              
              <div class="flex flex-col overflow-y-auto custom-scrollbar flex-1 max-h-[400px]">
                <div v-if="ledgerOperacoes.length === 0" class="text-center text-[10px] text-gray-500 py-10 font-mono uppercase tracking-widest bg-black/10 rounded flex-1 flex items-center justify-center mt-2">
                  Aguardando Operações na Base de Dados...
                </div>
                
                <div v-for="(op, i) in ledgerOperacoes" :key="'op'+i" class="grid grid-cols-12 items-center bg-black/10 even:bg-white/[0.01] hover:bg-white/5 border-b border-white/5 p-3 transition-colors group cursor-default">
                  
                  <div class="col-span-2 flex flex-col pl-1">
                    <span class="text-[10px] font-mono text-gray-400 group-hover:text-white transition-colors">{{ op.ticker || `BET-${i}X` }}</span>
                    <span class="text-[8px] text-gray-600 font-mono">{{ op.hora }}</span>
                  </div>

                  <div class="col-span-4 flex flex-col pr-2 border-l border-white/5 pl-3">
                    <span class="text-xs font-bold text-white truncate">{{ op.jogo }}</span>
                    <span class="text-[9px] text-[#10B981] uppercase tracking-wider mt-0.5 truncate font-bold">{{ op.mercado }}</span>
                  </div>
                  
                  <div class="col-span-1 flex flex-col items-center">
                    <span class="text-xs font-mono text-white">{{ parseFloat(op.odd).toFixed(2) }}</span>
                  </div>

                  <div class="col-span-2 flex flex-col items-center">
                    <span class="text-[10px] font-mono font-bold px-1.5 rounded border" :class="op.clv > 0 ? 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/30' : 'bg-red-500/10 text-red-500 border-red-500/30'">{{ op.clv > 0 ? '+' : ''}}{{ op.clv ? (op.clv * 100).toFixed(1) : '0.0' }}%</span>
                  </div>
                  
                  <div class="col-span-1 flex flex-col items-center">
                    <span class="text-xs font-mono text-gray-300 bg-black px-1.5 py-0.5 rounded border border-gray-800">{{ formatCurrency(op.stake) }}</span>
                  </div>
                  
                  <div class="col-span-2 flex justify-end items-center gap-3 pr-2">
                    <div v-if="op.status === 'WON'" class="flex flex-col items-end">
                       <span class="text-sm font-mono font-bold text-[#10B981] drop-shadow-[0_0_5px_rgba(16,185,129,0.3)]">+{{ formatCurrency(op.pnl) }}</span>
                       <span class="text-[8px] bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/30 px-1 rounded uppercase font-bold tracking-widest">WON</span>
                    </div>
                    <div v-else-if="op.status === 'LOST'" class="flex flex-col items-end">
                       <span class="text-sm font-mono font-bold text-red-500">{{ formatCurrency(op.pnl) }}</span>
                       <span class="text-[8px] bg-red-500/10 text-red-500 border border-red-500/30 px-1 rounded uppercase font-bold tracking-widest">LOST</span>
                    </div>
                    <div v-else class="flex flex-col items-end">
                       <span class="text-sm font-mono font-bold text-yellow-500">LIVE</span>
                       <span class="text-[8px] bg-yellow-500/10 text-yellow-500 border border-yellow-500/30 px-1 rounded uppercase font-bold tracking-widest animate-pulse">PENDING</span>
                    </div>
                  </div>

                </div>
              </div>
            </div>
          </WidgetCard>

        </div>
      </template>
    </draggable>

    <Teleport to="body">
      <transition name="fade">
        <div v-if="showAporteModal" class="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" @click.self="showAporteModal = false">
          <div class="bg-[#121927] border border-white/10 w-full max-w-md rounded-2xl shadow-[0_30px_60px_rgba(0,0,0,0.9)] overflow-hidden scale-up-center">
            
            <div class="p-5 border-b border-white/10 flex justify-between items-center bg-black/20">
              <h3 class="font-bold text-white uppercase tracking-widest text-sm flex items-center gap-2"><DollarSign size="16" class="text-[#10B981]"/> Injeção de Capital</h3>
              <button @click="showAporteModal = false" class="text-gray-500 hover:text-white transition-colors"><X size="18"/></button>
            </div>

            <div class="p-6">
              <p class="text-xs text-gray-400 mb-6 leading-relaxed">Insira o valor em BRL para integralizar no fundo <span class="text-white font-bold">REAL (AUM)</span>. Este valor recalibrará imediatamente as stakes de Kelly Criterion.</p>
              
              <div class="relative mb-6">
                <span class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 font-mono text-lg">R$</span>
                <input type="number" v-model.number="valorAporte" class="w-full bg-black/50 border border-white/10 rounded-xl py-4 pl-12 pr-4 text-2xl font-mono text-white focus:outline-none focus:border-[#10B981] focus:ring-1 focus:ring-[#10B981]/50 transition-all placeholder-gray-700" placeholder="0.00" min="1" step="100" />
              </div>

              <div class="grid grid-cols-3 gap-2 mb-8">
                <button @click="valorAporte = 1000" class="bg-white/5 hover:bg-white/10 border border-white/10 py-2 rounded-lg text-xs font-mono text-gray-300 transition-colors">+1K</button>
                <button @click="valorAporte = 5000" class="bg-white/5 hover:bg-white/10 border border-white/10 py-2 rounded-lg text-xs font-mono text-gray-300 transition-colors">+5K</button>
                <button @click="valorAporte = 10000" class="bg-white/5 hover:bg-white/10 border border-white/10 py-2 rounded-lg text-xs font-mono text-gray-300 transition-colors">+10K</button>
              </div>

              <div class="flex gap-3">
                <button @click="showAporteModal = false" class="flex-1 py-3 bg-black border border-white/10 text-gray-400 hover:text-white font-bold uppercase tracking-widest text-xs rounded-xl transition-colors">Cancelar</button>
                <button @click="realizarAporte" :disabled="!valorAporte || valorAporte <= 0 || isDepositing" class="flex-1 py-3 bg-[#10B981] text-black hover:bg-white font-bold uppercase tracking-widest text-xs rounded-xl shadow-[0_0_20px_rgba(16,185,129,0.3)] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2">
                  <div v-if="isDepositing" class="w-4 h-4 border-2 border-black/20 border-t-black rounded-full animate-spin"></div>
                  {{ isDepositing ? 'Processando...' : 'Confirmar Aporte' }}
                </button>
              </div>
            </div>

          </div>
        </div>
      </transition>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue';
import draggable from 'vuedraggable';
import { 
  Wallet, TrendingUp, TrendingDown, Crosshair, Target, Search, Plus,
  ShieldAlert, AlertTriangle, LayoutList, GripHorizontal, Activity, LineChart, PieChart, AlertOctagon, DollarSign, X, Check, Clock
} from 'lucide-vue-next';
import WidgetCard from './WidgetCard.vue';
import axios from 'axios';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:3000/api/v1').replace(/\/$/, '');
const globalState = inject('globalState');

const layoutBanca = ref([
  { id: 'equity', span: 'col-span-1 xl:col-span-8' },
  { id: 'risco', span: 'col-span-1 xl:col-span-4' },
  { id: 'atribuicao', span: 'col-span-1 xl:col-span-6' },
  { id: 'alocacao', span: 'col-span-1 xl:col-span-6' },
  { id: 'ledger', span: 'col-span-1 xl:col-span-12' }
]);

// ESTADOS DO MODAL E LOADINGS
const isLoading = ref(true);
const showAporteModal = ref(false);
const valorAporte = ref(null);
const isDepositing = ref(false);

// ESTADOS DOS WIDGETS
const statsBanca = ref({ exposicao: "R$ 0,00", exposicaoPct: 0, yield: "0.00", aum: "R$ 0,00" });
const statsPerformance = ref({ zScore: "2.1", turnover: "R$ 0,00", roi: "0.0%", clvRate: "0.0%" });
const statsRisco = ref({ drawdownAtual: "0.0%", drawdownMax: "0.0%", riscoRuinaPct: "0.0%", riscoRuinaGauge: 5, sharpe: "0.00", badRun: "-" });
const statsAlocacao = ref({ exposicaoPct: 0, exposicaoValor: "R$ 0,00", kellyMult: "0.0", unidade: "R$ 0,00", maxBet: "0u" });

const edgeMercado = ref([]);
const ledgerOperacoes = ref([]);

const formatCurrency = (val) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val || 0);

// ==========================================
// INTEGRAÇÃO BLINDADA COM O BACKEND
// ==========================================
const fetchGestaoData = async () => {
  try {
    isLoading.value = true;
    const token = localStorage.getItem('betgenius_token');
    const opts = { headers: { Authorization: `Bearer ${token}` } };
    const modoAtual = globalState?.uiMode || 'REAL'; 
    
    const response = await axios.get(`${API_BASE_URL}/fund/dashboard?mode=${modoAtual}`, opts);
    
    if (response.data) {
      const data = response.data;
      
      // O endpoint Python mapeia os dados nos dicts corretos
      if(data.statsBanca) statsBanca.value = data.statsBanca;
      if(data.statsPerformance) statsPerformance.value = data.statsPerformance;
      if(data.statsRisco) statsRisco.value = data.statsRisco;
      if(data.statsAlocacao) statsAlocacao.value = data.statsAlocacao;
      
      edgeMercado.value = data.edgeMercado || [];
      ledgerOperacoes.value = data.ledgerOperacoes || [];
    }
  } catch (error) {
    console.error("❌ Falha ao buscar dados da Tesouraria:", error);
  } finally {
    isLoading.value = false;
  }
};

// ==========================================
// AÇÃO: INJEÇÃO DE CAPITAL (DEPOSIT)
// ==========================================
const realizarAporte = async () => {
  if (!valorAporte.value || valorAporte.value <= 0) return;
  isDepositing.value = true;
  
  try {
    const token = localStorage.getItem('betgenius_token');
    const opts = { headers: { Authorization: `Bearer ${token}` } };
    
    // Dispara para a rota POST /deposit no Python
    await axios.post(`${API_BASE_URL}/fund/deposit`, { amount: valorAporte.value }, opts);
    
    showAporteModal.value = false;
    valorAporte.value = null;
    
    // Atualiza a tela para refletir o novo AUM!
    await fetchGestaoData(); 
    
  } catch (error) {
    alert("Falha ao registrar aporte. Certifique-se que o código Python do /deposit foi adicionado ao main.py");
    console.error(error);
  } finally {
    isDepositing.value = false;
  }
};

onMounted(() => {
  fetchGestaoData();
});
</script>

<style scoped>
.glass-card { background: rgba(18, 25, 39, 0.75); border-radius: 16px; backdrop-filter: blur(24px); }
.ghost-widget { opacity: 0.3 !important; border: 2px dashed #10B981 !important; transform: scale(0.98); }
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(16, 185, 129, 0.2); border-radius: 10px; }
.scale-up-center { animation: scaleUp 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes scaleUp { from { opacity: 0; transform: scale(0.95) translateY(10px); } to { opacity: 1; transform: scale(1) translateY(0); } }
</style>