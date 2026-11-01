// Tests for the local-ngspice backend. Real ngspice is NOT used: a tiny fake "ngspice" shell script
// writes a raw file built to the documented SPICE3 raw format, so these check the plumbing (spawn,
// temp files, parsing, errors, safety checks, browser-side engine), not ngspice's numbers.
// Run with: node tests/server.test.mjs
import http from 'node:http';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, chmodSync, mkdirSync, readFileSync, existsSync } from 'node:fs';
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
  // file access hidden inside a model line, and quotes, are refused too
  assert.match(checkNetlist('t\nR1 n1 0 1k\n.model x d_source(input_file=/etc/passwd)\n.end') ?? '', /Refused/);
  assert.match(checkNetlist('t\nR1 n1 0 1k\n.param s="x"\n.end') ?? '', /Refused/);
  assert.equal(checkNetlist('t\nR1 n1 0 1k\n.param profile=3\n.end'), null); // the word is fine; only file= / quotes are not
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
  const sp = parseLibraryText('.subckt FOO a b c PARAMS: gain=10 rf = 2k\n.ends', 'f.lib')[0];
  assert.deepEqual(sp.pins, ['a', 'b', 'c']);
  assert.deepEqual(sp.params, [{ name: 'gain', def: '10' }, { name: 'rf', def: '2k' }]);
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

await test('library upload: saves, lists, refuses duplicates and unsafe files', async () => {
  const up = (body, headers = { 'Content-Type': 'application/json' }) =>
    fetch(`${base}/api/models`, { method: 'POST', headers, body: typeof body === 'string' ? body : JSON.stringify(body) });
  const good = { name: 'up_test.lib', content: '* mine\n.model UPD D(IS=1n)\n.subckt SUBX a b\nR1 a b 1k\n.ends\n' };
  let r = await up(good);
  assert.equal(r.status, 200);
  const ok = await r.json();
  assert.deepEqual([ok.file, ok.replaced, ok.models, ok.subckts], ['up_test.lib', false, 1, 1]);
  assert.match(readFileSync(path.join(modelsDir, 'up_test.lib'), 'utf8'), /UPD/);
  const listed = await (await fetch(`${base}/api/models`)).json();
  assert.ok(listed.models.some((m) => m.name === 'UPD' && m.file === 'up_test.lib'));
  // same name again: 409 until overwrite is explicit
  r = await up(good);
  assert.equal(r.status, 409);
  assert.equal((await r.json()).exists, true);
  r = await up({ ...good, content: '.model UPD D(IS=2n)\n', overwrite: true });
  assert.equal(r.status, 200);
  assert.equal((await r.json()).replaced, true);
  // refusals, each with a readable reason
  const refuse = async (body, re) => {
    const x = await up(body);
    assert.equal(x.status, 400, JSON.stringify(body).slice(0, 60));
    assert.match((await x.json()).error, re);
  };
  await refuse({ name: '../evil.lib', content: '.model a D' }, /plain file name/);
  await refuse({ name: 'a b"c.lib', content: '.model a D' }, /plain file name/);
  await refuse({ name: 'x.exe', content: '.model a D' }, /file types/);
  await refuse({ name: 'e.lib', content: '   ' }, /empty/);
  await refuse({ name: 'c.lib', content: '.model a D\n.control\nshell ls\n.endc\n' }, /script or file command/);
  await refuse({ name: 'i.lib', content: '.include /etc/passwd\n' }, /by path/);
  await refuse({ name: 'j.lib', content: '.include ..\\secret.lib\n' }, /by path/);
  await refuse({ name: 'k.lib', content: '.model d d_source(input_file=data.txt)\n' }, /data file/);
  await refuse({ name: 'z.lib', content: 'a\u0000b' }, /binary/);
  assert.equal((await up('not json')).status, 400);
  assert.equal((await up('{}', { 'Content-Type': 'text/plain' })).status, 415);
  assert.equal((await up(good, { 'Content-Type': 'application/json', Origin: 'https://evil.example' })).status, 403);
  // a plain-name include and a normal .lib section are fine
  r = await up({ name: 'sec.lib', content: '.lib TT\n.model SEC D(IS=1n)\n.endl TT\n.include other.lib\n' });
  assert.equal(r.status, 200);
  assert.ok(!existsSync(path.join(modelsDir, 'evil.lib')));
  // LTspice-style .sub files are accepted
  r = await up({ name: 'NE555.sub', content: '.subckt NE555 gnd trig out rst ctrl thr dis vcc\nR1 vcc ctrl 5k\n.ends\n' });
  assert.equal(r.status, 200);
  assert.equal((await r.json()).subckts, 1);
});

