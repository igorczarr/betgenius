# betgenius-backend/engine/math_models.py
import logging
import numpy as np
from dataclasses import dataclass
from typing import List, Union, Optional

logger = logging.getLogger(__name__)

# =====================================================================
# DTOs (Data Transfer Objects) - Tipagem Estrita
# =====================================================================
@dataclass(frozen=True)
class PricingResult:
    margin_percent: float
    true_probs: np.ndarray
    fair_odds: np.ndarray

@dataclass(frozen=True)
class Opportunity:
    expected_value: float
    kelly_stake_pct: float
    is_value: bool

# =====================================================================
# BETGENIUS HFT - QUANTITATIVE MATH ENGINE (WALL STREET GRADE)
# =====================================================================

class QuantPricingEngine:
    
    @staticmethod
    def remove_vig_power_method(odds: Union[List[float], np.ndarray]) -> Optional[PricingResult]:
        """
        O Padrão Ouro: Método da Potência para remoção de margem.
        Resolve a distorção do 'Favorite-Longshot Bias'.
        Utiliza Newton-Raphson para convergência matemática ultrarrápida.
        """
        arr_odds = np.array(odds, dtype=np.float64)
        
        # Validação de integridade a nível de máquina
        if arr_odds.size == 0 or np.any(arr_odds <= 1.0):
            logger.error(f"⚠️ Odds inválidas detectadas pelo motor: {odds}")
            return None

        implied_probs = 1.0 / arr_odds
        margin = np.sum(implied_probs) - 1.0

        # Se não há margem (arbitragem exata) ou margem negativa, são fair odds puras
        if margin <= 0:
            return PricingResult(
                margin_percent=round(margin * 100, 4),
                true_probs=implied_probs,
                fair_odds=arr_odds
            )

        # Solver de Newton-Raphson vetorizado para achar a constante 'k'
        # Onde a soma de (implied_prob ^ k) = 1.0
        k = 1.0
        for _ in range(10): # Máximo de iterações (geralmente converge em 3-4)
            probs_k = np.power(implied_probs, k)
            sum_probs_k = np.sum(probs_k)
            
            # Se atingir a precisão máxima (1e-7), para o loop
            if abs(sum_probs_k - 1.0) < 1e-7:
                break
                
            # Derivada para o passo de Newton
            derivative = np.sum(probs_k * np.log(implied_probs))
            k -= (sum_probs_k - 1.0) / derivative

        # Calcula as probabilidades reais finais baseadas no 'k' encontrado
        true_probs = np.power(implied_probs, k)
        fair_odds = 1.0 / true_probs

        return PricingResult(
            margin_percent=(margin * 100),
            true_probs=true_probs,
            fair_odds=fair_odds
        )

    @staticmethod
    def evaluate_opportunity(true_prob: float, soft_odd: float, hft_fraction: float = 0.25) -> Opportunity:
        """
        Calcula o Expected Value (EV) puro e a alocação de risco simultaneamente,
        usando matrizes e tipos float puros para evitar 'Precision Loss'.
        """
        # HFT EV = (Probabilidade Real * Odd Oferecida) - 1
        ev_decimal = (true_prob * soft_odd) - 1.0
        
        # Filtro de lixo: EV menor ou igual a zero é ignorado.
        if ev_decimal <= 0:
            return Opportunity(expected_value=0.0, kelly_stake_pct=0.0, is_value=False)

        # HFT Kelly Criterion = (b*p - q) / b
        b = soft_odd - 1.0
        q = 1.0 - true_prob
        full_kelly = (b * true_prob - q) / b
        
        # Proteção de Ruína (Fracionamento)
        suggested_stake_pct = full_kelly * hft_fraction * 100.0

        return Opportunity(
            expected_value=(ev_decimal * 100.0),
            kelly_stake_pct=suggested_stake_pct,
            is_value=True
        )

# Instância Singleton global e imutável para alta performance
pricer = QuantPricingEngine()