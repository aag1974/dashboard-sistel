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

  const API = {
    effectiveBase, pooledZProportions, zMeans, pValueTwoSided, pLadderLabel
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.Crosstab = API;
})(typeof window !== 'undefined' ? window : globalThis);
