<template>
  <WidgetCard titulo="Scanner de Valor (+EV)">
    
    <template #icone>
      <Crosshair :size="16" class="text-blue-500" />
    </template>

    <template #acoes>
      <button 
        @click="exportToCSV"
        class="bg-black/50 hover:bg-blue-500/20 hover:text-blue-400 text-[10px] uppercase font-bold tracking-widest text-gray-400 px-3 py-1.5 rounded border border-white/10 transition-colors flex items-center gap-2"
        :disabled="isLoading"
      >
        <Download size="12" /> Exportar CSV
      </button>
    </template>

    <div class="w-full overflow-x-auto custom-scrollbar pb-2">
      <table class="w-full text-left border-collapse min-w-[700px]">
        <thead>
          <tr class="border-b border-white/10 text-[10px] text-gray-500 uppercase tracking-widest font-mono bg-black/20">
            <th class="py-3 px-4 font-bold rounded-tl-lg">Partida</th>
            <th class="py-3 px-2 font-bold">Mercado (SGP/Single)</th>
            <th class="py-3 px-2 font-bold text-center cursor-pointer hover:text-white transition-colors" @click="sortBy('prob')">
              Prob. IA <ArrowUpDown size="10" class="inline opacity-50" />
            </th>
            <th class="py-3 px-2 font-bold text-center">Odd Justa (Fair)</th>
            <th class="py-3 px-2 font-bold text-center cursor-pointer hover:text-white transition-colors" @click="sortBy('odd')">
              Odd Bookie <ArrowUpDown size="10" class="inline opacity-50" />
            </th>
            <th class="py-3 px-2 font-bold text-center cursor-pointer hover:text-yellow-400 transition-colors" @click="sortBy('ev')">
              EV (+Edge) <ArrowUpDown size="10" class="inline opacity-50" />
            </th>
            <th class="py-3 px-4 font-bold text-right rounded-tr-lg">Ação</th>
          </tr>
        </thead>
        <tbody class="text-sm">
          
          <template v-if="isLoading">
            <tr v-for="i in 5" :key="'skel'+i" class="border-b border-white/5 animate-pulse bg-white/[0.02]">
              <td class="py-3 px-4"><div class="h-4 w-32 bg-gray-700 rounded mb-1"></div><div class="h-3 w-20 bg-gray-800 rounded"></div></td>
              <td class="py-3 px-2"><div class="h-5 w-24 bg-gray-700 rounded"></div></td>
              <td class="py-3 px-2"><div class="h-4 w-10 bg-gray-700 rounded mx-auto"></div></td>
              <td class="py-3 px-2"><div class="h-4 w-10 bg-gray-700 rounded mx-auto"></div></td>
              <td class="py-3 px-2"><div class="h-5 w-12 bg-gray-700 rounded mx-auto"></div></td>
              <td class="py-3 px-2"><div class="h-4 w-12 bg-gray-700 rounded mx-auto"></div></td>
              <td class="py-3 px-4 text-right"><div class="h-8 w-8 bg-gray-700 rounded ml-auto"></div></td>
            </tr>
          </template>

          <template v-else>
            <tr v-for="opp in sortedOpportunities" :key="opp.match_id" 
                class="border-b border-white/5 hover:bg-white/[0.03] transition-colors group">
              
              <td class="py-3 px-4">
                <div class="font-bold text-white text-xs">{{ opp.home_team }} <span class="text-gray-600 font-normal">v</span> {{ opp.away_team }}</div>
                <div class="text-[9px] text-gray-500 font-mono uppercase tracking-widest mt-1">{{ opp.liga }}</div>
              </td>
              
              <td class="py-3 px-2">
                <span class="bg-[#121927] text-gray-300 text-[10px] font-bold px-2 py-1 rounded border border-gray-700 uppercase tracking-wide">
                  {{ opp.mercado }}
                </span>
              </td>
              
              <td class="py-3 px-2 text-center font-mono font-bold text-blue-400 drop-shadow-[0_0_5px_rgba(59,130,246,0.3)]">
                {{ opp.confianca }}%
              </td>
              
              <td class="py-3 px-2 text-center font-mono text-gray-500 text-xs">
                {{ calculateFairOdd(opp.confianca) }}
              </td>
              
              <td class="py-3 px-2 text-center font-mono font-bold text-white">
                <span class="bg-blue-500/10 border border-blue-500/30 px-2.5 py-1 rounded text-white shadow-inner">
                  {{ opp.odd.toFixed(2) }}
                </span>
              </td>
              
              <td class="py-3 px-2 text-center font-mono font-bold text-yellow-400 bg-yellow-500/5">
                +{{ opp.ev }}%
              </td>
              
              <td class="py-3 px-4 text-right">
                <button @click="addToSlip(opp)" class="bg-[#121927] border border-white/10 hover:border-blue-500 hover:bg-blue-500 hover:text-white text-gray-400 w-8 h-8 flex items-center justify-center rounded-lg transition-all shadow-lg group-hover:shadow-[0_0_10px_rgba(59,130,246,0.2)] ml-auto">
                  <Plus :size="16" />
                </button>
              </td>

            </tr>
            
            <tr v-if="sortedOpportunities.length === 0">
              <td colspan="7" class="py-10 text-center text-xs text-gray-500 font-mono uppercase tracking-widest">
                Nenhuma anomalia (+EV) detectada no mercado no momento.
              </td>
            </tr>
          </template>

        </tbody>
      </table>
    </div>

  </WidgetCard>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { Crosshair, Plus, Download, ArrowUpDown } from 'lucide-vue-next';
