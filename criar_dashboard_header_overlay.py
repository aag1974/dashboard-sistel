#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de Dashboard SPSS - Versão com Header Sobreposto

ARQUITETURA APRIMORADA:
- Header fixo da análise SPSS sobrepõe o Dashboard Master
- Dashboard Master só fornece menu lateral
- Filtros em dropdown compactos em linha única
- Comunicação via postMessage para sincronizar interface
- Layout otimizado para máximo aproveitamento de espaço
"""

from __future__ import annotations
import os, sys, json, re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import pyreadstat

# Truncagem de rótulos no gráfico
CHART_LABEL_MAX = 40

# ---------- TODAS AS FUNÇÕES CORE ORIGINAIS MANTIDAS (mesmo código) ----------

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

def _normalize_display_value(val: str) -> str:
    """Remove .0 de números para consistência entre filtros e records"""
    if val.replace('.', '').replace('-', '').isdigit() and val.endswith('.0'):
        return val[:-2]
    return val

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
            processed_val = _normalize_display_value(processed_val)
            
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
                rec[fv] = _normalize_display_value(str(valabs.get(fv, {}).get(val, val)).replace(":", "").strip())
        
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
                    processed_val = _normalize_display_value(processed_val)
                    
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

# ---------- RENDERIZAÇÃO HTML COM HEADER SOBREPOSTO ----------

def render_html_header_overlay(file_name: str, created_at: str, client_name: str,
                               vars_meta: List[Dict[str, Any]], filters_meta: List[Dict[str, Any]],
                               records: List[Dict[str, Any]]) -> str:
    """
    Renderização HTML com Header Sobreposto ao Dashboard Master
    - Header fixo que ocupa todo o topo da tela
    - Filtros em dropdown compactos em linha única
    - Comunicação com Dashboard Master para sincronizar interface
    - Layout sem margens para aproveitamento máximo
    """
    title_extra = f" — Para {client_name}" if client_name.strip() else ""
    
    # CSS PARA HEADER SOBREPOSTO E FILTROS COMPACTOS
    css = """
/* ========= PALETA CORPORATIVA ========= */
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
    --shadow-lg: 0 4px 20px rgba(0,0,0,0.15);
    --radius: 6px;
    --radius-lg: 10px;
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
    line-height: 1.5;
    margin: 0;
    padding: 0;
    overflow-x: hidden;
}

/* ========= HEADER FIXO SOBREPOSTO ========= */
.analysis-header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
    color: white;
    box-shadow: var(--shadow-lg);
    z-index: 10000; /* SOBREPÕE TUDO */
    border-bottom: 3px solid var(--secondary);
}

.header-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}

.header-title {
    display: flex;
    flex-direction: column;
}

.header-title h1 {
    font-size: 20px;
    font-weight: 600;
    margin: 0;
}

.header-subtitle {
    font-size: 12px;
    opacity: 0.9;
    margin-top: 2px;
}

.header-actions {
    display: flex;
    align-items: center;
    gap: 10px;
}

.header-btn {
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.3);
    color: white;
    padding: 6px 12px;
    border-radius: var(--radius);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    gap: 5px;
    font-weight: 500;
}

.header-btn:hover {
    background: rgba(255,255,255,0.25);
    transform: translateY(-1px);
}

.header-btn:active {
    transform: translateY(0);
}

.header-status {
    font-size: 11px;
    padding: 4px 8px;
    background: rgba(255,255,255,0.1);
    border-radius: 15px;
    border: 1px solid rgba(255,255,255,0.2);
}

/* ========= NOVO LAYOUT DE FILTROS SOFISTICADO ========= */
.filters-section {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: var(--radius);
    margin: 20px;
    box-shadow: var(--shadow);
}

