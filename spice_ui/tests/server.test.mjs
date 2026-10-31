// Tests for the local-ngspice backend. Real ngspice is NOT used: a tiny fake "ngspice" shell script
// writes a raw file built to the documented SPICE3 raw format, so these check the plumbing (spawn,
// temp files, parsing, errors, safety checks, browser-side engine), not ngspice's numbers.
// Run with: node tests/server.test.mjs
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, chmodSync, mkdirSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { parseRaw } from '../server/rawfile.mjs';
import { parseLibraryText, scanLibrary, safeFileName } from '../server/library.mjs';
import { normalizeRaw } from '../src/sim/results.js';
import { NgspiceServerEngine } from '../src/sim/engine-server.js';

let n = 0;
const test = async (name, fn) => { await fn(); n++; console.log('ok -', name); };

function rawBinary({ title = 't', plot = 'Transient Analysis', complex = false, vars, rows }) {
  const head = [
    `Title: ${title}`, 'Date: Sat Oct 31 2026', `Plotname: ${plot}`, `Flags: ${complex ? 'complex' : 'real'}`,
    `No. Variables: ${vars.length}`, `No. Points: ${rows.length}`, 'Variables:',
    ...vars.map((v, i) => `\t${i}\t${v[0]}\t${v[1]}`), 'Binary:', '',
  ].join('\n');
  const per = complex ? 2 : 1;
  const body = Buffer.alloc(rows.length * vars.length * per * 8);
  let p = 0;
  for (const row of rows) for (const c of row) {
    if (complex) { body.writeDoubleLE(c[0], p); p += 8; body.writeDoubleLE(c[1], p); p += 8; } else { body.writeDoubleLE(c, p); p += 8; }
  }
  return Buffer.concat([Buffer.from(head, 'latin1'), body]);
}

const TRAN = rawBinary({
  vars: [['time', 'time'], ['v(n1)', 'voltage'], ['v1#branch', 'current']],
  rows: [[0, 0, -0.001], [1e-3, 2.5, -0.001], [2e-3, 4, -0.001]],
});
const AC = rawBinary({
  plot: 'AC Analysis', complex: true,
  vars: [['frequency', 'frequency'], ['v(n2)', 'voltage']],
  rows: [[[1, 0], [1, 0]], [[10, 0], [0.5, -0.5]]],
});

await test('rawfile: binary real plot', () => {
  const r = parseRaw(TRAN);
  assert.equal(r.numPoints, 3);
  assert.equal(r.dataType, 'real');
  assert.deepEqual(r.variableNames, ['time', 'v(n1)', 'v1#branch']);
  assert.deepEqual(r.data[1].values, [0, 2.5, 4]);
});

await test('rawfile: binary complex plot', () => {
  const r = parseRaw(AC);
  assert.equal(r.dataType, 'complex');
  assert.deepEqual(r.data[1].values[1], { real: 0.5, img: -0.5 });
});

await test('rawfile: ascii plot', () => {
  const txt = [
    'Title: t', 'Plotname: Operating Point', 'Flags: real', 'No. Variables: 2', 'No. Points: 1',
    'Variables:', '\t0\tv(n1)\tvoltage', '\t1\tv1#branch\tcurrent', 'Values:', ' 0\t1.5e+00', '\t-1.0e-03', '',
  ].join('\n');
  const r = parseRaw(Buffer.from(txt));
  assert.deepEqual(r.data.map((d) => d.values[0]), [1.5, -0.001]);
});

await test('rawfile: several plots -> last one; truncated and empty files are errors', () => {
  const op = rawBinary({ plot: 'Operating Point', vars: [['v(n1)', 'voltage']], rows: [[1]] });
  assert.equal(parseRaw(Buffer.concat([op, TRAN])).numPoints, 3);
  assert.throws(() => parseRaw(TRAN.subarray(0, TRAN.length - 5)), /truncated/);
  assert.throws(() => parseRaw(Buffer.alloc(0)), /No plot/);
});

await test('raw result feeds the existing normaliser (labels, units, scale)', () => {
  const t = normalizeRaw(parseRaw(TRAN), 'tran');
  assert.deepEqual(t.vectors.map((v) => v.label), ['v(n1)', 'i(v1)']);
  assert.equal(t.x.length, 3);
  const a = normalizeRaw(parseRaw(AC), 'ac');
  assert.equal(a.x[1], 10);
  assert.ok(a.vectors[0].imag);
});

