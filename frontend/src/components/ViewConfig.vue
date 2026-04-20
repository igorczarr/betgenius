<template>
  <div class="flex flex-col gap-6 w-full h-full relative fade-in-up pb-10 max-w-6xl mx-auto transition-all duration-700"
       :class="config.modo === 'BENCHMARK' ? 'theme-benchmark' : 'theme-real'">
    
    <div class="glass-card p-8 flex flex-col md:flex-row justify-between items-start md:items-center relative overflow-hidden border-t-4 border-t-dynamic shrink-0">
      <div class="absolute -right-20 -top-20 w-64 h-64 rounded-full blur-[60px] pointer-events-none opacity-20 transition-colors duration-700 bg-dynamic"></div>
      
      <div class="flex items-center gap-5 relative z-10">
        <div class="relative group cursor-pointer" @click="$refs.avatarInput.click()">
          <div class="w-20 h-20 rounded-2xl bg-black/60 border-2 overflow-hidden flex items-center justify-center shadow-2xl transition-colors border-dynamic">
            <img v-if="config.avatar" :src="config.avatar" class="w-full h-full object-cover group-hover:opacity-50 transition-opacity" />
            <User v-else size="32" class="text-gray-400" />
          </div>
          <div class="absolute inset-0 flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none bg-black/40 rounded-2xl">
            <UploadCloud size="20" class="text-white" />
            <span class="text-[8px] font-bold uppercase mt-1">Alterar</span>
          </div>
          <input type="file" ref="avatarInput" class="hidden" @change="handleAvatarUpload" accept="image/*" />
        </div>

        <div class="flex flex-col">
          <h2 class="font-jersey text-4xl text-white tracking-widest drop-shadow-md flex items-center gap-3">
            CENTRO DE COMANDO
            <span v-if="config.modo === 'BENCHMARK'" class="text-[10px] font-mono bg-purple-500/20 text-purple-400 px-2 py-1 rounded border border-purple-500/30 shadow-[0_0_10px_rgba(168,85,247,0.2)]">
              <FlaskConical size="12" class="inline mb-0.5" /> SHADOW TRADING (SIMULAÇÃO)
            </span>
            <span v-else class="text-[10px] font-mono bg-[#10B981]/20 text-[#10B981] px-2 py-1 rounded border border-[#10B981]/30 shadow-[0_0_10px_rgba(16,185,129,0.2)]">
              <ShieldCheck size="12" class="inline mb-0.5" /> FUNDO OPERACIONAL (REAL)
            </span>
          </h2>
          <div class="flex items-center gap-2 mt-1">
            <span class="text-xs text-gray-400 uppercase tracking-widest font-bold">{{ config.cargo || 'Lead Quant' }} • {{ config.nome || 'Admin' }}</span>
          </div>
        </div>
      </div>
      
      <button @click="salvarConfiguracoes" :disabled="isSaving" class="mt-4 md:mt-0 bg-white text-black px-8 py-3 rounded-xl font-bold uppercase tracking-widest text-xs hover:bg-gray-200 transition-all shadow-[0_0_20px_rgba(255,255,255,0.2)] flex items-center gap-2 disabled:opacity-50">
        <Loader2 v-if="isSaving" size="16" class="animate-spin" />
        <Save v-else size="16" strokeWidth="3" /> 
        Sincronizar Sistema
      </button>
    </div>

    <div class="flex p-1 rounded-xl bg-black/40 border border-white/10 shadow-inner w-full md:w-fit z-10 flex-wrap shrink-0">
      <button @click="abaAtiva = 'operacao'" class="px-6 py-2.5 text-xs uppercase tracking-widest font-bold rounded-lg transition-all flex items-center gap-2" :class="abaAtiva === 'operacao' ? 'bg-white/10 text-white shadow-sm' : 'text-gray-500 hover:text-gray-300'">
        <Cpu size="14" /> Motor & IA
      </button>
      <button @click="abaAtiva = 'tesouraria'" class="px-6 py-2.5 text-xs uppercase tracking-widest font-bold rounded-lg transition-all flex items-center gap-2" :class="abaAtiva === 'tesouraria' ? 'bg-white/10 text-white shadow-sm' : 'text-gray-500 hover:text-gray-300'">
        <Landmark size="14" /> Tesouraria Institucional
      </button>
      <button @click="abaAtiva = 'perfil'" class="px-6 py-2.5 text-xs uppercase tracking-widest font-bold rounded-lg transition-all flex items-center gap-2" :class="abaAtiva === 'perfil' ? 'bg-white/10 text-white shadow-sm' : 'text-gray-500 hover:text-gray-300'">
        <Fingerprint size="14" /> Perfil & Acesso
      </button>
      <button @click="abaAtiva = 'visual'" class="px-6 py-2.5 text-xs uppercase tracking-widest font-bold rounded-lg transition-all flex items-center gap-2" :class="abaAtiva === 'visual' ? 'bg-white/10 text-white shadow-sm' : 'text-gray-500 hover:text-gray-300'">
        <Image size="14" /> Temas & Login UI
      </button>
    </div>

    <div v-if="isLoading" class="flex-1 w-full bg-black/20 border border-white/5 rounded-2xl p-8 shadow-2xl animate-pulse h-[400px]"></div>

    <div v-else class="flex-1 w-full bg-black/20 border border-white/5 rounded-2xl p-6 md:p-8 shadow-2xl relative overflow-y-auto custom-scrollbar z-10">
      <transition name="fade" mode="out-in">
        
        <div v-if="abaAtiva === 'operacao'" class="flex flex-col gap-8 pb-4">
           <div class="grid grid-cols-1 xl:grid-cols-2 gap-8">
            <div class="flex flex-col gap-4">
              <h3 class="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2 border-b border-white/10 pb-2">
                <Globe size="16" class="text-dynamic" /> Alternador de Realidade
              </h3>
              <p class="text-[11px] text-gray-400 leading-relaxed font-mono">O Fundo Real expõe capital. O Benchmark isola os testes.</p>
              <div class="flex bg-[#0b0f19] p-2 rounded-xl border border-white/5 relative mt-2 shadow-inner">
                <div class="absolute inset-y-2 w-[calc(50%-8px)] rounded-lg transition-all duration-500 ease-out z-0 bg-dynamic shadow-dynamic"
                     :class="config.modo === 'REAL' ? 'left-2' : 'left-[calc(50%+4px)]'"></div>
                <button @click="config.modo = 'REAL'" class="flex-1 py-4 text-xs uppercase tracking-widest font-bold rounded-lg relative z-10 transition-colors" :class="config.modo === 'REAL' ? 'text-black' : 'text-gray-500'">Fundo Real</button>
                <button @click="config.modo = 'BENCHMARK'" class="flex-1 py-4 text-xs uppercase tracking-widest font-bold rounded-lg relative z-10 transition-colors" :class="config.modo === 'BENCHMARK' ? 'text-white' : 'text-gray-500'">Benchmark</button>
              </div>
            </div>

            <div class="flex flex-col gap-4">
              <h3 class="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2 border-b border-white/10 pb-2">
                <BrainCircuit size="16" class="text-yellow-500"/> Hierarquia de Dominância
              </h3>
              <div class="bg-black/40 border border-white/5 p-5 rounded-xl flex flex-col gap-4">
                <div class="flex justify-between items-center text-[10px] uppercase font-bold tracking-widest text-gray-500">
                  <span :class="config.nivel_dominancia === 1 ? 'text-green-400 drop-shadow-[0_0_5px_rgba(74,222,128,0.5)]' : ''">1. Guiado</span>
                  <span :class="config.nivel_dominancia === 2 ? 'text-blue-400 drop-shadow-[0_0_5px_rgba(96,165,250,0.5)]' : ''">2. Copiloto</span>
                  <span :class="config.nivel_dominancia === 3 ? 'text-red-400 drop-shadow-[0_0_5px_rgba(248,113,113,0.5)]' : ''">3. Alpha</span>
                </div>
                <input type="range" v-model.number="config.nivel_dominancia" min="1" max="3" step="1" class="w-full accent-white cursor-pointer" />
                <div class="mt-2 text-center p-4 rounded-xl border shadow-inner transition-colors duration-500" :class="hierarquiaInfo.bgClass">
                  <span class="text-sm uppercase tracking-widest font-bold" :class="hierarquiaInfo.textClass">{{ hierarquiaInfo.titulo }}</span>
                  <p class="text-[10px] mt-2 font-mono text-gray-300 leading-relaxed">{{ hierarquiaInfo.desc }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="abaAtiva === 'tesouraria'" class="flex flex-col gap-8 pb-4">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="bg-black/40 border border-white/5 p-5 rounded-xl flex flex-col gap-1 relative overflow-hidden">
              <span class="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Banca Operacional ({{ config.modo }})</span>
              <span class="text-2xl font-mono text-white font-bold">
                {{ formatCurrency(config.modo === 'REAL' ? tesouraria.banca_real : tesouraria.banca_bench) }}
              </span>
            </div>
            <div class="bg-[#10B981]/10 border border-[#10B981]/30 p-5 rounded-xl flex flex-col gap-1 relative overflow-hidden shadow-[0_0_20px_rgba(16,185,129,0.1)]">
              <span class="text-[10px] text-[#10B981] uppercase tracking-widest font-bold">Lucro Líquido Retido</span>
              <span class="text-2xl font-mono text-[#10B981] font-bold">{{ formatCurrency(tesouraria.lucro_retido) }}</span>
            </div>
            <div class="bg-blue-500/10 border border-blue-500/30 p-5 rounded-xl flex flex-col gap-1 relative overflow-hidden">
              <span class="text-[10px] text-blue-400 uppercase tracking-widest font-bold">Aporte Rápido (R$)</span>
              <div class="flex mt-1 gap-2 z-10">
                <input type="number" v-model="valorAporte" class="bg-black/50 text-white text-sm px-2 py-1 w-full rounded border border-white/10 outline-none" placeholder="Valor" />
                <button @click="processarAporte" :disabled="isProcessing" class="bg-blue-500 text-black px-3 py-1 font-bold text-[10px] uppercase rounded hover:bg-white transition-colors disabled:opacity-50">Injetar</button>
              </div>
            </div>
          </div>

          <div class="border border-white/10 bg-black/20 rounded-xl p-6 flex flex-col gap-6">
            <div class="flex items-center justify-between border-b border-white/10 pb-4">
              <h3 class="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
                <CalendarClock size="16" class="text-[#10B981]"/> Política de Dividendos (Corporate S-Tier)
              </h3>
              <span class="text-[10px] bg-[#10B981]/20 text-[#10B981] px-3 py-1 rounded font-mono shadow-[0_0_10px_rgba(16,185,129,0.2)]">
                Cálculo Autônomo Ativo
              </span>
            </div>
            
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
               <div class="bg-black/40 border border-white/5 p-4 rounded-lg flex flex-col pointer-events-none">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">Base de Cálculo (Lucro Líquido)</span>
                  <span class="text-lg font-mono text-white mt-1">{{ formatCurrency(tesouraria.lucro_retido) }}</span>
               </div>
               <div class="bg-black/40 border border-white/5 p-4 rounded-lg flex flex-col pointer-events-none">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">Taxa de Repasse Máxima</span>
                  <span class="text-lg font-mono text-blue-400 mt-1">25%</span>
               </div>
               <div class="bg-[#10B981]/10 border border-[#10B981]/30 p-4 rounded-lg flex flex-col shadow-[0_0_15px_rgba(16,185,129,0.1)] relative overflow-hidden pointer-events-none">
                  <div class="absolute right-0 bottom-0 opacity-10"><DollarSign size="60"/></div>
                  <span class="text-[9px] text-[#10B981] uppercase tracking-widest font-bold relative z-10">Dividendo Projetado</span>
                  <span class="text-xl font-mono text-[#10B981] mt-1 font-bold relative z-10">{{ formatCurrency(valorDividendoEstimado) }}</span>
               </div>
               <div class="bg-black/40 border border-white/5 p-4 rounded-lg flex flex-col pointer-events-none">
                  <span class="text-[9px] text-gray-500 uppercase tracking-widest font-bold">Próxima Liquidação (D+4 Meses)</span>
                  <span class="text-lg font-mono text-white mt-1">{{ nextDividendDate }}</span>
               </div>
            </div>
            
            <div class="mt-2 bg-blue-500/10 border border-blue-500/20 p-3 rounded-lg flex items-center gap-3">
              <Info size="14" class="text-blue-400 shrink-0" />
              <p class="text-[10px] text-blue-200 font-mono leading-relaxed">
                <strong>Protocolo Institucional:</strong> Os dividendos são processados em janelas quadrimestrais (Jan, Mai, Set). Apenas o lucro excedente gerado pelas operações da IA é contabilizado. No dia <strong>{{ nextDividendDate }}</strong>, o montante exato de <strong>{{ formatCurrency(valorDividendoEstimado) }}</strong> será transferido e liquidado automaticamente para salvaguardar a operação de risco.
              </p>
            </div>
          </div>
        </div>

        <div v-else-if="abaAtiva === 'perfil'" class="flex flex-col gap-8 max-w-4xl pb-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="flex flex-col gap-2">
              <label class="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Nome do Operador</label>
              <input type="text" v-model="config.nome" class="bg-black/50 text-sm text-white border border-white/10 rounded-lg px-4 py-3 outline-none focus:border-white transition-colors" />
            </div>
            <div class="flex flex-col gap-2">
              <label class="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Username (Login)</label>
              <input type="text" v-model="config.username" class="bg-black/50 text-sm text-white border border-white/10 rounded-lg px-4 py-3 outline-none focus:border-white transition-colors" />
            </div>
            <div class="flex flex-col gap-2">
              <label class="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Cargo (Ex: Lead Quant Manager)</label>
              <input type="text" v-model="config.cargo" class="bg-black/50 text-sm text-white border border-white/10 rounded-lg px-4 py-3 outline-none focus:border-white transition-colors" />
            </div>
            <div class="flex flex-col gap-2">
              <label class="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Título / Patente Secundária</label>
              <input type="text" v-model="config.titulo" class="bg-black/50 text-sm text-white border border-white/10 rounded-lg px-4 py-3 outline-none focus:border-white transition-colors" />
            </div>
            <div class="flex flex-col gap-2 md:col-span-2">
              <label class="text-[10px] text-gray-400 uppercase tracking-widest font-bold">E-mail Administrativo</label>
              <input type="email" v-model="config.email" class="w-full bg-black/50 text-sm text-white border border-white/10 rounded-lg px-4 py-3 outline-none focus:border-white transition-colors" />
            </div>
          </div>

          <div class="border-t border-white/10 pt-6 flex flex-col gap-4">
             <h3 class="text-sm font-bold text-red-400 uppercase tracking-widest flex items-center gap-2">
              <KeyRound size="16" /> Modificar Chave de Acesso (Senha)
            </h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
               <input type="password" v-model="config.nova_senha" placeholder="Digite a nova senha..." class="bg-black/50 text-sm text-white border border-white/10 rounded-lg px-4 py-3 outline-none focus:border-red-500/50 transition-colors placeholder-gray-600" />
               <span class="text-[10px] text-gray-500 font-mono my-auto pl-2">* Deixe em branco se não quiser alterar a senha atual.</span>
            </div>
          </div>
        </div>

        <div v-else-if="abaAtiva === 'visual'" class="flex flex-col gap-8 pb-4">
          <div class="flex flex-col gap-4">
             <h3 class="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2 border-b border-white/10 pb-2">
              <Palette size="16" class="text-bet-primary"/> Tema Global da BetGenius
            </h3>
            <div class="grid grid-cols-2 gap-4 max-w-xl">
              <div @click="config.tema_interface = 'institutional-dark'" class="bg-[#0b0f19] border p-4 rounded-xl flex flex-col gap-2 cursor-pointer transition-colors" :class="config.tema_interface === 'institutional-dark' ? 'border-bet-primary shadow-[0_0_15px_rgba(140,199,255,0.2)]' : 'border-white/5 hover:border-white/20'">
                <span class="font-bold text-sm text-white uppercase">Institutional Dark</span>
                <span class="text-[10px] font-mono text-gray-500">O Padrão S-Tier (Escuro, Neon Azul).</span>
              </div>
              <div @click="config.tema_interface = 'light-bloomberg'" class="bg-gray-200 border p-4 rounded-xl flex flex-col gap-2 cursor-pointer transition-colors" :class="config.tema_interface === 'light-bloomberg' ? 'border-orange-500 shadow-[0_0_15px_rgba(249,115,22,0.3)]' : 'border-gray-400 hover:border-gray-500'">
                <span class="font-bold text-sm text-black uppercase">Terminal Light</span>
                <span class="text-[10px] font-mono text-gray-700">Foco extremo nos dados (Estilo Bloomberg).</span>
              </div>
            </div>
          </div>

          <div class="border-t border-white/10 pt-6 flex flex-col gap-4">
            <div class="flex justify-between items-center border-b border-white/10 pb-2">
               <h3 class="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
                <Image size="16" class="text-purple-400"/> Slideshow da Tela de Login
              </h3>
              <button @click="$refs.loginImageInput.click()" class="bg-purple-500/20 text-purple-400 border border-purple-500/30 px-3 py-1.5 rounded text-[10px] uppercase font-bold tracking-widest hover:bg-purple-500 hover:text-black transition-colors flex items-center gap-2">
                <Plus size="12"/> Adicionar Imagem
              </button>
              <input type="file" ref="loginImageInput" class="hidden" @change="handleLoginImageUpload" accept="image/*" />
            </div>

            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-2">
               <div v-for="(img, idx) in imagensLogin" :key="img.id || idx" class="relative group rounded-xl overflow-hidden border border-white/10 aspect-video bg-black">
                 <img :src="img.image_data" class="w-full h-full object-cover opacity-70 group-hover:opacity-30 transition-opacity" />
                 <div class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <button @click="removerImagemLogin(idx)" class="bg-red-500 text-black p-2 rounded-full hover:scale-110 shadow-lg">
                      <Trash2 size="16"/>
                    </button>
                 </div>
               </div>

               <div v-if="imagensLogin.length === 0" class="col-span-full py-8 flex flex-col items-center justify-center text-gray-500 border border-dashed border-white/10 rounded-xl bg-black/20">
                  <Image size="32" class="mb-2 opacity-50"/>
                  <span class="text-[10px] font-mono uppercase">Nenhuma imagem no slideshow</span>
               </div>
            </div>
          </div>
        </div>

      </transition>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue';
import axios from 'axios';
import { 
  Settings, Save, KeyRound, User, UploadCloud, Globe, BrainCircuit, Landmark, 
  Briefcase, FlaskConical, ShieldCheck, Fingerprint, Palette, Cpu, Loader2, ArrowDownCircle, DollarSign,
  CalendarClock, Image, Plus, Trash2, Info
} from 'lucide-vue-next';

const globalState = inject('globalState');

// Puxa a variável de ambiente da Vercel. Se não achar, usa o localhost de fallback.
const API_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1`;

const abaAtiva = ref('tesouraria');
const isLoading = ref(true);
const isSaving = ref(false);
const isProcessing = ref(false);
const valorAporte = ref(null);

const config = ref({
  modo: 'REAL',
  nivel_dominancia: 2,
  nome: '',
  username: '',
  cargo: '',
  titulo: '',
  email: '',
  nova_senha: '', 
  avatar: '',
  fonte: 'jersey',
  tema_interface: 'institutional-dark',
  auth_method: 'standard'
});

const tesouraria = ref({ banca_real: 0, banca_bench: 0, lucro_retido: 0 });
const imagensLogin = ref([]);

const getConfigHeaders = () => {
  const token = localStorage.getItem('betgenius_token');
  return { headers: { Authorization: `Bearer ${token}` } };
};

const carregarDados = async () => {
  isLoading.value = true;
  try {
    const opts = getConfigHeaders();
    // Cache-Buster para ignorar dados velhos
    const ts = new Date().getTime();
    
    const [resConfig, resTreasury] = await Promise.all([
      axios.get(`${API_URL}/system/config?t=${ts}`, opts),
      axios.get(`${API_URL}/fund/treasury?t=${ts}`, opts)
    ]);
    
    config.value = { ...config.value, ...resConfig.data.user_config };
    imagensLogin.value = resConfig.data.login_images || [];
    tesouraria.value = resTreasury.data;
    
    const wrapper = document.querySelector('.app-master-wrapper') || document.documentElement;
    if (wrapper && config.value.tema_interface) {
        wrapper.setAttribute('data-theme', config.value.tema_interface);
    }
    if (globalState) globalState.uiMode = config.value.modo;
    
  } catch (error) {
    console.error("Falha ao carregar Config:", error);
  } finally {
    isLoading.value = false;
  }
};

const salvarConfiguracoes = async () => {
  isSaving.value = true;
  try {
    const payload = {
      user_config: config.value,
      login_images: imagensLogin.value
    };

    await axios.put(`${API_URL}/system/config`, payload, getConfigHeaders());
    
    const wrapper = document.querySelector('.app-master-wrapper') || document.documentElement;
    if (wrapper) wrapper.setAttribute('data-theme', config.value.tema_interface);

    if (globalState) globalState.uiMode = config.value.modo;
    config.value.nova_senha = '';
    
    alert("Sincronizado. Recarregando o terminal para aplicar os novos perfis...");
    setTimeout(() => { window.location.reload(); }, 1000); 
    
  } catch (error) {
    alert("Falha de Comunicação: O Banco de Dados recusou a alteração.");
  } finally {
    isSaving.value = false;
  }
};

const processarAporte = async () => {
  const val = parseFloat(valorAporte.value);
  if (!val || val <= 0) return;
  
  isProcessing.value = true;
  try {
    await axios.post(`${API_URL}/fund/deposit`, { amount: val, target: config.value.modo }, getConfigHeaders());
    await carregarDados(); 
    valorAporte.value = null;
    
    // FIX S-TIER: Recarrega a Placa-Mãe inteira para que o TopBar (App.vue) também pegue o novo valor!
    alert(`Aporte de R$ ${val.toFixed(2)} processado com sucesso! Sincronizando terminal...`);
    setTimeout(() => { window.location.reload(); }, 500);
    
  } catch (e) {
    alert("Erro ao tentar processar o aporte na Tesouraria.");
  } finally {
    isProcessing.value = false;
  }
};

const handleAvatarUpload = (event) => {
  const file = event.target.files[0];
  if (file) {
    const reader = new FileReader();
    reader.onload = (e) => { config.value.avatar = e.target.result; };
    reader.readAsDataURL(file);
  }
};

const handleLoginImageUpload = (event) => {
  const file = event.target.files[0];
  if (file) {
    const reader = new FileReader();
    reader.onload = (e) => { imagensLogin.value.push({ image_data: e.target.result, is_active: true }); };
    reader.readAsDataURL(file);
  }
};

const removerImagemLogin = (index) => { imagensLogin.value.splice(index, 1); };

const formatCurrency = (value) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value || 0);

const valorDividendoEstimado = computed(() => {
    return (tesouraria.value.lucro_retido * 0.25);
});

const nextDividendDate = computed(() => {
  const now = new Date();
  const month = now.getMonth(); 
  let nextMonth = 0; 
  let nextYear = now.getFullYear();
  
  if (month < 4) { nextMonth = 4; }
  else if (month < 8) { nextMonth = 8; }
  else { nextMonth = 0; nextYear += 1; }
  
  return `05/${String(nextMonth + 1).padStart(2, '0')}/${nextYear}`;
});

const hierarquiaInfo = computed(() => {
  if (config.value.nivel_dominancia === 3) return { titulo: '3. Alpha', desc: 'IA recua. Você é o tomador de risco.', bgClass: 'bg-red-500/10 border-red-500/30', textClass: 'text-red-400' };
  if (config.value.nivel_dominancia === 2) return { titulo: '2. Copiloto', desc: 'Sinergia humano/IA.', bgClass: 'bg-blue-500/10 border-blue-500/30', textClass: 'text-blue-400' };
  return { titulo: '1. Guiado', desc: 'IA bloqueia saídas fora da grade de risco.', bgClass: 'bg-green-500/10 border-green-500/30', textClass: 'text-green-400' };
});

onMounted(carregarDados);
</script>

<style scoped>
.theme-real { --dynamic-color: var(--bet-primary); --dynamic-color-rgb: 140, 199, 255; }
.theme-benchmark { --dynamic-color: #a855f7; --dynamic-color-rgb: 168, 85, 247; }
.border-dynamic { border-color: var(--dynamic-color) !important; }
.border-t-dynamic { border-top-color: var(--dynamic-color) !important; }
.text-dynamic { color: var(--dynamic-color) !important; }
.bg-dynamic { background-color: var(--dynamic-color) !important; }
.shadow-dynamic { box-shadow: 0 0 20px rgba(var(--dynamic-color-rgb), 0.4) !important; }

.glass-card { background: rgba(18, 25, 39, 0.85); border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.05); backdrop-filter: blur(20px); }

.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.15); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.3); }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(10px); }
</style>