.filters-header {
    background: linear-gradient(135deg, var(--primary), var(--primary-dark));
    color: white;
    padding: 15px 20px;
    border-radius: var(--radius) var(--radius) 0 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.filters-title {
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 0.5px;
}

.filters-actions {
    display: flex;
    gap: 10px;
}

.btn-apply {
    background: rgba(255,255,255,0.2);
    border: 1px solid rgba(255,255,255,0.4);
    color: white;
    padding: 8px 16px;
    border-radius: var(--radius);
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
}

.btn-apply:hover {
    background: rgba(255,255,255,0.3);
    transform: translateY(-1px);
}

.btn-clear {
    background: transparent;
    border: 1px solid rgba(255,255,255,0.4);
    color: rgba(255,255,255,0.9);
    padding: 8px 16px;
    border-radius: var(--radius);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.3s ease;
}

.btn-clear:hover {
    background: rgba(255,255,255,0.1);
}

.filters-content {
    padding: 20px;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 25px;
}

.filter-group {
    display: flex;
    flex-direction: column;
}

.filter-group-title {
    font-size: 12px;
    font-weight: 600;
    color: #666;
    text-transform: uppercase;
    margin-bottom: 10px;
    letter-spacing: 0.5px;
}

/* Filtro tipo Checkbox (para faixas) */
.filter-checkbox-container {
    border: 1px solid #e0e0e0;
    border-radius: var(--radius);
    background: #f9f9f9;
}

.filter-checkbox-header {
    background: var(--primary);
    color: white;
    padding: 8px 12px;
    border-radius: var(--radius) var(--radius) 0 0;
    font-size: 13px;
    font-weight: 600;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.selection-count {
    background: rgba(255,255,255,0.2);
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 11px;
}

.filter-checkbox-list {
    max-height: 200px;
    overflow-y: auto;
    padding: 8px 0;
}

.checkbox-item {
    display: flex;
    align-items: center;
    padding: 6px 12px;
    cursor: pointer;
    transition: background 0.2s;
}

.checkbox-item:hover {
    background: #f0f0f0;
}

.checkbox-item input[type="checkbox"] {
    margin-right: 8px;
    width: 16px;
    height: 16px;
    accent-color: var(--primary);
}

.checkbox-item label {
    font-size: 13px;
    color: #333;
    cursor: pointer;
    flex: 1;
}

.select-all-item {
    border-bottom: 1px solid #e0e0e0;
    font-weight: 600;
    background: #f5f5f5;
}

/* Filtro tipo Dropdown */
.filter-dropdown-container {
    position: relative;
}

.filter-select-new {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid #d0d0d0;
    border-radius: var(--radius);
    background: white;
    font-size: 13px;
    color: #333;
    cursor: pointer;
    transition: all 0.3s ease;
}

.filter-select-new:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.2);
}

.filter-select-new:hover {
    border-color: var(--primary);
}

.filter-select-new option {
    padding: 8px 12px;
    font-size: 13px;
}

/* Responsividade */
@media (max-width: 768px) {
    .filters-content {
        grid-template-columns: 1fr;
        gap: 20px;
    }
    
    .filters-header {
        flex-direction: column;
        gap: 10px;
        text-align: center;
    }
}

/* ========= CONTEÚDO PRINCIPAL ========= */
.content-area {
    margin-top: 120px; /* Espaço para header fixo */
    padding: 20px;
    min-height: calc(100vh - 120px);
}

/* ========= CARDS DAS VARIÁVEIS ========= */
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
    height: 300px;
    cursor: pointer;
}

/* ========= ALERTAS ========= */
.low-n-warning {
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.3);
    color: #92400e;
    padding: 10px 15px;
    border-radius: var(--radius);
    margin-top: 15px;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.low-n-warning::before {
    content: "⚠️";
    font-size: 14px;
}

.selection-info-box {
    background: rgba(25, 118, 210, 0.05);
    border: 1px solid rgba(25, 118, 210, 0.2);
    border-radius: var(--radius);
    padding: 10px 15px;
    margin: 10px 0;
    font-size: 12px;
}

.selection-info-title {
    color: var(--secondary);
    font-weight: 600;
    margin-bottom: 4px;
}

.selection-info-items {
    color: var(--text-light);
}

