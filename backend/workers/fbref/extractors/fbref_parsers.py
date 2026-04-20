# betgenius-backend/workers/fbref/extractors/fbref_parsers.py
import pandas as pd
from bs4 import BeautifulSoup
import re
import logging
from io import StringIO

logger = logging.getLogger(__name__)

class FBrefParser:
    """
    Motor de Extração S-Tier (Blindado).
    Captura colunas de forma irrestrita, achata cabeçalhos complexos
    e realiza a limpeza de dados com tratamento rigoroso de anomalias.
    """
    
    @staticmethod
    def extract_dataframes(html_content: str) -> dict:
        """Lê a página inteira, quebra as defesas do FBref e devolve dicionários limpos."""
        
        # Guarda de Segurança S-Tier: Evita o erro de variável indefinida se o HTML falhar
        if not html_content or not isinstance(html_content, str):
            logger.warning("⚠️ Conteúdo HTML vazio ou inválido recebido no parser.")
            return {}

        try:
            # A Chave Mestra: Remove comentários HTML para revelar tabelas escondidas
            html_clean = re.sub(r'', '', html_content)
            soup = BeautifulSoup(html_clean, 'lxml')
            
            tables = soup.find_all('table')
            dataframes = {}
            
            for table in tables:
                table_id = table.get('id')
                if not table_id: continue
                
                try:
                    table_io = StringIO(str(table))
                    df = pd.read_html(table_io)[0]
                    
                    # Achatamento: Pega estritamente o último nível do header
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = [str(col[-1]).strip() for col in df.columns]
                    else:
                        df.columns = [str(col).strip() for col in df.columns]
                    
                    # Expurgo: Remove linhas de "Squad Total" ou "Opponent Average"
                    df = df[~df.iloc[:, 0].astype(str).str.contains("Total|Média|Average|Opponent", case=False, na=False)]
                    
                    dataframes[table_id] = df
                except Exception:
                    continue
                    
            return dataframes
            
        except Exception as e:
            logger.error(f"🚨 Falha crítica dentro do extract_dataframes: {e}")
            return {}

    @staticmethod
    def extract_safe_value(df: pd.DataFrame, row_index: int, possible_cols: list, is_float: bool = True):
        """Caçador de Valores: Encontra o dado sem quebrar se a coluna mudar de nome."""
        df_cols_lower = [str(c).lower().strip() for c in df.columns]
        
        for col_target in possible_cols:
            target = str(col_target).lower().strip()
            match_idx = -1
            
            # PRIORIDADE 1: Busca Exata
            if target in df_cols_lower:
                match_idx = df_cols_lower.index(target)
            else:
                # PRIORIDADE 2: Busca por Substring
                for i, c in enumerate(df_cols_lower):
                    if len(target) > 1 and target in c:
                        match_idx = i
                        break
                        
            if match_idx != -1:
                actual_col_name = df.columns[match_idx]
                val = df.at[row_index, actual_col_name]
                
                # Defesa contra colunas duplicadas do FBref
                if isinstance(val, pd.Series):
                    val = val.iloc[0]
                    
                try:
                    if pd.isna(val): 
                        return 0.0 if is_float else 0
                    
                    # Motor Financeiro: Converte "£ 1,500,000" para 1500000.0
                    if isinstance(val, str) and any(s in val for s in ['£', '$', '€', ',']):
                        clean_val = re.sub(r'[^\d.]', '', val)
                        return float(clean_val) if clean_val else 0.0
                        
                    return float(val) if is_float else int(val)
                except Exception:
                    continue
                    
        return 0.0 if is_float else 0