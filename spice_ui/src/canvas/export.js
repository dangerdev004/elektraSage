// Export the circuit as a PNG, an SVG, or a print page. All three redraw the circuit with the same
// symbol code the canvas uses (drawElement / drawLabel), on a white background in black ink, without
// the grid, the selection colour or the drag handles.
//
// SVG output: symbols.js draws with the canvas 2D API, so SvgContext below implements the small part of
// that API the drawers use and writes <path> / <text> elements instead of pixels. No DOM is needed, which
// is why it is unit-tested in Node.

import { drawElement, drawLabel } from './symbols.js';
import { getDef } from './parts.js';
import { directiveBox } from './directive.js';

const PAD = 48; // margin around the outermost pin, in canvas units
const INK = '#000000';
const PAPER = '#ffffff';
const NODE_LABEL = '#8a5a00'; // the yellow used on screen is unreadable on white

/** { x, y, w, h } around every part, or null for an empty circuit. */
export function circuitBounds(editor) {
  let x0 = Infinity; let y0 = Infinity; let x1 = -Infinity; let y1 = -Infinity;
  for (const el of editor.els) {
    const pts = [...editor.terminals(el), { x: el.x1, y: el.y1 }, { x: el.x2, y: el.y2 }];
    if (getDef(el.type).kind === 'directive') {
      const b = directiveBox(el);
      pts.push({ x: b.x, y: b.y }, { x: b.x + b.w, y: b.y + b.h });
    }
    for (const p of pts) {
      x0 = Math.min(x0, p.x); y0 = Math.min(y0, p.y);
      x1 = Math.max(x1, p.x); y1 = Math.max(y1, p.y);
    }
  }
  if (!Number.isFinite(x0)) return null;
  return { x: x0 - PAD, y: y0 - PAD, w: x1 - x0 + 2 * PAD, h: y1 - y0 + 2 * PAD };
}

/** Draw the circuit onto any canvas-like context whose origin is already at the circuit's top-left. */
export function renderCircuit(ctx, editor) {
  ctx.lineWidth = 2;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  const o = { euro: editor.opts.euro };
  const counts = new Map();
  for (const el of editor.els) {
    ctx.strokeStyle = INK;
    ctx.fillStyle = INK;
    drawElement(ctx, el, el.type === 'LogicOutputElm' ? { ...o, lamp: editor.lampProvider?.(el) ?? null } : o);
    if (editor.opts.showValues && getDef(el.type).kind !== 'directive' && getDef(el.type).kind !== 'label') {
      const def = getDef(el.type);
      drawLabel(ctx, el, el.model ?? el.value ?? def.value);
    }
    for (const t of editor.terminals(el)) {
      const k = `${Math.round(t.x)},${Math.round(t.y)}`;
      counts.set(k, (counts.get(k) ?? 0) + 1);
    }
  }
  ctx.fillStyle = INK;
  for (const [k, n] of counts) { // junction dots, same rule as the canvas: three or more pins meet
    if (n < 3) continue;
    const [x, y] = k.split(',').map(Number);
    ctx.beginPath();
    ctx.arc(x, y, 3.5, 0, Math.PI * 2);
    ctx.fill();
  }
  if (editor.opts.nodeLabels && editor.nodeLabelProvider) {
    ctx.font = 'bold 11px ui-monospace, Menlo, Consolas, monospace';
    ctx.textBaseline = 'bottom';
    ctx.textAlign = 'left';
    ctx.lineWidth = 3;
    for (const lb of editor.nodeLabelProvider()) {
      ctx.strokeStyle = PAPER;
      ctx.strokeText(lb.text, lb.x + 5, lb.y - 4);
      ctx.fillStyle = NODE_LABEL;
      ctx.fillText(lb.text, lb.x + 5, lb.y - 4);
    }
  }
}

// ---- SVG ------------------------------------------------------------------------------------
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const f2 = (v) => String(Math.round(v * 100) / 100);

