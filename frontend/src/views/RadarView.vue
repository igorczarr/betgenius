<template>
  <div class="w-full h-full overflow-y-auto custom-scrollbar px-8 py-6 pb-28 relative">
    
    <div class="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start fade-in-up">
      
      <div class="col-span-1 xl:col-span-9 flex flex-col gap-6">
        <WidgetRadarValor />
        
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <WidgetSteamers />
          <WidgetGeninho />
          <WidgetInPlay />
        </div>

        <WidgetGoldPicks class="mt-2" />
      </div>

      <div class="col-span-1 xl:col-span-3 h-[850px] glass-card overflow-hidden">
        <WidgetLateralDireito />
      </div>

    </div>

    <div class="fixed bottom-8 right-8 z-[90]">
      <transition name="slide-up">
        <div v-show="ticketAberto" class="mb-4 w-[360px] shadow-2xl origin-bottom-right rounded-2xl overflow-hidden border border-gray-700/50">
          <WidgetSmartTicket />
        </div>
      </transition>
      
      <button @click="ticketAberto = !ticketAberto" class="fab-btn ml-auto w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300 relative">
        <span class="absolute inset-0 rounded-full animate-ping opacity-20 bg-bet-primary"></span>
        <X v-if="ticketAberto" :size="28" class="text-black relative z-10" />
        <Receipt v-else :size="28" class="text-black relative z-10" />
        <div v-show="!ticketAberto" class="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold w-5 h-5 flex items-center justify-center rounded-full border-2 border-[#1b2539] z-20">3</div>
      </button>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue';
import { X, Receipt } from 'lucide-vue-next'; 

import WidgetRadarValor from '../components/WidgetRadarValor.vue';
import WidgetSmartTicket from '../components/WidgetSmartTicket.vue';
import WidgetLateralDireito from '../components/WidgetLateralDireito.vue';
import WidgetSteamers from '../components/WidgetSteamers.vue';
import WidgetGeninho from '../components/WidgetGeninho.vue';
import WidgetInPlay from '../components/WidgetInPlay.vue';
import WidgetGoldPicks from '../components/WidgetGoldPicks.vue';

const ticketAberto = ref(false);
</script>