/* ========= RESPONSIVIDADE ========= */
@media (max-width: 768px) {
    .header-top {
        flex-direction: column;
        gap: 8px;
        padding: 10px 15px;
    }

    .filters-bar {
        flex-direction: column;
        align-items: stretch;
        gap: 8px;
        padding: 10px 15px;
    }

    .filter-dropdown {
        min-width: 100%;
    }

    .filters-actions {
        margin-left: 0;
        justify-content: center;
    }

    .content-area {
        margin-top: 140px;
        padding: 15px;
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
    padding: 20px;
    color: var(--text-muted);
    font-size: 12px;
    border-top: 1px solid var(--border-light);
    margin-top: 30px;
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
    <!-- HEADER FIXO SOBREPOSTO -->
    <header class="analysis-header" id="analysisHeader">
        <!-- Linha superior: título e ações -->
        <div class="header-top">
            <div class="header-title">
                <h1>📊 {file_name_safe}{title_extra}</h1>
                <div class="header-subtitle">Gerado: {created_at_safe} | Opinião Informação Estratégica</div>
            </div>
            <div class="header-actions">
                <div class="header-status" id="headerStatus">
                    <span id="statusIndicator">🔄 Carregando...</span>
                </div>
                <button class="header-btn" id="btnExportHeader">📊 Exportar CSV</button>
                <button class="header-btn" id="btnFullscreen">⛶ Tela Cheia</button>
            </div>
        </div>

        <!-- Nova seção de filtros sofisticada -->
        <div class="filters-section" id="filtersSection">
            <div class="filters-header">
                <div class="filters-title">🔍 FILTROS DE SELEÇÃO</div>
                <div class="filters-actions">
                    <button class="btn-apply" id="btnApplyFilters">✓ Aplicar Filtros</button>
                    <button class="btn-clear" id="btnClearFilters">🔄 Limpar Filtros</button>
                </div>
            </div>
            <div class="filters-content" id="filtersContainer">
                <!-- Filtros serão gerados dinamicamente aqui -->
            </div>
        </div>
    </header>

    <!-- ÁREA DE CONTEÚDO -->
    <main class="content-area">
        <div id="tablesContainer">
            <!-- Tabelas e gráficos serão gerados aqui -->
        </div>

        <footer class="content-footer">
            Confidencial - Reprodução proibida
        </footer>
    </main>

<script>
// ========= VARIÁVEIS GLOBAIS =========
const VARS = {js_vars};
const FILTERS = {js_filters};
const RECORDS = {js_records};
const CHART_LABEL_MAX = {CHART_LABEL_MAX};
// Função utilitária para sanitizar nomes de filtros e variáveis para uso em IDs HTML.
function sanitize(name) {{
    return String(name).replace(/[^A-Za-z0-9_-]/g, '_');
}}

// Sistema de seleção múltipla nos gráficos (ORIGINAL)
let graphSelections = {{}};
let charts = {{}};

// ========= COMUNICAÇÃO COM DASHBOARD MASTER =========
function notifyDashboardMaster(type, data) {{
    if (window.parent !== window) {{
        try {{
            window.parent.postMessage({{
                source: 'spss-analysis-overlay',
                type: type,
                data: data,
                filename: '{file_name_safe}'
            }}, '*');
        }} catch (e) {{
            console.log('Dashboard Master não detectado:', e);
        }}
    }}
}}

function updateStatus(text, type = 'info') {{
    const indicator = document.getElementById('statusIndicator');
    const icons = {{
        'info': '📊',
        'loading': '🔄', 
        'success': '✅',
        'warning': '⚠️',
        'error': '❌'
    }};
    
    indicator.textContent = `${{icons[type] || '📊'}} ${{text}}`;
    
    // Notifica Dashboard Master
    notifyDashboardMaster('status-update', {{ text, type }});
}}

// ========= INICIALIZAÇÃO ========= 
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
    updateSelectionsInfo();
    
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
    updateSelectionsInfo();
    updateStatus('Seleções limpas', 'success');
    
    notifyDashboardMaster('selections-cleared', {{}});
}}

