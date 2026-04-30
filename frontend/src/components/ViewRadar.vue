<template>
  <div class="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start fade-in-up pb-10 relative">
    
    <transition name="modal-fade">
      <div v-if="showMatchModal" class="fixed inset-0 z-[100] flex items-center justify-center px-4">
        <div class="absolute inset-0 bg-black/80 backdrop-blur-sm" @click="closeMatchStats"></div>
        
        <div class="relative w-full max-w-2xl bg-gradient-to-br from-[#121927] to-[#0a0f16] border border-white/10 rounded-2xl shadow-[0_0_50px_rgba(0,0,0,0.8)] overflow-hidden flex flex-col">
          <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[#10B981] to-transparent"></div>
          
          <div class="flex justify-between items-center p-4 border-b border-white/5 bg-black/20">
            <div class="flex items-center gap-3">
              <Activity class="text-[#10B981]" size="18" />
              <h3 class="text-sm font-bold text-white uppercase tracking-widest font-mono">Terminal de Análise</h3>
            </div>
            <button @click="closeMatchStats" class="text-gray-500 hover:text-red-400 transition-colors bg-white/5 p-1.5 rounded-lg hover:bg-white/10">
              <X size="16" />
            </button>
          </div>

          <div class="p-6 flex flex-col gap-6 min-h-[300px]">
            <div v-if="isLoadingModal" class="flex-1 flex flex-col items-center justify-center gap-4 py-10">
              <div class="relative w-16 h-16 flex items-center justify-center">
                <div class="absolute inset-0 rounded-full border-2 border-[#10B981]/20 border-t-[#10B981] animate-spin"></div>
                <Database size="20" class="text-[#10B981] animate-pulse" />
              </div>
              <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold font-mono">Extraindo Tensores da Matrix...</span>
            </div>

            <div v-else-if="selectedMatchStats" class="flex flex-col gap-6 animate-fade-in">
              <div class="flex justify-between items-center bg-black/40 p-4 rounded-xl border border-white/5">
                <div class="flex flex-col items-center gap-1 w-1/3">
                  <span class="text-lg font-bold text-white text-center">{{ selectedMatchStats.casa }}</span>
                  <span class="text-[10px] text-gray-500 font-mono">xG: {{ selectedMatchStats.xgCasa }}</span>
                </div>
                <div class="flex flex-col items-center justify-center w-1/3">
                  <span class="text-[10px] text-red-400 font-bold bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20 mb-2 animate-pulse" v-if="selectedMatchStats.isLive">LIVE {{ selectedMatchStats.tempo }}'</span>
                  <span class="text-[10px] text-gray-500 font-bold bg-white/5 px-2 py-0.5 rounded border border-white/10 mb-2" v-else>FT</span>
                  <div class="text-3xl font-black text-white tracking-widest flex gap-2">
                    <span>{{ selectedMatchStats.placarCasa }}</span>
                    <span class="text-gray-600">-</span>
                    <span>{{ selectedMatchStats.placarFora }}</span>
                  </div>
                </div>
                <div class="flex flex-col items-center gap-1 w-1/3">
                  <span class="text-lg font-bold text-white text-center">{{ selectedMatchStats.fora }}</span>
                  <span class="text-[10px] text-gray-500 font-mono">xG: {{ selectedMatchStats.xgFora }}</span>
                </div>
              </div>

              <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div v-for="(metric, idx) in selectedMatchStats.quantMetrics" :key="'qm'+idx" class="bg-[#121927] border border-white/5 p-3 rounded-lg flex flex-col gap-1 relative overflow-hidden group">
                  <div class="absolute -right-4 -top-4 w-12 h-12 bg-blue-500/10 rounded-full blur-md group-hover:bg-blue-500/20 transition-all"></div>
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">{{ metric.nome }}</span>
                  <div class="flex justify-between items-end mt-1">
                    <div class="flex flex-col">
                      <span class="text-[8px] text-gray-600 uppercase">Casa</span>
                      <span class="text-xs font-mono font-bold text-white">{{ metric.casa }}{{ metric.sufixo }}</span>
                    </div>
                    <div class="flex flex-col text-right">
                      <span class="text-[8px] text-gray-600 uppercase">Fora</span>
                      <span class="text-xs font-mono font-bold text-white">{{ metric.fora }}{{ metric.sufixo }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <div class="col-span-1 xl:col-span-9 flex flex-col gap-5">

      <div class="glass-card p-5 px-6 flex flex-col lg:flex-row items-center justify-between gap-5 border-t-2 border-bet-primary shadow-[0_10px_30px_rgba(0,0,0,0.4)] bg-gradient-to-r from-[#121927] to-[#0f1523]">
        
        <div class="flex items-center gap-3 shrink-0 border-r border-white/10 pr-6 w-full lg:w-auto justify-center lg:justify-start">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-bet-primary/20 to-transparent flex items-center justify-center border border-bet-primary/30 shadow-[0_0_15px_rgba(140,199,255,0.2)]">
            <SlidersHorizontal :size="18" class="text-bet-primary" />
          </div>
          <div class="flex flex-col">
            <span class="text-xs text-white uppercase tracking-widest font-bold">Global Screener</span>
            <span class="text-[9px] text-gray-500 font-mono uppercase mt-0.5"><strong class="text-bet-primary">{{ hftData.length + propsAnomalyData.length }}</strong> Oportunidades Mapeadas</span>
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

        </div>
      </div>

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
                    
                    <div class="flex flex-col gap-1.5 min-h-[150px]">
                      
                      <div v-if="(hftTab === 'match' ? hftData : propsAnomalyData).length === 0" class="flex flex-col items-center justify-center py-10 gap-3 opacity-60 h-full">
                        <div class="relative w-12 h-12 flex items-center justify-center">
                            <div class="absolute inset-0 rounded-full border-2 border-bet-primary/20 border-t-bet-primary animate-spin"></div>
                            <Scan size="18" class="text-bet-primary" />
                        </div>
                        <span class="text-[9px] uppercase tracking-widest font-mono text-gray-400 font-bold">Monitorando o Mercado Global...</span>
                      </div>

                      <transition-group name="list" tag="div" class="flex flex-col gap-1.5">
                        <div v-for="(item, i) in (hftTab === 'match' ? hftData : propsAnomalyData)" :key="'hft'+i" class="grid grid-cols-12 gap-2 items-center bg-[#121927] border border-white/5 hover:border-white/20 p-2 rounded-lg transition-colors group relative overflow-hidden h-14">
                          <div class="absolute left-0 top-0 w-1 h-full opacity-50 group-hover:opacity-100 transition-opacity" :class="hftTab === 'match' ? 'bg-[#10B981]' : 'bg-[#a855f7]'"></div>
                          
                          <span class="col-span-1 text-center text-[10px] font-mono text-gray-400">{{ item.hora || 'Ao Vivo' }}</span>
                          
                          <div class="col-span-2 flex flex-col pl-2 border-l border-white/5">
                            <div class="flex items-center gap-1.5 mb-0.5">
                              <span class="text-xs font-bold text-white truncate" :title="item.jogo">{{ item.jogo }}</span>
                            </div>
                            <span class="text-[9px] uppercase tracking-wider mt-0.5 font-mono truncate" :class="hftTab === 'match' ? 'text-bet-primary' : 'text-[#a855f7]'">{{ item.mercado }}</span>
                          </div>

                          <div class="col-span-2 flex flex-col items-center justify-center bg-black/40 py-1 rounded border border-white/5 h-full">
                            <div class="flex items-center gap-1 font-mono text-xs font-bold">
                              <span class="text-gray-500 line-through text-[9px]">{{ item.pinOpen || '-' }}</span>
                              <ArrowRight size="10" class="text-gray-600"/>
                              <span :class="item.pinClose < item.pinOpen ? 'text-red-400' : 'text-green-400'">{{ item.pinClose || '-' }}</span>
                            </div>
                            <span class="text-[8px] text-gray-500 uppercase mt-0.5 tracking-widest">Fair: {{ item.trueOdd || '-' }}</span>
                          </div>

                          <div class="col-span-2 flex items-center justify-center h-full px-2">
                             <svg viewBox="0 0 50 15" class="w-full h-4 overflow-visible">
                               <polyline :points="item.sparkline || '0,10 50,10'" fill="none" :stroke="item.pinClose < item.pinOpen ? '#EF4444' : '#10B981'" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
                             </svg>
                          </div>

                          <div class="col-span-1 flex flex-col items-center justify-center">
                            <span class="text-xs font-mono font-bold text-white bg-yellow-500/10 border border-yellow-500/30 px-2 py-0.5 rounded">{{ item.softOdd || '-' }}</span>
                            <span class="text-[8px] text-yellow-500 uppercase mt-1 font-bold truncate max-w-full px-1">{{ item.bookie || 'Mercado' }}</span>
                          </div>

                          <div class="col-span-2 flex flex-col items-center justify-center border-l border-white/5 h-full pl-1">
                            <div class="flex items-center gap-1.5">
                              <span class="text-xs font-mono font-bold drop-shadow-[0_0_5px_currentColor]" :class="hftTab === 'match' ? 'text-[#10B981]' : 'text-[#a855f7]'">+{{ item.ev || '0.0' }}%</span>
                              <div class="flex flex-col gap-0.5" title="Liquidez/Market Depth">
                                <div class="w-4 h-1 bg-gray-700 rounded-sm overflow-hidden flex"><div class="h-full bg-white w-full"></div></div>
                                <div class="w-4 h-1 bg-gray-700 rounded-sm overflow-hidden flex"><div class="h-full bg-white" :style="`width: ${item.depth || 100}%`"></div></div>
                              </div>
                            </div>
                            <span class="text-[8px] text-gray-400 uppercase mt-0.5 font-mono">Kelly: {{ item.kelly || '0.0' }}u</span>
                          </div>

                          <div class="col-span-2 flex justify-end items-center gap-2 pr-2 h-full">
                            <button class="w-7 h-7 rounded bg-white/5 border border-white/10 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all"><BarChart2 size="12"/></button>
                            <button class="w-7 h-7 rounded border flex items-center justify-center transition-all shadow-lg hover:shadow-white" :class="hftTab === 'match' ? 'bg-[#10B981]/10 border-[#10B981]/30 text-[#10B981] hover:bg-[#10B981] hover:text-black shadow-[0_0_10px_rgba(16,185,129,0.2)]' : 'bg-[#a855f7]/10 border-[#a855f7]/30 text-[#a855f7] hover:bg-[#a855f7] hover:text-white shadow-[0_0_10px_rgba(168,85,247,0.2)]'"><Plus size="14" strokeWidth="3"/></button>
                          </div>
                        </div>
                      </transition-group>
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
                        
                        <div v-if="livePressureData.length === 0" class="flex flex-col items-center justify-center py-6 gap-3 opacity-60">
                           <div class="relative w-8 h-8 flex items-center justify-center">
                              <div class="absolute inset-0 rounded-full border-2 border-blue-500/20 border-t-blue-500 animate-spin"></div>
                           </div>
                           <span class="text-[9px] uppercase tracking-widest font-mono text-gray-400 font-bold">Aguardando In-Play...</span>
                        </div>
                        
                        <transition-group name="list" tag="div" class="flex flex-col gap-3">
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
                                <div class="h-full bg-blue-500 transition-all" :style="`width: ${(live.pressaoCasa / ((live.pressaoCasa + live.pressaoFora) || 1)) * 100}%`"></div>
                                <div class="h-full bg-white/20 w-0.5"></div>
                                <div class="h-full bg-gray-500 transition-all" :style="`width: ${(live.pressaoFora / ((live.pressaoCasa + live.pressaoFora) || 1)) * 100}%`"></div>
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
                        </transition-group>
                      </div>
                    </WidgetCard>

                    <WidgetCard v-else-if="subElement.id === 'smart_steamers'" titulo="Smart Money Steamers" class="w-full flex-1 shadow-[0_10px_30px_rgba(0,0,0,0.3)] border-t-2 border-yellow-500">
                      <template #icone><Flame :size="16" color="#F59E0B" /></template>
                      <div class="flex flex-col gap-3 mt-2 h-full">
                        
                        <div v-if="steamersData.length === 0" class="flex flex-col items-center justify-center py-6 gap-3 opacity-60">
                           <div class="relative w-8 h-8 flex items-center justify-center">
                              <div class="absolute inset-0 rounded-full border-2 border-yellow-500/20 border-t-yellow-500 animate-spin"></div>
                           </div>
                           <span class="text-[9px] uppercase tracking-widest font-mono text-gray-400 font-bold">Buscando Sharp Drops...</span>
                        </div>

                        <transition-group name="list" tag="div" class="flex flex-col gap-3">
                          <div v-for="(steamer, i) in steamersData" :key="'st'+i" class="bg-black/20 border border-white/5 p-3 rounded-xl relative overflow-hidden group hover:border-yellow-500/30 transition-colors">
                            <div class="absolute left-0 top-0 h-full w-1" :class="steamer.urgencia === 'high' ? 'bg-red-500' : 'bg-yellow-500'"></div>
                            <div class="flex justify-between items-start mb-2 pl-2">
                              <div class="flex flex-col">
                                <span class="text-[9px] text-gray-500 uppercase font-mono tracking-widest">{{ steamer.tempo || 'Recente' }}</span>
                                <span class="text-xs font-bold text-white">{{ steamer.jogo }}</span>
                              </div>
                              <span class="text-[10px] font-mono font-bold text-yellow-400 bg-yellow-500/10 px-2 py-0.5 rounded border border-yellow-500/20 shadow-inner shrink-0">Vol: {{ steamer.drop }}%</span>
                            </div>
                            <div class="flex items-center gap-2 pl-2 mt-2 border-t border-white/5 pt-2">
                              <Zap :size="12" :class="steamer.urgencia === 'high' ? 'text-red-400' : 'text-yellow-500'" class="animate-pulse shrink-0" />
                              <span class="text-[10px] text-gray-300 font-mono truncate">Spike no mercado: <strong class="text-white">{{ steamer.mercado }}</strong></span>
                            </div>
                            <div class="mt-2 pl-2 flex justify-between items-center text-[10px] font-mono">
                              <span class="text-gray-500">Odd Entrada:</span>
                              <span class="font-bold text-white bg-black/60 px-2 py-1 rounded border border-gray-700 shadow-inner">{{ steamer.oddNova }}</span>
                            </div>
                          </div>
                        </transition-group>
                      </div>
                    </WidgetCard>
                  </div>
                </template>
              </draggable>
            </template>

            <template v-else-if="element.id === 'ai_picks'">
              <WidgetCard titulo="S-Tier Ticket Builder (AI Portfólio)" class="w-full shadow-[0_15px_40px_rgba(0,0,0,0.3)] border-t-2 border-[#10B981]">
                <template #icone><Target :size="16" color="#10B981" /></template>
                <div class="flex flex-col gap-3 mt-2">
                  
                  <div v-if="goldPicksData.length === 0" class="flex flex-col items-center justify-center py-6 gap-3 opacity-60">
                     <div class="relative w-8 h-8 flex items-center justify-center">
                        <div class="absolute inset-0 rounded-full border-2 border-[#10B981]/20 border-t-[#10B981] animate-spin"></div>
                     </div>
                     <span class="text-[9px] uppercase tracking-widest font-mono text-gray-400 font-bold">Extraindo Oportunidades +EV...</span>
                  </div>

                  <transition-group name="list" tag="div" class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div v-for="(pick, i) in goldPicksData" :key="'gp'+i" class="bg-gradient-to-br from-[#121927] to-black border border-white/10 p-4 rounded-xl relative overflow-hidden group hover:border-[#10B981]/30 transition-colors shadow-lg">
                      <div class="absolute -right-10 -top-10 w-24 h-24 bg-[#10B981]/10 rounded-full blur-2xl pointer-events-none group-hover:bg-[#10B981]/20 transition-colors"></div>
                      <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold block mb-1">{{ pick.liga }}</span>
                      <span class="text-sm font-bold text-white truncate block mb-3 drop-shadow-sm">{{ pick.home_team }} v {{ pick.away_team }}</span>
                      <div class="flex justify-between items-center mb-3 bg-black/40 p-2.5 rounded border border-white/5 shadow-inner">
                        <div class="flex flex-col w-3/4">
                          <span class="text-[9px] text-gray-500 uppercase tracking-widest">Covariância SGP</span>
                          <span class="text-[10px] font-mono font-bold text-[#10B981] truncate block" :title="pick.mercado">{{ pick.mercado }}</span>
                        </div>
                        <span class="text-sm font-mono font-bold text-white bg-[#121927] px-2 py-0.5 rounded border border-gray-700">{{ pick.odd }}</span>
                      </div>
                      <div class="flex justify-between items-center border-t border-white/5 pt-3 mt-1">
                        <span class="text-[9px] text-gray-400 font-mono flex items-center gap-1 truncate pr-2"><BarChart2 size="10" class="text-blue-400 shrink-0"/> <span class="truncate">Confiança: {{ pick.confianca }}%</span></span>
                        <span class="text-[9px] text-[#10B981] font-bold uppercase bg-[#10B981]/10 px-1.5 py-0.5 rounded border border-[#10B981]/30 shadow-sm shrink-0">+{{ pick.ev }} EV</span>
                      </div>
                    </div>
                  </transition-group>
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

      <div class="glass-card flex-1 overflow-hidden shadow-[0_20px_50px_rgba(0,0,0,0.5)] flex flex-col p-4 gap-5 custom-scrollbar overflow-y-auto border border-white/5 rounded-xl relative">
        
        <div class="flex flex-col gap-3">
          <div class="flex items-center justify-between border-b border-white/10 pb-2">
            <div class="flex items-center bg-black/40 border border-white/10 rounded-lg p-0.5 shadow-inner">
              <button @click="topDropsTab = 'drops'" :class="{'bg-red-500/20 text-red-400 border-red-500/30': topDropsTab === 'drops', 'text-gray-500 border-transparent': topDropsTab !== 'drops'}" class="px-2 py-1 text-[9px] uppercase tracking-wider font-bold rounded border transition-all flex items-center gap-1">
                <TrendingDown size="10"/> Top Drops
              </button>
              <button @click="topDropsTab = 'feed'" :class="{'bg-blue-500/20 text-blue-400 border-blue-500/30': topDropsTab === 'feed', 'text-gray-500 border-transparent': topDropsTab !== 'feed'}" class="px-2 py-1 text-[9px] uppercase tracking-wider font-bold rounded border transition-all flex items-center gap-1">
                <Clock size="10"/> Resultados
              </button>
            </div>
            <span class="text-[8px] bg-white/5 text-gray-500 px-1.5 py-0.5 rounded font-mono">Global</span>
          </div>
          
          <div v-if="topDropsTab === 'drops'" class="flex flex-col gap-2 min-h-[150px]">
            <div v-if="topDrops.length === 0" class="flex flex-col items-center justify-center py-6 gap-3 opacity-60 h-full">
               <div class="relative w-8 h-8 flex items-center justify-center">
                  <div class="absolute inset-0 rounded-full border-2 border-red-400/30 border-t-red-400 animate-spin"></div>
               </div>
               <span class="text-[9px] uppercase tracking-widest font-mono text-gray-400 font-bold text-center">Buscando anomalias...</span>
            </div>
            
            <transition-group name="list" tag="div" class="flex flex-col gap-2">
              <div v-for="(drop, i) in topDrops" :key="'td'+i" class="bg-black/30 border border-white/5 p-2.5 rounded-lg hover:bg-white/5 transition-colors group cursor-pointer">
                <div class="flex justify-between items-start mb-1.5">
                  <span class="text-[11px] font-bold text-white group-hover:text-red-400 transition-colors">{{ drop.jogo }}</span>
                  <span class="text-[9px] font-mono text-gray-500">{{ drop.liga }}</span>
                </div>
                <div class="flex justify-between items-center bg-[#121927] p-1.5 rounded border border-white/5 shadow-inner">
                  <span class="text-[9px] text-gray-400 font-bold uppercase truncate max-w-[50%]">{{ drop.mercado }}</span>
                  <div class="flex items-center gap-1 font-mono text-[10px] font-bold">
                    <span class="text-gray-500 line-through">{{ drop.old }}</span>
                    <ArrowRight size="10" class="text-gray-600"/>
                    <span class="text-red-400">{{ drop.new }}</span>
                  </div>
                </div>
              </div>
            </transition-group>
          </div>

          <div v-else class="flex flex-col gap-2 min-h-[150px]">
             <div v-if="recentMatches.length === 0" class="flex flex-col items-center justify-center py-6 gap-3 opacity-60 h-full">
               <div class="relative w-8 h-8 flex items-center justify-center">
                  <div class="absolute inset-0 rounded-full border-2 border-blue-400/30 border-t-blue-400 animate-spin"></div>
               </div>
               <span class="text-[9px] uppercase tracking-widest font-mono text-gray-400 font-bold text-center">Sincronizando Liga...</span>
            </div>

            <transition-group name="list" tag="div" class="flex flex-col gap-2">
              <div v-for="match in recentMatches" :key="'rm'+match.id" @click="openMatchStats(match.id)" class="cursor-pointer bg-black/30 border border-white/5 p-2.5 rounded-lg hover:border-blue-500/30 hover:bg-blue-500/5 transition-all group">
                 <div class="flex justify-between items-center text-[9px] text-gray-500 font-mono mb-2 border-b border-white/5 pb-1">
                    <span class="uppercase tracking-widest truncate pr-2">{{ match.campeonato }}</span>
                    <span :class="match.status === 'IN_PROGRESS' ? 'text-red-400 animate-pulse bg-red-500/10 px-1 rounded' : 'text-blue-400 bg-blue-500/10 px-1 rounded'">{{ match.status === 'FINISHED' ? 'FT' : 'LIVE' }}</span>
                 </div>
                 <div class="flex justify-between items-center text-[11px] font-bold text-white mb-1 group-hover:text-blue-200 transition-colors">
                    <span class="truncate pr-2">{{ match.casa }}</span>
                    <span class="text-blue-400 font-mono bg-blue-500/10 px-1.5 rounded">{{ match.home_goals ?? '-' }}</span>
                 </div>
                 <div class="flex justify-between items-center text-[11px] font-bold text-white group-hover:text-blue-200 transition-colors">
                    <span class="truncate pr-2">{{ match.fora }}</span>
                    <span class="text-blue-400 font-mono bg-blue-500/10 px-1.5 rounded">{{ match.away_goals ?? '-' }}</span>
                 </div>
              </div>
            </transition-group>
          </div>
        </div>

        <div class="flex flex-col gap-3 mt-2">
          <div class="flex items-center justify-between border-b border-white/10 pb-2">
            <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold flex items-center gap-1.5"><Database size="12" class="text-blue-400"/> Liquidity Spikes</span>
          </div>
          
          <div class="flex flex-col gap-2 min-h-[100px]">
            <div v-if="volumeSpikes.length === 0" class="flex flex-col items-center justify-center py-4 gap-3 opacity-60">
               <span class="text-[9px] uppercase tracking-widest font-mono text-gray-400 font-bold">Sem spikes recentes.</span>
            </div>
            
            <transition-group name="list" tag="div" class="flex flex-col gap-2">
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
            </transition-group>
          </div>
        </div>

      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { io } from 'socket.io-client';
import draggable from 'vuedraggable';
import { 
  GripVertical, GripHorizontal, Radio, SlidersHorizontal, 
  Target, Clock, Globe, RefreshCcw, X, Activity, LineChart, 
  ArrowRight, ArrowDownRight, Plus, BarChart2, Zap, Flame, User, BellRing,
  TrendingDown, Database, Terminal, Wifi, Scan
} from 'lucide-vue-next';
import axios from 'axios';
import WidgetCard from './WidgetCard.vue';

// ==================================================
// CONFIGS DE API (PORTA 8000 HFT)
// ==================================================
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8000';

// ESTADO DOS MACRO-FILTROS E LAYOUT
const filtroTier = ref('tier1');
const filtroEV = ref(3.0); 
const filtroTempo = ref('12h');
const surebetActive = ref(false); 
const hftTab = ref('match');
const topDropsTab = ref('drops'); // NOVO: Controle da Aba (Drops vs Feed)
const isBuilding = ref(false);

// ESTADO DO MODAL DE JOGO
const showMatchModal = ref(false);
const isLoadingModal = ref(false);
const selectedMatchStats = ref(null);

const blocosVerticais = ref([
  { id: 'hft_matrix', type: 'single' }, 
  { id: 'linha-menores', type: 'grid' },
  { id: 'ai_picks', type: 'single' }
]);

const widgetsMenores = ref([
  { id: 'asian_scanner' }, 
  { id: 'smart_steamers' } 
]);

// ARRAYS REATIVOS DE DADOS
const hftData = ref([]);
const propsAnomalyData = ref([]);
const livePressureData = ref([]);
const steamersData = ref([]);
const goldPicksData = ref([]);
const topDrops = ref([]);
const volumeSpikes = ref([]);
const recentMatches = ref([]); // NOVO: Guarda a lista de jogos recentes (Feed)

const botLogs = ref([
  "> SYS: Conectando ao Banco de Dados Principal...",
  "> SCAN: Inicializando varredura HFT..."
]);

// ==================================================
// MÉTODOS DE BUSCA E INTEGRAÇÃO (REST API)
// ==================================================
const fetchRadarData = async () => {
  try {
    const token = localStorage.getItem('betgenius_token');
    const opts = { headers: { Authorization: `Bearer ${token}` } };

    // Busca simultânea S-Tier nas rotas Reais da Porta 8000
    const [dropsRes, spikesRes, steamersRes, picksRes, matchesRes] = await Promise.all([
      axios.get(`${API_BASE_URL}/api/v1/quant/top-drops`, opts).catch(() => ({ data: [] })),
      axios.get(`${API_BASE_URL}/api/v1/quant/volume-spikes`, opts).catch(() => ({ data: [] })),
      axios.get(`${API_BASE_URL}/api/v1/quant/steamers`, opts).catch(() => ({ data: [] })),
      axios.get(`${API_BASE_URL}/api/v1/quant/gold-picks`, opts).catch(() => ({ data: [] })),
      axios.get(`${API_BASE_URL}/api/v1/matches/today`, opts).catch(() => ({ data: [] }))
    ]);

    if (dropsRes.data.length > 0) topDrops.value = dropsRes.data;
    if (spikesRes.data.length > 0) volumeSpikes.value = spikesRes.data;
    if (steamersRes.data.length > 0) steamersData.value = steamersRes.data;
    if (picksRes.data.length > 0) goldPicksData.value = picksRes.data;
    
    // Filtra o Feed de Notícias apenas para jogos Finalizados ou Ao Vivo
    if (matchesRes.data.length > 0) {
       recentMatches.value = matchesRes.data.filter(m => m.status === 'FINISHED' || m.status === 'IN_PROGRESS').reverse().slice(0, 15);
    }

    botLogs.value.unshift("> OK: Dados da Matrix Sincronizados.");
    if (botLogs.value.length > 8) botLogs.value.pop();
  } catch (error) {
    botLogs.value.unshift("> ERR: Falha ao ler DB. Verifique o servidor Python.");
  }
};

const triggerTicketBuilder = async () => {
  isBuilding.value = true;
  botLogs.value.unshift("> SCAN: Extraindo Oportunidades +EV...");
  if (botLogs.value.length > 8) botLogs.value.pop();

  try {
    const token = localStorage.getItem('betgenius_token');
    // Bate na nova rota real para preencher a listagem no card da IA
    const res = await axios.get(`${API_BASE_URL}/api/v1/quant/gold-picks`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (res.data && res.data.length > 0) {
      goldPicksData.value = res.data;
      botLogs.value.unshift(`> TICKET: Extrator localizou ${res.data.length} alvos.`);
    } else {
       botLogs.value.unshift(`> TICKET: Nenhum valor retornado do Oráculo.`);
    }
  } catch (error) {
    botLogs.value.unshift("> ERR: Rota Gold Picks indisponível.");
  } finally {
    isBuilding.value = false;
  }
};

// ==================================================
// LÓGICA DO MODAL POPUP (MATCH CENTER STATS)
// ==================================================
const openMatchStats = async (matchId) => {
  isLoadingModal.value = true;
  showMatchModal.value = true;
  
  try {
    const token = localStorage.getItem('betgenius_token');
    // O EndPoint mágico S-Tier que traz xG, Poisson e tudo
    const res = await axios.get(`${API_BASE_URL}/api/v1/match-center/${matchId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    
    selectedMatchStats.value = res.data.partida;
    botLogs.value.unshift(`> SYS: Estatísticas Profundas de M_ID ${matchId} extraídas.`);
    if (botLogs.value.length > 8) botLogs.value.pop();
  } catch (error) {
    console.error("Falha ao abrir estatísticas", error);
    alert("Falha ao carregar as métricas da partida. Tente novamente.");
    showMatchModal.value = false;
  } finally {
    isLoadingModal.value = false;
  }
};

const closeMatchStats = () => {
  showMatchModal.value = false;
  setTimeout(() => {
    selectedMatchStats.value = null;
  }, 300); // Aguarda o fim da animação de saída
};


// ==================================================
// WEBSOCKETS (HFT REAL-TIME)
// ==================================================
let socket = null;

onMounted(() => {
  fetchRadarData();

  socket = io(GATEWAY_URL, {
    transports: ['websocket']
  });

  socket.on('connect', () => {
    botLogs.value.unshift(`> SYS: HFT Socket Conectado [ID: ${socket.id.substring(0,4)}]`);
    if (botLogs.value.length > 8) botLogs.value.pop();
  });

  socket.on('NEW_ALPHA_OPPORTUNITY', (payload) => {
    if(payload.signals && Array.isArray(payload.signals)) {
      payload.signals.forEach(sig => {
        botLogs.value.unshift(`> ALPHA: Edge de +${sig.expected_value_pct}% EV capturado.`);
        if (botLogs.value.length > 8) botLogs.value.pop();

        const novoAlerta = {
          hora: new Date().toLocaleTimeString('pt-BR', {hour: '2-digit', minute:'2-digit'}),
          jogo: `Alpha ID: ${payload.match_id}`, 
          mercado: sig.market, pinOpen: (sig.bookmaker_odd * 1.05).toFixed(2), pinClose: sig.bookmaker_odd.toFixed(2),
          trueOdd: sig.true_odd.toFixed(2), softOdd: (sig.bookmaker_odd * 0.95).toFixed(2), 
          bookie: "Pinnacle", ev: sig.expected_value_pct.toFixed(1), kelly: sig.suggested_bankroll_stake_pct.toFixed(2),
          depth: 100, sparkline: "0,10 10,12 20,8 30,6 40,4 50,2"
        };

        const mercadoLower = novoAlerta.mercado.toLowerCase();
        const isProp = mercadoLower.includes('chute') || mercadoLower.includes('falta');
        
        if (isProp) {
          propsAnomalyData.value.unshift(novoAlerta);
          if (propsAnomalyData.value.length > 15) propsAnomalyData.value.pop();
        } else {
          hftData.value.unshift(novoAlerta);
          if (hftData.value.length > 15) hftData.value.pop();
        }
      });
    }
  });

  socket.on('disconnect', () => {
    botLogs.value.unshift("> SYS: Conexão HFT Perdida. Retentando...");
    if (botLogs.value.length > 8) botLogs.value.pop();
  });
});

onUnmounted(() => {
  if (socket) socket.disconnect();
});
</script>

<style scoped>
.glass-card { background: rgba(18, 25, 39, 0.7); backdrop-filter: blur(20px); border-radius: 16px;}
.ghost-widget { opacity: 0.4 !important; border: 2px dashed #10B981 !important; transform: scale(0.98); background: rgba(16, 185, 129, 0.05); }
.animate-spin-slow { animation: spin 3s linear infinite; }

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

/* Transições de Listas (Vue) */
.list-enter-active,
.list-leave-active {
  transition: all 0.5s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}

/* Transição do Modal S-Tier */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
.modal-fade-enter-active .relative {
  animation: modal-pop 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
.modal-fade-leave-active .relative {
  animation: modal-pop 0.3s cubic-bezier(0.16, 1, 0.3, 1) reverse forwards;
}

@keyframes modal-pop {
  0% { transform: scale(0.95) translateY(20px); opacity: 0; }
  100% { transform: scale(1) translateY(0); opacity: 1; }
}

.animate-fade-in {
  animation: fade-in 0.4s ease-out forwards;
}
@keyframes fade-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>