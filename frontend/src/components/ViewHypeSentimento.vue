<template>
  <div class="flex flex-col gap-6 w-full min-h-full relative fade-in-up pb-10">
    
    <div class="glass-card shrink-0 p-6 md:p-8 relative overflow-hidden flex flex-col xl:flex-row justify-between items-center border-t-4 shadow-[0_20px_50px_rgba(0,0,0,0.5)] border-[#a855f7]">
      <div class="absolute -right-40 -top-40 w-96 h-96 rounded-full blur-[100px] pointer-events-none opacity-15 bg-[#a855f7]"></div>
      
      <div class="flex items-center gap-5 w-full xl:w-1/4 z-10 mb-6 xl:mb-0">
        <div class="w-16 h-16 rounded-xl bg-black/60 border border-[#a855f7]/30 flex items-center justify-center shadow-[0_0_30px_rgba(168,85,247,0.15)] relative overflow-hidden">
          <div class="absolute inset-0 bg-gradient-to-br from-[#a855f7]/20 to-transparent"></div>
          <Rss :size="30" class="text-[#a855f7] relative z-10" />
        </div>
        <div class="text-left flex flex-col">
          <h2 class="text-2xl font-mono text-white tracking-widest drop-shadow-md">SENTIMENT ENGINE</h2>
          <span class="text-[10px] text-[#a855f7] uppercase tracking-widest font-bold flex items-center gap-1.5 mt-0.5">
            <div class="w-1.5 h-1.5 bg-[#a855f7] rounded-full" :class="{'animate-pulse': isConnected}"></div> {{ isConnected ? 'NLP & Social Scraper Ativo' : 'Conectando ao Radar...' }}
          </span>
        </div>
      </div>

      <div class="flex flex-wrap md:flex-nowrap justify-between xl:justify-end gap-6 md:gap-12 w-full xl:w-3/4 z-10">
        <div class="flex flex-col items-start xl:items-end w-[45%] md:w-auto">
          <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 flex items-center gap-1"><Users size="12"/> Volume Social (24h)</span>
          <span class="text-lg font-mono text-white">{{ statsMacro.socialVolume }} <span class="text-[10px] text-gray-500 bg-white/5 px-1.5 py-0.5 rounded ml-1 font-sans">Menções</span></span>
        </div>
        
        <div class="hidden md:block w-px bg-gradient-to-b from-transparent via-white/10 to-transparent h-12"></div>
        
        <div class="flex flex-col items-start xl:items-end w-[45%] md:w-auto">
          <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1 flex items-center gap-1"><Zap size="12"/> Alertas Institucionais</span>
          <span class="text-xl font-mono text-yellow-500 font-bold">{{ statsMacro.alertasInst }} <span class="text-[10px] text-yellow-500 bg-yellow-500/10 px-1.5 py-0.5 rounded ml-1 border border-yellow-500/20 font-sans">Anomalias</span></span>
        </div>

        <div class="hidden md:block w-px bg-gradient-to-b from-transparent via-white/10 to-transparent h-12"></div>

        <div class="flex flex-col items-start xl:items-end w-full md:w-auto mt-4 md:mt-0 bg-black/30 p-3 rounded-lg border border-white/5 shadow-inner">
          <span class="text-[10px] text-[#a855f7] uppercase tracking-widest font-bold mb-1">Market Heat (Ganância/Medo)</span>
          <div class="flex items-center gap-3 mt-1">
            <div class="w-32 h-2 bg-gray-800 rounded-full overflow-hidden flex">
              <div class="h-full bg-gradient-to-r from-blue-500 via-[#a855f7] to-red-500 transition-all duration-1000" :style="`width: ${statsMacro.marketHeat}%`"></div>
            </div>
            <span class="text-2xl font-mono text-white font-bold drop-shadow-[0_0_15px_rgba(255,255,255,0.2)] tracking-tight">{{ statsMacro.marketHeat }}%</span>
          </div>
          <span class="text-[8px] font-bold uppercase tracking-widest mt-1" :class="statsMacro.marketHeat > 70 ? 'text-red-400' : 'text-blue-400'">
            Status: {{ statsMacro.marketHeat > 70 ? 'Extrema Ganância (Hype)' : 'Mercado Lento (Frio)' }}
          </span>
        </div>
      </div>
    </div>

    <div v-if="isLoading" class="grid grid-cols-1 xl:grid-cols-2 gap-6 mt-2">
      <div v-for="i in 4" :key="i" class="h-[300px] skeleton-pulse rounded-2xl border border-white/5 shadow-2xl"></div>
    </div>

    <draggable 
      v-else
      v-model="layoutSentimento" 
      item-key="id" 
      class="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start mt-2" 
      handle=".drag-handle" 
      ghost-class="ghost-widget"
      animation="250"
    >
      <template #item="{ element }">
        <div :class="element.span" class="relative group/widget h-full">
          
          <div class="drag-handle absolute -top-3 left-1/2 -translate-x-1/2 z-[80] opacity-0 group-hover/widget:opacity-100 cursor-move p-1 px-5 bg-black text-bet-primary rounded-b-xl border border-white/10 shadow-[0_5px_15px_rgba(0,0,0,0.8)] transition-all hover:bg-[#a855f7] hover:text-white">
            <GripHorizontal size="16" />
          </div>

          <WidgetCard v-if="element.id === 'money_flow'" titulo="Smart vs Dumb Money Flow" class="h-full">
            <template #icone><ArrowLeftRight :size="16" color="#3b82f6" /></template>
            <template #acoes>
              <select class="bg-black/40 text-[10px] text-white border border-white/10 rounded px-2 py-1 outline-none font-bold uppercase tracking-wider cursor-pointer hover:border-[#3b82f6]">
                <option>Hoje</option>
                <option>Próximas 48h</option>
              </select>
            </template>
            
            <div class="flex flex-col gap-4 mt-2 h-full">
              <div class="grid grid-cols-12 px-2 pb-2 border-b border-white/10 text-[9px] uppercase font-bold text-gray-500 tracking-widest bg-black/20 rounded-t-lg pt-2">
                <span class="col-span-5">Partida / Mercado</span>
                <span class="col-span-3 text-center">Ticket Count (Público)</span>
                <span class="col-span-3 text-center">Volume Financeiro (Sharps)</span>
                <span class="col-span-1 text-right">Edge</span>
              </div>
              
              <div class="flex flex-col gap-3 overflow-y-auto custom-scrollbar flex-1 pr-1 mt-2">
                <div v-for="(flow, i) in moneyFlowData" :key="'mf'+i" class="flex flex-col bg-black/20 border border-white/5 p-3 rounded-lg relative overflow-hidden group">
                  <div v-if="flow.edge > 0" class="absolute top-0 left-0 w-1 h-full bg-[#10B981]"></div>
                  <div v-if="flow.edge < 0" class="absolute top-0 left-0 w-1 h-full bg-[#a855f7]"></div>
                  
                  <div class="flex justify-between items-center mb-3 pl-2">
                    <div class="flex flex-col">
                      <span class="text-xs font-bold text-white">{{ flow.jogo }}</span>
                      <span class="text-[9px] text-gray-400 font-mono mt-0.5">{{ flow.mercado }}</span>
                    </div>
                    <span v-if="flow.edge > 0" class="text-[9px] bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/30 px-2 py-0.5 rounded font-bold uppercase">Smart Action</span>
                    <span v-if="flow.edge < 0" class="text-[9px] bg-[#a855f7]/10 text-[#a855f7] border border-[#a855f7]/30 px-2 py-0.5 rounded font-bold uppercase">Trap Bet</span>
                  </div>

                  <div class="flex flex-col gap-2 pl-2">
                    <div class="flex items-center gap-3">
                      <span class="text-[9px] text-gray-500 uppercase tracking-widest w-12 font-bold">Bilhetes</span>
                      <div class="flex-1 h-2.5 bg-gray-800 rounded flex overflow-hidden shadow-inner">
                        <div class="h-full bg-blue-500 flex items-center px-1 transition-all" :style="`width: ${flow.ticketCasa}%`"><span v-if="flow.ticketCasa > 20" class="text-[7px] text-white font-bold leading-none">{{flow.ticketCasa}}%</span></div>
                        <div class="h-full bg-gray-600 transition-all" :style="`width: ${flow.ticketEmpate}%`"></div>
                        <div class="h-full bg-red-500 flex items-center justify-end px-1 transition-all" :style="`width: ${flow.ticketFora}%`"><span v-if="flow.ticketFora > 20" class="text-[7px] text-white font-bold leading-none">{{flow.ticketFora}}%</span></div>
                      </div>
                    </div>
                    <div class="flex items-center gap-3">
                      <span class="text-[9px] text-[#10B981] uppercase tracking-widest w-12 font-bold drop-shadow-[0_0_5px_rgba(16,185,129,0.3)]">Dinheiro</span>
                      <div class="flex-1 h-2.5 bg-gray-800 rounded flex overflow-hidden shadow-inner">
                        <div class="h-full bg-blue-500 flex items-center px-1 transition-all" :style="`width: ${flow.moneyCasa}%`"><span v-if="flow.moneyCasa > 20" class="text-[7px] text-white font-bold leading-none">{{flow.moneyCasa}}%</span></div>
                        <div class="h-full bg-gray-600 transition-all" :style="`width: ${flow.moneyEmpate}%`"></div>
                        <div class="h-full bg-red-500 flex items-center justify-end px-1 transition-all" :style="`width: ${flow.moneyFora}%`"><span v-if="flow.moneyFora > 20" class="text-[7px] text-white font-bold leading-none">{{flow.moneyFora}}%</span></div>
                      </div>
                    </div>
                  </div>

                  <div class="flex justify-between mt-2 pl-2 text-[8px] text-gray-500 uppercase font-mono font-bold">
                    <span>Casa</span> <span>Empate</span> <span>Fora</span>
                  </div>
                </div>
                <div v-if="moneyFlowData.length === 0" class="text-center text-xs text-gray-500 py-10 font-mono uppercase tracking-widest bg-black/10 rounded flex items-center justify-center mt-2">
                  Analisando Livro de Ofertas...
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'nlp'" titulo="Social Media NLP Scanner" class="h-full">
            <template #icone><MessageSquare :size="16" color="#a855f7" /></template>
            
            <div class="flex flex-col gap-4 mt-2 h-full">
              <div class="bg-[#121927] border border-white/5 p-4 rounded-xl flex items-center justify-between shadow-inner">
                <div class="flex flex-col">
                  <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold mb-1">Time mais Hypado (24h)</span>
                  <span class="text-xl font-mono text-white font-bold">{{ topHypedTeam.nome || '---' }}</span>
                  <span v-if="topHypedTeam.nome" class="text-[9px] mt-1 uppercase px-1.5 py-0.5 w-max rounded font-bold border" :class="topHypedTeam.score > 80 ? 'text-red-400 bg-red-500/10 border-red-500/20' : 'text-blue-400 bg-blue-500/10 border-blue-500/20'">
                    {{ topHypedTeam.score > 80 ? 'Sentimento Irreal (Overvalued)' : 'Tração Orgânica (Saudável)' }}
                  </span>
                </div>
                <div class="w-14 h-14 rounded-full border-4 border-[#a855f7]/30 flex items-center justify-center bg-black/50 shrink-0">
                  <Flame size="20" class="text-[#a855f7]" :class="{'animate-pulse': topHypedTeam.score > 80}" />
                </div>
              </div>

              <div class="flex flex-col gap-3 mt-2 flex-1">
                <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold border-b border-white/5 pb-1">Hype Index Top 3</span>
                <div v-for="(item, i) in nlpData" :key="'nlp'+i" class="bg-black/20 p-3 rounded-lg border border-white/5 flex flex-col gap-2">
                  <div class="flex justify-between items-center">
                    <span class="text-xs font-bold text-white">{{ item.time }}</span>
                    <span class="text-[10px] font-mono px-2 py-0.5 rounded font-bold" :class="item.score > 70 ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'">Score: {{ item.score }}</span>
                  </div>
                  <div class="flex items-center gap-3">
                    <div class="w-full h-1.5 bg-gray-800 rounded flex overflow-hidden">
                      <div class="h-full bg-[#10B981] transition-all" :style="`width: ${item.positive}%`"></div>
                      <div class="h-full bg-gray-500 transition-all" :style="`width: ${item.neutral}%`"></div>
                      <div class="h-full bg-red-500 transition-all" :style="`width: ${item.negative}%`"></div>
                    </div>
                  </div>
                  <div class="flex justify-between text-[8px] text-gray-500 font-mono uppercase">
                    <span class="text-[#10B981]">Pos: {{item.positive}}%</span>
                    <span>Neu: {{item.neutral}}%</span>
                    <span class="text-red-400">Neg: {{item.negative}}%</span>
                  </div>
                </div>
                <div v-if="nlpData.length === 0" class="text-center text-[10px] text-gray-500 py-4 font-mono uppercase tracking-widest">Minerando X e Fóruns...</div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'contrarian'" titulo="Apostas Contrarianas (+EV)" class="h-full">
            <template #icone><Focus :size="16" color="#10B981" /></template>
            <template #acoes>
              <span class="bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/30 px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase animate-pulse">Algoritmo Ativo</span>
            </template>
            
            <div class="flex flex-col h-full mt-2">
              <p class="text-[10px] text-gray-400 mb-4 px-1 leading-relaxed">
                Operações onde o <strong class="text-white">Público está focando massivamente em um lado</strong>, inflando a Odd do lado oposto. O modelo matemático detectou valor real indo contra a massa.
              </p>
              
              <div class="flex flex-col gap-3 overflow-y-auto custom-scrollbar flex-1 pr-1">
                <div v-for="(pick, i) in contrarianPicks" :key="'cp'+i" class="bg-black/30 border border-[#10B981]/20 hover:border-[#10B981]/50 p-3 rounded-xl transition-all group relative overflow-hidden">
                  <div class="absolute right-0 top-0 w-16 h-16 bg-[#10B981]/5 rounded-bl-full pointer-events-none transition-colors group-hover:bg-[#10B981]/10"></div>
                  
                  <div class="flex justify-between items-start mb-2">
                    <div class="flex flex-col">
                      <span class="text-[10px] text-gray-500 font-mono">{{ pick.liga }}</span>
                      <span class="text-xs font-bold text-white">{{ pick.jogo }}</span>
                    </div>
                    <div class="flex flex-col items-end">
                      <span class="text-[9px] text-gray-500 uppercase font-bold tracking-widest">Public na Casa</span>
                      <span class="text-[10px] text-red-400 font-mono font-bold">{{ pick.publicOpinion }}%</span>
                    </div>
                  </div>

                  <div class="h-px w-full bg-white/5 my-2"></div>

                  <div class="flex justify-between items-center">
                    <div class="flex flex-col">
                      <span class="text-[9px] text-[#10B981] uppercase font-bold tracking-widest drop-shadow-sm">Ação Recomendada</span>
                      <span class="text-sm font-mono text-white font-bold">{{ pick.aposta }} <span class="text-gray-400 text-xs">@{{ pick.odd }}</span></span>
                    </div>
                    <button class="bg-[#10B981] text-black w-8 h-8 rounded-lg flex items-center justify-center hover:bg-white hover:text-black transition-colors shadow-[0_0_10px_rgba(16,185,129,0.4)] hover:shadow-white/50">
                      <Plus size="16" strokeWidth="3" />
                    </button>
                  </div>
                </div>
                <div v-if="contrarianPicks.length === 0" class="text-center text-xs text-gray-500 py-10 font-mono uppercase tracking-widest bg-black/10 rounded flex-1 flex items-center justify-center">
                  Ouvindo distorções do mercado...
                </div>
              </div>
            </div>
          </WidgetCard>

          <WidgetCard v-else-if="element.id === 'scraper'" titulo="News & Dropping Odds Radar" class="h-full">
            <template #icone><Radio :size="16" color="var(--bet-warning)" /></template>
            
            <div class="flex flex-col h-full mt-2">
              <div class="grid grid-cols-12 px-3 pb-2 border-b border-white/10 text-[9px] uppercase font-bold text-gray-500 tracking-widest bg-black/20 rounded-t-lg pt-2">
                <span class="col-span-2">Time</span>
                <span class="col-span-7 pl-2">Alerta Extratído</span>
                <span class="col-span-3 text-right">Confiança</span>
              </div>
              
              <div class="flex flex-col overflow-y-auto custom-scrollbar flex-1 max-h-[300px]">
                <div v-for="(news, i) in newsScraperData" :key="'ns'+i" class="grid grid-cols-12 items-center bg-black/10 even:bg-white/[0.01] hover:bg-white/5 border-b border-white/5 p-3 transition-colors group cursor-default">
                  
                  <div class="col-span-2 flex flex-col">
                    <span class="text-[10px] font-bold text-white truncate">{{ news.time }}</span>
                    <span class="text-[8px] text-gray-600 font-mono mt-0.5">{{ news.tempo }}</span>
                  </div>

                  <div class="col-span-7 flex flex-col pl-2 border-l border-white/5">
                    <span class="text-[10px] text-gray-300 leading-tight" :class="news.tipo === 'lesao' ? 'text-red-300' : 'text-yellow-300'">{{ news.texto }}</span>
                    <span class="text-[8px] text-gray-500 uppercase mt-1 flex items-center gap-1"><Link size="8"/> Fonte: {{ news.fonte }}</span>
                  </div>
                  
                  <div class="col-span-3 flex justify-end items-center">
                    <div class="bg-black/50 px-2 py-1 rounded border border-white/10 flex flex-col items-center">
                      <span class="text-[10px] font-mono font-bold" :class="news.confianca > 80 ? 'text-[#10B981]' : 'text-yellow-500'">{{ news.confianca }}%</span>
                    </div>
                  </div>

                </div>
                <div v-if="newsScraperData.length === 0" class="text-center text-xs text-gray-500 py-10 font-mono uppercase tracking-widest bg-black/10 rounded flex-1 flex items-center justify-center mt-2">
                  Scanner de Notícias Operando...
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
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { io } from 'socket.io-client';
import draggable from 'vuedraggable';
import { Rss, Users, Zap, GripHorizontal, ArrowLeftRight, 
  MessageSquare, Flame, Focus, Plus, Radio, Link } from 'lucide-vue-next';
