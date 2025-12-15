#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ========== IMPORTS E CONSTANTES ==========

import os, sys, json, re, pandas as pd
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    import pyreadstat
except ImportError:
    print("❌ ERRO: pyreadstat não instalado!")
    print("📦 Instale com: pip install pyreadstat --break-system-packages")
    sys.exit(1)

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog
    from tkinter import ttk
except ImportError:
    print("❌ ERRO: tkinter não disponível!")
    print("🖥️ tkinter é necessário para a interface gráfica")
    sys.exit(1)

# Constantes
CHART_LABEL_MAX = 15

# ========== FUNÇÕES DE UTILIDADE ==========

def _try_import_ftfy():
    try:
        import ftfy
        return ftfy
    except Exception:
        return None

def fix_string(s: str) -> str:
    if not isinstance(s, str) or not s:
        return s
    ftfy = _try_import_ftfy()
    if ftfy:
        try:
            return ftfy.fix_text(s)
        except Exception:
            pass
    try:
        s2 = s.encode("latin1", "ignore").decode("utf-8", "ignore")
        if any(ch in s2 for ch in "áéíóúãõçÁÉÍÓÚÃÕÇ"):
            return s2
    except Exception:
        pass
    return s

def read_sav_auto(path: str):
    tries = [dict(encoding=None), dict(encoding="cp1252"), dict(encoding="latin1")]
    last_err = None
    for kw in tries:
        try:
            df, meta = pyreadstat.read_sav(path, apply_value_formats=False, user_missing=True, **kw)
            return df, meta
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Falha ao ler o arquivo .sav: {last_err}")

def fix_labels_in_meta(meta):
    try:
        cl = getattr(meta, "column_labels", None)
        if isinstance(cl, dict):
            for k in list(cl.keys()):
                if isinstance(cl[k], str):
                    cl[k] = fix_string(cl[k])
        elif isinstance(cl, list) and hasattr(meta, "column_names"):
            cn = getattr(meta, "column_names", None)
            if isinstance(cn, list) and len(cn) == len(cl):
                for i in range(len(cl)):
                    if isinstance(cl[i], str):
                        cl[i] = fix_string(cl[i])
        vtl = getattr(meta, "variable_to_label", None)
        if isinstance(vtl, dict):
            for k in list(vtl.keys()):
                if isinstance(vtl[k], str):
                    vtl[k] = fix_string(vtl[k])
        vvl = getattr(meta, "variable_value_labels", None)
        if isinstance(vvl, dict):
            for var, d in vvl.items():
                for key in list(d.keys()):
                    if isinstance(d[key], str):
                        d[key] = fix_string(d[key])
        else:
            value_labels = getattr(meta, "value_labels", None)
            if isinstance(value_labels, dict):
                for labelset, d in value_labels.items():
                    for key in list(d.keys()):
                        if isinstance(d[key], str):
                            d[key] = fix_string(d[key])
    except Exception:
        pass

def safe_value_label_lookup(valabs_dict, var_name, value):
    """
    Lookup robusto para value labels que tenta diferentes tipos de chave.
    Resolve problema de 1.0 vs 1, "1" vs 1, etc.
    """
    var_valabs = valabs_dict.get(var_name, {})
    if not var_valabs:
        return value
    
    # Tentar valor original primeiro
    if value in var_valabs:
        result = var_valabs[value]
        return result.strip() if isinstance(result, str) else result
    
    # Se valor é numérico, tentar variações
    if isinstance(value, (int, float)):
        # Tentar como int se é float inteiro
        if isinstance(value, float) and value.is_integer():
            int_val = int(value)
            if int_val in var_valabs:
                result = var_valabs[int_val]
                return result.strip() if isinstance(result, str) else result
        
        # Tentar como float se é int
        if isinstance(value, int):
            float_val = float(value)
            if float_val in var_valabs:
                result = var_valabs[float_val]
                return result.strip() if isinstance(result, str) else result
        
        # Tentar como string
        str_val = str(value)
        if str_val in var_valabs:
            result = var_valabs[str_val]
            return result.strip() if isinstance(result, str) else result
        
        # Tentar string sem .0
        if str_val.endswith('.0'):
            clean_str = str_val[:-2]
            if clean_str in var_valabs:
                result = var_valabs[clean_str]
                return result.strip() if isinstance(result, str) else result
    
    # Se valor é string, tentar como número
    if isinstance(value, str):
        try:
            # Tentar int
            int_val = int(float(value))
            if int_val in var_valabs:
                result = var_valabs[int_val]
                return result.strip() if isinstance(result, str) else result
            
            # Tentar float  
            float_val = float(value)
            if float_val in var_valabs:
                result = var_valabs[float_val]
                return result.strip() if isinstance(result, str) else result
        except (ValueError, TypeError):
            pass
    
    # Se nada funcionou, retornar valor original
    return value

def get_value_labels_map(meta) -> Dict[str, Dict[Any, str]]:
    vvl = getattr(meta, "variable_value_labels", None)
    if isinstance(vvl, dict) and vvl:
        return {var: {k: str(v) for k, v in d.items()} for var, d in vvl.items()}
    mapping: Dict[str, Dict[Any, str]] = {}
    value_labels = getattr(meta, "value_labels", None)
    var_to_labelset = getattr(meta, "variable_to_labelset", None)
    if isinstance(value_labels, dict) and isinstance(var_to_labelset, dict):
        for var, labelset in var_to_labelset.items():
            vmap = value_labels.get(labelset, {})
            if vmap:
                mapping[var] = {k: str(v) for k, v in vmap.items()}
    return mapping

def get_var_label(meta, col: str) -> str:
    """Retorna o texto da pergunta / label de variável já limpo."""
    label = ""

    cl = getattr(meta, "column_labels", None)
    if isinstance(cl, dict) and col in cl:
        label = cl.get(col, "") or ""
    elif isinstance(cl, list) and hasattr(meta, "column_names"):
        cn = getattr(meta, "column_names", None)
        if isinstance(cn, list) and col in cn:
            i = cn.index(col)
            if 0 <= i < len(cl):
                label = cl[i] or ""

    if not label:
        vl = getattr(meta, "variable_labels", None)
        if isinstance(vl, dict):
            label = vl.get(col, "") or ""

    if not label:
        vtl = getattr(meta, "variable_to_label", None)
        if isinstance(vtl, dict):
            label = vtl.get(col, "") or ""

    if not isinstance(label, str):
        label = str(label) if label is not None else ""

    # remove blocos entre colchetes no início do texto
    label = label.strip()
    return label


def _normalize_display_value(value_str):
    if isinstance(value_str, str) and value_str.endswith('.0'):
        try:
            float_val = float(value_str)
            if float_val.is_integer():
                return str(int(float_val))
        except (ValueError, TypeError):
            pass
    return value_str

def format_text_response(text: str):
    """
    Normaliza respostas de texto abertas.
    - Remove espaços extras
    - Ignora códigos de não resposta como "99"
    - Retorna None para vazios ou missing
    """
    if text is None:
        return None
    if not isinstance(text, str):
        text = str(text)
    text = text.strip()
    if not text or text == "99":
        return None
    return text

# === PROCESSAMENTO DE PALAVRAS‑CHAVE PARA VARIÁVEIS DE TEXTO ===

# Conjunto básico de stopwords em português para filtrar termos pouco informativos.  Esta lista
# pode ser expandida conforme necessário.  Ela evita que artigos, preposições e pronomes se
# tornem palavras‑chave.
STOPWORDS_PT = {
    'a','o','e','é','de','do','da','para','por','em','que','na','no','nao','não','os','as','das','dos',
    'um','uma','uns','umas','com','sem','mais','menos','sobre','ou','ao','até','como','pela','pelas',
    'pelo','pelos','se','sua','suas','seu','seus','são','foi','ser','há','tem','têm','será','serão','faz',
    'fazer','vocês','nos','nós','eu','tu','você','ele','ela','eles','elas','também','onde','quando','nosso',
    'nossa','nossos','nossas','este','esta','esse','essa','aquele','aquela','isto','isso','aquilo','lhe','lhe',
}

def _normalize_token_pt(token: str) -> str:
    """
    Normaliza um token para a extração de palavras‑chave:
    - Converte para minúsculas
    - Remove acentos (unicode)
    - Remove caracteres não alfabéticos
    """
    # Converter para minúsculo
    token = token.lower()
    # Remover acentuação
    token = ''.join(c for c in unicodedata.normalize('NFKD', token) if not unicodedata.combining(c))
    # Manter apenas letras
    token = re.sub(r'[^a-z]+', '', token)
    return token

def extract_keywords_from_texts(texts, max_keywords: int = 20, min_freq: int = 2):
    """
    Recebe uma lista de respostas em texto e retorna as palavras‑chave mais frequentes.

    Esta função normaliza palavras (minúsculas, sem acentos e caracteres não alfabéticos),
    remove stopwords e agrupa diferentes flexões em uma mesma raiz simples. A raiz é
    definida como os primeiros 6 caracteres da palavra normalizada, o que ajuda a
    unificar termos como "informacao", "informacoes" e "informativo" na mesma categoria.

    Parâmetros:
        texts (List[str]): lista de respostas em texto.
        max_keywords (int): número máximo de palavras‑chave a retornar.
        min_freq (int): frequência mínima para considerar uma palavra.

    Retorna:
        List[Dict[str, Any]]: lista de dicionários com chaves 'word' (representante da raiz)
        e 'count' (frequência dessa raiz).
    """
    from collections import Counter
    root_counter = Counter()
    representative = {}
    for text in texts:
        if not isinstance(text, str):
            continue
        # Substituir pontuação por espaços para separar tokens
        clean = re.sub(r'[^A-Za-zÀ-ÿ\s]', ' ', text)
        seen_roots_in_response = set()
        for token in clean.split():
            norm = _normalize_token_pt(token)
            if not norm:
                continue
            # Ignorar tokens muito curtos e stopwords
            if len(norm) <= 2 or norm in STOPWORDS_PT:
                continue
            # Definir raiz como os primeiros 6 caracteres (ou a palavra inteira se menor)
            root = norm[:6]
            # Adicionar ao conjunto para contar apenas uma vez por resposta
            seen_roots_in_response.add(root)
            # Guardar um representante legível para essa raiz (primeiro encontrado ou
            # lexicograficamente menor).  O representante ajuda a exibir a palavra
            # numa forma compreensível para o usuário.
            if root not in representative or representative[root] > norm:
                representative[root] = norm
        # Após processar todos os tokens da resposta, incremente contadores uma vez por root
        for root in seen_roots_in_response:
            root_counter[root] += 1
    # Filtrar raízes por frequência mínima
    frequent_roots = [(root, cnt) for root, cnt in root_counter.items() if cnt >= min_freq]
    # Ordenar por frequência descrescente e, em caso de empate, pela palavra representante
    frequent_roots.sort(key=lambda x: (-x[1], representative[x[0]]))
    # Limitar ao número máximo de palavras‑chave
    keywords = []
    for root, cnt in frequent_roots[:max_keywords]:
        rep_word = representative[root]
        keywords.append({'word': rep_word, 'count': cnt, 'root': root})
    return keywords

# ========== FUNÇÕES AUXILIARES PARA EVITAR ERRO hashable ==========

def safe_unique_values(values_list):
    """Função segura para obter valores únicos, evitando erro 'unhashable type: dict'"""
    if not values_list:
        return []
    
    unique_values = []
    seen_values = []
    
    for value in values_list:
        # Converter para string para comparação segura
        str_value = str(value)
        if str_value not in seen_values:
            seen_values.append(str_value)
            unique_values.append(value)
    
    return unique_values

def safe_sorted_unique(values_list):
    """Função segura para ordenar valores únicos"""
    unique_vals = safe_unique_values(values_list)
    try:
        return sorted(unique_vals)
    except TypeError:
        # Se não conseguir ordenar (tipos mistos), retornar como lista
        return unique_vals

def detect_mr_type(group_cols, valabs, meta, df):
    """
    Detecta o tipo de múltipla resposta para um grupo de colunas.

    Retorna:
        - "binary"      → MR1 (checkbox: 0/1, Selected/Not Selected, etc.)
        - "categorical" → MR2 (categorias em value labels)
    """
    import re
    import pandas as pd

    if not group_cols:
        return "categorical"

    #MR1 forte: colchetes no label da variável
    if meta is not None:
        for col in group_cols:
            raw_label = get_var_label(meta, col)
            if isinstance(raw_label, str) and "[" in raw_label and "]" in raw_label:
                return "binary"

    #MR1 por value labels binários
    binary_indicators = {
        "selected", "not selected",
        "selecionado", "não selecionado",
        "nao selecionado", "nao seleccionado",
        "sim", "não", "nao",
        "yes", "no",
        "0", "1"
    }

    any_valmap = False
    all_valmaps_binary = True

    for col in group_cols:
        vmap = valabs.get(col, {}) or {}
        if vmap:
            any_valmap = True
            labels = {str(v).strip().lower() for v in vmap.values()}
            if not labels or not labels.issubset(binary_indicators):
                all_valmaps_binary = False
                break

    if any_valmap and all_valmaps_binary:
        return "binary"

    #MR1 por dados (sem value labels), grupo grande com 0/1
    if df is not None and len(group_cols) >= 3:
        all_01 = True
        for col in group_cols:
            if col not in df.columns:
                all_01 = False
                break
            series = df[col]
            nonnull = series.dropna()
            if nonnull.empty:
                all_01 = False
                break
            uniq = {str(v).strip() for v in nonnull}
            if not uniq.issubset({"0", "1", "0.0", "1.0"}):
                all_01 = False
                break

        if all_01:
            return "binary"

    #Caso não seja MR1 → MR2 categórica
    return "categorical"

def get_mr1_label(meta, col):
    """
    Retorna o texto da categoria para MR binária.
    Sempre prioriza o conteúdo entre colchetes.
    Nunca devolve o label completo da pergunta.
    """
    raw = get_var_label(meta, col)
    if not isinstance(raw, str):
        return str(raw)

    raw = raw.strip()

    #    Se tiver colchetes, é a categoria — ponto final.
    match = re.search(r'\[(.*?)\]', raw)
    if match:
        return match.group(1).strip()

    #    Se não houver colchetes, tenta usar só o texto antes da pergunta,
    #    dividindo no primeiro "P05." ou "P05 " (dependendo do padrão)
    #    Isso é fallback, mas 99% dos casos não precisa.
    m2 = re.split(r'P0?\d+\.', raw, maxsplit=1)
    if m2 and m2[0].strip():
        return m2[0].strip()

    # 3. Último fallback: o raw inteiro
    return raw

def get_mr2_label(valabs, col, val):
    """
    Obtém o texto da categoria diretamente do value label
    (MR categórica real).
    """
    vmap = valabs.get(col, {})
    label = vmap.get(val)

    if label:
        return str(label).strip()

    return None  # deixa o fallback lidar com isso

def mr_is_selected(val, valmap):
    """
    Retorna True se a opção de múltipla resposta foi marcada, 
    independente se o SPSS usou:
    - 1 / 0
    - "1" / "0"
    - Yes / No
    - Selected / Not Selected
    - Rotulagem invertida
    """
    # Nada selecionado ou valor nulo
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False

    sval = str(val).strip().lower()

    # Caso 1 – valor real é "1", "1.0", etc.
    if sval in {"1", "1.0", "01"}:
        return True

    # Caso 2 – SPSS exportou "Yes" diretamente como valor
    if sval in {"yes", "sim", "selected"}:
        return True

