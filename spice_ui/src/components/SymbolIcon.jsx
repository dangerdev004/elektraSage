import { useEffect, useRef } from 'react';
import { getDef } from '../canvas/parts.js';
import { drawElement } from '../canvas/symbols.js';

const W = 44;
const H = 30;

// Toolbar icon: draws the same symbol the canvas uses, so icons and canvas can't drift apart.
export function SymbolIcon({ type }) {
  const ref = useRef(null);

  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const dpr = window.devicePixelRatio || 1;
    c.width = W * dpr;
    c.height = H * dpr;
    const ctx = c.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);

    const def = getDef(type);
    const L = def.minLen || 32;
    const extent = L + def.ext;
    const scale = Math.min(1, (W - 6) / extent, (H - 4) / (2 * def.halfH));
    ctx.translate((W - extent * scale) / 2, H / 2);
    ctx.scale(scale, scale);
    const color = getComputedStyle(c).color;
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 2 / scale > 3 ? 3 : 2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    drawElement(ctx, { type, x1: 0, y1: 0, x2: L, y2: 0, mirror: false }, { euro: false });
  }, [type]);

  return <canvas ref={ref} className="sym-icon" style={{ width: W, height: H }} aria-hidden="true" />;
}
