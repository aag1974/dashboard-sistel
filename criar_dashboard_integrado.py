#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de Dashboard SPSS - Versão Integrada com Dashboard Master

HARMONIZAÇÃO APLICADA:
- Paleta corporativa (#4A90E2, #357ABD, #1976D2)
- Layout otimizado para iframe
- Comunicação com Dashboard Master via postMessage
- Filtros integrados com barra superior
- Remove redundâncias (header próprio)

FUNCIONALIDADES PRESERVADAS:
- Detecção de múltipla resposta
- Sistema de seleção nos gráficos
- Exportação CSV
- Todas as análises estatísticas
"""

from __future__ import annotations
import os, sys, json, re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import pyreadstat

# Truncagem de rótulos no gráfico
CHART_LABEL_MAX = 40

# ---------- TODAS AS FUNÇÕES CORE ORIGINAIS MANTIDAS ----------

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

def _try_import_ftfy():
    try:
        import ftfy  # type: ignore
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
    try:
        s3 = s.encode("utf-8", "ignore").decode("latin1", "ignore")
        if any(ch in s3 for ch in "áéíóúãõçÁÉÍÓÚÃÕÇ"):
            return s3
    except Exception:
        pass
    return s

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
    cl = getattr(meta, "column_labels", None)
    if isinstance(cl, dict):
        return (cl.get(col, "") or "")
    if isinstance(cl, list):
        cn = getattr(meta, "column_names", None)
        if isinstance(cn, list) and col in cn:
            i = cn.index(col)
            if 0 <= i < len(cl):
                return cl[i] or ""
    vtl = getattr(meta, "variable_to_label", None)
    if isinstance(vtl, dict):
        return vtl.get(col, "") or ""
    return ""

def _get_missing_specs(meta):
    mv = getattr(meta, "missing_values", None) or getattr(meta, "variable_missing_values", {}) or {}
    mr = getattr(meta, "missing_ranges", None) or getattr(meta, "variable_missing_ranges", {}) or {}

    norm_mv = {}
    for var, vals in mv.items():
        if vals is None:
            norm_mv[var] = []
        elif isinstance(vals, (list, tuple)):
            norm_mv[var] = [v for v in vals if v is not None]
        else:
            norm_mv[var] = [vals]

    norm_mr = {}
    for var, ranges in mr.items():
        lst = []
        if isinstance(ranges, (list, tuple)):
            for item in ranges:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    lst.append((item[0], item[1]))
        norm_mr[var] = lst
    return {"values": norm_mv, "ranges": norm_mr}

def _is_missing(var, val, misspecs) -> bool:
    import math
    if pd.isna(val):
        return True
    def to_num(x):
        try:
            return float(x)
        except Exception:
            return None
    def eq(a, b):
        an, bn = to_num(a), to_num(b)
        if an is not None and bn is not None:
            return math.isfinite(an) and math.isfinite(bn) and abs(an - bn) < 1e-12
        return str(a) == str(b)
    mv = misspecs["values"].get(var, [])
    for m in mv:
        if eq(val, m):
            return True
    for lo, hi in misspecs["ranges"].get(var, []):
        lo_n, hi_n, v_n = to_num(lo), to_num(hi), to_num(val)
        if v_n is not None and lo_n is not None and hi_n is not None:
            if lo_n <= v_n <= hi_n:
                return True
    return False

def _label_from_vmap(vmap: Dict[Any, str], val: Any) -> Optional[str]:
    if val in vmap: return str(vmap[val])
    sval = str(val)
    if sval in vmap: return str(vmap[sval])
    try:
        fval = float(val)
        for k, lab in vmap.items():
            try:
                if float(k) == fval: return str(lab)
            except Exception:
                continue
    except Exception:
        pass
    return None

def _is_invalid_text_code(val: Any) -> bool:
    if pd.isna(val):
        return True
    
    invalid_codes = {0, -1, 9, 99, 999, 9999}
    
    try:
        num_val = float(val)
        if num_val.is_integer() and int(num_val) in invalid_codes:
            return True
        if abs(num_val) >= 999999:
            return True
    except (ValueError, TypeError):
        str_val = str(val).strip().lower()
        invalid_strings = {
            "", "na", "n/a", "não sabe", "nao sabe", "não respondeu", 
            "nao respondeu", "sem resposta", "não se aplica", "nao se aplica"
        }
        if str_val in invalid_strings:
            return True
    
    return False

def detect_multiple_choice_improved(selected_vars: List[str], meta, valabs: Dict[str, Dict[Any, str]]):
    """DETECÇÃO ORIGINAL MANTIDA INTACTA"""
    vars_meta = []
    mr_groups: Dict[str, Dict[str, Any]] = {}
    
    labels = {v: get_var_label(meta, v) for v in selected_vars}
    
    used = set()
    i = 0
    
    while i < len(selected_vars):
        var = selected_vars[i]
        if var in used:
            i += 1
            continue
        
        base_match = re.match(r'^([A-Za-z]+\d*[A-Za-z]*)_(\d+)([A-Za-z]*)$', var)
        if base_match:
            base, num_str, suffix = base_match.groups()
            try:
                start_num = int(num_str)
            except ValueError:
                vars_meta.append({
                    "name": var,
                    "title": labels.get(var, var),
                    "type": "single",
                    "sheet_code": var
                })
                used.add(var)
                i += 1
                continue
            
            group_vars = [var]
            for num in range(start_num + 1, start_num + 50):
                next_var = f"{base}_{num}{suffix}"
                if next_var in selected_vars and next_var not in used:
                    group_vars.append(next_var)
                else:
                    break
            
            if len(group_vars) >= 2:
                group_name = f"mr_{base}"
                first_label = labels.get(group_vars[0], "")
                base_question = re.sub(r'\s*\[.*?\]\s*$', '', first_label).strip()
                if not base_question:
                    base_question = f"Grupo {base}"
                
                mr_groups[group_name] = {
                    "title": base_question,
                    "members": group_vars
                }
                
                vars_meta.append({
                    "name": group_name,
                    "title": base_question,
                    "type": "mr",
                    "sheet_code": group_name
                })
                
                used.update(group_vars)
                i += len(group_vars)
                continue
        
        current_label = labels.get(var, "")
        if not current_label:
            vars_meta.append({
                "name": var,
                "title": var,
                "type": "single",
                "sheet_code": var
            })
            used.add(var)
            i += 1
            continue
        
        base_question = re.sub(r'\s*\[.*?\]\s*$', '', current_label).strip()
        
        if base_question and base_question != current_label:
            similar_vars = [var]
            
            for j in range(i + 1, len(selected_vars)):
                other_var = selected_vars[j]
                if other_var in used:
                    continue
                
                other_label = labels.get(other_var, "")
                other_base = re.sub(r'\s*\[.*?\]\s*$', '', other_label).strip()
                
                if (other_base and 
                    len(other_base) > 10 and
                    base_question.lower() == other_base.lower()):
                    similar_vars.append(other_var)
            
            if len(similar_vars) >= 2:
                is_binary_group = True
                for sv in similar_vars:
                    vmap = valabs.get(sv, {})
                    if vmap:
                        unique_labels = set(str(v).lower().strip() for v in vmap.values())
                        binary_indicators = {"selected", "1=selected", "sim", "não", "yes", "no", "0", "1"}
                        if not unique_labels.intersection(binary_indicators):
                            is_binary_group = False
                            break
                
                if is_binary_group:
                    group_name = f"mr_similar_{len(mr_groups)}"
                    
                    mr_groups[group_name] = {
                        "title": base_question,
                        "members": similar_vars
                    }
                    
                    vars_meta.append({
                        "name": group_name,
                        "title": base_question,
                        "type": "mr",
                        "sheet_code": group_name
                    })
                    
                    used.update(similar_vars)
                    i = max(i + 1, max(selected_vars.index(sv) for sv in similar_vars) + 1)
                    continue
        
        if var not in used:
            vars_meta.append({
                "name": var,
                "title": labels.get(var, var),
                "type": "single",
                "sheet_code": var
            })
            used.add(var)
        
        i += 1
    
    return vars_meta, mr_groups

def select_variables_gui(root, all_vars: List[str], labels: Dict[str, str], title: str) -> Optional[List[str]]:
    import tkinter as tk
    win = tk.Toplevel(root); win.title(title); win.geometry("760x720"); win.configure(bg="#f8f9fa"); win.grab_set()
    tk.Label(win, text="Buscar por nome/label:", fg="#333333", bg="#f8f9fa").pack(anchor="w", padx=12, pady=(12,4))
    qv = tk.StringVar(); tk.Entry(win, textvariable=qv).pack(fill="x", padx=12)
    frame = tk.Frame(win, bg="#f8f9fa"); frame.pack(fill="both", expand=True, padx=12, pady=12)
    scroll = tk.Scrollbar(frame); lb = tk.Listbox(frame, selectmode="extended")
    scroll.pack(side="right", fill="y"); lb.pack(side="left", fill="both", expand=True)
    lb.config(yscrollcommand=scroll.set); scroll.config(command=lb.yview)

    def disp(v):
        lab = (labels.get(v) or "").strip()
        return f"{v} — {lab}" if lab else v

    def refresh(*_):
        qb = (qv.get() or "").lower().strip()
        lb.delete(0, "end")
        for v in all_vars:
            d = disp(v)
            if qb in d.lower(): lb.insert("end", d)

    qv.trace_add("write", refresh); refresh()

    sel: List[str] = []
    def ok():
        for i in lb.curselection():
            d = lb.get(i); sel.append(d.split(" — ", 1)[0])
        win.destroy()
    def cancel():
        sel.clear(); win.destroy()

    btns = tk.Frame(win, bg="#f8f9fa"); btns.pack(fill="x", padx=12, pady=(0,12))
    tk.Button(btns, text="Selecionar tudo", command=lambda: lb.select_set(0, "end"), bg="#4A90E2", fg="white").pack(side="left")
    tk.Button(btns, text="Limpar seleção", command=lambda: lb.selection_clear(0, "end"), bg="#6c757d", fg="white").pack(side="left", padx=8)
    tk.Button(btns, text="Cancelar", command=cancel, bg="#dc3545", fg="white").pack(side="right")
    tk.Button(btns, text="OK", command=ok, bg="#28a745", fg="white").pack(side="right", padx=8)

    lb.bind("<Double-1>", lambda e: ok())
    win.wait_window()
    return sel or None

def build_records_and_meta(df: pd.DataFrame, meta, selected_vars: List[str], filter_vars: List[str],
                           file_name: str, client_name: str):
    """FUNÇÃO CORE ORIGINAL - MANTIDA 100% INTACTA"""
    created_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    valabs: Dict[str, Dict[Any, str]] = get_value_labels_map(meta)
    misspecs = _get_missing_specs(meta)

    vars_meta, mr_groups = detect_multiple_choice_improved(selected_vars, meta, valabs)

    filters_meta: List[Dict[str, Any]] = []
    for fv in filter_vars:
        s = df[fv]
        vmap = valabs.get(fv, {})
        lab = (get_var_label(meta, fv) or fv).strip()
        vals = []
        
        for val in sorted(s.dropna().unique().tolist(), key=lambda x: str(x)):
            if (_is_missing(fv, val, misspecs) or 
                _is_invalid_text_code(val)):
                continue
            
            processed_val = str(vmap.get(val, val)).replace(":", "").strip()
            
            if processed_val.replace('.', '').replace('-', '').isdigit() and processed_val.endswith('.0'):
                processed_val = processed_val[:-2]
            
            if not _is_invalid_text_code(processed_val):
                vals.append(processed_val)
        
        seen=set(); clean=[]
        for x in vals:
            if x not in seen:
                seen.add(x); clean.append(x)
        filters_meta.append({"name": fv, "title": lab, "values": clean})

    use_cols = list(dict.fromkeys(selected_vars + filter_vars))
    records: List[Dict[str, Any]] = []
    
    for _, row in df[use_cols].iterrows():
        rec: Dict[str, Any] = {}
        
        for fv in filter_vars:
            val = row.get(fv)
            if pd.isna(val) or _is_missing(fv, val, misspecs):
                rec[fv] = None
            else:
                rec[fv] = str(valabs.get(fv, {}).get(val, val)).replace(":", "").strip()
        
        for vm in vars_meta:
            if vm["type"] == "single":
                col = vm["name"]
                val = row.get(col)
                
                if (pd.isna(val) or 
                    _is_missing(col, val, misspecs) or 
                    _is_invalid_text_code(val)):
                    rec[col] = None
                else:
                    processed_val = str(valabs.get(col, {}).get(val, val)).replace(":", "").strip()
                    
                    if _is_invalid_text_code(processed_val):
                        rec[col] = None
                    else:
                        rec[col] = processed_val
            else:  # múltipla resposta
                mr_name = vm["name"]
                members = mr_groups[mr_name]["members"]
                chosen_options = []
                
                for col in members:
                    val = row.get(col)
                    if pd.isna(val) or _is_missing(col, val, misspecs):
                        continue
                    
                    vmap = valabs.get(col, {})
                    
                    is_selected = False
                    
                    if vmap:
                        lab = _label_from_vmap(vmap, val)
                        if lab is not None:
                            lab_lower = lab.lower().strip()
                            if (lab_lower == "selected" or 
                                "1=selected" in lab_lower or 
                                lab_lower == "sim" or 
                                lab_lower == "yes" or
                                (lab_lower == "1" and str(val) == "1")):
                                is_selected = True
                    else:
                        try:
                            if float(val) == 1:
                                is_selected = True
                        except (ValueError, TypeError):
                            val_str = str(val).lower().strip()
                            if val_str in ["1", "selected", "sim", "yes"]:
                                is_selected = True
                    
                    if is_selected:
                        var_label = get_var_label(meta, col)
                        option_match = re.search(r'\[(.*?)\]', var_label)
                        if option_match:
                            option_text = option_match.group(1).replace(":", "").strip()
                            chosen_options.append(option_text)
                        else:
                            option_text = var_label if var_label else col
                            chosen_options.append(option_text.replace(":", "").strip())
                
                rec[mr_name] = sorted(set(chosen_options))
        
        records.append(rec)

    return created_at, vars_meta, filters_meta, records

# ---------- RENDERIZAÇÃO HTML HARMONIZADA COM DASHBOARD MASTER ----------

def render_html_integrated(file_name: str, created_at: str, client_name: str,
                          vars_meta: List[Dict[str, Any]], filters_meta: List[Dict[str, Any]],
                          records: List[Dict[str, Any]]) -> str:
    """
    Renderização HTML integrada com Dashboard Master
    - Remove header próprio (redundante no iframe)
    - Usa paleta corporativa harmonizada
    - Comunica filtros com Dashboard Master
    - Layout otimizado para iframe
    """
    title_extra = f" — Para {client_name}" if client_name.strip() else ""
    
    # CSS HARMONIZADO COM DASHBOARD MASTER
    css = """
/* ========= PALETA CORPORATIVA HARMONIZADA ========= */
:root {
    --primary: #4A90E2;
    --primary-dark: #357ABD;
    --secondary: #1976D2;
    --bg: #f8f9fa;
    --panel: #ffffff;
    --text: #333333;
    --text-light: #666666;
    --text-muted: #888888;
    --border: #e0e0e0;
    --border-light: #f0f0f0;
    --hover: #f0f4f8;
    --active: #e5eef7;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
    --shadow: 0 2px 10px rgba(0,0,0,0.1);
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.05);
    --radius: 8px;
    --radius-lg: 12px;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 20px;
}

