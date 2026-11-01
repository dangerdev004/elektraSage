// Symbol drawing. Each drawer builds a path in the element's local frame (x along the part
// from terminal 1 to terminal 2, y perpendicular, 16 units = one grid square) and the caller
// strokes it. Colours/line width are set by the caller. Symbols are my own drawings of the
// standard schematic shapes; nothing here is copied from CircuitJS1.

import { elLength, fromLocal } from './geometry.js';
import { directiveBox } from './directive.js';
import { getDef, halfHOf, subcktRows, pinNames } from './parts.js';

const line = (ctx, x1, y1, x2, y2) => {
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
};

function arrowHead(ctx, x, y, dx, dy, size = 6) {
  // filled triangle with its tip at (x, y), pointing along (dx, dy)
  const l = Math.hypot(dx, dy) || 1;
  const ux = dx / l;
  const uy = dy / l;
  ctx.moveTo(x, y);
  ctx.lineTo(x - ux * size + uy * size * 0.45, y - uy * size - ux * size * 0.45);
  ctx.lineTo(x - ux * size - uy * size * 0.45, y - uy * size + ux * size * 0.45);
  ctx.closePath();
}

const DRAW = {
  wire(ctx, L) {
    line(ctx, 0, 0, L, 0);
  },

  resistor(ctx, L, o) {
    const m = L / 2;
    const a = m - 16;
    const b = m + 16;
    line(ctx, 0, 0, a, 0);
    line(ctx, b, 0, L, 0);
    if (o.euro) {
      ctx.rect(a, -6, 32, 12);
    } else {
      ctx.moveTo(a, 0);
      for (let i = 1; i < 8; i++) ctx.lineTo(a + i * 4, i % 2 ? -6 : 6);
      ctx.lineTo(b, 0);
    }
  },

  capacitor(ctx, L) {
    const m = L / 2;
    line(ctx, 0, 0, m - 3, 0);
    line(ctx, m + 3, 0, L, 0);
    line(ctx, m - 3, -10, m - 3, 10);
    line(ctx, m + 3, -10, m + 3, 10);
  },

  polcap(ctx, L) {
    const m = L / 2;
    line(ctx, 0, 0, m - 3, 0);
    line(ctx, m + 4, 0, L, 0);
    line(ctx, m - 3, -10, m - 3, 10);
    ctx.moveTo(m + 6, -10);
    ctx.quadraticCurveTo(m - 1, 0, m + 6, 10);
    line(ctx, m - 11, -9, m - 11, -3); // plus sign
    line(ctx, m - 14, -6, m - 8, -6);
  },

  inductor(ctx, L) {
    const m = L / 2;
    const a = m - 16;
    line(ctx, 0, 0, a, 0);
    line(ctx, m + 16, 0, L, 0);
    for (let i = 0; i < 4; i++) {
      const cx = a + 4 + 8 * i;
      ctx.moveTo(cx - 4, 0);
      ctx.arc(cx, 0, 4, Math.PI, 0, false);
    }
  },

  switch(ctx, L, o) {
    const m = L / 2;
    line(ctx, 0, 0, m - 14, 0);
    line(ctx, m + 14, 0, L, 0);
    if (o.open) line(ctx, m - 14, 0, m + 12, -12); // open: lever raised
    else line(ctx, m - 14, 0, m + 14, 0); // closed: lever flat
    ctx.moveTo(m - 10, 0);
    ctx.arc(m - 14, 0, 3, 0, Math.PI * 2);
    ctx.moveTo(m + 17, 0);
    ctx.arc(m + 14, 0, 3, 0, Math.PI * 2);
  },

  ground(ctx, L) {
    line(ctx, 0, 0, L, 0);
    line(ctx, L, -10, L, 10);
    line(ctx, L + 4, -6, L + 4, 6);
    line(ctx, L + 8, -2, L + 8, 2);
  },

  dcvolt(ctx, L) {
    const m = L / 2;
    line(ctx, 0, 0, m - 3, 0);
    line(ctx, m + 3, 0, L, 0);
    line(ctx, m - 3, -12, m - 3, 12);
    line(ctx, m + 3, -6, m + 3, 6);
    line(ctx, m - 13, -9, m - 13, -3); // + sign next to the long plate
    line(ctx, m - 16, -6, m - 10, -6);
  },

  acvolt(ctx, L) {
    const m = L / 2;
    line(ctx, 0, 0, m - 14, 0);
    line(ctx, m + 14, 0, L, 0);
    ctx.moveTo(m + 14, 0);
    ctx.arc(m, 0, 14, 0, Math.PI * 2);
    ctx.moveTo(m - 8, 0);
    for (let i = 1; i <= 16; i++) ctx.lineTo(m - 8 + i, -6 * Math.sin((i / 16) * Math.PI * 2));
  },

  rail(ctx, L) {
    line(ctx, 0, 0, L, 0);
    ctx.moveTo(L + 20, 0);
    ctx.arc(L + 10, 0, 10, 0, Math.PI * 2);
  },

  current(ctx, L) {
    const m = L / 2;
    line(ctx, 0, 0, m - 14, 0);
    line(ctx, m + 14, 0, L, 0);
    ctx.moveTo(m + 14, 0);
    ctx.arc(m, 0, 14, 0, Math.PI * 2);
    line(ctx, m - 8, 0, m + 4, 0);
    arrowHead(ctx, m + 9, 0, 1, 0, 7);
  },

  diode(ctx, L) {
    const m = L / 2;
    line(ctx, 0, 0, m - 8, 0);
    line(ctx, m + 8, 0, L, 0);
    ctx.moveTo(m - 8, -9);
    ctx.lineTo(m - 8, 9);
    ctx.lineTo(m + 8, 0);
    ctx.closePath();
    line(ctx, m + 8, -9, m + 8, 9);
  },

  zener(ctx, L, o) {
    DRAW.diode(ctx, L, o);
    const m = L / 2;
    line(ctx, m + 8, -9, m + 12, -12);
    line(ctx, m + 8, 9, m + 4, 12);
  },

  led(ctx, L, o) {
    DRAW.diode(ctx, L, o);
    const m = L / 2;
    line(ctx, m - 2, -12, m + 6, -20);
    arrowHead(ctx, m + 6, -20, 1, -1, 5);
    line(ctx, m + 4, -9, m + 12, -17);
    arrowHead(ctx, m + 12, -17, 1, -1, 5);
  },

  npn(ctx, L, o, def, pnp = false) {
    const xb = L - 16;
    line(ctx, 0, 0, xb, 0);
    line(ctx, xb, -12, xb, 12);
    line(ctx, xb, -6, L, -16);
    line(ctx, xb, 6, L, 16);
    // emitter arrow: out of the base for NPN, into the base for PNP
    const dx = L - xb;
    const dy = 10;
    const t = 0.65;
    const px = xb + dx * t;
    const py = 6 + dy * t;
    if (pnp) arrowHead(ctx, xb + dx * 0.25, 6 + dy * 0.25, -dx, -dy, 6);
    else arrowHead(ctx, px, py, dx, dy, 6);
  },

  pnp(ctx, L, o, def) {
    DRAW.npn(ctx, L, o, def, true);
  },

  nmos(ctx, L, o, def, pmos = false) {
    const xg = L - 20;
    const xc = L - 14;
    line(ctx, 0, 0, xg, 0);
    line(ctx, xg, -10, xg, 10);
    line(ctx, xc, -12, xc, -6);
    line(ctx, xc, -3, xc, 3);
    line(ctx, xc, 6, xc, 12);
    ctx.moveTo(xc, -9);
    ctx.lineTo(L, -9);
    ctx.lineTo(L, -16);
    ctx.moveTo(xc, 9);
    ctx.lineTo(L, 9);
    ctx.lineTo(L, 16);
    line(ctx, xc, 0, L - 4, 0);
    if (pmos) arrowHead(ctx, L - 4, 0, 1, 0, 5);
    else arrowHead(ctx, xc, 0, -1, 0, 5);
  },

  pmos(ctx, L, o, def) {
    DRAW.nmos(ctx, L, o, def, true);
  },

  opamp(ctx, L, o, def) {
    const xa = L - 16;
    line(ctx, 0, -16, 16, -16);
    line(ctx, 0, 16, 16, 16);
    line(ctx, xa, 0, L, 0);
    ctx.moveTo(16, -32);
    ctx.lineTo(16, 32);
    ctx.lineTo(xa, 0);
    ctx.closePath();
    const swapped = def.swap || o.swap;
    const top = swapped ? '+' : '−';
    const bot = swapped ? '−' : '+';
    // input signs, drawn as strokes so they follow the part's colour
    const sign = (y, s) => {
      line(ctx, 20, y, 26, y);
      if (s === '+') line(ctx, 23, y - 3, 23, y + 3);
    };
    sign(-16, top);
    sign(16, bot);
  },

  clock(ctx, L) {
    line(ctx, 0, 0, L, 0);
    ctx.moveTo(L + 20, 0);
    ctx.arc(L + 10, 0, 10, 0, Math.PI * 2);
    // small square wave inside the circle
    ctx.moveTo(L + 4, 3);
    ctx.lineTo(L + 4, -3);
    ctx.lineTo(L + 10, -3);
    ctx.lineTo(L + 10, 3);
    ctx.lineTo(L + 16, 3);
    ctx.lineTo(L + 16, -3);
  },

  logicin(ctx, L) {
    line(ctx, 0, 0, L, 0);
    ctx.rect(L, -11, 24, 22);
  },

  // lamp: filled when the net is HIGH in the last result (o.lamp === true)
  logicout(ctx, L, o) {
    line(ctx, 0, 0, L, 0);
    ctx.moveTo(L + 22, 0);
    ctx.arc(L + 11, 0, 11, 0, Math.PI * 2);
    if (o.lamp === true) {
      ctx.fillStyle = '#ffd54f';
      ctx.fill();
    }
  },

  // Logic gates (distinctive-shape symbols). Body spans x = 16..52; inputs at (0, +-16), output at L.
  gate(ctx, L, o, def) {
    const tip = def.shape === 'buf' ? 48 : 52;
    if (def.shape === 'buf') {
      line(ctx, 0, 0, 16, 0);
      ctx.moveTo(16, -14);
      ctx.lineTo(16, 14);
      ctx.lineTo(tip, 0);
      ctx.closePath();
    } else if (def.shape === 'and') {
      line(ctx, 0, -16, 16, -16);
      line(ctx, 0, 16, 16, 16);
      ctx.moveTo(32, -20);
      ctx.lineTo(16, -20);
      ctx.lineTo(16, 20);
      ctx.lineTo(32, 20);
      ctx.arc(32, 0, 20, Math.PI / 2, -Math.PI / 2, true);
    } else {
      // OR / XOR: concave back, curved sides meeting at a point
      const xor = def.shape === 'xor';
      line(ctx, 0, -16, 18, -16);
      line(ctx, 0, 16, 18, 16);
      ctx.moveTo(16, -20);
      ctx.quadraticCurveTo(38, -20, tip, 0);
      ctx.quadraticCurveTo(38, 20, 16, 20);
      ctx.quadraticCurveTo(26, 0, 16, -20);
      if (xor) {
        ctx.moveTo(10, -20);
        ctx.quadraticCurveTo(20, 0, 10, 20);
      }
    }
    let xo = tip;
    if (def.bubble) {
      ctx.moveTo(tip + 8, 0);
      ctx.arc(tip + 4, 0, 4, 0, Math.PI * 2);
      xo = tip + 8;
    }
    line(ctx, xo, 0, L, 0);
  },

  chip(ctx, L, o, def) {
    ctx.rect(16, -32, L - 32, 64);
    for (const p of def.pinSpec) {
      const x = p.x === 'L' ? L : p.x;
      const gap = p.bubble ? 6 : 0; // room for the inversion bubble at the clock pin
      if (p.side === 'l') line(ctx, x, p.y, 16 - gap, p.y);
      else if (p.side === 'r') line(ctx, L - 16, p.y, x, p.y);
      else if (p.side === 't') line(ctx, x, p.y, x, -32);
      else line(ctx, x, p.y, x, 32);
      if (p.clk) {
        ctx.moveTo(16, p.y - 6);
        ctx.lineTo(24, p.y);
        ctx.lineTo(16, p.y + 6);
      }
      if (p.bubble) {
        ctx.moveTo(16, p.y);
        ctx.arc(13, p.y, 3, 0, Math.PI * 2);
      }
    }
  },

  subckt(ctx, L, o, def, el) {
    const pins = el?.pins ?? [];
    const half = subcktRows(el) * 16;
    const left = Math.ceil(pins.length / 2);
    ctx.rect(16, -half, L - 32, half * 2);
    pins.forEach((_, i) => {
      if (i < left) line(ctx, 0, -half + 16 + 32 * i, 16, -half + 16 + 32 * i);
      else line(ctx, L - 16, -half + 16 + 32 * (i - left), L, -half + 16 + 32 * (i - left));
    });
  },

  meter(ctx, L) {
    const m = L / 2;
    line(ctx, 0, 0, m - 14, 0);
    line(ctx, m + 14, 0, L, 0);
    ctx.moveTo(m + 14, 0);
    ctx.arc(m, 0, 14, 0, Math.PI * 2);
  },

  label(ctx, L, o, def) {
    line(ctx, 0, 0, L, 0);
    if (def.port) { ctx.rect(L, -10, 60, 20); return; } // ports are plain rectangles, labels are flags
    ctx.moveTo(L, 0);
    ctx.lineTo(L + 8, -10);
    ctx.lineTo(L + 60, -10);
    ctx.lineTo(L + 60, 10);
    ctx.lineTo(L + 8, 10);
    ctx.closePath();
  },

  box(ctx, L, o, def) {
    const m = L / 2;
    const w = 20;
    line(ctx, 0, 0, m - w, 0);
    line(ctx, m + w, 0, L, 0);
    ctx.rect(m - w, -12, w * 2, 24);
  },
};

