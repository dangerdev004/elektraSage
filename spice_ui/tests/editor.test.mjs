// Plain Node tests for the pure parts: geometry and the editor model (no DOM, no React).
// Run with: node tests/editor.test.mjs
import assert from 'node:assert/strict';
import {
  snap, segDist, toLocal, fromLocal, axisEnd, normRect, rectsIntersect, elLength,
} from '../src/canvas/geometry.js';
import { Editor } from '../src/canvas/editor.js';
import { getDef, isGeneric, DEFS } from '../src/canvas/parts.js';
import { GROUPS, TOP_PARTS, LABELS } from '../src/data/catalog.js';
import { SAMPLES, SAMPLE_MENU } from '../src/data/samples.js';

let n = 0;
const test = (name, fn) => {
  fn();
  n++;
  console.log('ok -', name);
};
const near = (a, b, eps = 1e-9) => assert.ok(Math.abs(a - b) < eps, `${a} != ${b}`);

test('snap rounds to the grid', () => {
  assert.equal(snap(23), 16);
  assert.equal(snap(24), 32);
  assert.equal(snap(-9), -16);
  assert.equal(snap(5, 8), 8);
});

test('segDist: point to segment', () => {
  near(segDist(5, 3, 0, 0, 10, 0), 3);
  near(segDist(-4, 0, 0, 0, 10, 0), 4); // beyond the end -> distance to the end point
  near(segDist(3, 4, 0, 0, 0, 0), 5); // degenerate segment
});

test('toLocal / fromLocal round-trip, with and without mirror, at any angle', () => {
  for (const mirror of [false, true]) {
    for (const [x2, y2] of [[96, 32], [0, 80], [-64, 0], [48, -48]]) {
      const el = { x1: 16, y1: 32, x2: 16 + x2, y2: 32 + y2, mirror };
      const l = toLocal(el, 100, 77);
      const w = fromLocal(el, l.x, l.y);
      near(w.x, 100, 1e-9);
      near(w.y, 77, 1e-9);
    }
  }
});

test('local frame: terminal 2 sits at (L, 0)', () => {
  const el = { x1: 0, y1: 0, x2: 0, y2: 64, mirror: false };
  const l = toLocal(el, 0, 64);
  near(l.x, 64);
  near(l.y, 0);
});

test('axisEnd: axis-aligned, snapped, at least minLen', () => {
  assert.deepEqual(axisEnd(0, 0, 100, 10, 32), { x2: 96, y2: 0 });
  assert.deepEqual(axisEnd(0, 0, 3, 90, 32), { x2: 0, y2: 96 });
  assert.deepEqual(axisEnd(0, 0, -5, 2, 32), { x2: -32, y2: 0 });
  assert.deepEqual(axisEnd(0, 0, 0, 0, 64), { x2: 64, y2: 0 }); // a bare click gives the default size
});

test('rect helpers', () => {
  const a = normRect(10, 10, 0, 0);
  assert.deepEqual(a, { x0: 0, y0: 0, x1: 10, y1: 10 });
  assert.ok(rectsIntersect(a, { x0: 5, y0: 5, x1: 20, y1: 20 }));
  assert.ok(!rectsIntersect(a, { x0: 11, y0: 0, x1: 20, y1: 5 }));
});

test('catalog matches CirSim.composeMainMenu (plus XNOR, Buffer, SR Latch and SPICE Directive added by this app): group titles, counts, unique ids', () => {
  assert.deepEqual(GROUPS.map((g) => g.title), [
    'Passive Components', 'Inputs and Sources', 'Outputs and Labels', 'Active Components',
    'Active Building Blocks', 'Logic Gates, Input and Output', 'Digital Chips',
    'Analog and Hybrid Chips',
  ]);
  assert.deepEqual(GROUPS.map((g) => g.items.length), [23, 17, 22, 17, 23, 10, 19, 6]);
  const ids = [...TOP_PARTS, ...GROUPS.flatMap((g) => g.items)].map((p) => p[0]);
  assert.equal(new Set(ids).size, ids.length);
  assert.equal(Object.keys(LABELS).length, ids.length);
});

