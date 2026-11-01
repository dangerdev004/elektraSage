// The circuit editor: model (elements), view (pan/zoom), mouse/keyboard behaviour and drawing.
// No React in here. React only owns the menus and panels and talks to this class through
// `exec(command)` and the `onChange` callback. There is NO simulation behind this.

import {
  GRID, snap, segDist, elLength, toLocal, fromLocal, axisEnd, rectsIntersect, normRect,
} from './geometry.js';
import { getDef, halfHOf } from './parts.js';
import { drawElement, drawLabel, drawPinLabels } from './symbols.js';
import { directiveBox } from './directive.js';
import { KEY_TO_PART } from '../data/shortcuts.js';
import { PART_PARAMS, stepText, withUnit } from '../sim/params.js';

const COLORS = {
  dark: { bg: '#000', dots: '#4a4a4a', base: '#a0a0a0', text: '#d8d8d8' },
  white: { bg: '#fff', dots: '#c4c4c4', base: '#303030', text: '#000' },
  select: '#00ffff',
};

export const DEFAULT_OPTS = {
  showValues: true,
  showPins: false,
  smallGrid: false,
  euro: false,
  white: false,
  crosshair: false,
  noEdit: false,
};

const clone = (el) => ({ ...el });

export class Editor {
  constructor() {
    this.els = [];
    this.nextId = 1;
    this.sel = new Set();
    this.view = { ox: 40, oy: 20, s: 1 };
    this.mode = 'select'; // 'select' | 'dragAll' | 'add:<classId>' | other Drag* modes
    this.opts = { ...DEFAULT_OPTS };
    this.undoStack = [];
    this.redoStack = [];
    this.clipboard = [];
    this.pasteCount = 0;
    this.drag = null;
    this.placing = null;
    this.hover = null;
    this.mouse = null; // world coords of the pointer
    this.size = { w: 800, h: 600, dpr: 1 };
    this.canvas = null;
    this.onChange = null; // (state) => void
    this.onContextMenu = null; // ({x, y, onElement}) => void
    this.onEdit = null; // (element) => void   (double click)
    this.onToggle = null; // (element) => void  (a switch or logic input was clicked)
    this.meterProvider = null; // (element) => string | null   reading shown beside a meter
    this.lampProvider = null; // (element) => true | false | null   state of a Logic Output's net
    this.onNotice = null; // (text) => void
    this.rev = 0; // bumped on every change to the circuit
    this.nodeLabelProvider = null; // () => [{x, y, text}] supplied by the app (SPICE node names)
    this.hoverEnd = null; // { el, which } while the pointer is over a part's end point
    this.onShortcut = null; // (command) => void   (keys the app handles, e.g. Ctrl+Enter)
    this.describeExtra = null; // (element) => string | ''
    this._lastState = '';
    this._raf = 0;
    this._unbind = [];
  }

  // ---------- state exposed to the UI ----------
  get grid() {
    return this.opts.smallGrid ? GRID / 2 : GRID;
  }

  state() {
    const h = this.hover ? this.describe(this.hover) : '';
    return {
      mode: this.mode,
      canUndo: this.undoStack.length > 0,
      canRedo: this.redoStack.length > 0,
      canPaste: this.clipboard.length > 0,
      selCount: this.sel.size,
      count: this.els.length,
      info: h,
      zoom: Math.round(this.view.s * 100),
      rev: this.rev, // changes whenever the circuit changes, so the app can notice stale results
    };
  }

  emit() {
    const st = this.state();
    const key = JSON.stringify(st);
    if (key === this._lastState) return;
    this._lastState = key;
    this.onChange?.(st);
  }

  describe(el) {
    const def = getDef(el.type);
    const v = el.model ?? el.value ?? def.value;
    const base = v ? `${def.label} (${v})` : def.label;
    const extra = this.describeExtra?.(el); // e.g. the SPICE node name, supplied by the app
    return extra ? `${base} — ${extra}` : base;
  }

  setOptions(o) {
    this.opts = { ...this.opts, ...o };
    this.redraw();
    this.emit();
  }

  // ---------- model ----------
  snapshot() {
    return JSON.stringify(this.els);
  }

  restore(json) {
    this.rev++;
    this.els = JSON.parse(json);
    const ids = new Set(this.els.map((e) => e.id));
    this.sel = new Set([...this.sel].filter((id) => ids.has(id)));
    this.hover = null;
    this.nextId = Math.max(this.nextId, ...this.els.map((e) => e.id + 1), 1);
  }

  pushUndo() {
    this.rev++;
    this.undoStack.push(this.snapshot());
    if (this.undoStack.length > 100) this.undoStack.shift();
    this.redoStack = [];
  }

  newElement(type, x1, y1, x2, y2, value, mirror = false) {
    const el = { id: this.nextId++, type, x1, y1, x2, y2, mirror };
    if (value !== undefined) el.value = value;
    return el;
  }