# ========== TRADUÇÃO E NORMALIZAÇÃO DE LABELS ==========

def normalize_and_translate_labels(labels_dict: Dict) -> Dict:
    """
    Normaliza e traduz labels comuns para português.
    
    Trata casos como:
    - Yes/No → Sim/Não
    - NSA → Não sabe avaliar
    - Selected/Not Selected → Selecionado/Não selecionado
    """
    
    if not labels_dict:
        return labels_dict
    
    # Dicionário de traduções
    translations = {
        # Inglês → Português
        'yes': 'Sim',
        'no': 'Não', 
        'selected': 'Selecionado',
        'not selected': 'Não selecionado',
        'unselected': 'Não selecionado',
        
        # Códigos comuns
        'nsa': 'Não sabe avaliar',
        'n/a': 'Não se aplica',
        'na': 'Não se aplica',
        'nr': 'Não respondeu',
        'dk': 'Não sabe',
        'ref': 'Recusou',
        
        # Escalas comuns em inglês
        'strongly disagree': 'Discordo totalmente',
        'disagree': 'Discordo', 
        'neutral': 'Neutro',
        'agree': 'Concordo',
        'strongly agree': 'Concordo totalmente',
        
        'very dissatisfied': 'Muito insatisfeito',
        'dissatisfied': 'Insatisfeito',
        'neither satisfied nor dissatisfied': 'Nem satisfeito nem insatisfeito',
        'satisfied': 'Satisfeito', 
        'very satisfied': 'Muito satisfeito'
    }
    
    normalized_labels = {}
    
    for key, label in labels_dict.items():
        if not isinstance(label, str):
            normalized_labels[key] = label
            continue
            
        # Normalizar texto (minúsculo, sem espaços extras)
        normalized_text = label.strip().lower()
        
        # Verificar se existe tradução
        if normalized_text in translations:
            normalized_labels[key] = translations[normalized_text]
            print(f"   📝 Traduzindo: '{label}' → '{translations[normalized_text]}'")
        else:
            # Manter original se não houver tradução
            normalized_labels[key] = label
    
    return normalized_labels

def detect_binary_indicators_improved(labels_dict: Dict) -> bool:
    """
    Versão melhorada para detectar indicadores binários.
    
    Inclui:
    - Yes/No, Sim/Não
    - Selected/Not Selected  
    - 0/1
    - True/False
    - Códigos NSA, N/A (tratados como missing)
    """
    
    if not labels_dict:
        return False
    
    # Normalizar labels para comparação
    normalized_labels = {str(v).strip().lower() for v in labels_dict.values() if v is not None}
    
    # Remover códigos de missing da análise
    missing_codes = {'nsa', 'n/a', 'na', 'nr', 'dk', 'ref', '99', '999', '9999', 'missing'}
    cleaned_labels = normalized_labels - missing_codes
    
    # Padrões binários expandidos
    binary_patterns = [
        # Português
        {'sim', 'não'}, {'sim', 'nao'}, 
        {'selecionado', 'não selecionado'}, {'selecionado', 'nao selecionado'},
        
        # Inglês
        {'yes', 'no'},
        {'selected', 'not selected'}, {'selected', 'unselected'},
        {'true', 'false'},
        
        # Numérico
        {'0', '1'}, {'0.0', '1.0'},
        
        # Outros padrões comuns
        {'checked', 'unchecked'},
        {'on', 'off'},
        {'ativo', 'inativo'},
        {'active', 'inactive'}
    ]
    
    # Verificar se os labels limpos correspondem a algum padrão binário
    for pattern in binary_patterns:
        if cleaned_labels == pattern or cleaned_labels.issubset(pattern):
            print(f"   ✅ Padrão binário detectado: {cleaned_labels}")
            return True
    
    return False

# ========== NOVA DETECÇÃO DE GRUPOS MR (CORRIGIDA) ==========

def detect_mr_groups_improved(selected_vars: List[str], meta, df) -> Tuple[Dict[str, Dict], List[str]]:
    """
    VERSÃO CORRIGIDA: Detecta grupos de múltipla resposta de forma mais robusta.
    
    Retorna:
        - mr_groups: dicionário com grupos MR detectados
        - standalone_vars: lista de variáveis independentes
    """
    
    print("\n🔍 === DETECTANDO GRUPOS MR (VERSÃO CORRIGIDA) ===")
    
    # Mapear todas as variáveis com padrão BASE_N
    var_patterns = {}  # base -> [lista de variáveis]
    standalone_vars = []  # variáveis que não seguem padrão MR
    
    for var in selected_vars:
        if var not in df.columns:
            print(f"⚠️ Variável {var} não encontrada no dataset")
            continue
            
        # Testar padrões MR comuns
        patterns = [
            r"^([A-Za-z]+\d+)_(\d+)([A-Za-z]*)$",  # P01_1, AP05_2, etc.
            r"^([A-Za-z]+)(\d+)_(\d+)$",            # P1_1, A5_2, etc.  
            r"^([A-Za-z]+\d+[A-Za-z]*)_(\d+)$"      # P01A_1, Q5B_2, etc.
        ]
        
        matched = False
        for pattern in patterns:
            match = re.match(pattern, var)
            if match:
                if len(match.groups()) >= 2:
                    base = match.group(1)
                    if base not in var_patterns:
                        var_patterns[base] = []
                    var_patterns[base].append(var)
                    print(f"✅ {var} → Grupo {base}")
                    matched = True
                    break
        
        if not matched:
            standalone_vars.append(var)
            print(f"📋 {var} → Variável independente")
    
    # Identificar quais bases têm múltiplas variáveis (são realmente MR)
    mr_groups = {}
    for base, vars_list in var_patterns.items():
        if len(vars_list) >= 2:
            print(f"\n🔗 Analisando possível grupo MR para base {base}: {vars_list}")
            
            # Determinar tipo MR (binary/categorical/rating_scale)
            mr_subtype = detect_mr_type_improved(vars_list, meta, df)
            print(f"   Tipo detectado: {mr_subtype}")
            
            # Se for rating_scale, NÃO agrupar como MR
            if mr_subtype == "rating_scale":
                print(f"   🎯 É bateria de escalas, tratando como variáveis individuais")
                standalone_vars.extend(vars_list)
                continue
            
            # Se chegou aqui, é MR verdadeira
            print(f"   ✅ Confirmado como múltipla resposta")
            
            # Obter título do grupo
            title = get_mr_group_title(base, vars_list, meta)
            print(f"   Título: {title}")
            
            # Verificar se há variável "_other"
            other_var = f"{base}_other"
            group_other = None   # <-- CRUCIAL: garantir que SEMPRE exista

            if other_var in df.columns:
                print(f"   Encontrada variável other: {other_var}")
                group_other = other_var
                if other_var not in standalone_vars:
                    standalone_vars.append(other_var)
        
            group_name = f"mr_{base.lower()}"
            mr_groups[group_name] = {
                "title": title,
                "members": vars_list,  # PRESERVAR ordem original (removido sorted())
                "mr_subtype": mr_subtype,
                "other_var": group_other,
                "base": base
            }
        else:
            # Se tem só 1 variável, tratar como standalone
            standalone_vars.extend(vars_list)
            print(f"📋 {base} tem só 1 variável, tratando como independente")
    
    print(f"\n📊 RESULTADO:")
    print(f"   Grupos MR criados: {len(mr_groups)}")
    print(f"   Variáveis independentes: {len(standalone_vars)}")
    
    # Identificar escalas que foram separadas
    scale_groups = 0
    for base, vars_list in var_patterns.items():
        if len(vars_list) >= 2:
            subtype = detect_mr_type_improved(vars_list, meta, df)
            if subtype == "rating_scale":
                scale_groups += 1
    
    if scale_groups > 0:
        print(f"   🎯 Baterias de escalas detectadas: {scale_groups} (tratadas como variáveis individuais)")
    
    return mr_groups, standalone_vars

def detect_mr_type_improved(group_vars: List[str], meta, df) -> str:
    """
    VERSÃO MELHORADA: Detecta se é MR binary (0/1), categorical ou rating scale.
    
    NOVIDADES:
    - Detecta Yes/No, Sim/Não como binário
    - Traduz automaticamente quando possível
    - Trata códigos NSA, N/A adequadamente
    """
    
    # 1. Verificar value labels para detectar escalas primeiro
    valabs = get_value_labels_map(meta)
    
    if group_vars and group_vars[0] in valabs:
        first_var_labels = valabs[group_vars[0]]
        
        # Aplicar tradução/normalização
        normalized_labels = normalize_and_translate_labels(first_var_labels)
        
        # Verificar se é escala de avaliação (padrão comum)
        scale_patterns = {
            # Escalas de satisfação
            r'(muito\s+)?insatisfeit|satisfeit|indiferente': 'satisfaction_scale',
            # Escalas de concordância  
            r'discord|concord|neutro': 'agreement_scale',
            # Escalas numéricas (1-5, 1-10, etc.)
            r'^[1-9]\d*$': 'numeric_scale',
            # Escalas de frequência
            r'sempre|frequente|raramente|nunca': 'frequency_scale',
            # Escalas de qualidade
            r'(muito\s+)?bom|ruim|regular|ótimo|péssimo': 'quality_scale'
        }
        
        label_text = ' '.join(normalized_labels.values()).lower()
        
        for pattern, scale_type in scale_patterns.items():
            if re.search(pattern, label_text):
                print(f"   🎯 Detectado como ESCALA ({scale_type}), não MR")
                return "rating_scale"
        
        # Verificar se os values formam uma sequência numérica (escala)
        try:
            numeric_values = []
            for val in normalized_labels.keys():
                try:
                    num = float(val)
                    if num not in [99, 999, 0]:  # Excluir códigos de missing
                        numeric_values.append(int(num))
                except:
                    pass
            
            if len(numeric_values) >= 3:  # Tem pelo menos 3 valores na escala
                numeric_values.sort()
                # Verificar se é sequencial (1,2,3,4,5 ou similar)
                if numeric_values == list(range(min(numeric_values), max(numeric_values) + 1)):
                    print(f"   🎯 Detectado como ESCALA NUMÉRICA ({min(numeric_values)}-{max(numeric_values)}), não MR")
                    return "rating_scale"
        except:
            pass
    
    # 2. Verificar se é MR binária usando detecção melhorada
    scale_keywords = [
        "satisfeito", "insatisfeito", "indiferente",
        "concord", "discord", "neutro",
        "ótim", "bom", "regular", "ruim", "péssim",
        "sempre", "nunca", "às vezes"
    ]

    for var in group_vars:
        vmap = valabs.get(var, {})
        labels = " ".join(str(v).lower() for v in vmap.values())

        # ➤ REGRA DEFINITIVA: Se contém palavras de escala → retornar "rating_scale"
        if any(kw in labels for kw in scale_keywords):
            print("   🎯 Escala de avaliação detectada — NÃO é MR")
            return "rating_scale"

    # 3. Só agora testar MR binária
    for var in group_vars:
        vmap = valabs.get(var, {})
        if vmap and detect_binary_indicators_improved(vmap):
            print("   ✅ Detectado como MR BINÁRIA")
            return "binary"    

    # 3. Fallback: verificar dados reais (se tem 3+ variáveis com só 0/1)
    if len(group_vars) >= 3:
        all_01 = True
        for var in group_vars:
            if var in df.columns:
                series = df[var].dropna()
                if not series.empty:
                    unique_vals = {str(v).strip() for v in series.unique()}
                    # Excluir códigos de missing da análise
                    unique_vals = unique_vals - {'99', '999', '9999', 'nan', 'None'}
                    if not unique_vals.issubset({"0", "1", "0.0", "1.0"}):
                        all_01 = False
                        break
        
        if all_01:
            print(f"   ✅ Detectado como MR BINÁRIA (pelos dados)")
            return "binary"
    
    # 4. Verificar colchetes nos labels (padrão LimeSurvey)
    for var in group_vars:
        label = get_var_label(meta, var)
        if "[" in label and "]" in label:
            print(f"   ✅ Detectado como MR BINÁRIA (padrão colchetes)")
            return "binary"
    
    print(f"   📊 Detectado como MR CATEGÓRICA")
    return "categorical"

def get_mr_group_title(base: str, vars_list: List[str], meta) -> str:
    """
    Obtém título do grupo MR, tentando várias estratégias.
    """
    # 1. Tentar usar label da variável base (se existir)
    base_label = get_var_label(meta, base)
    if base_label and len(base_label.strip()) > 3:
        return base_label.strip()
    
    # 2. Tentar usar primeira variável, removendo colchetes
    if vars_list:
        first_label = get_var_label(meta, vars_list[0])
        if first_label:
            # Remove texto entre colchetes no início
            clean_label = re.sub(r'^\s*\[.*?\]\s*', '', first_label).strip()
            # Remove numeração no final (ex: "Pergunta 1", "Question 1")
            clean_label = re.sub(r'\s+\d+\s*$', '', clean_label).strip()
            if clean_label:
                return clean_label
    
    # 3. Fallback
    return f"Grupo {base}"

# ========== NOVA CAMADA DE IDENTIFICAÇÃO DE TIPOS ==========

DATE_PREFIXES = (
    "DATE", "ADATE", "SDATE", "EDATE",
    "JDATE", "DATETIME", "QYR", "WKYR", "MOYR"
)

TIME_PREFIXES = (
    "TIME", "DTIME", "MTIME"
)

def detect_physical_type(meta, df, var_name: str) -> str:
    """
    Detecta o tipo REAL da variável (string, numeric, date),
    usando:
    1) display_format do SPSS
    2) original_variable_types
    3) inspeção do dataframe (conteúdo REAL)
    """
    import re

    # ---------- 1) Formato SPSS ----------
    var_formats = getattr(meta, "variable_display_formats", {}) or {}
    fmt = str(var_formats.get(var_name, "")).upper()

    # STRING por formato Axx
    if fmt.startswith("A"):
        return "string"

    # ---------- 2) Se SPSS diz STRING ----------
    var_types = getattr(meta, "original_variable_types", {}) or {}
    original_type = var_types.get(var_name)
    if original_type and "STRING" in str(original_type).upper():
        return "string"

    # ---------- 3) Inspeção do dataframe ----------
    if var_name in df.columns:
        series = df[var_name]

        # dtype object geralmente indica texto
        if series.dtype == object:
            return "string"

        # Verificar se 80% dos valores NÃO são numéricos → string
        sample = series.dropna().astype(str).head(20)
        nonnum = 0
        for v in sample:
            try:
                float(v)
            except:
                nonnum += 1
        if len(sample) > 0 and nonnum / len(sample) > 0.5:
            return "string"

        # Verificar presença de palavras → string
        for v in sample:
            if any(c.isalpha() for c in v):
                return "string"

    # ---------- 4) Detectar datas ----------
    DATE_PREFIXES = (
        "DATE","ADATE","SDATE","EDATE","JDATE",
        "DATETIME","QYR","WKYR","MOYR"
    )
    if any(fmt.startswith(pfx) for pfx in DATE_PREFIXES):
        return "date"

    # ---------- 5) Caso nada acima → é numérica ----------
    return "numeric"

