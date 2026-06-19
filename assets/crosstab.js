// ============ Tabelas Cruzadas (caderno de cruzamentos) ============
// Módulo browser + Node. Sem ES modules. Funções estatísticas puras + cálculo + render.
(function (root) {
  'use strict';

  // ---- estatística pura ----
  function effectiveBase(weights) {
    let s = 0, s2 = 0;
    for (let i = 0; i < weights.length; i++) {
      const w = weights[i] || 0;
      s += w; s2 += w * w;
    }
    if (s2 <= 0) return 0;
    return (s * s) / s2;
  }

  function pooledZProportions(p1, n1, p2, n2) {
    if (!(n1 > 0) || !(n2 > 0)) return NaN;
    const pPool = (p1 * n1 + p2 * n2) / (n1 + n2);
    const denom = Math.sqrt(pPool * (1 - pPool) * (1 / n1 + 1 / n2));
    if (!(denom > 0)) return NaN;
    return (p1 - p2) / denom;
  }

  function zMeans(m1, v1, n1, m2, v2, n2) {
    if (!(n1 > 0) || !(n2 > 0)) return NaN;
    const se = Math.sqrt((v1 / n1) + (v2 / n2));
    if (!(se > 0)) return NaN;
    return (m1 - m2) / se;
  }

  // erf por aproximação de Abramowitz & Stegun 7.1.26
  function _erf(x) {
    if (x === 0) return 0;
    const sign = x < 0 ? -1 : 1;
    x = Math.abs(x);
    const t = 1 / (1 + 0.3275911 * x);
    const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t
      - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x);
    return sign * y;
  }
  function pValueTwoSided(z) {
    if (Number.isNaN(z)) return NaN;
    // P(|Z| > |z|) = 2*(1 - Phi(|z|)); Phi(x) = 0.5*(1+erf(x/sqrt2))
    const phi = 0.5 * (1 + _erf(Math.abs(z) / Math.SQRT2));
    return 2 * (1 - phi);
  }

  function pLadderLabel(p) {
    if (Number.isNaN(p) || p >= 0.05) return '';
    if (p >= 0.01) return 'p<0,05';
    if (p >= 0.001) return 'p<0,01';
    return 'p<0,001';
  }

  function getCategories(varName, records, valueOrders) {
    if (valueOrders && Array.isArray(valueOrders[varName]) && valueOrders[varName].length) {
      return valueOrders[varName].slice();
    }
    const seen = new Set();
    for (const r of records) {
      const v = r[varName];
      if (v === null || v === undefined || v === '') continue;
      if (Array.isArray(v)) continue; // banner não usa MR
      seen.add(String(v));
    }
    return Array.from(seen).sort((a, b) => a.localeCompare(b, 'pt-BR'));
  }

  function buildColumns(bannerVars, records, valueOrders) {
    const cols = [{ key: '__total__', group: 'Total', label: '', isTotal: true }];
    for (const bv of bannerVars) {
      const cats = getCategories(bv, records, valueOrders);
      for (const cat of cats) {
        cols.push({ key: bv + '||' + cat, group: bv, label: cat, bannerVar: bv, cat: cat });
      }
    }
    return cols;
  }

  function _recordsForColumn(col, records) {
    if (col.isTotal) return records;
    return records.filter(r => {
      const v = r[col.bannerVar];
      return v !== null && v !== undefined && String(v) === col.cat;
    });
  }
  function _w(r) { return (r.__weight__ === undefined || r.__weight__ === null) ? 1 : r.__weight__; }

  function _baseFor(recs) {
    let wbase = 0; const weights = [];
    for (const r of recs) { const w = _w(r); wbase += w; weights.push(w); }
    return { wbase: wbase, neff: effectiveBase(weights) };
  }

  function computeCrosstab(rowVar, columns, records) {
    const tm = { rowVar: rowVar, columns: columns, rows: [], bases: {} };

    if (rowVar.kind === 'numeric') {
      const row = { id: '__mean__', label: 'Média', cells: {} };
      for (const col of columns) {
        const recs = _recordsForColumn(col, records);
        let sw = 0, swx = 0;
        for (const r of recs) {
          const v = r[rowVar.name];
          if (v === null || v === undefined || v === '' || isNaN(Number(v))) continue;
          const w = _w(r); sw += w; swx += w * Number(v);
        }
        const mean = sw > 0 ? swx / sw : null;
        let varc = 0;
        if (mean !== null && sw > 0) {
          let swd = 0;
          for (const r of recs) {
            const v = r[rowVar.name];
            if (v === null || v === undefined || v === '' || isNaN(Number(v))) continue;
            const w = _w(r); swd += w * Math.pow(Number(v) - mean, 2);
          }
          varc = swd / sw;
        }
        const valid = recs.filter(r => {
          const v = r[rowVar.name];
          return !(v === null || v === undefined || v === '' || isNaN(Number(v)));
        });
        const b = _baseFor(valid);
        row.cells[col.key] = { mean: mean, variance: varc, neff: b.neff };
        tm.bases[col.key] = b;
      }
      tm.rows.push(row);
      return tm;
    }

    // categorical ou mr: descobrir as linhas
    let rowKeys;
    if (rowVar.kind === 'mr') {
      const set = new Set();
      for (const r of records) {
        const v = r[rowVar.name];
        if (Array.isArray(v)) for (const it of v) { if (it !== null && it !== undefined && it !== '') set.add(String(it)); }
      }
      rowKeys = Array.from(set).sort((a, b) => a.localeCompare(b, 'pt-BR'));
    } else {
      rowKeys = getCategories(rowVar.name, records, {}); // ordem por dados; valueOrders aplicado pelo chamador via getCategories no render
    }

    for (const col of columns) {
      const recs = _recordsForColumn(col, records);
      // base da coluna: válidos (não-nulos) para a linha-variável
      let validRecs;
      if (rowVar.kind === 'mr') {
        validRecs = recs.filter(r => Array.isArray(r[rowVar.name]));
      } else {
        validRecs = recs.filter(r => {
          const v = r[rowVar.name];
          return !(v === null || v === undefined || v === '');
        });
      }
      const b = _baseFor(validRecs);
      tm.bases[col.key] = b;
      // acumular por categoria de linha
      for (let i = 0; i < rowKeys.length; i++) {
        const rk = rowKeys[i];
        if (!tm.rows[i]) tm.rows[i] = { id: rk, label: rk, cells: {} };
        let wsel = 0;
        for (const r of validRecs) {
          const v = r[rowVar.name];
          const hit = rowVar.kind === 'mr'
            ? (Array.isArray(v) && v.map(String).includes(rk))
            : (String(v) === rk);
          if (hit) wsel += _w(r);
        }
        const pct = b.wbase > 0 ? wsel / b.wbase : null;
        tm.rows[i].cells[col.key] = { pct: pct, wcount: wsel, neff: b.neff };
      }
    }
    return tm;
  }

  const API = {
    effectiveBase, pooledZProportions, zMeans, pValueTwoSided, pLadderLabel,
    getCategories, buildColumns, computeCrosstab
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.Crosstab = API;
})(typeof window !== 'undefined' ? window : globalThis);
