<template>
  <div class="flex flex-col gap-6 w-full min-h-full relative fade-in-up pb-10">
    
    <div class="glass-card shrink-0 p-6 md:p-8 relative overflow-hidden flex flex-col xl:flex-row justify-between items-center border-t-4 shadow-[0_20px_50px_rgba(0,0,0,0.5)] border-bet-primary">
      <div class="absolute -right-40 -top-40 w-96 h-96 rounded-full blur-[100px] pointer-events-none opacity-10 bg-bet-primary"></div>
      
      <div class="flex items-center gap-5 w-full xl:w-1/4 z-10 mb-6 xl:mb-0">
        <div class="w-16 h-16 rounded-xl bg-black/60 border border-bet-primary/30 flex items-center justify-center shadow-[0_0_30px_rgba(140,199,255,0.15)] relative overflow-hidden">
          <div class="absolute inset-0 bg-gradient-to-br from-bet-primary/20 to-transparent"></div>
          <Wallet :size="30" class="text-bet-primary relative z-10" />
        </div>
        <div class="text-left flex flex-col">
          <h2 class="text-2xl font-mono text-white tracking-widest drop-shadow-md">ALPHA FUND</h2>
          <span class="text-[10px] text-bet-primary uppercase tracking-widest font-bold flex items-center gap-1.5 mt-0.5">
            <div class="w-1.5 h-1.5 bg-bet-primary rounded-full animate-pulse"></div> Gestão Quantitativa Ativa
          </span>
        </div>
      </div>

      <div class="flex flex-wrap md:flex-nowrap justify-between xl:justify-end gap-6 md:gap-12 w-full xl:w-3/4 z-10">
        
        <div class="flex flex-col items-start xl:items-end w-[45%] md:w-auto">
          <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 flex items-center gap-1"><Activity size="12"/> Exposição Ativa</span>
          <span class="text-lg font-mono text-white">R$ 42.500 <span class="text-[10px] text-gray-500 bg-white/5 px-1.5 py-0.5 rounded ml-1">2.4%</span></span>
        </div>
        
        <div class="hidden md:block w-px bg-gradient-to-b from-transparent via-white/10 to-transparent h-12"></div>
        
        <div class="flex flex-col items-start xl:items-end w-[45%] md:w-auto">
          <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 flex items-center gap-1"><Target size="12"/> Yield (All-Time)</span>
          <span class="text-xl font-mono text-[#10B981] font-bold">+8.42% <span class="text-[10px] text-[#10B981] bg-[#10B981]/10 px-1.5 py-0.5 rounded ml-1 border border-[#10B981]/20">Alpha</span></span>
        </div>

        <div class="hidden md:block w-px bg-gradient-to-b from-transparent via-white/10 to-transparent h-12"></div>

        <div class="flex flex-col items-start xl:items-end w-full md:w-auto mt-4 md:mt-0 bg-black/30 p-3 rounded-lg border border-white/5 shadow-inner">
          <span class="text-[10px] text-bet-primary uppercase tracking-widest font-bold mb-1">AUM (Assets Under Mgt)</span>
          <span class="text-3xl font-mono text-white font-bold drop-shadow-[0_0_15px_rgba(255,255,255,0.2)] tracking-tight">R$ 1.745.250</span>
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
          
          <div class="drag-handle absolute -top-3 left-1/2 -translate-x-1/2 z-[80] opacity-0 group-hover/widget:opacity-100 cursor-move p-1 px-5 bg-black text-bet-primary rounded-b-xl border border-white/10 shadow-[0_5px_15px_rgba(0,0,0,0.8)] transition-all hover:bg-bet-primary hover:text-black">
            <GripHorizontal size="16" />
          </div>

          <WidgetCard v-if="element.id === 'equity'" titulo="Performance vs Expected Value (CLV)" class="h-full">
            <template #icone><LineChart :size="16" color="var(--bet-primary)" /></template>
            <template #acoes>
              <div class="flex items-center gap-4">
                <div class="flex items-center gap-1.5 text-[9px] font-mono text-gray-400 uppercase tracking-widest"><div class="w-2 h-2 rounded-full bg-bet-primary"></div> PnL Real</div>
                <div class="flex items-center gap-1.5 text-[9px] font-mono text-gray-400 uppercase tracking-widest"><div class="w-2 h-2 rounded-full bg-yellow-500 border border-yellow-500"></div> Expected (EV)</div>
                <div class="w-px h-3 bg-white/10"></div>
                <select class="bg-black/40 text-[10px] text-white border border-white/10 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-bet-primary">
                  <option>YTD (Year to Date)</option>
                  <option>Últimos 6 Meses</option>
                  <option>All Time</option>
                </select>
              </div>
            </template>
            
            <div class="flex flex-col gap-4 mt-4 h-full">
              <div class="grid grid-cols-4 gap-3">
                <div class="bg-black/20 border border-white/5 p-3 rounded-xl flex flex-col">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">Z-Score (Significância)</span>
                  <span class="text-xl font-mono text-[#10B981] font-bold mt-1">3.45</span>
                  <span class="text-[8px] text-gray-600 mt-1 uppercase">Prob. Sorte: &lt; 0.1%</span>
                </div>
                <div class="bg-black/20 border border-white/5 p-3 rounded-xl flex flex-col">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">Turnover (Volume)</span>
                  <span class="text-xl font-mono text-white font-bold mt-1">R$ 8.2M</span>
                  <span class="text-[8px] text-gray-600 mt-1 uppercase">Total Injetado</span>
                </div>
                <div class="bg-black/20 border border-white/5 p-3 rounded-xl flex flex-col">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">ROI Ponderado</span>
                  <span class="text-xl font-mono text-bet-primary font-bold mt-1">+21.4%</span>
                  <span class="text-[8px] text-gray-600 mt-1 uppercase">Crescimento Fundo</span>
                </div>
                <div class="bg-black/20 border border-white/5 p-3 rounded-xl flex flex-col">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">CLV Beating Rate</span>
                  <span class="text-xl font-mono text-yellow-500 font-bold mt-1">82.1%</span>
                  <span class="text-[8px] text-gray-600 mt-1 uppercase">Linhas batidas no Fech.</span>
                </div>
              </div>

              <div class="flex-1 relative w-full min-h-[220px] bg-[#0b0f19] rounded-xl border border-white/5 overflow-hidden flex items-end pt-4 pr-4 shadow-inner">
                <div class="absolute left-2 top-4 text-[9px] font-mono text-gray-600">+R$ 400k</div>
                <div class="absolute left-2 top-1/2 -translate-y-1/2 text-[9px] font-mono text-gray-600">+R$ 200k</div>
                <div class="absolute left-2 bottom-6 text-[9px] font-mono text-gray-600">R$ 0</div>
                
                <div class="absolute inset-0 flex flex-col justify-between py-6 px-12 pointer-events-none opacity-20">
                  <div class="w-full h-px bg-gray-600"></div><div class="w-full h-px bg-gray-600"></div><div class="w-full h-px bg-gray-600"></div>
                </div>

                <svg viewBox="0 0 100 40" class="w-full h-full overflow-visible preserve-3d px-12" preserveAspectRatio="none">
                  <polyline points="0,35 10,33 20,30 30,26 40,24 50,20 60,18 70,14 80,11 90,8 100,5" fill="none" stroke="#EAB308" stroke-width="1" stroke-dasharray="2,2" vector-effect="non-scaling-stroke" />
                  
                  <defs>
                    <linearGradient id="equity-grad-s" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stop-color="var(--bet-primary)" stop-opacity="0.2" />
                      <stop offset="100%" stop-color="var(--bet-primary)" stop-opacity="0" />
                    </linearGradient>
                  </defs>
                  <polygon points="0,40 0,35 10,34 20,28 30,29 40,22 50,25 60,16 70,17 80,10 90,12 100,4 100,40" fill="url(#equity-grad-s)" />
                  <polyline points="0,35 10,34 20,28 30,29 40,22 50,25 60,16 70,17 80,10 90,12 100,4" fill="none" stroke="var(--bet-primary)" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linecap="round" stroke-linejoin="round" />
                  
                  <circle cx="100" cy="4" r="1.5" fill="#fff" stroke="var(--bet-primary)" stroke-width="1" class="animate-pulse" />
                </svg>
                
                <div class="absolute bottom-2 right-4 bg-black/60 border border-white/10 px-2 py-1 rounded text-[8px] font-mono text-gray-400">
                  Variância Atual: <span class="text-red-400 font-bold">-1.2% (Running Cold)</span>
                </div>
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
                    <span class="text-2xl font-mono text-red-400 font-bold drop-shadow-md">-4.2%</span>
                  </div>
                  <div class="flex flex-col items-end">
                    <span class="text-[9px] text-gray-500 uppercase tracking-widest">Max Histórico</span>
                    <span class="text-sm font-mono text-white">-14.8%</span>
                  </div>
                </div>
                
                <div class="w-full flex flex-col gap-1">
                  <div class="flex justify-between text-[8px] uppercase tracking-widest font-mono text-gray-500 mb-0.5">
                    <span>Seguro</span><span>Perigo</span><span>Ruína</span>
                  </div>
                  <div class="w-full h-2 bg-gray-800 rounded-full overflow-hidden flex">
                    <div class="h-full w-[15%] bg-red-500 shadow-[0_0_10px_#EF4444]"></div>
                  </div>
                  <span class="text-[9px] text-gray-400 mt-1">Risco de Ruína (Monte Carlo): <strong class="text-white">0.02%</strong></span>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-3 mt-auto">
                <div class="bg-black/30 border border-white/5 p-3 rounded-lg flex flex-col gap-1 shadow-sm hover:border-white/20 transition-colors">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">Sharpe Ratio</span>
                  <span class="text-xl font-mono text-white font-bold">1.84</span>
                  <span class="text-[8px] text-green-400 uppercase tracking-widest mt-0.5">Excelente</span>
                </div>
                <div class="bg-black/30 border border-white/5 p-3 rounded-lg flex flex-col gap-1 shadow-sm hover:border-white/20 transition-colors">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">Pior Bad Run</span>
                  <span class="text-xl font-mono text-red-500 font-bold">11 Ls</span>
                  <span class="text-[8px] text-gray-600 uppercase tracking-widest mt-0.5">Out 2024</span>
                </div>
              </div>

            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'atribuicao'" titulo="Edge Attribution (Raio-X de Lucratividade)" class="h-full">
            <template #icone><PieChart :size="16" color="#a855f7" /></template>
            <template #acoes>
              <select v-model="viewAtribuicao" class="bg-black/40 text-[10px] text-white border border-white/10 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-[#a855f7]">
                <option value="mercado">Por Mercado</option>
                <option value="odds">Por Range de Odds</option>
              </select>
            </template>
            
            <div class="flex flex-col h-full mt-4">
              
              <div v-if="viewAtribuicao === 'mercado'" class="flex flex-col gap-3 flex-1">
                <div class="grid grid-cols-12 text-[9px] uppercase tracking-widest font-bold text-gray-500 border-b border-white/10 pb-2">
                  <span class="col-span-4">Mercado Foco</span>
                  <span class="col-span-3 text-center">Volume (R$)</span>
                  <span class="col-span-2 text-center">Yield</span>
                  <span class="col-span-3 text-right">Weight</span>
                </div>
                <div v-for="(edge, i) in edgeMercado" :key="'em'+i" class="grid grid-cols-12 items-center py-2 border-b border-white/5 group">
                  <span class="col-span-4 text-xs font-bold text-white group-hover:text-[#a855f7] transition-colors truncate">{{ edge.nome }}</span>
                  <span class="col-span-3 text-center text-xs font-mono text-gray-400">{{ edge.volume }}k</span>
                  <div class="col-span-2 flex justify-center">
                    <span class="text-xs font-mono font-bold px-1.5 py-0.5 rounded border" :class="edge.yield > 0 ? 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/30' : 'bg-red-500/10 text-red-500 border-red-500/30'">{{ edge.yield > 0 ? '+' : ''}}{{ edge.yield }}%</span>
                  </div>
                  <div class="col-span-3 flex items-center justify-end gap-2">
                    <span class="text-[9px] text-gray-500 font-mono">{{ edge.weight }}%</span>
                    <div class="w-12 h-1.5 bg-gray-800 rounded-full overflow-hidden"><div class="h-full bg-[#a855f7]" :style="`width: ${edge.weight}%`"></div></div>
                  </div>
                </div>
              </div>

              <div v-else class="flex flex-col gap-3 flex-1">
                <div class="grid grid-cols-12 text-[9px] uppercase tracking-widest font-bold text-gray-500 border-b border-white/10 pb-2">
                  <span class="col-span-4">Range de Odds</span>
                  <span class="col-span-3 text-center">Volume (R$)</span>
                  <span class="col-span-2 text-center">Yield</span>
                  <span class="col-span-3 text-right">Performance</span>
                </div>
                <div v-for="(edge, i) in edgeOdds" :key="'eo'+i" class="grid grid-cols-12 items-center py-2 border-b border-white/5 group">
                  <span class="col-span-4 text-xs font-mono font-bold text-white group-hover:text-bet-primary transition-colors">@{{ edge.range }}</span>
                  <span class="col-span-3 text-center text-xs font-mono text-gray-400">{{ edge.volume }}k</span>
                  <div class="col-span-2 flex justify-center">
                    <span class="text-xs font-mono font-bold px-1.5 py-0.5 rounded border" :class="edge.yield > 0 ? 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/30' : 'bg-red-500/10 text-red-500 border-red-500/30'">{{ edge.yield > 0 ? '+' : ''}}{{ edge.yield }}%</span>
                  </div>
                  <div class="col-span-3 flex items-center justify-end">
                    <div class="w-16 h-2 bg-gray-800 rounded-sm overflow-hidden flex" :class="edge.yield > 0 ? 'justify-start' : 'justify-end'">
                      <div class="h-full" :class="edge.yield > 0 ? 'bg-[#10B981]' : 'bg-red-500'" :style="`width: ${Math.abs(edge.yield) * 4}%`"></div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="mt-auto pt-2 flex items-center gap-2">
                <AlertOctagon size="12" class="text-yellow-500" />
                <span class="text-[9px] text-gray-400 uppercase tracking-widest font-mono">Insight: O sistema encontrou vazamento de lucro no mercado de <strong class="text-white">Ambas Marcam</strong>.</span>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'alocacao'" titulo="Capital Allocation & Sizing" class="h-full">
            <template #icone><PieChart :size="16" color="var(--bet-secondary)" /></template>
            
            <div class="flex flex-col gap-4 mt-2 h-full">
              <div class="flex gap-4 items-center bg-black/20 p-4 rounded-xl border border-white/5 shadow-inner">
                <div class="w-16 h-16 rounded-full border-[6px] border-gray-800 border-t-bet-primary border-r-bet-primary flex items-center justify-center transform -rotate-45 shadow-lg">
                  <span class="text-[10px] font-mono font-bold text-white transform rotate-45">18%</span>
                </div>
                <div class="flex flex-col">
                  <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1">Exposição Atual da Banca</span>
                  <span class="text-sm font-mono text-gray-300">R$ 314.145 alocados no mercado agora.</span>
                  <span class="text-[9px] text-bet-primary uppercase tracking-widest mt-1 border border-bet-primary/20 bg-bet-primary/10 w-max px-2 py-0.5 rounded">Operação Saudável</span>
                </div>
              </div>

              <div class="flex flex-col gap-2 mt-auto">
                <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold border-b border-white/5 pb-1">Diretrizes do Algoritmo (Kelly)</span>
                <div class="flex justify-between items-center bg-black/30 p-2.5 rounded-lg border border-white/5">
                  <span class="text-xs font-bold text-white">Multiplicador Kelly Fracionado</span>
                  <span class="text-sm font-mono text-bet-secondary font-bold bg-bet-secondary/10 px-2 py-0.5 border border-bet-secondary/30 rounded">0.25 (1/4)</span>
                </div>
                <div class="flex justify-between items-center bg-black/30 p-2.5 rounded-lg border border-white/5">
                  <span class="text-xs font-bold text-white">Unidade Padrão (1u) Recomendada</span>
                  <span class="text-sm font-mono text-white font-bold border border-gray-700 bg-black px-2 py-0.5 rounded">R$ 17.452</span>
                </div>
                <div class="flex justify-between items-center bg-black/30 p-2.5 rounded-lg border border-white/5">
                  <span class="text-xs font-bold text-white">Stake Máxima Recomendada (Max Bet)</span>
                  <span class="text-sm font-mono text-yellow-500 font-bold border border-yellow-500/20 bg-yellow-500/10 px-2 py-0.5 rounded">3.0u</span>
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'ledger'" titulo="Ledger de Operações Executadas" class="h-full">
            <template #icone><LayoutList :size="16" color="var(--text-muted)" /></template>
            <template #acoes>
              <div class="flex items-center gap-2 bg-black/40 border border-white/10 rounded px-2 py-1">
                <Search size="10" class="text-gray-400" />
                <input type="text" placeholder="Filtrar Ticker..." class="bg-transparent text-[10px] text-white outline-none w-24 font-mono">
              </div>
            </template>
            
            <div class="flex flex-col h-full mt-2">
              <div class="grid grid-cols-12 px-4 pb-2 border-b border-white/10 text-[9px] uppercase font-bold text-gray-500 tracking-widest bg-black/30 rounded-t-lg pt-3">
                <span class="col-span-2">Ticker / Hora</span>
                <span class="col-span-4">Ativo (Jogo / Mercado)</span>
                <span class="col-span-1 text-center">Odd</span>
                <span class="col-span-2 text-center">CLV Edge</span>
                <span class="col-span-1 text-center">Stake</span>
                <span class="col-span-2 text-right pr-2">PnL Final</span>
              </div>
              
              <div class="flex flex-col overflow-y-auto custom-scrollbar flex-1 max-h-[300px]">
                <div v-for="(op, i) in ledgerOperacoes" :key="'op'+i" class="grid grid-cols-12 items-center bg-black/10 even:bg-white/[0.01] hover:bg-white/5 border-b border-white/5 p-3 transition-colors group cursor-default">
                  
                  <div class="col-span-2 flex flex-col pl-1">
                    <span class="text-[10px] font-mono text-gray-400 group-hover:text-white transition-colors">{{ op.ticker }}</span>
                    <span class="text-[8px] text-gray-600 font-mono">{{ op.hora }}</span>
                  </div>

                  <div class="col-span-4 flex flex-col pr-2 border-l border-white/5 pl-3">
                    <span class="text-xs font-bold text-white truncate">{{ op.jogo }}</span>
                    <span class="text-[9px] text-bet-primary uppercase tracking-wider mt-0.5 truncate font-bold">{{ op.mercado }}</span>
                  </div>
                  
                  <div class="col-span-1 flex flex-col items-center">
                    <span class="text-xs font-mono text-white">{{ op.odd }}</span>
                  </div>

                  <div class="col-span-2 flex flex-col items-center">
                    <span class="text-[10px] font-mono font-bold px-1.5 rounded border" :class="op.clv > 0 ? 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/30' : 'bg-red-500/10 text-red-500 border-red-500/30'">{{ op.clv > 0 ? '+' : ''}}{{ op.clv }}%</span>
                    <span class="text-[8px] text-gray-500 font-mono uppercase mt-0.5">Fair: {{ op.fair }}</span>
                  </div>
                  
                  <div class="col-span-1 flex flex-col items-center">
                    <span class="text-xs font-mono text-gray-300 bg-black px-1.5 py-0.5 rounded border border-gray-800">{{ op.stake }}u</span>
                  </div>
                  
                  <div class="col-span-2 flex justify-end items-center gap-3 pr-2">
                    <span class="text-sm font-mono font-bold" :class="op.status === 'W' ? 'text-[#10B981] drop-shadow-[0_0_5px_rgba(16,185,129,0.3)]' : (op.status === 'L' ? 'text-red-500' : 'text-gray-400')">{{ op.pnl }}</span>
                    <div class="w-2 h-2 rounded-full shadow-[0_0_5px_currentColor]" :class="op.status === 'W' ? 'bg-[#10B981] text-[#10B981]' : (op.status === 'L' ? 'bg-red-500 text-red-500' : 'bg-gray-400 text-gray-400')"></div>
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
  Wallet, TrendingUp, TrendingDown, Crosshair, Target, Search,
  ShieldAlert, AlertTriangle, LayoutList, GripHorizontal, Activity, LineChart, PieChart, AlertOctagon
} from 'lucide-vue-next';
import WidgetCard from './WidgetCard.vue';

