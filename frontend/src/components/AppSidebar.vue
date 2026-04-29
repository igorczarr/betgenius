<template>
  <div class="navigation-wrapper">
    
    <header class="fixed top-0 left-0 w-full z-[100] topbar-glass border-b border-white/5 transition-all duration-300">
      <div class="px-6 py-3 flex justify-between items-center w-full">
        
        <div class="flex items-center gap-3 cursor-pointer group" @click="$emit('update:abaAtiva', 'radar')">
          <img src="../assets/images/bg-16.svg" alt="BG" class="h-8 object-contain drop-shadow-[0_0_15px_rgba(16,185,129,0.3)] group-hover:scale-110 transition-transform duration-300" />
          <span class="font-jersey text-2xl text-white tracking-widest hidden sm:block">BET<span class="text-bet-primary">GENIUS</span></span>
        </div>

        <div class="hidden md:flex flex-1 max-w-md mx-8">
          <div @click="$emit('openSearch')" class="w-full bg-black/40 hover:bg-black/60 border border-white/10 hover:border-bet-primary/50 rounded-full px-4 py-2 flex items-center justify-between cursor-pointer transition-all shadow-inner group">
            <div class="flex items-center gap-2">
              <Search :size="16" class="text-gray-500 group-hover:text-bet-primary transition-colors" />
              <span class="text-xs text-gray-500 group-hover:text-gray-300 font-mono">Pesquisar times, mercados, relatórios...</span>
            </div>
            <kbd class="text-[10px] bg-white/10 text-gray-400 px-2 py-0.5 rounded font-mono border border-white/5">Ctrl K</kbd>
          </div>
        </div>

        <div class="flex items-center gap-5">
          
          <div class="hidden lg:flex items-center gap-2 bg-black/30 border border-white/5 px-3 py-1.5 rounded-full cursor-help group relative">
            <span class="relative flex h-2 w-2">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-bet-primary opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-bet-primary"></span>
            </span>
            <span class="text-[10px] font-mono text-gray-400 uppercase tracking-widest group-hover:text-white transition-colors">Sistema Online</span>
            
            <div class="absolute top-full mt-3 right-0 w-64 bg-[#121927] border border-white/10 rounded-xl p-4 shadow-[0_20px_40px_rgba(0,0,0,0.8)] opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-300 translate-y-2 group-hover:translate-y-0">
              <div class="flex justify-between items-center mb-2 border-b border-white/5 pb-2">
                <span class="text-[9px] uppercase tracking-widest text-gray-500 font-bold">Saúde do Fundo</span>
                <Activity size="12" class="text-bet-primary" />
              </div>
              <div class="flex flex-col gap-2">
                <div class="flex justify-between"><span class="text-[10px] text-gray-400">Jogos Mapeados:</span><span class="text-[10px] font-mono text-white">{{ stats.mappedGames || 0 }}</span></div>
                <div class="flex justify-between"><span class="text-[10px] text-gray-400">Oportunidades (+EV):</span><span class="text-[10px] font-mono text-yellow-400">{{ stats.evOpportunities || 0 }}</span></div>
                <div class="flex justify-between"><span class="text-[10px] text-gray-400">AUM Atual:</span><span class="text-[10px] font-mono text-white">{{ formatCurrency(stats.currentBankroll) }}</span></div>
                <div class="flex justify-between"><span class="text-[10px] text-gray-400">PnL Diário:</span><span class="text-[10px] font-mono" :class="stats.dailyProfit >= 0 ? 'text-bet-primary' : 'text-red-500'">{{ formatCurrency(stats.dailyProfit) }}</span></div>
              </div>
            </div>
          </div>

          <div class="relative">
            <button @click="isNotifOpen = !isNotifOpen" class="relative text-gray-400 hover:text-white transition-colors p-1">
              <Bell :size="20" />
              <div v-if="unreadNotifs > 0" class="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full shadow-[0_0_8px_#EF4444] flex items-center justify-center text-[8px] font-bold text-white font-mono border border-[#0b0f19]">
                {{ unreadNotifs > 9 ? '9+' : unreadNotifs }}
              </div>
            </button>

            <transition name="fade-down">
              <div v-if="isNotifOpen" class="absolute top-full mt-4 right-0 w-80 sm:w-96 bg-[#121927] border border-white/10 rounded-2xl shadow-[0_30px_60px_rgba(0,0,0,0.9)] overflow-hidden flex flex-col z-[200]">
                <div class="p-4 border-b border-white/5 flex justify-between items-center bg-black/20">
                  <span class="text-xs font-bold text-white uppercase tracking-widest flex items-center gap-2"><Zap size="14" class="text-yellow-500"/> Radar de Eventos</span>
                  <button @click="marcarComoLidas" class="text-[9px] text-gray-500 hover:text-white uppercase tracking-widest font-mono transition-colors">Marcar Lidas</button>
                </div>
                
                <div class="flex flex-col max-h-[400px] overflow-y-auto custom-scrollbar p-2">
                  <div v-if="notificacoes.length === 0" class="p-6 text-center text-gray-500 text-[10px] uppercase font-mono tracking-widest">
                    <CheckCircle2 size="24" class="mx-auto mb-2 opacity-50"/>
                    Nenhum evento recente
                  </div>

                  <div v-for="(notif, idx) in notificacoes" :key="idx" class="p-3 hover:bg-white/5 rounded-xl transition-colors border-b border-white/5 last:border-0 flex gap-3 group">
                    <div class="w-8 h-8 rounded-full flex items-center justify-center shrink-0 border" :class="notif.colorClass">
                      <component :is="notif.icon" size="14" />
                    </div>
                    <div class="flex flex-col flex-1">
                      <div class="flex justify-between items-start mb-1">
                        <span class="text-[10px] font-bold text-white uppercase tracking-wider">{{ notif.title }}</span>
                        <span class="text-[9px] text-gray-500 font-mono whitespace-nowrap">{{ notif.time }}</span>
                      </div>
                      <span class="text-[11px] text-gray-400 leading-tight">{{ notif.message }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </transition>
          </div>

          <button @click="isProfileOpen = true" class="w-9 h-9 rounded-full overflow-hidden border-2 transition-all duration-300 hover:scale-105 shadow-lg" :class="isProfileOpen ? 'border-bet-primary' : 'border-white/10 hover:border-white/30'">
            <img v-if="userConfig.avatar" :src="userConfig.avatar" class="w-full h-full object-cover" />
            <div v-else class="w-full h-full bg-gradient-to-br from-gray-800 to-black flex items-center justify-center">
              <User size="16" class="text-gray-400" />
            </div>
          </button>
        </div>
      </div>
    </header>

    <nav class="fixed left-1/2 -translate-x-1/2 z-[100] dock-glass border border-white/10 rounded-full px-2 py-2 flex items-center gap-2 shadow-[0_30px_60px_rgba(0,0,0,0.8)] transition-all duration-500 bottom-2 opacity-30 scale-75 hover:bottom-6 hover:opacity-100 hover:scale-100">
      
      <div 
        v-for="item in menuItems" 
        :key="item.id"
        @click="$emit('update:abaAtiva', item.id)"
        class="relative group cursor-pointer flex flex-col items-center justify-center w-12 h-12 rounded-full transition-all duration-400 ease-out"
        :class="abaAtiva === item.id ? 'bg-white/10' : 'hover:bg-white/5'"
      >
        <component 
          :is="item.icon" 
          :size="20" 
          class="transition-all duration-300 relative z-10"
          :class="abaAtiva === item.id ? 'text-bet-primary scale-110 drop-shadow-[0_0_8px_rgba(16,185,129,0.8)]' : 'text-gray-500 group-hover:text-white group-hover:scale-110'"
          :strokeWidth="abaAtiva === item.id ? 2.5 : 2"
        />
        <div class="absolute bottom-1 w-1 h-1 rounded-full transition-all duration-300" :class="abaAtiva === item.id ? 'bg-bet-primary shadow-[0_0_5px_currentColor] scale-100' : 'bg-transparent scale-0'"></div>
        <div class="absolute -top-10 bg-[#121927] border border-white/10 text-white text-[10px] font-bold uppercase tracking-widest px-3 py-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-200 pointer-events-none whitespace-nowrap shadow-xl translate-y-2 group-hover:translate-y-0">
          {{ item.label }}
        </div>
      </div>

    </nav>

    <Teleport to="body">
      <transition name="fade">
        <div v-if="isProfileOpen" class="fixed inset-0 z-[9999] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 sm:p-0" @click.self="isProfileOpen = false">
          
          <div class="bg-[#0b0f19] border border-white/10 w-full max-w-2xl rounded-3xl shadow-[0_40px_80px_rgba(0,0,0,0.9)] overflow-hidden transform transition-all flex flex-col max-h-[95vh] mt-10 relative">
            
            <button @click="isProfileOpen = false" class="absolute top-4 right-4 z-50 bg-black/50 hover:bg-black/80 text-white p-2 rounded-full backdrop-blur-md transition-colors border border-white/10">
              <X size="18"/>
            </button>

            <div class="h-36 w-full relative bg-gradient-to-r from-bet-primary/20 via-blue-900/20 to-[#0b0f19] group">
              <div class="absolute inset-0 bg-pattern-grid opacity-20"></div>
              <img v-if="userConfig.cover" :src="userConfig.cover" class="w-full h-full object-cover opacity-80" />
            </div>

            <div class="px-8 relative pb-5 border-b border-white/5 shrink-0">
              <div class="flex justify-between items-start">
                <div class="relative -mt-14 group cursor-pointer">
                  <div class="w-28 h-28 rounded-full border-4 border-[#0b0f19] bg-[#121927] overflow-hidden shadow-2xl">
                    <img v-if="userConfig.avatar" :src="userConfig.avatar" class="w-full h-full object-cover" />
                    <User v-else size="48" class="text-gray-500 w-full h-full p-5" />
                  </div>
                </div>

                <div class="mt-4 flex gap-2">
                  <button @click="irParaAjustes" class="border border-white/10 hover:border-white/30 text-xs font-bold text-white px-5 py-2 rounded-full transition-colors flex items-center gap-2 bg-black/50 shadow-sm">
                    <Settings size="14"/> Configurar Perfil
                  </button>
                  <button @click="$emit('logout')" class="bg-red-500/10 hover:bg-red-500 border border-red-500/30 hover:border-red-500 text-red-400 hover:text-white text-xs font-bold px-5 py-2 rounded-full transition-colors flex items-center gap-2 shadow-sm">
                    <LogOut size="14"/> Sair
                  </button>
                </div>
              </div>

              <div class="mt-4">
                <h2 class="text-2xl font-bold text-white flex items-center gap-2">
                  {{ userConfig.nome || 'Gestor Quantitativo' }}
                  <CheckCircle2 size="18" class="text-blue-400" />
                </h2>
                <span class="text-sm font-mono text-gray-400">@{{ userConfig.username || 'admin' }}</span>
              </div>
              
              <p class="text-sm text-gray-300 mt-3 leading-relaxed">
                {{ userConfig.titulo || 'Estrategista Quantitativo' }} • {{ userConfig.cargo || 'Liderança de Operações' }}
              </p>

              <div class="flex items-center gap-5 mt-5 text-[10px] font-mono text-gray-400 uppercase tracking-widest font-bold">
                <span class="flex items-center gap-1.5"><Shield size="14" class="text-bet-primary"/> Acesso Nível {{ userConfig.nivel_dominancia || 2 }}</span>
                <span class="flex items-center gap-1.5"><Activity size="14" class="text-yellow-500"/> Modo: {{ userConfig.modo || 'REAL' }}</span>
              </div>
            </div>

            <div class="p-8 overflow-y-auto custom-scrollbar flex-1 bg-black/20 flex flex-col gap-6">
              
              <div class="grid grid-cols-2 gap-4">
                <div class="bg-black/50 border border-white/5 p-5 rounded-2xl flex flex-col gap-1 shadow-inner">
                  <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold flex items-center gap-2"><DollarSign size="12"/> Volume Ativo (Turnover)</span>
                  <span class="text-2xl font-mono text-white font-bold mt-1">{{ perfData.turnover }}</span>
                </div>
                
                <div class="bg-black/50 border border-white/5 p-5 rounded-2xl flex flex-col gap-1 shadow-inner">
                  <span class="text-[10px] text-gray-500 uppercase tracking-widest font-bold flex items-center gap-2"><TrendingUp size="12"/> Yield Líquido (ROI)</span>
                  <span class="text-2xl font-mono font-bold mt-1" :class="perfData.roiRaw >= 0 ? 'text-bet-primary drop-shadow-[0_0_10px_rgba(16,185,129,0.3)]' : 'text-red-500'">{{ perfData.roi }}</span>
                </div>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                
                <div class="bg-gradient-to-br from-red-900/10 to-black border border-red-500/20 p-5 rounded-2xl flex flex-col justify-between shadow-inner relative overflow-hidden group">
                  <div class="absolute right-0 top-0 w-24 h-24 bg-red-500/5 rounded-full blur-[30px]"></div>
                  <div class="flex justify-between items-start relative z-10 mb-4">
                    <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold flex items-center gap-1.5"><Heart size="12" class="text-red-500"/> Time do Coração</span>
                    <button @click="isEditingHeartTeam = !isEditingHeartTeam" class="text-[9px] uppercase tracking-widest font-bold text-gray-500 hover:text-white transition-colors bg-black/40 px-2 py-1 rounded border border-white/10">{{ isEditingHeartTeam ? 'Cancelar' : 'Editar' }}</button>
                  </div>
                  
                  <div v-if="!isEditingHeartTeam" class="relative z-10 flex items-center justify-between mt-auto">
                    <div class="flex flex-col w-full">
                      <span class="text-xl font-bold text-white truncate w-full" :title="userConfig.time_coracao">{{ userConfig.time_coracao || 'Nenhum' }}</span>
                      <span v-if="userConfig.time_coracao" class="text-[9px] text-gray-500 uppercase tracking-widest font-mono mt-0.5">Fidelidade Registrada</span>
                    </div>
                  </div>

                  <div v-else class="relative z-10 flex flex-col gap-2 mt-auto">
                    <select v-model="tempLeague" class="bg-black border border-white/10 text-white text-xs px-2 py-1.5 rounded outline-none w-full font-mono">
                      <option value="" disabled>Selecione a Liga...</option>
                      <option v-for="l in availableLeagues" :key="l" :value="l">{{ l }}</option>
                    </select>
                    <select v-model="tempTeam" :disabled="!tempLeague" class="bg-black border border-white/10 text-white text-xs px-2 py-1.5 rounded outline-none w-full font-mono disabled:opacity-50">
                      <option value="" disabled>Selecione o Time...</option>
                      <option v-for="t in getTeamsByLeague(tempLeague)" :key="t" :value="t">{{ t }}</option>
                    </select>
                    <button @click="salvarTimeCoracao" :disabled="!tempTeam" class="w-full mt-1 bg-red-500/20 text-red-400 hover:bg-red-500 hover:text-white transition-all text-[10px] font-bold uppercase tracking-widest py-1.5 rounded border border-red-500/30 disabled:opacity-50">Salvar Coração</button>
                  </div>
                </div>

                <div class="bg-gradient-to-br from-yellow-600/10 to-black border border-yellow-500/20 p-5 rounded-2xl flex flex-col justify-between shadow-inner relative overflow-hidden group">
                  <div class="absolute right-0 top-0 w-24 h-24 bg-yellow-500/5 rounded-full blur-[30px]"></div>
                  <div class="flex justify-between items-start relative z-10 mb-4">
                    <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold flex items-center gap-1.5"><Trophy size="12" class="text-yellow-500"/> Galinha dos Ovos de Ouro</span>
                  </div>
                  
                  <div class="relative z-10 flex items-center justify-between mt-auto gap-2">
                    <div class="flex flex-col overflow-hidden">
                      <span class="text-xl font-bold text-white truncate" :title="perfData.goldenGoose">{{ perfData.goldenGoose }}</span>
                      <span class="text-[9px] text-gray-500 uppercase tracking-widest font-mono mt-0.5">Top Equipe (Algoritmo)</span>
                    </div>
                    <span class="text-sm font-mono font-bold px-2 py-1 rounded shadow-inner whitespace-nowrap shrink-0" :class="perfData.goldenGooseProfit.includes('+') ? 'bg-bet-primary/10 text-bet-primary border border-bet-primary/20' : 'bg-gray-800 text-gray-400'">
                      {{ perfData.goldenGooseProfit }}
                    </span>
                  </div>
                </div>

              </div>
            </div>

          </div>
        </div>
      </transition>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import axios from 'axios';
import { 
  Search, Bell, User, Activity, CheckCircle2, Shield, X, Flame,
  LogOut, Settings, Camera, Target, Heart, Trophy, DollarSign,
  LayoutDashboard, FlaskConical, TrendingUp, Check, ArrowRight, Zap, Info
} from 'lucide-vue-next';

defineProps({ abaAtiva: { type: String, required: true } });
const emit = defineEmits(['update:abaAtiva', 'logout', 'openSearch']);

// Constante Blindada para garantir URL correta
const API_URL = 'http://localhost:3000/api/v1';

// Estados de UI
const isProfileOpen = ref(false);
const isNotifOpen = ref(false);
const unreadNotifs = ref(0);

// Edição Time do Coração
const isEditingHeartTeam = ref(false);
const tempLeague = ref('');
const tempTeam = ref('');

// Dados Base (Valores Seguros)
const stats = ref({ mappedGames: 0, evOpportunities: 0, dailyProfit: 0.0, currentBankroll: 0.0 });
const userConfig = ref({ nome: '', username: '', cargo: '', titulo: '', avatar: null, cover: null, modo: '', nivel_dominancia: 2, time_coracao: '' });
const notificacoes = ref([]);

// Catálogo Real do Banco de Dados
const dictTeams = ref({});
const availableLeagues = computed(() => Object.keys(dictTeams.value).sort());
const getTeamsByLeague = (league) => {
  return Array.isArray(dictTeams.value[league]) ? [...dictTeams.value[league]].sort() : [];
};

// Performance Pessoal (Fundo Real)
const perfData = ref({
  turnover: 'R$ 0,00',
  roi: '0.0%',
  roiRaw: 0,
  goldenGoose: 'Aguardando Oráculo...',
  goldenGooseProfit: '-'
});

const formatCurrency = (val) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val || 0);

