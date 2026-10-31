// Node tests for the simulation plumbing: value parsing, netlist builder, result handling and
// the result handling. The solver is replaced by tests/mock-eecircuit.mjs (a test double, not a solver).
// Run with: node tests/sim.test.mjs
import assert from 'node:assert/strict';
import { parseValue, parseSourceText, num } from '../src/sim/units.js';
import { ANALYSES, defaultParams, buildCommand, validateParams } from '../src/sim/analysis.js';
import { analyzeNodes, buildCircuitNetlist } from '../src/sim/netlist.js';
import { normalizeRaw, buildTraces, labelOf, defaultVisible, measure } from '../src/sim/results.js';
import { checkDirectives, logicalLines } from '../src/sim/directives.js';
import { directiveBox } from '../src/canvas/directive.js';
import { circuitToSvg, circuitBounds, SvgContext } from '../src/canvas/export.js';
import { NgspiceServerEngine } from '../src/sim/engine-server.js';
import { formatSI, stepValue, stepText, opampParam, withUnit, PART_PARAMS } from '../src/sim/params.js';
import { Editor } from '../src/canvas/editor.js';
import { parseLibraryText } from '../server/library.mjs';
import { SAMPLES } from '../src/data/samples.js';
import * as mock from './mock-eecircuit.mjs';

let n = 0;
const test = async (name, fn) => { await fn(); n++; console.log('ok -', name); };
const near = (a, b, eps = 1e-9) => assert.ok(Math.abs(a - b) <= eps * Math.max(1, Math.abs(b)), `${a} != ${b}`);

const build = (list, analysis = { type: 'op', params: {} }, title = 't') => {
  const ed = new Editor();
  ed.loadElements(list);
  return buildCircuitNetlist({ elements: ed.els, terminalsOf: (e) => ed.terminals(e), title, analysis });
};
const GND = ['GroundElm', 0, 0, 0, 16];

await test('parseValue: SI prefixes, units, symbols', () => {
  const cases = [
    ['1k', '', 1e3], ['4.7k', '', 4700], ['1 kΩ', '', 1e3], ['10 µF', 'F', 1e-5], ['10 μF', 'F', 1e-5],
    ['1 F', 'F', 1], ['1 fF', 'F', 1e-15], ['1 H', 'H', 1], ['2 mH', 'H', 2e-3], ['5 V', 'V', 5],
    ['100 Hz', 'Hz', 100], ['1 kHz', 'Hz', 1e3], ['10 mA', 'A', 1e-2], ['1Meg', '', 1e6],
    ['2 MΩ', '', 2e6], ['2 mΩ', '', 2e-3], ['1e3', '', 1e3], ['-5', 'V', -5], ['.5', '', 0.5], ['330', '', 330],
    ['22 n', '', 22e-9], ['1 mil', '', 25.4e-6],
  ];
  for (const [s, u, want] of cases) near(parseValue(s, u), want, 1e-12);
  assert.ok(Number.isNaN(parseValue('abc')));
  assert.ok(Number.isNaN(parseValue('')));
  assert.ok(Number.isNaN(parseValue(undefined)));
});

await test('parseSourceText / num', () => {
  assert.deepEqual(parseSourceText('5 V, 100 Hz'), { amp: 5, freq: 100 });
  assert.deepEqual(parseSourceText('1 V, 1 kHz'), { amp: 1, freq: 1000 });
  assert.deepEqual(parseSourceText('5 V'), { amp: 5, freq: undefined });
  assert.equal(num(1e-6), '0.000001');
  assert.equal(num(0.1 + 0.2), '0.3');
  assert.equal(num(1e-12), '1e-12');
});

await test('analysis cards and validation', () => {
  assert.equal(buildCommand('tran', defaultParams('tran')), '.tran 20u 20m');
  assert.equal(buildCommand('ac', defaultParams('ac')), '.ac dec 20 1 1Meg');
  assert.equal(buildCommand('dc', { source: 'V1', start: '0', stop: '5', step: '100m' }), '.dc V1 0 5 100m');
  assert.equal(buildCommand('op', {}), '.op');
  for (const t of Object.keys(ANALYSES)) assert.deepEqual(validateParams(t, defaultParams(t)), []);
  assert.ok(validateParams('tran', { step: '0', stop: '1m' }).length);
  assert.ok(validateParams('tran', { step: '1m', stop: '1u' }).length);
  assert.ok(validateParams('tran', { step: '1p', stop: '1' }).some((e) => /million/.test(e)));
  assert.ok(validateParams('tran', { step: 'abc', stop: '1m' })[0].includes('not a number'));
  assert.ok(validateParams('ac', { sweep: 'dec', points: '10', fstart: '1k', fstop: '1' }).length);
  assert.ok(validateParams('dc', { source: 'V1', start: '0', stop: '5', step: '0' }).length);
});

await test('every sample builds a clean deck', () => {
  for (const [key, s] of Object.entries(SAMPLES)) {
    const r = build(s.elements, { type: 'tran', params: defaultParams('tran') }, s.title);
    assert.deepEqual(r.errors, [], key);
    assert.deepEqual(r.warnings, [], key);
    assert.ok(r.text.startsWith(`${s.title}\n`));
    assert.ok(r.text.trimEnd().endsWith('.end'));
  }
});

await test('resistor divider deck is exactly right', () => {
  const r = build(SAMPLES.divider.elements, { type: 'op', params: {} }, 'Resistor divider');
  assert.equal(r.text, 'Resistor divider\nV1 n1 0 DC 10\nR1 n1 n2 1000\nR2 n2 0 2000\n.op\n.end\n');
  assert.deepEqual(r.sources, ['V1']);
});