function updateSelectionsInfo() {{
    const totalSelections = Object.values(graphSelections).reduce((total, selections) => {{
        return total + (selections ? selections.length : 0);
    }}, 0);
    
    const btn = document.getElementById('btnSelectionsInfo');
    if (totalSelections > 0) {{
        btn.style.display = 'block';
        btn.textContent = `🎯 ${{totalSelections}} seleções`;
    }} else {{
        btn.style.display = 'none';
    }}
}}

function buildFilters() {{
    const container = document.getElementById('filtersContainer');
    container.innerHTML = '';
    
    if (FILTERS.length === 0) {{
        const noFilters = document.createElement('div');
        noFilters.style.color = '#999';
        noFilters.style.fontStyle = 'italic';
        noFilters.style.textAlign = 'center';
        noFilters.style.padding = '40px 20px';
        noFilters.textContent = 'Nenhum filtro configurado';
        container.appendChild(noFilters);
        return;
    }}
    
    FILTERS.forEach(filter => {{
        const filterGroup = document.createElement('div');
        filterGroup.className = 'filter-group';
        
        const title = document.createElement('div');
        title.className = 'filter-group-title';
        title.textContent = filter.title.toUpperCase();
        filterGroup.appendChild(title);
        
        // Decidir tipo de filtro baseado no nome ou tipo de dados
        const filterType = detectFilterType(filter);
        
        if (filterType === 'checkbox') {{
            // Filtro tipo checkbox para faixas
            const checkboxContainer = createCheckboxFilter(filter);
            filterGroup.appendChild(checkboxContainer);
        }} else {{
            // Filtro tipo dropdown para categorias
            const dropdownContainer = createDropdownFilter(filter);
            filterGroup.appendChild(dropdownContainer);
        }}
        
        container.appendChild(filterGroup);
    }});
}}

function detectFilterType(filter) {{
    // Detecta se deve ser checkbox ou dropdown baseado nos dados
    const name = filter.name.toLowerCase();
    const title = filter.title.toLowerCase();
    
    // Palavras-chave que indicam faixas numéricas (checkbox)
    const rangeKeywords = ['valor', 'preço', 'price', 'faixa', 'range', 'ano', 'year'];
    
    // Se contém indicadores de faixa ou tem muitas opções numéricas
    if (rangeKeywords.some(keyword => name.includes(keyword) || title.includes(keyword))) {{
        return 'checkbox';
    }}
    
    // Se tem muitos valores ou parece ser faixa numérica
    if (filter.values.length > 8 || filter.values.some(v => v.includes('-') || v.includes('<') || v.includes('>'))) {{
        return 'checkbox';
    }}
    
    // Senão, é dropdown simples
    return 'dropdown';
}}

function createCheckboxFilter(filter) {{
    const container = document.createElement('div');
    container.className = 'filter-checkbox-container';
    
    // Header com contador de selecionados
    const header = document.createElement('div');
    header.className = 'filter-checkbox-header';
    const sanitized = sanitize(filter.name);
    header.innerHTML = `
        <span id="filter-count-${{sanitized}}">0 selecionados</span>
        <span class="selection-count">▼</span>
    `;
    container.appendChild(header);
    
    // Lista de checkboxes
    const list = document.createElement('div');
    list.className = 'filter-checkbox-list';
    
    // Opção "Selecionar Todos"
    const selectAllItem = document.createElement('div');
    selectAllItem.className = 'checkbox-item select-all-item';
    selectAllItem.innerHTML = `
        <input type="checkbox" id="selectAll_${{sanitized}}" />
        <label for="selectAll_${{sanitized}}">Selecionar Todos</label>
    `;
    list.appendChild(selectAllItem);
    
    // Opções individuais
    filter.values.forEach((value, index) => {{
        const item = document.createElement('div');
        item.className = 'checkbox-item';
        
        const checkboxId = `filter_${{sanitized}}_${{index}}`;
        item.innerHTML = `
            <input type="checkbox" id="${{checkboxId}}" value="${{value}}" />
            <label for="${{checkboxId}}">${{value}}</label>
        `;
        list.appendChild(item);
    }});
    
    container.appendChild(list);
    
    // Event listeners para checkboxes
    setupCheckboxEvents(filter, container);
    
    return container;
}}

