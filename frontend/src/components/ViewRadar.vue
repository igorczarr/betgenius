<template>
  <div class="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start fade-in-up pb-10">
    
    <div class="col-span-1 xl:col-span-9 flex flex-col gap-5">

      <div class="glass-card p-5 px-6 flex flex-col lg:flex-row items-center justify-between gap-5 border-t-2 border-bet-primary shadow-[0_10px_30px_rgba(0,0,0,0.4)] bg-gradient-to-r from-[#121927] to-[#0f1523]">
        
        <div class="flex items-center gap-3 shrink-0 border-r border-white/10 pr-6 w-full lg:w-auto justify-center lg:justify-start">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-bet-primary/20 to-transparent flex items-center justify-center border border-bet-primary/30 shadow-[0_0_15px_rgba(140,199,255,0.2)]">
            <SlidersHorizontal :size="18" class="text-bet-primary" />
          </div>
          <div class="flex flex-col">
            <span class="text-xs text-white uppercase tracking-widest font-bold">Global Screener</span>
            <span class="text-[9px] text-gray-500 font-mono uppercase mt-0.5"><strong class="text-bet-primary">14</strong> Oportunidades Mapeadas</span>
          </div>
        </div>

        <div class="flex flex-wrap md:flex-nowrap items-center gap-6 flex-1 w-full justify-between lg:justify-end">
          
          <div class="flex flex-col gap-1.5 w-[45%] md:w-auto">
            <span class="text-[9px] text-gray-400 uppercase tracking-widest font-bold flex items-center gap-1.5"><Globe size="10" class="text-bet-secondary"/> Liquidez de Mercado</span>
            <div class="flex bg-black/40 border border-white/10 rounded-lg overflow-hidden p-0.5 shadow-inner">
              <button @click="filtroTier = 'tier1'" :class="filtroTier === 'tier1' ? 'bg-bet-secondary/20 text-white border-bet-secondary/50' : 'text-gray-500 border-transparent hover:text-gray-300'" class="px-3 py-1 text-[9px] font-bold uppercase tracking-wider border rounded transition-colors">T1 (Elite)</button>
              <button @click="filtroTier = 'all'" :class="filtroTier === 'all' ? 'bg-bet-secondary/20 text-white border-bet-secondary/50' : 'text-gray-500 border-transparent hover:text-gray-300'" class="px-3 py-1 text-[9px] font-bold uppercase tracking-wider border rounded transition-colors">Todas</button>
            </div>
          </div>

          <div class="flex flex-col gap-1.5 w-full md:w-56 bg-black/20 p-2 rounded-lg border border-white/5 shadow-inner">
            <div class="flex justify-between items-center px-1">
              <span class="text-[9px] text-gray-400 uppercase tracking-widest font-bold flex items-center gap-1.5"><Target size="10" class="text-[#10B981]"/> Mínimo +EV</span>
              <span class="text-[11px] font-mono text-[#10B981] font-bold drop-shadow-[0_0_5px_rgba(16,185,129,0.5)]">{{ filtroEV.toFixed(1) }}%</span>
            </div>
            <div class="px-1 mt-1">
               <input type="range" v-model.number="filtroEV" min="0" max="15" step="0.5" class="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-[#10B981]" />
            </div>
          </div>

          <div class="flex flex-col gap-1.5 w-[45%] md:w-auto">
            <span class="text-[9px] text-gray-400 uppercase tracking-widest font-bold flex items-center gap-1.5"><Clock size="10" class="text-yellow-500"/> Janela de Tempo</span>
            <select v-model="filtroTempo" class="bg-black/50 text-[10px] text-white border border-white/10 rounded-lg px-3 py-1.5 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-yellow-500 transition-colors focus:ring-1 focus:ring-yellow-500 shadow-inner">
              <option value="live">🔴 Ao Vivo (In-Play)</option>
              <option value="2h">Próximas 2 Horas</option>
              <option value="12h">Próximas 12 Horas</option>
              <option value="24h">Hoje</option>
            </select>
          </div>

          <div class="hidden xl:flex items-center justify-center pl-4 border-l border-white/10">
            <button class="flex flex-col items-center gap-1 group">
              <div class="w-8 h-8 rounded-full bg-yellow-500/10 border border-yellow-500/30 flex items-center justify-center group-hover:bg-yellow-500 group-hover:text-black transition-all shadow-[0_0_10px_rgba(234,179,8,0.2)]">
                <BellRing size="14" class="text-yellow-500 group-hover:text-black" />
              </div>
              <span class="text-[8px] text-gray-500 uppercase tracking-widest font-bold group-hover:text-yellow-500 transition-colors">Regras</span>
            </button>
          </div>

        </div>
      </div>

      <transition name="slide-up">
         <div v-if="surebetActive" class="bg-gradient-to-r from-[#10B981]/20 to-transparent border border-[#10B981]/30 p-3 rounded-lg flex items-center justify-between shadow-[0_0_15px_rgba(16,185,129,0.15)] relative overflow-hidden group">
            <div class="absolute left-0 top-0 w-1 h-full bg-[#10B981] shadow-[0_0_10px_#10B981]"></div>
            <div class="flex items-center gap-4 pl-3">
               <div class="w-8 h-8 rounded-full bg-[#10B981]/10 flex items-center justify-center border border-[#10B981]/30">
                 <RefreshCcw size="16" class="text-[#10B981] animate-spin-slow" />
               </div>
               <div class="flex flex-col">
                  <span class="text-[11px] font-bold text-white uppercase tracking-widest flex items-center gap-2">Arbitragem Cross-Market Detectada <span class="bg-[#10B981] text-black px-1.5 py-0 rounded text-[8px] font-mono shadow-sm">Risco Zero</span></span>
                  <span class="text-[10px] text-gray-300 mt-0.5 font-mono">Real Madrid: BTTS-Sim @ <strong class="text-white">1.95</strong> vs Under 2.5 @ <strong class="text-white">2.20</strong> (Ambos Pinnacle)</span>
               </div>
            </div>
            <div class="flex items-center gap-4">
               <span class="text-lg font-mono text-[#10B981] font-bold drop-shadow-[0_0_5px_rgba(16,185,129,0.5)]">+0.84% PnL</span>
               <button @click="surebetActive = false" class="text-gray-500 hover:text-white transition-colors bg-black/40 p-1.5 rounded"><X size="14"/></button>
            </div>
         </div>
      </transition>

      <draggable 
        v-model="blocosVerticais" 
        item-key="id" 
        class="flex flex-col gap-6 w-full" 
        handle=".drag-vertical" 
        ghost-class="ghost-widget"
        animation="250"
      >
        <template #item="{ element }">
          <div class="relative group/vert w-full">
            
            <div class="drag-vertical absolute -left-2 top-1/2 -translate-y-1/2 z-50 opacity-0 group-hover/vert:opacity-100 cursor-move p-1.5 bg-black/80 text-bet-primary rounded border border-white/10 shadow-lg transition-all hover:bg-bet-primary hover:text-black">
              <GripVertical size="18" />
            </div>

            <template v-if="element.id === 'hft_matrix'">
              <WidgetCard titulo="HFT Value Matrix & Market Tracker" class="w-full shadow-[0_15px_40px_rgba(0,0,0,0.3)]">
                <template #icone><LineChart :size="16" color="#10B981" /></template>
                <template #acoes>
                  <div class="flex items-center bg-black/40 p-0.5 rounded border border-white/10">
                    <button @click="hftTab = 'match'" :class="hftTab === 'match' ? 'bg-[#10B981]/20 text-[#10B981] border-[#10B981]/50' : 'text-gray-500 border-transparent hover:text-white'" class="px-3 py-1 text-[9px] font-bold uppercase tracking-wider border rounded transition-colors">Match Odds</button>
                    <button @click="hftTab = 'props'" :class="hftTab === 'props' ? 'bg-[#a855f7]/20 text-[#a855f7] border-[#a855f7]/50' : 'text-gray-500 border-transparent hover:text-white'" class="px-3 py-1 text-[9px] font-bold uppercase tracking-wider border rounded transition-colors flex items-center gap-1"><User size="10"/> Player Props <div class="w-1.5 h-1.5 bg-[#a855f7] rounded-full animate-ping ml-1"></div></button>
                  </div>
                </template>

                <div class="flex flex-col w-full overflow-x-auto custom-scrollbar pb-2 mt-2">
                  <div class="min-w-[750px]">
                    <div class="grid grid-cols-12 gap-2 text-[9px] uppercase tracking-widest font-bold text-gray-500 border-b border-white/10 pb-2 mb-2 bg-black/20 p-2 rounded-t-lg">
                      <span class="col-span-1 text-center">Hora</span>
                      <span class="col-span-2">Ativo</span>
                      <span class="col-span-2 text-center text-blue-400">Sharp (Pinnacle)</span>
                      <span class="col-span-2 text-center text-gray-400">Trend (Sparkline)</span>
                      <span class="col-span-1 text-center text-yellow-500">Soft Bookie</span>
                      <span class="col-span-2 text-center text-[#10B981]">+EV Edge / Depth</span>
                      <span class="col-span-2 text-right pr-2">Ação</span>
                    </div>
                    
                    <div class="flex flex-col gap-1.5">
                      <div v-for="(item, i) in (hftTab === 'match' ? hftData : propsAnomalyData)" :key="'hft'+i" class="grid grid-cols-12 gap-2 items-center bg-[#121927] border border-white/5 hover:border-white/20 p-2 rounded-lg transition-colors group relative overflow-hidden h-14">
                        <div class="absolute left-0 top-0 w-1 h-full opacity-50 group-hover:opacity-100 transition-opacity" :class="hftTab === 'match' ? 'bg-[#10B981]' : 'bg-[#a855f7]'"></div>
                        
                        <span class="col-span-1 text-center text-[10px] font-mono text-gray-400">{{ item.hora }}</span>
                        
                        <div class="col-span-2 flex flex-col pl-2 border-l border-white/5">
                          <span class="text-xs font-bold text-white truncate">{{ item.jogo }}</span>
                          <span class="text-[9px] uppercase tracking-wider mt-0.5 font-mono truncate" :class="hftTab === 'match' ? 'text-bet-primary' : 'text-[#a855f7]'">{{ item.mercado }}</span>
                        </div>

                        <div class="col-span-2 flex flex-col items-center justify-center bg-black/40 py-1 rounded border border-white/5 h-full">
                          <div class="flex items-center gap-1 font-mono text-xs font-bold">
                            <span class="text-gray-500 line-through text-[9px]">{{ item.pinOpen }}</span>
                            <ArrowRight size="10" class="text-gray-600"/>
                            <span :class="item.pinClose < item.pinOpen ? 'text-red-400' : 'text-green-400'">{{ item.pinClose }}</span>
                          </div>
                          <span class="text-[8px] text-gray-500 uppercase mt-0.5 tracking-widest">Fair: {{ item.trueOdd }}</span>
                        </div>

                        <div class="col-span-2 flex items-center justify-center h-full px-2">
                           <svg viewBox="0 0 50 15" class="w-full h-4 overflow-visible">
                             <polyline :points="item.sparkline" fill="none" :stroke="item.pinClose < item.pinOpen ? '#EF4444' : '#10B981'" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
                             <circle cx="50" :cy="item.sparkline.split(' ').pop().split(',')[1]" r="1.5" :fill="item.pinClose < item.pinOpen ? '#EF4444' : '#10B981'" />
                           </svg>
                        </div>

                        <div class="col-span-1 flex flex-col items-center justify-center">
                          <span class="text-xs font-mono font-bold text-white bg-yellow-500/10 border border-yellow-500/30 px-2 py-0.5 rounded">{{ item.softOdd }}</span>
                          <span class="text-[8px] text-yellow-500 uppercase mt-1 font-bold truncate max-w-full px-1">{{ item.bookie }}</span>
                        </div>

                        <div class="col-span-2 flex flex-col items-center justify-center border-l border-white/5 h-full pl-1">
                          <div class="flex items-center gap-1.5">
                            <span class="text-xs font-mono font-bold drop-shadow-[0_0_5px_currentColor]" :class="hftTab === 'match' ? 'text-[#10B981]' : 'text-[#a855f7]'">+{{ item.ev }}%</span>
                            <div class="flex flex-col gap-0.5" title="Liquidez/Market Depth">
                              <div class="w-4 h-1 bg-gray-700 rounded-sm overflow-hidden flex"><div class="h-full bg-white w-full"></div></div>
                              <div class="w-4 h-1 bg-gray-700 rounded-sm overflow-hidden flex"><div class="h-full bg-white" :style="`width: ${item.depth}%`"></div></div>
                            </div>
                          </div>
                          <span class="text-[8px] text-gray-400 uppercase mt-0.5 font-mono">Kelly: {{ item.kelly }}u</span>
                        </div>

                        <div class="col-span-2 flex justify-end items-center gap-2 pr-2 h-full">
                          <button class="w-7 h-7 rounded bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all"><BarChart2 size="12"/></button>
                          <button class="w-7 h-7 rounded border flex items-center justify-center transition-all shadow-lg hover:shadow-white" :class="hftTab === 'match' ? 'bg-[#10B981]/10 border-[#10B981]/30 text-[#10B981] hover:bg-[#10B981] hover:text-black shadow-[0_0_10px_rgba(16,185,129,0.2)]' : 'bg-[#a855f7]/10 border-[#a855f7]/30 text-[#a855f7] hover:bg-[#a855f7] hover:text-white shadow-[0_0_10px_rgba(168,85,247,0.2)]'"><Plus size="14" strokeWidth="3"/></button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </WidgetCard>
            </template>

            <template v-else-if="element.type === 'grid'">
              <draggable 
                v-model="widgetsMenores" 
                item-key="id" 
                class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start w-full" 
                handle=".drag-horizontal" 
                ghost-class="ghost-widget"
                animation="250"
              >
                <template #item="{ element: subElement }">
                  <div class="relative group/horiz w-full h-full flex flex-col">
                    <div class="drag-horizontal absolute -top-3 left-1/2 -translate-x-1/2 z-50 opacity-0 group-hover/horiz:opacity-100 cursor-move p-1.5 px-6 bg-black/90 text-bet-primary rounded-b-xl border border-white/10 shadow-[0_10px_20px_rgba(0,0,0,0.8)] transition-all hover:bg-bet-primary hover:text-black">
                      <GripHorizontal size="16" />
                    </div>
                    
                    <WidgetCard v-if="subElement.id === 'asian_scanner'" titulo="Live Asian Pressure Scanner" class="w-full flex-1 shadow-[0_10px_30px_rgba(0,0,0,0.3)] border-t-2 border-blue-500">
                      <template #icone><Activity :size="16" color="#3b82f6" /></template>
                      <div class="flex flex-col gap-3 mt-2 h-full">
                        <div v-for="(live, i) in livePressureData" :key="'lp'+i" class="bg-black/20 border border-white/5 p-3 rounded-xl relative overflow-hidden group hover:border-blue-500/30 transition-colors">
                          <div class="absolute right-0 top-0 h-full w-24 bg-gradient-to-l from-blue-500/10 to-transparent pointer-events-none"></div>
                          
                          <div class="flex justify-between items-center mb-2">
                            <span class="text-xs font-bold text-white truncate pr-2">{{ live.jogo }}</span>
                            <span class="text-[10px] bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded font-mono font-bold animate-pulse border border-red-500/20 shrink-0">{{ live.tempo }}'</span>
                          </div>
                          
                          <div class="flex flex-col gap-1 mb-3">
                            <div class="flex justify-between items-end text-[9px] uppercase font-bold tracking-widest text-gray-500">
                              <span :class="live.pressaoCasa > live.pressaoFora ? 'text-blue-400' : ''">Casa APM: {{ live.apmCasa }}</span>
                              <span :class="live.pressaoFora > live.pressaoCasa ? 'text-blue-400' : ''">Fora APM: {{ live.apmFora }}</span>
                            </div>
                            <div class="w-full h-1.5 bg-gray-800 rounded flex overflow-hidden shadow-inner">
                              <div class="h-full bg-blue-500 transition-all" :style="`width: ${(live.pressaoCasa / (live.pressaoCasa + live.pressaoFora)) * 100}%`"></div>
                              <div class="h-full bg-white/20 w-0.5"></div>
                              <div class="h-full bg-gray-500 transition-all" :style="`width: ${(live.pressaoFora / (live.pressaoCasa + live.pressaoFora)) * 100}%`"></div>
                            </div>
                          </div>

                          <div class="flex justify-between items-center bg-[#121927] p-2 rounded border border-white/5">
                            <div class="flex flex-col">
                              <span class="text-[8px] text-gray-500 uppercase tracking-widest font-bold">Asian Line Drop</span>
                              <div class="flex items-center gap-1 font-mono text-xs font-bold text-white">
                                <span>{{ live.linhaAntiga }}</span> <ArrowDownRight size="12" class="text-red-400"/> <span class="text-red-400">{{ live.linhaAtual }}</span>
                              </div>
                            </div>
                            <button class="bg-blue-500/20 text-blue-400 border border-blue-500/30 px-2 py-1 rounded text-[9px] font-bold uppercase hover:bg-blue-500 hover:text-white transition-colors">Analisar</button>
                          </div>
                        </div>
                      </div>
                    </WidgetCard>

                    <WidgetCard v-else-if="subElement.id === 'smart_steamers'" titulo="Smart Money Steamers" class="w-full flex-1 shadow-[0_10px_30px_rgba(0,0,0,0.3)] border-t-2 border-yellow-500">
                      <template #icone><Flame :size="16" color="#F59E0B" /></template>
                      <div class="flex flex-col gap-3 mt-2 h-full">
                        <div v-for="(steamer, i) in steamersData" :key="'st'+i" class="bg-black/20 border border-white/5 p-3 rounded-xl relative overflow-hidden group hover:border-yellow-500/30 transition-colors">
                          <div class="absolute left-0 top-0 h-full w-1" :class="steamer.urgencia === 'high' ? 'bg-red-500' : 'bg-yellow-500'"></div>
                          <div class="flex justify-between items-start mb-2 pl-2">
                            <div class="flex flex-col">
                              <span class="text-[9px] text-gray-500 uppercase font-mono tracking-widest">{{ steamer.tempo }}</span>
                              <span class="text-xs font-bold text-white">{{ steamer.jogo }}</span>
                            </div>
                            <span class="text-[10px] font-mono font-bold text-yellow-400 bg-yellow-500/10 px-2 py-0.5 rounded border border-yellow-500/20 shadow-inner shrink-0">Vol: {{ steamer.volume }}</span>
                          </div>
                          <div class="flex items-center gap-2 pl-2 mt-2 border-t border-white/5 pt-2">
                            <Zap :size="12" :class="steamer.urgencia === 'high' ? 'text-red-400' : 'text-yellow-500'" class="animate-pulse shrink-0" />
                            <span class="text-[10px] text-gray-300 font-mono truncate">Spike no mercado: <strong class="text-white">{{ steamer.mercado }}</strong></span>
                          </div>
                          <div class="mt-2 pl-2 flex justify-between items-center text-[10px] font-mono">
                            <span class="text-gray-500">Odd de Entrada:</span>
                            <span class="font-bold text-white bg-black/60 px-2 py-1 rounded border border-gray-700 shadow-inner">{{ steamer.odd }}</span>
                          </div>
                        </div>
                      </div>
                    </WidgetCard>
                  </div>
                </template>
              </draggable>
            </template>

            <template v-else-if="element.id === 'ai_picks'">
              <WidgetCard titulo="AI Gold Picks (Z-Score > 2.0)" class="w-full shadow-[0_15px_40px_rgba(0,0,0,0.3)] border-t-2 border-[#10B981]">
                <template #icone><Target :size="16" color="#10B981" /></template>
                <template #acoes>
                   <span class="text-[9px] text-[#10B981] font-mono font-bold uppercase tracking-widest bg-[#10B981]/10 px-2 py-0.5 rounded border border-[#10B981]/20">Modelo Validado</span>
                </template>
                <div class="flex flex-col gap-3 mt-2">
                  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div v-for="(pick, i) in goldPicksData" :key="'gp'+i" class="bg-gradient-to-br from-[#121927] to-black border border-white/10 p-4 rounded-xl relative overflow-hidden group hover:border-[#10B981]/30 transition-colors shadow-lg">
                      <div class="absolute -right-10 -top-10 w-24 h-24 bg-[#10B981]/10 rounded-full blur-2xl pointer-events-none group-hover:bg-[#10B981]/20 transition-colors"></div>
                      <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold block mb-1">{{ pick.liga }}</span>
                      <span class="text-sm font-bold text-white truncate block mb-3 drop-shadow-sm">{{ pick.jogo }}</span>
                      <div class="flex justify-between items-center mb-3 bg-black/40 p-2.5 rounded border border-white/5 shadow-inner">
                        <div class="flex flex-col">
                          <span class="text-[9px] text-gray-500 uppercase tracking-widest">Ação Detectada</span>
                          <span class="text-[11px] font-mono font-bold text-[#10B981]">{{ pick.aposta }}</span>
                        </div>
                        <span class="text-sm font-mono font-bold text-white bg-[#121927] px-2 py-0.5 rounded border border-gray-700">{{ pick.odd }}</span>
                      </div>
                      <div class="flex justify-between items-center border-t border-white/5 pt-3 mt-1">
                        <span class="text-[9px] text-gray-400 font-mono flex items-center gap-1"><BarChart2 size="10" class="text-blue-400"/> Z-Score: <strong class="text-blue-400">{{ pick.zscore }}</strong></span>
                        <span class="text-[9px] text-[#10B981] font-bold uppercase bg-[#10B981]/10 px-1.5 py-0.5 rounded border border-[#10B981]/30 shadow-sm">+{{ pick.ev }}% EV</span>
                      </div>
                    </div>
                  </div>
                </div>
              </WidgetCard>
            </template>

          </div>
        </template>
      </draggable>
      
    </div>

    <div class="col-span-1 xl:col-span-3 flex flex-col gap-4 h-[850px]">
      
      <div class="bg-gradient-to-br from-[#121927] to-black border border-white/5 rounded-xl p-4 flex flex-col gap-1 shadow-[0_10px_30px_rgba(0,0,0,0.5)] shrink-0 relative overflow-hidden">
         <div class="absolute -right-10 -bottom-10 w-32 h-32 bg-bet-primary/10 rounded-full blur-[40px] pointer-events-none"></div>
         <div class="flex items-center gap-2 mb-1">
            <Activity size="14" class="text-bet-primary" />
            <h3 class="text-sm font-mono font-bold text-white tracking-widest uppercase">Alpha Quant Feed</h3>
         </div>
         <span class="text-[10px] text-gray-400 uppercase tracking-widest">Macro Market Movers</span>
      </div>

      <div class="glass-card flex-1 overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.5)] flex flex-col p-4 gap-5 custom-scrollbar overflow-y-auto border border-white/5 rounded-xl">
        
        <div class="flex flex-col gap-3">
          <div class="flex items-center justify-between border-b border-white/10 pb-2">
            <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold flex items-center gap-1.5"><TrendingDown size="12" class="text-red-400"/> Top Drops (1h)</span>
            <span class="text-[8px] bg-white/5 text-gray-500 px-1.5 py-0.5 rounded font-mono">Global</span>
          </div>
          
          <div class="flex flex-col gap-2">
            <div v-for="(drop, i) in topDrops" :key="'td'+i" class="bg-black/30 border border-white/5 p-2.5 rounded-lg hover:bg-white/5 transition-colors group cursor-pointer">
              <div class="flex justify-between items-start mb-1.5">
                <span class="text-[11px] font-bold text-white group-hover:text-bet-primary transition-colors">{{ drop.jogo }}</span>
                <span class="text-[9px] font-mono text-gray-500">{{ drop.liga }}</span>
              </div>
              <div class="flex justify-between items-center bg-[#121927] p-1.5 rounded border border-white/5 shadow-inner">
                <span class="text-[9px] text-gray-400 font-bold uppercase">{{ drop.mercado }}</span>
                <div class="flex items-center gap-1 font-mono text-[10px] font-bold">
                  <span class="text-gray-500 line-through">{{ drop.old }}</span>
                  <ArrowRight size="10" class="text-gray-600"/>
                  <span class="text-red-400">{{ drop.new }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="flex flex-col gap-3 mt-2">
          <div class="flex items-center justify-between border-b border-white/10 pb-2">
            <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold flex items-center gap-1.5"><Database size="12" class="text-blue-400"/> Liquidity Spikes</span>
          </div>
          
          <div class="flex flex-col gap-2">
            <div v-for="(spike, i) in volumeSpikes" :key="'vs'+i" class="bg-black/30 border border-white/5 p-2.5 rounded-lg flex flex-col gap-2">
              <div class="flex justify-between items-center">
                <span class="text-[11px] font-bold text-white">{{ spike.jogo }}</span>
                <span class="text-[9px] text-blue-400 font-bold uppercase bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/20">{{ spike.mercado }}</span>
              </div>
              <div class="flex items-center gap-2">
                <div class="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden flex">
                  <div class="h-full bg-blue-500 animate-pulse" :style="`width: ${spike.percent}%`"></div>
                </div>
                <span class="text-[9px] font-mono font-bold text-white w-12 text-right">{{ spike.vol }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="mt-auto flex flex-col gap-2 bg-black/60 p-3 rounded-xl border border-gray-800 shadow-inner relative overflow-hidden">
          <div class="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-[#10B981] to-transparent opacity-50"></div>
          <div class="flex items-center gap-2 mb-1">
            <Terminal size="12" class="text-gray-500" />
            <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">Bot Execution Log</span>
          </div>
          <div class="flex flex-col gap-1 font-mono text-[8px] text-gray-400 leading-tight h-16 overflow-hidden relative">
            <span v-for="(log, i) in botLogs" :key="'log'+i" class="truncate" :class="{'text-[#10B981]': log.includes('OK'), 'text-yellow-500': log.includes('SCAN')}">> {{ log }}</span>
            <div class="absolute bottom-0 w-full h-8 bg-gradient-to-t from-black/60 to-transparent"></div>
          </div>
          <div class="flex justify-between items-center border-t border-gray-800 pt-2 mt-1">
            <div class="flex items-center gap-1.5">
              <div class="w-1.5 h-1.5 rounded-full bg-[#10B981] shadow-[0_0_5px_#10B981]"></div>
              <span class="text-[8px] text-gray-500 uppercase">Sys: Online</span>
            </div>
            <span class="text-[8px] text-gray-500 font-mono flex items-center gap-1"><Wifi size="8"/> Ping: 12ms</span>
          </div>
        </div>

      </div>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue';
import draggable from 'vuedraggable';
import { 
  GripVertical, GripHorizontal, Radio, SlidersHorizontal, 
  Target, Clock, Globe, RefreshCcw, X, Activity, LineChart, 
  ArrowRight, ArrowDownRight, Plus, BarChart2, Zap, Flame, User, BellRing,
  TrendingDown, Database, Terminal, Wifi
} from 'lucide-vue-next';

// O Layout principal e os Cards
import WidgetCard from './WidgetCard.vue';

// ESTADO DOS MACRO-FILTROS
const filtroTier = ref('tier1');
const filtroEV = ref(5.0); 
const filtroTempo = ref('12h');
const surebetActive = ref(true); 

// ABA DA MATRIZ HFT
const hftTab = ref('match');

// ESTADO DO DRAG AND DROP - ESTRUTURA NATIVA S-TIER
const blocosVerticais = ref([
  { id: 'hft_matrix', type: 'single' }, 
  { id: 'linha-menores', type: 'grid' },
  { id: 'ai_picks', type: 'single' }
]);

const widgetsMenores = ref([
  { id: 'asian_scanner' }, 
  { id: 'smart_steamers' } 
]);

// ==================================================
// MOCK DATA DE ALTA DENSIDADE (HFT, ASIAN, STEAMERS)
// ==================================================

const hftData = ref([
  { hora: "16:00", jogo: "Arsenal x Liverpool", mercado: "Arsenal AH -0.5", pinOpen: "2.10", pinClose: "1.92", trueOdd: "1.85", softOdd: "2.05", bookie: "Betano", ev: "10.8", kelly: "2.5", depth: "100", sparkline: "0,10 10,8 20,12 30,14 40,6 50,4" },
  { hora: "16:45", jogo: "Juventus x Milan", mercado: "Over 2.5 Gols", pinOpen: "1.80", pinClose: "1.65", trueOdd: "1.60", softOdd: "1.75", bookie: "Bet365", ev: "9.3", kelly: "1.8", depth: "80", sparkline: "0,8 10,6 20,5 30,7 40,4 50,2" },
  { hora: "20:30", jogo: "Real Madrid x Sevilla", mercado: "Real Madrid ML", pinOpen: "1.55", pinClose: "1.42", trueOdd: "1.38", softOdd: "1.50", bookie: "Pinnacle", ev: "8.6", kelly: "1.5", depth: "100", sparkline: "0,12 10,10 20,8 30,6 40,5 50,4" },
  { hora: "Ao Vivo", jogo: "Inter x Roma", mercado: "Inter AH -1.0", pinOpen: "2.00", pinClose: "1.88", trueOdd: "1.82", softOdd: "1.95", bookie: "1xBet", ev: "7.1", kelly: "1.2", depth: "60", sparkline: "0,10 10,9 20,11 30,8 40,5 50,3" },
]);

const propsAnomalyData = ref([
  { hora: "16:00", jogo: "Arsenal x Liverpool", mercado: "Saka Over 0.5 Chutes", pinOpen: "1.85", pinClose: "1.55", trueOdd: "1.45", softOdd: "1.90", bookie: "Betano", ev: "22.5", kelly: "4.1", depth: "30", sparkline: "0,12 10,12 20,9 30,8 40,5 50,2" },
  { hora: "20:30", jogo: "Real M. x Sevilla", mercado: "Bellingham Over 1.5 Faltas", pinOpen: "2.10", pinClose: "1.80", trueOdd: "1.72", softOdd: "2.15", bookie: "Bet365", ev: "18.4", kelly: "3.2", depth: "40", sparkline: "0,14 10,12 20,12 30,9 40,6 50,5" },
]);

const livePressureData = ref([
  { jogo: "Napoli x Lazio", tempo: "62", apmCasa: 1.8, apmFora: 0.4, pressaoCasa: 82, pressaoFora: 18, linhaAntiga: "AH -0.5", linhaAtual: "AH -1.0" },
  { jogo: "B. Munique x Union", tempo: "38", apmCasa: 2.1, apmFora: 0.2, pressaoCasa: 91, pressaoFora: 9, linhaAntiga: "O 3.0", linhaAtual: "O 2.5" },
]);

const steamersData = ref([
  { tempo: "Há 2 min", jogo: "Chelsea x Tottenham", volume: "€ 450k", mercado: "Chelsea ML", odd: "2.10", urgencia: "high" },
  { tempo: "Há 14 min", jogo: "PSG x Lyon", volume: "€ 320k", mercado: "Over 3.5 Gols", odd: "1.85", urgencia: "medium" },
]);

const goldPicksData = ref([
  { liga: "Premier League", jogo: "Aston Villa x Newcastle", aposta: "Aston Villa AH -0.25", odd: "1.98", zscore: "2.84", ev: "12.4" },
  { liga: "La Liga", jogo: "Girona x Betis", aposta: "Under 2.5 Gols", odd: "1.82", zscore: "2.51", ev: "9.8" },
  { liga: "Bundesliga", jogo: "Leipzig x Frankfurt", aposta: "Leipzig Over 1.5 Gols", odd: "1.75", zscore: "2.33", ev: "8.1" }
]);

// ==================================================
// MOCK DATA: NOVO ALPHA QUANT FEED (LATERAL DIREITA)
// ==================================================
const topDrops = ref([
  { jogo: "Fenerbahce x Porto", liga: "Europa L.", mercado: "Porto AH 0.0", old: "2.20", new: "1.85" },
  { jogo: "Galatasaray x Celta", liga: "Europa L.", mercado: "Under 2.5", old: "1.95", new: "1.70" },
  { jogo: "Boca Jrs x River", liga: "Libertadores", mercado: "Boca ML", old: "2.40", new: "2.05" },
  { jogo: "Al Ahly x Al Ittihad", liga: "Saudi Pro", mercado: "Over 3.5", old: "2.10", new: "1.78" }
]);

const volumeSpikes = ref([
  { jogo: "Brighton x West Ham", mercado: "Match Odds", vol: "€ 1.2M", percent: 85 },
  { jogo: "Lille x Monaco", mercado: "Asian Handicap", vol: "€ 850k", percent: 60 },
  { jogo: "Fiorentina x Roma", mercado: "Goal Line", vol: "€ 620k", percent: 45 }
]);

const botLogs = ref([
  "FETCHING Pinnacle API... [OK]",
  "SCAN: 1,402 Active Markets...",
  "WARN: High Volatility detected in Serie B (ITA)",
  "CALC: Updating Kelly Multipliers...",
  "MATCH: 14 opportunities found."
]);
</script>

<style scoped>
.glass-card { background: rgba(18, 25, 39, 0.7); backdrop-filter: blur(20px); border-radius: 16px;}

.ghost-widget { opacity: 0.4 !important; border: 2px dashed #10B981 !important; transform: scale(0.98); background: rgba(16, 185, 129, 0.05); }

.animate-spin-slow { animation: spin 3s linear infinite; }

@keyframes marquee {
  0% { transform: translateX(50%); }
  100% { transform: translateX(-100%); }
}
.animate-marquee {
  display: inline-block;
  animation: marquee 35s linear infinite;
  will-change: transform;
}
.animate-marquee:hover {
  animation-play-state: paused;
}
.mask-edges {
  mask-image: linear-gradient(to right, transparent, black 5%, black 95%, transparent);
  -webkit-mask-image: linear-gradient(to right, transparent, black 5%, black 95%, transparent);
}

input[type=range]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #10B981;
  cursor: pointer;
  border: 2px solid #0f1523;
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.8);
  transition: transform 0.1s, box-shadow 0.1s;
}
input[type=range]::-webkit-slider-thumb:hover {
  transform: scale(1.2);
  box-shadow: 0 0 16px rgba(16, 185, 129, 1);
}
input[type=range]::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #10B981;
  cursor: pointer;
  border: 2px solid #0f1523;
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.8);
  transition: transform 0.1s;
}

.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(140, 199, 255, 0.2); border-radius: 10px; }
</style>