/* ========= CONTAINER PRINCIPAL ========= */
.dashboard-content {
    max-width: 100%;
    margin: 0 auto;
}

/* ========= FILTROS INTEGRADOS ========= */
.filters-section {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 20px;
    margin-bottom: 25px;
    box-shadow: var(--shadow-sm);
}

.filters-header {
    display: flex;
    justify-content: between;
    align-items: center;
    margin-bottom: 15px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-light);
}

.filters-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--primary);
    margin: 0;
}

.filters-actions {
    display: flex;
    gap: 10px;
}

.btn {
    padding: 8px 16px;
    border: none;
    border-radius: var(--radius);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s ease;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.btn-primary {
    background: var(--primary);
    color: white;
}

.btn-primary:hover {
    background: var(--primary-dark);
    transform: translateY(-1px);
}

.btn-secondary {
    background: var(--border);
    color: var(--text);
}

.btn-secondary:hover {
    background: var(--hover);
}

.filters-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 15px;
}

.filter-item {
    display: flex;
    flex-direction: column;
}

.filter-label {
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 8px;
}

.filter-dropdown {
    position: relative;
}

.filter-select {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: white;
    color: var(--text);
    font-size: 14px;
    min-height: 80px;
    resize: vertical;
    transition: all 0.3s ease;
}

