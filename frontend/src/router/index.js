// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  // Cria o histórico de navegação nativo do HTML5 (remove o '#' da URL)
  history: createWebHistory(import.meta.env.BASE_URL),
  
  routes: [
    // -----------------------------------------------------------
    // ROTA LIVRE (PÚBLICA)
    // -----------------------------------------------------------
    {
      path: '/login',
      name: 'login',
      // Apontamos diretamente para a pasta components
      component: () => import('@/components/ViewLogin.vue') 
    },

    // -----------------------------------------------------------
    // ROTAS PROTEGIDAS (DENTRO DA DASHBOARD)
    // -----------------------------------------------------------
    {
      path: '/',
      component: () => import('@/layouts/MasterLayout.vue'), // O esqueleto da Dashboard
      redirect: '/radar', // Se aceder apenas a '/', redireciona logo para o Radar
      children: [
        {
          path: 'radar',
          name: 'radar',
          component: () => import('@/components/ViewRadar.vue')
        },
        {
          path: 'match-center',
          name: 'matchCenter',
          component: () => import('@/components/ViewMatchCenter.vue')
        },
        {
          path: 'quantlab',
          name: 'quantlab',
          component: () => import('@/components/ViewQuantlab.vue')
        },
        {
          path: 'hype-engine',
          name: 'hypeEngine',
          component: () => import('@/components/ViewHypeEngine.vue')
        },
        {
          path: 'gestao-fundo',
          name: 'gestaoFundo',
          component: () => import('@/components/ViewGestaoFundo.vue')
        }
      ]
    }
  ]
})

export default router