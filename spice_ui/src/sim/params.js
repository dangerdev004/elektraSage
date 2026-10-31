// Editable parameters per part type, and the "+/-" stepping used by the Edit dialogs.
//
// Direction of this project (differs from CircuitJS1): every transistor, diode and op amp is a
// *generic SPICE model*. A semiconductor parameter that is left empty is simply not written to the
// `.model` card, so ngspice uses its own built-in default, like other SPICE editors do. Op amps have
// no SPICE default, so they carry explicit default values (shown filled in the dialog).

import { parseValue, parseSourceText } from './units.js';

const f = (key, label, unit, extra = {}) => ({ key, label, unit, ...extra });

// ---- semiconductor parameters (empty = SPICE default) --------------------------------------
const DIODE = [
  f('IS', 'Saturation current (IS)', 'A'),
  f('N', 'Emission coefficient (N)', ''),
  f('RS', 'Series resistance (RS)', 'Ω'),
  f('CJO', 'Zero-bias capacitance (CJO)', 'F'),
  f('TT', 'Transit time (TT)', 's'),
];
const BJT = [
  f('BF', 'Forward beta (BF)', ''),
  f('BR', 'Reverse beta (BR)', ''),
  f('IS', 'Saturation current (IS)', 'A'),
  f('VAF', 'Early voltage (VAF)', 'V'),
  f('RB', 'Base resistance (RB)', 'Ω'),
  f('CJE', 'B-E capacitance (CJE)', 'F'),
  f('CJC', 'B-C capacitance (CJC)', 'F'),
  f('TF', 'Forward transit time (TF)', 's'),
];
const MOS = [
  f('VTO', 'Threshold voltage (VTO)', 'V'),
  f('KP', 'Transconductance (KP)', 'A/V²'),
  f('LAMBDA', 'Channel-length modulation (LAMBDA)', '1/V'),
  f('W', 'Channel width (W)', 'm', { inst: true }),
  f('L', 'Channel length (L)', 'm', { inst: true }),
];

// ---- op amps (explicit defaults) -----------------------------------------------------------
export const OPAMP_IDEAL = [
  f('vmax', 'Max Output (V)', 'V', { def: '15' }),
  f('vmin', 'Min Output (V)', 'V', { def: '-15' }),
  f('gain', 'Gain', '', { def: '100k' }),
];

// "Generic" is this project's own default; "LM741" uses the slew rate and current limit shown in the
// CircuitJS1 dialog you sent. These are NOT datasheet-verified; edit them for the part you use.
export const OPAMP_PRESETS = {
  Generic: { gain: '200k', gbw: '1Meg', slew: '0.5', imax: '25m', rout: '75' },
  LM741: { gain: '200k', gbw: '1Meg', slew: '600m', imax: '23.1m', rout: '75' },
};
export const OPAMP_REAL = [
  f('preset', 'Model', '', { kind: 'select', options: Object.keys(OPAMP_PRESETS), def: 'Generic' }),
  f('swap', 'Swap Inputs', '', { kind: 'check' }),
  f('slew', 'Slew Rate (V/µs)', 'V/µs', { def: '0.5' }),
  f('imax', 'Output Current Limit (A)', 'A', { def: '25m' }),
  f('gain', 'Open-loop Gain', '', { def: '200k' }),
  f('gbw', 'Gain-Bandwidth Product (Hz)', 'Hz', { def: '1Meg' }),
  f('rout', 'Output Resistance (Ω)', 'Ω', { def: '75' }),
  f('vmax', 'Max Output (V)', 'V', { def: '15' }),
  f('vmin', 'Min Output (V)', 'V', { def: '-15' }),
];