function createDropdownFilter(filter) {{
    const container = document.createElement('div');
    container.className = 'filter-dropdown-container';
    
    const sanitized = sanitize(filter.name);
    const select = document.createElement('select');
    select.id = `filter_${{sanitized}}`;
    select.className = 'filter-select-new';
    select.title = filter.title;
    
    // Opção "Todos"
    const allOption = document.createElement('option');
    allOption.value = '';
    allOption.textContent = 'Todos';
    allOption.selected = true;
    select.appendChild(allOption);
    
    // Opções específicas
    filter.values.forEach(value => {{
        const option = document.createElement('option');
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
    }});
    
    // Event listener
    select.addEventListener('change', () => {{
        updateFilterStatus();
    }});
    
    container.appendChild(select);
    return container;
}}

function setupCheckboxEvents(filter, container) {{
    const sanitized = sanitize(filter.name);
    const selectAllCheckbox = container.querySelector(`#selectAll_${{sanitized}}`);
    const individualCheckboxes = container.querySelectorAll('input[value]');
    
    // Selecionar/deselecionar todos
    selectAllCheckbox.addEventListener('change', () => {{
        const isChecked = selectAllCheckbox.checked;
        individualCheckboxes.forEach(cb => {{
            cb.checked = isChecked;
        }});
        updateCheckboxCounter(filter, container);
    }});
    
    // Checkboxes individuais
    individualCheckboxes.forEach(checkbox => {{
        checkbox.addEventListener('change', () => {{
            updateCheckboxCounter(filter, container);
            
            // Atualizar estado do "Selecionar Todos"
            const checkedCount = Array.from(individualCheckboxes).filter(cb => cb.checked).length;
            selectAllCheckbox.checked = checkedCount === individualCheckboxes.length;
            selectAllCheckbox.indeterminate = checkedCount > 0 && checkedCount < individualCheckboxes.length;
        }});
    }});
}}

function updateCheckboxCounter(filter, container) {{
    const sanitized = sanitize(filter.name);
    const counter = container.querySelector(`#filter-count-${{sanitized}}`);
    const checkedBoxes = container.querySelectorAll('input[value]:checked');
    const count = checkedBoxes.length;
    
    if (count === 0) {{
        counter.textContent = 'Nenhum selecionado';
    }} else if (count === 1) {{
        counter.textContent = '1 selecionado';
    }} else {{
        counter.textContent = `${{count}} selecionados`;
    }}
}}

function updateFilterStatus() {{
    // Atualiza contadores e estado visual dos filtros
    FILTERS.forEach(filter => {{
        const sanitized = sanitize(filter.name);
        const counterElem = document.querySelector(`#filter-count-${{sanitized}}`);
        const container = counterElem ? counterElem.closest('.filter-checkbox-container') : null;
        if (container) {{
            updateCheckboxCounter(filter, container);
        }}
    }});
}}

function applyFilters() {{
    renderAll();
    updateStatus('Filtros aplicados', 'success');
    
    notifyDashboardMaster('filters-applied', {{
        appliedFilters: getAppliedFiltersInfo()
    }});
}}

function getAppliedFiltersInfo() {{
    const applied = [];
    
    FILTERS.forEach(filter => {{
        const sanitized = sanitize(filter.name);
        const filterType = detectFilterType(filter);
        
        if (filterType === 'checkbox') {{
            const checkedBoxes = document.querySelectorAll(`input[type="checkbox"][id^="filter_${{sanitized}}_"]:checked[value]`);
            if (checkedBoxes.length > 0) {{
                applied.push({{
                    name: filter.name,
                    title: filter.title,
                    type: 'checkbox',
                    selected: Array.from(checkedBoxes).map(cb => cb.value)
                }});
            }}
        }} else {{
            const selectEl = document.getElementById(`filter_${{sanitized}}`);
            if (selectEl && selectEl.value) {{
                applied.push({{
                    name: filter.name,
                    title: filter.title,
                    type: 'dropdown',
                    selected: selectEl.value
                }});
            }}
        }}
    }});
    
    return applied;
}}