// ---- server with a fake ngspice -------------------------------------------------------------
const dir = mkdtempSync(path.join(tmpdir(), 'fake-ngspice-'));
writeFileSync(path.join(dir, 'tran.raw'), TRAN);
const fake = path.join(dir, 'fake-ngspice');
// usage: fake -b -r <raw> -o <log> <cir>   ; behaviour chosen by the netlist's second line
writeFileSync(fake, `#!/bin/sh
if [ "$1" = "--version" ]; then echo "** ngspice-99 fake"; exit 0; fi
RAW="$3"; LOG="$5"; CIR="$6"
if grep -q "FAIL" "$CIR"; then echo "Error: singular matrix" > "$LOG"; exit 1; fi
if grep -q "HANG" "$CIR"; then sleep 5; fi
cp "$CIR" "${path.join(dir, 'last.cir')}"
echo "fake log" > "$LOG"
cp "${path.join(dir, 'tran.raw')}" "$RAW"
`);
chmodSync(fake, 0o755);
const modelsDir = path.join(dir, 'models');
mkdirSync(modelsDir);
writeFileSync(path.join(modelsDir, 'a.lib'), `* comment .model IGNORED D
.model D1N_TEST D(IS=1n
+ RS=0.5 N=1.8) ; trailing
.MODEL q_test npn (bf=100)
.subckt AMP in+ in- out PARAMS: gain=10
R1 in+ out 1k
.ends
`);
writeFileSync(path.join(modelsDir, 'b.mod'), '.model D1N_TEST D(IS=2n)\n.model PM PMOS(LEVEL=1)\n');
writeFileSync(path.join(modelsDir, 'notes.pdf'), 'not a library');
process.env.MODELS_DIR = modelsDir;
process.env.NGSPICE_BIN = fake;
process.env.SIM_TIMEOUT_MS = '700';
const { makeServer, checkNetlist } = await import('../server/server.mjs');