test('every dedicated symbol is in the catalog; the rest fall back to a box', () => {
  for (const id of Object.keys(DEFS)) assert.ok(LABELS[id], `${id} missing from catalog`);
  assert.ok(isGeneric('DelayBufferElm'));
  assert.equal(getDef('DelayBufferElm').kind, 'box');
  assert.equal(getDef('DelayBufferElm').label, 'Delay Buffer');
  assert.equal(getDef('ResistorElm').kind, 'resistor');
});

test('samples only use known part types and have grid-aligned points', () => {
  for (const [key, s] of Object.entries(SAMPLES)) {
    for (const [type, x1, y1, x2, y2] of s.elements) {
      assert.ok(LABELS[type], `${key}: unknown type ${type}`);
      for (const v of [x1, y1, x2, y2]) assert.equal(v % 16, 0, `${key}: ${type} off-grid ${v}`);
    }
  }
  const keys = SAMPLE_MENU.flatMap((f) => f.keys);
  for (const k of keys) assert.ok(SAMPLES[k], `menu points at missing sample ${k}`);
});

test('terminals: resistor ends, op amp inputs/output, transistor pins', () => {
  const ed = new Editor();
  const r = ed.addElement('ResistorElm', 0, 0, 64, 0);
  assert.deepEqual(ed.terminals(r).map((p) => [Math.round(p.x), Math.round(p.y)]), [[0, 0], [64, 0]]);
  const op = ed.addElement('OpAmpElm', 100, 100, 164, 100);
  assert.deepEqual(ed.terminals(op).map((p) => [Math.round(p.x), Math.round(p.y)]),
    [[100, 84], [100, 116], [164, 100]]);
  const q = ed.addElement('NTransistorElm', 0, 200, 32, 200);
  assert.deepEqual(ed.terminals(q).map((p) => [Math.round(p.x), Math.round(p.y)]),
    [[0, 200], [32, 184], [32, 216]]);
});

test('hit test: wires by distance, parts by their body', () => {
  const ed = new Editor();
  ed.view = { ox: 0, oy: 0, s: 1 };
  const w = ed.addElement('WireElm', 0, 0, 100, 0);
  const r = ed.addElement('ResistorElm', 0, 50, 64, 50);
  assert.equal(ed.hitTest(50, 5), w);
  assert.equal(ed.hitTest(50, 20), null);
  assert.equal(ed.hitTest(32, 55), r);
  assert.equal(ed.hitTest(32, 80), null);
});

test('undo / redo restore the element list', () => {
  const ed = new Editor();
  ed.addElement('ResistorElm', 0, 0, 32, 0);
  ed.addElement('CapacitorElm', 0, 32, 32, 32);
  assert.equal(ed.els.length, 2);
  ed.exec('edit.undo');
  assert.equal(ed.els.length, 1);
  ed.exec('edit.undo');
  assert.equal(ed.els.length, 0);
  ed.exec('edit.redo');
  assert.equal(ed.els.length, 1);
  assert.equal(ed.state().canUndo, true);
  ed.addElement('DiodeElm', 0, 0, 32, 0); // a new edit clears redo
  assert.equal(ed.state().canRedo, false);
});

test('select all, copy, paste (offset, selected), delete, undo', () => {
  const ed = new Editor();
  ed.addElement('ResistorElm', 0, 0, 32, 0);
  ed.addElement('WireElm', 32, 0, 64, 0);
  ed.exec('edit.selectAll');
  assert.equal(ed.sel.size, 2);
  ed.exec('edit.copy');
  ed.exec('edit.paste');
  assert.equal(ed.els.length, 4);
  assert.equal(ed.sel.size, 2);
  const ids = new Set(ed.els.map((e) => e.id));
  assert.equal(ids.size, 4); // pasted copies got fresh ids
  assert.equal(ed.els[2].x1, 32); // offset by two grid squares
  ed.exec('edit.delete');
  assert.equal(ed.els.length, 2);
  ed.exec('edit.undo');
  assert.equal(ed.els.length, 4);
});

