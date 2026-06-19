const test = require('node:test');
const assert = require('node:assert');
const C = require('../../assets/crosstab.js');

const VALUE_ORDERS = { sexo: ['Homens','Mulheres'], aval: ['Ótimo','Bom','Ruim'] };
// 6 registros, peso 1
const RECORDS = [
  { sexo:'Homens',  aval:'Ótimo', nota:8, meios:['TV','Internet'], __weight__:1 },
  { sexo:'Homens',  aval:'Bom',   nota:7, meios:['TV'],            __weight__:1 },
  { sexo:'Homens',  aval:'Ruim',  nota:5, meios:['Internet'],      __weight__:1 },
  { sexo:'Mulheres',aval:'Ótimo', nota:9, meios:['Internet'],      __weight__:1 },
  { sexo:'Mulheres',aval:'Ótimo', nota:8, meios:['TV','Internet'], __weight__:1 },
  { sexo:'Mulheres',aval:'Bom',   nota:7, meios:[],                __weight__:1 },
];

test('getCategories usa VALUE_ORDERS', () => {
  assert.deepStrictEqual(C.getCategories('sexo', RECORDS, VALUE_ORDERS), ['Homens','Mulheres']);
});
test('getCategories sem VALUE_ORDERS => alfabético', () => {
  assert.deepStrictEqual(C.getCategories('aval', RECORDS, {}), ['Bom','Ótimo','Ruim']);
});
test('buildColumns: Total primeiro + categorias do banner', () => {
  const cols = C.buildColumns(['sexo'], RECORDS, VALUE_ORDERS);
  assert.strictEqual(cols[0].isTotal, true);
  assert.deepStrictEqual(cols.map(c=>c.label), ['', 'Homens','Mulheres']);
});
test('computeCrosstab categorical: % de coluna soma 1 por coluna', () => {
  const cols = C.buildColumns(['sexo'], RECORDS, VALUE_ORDERS);
  const tm = C.computeCrosstab({name:'aval', kind:'categorical'}, cols, RECORDS);
  const colKey = cols.find(c=>c.label==='Mulheres').key;
  const soma = tm.rows.reduce((s,row)=> s + (row.cells[colKey].pct||0), 0);
  assert.ok(Math.abs(soma - 1) < 1e-9);
  // Mulheres: 2 Ótimo / 3 => 0,667
  const otimo = tm.rows.find(r=>r.label==='Ótimo');
  assert.ok(Math.abs(otimo.cells[colKey].pct - (2/3)) < 1e-9);
  assert.strictEqual(tm.bases[colKey].wbase, 3);
});
test('computeCrosstab mr: % de quem marcou dentro da coluna (não soma 1)', () => {
  const cols = C.buildColumns(['sexo'], RECORDS, VALUE_ORDERS);
  const tm = C.computeCrosstab({name:'meios', kind:'mr'}, cols, RECORDS);
  const hk = cols.find(c=>c.label==='Homens').key;
  const tv = tm.rows.find(r=>r.label==='TV');
  // Homens marcaram TV em 2 de 3
  assert.ok(Math.abs(tv.cells[hk].pct - (2/3)) < 1e-9);
});
test('computeCrosstab numeric: uma linha de média', () => {
  const cols = C.buildColumns(['sexo'], RECORDS, VALUE_ORDERS);
  const tm = C.computeCrosstab({name:'nota', kind:'numeric'}, cols, RECORDS);
  assert.strictEqual(tm.rows.length, 1);
  const mk = cols.find(c=>c.label==='Mulheres').key;
  // Mulheres: (9+8+7)/3 = 8
  assert.ok(Math.abs(tm.rows[0].cells[mk].mean - 8) < 1e-9);
});
test('computeCrosstab numeric: Total = média geral', () => {
  const cols = C.buildColumns(['sexo'], RECORDS, VALUE_ORDERS);
  const tm = C.computeCrosstab({name:'nota', kind:'numeric'}, cols, RECORDS);
  const tk = cols[0].key;
  assert.ok(Math.abs(tm.rows[0].cells[tk].mean - (8+7+5+9+8+7)/6) < 1e-9);
});

test('applySignificance: Mulheres Ótimo maior que Homens, marca direção +', () => {
  // base grande para dar significância
  const big = [];
  for (let i=0;i<300;i++) big.push({sexo:'Homens',  aval: i<120?'Ótimo':'Bom', __weight__:1});
  for (let i=0;i<300;i++) big.push({sexo:'Mulheres',aval: i<210?'Ótimo':'Bom', __weight__:1});
  const cols = C.buildColumns(['sexo'], big, { sexo:['Homens','Mulheres'] });
  const tm = C.computeCrosstab({name:'aval', kind:'categorical'}, cols, big);
  C.applySignificance(tm);
  const mk = cols.find(c=>c.label==='Mulheres').key;
  const otimo = tm.rows.find(r=>r.label==='Ótimo');
  assert.strictEqual(otimo.cells[mk].sig.dir, 1);
  assert.ok(['p<0,05','p<0,01','p<0,001'].includes(otimo.cells[mk].sig.label));
});
test('applySignificance: Total nunca marcado', () => {
  const big = [{sexo:'Homens',aval:'Ótimo',__weight__:1},{sexo:'Mulheres',aval:'Bom',__weight__:1}];
  const cols = C.buildColumns(['sexo'], big, {});
  const tm = C.computeCrosstab({name:'aval', kind:'categorical'}, cols, big);
  C.applySignificance(tm);
  const tk = cols[0].key;
  for (const row of tm.rows) assert.strictEqual(row.cells[tk].sig.label, '');
});
test('applySignificance: base pequena => sem marcador', () => {
  const small = [
    {sexo:'Homens',aval:'Ótimo',__weight__:1},
    {sexo:'Mulheres',aval:'Bom',__weight__:1},
  ];
  const cols = C.buildColumns(['sexo'], small, {});
  const tm = C.computeCrosstab({name:'aval', kind:'categorical'}, cols, small);
  C.applySignificance(tm);
  for (const row of tm.rows) for (const c of cols) {
    assert.strictEqual(row.cells[c.key].sig.label, '');
  }
});