def detect_measure_type(meta, var_name: str, physical_type: str):
    """
    Retorna nominal / ordinal / scale
    apenas para variáveis numéricas.
    """
    if physical_type != "numeric":
        return None

    measures = getattr(meta, "variable_measure", {}) or {}
    measure = measures.get(var_name)

    if isinstance(measure, str):
        m = measure.lower().strip()
        if m in ("nominal", "ordinal", "scale"):
            return m

    return None

def detect_variables_universal(selected_vars, meta, valabs, df):
    """
    VERSÃO CORRIGIDA que preserva a ordem original do SPSS.
    
    Em vez de processar primeiro todos os grupos MR e depois todas as standalone,
    processa na ordem original do selected_vars, decidindo para cada posição
    se é um grupo MR ou uma variável standalone.
    """
    print(f"\n🔍 === DETECÇÃO DE VARIÁVEIS - ORDEM ORIGINAL PRESERVADA ===")
    print(f"📋 Variáveis selecionadas: {selected_vars[:5]}{'...' if len(selected_vars) > 5 else ''}")
    
    vars_meta = []
    processed_vars = set()  # Rastrear variáveis já processadas
    
    # PASSO 1: Detectar grupos MR (usando apenas variáveis selecionadas para análise)
    mr_groups, standalone_vars = detect_mr_groups_improved(selected_vars, meta, df)
    
    print(f"\n📊 Grupos MR detectados: {list(mr_groups.keys())}")
    print(f"📋 Variáveis standalone: {len(standalone_vars)}")
    
    # PASSO 2: Processar na ORDEM ORIGINAL intercalando MR e standalone
    print(f"\n🔧 Processando na ordem original do SPSS:")
    
    for i, var in enumerate(selected_vars):
        if var in processed_vars:
            continue  # Já foi processada como parte de um grupo MR
        
        # Verificar se esta variável faz parte de um grupo MR
        mr_group_for_this_var = None
        for group_name, group_info in mr_groups.items():
            if var in group_info["members"]:
                mr_group_for_this_var = (group_name, group_info)
                break
        
        if mr_group_for_this_var:
            # Esta variável é a primeira do seu grupo MR - adicionar o grupo aqui
            group_name, group_info = mr_group_for_this_var
            
            print(f"   {i+1:2d}. {group_name} (grupo MR - primeiro membro: {var})")
            
            vars_meta.append({
                "name": group_name,
                "title": group_info["title"],
                "type": "mr",
                "spss_type": "Resposta Múltipla",
                "sheet_code": group_name,
                "var_type": "multiple_response", 
                "measure": None,
                "mr_subtype": group_info["mr_subtype"],
                "stats": None
            })
            
            # Marcar todas as variáveis do grupo como processadas
            for member_var in group_info["members"]:
                if member_var == group_info.get("other_var"):
                    continue
                processed_vars.add(member_var)
            
            print(f"      ✅ Grupo MR adicionado ({group_info['mr_subtype']}) - {len(group_info['members'])} variáveis")
            
        elif var in standalone_vars:
            # Esta é uma variável standalone - processar normalmente
            print(f"   {i+1:2d}. {var} (standalone)")
            
            if var not in df.columns:
                print(f"      ⚠️ Pulando {var} (não existe no dataset)")
                processed_vars.add(var)
                continue
            
            # Detectar tipo físico
            physical = detect_physical_type(meta, df, var)
            
            if physical == "string":
                vars_meta.append({
                    "name": var,
                    "title": get_var_label(meta, var),
                    "type": "string",
                    "spss_type": "Resposta Aberta",
                    "sheet_code": var,
                    "var_type": "string",
                    "measure": None,
                    "mr_subtype": None,
                    "stats": None
                })
                print(f"      ✅ Adicionado como string")
                
            elif physical == "date":
                vars_meta.append({
                    "name": var,
                    "title": get_var_label(meta, var),
                    "type": "single",
                    "spss_type": "Data",
                    "sheet_code": var,
                    "var_type": "date",
                    "measure": None,
                    "mr_subtype": None,
                    "stats": None
                })
                print(f"      ✅ Adicionado como data")
                
            else:
                # Numérico - detectar medida a partir do SPSS (sem inferência por value labels)
                measure = detect_measure_type(meta, var, physical)

                if measure == "scale":
                    # Numérica contínua (Escala) - stats serão calculadas depois com ponderação
                    vars_meta.append({
                        "name": var,
                        "title": get_var_label(meta, var),
                        "type": "single",
                        "spss_type": "Numérica (Escala)",
                        "sheet_code": var,
                        "var_type": "numeric",
                        "measure": "scale",
                        "mr_subtype": None,
                        "stats": None  # Será calculado depois com ponderação
                    })
                    print(f"      ✅ Adicionado como Numérica (Escala) seguindo SPSS")
                else:
                    # Categórica (Nominal ou Ordinal) seguindo APENAS o Measure do SPSS
                    human = "Categórica (Ordinal)" if measure == "ordinal" else "Categórica (Nominal)"
                    vars_meta.append({
                        "name": var,
                        "title": get_var_label(meta, var),
                        "type": "single",
                        "spss_type": human,
                        "sheet_code": var,
                        "var_type": "categorical",
                        "measure": measure or "nominal",
                        "mr_subtype": None,
                        "stats": None
                    })
                    print(f"      ✅ Adicionado como {human} (Measure SPSS)")

                processed_vars.add(var)
        
        else:
            # Variável não foi classificada (não deveria acontecer normalmente)
            print(f"   {i+1:2d}. {var} (⚠️ não classificada - pulando)")
            processed_vars.add(var)
    
    # PASSO 3: Verificar se todas as variáveis foram processadas
    print(f"\n🔍 Verificação final:")
    missing_vars = set(selected_vars) - processed_vars
    if missing_vars:
        print(f"⚠️ Variáveis não processadas: {missing_vars}")
    else:
        print(f"✅ Todas as {len(selected_vars)} variáveis foram processadas")
    
    print(f"\n📈 RESUMO FINAL:")
    print(f"   Total de variáveis no dashboard: {len(vars_meta)}")
    print(f"   Grupos MR detectados: {len(mr_groups)}")
    print(f"   Variáveis standalone: {len(standalone_vars)}")
    
    # Debug: mostrar ordem final CORRIGIDA
    print(f"\n✅ ORDEM FINAL PRESERVADA (CORRIGIDA):")
    for i, vm in enumerate(vars_meta):
        print(f"   {i+1:2d}. {vm['name']} ({vm.get('var_type', vm['type'])})")
    
    return vars_meta, mr_groups