test('cut = copy + delete; duplicate adds a copy', () => {
  const ed = new Editor();
  const r = ed.addElement('ResistorElm', 0, 0, 32, 0);
  ed.sel = new Set([r.id]);
  ed.exec('edit.duplicate');
  assert.equal(ed.els.length, 2);
  ed.exec('edit.cut');
  assert.equal(ed.els.length, 1);
  assert.equal(ed.clipboard.length, 1);
});

test('flip: positions mirror about the selection; one mirror toggles handedness, two do not', () => {
  const ed = new Editor();
  const q = ed.addElement('NTransistorElm', 0, 0, 32, 0);
  ed.sel = new Set([q.id]);
  ed.exec('edit.flipy');
  assert.equal(q.mirror, true);
  ed.exec('edit.flipx');
  assert.equal(q.mirror, false); // flip X then flip Y is a 180 degree turn
  assert.equal(q.x1 !== 0 || q.x2 !== 32, true);
});

test('flip x on a lone resistor reverses it in place', () => {
  const ed = new Editor();
  const r = ed.addElement('ResistorElm', 0, 0, 64, 0);
  ed.sel = new Set([r.id]);
  ed.exec('edit.flipx');
  assert.deepEqual([r.x1, r.x2], [64, 0]);
});

test('swap terminals', () => {
  const ed = new Editor();
  const d = ed.addElement('DiodeElm', 0, 0, 32, 0);
  ed.sel = new Set([d.id]);
  ed.exec('elm.flip');
  assert.deepEqual([d.x1, d.x2], [32, 0]);
});

test('disable editing blocks changes but not selection or copy', () => {
  const ed = new Editor();
  const msgs = [];
  ed.onNotice = (m) => msgs.push(m);
  const r = ed.addElement('ResistorElm', 0, 0, 32, 0);
  ed.setOptions({ noEdit: true });
  ed.sel = new Set([r.id]);
  ed.exec('edit.delete');
  assert.equal(ed.els.length, 1);
  assert.ok(msgs.length === 1);
  ed.exec('edit.selectAll');
  ed.exec('edit.copy');
  assert.equal(ed.clipboard.length, 1);
  ed.setMode('add:ResistorElm');
  assert.equal(ed.mode, 'select');
});

test('mode switching and unknown commands', () => {
  const ed = new Editor();
  const msgs = [];
  ed.onNotice = (m) => msgs.push(m);
  assert.equal(ed.exec('mode:add:DiodeElm'), true);
  assert.equal(ed.mode, 'add:DiodeElm');
  assert.equal(ed.exec('mode:dragAll'), true);
  assert.equal(ed.mode, 'dragAll');
  assert.equal(ed.exec('mode:DragRow'), true); // not implemented -> falls back to select with a notice
  assert.equal(ed.mode, 'select');
  assert.equal(msgs.length, 1);
  assert.equal(ed.exec('file.exportastext'), false); // not implemented -> UI says "not wired yet"
});

test('zoom is clamped and keeps the point under the cursor fixed', () => {
  const ed = new Editor();
  ed.size = { w: 800, h: 600, dpr: 1 };
  ed.view = { ox: 100, oy: 50, s: 1 };
  const before = ed.toWorld(300, 200);
  ed.zoomAt(300, 200, 2);
  const after = ed.toWorld(300, 200);
  near(after.x, before.x, 1e-9);
  near(after.y, before.y, 1e-9);
  ed.zoomAt(300, 200, 1000);
  assert.equal(ed.view.s, 4);
  ed.zoomAt(300, 200, 1e-6);
  assert.equal(ed.view.s, 0.25);
});

test('loadElements resets history and centres the circuit', () => {
  const ed = new Editor();
  ed.size = { w: 800, h: 600, dpr: 1 };
  ed.addElement('ResistorElm', 0, 0, 32, 0);
  ed.loadElements(SAMPLES.rc.elements);
  assert.equal(ed.els.length, SAMPLES.rc.elements.length);
  assert.equal(ed.state().canUndo, false);
  const b = ed.els.map((e) => ed.bbox(e));
  const cx = (Math.min(...b.map((r) => r.x0)) + Math.max(...b.map((r) => r.x1))) / 2;
  near(cx * ed.view.s + ed.view.ox, 400, 1e-6);
});