function applyFilters() {{
    renderAll();
}}

function clearFilters() {{
    FILTERS.forEach(filter => {{
        const sanitized = sanitize(filter.name);
        const filterType = detectFilterType(filter);
        
        if (filterType === 'checkbox') {{
            // Limpar checkboxes
            const checkboxes = document.querySelectorAll(`input[type="checkbox"][id^="filter_${{sanitized}}_"]`);
            checkboxes.forEach(cb => {{
                cb.checked = false;
                cb.indeterminate = false;
            }});
            // Limpar seletor "Selecionar Todos"
            const selectAll = document.getElementById(`selectAll_${{sanitized}}`);
            if (selectAll) {{
                selectAll.checked = false;
                selectAll.indeterminate = false;
            }}
            // Atualizar contador
            const counterElem = document.querySelector(`#filter-count-${{sanitized}}`);
            const container = counterElem ? counterElem.closest('.filter-checkbox-container') : null;
            if (container) {{
                updateCheckboxCounter(filter, container);
            }}
        }} else {{
            // Limpar dropdown
            const selectEl = document.getElementById(`filter_${{sanitized}}`);
            if (selectEl) {{
                selectEl.value = '';
            }}
        }}
    }});
    
    renderAll();
    updateStatus('Todos os filtros foram limpos', 'success');
    
    notifyDashboardMaster('filters-cleared', {{}});
}}

function getFilteredRecords() {{
    return RECORDS.filter(record => {{
        // Aplicar todos os filtros
        const passesFilters = FILTERS.every(filter => {{
            const sanitized = sanitize(filter.name);
            const filterType = detectFilterType(filter);
            
            if (filterType === 'checkbox') {{
                // Filtro checkbox - verificar se algum está selecionado
                const checkedBoxes = document.querySelectorAll(`input[type="checkbox"][id^="filter_${{sanitized}}_"]:checked[value]`);
                
                // Se nenhum checkbox marcado, passar todos os registros
                if (checkedBoxes.length === 0) {{
                    return true;
                }}
                
                // Verificar se o valor do record corresponde a algum checkbox marcado
                const recVal = record[filter.name];
                const recordValue = (recVal === null || recVal === undefined) ? '' : String(recVal);
                return Array.from(checkedBoxes).some(cb => String(cb.value) === recordValue);
                
            }} else {{
                // Filtro dropdown
                const selectEl = document.getElementById(`filter_${{sanitized}}`);
                if (!selectEl) return true;
                
                const selectedValue = selectEl.value;
                if (!selectedValue) return true; // "Todos" selecionado
                
                const recVal = record[filter.name];
                const recordValue = (recVal === null || recVal === undefined) ? '' : String(recVal);
                return recordValue === selectedValue;
            }}
        }});
        
        // Filtros de seleção dos gráficos (mantido original)
        const passesSelections = Object.entries(graphSelections).every(([varName, selectedValues]) => {{
            if (!selectedValues || selectedValues.length === 0) return true;
            
            const recordValue = record[varName];
            
            if (typeof recordValue === 'string' || typeof recordValue === 'number') {{
                return selectedValues.includes(String(recordValue));
            }}
            
            if (Array.isArray(recordValue)) {{
                return selectedValues.some(selection => recordValue.includes(selection));
            }}
            
            return true;
        }});
        
        return passesFilters && passesSelections;
    }});
}}

function renderAll() {{
    const filtered = getFilteredRecords();
    const container = document.getElementById('tablesContainer');
    container.innerHTML = '';
    
    updateStatus(`${{filtered.length}} registros • ${{VARS.length}} variáveis`, 'info');
    
    VARS.forEach(varMeta => {{
        renderVariableCard(varMeta, filtered, container);
    }});
}}