/** The subset of CanvasRenderingContext2D used by symbols.js, recording SVG instead of drawing. */
export class SvgContext {
  constructor() {
    this.out = [];
    this.m = [1, 0, 0, 1, 0, 0]; // a b c d e f
    this.stack = [];
    this.path = [];
    this.cur = null; // current point (device space) or null at the start of a subpath
    this.start = null;
    this.fillStyle = INK;
    this.strokeStyle = INK;
    this.lineWidth = 1;
    this.lineCap = 'butt';
    this.lineJoin = 'miter';
    this.font = '10px sans-serif';
    this.textAlign = 'start';
    this.textBaseline = 'alphabetic';
  }

  pt(x, y) {
    const [a, b, c, d, e, f] = this.m;
    return [a * x + c * y + e, b * x + d * y + f];
  }

  mul(a, b, c, d, e, f) {
    const [A, B, C, D, E, F] = this.m;
    this.m = [A * a + C * b, B * a + D * b, A * c + C * d, B * c + D * d, A * e + C * f + E, B * e + D * f + F];
  }

  save() {
    this.stack.push({
      m: [...this.m], fillStyle: this.fillStyle, strokeStyle: this.strokeStyle, lineWidth: this.lineWidth,
      font: this.font, textAlign: this.textAlign, textBaseline: this.textBaseline,
    });
  }

  restore() {
    const s = this.stack.pop();
    if (s) Object.assign(this, s);
  }

  translate(x, y) { this.mul(1, 0, 0, 1, x, y); }
  rotate(t) { this.mul(Math.cos(t), Math.sin(t), -Math.sin(t), Math.cos(t), 0, 0); }
  scale(x, y) { this.mul(x, 0, 0, y, 0, 0); }

  beginPath() { this.path = []; this.cur = null; this.start = null; }

  moveTo(x, y) {
    const p = this.pt(x, y);
    this.path.push(`M${f2(p[0])} ${f2(p[1])}`);
    this.cur = p;
    this.start = p;
  }

  lineTo(x, y) {
    const p = this.pt(x, y);
    this.path.push(this.cur ? `L${f2(p[0])} ${f2(p[1])}` : `M${f2(p[0])} ${f2(p[1])}`);
    if (!this.cur) this.start = p;
    this.cur = p;
  }

  quadraticCurveTo(cx, cy, x, y) {
    if (!this.cur) this.moveTo(cx, cy);
    const c = this.pt(cx, cy);
    const p = this.pt(x, y);
    this.path.push(`Q${f2(c[0])} ${f2(c[1])} ${f2(p[0])} ${f2(p[1])}`);
    this.cur = p;
  }

  /** Arcs become short line segments after the transform, so a mirrored or rotated arc stays exact. */
  arc(cx, cy, r, a0, a1, ccw = false) {
    const TAU = Math.PI * 2;
    const norm = (v) => ((v % TAU) + TAU) % TAU;
    let d;
    if (!ccw) d = a1 - a0 >= TAU ? TAU : norm(a1 - a0);
    else d = a0 - a1 >= TAU ? -TAU : -norm(a0 - a1);
    const n = Math.max(6, Math.ceil((Math.abs(d) / TAU) * 64));
    for (let i = 0; i <= n; i++) {
      const a = a0 + (d * i) / n;
      this.lineTo(cx + r * Math.cos(a), cy + r * Math.sin(a));
    }
  }

  rect(x, y, w, h) {
    this.moveTo(x, y);
    this.lineTo(x + w, y);
    this.lineTo(x + w, y + h);
    this.lineTo(x, y + h);
    this.closePath();
  }

  closePath() {
    if (!this.cur) return;
    this.path.push('Z');
    this.cur = this.start;
  }

  scaleFactor() { return Math.sqrt(Math.abs(this.m[0] * this.m[3] - this.m[1] * this.m[2])) || 1; }

  stroke() {
    if (!this.path.length) return;
    this.out.push(`<path d="${this.path.join('')}" fill="none" stroke="${esc(this.strokeStyle)}" stroke-width="${f2(this.lineWidth * this.scaleFactor())}" stroke-linecap="round" stroke-linejoin="round"/>`);
  }

