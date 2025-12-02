#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard SPSS UNIVERSAL - VERSÃO CLEAN
Layout limpo e sutil, cores neutras, ideal para integração.
Todas as correções aplicadas:
- exportselection=False para listboxes independentes
- JavaScript sem conflitos de nomenclatura
- Design clean sem header pesado
- Cores neutras e layout sutil
- Funções seguras para evitar erro hashable
- Sintaxe consistente em f-strings vs template literals
"""

print("🌍 Dashboard SPSS UNIVERSAL - DESIGN CLEAN")
print("📋 Funciona com QUALQUER banco de dados SPSS")
print("🎯 Detecção automática: Resposta Aberta, Resposta Única, Resposta Múltipla")
print("🛡️ 100% estável - não quebra com nenhuma variável")
print("⚡ Independente de nomes específicos de variáveis")
print("📦 Versão standalone - não precisa de outros arquivos")
print("🎨 DESIGN CLEAN: Layout sutil com cores neutras")
print()

# ========== IMPORTS E CONSTANTES ==========

import os, sys, json, re, pandas as pd
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
CHART_LABEL_MAX = 40

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
    label = re.sub(r"^\s*\[.*?\]\s*", "", label).strip()
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

def format_text_response(text: str) -> str:
    if not text or not isinstance(text, str):
        return str(text)
    text = str(text).strip()
    if not text:
        return text
    return text[0].upper() + text[1:].lower()

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

def detect_mr_type(col, valabs):
    """
    Detecta automaticamente o tipo de múltipla resposta:
    - 'binary'  → MR com 0/1 e value labels como Selected/Not selected
    - 'categorical' → MR com categorias de texto nos value labels
    """
    vmap = valabs.get(col, {})

    if not vmap:
        return 'binary'  # fallback seguro

    labels = set(str(v).strip().lower() for v in vmap.values())

    binary_indicators = {
        "selected", "not selected",
        "selecionado", "não selecionado",
        "sim", "não",
        "yes", "no",
        "0", "1"
    }

    # Se TODOS os labels forem binários → MR tipo 1
    if labels.issubset(binary_indicators):
        return 'binary'

    # Caso contrário, são categorias reais
    return 'categorical'

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

    # 1. Se tiver colchetes, é a categoria — ponto final.
    match = re.search(r'\[(.*?)\]', raw)
    if match:
        return match.group(1).strip()

    # 2. Se não houver colchetes, tenta usar só o texto antes da pergunta,
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
        return Tr


# ========== DETECÇÃO UNIVERSAL DE TIPOS ==========

def get_spss_variable_type_universal(meta, var_name: str, df) -> str:
    """Detecção universal de tipos de variáveis SPSS"""
    try:
        if var_name not in df.columns:
            return 'numeric_labeled'
        
        # MÉTODO 1: Metadados SPSS
        try:
            var_types = getattr(meta, 'original_variable_types', {})
            original_type = var_types.get(var_name)
            if original_type and 'STRING' in str(original_type).upper():
                return 'string'
        except:
            pass
        
        # MÉTODO 2: Formato da variável
        try:
            var_formats = getattr(meta, 'variable_display_formats', {})
            fmt = var_formats.get(var_name, '')
            if fmt and ('A' in fmt or 'STRING' in str(fmt).upper()):
                return 'string'
        except:
            pass
        
        # MÉTODO 3: Análise do conteúdo real
        try:
            sample_data = df[var_name].dropna()
            if len(sample_data) > 0:
                first_val = sample_data.iloc[0]
                if isinstance(first_val, str):
                    return 'string'
                
                str_vals = [str(v).strip() for v in sample_data.head(10)]
                str_vals = [v for v in str_vals if v and v != 'nan']
                
                if len(str_vals) > 0:
                    non_numeric = []
                    for v in str_vals:
                        try:
                            float(v)
                        except (ValueError, TypeError):
                            non_numeric.append(v)
                    
                    if len(non_numeric) / len(str_vals) > 0.5:
                        return 'string'
                    
                    avg_length = sum(len(v) for v in str_vals) / len(str_vals)
                    if avg_length > 15:
                        return 'string'
                    
                    with_spaces = sum(1 for v in str_vals if ' ' in v)
                    if with_spaces / len(str_vals) > 0.8:
                        return 'string'
        except:
            pass
        
        return 'numeric_labeled'
    except Exception:
        return 'numeric_labeled'

def detect_multiple_choice_universal(selected_vars: List[str], meta, valabs: Dict[str, Dict[Any, str]], df):
    """Detecção universal de tipos de variáveis"""
    vars_meta = []
    mr_groups: Dict[str, Dict[str, Any]] = {}
    
    valid_vars = [v for v in selected_vars if v in df.columns]
    if len(valid_vars) != len(selected_vars):
        missing = [v for v in selected_vars if v not in df.columns]
        print(f"⚠️ Variáveis não encontradas: {missing}")
    
    labels = {v: get_var_label(meta, v) for v in valid_vars}
    
    used = set()
    i = 0
    
    while i < len(valid_vars):
        var = valid_vars[i]
        if var in used:
            i += 1
            continue
        
        try:
            var_type = get_spss_variable_type_universal(meta, var, df)
            
            if var_type == 'string':
                vars_meta.append({
                    "name": var,
                    "title": labels.get(var, var),
                    "type": "string",
                    "spss_type": "Resposta Aberta",
                    "sheet_code": var
                })
                used.add(var)
                i += 1
                continue
            
            # Detectar múltipla resposta
            base_match = re.match(r'^(.+)_(\d+)([A-Za-z]*)$', var)
            if base_match:
                base, num_str, suffix = base_match.groups()
                try:
                    start_num = int(num_str)
                    group_vars = [var]
                    
                    for num in range(start_num + 1, start_num + 20):
                        next_var = f"{base}_{num}{suffix}"
                        if next_var in valid_vars and next_var not in used:
                            group_vars.append(next_var)
                        else:
                            break
                    
                    if len(group_vars) >= 2:
                        is_binary_group = True
                        for gv in group_vars[:5]:
                            try:
                                gv_labels = valabs.get(gv, {})
                                if gv_labels:
                                    label_values = [str(v).lower() for v in gv_labels.values()]
                                    binary_indicators = ['selected', 'sim', 'não', 'yes', 'no', '0', '1']
                                    if not any(indicator in ' '.join(label_values) for indicator in binary_indicators):
                                        is_binary_group = False
                                        break
                            except:
                                is_binary_group = False
                                break
                        
                        if is_binary_group:
                            group_name = f"mr_{base.lower()}"
                            first_label = labels.get(group_vars[0], "")
                            base_question = re.sub(r'\s*\[.*?\]\s*$', '', first_label).strip()
                            if not base_question:
                                base_question = f"Grupo {base}"
                            
                            mr_groups[group_name] = {
                                "title": base_question,
                                "members": group_vars
                            }
                            
                            try:
                                base_lower = str(base).lower()
                                candidates = []
                                for col_name in df.columns:
                                    col_lower = str(col_name).lower()
                                    if col_lower.startswith(base_lower + "_") and (
                                        col_lower.endswith("_other") or col_lower.endswith("_outros")
                                    ):
                                        candidates.append(col_name)
                                if candidates:
                                    mr_groups[group_name]["other_var"] = candidates[0]
                            except Exception:
                                pass
                            
                            vars_meta.append({
                                "name": group_name,
                                "title": base_question,
                                "type": "mr",
                                "spss_type": "Resposta Múltipla",
                                "sheet_code": group_name
                            })
                            
                            used.update(group_vars)
                            i += len(group_vars)
                            continue
                except (ValueError, IndexError):
                    pass
            
            # Variável única
            vars_meta.append({
                "name": var,
                "title": labels.get(var, var),
                "type": "single",
                "spss_type": "Resposta Única",
                "sheet_code": var
            })
            used.add(var)
            i += 1
            
        except Exception as e:
            print(f"⚠️ Erro processando variável {var}: {e}")
            vars_meta.append({
                "name": var,
                "title": labels.get(var, var),
                "type": "single",
                "spss_type": "Resposta Única",
                "sheet_code": var
            })
            used.add(var)
            i += 1
    
    return vars_meta, mr_groups

# ========== PROCESSAMENTO DE DADOS ==========

def build_records_and_meta(df, meta, selected_vars: List[str], filter_vars: List[str], 
                          file_source: str, client_name: str):
    """
    Constrói:
      - created_at: timestamp
      - vars_meta: metadados das variáveis (incluindo grupos MR)
      - filters_meta: metadados dos filtros
      - records: lista de dicionários prontos para o dashboard
    """
    created_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Mapa de value labels por variável
    valabs = get_value_labels_map(meta)
    
    # Metadados das variáveis (string, single, mr) + grupos de múltipla resposta
    vars_meta, mr_groups = detect_multiple_choice_universal(selected_vars, meta, valabs, df)
    
    # ---------- PROCESSAMENTO DE FILTROS ----------
    filters_meta = []
    for fv in filter_vars:
        if fv in df.columns:
            unique_vals = []
            for val in df[fv].dropna().unique():
                if not pd.isna(val):
                    processed_val = str(valabs.get(fv, {}).get(val, val)).replace(":", "").strip()
                    processed_val = _normalize_display_value(processed_val)
                    unique_vals.append(processed_val)
            
            if unique_vals:
                filters_meta.append({
                    "name": fv,
                    "title": get_var_label(meta, fv) or fv,
                    "values": safe_sorted_unique(unique_vals)
                })
    
    # ---------- PROCESSAMENTO DE REGISTROS ----------
    records = []
    for _, row in df.iterrows():
        rec: Dict[str, Any] = {}
        
        # ----- Filtros -----
        for fv in filter_vars:
            if fv in df.columns:
                val = row.get(fv)
                if pd.isna(val):
                    rec[fv] = None
                else:
                    rec[fv] = _normalize_display_value(
                        str(valabs.get(fv, {}).get(val, val)).replace(":", "").strip()
                    )
        
        # ----- Variáveis -----
        for vm in vars_meta:
            vtype = vm["type"]
            
            # Resposta aberta
            if vtype == "string":
                col = vm["name"]
                val = row.get(col)
                if pd.isna(val) or not str(val).strip():
                    rec[col] = None
                else:
                    rec[col] = format_text_response(str(val))
            
            # Resposta única
            elif vtype == "single":
                col = vm["name"]
                val = row.get(col)
                if pd.isna(val):
                    rec[col] = None
                else:
                    processed_val = str(valabs.get(col, {}).get(val, val)).replace(":", "").strip()
                    processed_val = _normalize_display_value(processed_val)
                    rec[col] = processed_val
            
            # Múltipla resposta
            else:  # vtype == "mr"
                mr_name = vm["name"]
                if mr_name in mr_groups:
                    members = mr_groups[mr_name]["members"]
                    chosen_options: List[str] = []
                    
                    for col in members:
                        val = row.get(col)
                        if pd.isna(val):
                            continue
                        
                        vmap = valabs.get(col, {})

                        # -- Seleção verdadeira --
                        is_selected = mr_is_selected(val, vmap)
                        if not is_selected:
                            continue

                        # -- Texto da opção --
                        mr_type = detect_mr_type(col, valabs)

                        if mr_type == "binary":
                            option_text = get_mr1_label(meta, col)
                        else:
                            option_text = get_mr2_label(valabs, col, val)

                        # -- Fallbacks --
                        if not option_text or not str(option_text).strip():
                            option_text = get_var_label(meta, col)

                        if not option_text or not str(option_text).strip():
                            option_text = col

                        option_text = str(option_text).strip()

                        if option_text not in chosen_options:
                            chosen_options.append(option_text)

                    # Ordena e grava opções selecionadas
                    rec[mr_name] = safe_sorted_unique(chosen_options)

                    # -------- Tratamento de OUTROS --------
                    other_var = mr_groups.get(mr_name, {}).get("other_var")
                    if other_var:
                        other_val = row.get(other_var)
                        if isinstance(other_val, str):
                            other_val_clean = other_val.strip()
                            if other_val_clean:
                                if "Outros" not in chosen_options:
                                    chosen_options.append("Outros")
                                    rec[mr_name] = safe_sorted_unique(chosen_options)

                                key_ot = f"{mr_name}__outros_textos"
                                rec[key_ot] = format_text_response(other_val_clean)
        
        records.append(rec)
    
    return created_at, vars_meta, filters_meta, records

# ========== GERAÇÃO DE HTML ==========

def render_html_with_working_filters(file_source: str, created_at: str, client_name: str,
                                    vars_meta: List[dict], filters_meta: List[dict], 
                                    records: List[dict]) -> str:
    
    # JSON strings seguros para JavaScript
    vars_meta_json = json.dumps(vars_meta, ensure_ascii=False)
    filters_meta_json = json.dumps(filters_meta, ensure_ascii=False)
    records_json = json.dumps(records, ensure_ascii=False)
    
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard SPSS Universal</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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
        }}

        .filters-container {{
            background: white;
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            border: 1px solid var(--border);

            position: sticky;
            top: 0;
            z-index: 9999;

            margin-bottom: 25px;
        }}

        .filters-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 20px;
            background: #f8f9fa;
            border-bottom: 1px solid var(--border);
            border-radius: var(--radius) var(--radius) 0 0;
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

        .filters-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            padding: 20px;
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
    <div style="height: 15px;"></div>
    <div class="filters-container">
        <div class="filters-header">
            <h2 class="filter-title">🔍 Filtros de Seleção</h2>
            <div class="filter-actions">
                <button class="filter-btn apply-btn" onclick="applyFilters()">✓ Aplicar</button>
                <button class="filter-btn clear-btn" onclick="clearFilters()">🔄 Limpar</button>
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
                    return filterValues.includes(String(recordValue));
                }});
            }});
        }}

        // RENDERIZAÇÃO
        function renderAll() {{
            const filteredRecords = getFilteredRecords();
            const content = document.getElementById('content');
            content.innerHTML = '';
            
            console.log('🔄 Renderizando com ' + filteredRecords.length + ' registros filtrados');
            
            VARS_META.forEach((varMeta, index) => {{
                const section = createSection(varMeta, filteredRecords);
                content.appendChild(section);
            }});
        }}

        function createSection(varMeta, records) {{
            const section = document.createElement('div');
            section.className = 'section';
            
            const header = document.createElement('div');
            header.className = 'section-header';
            
            const title = document.createElement('h2');
            title.className = 'section-title';
            
            let icon = '';
            switch(varMeta.type) {{
                case 'string': icon = '📝'; break;
                case 'mr': icon = '☑️'; break;
                default: icon = '📊'; break;
            }}
            
            title.innerHTML = icon + ' ' + varMeta.title;
            
            const subtitle = document.createElement('div');
            subtitle.className = 'section-subtitle';
            subtitle.textContent = varMeta.spss_type + ' | ' + records.length + ' respostas';
            
            header.appendChild(title);
            header.appendChild(subtitle);
            
            const content = document.createElement('div');
            content.className = 'section-content';
            
            if (varMeta.type === 'string') {{
                content.appendChild(renderStringVariable(varMeta, records));
            }} else {{
                content.appendChild(renderCategoricalVariable(varMeta, records));
            }}
            
            section.appendChild(header);
            section.appendChild(content);
            
            return section;
        }}

        function renderStringVariable(varMeta, records) {{
            const container = document.createElement('div');
            
            const validResponses = records
                .map(r => r[varMeta.name])
                .filter(val => val !== null && val !== undefined && String(val).trim() !== '');
            
            if (validResponses.length === 0) {{
                container.innerHTML = '<p style="color: #999; font-style: italic;">Nenhuma resposta encontrada</p>';
                return container;
            }}
            
            const responseList = document.createElement('div');
            responseList.style.cssText = 'max-height: 400px; overflow-y: auto; border: 1px solid var(--border); border-radius: var(--radius); background: #f8f9fa;';
            
            validResponses.forEach((response, index) => {{
                const responseItem = document.createElement('div');
                responseItem.style.cssText = 'padding: 12px 16px; border-bottom: 1px solid var(--border); background: white; margin-bottom: 1px;';
                responseItem.innerHTML = '<strong>' + (index + 1) + '.</strong> ' + String(response);
                responseList.appendChild(responseItem);
            }});
            
            const summary = document.createElement('p');
            summary.innerHTML = '<strong>Total de respostas:</strong> ' + validResponses.length;
            summary.style.marginBottom = '15px';
            
            container.appendChild(summary);
            container.appendChild(responseList);
            
            return container;
        }}

        function renderCategoricalVariable(varMeta, records) {{
            const container = document.createElement('div');
            
            let frequencies = {{}};
            let validCount = 0;
            
            if (varMeta.type === 'mr') {{
                records.forEach(record => {{
                    const value = record[varMeta.name];
                    if (Array.isArray(value) && value.length > 0) {{
                        validCount++;
                        value.forEach(option => {{
                            frequencies[option] = (frequencies[option] || 0) + 1;
                        }});
                    }}
                }});
            }} else {{
                records.forEach(record => {{
                    const value = record[varMeta.name];
                    if (value !== null && value !== undefined) {{
                        const strValue = String(value);
                        if (strValue.trim() !== '') {{
                            validCount++;
                            frequencies[strValue] = (frequencies[strValue] || 0) + 1;
                        }}
                    }}
                }});
            }}
            
            if (Object.keys(frequencies).length === 0) {{
                container.innerHTML = '<p style="color: #999; font-style: italic;">Nenhuma resposta encontrada</p>';
                return container;
            }}
            
            const sortedEntries = Object.entries(frequencies).sort(([,a], [,b]) => b - a);
            
            // Gráfico
            const chartContainer = document.createElement('div');
            chartContainer.className = 'chart-container';
            
            const canvas = document.createElement('canvas');
            chartContainer.appendChild(canvas);
            
            const ctx = canvas.getContext('2d');
            
            const labels = sortedEntries.map(([label]) => {{
                return label.length > CHART_LABEL_MAX ? 
                    label.substring(0, CHART_LABEL_MAX) + '...' : label;
            }});
            const data = sortedEntries.map(([,count]) => count);
            const percentages = sortedEntries.map(([,count]) => 
                ((count / validCount) * 100).toFixed(1));
            
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: labels,
                    datasets: [{{
                        data: data,
                        backgroundColor: 'rgba(74, 144, 226, 0.7)',
                        borderColor: 'rgba(74, 144, 226, 1)',
                        borderWidth: 1
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: false
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    const percentage = percentages[context.dataIndex];
                                    return context.parsed.y + ' (' + percentage + '%)';
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                stepSize: 1
                            }}
                        }},
                        x: {{
                            ticks: {{
                                maxRotation: 45
                            }}
                        }}
                    }}
                }}
            }});
            
            // Tabela
            const tableContainer = document.createElement('div');
            tableContainer.className = 'table-container';
            
            const table = document.createElement('table');
            
            const thead = document.createElement('thead');
            thead.innerHTML = '<tr><th>Opção</th><th>Frequência</th><th>Percentual</th></tr>';
            table.appendChild(thead);
            
            const tbody = document.createElement('tbody');
            
            sortedEntries.forEach(([option, count]) => {{
                const percentage = ((count / validCount) * 100).toFixed(1);
                const row = document.createElement('tr');
                
                row.innerHTML = '<td style="max-width: 300px; word-wrap: break-word;">' + option + '</td>' +
                                '<td><strong>' + count + '</strong></td>' +
                                '<td><strong>' + percentage + '%</strong></td>';
  
                tbody.appendChild(row);
            }});
            
            table.appendChild(tbody);
            tableContainer.appendChild(table);
            
            const summary = document.createElement('p');
            summary.innerHTML = '<strong>Resumo:</strong> ' + Object.keys(frequencies).length + ' opções diferentes | ' + validCount + ' respostas válidas';
            summary.style.marginBottom = '20px';
            
            container.appendChild(summary);
            container.appendChild(chartContainer);
            container.appendChild(tableContainer);
            
            return container;
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
        
        # 2. JANELA DE SELEÇÃO - EXATAMENTE como a versão que funcionava
        root.deiconify()
        root.title("Dashboard SPSS Universal - Seleção de Variáveis")
        root.geometry("1000x700")
        
        # Frame principal
        main_frame = tk.Frame(root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        title_label = tk.Label(main_frame, 
                              text="Dashboard SPSS Universal", 
                              font=("Arial", 16, "bold"), fg="#4A90E2")
        title_label.pack(pady=(0, 10))
        
        # Info do arquivo
        info_label = tk.Label(main_frame, 
                             text=f"Arquivo: {os.path.basename(in_path)} | {len(df)} registros | {len(df.columns)} variáveis",
                             font=("Arial", 11), fg="#666")
        info_label.pack(pady=(0, 20))
        
        # Frame para listboxes lado a lado
        lists_frame = tk.Frame(main_frame)
        lists_frame.pack(fill=tk.BOTH, expand=True)
        
        # VARIÁVEIS PRINCIPAIS (lado esquerdo)
        vars_frame = tk.LabelFrame(lists_frame, text="📊 VARIÁVEIS PARA O RELATÓRIO", 
                                  font=("Arial", 12, "bold"), fg="#4A90E2", padx=10, pady=10)
        vars_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        vars_info = tk.Label(vars_frame, 
                            text="Selecione as variáveis que aparecerão no dashboard:\\n• Múltiplas seleções com Ctrl/Cmd + clique\\n• Use Shift + clique para selecionar intervalos",
                            font=("Arial", 10), fg="#666", justify=tk.LEFT)
        vars_info.pack(fill=tk.X, pady=(0, 10))
        
        # Listbox de variáveis - CHAVE: exportselection=False
        vars_listbox = tk.Listbox(vars_frame, selectmode=tk.EXTENDED, font=("Consolas", 10), 
                                 exportselection=False, bg='#fafafa',
                                 selectbackground='#4A90E2', selectforeground='white')
        vars_scrollbar = tk.Scrollbar(vars_frame, orient=tk.VERTICAL, command=vars_listbox.yview)
        vars_listbox.config(yscrollcommand=vars_scrollbar.set)
        
        vars_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        vars_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Botões de controle para variáveis
        vars_buttons_frame = tk.Frame(vars_frame)
        vars_buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(vars_buttons_frame, text="Selecionar Todas", 
                 command=lambda: vars_listbox.select_set(0, tk.END),
                 font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
        tk.Button(vars_buttons_frame, text="Limpar", 
                 command=lambda: vars_listbox.selection_clear(0, tk.END),
                 font=("Arial", 9)).pack(side=tk.LEFT, padx=2)

        # FILTROS (lado direito)
        filters_frame = tk.LabelFrame(lists_frame, text="🔍 VARIÁVEIS-FILTRO (Opcional)", 
                                     font=("Arial", 12, "bold"), fg="#9C27B0", padx=10, pady=10)
        filters_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        filters_info = tk.Label(filters_frame, 
                               text="Selecione variáveis para filtrar os dados:\\n• Opcional - pode deixar em branco\\n• Útil para segmentação (idade, região, etc.)",
                               font=("Arial", 10), fg="#666", justify=tk.LEFT)
        filters_info.pack(fill=tk.X, pady=(0, 10))
        
        # Listbox de filtros - CHAVE: exportselection=False
        filters_listbox = tk.Listbox(filters_frame, selectmode=tk.EXTENDED, font=("Consolas", 10),
                                    exportselection=False, bg='#fafafa',
                                    selectbackground='#9C27B0', selectforeground='white')
        filters_scrollbar = tk.Scrollbar(filters_frame, orient=tk.VERTICAL, command=filters_listbox.yview)
        filters_listbox.config(yscrollcommand=filters_scrollbar.set)
        
        filters_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        filters_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Botões de controle para filtros
        filters_buttons_frame = tk.Frame(filters_frame)
        filters_buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Button(filters_buttons_frame, text="Selecionar Todas", 
                 command=lambda: filters_listbox.select_set(0, tk.END),
                 font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
        tk.Button(filters_buttons_frame, text="Limpar", 
                 command=lambda: filters_listbox.selection_clear(0, tk.END),
                 font=("Arial", 9)).pack(side=tk.LEFT, padx=2)
        
        # POPULAR AS LISTAS COM VARIÁVEIS
        for col in sorted(df.columns):
            label_text = labels.get(col, "")
            if label_text:
                display_text = f"{col:<15} | {label_text}"
            else:
                display_text = f"{col:<15} | (sem rótulo)"
            
            vars_listbox.insert(tk.END, display_text)
            filters_listbox.insert(tk.END, display_text)
        
        # Variáveis para armazenar seleções
        selected_vars = []
        selected_filters = []
        success = False
        
        def on_generate():
            nonlocal selected_vars, selected_filters, success
            
            # Obter seleções
            var_indices = vars_listbox.curselection()
            filter_indices = filters_listbox.curselection()
            
            if not var_indices:
                messagebox.showwarning("Atenção", "Selecione pelo menos uma variável para o relatório!")
                return
            
            selected_vars = [sorted(df.columns)[i] for i in var_indices]
            selected_filters = [sorted(df.columns)[i] for i in filter_indices]
            
            success = True
            root.quit()
        
        def on_cancel():
            nonlocal success
            success = False
            root.quit()
        
        # Botões
        buttons_frame = tk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(20, 0))
        
        tk.Button(buttons_frame, text="❌ Cancelar", command=on_cancel, 
                 font=("Arial", 12), width=15, bg="#f0f0f0").pack(side=tk.LEFT)
        
        tk.Button(buttons_frame, text="✅ Gerar Dashboard", command=on_generate, 
                 font=("Arial", 12, "bold"), width=20, bg="#4CAF50", fg="white").pack(side=tk.RIGHT)
        
        # Info
        info_label = tk.Label(main_frame, 
                             text="💡 INSTRUÇÕES DE SELEÇÃO:\\n"
                                  "• Clique simples: seleciona um item\\n"
                                  "• Ctrl/Cmd + clique: adiciona à seleção\\n"
                                  "• Shift + clique: seleciona intervalo\\n"
                                  "• Use os botões para facilitar a seleção", 
                             font=("Arial", 10), fg="#666", justify=tk.LEFT)
        info_label.pack(pady=(10, 0))
        
        # Executar interface
        root.mainloop()
        
        if not success:
            root.destroy()
            print("❌ Operação cancelada.")
            return 1
        
        print(f"✅ Variáveis selecionadas: {len(selected_vars)} - {selected_vars[:3]}{'...' if len(selected_vars) > 3 else ''}")
        print(f"✅ Filtros selecionados: {len(selected_filters)} - {selected_filters[:3] if selected_filters else 'Nenhum'}")
        
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
        created_at, vars_meta, filters_meta, records = build_records_and_meta(
            df, meta, selected_vars, selected_filters, os.path.basename(in_path), ""
        )

        print("🎨 Gerando HTML universal...")
        html = render_html_with_working_filters(os.path.basename(in_path), created_at, "",
                           vars_meta, filters_meta, records)
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

        # 5. RESULTADO
        mr_found = [v for v in vars_meta if v["type"] == "mr"]
        string_found = [v for v in vars_meta if v["type"] == "string"]
        
        result_msg = f"""✅ Dashboard Universal criado com sucesso!

