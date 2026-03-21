// src/main.js
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './style.css' // Seu CSS global e Tailwind

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')