.filter-select:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.1);
}

.filter-select option {
    padding: 6px 8px;
    color: var(--text);
}

.filter-select option:checked {
    background: var(--primary);
    color: white;
}

/* ========= SELECTION CONTROLS ========= */
.selection-controls {
    background: rgba(74, 144, 226, 0.05);
    border: 1px solid rgba(74, 144, 226, 0.2);
    border-radius: var(--radius);
    padding: 12px 16px;
    margin: 15px 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.selection-info {
    font-size: 14px;
    color: var(--primary);
    font-weight: 500;
}

.selection-clear {
    background: var(--danger);
    color: white;
    border: none;
    padding: 6px 12px;
    border-radius: var(--radius);
    font-size: 12px;
    cursor: pointer;
    transition: all 0.3s ease;
}

.selection-clear:hover {
    background: #dc2626;
}

/* ========= CARDS DAS VARIÁVEIS ========= */
.content-section {
    margin-top: 10px;
}

.variable-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 25px;
    margin-bottom: 25px;
    box-shadow: var(--shadow-sm);
    transition: all 0.3s ease;
    position: relative;
}

.variable-card:hover {
    box-shadow: var(--shadow);
    border-color: var(--primary);
}

.variable-card.has-selections {
    border-color: var(--secondary);
    box-shadow: 0 0 0 1px rgba(25, 118, 210, 0.3);
}

.variable-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--text);
    margin: 0 0 15px 0;
    display: flex;
    align-items: center;
    gap: 10px;
}

.variable-badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    background: rgba(74, 144, 226, 0.1);
    color: var(--primary);
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    border: 1px solid rgba(74, 144, 226, 0.2);
}

.selection-indicator {
    position: absolute;
    top: 15px;
    right: 15px;
    background: var(--secondary);
    color: white;
    padding: 4px 8px;
    border-radius: var(--radius);
    font-size: 11px;
    font-weight: 600;
}