// ---- logic gates (XSPICE d_* models; empty = default) ---------------------------------------
const GATE = [
  f('vhigh', 'Logic high level (V)', 'V', { def: '5' }),
  f('delay', 'Propagation delay (s)', 's'),
];
const GATE_NOTE = 'Empty delay = XSPICE default (1 ns). Input thresholds are 30% / 70% of the logic high level.';
// Flip-flops and latches: XSPICE code model, terminal roles in canvas terminal order.
//   'i' required input, 'o' optional input (left unconnected => NULL), 'q' output.
// `order` lists the terminal indexes in the order the model's ports are written.
export const SEQ_TYPES = {
  DFlipFlopElm: { code: 'd_dff', roles: 'iiooqq', order: [0, 1, 2, 3, 4, 5], ff: true },
  JKFlipFlopElm: { code: 'd_jkff', roles: 'iiiooqq', order: [0, 1, 2, 3, 4, 5, 6], ff: true },
  TFlipFlopElm: { code: 'd_tff', roles: 'iiooqq', order: [0, 1, 2, 3, 4, 5], ff: true },
  LatchElm: { code: 'd_dlatch', roles: 'iiooqq', order: [0, 1, 2, 3, 4, 5], ff: false },
  SRLatchElm: { code: 'd_srlatch', roles: 'iiqq', order: [0, 1, -1, -1, -1, 2, 3], ff: false }, // enable, set, reset are NULL
};
const SEQ_FF = [
  f('vhigh', 'Logic high level (V)', 'V', { def: '5' }),
  f('delay', 'Clock-to-output delay (s)', 's'),
  f('ic', 'Initial state (0 or 1)', ''),
];
const SEQ_LATCH = [f('vhigh', 'Logic high level (V)', 'V', { def: '5' }), f('ic', 'Initial state (0 or 1)', '')];
const SEQ_NOTE = 'Empty = XSPICE default (initial state 0, delay 1 ns). Unconnected SET/RST and unused outputs are left open. SET and RST are active high.';

export const GATE_TYPES = {
  AndGateElm: ['d_and', 2], NandGateElm: ['d_nand', 2], OrGateElm: ['d_or', 2], NorGateElm: ['d_nor', 2],
  XorGateElm: ['d_xor', 2], XnorGateElm: ['d_xnor', 2], InverterElm: ['d_inverter', 1], BufferElm: ['d_buffer', 1],
};

// ---- basic parts: the main value (stepper) plus extra fields ------------------------------
// valueUnit is appended to a typed number so the label on the canvas reads "1kΩ", "10uF", "5V".
const SOURCE_FIELDS = [
  f('amp', 'Amplitude (V)', 'V', { def: '5' }),
  f('freq', 'Frequency (Hz)', 'Hz', { def: '40' }),
  f('offset', 'DC offset (V)', 'V'),
  f('phase', 'Phase (degrees)', '°'),
];
const sourceInitial = (el) => {
  const t = parseSourceText(el.value);
  return { amp: Number.isFinite(t.amp) ? formatSI(t.amp) : '5', freq: t.freq !== undefined ? formatSI(t.freq) : '40' };
};
const sourceLabel = (v) => `${withUnit(v.amp, 'V')}, ${withUnit(v.freq, 'Hz')}`;

