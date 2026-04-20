<template>
  <transition name="preloader-fade">
    <div v-if="isPreloading" class="fixed inset-0 z-[9999] bg-[#0b0f19] flex flex-col items-center justify-center">
      <div class="relative flex items-center justify-center">
        <div class="absolute w-40 h-40 bg-bet-primary/20 rounded-full blur-[50px] animate-pulse-fast"></div>
        
        <svg class="w-32 h-32 relative z-10 animate-logo-draw" viewBox="0 0 550 550" xmlns="http://www.w3.org/2000/svg">
          <path class="fill-bet-primary drop-shadow-[0_0_15px_rgba(140,199,255,0.8)]" 
                d="M378.51,206.83c6.63,0,25.82-18,25.82-47.06,0-36.86-30.92-72.54-79.51-72.54H250.06V190H305V140.74h23.27c12.74,0,24.8,10.88,24.8,26.34,0,16-12.74,27.17-25.82,27.17H244.27c-72,0-131.71,57.13-133.23,129.08q0,1.46,0,2.91c0,75.12,61.08,136.53,138.65,136.53,59.29,0,109.89-36,122.54-99.12H317.73c-4.25,28.65-30.27,45.89-65.78,45.89-51.45,0-87-37.57-87-83.3,0-49.16,41.31-83.77,82.13-83.77.67,0,1.34,0,2,0h99.22c26.16,0,37,15.8,37,31.6,0,21.06-19,33.3-36.87,33.3H250.06v51.67H370.41a48.57,48.57,0,0,0,9.16-.85c42.06-8,59.42-46.44,59.42-80.21C439,234,404.83,206.83,378.51,206.83Z"/>
        </svg>
      </div>
      
      <div class="mt-8 flex flex-col items-center gap-2">
        <div class="w-48 h-1 bg-white/10 rounded-full overflow-hidden">
          <div class="h-full bg-bet-primary animate-progress-bar"></div>
        </div>
        <span class="text-[9px] font-mono text-bet-primary uppercase tracking-[0.3em] animate-pulse">Iniciando Motor Quantitativo...</span>
      </div>
    </div>
  </transition>

  <div v-show="!isPreloading" class="h-screen w-full flex bg-[#0b0f19] overflow-hidden fade-in-up">

    <div class="hidden lg:flex relative w-[55%] flex-col justify-between p-14 border-r border-white/5 overflow-hidden shadow-[20px_0_50px_rgba(0,0,0,0.8)] z-10 immersive-bg">
      
      <div class="relative z-10 flex flex-col items-start gap-2">
         <svg class="w-24 h-24 mb-2 drop-shadow-[0_0_20px_rgba(140,199,255,0.4)]" viewBox="0 0 550 550" xmlns="http://www.w3.org/2000/svg">
            <path class="fill-white" d="M378.51,206.83c6.63,0,25.82-18,25.82-47.06,0-36.86-30.92-72.54-79.51-72.54H250.06V190H305V140.74h23.27c12.74,0,24.8,10.88,24.8,26.34,0,16-12.74,27.17-25.82,27.17H244.27c-72,0-131.71,57.13-133.23,129.08q0,1.46,0,2.91c0,75.12,61.08,136.53,138.65,136.53,59.29,0,109.89-36,122.54-99.12H317.73c-4.25,28.65-30.27,45.89-65.78,45.89-51.45,0-87-37.57-87-83.3,0-49.16,41.31-83.77,82.13-83.77.67,0,1.34,0,2,0h99.22c26.16,0,37,15.8,37,31.6,0,21.06-19,33.3-36.87,33.3H250.06v51.67H370.41a48.57,48.57,0,0,0,9.16-.85c42.06-8,59.42-46.44,59.42-80.21C439,234,404.83,206.83,378.51,206.83Z"/>
         </svg>
         
         <div class="inline-flex items-center gap-3 bg-black/30 border border-bet-primary/20 px-5 py-2.5 rounded-xl backdrop-blur-md shadow-[0_5px_15px_rgba(0,0,0,0.5)]">
            <span class="w-2 h-2 rounded-full bg-bet-primary animate-pulse"></span>
            <span class="text-xs font-jersey uppercase tracking-[0.15em] text-white">Paga o que é meu, Bethânia!</span>
         </div>
      </div>

      <div class="relative z-10 flex flex-col gap-6">
        <h2 class="font-jersey text-[5rem] text-white tracking-wider leading-[0.9] drop-shadow-lg">
          QUANTITATIVE<br/>
          <span class="text-transparent bg-clip-text bg-gradient-to-r from-bet-primary to-blue-400 drop-shadow-[0_0_30px_rgba(140,199,255,0.3)]">
            ALPHA GENERATION
          </span>
        </h2>
        <p class="text-gray-300 max-w-md text-sm leading-relaxed border-l-2 border-bet-primary/50 pl-5 font-mono">
          Terminal de Alta Frequência (HFT) de uso estrito por gestores do fundo. Algoritmos matemáticos em tempo real para detecção de assimetrias no mercado esportivo.
        </p>
      </div>

      <div class="relative z-10 flex items-center justify-between text-[10px] text-gray-400 font-mono uppercase tracking-widest bg-black/20 px-4 py-2 rounded-lg border border-white/5 backdrop-blur-sm w-fit gap-8">
        <span>&copy; 2026 BetGenius Quant Fund</span>
        <span class="flex items-center gap-2 text-bet-primary"><Lock size="10"/> ACESSO SECURE-ENCLAVE</span>
      </div>
    </div>


    <div class="w-full lg:w-[45%] flex items-center justify-center relative bg-black">
      
      <div class="absolute inset-0 z-0 overflow-hidden">
        <transition-group name="slide-fade">
          <div v-for="(img, index) in slideImages" :key="index" 
               v-show="activeSlide === index"
               class="absolute inset-0 w-full h-full bg-cover bg-center slide-image"
               :style="{ backgroundImage: `url(${img})` }">
          </div>
        </transition-group>
        
        <div class="absolute inset-0 bg-gradient-to-b from-[#0b0f19]/80 via-[#0b0f19]/60 to-[#0b0f19]/90 z-10 backdrop-blur-[2px]"></div>
      </div>

      <div class="w-full max-w-[420px] p-8 sm:p-10 relative z-20 bg-[#0f1523]/70 backdrop-blur-2xl border border-white/10 rounded-3xl shadow-[0_30px_60px_rgba(0,0,0,0.8)] mx-4">

        <div class="mb-10 text-center lg:text-left">
          <div class="lg:hidden flex flex-col items-center mb-8 gap-3">
             <svg class="w-20 h-20 drop-shadow-[0_0_15px_rgba(140,199,255,0.4)]" viewBox="0 0 550 550" xmlns="http://www.w3.org/2000/svg">
                <path class="fill-white" d="M378.51,206.83c6.63,0,25.82-18,25.82-47.06,0-36.86-30.92-72.54-79.51-72.54H250.06V190H305V140.74h23.27c12.74,0,24.8,10.88,24.8,26.34,0,16-12.74,27.17-25.82,27.17H244.27c-72,0-131.71,57.13-133.23,129.08q0,1.46,0,2.91c0,75.12,61.08,136.53,138.65,136.53,59.29,0,109.89-36,122.54-99.12H317.73c-4.25,28.65-30.27,45.89-65.78,45.89-51.45,0-87-37.57-87-83.3,0-49.16,41.31-83.77,82.13-83.77.67,0,1.34,0,2,0h99.22c26.16,0,37,15.8,37,31.6,0,21.06-19,33.3-36.87,33.3H250.06v51.67H370.41a48.57,48.57,0,0,0,9.16-.85c42.06-8,59.42-46.44,59.42-80.21C439,234,404.83,206.83,378.51,206.83Z"/>
             </svg>
             <span class="text-[9px] font-jersey uppercase tracking-[0.2em] text-bet-primary bg-bet-primary/10 px-3 py-1 rounded border border-bet-primary/20">Paga o que é meu, Bethânia!</span>
          </div>
          <h3 class="text-2xl font-bold text-white mb-2">Acesso Restrito</h3>
          <p class="text-[13px] text-gray-400 font-mono">Insira suas credenciais institucionais.</p>
        </div>

        <form @submit.prevent="submitLogin" class="flex flex-col gap-5">

          <div class="flex flex-col gap-2 relative group">
            <label class="text-[10px] uppercase tracking-widest font-bold text-gray-400 group-focus-within:text-bet-primary transition-colors">ID do Gestor</label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <User size="16" class="text-gray-500 group-focus-within:text-bet-primary transition-colors" />
              </div>
              <input type="email" v-model="email" required
                class="w-full bg-black/50 border border-white/10 text-white text-sm rounded-xl pl-12 pr-4 py-4 outline-none focus:bg-black/80 focus:border-bet-primary/70 focus:ring-1 focus:ring-bet-primary/50 transition-all placeholder-gray-600 font-mono shadow-inner"
                placeholder="nome@betgenius.fund" />
            </div>
          </div>

          <div class="flex flex-col gap-2 relative group mt-2">
            <div class="flex justify-between items-center">
              <label class="text-[10px] uppercase tracking-widest font-bold text-gray-400 group-focus-within:text-bet-primary transition-colors">Chave de Acesso</label>
              <a href="#" class="text-[10px] text-gray-500 hover:text-white underline decoration-gray-700 underline-offset-2 transition-colors">Esqueci a chave</a>
            </div>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <KeyRound size="16" class="text-gray-500 group-focus-within:text-bet-primary transition-colors" />
              </div>
              <input type="password" v-model="senha" required
                class="w-full bg-black/50 border border-white/10 text-white text-sm rounded-xl pl-12 pr-4 py-4 outline-none focus:bg-black/80 focus:border-bet-primary/70 focus:ring-1 focus:ring-bet-primary/50 transition-all placeholder-gray-600 font-mono tracking-widest shadow-inner"
                placeholder="••••••••••••" />
            </div>
          </div>

          <button type="submit" class="group relative w-full flex items-center justify-center gap-3 bg-bet-primary text-black font-bold uppercase tracking-widest text-xs py-4 rounded-xl mt-6 overflow-hidden transition-all hover:scale-[1.02] hover:shadow-[0_10px_30px_rgba(140,199,255,0.3)] active:scale-95">
            <div class="absolute inset-0 w-full h-full bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-out"></div>
            <span class="relative z-10">Inicializar Terminal</span>
            <ArrowRight size="16" strokeWidth="3" class="relative z-10 group-hover:translate-x-1 transition-transform" />
          </button>

        </form>

      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import axios from 'axios';