const srv = makeServer();
await new Promise((r) => srv.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${srv.address().port}`;
const post = (body, headers = { 'Content-Type': 'application/json' }) =>
  fetch(`${base}/api/simulate`, { method: 'POST', headers, body: typeof body === 'string' ? body : JSON.stringify(body) });

await test('checkNetlist: allows normal netlists and odd titles, refuses control constructs', () => {
  assert.equal(checkNetlist('Load test echo\nR1 n1 0 1k\n.tran 1u 1m\n.end\n'), null);
  for (const bad of ['.control', '.include /etc/passwd', '.lib x', 'shell rm -rf /', '  .CONTROL', 'write out.txt', 'source x']) {
    assert.match(checkNetlist(`t\nR1 n1 0 1k\n${bad}\n.end`) ?? '', /Refused/, bad);
  }
  assert.ok(checkNetlist(''));
});

await test('server: health reports the ngspice line', async () => {
  const r = await (await fetch(`${base}/api/health`)).json();
  assert.equal(r.ok, true);
  assert.match(r.ngspice, /ngspice-99/);
});

await test('server: simulate returns parsed raw + log', async () => {
  const res = await post({ netlist: 't\nR1 n1 0 1k\n.tran 1m 2m\n.end\n' });
  assert.equal(res.status, 200);
  const b = await res.json();
  assert.equal(b.raw.numPoints, 3);
  assert.equal(b.log.trim(), 'fake log');
});

await test('server: ngspice failure -> 422 with the error line from its log', async () => {
  const res = await post({ netlist: 't\nR1 n1 0 1k\n* FAIL\n.end\n' });
  assert.equal(res.status, 422);
  assert.match((await res.json()).error, /singular matrix/);
});

await test('server: timeout kills a hung run', async () => {
  const res = await post({ netlist: 't\nR1 n1 0 1k\n* HANG\n.end\n' });
  assert.equal(res.status, 504);
  assert.match((await res.json()).error, /did not finish/);
});

await test('server: rejects forbidden netlist, bad JSON, wrong content type, foreign Origin, unknown path', async () => {
  assert.equal((await post({ netlist: 't\n.control\n.endc\n.end' })).status, 400);
  assert.equal((await post('{not json')).status, 400);
  assert.equal((await post({ netlist: 'x' }, { 'Content-Type': 'text/plain' })).status, 415);
  assert.equal((await post({ netlist: 't\nR1 a 0 1\n.end' }, { 'Content-Type': 'application/json', Origin: 'https://evil.example' })).status, 403);
  assert.equal((await fetch(`${base}/nope`)).status, 404);
});

await test('browser engine: success through the real server, errors are readable, busy guard', async () => {
  const eng = new NgspiceServerEngine({ base });
  const r = await eng.run({ netlist: 't\nR1 n1 0 1k\n.tran 1m 2m\n.end\n', analysisType: 'tran' });
  assert.equal(r.x.length, 3);
  assert.equal(eng.lastLog.trim(), 'fake log');
  await assert.rejects(eng.run({ netlist: 't\n* FAIL\n.end\n', analysisType: 'tran' }), /ngspice: .*singular matrix/);
  const p = eng.run({ netlist: 't\nR1 n1 0 1k\n.tran 1m 2m\n.end\n', analysisType: 'tran' });
  await assert.rejects(eng.run({ netlist: 'x', analysisType: 'tran' }), /busy/);
  await p;
  const down = new NgspiceServerEngine({ base: 'http://127.0.0.1:1' });
  await assert.rejects(down.run({ netlist: 'x', analysisType: 'tran' }), /npm run server/);
});

await test('library parser: .model, case, continuation lines, comments, .subckt pins', () => {
  const r = parseLibraryText(readFileSync(path.join(modelsDir, 'a.lib'), 'utf8'), 'a.lib');
  assert.deepEqual(r.map((m) => [m.kind, m.name, m.type]), [['model', 'D1N_TEST', 'D'], ['model', 'q_test', 'NPN'], ['subckt', 'AMP', 'SUBCKT']]);
  assert.deepEqual(r[2].pins, ['in+', 'in-', 'out']); // PARAMS: and gain=10 are not pins
});

await test('library scan: lists supported files only, reports duplicates, missing folder is a message', async () => {
  const lib = await scanLibrary(modelsDir);
  assert.deepEqual(lib.files, ['a.lib', 'b.mod']);
  assert.deepEqual(lib.models.map((m) => m.name), ['D1N_TEST', 'q_test', 'AMP', 'PM']);
  assert.ok(lib.problems.some((p) => /D1N_TEST.*already defined/.test(p)));
  const none = await scanLibrary(path.join(dir, 'nope'));
  assert.match(none.problems[0], /does not exist/);
  assert.equal(safeFileName('../x.lib'), false);
  assert.equal(safeFileName('a"b.lib'), false);
  assert.equal(safeFileName('ok name.lib'), true);
});

await test('server: GET /api/models', async () => {
  const b = await (await fetch(`${base}/api/models`)).json();
  assert.equal(b.models.length, 4);
  assert.equal(b.dir, modelsDir);
});

await test('server: libs are included by the server after the title; unknown or unsafe names are refused', async () => {
  const nl = 'title\nR1 n1 0 1k\n.op\n.end\n';
  const ok = await post({ netlist: nl, libs: ['a.lib', 'a.lib'] });
  assert.equal(ok.status, 200);
  const deck = readFileSync(path.join(dir, 'last.cir'), 'utf8').split('\n');
  assert.equal(deck[0], 'title');
  assert.equal(deck[1], `.include "${path.join(modelsDir, 'a.lib')}"`);
  assert.equal(deck.filter((l) => l.startsWith('.include')).length, 1); // de-duplicated
  for (const libs of [['missing.lib'], ['../etc/passwd'], ['a"b'], 'a.lib', Array(51).fill('a.lib')]) {
    const r = await post({ netlist: nl, libs });
    assert.equal(r.status, 400, JSON.stringify(libs));
  }
  const without = await post({ netlist: nl });
  assert.equal(without.status, 200);
  assert.ok(!readFileSync(path.join(dir, 'last.cir'), 'utf8').includes('.include'));
});

await test('browser engine sends libs to the server', async () => {
  const eng = new NgspiceServerEngine({ base });
  await eng.run({ netlist: 'title\nR1 n1 0 1k\n.op\n.end\n', analysisType: 'tran', libs: ['b.mod'] });
  assert.match(readFileSync(path.join(dir, 'last.cir'), 'utf8'), /\.include ".*b\.mod"/);
});

srv.close();
console.log(`\n${n} tests passed`);