const BASIC = {
  ResistorElm: { title: 'Resistor', valueLabel: 'Resistance (Ω)', valueUnit: 'Ω', valueDef: '1k', fields: [] },
  CapacitorElm: { title: 'Capacitor', valueLabel: 'Capacitance (F)', valueUnit: 'F', valueDef: '10u', fields: [] },
  PolarCapacitorElm: { title: 'Capacitor (polarized)', valueLabel: 'Capacitance (F)', valueUnit: 'F', valueDef: '10u', fields: [], note: 'Simulated as an ordinary capacitor.' },
  InductorElm: { title: 'Inductor', valueLabel: 'Inductance (H)', valueUnit: 'H', valueDef: '1', fields: [] },
  DCVoltageElm: { title: 'DC Voltage Source', valueLabel: 'Voltage (V)', valueUnit: 'V', valueDef: '5', fields: [] },
  RailElm: { title: 'Voltage Rail', valueLabel: 'Voltage (V)', valueUnit: 'V', valueDef: '5', fields: [] },
  CurrentElm: { title: 'Current Source', valueLabel: 'Current (A)', valueUnit: 'A', valueDef: '10m', fields: [] },
  ACVoltageElm: { title: 'A/C Voltage Source', fields: SOURCE_FIELDS, initial: sourceInitial, compose: sourceLabel, note: 'Transient: sine. AC analysis: 1 V stimulus. Empty offset / phase = 0.' },
  ACRailElm: { title: 'A/C Rail', fields: SOURCE_FIELDS, initial: sourceInitial, compose: sourceLabel, note: 'Transient: sine. AC analysis: 1 V stimulus. Empty offset / phase = 0.' },
  ClockElm: {
    title: 'Clock',
    fields: [f('amp', 'High level (V)', 'V', { def: '5' }), f('freq', 'Frequency (Hz)', 'Hz', { def: '1k' }), f('duty', 'Duty cycle (%)', '%', { def: '50' })],
    initial: (el) => { const t = parseSourceText(el.value); return { amp: Number.isFinite(t.amp) ? formatSI(t.amp) : '5', freq: t.freq !== undefined ? formatSI(t.freq) : '1k', duty: '50' }; },
    compose: sourceLabel,
    note: 'Square wave from 0 V to the high level.',
  },
  LogicInputElm: {
    title: 'Logic Input',
    fields: [f('high', 'Output HIGH', '', { kind: 'check' }), f('vhigh', 'Logic high level (V)', 'V', { def: '5' })],
    note: 'Click the part on the canvas to toggle 0 / 1. Drives its net with 0 V or the logic high level (empty = 5 V).',
  },
  LogicOutputElm: {
    title: 'Logic Output',
    fields: [f('vhigh', 'Logic high level (V)', 'V', { def: '5' })],
    note: 'Lit and shown as 1 when the net is above half the logic high level in the last result; "?" when there is no current result.',
  },
  SwitchElm: { title: 'Switch', fields: [f('open', 'Open', '', { kind: 'check' })], note: 'Closed = 1 mΩ, open = 1 GΩ. Click the switch on the canvas to toggle it.' },
  PushSwitchElm: { title: 'Push Switch', fields: [f('open', 'Open', '', { kind: 'check' })], note: 'No momentary action in a batch run: this is a switch with a fixed state. Click it to toggle.' },
};

/** Append `unit` to a plain number with an optional SI prefix ("1k" -> "1kΩ"); leave anything else alone. */
export function withUnit(text, unit) {
  const t = String(text ?? '').trim();
  return unit && /^[+-]?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?\s*(meg|[tgkmunpfTGkMunpf])?$/i.test(t) ? `${t}${unit}` : t;
}

export const PART_PARAMS = {
  ...BASIC,
  DiodeElm: { title: 'Diode', modelType: 'D', fields: DIODE, note: 'Empty = SPICE default.' },
  LEDElm: { title: 'LED', modelType: 'D', fields: DIODE, note: 'Empty = this app\'s generic LED (IS=1e-18, N=1.9, RS=2).' },
  ZenerElm: {
    title: 'Zener Diode', modelType: 'D', valueLabel: 'Breakdown voltage (V)',
    fields: [...DIODE, f('IBV', 'Current at breakdown (IBV)', 'A')], note: 'Empty = SPICE default (breakdown from the voltage above, IBV=5m).',
  },
  NTransistorElm: { title: 'NPN Transistor', modelType: 'NPN', fields: BJT, note: 'Empty = SPICE default.' },
  PTransistorElm: { title: 'PNP Transistor', modelType: 'PNP', fields: BJT, note: 'Empty = SPICE default.' },
  NMosfetElm: { title: 'N-MOSFET (level 1)', modelType: 'NMOS', fields: MOS, note: 'Empty = SPICE default. The default threshold is 0 V, so set VTO for an enhancement device.' },
  PMosfetElm: { title: 'P-MOSFET (level 1)', modelType: 'PMOS', fields: MOS, note: 'Empty = SPICE default. Set VTO (negative) for an enhancement device.' },
  ...Object.fromEntries(Object.keys({ AndGateElm: 1, NandGateElm: 1, OrGateElm: 1, NorGateElm: 1, XorGateElm: 1, XnorGateElm: 1, InverterElm: 1, BufferElm: 1 })
    .map((k) => [k, { title: k.replace('Elm', '').replace(/([a-z])([A-Z])/g, '$1 $2'), fields: GATE, note: GATE_NOTE, gate: true }])),
  DFlipFlopElm: { title: 'D Flip-Flop', fields: SEQ_FF, note: SEQ_NOTE, gate: true },
  JKFlipFlopElm: { title: 'JK Flip-Flop', fields: SEQ_FF, note: SEQ_NOTE, gate: true },
  TFlipFlopElm: { title: 'T Flip-Flop', fields: SEQ_FF, note: SEQ_NOTE, gate: true },
  LatchElm: { title: 'D Latch', fields: SEQ_LATCH, note: SEQ_NOTE, gate: true },
  SRLatchElm: { title: 'SR Latch', fields: SEQ_LATCH, note: 'Enable, SET and RESET are left open. Empty = initial state 0.', gate: true },
  OpAmpElm: { title: 'Op-amp (ideal)', fields: OPAMP_IDEAL, opamp: 'ideal' },
  OpAmpSwapElm: { title: 'Op-amp (ideal)', fields: OPAMP_IDEAL, opamp: 'ideal' },
  OpAmpRealElm: { title: 'Op-amp (real)', fields: OPAMP_REAL, opamp: 'real' },
};