await test('chat: disabled without CHAT_URL, validates input, forwards to the configured model', async () => {
  const post = (body, headers = { 'Content-Type': 'application/json' }) =>
    fetch(`${base}/api/chat`, { method: 'POST', headers, body: typeof body === 'string' ? body : JSON.stringify(body) });
  delete process.env.CHAT_URL;
  assert.equal((await (await fetch(`${base}/api/chat/config`)).json()).configured, false);
  assert.equal((await post({ messages: [{ role: 'user', content: 'hi' }] })).status, 503);
  // a stand-in model
  let seen = null;
  const fake = http.createServer((rq, rs) => {
    let b = '';
    rq.on('data', (d) => { b += d; });
    rq.on('end', () => { seen = { auth: rq.headers.authorization, body: JSON.parse(b) }; rs.setHeader('Content-Type', 'application/json'); rs.end(JSON.stringify({ choices: [{ message: { content: 'use 1k' } }] })); });
  });
  await new Promise((r) => fake.listen(0, '127.0.0.1', r));
  process.env.CHAT_URL = `http://127.0.0.1:${fake.address().port}/v1/chat/completions`;
  process.env.CHAT_MODEL = 'm1';
  process.env.CHAT_API_KEY = 'k';
  const cfg = await (await fetch(`${base}/api/chat/config`)).json();
  assert.deepEqual([cfg.configured, cfg.model], [true, 'm1']);
  const ok = await post({ messages: [{ role: 'user', content: 'what R?' }], context: 'R1 n1 0 1k' });
  assert.equal(ok.status, 200);
  assert.equal((await ok.json()).reply, 'use 1k');
  assert.equal(seen.auth, 'Bearer k');
  assert.equal(seen.body.model, 'm1');
  assert.equal(seen.body.stream, false);
  assert.equal(seen.body.messages.at(-1).content, 'what R?');
  assert.ok(seen.body.messages.some((m) => m.role === 'system' && /R1 n1 0 1k/.test(m.content)));
  // bad input
  for (const bad of [{}, { messages: [] }, { messages: [{ role: 'system', content: 'x' }] }, { messages: [{ role: 'assistant', content: 'x' }] }, { messages: [{ role: 'user', content: 'x'.repeat(9000) }] }]) {
    assert.equal((await post(bad)).status, 400);
  }
  assert.equal((await post('{}', { 'Content-Type': 'text/plain' })).status, 415);
  assert.equal((await post({ messages: [{ role: 'user', content: 'x' }] }, { 'Content-Type': 'application/json', Origin: 'https://evil.example' })).status, 403);
  // model down
  fake.close();
  const down = await post({ messages: [{ role: 'user', content: 'x' }] });
  assert.equal(down.status, 502);
  delete process.env.CHAT_URL; delete process.env.CHAT_MODEL; delete process.env.CHAT_API_KEY;
});

srv.close();
await test('checkNetlist: unrestricted switch lets control constructs through but still needs a netlist', () => {
  assert.equal(checkNetlist('t\nR1 n1 0 1k\n.control\nshell ls\n.endc\n.end', true), null);
  assert.ok(checkNetlist('', true));
  assert.match(checkNetlist('t\nR1 n1 0 1k\n.control\n.endc\n.end', false) ?? '', /Refused/);
});

console.log(`\n${n} tests passed`);