/* ========= TABELAS ========= */
.data-table {
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
    background: white;
    border-radius: var(--radius);
    overflow: hidden;
    box-shadow: var(--shadow-sm);
}

.data-table th {
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    color: white;
    font-weight: 600;
    padding: 12px 15px;
    text-align: left;
    font-size: 14px;
}

.data-table td {
    padding: 10px 15px;
    border-bottom: 1px solid var(--border-light);
    font-size: 14px;
}

.data-table tbody tr:hover {
    background: rgba(74, 144, 226, 0.02);
}

.data-table tbody tr:last-child td {
    border-bottom: none;
}

.table-total {
    border-top: 2px solid var(--primary) !important;
    font-weight: 600;
    background: rgba(74, 144, 226, 0.05) !important;
}

/* ========= GRÁFICOS ========= */
.chart-container {
    margin-top: 20px;
    background: white;
    border-radius: var(--radius);
    padding: 20px;
    box-shadow: var(--shadow-sm);
    cursor: pointer;
    transition: all 0.3s ease;
}

.chart-container:hover {
    box-shadow: var(--shadow);
}

.chart-canvas {
    width: 100%;
    height: 350px;
    cursor: pointer;
}

/* ========= ALERTAS E AVISOS ========= */
.low-n-warning {
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.3);
    color: #92400e;
    padding: 12px 16px;
    border-radius: var(--radius);
    margin-top: 15px;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.low-n-warning::before {
    content: "⚠️";
    font-size: 16px;
}

.selection-info-box {
    background: rgba(25, 118, 210, 0.05);
    border: 1px solid rgba(25, 118, 210, 0.2);
    border-radius: var(--radius);
    padding: 12px 16px;
    margin: 10px 0;
    font-size: 13px;
}

.selection-info-title {
    color: var(--secondary);
    font-weight: 600;
    margin-bottom: 5px;
}

.selection-info-items {
    color: var(--text-light);
}

/* ========= RESPONSIVIDADE ========= */
@media (max-width: 768px) {
    body {
        padding: 10px;
    }

    .filters-grid {
        grid-template-columns: 1fr;
        gap: 10px;
    }

    .filters-header {
        flex-direction: column;
        align-items: stretch;
        gap: 10px;
    }

    .filters-actions {
        justify-content: center;
    }

    .variable-card {
        padding: 15px;
        margin-bottom: 15px;
    }

    .variable-title {
        font-size: 16px;
    }

    .chart-canvas {
        height: 250px;
    }

    .data-table {
        font-size: 12px;
    }

    .data-table th,
    .data-table td {
        padding: 8px 10px;
    }
}