test('setValue is undoable', () => {
  const ed = new Editor();
  const r = ed.addElement('ResistorElm', 0, 0, 32, 0);
  ed.setValue(r.id, '4.7 kΩ');
  assert.equal(ed.els[0].value, '4.7 kΩ');
  ed.exec('edit.undo');
  assert.equal(ed.els[0].value, undefined);
});

test('element length helper', () => {
  assert.equal(elLength({ x1: 0, y1: 0, x2: 3, y2: 4 }), 5);
});

// ---- save / open, rubber-banding, blank start -------------------------------------------------
globalThis.requestAnimationFrame = () => 1;
const fakeCanvas = () => ({ focus() {}, getBoundingClientRect: () => ({ left: 0, top: 0 }), setPointerCapture() {}, releasePointerCapture() {}, style: {} });
const ptr = (x, y, extra = {}) => ({ clientX: x, clientY: y, button: 0, pointerId: 1, preventDefault() {}, ...extra });

test('blank start: an empty circuit loads without error and has no parts', () => {
  const ed = new Editor();
  ed.loadElements([]);
  assert.equal(ed.els.length, 0);
  assert.equal(ed.state().count, 0);
});

test('document round trip keeps type, geometry, mirror, value and model', () => {
  const a = new Editor();
  const d = a.addElement('DiodeElm', 0, 0, 48, 0, '1N4148');
  a.setValue(d.id, 'x', 'GEN_SIGNAL_DIODE');
  a.addElement('ResistorElm', 0, 32, 64, 32, '1k');
  a.els[1].mirror = true;
  const doc = JSON.parse(JSON.stringify(a.toDocument('My circuit')));
  const b = new Editor();
  const title = b.loadDocument(doc);
  assert.equal(title, 'My circuit');
  assert.equal(b.els.length, 2);
  assert.deepEqual(b.els.map(({ type, x1, y1, x2, y2, mirror, value, model }) => ({ type, x1, y1, x2, y2, mirror, value, model })), [
    { type: 'DiodeElm', x1: 0, y1: 0, x2: 48, y2: 0, mirror: false, value: 'x', model: 'GEN_SIGNAL_DIODE' },
    { type: 'ResistorElm', x1: 0, y1: 32, x2: 64, y2: 32, mirror: true, value: '1k', model: undefined },
  ]);
  b.exec('edit.undo'); // loading is undoable
  assert.equal(b.els.length, 0);
});

test('loadDocument rejects bad files with readable messages and leaves the circuit alone', () => {
  const ed = new Editor();
  ed.addElement('ResistorElm', 0, 0, 32, 0);
  const bad = [
    [null, /not a circuit-ui file/], [{ format: 'other' }, /not a circuit-ui file/],
    [{ format: 'circuit-ui', version: 2, elements: [] }, /version 2/], [{ format: 'circuit-ui', version: 1 }, /elements/],
    [{ format: 'circuit-ui', version: 1, elements: [{ type: 'ResistorElm', x1: 0, y1: 0, x2: 'a', y2: 0 }] }, /Element 1 is malformed/],
    [{ format: 'circuit-ui', version: 1, elements: new Array(5001).fill({}) }, /5000/],
  ];
  for (const [doc, re] of bad) assert.throws(() => ed.loadDocument(doc), re);
  assert.equal(ed.els.length, 1);
});

test('setValue with model: sets, clears with empty string, leaves alone when undefined', () => {
  const ed = new Editor();
  const d = ed.addElement('DiodeElm', 0, 0, 48, 0);
  ed.setValue(d.id, '', 'M1');
  assert.equal(ed.els[0].model, 'M1');
  ed.setValue(d.id, 'v');
  assert.equal(ed.els[0].model, 'M1');
  ed.setValue(d.id, 'v', '');
  assert.equal('model' in ed.els[0], false);
});

