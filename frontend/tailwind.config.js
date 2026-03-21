/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bg-dark': '#0f172a', // Azul escuro institucional profundo
        'panel-dark': '#1e293b', // Fundo dos widgets
        'bet-green': '#10b981', // Verde lucro
        'bet-red': '#ef4444', // Vermelho red
      }
    },
  },
  plugins: [],
}