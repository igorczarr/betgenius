<template>
  <div class="flex flex-col gap-6 w-full h-full relative fade-in-up pb-30">
    
    <div class="glass-card p-6 md:p-8 relative flex flex-col md:flex-row justify-between items-center border-t-4 shadow-[0_15px_40px_rgba(0,0,0,0.6)] transition-all duration-500" :style="`border-color: ${partida.corCasa}`">
      <div class="absolute -right-20 -top-20 w-72 h-72 rounded-full blur-[100px] pointer-events-none opacity-20 transition-colors duration-500" :style="`background-color: ${partida.corCasa}`"></div>
      <div class="absolute -left-20 -bottom-20 w-72 h-72 rounded-full blur-[100px] pointer-events-none opacity-20 transition-colors duration-500" :style="`background-color: ${partida.corFora}`"></div>
      
      <div class="flex items-center gap-5 w-full md:w-2/5 justify-end z-10">
        <div class="text-right">
          <h2 class="text-3xl font-mono text-white tracking-wider drop-shadow-md">{{ partida.casa }}</h2>
          <div class="flex items-center justify-end gap-2 mt-1" v-if="!isLoading">
            <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold">{{ partida.posCasa }}º Lugar •</span>
            <div class="flex gap-0.5">
              <span v-for="(f, i) in partida.formCasa" :key="'fc'+i" class="w-4 h-4 flex items-center justify-center rounded-[3px] text-[8px] font-bold text-white shadow-sm" :class="f === 'W' ? 'bg-[#10B981]' : (f === 'D' ? 'bg-gray-500' : 'bg-red-500')">{{ f }}</span>
            </div>
          </div>
        </div>
        <div class="w-20 h-20 rounded-full bg-[#121927] border-[3px] flex items-center justify-center shadow-[0_0_25px_rgba(0,0,0,0.8)] relative overflow-hidden transition-colors duration-500" :style="`border-color: ${partida.corCasa}`">
          <img v-if="partida.casa !== '---'" :src="getTeamLogo(partida.casa)" @error="handleImageError" class="w-12 h-12 object-contain drop-shadow-[0_0_8px_currentColor]" />
          <Shield v-else :size="36" color="#4B5563" class="drop-shadow-[0_0_8px_currentColor]" />
        </div>
      </div>

      <div class="flex flex-col items-center justify-center w-full md:w-1/5 my-6 md:my-0 z-10">
        <div v-if="partida.isLive" class="bg-red-500/20 text-red-400 px-4 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-widest mb-2 flex items-center gap-2 border border-red-500/30 shadow-[0_0_15px_rgba(239,68,68,0.3)] backdrop-blur-sm">
          <div class="w-2 h-2 bg-red-500 rounded-full animate-pulse shadow-[0_0_8px_#EF4444]"></div> {{ partida.tempo }}' (Ao Vivo)
        </div>
        <div v-else class="bg-bet-primary/10 text-bet-primary px-4 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-widest mb-2 border border-bet-primary/30 backdrop-blur-sm">
          Pré-Jogo • {{ partida.hora }}
        </div>
        
        <div class="text-6xl font-mono font-bold text-white tracking-widest drop-shadow-[0_5px_15px_rgba(0,0,0,0.8)] flex items-center gap-5 my-1">
          <span>{{ partida.placarCasa }}</span>
          <span class="text-gray-600 text-4xl pb-2 font-light">-</span>
          <span>{{ partida.placarFora }}</span>
        </div>
        
        <div class="mt-2 bg-black/60 px-5 py-1.5 rounded-full border border-white/10 flex items-center gap-3 shadow-inner">
          <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold">xG HT</span>
          <span class="text-sm font-mono text-bet-primary font-bold drop-shadow-[0_0_5px_rgba(140,199,255,0.4)]">{{ partida.xgCasa }} <span class="text-gray-600 text-xs mx-1">-</span> {{ partida.xgFora }}</span>
        </div>
      </div>

      <div class="flex items-center gap-5 w-full md:w-2/5 justify-start z-10">
        <div class="w-20 h-20 rounded-full bg-[#121927] border-[3px] flex items-center justify-center shadow-[0_0_25px_rgba(0,0,0,0.8)] relative overflow-hidden transition-colors duration-500" :style="`border-color: ${partida.corFora}`">
          <img v-if="partida.fora !== '---'" :src="getTeamLogo(partida.fora)" @error="handleImageError" class="w-12 h-12 object-contain drop-shadow-[0_0_8px_currentColor]" />
          <ShieldAlert v-else :size="36" color="#4B5563" class="drop-shadow-[0_0_8px_currentColor]" />
        </div>
        <div class="text-left">
          <h2 class="text-3xl font-mono text-white tracking-wider drop-shadow-md">{{ partida.fora }}</h2>
          <div class="flex items-center justify-start gap-2 mt-1" v-if="!isLoading">
            <div class="flex gap-0.5">
              <span v-for="(f, i) in partida.formFora" :key="'ff'+i" class="w-4 h-4 flex items-center justify-center rounded-[3px] text-[8px] font-bold text-white shadow-sm" :class="f === 'W' ? 'bg-[#10B981]' : (f === 'D' ? 'bg-gray-500' : 'bg-red-500')">{{ f }}</span>
            </div>
            <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold">• {{ partida.posFora }}º Lugar</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="isLoading" class="grid grid-cols-1 lg:grid-cols-12 gap-5 mt-2">
      <div class="col-span-1 lg:col-span-5 h-[460px] skeleton-pulse rounded-2xl border border-white/5 shadow-lg"></div>
      <div class="col-span-1 lg:col-span-4 h-[460px] skeleton-pulse rounded-2xl border border-white/5 shadow-lg"></div>
      <div class="col-span-1 lg:col-span-3 h-[460px] skeleton-pulse rounded-2xl border border-white/5 shadow-lg"></div>
    </div>

    <draggable 
      v-else
      v-model="layoutWidgets" 
      item-key="id" 
      class="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start mt-2" 
      handle=".drag-handle" 
      ghost-class="ghost-widget"
      animation="250"
    >
      <template #item="{ element }">
        <div :class="element.span" class="relative w-full group/widget h-[460px] bg-[#121927] rounded-2xl border border-white/5 shadow-xl flex flex-col overflow-hidden">
          
          <div class="drag-handle absolute top-0 left-1/2 -translate-x-1/2 z-[80] opacity-0 group-hover/widget:opacity-100 cursor-move py-1 px-6 bg-black/80 text-gray-400 rounded-b-lg border-x border-b border-white/10 transition-all hover:bg-[#10B981] hover:text-black hover:border-[#10B981]">
            <GripHorizontal size="14" />
          </div>

          <WidgetCard v-if="element.id === 'contexto'" titulo="Overview & Head-to-Head" class="h-full flex flex-col">
            <template #icone><History :size="16" class="text-[#10B981]" /></template>
            <template #acoes>
              <div class="flex items-center gap-2">
                <button @click="contextTab = 'stats'" class="text-[9px] font-bold uppercase tracking-widest px-2 py-1 rounded transition-colors" :class="contextTab === 'stats' ? 'bg-[#10B981]/20 text-[#10B981]' : 'text-gray-500 hover:text-white'">Stats</button>
                <button @click="contextTab = 'h2h'" class="text-[9px] font-bold uppercase tracking-widest px-2 py-1 rounded transition-colors" :class="contextTab === 'h2h' ? 'bg-[#10B981]/20 text-[#10B981]' : 'text-gray-500 hover:text-white'">H2H</button>
                <div class="w-px h-3 bg-white/20 mx-1"></div>
                <select v-model="filtroJogosH2H" class="bg-black/60 text-[9px] text-white border border-gray-700 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-[#10B981] transition-colors">
                  <option value="5">Últimos 5</option>
                  <option value="10">Últimos 10</option>
                  <option value="15">Últimos 15</option>
                </select>
              </div>
            </template>
            
            <div class="flex flex-col h-full mt-3 overflow-hidden">
              <transition name="fade" mode="out-in">
                <div v-if="contextTab === 'stats'" class="flex flex-col h-full">
                  <div class="grid grid-cols-3 bg-black/60 p-2.5 text-[9px] uppercase tracking-widest text-gray-500 font-bold text-center border border-white/10 rounded-t-lg shrink-0">
                    <span class="text-left text-white truncate px-2" :style="`color: ${partida.corCasa || '#10B981'}`">{{ partida.casa }}</span>
                    <span>Radar ({{ filtroJogosH2H }}J)</span>
                    <span class="text-right text-white truncate px-2" :style="`color: ${partida.corFora || '#3B82F6'}`">{{ partida.fora }}</span>
                  </div>
                  <div class="flex flex-col text-xs font-mono text-gray-300 border border-t-0 border-white/10 rounded-b-lg bg-black/20 flex-1 justify-around py-2">
                    <div class="grid grid-cols-3 px-4 py-2 border-b border-white/5 hover:bg-white/5"><span class="font-bold">{{ calcStats.casa.pts }} <span class="text-[9px] text-gray-500">({{ calcStats.casa.j }})</span></span><span class="text-center text-[9px] text-gray-500 font-sans tracking-widest uppercase">PTS / J</span><span class="text-right font-bold">{{ calcStats.fora.pts }} <span class="text-[9px] text-gray-500">({{ calcStats.fora.j }})</span></span></div>
                    <div class="grid grid-cols-3 px-4 py-2 border-b border-white/5 hover:bg-white/5"><span>{{ calcStats.casa.win }}%</span><span class="text-center text-[9px] text-gray-500 font-sans tracking-widest uppercase">Win Rate</span><span class="text-right">{{ calcStats.fora.win }}%</span></div>
                    <div class="grid grid-cols-3 px-4 py-2 border-b border-white/5 hover:bg-white/5"><span>{{ calcStats.casa.avg_gf }} <span class="text-gray-600">/</span> {{ calcStats.casa.avg_gc }}</span><span class="text-center text-[9px] text-gray-500 font-sans tracking-widest uppercase">Gols F/S</span><span class="text-right">{{ calcStats.fora.avg_gf }} <span class="text-gray-600">/</span> {{ calcStats.fora.avg_gc }}</span></div>
                    <div class="grid grid-cols-3 px-4 py-2 border-b border-white/5 hover:bg-white/5"><span class="text-[#10B981] font-bold">{{ calcStats.casa.over }}%</span><span class="text-center text-[9px] text-gray-500 font-sans tracking-widest uppercase">Over 2.5</span><span class="text-right text-[#10B981] font-bold">{{ calcStats.fora.over }}%</span></div>
                    <div class="grid grid-cols-3 px-4 py-2 hover:bg-white/5"><span>{{ calcStats.casa.btts }}%</span><span class="text-center text-[9px] text-gray-500 font-sans tracking-widest uppercase">BTTS</span><span class="text-right">{{ calcStats.fora.btts }}%</span></div>
                  </div>
                  <div class="grid grid-cols-2 gap-3 mt-3 shrink-0">
                    <div class="bg-[#121927] border border-white/5 p-3 rounded-xl flex flex-col gap-1 shadow-inner group">
                      <div class="flex items-center gap-2 mb-1"><Gavel size="12" class="text-yellow-500"/><span class="text-[9px] font-bold text-gray-400 uppercase tracking-widest truncate">Média Cartões (H)</span></div>
                      <div class="flex justify-between font-mono text-[11px] text-white"><span>Y: <strong class="text-yellow-400">{{ partida.disciplina?.h_y || '-' }}</strong></span><span>R: <strong class="text-red-400">{{ partida.disciplina?.h_r || '-' }}</strong></span></div>
                    </div>
                    <div class="bg-[#121927] border border-white/5 p-3 rounded-xl flex flex-col gap-1 shadow-inner group">
                      <div class="flex items-center gap-2 mb-1"><Gavel size="12" class="text-yellow-500"/><span class="text-[9px] font-bold text-gray-400 uppercase tracking-widest truncate">Média Cartões (A)</span></div>
                      <div class="flex justify-between font-mono text-[11px] text-white"><span>Y: <strong class="text-yellow-400">{{ partida.disciplina?.a_y || '-' }}</strong></span><span>R: <strong class="text-red-400">{{ partida.disciplina?.a_r || '-' }}</strong></span></div>
                    </div>
                  </div>
                </div>

                <div v-else class="flex flex-col h-full border border-white/5 rounded-xl overflow-hidden bg-black/10 shadow-sm">
                  <div class="flex-1 overflow-y-auto custom-scrollbar">
                    <div v-for="(h2h, i) in historicoFiltrado" :key="'h2h'+i" class="flex justify-between items-center p-3 text-xs font-mono even:bg-white/[0.02] hover:bg-white/5 transition-colors border-b border-white/5 last:border-0 group">
                      <span class="text-gray-500 w-16 text-[9px] uppercase">{{ h2h.data }}</span>
                      <span class="flex-1 text-right truncate pr-3 transition-colors" :class="h2h.win === 'casa' ? 'text-white font-bold' : 'text-gray-400'">{{ h2h.casa }}</span>
                      <span class="bg-[#121927] px-3 py-1 rounded text-white font-bold border border-gray-700 shadow-inner tracking-widest min-w-[45px] text-center">{{ h2h.placar }}</span>
                      <span class="flex-1 text-left truncate pl-3 transition-colors" :class="h2h.win === 'fora' ? 'text-white font-bold' : 'text-gray-400'">{{ h2h.fora }}</span>
                    </div>
                    <div v-if="historicoFiltrado.length === 0" class="text-center text-xs text-gray-500 py-10 font-mono uppercase tracking-widest flex items-center justify-center h-full">Sem histórico recente</div>
                  </div>
                </div>
              </transition>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'forma'" titulo="Forma Recente" class="h-full flex flex-col">
            <template #icone><LayoutList :size="16" class="text-[#3B82F6]" /></template>
            <template #acoes>
              <select v-model="filtroJogosForma" class="bg-black/60 text-[9px] text-white border border-gray-700 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-[#3B82F6] transition-colors">
                <option value="5">5 Jogos</option>
                <option value="10">10 Jogos</option>
                <option value="15">15 Jogos</option>
              </select>
            </template>
            
            <div class="flex gap-2 h-full mt-3 overflow-hidden">
              <div class="w-1/2 flex flex-col h-full overflow-y-auto custom-scrollbar pr-1.5">
                <div class="flex items-center justify-between border-b border-white/10 pb-2 mb-2 sticky top-0 bg-[#121927] z-10 shadow-sm">
                  <span :style="`color: ${partida.corCasa || '#10B981'}`" class="text-[10px] md:text-[11px] uppercase font-bold tracking-widest drop-shadow-md truncate flex-1 pr-2">{{ partida.casa }}</span>
                  <span class="bg-white/5 px-1.5 py-0.5 rounded text-[8px] font-bold text-gray-400 shrink-0">CASA</span>
                </div>
                <div class="flex flex-col gap-1.5">
                  <div v-for="(jogo, i) in formaCasaFiltrada" :key="'ih'+i" class="bg-black/20 border border-white/5 p-2.5 rounded-lg flex flex-col gap-1.5 hover:bg-white/5 transition-colors">
                    <div class="flex justify-between items-center text-[9px] font-mono">
                      <span class="text-gray-500">{{ jogo.data }}</span>
                      <span class="font-bold px-1.5 py-0.5 rounded" :class="jogo.res === 'W' ? 'bg-[#10B981]/20 text-[#10B981]' : (jogo.res === 'L' ? 'bg-red-500/20 text-red-400' : 'bg-gray-500/20 text-gray-300')">{{ jogo.res }}</span>
                    </div>
                    <div class="flex justify-between items-center text-[10px]">
                      <span class="text-gray-300 truncate w-[70px]">{{ jogo.adv }}</span>
                      <span class="font-bold font-mono text-white">{{ jogo.placar }}</span>
                    </div>
                  </div>
                  <div v-if="formaCasaFiltrada.length === 0" class="text-center text-[9px] text-gray-500 py-4 font-mono uppercase tracking-widest">S/ Dados</div>
                </div>
              </div>
              
              <div class="w-px bg-white/5 h-full shrink-0"></div>
              
              <div class="w-1/2 flex flex-col h-full overflow-y-auto custom-scrollbar pl-1.5">
                <div class="flex items-center justify-between border-b border-white/10 pb-2 mb-2 sticky top-0 bg-[#121927] z-10 shadow-sm">
                  <span class="bg-white/5 px-1.5 py-0.5 rounded text-[8px] font-bold text-gray-400 shrink-0">FORA</span>
                  <span :style="`color: ${partida.corFora || '#3B82F6'}`" class="text-[10px] md:text-[11px] uppercase font-bold tracking-widest drop-shadow-md truncate flex-1 text-right pl-2">{{ partida.fora }}</span>
                </div>
                <div class="flex flex-col gap-1.5">
                  <div v-for="(jogo, i) in formaForaFiltrada" :key="'ia'+i" class="bg-black/20 border border-white/5 p-2.5 rounded-lg flex flex-col gap-1.5 hover:bg-white/5 transition-colors">
                    <div class="flex justify-between items-center text-[9px] font-mono">
                      <span class="font-bold px-1.5 py-0.5 rounded" :class="jogo.res === 'W' ? 'bg-[#10B981]/20 text-[#10B981]' : (jogo.res === 'L' ? 'bg-red-500/20 text-red-400' : 'bg-gray-500/20 text-gray-300')">{{ jogo.res }}</span>
                      <span class="text-gray-500">{{ jogo.data }}</span>
                    </div>
                    <div class="flex justify-between items-center text-[10px]">
                      <span class="font-bold font-mono text-white">{{ jogo.placar }}</span>
                      <span class="text-gray-300 truncate w-[70px] text-right">{{ jogo.adv }}</span>
                    </div>
                  </div>
                  <div v-if="formaForaFiltrada.length === 0" class="text-center text-[9px] text-gray-500 py-4 font-mono uppercase tracking-widest">S/ Dados</div>
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'ml'" titulo="xG Flow & Poisson" class="h-full flex flex-col">
            <template #icone><Grid :size="16" class="text-orange-400" /></template>
            <template #acoes>
              <button @click="showPoisson = !showPoisson" class="text-[9px] font-bold uppercase tracking-widest px-2 py-1 rounded transition-colors bg-orange-400/10 text-orange-400 border border-orange-400/30 hover:bg-orange-400 hover:text-black">
                <Grid size="10" class="inline mr-1" /> {{ showPoisson ? 'xG Flow' : 'Heatmap' }}
              </button>
            </template>
            
            <div class="flex flex-col h-full mt-3 overflow-hidden relative">
              <transition name="fade" mode="out-in">
                
                <div v-if="!showPoisson" class="flex flex-col h-full w-full">
                  <p class="text-[10px] text-gray-400 mb-2 leading-relaxed px-1 shrink-0">Evolução do <strong class="text-white">Expected Goals (xG)</strong> EWMA.</p>
                  <div class="flex-1 relative w-full bg-[#0b0f19] rounded-xl border border-white/5 overflow-hidden flex items-end pt-4 pr-3 shadow-inner mb-2">
                    <div class="absolute left-2 top-4 text-[9px] font-mono text-gray-600">2.0</div>
                    <div class="absolute left-2 top-1/2 -translate-y-1/2 text-[9px] font-mono text-gray-600">1.0</div>
                    <div class="absolute left-2 bottom-6 text-[9px] font-mono text-gray-600">0.0</div>
                    <div class="absolute left-8 bottom-1 text-[8px] font-mono text-gray-500">0'</div>
                    <div class="absolute left-1/2 bottom-1 text-[8px] font-mono text-gray-500">45'</div>
                    <div class="absolute right-4 bottom-1 text-[8px] font-mono text-gray-500">90'</div>
                    
                    <div class="absolute inset-0 flex flex-col justify-between py-6 px-8 pointer-events-none opacity-20">
                      <div class="w-full h-px bg-gray-600"></div><div class="w-full h-px bg-gray-600"></div><div class="w-full h-px bg-gray-600"></div>
                    </div>
                    
                    <svg viewBox="0 0 100 40" class="w-full h-full overflow-visible preserve-3d px-8 pb-4" preserveAspectRatio="none">
                      <polyline points="0,40 10,38 20,35 30,25 40,24 50,22 60,18 70,12 80,10 90,8 100,5" fill="none" :stroke="partida.corCasa || '#10B981'" stroke-width="2" vector-effect="non-scaling-stroke" />
                      <polyline points="0,40 10,39 20,38 30,36 40,30 50,28 60,25 70,26 80,24 90,20 100,18" fill="none" :stroke="partida.corFora || '#3B82F6'" stroke-width="2" stroke-dasharray="2,2" vector-effect="non-scaling-stroke" />
                    </svg>
                  </div>
                  <div class="flex justify-between items-center mt-1 px-2 shrink-0">
                    <div class="flex items-center gap-2 text-[9px] font-mono text-gray-400 uppercase tracking-widest font-bold"><div class="w-2 h-2 rounded-full" :style="`background: ${partida.corCasa || '#10B981'}`"></div> {{ partida.casa }} (xG)</div>
                    <div class="flex items-center gap-2 text-[9px] font-mono text-gray-400 uppercase tracking-widest font-bold"><div class="w-2 h-2 rounded-full border" :style="`border-color: ${partida.corFora || '#3B82F6'}`"></div> {{ partida.fora }} (xG)</div>
                  </div>
                </div>

                <div v-else class="flex flex-col h-full bg-black/20 rounded-xl border border-white/5 p-3 shadow-inner w-full">
                  <div v-if="!partida.poisson || partida.poisson.length === 0" class="flex-1 flex items-center justify-center text-[10px] font-mono text-gray-500 uppercase tracking-widest">
                    Calculando...
                  </div>
                  <div v-else class="flex flex-col h-full">
                    <div class="flex shrink-0">
                      <div class="w-8"></div>
                      <div class="flex-1 grid grid-cols-4 text-center text-[9px] font-bold text-gray-500 uppercase tracking-widest pb-1.5 border-b border-white/10">
                        <span class="col-span-4 flex items-center justify-center gap-1.5">
                          <div class="w-2 h-2 rounded-full" :style="`background-color: ${partida.corFora || '#3B82F6'}`"></div>
                          {{ partida.fora }} (G)
                        </span>
                      </div>
                    </div>
                    <div class="flex flex-1 mt-1.5">
                      <div class="w-8 flex flex-col justify-center items-center text-[9px] font-bold text-gray-500 uppercase tracking-widest rotate-180 border-r border-white/10 gap-1.5" style="writing-mode: vertical-rl;">
                        <div class="w-2 h-2 rounded-full" :style="`background-color: ${partida.corCasa || '#10B981'}`"></div>
                        {{ partida.casa }} (G)
                      </div>
                      <div class="flex-1 grid grid-cols-4 grid-rows-4 gap-1 pl-1.5">
                        <div v-for="p in partida.poisson" :key="`p${p.h}${p.a}`" class="border rounded-lg flex flex-col items-center justify-center text-[10px] font-mono transition-colors cursor-default" 
                             :class="p.prob > 10 ? 'bg-[#10B981]/20 border-[#10B981]/40 text-white font-bold shadow-[0_0_10px_rgba(16,185,129,0.15)]' : (p.prob > 5 ? 'bg-yellow-500/10 border-yellow-500/20 text-gray-300' : 'bg-black/40 border-white/5 text-gray-500')">
                          <span class="mb-0.5">{{ p.h }}-{{ p.a }}</span>
                          <span class="text-[7px] opacity-80 uppercase tracking-widest">{{ p.prob }}%</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

              </transition>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'mercados_props'" titulo="Value Finder & Props" class="h-full flex flex-col">
            <template #icone><Percent :size="16" class="text-[#3b82f6]" /></template>
            <template #acoes>
              <div class="flex items-center gap-2">
                <button @click="mercadosTab = 'value'" class="text-[9px] font-bold uppercase tracking-widest px-2 py-1 rounded transition-colors" :class="mercadosTab === 'value' ? 'bg-[#3b82f6]/20 text-[#3b82f6]' : 'text-gray-500 hover:text-white'">Mercados</button>
                <button @click="mercadosTab = 'props'" class="text-[9px] font-bold uppercase tracking-widest px-2 py-1 rounded transition-colors" :class="mercadosTab === 'props' ? 'bg-[#3b82f6]/20 text-[#3b82f6]' : 'text-gray-500 hover:text-white'">Props</button>
                <div class="w-px h-3 bg-white/20 mx-1"></div>
                <select v-if="mercadosTab === 'value'" v-model="filtroMercado" class="bg-black/60 text-[9px] text-white border border-gray-700 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-[#3b82f6] transition-colors">
                  <option value="all">Todos (+EV)</option>
                  <option value="match_odds">Match Odds</option>
                  <option value="goals">Gols (O/U)</option>
                  <option value="btts">Ambas Marcam</option>
                  <option value="handicap">Handicap As.</option>
                  <option value="dnb">Draw No Bet</option>
                  <option value="corners">Escanteios</option>
                  <option value="cards">Cartões</option>
                </select>
                <select v-if="mercadosTab === 'props'" v-model="propsTab" class="bg-black/60 text-[9px] text-white border border-gray-700 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-[#3b82f6] transition-colors">
                  <option value="chutes">Chutes no Gol</option>
                  <option value="gols">Gols Marcados</option>
                  <option value="assists">Assistências</option>
                  <option value="faltas">Faltas</option>
                  <option value="escanteios">Team Corners</option>
                  <option value="cartoes">Cartões</option>
                </select>
              </div>
            </template>
            
            <div class="flex flex-col h-full mt-3 overflow-hidden">
              <transition name="fade" mode="out-in">
                <div v-if="mercadosTab === 'value'" class="flex flex-col h-full">
                  <div class="grid grid-cols-12 px-3 pb-2 border-b border-white/10 text-[9px] uppercase font-bold text-gray-500 tracking-widest bg-black/40 rounded-t-lg pt-3 shrink-0">
                    <span class="col-span-5 pl-1">Mercado (Aposta)</span>
                    <span class="col-span-2 text-center">IA Prob</span>
                    <span class="col-span-3 text-center">Odd Move</span>
                    <span class="col-span-2 text-right pr-2">Ação</span>
                  </div>
                  <div class="flex flex-col overflow-y-auto custom-scrollbar flex-1 pb-2 bg-black/10 border border-t-0 border-white/10 rounded-b-lg">
                    <div v-for="(mercado, i) in currentMercados" :key="'m'+i" class="grid grid-cols-12 items-center even:bg-white/[0.02] hover:bg-black/40 border-b border-white/5 p-3 transition-all relative group overflow-hidden">
                      <div v-if="parseFloat(mercado.ev) > 0" class="absolute top-0 left-0 w-1 h-full bg-[#10B981] shadow-[0_0_10px_#10B981]"></div>
                      <div class="col-span-5 flex flex-col pl-3">
                        <span class="text-xs font-bold text-white truncate">{{ mercado.nome }}</span>
                        <div class="flex items-center gap-1.5 mt-1">
                          <span v-if="parseFloat(mercado.ev) > 0" class="text-[9px] bg-[#10B981]/10 text-[#10B981] px-1.5 py-0.5 rounded border border-[#10B981]/20 font-bold uppercase tracking-wider">+{{ mercado.ev }}% EV</span>
                          <span v-else class="text-[9px] bg-red-500/10 text-red-400 px-1.5 py-0.5 rounded border border-red-500/20 font-bold uppercase tracking-wider">{{ mercado.ev }}% EV</span>
                        </div>
                      </div>
                      <div class="col-span-2 flex flex-col items-center justify-center">
                        <span class="text-xs font-mono font-bold" :class="parseFloat(mercado.ev) > 0 ? 'text-[#10B981] drop-shadow-[0_0_5px_rgba(16,185,129,0.3)]' : 'text-gray-300'">{{ mercado.prob }}%</span>
                        <span class="text-[8px] text-gray-500 font-mono uppercase mt-0.5">Fair: {{ mercado.fair }}</span>
                      </div>
                      <div class="col-span-3 flex flex-col items-center justify-center border-l border-white/5 pl-2">
                        <div class="flex items-center gap-1 text-xs font-mono font-bold">
                          <span class="text-gray-500 line-through text-[10px]">{{ mercado.openOdd }}</span>
                          <ArrowRight size="10" class="text-gray-600" />
                          <span class="text-white" :class="parseFloat(mercado.openOdd) > parseFloat(mercado.bookie) ? 'text-red-400' : 'text-[#10B981]'">{{ mercado.bookie }}</span>
                        </div>
                        <span class="text-[8px] text-gray-500 font-bold uppercase tracking-widest mt-0.5">{{ mercado.casaNome }}</span>
                      </div>
                      <div class="col-span-2 flex justify-end pr-1">
                        <button class="w-8 h-8 rounded-xl bg-[#121927] border border-white/10 flex items-center justify-center text-gray-400 hover:bg-[#3b82f6] hover:border-[#3b82f6] hover:text-white transition-all shadow-lg hover:scale-105 hover:shadow-[0_0_15px_rgba(59,130,246,0.4)]">
                          <Plus size="16" strokeWidth="2.5" />
                        </button>
                      </div>
                    </div>
                    <div v-if="currentMercados.length === 0" class="text-center text-[10px] text-gray-500 py-10 font-mono uppercase tracking-widest flex-1 flex items-center justify-center">Sem valor detectado</div>
                  </div>
                </div>

                <div v-else class="flex flex-col h-full">
                  <div class="grid grid-cols-12 px-3 pb-2 border-b border-white/10 text-[9px] uppercase font-bold text-gray-500 tracking-widest bg-black/40 rounded-t-lg pt-3 shrink-0">
                    <span class="col-span-5">Jogador Em Foco</span>
                    <span class="col-span-2 text-center">IA Prob</span>
                    <span class="col-span-2 text-center">WAR</span>
                    <span class="col-span-3 text-right pr-2">Fair Odd</span>
                  </div>
                  <div class="flex flex-col gap-1 overflow-y-auto custom-scrollbar flex-1 pb-2 bg-black/10 border border-t-0 border-white/10 rounded-b-lg p-1.5">
                    <div v-for="(prop, i) in currentPlayerProps" :key="'prop'+i" class="grid grid-cols-12 items-center bg-[#121927] hover:bg-white/5 border border-white/5 p-2.5 rounded-lg transition-colors group cursor-default">
                      <div class="col-span-5 flex items-center gap-3 pl-1">
                        <div class="w-8 h-8 rounded-full flex items-center justify-center border-2 shadow-md shrink-0 bg-black/60" :style="`border-color: ${prop.time === partida.casa ? partida.corCasa : partida.corFora}80`">
                          <User size="14" :color="prop.time === partida.casa ? partida.corCasa : partida.corFora" />
                        </div>
                        <div class="flex flex-col truncate">
                          <span class="text-xs font-bold text-white truncate group-hover:text-[#3B82F6] transition-colors">{{ prop.nome }}</span>
                          <span class="text-[9px] text-gray-500 font-mono mt-0.5 truncate">{{ prop.time }}</span>
                        </div>
                      </div>
                      <div class="col-span-2 flex flex-col items-center">
                        <span class="text-xs font-mono text-[#10B981] font-bold drop-shadow-[0_0_5px_rgba(16,185,129,0.3)]">{{ prop.prob }}%</span>
                      </div>
                      <div class="col-span-2 flex flex-col items-center">
                        <span class="text-[10px] font-mono font-bold px-1.5 rounded border border-gray-600" :class="parseFloat(prop.war) > 0.15 ? 'text-yellow-400 bg-yellow-400/10' : 'text-gray-400 bg-black/40'">+{{ prop.war }}</span>
                      </div>
                      <div class="col-span-3 flex justify-end pr-1">
                        <span class="text-xs font-mono font-bold bg-black px-3 py-1 rounded border border-gray-700 text-white shadow-inner">{{ prop.fair }}</span>
                      </div>
                    </div>
                    <div v-if="currentPlayerProps.length === 0" class="text-center text-[10px] text-gray-500 py-10 font-mono uppercase tracking-widest flex-1 flex items-center justify-center">Dados Específicos Indisponíveis</div>
                  </div>
                </div>
              </transition>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'quant_fbref'" titulo="Matrix & FBref Engine" class="h-full flex flex-col">
            <template #icone><BrainCircuit :size="16" class="text-[#a855f7]" /></template>
            <template #acoes>
              <div class="flex items-center gap-2">
                <button @click="quantTab = 'matrix'" class="text-[9px] font-bold uppercase tracking-widest px-2 py-1 rounded transition-colors" :class="quantTab === 'matrix' ? 'bg-[#a855f7]/20 text-[#a855f7]' : 'text-gray-500 hover:text-white'">Matrix</button>
                <button @click="quantTab = 'fbref'" class="text-[9px] font-bold uppercase tracking-widest px-2 py-1 rounded transition-colors" :class="quantTab === 'fbref' ? 'bg-[#a855f7]/20 text-[#a855f7]' : 'text-gray-500 hover:text-white'">FBref</button>
                <div class="w-px h-3 bg-white/20 mx-1" v-if="quantTab === 'fbref'"></div>
                <select v-if="quantTab === 'fbref'" v-model="fbrefSubTab" class="bg-black/60 text-[9px] text-white border border-gray-700 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-[#a855f7] transition-colors">
                  <option value="ofensivas">Ofensivas</option>
                  <option value="defensivas">Defensivas</option>
                  <option value="avancadas">Avançadas</option>
                  <option value="variadas">Variadas</option>
                  <option value="game_state">Game State</option>
                </select>
              </div>
            </template>
            
            <div class="flex flex-col h-full mt-3 overflow-hidden">
              <transition name="fade" mode="out-in">
                <div v-if="quantTab === 'matrix'" class="flex flex-col gap-2.5 h-full overflow-y-auto custom-scrollbar pr-1 pb-2">
                  <div v-if="!partida.quantMetrics || partida.quantMetrics.length === 0" class="flex-1 flex items-center justify-center text-[10px] text-gray-500 font-mono uppercase tracking-widest text-center">
                    Extraindo Tensores<br>da Alpha Matrix...
                  </div>
                  <div v-for="(stat, i) in partida.quantMetrics" :key="'qm'+i" class="flex flex-col gap-2 bg-black/20 p-3 rounded-xl border border-white/5">
                    <div class="flex justify-between items-end px-1">
                      <span class="font-mono text-sm w-12 text-left" :class="parseFloat(stat.casa) >= parseFloat(stat.fora) ? 'text-white font-bold drop-shadow-[0_0_5px_rgba(255,255,255,0.3)]' : 'text-gray-500'">{{ stat.casa }}{{ stat.sufixo }}</span>
                      <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold text-center">{{ stat.nome }}</span>
                      <span class="font-mono text-sm w-12 text-right" :class="parseFloat(stat.fora) >= parseFloat(stat.casa) ? 'text-white font-bold drop-shadow-[0_0_5px_rgba(255,255,255,0.3)]' : 'text-gray-500'">{{ stat.fora }}{{ stat.sufixo }}</span>
                    </div>
                    <div class="w-full h-2.5 bg-[#0b0f19] rounded-full flex overflow-hidden shadow-inner border border-white/5">
                      <div class="h-full transition-all duration-700 relative" :style="`width: ${(parseFloat(stat.casa) / ((parseFloat(stat.casa) + parseFloat(stat.fora)) || 1)) * 100}%; background-color: ${partida.corCasa || '#10B981'}`"></div>
                      <div class="h-full bg-black w-1 z-10 shrink-0"></div>
                      <div class="h-full transition-all duration-700 relative" :style="`width: ${(parseFloat(stat.fora) / ((parseFloat(stat.casa) + parseFloat(stat.fora)) || 1)) * 100}%; background-color: ${partida.corFora || '#3B82F6'}`"></div>
                    </div>
                    <span class="text-[9px] text-gray-500 text-center block leading-tight font-mono uppercase">{{ stat.desc }}</span>
                  </div>
                </div>

                <div v-else class="flex flex-col h-full overflow-y-auto custom-scrollbar pr-1 pb-2">
                  <div v-if="fbrefSubTab === 'game_state'" class="flex flex-col gap-3">
                    <p class="text-[10px] text-gray-400 mb-1 leading-relaxed px-1">Métricas de <strong class="text-white">xG/90 min</strong> baseadas no estado da partida.</p>
                    <div class="grid grid-cols-12 text-[9px] uppercase tracking-widest font-bold text-gray-500 border-b border-white/10 pb-2 px-1">
                      <span class="col-span-4">Time</span><span class="col-span-3 text-center text-green-400">À Frente</span><span class="col-span-3 text-center text-gray-400">Empatado</span><span class="col-span-2 text-center text-red-400">Atrás</span>
                    </div>
                    <div class="flex flex-col gap-2">
                      <div v-for="(gs, i) in (partida.gameState || [])" :key="'gs'+i" class="grid grid-cols-12 items-center bg-black/20 p-2.5 rounded-lg border border-white/5 shadow-inner">
                        <span class="col-span-4 text-xs font-bold truncate pr-2" :style="`color: ${gs.time === partida.casa ? partida.corCasa : partida.corFora}`">{{ gs.time }}</span>
                        <span class="col-span-3 text-center font-mono text-xs text-white bg-[#10B981]/10 border border-[#10B981]/20 rounded mx-1 py-1">{{ gs.vencendo }}</span>
                        <span class="col-span-3 text-center font-mono text-xs text-white bg-gray-500/10 border border-gray-500/20 rounded mx-1 py-1">{{ gs.empatando }}</span>
                        <span class="col-span-2 text-center font-mono text-xs text-white bg-red-500/10 border border-red-500/20 rounded mx-1 py-1">{{ gs.perdendo }}</span>
                      </div>
                      <div v-if="!partida.gameState || partida.gameState.length === 0" class="text-center text-[10px] text-gray-500 py-6 font-mono uppercase tracking-widest">Game State Indisponível</div>
                    </div>
                  </div>

                  <div v-else class="flex flex-col gap-2.5">
                    <div v-if="currentFbrefStats.length === 0" class="text-center text-[10px] text-gray-500 py-6 font-mono uppercase tracking-widest">Métricas Indisponíveis</div>
                    <div v-for="(stat, i) in currentFbrefStats" :key="'fbref'+i" class="flex flex-col gap-1.5 bg-black/20 p-3 rounded-xl border border-white/5">
                      <div class="flex justify-between items-end px-1">
                        <span class="font-mono text-sm w-12 text-left" :class="parseFloat(stat.casa) >= parseFloat(stat.fora) ? 'text-white font-bold drop-shadow-[0_0_5px_rgba(255,255,255,0.3)]' : 'text-gray-500'">{{ stat.casa }}{{ stat.sufixo }}</span>
                        <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold text-center">{{ stat.nome }}</span>
                        <span class="font-mono text-sm w-12 text-right" :class="parseFloat(stat.fora) >= parseFloat(stat.casa) ? 'text-white font-bold drop-shadow-[0_0_5px_rgba(255,255,255,0.3)]' : 'text-gray-500'">{{ stat.fora }}{{ stat.sufixo }}</span>
                      </div>
                      <div class="w-full h-2.5 bg-[#0b0f19] rounded-full flex overflow-hidden shadow-inner border border-white/5">
                        <div class="h-full transition-all duration-700 relative" :style="`width: ${(parseFloat(stat.casa) / ((parseFloat(stat.casa) + parseFloat(stat.fora)) || 1)) * 100}%; background-color: ${partida.corCasa || '#10B981'}`"></div>
                        <div class="h-full bg-black w-1 z-10 shrink-0"></div>
                        <div class="h-full transition-all duration-700 relative" :style="`width: ${(parseFloat(stat.fora) / ((parseFloat(stat.casa) + parseFloat(stat.fora)) || 1)) * 100}%; background-color: ${partida.corFora || '#3B82F6'}`"></div>
                      </div>
                      <span class="text-[8px] text-gray-500 text-center block leading-tight font-mono uppercase">{{ stat.desc }}</span>
                    </div>
                  </div>
                </div>
              </transition>
            </div>
          </WidgetCard>

        </div>
      </template>
    </draggable>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject, watch } from 'vue';
