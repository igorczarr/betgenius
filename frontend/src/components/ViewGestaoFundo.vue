<template>
  <div class="flex flex-col gap-6 w-full h-full relative fade-in-up pb-10">
    
    <div class="glass-card shrink-0 p-6 md:p-8 relative overflow-hidden flex flex-col xl:flex-row justify-between items-center border-t-4 shadow-[0_20px_50px_rgba(0,0,0,0.5)] border-[#10B981]">
      <div class="absolute -right-40 -top-40 w-96 h-96 rounded-full blur-[100px] pointer-events-none opacity-10 bg-[#10B981]"></div>
      
      <div class="flex items-center gap-5 w-full xl:w-1/4 z-10 mb-6 xl:mb-0 group cursor-default">
        <div class="w-16 h-16 rounded-2xl bg-[#0b0f19] border border-[#10B981]/30 flex items-center justify-center shadow-[0_0_30px_rgba(16,185,129,0.15)] relative overflow-hidden transition-transform duration-500 group-hover:scale-105">
          <div class="absolute inset-0 bg-gradient-to-br from-[#10B981]/20 to-transparent"></div>
          <Wallet :size="28" class="text-[#10B981] relative z-10" />
        </div>
        <div class="text-left flex flex-col">
          <h2 class="text-2xl font-mono text-white tracking-[0.2em] drop-shadow-md font-bold">ALPHA FUND</h2>
          <span class="text-[10px] text-[#10B981] uppercase tracking-widest font-bold flex items-center gap-1.5 mt-1">
            <div class="w-1.5 h-1.5 bg-[#10B981] rounded-full shadow-[0_0_8px_#10B981]" :class="{'animate-pulse': !isLoading}"></div> 
            {{ isLoading ? 'Verificando Liquidez...' : 'AUM Real Management' }}
          </span>
        </div>
      </div>

      <div class="flex flex-wrap md:flex-nowrap justify-between xl:justify-end items-center gap-6 md:gap-12 w-full xl:w-3/4 z-10">
        
        <div class="flex flex-col items-start xl:items-end w-[45%] md:w-auto">
          <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 flex items-center gap-1"><Activity size="12"/> Exposição Ativa</span>
          <span class="text-lg font-mono text-white font-bold tracking-wider flex items-center gap-2">
            {{ statsBanca.exposicao }} 
            <span class="text-[9px] text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20 uppercase tracking-widest">{{ statsBanca.exposicaoPct }}%</span>
          </span>
        </div>
        
        <div class="hidden md:block w-px bg-gradient-to-b from-transparent via-white/10 to-transparent h-12"></div>
        
        <div class="flex flex-col items-start xl:items-end w-[45%] md:w-auto">
          <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 flex items-center gap-1"><Target size="12"/> Yield (Global)</span>
          <span class="text-xl font-mono font-bold tracking-wider" :class="parseFloat(statsBanca.yield) >= 0 ? 'text-[#10B981] drop-shadow-[0_0_10px_rgba(16,185,129,0.3)]' : 'text-red-500'">
            {{ parseFloat(statsBanca.yield) > 0 ? '+' : '' }}{{ statsBanca.yield }}% 
          </span>
        </div>

        <div class="hidden md:block w-px bg-gradient-to-b from-transparent via-white/10 to-transparent h-12"></div>

        <div class="flex items-center justify-between xl:justify-end gap-4 w-full md:w-auto mt-4 md:mt-0 bg-[#10B981]/5 p-3 px-5 rounded-xl border border-[#10B981]/20 shadow-[0_0_20px_rgba(16,185,129,0.05)] transition-all">
          <div class="flex flex-col items-start xl:items-end">
            <span class="text-[10px] text-[#10B981] uppercase tracking-widest font-bold mb-1">AUM (Bankroll)</span>
            <span class="text-3xl font-mono text-white font-black drop-shadow-[0_0_10px_rgba(255,255,255,0.2)] tracking-tight">{{ statsBanca.aum }}</span>
          </div>
          <button @click="showAporteModal = true" class="w-12 h-12 bg-[#10B981]/20 hover:bg-[#10B981] border border-[#10B981]/40 rounded-xl flex items-center justify-center text-[#10B981] hover:text-black transition-all duration-300 shadow-[0_0_15px_rgba(16,185,129,0.2)] hover:shadow-[0_0_20px_rgba(16,185,129,0.6)] group ml-4" title="Injetar Capital (Aporte)">
            <Plus :size="24" class="group-hover:rotate-90 transition-transform duration-300" strokeWidth="3" />
          </button>
        </div>

      </div>
    </div>

    <div v-if="isLoading" class="flex flex-col justify-center items-center py-32 gap-4">
      <div class="w-10 h-10 border-4 border-white/10 border-t-[#10B981] rounded-full animate-spin shadow-[0_0_15px_rgba(16,185,129,0.3)]"></div>
      <span class="text-xs font-mono text-gray-500 uppercase tracking-widest animate-pulse">Auditando Livro-Razão Financeiro...</span>
    </div>

    <draggable 
      v-else
      v-model="layoutBanca" 
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

          <WidgetCard v-if="element.id === 'equity'" titulo="Performance vs Expected Value (CLV)" class="h-full shadow-2xl border border-white/5 bg-[#0b0f19]">
            <template #icone><LineChart :size="16" color="#10B981" /></template>
            <template #acoes>
              <select class="bg-black/50 text-[10px] text-white border border-white/10 rounded-lg px-3 py-1.5 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-[#10B981] transition-colors shadow-inner">
                <option>YTD (Year to Date)</option>
                <option>All Time</option>
              </select>
            </template>
            
            <div class="flex flex-col gap-5 mt-4 h-full">
              <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div class="bg-black/30 border border-white/5 p-4 rounded-xl flex flex-col relative overflow-hidden group">
                  <div class="absolute inset-0 bg-gradient-to-t from-[#10B981]/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold z-10">Z-Score (Significância)</span>
                  <span class="text-xl font-mono text-[#10B981] font-black mt-1 z-10 drop-shadow-[0_0_5px_currentColor]">{{ statsPerformance.zScore }}</span>
                </div>
                <div class="bg-black/30 border border-white/5 p-4 rounded-xl flex flex-col relative z-10">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">Turnover (Volume)</span>
                  <span class="text-xl font-mono text-white font-black mt-1">{{ statsPerformance.turnover }}</span>
                </div>
                <div class="bg-black/30 border border-white/5 p-4 rounded-xl flex flex-col relative z-10">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">ROI Ponderado</span>
                  <span class="text-xl font-mono text-[#10B981] font-black mt-1">{{ statsPerformance.roi }}</span>
                </div>
                <div class="bg-black/30 border border-white/5 p-4 rounded-xl flex flex-col relative overflow-hidden group">
                  <div class="absolute inset-0 bg-gradient-to-t from-yellow-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold z-10">CLV Beating Rate</span>
                  <span class="text-xl font-mono text-yellow-500 font-black mt-1 z-10 drop-shadow-[0_0_5px_currentColor]">{{ statsPerformance.clvRate }}</span>
                </div>
              </div>

              <div class="flex-1 relative w-full min-h-[220px] bg-[#121927] rounded-xl border border-white/5 overflow-hidden flex items-end pt-4 shadow-inner">
                <div class="absolute inset-0 flex flex-col justify-between py-6 px-12 pointer-events-none opacity-20">
                  <div class="w-full h-px bg-gray-500"></div><div class="w-full h-px bg-gray-500"></div><div class="w-full h-px bg-gray-500"></div>
                </div>
                <div class="absolute top-4 left-6 pointer-events-none opacity-50 flex items-center gap-2">
                   <div class="w-2 h-2 rounded-full bg-[#10B981]"></div>
                   <span class="text-[9px] font-mono font-bold text-gray-400 uppercase tracking-widest">Equity Curve Real-Time</span>
                </div>
                <svg viewBox="0 0 100 40" class="w-full h-full overflow-visible preserve-3d px-6 sm:px-12" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="equity-grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stop-color="#10B981" stop-opacity="0.3" />
                      <stop offset="100%" stop-color="#10B981" stop-opacity="0" />
                    </linearGradient>
                  </defs>
                  <polygon points="0,40 0,35 10,34 20,28 30,29 40,22 50,25 60,16 70,17 80,10 90,12 100,4 100,40" fill="url(#equity-grad)" class="animate-pulse-slow" />
                  <polyline points="0,35 10,34 20,28 30,29 40,22 50,25 60,16 70,17 80,10 90,12 100,4" fill="none" stroke="#10B981" stroke-width="1.5" vector-effect="non-scaling-stroke" />
                  <circle cx="100" cy="4" r="1.5" fill="#fff" stroke="#10B981" stroke-width="0.5" class="animate-ping shadow-[0_0_10px_#10B981]" />
                </svg>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'risco'" titulo="Risk Management & Ruin" class="h-full shadow-2xl border border-white/5 bg-[#0b0f19]">
            <template #icone><ShieldAlert :size="16" color="#EF4444" /></template>
            <div class="flex flex-col gap-5 mt-4 h-full">
              <div class="bg-gradient-to-br from-red-500/10 to-[#121927] border border-red-500/20 p-5 rounded-xl flex flex-col relative overflow-hidden shadow-inner group">
                <div class="absolute right-0 top-0 w-32 h-32 bg-red-500/5 rounded-full blur-[30px] group-hover:bg-red-500/10 transition-colors"></div>
                <div class="flex justify-between items-start mb-6 relative z-10">
                  <div class="flex flex-col">
                    <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold flex items-center gap-1.5 mb-1"><TrendingDown size="12" class="text-red-500"/> Current Drawdown</span>
                    <span class="text-3xl font-mono text-red-400 font-black drop-shadow-[0_0_10px_rgba(239,68,68,0.3)]">{{ statsRisco.drawdownAtual }}</span>
                  </div>
                </div>
                
                <div class="w-full flex flex-col gap-2 relative z-10">
                  <div class="flex justify-between text-[9px] uppercase tracking-widest font-mono text-gray-500 font-bold">
                    <span>Safe Zone</span><span class="text-yellow-500">Warning</span><span class="text-red-500">Ruin</span>
                  </div>
                  <div class="w-full h-3 bg-black rounded-full overflow-hidden flex border border-white/5 relative">
                    <div class="absolute w-px h-full bg-white/20 left-1/3"></div>
                    <div class="absolute w-px h-full bg-white/20 left-2/3"></div>
                    <div class="h-full bg-gradient-to-r from-[#10B981] via-yellow-500 to-red-500 shadow-[0_0_10px_#EF4444] transition-all duration-[1.5s] ease-out" style="width: 5%"></div>
                  </div>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-4 mt-auto">
                <div class="bg-black/30 border border-white/5 p-4 rounded-xl flex flex-col gap-1 shadow-inner relative overflow-hidden">
                  <div class="absolute -right-5 -bottom-5 opacity-5"><TrendingDown size="40"/></div>
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">Max Drawdown</span>
                  <span class="text-xl font-mono text-white font-black">{{ statsRisco.drawdownMax }}</span>
                </div>
                <div class="bg-black/30 border border-white/5 p-4 rounded-xl flex flex-col gap-1 shadow-inner relative overflow-hidden">
                  <div class="absolute -right-5 -bottom-5 opacity-5"><Activity size="40"/></div>
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">Sharpe Ratio</span>
                  <span class="text-xl font-mono text-yellow-500 font-black drop-shadow-[0_0_8px_rgba(234,179,8,0.3)]">{{ statsRisco.sharpe }}</span>
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'alocacao'" titulo="Capital Allocation & Sizing" class="h-full shadow-2xl border border-white/5 bg-[#0b0f19]">
            <template #icone><Crosshair :size="16" color="#F59E0B" /></template>
            <template #acoes>
               <span class="bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/30 px-3 py-1 rounded-lg text-[9px] font-mono font-bold uppercase tracking-widest flex items-center gap-1.5 shadow-[0_0_10px_rgba(245,158,11,0.2)]">Kelly Tuned</span>
            </template>
            
            <div class="flex flex-col gap-5 mt-4 h-full">
              <div class="flex gap-5 items-center bg-[#121927] p-5 rounded-2xl border border-white/5 shadow-inner">
                <div class="w-20 h-20 relative shrink-0">
                  <svg class="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r="40" fill="transparent" stroke="rgba(255,255,255,0.05)" stroke-width="10" />
                    <circle cx="50" cy="50" r="40" fill="transparent" stroke="#F59E0B" stroke-width="10" stroke-linecap="round" 
                            :stroke-dasharray="251.2" :stroke-dashoffset="251.2 - (251.2 * (statsAlocacao.exposicaoPct / 100))" 
                            class="transition-all duration-1000 ease-out" />
                  </svg>
                  <div class="absolute inset-0 flex items-center justify-center flex-col">
                    <span class="text-[14px] font-mono font-black text-white">{{ statsAlocacao.exposicaoPct.toFixed(1) }}%</span>
                  </div>
                </div>

                <div class="flex flex-col">
                  <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold mb-1">Exposição do Fundo</span>
                  <span class="text-sm font-mono text-white font-bold tracking-wider">{{ statsAlocacao.exposicaoValor }} <span class="text-[10px] text-gray-500 font-sans tracking-normal font-normal">alocados em Open Bets.</span></span>
                </div>
              </div>

              <div class="flex flex-col gap-3 mt-auto">
                <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold border-b border-white/5 pb-1">Diretrizes Matemáticas</span>
                <div class="flex justify-between items-center bg-black/40 p-4 rounded-xl border border-white/5 hover:bg-white/[0.02] transition-colors">
                  <span class="text-xs font-bold text-gray-300">Kelly Fracionado Target</span>
                  <span class="text-sm font-mono text-yellow-500 font-bold bg-yellow-500/10 px-2 py-1 rounded border border-yellow-500/20">{{ statsAlocacao.kellyMult }}</span>
                </div>
                <div class="flex justify-between items-center bg-black/40 p-4 rounded-xl border border-white/5 hover:bg-white/[0.02] transition-colors">
                  <span class="text-xs font-bold text-gray-300">Unidade Base Recomendada (1u)</span>
                  <span class="text-sm font-mono text-white font-bold">{{ statsAlocacao.unidade }}</span>
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'ledger'" titulo="Ledger de Operações Instanciadas" class="h-full min-h-[400px] shadow-2xl border border-white/5 bg-[#0b0f19]">
            <template #icone><LayoutList :size="16" color="var(--text-muted)" /></template>
            <template #acoes>
               <span class="text-[9px] text-[#10B981] uppercase tracking-widest font-bold bg-[#10B981]/10 px-3 py-1 rounded-lg border border-[#10B981]/20 shadow-[0_0_10px_rgba(16,185,129,0.1)] flex items-center gap-1.5"><Radio size="10" class="animate-pulse"/> Real-Time Ledger</span>
            </template>

            <div class="flex flex-col h-full mt-4">
              <div class="grid grid-cols-12 px-5 py-3 border-b border-white/10 text-[9px] uppercase font-bold text-gray-500 tracking-widest bg-black/60 rounded-t-xl">
                <span class="col-span-2">Time/Ref</span>
                <span class="col-span-4 pl-2">Ativo (Jogo / Mercado)</span>
                <span class="col-span-1 text-center">Odd</span>
                <span class="col-span-2 text-center">CLV Edge</span>
                <span class="col-span-1 text-center">Stake</span>
                <span class="col-span-2 text-right">Resultado</span>
              </div>
              
              <div class="flex flex-col overflow-y-auto custom-scrollbar flex-1 p-1 gap-1.5">
                <div v-if="ledgerOperacoes.length === 0" class="text-center text-[10px] text-gray-500 py-16 font-mono uppercase tracking-widest bg-black/20 rounded-xl flex-1 flex flex-col items-center justify-center mt-1 gap-3 opacity-50 border border-dashed border-white/5">
                  <Database size="32" class="text-gray-600"/> Aguardando Operações na Base de Dados...
                </div>
                
                <div v-for="(op, i) in ledgerOperacoes" :key="'op'+i" class="grid grid-cols-12 items-center bg-[#121927] border border-white/5 rounded-xl p-3 relative group hover:border-white/20 transition-all cursor-default overflow-hidden">
                  <div class="absolute left-0 top-0 w-1 h-full transition-colors" 
                       :class="op.status === 'WON' ? 'bg-[#10B981] shadow-[2px_0_10px_#10B981]' : (op.status === 'LOST' ? 'bg-red-500' : 'bg-blue-500')"></div>
                  
                  <div class="col-span-2 flex flex-col pl-3">
                    <span class="text-[10px] font-mono font-bold text-gray-400 group-hover:text-white transition-colors">{{ op.ticker || `BTG-${i}X` }}</span>
                    <span class="text-[8px] text-gray-600 font-mono mt-0.5 flex items-center gap-1"><Clock size="8"/>{{ op.hora }}</span>
                  </div>

                  <div class="col-span-4 flex flex-col border-l border-white/5 pl-3">
                    <span class="text-[11px] font-bold text-white truncate font-sans tracking-wide">{{ op.jogo }}</span>
                    <span class="text-[9px] text-[#3B82F6] uppercase tracking-widest mt-1 truncate font-bold font-mono">{{ op.mercado }}</span>
                  </div>
                  
                  <div class="col-span-1 flex flex-col items-center justify-center">
                    <span class="text-[13px] font-mono text-white font-black">@{{ parseFloat(op.odd || op.odd_placed).toFixed(2) }}</span>
                  </div>

                  <div class="col-span-2 flex flex-col items-center justify-center">
                    <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded border" 
                          :class="op.clv > 0 ? 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/30 shadow-[0_0_8px_rgba(16,185,129,0.2)]' : 'bg-red-500/10 text-red-400 border-red-500/30'">
                      {{ op.clv > 0 ? '+' : ''}}{{ op.clv ? parseFloat(op.clv).toFixed(1) : '0.0' }}%
                    </span>
                  </div>
                  
                  <div class="col-span-1 flex flex-col items-center justify-center">
                    <span class="text-[11px] font-mono text-gray-300 bg-black/60 px-2 py-1 rounded border border-white/10 font-bold">{{ parseFloat(op.stake || op.stake_amount).toFixed(1) }}u</span>
                  </div>
                  
                  <div class="col-span-2 flex justify-end items-center pr-2">
                    <div v-if="op.status === 'WON'" class="flex flex-col items-end gap-1">
                       <span class="text-sm font-mono font-black text-[#10B981] drop-shadow-[0_0_8px_rgba(16,185,129,0.4)] tracking-tight">+{{ formatCurrency(op.pnl) }}</span>
                       <span class="text-[8px] bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/30 px-1.5 py-0.5 rounded uppercase font-bold tracking-widest">WON</span>
                    </div>
                    <div v-else-if="op.status === 'LOST'" class="flex flex-col items-end gap-1">
                       <span class="text-sm font-mono font-bold text-red-500 tracking-tight">{{ formatCurrency(op.pnl) }}</span>
                       <span class="text-[8px] bg-red-500/10 text-red-500 border border-red-500/30 px-1.5 py-0.5 rounded uppercase font-bold tracking-widest">LOST</span>
                    </div>
                    <div v-else class="flex flex-col items-end gap-1">
                       <span class="text-sm font-mono font-bold text-blue-400">LIVE</span>
                       <span class="text-[8px] bg-blue-500/10 text-blue-400 border border-blue-500/30 px-1.5 py-0.5 rounded uppercase font-bold tracking-widest animate-pulse shadow-[0_0_8px_rgba(59,130,246,0.3)]">PENDING</span>
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
      <transition name="fade-modal">
        <div v-if="showAporteModal" class="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-md flex items-center justify-center p-4" @click.self="showAporteModal = false">
          <div class="bg-[#0b0f19] border border-white/10 w-full max-w-md rounded-3xl shadow-[0_30px_80px_rgba(0,0,0,0.9)] overflow-hidden scale-up-center relative">
            <div class="absolute top-0 right-0 w-48 h-48 bg-[#10B981]/10 rounded-full blur-[40px] pointer-events-none"></div>
            
            <div class="p-6 border-b border-white/5 flex justify-between items-center bg-[#121927]">
              <h3 class="font-bold text-white uppercase tracking-widest text-sm flex items-center gap-2">
                <DollarSign size="18" class="text-[#10B981]"/> Injeção de Capital (AUM)
              </h3>
              <button @click="showAporteModal = false" class="text-gray-500 hover:text-red-400 transition-colors bg-black/50 p-1.5 rounded-full border border-white/5"><X size="16"/></button>
            </div>

            <div class="p-8">
              <p class="text-[11px] text-gray-400 mb-6 leading-relaxed font-mono">Insira o valor nominal em <strong class="text-white">BRL</strong> para integralizar no fundo ativo ({{ globalState?.uiMode || 'REAL' }}). Este montante recalibrará de imediato a matriz de Kelly Criterion e exposição global das bancas.</p>
              
              <div class="relative mb-8 group">
                <span class="absolute left-5 top-1/2 -translate-y-1/2 text-gray-500 font-mono text-xl group-focus-within:text-[#10B981] transition-colors">R$</span>
                <input type="number" v-model.number="valorAporte" class="w-full bg-[#121927] border border-white/10 rounded-2xl py-5 pl-14 pr-6 text-3xl font-mono text-white focus:outline-none focus:border-[#10B981] focus:ring-1 focus:ring-[#10B981]/50 transition-all placeholder-gray-700 shadow-inner" placeholder="0.00" min="1" step="100" />
              </div>

              <div class="grid grid-cols-3 gap-3 mb-8">
                <button @click="valorAporte = 1000" class="bg-white/[0.02] hover:bg-white/10 border border-white/5 hover:border-white/20 py-3 rounded-xl text-xs font-mono text-gray-300 font-bold transition-all hover:scale-105">+1K</button>
                <button @click="valorAporte = 5000" class="bg-white/[0.02] hover:bg-white/10 border border-white/5 hover:border-white/20 py-3 rounded-xl text-xs font-mono text-gray-300 font-bold transition-all hover:scale-105">+5K</button>
                <button @click="valorAporte = 10000" class="bg-white/[0.02] hover:bg-white/10 border border-white/5 hover:border-white/20 py-3 rounded-xl text-xs font-mono text-gray-300 font-bold transition-all hover:scale-105">+10K</button>
              </div>

              <button @click="realizarAporte" :disabled="!valorAporte || valorAporte <= 0 || isDepositing" class="w-full py-4 bg-gradient-to-r from-[#10B981] to-[#059669] text-black font-black uppercase tracking-widest text-sm rounded-xl shadow-[0_10px_30px_rgba(16,185,129,0.3)] hover:shadow-[0_10px_40px_rgba(16,185,129,0.5)] hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2">
                <div v-if="isDepositing" class="w-5 h-5 border-2 border-black/20 border-t-black rounded-full animate-spin"></div>
                {{ isDepositing ? 'Sincronizando Ledger...' : 'Confirmar Transferência' }}
              </button>
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
  Wallet, TrendingUp, TrendingDown, Crosshair, Target, Search, Plus, Radio,
  ShieldAlert, AlertTriangle, LayoutList, GripHorizontal, Activity, LineChart, PieChart, DollarSign, X, Check, Clock, Database
} from 'lucide-vue-next';
import WidgetCard from './WidgetCard.vue';
import axios from 'axios';

const rawApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_BASE_URL = rawApiUrl.endsWith('/api/v1') ? rawApiUrl : `${rawApiUrl.replace(/\/$/, '')}/api/v1`;
const globalState = inject('globalState');

// 🛑 A CURA DO LAYOUT: Ajuste dos spans (5 para Alocação, 7 para Ledger)
const layoutBanca = ref([
  { id: 'equity', span: 'col-span-1 xl:col-span-8' },
  { id: 'risco', span: 'col-span-1 xl:col-span-4' },
  { id: 'alocacao', span: 'col-span-1 xl:col-span-5' },
  { id: 'ledger', span: 'col-span-1 xl:col-span-7' }
]);

const isLoading = ref(true);
const showAporteModal = ref(false);
const valorAporte = ref(null);
const isDepositing = ref(false);

const statsBanca = ref({ exposicao: "R$ 0,00", exposicaoPct: 0, yield: "0.00", aum: "R$ 0,00" });
const statsPerformance = ref({ zScore: "2.1", turnover: "R$ 0,00", roi: "0.0%", clvRate: "0.0%" });
const statsRisco = ref({ drawdownAtual: "0.0%", drawdownMax: "0.0%", riscoRuinaPct: "0.01%", riscoRuinaGauge: 5, sharpe: "0.00", badRun: "-" });
const statsAlocacao = ref({ exposicaoPct: 0, exposicaoValor: "R$ 0,00", kellyMult: "0.0", unidade: "R$ 0,00", maxBet: "0u" });
const ledgerOperacoes = ref([]);

const formatCurrency = (val) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val || 0);

const fetchGestaoData = async () => {
  try {
    isLoading.value = true;
    const token = localStorage.getItem('betgenius_token');
    const opts = { headers: { Authorization: `Bearer ${token}` } };
    const modoAtual = globalState?.uiMode || 'REAL'; 
    
    const response = await axios.get(`${API_BASE_URL}/fund/dashboard?mode=${modoAtual}`, opts);
    
    if (response.data) {
      const data = response.data;
      if(data.statsBanca) statsBanca.value = data.statsBanca;
      if(data.statsPerformance) statsPerformance.value = data.statsPerformance;
      if(data.statsRisco) statsRisco.value = data.statsRisco;
      if(data.statsAlocacao) statsAlocacao.value = data.statsAlocacao;
      ledgerOperacoes.value = data.ledgerOperacoes || [];
    }
  } catch (error) {
    console.error("❌ Falha ao buscar dados da Tesouraria:", error);
  } finally {
    isLoading.value = false;
  }
};

const realizarAporte = async () => {
  if (!valorAporte.value || valorAporte.value <= 0) return;
  isDepositing.value = true;
  
  try {
    const token = localStorage.getItem('betgenius_token');
    const opts = { headers: { Authorization: `Bearer ${token}` } };
    const modoAtual = globalState?.uiMode || 'REAL'; 
    
    await axios.post(`${API_BASE_URL}/fund/deposit`, { amount: valorAporte.value, target: modoAtual }, opts);
    
    showAporteModal.value = false;
    valorAporte.value = null;
    
    alert("Injeção Registrada! Banco de Dados e Ledger atualizados.");
    await fetchGestaoData(); 
  } catch (error) {
    alert("Falha na Injeção de Capital (Erro 500 no Servidor Evitado). Verifique a base de dados.");
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
.glass-card { background: rgba(18, 25, 39, 0.85); border-radius: 20px; backdrop-filter: blur(30px); border: 1px solid rgba(255, 255, 255, 0.05); }
.ghost-widget { opacity: 0.3 !important; border: 2px dashed #10B981 !important; transform: scale(0.98); background: rgba(16, 185, 129, 0.05); border-radius: 20px;}
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(16, 185, 129, 0.2); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(16, 185, 129, 0.4); }

.fade-in-up { animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
@keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }

.scale-up-center { animation: scaleUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
@keyframes scaleUp { from { opacity: 0; transform: scale(0.95) translateY(10px); } to { opacity: 1; transform: scale(1) translateY(0); } }

.fade-modal-enter-active, .fade-modal-leave-active { transition: opacity 0.3s ease; }
.fade-modal-enter-from, .fade-modal-leave-to { opacity: 0; }
</style>