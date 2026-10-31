// Canvas plotter: multiple traces, two y-axes (left/right), linear or log x axis,
// wheel zoom, drag pan, double-click fit, click = cursor 1, shift-click = cursor 2, right-click = clear.
// No dependencies. The class touches the DOM only in its constructor, so si()/interp() are testable in Node.

export const COLORS = ['#4fc3f7', '#ff8a65', '#aed581', '#ba68c8', '#ffd54f', '#4db6ac', '#f06292', '#90a4ae'];

const UNITS = ['f', 'p', 'n', 'µ', 'm', '', 'k', 'M', 'G', 'T'];
const BG = '#14181c', GRID = '#2a3138', GRID_MINOR = '#20262b', AXIS = '#8b98a5', TEXT = '#c5ced6';

/** 0.0015 -> "1.5m", 159155 -> "159k" */
export function si(v, digits = 3) {
  if (!Number.isFinite(v)) return String(v);
  if (v === 0) return '0';
  let e = Math.floor(Math.log10(Math.abs(v)) / 3);
  e = Math.max(-5, Math.min(4, e));
  return String(+(v / Math.pow(10, 3 * e)).toPrecision(digits)) + UNITS[e + 5];
}

/** Linear interpolation of y(x) at xv; x must be ascending. NaN outside the data range. */
export function interp(x, y, xv) {
  const n = x.length;
  if (!n || xv < x[0] || xv > x[n - 1]) return NaN;
  let lo = 0, hi = n - 1;
  while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (x[mid] <= xv) lo = mid; else hi = mid; }
  const dx = x[hi] - x[lo];
  return dx === 0 ? y[lo] : y[lo] + (y[hi] - y[lo]) * (xv - x[lo]) / dx;
}

function niceTicks(lo, hi, target = 8) {
  const span = hi - lo;
  if (!(span > 0)) return [lo];
  const raw = span / target, mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw);
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(+v.toPrecision(12));
  return out;
}

export class Plotter {
  /** traces: [{ name, color, x:Float64Array, y:Float64Array, axis:'left'|'right', unit, visible, dash? }] */
  constructor(canvas, { onCursor } = {}) {
    this.cv = canvas;
    this.ctx = canvas.getContext('2d');
    this.traces = [];
    this.xlog = false;
    this.xLabel = '';
    this.xUnit = '';
    this.view = null;
    this.full = null;
    this.cursors = [null, null];
    this.onCursor = onCursor || (() => {});
    this.m = { l: 70, r: 16, t: 12, b: 36 };
    this._off = [];
    this._bind();
    this._ro = new ResizeObserver(() => this.draw());
    this._ro.observe(canvas);
  }

  /** Remove every listener this plotter added (needed when React unmounts the canvas). */
  destroy() {
    this._off.forEach((f) => f());
    this._off = [];
    this._ro?.disconnect();
  }

  setData({ traces = [], xlog = false, xLabel = '', xUnit = '' }, cursors = [null, null]) {
    this.traces = traces;
    this.xlog = xlog;
    this.xLabel = xLabel;
    this.xUnit = xUnit;
    this.cursors = cursors;
    let lo = Infinity, hi = -Infinity;
    for (const t of traces) {
      if (!t.x || !t.x.length) continue;
      const first = xlog ? (t.x.find((v) => v > 0) ?? Infinity) : t.x[0];
      lo = Math.min(lo, first);
      hi = Math.max(hi, t.x[t.x.length - 1]);
    }
    this.full = lo < hi ? { x0: lo, x1: hi } : null;
    this.view = this.full ? { ...this.full } : null;
    this.draw();
  }

  fit() { this.view = this.full ? { ...this.full } : null; this.draw(); }

  /** f < 1 zooms in, f > 1 zooms out, around the centre of the current view. */
  zoom(f) {
    if (!this.view) return;
    const u0 = this._u(this.view.x0), u1 = this._u(this.view.x1), uc = (u0 + u1) / 2;
    this.view = { x0: this._x(uc + (u0 - uc) * f), x1: this._x(uc + (u1 - uc) * f) };
    this.draw();
  }

