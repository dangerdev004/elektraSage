// Parsing of the free-text values shown on parts ("1 kΩ", "10 µF", "5 V, 100 Hz").
// No DOM, so it is unit-tested in Node.

const PREFIX = { t: 1e12, g: 1e9, k: 1e3, m: 1e-3, u: 1e-6, n: 1e-9, p: 1e-12, f: 1e-15 };

/**
 * Parse "4.7k", "1 kΩ", "10 µF", "1Meg", "2 MΩ", "5 V", "100 Hz".
 * `unit` is the unit symbol this field should carry ('F', 'H', 'V', 'A', 'Hz', '' for ohms).
 * Passing it matters: without it "1 F" would read as 1 femto and "1 H" / "1 V" would be fine only by luck.
 * Returns NaN if there is no number.
 *
 * One deliberate difference from SPICE: a capital M (as in "2 MΩ") means mega, because that is
 * what people type on a schematic; SPICE itself reads both "m" and "M" as milli. Write "Meg" or
 * "M" for mega and "m" for milli.
 */
export function parseValue(input, unit = '') {
  const s = String(input ?? '')
    .trim()
    .replace(/[µμ]/g, 'u')
    .replace(/Ω|ohms?\b/gi, '');
  const m = /^([+-]?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?)\s*([a-zA-Z]*)/.exec(s);
  if (!m) return NaN;
  const num = parseFloat(m[1]);
  let suf = m[2];
  if (!suf) return num;
  if (unit) {
    if (suf === unit) return num;
    if (suf.length > unit.length && suf.endsWith(unit)) suf = suf.slice(0, -unit.length);
  }
  const low = suf.toLowerCase();
  if (low.startsWith('meg')) return num * 1e6;
  if (low.startsWith('mil')) return num * 25.4e-6;
  if (suf[0] === 'M') return num * 1e6;
  const mult = PREFIX[low[0]];
  return mult === undefined ? num : num * mult;
}

/** "5 V, 100 Hz" -> { amp: 5, freq: 100 }. freq is undefined when not given. */
export function parseSourceText(text) {
  const [a, f] = String(text ?? '').split(/[,;]/);
  return {
    amp: parseValue(a, 'V'),
    freq: f && f.trim() ? parseValue(f, 'Hz') : undefined,
  };
}

/** Number -> a string every SPICE accepts (plain decimal or exponent form). */
export function num(x) {
  return String(Number(x.toPrecision(12)));
}
