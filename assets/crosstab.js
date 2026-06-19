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

  function computeCrosstab(rowVar, columns, records, valueOrders) {
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
      rowKeys = getCategories(rowVar.name, records, valueOrders || {});
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

  var MIN_NEFF = 30;

  function _groupColumns(columns) {
    // mapa bannerVar -> [colunas do grupo] (exclui Total)
    const m = {};
    for (const c of columns) {
      if (c.isTotal) continue;
      (m[c.bannerVar] = m[c.bannerVar] || []).push(c);
    }
    return m;
  }

  function applySignificance(tm) {
    const groups = _groupColumns(tm.columns);
    const isNumeric = tm.rowVar.kind === 'numeric';

    for (const col of tm.columns) {
      for (const row of tm.rows) {
        if (col.isTotal) { row.cells[col.key].sig = { dir: 0, label: '' }; continue; }
        const grp = groups[col.bannerVar] || [];
        const rest = grp.filter(c => c.key !== col.key);
        const cell = row.cells[col.key];

        if (rest.length === 0) { cell.sig = { dir: 0, label: '' }; continue; }

        if (isNumeric) {
          const nC = cell.neff, mC = cell.mean, vC = cell.variance;
          // resto: combinar média/variância ponderadas pelas bases efetivas
          let nR = 0, sumW = 0, swx = 0;
          for (const c of rest) { const cc = row.cells[c.key]; if (cc.mean === null) continue; nR += cc.neff; sumW += cc.neff; swx += cc.neff * cc.mean; }
          const mR = sumW > 0 ? swx / sumW : null;
          let vR = 0; if (mR !== null && sumW > 0) { let s=0; for (const c of rest){const cc=row.cells[c.key]; if(cc.mean===null) continue; s += cc.neff * (cc.variance + Math.pow(cc.mean-mR,2));} vR = s/sumW; }
          if (mC === null || mR === null || nC < MIN_NEFF || nR < MIN_NEFF) { cell.sig = { dir: 0, label: '' }; continue; }
          const z = zMeans(mC, vC, nC, mR, vR, nR);
          const p = pValueTwoSided(z);
          const label = pLadderLabel(p);
          cell.sig = { dir: label ? (mC > mR ? 1 : -1) : 0, label: label };
        } else {
          const pC = cell.pct, nC = cell.neff;
          let nR = 0, selR = 0;
          for (const c of rest) { const cc = row.cells[c.key]; const b = tm.bases[c.key]; nR += b.neff; selR += (cc.pct === null ? 0 : cc.pct) * b.neff; }
          const pR = nR > 0 ? selR / nR : null;
          if (pC === null || pR === null || nC < MIN_NEFF || nR < MIN_NEFF) { cell.sig = { dir: 0, label: '' }; continue; }
          const z = pooledZProportions(pC, nC, pR, nR);
          const p = pValueTwoSided(z);
          const label = pLadderLabel(p);
          cell.sig = { dir: label ? (pC > pR ? 1 : -1) : 0, label: label };
        }
      }
    }
  }

  function rowKindFromMeta(vm) {
    const t = (vm.var_type || vm.type || '').toLowerCase();
    if (t === 'multiple_response' || vm.type === 'mr') return 'mr';
    if (t === 'string' || t === 'date') return 'skip';
    if (t === 'numeric' && (vm.measure || '') === 'scale') return 'numeric';
    return 'categorical';
  }

  function _fmtPct(p) { return p === null ? '—' : Math.round(p * 100) + '%'; }
  function _fmtNum(x) { return x === null ? '—' : x.toLocaleString('pt-BR', {minimumFractionDigits:1, maximumFractionDigits:1}); }
  function _fmtBase(n) { return Math.round(n).toLocaleString('pt-BR'); }

  function _sigSpan(sig) {
    if (!sig || !sig.label) return '';
    const arrow = sig.dir === 1 ? '▲' : '▼';
    const cls = sig.dir === 1 ? 'xt-up' : 'xt-down';
    return ' <span class="' + cls + '">' + arrow + ' ' + sig.label + '</span>';
  }

  function renderCrosstabTable(tm) {
    const card = document.createElement('div');
    card.className = 'xt-card';
    const cols = tm.columns;
    const isNumeric = tm.rowVar.kind === 'numeric';

    // título
    const h = document.createElement('h2');
    h.className = 'xt-title';
    h.textContent = tm.rowVar.title || tm.rowVar.name;
    card.appendChild(h);

    const table = document.createElement('table');
    table.className = 'xt';

    // cabeçalho nível 1 (grupos)
    const groups = [];
    let i = 0;
    while (i < cols.length) {
      const g = cols[i].isTotal ? 'Total' : cols[i].group;
      let span = 0; const start = i;
      while (i < cols.length && (cols[i].isTotal ? 'Total' : cols[i].group) === g) { span++; i++; }
      groups.push({ g: g, span: span, isTotal: cols[start].isTotal });
    }
    const thead = document.createElement('thead');
    const tr1 = document.createElement('tr');
    tr1.innerHTML = '<th class="xt-rowlabel"></th>';
    for (const gr of groups) {
      const th = document.createElement('th');
      th.className = 'xt-grp' + (gr.isTotal ? ' xt-total' : '');
      th.colSpan = gr.span; th.textContent = gr.g;
      tr1.appendChild(th);
    }
    thead.appendChild(tr1);
    const tr2 = document.createElement('tr');
    tr2.innerHTML = '<th class="xt-rowlabel"></th>';
    for (const c of cols) {
      const th = document.createElement('th');
      th.className = 'xt-cat' + (c.isTotal ? ' xt-total' : '');
      th.textContent = c.isTotal ? '' : c.label;
      tr2.appendChild(th);
    }
    thead.appendChild(tr2);
    table.appendChild(thead);

    // corpo
    const tbody = document.createElement('tbody');
    for (const row of tm.rows) {
      const tr = document.createElement('tr');
      const tdl = document.createElement('td');
      tdl.className = 'xt-rowlabel'; tdl.textContent = row.label;
      tr.appendChild(tdl);
      for (const c of cols) {
        const cell = row.cells[c.key];
        const td = document.createElement('td');
        if (c.isTotal) td.className = 'xt-total-col';
        const val = isNumeric ? _fmtNum(cell.mean) : _fmtPct(cell.pct);
        td.innerHTML = val + _sigSpan(cell.sig);
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    // base
    const trb = document.createElement('tr');
    trb.className = 'xt-base';
    trb.innerHTML = '<td class="xt-rowlabel">Base (n)</td>';
    for (const c of cols) {
      const b = tm.bases[c.key];
      const td = document.createElement('td');
      if (c.isTotal) td.className = 'xt-total-col';
      const small = b.neff < 30 ? ' xt-smallbase' : '';
      td.innerHTML = '<span class="' + small.trim() + '">' + _fmtBase(b.wbase) + '</span>';
      trb.appendChild(td);
    }
    tbody.appendChild(trb);
    table.appendChild(tbody);
    card.appendChild(table);

    // rodapé legenda
    const foot = document.createElement('div');
    foot.className = 'xt-legend';
    const naoSoma = tm.rowVar.kind === 'mr' ? ' · colunas não somam 100% (múltipla resposta)' : '';
    foot.innerHTML = '<span class="xt-up">▲</span>/<span class="xt-down">▼</span> maior/menor que o grupo · escala: p&lt;0,05 · p&lt;0,01 · p&lt;0,001' + naoSoma;
    card.appendChild(foot);
    return card;
  }

  function buildCrosstabBook(bannerVars) {
    const host = document.getElementById('crosstab-content');
    if (!host) return;
    host.innerHTML = '';
    if (!bannerVars || bannerVars.length === 0) {
      host.innerHTML = '<p class="xt-empty">Escolha uma ou mais variáveis para as colunas (banner).</p>';
      return;
    }
    const records = getFilteredRecords(null);
    const cols = buildColumns(bannerVars, records, (typeof VALUE_ORDERS !== 'undefined' ? VALUE_ORDERS : {}));
    const bannerSet = new Set(bannerVars);
    for (const vm of VARS_META) {
      if (bannerSet.has(vm.name)) continue;
      const kind = rowKindFromMeta(vm);
      if (kind === 'skip') continue;
      const rowVar = { name: vm.name, title: vm.title, kind: kind };
      const tm = computeCrosstab(rowVar, cols, records, (typeof VALUE_ORDERS !== 'undefined' ? VALUE_ORDERS : {}));
      applySignificance(tm);
      host.appendChild(renderCrosstabTable(tm));
    }
  }

  var _bannerVars = [];

  function crosstabBannerCandidates() {
    const out = [];
    for (const vm of VARS_META) {
      if (rowKindFromMeta(vm) === 'categorical') out.push({ name: vm.name, title: vm.title || vm.name });
    }
    return out;
  }

  function _renderBannerBar() {
    const bar = document.getElementById('crosstab-banner');
    if (!bar) return;
    const chips = _bannerVars.map(function (n) {
      const vm = VARS_META.find(function (v) { return v.name === n; });
      const label = vm ? (vm.title || vm.name) : n;
      return '<span class="xt-chip" data-name="' + n + '">' + label +
        ' <span class="xt-chip-x" data-name="' + n + '">✕</span></span>';
    }).join('');
    const cands = crosstabBannerCandidates().filter(function (c) { return _bannerVars.indexOf(c.name) === -1; });
    const opts = ['<option value="">+ adicionar variável…</option>'].concat(
      cands.map(function (c) { return '<option value="' + c.name + '">' + c.title + '</option>'; })
    ).join('');
    bar.innerHTML = '<span class="xt-banner-lbl">Colunas (banner):</span> ' + chips +
      ' <select id="xt-add-select" class="xt-add">' + opts + '</select>' +
      '<span class="xt-banner-hint">respeita os filtros e o peso atuais</span>';
    bar.querySelectorAll('.xt-chip-x').forEach(function (x) {
      x.addEventListener('click', function () {
        const nm = x.getAttribute('data-name');
        _bannerVars = _bannerVars.filter(function (v) { return v !== nm; });
        _renderBannerBar(); buildCrosstabBook(_bannerVars);
      });
    });
    const sel = document.getElementById('xt-add-select');
    if (sel) sel.addEventListener('change', function () {
      if (sel.value && _bannerVars.indexOf(sel.value) === -1) {
        _bannerVars.push(sel.value);
        _renderBannerBar(); buildCrosstabBook(_bannerVars);
      }
    });
  }

  function _showView(which) {
    const vf = document.getElementById('view-frequencias');
    const vc = document.getElementById('view-crosstab');
    const tf = document.getElementById('tab-freq');
    const tc = document.getElementById('tab-cross');
    if (!vf || !vc) return;
    const cross = which === 'cross';
    vf.style.display = cross ? 'none' : '';
    vc.style.display = cross ? '' : 'none';
    if (tf) tf.classList.toggle('active', !cross);
    if (tc) tc.classList.toggle('active', cross);
    if (cross) buildCrosstabBook(_bannerVars);
  }

  function initCrosstab() {
    const tf = document.getElementById('tab-freq');
    const tc = document.getElementById('tab-cross');
    if (tf) tf.addEventListener('click', function () { _showView('freq'); });
    if (tc) tc.addEventListener('click', function () { _showView('cross'); });
    _renderBannerBar();
    if (typeof window !== 'undefined') {
      window.refreshCrosstab = function () {
        const vc = document.getElementById('view-crosstab');
        if (vc && vc.style.display !== 'none') buildCrosstabBook(_bannerVars);
      };
    }
  }

  const API = {
    effectiveBase, pooledZProportions, zMeans, pValueTwoSided, pLadderLabel,
    getCategories, buildColumns, computeCrosstab,
    applySignificance, MIN_NEFF,
    rowKindFromMeta, renderCrosstabTable, buildCrosstabBook,
    initCrosstab, crosstabBannerCandidates
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.Crosstab = API;
})(typeof window !== 'undefined' ? window : globalThis);