  addElement(type, x1, y1, x2, y2, value) {
    this.pushUndo();
    const el = this.newElement(type, x1, y1, x2, y2, value);
    this.els.push(el);
    this.redraw();
    this.emit();
    return el;
  }

  loadElements(list) {
    this.rev++;
    this.els = list.map(([type, x1, y1, x2, y2, value, params]) => {
      const el = this.newElement(type, x1, y1, x2, y2, value);
      if (params) el.params = { ...params }; // optional 7th entry, e.g. { open: 'true' } for a switch
      return el;
    });
    this.sel.clear();
    this.undoStack = [];
    this.redoStack = [];
    this.hover = null;
    this.centre();
    this.emit();
  }

  selected() {
    return this.els.filter((e) => this.sel.has(e.id));
  }

  terminals(el) {
    const def = getDef(el.type);
    return def.terminals(elLength(el), el).map((t) => fromLocal(el, t.x, t.y));
  }

  bbox(el) {
    const def = getDef(el.type);
    if (def.kind === 'directive') {
      const b = directiveBox(el);
      return { x0: b.x, y0: b.y, x1: b.x + b.w, y1: b.y + b.h };
    }
    const L = elLength(el);
    const pts = [
      fromLocal(el, -2, -halfHOf(el)), fromLocal(el, L + def.ext, -halfHOf(el)),
      fromLocal(el, -2, halfHOf(el)), fromLocal(el, L + def.ext, halfHOf(el)),
    ];
    return {
      x0: Math.min(...pts.map((p) => p.x)), y0: Math.min(...pts.map((p) => p.y)),
      x1: Math.max(...pts.map((p) => p.x)), y1: Math.max(...pts.map((p) => p.y)),
    };
  }

  /**
   * The end point (1 or 2) of a part under the pointer, if any. Where several ends share a spot
   * (a wire meeting a pin), a selected part wins, then a non-wire part, then the topmost wire.
   */
  hitEnd(wx, wy) {
    const tol = 7 / this.view.s;
    const found = [];
    for (let i = this.els.length - 1; i >= 0; i--) {
      const el = this.els[i];
      if (Math.hypot(wx - el.x1, wy - el.y1) <= tol) found.push({ el, which: 1 });
      else if (Math.hypot(wx - el.x2, wy - el.y2) <= tol) found.push({ el, which: 2 });
    }
    return found.find((f) => this.sel.has(f.el.id)) ?? found.find((f) => f.el.type !== 'WireElm') ?? found[0] ?? null;
  }

  hitTest(wx, wy) {
    const tol = 8 / this.view.s;
    for (let i = this.els.length - 1; i >= 0; i--) {
      const el = this.els[i];
      const def = getDef(el.type);
      if (def.kind === 'wire') {
        if (segDist(wx, wy, el.x1, el.y1, el.x2, el.y2) <= tol) return el;
        continue;
      }
      if (def.kind === 'directive') {
        const b = directiveBox(el);
        if (wx >= b.x - tol && wx <= b.x + b.w + tol && wy >= b.y - tol && wy <= b.y + b.h + tol) return el;
        continue;
      }
      const l = toLocal(el, wx, wy);
      const L = elLength(el);
      if (l.x >= -tol && l.x <= L + def.ext + tol && Math.abs(l.y) <= halfHOf(el) + tol) return el;
    }
    return null;
  }

  // ---------- commands ----------
  // Returns true if the command is implemented here, false if the UI should say "not wired yet".
  exec(cmd) {
    const noEdit = this.opts.noEdit;
    const needsEdit = ['edit.cut', 'edit.paste', 'edit.duplicate', 'edit.delete', 'edit.flipx',
      'edit.flipy', 'edit.flipxy', 'elm.flip', 'edit.undo', 'edit.redo', 'file.newblankcircuit'];
    if (noEdit && needsEdit.includes(cmd)) {
      this.onNotice?.('Editing is disabled (Options > Disable Editing).');
      return true;
    }
    switch (cmd) {
      case 'edit.undo': return this.undo(), true;
      case 'edit.redo': return this.redo(), true;
      case 'edit.cut': return this.copy(), this.deleteSelected(), true;
      case 'edit.copy': return this.copy(), true;
      case 'edit.paste': return this.paste(), true;
      case 'edit.duplicate': return this.copy(), this.paste(), true;
      case 'edit.delete': return this.deleteSelected(), true;
      case 'edit.selectAll':
        this.sel = new Set(this.els.map((e) => e.id));
        this.redraw(); this.emit();
        return true;
      case 'edit.centrecircuit': return this.centre(), true;
      case 'zoom.zoom100': return this.zoomTo(1), true;
      case 'zoom.zoomin': return this.zoomTo(this.view.s * 1.25), true;
      case 'zoom.zoomout': return this.zoomTo(this.view.s / 1.25), true;
      case 'edit.flipx': return this.flip(true, false), true;
      case 'edit.flipy': return this.flip(false, true), true;
      case 'edit.flipxy': return this.flip(true, true), true;
      case 'elm.flip': return this.swapTerminals(), true;
      case 'file.newblankcircuit':
        this.pushUndo();
        this.els = [];
        this.sel.clear();
        this.redraw(); this.emit();
        return true;
      default:
        if (cmd.startsWith('mode:')) {
          const m = cmd.slice(5);
          if (['select', 'dragAll'].includes(m) || m.startsWith('add:')) {
            this.setMode(m);
            return true;
          }
          this.setMode('select');
          this.onNotice?.('That mouse mode is not implemented yet; staying in Select.');
          return true;
        }
        return false;
    }
  }

