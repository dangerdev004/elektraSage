// Turns what the engine returns into one shape the UI uses, and builds plot traces from it.
// Pure, no DOM.
//
// Normalised result:
//   { analysis: 'tran'|'ac'|'dc'|'op', xLabel, xUnit, x: Float64Array | null,
//     vectors: [{ label: 'v(n2)', unit: 'V', real: Float64Array, imag?: Float64Array }] }

import { COLORS } from './plotter.js';

const UNIT_OF = { time: 's', frequency: 'Hz' };

/** ngspice vector name -> label shown to the user: "n2" -> "v(n2)", "v1#branch" -> "i(v1)". */
export function labelOf(name) {
  const n = String(name).trim().toLowerCase();
  if (/^[vi]\(.+\)$/.test(n)) return n;
  if (n.endsWith('#branch')) return `i(${n.slice(0, -7)})`;
  return `v(${n})`;
}

const unitOfLabel = (label) => (label.startsWith('i(') ? 'A' : 'V');

const toF64 = (arr) => Float64Array.from(arr, (v) => Number(v));

function splitComplex(values) {
  const re = new Float64Array(values.length);
  const im = new Float64Array(values.length);
  values.forEach((c, i) => {
    re[i] = Number(c.real ?? c.re ?? c.r ?? 0);
    im[i] = Number(c.img ?? c.imag ?? c.im ?? c.i ?? 0);
  });
  return [re, im];
}

/**
 * The shape produced by server/rawfile.mjs (parsed ngspice raw file):
 *   { variableNames: string[], numPoints, dataType: 'real'|'complex',
 *     data: [{ name, type, values: number[] | {real, img}[] }] }
 * It accepts a few spellings of the complex fields and throws a clear error, naming the keys it saw,
 * if the shape does not fit.
 */
