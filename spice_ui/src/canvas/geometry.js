// Pure geometry helpers. No DOM, so they can be unit-tested in Node.

export const GRID = 16;

// `|| 0` turns -0 into 0 so coordinates compare and serialise cleanly.
export const snap = (v, g = GRID) => Math.round(v / g) * g || 0;

export function segDist(px, py, x1, y1, x2, y2) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const l2 = dx * dx + dy * dy;
  if (l2 === 0) return Math.hypot(px - x1, py - y1);
  let t = ((px - x1) * dx + (py - y1) * dy) / l2;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
}

export const elLength = (el) => Math.hypot(el.x2 - el.x1, el.y2 - el.y1);

// An element is defined by two grid points (x1,y1) -> (x2,y2). Its symbol is drawn in a
// local frame: x runs from point 1 towards point 2, y is perpendicular. `mirror` flips y.
export function toLocal(el, wx, wy) {
  const L = elLength(el);
  if (L === 0) return { x: wx - el.x1, y: wy - el.y1 };
  const c = (el.x2 - el.x1) / L;
  const s = (el.y2 - el.y1) / L;
  const dx = wx - el.x1;
  const dy = wy - el.y1;
  const x = dx * c + dy * s;
  let y = -dx * s + dy * c;
  if (el.mirror) y = -y;
  return { x, y };
}

export function fromLocal(el, lx, ly) {
  const L = elLength(el);
  if (L === 0) return { x: el.x1 + lx, y: el.y1 + ly };
  const c = (el.x2 - el.x1) / L;
  const s = (el.y2 - el.y1) / L;
  if (el.mirror) ly = -ly;
  return { x: el.x1 + lx * c - ly * s, y: el.y1 + lx * s + ly * c };
}

// End point for a part dragged from (x1,y1) towards (px,py): axis-aligned, at least minLen long.
export function axisEnd(x1, y1, px, py, minLen, grid = GRID) {
  const dx = px - x1;
  const dy = py - y1;
  if (Math.abs(dx) >= Math.abs(dy)) {
    const len = Math.max(minLen, snap(Math.abs(dx), grid));
    return { x2: x1 + (dx < 0 ? -len : len), y2: y1 };
  }
  const len = Math.max(minLen, snap(Math.abs(dy), grid));
  return { x2: x1, y2: y1 + (dy < 0 ? -len : len) };
}

export function rectsIntersect(a, b) {
  return a.x0 <= b.x1 && a.x1 >= b.x0 && a.y0 <= b.y1 && a.y1 >= b.y0;
}

export function normRect(x0, y0, x1, y1) {
  return { x0: Math.min(x0, x1), y0: Math.min(y0, y1), x1: Math.max(x0, x1), y1: Math.max(y0, y1) };
}
