// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      // Uma rota base vazia é suficiente, pois o App.vue controla o login e as abas.
      path: '/',
      name: 'home',
      component: { template: '<div>Carregando BetGenius...</div>' } 
    }
  ]
})

export default router