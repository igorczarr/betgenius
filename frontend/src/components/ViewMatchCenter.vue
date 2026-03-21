<template>
  <div class="flex flex-col gap-6 w-full h-full relative fade-in-up pb-10">
    
    <div class="glass-card p-6 md:p-8 relative flex flex-col md:flex-row justify-between items-center border-t-4 shadow-[0_15px_40px_rgba(0,0,0,0.6)]" :style="`border-color: ${partida.corCasa}`">
      <div class="absolute -right-20 -top-20 w-72 h-72 rounded-full blur-[100px] pointer-events-none opacity-20" :style="`background-color: ${partida.corCasa}`"></div>
      <div class="absolute -left-20 -bottom-20 w-72 h-72 rounded-full blur-[100px] pointer-events-none opacity-20" :style="`background-color: ${partida.corFora}`"></div>
      
      <div class="flex items-center gap-5 w-full md:w-2/5 justify-end z-10">
        <div class="text-right">
          <h2 class="text-3xl font-mono text-white tracking-wider drop-shadow-md">{{ partida.casa }}</h2>
          <div class="flex items-center justify-end gap-2 mt-1">
            <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold">{{ partida.posCasa }}º Lugar •</span>
            <div class="flex gap-0.5">
              <span v-for="(f, i) in partida.formCasa" :key="'fc'+i" class="w-4 h-4 flex items-center justify-center rounded-[3px] text-[8px] font-bold text-white shadow-sm" :class="f === 'W' ? 'bg-[#10B981]' : (f === 'D' ? 'bg-gray-500' : 'bg-red-500')">{{ f }}</span>
            </div>
          </div>
        </div>
        <div class="w-20 h-20 rounded-full bg-[#121927] border-[3px] flex items-center justify-center shadow-[0_0_25px_rgba(0,0,0,0.8)] relative" :style="`border-color: ${partida.corCasa}`">
          <Shield :size="36" :color="partida.corCasa" class="drop-shadow-[0_0_8px_currentColor]" />
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
        <div class="w-20 h-20 rounded-full bg-[#121927] border-[3px] flex items-center justify-center shadow-[0_0_25px_rgba(0,0,0,0.8)] relative" :style="`border-color: ${partida.corFora}`">
          <ShieldAlert :size="36" :color="partida.corFora" class="drop-shadow-[0_0_8px_currentColor]" />
        </div>
        <div class="text-left">
          <h2 class="text-3xl font-mono text-white tracking-wider drop-shadow-md">{{ partida.fora }}</h2>
          <div class="flex items-center justify-start gap-2 mt-1">
            <div class="flex gap-0.5">
              <span v-for="(f, i) in partida.formFora" :key="'ff'+i" class="w-4 h-4 flex items-center justify-center rounded-[3px] text-[8px] font-bold text-white shadow-sm" :class="f === 'W' ? 'bg-[#10B981]' : (f === 'D' ? 'bg-gray-500' : 'bg-red-500')">{{ f }}</span>
            </div>
            <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold">• {{ partida.posFora }}º Lugar</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="isLoading" class="grid grid-cols-1 xl:grid-cols-3 gap-6 mt-2">
      <div v-for="i in 8" :key="i" class="h-[400px] skeleton-pulse rounded-2xl border border-white/5 shadow-2xl"></div>
    </div>

    <draggable 
      v-else
      v-model="layoutWidgets" 
      item-key="id" 
      class="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start mt-2" 
      handle=".drag-handle" 
      ghost-class="ghost-widget"
      animation="250"
    >
      <template #item="{ element }">
        <div :class="element.span" class="relative w-full group/widget h-full">
          
          <div class="drag-handle absolute -top-3 left-1/2 -translate-x-1/2 z-[80] opacity-0 group-hover/widget:opacity-100 cursor-move p-1.5 px-6 bg-black text-bet-primary rounded-b-xl border border-white/10 shadow-[0_10px_20px_rgba(0,0,0,0.9)] transition-all hover:bg-bet-primary hover:text-black">
            <GripHorizontal size="16" />
          </div>

          <WidgetCard v-if="element.id === 'contexto'" titulo="Overview & Head-to-Head" class="h-full">
            <template #icone><History :size="16" color="var(--bet-primary)" /></template>
            
            <div class="flex flex-col gap-4 h-full">
              <div class="flex flex-wrap gap-2 bg-black/30 p-2 rounded-xl border border-white/5 shadow-inner">
                <select v-model="filtroJogosH2H" class="bg-black text-[10px] text-white border border-gray-700 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-bet-primary focus:border-bet-primary transition-colors">
                  <option value="5">Últimos 5</option><option value="10">Últimos 10</option><option value="15">Últimos 15</option>
                </select>
                <select v-model="filtroLocalH2H" class="bg-black text-[10px] text-white border border-gray-700 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-bet-primary focus:border-bet-primary transition-colors">
                  <option value="all">Casa/Fora</option><option value="home">Som. Casa</option><option value="away">Som. Fora</option>
                </select>
                <select v-model="filtroCompH2H" class="bg-black text-[10px] text-white border border-gray-700 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-bet-primary flex-1 focus:border-bet-primary transition-colors">
                  <option value="all">Todas Comp.</option><option value="league">Premier League</option>
                </select>
              </div>

              <div class="flex flex-col border border-white/5 rounded-xl overflow-hidden bg-black/10 shadow-sm">
                <div v-for="(h2h, i) in partida.historico" :key="'h2h'+i" class="flex justify-between items-center p-2.5 text-xs font-mono even:bg-white/[0.02] hover:bg-white/5 transition-colors group">
                  <span class="text-gray-500 w-16 text-[9px] uppercase">{{ h2h.data }}</span>
                  <span class="w-20 text-right truncate group-hover:text-white transition-colors" :class="{'text-bet-primary font-bold': h2h.win === 'casa', 'text-gray-400': h2h.win !== 'casa'}">{{ h2h.casa }}</span>
                  <span class="bg-[#121927] px-2.5 py-0.5 rounded text-white font-bold border border-gray-700 shadow-inner tracking-widest">{{ h2h.placar }}</span>
                  <span class="w-20 text-left truncate group-hover:text-white transition-colors" :class="{'text-bet-primary font-bold': h2h.win === 'fora', 'text-gray-400': h2h.win !== 'fora'}">{{ h2h.fora }}</span>
                </div>
              </div>

              <div class="mt-1 border border-white/10 rounded-lg overflow-hidden bg-black/20 shadow-inner flex-1">
                <div class="grid grid-cols-3 bg-black/60 p-2.5 text-[9px] uppercase tracking-widest text-gray-500 font-bold text-center border-b border-white/10">
                  <span class="text-left text-white truncate px-2">{{ partida.casa }}</span>
                  <span>Métrica ({{ filtroJogosH2H }})</span>
                  <span class="text-right text-white truncate px-2">{{ partida.fora }}</span>
                </div>
                <div class="flex flex-col text-[11px] font-mono text-gray-300">
                  <div class="grid grid-cols-3 py-2 px-3 border-b border-white/5 even:bg-white/[0.02] hover:bg-white/10 transition-colors"><span class="font-semibold">{{ partida.stats.pts }} <span class="text-[9px] text-gray-500">({{ partida.stats.pts_j }})</span></span><span class="text-center text-[9px] text-gray-500 font-sans tracking-widest uppercase">PTS / J</span><span class="text-right font-semibold">{{ partida.stats.pts_f }} <span class="text-[9px] text-gray-500">({{ partida.stats.pts_jf }})</span></span></div>
                  <div class="grid grid-cols-3 py-2 px-3 border-b border-white/5 even:bg-white/[0.02] hover:bg-white/10 transition-colors"><span>{{ partida.stats.win }}%</span><span class="text-center text-[9px] text-gray-500 font-sans tracking-widest uppercase">Win Rate</span><span class="text-right">{{ partida.stats.win_f }}%</span></div>
                  <div class="grid grid-cols-3 py-2 px-3 border-b border-white/5 even:bg-white/[0.02] hover:bg-white/10 transition-colors"><span>{{ partida.stats.avg_g }} <span class="text-gray-600">/</span> {{ partida.stats.avg_gc }}</span><span class="text-center text-[9px] text-gray-500 font-sans tracking-widest uppercase">Gols F/S</span><span class="text-right">{{ partida.stats.avg_gf }} <span class="text-gray-600">/</span> {{ partida.stats.avg_gcf }}</span></div>
                  <div class="grid grid-cols-3 py-2 px-3 border-b border-white/5 even:bg-white/[0.02] hover:bg-white/10 transition-colors"><span class="text-bet-primary font-bold">{{ partida.stats.over }}%</span><span class="text-center text-[9px] text-gray-500 font-sans tracking-widest uppercase">Over 2.5</span><span class="text-right text-bet-primary font-bold">{{ partida.stats.over_f }}%</span></div>
                  <div class="grid grid-cols-3 py-2 px-3 border-b border-white/5 even:bg-white/[0.02] hover:bg-white/10 transition-colors"><span>{{ partida.stats.btts }}%</span><span class="text-center text-[9px] text-gray-500 font-sans tracking-widest uppercase">BTTS</span><span class="text-right">{{ partida.stats.btts_f }}%</span></div>
                  <div class="grid grid-cols-3 py-2 px-3 border-b border-white/5 even:bg-white/[0.02] hover:bg-white/10 transition-colors"><span>{{ partida.stats.pos }}%</span><span class="text-center text-[9px] text-gray-500 font-sans tracking-widest uppercase">Posse</span><span class="text-right">{{ partida.stats.pos_f }}%</span></div>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-3 mt-auto">
                <div class="bg-[#121927] border border-white/5 p-3 rounded-xl flex flex-col gap-1 shadow-inner hover:border-yellow-500/30 transition-colors group">
                  <div class="flex items-center gap-2 mb-1"><Gavel size="12" class="text-yellow-500 group-hover:animate-bounce"/><span class="text-[10px] font-bold text-white uppercase tracking-widest truncate">{{ partida.arbitro }}</span></div>
                  <div class="flex justify-between font-mono text-[10px] text-gray-400"><span>Y: <strong class="text-yellow-400">{{ partida.arb_amarelos }}</strong></span><span>R: <strong class="text-red-400">{{ partida.arb_vermelhos }}</strong></span></div>
                </div>
                <div class="bg-[#121927] border border-white/5 p-3 rounded-xl flex flex-col gap-1 shadow-inner hover:border-blue-400/30 transition-colors group">
                  <div class="flex items-center gap-2 mb-1"><CloudRain size="12" class="text-blue-400 group-hover:animate-pulse"/><span class="text-[10px] font-bold text-white uppercase tracking-widest">Clima</span></div>
                  <div class="flex justify-between font-mono text-[10px] text-gray-400 items-center"><span class="truncate pr-2">{{ partida.clima }}</span><span class="text-white font-bold">{{ partida.temp }}°C</span></div>
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'forma'" titulo="Performance Individual Recente" class="h-full">
            <template #icone><LayoutList :size="16" color="var(--bet-secondary)" /></template>
            <template #acoes>
              <select v-model="filtroJogosForma" class="bg-black/40 text-[10px] text-white border border-white/10 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-bet-primary transition-colors">
                <option value="5">5 Jogos</option><option value="10">10 Jogos</option><option value="15">15 Jogos</option>
              </select>
            </template>
            
            <div class="flex gap-5 h-full mt-3">
              <div class="w-1/2 flex flex-col gap-3">
                <div class="text-[10px] uppercase font-bold tracking-widest border-b border-white/10 pb-2 flex justify-between items-center">
                  <span :style="`color: ${partida.corCasa}`" class="text-sm drop-shadow-md truncate max-w-[80px]">{{ partida.casa }}</span> <span class="text-gray-400 bg-white/5 px-2 py-0.5 rounded shadow-inner">CASA</span>
                </div>
                <div class="flex flex-col gap-2 flex-1">
                  <div v-for="(jogo, i) in partida.indFormCasa" :key="'ih'+i" class="bg-[#121927] border border-white/5 p-3 rounded-xl flex flex-col gap-2 hover:bg-white/5 transition-colors shadow-sm group">
                    <div class="flex justify-between items-center text-[10px] font-mono">
                      <span class="text-gray-500 uppercase">{{ jogo.data }}</span>
                      <span class="font-bold uppercase px-2 py-0.5 rounded shadow-inner" :class="jogo.res === 'W' ? 'bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/20' : (jogo.res === 'L' ? 'bg-red-500/20 text-red-400 border border-red-500/20' : 'bg-gray-500/20 text-gray-300 border border-gray-500/20')">{{ jogo.res }}</span>
                    </div>
                    <div class="flex justify-between items-center text-xs">
                      <span class="text-gray-300 truncate w-24 font-semibold group-hover:text-white transition-colors">{{ jogo.adv }}</span>
                      <span class="font-bold font-mono text-white bg-black/60 px-2 py-1 rounded border border-gray-700">{{ jogo.placar }}</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div class="w-px bg-gradient-to-b from-transparent via-white/10 to-transparent h-full"></div>
              
              <div class="w-1/2 flex flex-col gap-3">
                <div class="text-[10px] uppercase font-bold tracking-widest border-b border-white/10 pb-2 flex justify-between items-center">
                  <span class="text-gray-400 bg-white/5 px-2 py-0.5 rounded shadow-inner">FORA</span> <span :style="`color: ${partida.corFora}`" class="text-sm drop-shadow-md truncate max-w-[80px] text-right">{{ partida.fora }}</span>
                </div>
                <div class="flex flex-col gap-2 flex-1">
                  <div v-for="(jogo, i) in partida.indFormFora" :key="'ia'+i" class="bg-[#121927] border border-white/5 p-3 rounded-xl flex flex-col gap-2 hover:bg-white/5 transition-colors shadow-sm group">
                    <div class="flex justify-between items-center text-[10px] font-mono">
                      <span class="font-bold uppercase px-2 py-0.5 rounded shadow-inner" :class="jogo.res === 'W' ? 'bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/20' : (jogo.res === 'L' ? 'bg-red-500/20 text-red-400 border border-red-500/20' : 'bg-gray-500/20 text-gray-300 border border-gray-500/20')">{{ jogo.res }}</span>
                      <span class="text-gray-500 uppercase">{{ jogo.data }}</span>
                    </div>
                    <div class="flex justify-between items-center text-xs">
                      <span class="font-bold font-mono text-white bg-black/60 px-2 py-1 rounded border border-gray-700">{{ jogo.placar }}</span>
                      <span class="text-gray-300 truncate w-24 text-right font-semibold group-hover:text-white transition-colors">{{ jogo.adv }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'fbref'" titulo="FBref & Game State Analytics" class="h-full">
            <template #icone><LineChart :size="16" color="#10B981" /></template>
            <template #acoes>
              <select v-model="fbrefTab" class="bg-black/40 text-[10px] text-white border border-white/10 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-[#10B981] transition-colors">
                <option value="ofensivas">Ofensivas</option>
                <option value="defensivas">Defensivas</option>
                <option value="avancadas">Avançadas</option>
                <option value="variadas">Variadas</option>
                <option value="game_state">Game State (Situação)</option>
              </select>
            </template>

            <div class="flex flex-col justify-between h-full">
              <div v-if="fbrefTab === 'game_state'" class="flex flex-col gap-4 mt-4 animate-fade-in">
                <p class="text-[10px] text-gray-400 mb-2 leading-relaxed px-1">Métricas de produção de <strong class="text-white">xG a cada 90 min</strong> baseadas no estado da partida (Liderando, Empatando, Perdendo).</p>
                
                <div class="grid grid-cols-12 text-[9px] uppercase tracking-widest font-bold text-gray-500 border-b border-white/10 pb-2">
                  <span class="col-span-4">Equipe / Estado</span>
                  <span class="col-span-3 text-center text-green-400">À Frente (W)</span>
                  <span class="col-span-3 text-center text-gray-400">Empatado (D)</span>
                  <span class="col-span-2 text-center text-red-400">Atrás (L)</span>
                </div>
                
                <div class="flex flex-col gap-3 mt-2">
                  <div v-for="(gs, i) in partida.gameState" :key="'gs'+i" class="grid grid-cols-12 items-center bg-black/20 p-3 rounded-lg border border-white/5 shadow-inner">
                    <span class="col-span-4 text-xs font-bold text-white" :style="`color: ${gs.time === partida.casa ? partida.corCasa : partida.corFora}`">{{ gs.time }}</span>
                    <span class="col-span-3 text-center font-mono text-xs text-white bg-[#10B981]/10 border border-[#10B981]/20 rounded mx-1 py-1">{{ gs.vencendo }} <span class="text-[8px] text-gray-500">xG/90</span></span>
                    <span class="col-span-3 text-center font-mono text-xs text-white bg-gray-500/10 border border-gray-500/20 rounded mx-1 py-1">{{ gs.empatando }} <span class="text-[8px] text-gray-500">xG/90</span></span>
                    <span class="col-span-2 text-center font-mono text-xs text-white bg-red-500/10 border border-red-500/20 rounded mx-1 py-1">{{ gs.perdendo }}</span>
                  </div>
                </div>
              </div>

              <div v-else class="flex flex-col gap-5 mt-4">
                <div v-for="(stat, i) in currentFbrefStats" :key="'fbref'+i" class="flex flex-col gap-2 group">
                  <div class="flex justify-between items-end px-1">
                    <span class="font-mono text-sm w-12 text-left" :class="stat.casa > stat.fora ? 'text-white font-bold drop-shadow-[0_0_5px_rgba(255,255,255,0.3)]' : 'text-gray-500'">{{ stat.casa }}{{ stat.sufixo }}</span>
                    <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold group-hover:text-bet-primary transition-colors">{{ stat.nome }}</span>
                    <span class="font-mono text-sm w-12 text-right" :class="stat.fora > stat.casa ? 'text-white font-bold drop-shadow-[0_0_5px_rgba(255,255,255,0.3)]' : 'text-gray-500'">{{ stat.fora }}{{ stat.sufixo }}</span>
                  </div>
                  <div class="w-full h-2.5 bg-[#121927] rounded-full flex overflow-hidden shadow-inner border border-white/5">
                    <div class="h-full transition-all duration-700 relative" :style="`width: ${(stat.casa / (stat.casa + stat.fora)) * 100}%; background-color: ${partida.corCasa}`">
                      <div class="absolute inset-0 bg-gradient-to-r from-transparent to-white/20"></div>
                    </div>
                    <div class="h-full bg-black w-1 z-10"></div>
                    <div class="h-full transition-all duration-700 relative" :style="`width: ${(stat.fora / (stat.casa + stat.fora)) * 100}%; background-color: ${partida.corFora}`">
                      <div class="absolute inset-0 bg-gradient-to-l from-transparent to-white/20"></div>
                    </div>
                  </div>
                  <span class="text-[8px] text-gray-500 text-center block leading-tight font-mono">{{ stat.desc }}</span>
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'jogadores'" titulo="Player Props & Impact (WAR)" class="h-full">
            <template #icone><Crosshair :size="16" color="#a855f7" /></template>
            <template #acoes>
              <select v-model="propsTab" class="bg-black/40 text-[10px] text-white border border-white/10 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-[#a855f7] transition-colors">
                <option value="chutes">Chutes no Gol</option>
                <option value="gols">Gols Marcados</option>
                <option value="assists">Assistências</option>
                <option value="faltas">Faltas</option>
              </select>
            </template>

            <div class="flex flex-col gap-2 mt-2 h-full">
              <div class="grid grid-cols-12 px-3 pb-2 border-b border-white/10 text-[9px] uppercase font-bold text-gray-500 tracking-widest bg-black/40 rounded-t-lg pt-3">
                <span class="col-span-5">Jogador Em Foco</span>
                <span class="col-span-2 text-center">IA Prob</span>
                <span class="col-span-2 text-center">WAR</span>
                <span class="col-span-3 text-right pr-2">Fair Odd</span>
              </div>
              
              <div class="flex flex-col gap-1.5 overflow-y-auto custom-scrollbar flex-1 pb-2 pr-1">
                <div v-for="(prop, i) in currentPlayerProps" :key="'prop'+i" class="grid grid-cols-12 items-center bg-black/10 even:bg-white/[0.02] hover:bg-white/5 border-b border-white/5 p-3 transition-colors group cursor-default">
                  
                  <div class="col-span-5 flex items-center gap-3 pl-1">
                    <div class="w-8 h-8 rounded-full flex items-center justify-center border-2 shadow-[0_0_10px_rgba(0,0,0,0.5)] shrink-0 bg-black/60" :style="`border-color: ${prop.time === partida.casa ? partida.corCasa : partida.corFora}80`">
                      <User size="14" :color="prop.time === partida.casa ? partida.corCasa : partida.corFora" />
                    </div>
                    <div class="flex flex-col truncate">
                      <span class="text-xs font-bold text-white truncate group-hover:text-[#a855f7] transition-colors">{{ prop.nome }}</span>
                      <span class="text-[9px] text-gray-500 font-mono mt-0.5">{{ prop.time }}</span>
                    </div>
                  </div>
                  
                  <div class="col-span-2 flex flex-col items-center">
                    <span class="text-xs font-mono text-[#10B981] font-bold drop-shadow-[0_0_5px_rgba(16,185,129,0.3)]">{{ prop.prob }}%</span>
                  </div>

                  <div class="col-span-2 flex flex-col items-center">
                    <span class="text-[10px] font-mono font-bold px-1.5 rounded border border-gray-600" :class="prop.war > 0.15 ? 'text-yellow-400 bg-yellow-400/10' : 'text-gray-400 bg-black/40'">+{{ prop.war }}</span>
                  </div>
                  
                  <div class="col-span-3 flex justify-end pr-1">
                    <span class="text-xs font-mono font-bold bg-[#121927] px-3 py-1 rounded border border-gray-700 text-white group-hover:border-[#a855f7] transition-colors shadow-inner">{{ prop.fair }}</span>
                  </div>
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'mercados'" titulo="Value Finder & ATS Tracker" class="h-full">
            <template #icone><Percent :size="16" color="#3b82f6" /></template>
            <template #acoes>
              <select v-model="filtroMercado" class="bg-black/40 text-[10px] text-white border border-white/10 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-[#3b82f6] transition-colors">
                <option value="all">Todos Mercados</option>
                <option value="match_odds">Match Odds</option>
                <option value="goals">Gols (O/U)</option>
                <option value="handicap">Handicap</option>
                <option value="props">Player Props</option>
              </select>
            </template>
            
            <div class="flex flex-col h-full mt-3">
              <div class="grid grid-cols-12 px-3 pb-2 border-b border-white/10 text-[9px] uppercase font-bold text-gray-500 tracking-widest bg-black/40 rounded-t-lg pt-3">
                <span class="col-span-5 pl-1">Mercado (Aposta)</span>
                <span class="col-span-2 text-center">IA Prob</span>
                <span class="col-span-3 text-center">Line Movement</span>
                <span class="col-span-2 text-right pr-2">Ação</span>
              </div>
              
              <div class="flex flex-col overflow-y-auto custom-scrollbar flex-1 pb-2">
                <div v-for="(mercado, i) in currentMercados" :key="'m'+i" class="grid grid-cols-12 items-center bg-black/10 even:bg-white/[0.02] hover:bg-black/40 border-b border-white/5 p-3 transition-all relative group overflow-hidden">
                  <div v-if="mercado.ev > 0" class="absolute top-0 left-0 w-1 h-full bg-[#10B981] shadow-[0_0_10px_#10B981]"></div>
                  
                  <div class="col-span-5 flex flex-col pl-3">
                    <span class="text-xs font-bold text-white truncate">{{ mercado.nome }}</span>
                    <div class="flex items-center gap-1.5 mt-1">
                      <span v-if="mercado.ev > 0" class="text-[9px] bg-[#10B981]/10 text-[#10B981] px-1.5 py-0.5 rounded border border-[#10B981]/20 font-bold uppercase tracking-wider">+{{ mercado.ev }}% EV</span>
                      <span v-else class="text-[9px] bg-red-500/10 text-red-400 px-1.5 py-0.5 rounded border border-red-500/20 font-bold uppercase tracking-wider">{{ mercado.ev }}% EV</span>
                    </div>
                  </div>
                  
                  <div class="col-span-2 flex flex-col items-center justify-center">
                    <span class="text-xs font-mono font-bold" :class="mercado.ev > 0 ? 'text-[#10B981] drop-shadow-[0_0_5px_rgba(16,185,129,0.3)]' : 'text-gray-300'">{{ mercado.prob }}%</span>
                    <span class="text-[8px] text-gray-500 font-mono uppercase mt-0.5">Fair: {{ mercado.fair }}</span>
                  </div>
                  
                  <div class="col-span-3 flex flex-col items-center justify-center border-l border-white/5 pl-2">
                    <div class="flex items-center gap-1 text-xs font-mono font-bold">
                      <span class="text-gray-500 line-through text-[10px]">{{ mercado.openOdd }}</span>
                      <ArrowRight size="10" class="text-gray-600" />
                      <span class="text-white" :class="mercado.openOdd > mercado.bookie ? 'text-red-400' : 'text-green-400'">{{ mercado.bookie }}</span>
                    </div>
                    <span class="text-[8px] text-gray-500 font-bold uppercase tracking-widest mt-0.5">{{ mercado.casaNome }}</span>
                  </div>
                  
                  <div class="col-span-2 flex justify-end pr-1">
                    <button class="w-9 h-9 rounded-xl bg-[#121927] border border-white/10 flex items-center justify-center text-gray-400 hover:bg-[#3b82f6] hover:border-[#3b82f6] hover:text-white transition-all shadow-lg hover:scale-105 hover:shadow-[0_0_15px_rgba(59,130,246,0.4)]">
                      <Plus size="18" strokeWidth="2.5" />
                    </button>
                  </div>
                </div>
                
                <div v-if="currentMercados.length === 0" class="text-center text-xs text-gray-500 py-10 font-mono uppercase tracking-widest bg-black/10 flex-1 flex items-center justify-center">
                  Nenhum mercado encontrado
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'ml'" titulo="Poisson Matrix & xG Momentum" class="h-full">
            <template #icone><Grid :size="16" color="var(--bet-warning)" /></template>
            <template #acoes>
              <select v-model="mlTab" class="bg-black/40 text-[10px] text-white border border-white/10 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-yellow-500 transition-colors">
                <option value="poisson">Poisson Heatmap</option>
                <option value="xgflow">xG Flow (Momentum)</option>
              </select>
            </template>
            
            <div class="flex flex-col gap-4 h-full mt-3">
              
              <div v-if="mlTab === 'poisson'" class="flex flex-col h-full animate-fade-in">
                <p class="text-[10px] text-gray-400 mb-2 leading-relaxed px-1">Matriz de probabilidade de <strong class="text-white">Placar Exato</strong> baseada no modelo de Poisson cruzado com o Expected Goals (xG).</p>
                
                <div class="flex-1 bg-black/30 rounded-xl border border-white/5 p-3 flex flex-col shadow-inner">
                  <div class="flex">
                    <div class="w-8"></div>
                    <div class="flex-1 grid grid-cols-4 text-center text-[9px] font-bold text-gray-500 uppercase tracking-widest pb-2 border-b border-white/10">
                      <span class="col-span-4">{{ partida.fora }} (Gols)</span>
                    </div>
                  </div>
                  
                  <div class="flex flex-1 mt-2">
                    <div class="w-8 flex flex-col justify-center text-[9px] font-bold text-gray-500 uppercase tracking-widest rotate-180 border-l border-white/10" style="writing-mode: vertical-rl;">
                      {{ partida.casa }} (Gols)
                    </div>
                    
                    <div class="flex-1 grid grid-cols-4 grid-rows-4 gap-1 p-1">
                      <div class="bg-red-500/10 border border-red-500/20 rounded flex items-center justify-center text-[10px] font-mono text-gray-400">4.2%</div>
                      <div class="bg-yellow-500/10 border border-yellow-500/20 rounded flex items-center justify-center text-[10px] font-mono text-gray-400">6.1%</div>
                      <div class="bg-black/50 border border-white/5 rounded flex items-center justify-center text-[10px] font-mono text-gray-500">2.8%</div>
                      <div class="bg-black/50 border border-white/5 rounded flex items-center justify-center text-[10px] font-mono text-gray-500">1.1%</div>
                      <div class="bg-yellow-500/20 border border-yellow-500/30 rounded flex items-center justify-center text-[10px] font-mono text-gray-300 font-bold">8.5%</div>
                      <div class="bg-[#10B981]/40 border border-[#10B981]/50 rounded flex items-center justify-center text-[11px] font-mono text-white font-bold drop-shadow-md shadow-[0_0_10px_rgba(16,185,129,0.3)]">12.4%</div>
                      <div class="bg-[#10B981]/20 border border-[#10B981]/30 rounded flex items-center justify-center text-[10px] font-mono text-white font-bold">9.1%</div>
                      <div class="bg-black/50 border border-white/5 rounded flex items-center justify-center text-[10px] font-mono text-gray-500">3.2%</div>
                      <div class="bg-yellow-500/10 border border-yellow-500/20 rounded flex items-center justify-center text-[10px] font-mono text-gray-400">7.2%</div>
                      <div class="bg-[#10B981]/20 border border-[#10B981]/30 rounded flex items-center justify-center text-[10px] font-mono text-white font-bold">10.8%</div>
                      <div class="bg-yellow-500/20 border border-yellow-500/30 rounded flex items-center justify-center text-[10px] font-mono text-gray-300">6.5%</div>
                      <div class="bg-black/50 border border-white/5 rounded flex items-center justify-center text-[10px] font-mono text-gray-500">2.1%</div>
                      <div class="bg-black/50 border border-white/5 rounded flex items-center justify-center text-[10px] font-mono text-gray-500">2.1%</div>
                      <div class="bg-black/50 border border-white/5 rounded flex items-center justify-center text-[10px] font-mono text-gray-500">3.8%</div>
                      <div class="bg-black/50 border border-white/5 rounded flex items-center justify-center text-[10px] font-mono text-gray-500">1.8%</div>
                      <div class="bg-black/50 border border-white/5 rounded flex items-center justify-center text-[10px] font-mono text-gray-600">&lt;1%</div>
                    </div>
                  </div>
                  
                  <div class="mt-3 flex justify-between items-center bg-black/40 px-3 py-1.5 rounded border border-white/5">
                    <span class="text-[9px] text-gray-500 uppercase font-bold tracking-widest">Placar Mais Provável:</span>
                    <span class="text-sm font-mono text-white font-bold bg-[#10B981]/20 px-2 py-0.5 rounded border border-[#10B981]/30">1 - 1</span>
                  </div>
                </div>
              </div>

              <div v-else class="flex flex-col h-full animate-fade-in">
                <p class="text-[10px] text-gray-400 mb-2 leading-relaxed px-1">Evolução do <strong class="text-white">Expected Goals (xG)</strong> ao longo dos 90 minutos projetados.</p>
                
                <div class="flex-1 relative w-full min-h-[180px] bg-[#0b0f19] rounded-xl border border-white/5 overflow-hidden flex items-end pt-4 pr-4 shadow-inner">
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
                    <polyline points="0,40 10,38 20,35 30,25 40,24 50,22 60,18 70,12 80,10 90,8 100,5" fill="none" :stroke="partida.corCasa" stroke-width="2" vector-effect="non-scaling-stroke" />
                    <polyline points="0,40 10,39 20,38 30,36 40,30 50,28 60,25 70,26 80,24 90,20 100,18" fill="none" :stroke="partida.corFora" stroke-width="2" stroke-dasharray="2,2" vector-effect="non-scaling-stroke" />
                  </svg>
                </div>
                
                <div class="flex justify-between items-center mt-3 px-2">
                  <div class="flex items-center gap-2 text-[9px] font-mono text-gray-400 uppercase tracking-widest font-bold"><div class="w-2 h-2 rounded-full" :style="`background: ${partida.corCasa}`"></div> {{ partida.casa }} (xG)</div>
                  <div class="flex items-center gap-2 text-[9px] font-mono text-gray-400 uppercase tracking-widest font-bold"><div class="w-2 h-2 rounded-full border" :style="`border-color: ${partida.corFora}`"></div> {{ partida.fora }} (xG)</div>
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
import { ref, computed } from 'vue';
import draggable from 'vuedraggable';
import { 
  Shield, ShieldAlert, History, User, LineChart, 
  BrainCircuit, Scale, Gavel, CloudRain, Cpu, GripHorizontal, 
  LayoutList, Crosshair, Percent, Plus, ArrowRight, Grid, Activity
} from 'lucide-vue-next';
import WidgetCard from './WidgetCard.vue';

const isLoading = ref(false);

const filtroJogosH2H = ref("5");
const filtroLocalH2H = ref("all");
const filtroCompH2H = ref("league");

const filtroJogosForma = ref("5");

const fbrefTab = ref("avancadas");
const propsTab = ref("chutes");
const filtroMercado = ref("all");
const mlTab = ref("poisson");

const layoutWidgets = ref([
  { id: 'contexto', span: 'col-span-1 xl:col-span-4' },
  { id: 'forma', span: 'col-span-1 xl:col-span-4' },
  { id: 'fbref', span: 'col-span-1 xl:col-span-4' },
  { id: 'jogadores', span: 'col-span-1 xl:col-span-4' },
  { id: 'mercados', span: 'col-span-1 xl:col-span-4' },
  { id: 'ml', span: 'col-span-1 xl:col-span-4' }
]);

const partida = ref({
  casa: "ARSENAL", fora: "LIVERPOOL", posCasa: 1, pontosCasa: 72, posFora: 2, pontosFora: 71,
  corCasa: "#EF0107", corFora: "#00B2A9", placarCasa: 1, placarFora: 1, xgCasa: "1.84", xgFora: "0.92",
  isLive: true, tempo: 68, hora: "16:00",
  
  formCasa: ['W', 'W', 'W', 'D', 'W'], formFora: ['W', 'D', 'W', 'W', 'W'],
  historico: [
    { data: "23 Dez 23", casa: "LIV", placar: "1-1", fora: "ARS", win: "draw" },
    { data: "09 Abr 23", casa: "LIV", placar: "2-2", fora: "ARS", win: "draw" },
  ],
  stats: {
    pts: 72, pts_j: 2.32, pts_f: 71, pts_jf: 2.29, win: 74, win_f: 68, avg_g: 2.4, avg_gc: 0.8, avg_gf: 2.2, avg_gcf: 1.1,
    over: 65, over_f: 71, btts: 45, btts_f: 62, pos: 59, pos_f: 61, public: "60.1k", wage: "£166m", public_f: "53.2k", wage_f: "£136m"
  },
  arbitro: "M. Oliver", arb_amarelos: "4.2", arb_vermelhos: "0.18", clima: "Chuva", temp: "14",

  indFormCasa: [
    { data: "14 Fev", adv: "Aston Villa", placar: "0-3", res: "W" },
    { data: "10 Fev", adv: "West Ham", placar: "2-1", res: "W" },
    { data: "03 Fev", adv: "Nott. Forest", placar: "1-2", res: "W" },
    { data: "29 Jan", adv: "Crystal P.", placar: "1-1", res: "D" },
    { data: "22 Jan", adv: "Brighton", placar: "4-0", res: "W" }
  ],
  indFormFora: [
    { data: "15 Fev", adv: "Brentford", placar: "1-4", res: "W" },
    { data: "11 Fev", adv: "Burnley", placar: "2-0", res: "W" },
    { data: "04 Fev", adv: "Fulham", placar: "1-1", res: "D" },
    { data: "30 Jan", adv: "Chelsea", placar: "4-1", res: "W" },
    { data: "23 Jan", adv: "Bournemouth", placar: "0-2", res: "W" }
  ],

  fbrefOfensivas: [
    { nome: "xG p/ 90", casa: 2.15, fora: 1.95, sufixo: "", desc: "Gols esperados por jogo" },
    { nome: "Chutes no Gol", casa: 6.2, fora: 5.8, sufixo: "", desc: "Finalizações no alvo" },
    { nome: "Grandes Chances", casa: 3.1, fora: 3.4, sufixo: "", desc: "Chances claras geradas" },
  ],
  fbrefDefensivas: [
    { nome: "xGA p/ 90", casa: 0.85, fora: 1.12, sufixo: "", desc: "Gols sofridos esperados" },
    { nome: "Desarmes T. Ataque", casa: 6.5, fora: 5.2, sufixo: "", desc: "Pressão no campo rival" },
    { nome: "Faltas Cometidas", casa: 10.2, fora: 11.5, sufixo: "", desc: "Média de faltas" },
  ],
  fbrefAvancadas: [
    { nome: "Posse de Bola", casa: 58, fora: 42, sufixo: "%", desc: "Controle territorial" },
    { nome: "PPDA (Pressão)", casa: 8.4, fora: 11.2, sufixo: "", desc: "Passes p/ ação def. (Menor é melhor)" },
    { nome: "Field Tilt", casa: 64, fora: 36, sufixo: "%", desc: "Domínio no terço final" },
  ],
  fbrefVariadas: [
    { nome: "Dribles Certos", casa: 14.2, fora: 11.8, sufixo: "", desc: "Frequência de um-contra-um vencidos" },
    { nome: "Cruzamentos", casa: 22.4, fora: 18.5, sufixo: "", desc: "Média de cruzamentos na área" },
    { nome: "Interceptações", casa: 9.1, fora: 12.3, sufixo: "", desc: "Leitura defensiva" },
  ],
  
  // Game State Analytics
  gameState: [
    { time: "ARSENAL", vencendo: "1.42", empatando: "2.10", perdendo: "3.25" },
    { time: "LIVERPOOL", vencendo: "1.18", empatando: "1.95", perdendo: "2.84" }
  ],

  mercados: [
    { nome: "Arsenal Vence (ML)", categoria: "match_odds", prob: 52.4, fair: "1.91", bookie: "2.10", openOdd: "2.25", ev: "9.9", casaNome: "Pinnacle" },
    { nome: "Over 2.5 Gols", categoria: "goals", prob: 64.1, fair: "1.56", bookie: "1.65", openOdd: "1.50", ev: "5.7", casaNome: "Bet365" },
    { nome: "Liverpool +0.5 (AH)", categoria: "handicap", prob: 47.6, fair: "2.10", bookie: "1.85", openOdd: "1.90", ev: "-11.9", casaNome: "Betfair" },
    { nome: "BTTS (Ambas Marcam)", categoria: "goals", prob: 68.5, fair: "1.46", bookie: "1.52", openOdd: "1.60", ev: "4.1", casaNome: "1xBet" },
    { nome: "B. Saka Over 0.5 Chutes", categoria: "props", prob: 71.2, fair: "1.40", bookie: "1.60", openOdd: "1.60", ev: "14.2", casaNome: "Betano" },
  ],
});

const currentFbrefStats = computed(() => {
  if(fbrefTab.value === 'ofensivas') return partida.value.fbrefOfensivas;
  if(fbrefTab.value === 'defensivas') return partida.value.fbrefDefensivas;
  if(fbrefTab.value === 'variadas') return partida.value.fbrefVariadas;
  return partida.value.fbrefAvancadas;
});

const playerPropsMock = {
  chutes: [
    { nome: "B. Saka", time: "ARSENAL", avg: "2.8", prob: 71, fair: "1.40", war: 0.35 },
    { nome: "M. Salah", time: "LIVERPOOL", avg: "3.1", prob: 65, fair: "1.54", war: 0.42 },
    { nome: "M. Ødegaard", time: "ARSENAL", avg: "1.9", prob: 54, fair: "1.85", war: 0.28 },
    { nome: "D. Núñez", time: "LIVERPOOL", avg: "2.4", prob: 49, fair: "2.04", war: 0.15 },
  ],
  gols: [
    { nome: "M. Salah", time: "LIVERPOOL", avg: "0.8", prob: 42, fair: "2.38", war: 0.42 },
    { nome: "B. Saka", time: "ARSENAL", avg: "0.6", prob: 38, fair: "2.63", war: 0.35 },
    { nome: "G. Jesus", time: "ARSENAL", avg: "0.5", prob: 35, fair: "2.85", war: 0.20 },
    { nome: "L. Díaz", time: "LIVERPOOL", avg: "0.4", prob: 28, fair: "3.57", war: 0.18 },
  ],
  assists: [
    { nome: "M. Ødegaard", time: "ARSENAL", avg: "0.4", prob: 30, fair: "3.33", war: 0.28 },
    { nome: "T. Arnold", time: "LIVERPOOL", avg: "0.5", prob: 28, fair: "3.57", war: 0.38 },
  ],
  faltas: [
    { nome: "W. Endo", time: "LIVERPOOL", avg: "1.8", prob: 65, fair: "1.54", war: 0.10 },
    { nome: "D. Rice", time: "ARSENAL", avg: "1.5", prob: 58, fair: "1.72", war: 0.32 },
  ]
};

const currentPlayerProps = computed(() => {
  return playerPropsMock[propsTab.value] || [];
});

const currentMercados = computed(() => {
  if(filtroMercado.value === 'all') return partida.value.mercados;
  return partida.value.mercados.filter(m => m.categoria === filtroMercado.value);
});
</script>

<style scoped>
.glass-card { background: rgba(18, 25, 39, 0.7); border-radius: 16px; border: 1px solid rgba(140, 199, 255, 0.1); backdrop-filter: blur(20px); }
.skeleton-pulse { background: linear-gradient(90deg, rgba(255,255,255,0.02) 25%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.02) 75%); background-size: 400% 100%; animation: skeletonLoading 1.5s infinite ease-in-out; }
@keyframes skeletonLoading { 0% { background-position: 100% 50%; } 100% { background-position: 0 50%; } }
.ghost-widget { opacity: 0.3 !important; border: 2px dashed var(--bet-primary) !important; transform: scale(0.98); }
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(140, 199, 255, 0.2); border-radius: 10px; }
.animate-fade-in { animation: fadeIn 0.4s ease-in-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
</style>