function renderVariableCard(varMeta, filtered, container) {{
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
        // LÓGICA ORIGINAL PARA SINGLE MANTIDA
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
            totalRow.innerHTML = `<td>Total</td><td>${{total}}</td><td>100,0%</td>`;
            tbody.appendChild(totalRow);
            
            table.appendChild(tbody);
            card.appendChild(table);
            
            if (total < 30) {{
                const warning = document.createElement('div');
                warning.className = 'low-n-warning';
                warning.textContent = 'n < 30: sem representatividade estatística.';
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
        // LÓGICA ORIGINAL PARA MR MANTIDA
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
            thead.innerHTML = '<tr><th>Opção</th><th>N</th><th>%</th></tr>';
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
            totalRow.innerHTML = `<td>Base: Respondentes</td><td>${{questionRespondents}}</td><td>100,0%</td>`;
            tbody.appendChild(totalRow);
            
            table.appendChild(tbody);
            card.appendChild(table);
            
            if (questionRespondents < 30) {{
                const warning = document.createElement('div');
                warning.className = 'low-n-warning';
                warning.textContent = 'n < 30: sem representatividade estatística.';
                card.appendChild(warning);
            }}
            
            // Gráfico MR
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
        indicator.textContent = `${{selections.length}} seleção${{selections.length > 1 ? 'ões' : ''}}`;
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
function exportCSV() {{
    const filtered = getFilteredRecords();
    
    if (filtered.length === 0) {{
        alert('Nenhum dado para exportar.');
        return;
    }}
    
    function escapeCsvField(value) {{
        let str = String(value || '');
        if (str.includes(';') || str.includes('"')) {{
            str = '"' + str.replace(/"/g, '""') + '"';
        }}
        return str;
    }}
    
    let csvContent = '\\ufeff'; // BOM para UTF-8
    
    VARS.forEach((varMeta, varIndex) => {{
        if (varIndex > 0) csvContent += '\\n\\n';
        
        csvContent += `"${{varMeta.title.replace(/"/g, '""')}}"\\n`;
        
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
                
                csvContent += `${{escapeCsvField('Total')}};${{total}};100,0%\\n`;
            }}
        }} else {{
            // Lógica MR original
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
                
                csvContent += 'Opção;N;%\\n';
                
                entries.forEach(([opt, count]) => {{
                    const pct = ((count / questionRespondents) * 100).toFixed(1).replace('.', ',') + '%';
                    csvContent += `${{escapeCsvField(opt)}};${{count}};${{pct}}\\n`;
                }});
                
                csvContent += `${{escapeCsvField('Base: Respondentes')}};${{questionRespondents}};100,0%\\n`;
            }}
        }}
    }});
    
    const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'analise_spss.csv';
    link.click();
    
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    
    updateStatus('CSV exportado', 'success');
    notifyDashboardMaster('data-exported', {{ filename: 'analise_spss.csv' }});
}}

function toggleFullscreen() {{
    if (!document.fullscreenElement) {{
        document.documentElement.requestFullscreen();
        updateStatus('Modo tela cheia ativado', 'info');
    }} else {{
        document.exitFullscreen();
        updateStatus('Tela cheia desativada', 'info');
    }}
}}

// ========= EVENT LISTENERS E INICIALIZAÇÃO =========
document.addEventListener('DOMContentLoaded', () => {{
    // Event listeners
    document.getElementById('btnExportHeader').addEventListener('click', exportCSV);
    document.getElementById('btnApplyFilters').addEventListener('click', applyFilters);
    document.getElementById('btnClearFilters').addEventListener('click', clearFilters);
    document.getElementById('btnSelectionsInfo').addEventListener('click', clearAllSelections);
    document.getElementById('btnFullscreen').addEventListener('click', toggleFullscreen);
    
    // Inicialização
    initializeSelections();
    buildFilters();
    renderAll();
    updateSelectionsInfo();
    
    // Notifica Dashboard Master que carregou
    notifyDashboardMaster('analysis-loaded', {{
        title: '{file_name_safe}',
        variables: VARS.length,
        filters: FILTERS.length,
        records: RECORDS.length,
        hasOverlayHeader: true
    }});
    
    updateStatus('Análise carregada', 'success');
    
    console.log('📊 Dashboard SPSS com Header Sobreposto carregado!');
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
                exportCSV();
                break;
            case 'toggle-fullscreen':
                toggleFullscreen();
                break;
        }}
    }}
}});