  // ---- coordinate helpers
  _u(x) { return this.xlog ? Math.log10(x) : x; }
  _x(u) { return this.xlog ? Math.pow(10, u) : u; }
  _rect() {
    const W = this.cv.clientWidth, H = this.cv.clientHeight, m = this.m;
    return { l: m.l, t: m.t, w: Math.max(W - m.l - m.r, 10), h: Math.max(H - m.t - m.b, 10) };
  }
  _xToPx(x, R) {
    const u0 = this._u(this.view.x0), u1 = this._u(this.view.x1);
    return R.l + (this._u(x) - u0) / (u1 - u0) * R.w;
  }
  _pxToX(px, R) {
    const u0 = this._u(this.view.x0), u1 = this._u(this.view.x1);
    return this._x(u0 + (px - R.l) / R.w * (u1 - u0));
  }
  _yRange(vis, axis) {
    let lo = Infinity, hi = -Infinity;
    for (const t of vis) {
      if ((t.axis || 'left') !== axis) continue;
      for (let i = 0; i < t.x.length; i++) {
        const x = t.x[i];
        if (x < this.view.x0 || x > this.view.x1) continue;
        const y = t.y[i];
        if (!Number.isFinite(y)) continue;
        if (y < lo) lo = y;
        if (y > hi) hi = y;
      }
    }
    if (lo === Infinity) return null;
    if (lo === hi) { const d = Math.abs(lo) * 0.1 || 1; lo -= d; hi += d; }
    const pad = (hi - lo) * 0.06;
    return [lo - pad, hi + pad];
  }

  // ---- interaction
  _bind() {
    const cv = this.cv;
    let drag = null;
    const on = (t, type, fn, o) => { t.addEventListener(type, fn, o); this._off.push(() => t.removeEventListener(type, fn, o)); };
    on(cv, 'wheel', (e) => {
      e.preventDefault();
      if (!this.view) return;
      const R = this._rect(), px = e.clientX - cv.getBoundingClientRect().left;
      const f = e.deltaY > 0 ? 1.25 : 0.8;
      const uc = this._u(Math.min(Math.max(this._pxToX(px, R), this.view.x0), this.view.x1));
      const u0 = this._u(this.view.x0), u1 = this._u(this.view.x1);
      this.view = { x0: this._x(uc + (u0 - uc) * f), x1: this._x(uc + (u1 - uc) * f) };
      this.draw();
    }, { passive: false });
    on(cv, 'mousedown', (e) => {
      if (e.button !== 0 || !this.view) return;
      drag = { x: e.clientX, view: { ...this.view }, moved: false };
    });
    on(window, 'mousemove', (e) => {
      if (!drag) return;
      const dx = e.clientX - drag.x;
      if (Math.abs(dx) > 3) drag.moved = true;
      if (!drag.moved) return;
      const R = this._rect();
      const u0 = this._u(drag.view.x0), u1 = this._u(drag.view.x1), shift = -dx / R.w * (u1 - u0);
      this.view = { x0: this._x(u0 + shift), x1: this._x(u1 + shift) };
      this.draw();
    });
    on(window, 'mouseup', (e) => {
      if (!drag) return;
      const d = drag; drag = null;
      if (d.moved || !this.view) return;
      const R = this._rect(), rect = cv.getBoundingClientRect();
      const px = e.clientX - rect.left, py = e.clientY - rect.top;
      if (px < R.l || px > R.l + R.w || py < R.t || py > R.t + R.h) return;
      this.cursors[e.shiftKey ? 1 : 0] = this._pxToX(px, R);
      this.onCursor(this.cursors);
      this.draw();
    });
    on(cv, 'dblclick', () => this.fit());
    on(cv, 'contextmenu', (e) => {
      e.preventDefault();
      this.cursors = [null, null];
      this.onCursor(this.cursors);
      this.draw();
    });
  }