import axios from 'axios';
import WidgetCard from './WidgetCard.vue';

const oportunidades = ref([]);
const isLoading = ref(true);

// Estado de Ordenação
const sortKey = ref('ev');
const sortDesc = ref(true);

const sortBy = (key) => {
  if (sortKey.value === key) {
    sortDesc.value = !sortDesc.value;
  } else {
    sortKey.value = key;
    sortDesc.value = true;
  }
};

// Computa as oportunidades ordenadas
const sortedOpportunities = computed(() => {
  return [...oportunidades.value].sort((a, b) => {
    let valA, valB;
    
    if (sortKey.value === 'prob') { valA = parseFloat(a.confianca); valB = parseFloat(b.confianca); }
    else if (sortKey.value === 'odd') { valA = parseFloat(a.odd); valB = parseFloat(b.odd); }
    else { valA = parseFloat(a.ev); valB = parseFloat(b.ev); } // default 'ev'

    return sortDesc.value ? valB - valA : valA - valB;
  });
});

// A matemática clássica: Odd Justa = 100 / Probabilidade
const calculateFairOdd = (prob) => {
  const p = parseFloat(prob);
  if (!p || p === 0) return "0.00";
  return (100 / p).toFixed(2);
};

// Busca os dados diretamente da API que criamos anteriormente
const fetchOpportunities = async () => {
  try {
    const res = await axios.get('http://localhost:8000/api/v1/quant/gold-picks');
    oportunidades.value = res.data;
  } catch (error) {
    console.error("❌ Falha ao carregar o Scanner de Valor:", error);
  } finally {
    isLoading.value = false;
  }
};

const addToSlip = (opp) => {
  console.log("Adicionando ao Ticket Builder:", opp);
  // Em uma arquitetura real Vue.js (Pinia/Vuex), aqui você despacha uma action
  // store.dispatch('ticket/addPick', opp)
  alert(`"${opp.home_team} v ${opp.away_team}" (${opp.mercado}) enviado para o Ticket Builder!`);
};

// Exportar os dados para CSV (Para o analista rodar no Excel/Python)
const exportToCSV = () => {
  const headers = ["Partida", "Liga", "Mercado", "ProbIA_%", "OddJusta", "OddBookie", "EV_%"];
  const rows = sortedOpportunities.value.map(o => 
    `"${o.home_team} v ${o.away_team}","${o.liga}","${o.mercado}",${o.confianca},${calculateFairOdd(o.confianca)},${o.odd},${o.ev}`
  );
  
  const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows].join("\n");
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `quant_scanner_ev_${new Date().toISOString().split('T')[0]}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

onMounted(fetchOpportunities);
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { height: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(59, 130, 246, 0.2); border-radius: 10px; }
</style>