import draggable from 'vuedraggable';
import { 
  Shield, ShieldAlert, History, User, BrainCircuit, GripHorizontal, 
  LayoutList, Percent, Grid, ArrowRight, Plus, Gavel
} from 'lucide-vue-next';
import axios from 'axios';
import WidgetCard from './WidgetCard.vue';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:3000/api/v1').replace(/\/$/, '');
const globalState = inject('globalState'); 

const isLoading = ref(true);

// Guias Locais (Reatividade de Abas)
const contextTab = ref("stats");
const quantTab = ref("matrix");
const mercadosTab = ref("value");
const fbrefSubTab = ref("avancadas");
const showPoisson = ref(false);

// Filtros Numéricos Dinâmicos
const filtroJogosH2H = ref("5");
const filtroJogosForma = ref("5");
const propsTab = ref("chutes");
const filtroMercado = ref("all");

// Matriz do Layout Drag & Drop (5 Widgets otimizados em 12 colunas)
const layoutWidgets = ref([
  { id: 'contexto', span: 'col-span-1 lg:col-span-5 xl:col-span-5' },
  { id: 'forma', span: 'col-span-1 lg:col-span-4 xl:col-span-4' },
  { id: 'ml', span: 'col-span-1 lg:col-span-3 xl:col-span-3' },
  { id: 'mercados_props', span: 'col-span-1 lg:col-span-6 xl:col-span-6' },
  { id: 'quant_fbref', span: 'col-span-1 lg:col-span-6 xl:col-span-6' }
]);

