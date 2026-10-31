// Size of a SPICE Directive block on the canvas. The block hangs down and to the right of its first
// point (x1, y1); it is drawn in screen orientation whatever the part's angle.

const CHAR_W = 6.6;
const LINE_H = 14;
const PAD = 6;

export const directiveText = (el) => String(el.value ?? '');

export function directiveBox(el) {
  const lines = directiveText(el).split(/\r?\n/);
  const longest = Math.max(8, ...lines.map((l) => l.length));
  return { x: el.x1, y: el.y1 - LINE_H / 2 - PAD, w: Math.ceil(longest * CHAR_W + PAD * 2), h: lines.length * LINE_H + PAD * 2, lines, lineH: LINE_H, pad: PAD };
}