  fill() {
    if (!this.path.length) return;
    this.out.push(`<path d="${this.path.join('')}" fill="${esc(this.fillStyle)}"/>`);
  }

  text(str, x, y, maxWidth, style) {
    const p = this.pt(x, y);
    const size = parseFloat(/(\d+(?:\.\d+)?)px/.exec(this.font)?.[1] ?? '10') * this.scaleFactor();
    const family = /monospace/.test(this.font) ? 'ui-monospace, Menlo, Consolas, monospace' : 'sans-serif';
    const anchor = { center: 'middle', left: 'start', start: 'start', right: 'end', end: 'end' }[this.textAlign] ?? 'start';
    const base = { middle: 'central', bottom: 'text-after-edge', top: 'text-before-edge' }[this.textBaseline] ?? 'alphabetic';
    const weight = /\bbold\b/.test(this.font) ? ' font-weight="bold"' : '';
    // a rough width estimate stands in for ctx.measureText so a maxWidth squeeze can be honoured
    const fit = maxWidth && String(str).length * size * 0.55 > maxWidth ? ` textLength="${f2(maxWidth)}" lengthAdjust="spacingAndGlyphs"` : '';
    this.out.push(`<text x="${f2(p[0])}" y="${f2(p[1])}" font-family="${family}" font-size="${f2(size)}"${weight} text-anchor="${anchor}" dominant-baseline="${base}"${fit} ${style}>${esc(str)}</text>`);
  }

  fillText(str, x, y, maxWidth) { this.text(str, x, y, maxWidth, `fill="${esc(this.fillStyle)}"`); }

  strokeText(str, x, y, maxWidth) {
    this.text(str, x, y, maxWidth, `fill="none" stroke="${esc(this.strokeStyle)}" stroke-width="${f2(this.lineWidth)}" stroke-linejoin="round"`);
  }
}

/** Full SVG document text for the circuit, or null when there is nothing to export. */
export function circuitToSvg(editor) {
  const b = circuitBounds(editor);
  if (!b) return null;
  const ctx = new SvgContext();
  ctx.translate(-b.x, -b.y);
  renderCircuit(ctx, editor);
  const w = Math.ceil(b.w);
  const h = Math.ceil(b.h);
  return [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">`,
    `<rect width="${w}" height="${h}" fill="${PAPER}"/>`,
    ...ctx.out,
    '</svg>',
    '',
  ].join('\n');
}

// ---- PNG (browser only) -----------------------------------------------------------------------
/** PNG Blob of the circuit at `scale` times its canvas size (capped so the bitmap stays reasonable). */
export function circuitToPng(editor, scale = 2) {
  const b = circuitBounds(editor);
  if (!b) return Promise.resolve(null);
  const s = Math.min(scale, 8000 / Math.max(b.w, b.h));
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, Math.round(b.w * s));
  canvas.height = Math.max(1, Math.round(b.h * s));
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = PAPER;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.setTransform(s, 0, 0, s, -b.x * s, -b.y * s);
  renderCircuit(ctx, editor);
  return new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
}

/** Browser download of text or a Blob. */
export function downloadFile(name, data, type) {
  const blob = data instanceof Blob ? data : new Blob([data], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Print the circuit (as vector SVG) through a hidden frame so the app UI is not printed. */
export function printCircuit(editor, title = 'Circuit') {
  const svg = circuitToSvg(editor);
  if (!svg) return false;
  const frame = document.createElement('iframe');
  frame.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0;';
  document.body.appendChild(frame);
  const doc = frame.contentDocument;
  doc.open();
  doc.write(`<!doctype html><title>${esc(title)}</title><style>@page{margin:12mm}html,body{margin:0;background:#fff}svg{width:100%;height:auto;max-height:95vh}</style>${svg}`);
  doc.close();
  setTimeout(() => {
    frame.contentWindow.focus();
    frame.contentWindow.print();
    setTimeout(() => frame.remove(), 1500);
  }, 150);
  return true;
}