// Detecta mudanças de tela cheia
document.addEventListener('fullscreenchange', () => {{
    const btn = document.getElementById('btnFullscreen');
    if (document.fullscreenElement) {{
        btn.innerHTML = '⛗ Sair Tela Cheia';
    }} else {{
        btn.innerHTML = '⛶ Tela Cheia';
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

        default_out = os.path.splitext(in_path)[0] + "_dashboard_header_overlay.html"
        out_path = filedialog.asksaveasfilename(parent=root, title="Salvar dashboard HTML como...",
                            defaultextension=".html", initialfile=os.path.basename(default_out),
                            filetypes=[("HTML", "*.html")]) or default_out

        print("⚙️ Processando dados...")
        created_at, vars_meta, filters_meta, records = build_records_and_meta(
            df, meta, selected, filt_vars, in_path, client_name
        )

        print("🎨 Gerando HTML com header sobreposto...")
        html = render_html_header_overlay(os.path.basename(in_path), created_at, client_name,
                           vars_meta, filters_meta, records)
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)

        mr_found = [v for v in vars_meta if v["type"] == "mr"]
        if mr_found:
            mr_info = "\n".join([f"• {v['title']}" for v in mr_found])
            messagebox.showinfo("Dashboard com Header Sobreposto - Concluído",
                               f"✅ Dashboard com header sobreposto criado!\n\n🎯 FUNCIONALIDADES:\n• Header fixo que sobrepõe Dashboard Master\n• Filtros dropdown compactos\n• Comunicação bidirecional\n• Layout otimizado\n\n🔍 Múltipla resposta detectada:\n\n{mr_info}",
                               parent=root)
        else:
            messagebox.showinfo("Dashboard com Header Sobreposto - Concluído", 
                               "✅ Dashboard com header sobreposto criado!\n\n🎯 FUNCIONALIDADES:\n• Header fixo que sobrepõe Dashboard Master\n• Filtros dropdown compactos em linha\n• Comunicação bidirecional via postMessage\n• Layout otimizado para máximo aproveitamento\n\n🔍 Nenhum grupo de múltipla resposta detectado.",
                               parent=root)

        root.destroy()
        print(f"✅ HTML com header sobreposto: {out_path}")
        print("🔗 Este arquivo ocupa toda a tela no Dashboard Master!")
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
    p = argparse.ArgumentParser(description="Dashboard SPSS com header sobreposto.")
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
    out_path = args.output or os.path.splitext(args.input)[0] + "_dashboard_header_overlay.html"

    created_at, vars_meta, filters_meta, records = build_records_and_meta(
        df, meta, selected, filt_vars, args.input, client_name
    )

    html = render_html_header_overlay(os.path.basename(args.input), created_at, client_name,
                       vars_meta, filters_meta, records)
    with open(out_path, "w", encoding="utf-8") as f: f.write(html)

    mr_found = [v for v in vars_meta if v["type"] == "mr"]
    print("✅ Dashboard com Header Sobreposto gerado!")
    print("🎯 FUNCIONALIDADES IMPLEMENTADAS:")
    print("   • Header fixo que sobrepõe o Dashboard Master")
    print("   • Filtros dropdown compactos em linha única")
    print("   • Comunicação bidirecional via postMessage")
    print("   • Layout otimizado para máximo aproveitamento")
    print("   • Paleta corporativa harmonizada (#4A90E2)")
    
    if mr_found:
        print("\n🔍 Grupos de múltipla resposta detectados:")
        for v in mr_found:
            print(f"   • {v['title']}")
    
    print(f"\n📁 Arquivo: {out_path}")
    print("🔗 Pronto para uso no Dashboard Master - ocupa toda a tela!")
    return 0

if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(run_cli())
    else:
        sys.exit(run_gui())
