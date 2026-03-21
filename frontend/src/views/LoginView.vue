<template>
  <div class="login-wrapper">
    <div class="login-orb orb-1"></div>
    <div class="login-orb orb-2"></div>
    
    <div class="glass-login-panel scale-up-center">
      <div class="mb-6 flex justify-center">
        <img src="../assets/images/logo.png" alt="BetGenius" class="h-24 object-contain drop-shadow-2xl" />
      </div>
      <h1 class="font-mono login-title">BETGENIUS</h1>
      <p class="login-subtitle uppercase tracking-widest text-xs">Operações Quantitativas</p>
      
      <form @submit.prevent="fazerLogin" style="width: 100%; margin-top: 30px;">
        <input type="email" class="glass-input-premium" placeholder="ID Institucional (E-mail)" v-model="email" required />
        <input type="password" class="glass-input-premium" placeholder="Chave de Acesso" v-model="senha" required />
        
        <button type="submit" class="btn-neon-green w-full mt-4">
          Acessar Terminal
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();
const email = ref('');
const senha = ref('');

const fazerLogin = () => {
  // Simulando a autenticação e redirecionando para a Dashboard ("/")
  if (email.value && senha.value) {
    localStorage.setItem('betgenius_user', 'Igor C.');
    router.push('/');
  }
};
</script>

<style scoped>
/* Os estilos específicos do Login que tiramos do App.vue global */
.login-wrapper { position: relative; width: 100vw; height: 100vh; display: flex; align-items: center; justify-content: center; overflow: hidden; background: var(--bg-app); }
.login-orb { position: absolute; border-radius: 50%; filter: blur(120px); opacity: 0.2; }
.orb-1 { width: 600px; height: 600px; background: var(--bet-primary); top: -200px; left: -100px; }
.orb-2 { width: 500px; height: 500px; background: var(--bet-secondary); bottom: -150px; right: -100px; }
.glass-login-panel { background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(40px); border: 1px solid rgba(140, 199, 255, 0.15); padding: 50px 40px; border-radius: 24px; width: 100%; max-width: 420px; text-align: center; position: relative; z-index: 10; box-shadow: 0 40px 80px rgba(0,0,0,0.8); }
.login-title { color: var(--text-main); font-size: 36px; margin: 0 0 5px 0; }
.login-subtitle { color: var(--bet-primary); margin-bottom: 30px; font-weight: 600; opacity: 0.8;}
.scale-up-center { animation: scaleUp 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes scaleUp { from { opacity: 0; transform: scale(0.9); } to { opacity: 1; transform: scale(1); } }
</style>