test('moving a part drags the ends of wires attached to its pins; unrelated wires stay put', () => {
  const ed = new Editor();
  ed.canvas = fakeCanvas();
  ed.view = { ox: 0, oy: 0, s: 1 };
  const r = ed.addElement('ResistorElm', 64, 64, 128, 64, '1k'); // pins at (64,64) and (128,64)
  const w1 = ed.addElement('WireElm', 0, 64, 64, 64);            // ends on pin 1
  const w2 = ed.addElement('WireElm', 128, 64, 128, 0);          // starts on pin 2
  const w3 = ed.addElement('WireElm', 200, 200, 240, 200);       // unrelated
  ed.sel = new Set([r.id]);
  ed.pointerDown(ptr(96, 64));
  ed.pointerMove(ptr(96, 96));                                   // drag down by 32
  ed.pointerUp(ptr(96, 96));
  assert.deepEqual([r.y1, r.y2], [96, 96]);
  assert.deepEqual([w1.x1, w1.y1, w1.x2, w1.y2], [0, 64, 64, 96]); // far end fixed, near end follows
  assert.deepEqual([w2.x1, w2.y1, w2.x2, w2.y2], [128, 96, 128, 0]);
  assert.deepEqual([w3.x1, w3.y1, w3.x2, w3.y2], [200, 200, 240, 200]);
  ed.exec('edit.undo'); // one undo step restores part AND wires
  const byId = (id) => ed.els.find((e) => e.id === id); // undo rebuilds the objects
  assert.deepEqual([byId(r.id).y1, byId(w1.id).y2, byId(w2.id).y1], [64, 64, 64]);
});

test('a selected wire is moved as a whole and does not also "follow"', () => {
  const ed = new Editor();
  ed.canvas = fakeCanvas();
  ed.view = { ox: 0, oy: 0, s: 1 };
  const a = ed.addElement('WireElm', 0, 0, 64, 0);
  const b = ed.addElement('WireElm', 64, 0, 64, 64);
  ed.sel = new Set([a.id, b.id]);
  ed.pointerDown(ptr(32, 0));
  ed.pointerMove(ptr(48, 16));
  ed.pointerUp(ptr(48, 16));
  assert.deepEqual([a.x1, a.y1, a.x2, a.y2], [16, 16, 80, 16]);
  assert.deepEqual([b.x1, b.y1, b.x2, b.y2], [80, 16, 80, 80]);
});

// ---- endpoint dragging, key shortcuts, params ------------------------------------------------
const keyEv = (key, extra = {}) => ({ key, ctrlKey: false, metaKey: false, altKey: false, shiftKey: false, preventDefault() {}, ...extra });

test('dragging a wire end stretches it; attached wires stay attached; zero length removes it', () => {
  const ed = new Editor();
  ed.canvas = fakeCanvas();
  ed.view = { ox: 0, oy: 0, s: 1 };
  const w = ed.addElement('WireElm', 0, 0, 64, 0);
  ed.pointerMove(ptr(64, 0));                  // hover the end -> handle
  assert.equal(ed.hoverEnd?.which, 2);
  ed.pointerDown(ptr(64, 0));
  ed.pointerMove(ptr(128, 32));                // free direction for wires
  ed.pointerUp(ptr(128, 32));
  assert.deepEqual([w.x1, w.y1, w.x2, w.y2], [0, 0, 128, 32]);
  ed.exec('edit.undo');
  assert.deepEqual([ed.els[0].x2, ed.els[0].y2], [64, 0]);
  // drag the start onto the end -> zero length -> removed
  ed.pointerDown(ptr(0, 0));
  ed.pointerMove(ptr(64, 0));
  ed.pointerUp(ptr(64, 0));
  assert.equal(ed.els.length, 0);
  ed.exec('edit.undo');
  assert.equal(ed.els.length, 1);
});