import WidgetCard from './WidgetCard.vue';
import axios from 'axios';

// ==================================================
// CONFIGURAÇÕES DA API BASE E WEBSOCKET
// ==================================================
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000';
const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || 'http://localhost:3000';

const isLoading = ref(true);
const isConnected = ref(false);

// ESTRUTURA DRAGGABLE
const layoutSentimento = ref([
  { id: 'money_flow', span: 'col-span-1 xl:col-span-8' },
  { id: 'nlp', span: 'col-span-1 xl:col-span-4' },
  { id: 'contrarian', span: 'col-span-1 xl:col-span-6' },
  { id: 'scraper', span: 'col-span-1 xl:col-span-6' }
]);

// ==================================================
// ESTADO REATIVO BASE (Inicia vazio)
// ==================================================
const statsMacro = ref({
  socialVolume: "---",
  alertasInst: "0",
  marketHeat: 50 // Meio (Neutro)
});

const topHypedTeam = ref({ nome: "", score: 0 });

const moneyFlowData = ref([]);
const nlpData = ref([]);
const contrarianPicks = ref([]);
const newsScraperData = ref([]);

// ==================================================
// MÉTODOS DE INGESTÃO (REST API)
// ==================================================
const carregarSentimentoGeral = async () => {
  isLoading.value = true;
  try {
    const response = await fetch(`${API_BASE_URL}/api/sentiment/dashboard`);
    if (response.ok) {
      const data = await response.json();
      
      // Mapeia os dados reais do banco
      statsMacro.value = data.statsMacro || statsMacro.value;
      moneyFlowData.value = data.moneyFlowData || [];
      nlpData.value = data.nlpData || [];
      contrarianPicks.value = data.contrarianPicks || [];
      newsScraperData.value = data.newsScraperData || [];
      
      if(nlpData.value.length > 0) {
        // Encontra o time com o maior score de hype para o card de destaque
        topHypedTeam.value = nlpData.value.reduce((prev, current) => (prev.score > current.score) ? prev : current, {score: 0});
      }
    } else {
       console.warn("⚠️ API do Sentiment Engine não conectada ainda. Aguardando HFT Websocket.");
    }
  } catch (error) {
    console.error("❌ Falha ao buscar dados históricos de sentimento:", error);
  } finally {
    isLoading.value = false;
  }
};