// Helpers de Cabeçalho dos Widgets Dinâmicos
const getWidgetIcon = (id) => {
  const map = {
    'contexto': History, 'forma': LayoutList, 'quant_fbref': BrainCircuit,
    'mercados_props': Percent, 'ml': Grid
  };
  return map[id] || History;
};

const getWidgetTitle = (id) => {
  const map = {
    'contexto': 'Overview & H2H', 'forma': 'Forma Recente', 'quant_fbref': 'Matrix & FBref',
    'mercados_props': 'Value Finder & Props', 'ml': 'xG Flow & Poisson'
  };
  return map[id] || 'Widget';
};

const getWidgetColor = (id) => {
  const map = {
    'contexto': 'text-[#10B981]', 'forma': 'text-[#3B82F6]', 'quant_fbref': 'text-[#a855f7]',
    'mercados_props': 'text-[#3B82F6]', 'ml': 'text-orange-400'
  };
  return map[id] || 'text-white';
};

// Estado Inicial Blindado
const partida = ref({
  id: 0, casa: "---", fora: "---", posCasa: 0, posFora: 0,
  corCasa: "#10B981", corFora: "#3B82F6", placarCasa: "-", placarFora: "-", xgCasa: "-", xgFora: "-",
  folhaCasa: "", folhaFora: "",
  isLive: false, tempo: 0, hora: "--:--",
  formCasa: [], formFora: [], indFormCasa: [], indFormFora: [], historico: [],
  disciplina: { h_y: "-", h_r: "-", a_y: "-", a_r: "-" },
  quantMetrics: [], fbrefOfensivas: [], fbrefDefensivas: [], fbrefAvancadas: [], fbrefVariadas: [], gameState: [], poisson: [], mercados: []
});