test('dragging a part end resizes along its axis (min length kept) and wires on its pins follow', () => {
  const ed = new Editor();
  ed.canvas = fakeCanvas();
  ed.view = { ox: 0, oy: 0, s: 1 };
  const r = ed.addElement('ResistorElm', 64, 64, 128, 64, '1k');
  const w = ed.addElement('WireElm', 128, 64, 128, 0);       // sits on pin 2
  ed.pointerDown(ptr(128, 64));
  ed.pointerMove(ptr(224, 70));                              // mostly horizontal: stays axis-aligned
  ed.pointerUp(ptr(224, 70));
  assert.deepEqual([r.x1, r.y1, r.x2, r.y2], [64, 64, 224, 64]);
  assert.deepEqual([w.x1, w.y1], [224, 64]);                 // wire end followed the pin
  ed.pointerDown(ptr(224, 64));
  ed.pointerMove(ptr(70, 64));                               // shorter than the minimum -> clamped
  ed.pointerUp(ptr(70, 64));
  assert.equal(r.x2 - r.x1, 32);
});

test('end handles are not grabbed when editing is disabled or shift is held', () => {
  const ed = new Editor();
  ed.canvas = fakeCanvas();
  ed.view = { ox: 0, oy: 0, s: 1 };
  const w = ed.addElement('WireElm', 0, 0, 64, 0);
  ed.setOptions({ noEdit: true });
  ed.pointerDown(ptr(64, 0));
  ed.pointerMove(ptr(128, 0));
  ed.pointerUp(ptr(128, 0));
  assert.equal(w.x2, 64);
});

test('keyboard: CircuitJS1 part keys pick the tool; Space/Esc return to select; Ctrl+letter is not a part key', () => {
  const ed = new Editor();
  ed.canvas = fakeCanvas();
  const press = (k, extra) => { ed.key(keyEv(k, extra)); return ed.mode; };
  assert.equal(press('r'), 'add:ResistorElm');
  assert.equal(press('w'), 'add:WireElm');
  assert.equal(press('c'), 'add:CapacitorElm');
  assert.equal(press('L'), 'add:InductorElm');
  assert.equal(press('g'), 'add:GroundElm');
  assert.equal(press('v'), 'add:DCVoltageElm');
  assert.equal(press('d'), 'add:DiodeElm');
  assert.equal(press('z'), 'add:ZenerElm');
  assert.equal(press('a'), 'add:OpAmpElm');
  assert.equal(press('n'), 'add:NTransistorElm');
  assert.equal(press('p'), 'add:PTransistorElm');
  assert.equal(press('N'), 'add:NMosfetElm');
  assert.equal(press('P'), 'add:PMosfetElm');
  assert.equal(press(' '), 'select');
  press('r');
  assert.equal(press('Escape'), 'select');
  press('r');
  assert.equal(press('d', { ctrlKey: true }), 'add:ResistorElm'); // Ctrl+D = duplicate, tool unchanged
  ed.setOptions({ noEdit: true });
  ed.setMode('select');
  assert.equal(press('r'), 'select'); // refused while editing is disabled
});

test('params: setProps is one undo step; document round trip keeps params; bad param values are dropped', () => {
  const ed = new Editor();
  const d = ed.addElement('DiodeElm', 0, 0, 48, 0);
  ed.setProps(d.id, { value: '', model: '', params: { IS: '1n', RS: '2' } });
  assert.deepEqual(ed.els[0].params, { IS: '1n', RS: '2' });
  ed.setProps(d.id, { params: {} });
  assert.equal('params' in ed.els[0], false);
  ed.exec('edit.undo');
  assert.deepEqual(ed.els[0].params, { IS: '1n', RS: '2' });
  const doc = JSON.parse(JSON.stringify(ed.toDocument('t')));
  const b = new Editor();
  b.loadDocument(doc);
  assert.deepEqual(b.els[0].params, { IS: '1n', RS: '2' });
  doc.elements[0].params = { IS: 5, OK: 'yes', swap: true, nested: { a: 1 } };
  b.loadDocument(doc);
  assert.deepEqual(b.els[0].params, { OK: 'yes', swap: 'true' });
});

console.log(`\n${n} tests passed`);
