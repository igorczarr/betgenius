<template>
  <div class="flex flex-col gap-6 w-full h-full relative fade-in-up pb-30">
    
    <div class="glass-card p-6 md:p-8 relative flex flex-col md:flex-row justify-between items-center border-t-4 shadow-[0_15px_40px_rgba(0,0,0,0.6)] transition-all duration-700" :style="`border-color: ${partida.corCasa || '#10B981'}`">
      <div class="absolute -right-20 -top-20 w-72 h-72 rounded-full blur-[100px] pointer-events-none opacity-20 transition-colors duration-1000" :style="`background-color: ${partida.corCasa || '#10B981'}`"></div>
      <div class="absolute -left-20 -bottom-20 w-72 h-72 rounded-full blur-[100px] pointer-events-none opacity-20 transition-colors duration-1000" :style="`background-color: ${partida.corFora || '#3B82F6'}`"></div>
      
      <div class="flex items-center gap-5 w-full md:w-2/5 justify-end z-10 group cursor-default">
        <div class="text-right flex flex-col items-end">
          <h2 class="text-3xl font-mono text-white tracking-wider drop-shadow-[0_0_10px_rgba(255,255,255,0.2)] group-hover:scale-105 transition-transform duration-300">{{ partida.casa }}</h2>
          <div class="flex items-center justify-end gap-2 mt-2 bg-black/40 px-3 py-1 rounded-full border border-white/5" v-if="!isLoading">
            <span class="text-[9px] text-gray-400 uppercase tracking-widest font-bold">{{ partida.posCasa }}º Lugar</span>
            <div class="w-px h-3 bg-white/20 mx-1"></div>
            <div class="flex gap-1">
              <span v-for="(f, i) in (partida.formCasa || []).slice(0, 5)" :key="'fc'+i" class="w-4 h-4 flex items-center justify-center rounded-sm text-[8px] font-bold text-white shadow-sm" :class="f === 'W' ? 'bg-[#10B981]' : (f === 'D' ? 'bg-gray-500' : 'bg-red-500')">{{ f }}</span>
            </div>
          </div>
        </div>
        <div class="w-20 h-20 rounded-2xl bg-[#0b0f19] border border-white/10 flex items-center justify-center shadow-[0_0_30px_rgba(0,0,0,0.8)] relative overflow-hidden transition-all duration-500 group-hover:scale-110" :style="`box-shadow: 0 0 20px ${partida.corCasa || '#10B981'}40`">
          <img v-if="partida.casa !== '---'" :src="getTeamLogo(partida.casa)" @error="handleImageError" class="w-12 h-12 object-contain drop-shadow-[0_0_8px_currentColor]" />
          <Shield v-else :size="36" color="#4B5563" class="drop-shadow-[0_0_8px_currentColor]" />
        </div>
      </div>

      <div class="flex flex-col items-center justify-center w-full md:w-1/5 my-6 md:my-0 z-10">
        <div class="bg-black/60 text-white px-5 py-2 rounded-xl text-[10px] font-bold uppercase tracking-[0.2em] mb-2 border border-white/10 backdrop-blur-md flex flex-col items-center gap-1 shadow-inner">
          <span class="text-gray-400">Match Preview</span>
          <span class="text-bet-primary">{{ partida.hora || '--:--' }}</span>
        </div>
        
        <div class="text-3xl font-mono font-black text-gray-600 tracking-widest drop-shadow-md my-2">
          VS
        </div>
      </div>

      <div class="flex items-center gap-5 w-full md:w-2/5 justify-start z-10 group cursor-default">
        <div class="w-20 h-20 rounded-2xl bg-[#0b0f19] border border-white/10 flex items-center justify-center shadow-[0_0_30px_rgba(0,0,0,0.8)] relative overflow-hidden transition-all duration-500 group-hover:scale-110" :style="`box-shadow: 0 0 20px ${partida.corFora || '#3B82F6'}40`">
          <img v-if="partida.fora !== '---'" :src="getTeamLogo(partida.fora)" @error="handleImageError" class="w-12 h-12 object-contain drop-shadow-[0_0_8px_currentColor]" />
          <ShieldAlert v-else :size="36" color="#4B5563" class="drop-shadow-[0_0_8px_currentColor]" />
        </div>
        <div class="text-left flex flex-col items-start">
          <h2 class="text-3xl font-mono text-white tracking-wider drop-shadow-[0_0_10px_rgba(255,255,255,0.2)] group-hover:scale-105 transition-transform duration-300">{{ partida.fora }}</h2>
          <div class="flex items-center justify-start gap-2 mt-2 bg-black/40 px-3 py-1 rounded-full border border-white/5" v-if="!isLoading">
            <div class="flex gap-1">
              <span v-for="(f, i) in (partida.formFora || []).slice(0, 5)" :key="'ff'+i" class="w-4 h-4 flex items-center justify-center rounded-sm text-[8px] font-bold text-white shadow-sm" :class="f === 'W' ? 'bg-[#10B981]' : (f === 'D' ? 'bg-gray-500' : 'bg-red-500')">{{ f }}</span>
            </div>
            <div class="w-px h-3 bg-white/20 mx-1"></div>
            <span class="text-[9px] text-gray-400 uppercase tracking-widest font-bold">{{ partida.posFora }}º Lugar</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="isLoading" class="flex flex-col justify-center items-center py-32 gap-4">
      <div class="w-10 h-10 border-4 border-white/10 border-t-[#10B981] rounded-full animate-spin shadow-[0_0_15px_rgba(16,185,129,0.3)]"></div>
      <span class="text-xs font-mono text-gray-500 uppercase tracking-widest animate-pulse">Carregando Tensores da Partida...</span>
    </div>

    <draggable 
      v-else
      v-model="layoutWidgets" 
      item-key="id" 
      class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start mt-2" 
      handle=".drag-handle" 
      ghost-class="ghost-widget"
      animation="300"
      :delay="50"
    >
      <template #item="{ element }">
        <div :class="element.span" class="relative w-full group/widget h-[480px] bg-[#0b0f19] rounded-2xl border border-white/5 shadow-2xl flex flex-col overflow-hidden">
          
          <div class="drag-handle absolute top-0 left-1/2 -translate-x-1/2 z-[80] opacity-0 group-hover/widget:opacity-100 cursor-move py-1 px-8 bg-[#121927] text-gray-400 rounded-b-xl border-x border-b border-white/10 transition-all hover:bg-[#10B981] hover:text-black shadow-md">
            <GripHorizontal size="16" />
          </div>

          <WidgetCard v-if="element.id === 'contexto'" titulo="Overview & Head-to-Head" class="h-full flex flex-col border-none bg-transparent">
            <template #icone><History :size="16" class="text-[#10B981]" /></template>
            <template #acoes>
              <div class="flex items-center gap-1 bg-black/40 p-1 rounded-lg border border-white/5 shadow-inner">
                <button @click="contextTab = 'stats'" class="text-[9px] font-bold uppercase tracking-widest px-3 py-1.5 rounded-md transition-all" :class="contextTab === 'stats' ? 'bg-[#10B981]/20 text-[#10B981] shadow-sm' : 'text-gray-500 hover:text-white'">Stats</button>
                <button @click="contextTab = 'h2h'" class="text-[9px] font-bold uppercase tracking-widest px-3 py-1.5 rounded-md transition-all" :class="contextTab === 'h2h' ? 'bg-[#10B981]/20 text-[#10B981] shadow-sm' : 'text-gray-500 hover:text-white'">H2H (5)</button>
              </div>
            </template>
            
            <div class="flex flex-col h-full mt-4 overflow-hidden">
              <transition name="fade-scale" mode="out-in">
                
                <div v-if="contextTab === 'stats'" class="flex flex-col h-full gap-3">
                  <div class="grid grid-cols-3 bg-[#121927] py-3 text-[10px] uppercase tracking-widest text-gray-500 font-bold text-center border border-white/10 rounded-xl shrink-0 shadow-inner">
                    <span class="text-left text-white truncate px-4 drop-shadow-md font-sans" :style="`color: ${partida.corCasa || '#10B981'}`">{{ partida.casa }}</span>
                    <span>Radar Analítico</span>
                    <span class="text-right text-white truncate px-4 drop-shadow-md font-sans" :style="`color: ${partida.corFora || '#3B82F6'}`">{{ partida.fora }}</span>
                  </div>
                  
                  <div class="flex flex-col text-xs font-mono text-gray-300 border border-white/5 rounded-xl bg-black/20 flex-1 justify-around py-1 shadow-inner">
                    <div class="grid grid-cols-3 px-5 py-2.5 border-b border-white/5 hover:bg-white/[0.02] transition-colors"><span class="font-bold text-white">{{ calcStats.casa.pts }}</span><span class="text-center text-[9px] text-gray-500 font-sans tracking-widest uppercase font-bold">PTS / J</span><span class="text-right font-bold text-white">{{ calcStats.fora.pts }}</span></div>
                    <div class="grid grid-cols-3 px-5 py-2.5 border-b border-white/5 hover:bg-white/[0.02] transition-colors"><span>{{ calcStats.casa.win }}%</span><span class="text-center text-[9px] text-gray-500 font-sans tracking-widest uppercase font-bold">Win Rate</span><span class="text-right">{{ calcStats.fora.win }}%</span></div>
                    <div class="grid grid-cols-3 px-5 py-2.5 border-b border-white/5 hover:bg-white/[0.02] transition-colors"><span>{{ calcStats.casa.avg_gf }} <span class="text-gray-600">/</span> {{ calcStats.casa.avg_gc }}</span><span class="text-center text-[9px] text-gray-500 font-sans tracking-widest uppercase font-bold">Gols F/S</span><span class="text-right">{{ calcStats.fora.avg_gf }} <span class="text-gray-600">/</span> {{ calcStats.fora.avg_gc }}</span></div>
                    <div class="grid grid-cols-3 px-5 py-2.5 border-b border-white/5 hover:bg-white/[0.02] transition-colors"><span class="text-[#10B981] font-bold">{{ calcStats.casa.over }}%</span><span class="text-center text-[9px] text-gray-500 font-sans tracking-widest uppercase font-bold">Over 2.5</span><span class="text-right text-[#10B981] font-bold">{{ calcStats.fora.over }}%</span></div>
                    <div class="grid grid-cols-3 px-5 py-2.5 hover:bg-white/[0.02] transition-colors"><span>{{ calcStats.casa.btts }}%</span><span class="text-center text-[9px] text-gray-500 font-sans tracking-widest uppercase font-bold">BTTS</span><span class="text-right">{{ calcStats.fora.btts }}%</span></div>
                  </div>
                  
                  <div class="grid grid-cols-2 gap-3 mt-1 shrink-0">
                    <div class="bg-[#121927] border border-white/5 p-3.5 rounded-xl flex flex-col gap-1.5 shadow-inner">
                      <div class="flex items-center gap-2 mb-1"><Gavel size="12" class="text-yellow-500"/><span class="text-[9px] font-bold text-gray-400 uppercase tracking-widest truncate">Média Cartões (H)</span></div>
                      <div class="flex justify-between font-mono text-xs text-white"><span>Y: <strong class="text-yellow-400">{{ partida.disciplina?.h_y || '-' }}</strong></span><span>R: <strong class="text-red-400">{{ partida.disciplina?.h_r || '-' }}</strong></span></div>
                    </div>
                    <div class="bg-[#121927] border border-white/5 p-3.5 rounded-xl flex flex-col gap-1.5 shadow-inner">
                      <div class="flex items-center gap-2 mb-1"><Gavel size="12" class="text-yellow-500"/><span class="text-[9px] font-bold text-gray-400 uppercase tracking-widest truncate">Média Cartões (A)</span></div>
                      <div class="flex justify-between font-mono text-xs text-white"><span>Y: <strong class="text-yellow-400">{{ partida.disciplina?.a_y || '-' }}</strong></span><span>R: <strong class="text-red-400">{{ partida.disciplina?.a_r || '-' }}</strong></span></div>
                    </div>
                  </div>
                </div>

                <div v-else class="flex flex-col h-full bg-[#121927] rounded-xl border border-white/5 shadow-inner overflow-hidden">
                  <div class="flex-1 overflow-y-auto custom-scrollbar p-2">
                    <div v-for="(h2h, i) in historicoFiltrado" :key="'h2h'+i" class="flex justify-between items-center p-3.5 text-xs font-mono bg-black/20 hover:bg-white/[0.04] transition-colors border border-white/5 rounded-lg mb-2 last:mb-0 group cursor-default">
                      <span class="text-gray-500 w-16 text-[9px] uppercase font-bold">{{ h2h.data }}</span>
                      <span class="flex-1 text-right truncate pr-4 transition-colors" :class="h2h.win === 'casa' ? 'text-[#10B981] font-black' : 'text-gray-400'">{{ h2h.casa }}</span>
                      <span class="bg-black/60 px-4 py-1.5 rounded-md text-white font-bold border border-white/10 shadow-inner tracking-[0.2em] min-w-[55px] text-center">{{ h2h.placar }}</span>
                      <span class="flex-1 text-left truncate pl-4 transition-colors" :class="h2h.win === 'fora' ? 'text-[#3B82F6] font-black' : 'text-gray-400'">{{ h2h.fora }}</span>
                    </div>
                    <div v-if="historicoFiltrado.length === 0" class="flex flex-col items-center justify-center h-full text-center text-[10px] text-gray-500 font-mono uppercase tracking-widest gap-2 opacity-50">
                      <History size="24"/> Sem histórico recente (H2H)
                    </div>
                  </div>
                </div>
              </transition>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'forma'" titulo="Forma Recente (Últimos 5)" class="h-full flex flex-col border-none bg-transparent">
            <template #icone><LayoutList :size="16" class="text-[#3B82F6]" /></template>
            
            <div class="flex gap-4 h-full mt-4 overflow-hidden">
              <div class="w-1/2 flex flex-col h-full bg-[#121927] border border-white/5 rounded-xl shadow-inner overflow-hidden">
                <div class="flex items-center justify-between border-b border-white/10 px-4 py-3 bg-black/40">
                  <span :style="`color: ${partida.corCasa || '#10B981'}`" class="text-[11px] uppercase font-black tracking-widest drop-shadow-md truncate flex-1 font-sans">{{ partida.casa }}</span>
                  <span class="bg-white/5 px-2 py-0.5 rounded text-[8px] font-bold text-gray-400">CASA</span>
                </div>
                <div class="flex flex-col gap-2 p-2 overflow-y-auto custom-scrollbar">
                  <div v-for="(jogo, i) in formaCasaFiltrada" :key="'ih'+i" class="bg-black/20 border border-white/5 p-3 rounded-lg flex flex-col gap-2 hover:bg-white/[0.04] transition-colors cursor-default">
                    <div class="flex justify-between items-center text-[10px] font-mono">
                      <span class="text-gray-500 font-bold">{{ jogo.data }}</span>
                      <span class="font-black px-2 py-0.5 rounded shadow-sm" :class="jogo.res === 'W' ? 'bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/30' : (jogo.res === 'L' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-gray-500/20 text-gray-300 border border-gray-500/30')">{{ jogo.res }}</span>
                    </div>
                    <div class="flex justify-between items-center text-[11px]">
                      <span class="text-gray-300 truncate font-sans font-bold pr-2">{{ jogo.adv }}</span>
                      <span class="font-black font-mono text-white bg-black/40 px-2 py-0.5 rounded">{{ jogo.placar }}</span>
                    </div>
                  </div>
                  <div v-if="formaCasaFiltrada.length === 0" class="text-center text-[9px] text-gray-500 py-10 font-mono uppercase tracking-widest opacity-50">S/ Dados</div>
                </div>
              </div>
              
              <div class="w-1/2 flex flex-col h-full bg-[#121927] border border-white/5 rounded-xl shadow-inner overflow-hidden">
                <div class="flex items-center justify-between border-b border-white/10 px-4 py-3 bg-black/40">
                  <span class="bg-white/5 px-2 py-0.5 rounded text-[8px] font-bold text-gray-400">FORA</span>
                  <span :style="`color: ${partida.corFora || '#3B82F6'}`" class="text-[11px] uppercase font-black tracking-widest drop-shadow-md truncate flex-1 text-right font-sans">{{ partida.fora }}</span>
                </div>
                <div class="flex flex-col gap-2 p-2 overflow-y-auto custom-scrollbar">
                  <div v-for="(jogo, i) in formaForaFiltrada" :key="'ia'+i" class="bg-black/20 border border-white/5 p-3 rounded-lg flex flex-col gap-2 hover:bg-white/[0.04] transition-colors cursor-default">
                    <div class="flex justify-between items-center text-[10px] font-mono">
                      <span class="font-black px-2 py-0.5 rounded shadow-sm" :class="jogo.res === 'W' ? 'bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/30' : (jogo.res === 'L' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-gray-500/20 text-gray-300 border border-gray-500/30')">{{ jogo.res }}</span>
                      <span class="text-gray-500 font-bold">{{ jogo.data }}</span>
                    </div>
                    <div class="flex justify-between items-center text-[11px]">
                      <span class="font-black font-mono text-white bg-black/40 px-2 py-0.5 rounded">{{ jogo.placar }}</span>
                      <span class="text-gray-300 truncate font-sans font-bold pl-2 text-right">{{ jogo.adv }}</span>
                    </div>
                  </div>
                  <div v-if="formaForaFiltrada.length === 0" class="text-center text-[9px] text-gray-500 py-10 font-mono uppercase tracking-widest opacity-50">S/ Dados</div>
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'ml'" titulo="Machine Learning Prediction" class="h-full flex flex-col border-none bg-transparent">
            <template #icone><Grid :size="16" class="text-orange-400" /></template>
            <template #acoes>
               <span class="bg-orange-400/10 text-orange-400 border border-orange-400/30 px-3 py-1 rounded-md text-[9px] font-mono font-bold uppercase tracking-widest flex items-center gap-1.5 shadow-[0_0_10px_rgba(251,146,60,0.15)]"><Cpu size="10"/> Poisson Dist</span>
            </template>
            
            <div class="flex flex-col h-full mt-4 overflow-hidden relative">
              <div class="flex flex-col h-full bg-[#121927] rounded-xl border border-white/5 p-4 shadow-inner w-full">
                <div v-if="!partida.poisson || partida.poisson.length === 0" class="flex-1 flex flex-col items-center justify-center text-[10px] font-mono text-gray-500 uppercase tracking-widest gap-3 opacity-50 border border-dashed border-white/5 rounded-lg">
                  <Grid size="24"/>
                  Calculando Distribuição...
                </div>
                
                <div v-else class="flex flex-col h-full">
                  <div class="flex shrink-0">
                    <div class="w-8"></div>
                    <div class="flex-1 grid grid-cols-4 text-center text-[10px] font-bold text-gray-500 uppercase tracking-widest pb-3 border-b border-white/10">
                      <span class="col-span-4 flex items-center justify-center gap-2">
                        <div class="w-2 h-2 rounded-full shadow-[0_0_5px_currentColor]" :style="`background-color: ${partida.corFora || '#3B82F6'}; color: ${partida.corFora || '#3B82F6'}`"></div>
                        <span class="truncate font-sans">{{ partida.fora }} (Golos)</span>
                      </span>
                    </div>
                  </div>
                  
                  <div class="flex flex-1 mt-3">
                    <div class="w-8 flex flex-col justify-center items-center text-[10px] font-bold text-gray-500 uppercase tracking-widest rotate-180 border-r border-white/10 gap-2 pr-2" style="writing-mode: vertical-rl;">
                      <div class="w-2 h-2 rounded-full shadow-[0_0_5px_currentColor]" :style="`background-color: ${partida.corCasa || '#10B981'}; color: ${partida.corCasa || '#10B981'}`"></div>
                      <span class="truncate font-sans">{{ partida.casa }} (Golos)</span>
                    </div>
                    
                    <div class="flex-1 grid grid-cols-4 grid-rows-4 gap-2 pl-3">
                      <div v-for="p in partida.poisson" :key="`p${p.h}${p.a}`" class="border rounded-xl flex flex-col items-center justify-center text-[12px] font-mono transition-all duration-300 cursor-default hover:scale-105" 
                           :class="p.prob > 10 ? 'bg-gradient-to-br from-[#10B981]/30 to-[#10B981]/10 border-[#10B981]/50 text-white font-black shadow-[0_0_15px_rgba(16,185,129,0.3)]' : (p.prob > 5 ? 'bg-gradient-to-br from-yellow-500/20 to-yellow-500/5 border-yellow-500/30 text-gray-200 font-bold' : 'bg-black/60 border-white/5 text-gray-600')">
                        <span class="mb-1">{{ p.h }}-{{ p.a }}</span>
                        <span class="text-[8px] opacity-80 uppercase tracking-widest" :class="p.prob > 10 ? 'text-[#10B981]' : ''">{{ p.prob }}%</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'mercados_props'" titulo="Value Finder & Props" class="h-full flex flex-col border-none bg-transparent">
            <template #icone><Percent :size="16" class="text-[#3b82f6]" /></template>
            <template #acoes>
              <div class="flex items-center gap-1 bg-black/40 p-1 rounded-lg border border-white/5 shadow-inner">
                <button @click="mercadosTab = 'value'" class="text-[9px] font-bold uppercase tracking-widest px-3 py-1.5 rounded-md transition-all" :class="mercadosTab === 'value' ? 'bg-[#3b82f6]/20 text-[#3b82f6] shadow-sm' : 'text-gray-500 hover:text-white'">Mercados</button>
                <button @click="mercadosTab = 'props'" class="text-[9px] font-bold uppercase tracking-widest px-3 py-1.5 rounded-md transition-all" :class="mercadosTab === 'props' ? 'bg-[#3b82f6]/20 text-[#3b82f6] shadow-sm' : 'text-gray-500 hover:text-white'">Props</button>
              </div>
            </template>
            
            <div class="flex flex-col h-full mt-4 overflow-hidden">
              <transition name="fade-scale" mode="out-in">
                
                <div v-if="mercadosTab === 'value'" class="flex flex-col h-full bg-[#121927] rounded-xl border border-white/5 shadow-inner overflow-hidden">
                  <div class="grid grid-cols-12 px-4 pb-2 border-b border-white/10 text-[9px] uppercase font-bold text-gray-500 tracking-widest bg-black/40 pt-3 shrink-0">
                    <span class="col-span-5 pl-1">Mercado Detetado</span>
                    <span class="col-span-2 text-center">IA Prob</span>
                    <span class="col-span-3 text-center">Odd Movement</span>
                    <span class="col-span-2 text-right pr-2">Ação</span>
                  </div>
                  
                  <div class="flex flex-col overflow-y-auto custom-scrollbar flex-1 p-2 gap-1.5">
                    <div v-for="(mercado, i) in currentMercados" :key="'m'+i" class="grid grid-cols-12 items-center bg-black/40 hover:bg-white/[0.04] border border-white/5 rounded-lg p-3 transition-all relative group overflow-hidden">
                      <div v-if="parseFloat(mercado.ev) > 0" class="absolute top-0 left-0 w-1.5 h-full bg-[#10B981] shadow-[2px_0_10px_#10B981]"></div>
                      
                      <div class="col-span-5 flex flex-col pl-3">
                        <span class="text-xs font-bold text-white truncate font-sans">{{ mercado.nome }}</span>
                        <div class="flex items-center gap-1.5 mt-1.5">
                          <span v-if="parseFloat(mercado.ev) > 0" class="text-[8px] bg-[#10B981]/10 text-[#10B981] px-1.5 py-0.5 rounded border border-[#10B981]/20 font-bold uppercase tracking-widest shadow-sm">+{{ mercado.ev }}% EV</span>
                          <span v-else class="text-[8px] bg-red-500/10 text-red-400 px-1.5 py-0.5 rounded border border-red-500/20 font-bold uppercase tracking-widest">{{ mercado.ev }}% EV</span>
                        </div>
                      </div>
                      
                      <div class="col-span-2 flex flex-col items-center justify-center">
                        <span class="text-[13px] font-mono font-black" :class="parseFloat(mercado.ev) > 0 ? 'text-[#10B981] drop-shadow-[0_0_5px_rgba(16,185,129,0.4)]' : 'text-gray-300'">{{ mercado.prob }}%</span>
                        <span class="text-[8px] text-gray-500 font-mono uppercase mt-0.5 font-bold">Fair: {{ mercado.fair }}</span>
                      </div>
                      
                      <div class="col-span-3 flex flex-col items-center justify-center border-l border-white/5 pl-2">
                        <div class="flex items-center gap-2 text-xs font-mono font-bold">
                          <span class="text-gray-600 line-through text-[10px]">{{ mercado.openOdd }}</span>
                          <ArrowRight size="10" class="text-gray-500" />
                          <span class="text-white bg-black/60 px-2 py-0.5 rounded border border-white/10" :class="parseFloat(mercado.openOdd) > parseFloat(mercado.bookie) ? 'text-red-400 border-red-500/30' : 'text-[#10B981] border-[#10B981]/30'">{{ mercado.bookie }}</span>
                        </div>
                        <span class="text-[8px] text-gray-500 font-bold uppercase tracking-widest mt-1">{{ mercado.casaNome }}</span>
                      </div>
                      
                      <div class="col-span-2 flex justify-end pr-1">
                        <button class="w-10 h-10 rounded-xl bg-[#0b0f19] border border-white/10 flex items-center justify-center text-gray-400 hover:bg-[#3b82f6] hover:border-[#3b82f6] hover:text-white transition-all shadow-lg hover:scale-105 hover:shadow-[0_0_15px_rgba(59,130,246,0.4)] group/btn">
                          <Plus size="18" strokeWidth="2.5" class="group-hover/btn:rotate-90 transition-transform" />
                        </button>
                      </div>
                    </div>
                    <div v-if="currentMercados.length === 0" class="text-center text-[10px] text-gray-500 py-10 font-mono uppercase tracking-widest flex-1 flex flex-col items-center justify-center gap-2 opacity-50">
                      <Search size="24"/> Sem valor detectado no mercado
                    </div>
                  </div>
                </div>

                <div v-else class="flex flex-col h-full bg-[#121927] rounded-xl border border-white/5 shadow-inner overflow-hidden">
                  <div class="flex items-center justify-between p-2 border-b border-white/10 bg-black/40 shrink-0">
                    <select v-model="propsTab" class="bg-black/60 text-[10px] text-white border border-gray-700 rounded-lg px-3 py-1.5 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-[#3b82f6] transition-colors w-full mx-2 shadow-inner">
                      <option value="chutes">Chutes no Gol</option>
                      <option value="gols">Gols Marcados</option>
                      <option value="assists">Assistências</option>
                      <option value="cartoes">Cartões</option>
                    </select>
                  </div>
                  
                  <div class="grid grid-cols-12 px-4 pb-2 border-b border-white/10 text-[9px] uppercase font-bold text-gray-500 tracking-widest bg-black/40 pt-3 shrink-0">
                    <span class="col-span-5">Jogador Em Foco</span>
                    <span class="col-span-2 text-center">IA Prob</span>
                    <span class="col-span-2 text-center">WAR</span>
                    <span class="col-span-3 text-right pr-2">Fair Odd</span>
                  </div>
                  
                  <div class="flex flex-col gap-1.5 overflow-y-auto custom-scrollbar flex-1 p-2">
                    <div v-for="(prop, i) in currentPlayerProps" :key="'prop'+i" class="grid grid-cols-12 items-center bg-black/40 hover:bg-white/[0.04] border border-white/5 p-3 rounded-lg transition-colors group cursor-default">
                      <div class="col-span-5 flex items-center gap-3 pl-1">
                        <div class="w-10 h-10 rounded-full flex items-center justify-center border-2 shadow-md shrink-0 bg-[#0b0f19]" :style="`border-color: ${prop.time === partida.casa ? partida.corCasa : partida.corFora}80`">
                          <User size="16" :color="prop.time === partida.casa ? partida.corCasa : partida.corFora" />
                        </div>
                        <div class="flex flex-col truncate">
                          <span class="text-xs font-bold text-white truncate group-hover:text-[#3B82F6] transition-colors font-sans">{{ prop.nome }}</span>
                          <span class="text-[9px] text-gray-500 font-mono mt-0.5 truncate">{{ prop.time }}</span>
                        </div>
                      </div>
                      
                      <div class="col-span-2 flex flex-col items-center">
                        <span class="text-[13px] font-mono text-[#10B981] font-black drop-shadow-[0_0_5px_rgba(16,185,129,0.3)]">{{ prop.prob }}%</span>
                      </div>
                      
                      <div class="col-span-2 flex flex-col items-center">
                        <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded border" :class="parseFloat(prop.war) > 0.15 ? 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30' : 'text-gray-400 bg-black/40 border-gray-700'">+{{ prop.war }}</span>
                      </div>
                      
                      <div class="col-span-3 flex justify-end pr-1">
                        <span class="text-sm font-mono font-bold bg-[#0b0f19] px-3 py-1.5 rounded-lg border border-white/10 text-white shadow-inner">@{{ prop.fair }}</span>
                      </div>
                    </div>
                    
                    <div v-if="currentPlayerProps.length === 0" class="text-center text-[10px] text-gray-500 py-10 font-mono uppercase tracking-widest flex-1 flex flex-col items-center justify-center gap-2 opacity-50 border border-dashed border-white/5 rounded-xl mt-1">
                      <User size="24" class="text-gray-600"/> Dados Isolados Indisponíveis
                    </div>
                  </div>
                </div>
              </transition>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'quant_fbref'" titulo="Matrix & FBref Engine" class="h-full flex flex-col border-none bg-transparent">
            <template #icone><BrainCircuit :size="16" class="text-[#a855f7]" /></template>
            <template #acoes>
              <div class="flex items-center gap-1 bg-black/40 p-1 rounded-lg border border-white/5 shadow-inner">
                <button @click="quantTab = 'matrix'" class="text-[9px] font-bold uppercase tracking-widest px-3 py-1.5 rounded-md transition-all" :class="quantTab === 'matrix' ? 'bg-[#a855f7]/20 text-[#a855f7] shadow-sm' : 'text-gray-500 hover:text-white'">Matrix</button>
                <button @click="quantTab = 'fbref'" class="text-[9px] font-bold uppercase tracking-widest px-3 py-1.5 rounded-md transition-all" :class="quantTab === 'fbref' ? 'bg-[#a855f7]/20 text-[#a855f7] shadow-sm' : 'text-gray-500 hover:text-white'">FBref</button>
              </div>
            </template>
            
            <div class="flex flex-col h-full mt-4 overflow-hidden">
              <transition name="fade-scale" mode="out-in">
                
                <div v-if="quantTab === 'matrix'" class="flex flex-col gap-3 h-full overflow-y-auto custom-scrollbar pr-2 pb-2">
                  <div v-if="!partida.quantMetrics || partida.quantMetrics.length === 0" class="flex-1 flex flex-col gap-3 items-center justify-center text-[10px] text-gray-500 font-mono uppercase tracking-widest text-center bg-[#121927] rounded-xl border border-dashed border-white/5 opacity-50">
                    <BrainCircuit size="24"/> Extraindo Tensores da Alpha Matrix...
                  </div>
                  
                  <div v-for="(stat, i) in partida.quantMetrics" :key="'qm'+i" class="flex flex-col gap-2.5 bg-[#121927] p-4 rounded-xl border border-white/5 hover:border-white/10 transition-colors shadow-sm">
                    <div class="flex justify-between items-end px-1">
                      <span class="font-mono text-sm w-12 text-left" :class="parseFloat(stat.casa) >= parseFloat(stat.fora) ? 'text-white font-black drop-shadow-[0_0_5px_rgba(255,255,255,0.3)]' : 'text-gray-500 font-bold'">{{ stat.casa }}{{ stat.sufixo }}</span>
                      <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold text-center bg-black/40 px-3 py-1 rounded-full border border-white/5">{{ stat.nome }}</span>
                      <span class="font-mono text-sm w-12 text-right" :class="parseFloat(stat.fora) >= parseFloat(stat.casa) ? 'text-white font-black drop-shadow-[0_0_5px_rgba(255,255,255,0.3)]' : 'text-gray-500 font-bold'">{{ stat.fora }}{{ stat.sufixo }}</span>
                    </div>
                    <div class="w-full h-3 bg-[#0b0f19] rounded-full flex overflow-hidden shadow-inner border border-white/5 mt-1">
                      <div class="h-full transition-all duration-1000 ease-out relative" :style="`width: ${(parseFloat(stat.casa) / ((parseFloat(stat.casa) + parseFloat(stat.fora)) || 1)) * 100}%; background-color: ${partida.corCasa || '#10B981'}`"></div>
                      <div class="h-full bg-black w-1 z-10 shrink-0"></div>
                      <div class="h-full transition-all duration-1000 ease-out relative" :style="`width: ${(parseFloat(stat.fora) / ((parseFloat(stat.casa) + parseFloat(stat.fora)) || 1)) * 100}%; background-color: ${partida.corFora || '#3B82F6'}`"></div>
                    </div>
                    <span class="text-[9px] text-gray-500 text-center block font-mono uppercase mt-1">{{ stat.desc }}</span>
                  </div>
                </div>

                <div v-else class="flex flex-col h-full bg-[#121927] rounded-xl border border-white/5 shadow-inner overflow-hidden">
                  <div class="flex items-center justify-between p-2 border-b border-white/10 bg-black/40 shrink-0">
                     <select v-model="fbrefSubTab" class="bg-black/60 text-[10px] text-white border border-gray-700 rounded-lg px-3 py-1.5 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-[#a855f7] transition-colors w-full mx-2 shadow-inner">
                      <option value="ofensivas">Ofensivas</option>
                      <option value="defensivas">Defensivas</option>
                      <option value="avancadas">Avançadas</option>
                      <option value="game_state">Game State (xG Flow)</option>
                    </select>
                  </div>
                  
                  <div class="flex flex-col overflow-y-auto custom-scrollbar flex-1 p-2">
                    <div v-if="fbrefSubTab === 'game_state'" class="flex flex-col gap-4">
                      <p class="text-[10px] text-gray-400 mb-1 leading-relaxed px-2 text-center mt-2">Métricas de <strong class="text-white">xG / 90 min</strong> baseadas no estado da partida.</p>
                      
                      <div class="grid grid-cols-12 text-[9px] uppercase tracking-widest font-bold text-gray-500 border-b border-white/10 pb-2 px-2 text-center">
                        <span class="col-span-4 text-left">Time</span><span class="col-span-3 text-[#10B981]">À Frente</span><span class="col-span-3">Empatado</span><span class="col-span-2 text-red-400">Atrás</span>
                      </div>
                      
                      <div class="flex flex-col gap-2">
                        <div v-for="(gs, i) in (partida.gameState || [])" :key="'gs'+i" class="grid grid-cols-12 items-center bg-black/40 p-3 rounded-xl border border-white/5 shadow-inner transition-colors hover:border-white/10">
                          <span class="col-span-4 text-xs font-bold truncate pr-2 font-sans" :style="`color: ${gs.time === partida.casa ? partida.corCasa : partida.corFora}`">{{ gs.time }}</span>
                          <span class="col-span-3 text-center font-mono text-xs text-white bg-[#10B981]/10 border border-[#10B981]/20 rounded-md mx-1.5 py-1.5 font-bold">{{ gs.vencendo }}</span>
                          <span class="col-span-3 text-center font-mono text-xs text-white bg-gray-500/10 border border-gray-500/20 rounded-md mx-1.5 py-1.5 font-bold">{{ gs.empatando }}</span>
                          <span class="col-span-2 text-center font-mono text-xs text-white bg-red-500/10 border border-red-500/20 rounded-md mx-1.5 py-1.5 font-bold">{{ gs.perdendo }}</span>
                        </div>
                        <div v-if="!partida.gameState || partida.gameState.length === 0" class="text-center text-[10px] text-gray-500 py-10 font-mono uppercase tracking-widest border border-dashed border-white/5 rounded-xl opacity-50 mt-2">Game State Indisponível</div>
                      </div>
                    </div>

                    <div v-else class="flex flex-col gap-3">
                      <div v-if="currentFbrefStats.length === 0" class="text-center text-[10px] text-gray-500 py-10 font-mono uppercase tracking-widest border border-dashed border-white/5 rounded-xl opacity-50 mt-2">Métricas Indisponíveis</div>
                      <div v-for="(stat, i) in currentFbrefStats" :key="'fbref'+i" class="flex flex-col gap-2 bg-black/40 p-4 rounded-xl border border-white/5 hover:border-white/10 transition-colors">
                        <div class="flex justify-between items-end px-1">
                          <span class="font-mono text-sm w-12 text-left" :class="parseFloat(stat.casa) >= parseFloat(stat.fora) ? 'text-white font-bold drop-shadow-[0_0_5px_rgba(255,255,255,0.3)]' : 'text-gray-500'">{{ stat.casa }}{{ stat.sufixo }}</span>
                          <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold text-center bg-[#0b0f19] px-2 py-0.5 rounded border border-white/5">{{ stat.nome }}</span>
                          <span class="font-mono text-sm w-12 text-right" :class="parseFloat(stat.fora) >= parseFloat(stat.casa) ? 'text-white font-bold drop-shadow-[0_0_5px_rgba(255,255,255,0.3)]' : 'text-gray-500'">{{ stat.fora }}{{ stat.sufixo }}</span>
                        </div>
                        <div class="w-full h-2 bg-[#0b0f19] rounded-full flex overflow-hidden shadow-inner border border-white/5 mt-1">
                          <div class="h-full transition-all duration-1000 ease-out relative" :style="`width: ${(parseFloat(stat.casa) / ((parseFloat(stat.casa) + parseFloat(stat.fora)) || 1)) * 100}%; background-color: ${partida.corCasa || '#10B981'}`"></div>
                          <div class="h-full bg-black w-1 z-10 shrink-0"></div>
                          <div class="h-full transition-all duration-1000 ease-out relative" :style="`width: ${(parseFloat(stat.fora) / ((parseFloat(stat.casa) + parseFloat(stat.fora)) || 1)) * 100}%; background-color: ${partida.corFora || '#3B82F6'}`"></div>
                        </div>
                      </div>
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

// 🛑 A CURA DA ROTA (Render vs Localhost S-Tier Validation)
const rawApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_BASE_URL = rawApiUrl.endsWith('/api/v1') ? rawApiUrl : `${rawApiUrl.replace(/\/$/, '')}/api/v1`;
const globalState = inject('globalState'); 

const isLoading = ref(true);

const contextTab = ref("stats");
const quantTab = ref("matrix");
const mercadosTab = ref("value");
const fbrefSubTab = ref("avancadas");

// Filtros Numéricos Dinâmicos fixados e otimizados
const filtroJogosH2H = ref("5");
const filtroJogosForma = ref("5");
const propsTab = ref("chutes");
const filtroMercado = ref("all");

// Matriz do Layout Drag & Drop
const layoutWidgets = ref([
  { id: 'contexto', span: 'col-span-1 lg:col-span-5 xl:col-span-5' },
  { id: 'forma', span: 'col-span-1 lg:col-span-4 xl:col-span-4' },
  { id: 'ml', span: 'col-span-1 lg:col-span-3 xl:col-span-3' },
  { id: 'mercados_props', span: 'col-span-1 lg:col-span-6 xl:col-span-6' },
  { id: 'quant_fbref', span: 'col-span-1 lg:col-span-6 xl:col-span-6' }
]);

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

const getTeamLogo = (teamName) => {
  if (!teamName || teamName === '---') return '';
  return `${API_BASE_URL}/teams/shield/${encodeURIComponent(teamName.trim())}`;
};

const handleImageError = (e) => { 
  e.target.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'; 
};

// ==================================================
// MOTOR DE BUSCA DEFENSIVO S-TIER
// ==================================================
const carregarDadosDaPartida = async () => {
  isLoading.value = true;
  try {
    const token = localStorage.getItem('betgenius_token');
    let matchId = 0;
    if (globalState && globalState.activeMatch) {
      matchId = typeof globalState.activeMatch === 'object' ? (globalState.activeMatch.id || 0) : globalState.activeMatch;
    }
    
    // Axios request properly routed to the normalized endpoint
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
// COMPUTED PROPERTIES
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
  return (partida.value.indFormCasa || []).slice(0, 5); // Fixed to 5
});

const formaForaFiltrada = computed(() => {
  return (partida.value.indFormFora || []).slice(0, 5); // Fixed to 5
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
.glass-card { background: rgba(11, 15, 25, 0.9); backdrop-filter: blur(30px); border-radius: 20px; border-left: 1px solid rgba(255,255,255,0.05); border-right: 1px solid rgba(255,255,255,0.05);}
.skeleton-pulse { background: linear-gradient(90deg, rgba(255,255,255,0.02) 25%, rgba(255,255,255,0.05) 50%, rgba(255,255,255,0.02) 75%); background-size: 400% 100%; animation: skeletonLoading 1.5s infinite ease-in-out; }
@keyframes skeletonLoading { 0% { background-position: 100% 50%; } 100% { background-position: 0 50%; } }
.ghost-widget { opacity: 0.2 !important; border: 2px dashed rgba(255,255,255,0.3) !important; transform: scale(0.95); border-radius: 16px;}
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.15); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.3); }

.fade-scale-enter-active, .fade-scale-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.fade-scale-enter-from, .fade-scale-leave-to { opacity: 0; transform: scale(0.98); }

.list-enter-active, .list-leave-active { transition: all 0.4s ease; }
.list-enter-from { opacity: 0; transform: translateX(-20px); }
.list-leave-to { opacity: 0; transform: translateX(20px); }

.fade-in-up { animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
@keyframes fadeInUp { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }
</style>