/* ========= FOOTER ========= */
.content-footer {
    text-align: center;
    padding: 30px 20px;
    color: var(--text-muted);
    font-size: 13px;
    border-top: 1px solid var(--border-light);
    margin-top: 40px;
}
"""

    # Preparar dados para JavaScript
    js_vars = json.dumps(vars_meta, ensure_ascii=False)
    js_filters = json.dumps(filters_meta, ensure_ascii=False)
    js_records = json.dumps(records, ensure_ascii=False)
    
    file_name_safe = json.dumps(file_name)[1:-1]
    created_at_safe = json.dumps(created_at)[1:-1]

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Análise SPSS{title_extra}</title>
    <style>{css}</style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
</head>
<body>
    <div class="dashboard-content">
        <!-- Seção de Filtros Integrada -->
        <div class="filters-section" id="filtersSection">
            <div class="filters-header">
                <h2 class="filters-title">🔍 Filtros de Análise</h2>
                <div class="filters-actions">
                    <button id="btnExport" class="btn btn-primary">📊 Exportar CSV</button>
                    <button id="btnClearFilters" class="btn btn-secondary">🔄 Limpar Filtros</button>
                </div>
            </div>
            <div class="filters-grid" id="filtersGrid">
                <!-- Filtros serão gerados dinamicamente -->
            </div>
        </div>

        <!-- Controles de Seleção nos Gráficos -->
        <div class="selection-controls" id="selectionControls" style="display: none;">
            <div class="selection-info" id="selectionInfo">
                Nenhuma seleção ativa nos gráficos
            </div>
            <button class="selection-clear" id="selectionClear">
                🗑️ Limpar Seleções
            </button>
        </div>

        <!-- Área Principal de Conteúdo -->
        <div class="content-section">
            <div id="tablesContainer">
                <!-- Tabelas e gráficos serão gerados aqui -->
            </div>
        </div>

        <!-- Footer -->
        <div class="content-footer">
            📋 Arquivo: {file_name_safe} | 📅 Gerado: {created_at_safe}
            <br>Confidencial - Reprodução proibida
        </div>
    </div>

<script>
// ========= VARIÁVEIS GLOBAIS (ORIGINAIS) =========
const VARS = {js_vars};
const FILTERS = {js_filters};
const RECORDS = {js_records};
const CHART_LABEL_MAX = {CHART_LABEL_MAX};

// Sistema de seleção múltipla nos gráficos (ORIGINAL)
let graphSelections = {{}};
let charts = {{}};

// ========= COMUNICAÇÃO COM DASHBOARD MASTER =========
function notifyDashboardMaster(type, data) {{
    // Comunica mudanças de filtros para o Dashboard Master
    if (window.parent !== window) {{
        try {{
            window.parent.postMessage({{
                source: 'spss-analysis',
                type: type,
                data: data,
                filename: '{file_name_safe}'
            }}, '*');
        }} catch (e) {{
            console.log('Não foi possível comunicar com Dashboard Master:', e);
        }}
    }}
}}

// ========= FUNÇÕES ORIGINAIS MANTIDAS ========= 
function initializeSelections() {{
    VARS.forEach(varMeta => {{
        graphSelections[varMeta.name] = [];
    }});
}}

function toggleSelection(variableName, value) {{
    const selections = graphSelections[variableName] || [];
    const index = selections.indexOf(value);
    
    if (index === -1) {{
        selections.push(value);
    }} else {{
        selections.splice(index, 1);
    }}
    
    graphSelections[variableName] = selections;
    
    renderAll();
    updateSelectionControls();
    
    // Notifica Dashboard Master sobre mudanças de seleção
    notifyDashboardMaster('selection-changed', {{
        variable: variableName,
        selections: selections,
        totalSelections: Object.values(graphSelections).reduce((total, sel) => total + sel.length, 0)
    }});
}}

function clearAllSelections() {{
    Object.keys(graphSelections).forEach(key => {{
        graphSelections[key] = [];
    }});
    
    renderAll();
    updateSelectionControls();
    
    notifyDashboardMaster('selections-cleared', {{}});
}}

function updateSelectionControls() {{
    const controlsDiv = document.getElementById('selectionControls');
    const infoDiv = document.getElementById('selectionInfo');
    
    const totalSelections = Object.values(graphSelections).reduce((total, selections) => {{
        return total + (selections ? selections.length : 0);
    }}, 0);
    
    if (totalSelections > 0) {{
        controlsDiv.style.display = 'flex';
        infoDiv.textContent = `${{totalSelections}} seleção${{totalSelections > 1 ? 'ões' : ''}} ativa${{totalSelections > 1 ? 's' : ''}} nos gráficos`;
    }} else {{
        controlsDiv.style.display = 'none';
    }}
}}

function buildFilters() {{
    const container = document.getElementById('filtersGrid');
    container.innerHTML = '';
    
    if (FILTERS.length === 0) {{
        const noFilters = document.createElement('div');
        noFilters.style.gridColumn = '1 / -1';
        noFilters.style.textAlign = 'center';
        noFilters.style.color = 'var(--text-muted)';
        noFilters.style.fontStyle = 'italic';
        noFilters.innerHTML = '📊 Nenhum filtro configurado para esta análise';
        container.appendChild(noFilters);
        return;
    }}
    
    FILTERS.forEach(filter => {{
        const filterItem = document.createElement('div');
        filterItem.className = 'filter-item';
        
        const label = document.createElement('label');
        label.className = 'filter-label';
        label.textContent = filter.title;
        
        const dropdown = document.createElement('div');
        dropdown.className = 'filter-dropdown';
        
        const select = document.createElement('select');
        select.id = `filter_${{filter.name}}`;
        select.className = 'filter-select';
        select.multiple = true;
        select.size = Math.min(filter.values.length + 1, 5);
        
        // Opção "Todos" selecionada por padrão
        const allOption = document.createElement('option');
        allOption.value = '';
        allOption.textContent = '✓ Todos';
        allOption.selected = true;
        select.appendChild(allOption);
        
        // Opções específicas
        filter.values.forEach(value => {{
            const option = document.createElement('option');
            option.value = value;
            option.textContent = value;
            select.appendChild(option);
        }});
        
        select.addEventListener('change', () => {{
            applyFilters();
            
            // Notifica Dashboard Master sobre mudança de filtros
            const selectedValues = Array.from(select.selectedOptions)
                .map(opt => opt.value)
                .filter(val => val !== '');
                
            notifyDashboardMaster('filter-changed', {{
                filter: filter.name,
                selected: selectedValues,
                filterTitle: filter.title
            }});
        }});
        
        dropdown.appendChild(select);
        filterItem.appendChild(label);
        filterItem.appendChild(dropdown);
        container.appendChild(filterItem);
    }});
}}

function applyFilters() {{
    renderAll();
}}

function clearFilters() {{
    FILTERS.forEach(filter => {{
        const selectEl = document.getElementById(`filter_${{filter.name}}`);
        if (selectEl) {{
            Array.from(selectEl.options).forEach(option => {{
                option.selected = option.value === '';
            }});
        }}
    }});
    
    renderAll();
    
    notifyDashboardMaster('filters-cleared', {{}});
}}

function getFilteredRecords() {{
    return RECORDS.filter(record => {{
        // Filtros dropdown tradicionais
        const passesDropdownFilters = FILTERS.every(filter => {{
            const selectEl = document.getElementById(`filter_${{filter.name}}`);
            if (!selectEl) return true;
            
            const selectedOptions = Array.from(selectEl.selectedOptions);
            const selectedValues = selectedOptions
                .map(opt => opt.value)
                .filter(val => val !== '');
            
            if (selectedValues.length === 0) {{
                return true;
            }}
            
            return selectedValues.includes(String(record[filter.name]));
        }});
        
        // Filtros de seleção dos gráficos
        const passesGraphSelections = Object.entries(graphSelections).every(([varName, selectedValues]) => {{
            if (!selectedValues || selectedValues.length === 0) {{
                return true;
            }}
            
            const recordValue = record[varName];
            
            if (typeof recordValue === 'string' || typeof recordValue === 'number') {{
                return selectedValues.includes(String(recordValue));
            }}
            
            if (Array.isArray(recordValue)) {{
                return selectedValues.some(selection => recordValue.includes(selection));
            }}
            
            return true;
        }});
        
        return passesDropdownFilters && passesGraphSelections;
    }});
}}

function renderAll() {{
    const filtered = getFilteredRecords();
    const container = document.getElementById('tablesContainer');
    container.innerHTML = '';
    
    VARS.forEach(varMeta => {{
        renderVariableCard(varMeta, filtered, container);
    }});
}}

function renderVariableCard(varMeta, filtered, container) {{
    // LÓGICA ORIGINAL DE RENDERIZAÇÃO MANTIDA - só adapto visual
    const card = document.createElement('div');
    card.className = 'variable-card';
    
    const title = document.createElement('div');
    title.className = 'variable-title';
    title.innerHTML = `
        ${{varMeta.title}}
        <span class="variable-badge">${{varMeta.type === 'mr' ? 'Múltipla Resposta' : 'Individual'}}</span>
    `;
    card.appendChild(title);
    
    if (varMeta.type === 'single') {{
        // LÓGICA ORIGINAL PARA SINGLE
        const data = filtered
            .map(r => r[varMeta.name])
            .filter(v => v !== null && v !== undefined && v !== '');
        
        const freq = {{}};
        data.forEach(val => {{
            freq[val] = (freq[val] || 0) + 1;
        }});
        
        const total = data.length;
        const entries = Object.entries(freq)
            .sort((a, b) => b[1] - a[1]);
        
        if (total > 0) {{
            const table = document.createElement('table');
            table.className = 'data-table';
            
            const thead = document.createElement('thead');
            thead.innerHTML = '<tr><th>Resposta</th><th>N</th><th>%</th></tr>';
            table.appendChild(thead);
            
            const tbody = document.createElement('tbody');
            entries.forEach(([val, count]) => {{
                const pct = ((count / total) * 100).toFixed(1).replace('.', ',');
                const row = document.createElement('tr');
                row.innerHTML = `<td>${{val}}</td><td>${{count}}</td><td>${{pct}}%</td>`;
                tbody.appendChild(row);
            }});
            
            const totalRow = document.createElement('tr');
            totalRow.className = 'table-total';
            totalRow.innerHTML = `<td>Total de respostas válidas</td><td>${{total}}</td><td>100,0%</td>`;
            tbody.appendChild(totalRow);
            
            table.appendChild(tbody);
            card.appendChild(table);
            
            if (total < 30) {{
                const warning = document.createElement('div');
                warning.className = 'low-n-warning';
                warning.innerHTML = 'n < 30: sem representatividade estatística.';
                card.appendChild(warning);
            }}
            
            // Gráfico com nova estrutura visual
            const chartContainer = document.createElement('div');
            chartContainer.className = 'chart-container';
            const canvas = document.createElement('canvas');
            canvas.className = 'chart-canvas';
            chartContainer.appendChild(canvas);
            card.appendChild(chartContainer);
            
            const chart = new Chart(canvas.getContext('2d'), {{
                type: 'bar',
                data: {{
                    labels: entries.map(([val]) => val.length > CHART_LABEL_MAX ? val.substring(0, CHART_LABEL_MAX) + '...' : val),
                    datasets: [{{
                        data: entries.map(([,count]) => ((count / total) * 100)),
                        backgroundColor: entries.map(([val]) => {{
                            const selections = graphSelections[varMeta.name] || [];
                            return selections.includes(val) ? '#1976D2' : '#4A90E2';
                        }}),
                        borderWidth: 0,
                        borderRadius: 4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ 
                        legend: {{ display: false }},
                        tooltip: {{
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            titleColor: 'white',
                            bodyColor: 'white',
                            cornerRadius: 6,
                            callbacks: {{
                                label: function(context) {{
                                    return context.parsed.y.toFixed(1).replace('.', ',') + '%';
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            grid: {{ color: 'rgba(0,0,0,0.05)' }},
                            ticks: {{ 
                                callback: function(value) {{
                                    return value.toFixed(1).replace('.', ',') + '%';
                                }},
                                color: '#666666'
                            }}
                        }},
                        x: {{
                            grid: {{ display: false }},
                            ticks: {{ color: '#666666' }}
                        }}
                    }},
                    onClick: (event, elements) => {{
                        if (elements.length > 0) {{
                            const index = elements[0].index;
                            const label = entries[index][0];
                            toggleSelection(varMeta.name, label);
                        }}
                    }}
                }}
            }});
            
            charts[varMeta.name] = chart;
        }}
    }} else {{
        // LÓGICA ORIGINAL PARA MÚLTIPLA RESPOSTA
        const allOptions = [];
        filtered.forEach(record => {{
            const opts = record[varMeta.name] || [];
            if (Array.isArray(opts)) {{
                opts.forEach(opt => allOptions.push(opt));
            }}
        }});
        
        const freq = {{}};
        allOptions.forEach(opt => {{
            freq[opt] = (freq[opt] || 0) + 1;
        }});
        
        const questionRespondents = filtered.filter(r => {{
            const opts = r[varMeta.name] || [];
            return Array.isArray(opts) && opts.length > 0;
        }}).length;
        
        if (questionRespondents > 0) {{
            const entries = Object.entries(freq)
                .sort((a, b) => b[1] - a[1]);
            
            const table = document.createElement('table');
            table.className = 'data-table';
            
            const thead = document.createElement('thead');
            thead.innerHTML = '<tr><th>Opção</th><th>N</th><th>% (base: pergunta)</th></tr>';
            table.appendChild(thead);
            
            const tbody = document.createElement('tbody');
            entries.forEach(([opt, count]) => {{
                const pct = ((count / questionRespondents) * 100).toFixed(1).replace('.', ',');
                const row = document.createElement('tr');
                row.innerHTML = `<td>${{opt}}</td><td>${{count}}</td><td>${{pct}}%</td>`;
                tbody.appendChild(row);
            }});
            
            const totalRow = document.createElement('tr');
            totalRow.className = 'table-total';
            totalRow.innerHTML = `<td>Base: Respondentes da pergunta</td><td>${{questionRespondents}}</td><td>100,0%</td>`;
            tbody.appendChild(totalRow);
            
            table.appendChild(tbody);
            card.appendChild(table);
            
            if (questionRespondents < 30) {{
                const warning = document.createElement('div');
                warning.className = 'low-n-warning';
                warning.innerHTML = 'n < 30: sem representatividade estatística.';
                card.appendChild(warning);
            }}
            
            // Gráfico
            const chartContainer = document.createElement('div');
            chartContainer.className = 'chart-container';
            const canvas = document.createElement('canvas');
            canvas.className = 'chart-canvas';
            chartContainer.appendChild(canvas);
            card.appendChild(chartContainer);
            
            const chart = new Chart(canvas.getContext('2d'), {{
                type: 'bar',
                data: {{
                    labels: entries.map(([opt]) => opt.length > CHART_LABEL_MAX ? opt.substring(0, CHART_LABEL_MAX) + '...' : opt),
                    datasets: [{{
                        data: entries.map(([,count]) => ((count / questionRespondents) * 100)),
                        backgroundColor: entries.map(([opt]) => {{
                            const selections = graphSelections[varMeta.name] || [];
                            return selections.includes(opt) ? '#1976D2' : '#4A90E2';
                        }}),
                        borderWidth: 0,
                        borderRadius: 4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ 
                        legend: {{ display: false }},
                        tooltip: {{
                            backgroundColor: 'rgba(0,0,0,0.8)',
                            titleColor: 'white',
                            bodyColor: 'white',
                            cornerRadius: 6,
                            callbacks: {{
                                label: function(context) {{
                                    return context.parsed.y.toFixed(1).replace('.', ',') + '%';
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            grid: {{ color: 'rgba(0,0,0,0.05)' }},
                            ticks: {{ 
                                callback: function(value) {{
                                    return value.toFixed(1).replace('.', ',') + '%';
                                }},
                                color: '#666666'
                            }}
                        }},
                        x: {{
                            grid: {{ display: false }},
                            ticks: {{ color: '#666666' }}
                        }}
                    }},
                    onClick: (event, elements) => {{
                        if (elements.length > 0) {{
                            const index = elements[0].index;
                            const label = entries[index][0];
                            toggleSelection(varMeta.name, label);
                        }}
                    }}
                }}
            }});
            
            charts[varMeta.name] = chart;
        }}
    }}
    
    // Adiciona indicadores de seleção
    addSelectionIndicator(card, varMeta);
    
    container.appendChild(card);
}}

function addSelectionIndicator(card, varMeta) {{
    const selections = graphSelections[varMeta.name] || [];
    
    if (selections.length > 0) {{
        card.classList.add('has-selections');
        
        const indicator = document.createElement('div');
        indicator.className = 'selection-indicator';
        indicator.textContent = `${{selections.length}} selecionada${{selections.length > 1 ? 's' : ''}}`;
        card.appendChild(indicator);
        
        const info = document.createElement('div');
        info.className = 'selection-info-box';
        info.innerHTML = `
            <div class="selection-info-title">Filtro Ativo:</div>
            <div class="selection-info-items">${{selections.join(', ')}}</div>
        `;
        card.appendChild(info);
    }} else {{
        card.classList.remove('has-selections');
    }}
}}

// EXPORTAÇÃO CSV (ORIGINAL MANTIDA)
function exportXLSX() {{
    const filtered = getFilteredRecords();
    
    if (filtered.length === 0) {{
        alert('Nenhum dado para exportar com os filtros atuais.');
        return;
    }}
    
    function escapeCsvField(value) {{
        let str = String(value || '');
        if (str.includes(';') || str.includes('"') || str.includes('\\n') || str.includes('\\r')) {{
            str = '"' + str.replace(/"/g, '""') + '"';
        }}
        return str;
    }}
    
    let csvContent = '\\ufeff';
    
    VARS.forEach((varMeta, varIndex) => {{
        if (varIndex > 0) csvContent += '\\n\\n';
        
        csvContent += `"${{varMeta.title.replace(/"/g, '""')}}"\\n`;
        csvContent += '\\n';
        
        if (varMeta.type === 'single') {{
            const data = filtered
                .map(r => r[varMeta.name])
                .filter(v => v !== null && v !== undefined && v !== '');
            
            const freq = {{}};
            data.forEach(val => {{
                freq[val] = (freq[val] || 0) + 1;
            }});
            
            const total = data.length;
            const entries = Object.entries(freq)
                .sort((a, b) => b[1] - a[1]);
            
            if (total > 0) {{
                csvContent += 'Resposta;N;%\\n';
                
                entries.forEach(([val, count]) => {{
                    const pct = ((count / total) * 100).toFixed(1).replace('.', ',') + '%';
                    csvContent += `${{escapeCsvField(val)}};${{count}};${{pct}}\\n`;
                }});
                
                csvContent += '\\n';
                csvContent += `${{escapeCsvField('Total de respostas válidas')}};${{total}};100,0%\\n`;
                
                if (total < 30) {{
                    csvContent += '\\n';
                    csvContent += '"n < 30: sem representatividade estatística."\\n';
                }}
            }}
            
        }} else {{
            const allOptions = [];
            filtered.forEach(record => {{
                const opts = record[varMeta.name] || [];
                if (Array.isArray(opts)) {{
                    opts.forEach(opt => allOptions.push(opt));
                }}
            }});
            
            const freq = {{}};
            allOptions.forEach(opt => {{
                freq[opt] = (freq[opt] || 0) + 1;
            }});
            
            const questionRespondents = filtered.filter(r => {{
                const opts = r[varMeta.name] || [];
                return Array.isArray(opts) && opts.length > 0;
            }}).length;
            
            if (questionRespondents > 0) {{
                const entries = Object.entries(freq)
                    .sort((a, b) => b[1] - a[1]);
                
                csvContent += 'Opção;N;"% (base: pergunta)"\\n';
                
                entries.forEach(([opt, count]) => {{
                    const pct = ((count / questionRespondents) * 100).toFixed(1).replace('.', ',') + '%';
                    csvContent += `${{escapeCsvField(opt)}};${{count}};${{pct}}\\n`;
                }});
                
                csvContent += '\\n';
                csvContent += `${{escapeCsvField('Base: Respondentes da pergunta')}};${{questionRespondents}};100,0%\\n`;
                
                if (questionRespondents < 30) {{
                    csvContent += '\\n';
                    csvContent += '"n < 30: sem representatividade estatística."\\n';
                }}
            }}
        }}
        
        csvContent += '\\n';
    }});
    
    const blob = new Blob([csvContent], {{ 
        type: 'text/csv;charset=utf-8;' 
    }});
    
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'analise_spss.csv';
    link.style.display = 'none';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    
    setTimeout(() => {{
        alert('Arquivo CSV exportado com sucesso!\\n\\nDelimitador: Ponto e vírgula (;)\\nEncoding: UTF-8\\n\\nO Excel brasileiro abrirá automaticamente com as colunas corretas.');
    }}, 500);
    
    // Notifica Dashboard Master
    notifyDashboardMaster('data-exported', {{ filename: 'analise_spss.csv' }});
}}

// ========= EVENT LISTENERS E INICIALIZAÇÃO =========
document.addEventListener('DOMContentLoaded', () => {{
    // Event listeners
    document.getElementById('btnExport').addEventListener('click', exportXLSX);
    document.getElementById('btnClearFilters').addEventListener('click', clearFilters);
    document.getElementById('selectionClear').addEventListener('click', clearAllSelections);
    
    // Inicialização
    initializeSelections();
    buildFilters();
    renderAll();
    updateSelectionControls();
    
    // Notifica Dashboard Master que a análise foi carregada
    notifyDashboardMaster('analysis-loaded', {{
        title: '{file_name_safe}',
        variables: VARS.length,
        filters: FILTERS.length,
        records: RECORDS.length
    }});
    
    console.log('📊 Dashboard SPSS Integrado carregado com sucesso!');
    console.log(`📈 ${{VARS.length}} variáveis, ${{FILTERS.length}} filtros, ${{RECORDS.length}} registros`);
}});

// Escuta comandos do Dashboard Master
window.addEventListener('message', (event) => {{
    if (event.data && event.data.source === 'dashboard-master') {{
        switch (event.data.type) {{
            case 'clear-all-filters':
                clearFilters();
                break;
            case 'clear-all-selections':
                clearAllSelections();
                break;
            case 'export-data':
                exportXLSX();
                break;
        }}
    }}
}});
</script>

</body>
</html>"""