  setMode(m) {
    if (this.opts.noEdit && m.startsWith('add:')) {
      this.onNotice?.('Editing is disabled (Options > Disable Editing).');
      return;
    }
    this.mode = m;
    this.placing = null;
    this.redraw();
    this.emit();
    if (this.canvas) this.canvas.style.cursor = m === 'dragAll' ? 'grab' : m === 'select' ? 'default' : 'crosshair';
  }

  undo() {
    if (!this.undoStack.length) return;
    this.redoStack.push(this.snapshot());
    this.restore(this.undoStack.pop());
    this.redraw(); this.emit();
  }

  redo() {
    if (!this.redoStack.length) return;
    this.undoStack.push(this.snapshot());
    this.restore(this.redoStack.pop());
    this.redraw(); this.emit();
  }

  deleteSelected() {
    if (!this.sel.size) return;
    this.pushUndo();
    this.els = this.els.filter((e) => !this.sel.has(e.id));
    this.sel.clear();
    this.hover = null;
    this.redraw(); this.emit();
  }

  copy() {
    this.clipboard = this.selected().map(clone);
    this.pasteCount = 0;
    this.emit();
  }

  paste() {
    if (!this.clipboard.length) return;
    this.pushUndo();
    this.pasteCount++;
    const d = this.grid * 2 * this.pasteCount;
    const added = this.clipboard.map((e) => ({
      ...clone(e), id: this.nextId++, x1: e.x1 + d, y1: e.y1 + d, x2: e.x2 + d, y2: e.y2 + d,
    }));
    this.els.push(...added);
    this.sel = new Set(added.map((e) => e.id));
    this.redraw(); this.emit();
  }

  // Mirror the selection about its own centre. One mirror flips handedness; both (a 180 degree
  // turn) does not.
  flip(x, y) {
    const sel = this.selected();
    if (!sel.length) return;
    this.pushUndo();
    const b = sel.map((e) => this.bbox(e));
    const cx = (Math.min(...b.map((r) => r.x0)) + Math.max(...b.map((r) => r.x1))) / 2;
    const cy = (Math.min(...b.map((r) => r.y0)) + Math.max(...b.map((r) => r.y1))) / 2;
    const g = this.grid;
    for (const e of sel) {
      if (x) { e.x1 = snap(2 * cx - e.x1, g); e.x2 = snap(2 * cx - e.x2, g); }
      if (y) { e.y1 = snap(2 * cy - e.y1, g); e.y2 = snap(2 * cy - e.y2, g); }
      if (x !== y) e.mirror = !e.mirror;
    }
    this.redraw(); this.emit();
  }

  swapTerminals() {
    const sel = this.selected();
    if (!sel.length) return;
    this.pushUndo();
    for (const e of sel) {
      [e.x1, e.x2] = [e.x2, e.x1];
      [e.y1, e.y2] = [e.y2, e.y1];
    }
    this.redraw(); this.emit();
  }

  /** Set a part's value text and (optionally) its library model. model === '' clears it. */
  setValue(id, value, model) {
    const el = this.els.find((e) => e.id === id);
    if (!el) return;
    this.pushUndo();
    el.value = value;
    if (model !== undefined) { if (model) el.model = model; else delete el.model; }
    this.redraw(); this.emit();
  }

  /** Set several properties of one part in a single undo step. patch: { value?, model?, params? }. */
  setProps(id, patch) {
    const el = this.els.find((e) => e.id === id);
    if (!el) return;
    this.pushUndo();
    if (patch.value !== undefined) el.value = patch.value;
    if (patch.labels !== undefined) { if (patch.labels?.some((l) => l)) el.labels = [...patch.labels]; else delete el.labels; }
    if (patch.pins !== undefined) { if (patch.pins?.length) el.pins = [...patch.pins]; else delete el.pins; }
    if (patch.model !== undefined) { if (patch.model) el.model = patch.model; else delete el.model; }
    if (patch.params !== undefined) { if (Object.keys(patch.params).length) el.params = { ...patch.params }; else delete el.params; }
    this.redraw(); this.emit();
  }