def build_records_and_meta(df, meta, selected_vars: List[str], filter_vars: List[str], 
                          file_source: str, client_name: str, weight_var: str = None):
    """
    Constrói:
      - created_at: timestamp
      - vars_meta: metadados das variáveis (incluindo grupos MR e stats)
      - filters_meta: metadados dos filtros
      - records: lista de dicionários prontos para o dashboard
      
    NOVO: Inclui automaticamente campos de data (submitdate, etc.) para cálculo de período de coleta
    """
    created_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # === DETECTAR E INCLUIR CAMPOS DE DATA AUTOMATICAMENTE ===
    date_fields = []
    for col in df.columns:
        col_lower = col.lower()
        if (col_lower == 'submitdate' or 
            'submit' in col_lower or 
            ('date' in col_lower and col_lower not in ['updatedate', 'update_date']) or
            ('data' in col_lower and 'update' not in col_lower)):
            
            # Verificar se é realmente uma data
            try:
                sample_values = df[col].dropna().head(10)
                if len(sample_values) > 0:
                    for val in sample_values:
                        test_date = pd.to_datetime(val, errors='coerce')
                        if pd.notna(test_date) and test_date.year > 1900:
                            date_fields.append(col)
                            print(f"📅 Campo de data detectado: {col}")
                            break
            except:
                continue
    
    # Combinar variáveis selecionadas com campos de data (removendo duplicatas)
    all_vars_for_records = list(selected_vars)
    for date_field in date_fields:
        if date_field not in all_vars_for_records:
            all_vars_for_records.append(date_field)
            print(f"✅ Incluído automaticamente para período de coleta: {date_field}")
    
    # Mapa de value labels por variável
    valabs = get_value_labels_map(meta)

    # ----- PROCESSAMENTO DE VARIÁVEL PESO -----
    weight_values = None
    if weight_var and weight_var in df.columns:
        try:
            weight_series = pd.to_numeric(df[weight_var], errors='coerce')
            # Substituir missing/NaN por 1.0 (peso neutro)
            weight_values = weight_series.fillna(1.0)
            # Validar pesos (devem ser positivos)
            weight_values = weight_values.abs()
            weight_values = weight_values.replace(0, 1.0)  # Zero vira 1
            print(f"⚖️ Usando variável peso: {weight_var}")
            print(f"   📊 Estatísticas do peso: Média={weight_values.mean():.3f}, Min={weight_values.min():.3f}, Max={weight_values.max():.3f}")
        except Exception as e:
            print(f"⚠️ Erro ao processar peso {weight_var}: {e}. Prosseguindo sem ponderação.")
            weight_values = None
    elif weight_var:
        print(f"⚠️ Variável peso '{weight_var}' não encontrada. Prosseguindo sem ponderação.")
        
    # Função helper para aplicar pesos
    def apply_weight(base_value, index):
        if weight_values is not None and index < len(weight_values):
            return base_value * weight_values.iloc[index]
        return base_value

    # ----- ORDEM ORIGINAL DAS CATEGORIAS (labels já normalizados) -----
    def _normalize_label_for_js(lbl):
        txt = str(lbl).replace(":", "").strip()
        return _normalize_display_value(txt)

    value_orders = {}
    for var_name, labels_dict in valabs.items():
        if not labels_dict:
            continue
        # A ordem do dict de value_labels do SPSS já vem na ordem correta
        ordered_labels = [_normalize_label_for_js(lbl) for lbl in labels_dict.values()]
        value_orders[var_name] = ordered_labels
    
    # Criar mapeamento código -> label para exibição  
    code_to_label = {}
    for var_name, labels_dict in valabs.items():
        if labels_dict:
            # CORREÇÃO: converter chaves numéricas para strings
            string_mapping = {}
            for k, v in labels_dict.items():
                # Converter 0.0 → "0", 1.0 → "1", etc.
                if isinstance(k, (int, float)) and k == int(k):
                    key_str = str(int(k))
                else:
                    key_str = str(k)
                string_mapping[key_str] = str(_normalize_label_for_js(v))
            code_to_label[var_name] = string_mapping
    
    # Metadados das variáveis e grupos de múltipla resposta (FASE 1)
    vars_meta, mr_groups = detect_variables_universal(selected_vars, meta, valabs, df)
    
    # ---------- PROCESSAMENTO DE FILTROS ----------
    filters_meta = []
    for fv in filter_vars:
        if fv in df.columns:
            unique_vals = []
            print(f"🔍 DEBUG FILTRO {fv}:")
            
            # Debug: mostrar estrutura do valabs para esta variável
            var_valabs = valabs.get(fv, {})
            if var_valabs:
                print(f"   📋 Valabs keys: {list(var_valabs.keys())} (types: {[type(k).__name__ for k in var_valabs.keys()]})")
                print(f"   📋 Valabs values: {list(var_valabs.values())}")
            else:
                print(f"   ⚠️ Nenhum value_labels encontrado para {fv}")
            
            for val in df[fv].dropna().unique():
                # Usar lookup robusto para pegar o label correto
                label = safe_value_label_lookup(valabs, fv, val)
                processed_val = str(label).replace(":", "").strip()
                processed_val = _normalize_display_value(processed_val)
                unique_vals.append(processed_val)
                print(f"   {val} ({type(val).__name__}) → '{label}' → '{processed_val}'")
            
            if unique_vals:
                filters_meta.append({
                    "name": fv,
                    "title": get_var_label(meta, fv) or fv,
                    "values": safe_sorted_unique(unique_vals)
                })
                print(f"✅ Filtro {fv}: {len(unique_vals)} valores únicos")
                print(f"   Final values: {unique_vals}")
            print()
    
    # ---------- HELPERS ESPECÍFICOS DA FASE 3 ----------
    def format_spss_date(v):
        """Converte data SPSS (número de dias) em 'YYYY-MM-DD'."""
        if pd.isna(v):
            return None
        try:
            return pd.to_datetime(v, unit='d', origin='1582-10-14').strftime('%Y-%m-%d')
        except Exception:
            return None

    def add_scale_value(scale_store, var_name, value, weight=1.0):
        """Acumula valores de variáveis scale para cálculo posterior de stats."""
        if value is None:
            return
        try:
            f = float(value)
        except Exception:
            return
        if var_name not in scale_store:
            scale_store[var_name] = []
        # Armazenar como tupla (valor, peso) para estatísticas ponderadas
        scale_store[var_name].append((f, weight))

    def compute_stats(values):
        """Calcula média, mediana, desvio padrão, min, max, n com suporte a ponderação."""
        import math
        if not values:
            return None
        
        # DEBUG: Verificar tipo dos dados recebidos
        try:
            # Verificar se são tuplas (valor, peso) ou valores simples
            if values and isinstance(values[0], tuple):
                # Valores ponderados
                weighted_values = values
                total_weight = sum(weight for _, weight in weighted_values)
                
                if total_weight == 0:
                    return None
                    
                # Média ponderada
                weighted_sum = sum(value * weight for value, weight in weighted_values)
                mean = weighted_sum / total_weight
                
                # Para mediana, criar lista expandida pelos pesos (aproximação)
                expanded_values = []
                for value, weight in weighted_values:
                    # Adicionar valor repetido proporcionalmente ao peso
                    count = max(1, int(round(weight)))
                    expanded_values.extend([value] * count)
                
                expanded_values.sort()
                n_expanded = len(expanded_values)
                if n_expanded % 2 == 1:
                    median = expanded_values[n_expanded // 2]
                else:
                    median = (expanded_values[n_expanded // 2 - 1] + expanded_values[n_expanded // 2]) / 2
                
                # Desvio padrão ponderado
                var = sum(weight * (value - mean) ** 2 for value, weight in weighted_values) / total_weight
                stddev = math.sqrt(var)
                
                # Min/Max dos valores originais
                raw_values = [value for value, _ in weighted_values]
                
                return {
                    "n": int(round(total_weight)),  # Total ponderado
                    "mean": mean,
                    "median": median,
                    "stddev": stddev,
                    "min": min(raw_values),
                    "max": max(raw_values)
                }
            else:
                # Valores simples (comportamento original)
                vals = list(values)
                n = len(vals)
                vals_sorted = sorted(vals)
                mean = sum(vals) / n
                if n % 2 == 1:
                    median = vals_sorted[n // 2]
                else:
                    median = (vals_sorted[n // 2 - 1] + vals_sorted[n // 2]) / 2
                var = sum((x - mean) ** 2 for x in vals) / n
                stddev = math.sqrt(var)
                
                return {
                    "n": n,
                    "mean": mean,
                    "median": median,
                    "stddev": stddev,
                    "min": min(vals),
                    "max": max(vals)
                }
        except Exception as e:
            print(f"⚠️ Erro em compute_stats: {e}")
            print(f"   Tipo de values: {type(values)}")
            if values:
                print(f"   Primeiro elemento: {type(values[0])} = {values[0]}")
            return None
    
    # Mapeia quais variáveis são scale numéricas
    scale_vars = {
        vm["name"]: vm
        for vm in vars_meta
        if vm.get("var_type") == "numeric" and vm.get("measure") == "scale"
    }
    scale_values_store: Dict[str, List[Tuple[float, float]]] = {name: [] for name in scale_vars.keys()}
    
    # ---------- PROCESSAMENTO DE REGISTROS ----------
    records = []
    for index, row in df.iterrows():
        rec: Dict[str, Any] = {}
        
        # Adicionar peso do registro (1.0 se não há ponderação)
        current_weight = apply_weight(1.0, index)
        rec["__weight__"] = current_weight  # Campo especial para ponderação
        
        # ----- Filtros -----
        filter_debug = {}
        for fv in filter_vars:
            if fv in df.columns:
                val = row.get(fv)
                if pd.isna(val):
                    rec[fv] = None
                    filter_debug[fv] = f"NULL"
                else:
                    # Usar lookup robusto para pegar o label correto
                    label = safe_value_label_lookup(valabs, fv, val)
                    processed_val = _normalize_display_value(
                        str(label).replace(":", "").strip()
                    )
                    rec[fv] = processed_val
                    filter_debug[fv] = f"{val}→{label}→{processed_val}"
        
        # Debug para primeiros registros
        if index < 3:
            print(f"📋 Record {index}: {filter_debug}")
        
        # ----- Variáveis -----
        for vm in vars_meta:
            vname = vm["name"]
            vtype = vm.get("var_type")      # string / numeric / date / multiple_response
            measure = vm.get("measure")     # nominal/ordinal/scale/None
            base_col = vm["sheet_code"]     # nome original da coluna ou base MR
            
            # ========= STRING =========
            if vtype == "string":
                val = row.get(base_col)
                if pd.isna(val) or not str(val).strip():
                    rec[vname] = None
                else:
                    rec[vname] = format_text_response(str(val))
                continue
            
            # ========= DATE =========
            if vtype == "date":
                val = row.get(base_col)
                rec[vname] = format_spss_date(val)
                continue
            
            # ========= MULTIPLE RESPONSE =========
            if vtype == "multiple_response":
                group = mr_groups.get(vname, {})
                members = group.get("members", [])
                subtype = group.get("mr_subtype")
                
                chosen_options: List[str] = []
                for col in members:
                    val = row.get(col)
                    if pd.isna(val):
                        continue

                    vmap = valabs.get(col, {})
                    if not mr_is_selected(val, vmap):
                        continue

                    if subtype == "binary":
                        option_text = get_mr1_label(meta, col)
                    else:
                        option_text = get_mr2_label(valabs, col, val)

                    if not option_text:
                        option_text = get_var_label(meta, col)
                    if not option_text:
                        option_text = col

                    option_text = str(option_text).strip()
                    if option_text not in chosen_options:
                        chosen_options.append(option_text)

                # Se existir variável de "outros" associada a este grupo,
                # ela entra como categoria "Outros" na MR principal.
                other_var = group.get("other_var")
                if other_var and other_var in df.columns:
                    other_val = row.get(other_var)

                    # Se é um texto preenchido válido → ativa "Outros"
                    if isinstance(other_val, str):
                        other_text = other_val.strip()

                        if other_text and other_text not in ("99", ".", "NA", "na", "N/A", "n/a", "-"):
                            if "Outros" not in chosen_options:
                                chosen_options.append("Outros")
                
                rec[vname] = safe_sorted_unique(chosen_options)
                continue
            
            # ========= NUMERIC (nominal / ordinal / scale) =========
            val = row.get(base_col)
            if pd.isna(val):
                rec[vname] = None
                continue
            
            # Categórico (nominal / ordinal)
            if measure in ("nominal", "ordinal"):
                if measure == "ordinal":
                    # Para ordinais: manter o CÓDIGO original para ordenação correta
                    processed_val = str(val).replace(":", "").strip()
                    processed_val = _normalize_display_value(processed_val)
                else:
                    # Para nominais: usar o LABEL (comportamento original)
                    label = safe_value_label_lookup(valabs, base_col, val)
                    processed_val = str(label).replace(":", "").strip()
                    processed_val = _normalize_display_value(processed_val)
                rec[vname] = processed_val
                continue
            
            # Escalar (contínuo)
            if measure == "scale":
                try:
                    num_val = float(val)
                    rec[vname] = num_val
                    add_scale_value(scale_values_store, vname, num_val, current_weight)
                except Exception:
                    rec[vname] = None
                continue
            
            # Fallback genérico
            rec[vname] = _normalize_display_value(str(val))
        
        # === PROCESSAR CAMPOS DE DATA ADICIONAIS ===
        for date_field in date_fields:
            if date_field not in rec:  # Só adicionar se não foi processado ainda
                val = row.get(date_field)
                if pd.isna(val):
                    rec[date_field] = None
                else:
                    # Tentar converter para timestamp JavaScript (formato ISO)
                    try:
                        date_obj = pd.to_datetime(val)
                        if pd.notna(date_obj):
                            # Converter para string ISO para JavaScript
                            rec[date_field] = date_obj.isoformat()
                        else:
                            rec[date_field] = None
                    except:
                        # Se não conseguir converter, manter string original
                        rec[date_field] = str(val) if val is not None else None
        
        records.append(rec)
    
    # ---------- CÁLCULO FINAL DE STATS PARA VARIÁVEIS SCALE ----------
    for vm in vars_meta:
        if vm.get("var_type") == "numeric" and vm.get("measure") == "scale":
            name = vm["name"]
            values = scale_values_store.get(name, [])
            vm["stats"] = compute_stats(values) if values else None

    # ---------- EXTRAÇÃO DE PALAVRAS‑CHAVE PARA VARIÁVEIS STRING ----------
    # Para cada variável de texto, coletar todas as respostas válidas e gerar palavras‑chave frequentes.
    try:
        for vm in vars_meta:
            if vm.get("var_type") == "string":
                vname = vm["name"]
                # Coletar respostas válidas (não nulas)
                texts = [rec.get(vname) for rec in records if rec.get(vname)]
                if texts:
                    keywords = extract_keywords_from_texts(texts)
                    vm["keywords"] = keywords  # lista de {'word': ..., 'count': ...}
                else:
                    vm["keywords"] = []
    except Exception as e:
        # Em caso de erro, não interromper o fluxo; apenas registrar no console.
        print(f"⚠️ Erro ao extrair palavras‑chave: {e}")
    
    return created_at, vars_meta, filters_meta, records, value_orders, code_to_label

# ========== GERAÇÃO DE HTML ==========

def render_html_with_working_filters(file_source: str, created_at: str, client_name: str,
                                    vars_meta: List[dict], filters_meta: List[dict], 
                                    records: List[dict], value_orders: dict, code_to_label: dict) -> str:

    # JSON strings seguros para JavaScript
    vars_meta_json = json.dumps(vars_meta, ensure_ascii=False)
    filters_meta_json = json.dumps(filters_meta, ensure_ascii=False)
    records_json = json.dumps(records, ensure_ascii=False)
    value_orders_js = json.dumps(value_orders, ensure_ascii=False)
    code_to_label_js = json.dumps(code_to_label, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard SPSS Universal</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>

    <script>
    // Ordem original das categorias vinda do SPSS
    const VARS_VALUE_ORDER = {value_orders_js};
    // Mapeamento código -> label para exibição
    const CODE_TO_LABEL = {code_to_label_js};
    
    // Função para formatação brasileira (vírgula decimal)
    function formatBR(number, decimals = 2) {{
        if (number === null || number === undefined || isNaN(number)) return 'N/A';
        return number.toFixed(decimals).replace('.', ',');
    }}
    </script>

    <style>
        :root {{
            --primary: #4A90E2;
            --primary-dark: #357ABD;
            --success: #4CAF50;
            --warning: #FF9800;
            --info: #9C27B0;
            --background: #f8f9fa;
            --text: #333;
            --border: #e5e5e5;
            --radius: 8px;
            --shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--background);
            color: var(--text);
            line-height: 1.6;
            padding: 15px;
            padding-top: 140px; /* Aumentado de 100px para 140px */
        }}

        .filters-container {{
            background: white;
            border-radius: 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            border: none;
            border-bottom: 1px solid var(--border);

            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 9999;
            width: 100%;

            margin-bottom: 0;
        }}

        .content {{
            margin-top: 40px; /* Aumentado de 30px para 40px para maior segurança */
        }}

        .filters-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 20px; /* Reduzido de 16px para 12px */
            background: #f8f9fa;
            border-bottom: 1px solid var(--border);
            border-radius: 0;
        }}

        .filter-title {{
            font-size: 16px;
            font-weight: 600;
            color: var(--text);
            margin: 0;
        }}

        .filter-actions {{
            display: flex;
            gap: 8px;
        }}

        .filter-btn {{
            padding: 8px 16px;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            background: white;
        }}

        .apply-btn {{
            background: var(--success);
            color: white;
            border-color: var(--success);
        }}

        .apply-btn:hover {{
            background: #45a049;
            border-color: #45a049;
        }}

        .clear-btn {{
            background: #f8f9fa;
            color: var(--text);
        }}

        .clear-btn:hover {{
            background: #e9ecef;
        }}

        .export-btn {{
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }}

        .export-btn:hover {{
            background: var(--primary-dark);
            border-color: var(--primary-dark);
        }}

        .filters-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            padding: 16px 20px; /* Reduzido de 20px para 16px */
        }}

        .filter-group {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .filter-label {{
            font-weight: 600;
            color: var(--text);
            font-size: 13px;
            margin-bottom: 4px;
        }}

        .custom-dropdown {{
            position: relative;
        }}

        .dropdown-button {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 12px;
            background: white;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            cursor: pointer;
            user-select: none;
            transition: all 0.2s ease;
            font-size: 13px;
        }}

        .dropdown-button:hover {{
            border-color: var(--primary);
            box-shadow: 0 0 0 1px rgba(74, 144, 226, 0.1);
        }}

        .dropdown-button.open {{
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.1);
        }}

        .dropdown-content {{
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
            margin-top: 2px;
        }}

        .dropdown-content.show {{
            display: block;
        }}

        .dropdown-option {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            cursor: pointer;
            transition: background 0.2s ease;
            font-size: 13px;
        }}

        .dropdown-option:hover {{
            background: #f8f9fa;
        }}

        .dropdown-option.select-all {{
            background: #f1f3f4;
            font-weight: 600;
            border-bottom: 1px solid var(--border);
        }}

        .dropdown-option input[type="checkbox"] {{
            margin: 0;
        }}

        .dropdown-option label {{
            cursor: pointer;
            flex: 1;
        }}

        .arrow {{
            transition: transform 0.2s ease;
            color: #666;
            font-size: 12px;
        }}

        .dropdown-button.open .arrow {{
            transform: rotate(180deg);
        }}

        .content {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}

        .section {{
            background: white;
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            overflow: hidden;
            border: 1px solid var(--border);
        }}

        .section-header {{
            background: #f8f9fa;
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
        }}

        .section-title {{
            font-size: 16px;
            font-weight: 600;
            color: var(--text);
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .section-subtitle {{
            font-size: 13px;
            color: #6c757d;
        }}

        .section-content {{
            padding: 20px;
        }}

        .chart-container {{
            position: relative;
            height: 350px;
            margin-bottom: 15px;
        }}

        .table-container {{
            overflow-x: auto;
            margin-top: 15px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}

        th, td {{
            text-align: left;
            padding: 10px 8px;
            border-bottom: 1px solid var(--border);
        }}

        th {{
            background: #f8f9fa;
            font-weight: 600;
            font-size: 13px;
        }}

        td {{
            font-size: 13px;
        }}

        .percent-bar {{
            background: #f1f3f4;
            border-radius: 4px;
            height: 18px;
            position: relative;
            overflow: hidden;
        }}

        .percent-fill {{
            background: linear-gradient(90deg, var(--primary), var(--primary-dark));
            height: 100%;
            transition: width 0.8s ease;
        }}

        /* Responsivo */
        @media (max-width: 768px) {{
            body {{
                padding: 10px;
                padding-top: 160px; /* Aumentado para mobile */
            }}
            
            .filters-grid {{
                grid-template-columns: 1fr;
                padding: 15px;
                gap: 12px;
            }}
            
            .filter-actions {{
                flex-direction: column;
                gap: 6px;
            }}
            
            .filter-btn {{
                font-size: 12px;
                padding: 6px 12px;
            }}
        }}

        @media (max-width: 480px) {{
            .filters-header {{
                flex-direction: column;
                gap: 12px;
                align-items: stretch;
            }}
            
            .filter-actions {{
                flex-direction: row;
                justify-content: center;
            }}
        }}
    </style>
</head>
<body>
    <div class="filters-container">
        <div class="filters-header">
            <h2 class="filter-title">🔍 Filtros de Seleção</h2>
            <div class="filter-actions">
                <button class="filter-btn apply-btn" onclick="applyFilters()">✓ Aplicar</button>
                <button class="filter-btn clear-btn" onclick="clearFilters()">🔄 Limpar</button>
                <button class="filter-btn export-btn" onclick="exportAllTables()">📊 Excel</button>
                <button class="filter-btn export-btn" onclick="exportToPDF()">📄 PDF</button>
            </div>
        </div>
        <div class="filters-grid" id="filtersGrid">
            <!-- Filtros gerados dinamicamente -->
        </div>
    </div>

    <div class="content" id="content">
        <!-- Conteúdo gerado dinamicamente -->
    </div>

    <script>
        // DADOS GLOBAIS - JSONs seguros
        const VARS_META = {vars_meta_json};
        const FILTERS_META = {filters_meta_json};
        const RECORDS = {records_json};
        const FILTERS = FILTERS_META;
        const CHART_LABEL_MAX = {CHART_LABEL_MAX};
    // Função para quebrar rótulos longos em múltiplas linhas
    function wrapLabel(label, maxLen) {{
        if (label === null || label === undefined) return [''];
        const raw = String(label).trim();
        if (raw.length <= maxLen) return [raw];

        const words = raw.split(' ');
        const lines = [];
        let current = '';

        words.forEach(word => {{
            const tentative = (current + ' ' + word).trim();
            if (tentative.length > maxLen) {{
                if (current.trim().length > 0) {{
                    lines.push(current.trim());
                }}
                current = word;
            }} else {{
                current = tentative;
            }}
        }});

        if (current.trim().length > 0) {{
            lines.push(current.trim());
        }}
        return lines;
    }}


        // Estados globais
        let charts = {{}};

        // INICIALIZAÇÃO
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('🌍 Dashboard SPSS Universal carregado');
            console.log('📊 ' + VARS_META.length + ' variáveis, ' + FILTERS.length + ' filtros, ' + RECORDS.length + ' registros');
            
            buildFilters();
            renderAll();
        }});

        // FILTROS - USANDO f em vez de filter para evitar conflitos
        function buildFilters() {{
            const container = document.getElementById('filtersGrid');
            if (!container) return;
            
            container.innerHTML = '';
            
            if (FILTERS.length === 0) {{
                container.innerHTML = '<p style="color: #999; font-style: italic;">Nenhum filtro disponível</p>';
                return;
            }}
            
            FILTERS.forEach(f => {{
                const filterGroup = document.createElement('div');
                filterGroup.className = 'filter-group';
                
                const label = document.createElement('label');
                label.className = 'filter-label';
                label.textContent = f.title;
                filterGroup.appendChild(label);
                
                const dropdownContainer = document.createElement('div');
                dropdownContainer.className = 'custom-dropdown';
                
                const dropdownButton = document.createElement('div');
                dropdownButton.className = 'dropdown-button';
                dropdownButton.onclick = () => toggleDropdown(f.name);
                dropdownButton.innerHTML = '<span id="' + f.name + 'Text">Todos</span><span class="arrow">▼</span>';
                
                const dropdownContent = document.createElement('div');
                dropdownContent.className = 'dropdown-content';
                dropdownContent.id = f.name + 'Content';
                
                const selectAllOption = document.createElement('div');
                selectAllOption.className = 'dropdown-option select-all';
                selectAllOption.innerHTML = '<input type="checkbox" onchange="selectAllOptions(\\'' + f.name + '\\')"><label>Selecionar Todos</label>';
                dropdownContent.appendChild(selectAllOption);
                
                f.values.forEach(value => {{
                    const option = document.createElement('div');
                    option.className = 'dropdown-option';
                    option.innerHTML = '<input type="checkbox" value="' + value + '" onchange="updateDropdownText(\\'' + f.name + '\\')"><label>' + value + '</label>';
                    dropdownContent.appendChild(option);
                }});
                
                dropdownContainer.appendChild(dropdownButton);
                dropdownContainer.appendChild(dropdownContent);
                filterGroup.appendChild(dropdownContainer);
                container.appendChild(filterGroup);
            }});
        }}

        function toggleDropdown(filterId) {{
            const button = event.currentTarget;
            const content = document.getElementById(filterId + 'Content');
            
            document.querySelectorAll('.dropdown-content').forEach(dropdown => {{
                if (dropdown !== content) dropdown.classList.remove('show');
            }});
            document.querySelectorAll('.dropdown-button').forEach(btn => {{
                if (btn !== button) btn.classList.remove('open');
            }});
            
            content.classList.toggle('show');
            button.classList.toggle('open');
        }}

        function selectAllOptions(filterId) {{
            const content = document.getElementById(filterId + 'Content');
            const selectAllCheckbox = content.querySelector('.select-all input');
            const checkboxes = content.querySelectorAll('.dropdown-option:not(.select-all) input');
            
            checkboxes.forEach(cb => cb.checked = selectAllCheckbox.checked);
            updateDropdownText(filterId);
        }}

        function updateDropdownText(filterId) {{
            const content = document.getElementById(filterId + 'Content');
            const textElement = document.getElementById(filterId + 'Text');
            const checkboxes = content.querySelectorAll('.dropdown-option:not(.select-all) input');
            const checkedBoxes = content.querySelectorAll('.dropdown-option:not(.select-all) input:checked');
            
            if (checkedBoxes.length === 0) {{
                textElement.textContent = 'Todos';
            }} else if (checkedBoxes.length === 1) {{
                textElement.textContent = checkedBoxes[0].nextElementSibling.textContent;
            }} else if (checkedBoxes.length === checkboxes.length) {{
                textElement.textContent = 'Todos';
            }} else {{
                textElement.textContent = checkedBoxes.length + ' selecionados';
            }}
        }}

        function getSelectedFilters() {{
            const selectedFilters = {{}};
            FILTERS.forEach(f => {{
                const content = document.getElementById(f.name + 'Content');
                if (content) {{
                    const checkedBoxes = content.querySelectorAll('.dropdown-option:not(.select-all) input:checked');
                    selectedFilters[f.name] = Array.from(checkedBoxes).map(cb => cb.value);
                }}
            }});
            return selectedFilters;
        }}

        function applyFilters() {{
            document.querySelectorAll('.dropdown-content').forEach(d => d.classList.remove('show'));
            document.querySelectorAll('.dropdown-button').forEach(b => b.classList.remove('open'));
            renderAll();
        }}

        function clearFilters() {{
            document.querySelectorAll('.dropdown-content input[type="checkbox"]').forEach(cb => cb.checked = false);
            FILTERS.forEach(f => {{
                const textElement = document.getElementById(f.name + 'Text');
                if (textElement) textElement.textContent = 'Todos';
            }});
            document.querySelectorAll('.dropdown-content').forEach(d => d.classList.remove('show'));
            document.querySelectorAll('.dropdown-button').forEach(b => b.classList.remove('open'));
            renderAll();
        }}

        function getFilteredRecords() {{
            const selectedFilters = getSelectedFilters();
            return RECORDS.filter(record => {{
                return Object.keys(selectedFilters).every(filterName => {{
                    const filterValues = selectedFilters[filterName];
                    if (filterValues.length === 0) return true;
                    const recordValue = record[filterName];
                    if (recordValue === null || recordValue === undefined) return false;
                    
                    // Normalizar valores para comparação
                    const normalizedRecordValue = String(recordValue).trim();
                    const normalizedFilterValues = filterValues.map(v => String(v).trim());
                    
                    return normalizedFilterValues.includes(normalizedRecordValue);
                }});
            }});
        }}

        // RENDERIZAÇÃO
        function renderAll() {{
            const filteredRecords = getFilteredRecords();
            const content = document.getElementById('content');
            content.innerHTML = '';
            
            console.log('🔄 Renderizando com ' + filteredRecords.length + ' registros filtrados');
            console.log('📋 Ordem das variáveis sendo processadas:', VARS_META.map(v => v.name));
            
            VARS_META.forEach((varMeta, index) => {{
                const section = createSection(varMeta, filteredRecords);
                content.appendChild(section);
            }});
        }}


        function renderStringVariable(varMeta, records) {{
            const container = document.createElement('div');

            // Normaliza texto: tira espaços, ignora '99' e aplica capitalização simples
            function normalizeText(text) {{
                if (text === null || text === undefined) return '';
                let t = String(text).trim();
                if (!t || t === '99') return '';
                return t.charAt(0).toUpperCase() + t.slice(1).toLowerCase();
            }}

            // Coleta e normaliza as respostas
            let validResponses = records
                .map(r => normalizeText(r[varMeta.name]))
                .filter(v => v !== '');

            if (validResponses.length === 0) {{
                container.innerHTML = '<p style="color: #999; font-style: italic;">Nenhuma resposta encontrada</p>';
                return container;
            }}

            // ✅ DEBUG: Verificar ordem das respostas
            console.log(`📝 ${{varMeta.name}}: Respostas de texto encontradas:`, validResponses.slice(0, 5));

            // ✅ REGRA CORRETA: Textual = Ordem alfabética
            validResponses.sort((a, b) => a.localeCompare(b, 'pt-BR'));

            // --------- BLOCO VISUAL (lista normal como antes) ----------
            const summary = document.createElement('p');
            summary.innerHTML = '<strong>Total de respostas:</strong> ' + validResponses.length;
            summary.style.marginBottom = '15px';

            const responseList = document.createElement('div');
            responseList.style.cssText =
                'max-height: 400px; overflow-y: auto; border: 1px solid var(--border); ' +
                'border-radius: var(--radius); background: #f8f9fa;';

            validResponses.forEach((response, index) => {{
                const responseItem = document.createElement('div');
                responseItem.style.cssText =
                    'padding: 12px 16px; border-bottom: 1px solid var(--border); ' +
                    'background: white; margin-bottom: 1px; font-size: 13px;';
                responseItem.innerHTML =
                    '<strong>' + (index + 1) + '.</strong> ' + String(response);
                responseList.appendChild(responseItem);
            }});

            // --------- TABELA OCULTA PARA EXPORTAÇÃO (USADA PELO EXCEL) ----------
            const exportTable = document.createElement('table');
            exportTable.className = 'export-text-table';
            exportTable.style.display = 'none'; // invisível para o usuário

            const thead = document.createElement('thead');
            const headRow = document.createElement('tr');
            ['Nº', 'Resposta'].forEach(h => {{
                const th = document.createElement('th');
                th.innerText = h;
                headRow.appendChild(th);
            }});
            thead.appendChild(headRow);

            const tbody = document.createElement('tbody');
            validResponses.forEach((resp, idx) => {{
                const tr = document.createElement('tr');

                const tdIndex = document.createElement('td');
                tdIndex.innerText = (idx + 1).toString();
                tr.appendChild(tdIndex);

                const tdResp = document.createElement('td');
                tdResp.innerText = resp;
                tr.appendChild(tdResp);

                tbody.appendChild(tr);
            }});

            exportTable.appendChild(thead);
            exportTable.appendChild(tbody);

            // Conteúdo principal: adiciona sumário e lista de respostas
            container.appendChild(summary);

            // --------- PALAVRAS‑CHAVE E FILTRO ---------
            const keywords = varMeta.keywords || [];
            if (keywords && keywords.length > 0) {{
                const filterContainer = document.createElement('div');
                filterContainer.style.cssText = 'margin-bottom: 8px; display: flex; flex-wrap: wrap; gap: 4px; align-items: center;';
                const filterTitle = document.createElement('span');
                filterTitle.style.fontSize = '13px';
                filterTitle.style.fontWeight = '600';
                filterTitle.textContent = 'Palavras‑chave:';
                filterContainer.appendChild(filterTitle);

                // Função auxiliar para normalizar texto para comparação: converte para minúsculas
                // e remove acentos.  Isso garante que "informacoes" corresponda a "informação".
                function normalizeForComparison(str) {{
                    if (!str) return '';
                    return String(str).toLowerCase()
                        .normalize('NFD')
                        .replace(/[\u0300-\u036f]/g, '');
                }}

                // Função para aplicar filtro nas respostas.
                // Normaliza tanto o termo pesquisado quanto o texto de cada resposta para
                // garantir correspondência sem acentuação.
                function applyKeywordFilter(kw) {{
                    const normKw = kw ? normalizeForComparison(kw) : null;
                    const items = responseList.children;
                    for (let i = 0; i < items.length; i++) {{
                        const item = items[i];
                        const text = item.textContent || '';
                        const normText = normalizeForComparison(text);
                        if (!normKw || normText.includes(normKw)) {{
                            item.style.display = '';
                        }} else {{
                            item.style.display = 'none';
                        }}
                    }}
                }}

                keywords.forEach(k => {{
                    const kwBtn = document.createElement('span');
                    kwBtn.style.cssText = 'padding: 4px 6px; border: 1px solid var(--border); border-radius: 4px; cursor: pointer; font-size: 12px; background: #f1f1f1;';
                    kwBtn.textContent = k.word + ' (' + k.count + ')';
                    // Define tooltip sem usar aspas internas para evitar erros de sintaxe
                    kwBtn.title = "Filtrar por " + k.word;
                    // Armazena a raiz normalizada como dataset para o botão
                    kwBtn.dataset.root = k.root;
                    kwBtn.onclick = () => applyKeywordFilter(k.root);
                    filterContainer.appendChild(kwBtn);
                }});
                // Botão para limpar filtro.  Usa a mesma paleta do botão "Limpar" do header e inclui ícone.
                const clearBtn = document.createElement('span');
                clearBtn.style.cssText = 'padding: 4px 8px; border: 1px solid #b6e0fe; border-radius: 4px; cursor: pointer; font-size: 12px; background: #e9f7fe; color: #0d6efd; display: inline-flex; align-items: center; gap: 4px;';
                clearBtn.innerHTML = '🔄 <span>Limpar filtros</span>';
                clearBtn.title = "Remover filtro de palavra‑chave";
                clearBtn.onclick = () => applyKeywordFilter(null);
                filterContainer.appendChild(clearBtn);
                container.appendChild(filterContainer);
            }}

            container.appendChild(responseList);

            // adiciona a tabela escondida ao container
            container.appendChild(exportTable);


            return container;
        }}

        function renderNumericScaleVariable(varMeta, records) {{
            const container = document.createElement('div');

            // Coletar valores com seus pesos para histograma ponderado
            const weightedValues = [];
            records.forEach(r => {{
                const value = r[varMeta.name];
                const weight = r.__weight__ || 1.0;
                if (value !== null && value !== undefined && !isNaN(value)) {{
                    weightedValues.push({{value: Number(value), weight: weight}});
                }}
            }});

            if (weightedValues.length === 0) {{
                container.innerHTML = '<p style="color: #999; font-style: italic;">Nenhum valor numérico válido encontrado</p>';
                return container;
            }}

            const stats = varMeta.stats || {{}};
            const summary = document.createElement('p');
            let statsText = '<strong>Estatísticas</strong>: ';

            if (stats && typeof stats === 'object') {{
                const parts = [];
                if (stats.n !== undefined)      parts.push(`N = ${{Math.round(stats.n)}}`);
                if (stats.mean !== undefined)   parts.push(`Média = ${{formatBR(stats.mean)}}`);
                if (stats.median !== undefined) parts.push(`Mediana = ${{formatBR(stats.median)}}`);
                if (stats.stddev !== undefined) parts.push(`DP = ${{formatBR(stats.stddev)}}`);
                if (stats.min !== undefined)    parts.push(`Mín = ${{formatBR(stats.min)}}`);
                if (stats.max !== undefined)    parts.push(`Máx = ${{formatBR(stats.max)}}`);
                statsText += parts.join(' | ');
            }} else {{
                statsText += 'não disponível';
            }}

            summary.innerHTML = statsText;
            summary.style.marginBottom = '15px';

            const chartContainer = document.createElement('div');
            chartContainer.className = 'chart-container';

            const canvas = document.createElement('canvas');
            chartContainer.appendChild(canvas);
            const ctx = canvas.getContext('2d');

            // Extrair apenas os valores para calcular min/max
            const values = weightedValues.map(wv => wv.value);
            const minVal = Math.min(...values);
            const maxVal = Math.max(...values);
            const binCount = 10;
            const range = maxVal - minVal || 1;
            const binSize = range / binCount;

            const bins = new Array(binCount).fill(0);
            const labels = [];

            for (let i = 0; i < binCount; i++) {{
                const start = minVal + i * binSize;
                const end = (i === binCount - 1) ? maxVal : (start + binSize);
                labels.push(`${{formatBR(start, 1)}} – ${{formatBR(end, 1)}}`);
            }}

            // Distribuir valores ponderados nos bins
            weightedValues.forEach(wv => {{
                let idx = Math.floor((wv.value - minVal) / binSize);
                if (idx < 0) idx = 0;
                if (idx >= binCount) idx = binCount - 1;
                bins[idx] += wv.weight;  // Usar peso em vez de 1
            }});

            const totalCases = weightedValues.reduce((sum, wv) => sum + wv.weight, 0);
            const percentages = bins.map(count => totalCases > 0 ? (count / totalCases * 100) : 0);
            
            // ✅ AJUSTE DINÂMICO: Eixo Y se adapta ao valor máximo
            const maxPercentage = Math.max(...percentages);
            const yAxisMax = maxPercentage > 0
                ? Math.min(100, Math.ceil(maxPercentage / 10) * 10)
                : 100;

            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: labels.map(label => wrapLabel(label, CHART_LABEL_MAX)),
                    datasets: [{{
                        data: percentages,
                        backgroundColor: 'rgba(74, 144, 226, 0.7)',
                        borderColor: 'rgba(74, 144, 226, 1)',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    const index = context.dataIndex;
                                    const count = Math.round(bins[index]);  // Arredondar para inteiro
                                    const pct = context.parsed.y;
                                    return `${{formatBR(pct, 1)}}% (${{count}} casos)`;
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            max: yAxisMax,
                            ticks: {{
                                callback: function(value) {{
                                    return value + '%';
                                }}
                            }}
                        }},
                        x: {{
                            // Para histograma: barras sem espaço entre elas
                            categoryPercentage: 1.0,
                            barPercentage: 1.0
                        }}
                    }}
                }}
            }});

            container.appendChild(summary);
            container.appendChild(chartContainer);

            return container;
        }}

        function renderDateVariable(varMeta, records) {{
            const container = document.createElement('div');

            const freq = {{}};
            let validCount = 0;

            records.forEach(r => {{
                const v = r[varMeta.name];
                const weight = r.__weight__ || 1.0;  // Peso do registro
                if (v !== null && v !== undefined && String(v).trim() !== '') {{
                    validCount += weight;
                    const key = String(v);
                    freq[key] = (freq[key] || 0) + weight;
                }}
            }});

            const entries = Object.entries(freq);
            if (entries.length === 0) {{
                container.innerHTML = '<p style="color: #999; font-style: italic;">Nenhuma data válida encontrada</p>';
                return container;
            }}

            // ✅ REGRA CORRETA: Datas ordenadas cronologicamente
            entries.sort((a, b) => new Date(a[0]) - new Date(b[0]));

            const labels = entries.map(([d]) => d);
            const counts = entries.map(([, c]) => c);
            const percentages = counts.map(count => validCount > 0 ? (count / validCount * 100) : 0);
            
            // ✅ AJUSTE DINÂMICO: Eixo Y se adapta ao valor máximo
            const maxPercentage = Math.max(...percentages);
            const yAxisMax = maxPercentage > 0
                ? Math.min(100, Math.ceil(maxPercentage / 10) * 10)
                : 100;

            const chartContainer = document.createElement('div');
            chartContainer.className = 'chart-container';
            const canvas = document.createElement('canvas');
            chartContainer.appendChild(canvas);
            const ctx = canvas.getContext('2d');

            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: labels.map(label => wrapLabel(label, CHART_LABEL_MAX)),
                    datasets: [{{
                        data: percentages,
                        backgroundColor: 'rgba(76, 175, 80, 0.7)',
                        borderColor: 'rgba(76, 175, 80, 1)',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    const index = context.dataIndex;
                                    const qty = Math.round(counts[index]);  // Arredondar para inteiro
                                    const pct = context.parsed.y;
                                    return `${{formatBR(pct, 1)}}% (${{qty}} casos)`;
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            max: yAxisMax,
                            ticks: {{
                                callback: function(value) {{
                                    return value + '%';
                                }}
                            }}
                        }},
                        x: {{
                            ticks: {{
                                maxRotation: 45,
                                minRotation: 0
                            }}
                        }}
                    }}
                }}
            }});

            const summary = document.createElement('p');
            summary.innerHTML = '<strong>Resumo:</strong> ' +
                entries.length + ' datas distintas';
            summary.style.marginTop = '15px';

            container.appendChild(chartContainer);
            container.appendChild(summary);

            return container;
        }}

        function renderCategoricalVariable(varMeta, records) {{
            const container = document.createElement('div');
            const freq = {{}};
            let validCount = 0;

            // Conta frequências
            records.forEach(r => {{
                let v = r[varMeta.name];
                const weight = r.__weight__ || 1.0;  // Peso do registro
                
                if (Array.isArray(v)) {{
                    // MR
                    v.forEach(item => {{
                        if (item !== null && item !== undefined && String(item).trim() !== '') {{
                            const key = String(item).trim();
                            freq[key] = (freq[key] || 0) + weight;
                            validCount += weight;
                        }}
                    }});
                }} else {{
                    // Categórica simples
                    if (v !== null && v !== undefined && String(v).trim() !== '') {{
                        const key = String(v).trim();
                        freq[key] = (freq[key] || 0) + weight;
                        validCount += weight;
                    }}
                }}
            }});

            const entries = Object.entries(freq);
            if (entries.length === 0) {{
                container.innerHTML = '<p style="color:#999;font-style:italic;">Nenhum dado disponível</p>';
                return container;
            }}

            // ✅ DEBUG: Verificar ordem das categorias
            console.log(`📊 ${{varMeta.name}}: Categorias encontradas:`, entries.map(([label]) => label));

            // ✅ REGRAS CORRETAS DE ORDENAÇÃO baseadas no tipo da variável
            const varType = varMeta.var_type || varMeta.type || 'single';
            const measure = varMeta.measure || 'nominal';
            
            if (varType === 'multiple_response' || varMeta.type === 'mr') {{
                // 🔗 MR NOMINAL: Da maior frequência para a menor
                entries.sort((a, b) => b[1] - a[1]);
                console.log(`🔗 ${{varMeta.name}}: MR ordenado por frequência (maior→menor)`);
                
            }} else if (measure === 'ordinal') {{
                console.log(`📈 Ordenando categorias pela ordem SPSS (ordinal)`);

                // Recuperar ordem SPSS vinda do Python
                const valueOrder = VARS_VALUE_ORDER[varMeta.name] || [];

                // Ordenar conforme a ordem real dos códigos SPSS
                entries.sort((a, b) => {{
                    const codeA = isNaN(a[0]) ? a[0] : Number(a[0]);
                    const codeB = isNaN(b[0]) ? b[0] : Number(b[0]);

                    const ia = valueOrder.indexOf(codeA);
                    const ib = valueOrder.indexOf(codeB);

                    return ia - ib;
                }});
                
            }} else {{
                // 📊 SINGLE NOMINAL: Da maior frequência para a menor
                entries.sort((a, b) => b[1] - a[1]);
                console.log(`📊 ${{varMeta.name}}: Nominal ordenado por frequência (maior→menor)`);
            }}

            // Aplicar labels descritivos APÓS ordenação
            const labels = entries.map(([label]) => {{
                if (CODE_TO_LABEL[varMeta.name] && CODE_TO_LABEL[varMeta.name][label]) {{
                    const descLabel = CODE_TO_LABEL[varMeta.name][label];
                    console.log(`✅ ${{varMeta.name}}: "${{label}}" → "${{descLabel}}"`);
                    return descLabel;
                }}
                return label;
            }});
            const counts = entries.map(([,count]) => count);
            const percentages = counts.map(count => validCount > 0 ? (count / validCount * 100) : 0);
            
            // ✅ AJUSTE DINÂMICO: Eixo Y se adapta ao valor máximo
            const maxPercentage = Math.max(...percentages);
            const yAxisMax = maxPercentage > 0
                ? Math.min(100, Math.ceil(maxPercentage / 10) * 10)
                : 100;

            // ----- Gráfico -----
            const chartContainer = document.createElement('div');
            chartContainer.className = 'chart-container';
            
            const canvas = document.createElement('canvas');
            chartContainer.appendChild(canvas);
            const ctx = canvas.getContext('2d');

            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: labels.map(label => wrapLabel(label, CHART_LABEL_MAX)),
                    datasets: [{{
                        data: percentages,
                        backgroundColor: 'rgba(74, 144, 226, 0.7)',
                        borderColor: 'rgba(74, 144, 226, 1)',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    const index = context.dataIndex;
                                    const qty = Math.round(counts[index]);  // Arredondar para inteiro
                                    const pct = context.parsed.y;
                                    return `${{formatBR(pct, 1)}}% (${{qty}} casos)`;
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            max: yAxisMax,
                            ticks: {{
                                callback: function(value) {{
                                    return value + '%';
                                }}
                            }}
                        }}
                    }}
                }}
            }});

            // ----- Tabela -----
            const table = document.createElement('table');
            table.className = 'table-categorical';

            const header = document.createElement('tr');
            header.innerHTML = '<th>Categoria</th><th>Frequência</th><th>%</th>';
            table.appendChild(header);

            entries.forEach(([label, count]) => {{
                const pct = validCount > 0 ? formatBR(count / validCount * 100, 1) : '0,0';
                
                // Usar label descritivo se disponível
                let displayLabel = label;
                if (CODE_TO_LABEL[varMeta.name] && CODE_TO_LABEL[varMeta.name][label]) {{
                    displayLabel = CODE_TO_LABEL[varMeta.name][label];
                }}
                
                const row = document.createElement('tr');
                row.innerHTML = `<td>${{displayLabel}}</td><td>${{Math.round(count)}}</td><td>${{pct}}%</td>`;
                table.appendChild(row);
            }});

            // Linha de total
            const totalRow = document.createElement('tr');
            totalRow.style.fontWeight = 'bold';
            totalRow.style.borderTop = '2px solid #ddd';
            totalRow.style.backgroundColor = '#f8f9fa';
            const totalCount = Math.round(entries.reduce((sum, [, count]) => sum + count, 0));
            totalRow.innerHTML = `<td>Total</td><td>${{totalCount}}</td><td>100,0%</td>`;
            table.appendChild(totalRow);

            container.appendChild(chartContainer);
            
            // const summary = document.createElement('p');
            // summary.textContent = validCount + ' respostas válidas';
            // summary.style.marginTop = '15px';
            // container.appendChild(summary);
            container.appendChild(table);

            return container;
        }}

        function createSection(varMeta, records) {{
            const section = document.createElement('div');
            section.className = 'section';
            
            const header = document.createElement('div');
            header.className = 'section-header';
            
            const title = document.createElement('h2');
            title.className = 'section-title';
            
            const varType = varMeta.var_type || varMeta.type || "single";
            const measure = varMeta.measure || null;
            
            let icon = '';
            if (varType === 'string') {{
                icon = '📝';
            }} else if (varType === 'multiple_response' || varMeta.type === 'mr') {{
                icon = '☑️';
            }} else if (varType === 'date') {{
                icon = '📅';
            }} else if (varType === 'numeric' && measure === 'scale') {{
                icon = '📈';
            }} else {{
                icon = '📊';
            }}
            
            title.innerHTML = icon + ' ' + varMeta.title;
            
            const subtitle = document.createElement('div');
            subtitle.className = 'section-subtitle';
            subtitle.textContent = varMeta.spss_type || '';
            
            header.appendChild(title);
            header.appendChild(subtitle);
            
            const content = document.createElement('div');
            content.className = 'section-content';
            
            // Escolha do renderizador
            if (varType === 'string') {{
                content.appendChild(renderStringVariable(varMeta, records));
            }} else if (varType === 'multiple_response' || varMeta.type === 'mr') {{
                content.appendChild(renderCategoricalVariable(varMeta, records));
            }} else if (varType === 'date') {{
                content.appendChild(renderDateVariable(varMeta, records));
            }} else if (varType === 'numeric' && measure === 'scale') {{
                content.appendChild(renderNumericScaleVariable(varMeta, records));
            }} else {{
                // numeric nominal/ordinal ou qualquer categórico
                content.appendChild(renderCategoricalVariable(varMeta, records));
            }}
            section.appendChild(header);
            section.appendChild(content);            
            return section;
        }}


        // Eventos globais
        document.addEventListener('click', function(event) {{
            if (!event.target.closest('.custom-dropdown')) {{
                document.querySelectorAll('.dropdown-content').forEach(d => d.classList.remove('show'));
                document.querySelectorAll('.dropdown-button').forEach(b => b.classList.remove('open'));
            }}
        }});

        document.addEventListener('keydown', function(event) {{
            if (event.key === 'Escape') {{
                document.querySelectorAll('.dropdown-content').forEach(d => d.classList.remove('show'));
                document.querySelectorAll('.dropdown-button').forEach(b => b.classList.remove('open'));
            }}
        }});

        function exportAllTables() {{
            const sections = document.querySelectorAll('.section');
            if (!sections.length) {{
                alert("Nenhuma tabela encontrada.");
                return;
            }}

            const wb = XLSX.utils.book_new();

            sections.forEach(section => {{
                const titleEl = section.querySelector('.section-title');
                const table = section.querySelector('table');

                if (!table) return;

                const title = titleEl ? titleEl.innerText.trim() : "Variável";

                // Extrair linhas
                const rows = [];
                table.querySelectorAll('tr').forEach(tr => {{
                    const row = [];
                    tr.querySelectorAll('th, td').forEach(cell => {{
                        row.push(cell.innerText.trim());
                    }});
                    rows.push(row);
                }});

                // Criar aba
                const ws = XLSX.utils.aoa_to_sheet([
                    [title],
                    [""],
                    ...rows
                ]);

                // Remove caracteres proibidos pelo Excel
                let safeName = title.replace(/[:\\\\/\\?\\*\\[\\]]/g, "");

                // Remove múltiplos espaços
                safeName = safeName.replace(/\\s+/g, ' ').trim();

                // Corta para 31 caracteres (limite do Excel)
                const sheetName = safeName.substring(0, 31) || "Aba";
                XLSX.utils.book_append_sheet(wb, ws, sheetName);
            }});

            const fileName = "tabelas_exportadas.xlsx";
            XLSX.writeFile(wb, fileName);
        }}

        // ===== FUNÇÕES DE EXPORTAÇÃO PDF =====
        
        function formatNumberBR(num) {{
            // Formatação brasileira: 1.234 (ponto para milhares)
            return num.toLocaleString('pt-BR');
        }}

        function getActiveFiltersDescription() {{
            const selectedFilters = getSelectedFilters();
            const activeFilters = [];
            
            Object.keys(selectedFilters).forEach(filterName => {{
                const filterValues = selectedFilters[filterName];
                if (filterValues.length > 0) {{
                    const filterMeta = FILTERS.find(f => f.name === filterName);
                    const filterTitle = filterMeta ? filterMeta.title : filterName;
                    
                    if (filterValues.length === 1) {{
                        activeFilters.push(`${{filterTitle}}: ${{filterValues[0]}}`);
                    }} else {{
                        activeFilters.push(`${{filterTitle}}: ${{filterValues.length}} selecionados`);
                    }}
                }}
            }});
            
            return activeFilters.length > 0 ? activeFilters : ['Nenhum filtro aplicado'];
        }}

        function createPDFHeader() {{
            const now = new Date();
            const dateStr = now.toLocaleString('pt-BR', {{
                day: '2-digit',
                month: '2-digit', 
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            }});
            
            // Extrair informações dos dados globais
            const totalRecords = RECORDS.length;
            const totalVars = VARS_META.length;
            const activeFilters = getActiveFiltersDescription();
            
            const header = document.createElement('div');
            header.style.cssText = `
                background: white;
                padding: 20px;
                border-bottom: 3px solid #4A90E2;
                margin-bottom: 20px;
                font-family: Arial, sans-serif;
                page-break-after: always;
            `;
            
            header.innerHTML = `
                <div style="text-align: center; margin-bottom: 20px;">
                    <h1 style="color: #4A90E2; font-size: 24px; margin: 0;">📋 DASHBOARD DE ANÁLISE - PESQUISA SPSS</h1>
                    <div style="border: 2px solid #4A90E2; margin: 10px 0;"></div>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; font-size: 16px;">
                    <div>
                        <p style="margin: 5px 0;"><strong>📂 Arquivo:</strong> {file_source}</p>
                        <p style="margin: 5px 0;"><strong>📅 Gerado em:</strong> ${{dateStr}}</p>
                    </div>
                    <div>
                        <p style="margin: 5px 0;"><strong>👥 Respondentes:</strong> ${{formatNumberBR(totalRecords)}}</p>
                        <p style="margin: 5px 0;"><strong>📊 Variáveis analisadas:</strong> ${{formatNumberBR(totalVars)}}</p>
                    </div>
                </div>
                
                <div style="margin-top: 15px;">
                    <p style="margin: 5px 0; font-weight: bold;">🔍 Filtros aplicados:</p>
                    ${{activeFilters.map(filter => `<p style="margin: 2px 0 2px 20px;">• ${{filter}}</p>`).join('')}}
                </div>
                
                <div style="border: 2px solid #4A90E2; margin: 20px 0 10px 0;"></div>
            `;
            
            return header;
        }}

        async function exportToPDF() {{
            try {{
                // Mostrar loading
                const originalBtn = event.target;
                originalBtn.textContent = '📄 Gerando...';
                originalBtn.disabled = true;
                
                console.log('=== EXPORTAÇÃO PDF INICIADA ===');
                
                // Verificar se há conteúdo
                const contentEl = document.getElementById('content');
                const sections = contentEl.querySelectorAll('.section');
                
                if (sections.length === 0) {{
                    alert('⚠️ Nenhum conteúdo encontrado para exportar!');
                    originalBtn.textContent = '📄 PDF';
                    originalBtn.disabled = false;
                    return;
                }}
                
                console.log(`📊 Encontradas ${{sections.length}} seções para exportar`);
                
                // === ESTRATÉGIA SIMPLES E ROBUSTA ===
                
                // Criar cabeçalho simples
                const headerDiv = document.createElement('div');
                headerDiv.className = 'pdf-header-temp';
                headerDiv.style.cssText = `
                    background: white;
                    padding: 20px;
                    border-bottom: 3px solid #4A90E2;
                    margin-bottom: 20px;
                    font-family: Arial, sans-serif;
                    display: none;
                    print-color-adjust: exact;
                    -webkit-print-color-adjust: exact;
                `;
                
                // Informações do cabeçalho
                const now = new Date();
                const dateStr = now.toLocaleString('pt-BR');
                const totalRecords = RECORDS.length;
                const totalVars = VARS_META.length;
                const activeFilters = getActiveFiltersDescription();
                
                // === CALCULAR PERÍODO DE COLETA ===
                let periodoColeta = 'Não disponível';
                try {{
                    const submitDates = [];
                    RECORDS.forEach(record => {{
                        // Procurar por campos que possam conter Submit Date
                        Object.keys(record).forEach(key => {{
                            if (key.toLowerCase().includes('submit') || 
                                key.toLowerCase().includes('date') || 
                                key.toLowerCase().includes('data')) {{
                                const value = record[key];
                                if (value && value !== null) {{
                                    // Tentar converter para data
                                    const dateValue = new Date(value);
                                    if (!isNaN(dateValue.getTime()) && dateValue.getFullYear() > 1900) {{
                                        submitDates.push(dateValue);
                                    }}
                                }}
                            }}
                        }});
                    }});
                    
                    if (submitDates.length > 0) {{
                        const minDate = new Date(Math.min(...submitDates));
                        const maxDate = new Date(Math.max(...submitDates));
                        
                        const formatDateBR = (date) => {{
                            return date.toLocaleDateString('pt-BR');
                        }};
                        
                        if (minDate.getTime() === maxDate.getTime()) {{
                            periodoColeta = formatDateBR(minDate);
                        }} else {{
                            periodoColeta = `${{formatDateBR(minDate)}} até ${{formatDateBR(maxDate)}}`;
                        }}
                    }}
                }} catch (error) {{
                    console.log('ℹ️ Não foi possível calcular período de coleta:', error);
                }}
                
                headerDiv.innerHTML = `
                    <h1 style="color: #4A90E2; text-align: center; margin-bottom: 20px;">📋 DASHBOARD DE ANÁLISE - PESQUISA SPSS</h1>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; font-size: 14px;">
                        <div>
                            <div style="margin: 4px 0;"><strong>📂 Arquivo:</strong> {file_source}</div>
                            <div style="margin: 4px 0;"><strong>📅 Gerado em:</strong> ${{dateStr}}</div>
                            <div style="margin: 4px 0;"><strong>📅 Período de coleta:</strong> ${{periodoColeta}}</div>
                        </div>
                        <div>
                            <div style="margin: 4px 0;"><strong>👥 Respondentes:</strong> ${{formatNumberBR(totalRecords)}}</div>
                            <div style="margin: 4px 0;"><strong>📊 Variáveis analisadas:</strong> ${{formatNumberBR(totalVars)}}</div>
                            <div style="margin: 4px 0;"><strong>🔍 Filtros aplicados:</strong> ${{activeFilters.join('; ') || 'Nenhum'}}</div>
                        </div>
                    </div>
                `;
                
                // Inserir cabeçalho no INÍCIO do content (não no body)
                const contentElement = document.getElementById('content');
                if (contentElement && contentElement.firstChild) {{
                    contentElement.insertBefore(headerDiv, contentElement.firstChild);
                }} else {{
                    contentElement.appendChild(headerDiv);
                }}
                
                // Criar estilo de impressão
                const printStyle = document.createElement('style');
                printStyle.id = 'pdf-print-style';
                printStyle.textContent = `
                    @media print {{
                        body {{ margin: 0; padding: 15mm; background: white; font-family: Arial, sans-serif; }}
                        .filters-container {{ display: none !important; }}
                        
                        /* CABEÇALHO - Garantir que apareça */
                        .pdf-header-temp {{ 
                            display: block !important; 
                            visibility: visible !important;
                            position: static !important;
                            margin-bottom: 30px !important;
                            page-break-after: avoid !important;
                            border-bottom: 3px solid #4A90E2 !important;
                            padding-bottom: 20px !important;
                        }}
                        
                        .section {{ margin-bottom: 20px; page-break-inside: avoid; }}
                        .section-title {{ 
                            font-size: 16px; 
                            font-weight: bold; 
                            color: #4A90E2; 
                            margin: 20px 0 10px 0; 
                            border-bottom: 2px solid #4A90E2; 
                            padding-bottom: 5px; 
                        }}
                        table {{ 
                            width: 100%; 
                            border-collapse: collapse; 
                            margin: 10px 0; 
                            font-size: 11px; 
                        }}
                        table th {{ 
                            background: #4A90E2 !important; 
                            color: white !important; 
                            padding: 8px 4px; 
                            text-align: left; 
                            border: 1px solid #357ABD; 
                            -webkit-print-color-adjust: exact; 
                        }}
                        table td {{ 
                            padding: 6px 4px; 
                            border: 1px solid #ddd; 
                            text-align: left; 
                        }}
                        table tr:nth-child(even) td {{ 
                            background: #f8f9fa !important; 
                            -webkit-print-color-adjust: exact; 
                        }}
                        .chart-container {{ 
                            display: none !important;
                        }}
                        canvas {{ display: none !important; }}
                    }}
                `;
                
                document.head.appendChild(printStyle);
                
                // Aguardar um momento
                await new Promise(resolve => setTimeout(resolve, 500));
                
                console.log('🖨️ Abrindo diálogo de impressão...');
                window.print();
                
                // Limpeza após 3 segundos
                setTimeout(() => {{
                    // Remover cabeçalho
                    const header = document.querySelector('.pdf-header-temp');
                    if (header && header.parentNode) {{
                        header.parentNode.removeChild(header);
                    }}
                    
                    // Remover estilos
                    const style = document.getElementById('pdf-print-style');
                    if (style && style.parentNode) {{
                        style.parentNode.removeChild(style);
                    }}
                    
                    console.log('🧹 Limpeza concluída');
                }}, 3000);
                
                // Restaurar botão
                originalBtn.textContent = '📄 PDF';
                originalBtn.disabled = false;
                
                // Mostrar instruções
                setTimeout(() => {{
                    alert(`✅ Relatório em PDF gerado com sucesso!`);
                }}, 800);
                
                console.log('✅ Processo de PDF concluído com sucesso');
                
            }} catch (error) {{
                console.error('❌ Erro na exportação PDF:', error);
                
                // Restaurar botão
                const btn = event.target;
                btn.textContent = '📄 PDF';
                btn.disabled = false;
                
                // Fallback mais simples
                alert(`⚠️ Erro na exportação automática.\\n\\n` +
                      `💡 ALTERNATIVA MANUAL:\\n` +
                      `1. Pressione Ctrl+P (Cmd+P no Mac)\\n` +
                      `2. Escolha "Salvar como PDF"\\n` +
                      `3. Salve o arquivo\\n\\n` +
                      `Erro detalhado: ${{error.message}}`);
            }}
        }}
        
    </script>