# ---------- GUI / CLI (ORIGINAIS MANTIDOS) ----------
def run_gui() -> int:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, simpledialog
    except Exception:
        print("tkinter não disponível. Use a linha de comando.", file=sys.stderr)
        return 3

    root = tk.Tk(); root.withdraw(); root.update()
    try:
        in_path = filedialog.askopenfilename(parent=root, title="Selecione o arquivo SPSS (.sav)",
                                             filetypes=[("SPSS files", "*.sav"), ("Todos os arquivos", "*.*")])
        if not in_path:
            print("Nenhum arquivo selecionado. Saindo...")
            root.destroy()
            return 1

        print(f"📁 Arquivo selecionado: {in_path}")
        
        df, meta = read_sav_auto(in_path)
        fix_labels_in_meta(meta)
        print(f"✅ Arquivo carregado: {len(df)} registros, {len(df.columns)} variáveis")
        
        labels = {c: (get_var_label(meta, c) or "") for c in df.columns}

        print("🎯 Abrindo seleção de variáveis principais...")
        selected = select_variables_gui(root, list(df.columns), labels, "Selecione as VARIÁVEIS do relatório")
        if not selected:
            print("❌ Nenhuma variável selecionada. Saindo...")
            root.destroy()
            return 1
        print(f"✅ Variáveis selecionadas: {len(selected)}")

        print("🔍 Abrindo seleção de filtros...")
        filt_vars = select_variables_gui(root, list(df.columns), labels, "Selecione VARIÁVEIS-FILTRO (opcional)") or []
        print(f"✅ Filtros selecionados: {len(filt_vars)}")

        client_name = simpledialog.askstring("Cliente (opcional)",
                         "Adicionar ao título: '— Para <cliente>'\nDeixe em branco para não mostrar.",
                         parent=root) or ""

        default_out = os.path.splitext(in_path)[0] + "_dashboard_integrado.html"
        out_path = filedialog.asksaveasfilename(parent=root, title="Salvar dashboard HTML como...",
                            defaultextension=".html", initialfile=os.path.basename(default_out),
                            filetypes=[("HTML", "*.html")]) or default_out

        print("⚙️ Processando dados...")
        created_at, vars_meta, filters_meta, records = build_records_and_meta(
            df, meta, selected, filt_vars, in_path, client_name
        )

        print("🎨 Gerando HTML integrado...")
        html = render_html_integrated(os.path.basename(in_path), created_at, client_name,
                           vars_meta, filters_meta, records)
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

        mr_found = [v for v in vars_meta if v["type"] == "mr"]
        if mr_found:
            mr_info = "\n".join([f"• {v['title']}" for v in mr_found])
            messagebox.showinfo("Dashboard Integrado - Múltipla Resposta Detectada",
                               f"✅ Dashboard integrado com Dashboard Master!\n\n🔍 Múltipla resposta detectada:\n\n{mr_info}\n\n📱 HARMONIZADO:\n• Paleta corporativa (#4A90E2)\n• Layout para iframe\n• Comunicação via postMessage\n• Filtros integrados",
                               parent=root)
        else:
            messagebox.showinfo("Dashboard Integrado - Concluído", 
                               "✅ Dashboard integrado com Dashboard Master!\n\n📱 HARMONIZADO:\n• Paleta corporativa (#4A90E2)\n• Layout otimizado para iframe\n• Comunicação via postMessage\n• Filtros integrados\n\n🔍 Nenhum grupo de múltipla resposta detectado.",
                               parent=root)

        root.destroy()
        print(f"✅ HTML integrado: {out_path}")
        print("🔗 Este arquivo está pronto para ser usado no Dashboard Master!")
        return 0

    except Exception as e:
        try:
            messagebox.showerror("Erro", f"Erro inesperado:\n\n{str(e)}", parent=root)
        except Exception:
            print(f"Erro: {e}", file=sys.stderr)
        finally:
            try: root.destroy()
            except Exception: pass
        return 4