// Draws the element's symbol at its position. Stroke/fill colour must already be set.
export function drawElement(ctx, el, opts = {}) {
  const def = getDef(el.type);
  const L = elLength(el);
  const fn = DRAW[def.kind] ?? DRAW.box;
  ctx.save();
  ctx.translate(el.x1, el.y1);
  ctx.rotate(Math.atan2(el.y2 - el.y1, el.x2 - el.x1));
  if (el.mirror) ctx.scale(1, -1);
  ctx.beginPath();
  fn(ctx, L, { ...opts, swap: String(el.params?.swap) === 'true', open: String(el.params?.open) === 'true' }, def, el);
  ctx.stroke();
  ctx.restore();
  if (def.kind === 'directive') {
    // a framed block of monospace text, always upright
    const b = directiveBox(el);
    ctx.save();
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.rect(b.x, b.y, b.w, b.h);
    ctx.stroke();
    ctx.font = '11px ui-monospace, Menlo, Consolas, monospace';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    b.lines.forEach((l, i) => ctx.fillText(l, b.x + b.pad, b.y + b.pad + b.lineH / 2 + i * b.lineH));
    ctx.restore();
  }
  if (def.kind === 'logicin' || def.kind === 'logicout') {
    ctx.save();
    ctx.font = 'bold 12px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const c = fromLocal(el, L + (def.kind === 'logicin' ? 12 : 11), 0);
    let txt;
    if (def.kind === 'logicin') txt = String(el.params?.high) === 'true' ? '1' : '0';
    else txt = opts.lamp === true ? '1' : opts.lamp === false ? '0' : '?';
    if (def.kind === 'logicout' && opts.lamp === true) ctx.fillStyle = '#000000'; // dark digit on the lit lamp
    ctx.fillText(txt, c.x, c.y);
    ctx.restore();
  }
  if (def.kind === 'chip') {
    // pin names and the part title in world space so they are never rotated or mirrored
    ctx.save();
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const at = (lx, ly) => fromLocal(el, lx, ly);
    ctx.font = '9px sans-serif';
    for (const p of def.pinSpec) {
      if (!p.n) continue;
      const x = p.x === 'L' ? L : p.x;
      const q = p.side === 'l' ? at(x + 26, p.y) : p.side === 'r' ? at(x - 26, p.y) : p.side === 't' ? at(x, p.y + 22) : at(x, p.y - 22);
      ctx.fillText(p.n, q.x, q.y);
    }
    ctx.font = '8px sans-serif';
    const c = at(L / 2, 0);
    ctx.fillText(def.title, c.x, c.y, L - 36);
    ctx.restore();
  }
  if (def.kind === 'meter') {
    ctx.save();
    ctx.font = 'bold 14px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const c = fromLocal(el, L / 2, 0);
    ctx.fillText(def.letter, c.x, c.y);
    ctx.restore();
  }
  if (def.kind === 'label') {
    ctx.save();
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const c = fromLocal(el, L + 34, 0);
    ctx.fillText(String(el.value ?? '').trim() || '?', c.x, c.y, 48);
    ctx.restore();
  }
  if (def.kind === 'subckt') {
    ctx.save();
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const pins = el.pins ?? [];
    const left = Math.ceil(pins.length / 2);
    const half = subcktRows(el) * 16;
    const at = (lx, ly) => fromLocal(el, lx, ly);
    ctx.font = '9px sans-serif';
    pins.forEach((n, i) => {
      const q = i < left ? at(40, -half + 16 + 32 * i) : at(L - 40, -half + 16 + 32 * (i - left));
      ctx.fillText(el.labels?.[i] || n, q.x, q.y, 52);
    });
    if (!pins.length) { const c = at(L / 2, 0); ctx.fillText('SUBCKT ?', c.x, c.y, L - 36); }
    ctx.restore();
  }
  if (def.kind === 'box') {
    // name inside the box, squeezed to fit; drawn in world space so it is never rotated
    ctx.save();
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(def.label, (el.x1 + el.x2) / 2, (el.y1 + el.y2) / 2, 38);
    ctx.restore();
  }
}