// ==================================================
// WEBSOCKETS (HFT E ALERTAS AO VIVO)
// ==================================================
let socket = null;

onMounted(() => {
  // 1. Carrega o estado base da API
  carregarSentimentoGeral();

  // 2. Acopla o ouvido de Alta Frequência
  socket = io(GATEWAY_URL, { transports: ['websocket'] });

  socket.on('connect', () => {
    isConnected.value = true;
    console.log(`[HFT SOCKET] Sentiment Engine Conectado.`);
  });

  // O Node.js emitirá alertas de "Drop de Odds" e "Quebra de Notícias" neste canal
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
});

onUnmounted(() => {
  if (socket) socket.disconnect();
});
</script>

<style scoped>
.glass-card { background: rgba(18, 25, 39, 0.75); border-radius: 16px; backdrop-filter: blur(24px); }
.skeleton-pulse { background: linear-gradient(90deg, rgba(255,255,255,0.02) 25%, rgba(255,255,255,0.06) 50%, rgba(255,255,255,0.02) 75%); background-size: 400% 100%; animation: skeletonLoading 1.5s infinite ease-in-out; }
@keyframes skeletonLoading { 0% { background-position: 100% 50%; } 100% { background-position: 0 50%; } }
.ghost-widget { opacity: 0.3 !important; border: 2px dashed #a855f7 !important; transform: scale(0.98); }
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(168, 85, 247, 0.2); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(168, 85, 247, 0.4); }
</style>