  // ---- drawing
  draw() {
    const cv = this.cv, ctx = this.ctx, dpr = window.devicePixelRatio || 1;
    const W = cv.clientWidth, H = cv.clientHeight;
    if (!W || !H) return;
    if (cv.width !== Math.round(W * dpr) || cv.height !== Math.round(H * dpr)) {
      cv.width = Math.round(W * dpr);
      cv.height = Math.round(H * dpr);
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = BG;
    ctx.fillRect(0, 0, W, H);
    const vis = this.traces.filter((t) => t.visible && t.x && t.x.length);
    if (!this.view || !vis.length) return;

    this.m.r = vis.some((t) => t.axis === 'right') ? 70 : 16;
    const R = this._rect();
    const yl = this._yRange(vis, 'left'), yr = this._yRange(vis, 'right');
    const ymap = (r, v) => R.t + R.h - (v - r[0]) / (r[1] - r[0]) * R.h;
    ctx.font = '11px ui-monospace, Menlo, Consolas, monospace';

    // vertical grid / x ticks
    ctx.textAlign = 'center'; ctx.textBaseline = 'top';
    const xTicks = [];
    if (this.xlog) {
      const d0 = Math.floor(Math.log10(this.view.x0)), d1 = Math.ceil(Math.log10(this.view.x1));
      for (let d = d0; d <= d1; d++) for (let k = 1; k < 10; k++) xTicks.push({ x: k * Math.pow(10, d), major: k === 1 });
    } else {
      for (const v of niceTicks(this.view.x0, this.view.x1, 10)) xTicks.push({ x: v, major: true });
    }
    for (const t of xTicks) {
      if (t.x < this.view.x0 || t.x > this.view.x1) continue;
      const px = this._xToPx(t.x, R);
      ctx.strokeStyle = t.major ? GRID : GRID_MINOR;
      ctx.beginPath(); ctx.moveTo(px, R.t); ctx.lineTo(px, R.t + R.h); ctx.stroke();
      if (t.major) { ctx.fillStyle = TEXT; ctx.fillText(si(t.x, 4), px, R.t + R.h + 5); }
    }

    // horizontal grid + y ticks
    const gridRange = yl || yr;
    ctx.textBaseline = 'middle';
    if (yl) {
      ctx.textAlign = 'right';
      for (const v of niceTicks(yl[0], yl[1], 8)) {
        const py = ymap(yl, v);
        if (gridRange === yl) { ctx.strokeStyle = GRID; ctx.beginPath(); ctx.moveTo(R.l, py); ctx.lineTo(R.l + R.w, py); ctx.stroke(); }
        ctx.fillStyle = TEXT; ctx.fillText(si(v, 4), R.l - 6, py);
      }
    }
    if (yr) {
      ctx.textAlign = 'left';
      for (const v of niceTicks(yr[0], yr[1], 8)) {
        const py = ymap(yr, v);
        if (gridRange === yr) { ctx.strokeStyle = GRID; ctx.beginPath(); ctx.moveTo(R.l, py); ctx.lineTo(R.l + R.w, py); ctx.stroke(); }
        ctx.fillStyle = TEXT; ctx.fillText(si(v, 4), R.l + R.w + 6, py);
      }
    }
    ctx.strokeStyle = AXIS; ctx.strokeRect(R.l + 0.5, R.t + 0.5, R.w, R.h);

    // axis captions
    ctx.fillStyle = AXIS; ctx.textAlign = 'right'; ctx.textBaseline = 'bottom';
    ctx.fillText(`${this.xLabel}${this.xUnit ? ` (${this.xUnit})` : ''}`, R.l + R.w, H - 2);
    const lu = vis.find((t) => (t.axis || 'left') === 'left')?.unit, ru = vis.find((t) => t.axis === 'right')?.unit;
    ctx.textAlign = 'left'; ctx.textBaseline = 'top';
    if (lu) ctx.fillText(lu, 4, 2);
    if (ru) { ctx.textAlign = 'right'; ctx.fillText(ru, W - 4, 2); }

    // traces (clipped to the plot area)
    ctx.save();
    ctx.beginPath(); ctx.rect(R.l, R.t, R.w, R.h); ctx.clip();
    ctx.lineWidth = 1.6; ctx.lineJoin = 'round';
    for (const t of vis) {
      const r = (t.axis === 'right' ? yr : yl);
      if (!r) continue;
      ctx.strokeStyle = t.color;
      ctx.setLineDash(t.dash ? [6, 4] : []);
      ctx.beginPath();
      let pen = false;
      for (let i = 0; i < t.x.length; i++) {
        if (!Number.isFinite(t.y[i]) || (this.xlog && t.x[i] <= 0)) { pen = false; continue; }
        const px = this._xToPx(t.x[i], R), py = ymap(r, t.y[i]);
        if (pen) ctx.lineTo(px, py); else { ctx.moveTo(px, py); pen = true; }
      }
      ctx.stroke();
    }
    ctx.restore();
    ctx.setLineDash([]);

    // cursors
    this.cursors.forEach((cx, k) => {
      if (cx == null || cx < this.view.x0 || cx > this.view.x1) return;
      const px = this._xToPx(cx, R);
      ctx.strokeStyle = k === 0 ? '#ffffff' : '#ffcc66';
      ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(px, R.t); ctx.lineTo(px, R.t + R.h); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = ctx.strokeStyle; ctx.textAlign = 'left'; ctx.textBaseline = 'top';
      ctx.fillText(`C${k + 1}`, px + 3, R.t + 2);
      for (const t of vis) {
        const r = (t.axis === 'right' ? yr : yl);
        const y = interp(t.x, t.y, cx);
        if (!r || !Number.isFinite(y)) continue;
        ctx.fillStyle = t.color;
        ctx.beginPath(); ctx.arc(px, ymap(r, y), 3.5, 0, 2 * Math.PI); ctx.fill();
      }
    });
  }
}
