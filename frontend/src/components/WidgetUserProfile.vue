<template>
  <div class="fixed inset-0 z-[9999] bg-black/60 backdrop-blur-sm flex items-center justify-center sm:p-4" @click.self="$emit('close')">
    
    <div class="bg-[#0b0f19] border border-white/10 w-full max-w-2xl sm:rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.9)] overflow-hidden flex flex-col h-full sm:h-auto max-h-screen sm:max-h-[90vh] animate-modal-pop relative">
      
      <div class="absolute top-0 left-0 w-full p-3 flex justify-between items-center z-50 pointer-events-none">
        <button @click="$emit('close')" class="pointer-events-auto bg-black/50 hover:bg-black/80 text-white p-2 rounded-full backdrop-blur-md transition-all border border-white/10">
          <ArrowLeft size="18"/>
        </button>
      </div>

      <div class="flex-1 overflow-y-auto custom-scrollbar">
        
        <div class="h-40 sm:h-48 w-full relative bg-gradient-to-r from-gray-900 to-black group cursor-pointer" @click="promptCoverUpdate">
          <img v-if="profileData.cover_url" :src="profileData.cover_url" class="absolute inset-0 w-full h-full object-cover opacity-80 transition-opacity group-hover:opacity-60" />
          <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity backdrop-blur-[2px]">
            <div class="bg-black/60 p-2 rounded-full border border-white/20"><Camera size="20" class="text-white"/></div>
          </div>
        </div>

        <div class="px-5 relative">
          <div class="flex justify-between items-start">
            <div class="relative -mt-12 sm:-mt-16 w-24 h-24 sm:w-32 sm:h-32 rounded-full border-4 border-[#0b0f19] bg-[#121927] overflow-hidden shadow-xl z-20">
              <img v-if="userConfig.avatar" :src="userConfig.avatar" class="w-full h-full object-cover" />
              <User v-else size="48" class="text-gray-500 w-full h-full p-6" />
            </div>
            
            <div class="mt-3 flex gap-2">
              <button @click="$emit('open-config')" class="border border-white/20 hover:bg-white/10 text-white font-bold text-xs px-4 py-1.5 rounded-full transition-colors">
                Editar Perfil
              </button>
              <button @click="$emit('logout')" class="border border-red-500/30 text-red-400 hover:bg-red-500/10 font-bold text-xs px-4 py-1.5 rounded-full transition-colors">
                Sair
              </button>
            </div>
          </div>

          <div class="mt-3">
            <h2 class="text-xl font-bold text-white flex items-center gap-1.5 leading-none">
              {{ userConfig.nome || 'Gestor Quantitativo' }}
              <CheckCircle2 size="16" class="text-blue-400" />
            </h2>
            <span class="text-[13px] text-gray-500 font-mono mt-1 block">@{{ userConfig.username || 'admin' }}</span>
          </div>

          <div class="mt-4 text-[14px] text-gray-200 leading-relaxed">
            <p>{{ userConfig.titulo || 'Estrategista Quantitativo' }} focado em Alpha Generation e Arbitragem Estatística. {{ userConfig.cargo }} no Fundo.</p>
            <div class="flex items-center gap-4 mt-3 text-gray-500 text-xs font-mono">
              <span class="flex items-center gap-1"><Shield size="14"/> Nível {{ userConfig.nivel_dominancia || 2 }}</span>
              <span class="flex items-center gap-1 cursor-pointer hover:text-white transition-colors" @click="promptHeartTeam">
                <Heart size="14" :class="profileData.time_coracao ? 'text-red-500 fill-red-500' : ''"/> 
                {{ profileData.time_coracao || 'Adicionar Time' }}
              </span>
            </div>
          </div>

          <div class="flex items-center gap-6 mt-4 text-[13px]">
            <div class="flex gap-1.5"><span class="font-bold text-white">{{ perfData.turnover }}</span> <span class="text-gray-500">Volume</span></div>
            <div class="flex gap-1.5"><span class="font-bold" :class="perfData.roiRaw >= 0 ? 'text-[#10B981]' : 'text-red-400'">{{ perfData.roi }}</span> <span class="text-gray-500">ROI Líquido</span></div>
          </div>
        </div>

        <div class="flex border-b border-white/10 mt-6 px-1">
          <button @click="activeTab = 'visao'" class="flex-1 pb-3 text-[13px] font-bold transition-colors relative" :class="activeTab === 'visao' ? 'text-white' : 'text-gray-500 hover:text-gray-300'">
            Visão Geral
            <div v-if="activeTab === 'visao'" class="absolute bottom-0 left-1/2 -translate-x-1/2 w-12 h-1 bg-[#10B981] rounded-t-full"></div>
          </button>
          <button @click="activeTab = 'highlight'" class="flex-1 pb-3 text-[13px] font-bold transition-colors relative" :class="activeTab === 'highlight' ? 'text-white' : 'text-gray-500 hover:text-gray-300'">
            Highlight
            <div v-if="activeTab === 'highlight'" class="absolute bottom-0 left-1/2 -translate-x-1/2 w-12 h-1 bg-[#10B981] rounded-t-full"></div>
          </button>
          <button @click="activeTab = 'disciplina'" class="flex-1 pb-3 text-[13px] font-bold transition-colors relative" :class="activeTab === 'disciplina' ? 'text-white' : 'text-gray-500 hover:text-gray-300'">
            Disciplina
            <div v-if="activeTab === 'disciplina'" class="absolute bottom-0 left-1/2 -translate-x-1/2 w-12 h-1 bg-[#10B981] rounded-t-full"></div>
          </button>
        </div>

        <div class="p-5 min-h-[250px] bg-black/20">
          
          <transition name="fade" mode="out-in">
            <div v-if="activeTab === 'visao'" class="flex flex-col gap-4">
              <div class="bg-[#121927] border border-white/5 rounded-2xl p-4 flex gap-3 hover:bg-white/[0.02] transition-colors cursor-pointer">
                <div class="w-10 h-10 rounded-full bg-yellow-500/10 border border-yellow-500/30 flex items-center justify-center shrink-0">
                  <Trophy size="18" class="text-yellow-500" />
                </div>
                <div class="flex flex-col flex-1">
                  <div class="flex items-center gap-1.5">
                    <span class="font-bold text-white text-[13px]">Galinha dos Ovos de Ouro</span>
                    <span class="text-gray-500 text-xs font-mono">· Algoritmo</span>
                  </div>
                  <p class="text-sm text-gray-300 mt-1">A equipe que mais gerou lucro líquido para o fundo até o momento é o <strong class="text-white">{{ perfData.goldenGoose }}</strong>.</p>
                  <div class="mt-3 flex items-center gap-2">
                    <span class="text-[11px] font-mono font-bold bg-[#10B981]/10 text-[#10B981] px-2 py-0.5 rounded border border-[#10B981]/20">
                      {{ perfData.goldenGooseProfit }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="activeTab === 'highlight'" class="flex flex-col gap-4">
              <div v-if="isLoading" class="flex items-center justify-center h-32"><div class="w-6 h-6 border-2 border-white/20 border-t-[#10B981] rounded-full animate-spin"></div></div>
              <div v-else-if="gamification.highlight" class="bg-[#121927] border border-white/5 rounded-2xl p-4 flex gap-3 relative overflow-hidden group">
                <div class="absolute right-0 top-0 w-32 h-32 bg-yellow-500/5 rounded-full blur-[40px] pointer-events-none"></div>
                <div class="w-10 h-10 rounded-full bg-black border border-white/10 overflow-hidden flex items-center justify-center shrink-0">
                  <img v-if="userConfig.avatar" :src="userConfig.avatar" class="w-full h-full object-cover" />
                </div>
                <div class="flex flex-col flex-1 relative z-10">
                  <div class="flex items-center gap-1.5">
                    <span class="font-bold text-white text-[13px]">{{ userConfig.nome }}</span>
                    <CheckCircle2 size="12" class="text-blue-400" />
                    <span class="text-gray-500 text-xs font-mono">· {{ gamification.highlight.data }}</span>
                  </div>
                  <span class="text-[10px] text-yellow-500 font-bold uppercase tracking-widest mt-0.5 mb-2 flex items-center gap-1"><Crown size="10"/> Recorde Histórico</span>
                  
                  <div class="bg-black/40 border border-white/10 rounded-xl p-3 mt-1">
                    <p class="text-sm text-white font-bold">{{ gamification.highlight.jogo }}</p>
                    <p class="text-xs text-gray-400 mt-1">{{ gamification.highlight.mercado }}</p>
                    <div class="flex items-center justify-between mt-3 pt-3 border-t border-white/5">
                      <span class="text-xs font-mono text-gray-500">Odd Pega: <strong class="text-white">@{{ gamification.highlight.odd }}</strong></span>
                      <span class="text-xs font-mono text-[#10B981] font-bold bg-[#10B981]/10 px-2 py-0.5 rounded border border-[#10B981]/20">+ R$ {{ gamification.highlight.pnl }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="text-center text-gray-500 text-xs font-mono py-10">Nenhuma aposta liquidada ainda.</div>
            </div>

            <div v-else-if="activeTab === 'disciplina'" class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div v-if="isLoading" class="col-span-2 flex items-center justify-center h-32"><div class="w-6 h-6 border-2 border-white/20 border-t-[#10B981] rounded-full animate-spin"></div></div>
              <template v-else>
                <div class="bg-[#121927] border border-white/5 p-5 rounded-2xl flex flex-col items-center justify-center text-center gap-2 relative overflow-hidden shadow-inner">
                  <div class="absolute top-0 w-full h-1 bg-gradient-to-r from-transparent via-[#10B981] to-transparent"></div>
                  <Flame :size="24" :class="gamification.win_streak > 2 ? 'text-[#10B981] animate-pulse drop-shadow-[0_0_8px_rgba(16,185,129,0.8)]' : 'text-gray-500'" />
                  <span class="text-3xl font-black font-mono text-white mt-1">{{ gamification.win_streak }}</span>
                  <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Vitórias Seguidas</span>
                </div>

                <div class="bg-[#121927] border border-white/5 p-5 rounded-2xl flex flex-col items-center justify-center text-center gap-2 relative overflow-hidden group cursor-pointer shadow-inner" @click="resetTilt">
                  <div class="absolute inset-0 bg-gradient-to-t from-red-500/0 to-transparent group-hover:from-red-500/10 transition-colors"></div>
                  <ShieldAlert :size="24" class="text-blue-400 group-hover:text-red-400 transition-colors relative z-10" />
                  <span class="text-3xl font-black font-mono text-white relative z-10">{{ gamification.days_without_tilt }}</span>
                  <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold relative z-10 group-hover:hidden">Dias sem Tiltar</span>
                  <span class="text-[10px] text-red-400 uppercase tracking-widest font-bold relative z-10 hidden group-hover:block">Zerar Contador</span>
                </div>
                
                <div class="bg-[#121927] border border-white/5 p-5 rounded-2xl flex flex-col items-center justify-center text-center gap-2 col-span-1 sm:col-span-2 shadow-inner">
                  <span class="text-xl font-black font-mono text-white">{{ gamification.days_without_serie_b }} Dias</span>
                  <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Limpos de Mercados Tóxicos</span>
                </div>
              </template>
            </div>

          </transition>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';
import { 
  X, Camera, User, Settings, LogOut, CheckCircle2, Shield, Heart, 
  Trophy, Flame, ShieldAlert, ArrowLeft, Crown, BarChart2, DollarSign, TrendingUp
} from 'lucide-vue-next';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

const props = defineProps({
  userConfig: { type: Object, required: true },
  perfData: { type: Object, required: true },
  dictTeams: { type: Object, required: true }
});

const emit = defineEmits(['close', 'logout', 'open-config', 'save-team']);

const activeTab = ref('visao');
const isLoading = ref(true);

const profileData = ref({
  cover_url: null,
  time_coracao: null
});

const gamification = ref({
  win_streak: 0,
  days_without_tilt: 0,
  days_without_serie_b: 0,
  highlight: null
});

// Ações Visuais Diretas
const promptCoverUpdate = async () => {
  const url = prompt("Cole a URL da nova imagem de Capa:");
  if (url) {
    profileData.value.cover_url = url;
    try {
      const token = localStorage.getItem('betgenius_token');
      await axios.post(`${API_BASE_URL}/system/profile/update`, { cover_url: url }, { headers: { Authorization: `Bearer ${token}` }});
    } catch(e) {}
  }
};

const promptHeartTeam = async () => {
  const team = prompt("Digite o nome exato do seu Time do Coração:");
  if (team) {
    profileData.value.time_coracao = team;
    try {
      const token = localStorage.getItem('betgenius_token');
      await axios.post(`${API_BASE_URL}/system/profile/update`, { time_coracao: team }, { headers: { Authorization: `Bearer ${token}` }});
    } catch(e) {}
  }
};

const resetTilt = async () => {
  if(confirm("Tem certeza que quer zerar seus dias de disciplina?")) {
    try {
      const token = localStorage.getItem('betgenius_token');
      await axios.post(`${API_BASE_URL}/system/profile/reset-tilt`, {}, { headers: { Authorization: `Bearer ${token}` }});
      gamification.value.days_without_tilt = 0;
    } catch(e) {}
  }
};

// Requisição Oficial de Dados
onMounted(async () => {
  try {
    const token = localStorage.getItem('betgenius_token');
    const res = await axios.get(`${API_BASE_URL}/system/profile`, { headers: { Authorization: `Bearer ${token}` }});
    
    if (res.data) {
      profileData.value.cover_url = res.data.cover_url;
      profileData.value.time_coracao = res.data.time_coracao;
      gamification.value = res.data.gamification;
    }
  } catch (error) {
    console.error("Erro ao puxar Gamification Data", error);
  } finally {
    isLoading.value = false;
  }
});
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }

.animate-modal-pop { animation: modal-pop 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
@keyframes modal-pop {
  0% { transform: scale(0.95) translateY(20px); opacity: 0; }
  100% { transform: scale(1) translateY(0); opacity: 1; }
}

.bg-pattern-grid {
  background-image: linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
  linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 20px 20px;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(5px); }
</style>