const layoutBanca = ref([
  { id: 'equity', span: 'col-span-1 xl:col-span-8' },
  { id: 'risco', span: 'col-span-1 xl:col-span-4' },
  { id: 'atribuicao', span: 'col-span-1 xl:col-span-6' },
  { id: 'alocacao', span: 'col-span-1 xl:col-span-6' },
  { id: 'ledger', span: 'col-span-1 xl:col-span-12' }
]);

const viewAtribuicao = ref('mercado');

const edgeMercado = [
  { nome: "Match Odds (1x2)", volume: "2,450", yield: 11.2, weight: 85 },
  { nome: "Handicap Asiático", volume: "3,120", yield: 8.4, weight: 65 },
  { nome: "Over 2.5 Gols", volume: "1,800", yield: 4.1, weight: 30 },
  { nome: "Ambas Marcam (BTTS)", volume: "850", yield: -4.2, weight: 15 },
];

const edgeOdds = [
  { range: "1.50 - 1.80", volume: "1,400", yield: 2.1 },
  { range: "1.81 - 2.20", volume: "3,800", yield: 14.5 },
  { range: "2.21 - 3.00", volume: "2,100", yield: 8.2 },
  { range: "3.01+", volume: "920", yield: -6.8 },
];

const ledgerOperacoes = ref([
  { ticker: "ARS-LIV", hora: "Hoje, 16:00", jogo: "Arsenal x Liverpool", mercado: "Arsenal AH -0.5", odd: "1.95", stake: "2.0", pnl: "+1.90u", status: "W", clv: 4.2, fair: "1.87" },
  { ticker: "RMA-SEV", hora: "Ontem, 20:30", jogo: "Real Madrid x Sevilla", mercado: "Real Madrid Vence (ML)", odd: "1.80", stake: "1.5", pnl: "+1.20u", status: "W", clv: 2.1, fair: "1.76" },
  { ticker: "JUV-MIL", hora: "Ontem, 16:45", jogo: "Juventus x Milan", mercado: "BTTS - Sim", odd: "2.10", stake: "1.0", pnl: "-1.00u", status: "L", clv: -1.4, fair: "2.13" },
  { ticker: "BAY-DOR", hora: "14 Fev, 15:30", jogo: "Bayern x Dortmund", mercado: "Over 3.5 Gols", odd: "2.25", stake: "1.0", pnl: "+1.25u", status: "W", clv: 8.5, fair: "2.05" },
  { ticker: "PSG-MAR", hora: "12 Fev, 21:00", jogo: "PSG x Marseille", mercado: "PSG Vence HT", odd: "1.75", stake: "2.0", pnl: "-2.00u", status: "L", clv: 0.8, fair: "1.73" },
  { ticker: "FLA-PAL", hora: "10 Fev, 16:00", jogo: "Flamengo x Palmeiras", mercado: "Under 2.5 Gols", odd: "1.65", stake: "3.0", pnl: "+1.95u", status: "W", clv: 3.2, fair: "1.60" },
  { ticker: "MCI-CHE", hora: "08 Fev, 18:30", jogo: "Man City x Chelsea", mercado: "Man City AH -1.5", odd: "2.05", stake: "1.5", pnl: "+1.57u", status: "W", clv: 6.4, fair: "1.92" },
]);
</script>

<style scoped>
.glass-card { background: rgba(18, 25, 39, 0.75); border-radius: 16px; backdrop-filter: blur(24px); }
.ghost-widget { opacity: 0.3 !important; border: 2px dashed var(--bet-primary) !important; transform: scale(0.98); }
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(140, 199, 255, 0.2); border-radius: 10px; }
</style>