export function normalizeRaw(raw, analysisType) {
  const data = raw?.data;
  if (!Array.isArray(data) || !data.length) {
    const keys = raw && typeof raw === 'object' ? Object.keys(raw).join(', ') : typeof raw;
    throw new Error(`Unrecognised result from the simulator engine (keys: ${keys}). Open the browser console and send me the logged "raw result".`);
  }
  const entries = data.map((d) => {
    const vals = d.values ?? d.data ?? [];
    const complex = vals.length > 0 && typeof vals[0] === 'object' && vals[0] !== null;
    if (complex) {
      const [re, im] = splitComplex(vals);
      return { name: String(d.name), real: re, imag: im };
    }
    return { name: String(d.name), real: toF64(vals) };
  });

  const scaleName = { tran: 'time', ac: 'frequency' }[analysisType];
  let si = scaleName ? entries.findIndex((e) => e.name.toLowerCase() === scaleName) : -1;
  if (si < 0 && (analysisType === 'dc' || scaleName)) si = 0; // sweep/scale is the first vector
  const scale = si >= 0 ? entries[si] : null;

  const vectors = entries
    .filter((e, i) => i !== si && !/^(v\()?(z_|d_n)/i.test(e.name)) // z_* = op-amp internals, d_n* = digital shadow nodes of logic nets

    .map((e) => {
      const label = labelOf(e.name);
      return { label, unit: unitOfLabel(label), real: e.real, ...(e.imag ? { imag: e.imag } : {}) };
    });

  const xName = scale?.name.toLowerCase();
  return {
    analysis: analysisType,
    xLabel: analysisType === 'tran' ? 'Time' : analysisType === 'ac' ? 'Frequency' : analysisType === 'dc' ? 'Sweep' : '',
    xUnit: UNIT_OF[xName] ?? (analysisType === 'dc' ? 'V' : ''),
    x: scale ? scale.real : null,
    vectors,
  };
}

/** Which vectors start ticked: all voltages, no currents. */
export const defaultVisible = (res) => new Set(res.vectors.filter((v) => v.unit === 'V' && !v.label.includes('.')).map((v) => v.label)); // x1.n002 = inside a subcircuit

export const colorFor = (res, label) => {
  const i = res.vectors.findIndex((v) => v.label === label);
  return COLORS[(i < 0 ? 0 : i) % COLORS.length];
};

/** Traces for Plotter.setData(). AC shows dB on the left axis and (optionally) phase on the right. */
export function buildTraces(res, visible, { showPhase = true } = {}) {
  if (!res || res.analysis === 'op' || !res.x) return { traces: [], xlog: false, xLabel: '', xUnit: '' };
  const traces = [];
  for (const v of res.vectors) {
    if (!visible.has(v.label)) continue;
    const color = colorFor(res, v.label);
    if (res.analysis === 'ac') {
      const n = res.x.length;
      const mag = new Float64Array(n);
      const ph = new Float64Array(n);
      for (let i = 0; i < n; i++) {
        const re = v.real[i];
        const im = v.imag ? v.imag[i] : 0;
        mag[i] = 20 * Math.log10(Math.hypot(re, im));
        ph[i] = (Math.atan2(im, re) * 180) / Math.PI;
      }
      traces.push({ name: `${v.label} dB`, color, x: res.x, y: mag, axis: 'left', unit: 'dB', visible: true });
      if (showPhase) traces.push({ name: `${v.label} °`, color, x: res.x, y: ph, axis: 'right', unit: '°', visible: true, dash: true });
    } else {
      traces.push({
        name: v.label, color, x: res.x, y: v.real, axis: v.unit === 'A' ? 'right' : 'left', unit: v.unit, visible: true,
      });
    }
  }
  return { traces, xlog: res.analysis === 'ac', xLabel: res.xLabel, xUnit: res.xUnit };
}

/** First-order measurements shown under the plot. Returns [[label, value-string]]. */
export function measure(res, label, si) {
  const v = res.vectors.find((x) => x.label === label);
  if (!v || res.analysis === 'op' || res.analysis === 'ac') return [];
  let min = Infinity, max = -Infinity, sum = 0;
  for (const y of v.real) { if (y < min) min = y; if (y > max) max = y; sum += y; }
  return [['min', si(min)], ['max', si(max)], ['pk-pk', si(max - min)], ['mean', si(sum / v.real.length)]];
}

// ---------- meters ----------
// `meters` comes from buildCircuitNetlist: [{ id, kind: 'probe'|'ammeter'|'ohm', name, nodes: [a, b], source?, amps? }].

const vecOf = (res, label) => res.vectors.find((v) => v.label === label);
const GROUND = (name) => name === '0';

function nodeSeries(res, node) {
  if (GROUND(node)) return { re: null, im: null };
  const v = vecOf(res, `v(${node})`);
  return v ? { re: v.real, im: v.imag ?? null } : null;
}

/** Add a v(P1)-style differential trace for every voltmeter probe, so it plots like any node. */
export function addMeterVectors(res, meters = []) {
  const extra = [];
  for (const m of meters) {
    if (m.kind !== 'probe') continue;
    const a = nodeSeries(res, m.nodes[0]);
    const b = nodeSeries(res, m.nodes[1]);
    if (!a || !b) continue;
    const n = (res.x ? res.x.length : 1);
    const real = new Float64Array(n);
    let imag = null;
    for (let i = 0; i < n; i++) real[i] = (a.re ? a.re[i] : 0) - (b.re ? b.re[i] : 0);
    if (a.im || b.im) {
      imag = new Float64Array(n);
      for (let i = 0; i < n; i++) imag[i] = (a.im ? a.im[i] : 0) - (b.im ? b.im[i] : 0);
    }
    extra.push({ label: `v(${m.name.toLowerCase()})`, unit: 'V', real, ...(imag ? { imag } : {}) });
  }
  return extra.length ? { ...res, vectors: [...res.vectors, ...extra] } : res;
}

const last = (arr, imag) => {
  const i = arr.length - 1;
  return imag ? Math.hypot(arr[i], imag[i]) : arr[i];
};

/** The value a meter shows on the canvas: { value, unit } from the last point of the result, or null. */
export function meterReading(res, meter) {
  if (!res || !meter) return null;
  const diff = () => {
    const a = nodeSeries(res, meter.nodes[0]);
    const b = nodeSeries(res, meter.nodes[1]);
    if (!a || !b) return null;
    const va = a.re ? last(a.re, a.im) : 0;
    const vb = b.re ? last(b.re, b.im) : 0;
    return va - vb;
  };
  if (meter.kind === 'probe') {
    const d = diff();
    return d === null ? null : { value: d, unit: 'V' };
  }
  if (meter.kind === 'ammeter') {
    const v = vecOf(res, `i(${meter.source})`);
    return v && v.real.length ? { value: last(v.real, v.imag), unit: 'A' } : null;
  }
  if (meter.kind === 'ohm') {
    const d = diff();
    return d === null ? null : { value: d / meter.amps, unit: 'Ω' };
  }
  return null;
}