/** Effective op-amp parameter text: the part's own value, else the field default (or preset value). */
export function opampParam(el, key) {
  const p = el.params ?? {};
  if (p[key] !== undefined && String(p[key]).trim() !== '') return String(p[key]);
  if (el.type === 'OpAmpRealElm') {
    const preset = OPAMP_PRESETS[p.preset ?? 'Generic'] ?? OPAMP_PRESETS.Generic;
    if (preset[key] !== undefined) return preset[key];
  }
  const def = (el.type === 'OpAmpRealElm' ? OPAMP_REAL : OPAMP_IDEAL).find((x) => x.key === key)?.def;
  return def ?? '';
}

// ---- engineering-notation text and +/- stepping --------------------------------------------
const SI_STEPS = [[1e12, 'T'], [1e9, 'G'], [1e6, 'Meg'], [1e3, 'k'], [1, ''], [1e-3, 'm'], [1e-6, 'u'], [1e-9, 'n'], [1e-12, 'p'], [1e-15, 'f']];

/** 0.0231 -> "23.1m", 100000 -> "100k", 1e6 -> "1Meg", 0 -> "0". */
export function formatSI(x) {
  if (!Number.isFinite(x)) return '';
  if (x === 0) return '0';
  const a = Math.abs(x);
  const [scale, suffix] = SI_STEPS.find(([s]) => a >= s * 0.9995) ?? SI_STEPS[SI_STEPS.length - 1];
  const m = Number((x / scale).toPrecision(3));
  return `${m}${suffix}`;
}

const MANT = [1, 2, 5, 10];
/** Next value in a 1-2-5 series above (dir > 0) or below (dir < 0) `v`. */
export function stepValue(v, dir) {
  if (!Number.isFinite(v)) return NaN;
  if (v === 0) return dir > 0 ? 1 : -1;
  const sign = Math.sign(v);
  const a = Math.abs(v);
  const up = dir * sign > 0; // does the magnitude grow?
  const e = Math.floor(Math.log10(a) + 1e-12);
  const m = a / 10 ** e;
  let nm;
  if (up) nm = MANT.find((x) => x > m * (1 + 1e-9));
  else nm = [...MANT].reverse().find((x) => x < m * (1 - 1e-9)) ?? 0.5;
  const out = sign * nm * 10 ** e;
  return Number(out.toPrecision(12));
}

/** Click on "+" (dir 1) or "-" (dir -1): text in -> text out. `fallback` is used when the field is empty. */
export function stepText(text, dir, fallback = '1', unit = '') {
  const raw = String(text ?? '').trim();
  const v = parseValue(raw === '' ? fallback : raw, unit);
  if (!Number.isFinite(v)) return raw;
  return formatSI(stepValue(v, dir));
}