import { User, KeyRound, ArrowRight, ShieldCheck, Lock } from 'lucide-vue-next';

const emit = defineEmits(['do-login']);
const email = ref('');
const senha = ref('');

const isPreloading = ref(true);
const activeSlide = ref(0);
let slideInterval;

// Fallbacks caso o banco esteja vazio
const slideImages = ref([
  'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?q=80&w=1920&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1540747913346-19e32dc3e97e?q=80&w=1920&auto=format&fit=crop',
  'https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=1920&auto=format&fit=crop'
]);

onMounted(async () => {
  // Busca dinamicamente as imagens cadastradas na Configuração
  try {
    const response = await axios.get('http://localhost:8000/api/v1/system/config');
    if (response.data && response.data.login_images && response.data.login_images.length > 0) {
        slideImages.value = response.data.login_images.map(img => img.image_data);
    }
  } catch (error) {
    console.log('Utilizando imagens padrão.');
  }

  setTimeout(() => {
    isPreloading.value = false;
  }, 2500);

  slideInterval = setInterval(() => {
    activeSlide.value = (activeSlide.value + 1) % slideImages.value.length;
  }, 6000);
});

onUnmounted(() => {
  clearInterval(slideInterval);
});

const submitLogin = () => {
  if (email.value && senha.value) {
    emit('do-login', { email: email.value, senha: senha.value });
  }
};
</script>