</body>
</html>"""

# ========== INTERFACE GRÁFICA CORRIGIDA ==========

def run_gui() -> int:
    """Interface gráfica CORRIGIDA - exportselection=False é a chave"""
    try:
        # 1. SELEÇÃO DO ARQUIVO
        root = tk.Tk()
        root.withdraw()
        
        in_path = filedialog.askopenfilename(
            title="Selecione o arquivo .sav (SPSS)",
            filetypes=[("SPSS files", "*.sav"), ("All files", "*.*")]
        )
        
        if not in_path:
            print("❌ Nenhum arquivo selecionado.")
            return 1
        
        print(f"📂 Carregando: {os.path.basename(in_path)}")
        
        try:
            df, meta = read_sav_auto(in_path)
            fix_labels_in_meta(meta)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar arquivo:\\n{str(e)}")
            return 2
        
        print(f"✅ Arquivo carregado: {len(df)} registros, {len(df.columns)} variáveis")
        
        # Obter labels das variáveis
        labels = {}
        for col in df.columns:
            label = get_var_label(meta, col)
            labels[col] = label if label else ""
        
        # Configurar estilo moderno para componentes ttk
        style = ttk.Style()
        style.theme_use('clam')
        
        # Estilo para combobox
        style.configure("Modern.TCombobox", 
                       fieldbackground="white",
                       background="#f8f9fa",
                       foreground="#2c3e50",
                       borderwidth=1,
                       relief="solid")
        
        # Configurar cores padrão para melhor visibilidade
        style.configure("TLabel", background="#f8f9fa", foreground="#2c3e50")
        style.configure("TFrame", background="#f8f9fa")
        
        # 2. JANELA DE SELEÇÃO - Layout moderno melhorado
        root.deiconify()
        root.title("📊 Dashboard SPSS Universal - Seleção de Variáveis")
        root.geometry("1400x800")
        root.minsize(1200, 700)
        root.configure(bg="#f8f9fa")
        
        # Configurar cores padrão para evitar problemas de sistema
        root.option_add('*TkDefaultFont', 'Segoe UI 10')
        root.option_add('*Background', '#f8f9fa')
        root.option_add('*Foreground', '#2c3e50')
        
        # Configurar grid weights para responsividade
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(0, weight=1)
        
        # Frame principal com melhor padding
        main_frame = tk.Frame(root, bg="#f8f9fa")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=25, pady=20)
        
        # Header melhorado
        header_frame = tk.Frame(main_frame, bg="#f8f9fa")
        header_frame.pack(fill=tk.X, pady=(0, 25))
        
        # Título principal
        title_label = tk.Label(header_frame, 
                              text="📊 Dashboard SPSS Universal", 
                              font=("Segoe UI", 24, "bold"), 
                              fg="#2c3e50", bg="#f8f9fa")
        title_label.pack()
        
        # Subtítulo com informações do arquivo
        subtitle_label = tk.Label(header_frame,
                                 text=f"📁 {os.path.basename(in_path)} • {len(df):,} registros • {len(df.columns)} variáveis",
                                 font=("Segoe UI", 12), 
                                 fg="#7f8c8d", bg="#f8f9fa")
        subtitle_label.pack(pady=(5, 0))
        
        # Container principal para as listas
        content_frame = tk.Frame(main_frame, bg="#f8f9fa")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame para listboxes lado a lado com melhor espaçamento
        lists_frame = tk.Frame(content_frame, bg="#f8f9fa")
        lists_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # VARIÁVEIS PRINCIPAIS (lado esquerdo) - Layout melhorado
        vars_frame = tk.LabelFrame(lists_frame, text="📊 VARIÁVEIS PARA O RELATÓRIO", 
                                  font=("Segoe UI", 14, "bold"), fg="#2980b9", bg="#f8f9fa",
                                  relief="solid", borderwidth=1, padx=15, pady=15)
        vars_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        # Informações melhoradas das variáveis principais
        vars_info = tk.Label(vars_frame, 
                            text="Selecione as variáveis para análise:\n• Ctrl/Cmd + clique: múltiplas seleções\n• Shift + clique: intervalos",
                            font=("Segoe UI", 11), fg="#5d6d7e", bg="#f8f9fa", justify=tk.LEFT)
        vars_info.pack(fill=tk.X, pady=(0, 15))
        
        # Container para listbox e scrollbar
        vars_list_frame = tk.Frame(vars_frame, bg="#f8f9fa")
        vars_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Listbox de variáveis melhorada
        vars_listbox = tk.Listbox(vars_list_frame, selectmode=tk.EXTENDED, 
                                 font=("Consolas", 11), exportselection=False, 
                                 bg='white', fg="#2c3e50",
                                 selectbackground='#3498db', selectforeground='white',
                                 relief="solid", borderwidth=1, highlightthickness=0)
        vars_scrollbar = tk.Scrollbar(vars_list_frame, orient=tk.VERTICAL, command=vars_listbox.yview)
        vars_listbox.config(yscrollcommand=vars_scrollbar.set)
        
        vars_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        vars_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Botões de controle melhorados para variáveis
        vars_buttons_frame = tk.Frame(vars_frame, bg="#f8f9fa")
        vars_buttons_frame.pack(fill=tk.X)
        
        # Botão Selecionar Todas
        select_all_btn = tk.Button(vars_buttons_frame, text="✅ Selecionar Todas", 
                                  command=lambda: vars_listbox.select_set(0, tk.END),
                                  font=("Segoe UI", 10, "bold"), bg="#1e8449", fg="#ffffff",
                                  relief="flat", padx=15, pady=8, cursor="hand2")
        select_all_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Efeitos hover para botão Selecionar Todas
        def on_select_all_enter(e): select_all_btn.configure(bg="#239b56")
        def on_select_all_leave(e): select_all_btn.configure(bg="#1e8449")
        select_all_btn.bind("<Enter>", on_select_all_enter)
        select_all_btn.bind("<Leave>", on_select_all_leave)
        
        # Botão Limpar
        clear_btn = tk.Button(vars_buttons_frame, text="❌ Limpar", 
                             command=lambda: vars_listbox.selection_clear(0, tk.END),
                             font=("Segoe UI", 10, "bold"), bg="#c0392b", fg="#ffffff",
                             relief="flat", padx=15, pady=8, cursor="hand2")
        clear_btn.pack(side=tk.LEFT)
        
        # Efeitos hover para botão Limpar
        def on_clear_enter(e): clear_btn.configure(bg="#a93226")
        def on_clear_leave(e): clear_btn.configure(bg="#c0392b")
        clear_btn.bind("<Enter>", on_clear_enter)
        clear_btn.bind("<Leave>", on_clear_leave)
        
        # FILTROS (lado direito) - Layout melhorado
        filters_frame = tk.LabelFrame(lists_frame, text="🔍 VARIÁVEIS-FILTRO (Opcional)", 
                                     font=("Segoe UI", 14, "bold"), fg="#8e44ad", bg="#f8f9fa",
                                     relief="solid", borderwidth=1, padx=15, pady=15)
        filters_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Informações melhoradas dos filtros
        filters_info = tk.Label(filters_frame, 
                               text="Filtros para segmentação:\n• Opcional (pode deixar vazio)\n• Útil para análises específicas",
                               font=("Segoe UI", 11), fg="#5d6d7e", bg="#f8f9fa", justify=tk.LEFT)
        filters_info.pack(fill=tk.X, pady=(0, 15))
        
        # Container para listbox de filtros
        filters_list_frame = tk.Frame(filters_frame, bg="#f8f9fa")
        filters_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Listbox de filtros melhorada
        filters_listbox = tk.Listbox(filters_list_frame, selectmode=tk.EXTENDED, 
                                    font=("Consolas", 11), exportselection=False,
                                    bg='white', fg="#2c3e50",
                                    selectbackground='#9b59b6', selectforeground='white',
                                    relief="solid", borderwidth=1, highlightthickness=0)
        filters_scrollbar = tk.Scrollbar(filters_list_frame, orient=tk.VERTICAL, command=filters_listbox.yview)
        filters_listbox.config(yscrollcommand=filters_scrollbar.set)
        
        filters_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        filters_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Botões de controle melhorados para filtros
        filters_buttons_frame = tk.Frame(filters_frame, bg="#f8f9fa")
        filters_buttons_frame.pack(fill=tk.X)
        
        # Botão Selecionar Todas (filtros)
        filters_select_all_btn = tk.Button(filters_buttons_frame, text="✅ Selecionar Todas", 
                                          command=lambda: filters_listbox.select_set(0, tk.END),
                                          font=("Segoe UI", 10, "bold"), bg="#1e8449", fg="#ffffff",
                                          relief="flat", padx=15, pady=8, cursor="hand2")
        filters_select_all_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Efeitos hover para botão Selecionar Todas (filtros)
        def on_filters_select_enter(e): filters_select_all_btn.configure(bg="#239b56")
        def on_filters_select_leave(e): filters_select_all_btn.configure(bg="#1e8449")
        filters_select_all_btn.bind("<Enter>", on_filters_select_enter)
        filters_select_all_btn.bind("<Leave>", on_filters_select_leave)
        
        # Botão Limpar (filtros)
        filters_clear_btn = tk.Button(filters_buttons_frame, text="❌ Limpar", 
                                     command=lambda: filters_listbox.selection_clear(0, tk.END),
                                     font=("Segoe UI", 10, "bold"), bg="#c0392b", fg="#ffffff",
                                     relief="flat", padx=15, pady=8, cursor="hand2")
        filters_clear_btn.pack(side=tk.LEFT)
        
        # Efeitos hover para botão Limpar (filtros)
        def on_filters_clear_enter(e): filters_clear_btn.configure(bg="#a93226")
        def on_filters_clear_leave(e): filters_clear_btn.configure(bg="#c0392b")
        filters_clear_btn.bind("<Enter>", on_filters_clear_enter)
        filters_clear_btn.bind("<Leave>", on_filters_clear_leave)
        
        # PESO/PONDERAÇÃO (nova seção melhorada abaixo dos filtros)
        weight_frame = tk.LabelFrame(filters_frame, text="⚖️ VARIÁVEL PESO (Opcional)", 
                                   font=("Segoe UI", 13, "bold"), fg="#e67e22", bg="#f8f9fa",
                                   relief="solid", borderwidth=1, padx=15, pady=10)
        weight_frame.pack(fill=tk.X, pady=(20, 0))
        
        weight_info = tk.Label(weight_frame, 
                             text="Para pesquisas por amostragem:",
                             font=("Segoe UI", 10), fg="#5d6d7e", bg="#f8f9fa")
        weight_info.pack(fill=tk.X, pady=(0, 8))
        
        # Combobox melhorado para seleção de peso
        weight_var = tk.StringVar()
        weight_combo = ttk.Combobox(weight_frame, textvariable=weight_var, 
                                  font=("Segoe UI", 11), state="readonly", width=30,
                                  style="Modern.TCombobox")
        weight_combo.pack(fill=tk.X)
        
        # POPULAR AS LISTAS COM VARIÁVEIS (preservando ordem original do SPSS)
        print(f"🔧 Preservando ordem original das {len(df.columns)} variáveis do SPSS")
        for col in df.columns:  # REMOVIDO sorted() para preservar ordem SPSS
            label_text = labels.get(col, "")
            if label_text:
                display_text = f"{col:<15} | {label_text}"
            else:
                display_text = f"{col:<15} | (sem rótulo)"
            
            vars_listbox.insert(tk.END, display_text)
            filters_listbox.insert(tk.END, display_text)
        
        # Popular combobox de peso apenas com variáveis numéricas candidatas
        weight_candidates = ["(Nenhuma - sem ponderação)"]
        for col in df.columns:
            # Detectar se é variável numérica (candidata a peso)
            if col.lower() in ['peso', 'weight', 'pond', 'ponderacao', 'factor', 'wgt']:
                weight_candidates.append(f"{col} | {labels.get(col, '(peso)')}")
            elif df[col].dtype in ['int64', 'float64'] or pd.api.types.is_numeric_dtype(df[col]):
                # Verificar se parece com peso (valores entre 0.1 e 10, média próxima de 1)
                numeric_vals = pd.to_numeric(df[col], errors='coerce').dropna()
                if len(numeric_vals) > 0:
                    mean_val = numeric_vals.mean()
                    min_val = numeric_vals.min()
                    max_val = numeric_vals.max()
                    if 0.1 <= min_val and max_val <= 20 and 0.5 <= mean_val <= 3.0:
                        weight_candidates.append(f"{col} | {labels.get(col, '(numérica)')}")
        
        weight_combo['values'] = weight_candidates
        weight_combo.current(0)  # Seleciona "Nenhuma" por padrão
        
        # Variáveis para armazenar seleções
        selected_vars = []
        selected_filters = []
        selected_weight = None
        success = False
        
        def on_generate():
            nonlocal selected_vars, selected_filters, selected_weight, success
            
            # Obter seleções
            var_indices = vars_listbox.curselection()
            filter_indices = filters_listbox.curselection()
            
            if not var_indices:
                messagebox.showwarning("Atenção", "Selecione pelo menos uma variável para o relatório!")
                return
            
            # Preservar ordem original do SPSS (REMOVIDO sorted())
            columns_list = list(df.columns)  # Ordem original preservada
            selected_vars = [columns_list[i] for i in var_indices]
            selected_filters = [columns_list[i] for i in filter_indices]
            
            # Obter variável peso selecionada
            weight_selection = weight_var.get()
            if weight_selection and not weight_selection.startswith("(Nenhuma"):
                # Extrair nome da variável do formato "PESO | descrição"
                selected_weight = weight_selection.split(" | ")[0]
                if selected_weight not in df.columns:
                    selected_weight = None
            else:
                selected_weight = None
            
            success = True
            root.quit()
        
        def on_cancel():
            nonlocal success
            success = False
            root.quit()
        
        # BOTÕES FINAIS - Layout moderno
        buttons_section = tk.Frame(main_frame, bg="#f8f9fa")
        buttons_section.pack(fill=tk.X, pady=(30, 0))
        
        # Frame para centralizar botões
        buttons_frame = tk.Frame(buttons_section, bg="#f8f9fa")
        buttons_frame.pack(anchor=tk.CENTER)
        
        # Botão Cancelar melhorado
        cancel_btn = tk.Button(buttons_frame, text="❌ Cancelar", command=on_cancel, 
                              font=("Segoe UI", 12, "bold"), width=15, 
                              bg="#bdc3c7", fg="#2c3e50", relief="flat",
                              padx=20, pady=12, cursor="hand2")
        cancel_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        # Efeitos hover para botão Cancelar
        def on_cancel_enter(e): cancel_btn.configure(bg="#95a5a6")
        def on_cancel_leave(e): cancel_btn.configure(bg="#bdc3c7")
        cancel_btn.bind("<Enter>", on_cancel_enter)
        cancel_btn.bind("<Leave>", on_cancel_leave)
        
        # Botão Gerar melhorado
        generate_btn = tk.Button(buttons_frame, text="🚀 Gerar Dashboard", command=on_generate, 
                                font=("Segoe UI", 12, "bold"), width=20, 
                                bg="#1e8449", fg="#ffffff", relief="flat",
                                padx=25, pady=12, cursor="hand2")
        generate_btn.pack(side=tk.RIGHT)
        
        # Efeitos hover para botão Gerar
        def on_generate_enter(e): generate_btn.configure(bg="#239b56")
        def on_generate_leave(e): generate_btn.configure(bg="#1e8449")
        generate_btn.bind("<Enter>", on_generate_enter)
        generate_btn.bind("<Leave>", on_generate_leave)
        
        # Instruções melhoradas
        instructions_frame = tk.Frame(main_frame, bg="#f8f9fa")
        instructions_frame.pack(fill=tk.X, pady=(20, 10))
        
        instructions_title = tk.Label(instructions_frame, 
                                     text="💡 INSTRUÇÕES DE USO",
                                     font=("Segoe UI", 12, "bold"), 
                                     fg="#34495e", bg="#f8f9fa")
        instructions_title.pack(anchor=tk.W)
        
        instructions_text = tk.Label(instructions_frame, 
                                    text="• Clique simples: seleciona um item\n"
                                         "• Ctrl/Cmd + clique: múltiplas seleções\n"
                                         "• Shift + clique: seleciona intervalo\n"
                                         "• Use os botões para facilitar a seleção", 
                                    font=("Segoe UI", 10), fg="#7f8c8d", bg="#f8f9fa", 
                                    justify=tk.LEFT)
        instructions_text.pack(anchor=tk.W, pady=(5, 0))
        
        # Executar interface
        root.mainloop()
        
        if not success:
            root.destroy()
            print("❌ Operação cancelada.")
            return 1
        
        print(f"✅ Variáveis selecionadas: {len(selected_vars)} - {selected_vars[:3]}{'...' if len(selected_vars) > 3 else ''}")
        print(f"✅ Filtros selecionados: {len(selected_filters)} - {selected_filters[:3] if selected_filters else 'Nenhum'}")
        
        # DEBUG: Mostrar detalhes das variáveis selecionadas
        print("\n🔍 === DEBUG: VARIÁVEIS SELECIONADAS ===")
        mr_candidates = []
        single_vars = []
        
        for var in selected_vars:
            if "_" in var and re.match(r'^[A-Za-z]+\d+_\d+', var):
                mr_candidates.append(var)
            else:
                single_vars.append(var)
        
        print(f"📊 Variáveis com padrão MR: {len(mr_candidates)}")
        if mr_candidates:
            for var in mr_candidates[:10]:
                print(f"   • {var}")
            if len(mr_candidates) > 10:
                print(f"   ... e mais {len(mr_candidates) - 10}")
        
        print(f"📋 Variáveis individuais: {len(single_vars)}")
        if single_vars:
            for var in single_vars[:10]:
                print(f"   • {var}")
            if len(single_vars) > 10:
                print(f"   ... e mais {len(single_vars) - 10}")
        print()
        
        root.destroy()
        
        # 3. ARQUIVO DE SAÍDA
        root2 = tk.Tk()
        root2.withdraw()
        
        default_out = os.path.splitext(in_path)[0] + "_dashboard_universal.html"
        out_path = filedialog.asksaveasfilename(
            title="Salvar dashboard HTML como...",
            defaultextension=".html", 
            initialfile=os.path.basename(default_out),
            filetypes=[("HTML", "*.html")]
        ) or default_out
        
        root2.destroy()

        # 4. PROCESSAMENTO
        print("⚙️ Processando dados...")
        created_at, vars_meta, filters_meta, records, value_orders, code_to_label = build_records_and_meta(
            df, meta, selected_vars, selected_filters, os.path.basename(in_path), "", selected_weight
        )

        print("🎨 Gerando HTML universal...")
        html = render_html_with_working_filters(
            os.path.basename(in_path), created_at, "",
            vars_meta, filters_meta, records, value_orders, code_to_label
        )
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

        # 5. RESULTADO
        mr_found = [v for v in vars_meta if v["type"] == "mr"]
        string_found = [v for v in vars_meta if v["type"] == "string"]
        
        result_msg = f"""✅ Dashboard criado com sucesso!