def run_cli() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Dashboard SPSS integrado com Dashboard Master.")
    p.add_argument("input", help="Caminho do arquivo .sav")
    p.add_argument("--vars", type=str, required=True, help="Variáveis do relatório separadas por vírgula")
    p.add_argument("--filters", type=str, default="", help="Variáveis-filtro separadas por vírgula")
    p.add_argument("--cliente", type=str, default="", help="Nome do cliente para o título")
    p.add_argument("-o", "--output", default=None, help="HTML de saída")
    args = p.parse_args()

    if not os.path.exists(args.input):
        print(f"Arquivo não encontrado: {args.input}", file=sys.stderr); return 1

    df, meta = read_sav_auto(args.input); fix_labels_in_meta(meta)
    selected = [v.strip() for v in args.vars.split(",") if v.strip()]
    filt_vars = [v.strip() for v in args.filters.split(",") if v.strip()]
    client_name = args.cliente or ""
    out_path = args.output or os.path.splitext(args.input)[0] + "_dashboard_integrado.html"

    created_at, vars_meta, filters_meta, records = build_records_and_meta(
        df, meta, selected, filt_vars, args.input, client_name
    )

    html = render_html_integrated(os.path.basename(args.input), created_at, client_name,
                       vars_meta, filters_meta, records)
    with open(out_path, "w", encoding="utf-8") as f: f.write(html)

    mr_found = [v for v in vars_meta if v["type"] == "mr"]
    print("✅ Dashboard integrado com Dashboard Master gerado!")
    print("📱 HARMONIZADO:")
    print("   • Paleta corporativa (#4A90E2, #357ABD, #1976D2)")
    print("   • Layout otimizado para iframe") 
    print("   • Comunicação via postMessage")
    print("   • Filtros integrados com barra superior")
    
    if mr_found:
        print("\n🔍 Grupos de múltipla resposta detectados:")
        for v in mr_found:
            print(f"   • {v['title']}")
    
    print(f"\n📁 Arquivo: {out_path}")
    print("🔗 Pronto para ser usado no Dashboard Master!")
    return 0

if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(run_cli())
    else:
        sys.exit(run_gui())
