const test = require('node:test');
const assert = require('node:assert');
const C = require('../../assets/crosstab.js');

test('effectiveBase: pesos uniformes => n', () => {
  assert.strictEqual(C.effectiveBase([1,1,1,1]), 4);
});
test('effectiveBase: vazio => 0', () => {
  assert.strictEqual(C.effectiveBase([]), 0);
});
test('effectiveBase: pesos desiguais reduzem n_eff', () => {
  const ne = C.effectiveBase([2,2,0.5,0.5]); // (5)^2 / (4+4+0.25+0.25)=25/8.5
  assert.ok(Math.abs(ne - 2.941) < 0.01);
});
test('pooledZProportions: 0,55 vs 0,42 com n grande => z positivo ~2-3', () => {
  const z = C.pooledZProportions(0.55, 640, 0.42, 560);
  assert.ok(z > 4 && z < 5, 'z=' + z);
});
test('pooledZProportions: n invalido => NaN', () => {
  assert.ok(Number.isNaN(C.pooledZProportions(0.5, 0, 0.5, 10)));
});
test('pValueTwoSided: z=1.96 => ~0,05', () => {
  assert.ok(Math.abs(C.pValueTwoSided(1.96) - 0.05) < 0.005);
});
test('pValueTwoSided: z=0 => 1', () => {
  assert.ok(Math.abs(C.pValueTwoSided(0) - 1) < 1e-9);
});
test('pLadderLabel: escada', () => {
  assert.strictEqual(C.pLadderLabel(0.20), '');
  assert.strictEqual(C.pLadderLabel(0.049), 'p<0,05');
  assert.strictEqual(C.pLadderLabel(0.008), 'p<0,01');
  assert.strictEqual(C.pLadderLabel(0.0003), 'p<0,001');
  assert.strictEqual(C.pLadderLabel(NaN), '');
});
test('zMeans: medias diferentes => z != 0', () => {
  const z = C.zMeans(8.2, 4, 640, 7.8, 4, 560);
  assert.ok(z > 0 && Number.isFinite(z));
});