• Registros: {len(records)}
• Variáveis analisadas: {len(vars_meta)}
• Filtros: {len(filters_meta)}
• Arquivo gerado: {os.path.basename(out_path)}
"""
        
        # Informar sobre ponderação
        if selected_weight:
            result_msg += f"⚖️ Ponderação aplicada: {selected_weight}\\n"
        
        # Adiciona informações resumidas sobre tipos especiais de variáveis
        special_vars = []
        mr_count = len([v for v in vars_meta if v["type"] == "mr"])
        string_count = len([v for v in vars_meta if v["type"] == "string"])
        
        if string_count > 0:
            special_vars.append(f"🟣 {string_count} Respostas Abertas")
        if mr_count > 0:
            special_vars.append(f"🟠 {mr_count} Respostas Múltiplas")
            
        if special_vars:
            result_msg += f"\n{' | '.join(special_vars)}"

        root3 = tk.Tk()
        root3.withdraw()
        messagebox.showinfo("Dashboard Universal - Concluído", result_msg)
        root3.destroy()
        return 0

    except Exception as e:
        try:
            messagebox.showerror("Erro", f"Erro inesperado:\\n\\n{str(e)}")
        except Exception:
            print(f"Erro: {e}", file=sys.stderr)
        finally:
            try: 
                root.destroy()
            except Exception: 
                pass
        return 4

# ========== LINHA DE COMANDO ==========

def run_cli() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Dashboard SPSS Universal")
    p.add_argument("input", help="Caminho do arquivo .sav")
    p.add_argument("--vars", type=str, required=True, help="Variáveis do relatório separadas por vírgula")
    p.add_argument("--filters", type=str, default="", help="Variáveis-filtro separadas por vírgula")
    p.add_argument("--cliente", type=str, default="", help="Nome do cliente para o título")
    p.add_argument("-o", "--output", default=None, help="HTML de saída")
    args = p.parse_args()

    try:
        df, meta = read_sav_auto(args.input)
        fix_labels_in_meta(meta)
        
        selected_vars = [v.strip() for v in args.vars.split(",") if v.strip()]
        filter_vars = [v.strip() for v in args.filters.split(",") if v.strip()] if args.filters else []
        
        out_path = args.output or os.path.splitext(args.input)[0] + "_dashboard_universal.html"
        
        created_at, vars_meta, filters_meta, records, value_orders, code_to_label = build_records_and_meta(
            df, meta, selected_vars, filter_vars, os.path.basename(args.input), args.cliente, None
        )

        html = render_html_with_working_filters(
            os.path.basename(args.input), created_at, args.cliente,
            vars_meta, filters_meta, records, value_orders, code_to_label
        )
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        
        print(f"✅ Dashboard universal criado: {out_path}")
        return 0
        
    except Exception as e:
        print(f"❌ Erro: {e}", file=sys.stderr)
        return 1

# ========== MAIN ==========

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        sys.exit(run_cli())
    else:
        sys.exit(run_gui())
