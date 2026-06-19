#!/usr/bin/env python3
"""Confere % de coluna ponderada e z-test de um cruzamento categórico
contra o que o dashboard mostra. Uso:
    python3 tests/crosstab/verify_reference.py CAMINHO.sav VAR_LINHA VAR_COLUNA [VAR_PESO]
"""
import sys, math
import pandas as pd
import pyreadstat

def main():
    path, rowv, colv = sys.argv[1], sys.argv[2], sys.argv[3]
    wv = sys.argv[4] if len(sys.argv) > 4 else None
    df, meta = pyreadstat.read_sav(path, apply_value_formats=True)
    df = df[[c for c in [rowv, colv, wv] if c]].dropna(subset=[rowv, colv])
    w = df[wv].fillna(1.0) if wv else pd.Series(1.0, index=df.index)
    for cat in sorted(df[colv].astype(str).unique()):
        sub = df[df[colv].astype(str) == cat]
        ws = w.loc[sub.index]
        base = ws.sum()
        neff = (ws.sum() ** 2) / (ws.pow(2).sum()) if ws.pow(2).sum() else 0
        print(f"\n[{colv}={cat}] base_pond={base:.0f} n_eff={neff:.1f}")
        for rk in sorted(sub[rowv].astype(str).unique()):
            sel = ws.loc[sub[sub[rowv].astype(str) == rk].index].sum()
            print(f"   {rk:<24} {100*sel/base:5.1f}%")

if __name__ == "__main__":
    main()