const menuItems = [
  { id: 'radar', label: 'Radar HFT', icon: Target },
  { id: 'match-center', label: 'Match Center', icon: LayoutDashboard },
  { id: 'banca', label: 'Tesouraria', icon: DollarSign },
  { id: 'backtest', label: 'Quant Lab', icon: FlaskConical },
  { id: 'sentimento', label: 'Hype Engine', icon: TrendingUp }
];

const irParaAjustes = () => {
  isProfileOpen.value = false;
  emit('update:abaAtiva', 'config');
};

const salvarTimeCoracao = () => {
  if (tempTeam.value) {
    userConfig.value.time_coracao = tempTeam.value;
    localStorage.setItem('betgenius_time_coracao', tempTeam.value);
    isEditingHeartTeam.value = false;
  }
};

// MOTOR DE NOTIFICAÇÕES (Tratamento Anti-Quebra S-Tier)
const parseNotifications = (alertsData, ledgerData) => {
  let merged = [];
  
  if (Array.isArray(alertsData)) {
    alertsData.forEach(a => {
      if (!a) return;
      let icon = Info; 
      let colorClass = 'text-blue-400 bg-blue-500/10 border-blue-500/30';
      const tipoStr = String(a.tipo || '').toUpperCase();
      
      if (tipoStr.includes('ODDS DROP')) { icon = Zap; colorClass = 'text-yellow-500 bg-yellow-500/10 border-yellow-500/30'; }
      if (tipoStr.includes('CRÍTICO') || tipoStr.includes('CRITICO')) { icon = Flame; colorClass = 'text-red-500 bg-red-500/10 border-red-500/30'; }

      const timestamp = a.criado_em ? new Date(a.criado_em).getTime() : new Date().getTime();
      const dateStr = new Date(timestamp).toLocaleTimeString('pt-BR', {hour: '2-digit', minute:'2-digit'});

      merged.push({
        title: a.tipo || 'Alerta', time: dateStr, message: a.texto || '',
        icon, colorClass, timestamp
      });
    });
  }

  if (Array.isArray(ledgerData)) {
    ledgerData.forEach(l => {
      if (l && l.status === 'WON') {
        merged.push({
          title: '✅ LIQUIDAÇÃO POSITIVA (+EV)', 
          time: l.hora || 'Hoje',
          message: `SGP Vencedor em ${l.jogo || 'Partida'} (${l.mercado || '-'}). Lucro Creditado: R$ ${l.pnl || '0,00'}`,
          icon: Check, colorClass: 'text-[#10B981] bg-[#10B981]/10 border-[#10B981]/30',
          timestamp: new Date().getTime() 
        });
      }
    });
  }

  merged.sort((a, b) => b.timestamp - a.timestamp);
  notificacoes.value = merged.slice(0, 15);
  
  if (merged.length > 0 && !isNotifOpen.value) {
    unreadNotifs.value = merged.length;
  }
};

