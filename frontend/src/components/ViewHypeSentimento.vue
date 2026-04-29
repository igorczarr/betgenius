<template>
  <div class="flex flex-col gap-6 w-full min-h-full relative fade-in-up pb-10">
    
    <div class="glass-card shrink-0 p-6 md:p-8 relative overflow-hidden flex flex-col xl:flex-row justify-between items-center border-t border-b-4 shadow-[0_20px_50px_rgba(0,0,0,0.6)] border-b-[#a855f7]">
      <div class="absolute -right-40 -top-40 w-96 h-96 rounded-full blur-[100px] pointer-events-none opacity-20 bg-[#a855f7] transition-all duration-[2s]" :class="{'scale-110 opacity-30': isConnected}"></div>
      
      <div class="flex items-center gap-5 w-full xl:w-1/4 z-10 mb-6 xl:mb-0 group cursor-default">
        <div class="w-16 h-16 rounded-2xl bg-[#0b0f19] border border-[#a855f7]/30 flex items-center justify-center shadow-[0_0_30px_rgba(168,85,247,0.15)] relative overflow-hidden transition-transform duration-500 group-hover:scale-105">
          <div class="absolute inset-0 bg-gradient-to-br from-[#a855f7]/20 to-transparent"></div>
          <Rss :size="28" class="text-[#a855f7] relative z-10" />
        </div>
        <div class="text-left flex flex-col">
          <h2 class="text-2xl font-mono text-white tracking-[0.2em] drop-shadow-md font-bold">HYPE ENGINE</h2>
          <span class="text-[10px] text-[#a855f7] uppercase tracking-widest font-bold flex items-center gap-1.5 mt-1">
            <div class="w-1.5 h-1.5 rounded-full shadow-[0_0_8px_currentColor]" :class="isConnected ? 'bg-[#a855f7] animate-pulse text-[#a855f7]' : 'bg-gray-500 text-gray-500'"></div> 
            {{ isConnected ? 'NLP Scanner Online' : 'Connecting to HFT Node...' }}
          </span>
        </div>
      </div>

      <div class="flex flex-wrap md:flex-nowrap justify-between xl:justify-end items-center gap-6 md:gap-12 w-full xl:w-3/4 z-10">
        
        <div class="flex flex-col items-start xl:items-end w-[45%] md:w-auto">
          <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 flex items-center gap-1"><Users size="12"/> Volume Social (24h)</span>
          <span class="text-xl font-mono text-white font-bold tracking-wider flex items-center gap-2">
            {{ statsMacro.socialVolume }}
            <span class="text-[9px] text-[#a855f7] bg-[#a855f7]/10 px-2 py-0.5 rounded border border-[#a855f7]/20 uppercase tracking-widest font-sans">Menções</span>
          </span>
        </div>
        
        <div class="hidden md:block w-px bg-gradient-to-b from-transparent via-white/10 to-transparent h-12"></div>
        
        <div class="flex flex-col items-start xl:items-end w-[45%] md:w-auto">
          <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 flex items-center gap-1"><Zap size="12" class="text-yellow-500"/> Anomalias (Alertas)</span>
          <span class="text-xl font-mono text-yellow-400 font-bold tracking-wider drop-shadow-[0_0_8px_rgba(250,204,21,0.3)]">
            {{ statsMacro.alertasInst }} 
          </span>
        </div>

        <div class="hidden md:block w-px bg-gradient-to-b from-transparent via-white/10 to-transparent h-12"></div>

        <div class="flex flex-col items-start xl:items-end w-full md:w-auto mt-4 md:mt-0 bg-[#0b0f19] p-4 rounded-xl border border-white/5 shadow-inner transition-all hover:bg-black/60">
          <span class="text-[10px] text-[#a855f7] uppercase tracking-widest font-bold mb-1">Market Heat (Ganância)</span>
          <div class="flex items-center gap-4 mt-1">
            <div class="w-32 h-2.5 bg-gray-800 rounded-full overflow-hidden flex border border-white/5 shadow-inner">
              <div class="h-full bg-gradient-to-r from-blue-500 via-[#a855f7] to-red-500 transition-all duration-[1.5s] ease-out shadow-[0_0_10px_rgba(168,85,247,0.5)]" :style="`width: ${statsMacro.marketHeat}%`"></div>
            </div>
            <span class="text-2xl font-mono text-white font-black drop-shadow-[0_0_15px_rgba(255,255,255,0.2)] tracking-tight">{{ statsMacro.marketHeat }}%</span>
          </div>
          <span class="text-[8px] font-bold uppercase tracking-widest mt-1.5" :class="statsMacro.marketHeat > 70 ? 'text-red-400 drop-shadow-[0_0_5px_rgba(248,113,113,0.5)]' : 'text-blue-400'">
            {{ statsMacro.marketHeat > 70 ? 'Alerta: Extrema Ganância' : 'Mercado Lento (Frio)' }}
          </span>
        </div>
      </div>
    </div>

    <div v-if="isLoading" class="flex flex-col justify-center items-center py-32 gap-4">
      <div class="w-10 h-10 border-4 border-white/10 border-t-[#a855f7] rounded-full animate-spin shadow-[0_0_15px_rgba(168,85,247,0.3)]"></div>
      <span class="text-xs font-mono text-gray-500 uppercase tracking-widest animate-pulse">Varrendo Redes Sociais e Liquidez...</span>
    </div>

    <draggable 
      v-else
      v-model="layoutSentimento" 
      item-key="id" 
      class="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start mt-2" 
      handle=".drag-handle" 
      ghost-class="ghost-widget"
      animation="300"
      :delay="50"
    >
      <template #item="{ element }">
        <div :class="element.span" class="relative group/widget h-full">
          
          <div class="drag-handle absolute -top-3 left-1/2 -translate-x-1/2 z-[80] opacity-0 group-hover/widget:opacity-100 cursor-move p-1 px-5 bg-[#121927] text-gray-400 rounded-b-xl border border-white/10 shadow-[0_5px_15px_rgba(0,0,0,0.8)] transition-all hover:bg-[#a855f7] hover:text-white">
            <GripHorizontal size="16" />
          </div>

          <WidgetCard v-if="element.id === 'money_flow'" titulo="Smart vs Dumb Money Flow" class="h-full shadow-2xl border border-white/5 bg-[#0b0f19]">
            <template #icone><ArrowLeftRight :size="16" color="#a855f7" /></template>
            <template #acoes>
              <select class="bg-black/50 text-[10px] text-white border border-white/10 rounded-lg px-3 py-1.5 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-[#a855f7] transition-colors shadow-inner">
                <option>Últimas 24h</option>
                <option>Próximas 48h</option>
              </select>
            </template>
            
            <div class="flex flex-col gap-4 mt-4 h-full">
              <div class="grid grid-cols-12 px-4 py-2 border-b border-white/10 text-[9px] uppercase font-bold text-gray-500 tracking-widest bg-black/60 rounded-t-xl">
                <span class="col-span-5">Ativo Foco</span>
                <span class="col-span-3 text-center">Ação do Público (Bilhetes)</span>
                <span class="col-span-3 text-center">Liquidez Institucional (Sharps)</span>
                <span class="col-span-1 text-right pr-2">Edge</span>
              </div>
              
              <div class="flex flex-col gap-2 overflow-y-auto custom-scrollbar flex-1 p-1">
                <transition-group name="list">
                  <div v-for="(flow, i) in moneyFlowData" :key="'mf'+i" class="flex flex-col bg-[#121927] border border-white/5 p-4 rounded-xl relative overflow-hidden group hover:border-white/20 transition-all">
                    <div class="absolute left-0 top-0 w-1.5 h-full transition-all duration-500" :class="flow.edge > 0 ? 'bg-[#10B981] shadow-[2px_0_10px_#10B981]' : 'bg-[#a855f7] shadow-[2px_0_10px_#a855f7]'"></div>
                    
                    <div class="flex justify-between items-start mb-4 pl-3">
                      <div class="flex flex-col">
                        <span class="text-xs font-bold text-white tracking-wide font-sans">{{ flow.jogo }}</span>
                        <span class="text-[9px] text-gray-400 font-mono mt-1 bg-black/40 px-2 py-0.5 rounded w-fit border border-white/5">{{ flow.mercado }}</span>
                      </div>
                      <div class="flex flex-col items-end">
                         <span v-if="flow.edge > 0" class="text-[9px] bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/30 px-2 py-1 rounded font-bold uppercase tracking-widest shadow-[0_0_8px_rgba(16,185,129,0.2)] flex items-center gap-1"><TrendingUp size="10"/> Smart Action</span>
                         <span v-if="flow.edge < 0" class="text-[9px] bg-[#a855f7]/10 text-[#a855f7] border border-[#a855f7]/30 px-2 py-1 rounded font-bold uppercase tracking-widest shadow-[0_0_8px_rgba(168,85,247,0.2)] flex items-center gap-1"><AlertOctagon size="10"/> Trap Bet</span>
                      </div>
                    </div>

                    <div class="flex flex-col gap-3 pl-3">
                      <div class="flex items-center gap-3">
                        <span class="text-[9px] text-gray-500 uppercase tracking-widest w-14 font-bold shrink-0">Público</span>
                        <div class="flex-1 h-2.5 bg-black rounded-full flex overflow-hidden border border-white/5">
                          <div class="h-full bg-blue-500 flex items-center px-1.5 transition-all duration-1000 ease-out" :style="`width: ${flow.ticketCasa}%`"><span v-if="flow.ticketCasa > 15" class="text-[8px] text-white font-black leading-none drop-shadow-md">{{flow.ticketCasa}}%</span></div>
                          <div class="h-full bg-gray-600 transition-all duration-1000 ease-out" :style="`width: ${flow.ticketEmpate}%`"></div>
                          <div class="h-full bg-red-500 flex items-center justify-end px-1.5 transition-all duration-1000 ease-out" :style="`width: ${flow.ticketFora}%`"><span v-if="flow.ticketFora > 15" class="text-[8px] text-white font-black leading-none drop-shadow-md">{{flow.ticketFora}}%</span></div>
                        </div>
                      </div>
                      <div class="flex items-center gap-3">
                        <span class="text-[9px] text-[#10B981] uppercase tracking-widest w-14 font-bold drop-shadow-[0_0_5px_rgba(16,185,129,0.3)] shrink-0">Capital</span>
                        <div class="flex-1 h-2.5 bg-black rounded-full flex overflow-hidden border border-white/5 shadow-inner">
                          <div class="h-full bg-blue-500 flex items-center px-1.5 transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(59,130,246,0.6)]" :style="`width: ${flow.moneyCasa}%`"><span v-if="flow.moneyCasa > 15" class="text-[8px] text-white font-black leading-none drop-shadow-md">{{flow.moneyCasa}}%</span></div>
                          <div class="h-full bg-gray-600 transition-all duration-1000 ease-out" :style="`width: ${flow.moneyEmpate}%`"></div>
                          <div class="h-full bg-red-500 flex items-center justify-end px-1.5 transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(239,68,68,0.6)]" :style="`width: ${flow.moneyFora}%`"><span v-if="flow.moneyFora > 15" class="text-[8px] text-white font-black leading-none drop-shadow-md">{{flow.moneyFora}}%</span></div>
                        </div>
                      </div>
                    </div>

                    <div class="flex justify-between mt-3 pl-3 text-[8px] text-gray-500 uppercase font-mono font-bold">
                      <span class="w-1/3 text-left">Mandante</span> <span class="w-1/3 text-center">Empate</span> <span class="w-1/3 text-right">Visitante</span>
                    </div>
                  </div>
                </transition-group>
                <div v-if="moneyFlowData.length === 0" class="text-center text-xs text-gray-500 py-16 font-mono uppercase tracking-widest bg-black/20 rounded-xl flex items-center justify-center mt-2 flex-col gap-3 border border-dashed border-white/5 opacity-50">
                   <ArrowLeftRight size="32" class="text-gray-600"/> Analisando Livro de Ofertas...
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'nlp'" titulo="Social NLP Scanner" class="h-full shadow-2xl border border-white/5 bg-[#0b0f19]">
            <template #icone><MessageSquare :size="16" color="#a855f7" /></template>
            
            <div class="flex flex-col gap-4 mt-4 h-full">
              <div class="bg-gradient-to-br from-[#a855f7]/10 to-[#121927] border border-[#a855f7]/20 p-5 rounded-xl flex items-center justify-between shadow-inner relative overflow-hidden group">
                <div class="absolute right-0 top-0 w-24 h-24 bg-[#a855f7]/5 rounded-full blur-[30px] group-hover:bg-[#a855f7]/10 transition-colors"></div>
                <div class="flex flex-col relative z-10">
                  <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold mb-1 flex items-center gap-1.5"><Flame size="12" class="text-[#a855f7]"/> Peak Hype Team (24h)</span>
                  <span class="text-2xl font-mono text-white font-black tracking-tight drop-shadow-md">{{ topHypedTeam.nome || '---' }}</span>
                  <span v-if="topHypedTeam.nome" class="text-[9px] mt-2 uppercase px-2 py-0.5 w-max rounded font-bold border tracking-widest shadow-sm" :class="topHypedTeam.score > 80 ? 'text-red-400 bg-red-500/10 border-red-500/30' : 'text-blue-400 bg-blue-500/10 border-blue-500/30'">
                    {{ topHypedTeam.score > 80 ? 'Sentimento Irreal (Overvalued)' : 'Tração Orgânica (Saudável)' }}
                  </span>
                </div>
              </div>

              <div class="flex flex-col gap-3 mt-2 flex-1">
                <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold border-b border-white/5 pb-1">Hype Index Top 3</span>
                <div v-for="(item, i) in nlpData" :key="'nlp'+i" class="bg-[#121927] p-4 rounded-xl border border-white/5 flex flex-col gap-3 hover:border-white/10 transition-colors shadow-sm">
                  <div class="flex justify-between items-center">
                    <span class="text-sm font-bold text-white font-sans">{{ item.time }}</span>
                    <span class="text-[10px] font-mono px-2 py-0.5 rounded font-black border" :class="item.score > 70 ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-blue-500/10 text-blue-400 border-blue-500/20'">SCORE: {{ item.score }}</span>
                  </div>
                  <div class="flex items-center gap-3 w-full">
                    <div class="w-full h-1.5 bg-black border border-white/5 rounded-full flex overflow-hidden">
                      <div class="h-full bg-[#10B981] transition-all duration-1000 ease-out shadow-[0_0_5px_#10B981]" :style="`width: ${item.positive}%`"></div>
                      <div class="h-full bg-gray-600 transition-all duration-1000 ease-out" :style="`width: ${item.neutral}%`"></div>
                      <div class="h-full bg-red-500 transition-all duration-1000 ease-out shadow-[0_0_5px_#EF4444]" :style="`width: ${item.negative}%`"></div>
                    </div>
                  </div>
                  <div class="flex justify-between text-[9px] font-mono uppercase font-bold tracking-widest">
                    <span class="text-[#10B981]">Pos: {{item.positive}}%</span>
                    <span class="text-gray-500">Neu: {{item.neutral}}%</span>
                    <span class="text-red-400">Neg: {{item.negative}}%</span>
                  </div>
                </div>
                <div v-if="nlpData.length === 0" class="text-center text-[10px] text-gray-500 py-8 font-mono uppercase tracking-widest border border-dashed border-white/5 rounded-xl bg-black/20 opacity-50 flex flex-col items-center gap-2">
                  <MessageSquare size="24" class="text-gray-600"/> Minerando X e Fóruns...
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'contrarian'" titulo="Apostas Contrarianas (+EV)" class="h-full shadow-2xl border border-white/5 bg-[#0b0f19]">
            <template #icone><Focus :size="16" color="#10B981" /></template>
            <template #acoes>
              <span class="bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/30 px-3 py-1 rounded-lg text-[9px] font-mono font-bold uppercase tracking-widest flex items-center gap-1.5 shadow-[0_0_10px_rgba(16,185,129,0.2)]">
                <div class="w-1.5 h-1.5 bg-[#10B981] rounded-full animate-pulse"></div> Auto-Hunt
              </span>
            </template>
            
            <div class="flex flex-col h-full mt-4">
              <div class="bg-blue-500/5 border border-blue-500/10 p-3 rounded-xl mb-4 flex gap-3">
                 <Info size="14" class="text-blue-400 shrink-0 mt-0.5"/>
                 <p class="text-[10px] text-blue-200 leading-relaxed font-mono">
                  O <strong class="text-white">Dumb Money</strong> está a amontoar-se num lado, inflacionando a odd oposta. O algoritmo matemático detetou *value* real. Siga o Smart Money.
                 </p>
              </div>
              
              <div class="flex flex-col gap-3 overflow-y-auto custom-scrollbar flex-1 p-1">
                <transition-group name="list">
                  <div v-for="(pick, i) in contrarianPicks" :key="'cp'+i" class="bg-[#121927] border border-white/5 hover:border-[#10B981]/40 p-4 rounded-xl transition-all duration-300 group relative overflow-hidden shadow-inner cursor-pointer hover:-translate-y-0.5 hover:shadow-[0_10px_20px_rgba(0,0,0,0.4)]">
                    <div class="absolute right-0 top-0 w-24 h-24 bg-[#10B981]/5 rounded-bl-full pointer-events-none transition-colors group-hover:bg-[#10B981]/10"></div>
                    
                    <div class="flex justify-between items-start mb-3 relative z-10">
                      <div class="flex flex-col">
                        <span class="text-[9px] text-gray-500 font-mono bg-black/40 px-2 py-0.5 rounded w-fit border border-white/5 mb-1">{{ pick.liga }}</span>
                        <span class="text-sm font-bold text-white tracking-wide font-sans">{{ pick.jogo }}</span>
                      </div>
                      <div class="flex flex-col items-end bg-black/30 p-2 rounded-lg border border-white/5">
                        <span class="text-[8px] text-gray-500 uppercase font-bold tracking-widest mb-0.5">Public na Casa</span>
                        <span class="text-[12px] text-red-400 font-mono font-black">{{ pick.publicOpinion }}%</span>
                      </div>
                    </div>

                    <div class="h-px w-full bg-gradient-to-r from-transparent via-white/10 to-transparent my-3 relative z-10"></div>

                    <div class="flex justify-between items-center relative z-10">
                      <div class="flex flex-col">
                        <span class="text-[9px] text-[#10B981] uppercase font-bold tracking-widest drop-shadow-sm mb-0.5">Ação Recomendada</span>
                        <span class="text-sm font-mono text-white font-black bg-black/50 px-2 py-1 rounded border border-white/5">{{ pick.aposta }} <span class="text-gray-400 text-xs font-normal">@{{ pick.odd }}</span></span>
                      </div>
                      <button class="bg-[#10B981] text-black w-10 h-10 rounded-xl flex items-center justify-center hover:bg-white hover:text-black transition-all duration-300 shadow-[0_0_15px_rgba(16,185,129,0.3)] hover:shadow-[0_0_20px_rgba(255,255,255,0.6)] group/btn hover:scale-105">
                        <Plus size="20" strokeWidth="2.5" class="group-hover/btn:rotate-90 transition-transform" />
                      </button>
                    </div>
                  </div>
                </transition-group>
                <div v-if="contrarianPicks.length === 0" class="text-center text-[10px] text-gray-500 py-16 font-mono uppercase tracking-widest bg-black/20 rounded-xl flex-1 flex flex-col items-center justify-center gap-3 opacity-50 border border-dashed border-white/5 mt-1">
                  <Focus size="32" class="text-gray-600"/> Ouvindo distorções estruturais...
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'scraper'" titulo="News & Dropping Odds Radar" class="h-full shadow-2xl border border-white/5 bg-[#0b0f19]">
            <template #icone><Radio :size="16" color="var(--bet-warning)" /></template>
            <template #acoes>
               <span class="text-[9px] text-yellow-500 uppercase tracking-widest font-bold bg-yellow-500/10 px-3 py-1 rounded-lg border border-yellow-500/20 shadow-[0_0_10px_rgba(234,179,8,0.1)] flex items-center gap-1.5"><Search size="10"/> Social Mine</span>
            </template>
            
            <div class="flex flex-col h-full mt-4">
              <div class="grid grid-cols-12 px-4 py-2 border-b border-white/10 text-[9px] uppercase font-bold text-gray-500 tracking-widest bg-black/60 rounded-t-xl">
                <span class="col-span-3">Entity</span>
                <span class="col-span-7 pl-2">Alerta Extraído</span>
                <span class="col-span-2 text-right">Confiança</span>
              </div>
              
              <div class="flex flex-col overflow-y-auto custom-scrollbar flex-1 p-1 gap-1">
                <transition-group name="list">
                  <div v-for="(news, i) in newsScraperData" :key="'ns'+i" class="grid grid-cols-12 items-center bg-[#121927] border border-white/5 rounded-lg p-3 transition-colors group cursor-default hover:border-white/20">
                    
                    <div class="col-span-3 flex flex-col pr-2">
                      <span class="text-[11px] font-bold text-white truncate font-sans">{{ news.time }}</span>
                      <span class="text-[8px] text-gray-500 font-mono mt-0.5 bg-black px-1.5 py-0.5 rounded w-fit">{{ news.tempo }}</span>
                    </div>

                    <div class="col-span-7 flex flex-col px-3 border-l border-white/5">
                      <span class="text-[11px] font-mono leading-relaxed" :class="news.tipo === 'lesao' ? 'text-red-400 drop-shadow-[0_0_2px_rgba(248,113,113,0.3)]' : 'text-yellow-400 drop-shadow-[0_0_2px_rgba(250,204,21,0.3)]'">{{ news.texto }}</span>
                      <span class="text-[8px] text-gray-500 uppercase mt-1.5 flex items-center gap-1 font-bold"><Link size="10"/> Fonte: <span class="text-gray-400">{{ news.fonte }}</span></span>
                    </div>
                    
                    <div class="col-span-2 flex justify-end items-center pl-2">
                      <div class="bg-black/50 px-2 py-1.5 rounded-lg border shadow-inner flex items-center justify-center w-full" :class="news.confianca > 80 ? 'border-[#10B981]/30 text-[#10B981]' : 'border-yellow-500/30 text-yellow-500'">
                        <span class="text-[10px] font-mono font-black">{{ news.confianca }}%</span>
                      </div>
                    </div>

                  </div>
                </transition-group>
                <div v-if="newsScraperData.length === 0" class="text-center text-[10px] text-gray-500 py-16 font-mono uppercase tracking-widest bg-black/20 rounded-xl flex-1 flex flex-col items-center justify-center gap-3 opacity-50 border border-dashed border-white/5 mt-1">
                  <Radio size="32" class="text-gray-600"/> Scanner Operando no Submundo...
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
import { ref, onMounted, onUnmounted } from 'vue';
import { io } from 'socket.io-client';
import draggable from 'vuedraggable';
import { Rss, Users, Zap, GripHorizontal, ArrowLeftRight, 
  MessageSquare, Flame, Focus, Plus, Radio, Link, TrendingUp, AlertOctagon, Info } from 'lucide-vue-next';
import WidgetCard from './WidgetCard.vue';
import axios from 'axios';

// 🛑 A CURA DAS PORTAS (S-Tier Endpoint Resolution)
const rawApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_BASE_URL = rawApiUrl.endsWith('/api/v1') ? rawApiUrl : `${rawApiUrl.replace(/\/$/, '')}/api/v1`;
const GATEWAY_URL = (import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8000').replace(/\/$/, '');

const isLoading = ref(true);
const isConnected = ref(false);

const layoutSentimento = ref([
  { id: 'money_flow', span: 'col-span-1 xl:col-span-8' },
  { id: 'nlp', span: 'col-span-1 xl:col-span-4' },
  { id: 'contrarian', span: 'col-span-1 xl:col-span-6' },
  { id: 'scraper', span: 'col-span-1 xl:col-span-6' }
]);

const statsMacro = ref({ socialVolume: "---", alertasInst: "0", marketHeat: 50 });
const topHypedTeam = ref({ nome: "", score: 0 });

const moneyFlowData = ref([]);
const nlpData = ref([]);
const contrarianPicks = ref([]);
const newsScraperData = ref([]);

const carregarSentimentoGeral = async () => {
  isLoading.value = true;
  try {
    const token = localStorage.getItem('betgenius_token');
    
    // Requisição ao Endpoint Python FastAPI Corrigido
    const response = await axios.get(`${API_BASE_URL}/sentiment/dashboard`, {
       headers: { Authorization: `Bearer ${token}` }
    });
    
    if (response.data) {
      const data = response.data;
      
      statsMacro.value = data.statsMacro || statsMacro.value;
      moneyFlowData.value = data.moneyFlowData || [];
      nlpData.value = data.nlpData || [];
      contrarianPicks.value = data.contrarianPicks || [];
      newsScraperData.value = data.newsScraperData || [];
      
      if(nlpData.value.length > 0) {
        topHypedTeam.value = nlpData.value.reduce((prev, current) => (prev.score > current.score) ? prev : current, {score: 0});
      }
    }
  } catch (error) {
    console.error("❌ Falha ao buscar dados históricos de sentimento:", error);
  } finally {
    isLoading.value = false;
  }
};

let socket = null;

onMounted(() => {
  carregarSentimentoGeral();

  try {
      socket = io(GATEWAY_URL, { transports: ['websocket'] });

      socket.on('connect', () => {
        isConnected.value = true;
        console.log(`[HFT SOCKET] Sentiment Engine Conectado em ${GATEWAY_URL}`);
      });

      socket.on('MARKET_SENTIMENT_ALERT', (alerta) => {
        if (alerta.tipo === 'money_flow') {
          moneyFlowData.value.unshift(alerta.data);
          if (moneyFlowData.value.length > 10) moneyFlowData.value.pop();
        } 
        else if (alerta.tipo === 'news' || alerta.tipo === 'odd_drop') {
          newsScraperData.value.unshift(alerta.data);
          if (newsScraperData.value.length > 15) newsScraperData.value.pop();
        }
      });

      socket.on('disconnect', () => {
        isConnected.value = false;
        console.log(`[HFT SOCKET] Desconectado.`);
      });
  } catch (err) {
      console.warn("⚠️ Falha ao inicializar o WebSocket.");
  }
});

onUnmounted(() => {
  if (socket) socket.disconnect();
});
</script>

<style scoped>
.glass-card { background: rgba(11, 15, 25, 0.9); backdrop-filter: blur(30px); border-radius: 20px;}
.ghost-widget { opacity: 0.2 !important; border: 2px dashed #a855f7 !important; transform: scale(0.95); background: rgba(168, 85, 247, 0.05); border-radius: 20px;}

.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(168, 85, 247, 0.2); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(168, 85, 247, 0.5); }

.list-enter-active, .list-leave-active { transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1); }
.list-enter-from { opacity: 0; transform: translateX(-30px); }
.list-leave-to { opacity: 0; transform: translateX(30px); }

.fade-in-up { animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
@keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
</style>