const playerPropsData = ref({ chutes: [], gols: [], assists: [], faltas: [], escanteios: [], cartoes: [] });

// Carrega as Imagens de forma Nativa
const getTeamLogo = (teamName) => {
  if (!teamName || teamName === '---') return '';
  return `${API_BASE_URL}/teams/shield/${encodeURIComponent(teamName.trim())}`;
};

const handleImageError = (e) => { 
  e.target.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'; 
};

// ==================================================
// MOTOR DE BUSCA DEFENSIVO
// ==================================================
const carregarDadosDaPartida = async () => {
  isLoading.value = true;
  try {
    const token = localStorage.getItem('betgenius_token');
    let matchId = 0;
    if (globalState && globalState.activeMatch) {
      matchId = typeof globalState.activeMatch === 'object' ? (globalState.activeMatch.id || 0) : globalState.activeMatch;
    }
    
    const response = await axios.get(`${API_BASE_URL}/match-center/${matchId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    
    if (response.data && response.data.partida) {
      partida.value = response.data.partida;
      playerPropsData.value = response.data.playerProps || { chutes: [], gols: [], assists: [], faltas: [], escanteios: [], cartoes: [] };
      if (globalState) globalState.activeMatch = response.data.partida.id;
    }
  } catch (error) {
    console.error("❌ Erro ao buscar Match Center:", error);
  } finally {
    isLoading.value = false;
  }
};

watch(() => globalState?.activeMatch, (newVal, oldVal) => {
  if (newVal && newVal !== oldVal) carregarDadosDaPartida();
});

onMounted(() => { carregarDadosDaPartida(); });

// ==================================================
// COMPUTED PROPERTIES (REATIVIDADE S-TIER)
// ==================================================
const calcStats = computed(() => {
  const limite = parseInt(filtroJogosH2H.value) || 5;
  
  const getStats = (formaArray) => {
    if (!formaArray || formaArray.length === 0) return { pts: 0, j: 0, win: 0, avg_gf: '0.0', avg_gc: '0.0', over: 0, btts: 0 };
    
    let pts = 0, wins = 0, gf = 0, gc = 0, over = 0, btts = 0;
    const j = formaArray.length;

    formaArray.forEach(jogo => {
      if(jogo.res === 'W') { pts += 3; wins++; }
      else if(jogo.res === 'D') pts += 1;

      const placarStr = jogo.placar || '0-0';
      const placarParts = placarStr.split('-');
      const g_f = parseInt(placarParts[0]) || 0;
      const g_c = parseInt(placarParts[1]) || 0;
      
      gf += g_f;
      gc += g_c;
      if((g_f + g_c) > 2.5) over++;
      if(g_f > 0 && g_c > 0) btts++;
    });

    return {
      pts, j,
      win: Math.round((wins/j)*100),
      avg_gf: (gf/j).toFixed(1),
      avg_gc: (gc/j).toFixed(1),
      over: Math.round((over/j)*100),
      btts: Math.round((btts/j)*100)
    };
  };

  const arrayCasa = (partida.value.indFormCasa || []).slice(0, limite);
  const arrayFora = (partida.value.indFormFora || []).slice(0, limite);

  return { casa: getStats(arrayCasa), fora: getStats(arrayFora) };
});

const historicoFiltrado = computed(() => {
  return (partida.value.historico || []).slice(0, parseInt(filtroJogosH2H.value) || 5);
});

const formaCasaFiltrada = computed(() => {
  return (partida.value.indFormCasa || []).slice(0, parseInt(filtroJogosForma.value) || 5);
});

const formaForaFiltrada = computed(() => {
  return (partida.value.indFormFora || []).slice(0, parseInt(filtroJogosForma.value) || 5);
});

const currentPlayerProps = computed(() => {
  return playerPropsData.value[propsTab.value] || [];
});

const currentMercados = computed(() => {
  const mercs = partida.value.mercados || [];
  if(filtroMercado.value === 'all') return mercs;
  return mercs.filter(m => {
    if(!m || !m.categoria) return false;
    return m.categoria.toLowerCase().includes(filtroMercado.value.toLowerCase());
  });
});

const currentFbrefStats = computed(() => {
  if(fbrefSubTab.value === 'ofensivas') return partida.value.fbrefOfensivas || [];
  if(fbrefSubTab.value === 'defensivas') return partida.value.fbrefDefensivas || [];
  if(fbrefSubTab.value === 'variadas') return partida.value.fbrefVariadas || [];
  return partida.value.fbrefAvancadas || [];
});
</script>

<style scoped>
.glass-card { background: rgba(18, 25, 39, 0.85); backdrop-filter: blur(24px); }
.skeleton-pulse { background: linear-gradient(90deg, rgba(255,255,255,0.02) 25%, rgba(255,255,255,0.05) 50%, rgba(255,255,255,0.02) 75%); background-size: 400% 100%; animation: skeletonLoading 1.5s infinite ease-in-out; }
@keyframes skeletonLoading { 0% { background-position: 100% 50%; } 100% { background-position: 0 50%; } }
.ghost-widget { opacity: 0.3 !important; border: 2px dashed #10B981 !important; transform: scale(0.98); }
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.15); border-radius: 10px; }
.animate-fade-in { animation: fadeIn 0.3s ease-in-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: scale(0.98); }
</style>