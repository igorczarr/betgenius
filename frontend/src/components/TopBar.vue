<template>
  <header class="bg-panel-dark border-b border-gray-700 p-4 shadow-lg">
    <div class="container mx-auto flex justify-between items-center">
      
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 bg-bet-green rounded flex items-center justify-center font-bold text-bg-dark">
          BG
        </div>
        <h1 class="text-xl font-bold tracking-wider text-white">BET<span class="text-bet-green">GENIUS</span> <span class="text-xs text-gray-400 font-normal border border-gray-600 px-1 rounded">PRO</span></h1>
      </div>

      <div class="flex gap-6">
        
        <div class="flex flex-col items-end">
          <span class="text-xs text-gray-400 uppercase tracking-widest">Jogos Mapeados</span>
          <span class="text-lg font-bold text-white">247</span>
        </div>

        <div class="flex flex-col items-end border-l border-gray-600 pl-6">
          <span class="text-xs text-gray-400 uppercase tracking-widest">Oportunidades (+EV)</span>
          <span class="text-lg font-bold text-yellow-400 flex items-center gap-1">
            <span class="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></span> 12
          </span>
        </div>

        <div class="flex flex-col items-end border-l border-gray-600 pl-6">
          <span class="text-xs text-gray-400 uppercase tracking-widest">Lucro Diário</span>
          <span class="text-lg font-bold text-bet-green">+ R$ 420,50</span>
        </div>

        <div class="flex flex-col items-end border-l border-gray-600 pl-6">
          <span class="text-xs text-gray-400 uppercase tracking-widest">Banca Atual</span>
          <span class="text-lg font-bold text-white">R$ 200,00</span>
        </div>

      </div>
    </div>
  </header>
</template>

<script setup>
// Aqui depois vamos conectar com o Pinia (Gerenciador de Estado) 
// para que esses números venham do Backend/Banco de Dados em tempo real.
</script>