await test('rc, led, rectifier, amp decks contain the right cards', () => {
  const rc = build(SAMPLES.rc.elements).text;
  assert.match(rc, /^V1 n1 0 SIN\(0 5 100\) AC 1$/m);
  assert.match(rc, /^R1 n1 n2 1000$/m);
  assert.match(rc, /^C1 n2 0 0\.000001$/m);
  const led = build(SAMPLES.led.elements).text;
  assert.match(led, /^D1 n2 0 DLED$/m);
  assert.match(led, /^\.model DLED D\(/m);
  const rec = build(SAMPLES.rectifier.elements).text;
  assert.match(rec, /^D1 n1 n2 DDEFAULT$/m);
  const amp = build(SAMPLES.amp.elements).text;
  assert.match(amp, /^B1 n3 0 V=0\+15\*tanh\(100000\*\(v\(0\)-v\(n2\)\)\/15\)$/m); // out, 0, +in (ground), -in
});

await test('connectivity: wires join, grounds are one node, crossing is not a connection', () => {
  const ed = new Editor();
  ed.loadElements([
    ['ResistorElm', 0, 0, 64, 0], ['WireElm', 64, 0, 128, 0], ['ResistorElm', 128, 0, 192, 0],
    ['WireElm', 64, -32, 64, 32], // passes over (64,0) without ending there
    ['GroundElm', 192, 0, 192, 16], ['GroundElm', 500, 500, 500, 516],
  ]);
  const a = analyzeNodes(ed.els, (e) => ed.terminals(e));
  const [r1, w1, r2, wc, g1, g2] = ed.els;
  assert.equal(a.nodeOfTerminal(r1, 1), a.nodeOfTerminal(r2, 0)); // joined through the wire
  assert.equal(a.nodeOfTerminal(r2, 1), '0');
  assert.equal(a.nodeOfTerminal(g1, 0), a.nodeOfTerminal(g2, 0)); // every ground is node 0
  assert.equal(a.nodeOfTerminal(g2, 0), '0');
  // the vertical wire runs from (64,-32) to (64,32), straight over the joint at (64,0) without
  // ending there, so it is its own node and does NOT connect to the resistors
  assert.equal(a.nodeOfTerminal(wc, 0), a.nodeOfTerminal(wc, 1)); // a wire joins its own two ends
  assert.notEqual(a.nodeOfTerminal(wc, 0), a.nodeOfTerminal(r1, 1));
  assert.equal(a.nodeOfTerminal(r1, 0).startsWith('n'), true);
});

await test('errors: empty, no ground, unsupported part, bad value, unknown DC source', () => {
  assert.ok(build([]).errors.some((e) => /empty/.test(e)));
  const noG = build([['DCVoltageElm', 0, 0, 0, 64], ['ResistorElm', 0, 0, 64, 0], ['WireElm', 64, 0, 64, 64], ['WireElm', 0, 64, 64, 64]]);
  assert.equal(noG.ok, false);
  assert.ok(noG.errors.some((e) => /no ground/.test(e)));
  const nand = build([['DelayBufferElm', 0, 0, 48, 0], GND, ['WireElm', 0, 0, 0, 0]]);
  assert.ok(nand.errors.some((e) => /Delay Buffer is not supported/.test(e)));
  const bad = build([['ResistorElm', 0, 0, 64, 0, 'lots'], ['WireElm', 64, 0, 64, 16], ['GroundElm', 64, 16, 64, 32]]);
  assert.ok(bad.errors.some((e) => /resistance must be a positive number \("lots"\)/.test(e)));
  const zero = build([['ResistorElm', 0, 0, 64, 0, '0'], ['GroundElm', 64, 0, 64, 16]]);
  assert.ok(zero.errors.some((e) => /positive/.test(e)));
  const dc = build(SAMPLES.divider.elements, { type: 'dc', params: { source: 'V9', start: '0', stop: '5', step: '1' } });
  assert.ok(dc.errors.some((e) => /no source called "V9".*V1/.test(e)));
  const dcOk = build(SAMPLES.divider.elements, { type: 'dc', params: { source: 'V1', start: '0', stop: '5', step: '1' } });
  assert.deepEqual(dcOk.errors, []);
  assert.match(dcOk.text, /^\.dc V1 0 5 1$/m);
});

await test('warnings: loose pin, no source, switch', () => {
  const loose = build([['ResistorElm', 0, 0, 64, 0], ['GroundElm', 64, 0, 64, 16]]);
  assert.ok(loose.warnings.some((w) => /only one connection/.test(w)));
  assert.ok(loose.warnings.some((w) => /no voltage or current source/.test(w)));
  const sw = build([['DCVoltageElm', 0, 0, 0, 64, '5 V'], ['SwitchElm', 0, 0, 64, 0], ['WireElm', 64, 0, 64, 64], ['WireElm', 0, 64, 64, 64], ['GroundElm', 0, 64, 0, 80]]);
  assert.match(sw.text, /^R1 \S+ \S+ 1m$/m);          // default: closed
  assert.match(sw.text, /^R1 n1 0 1m$/m); // the test circuit wires the switch straight across the source
});

await test('device pin order: BJT, MOSFET, op amp (both orientations), zener, rail, current source', () => {
  // NPN: base at (0,0), collector (32,-16), emitter (32,16)
  const q = build([
    ['NTransistorElm', 0, 0, 32, 0], ['WireElm', 0, 0, 0, -16], ['WireElm', 32, -16, 32, -48],
    ['GroundElm', 32, 16, 32, 32], ['DCVoltageElm', 0, -16, 0, -80, '5 V'], ['ResistorElm', 32, -48, 96, -48],
  ]);
  assert.match(q.text, /^Q1 n\d n\d 0 QNPN$/m);
  const qline = q.text.match(/^Q1 (\S+) (\S+) (\S+) QNPN$/m);
  const refsNodes = (id) => q.refs.get(id);
  assert.ok(qline[1] !== qline[2]); // collector and base are different nodes
  const m = build([['PMosfetElm', 0, 0, 32, 0], ['GroundElm', 32, 16, 32, 32]]);
  assert.match(m.text, /^M1 n\d n\d 0 0 PMOD$/m); // d g s b(=s)
  assert.match(m.text, /^\.model PMOD PMOS\(LEVEL=1\)$/m);
  // op amp: "- on top"; the + input (second terminal) goes to the grounded node
  const op = build([['OpAmpElm', 0, 0, 64, 0], ['WireElm', 0, 16, 0, 32], ['GroundElm', 0, 32, 0, 48]]);
  assert.match(op.text, /^B1 n\d 0 V=0\+15\*tanh\(100000\*\(v\(0\)-v\(n\d\)\)\/15\)$/m);
  const opSwap = build([['OpAmpSwapElm', 0, 0, 64, 0], ['WireElm', 0, -16, 0, -32], ['GroundElm', 0, -32, 0, -48]]);
  assert.match(opSwap.text, /^B1 n\d 0 V=0\+15\*tanh\(100000\*\(v\(0\)-v\(n\d\)\)\/15\)$/m); // + is on top here, and is the grounded one
  const z = build([['ZenerElm', 0, 0, 64, 0, '3.3 V'], ['GroundElm', 64, 0, 64, 16]]);
  assert.match(z.text, /^D1 n1 0 DZ3_3$/m);
  assert.match(z.text, /^\.model DZ3_3 D\(BV=3\.3 IBV=5m\)$/m);
  const rail = build([['RailElm', 0, 0, 16, 0, '12 V'], ['ResistorElm', 16, 0, 80, 0, '1 k'], ['GroundElm', 80, 0, 80, 16]]);
  assert.match(rail.text, /^V1 n1 0 DC 12$/m);
  const cur = build([['CurrentElm', 0, 0, 64, 0, '2 mA'], ['GroundElm', 0, 0, 0, 16], ['ResistorElm', 64, 0, 64, 64], ['GroundElm', 64, 64, 64, 80]]);
  assert.match(cur.text, /^I1 0 n1 DC 0\.002$/m);
});

await test('same-type parts are numbered in order; refs map back to element ids', () => {
  const r = build([
    ['ResistorElm', 0, 0, 64, 0], ['ResistorElm', 64, 0, 128, 0], ['ResistorElm', 128, 0, 192, 0], ['GroundElm', 192, 0, 192, 16],
  ]);
  assert.deepEqual([...r.refs.values()], ['R1', 'R2', 'R3']);
});

await test('title cannot inject extra lines', () => {
  const r = build(SAMPLES.divider.elements, undefined, 'bad\n.control\nshell rm -rf\n.endc');
  assert.equal(r.text.split('\n')[0], 'bad .control shell rm -rf .endc');
  assert.ok(!/^\.control/m.test(r.text));
});

await test('labelOf', () => {
  assert.equal(labelOf('n1'), 'v(n1)');
  assert.equal(labelOf('N1'), 'v(n1)');
  assert.equal(labelOf('V1#branch'), 'i(v1)');
  assert.equal(labelOf('v(out)'), 'v(out)');
  assert.equal(labelOf('i(v1)'), 'i(v1)');
});

const runWith = async (list, analysis) => {
  const nl = build(list, analysis);
  assert.deepEqual(nl.errors, []);
  // A fetch stand-in that hands the netlist to the test double (NOT a solver) and answers like the server.
  const fetchImpl = async (_url, init) => {
    const sim = new mock.Simulation();
    await sim.start();
    sim.setNetList(JSON.parse(init.body).netlist);
    return { ok: true, status: 200, json: async () => ({ raw: await sim.runSim(), log: '' }) };
  };
  const eng = new NgspiceServerEngine({ fetchImpl });
  return { nl, res: await eng.run({ netlist: nl.text, analysisType: analysis.type }) };
};

await test('result + mock: transient result is normalised', async () => {
  const { res } = await runWith(SAMPLES.rc.elements, { type: 'tran', params: { step: '1m', stop: '10m' } });
  assert.equal(res.analysis, 'tran');
  assert.equal(res.xLabel, 'Time');
  assert.equal(res.xUnit, 's');
  assert.equal(res.x.length, 11);
  assert.deepEqual(res.vectors.map((v) => v.label), ['v(n1)', 'v(n2)', 'i(v1)']);
  assert.deepEqual(res.vectors.map((v) => v.unit), ['V', 'V', 'A']);
  assert.ok(res.x instanceof Float64Array && res.vectors[0].real instanceof Float64Array);
  assert.deepEqual([...defaultVisible(res)], ['v(n1)', 'v(n2)']); // currents start hidden
});

await test('result + mock: AC result keeps real and imaginary parts; traces are dB and degrees', async () => {
  const { res } = await runWith(SAMPLES.rc.elements, { type: 'ac', params: defaultParams('ac') });
  assert.equal(res.analysis, 'ac');
  assert.equal(res.xUnit, 'Hz');
  const v = res.vectors.find((x) => x.label === 'v(n2)');
  assert.ok(v.imag instanceof Float64Array);
  const { traces, xlog } = buildTraces(res, new Set(['v(n2)']));
  assert.equal(xlog, true);
  assert.deepEqual(traces.map((t) => [t.name, t.axis, !!t.dash]), [['v(n2) dB', 'left', false], ['v(n2) °', 'right', true]]);
  // the mock's corner frequency is 159.155 Hz: find the point nearest it, expect about -3 dB / -45 deg
  let best = 0;
  res.x.forEach((f, i) => { if (Math.abs(Math.log(f / 159.155)) < Math.abs(Math.log(res.x[best] / 159.155))) best = i; });
  assert.ok(Math.abs(traces[0].y[best] + 3.01) < 0.6, traces[0].y[best]);
  assert.ok(Math.abs(traces[1].y[best] + 45) < 8, traces[1].y[best]);
  assert.equal(buildTraces(res, new Set(['v(n2)']), { showPhase: false }).traces.length, 1);
});

await test('buildTraces dB / phase maths on exact values', () => {
  const res = {
    analysis: 'ac', xLabel: 'Frequency', xUnit: 'Hz', x: Float64Array.of(1, 10),
    vectors: [{ label: 'v(a)', unit: 'V', real: Float64Array.of(0.5, 0), imag: Float64Array.of(-0.5, 1) }],
  };
  const { traces } = buildTraces(res, new Set(['v(a)']));
  near(traces[0].y[0], 20 * Math.log10(Math.SQRT1_2));
  near(traces[0].y[1], 0);
  near(traces[1].y[0], -45);
  near(traces[1].y[1], 90);
});

await test('result + mock: DC sweep and operating point', async () => {
  const dc = await runWith(SAMPLES.divider.elements, { type: 'dc', params: { source: 'V1', start: '0', stop: '10', step: '1' } });
  assert.equal(dc.res.analysis, 'dc');
  assert.equal(dc.res.x.length, 11);
  assert.equal(dc.res.xUnit, 'V');
  assert.ok(dc.res.vectors.every((v) => v.label.startsWith('v(')));
  const op = await runWith(SAMPLES.divider.elements, { type: 'op', params: {} });
  assert.equal(op.res.analysis, 'op');
  assert.equal(op.res.x, null);
  assert.equal(op.res.vectors[0].real.length, 1);
  assert.deepEqual(buildTraces(op.res, new Set()).traces, []);
});

await test('measure: min / max / pk-pk / mean on a transient vector', () => {
  const res = { analysis: 'tran', vectors: [{ label: 'v(a)', unit: 'V', real: Float64Array.of(0, 2, 4, 2) }] };
  const m = Object.fromEntries(measure(res, 'v(a)', (x) => String(x)));
  assert.deepEqual(m, { min: '0', max: '4', 'pk-pk': '4', mean: '2' });
  assert.deepEqual(measure({ ...res, analysis: 'ac' }, 'v(a)', String), []);
});

await test('normalize: rejects unknown shapes with a useful message', () => {
  assert.throws(() => normalizeRaw({ foo: 1, bar: 2 }, 'tran'), /keys: foo, bar/);
  assert.throws(() => normalizeRaw(null, 'tran'), /Unrecognised/);
  assert.throws(() => normalizeRaw({ data: [] }, 'tran'), /Unrecognised/);
});

await test('normalize: accepts re/im spellings', () => {
  const raw = { data: [
    { name: 'frequency', values: [{ re: 1, im: 0 }, { re: 10, im: 0 }] },
    { name: 'out', values: [{ re: 1, im: 0 }, { real: 0, imag: -1 }] },
  ] };
  const r = normalizeRaw(raw, 'ac');
  assert.deepEqual([...r.x], [1, 10]);
  assert.deepEqual([...r.vectors[0].imag], [0, -1]);
});

// ---- library models -----------------------------------------------------------------------
const LIB = [
  { kind: 'model', name: 'GEN_SIGNAL_DIODE', type: 'D', file: 'generic.lib' },
  { kind: 'model', name: 'MYNPN', type: 'NPN', file: 'my.lib' },
  { kind: 'subckt', name: 'OPAMP1', type: 'SUBCKT', pins: ['1', '2', '3'], file: 'my.lib' },
];
const buildLib = (list, library) => {
  const ed = new Editor();
  ed.loadElements(list);
  for (const [i, m] of Object.entries(list.models ?? {})) ed.els[Number(i)].model = m;
  return { ed, nl: (models = {}) => {
    for (const [i, m] of Object.entries(models)) ed.els[Number(i)].model = m;
    return buildCircuitNetlist({ elements: ed.els, terminalsOf: (e) => ed.terminals(e), title: 't', analysis: { type: 'op', params: {} }, library });
  } };
};
const DIODE_CKT = [['DCVoltageElm', 0, 0, 0, 64, '5 V'], ['DiodeElm', 0, 0, 64, 0], ['ResistorElm', 64, 0, 64, 64, '1k'], GND];

await test('library model: used for the diode, file recorded, built-in model not emitted', () => {
  const { ed, nl } = buildLib(DIODE_CKT, LIB);
  const d = ed.els.findIndex((e) => e.type === 'DiodeElm');
  const r = nl({ [d]: 'GEN_SIGNAL_DIODE' });
  assert.deepEqual(r.errors, []);
  assert.deepEqual(r.libs, ['generic.lib']);
  assert.match(r.text, /^D1 \S+ \S+ GEN_SIGNAL_DIODE$/m);
  assert.doesNotMatch(r.text, /\.model DDEFAULT/);
  assert.match(r.text, /^\* library file .*generic\.lib$/m);
  assert.ok(!r.text.split('\n').some((l) => /^\.(include|lib)/i.test(l)), 'client netlist has no .include');
});

await test('library model: no model -> built-in default and no libs', () => {
  const r = buildLib(DIODE_CKT, LIB).nl();
  assert.deepEqual(r.libs, []);
  assert.match(r.text, /^\.model DDEFAULT D$/m);
});

await test('library model: wrong type, missing, and subckt are errors that name the part', () => {
  const { ed, nl } = buildLib(DIODE_CKT, LIB);
  const d = ed.els.findIndex((e) => e.type === 'DiodeElm');
  assert.match(nl({ [d]: 'MYNPN' }).errors.join('\n'), /NPN model, but this part needs a D model/);
  assert.match(nl({ [d]: 'NOPE' }).errors.join('\n'), /"NOPE" was not found in the model library/);
  assert.match(nl({ [d]: 'OPAMP1' }).errors.join('\n'), /was not found/); // subckts are not assignable
  assert.equal(nl({ [d]: 'MYNPN' }).ok, false);
});

await test('library model: transistor and MOSFET cards use the library name', () => {
  const lib = [{ kind: 'model', name: 'MYNPN', type: 'NPN', file: 'a.lib' }, { kind: 'model', name: 'MYN', type: 'NMOS', file: 'b.lib' }];
  const list = [['DCVoltageElm', 0, 0, 0, 64, '5 V'], ['NTransistorElm', 32, 0, 32, 48], ['NMosfetElm', 96, 0, 96, 48], GND];
  const { ed, nl } = buildLib(list, lib);
  const q = ed.els.findIndex((e) => e.type === 'NTransistorElm');
  const m = ed.els.findIndex((e) => e.type === 'NMosfetElm');
  const r = nl({ [q]: 'MYNPN', [m]: 'MYN' });
  assert.match(r.text, /^Q1 \S+ \S+ \S+ MYNPN$/m);
  assert.match(r.text, /^M1 \S+ \S+ \S+ \S+ MYN$/m);
  assert.deepEqual(r.libs.sort(), ['a.lib', 'b.lib']);
});

// ---- generic models and parameters ---------------------------------------------------------
const withParams = (list, idx, params, analysis) => {
  const ed = new Editor();
  ed.loadElements(list);
  ed.els[idx].params = params;
  return buildCircuitNetlist({ elements: ed.els, terminalsOf: (e) => ed.terminals(e), title: 't', analysis: analysis ?? { type: 'op', params: {} } });
};

await test('params: SI formatting and 1-2-5 stepping', () => {
  assert.equal(formatSI(0.0231), '23.1m');
  assert.equal(formatSI(100000), '100k');
  assert.equal(formatSI(1e6), '1Meg');
  assert.equal(formatSI(0), '0');
  assert.equal(formatSI(-15), '-15');
  assert.equal(stepValue(1, 1), 2);
  assert.equal(stepValue(2, 1), 5);
  assert.equal(stepValue(5, 1), 10);
  assert.equal(stepValue(10, -1), 5);
  assert.equal(stepValue(1, -1), 0.5);
  assert.equal(stepValue(-15, 1), -10); // "+" always moves the number up, also for negatives
  assert.equal(stepValue(0, 1), 1);
  assert.equal(stepText('600m', 1), '1');
  assert.equal(stepText('', 1, '15'), '20');
  assert.equal(stepText('abc', 1), 'abc'); // unparsable text is left alone
});

await test('generic diode: no parameters -> bare SPICE default model; parameters -> own model card', () => {
  const none = withParams(DIODE_CKT, 1, undefined);
  assert.match(none.text, /^\.model DDEFAULT D$/m);
  const some = withParams(DIODE_CKT, 1, { IS: '2n', RS: '0.5', N: '' });
  assert.deepEqual(some.errors, []);
  assert.match(some.text, /^\.model DDEFAULT_1 D\(IS=2e-9 RS=0\.5\)$/m);
  assert.match(some.text, /^D1 \S+ \S+ DDEFAULT_1$/m);
  const bad = withParams(DIODE_CKT, 1, { IS: 'lots' });
  assert.match(bad.errors.join(), /Diode: IS is not a number \("lots"\)/);
});

await test('generic BJT / MOSFET: only set parameters are written; W and L go on the instance card', () => {
  const q = withParams([['DCVoltageElm', 0, 0, 0, 64, '5 V'], ['NTransistorElm', 32, 0, 32, 48], GND], 1, { BF: '250' });
  assert.match(q.text, /^\.model QNPN_1 NPN\(BF=250\)$/m);
  const bare = withParams([['DCVoltageElm', 0, 0, 0, 64, '5 V'], ['NTransistorElm', 32, 0, 32, 48], GND], 1, undefined);
  assert.match(bare.text, /^\.model QNPN NPN$/m);
  const m = withParams([['DCVoltageElm', 0, 0, 0, 64, '5 V'], ['NMosfetElm', 32, 0, 32, 48], GND], 1, { VTO: '1', KP: '20m', W: '10u', L: '1u' });
  assert.match(m.text, /^\.model NMOD_1 NMOS\(LEVEL=1 VTO=1 KP=0\.02\)$/m);
  assert.match(m.text, /^M1 \S+ \S+ \S+ \S+ NMOD_1 W=0\.00001 L=0\.000001$/m);
});

await test('generic models: identical parameter sets share one card', () => {
  const ed = new Editor();
  ed.loadElements([['DCVoltageElm', 0, 0, 0, 64, '5 V'], ['DiodeElm', 0, 0, 64, 0], ['DiodeElm', 64, 0, 128, 0], GND]);
  ed.els[1].params = { IS: '1n' }; ed.els[2].params = { IS: '1n' };
  const r = buildCircuitNetlist({ elements: ed.els, terminalsOf: (e) => ed.terminals(e), title: 't', analysis: { type: 'op', params: {} } });
  assert.equal(r.text.match(/^\.model /gm).length, 1);
});

await test('ideal op amp: defaults, custom limits, validation', () => {
  const ckt = [['OpAmpElm', 0, 0, 64, 0], ['WireElm', 0, 16, 0, 32], ['GroundElm', 0, 32, 0, 48]];
  assert.match(withParams(ckt, 0, { vmax: '5', vmin: '0', gain: '1Meg' }).text, /^B1 n\d 0 V=2\.5\+2\.5\*tanh\(1000000\*\(v\(0\)-v\(n\d\)\)\/2\.5\)$/m);
  assert.match(withParams(ckt, 0, { vmax: '-5', vmin: '5' }).errors.join(), /Max Output must be greater than Min Output/);
  assert.match(withParams(ckt, 0, { gain: '0' }).errors.join(), /Gain must be a positive number/);
  assert.match(withParams(ckt, 0, { gain: 'big' }).errors.join(), /Gain must be a positive number \(got "big"\)/);
  assert.equal(opampParam({ type: 'OpAmpElm' }, 'gain'), '100k');
});

await test('real op amp: macromodel cards, preset values, swap, hidden internal node', () => {
  const ckt = [['DCVoltageElm', 0, 0, 0, 64, '5 V'], ['OpAmpRealElm', 0, 0, 64, 0], ['GroundElm', 0, 64, 0, 80]];
  const r = withParams(ckt, 1, undefined);
  assert.deepEqual(r.errors, []);
  assert.match(r.text, /^Bg1 0 z_oa1_x I=/m);
  assert.match(r.text, /^Rp1 z_oa1_x 0 2000000000$/m);   // gain 200k / gm 1e-4
  assert.match(r.text, /^Cp1 z_oa1_x 0 1\.59/m);          // gm / (2 pi GBW) for 1 MHz
  assert.match(r.text, /^Bo1 0 n\d I=0\.025\*tanh\(/m);   // default current limit 25 mA
  const lm = withParams(ckt, 1, { preset: 'LM741' });
  assert.equal(opampParam({ type: 'OpAmpRealElm', params: { preset: 'LM741' } }, 'slew'), '600m');
  assert.match(lm.text, /^Bg1 0 z_oa1_x I=0\.0000095/m);   // slew 0.6 V/us -> Isl = 0.6e6 * Cp
  // swap flips which input is + (t0 and t1 exchange)
  const a = withParams(ckt, 1, undefined).text.match(/^Bg1 .*v\((\S+)\)-v\((\S+)\)\)/m);
  const b = withParams(ckt, 1, { swap: 'true' }).text.match(/^Bg1 .*v\((\S+)\)-v\((\S+)\)\)/m);
  assert.deepEqual([a[1], a[2]], [b[2], b[1]]);
  assert.match(withParams(ckt, 1, { slew: '-1' }).errors.join(), /Slew Rate must be a positive number/);
  // the internal node never shows up in the results
  const raw = { data: [{ name: 'time', values: [0, 1] }, { name: 'v(n1)', values: [0, 1] }, { name: 'z_oa1_x', values: [0, 1] }, { name: 'v(z_oa1_x)', values: [0, 1] }] };
  assert.deepEqual(normalizeRaw(raw, 'tran').vectors.map((v) => v.label), ['v(n1)']);
});