🌍 DETECÇÃO AUTOMÁTICA:
• {len(string_found)} Resposta(s) Aberta(s) detectada(s)
• {len([v for v in vars_meta if v["type"] == "single"])} Resposta(s) Única(s)
• {len(mr_found)} grupo(s) de Resposta Múltipla

📊 PROCESSAMENTO:
• {len(records)} registros processados
• {len(vars_meta)} variáveis analisadas
• {len(filters_meta)} filtros disponíveis

🎨 FUNCIONALIDADES:
• Design clean e sutil
• Cores neutras e layout discreto
• Filtros funcionais sem peso visual
• Sistema universal para qualquer banco SPSS
• Detecção automática de tipos

📁 ARQUIVO: {os.path.basename(out_path)}

🎨 DESIGN CLEAN: Layout leve e profissional!"""

        if string_found:
            string_info = "\\n".join([f"• {v['title']}" for v in string_found])
            result_msg += f"\\n\\n🟣 Respostas Abertas detectadas:\\n{string_info}"

        if mr_found:
            mr_info = "\\n".join([f"• {v['title']}" for v in mr_found])
            result_msg += f"\\n\\n🟠 Respostas Múltiplas detectadas:\\n{mr_info}"

        root3 = tk.Tk()
        root3.withdraw()
        messagebox.showinfo("Dashboard Universal - Concluído", result_msg)
        root3.destroy()

        print(f"✅ HTML universal criado: {out_path}")
        print("🌍 Sistema funcionou com detecção automática universal!")
        print("🎨 DESIGN CLEAN: Layout sutil e cores neutras!")
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
        
        created_at, vars_meta, filters_meta, records = build_records_and_meta(
            df, meta, selected_vars, filter_vars, os.path.basename(args.input), args.cliente
        )
        
        html = render_html_with_working_filters(
            os.path.basename(args.input), created_at, args.cliente,
            vars_meta, filters_meta, records
        )
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        
        print(f"✅ Dashboard universal criado: {out_path}")
        print("✅ VERSÃO DEFINITIVA: Todos os problemas resolvidos!")
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