<style scoped>
.animate-pulse-fast { animation: pulseFast 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
@keyframes pulseFast { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(1.2); } }
.animate-logo-draw { animation: logoGlow 2s ease-out forwards; }
@keyframes logoGlow { 0% { opacity: 0; filter: brightness(0) blur(10px); transform: scale(0.9); } 50% { filter: brightness(2) blur(0px); transform: scale(1.05); } 100% { opacity: 1; filter: brightness(1) blur(0px); transform: scale(1); } }
.animate-progress-bar { animation: fillProgress 2s cubic-bezier(0.65, 0, 0.35, 1) forwards; }
@keyframes fillProgress { 0% { width: 0%; } 100% { width: 100%; } }
.preloader-fade-leave-active { transition: opacity 0.8s ease, transform 0.8s ease; }
.preloader-fade-leave-to { opacity: 0; transform: scale(1.1); }
.immersive-bg { background: linear-gradient(45deg, #0b0f19, #172033, #0b0f19); background-size: 400% 400%; animation: gradientAura 15s ease infinite; }
@keyframes gradientAura { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
.slide-image { transform: scale(1.05); will-change: opacity, filter; }
.slide-fade-enter-active, .slide-fade-leave-active { transition: all 1.5s cubic-bezier(0.4, 0, 0.2, 1); }
.slide-fade-enter-from { opacity: 0; filter: blur(10px); }
.slide-fade-leave-to { opacity: 0; filter: blur(10px); }
.fade-in-up { animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
@keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
</style>