await test('logic gates: automatic bridges, shared digital nets, errors', () => {
  const ed = new Editor();
  ed.loadElements([
    ['ClockElm', 0, 0, 16, 0, '5 V, 1 kHz'],
    ['WireElm', 0, 0, 64, -16],
    ['RailElm', 64, 16, 80, 16, '5 V'],
    ['NandGateElm', 64, 0, 128, 0],
    ['WireElm', 128, 0, 160, 0],
    ['InverterElm', 160, 0, 224, 0],
    ['ResistorElm', 224, 0, 288, 0],
    ['GroundElm', 288, 0, 288, 16],
  ]);
  ed.els.find((e) => e.type === 'InverterElm').params = { delay: '10n' };
  const r = buildCircuitNetlist({ elements: ed.els, terminalsOf: (e) => ed.terminals(e), analysis: { type: 'tran', params: { step: '1u', stop: '3m' } } });
  assert.ok(r.ok, r.errors.join());
  assert.match(r.text, /^V1 n1 0 PULSE\(0 5 0 /m);
  assert.match(r.text, /^A1 \[d_n1 d_n2\] d_n3 G_NAND$/m);       // NAND inputs read the digital shadows
  assert.match(r.text, /^A2 d_n3 d_n4 G_INVERTER_2$/m);          // gate-to-gate net stays digital
  assert.match(r.text, /^Abr\d+ \[n1\] \[d_n1\] ADC_5$/m);          // analog net feeding a gate input
  assert.match(r.text, /^Abr\d+ \[d_n3\] \[n3\] DAC_5$/m);          // gate output also drives its analog net
  assert.match(r.text, /^\.model G_INVERTER_2 d_inverter\(rise_delay=1e-8 fall_delay=1e-8\)$/m);
  assert.match(r.text, /^\.model ADC_5 adc_bridge\(in_low=1\.5 in_high=3\.5\)$/m);
  // two outputs on one net, and an undriven input, are errors
  assert.match(build([['InverterElm', 0, 0, 64, 0], ['InverterElm', 128, 0, 64, 0], ['GroundElm', 0, 32, 0, 48]]).errors.join(), /outputs are connected together/);
  assert.match(build([['InverterElm', 0, 0, 64, 0], ['GroundElm', 64, 0, 64, 16]]).errors.join(), /nothing driving it/);
  // shadow nodes never reach the results list
  const raw = { data: [{ name: 'time', values: [0, 1] }, { name: 'v(n3)', values: [0, 1] }, { name: 'v(d_n3)', values: [0, 1] }, { name: 'd_n3', values: [0, 1] }] };
  assert.deepEqual(normalizeRaw(raw, 'tran').vectors.map((v) => v.label), ['v(n3)']);
});
await test('flip-flops: port order, NULL for unused pins, models, dummy outputs', () => {
  const ed = new Editor();
  ed.loadElements([
    ['ClockElm', 0, 0, 16, 0, '5 V, 1 kHz'],
    ['DFlipFlopElm', 64, 0, 144, 0],
    ['WireElm', 0, 0, 0, 16], ['WireElm', 0, 16, 64, 16],
    ['WireElm', 144, 16, 160, 16], ['WireElm', 160, 16, 160, -48], ['WireElm', 160, -48, 48, -48],
    ['WireElm', 48, -48, 48, -16], ['WireElm', 48, -16, 64, -16],
    ['ResistorElm', 144, -16, 208, -16], ['GroundElm', 208, -16, 208, 0],
  ]);
  ed.els.find((e) => e.type === 'DFlipFlopElm').params = { delay: '5n', ic: '1' };
  const r = buildCircuitNetlist({ elements: ed.els, terminalsOf: (e) => ed.terminals(e), analysis: { type: 'tran', params: { step: '20u', stop: '20m' } } });
  assert.ok(r.ok, r.errors.join());
  assert.equal(r.warnings.length, 0, r.warnings.join());       // unused SET / RST do not warn
  assert.match(r.text, /^A1 d_n2 d_n1 NULL NULL d_n5 d_n2 F_DFF_1$/m); // D(=Q-bar net) CLK SET RST Q Q-bar
  assert.match(r.text, /^\.model F_DFF_1 d_dff\(clk_delay=5e-9 ic=1\)$/m);
  // JK: J K CLK SET RST Q QB ; unused Q-bar gets a dummy node, a floating J is an error
  const jk = (extra = []) => {
    const e = new Editor();
    e.loadElements([['DCVoltageElm', 0, 0, 0, 32], ['JKFlipFlopElm', 64, 0, 144, 0], ['ClockElm', 32, 0, 48, 0], ['WireElm', 0, 0, 64, -16],
      ['WireElm', 32, 0, 64, 0], ['WireElm', 0, 32, 64, 16], ['GroundElm', 0, 32, 0, 48], ...extra]);
    return buildCircuitNetlist({ elements: e.els, terminalsOf: (x) => e.terminals(x), analysis: { type: 'op', params: {} } });
  };
  assert.match(jk().text, /^A1 d_\w+ d_\w+ d_\w+ NULL NULL d_nc1 d_nc2 F_JKFF$/m);
  // SR latch: S R Q Qb with enable/set/reset NULL
  const e2 = new Editor();
  e2.loadElements([['DCVoltageElm', 0, 0, 0, 32], ['SRLatchElm', 64, 0, 144, 0], ['WireElm', 0, 0, 64, -16], ['WireElm', 0, 32, 64, 16], ['GroundElm', 0, 32, 0, 48]]);
  const sr = buildCircuitNetlist({ elements: e2.els, terminalsOf: (x) => e2.terminals(x), analysis: { type: 'op', params: {} } });
  assert.match(sr.text, /^A1 d_\w+ d_\w+ NULL NULL NULL d_nc1 d_nc2 F_SRLATCH$/m);
});

await test('switch state, AC/clock parameters and unit labels', () => {
  const ckt = (type, params, value) => {
    const e = new Editor();
    e.loadElements([[type, 0, 0, 0, 64, value], ['ResistorElm', 0, 0, 64, 0], ['WireElm', 64, 0, 64, 64], ['WireElm', 0, 64, 64, 64], ['GroundElm', 0, 64, 0, 80]]);
    if (params) e.els[0].params = params;
    return buildCircuitNetlist({ elements: e.els, terminalsOf: (x) => e.terminals(x), analysis: { type: 'op', params: {} } });
  };
  // switch
  const e = new Editor();
  e.loadElements([['DCVoltageElm', 0, 0, 0, 64, '5 V'], ['SwitchElm', 0, 0, 64, 0], ['WireElm', 64, 0, 64, 64], ['WireElm', 0, 64, 64, 64], ['GroundElm', 0, 64, 0, 80]]);
  e.els[1].params = { open: 'true' };
  assert.match(buildCircuitNetlist({ elements: e.els, terminalsOf: (x) => e.terminals(x), analysis: { type: 'op', params: {} } }).text, /^R1 \S+ \S+ 1e9$/m);
  // AC source: label text still works, params override, offset and phase are written
  assert.match(ckt('ACVoltageElm', undefined, '5 V, 100 Hz').text, /SIN\(0 5 100\) AC 1/);
  assert.match(ckt('ACVoltageElm', { amp: '2', freq: '1k', offset: '1', phase: '90' }, '5 V, 100 Hz').text, /SIN\(1 2 1000 0 0 90\) AC 1/);
  assert.match(ckt('ACVoltageElm', { freq: '-1' }, '5 V').errors.join(), /frequency must be greater than 0/);
  // clock duty
  assert.match(ckt('ClockElm', { amp: '3.3', freq: '1k', duty: '25' }, '5 V, 1 kHz').text, /PULSE\(0 3\.3 0 0\.000001 0\.000001 0\.000249 0\.001\)/);
  assert.match(ckt('ClockElm', { duty: '100' }, '5 V, 1 kHz').errors.join(), /duty cycle must be between 1 and 99/);
  // labels and stepping
  assert.equal(withUnit('1k', 'Ω'), '1kΩ');
  assert.equal(withUnit('10u', 'F'), '10uF');
  assert.equal(withUnit('5 V', 'V'), '5 V');
  assert.equal(withUnit('Meg', 'Ω'), 'Meg');
  assert.equal(stepText('1 F', 1, '1', 'F'), '2');           // 1 farad, not 1 femto
  for (const t of ['ResistorElm', 'CapacitorElm', 'InductorElm', 'DCVoltageElm', 'ACVoltageElm', 'ClockElm', 'CurrentElm', 'SwitchElm', 'RailElm']) assert.ok(PART_PARAMS[t], t);
});

await test('sample: D flip-flop builds, switches start open with pull-downs', () => {
  const ed = new Editor();
  ed.loadElements(SAMPLES.dff.elements);
  const r = buildCircuitNetlist({ elements: ed.els, terminalsOf: (e) => ed.terminals(e), analysis: { type: 'tran', params: { step: '20u', stop: '20m' } } });
  assert.ok(r.ok, r.errors.join());
  assert.equal(r.warnings.length, 0, r.warnings.join());
  assert.match(r.text, /^A1 d_\w+ d_\w+ d_\w+ d_\w+ d_\w+ d_\w+ F_DFF$/m);   // D CLK SET RST Q Q-bar
  assert.equal((r.text.match(/ 1e9$/gm) ?? []).length, 2);                    // both switches open
  assert.equal((r.text.match(/^R\d+ \S+ 0 10000$/gm) ?? []).length, 2);          // pull-downs to ground
});

await test('export: SVG of a circuit, bounds, empty circuit, arcs and text', () => {
  const ed = new Editor();
  assert.equal(circuitToSvg(ed), null);
  assert.equal(circuitBounds(ed), null);
  ed.loadElements(SAMPLES.dff.elements);
  const svg = circuitToSvg(ed);
  assert.match(svg, /^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg" width="\d+" height="\d+" viewBox="0 0 \d+ \d+">/);
  assert.match(svg, /<rect width="\d+" height="\d+" fill="#ffffff"\/>/);
  assert.ok((svg.match(/<path /g) ?? []).length > 20, 'draws the symbols');
  assert.match(svg, />D FF<\/text>/);                        // chip title
  assert.match(svg, />10 kΩ<\/text>/);                       // value labels, escaped properly
  assert.ok(!/NaN|undefined/.test(svg), 'no NaN or undefined in the output');
  assert.match(svg, /<\/svg>\n$/);
  // the document is well-formed enough that every tag closes
  assert.equal((svg.match(/<text /g) ?? []).length, (svg.match(/<\/text>/g) ?? []).length);
  // everything lies inside the viewBox
  const b = circuitBounds(ed);
  for (const el of ed.els) for (const t of ed.terminals(el)) assert.ok(t.x >= b.x && t.x <= b.x + b.w && t.y >= b.y && t.y <= b.y + b.h);
  // SvgContext: half circle through the right side, then a mirrored copy
  const c = new SvgContext();
  c.beginPath(); c.arc(0, 0, 10, Math.PI / 2, -Math.PI / 2, true); c.stroke();
  const xs = [...c.out[0].matchAll(/[ML]([-\d.]+) ([-\d.]+)/g)].map((m) => +m[1]);
  assert.ok(Math.max(...xs) > 9.9 && Math.min(...xs) > -0.01, 'counter-clockwise half circle bulges to +x');
  const m = new SvgContext();
  m.translate(5, 5); m.scale(1, -1);
  m.beginPath(); m.moveTo(0, 2); m.lineTo(0, 4); m.stroke();
  assert.match(m.out[0], /d="M5 3L5 1"/);
  const t2 = new SvgContext();
  t2.textAlign = 'center'; t2.textBaseline = 'middle'; t2.font = '9px sans-serif'; t2.fillText('A<B', 1, 2);
  assert.match(t2.out[0], /text-anchor="middle" dominant-baseline="central" fill="#000000">A&lt;B<\/text>/);
});

await test('mouse-wheel value editing steps the part under the cursor', () => {
  const ed = new Editor();
  ed.loadElements([['ResistorElm', 160, 160, 224, 160, '1 kΩ'], ['CapacitorElm', 160, 224, 224, 224, '1 F'], ['WireElm', 0, 0, 64, 0]]);
  ed.setOptions({ wheelEdit: true });
  const at = (x, y) => ed.toWorld ? { x: x * ed.view.s + ed.view.ox, y: y * ed.view.s + ed.view.oy } : { x, y };
  const up = { deltaY: -100 };
  const down = { deltaY: 100 };
  assert.equal(ed.wheelEditValue(up, at(192, 160)), true);
  assert.equal(ed.els[0].value, '2kΩ');                      // 1k -> 2k, unit re-attached
  ed.wheelEditValue(up, at(192, 160));
  assert.equal(ed.els[0].value, '5kΩ');
  ed.wheelEditValue(down, at(192, 160));
  assert.equal(ed.els[0].value, '2kΩ');
  assert.equal(ed.undoStack.length, 1);                       // a burst of scrolling is one undo step
  ed.wheelEditValue(up, at(192, 224));
  assert.equal(ed.els[1].value, '2F');                        // 1 farad, not 1 femto
  assert.equal(ed.wheelEditValue(up, at(500, 500)), false);   // nothing under the cursor: zoom as usual
  assert.equal(ed.wheelEditValue(up, at(32, 0)), false);      // wires have no value
  ed.setOptions({ noEdit: true });
});

await test('logic input and output: DC source from state, lamp adds nothing, click toggles', () => {
  const ed = new Editor();
  ed.loadElements([['LogicInputElm', 0, 0, 16, 0], ['InverterElm', 64, 0, 128, 0], ['WireElm', 0, 0, 64, 0], ['LogicOutputElm', 128, 0, 144, 0], ['GroundElm', 192, 0, 192, 16], ['ResistorElm', 128, 0, 192, 0]]);
  const build2 = () => buildCircuitNetlist({ elements: ed.els, terminalsOf: (e) => ed.terminals(e), analysis: { type: 'op', params: {} } });
  const r0 = build2();
  assert.ok(r0.ok, r0.errors.join());
  assert.match(r0.text, /^V1 n1 0 DC 0$/m);                  // default LOW
  assert.doesNotMatch(r0.text, /LogicOutput/);               // the lamp is not a circuit element
  ed.els[0].params = { high: 'true', vhigh: '3.3' };
  assert.match(build2().text, /^V1 n1 0 DC 3\.3$/m);
  // clicking the input toggles it (pointerUp path): simulate the drag record it leaves behind
  ed.els[0].params = {};
  ed.drag = { type: 'move', moved: false, hitId: ed.els[0].id };
  ed.pointerUp({ shiftKey: false, pointerId: 1 });
  assert.equal(ed.els[0].params.high, 'true');
});

await test('sample: NAND with logic inputs builds', () => {
  const ed = new Editor();
  ed.loadElements(SAMPLES.nand.elements);
  ed.els[0].params = { high: 'true' };
  ed.els[1].params = { high: 'true' };
  const r = buildCircuitNetlist({ elements: ed.els, terminalsOf: (e) => ed.terminals(e), analysis: { type: 'op', params: {} } });
  assert.ok(r.ok, r.errors.join());
  assert.equal(r.warnings.length, 0, r.warnings.join());
  assert.match(r.text, /^V1 n1 0 DC 5$/m);
  assert.match(r.text, /^A1 \[d_n1 d_n2\] d_n3 G_NAND$/m);
});

await test('SPICE directives: allowlist, continuation, blocked commands, netlist and canvas box', () => {
  const ok = checkDirectives('* a comment\n.param vcc=5 ; trailing\n.model DX D(IS=1e-14\n+ RS=2)\n.options reltol=1e-4\n.ic v(n1)=2');
  assert.deepEqual(ok.problems, []);
  assert.deepEqual(ok.lines, ['.param vcc=5', '.model DX D(IS=1e-14 RS=2)', '.options reltol=1e-4', '.ic v(n1)=2']);
  const bad = (t) => checkDirectives(t).problems.join(' | ');
  assert.match(bad('.include foo.lib'), /\.include is not allowed/);
  assert.match(bad('.lib x'), /\.lib is not allowed/);
  assert.match(bad('.control'), /\.control is not allowed/);
  assert.match(bad('.tran 1u 1m'), /Analysis Setup/);
  assert.match(bad('R1 a b 1k'), /not a directive/);
  assert.match(bad('.model x d_source(input_file=data.txt)'), /file or script/);
  assert.match(bad('.param s="abc"'), /quotes/);
  assert.match(bad('.param x=1 ; ok\n.shell ls'), /\.shell is not allowed/);
  assert.equal(logicalLines('\n\n* c\n').length, 0);
  // in a circuit: the lines land after the model cards, errors keep the run from starting
  const ed = new Editor();
  ed.loadElements([['DCVoltageElm', 0, 0, 0, 64, '5 V'], ['ResistorElm', 0, 0, 64, 0, '1k'], ['WireElm', 64, 0, 64, 64], ['WireElm', 0, 64, 64, 64], ['GroundElm', 0, 64, 0, 80],
    ['DirectiveElm', 160, 0, 208, 0, '.param gain=10\n.options reltol=1e-4']]);
  const an = { type: 'op', params: {} };
  const r = buildCircuitNetlist({ elements: ed.els, terminalsOf: (e) => ed.terminals(e), analysis: an });
  assert.ok(r.ok, r.errors.join());
  assert.match(r.text, /\.param gain=10\n\.options reltol=1e-4\n\.op\n\.end/);
  ed.els.at(-1).value = '.include evil.lib';
  const r2 = buildCircuitNetlist({ elements: ed.els, terminalsOf: (e) => ed.terminals(e), analysis: an });
  assert.equal(r2.ok, false);
  assert.match(r2.errors.join(), /SPICE Directive: line 1: \.include is not allowed/);
  // the block is what you click on, grows with the text, and is exported
  ed.els.at(-1).value = '.param a=1\n.param averyveryverylongname=2';
  const b = directiveBox(ed.els.at(-1));
  assert.equal(b.lines.length, 2);
  assert.ok(b.w > 150 && b.h === 2 * 14 + 12);
  assert.equal(ed.hitTest(b.x + b.w - 3, b.y + b.h - 3)?.type, 'DirectiveElm');
  assert.equal(ed.hitTest(b.x + b.w + 40, b.y), null);
  assert.match(circuitToSvg(ed), /averyveryverylongname=2<\/text>/);
});

await test('Subcircuit block: pins from the library definition, X card, params, document round trip', () => {
  const library = [{ kind: 'subckt', name: 'AMP2', type: 'SUBCKT', pins: ['in', 'out', 'vcc', 'gnd'], params: [{ name: 'gain', def: '10' }], file: 'amp.lib' }];
  const ed = new Editor();
  ed.loadElements([['SubcktElm', 0, 0, 128, 0]]);
  assert.equal(ed.terminals(ed.els[0]).length, 0);
  ed.setProps(ed.els[0].id, { model: 'AMP2', pins: library[0].pins, params: { gain: '5' } });
  const t = ed.terminals(ed.els[0]);
  assert.equal(t.length, 4);
  assert.deepEqual(t.map((p) => [p.x, p.y]), [[0, -16], [0, 16], [128, -16], [128, 16]]);
  // wire ports to nets: ground on gnd, source on in
  ed.loadElements([['SubcktElm', 0, 0, 128, 0, undefined], GND, ['DCVoltageElm', 200, 0, 200, 64, '5 V']]);
  ed.setProps(ed.els[0].id, { model: 'AMP2', pins: library[0].pins, params: { gain: '5' } });
  const r = buildCircuitNetlist({ elements: ed.els, terminalsOf: (e) => ed.terminals(e), title: 't', analysis: { type: 'op', params: {} }, library });
  assert.match(r.text, /^X1 \S+ \S+ \S+ \S+ AMP2 gain=5$/m);
  assert.deepEqual(r.libs, ['amp.lib']);
  // missing from library / not chosen
  const none = buildCircuitNetlist({ elements: ed.els, terminalsOf: (e) => ed.terminals(e), title: 't', analysis: { type: 'op', params: {} }, library: [] });
  assert.ok(none.errors.some((m) => /AMP2.*not found/.test(m)));
  const changed = buildCircuitNetlist({ elements: ed.els, terminalsOf: (e) => ed.terminals(e), title: 't', analysis: { type: 'op', params: {} }, library: [{ ...library[0], pins: ['a', 'b'] }] });
  assert.ok(changed.errors.some((m) => /4 pins but AMP2 now has 2/.test(m)));
  // saved file keeps the pins
  const doc = JSON.parse(JSON.stringify(ed.toDocument('x')));
  const ed2 = new Editor();
  ed2.loadDocument(doc);
  assert.deepEqual(ed2.els[0].pins, library[0].pins);
  assert.equal(ed2.terminals(ed2.els[0]).length, 4);
  // odd pin count: 3 pins -> 2 left, 1 right
  ed2.setProps(ed2.els[0].id, { pins: ['a', 'b', 'c'] });
  assert.deepEqual(ed2.terminals(ed2.els[0]).map((p) => p.x), [0, 0, 128]);
});

await test('Labeled nodes: same name joins nets, names reach the netlist, 0/gnd is ground, conflicts reported', () => {
  const r = build([
    ['DCVoltageElm', 0, 0, 0, 64, '5 V'], ['LabeledNodeElm', 0, 0, 16, 0, 'VCC'],
    ['LabeledNodeElm', 200, 0, 216, 0, 'vcc'], ['ResistorElm', 200, 0, 200, 64, '1k'],
    ['LabeledNodeElm', 0, 64, 16, 64, 'GND'], ['LabeledNodeElm', 200, 64, 216, 64, '0'],
  ]);
  assert.deepEqual(r.errors, []);
  assert.match(r.text, /^V1 vcc 0 DC 5$/m);
  assert.match(r.text, /^R1 vcc 0 1000$/m);
  const bad = build([['ResistorElm', 0, 0, 64, 0, '1k'], ['LabeledNodeElm', 0, 0, 16, 0, 'a'], ['LabeledNodeElm', 64, 0, 80, 0, 'b'], ['WireElm', 0, 0, 64, 0], ['GroundElm', 300, 0, 300, 16]]);
  assert.ok(bad.errors.some((m) => /"a" and "b" are on the same net/.test(m)));
  const res = build([['LabeledNodeElm', 0, 0, 16, 0, 'n3'], ['LabeledNodeElm', 40, 0, 56, 0, ''], ['LabeledNodeElm', 80, 0, 96, 0, '1x'], GND]);
  assert.equal(res.errors.filter((m) => /Labeled Node/.test(m)).length, 3);
});

let ed2;
await test('Pack as subcircuit: ports become pins, body is wrapped, unsupported content refused', () => {
  const ed = new Editor();
  // divider: IN -- R1 -- OUT -- R2 -- ground, ports IN and OUT
  ed.loadElements([
    ['PortElm', 0, 0, 16, 0, 'in'], ['ResistorElm', 0, 0, 64, 0, '1k'], ['PortElm', 64, 0, 80, 0, 'out'],
    ['ResistorElm', 64, 0, 64, 64, '2k'], ['GroundElm', 64, 64, 64, 80],
  ]);
  const pk = (name) => buildCircuitNetlist({ elements: ed.els, terminalsOf: (e) => ed.terminals(e), title: 'Divider', analysis: null, pack: { name } });
  const r = pk('DIV');
  assert.deepEqual(r.errors, []);
  assert.deepEqual(r.ports, ['in', 'out']);
  assert.match(r.text, /^\.subckt DIV in out$/m);
  assert.match(r.text, /^R1 in out 1000$/m);
  assert.match(r.text, /^R2 out 0 2000$/m);
  assert.match(r.text, /^\.ends DIV$/m);
  // the packed text parses back as a library subcircuit with those pins
  const found = parseLibraryText(r.text, 'DIV.lib')[0];
  assert.deepEqual([found.name, found.pins], ['DIV', ['in', 'out']]);
  assert.ok(pk('1bad').errors.some((m) => /Subcircuit name/.test(m)));
  // no ports, no ground needed
  const none = buildCircuitNetlist({ elements: build([['ResistorElm', 0, 0, 64, 0, '1k']]) && (() => { const e = new Editor(); e.loadElements([['ResistorElm', 0, 0, 64, 0, '1k']]); ed2 = e; return e.els; })(), terminalsOf: (x) => ed2.terminals(x), analysis: null, pack: { name: 'X' } });
  assert.ok(none.errors.some((m) => /at least one Subcircuit Port/.test(m)));
  assert.ok(!none.errors.some((m) => /no ground/.test(m)));
});

console.log(`\n${n} tests passed`);