// Value text next to the part, always horizontal.
/** Small pin names just outside each pin (Options > Show Pin Labels). `terms` = the part's pins in world space. */
export function drawPinLabels(ctx, el, terms) {
  const names = pinNames(el);
  if (!names || names.length !== terms.length) return;
  const cx = (el.x1 + el.x2) / 2;
  const cy = (el.y1 + el.y2) / 2;
  ctx.save();
  ctx.font = '9px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  terms.forEach((p, i) => {
    const dx = p.x - cx; const dy = p.y - cy;
    const d = Math.hypot(dx, dy) || 1;
    ctx.fillText(names[i], p.x + (dx / d) * 8, p.y + (dy / d) * 8 - 6);
  });
  ctx.restore();
}

export function drawLabel(ctx, el, text) {
  if (!text) return;
  const mx = (el.x1 + el.x2) / 2;
  const my = (el.y1 + el.y2) / 2;
  const horizontal = Math.abs(el.x2 - el.x1) >= Math.abs(el.y2 - el.y1);
  ctx.save();
  ctx.font = '11px sans-serif';
  ctx.textBaseline = 'middle';
  if (horizontal) {
    ctx.textAlign = 'center';
    ctx.fillText(text, mx, my - (halfHOf(el) + 6));
  } else {
    ctx.textAlign = 'left';
    ctx.fillText(text, mx + halfHOf(el) + 6, my);
  }
  ctx.restore();
}
