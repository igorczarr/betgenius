// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

// Vamos criar essas telas no próximo passo
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue')
    },
    {
      path: '/',
      component: () => import('../layouts/MasterLayout.vue'), // O esqueleto da Dashboard
      children: [
        {
          path: '', // Rota padrão ao logar
          name: 'radar',
          component: () => import('../views/RadarView.vue')
        }
        // Futuramente colocaremos o Match Center e Banca aqui!
      ]
    }
  ]
})

export default router