  // ---------- save / open ----------
  /** The circuit as a plain object, for saving to a file. */
  toDocument(title = '') {
    return {
      format: 'circuit-ui', version: 1, title,
      elements: this.els.map(({ type, x1, y1, x2, y2, mirror, value, model, params, pins, labels }) => {
        const o = { type, x1, y1, x2, y2, mirror: !!mirror };
        if (value !== undefined) o.value = value;
        if (model) o.model = model;
        if (pins && pins.length) o.pins = [...pins];
        if (labels && labels.some((l) => l)) o.labels = [...labels];
        if (params && Object.keys(params).length) o.params = { ...params };
        return o;
      }),
    };
  }

  /** Replace the circuit with a saved document. Throws Error with a readable message if it is not one. */
  loadDocument(doc) {
    if (!doc || typeof doc !== 'object' || doc.format !== 'circuit-ui') throw new Error('This is not a circuit-ui file (missing "format": "circuit-ui").');
    if (doc.version !== 1) throw new Error(`Unsupported file version ${doc.version}; this app reads version 1.`);
    if (!Array.isArray(doc.elements)) throw new Error('The file has no "elements" list.');
    if (doc.elements.length > 5000) throw new Error('The file has more than 5000 parts; refusing to load it.');
    const els = doc.elements.map((o, i) => {
      const ok = o && typeof o.type === 'string' && ['x1', 'y1', 'x2', 'y2'].every((k) => Number.isFinite(o[k]));
      if (!ok) throw new Error(`Element ${i + 1} is malformed (needs type, x1, y1, x2, y2 as numbers).`);
      const el = this.newElement(o.type, o.x1, o.y1, o.x2, o.y2, typeof o.value === 'string' ? o.value : undefined, !!o.mirror);
      if (typeof o.model === 'string' && o.model) el.model = o.model;
      if (o.type === 'SubcktElm' && Array.isArray(o.labels) && o.labels.length <= 64 && o.labels.every((l) => typeof l === 'string' && l.length <= 24 && !/[\u0000-\u001f]/.test(l))) el.labels = [...o.labels];
      if (o.type === 'SubcktElm' && Array.isArray(o.pins) && o.pins.length <= 64 && o.pins.every((p) => typeof p === 'string' && /^[\w.+\-#$%@!]{1,40}$/.test(p))) el.pins = [...o.pins];
      if (o.params && typeof o.params === 'object' && !Array.isArray(o.params)) {
        const params = {};
        for (const [k, v] of Object.entries(o.params)) if (typeof v === 'string' || typeof v === 'boolean') params[k] = String(v);
        if (Object.keys(params).length) el.params = params;
      }
      return el;
    });
    this.pushUndo();
    this.els = els;
    this.sel.clear();
    this.hover = null;
    this.centre();
    this.redraw(); this.emit();
    return typeof doc.title === 'string' ? doc.title : '';
  }

  // ---------- view ----------
  toWorld(sx, sy) {
    return { x: (sx - this.view.ox) / this.view.s, y: (sy - this.view.oy) / this.view.s };
  }

  zoomAt(sx, sy, factor) {
    const w = this.toWorld(sx, sy);
    const s = Math.max(0.25, Math.min(4, this.view.s * factor));
    this.view = { s, ox: sx - w.x * s, oy: sy - w.y * s };
    this.redraw(); this.emit();
  }

  zoomTo(s) {
    this.zoomAt(this.size.w / 2, this.size.h / 2, s / this.view.s);
  }

  centre() {
    if (!this.els.length) {
      this.view = { ox: 40, oy: 20, s: 1 };
    } else {
      const b = this.els.map((e) => this.bbox(e));
      const cx = (Math.min(...b.map((r) => r.x0)) + Math.max(...b.map((r) => r.x1))) / 2;
      const cy = (Math.min(...b.map((r) => r.y0)) + Math.max(...b.map((r) => r.y1))) / 2;
      const s = this.view.s;
      this.view = { s, ox: this.size.w / 2 - cx * s, oy: this.size.h / 2 - cy * s };
    }
    this.redraw();
    this.emit();
  }

  // ---------- pointer / keyboard ----------
  attach(canvas, wrap) {
    this.canvas = canvas;
    this.wrap = wrap;
    const on = (target, type, fn, opt) => {
      target.addEventListener(type, fn, opt);
      this._unbind.push(() => target.removeEventListener(type, fn, opt));
    };
    on(canvas, 'pointerdown', (e) => this.pointerDown(e));
    on(canvas, 'pointermove', (e) => this.pointerMove(e));
    on(canvas, 'pointerup', (e) => this.pointerUp(e));
    on(canvas, 'pointerleave', () => { this.mouse = null; this.hover = null; this.redraw(); this.emit(); });
    on(canvas, 'wheel', (e) => this.wheel(e), { passive: false });
    on(canvas, 'dblclick', (e) => this.dblClick(e));
    on(canvas, 'contextmenu', (e) => this.contextMenu(e));
    on(canvas, 'keydown', (e) => this.key(e));
    if (typeof ResizeObserver !== 'undefined') {
      const ro = new ResizeObserver(() => this.resize());
      ro.observe(wrap);
      this._unbind.push(() => ro.disconnect());
    }
    this.resize();
  }

  detach() {
    this._unbind.forEach((f) => f());
    this._unbind = [];
    if (this._raf) cancelAnimationFrame(this._raf);
    this._raf = 0;
    this.canvas = null;
  }

  resize() {
    if (!this.canvas || !this.wrap) return;
    const r = this.wrap.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.size = { w: r.width, h: r.height, dpr };
    this.canvas.width = Math.max(1, Math.round(r.width * dpr));
    this.canvas.height = Math.max(1, Math.round(r.height * dpr));
    this.canvas.style.width = `${r.width}px`;
    this.canvas.style.height = `${r.height}px`;
    if (!this._laidOut && r.width > 0 && r.height > 0) {
      this._laidOut = true; // first real size: centre whatever circuit was loaded before layout
      this.centre();
    }
    this.redraw();
  }

  pos(e) {
    const r = this.canvas.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  pointerDown(e) {
    this.canvas.focus();
    const p = this.pos(e);
    const w = this.toWorld(p.x, p.y);
    if (e.button === 1 || (e.button === 0 && (e.altKey || this.mode === 'dragAll'))) {
      this.drag = { type: 'pan', sx: p.x, sy: p.y, ox: this.view.ox, oy: this.view.oy };
      this.canvas.setPointerCapture?.(e.pointerId);
      this.canvas.style.cursor = 'grabbing';
      e.preventDefault();
      return;
    }
    if (e.button !== 0) return;
    this.canvas.setPointerCapture?.(e.pointerId);

    if (this.mode.startsWith('add:')) {
      const type = this.mode.slice(4);
      const def = getDef(type);
      const g = this.grid;
      const x1 = snap(w.x, g);
      const y1 = snap(w.y, g);
      const el = this.newElement(type, x1, y1, x1 + (def.minLen || 0), y1);
      this.placing = el;
      this.drag = { type: 'place', el };
      this.redraw();
      return;
    }

    const end = !this.opts.noEdit && !e.shiftKey ? this.hitEnd(w.x, w.y) : null;
    if (end) {
      this.sel = new Set([end.el.id]);
      // wires attached to a pin of this part follow that pin
      const oldTerms = this.terminals(end.el);
      const key = (p) => `${Math.round(p.x)},${Math.round(p.y)}`;
      const follow = [];
      for (const wire of this.els) {
        if (wire === end.el || wire.type !== 'WireElm') continue;
        for (const [which, px, py] of [[1, wire.x1, wire.y1], [2, wire.x2, wire.y2]]) {
          const i = oldTerms.findIndex((t) => key(t) === key({ x: px, y: py }));
          if (i >= 0) follow.push({ id: wire.id, which, term: i });
        }
      }
      this.drag = { type: 'end', el: end.el, which: end.which, follow, moved: false };
      this.redraw(); this.emit();
      return;
    }

    const hit = this.hitTest(w.x, w.y);
    if (hit) {
      if (e.shiftKey) {
        if (this.sel.has(hit.id)) this.sel.delete(hit.id); else this.sel.add(hit.id);
      } else if (!this.sel.has(hit.id)) {
        this.sel = new Set([hit.id]);
      }
      if (this.sel.has(hit.id) && !this.opts.noEdit) {
        const picked = this.selected();
        // Wires that are NOT selected but end on a selected part's pin follow that pin (rubber-banding).
        const pinKeys = new Set(picked.flatMap((el) => this.terminals(el).map((t) => `${Math.round(t.x)},${Math.round(t.y)}`)));
        const follow = [];
        for (const wire of this.els) {
          if (wire.type !== 'WireElm' || this.sel.has(wire.id)) continue;
          const f1 = pinKeys.has(`${Math.round(wire.x1)},${Math.round(wire.y1)}`);
          const f2 = pinKeys.has(`${Math.round(wire.x2)},${Math.round(wire.y2)}`);
          if (f1 || f2) follow.push({ id: wire.id, f1, f2, x1: wire.x1, y1: wire.y1, x2: wire.x2, y2: wire.y2 });
        }
        this.drag = {
          type: 'move', start: w, moved: false, follow, hitId: hit.id,
          orig: picked.map((el) => ({ id: el.id, x1: el.x1, y1: el.y1, x2: el.x2, y2: el.y2 })),
        };
      }
    } else {
      if (!e.shiftKey) this.sel.clear();
      this.drag = { type: 'marquee', x0: w.x, y0: w.y, x1: w.x, y1: w.y, add: e.shiftKey, base: new Set(this.sel) };
    }
    this.redraw(); this.emit();
  }

  pointerMove(e) {
    const p = this.pos(e);
    const w = this.toWorld(p.x, p.y);
    this.mouse = w;
    const d = this.drag;
    if (!d) {
      const he = this.mode === 'select' && !this.opts.noEdit ? this.hitEnd(w.x, w.y) : null;
      this.hoverEnd = he;
      if (this.canvas && this.mode === 'select') this.canvas.style.cursor = he ? 'move' : 'default';
      const h = this.hitTest(w.x, w.y);
      if (h !== this.hover) this.hover = h;
      this.redraw(); this.emit();
      return;
    }
    if (d.type === 'pan') {
      this.view.ox = d.ox + (p.x - d.sx);
      this.view.oy = d.oy + (p.y - d.sy);
    } else if (d.type === 'place') {
      const def = getDef(d.el.type);
      const g = this.grid;
      if (def.free) {
        d.el.x2 = snap(w.x, g);
        d.el.y2 = snap(w.y, g);
      } else {
        const end = axisEnd(d.el.x1, d.el.y1, w.x, w.y, def.minLen, g);
        d.el.x2 = end.x2;
        d.el.y2 = end.y2;
      }
    } else if (d.type === 'move') {
      const g = this.grid;
      const dx = snap(w.x - d.start.x, g);
      const dy = snap(w.y - d.start.y, g);
      if (!d.moved && (dx || dy)) {
        d.moved = true;
        // snapshot the pre-move state for undo (elements have not been changed yet)
        this.pushUndo();
      }
      if (d.moved) {
        this.rev++;
        for (const o of d.orig) {
          const el = this.els.find((x) => x.id === o.id);
          if (!el) continue;
          el.x1 = o.x1 + dx; el.y1 = o.y1 + dy; el.x2 = o.x2 + dx; el.y2 = o.y2 + dy;
        }
        for (const f of d.follow ?? []) {
          const wire = this.els.find((x) => x.id === f.id);
          if (!wire) continue;
          wire.x1 = f.f1 ? f.x1 + dx : f.x1; wire.y1 = f.f1 ? f.y1 + dy : f.y1;
          wire.x2 = f.f2 ? f.x2 + dx : f.x2; wire.y2 = f.f2 ? f.y2 + dy : f.y2;
        }
      }
    } else if (d.type === 'end') {
      const el = d.el;
      const def = getDef(el.type);
      const g = this.grid;
      const fixed = d.which === 1 ? { x: el.x2, y: el.y2 } : { x: el.x1, y: el.y1 };
      let nx;
      let ny;
      if (def.free) { nx = snap(w.x, g); ny = snap(w.y, g); } else {
        const a = axisEnd(fixed.x, fixed.y, w.x, w.y, def.minLen, g);
        nx = a.x2; ny = a.y2;
      }
      const cur = d.which === 1 ? { x: el.x1, y: el.y1 } : { x: el.x2, y: el.y2 };
      if (nx !== cur.x || ny !== cur.y) {
        if (!d.moved) { d.moved = true; this.pushUndo(); }
        this.rev++;
        if (d.which === 1) { el.x1 = nx; el.y1 = ny; } else { el.x2 = nx; el.y2 = ny; }
        const terms = this.terminals(el);
        for (const f of d.follow) {
          const wire = this.els.find((x) => x.id === f.id);
          if (!wire) continue;
          if (f.which === 1) { wire.x1 = terms[f.term].x; wire.y1 = terms[f.term].y; } else { wire.x2 = terms[f.term].x; wire.y2 = terms[f.term].y; }
        }
      }
    } else if (d.type === 'marquee') {
      d.x1 = w.x; d.y1 = w.y;
      const r = normRect(d.x0, d.y0, d.x1, d.y1);
      const hit = this.els.filter((el) => rectsIntersect(this.bbox(el), r)).map((el) => el.id);
      this.sel = new Set([...(d.add ? d.base : []), ...hit]);
    }
    this.redraw(); this.emit();
  }

  pointerUp(e) {
    const d = this.drag;
    this.drag = null;
    this.canvas?.releasePointerCapture?.(e.pointerId);
    if (!d) return;
    if (d.type === 'pan') {
      this.canvas.style.cursor = this.mode === 'dragAll' ? 'grab' : this.mode === 'select' ? 'default' : 'crosshair';
    }
    if (d.type === 'end' && d.moved && d.el.type === 'WireElm' && elLength(d.el) === 0) {
      // a wire shrunk to nothing is removed (undo brings it back)
      this.els = this.els.filter((x) => x !== d.el);
      this.sel.delete(d.el.id);
    }
    if (d.type === 'move' && !d.moved && !e.shiftKey && !this.opts.noEdit) {
      const el = this.els.find((x) => x.id === d.hitId);
      if (el && (el.type === 'SwitchElm' || el.type === 'PushSwitchElm')) {
        this.pushUndo();
        el.params = { ...el.params, open: String(el.params?.open) === 'true' ? 'false' : 'true' };
        this.onToggle?.(el);
      } else if (el && el.type === 'LogicInputElm') {
        this.pushUndo();
        el.params = { ...el.params, high: String(el.params?.high) === 'true' ? 'false' : 'true' };
        this.onToggle?.(el);
      }
    }
    if (d.type === 'place') {
      this.placing = null;
      const el = d.el;
      const def = getDef(el.type);
      if (!(def.free && elLength(el) === 0)) {
        this.pushUndo();
        this.els.push(el);
      }
    }
    this.redraw(); this.emit();
  }

  wheel(e) {
    e.preventDefault();
    const p = this.pos(e);
    if (this.opts.wheelEdit && !this.opts.noEdit && this.wheelEditValue(e, p)) return;
    this.zoomAt(p.x, p.y, Math.exp(-e.deltaY * 0.0015));
  }

  /**
   * "Edit Values With Mouse Wheel": with the option on, scrolling over a part steps its main value
   * (resistance, capacitance, voltage, ...) up or down in 1-2-5 steps instead of zooming.
   * Returns true when it handled the wheel event.
   */
  wheelEditValue(e, p) {
    const w = this.toWorld(p.x, p.y);
    const el = this.hitTest(w.x, w.y);
    const spec = el && PART_PARAMS[el.type];
    if (!spec?.valueLabel) return false; // not over a part with a single main value: zoom as usual
    const unit = spec.valueUnit === 'Ω' ? '' : spec.valueUnit ?? '';
    const next = withUnit(stepText(el.value ?? getDef(el.type).value, e.deltaY < 0 ? 1 : -1, spec.valueDef ?? '1', unit), spec.valueUnit);
    if (next === el.value) return true;
    // one undo step per burst of scrolling on the same part
    const now = Date.now();
    if (this._wheelId !== el.id || now - (this._wheelAt ?? 0) > 700) this.pushUndo();
    this._wheelId = el.id;
    this._wheelAt = now;
    el.value = next;
    this.redraw(); this.emit();
    this.onValueChange?.(el);
    return true;
  }

  dblClick(e) {
    if (this.mode !== 'select') return;
    const p = this.pos(e);
    const w = this.toWorld(p.x, p.y);
    const hit = this.hitTest(w.x, w.y);
    if (hit && getDef(hit.type).kind !== 'wire') this.onEdit?.(hit);
  }

  contextMenu(e) {
    e.preventDefault();
    const p = this.pos(e);
    const w = this.toWorld(p.x, p.y);
    const hit = this.hitTest(w.x, w.y);
    if (hit && !this.sel.has(hit.id)) this.sel = new Set([hit.id]);
    this.redraw(); this.emit();
    this.onContextMenu?.({ x: e.clientX, y: e.clientY, onElement: !!hit });
  }

  key(e) {
    const ctrl = e.ctrlKey || e.metaKey;
    const k = e.key;
    let handled = true;
    if (ctrl && k === 'Enter') this.onShortcut?.('sim.run');
    else if (ctrl && k.toLowerCase() === 's') this.onShortcut?.('file.exportaslocalfile');
    else if (ctrl && k.toLowerCase() === 'o') this.onShortcut?.('file.importfromlocalfile');
    else if (ctrl && k.toLowerCase() === 'p') this.onShortcut?.('file.print');
    else if (ctrl && k.toLowerCase() === 'z') this.exec(e.shiftKey ? 'edit.redo' : 'edit.undo');
    else if (ctrl && k.toLowerCase() === 'y') this.exec('edit.redo');
    else if (ctrl && k.toLowerCase() === 'x') this.exec('edit.cut');
    else if (ctrl && k.toLowerCase() === 'c') this.exec('edit.copy');
    else if (ctrl && k.toLowerCase() === 'v') this.exec('edit.paste');
    else if (ctrl && k.toLowerCase() === 'd') this.exec('edit.duplicate');
    else if (ctrl && k.toLowerCase() === 'a') this.exec('edit.selectAll');
    else if (k === 'Delete' || k === 'Backspace') this.exec('edit.delete');
    else if (k === 'Escape') { this.sel.clear(); this.setMode('select'); }
    else if (k === '+' || k === '=') this.exec('zoom.zoomin');
    else if (k === '-') this.exec('zoom.zoomout');
    else if (k === '0') this.exec('zoom.zoom100');
    else if (k === '/') this.onNotice?.('Find Component is not wired yet.');
    else if (k === ' ') this.setMode('select');
    else if (!ctrl && !e.altKey && KEY_TO_PART[k]) this.setMode(`add:${KEY_TO_PART[k]}`);
    else handled = false;
    if (handled) e.preventDefault();
    return handled;
  }

  // ---------- drawing ----------
  redraw() {
    if (!this.canvas || this._raf) return;
    this._raf = requestAnimationFrame(() => {
      this._raf = 0;
      this.draw();
    });
  }

  draw() {
    const c = this.canvas;
    if (!c) return;
    const ctx = c.getContext('2d');
    const { w, h, dpr } = this.size;
    const { s, ox, oy } = this.view;
    const pal = this.opts.white ? COLORS.white : COLORS.dark;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = pal.bg;
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.setTransform(dpr * s, 0, 0, dpr * s, dpr * ox, dpr * oy);

    // grid dots
    const g = this.grid;
    if (g * s >= 5) {
      const gx0 = Math.floor(-ox / s / g) * g;
      const gy0 = Math.floor(-oy / s / g) * g;
      const gx1 = (w - ox) / s;
      const gy1 = (h - oy) / s;
      ctx.fillStyle = pal.dots;
      const r = 0.8 / Math.max(s, 0.6);
      for (let x = gx0; x <= gx1; x += g) {
        for (let y = gy0; y <= gy1; y += g) ctx.fillRect(x - r, y - r, r * 2, r * 2);
      }
    }

    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    const o = { euro: this.opts.euro };

    const paint = (el, color) => {
      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      drawElement(ctx, el, el.type === 'LogicOutputElm' ? { ...o, lamp: this.lampProvider?.(el) ?? null } : o);
      if (getDef(el.type).kind === 'meter') {
        drawLabel(ctx, el, this.meterProvider?.(el) ?? '');
      } else if (this.opts.showValues && getDef(el.type).kind !== 'directive' && getDef(el.type).kind !== 'label') {
        const def = getDef(el.type);
        drawLabel(ctx, el, el.model ?? el.value ?? def.value);
      }
      if (this.opts.showPins) drawPinLabels(ctx, el, this.terminals(el));
    };

    const counts = new Map();
    for (const el of this.els) {
      paint(el, this.sel.has(el.id) ? COLORS.select : pal.base);
      for (const t of this.terminals(el)) {
        const k = `${Math.round(t.x)},${Math.round(t.y)}`;
        counts.set(k, (counts.get(k) ?? 0) + 1);
      }
    }
    // junction dots where three or more terminals meet
    ctx.fillStyle = pal.base;
    for (const [k, n] of counts) {
      if (n < 3) continue;
      const [x, y] = k.split(',').map(Number);
      ctx.beginPath();
      ctx.arc(x, y, 3.5, 0, Math.PI * 2);
      ctx.fill();
    }

    if (this.placing) paint(this.placing, COLORS.select);

    // end-point handles on selected parts (drag one to stretch or move that end), bigger when hovered
    if (this.mode === 'select' && !this.opts.noEdit) {
      ctx.fillStyle = COLORS.select;
      const r = 4 / Math.max(s, 0.5);
      for (const el of this.els) {
        const hot = this.hoverEnd && this.hoverEnd.el === el;
        if (!this.sel.has(el.id) && !hot) continue;
        for (const [which, x, y] of [[1, el.x1, el.y1], [2, el.x2, el.y2]]) {
          const big = hot && this.hoverEnd.which === which;
          ctx.fillRect(x - (big ? r * 1.5 : r), y - (big ? r * 1.5 : r), (big ? r * 3 : r * 2), (big ? r * 3 : r * 2));
        }
      }
    }

    // SPICE node names (the same names the results list uses)
    if (this.opts.nodeLabels && this.nodeLabelProvider) {
      ctx.font = 'bold 11px ui-monospace, Menlo, Consolas, monospace';
      ctx.textBaseline = 'bottom';
      ctx.textAlign = 'left';
      ctx.lineWidth = 3;
      for (const lb of this.nodeLabelProvider()) {
        ctx.strokeStyle = pal.bg;
        ctx.strokeText(lb.text, lb.x + 5, lb.y - 4);
        ctx.fillStyle = '#ffd54f';
        ctx.fillText(lb.text, lb.x + 5, lb.y - 4);
      }
      ctx.lineWidth = 2;
    }

    const d = this.drag;
    if (d && d.type === 'marquee') {
      const r = normRect(d.x0, d.y0, d.x1, d.y1);
      ctx.strokeStyle = COLORS.select;
      ctx.lineWidth = 1 / s;
      ctx.strokeRect(r.x0, r.y0, r.x1 - r.x0, r.y1 - r.y0);
    }

    if (this.opts.crosshair && this.mouse) {
      ctx.strokeStyle = pal.dots;
      ctx.lineWidth = 1 / s;
      ctx.beginPath();
      ctx.moveTo(this.mouse.x, -1e5); ctx.lineTo(this.mouse.x, 1e5);
      ctx.moveTo(-1e5, this.mouse.y); ctx.lineTo(1e5, this.mouse.y);
      ctx.stroke();
    }
  }
}