const marcarComoLidas = () => {
  unreadNotifs.value = 0;
  isNotifOpen.value = false;
};

// ==================================================
// O CORAÇÃO DO SISTEMA (Busca Segura Isolada)
// ==================================================
const fetchSystemData = async () => {
  try {
    const token = localStorage.getItem('betgenius_token');
    const opts = { headers: { Authorization: `Bearer ${token}` } };

    // Resolve as promessas individualmente. Se o /catalog der 404, não quebra o Heartbeat!
    const promises = [
      axios.get(`${API_URL}/system/heartbeat`, opts).catch(e => ({ data: null, error: e })),
      axios.get(`${API_URL}/system/config`, opts).catch(e => ({ data: null, error: e })),
      axios.get(`${API_URL}/quant/dashboard`, opts).catch(e => ({ data: null, error: e })),
      axios.get(`${API_URL}/system/alerts`, opts).catch(e => ({ data: [], error: e })),
      axios.get(`${API_URL}/system/catalog`, opts).catch(e => ({ data: {}, error: e })) 
    ];

    const [resHeartbeat, resConfig, resFund, resAlerts, resCatalog] = await Promise.all(promises);
    
    // 1. Alimenta o Catálogo (Ligas e Times REAIS do Banco)
    if (resCatalog.data && Object.keys(resCatalog.data).length > 0) {
      dictTeams.value = resCatalog.data;
    }

    // 2. Pulse do Sistema (A barra superior)
    if (resHeartbeat.data) {
      stats.value = { ...stats.value, ...resHeartbeat.data };
    }
    
    // 3. Configurações de Perfil
    if (resConfig.data && resConfig.data.user_config) {
      userConfig.value = { ...userConfig.value, ...resConfig.data.user_config };
      const cachedHeart = localStorage.getItem('betgenius_time_coracao');
      if (cachedHeart) userConfig.value.time_coracao = cachedHeart;
    }
    
    // 4. Galinha dos Ovos de Ouro (Dados Reais do Fundo)
    if (resFund.data && resFund.data.attributionData) {
        perfData.value.turnover = resFund.data.systemStats?.globalYield !== undefined ? `Calculado` : 'R$ 0,00';
        perfData.value.roiRaw = resFund.data.systemStats?.globalYield || 0;
        perfData.value.roi = `${perfData.value.roiRaw > 0 ? '+' : ''}${perfData.value.roiRaw}%`;

        const teams = resFund.data.attributionData.teams || [];
        if (teams.length > 0) {
            // Acha o time com maior ROI real na sua conta
            const goldenGoose = teams.sort((a,b) => parseFloat(b.roi) - parseFloat(a.roi))[0];
            perfData.value.goldenGoose = goldenGoose.name || 'Desconhecido';
            perfData.value.goldenGooseProfit = `ROI: +${parseFloat(goldenGoose.roi).toFixed(1)}%`;
        } else {
            perfData.value.goldenGoose = 'Aguardando Operações';
            perfData.value.goldenGooseProfit = '0.0%';
        }

        // 5. Notificações
        parseNotifications(resAlerts.data, resFund.data.fundLedger);
    }

  } catch (error) {
    console.warn("⚠️ Loop de atualização encontrou resistência da rede.", error);
  }
};

onMounted(() => {
  fetchSystemData();
  setInterval(fetchSystemData, 45000); 
});
</script>

<style scoped>
.topbar-glass { background: rgba(11, 15, 25, 0.85); backdrop-filter: blur(24px) saturate(150%); }
.dock-glass { background: rgba(18, 25, 39, 0.85); backdrop-filter: blur(30px); }

.bg-pattern-grid {
  background-image: linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
  linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 20px 20px;
}

.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(59, 130, 246, 0.5); }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: scale(0.95); }

.fade-down-enter-active, .fade-down-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.fade-down-enter-from, .fade-down-leave-to { opacity: 0; transform: translateY(-10px); }
</style>