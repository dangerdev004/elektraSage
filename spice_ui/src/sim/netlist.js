// Turns the canvas circuit into a SPICE deck. Pure: it takes the element list and a function
// that returns each element's terminal points, so it runs in Node tests as well as in the app.
//
// Connectivity rule (same as drawing it by hand): terminals that sit on the SAME grid point are
// connected, and a wire connects its two end points. A wire passing over a part's pin without
// ending there does not connect.

import { getDef } from '../canvas/parts.js';
import { parseValue, parseSourceText, num } from './units.js';
import { buildCommand, validateParams } from './analysis.js';
import { PART_PARAMS, GATE_TYPES, SEQ_TYPES, opampParam } from './params.js';
import { checkDirectives } from './directives.js';

const ANNOTATION = new Set(['TextElm', 'BoxElm', 'LineElm']);


const keyOf = (p) => `${Math.round(p.x)},${Math.round(p.y)}`;

/**
 * Group terminals into electrical nodes.
 * Returns { nodeOfTerminal(el, i), keysOf(el), names, hasGround }.
 * Node "0" is ground (every Ground part is the same node); the others are n1, n2, ... in the
 * order they first appear.
 */
export function analyzeNodes(elements, terminalsOf) {
  const parent = new Map();
  const find = (k) => {
    if (!parent.has(k)) parent.set(k, k);
    let r = k;
    while (parent.get(r) !== r) r = parent.get(r);
    for (let c = k; parent.get(c) !== r;) { const n = parent.get(c); parent.set(c, r); c = n; }
    return r;
  };
  const union = (a, b) => {
    const ra = find(a);
    const rb = find(b);
    if (ra !== rb) parent.set(ra, rb);
  };

  const keys = new Map();
  const labelProblems = [];
  const labelOf = new Map(); // union key -> label name
  let hasGround = false;
  for (const el of elements) {
    const ks = terminalsOf(el).map(keyOf);
    keys.set(el.id, ks);
    ks.forEach(find);
    if (el.type === 'WireElm') union(ks[0], ks[1]);
    if (el.type === 'GroundElm') { hasGround = true; union(ks[0], 'GND'); }
    if (el.type === 'LabeledNodeElm' || el.type === 'PortElm') {
      // Same name = same net, as in SPICE (names are case-insensitive). 0 and gnd mean ground.
      const nm = String(el.value ?? '').trim().toLowerCase();
      if (!nm) labelProblems.push('Labeled Node: the label has no name (double-click it to type one).');
      else if (!/^[a-z_][\w.]*$|^0$/.test(nm)) labelProblems.push(`Labeled Node: "${el.value}" is not a usable net name (letters, digits, _ and . only, not starting with a digit).`);
      else if (/^(n\d+|d_.*|z_.*)$/.test(nm)) labelProblems.push(`Labeled Node: "${nm}" is reserved for automatic node names; choose another name.`);
      else if (nm === '0' || nm === 'gnd') { hasGround = true; union(ks[0], 'GND'); }
      else { union(ks[0], `L:${nm}`); labelOf.set(`L:${nm}`, nm); }
    }
  }

  const names = new Map();
  let n = 0;
  const gndRoot = hasGround ? find('GND') : null;
  // each net may carry at most one label name; a wire joining two different names is reported
  const rootLabel = new Map();
  for (const [k, nm] of labelOf) {
    const r = find(k);
    if (r === gndRoot) { labelProblems.push(`Labeled Node: "${nm}" is joined to ground.`); continue; }
    if (rootLabel.has(r) && rootLabel.get(r) !== nm) labelProblems.push(`Labeled Node: "${rootLabel.get(r)}" and "${nm}" are on the same net; give it one name.`);
    else rootLabel.set(r, nm);
  }
  for (const el of elements) {
    for (const k of keys.get(el.id)) {
      const r = find(k);
      if (names.has(r)) continue;
      names.set(r, r === gndRoot ? '0' : rootLabel.get(r) ?? `n${++n}`);
    }
  }

  return {
    hasGround,
    keysOf: (el) => keys.get(el.id),
    nodeOfTerminal: (el, i) => names.get(find(keys.get(el.id)[i])),
    nodeNames: [...names.values()],
    labelProblems: [...new Set(labelProblems)],
  };
}

/**
 * Build the deck.
 * Returns { ok, text, errors, warnings, refs, sources } — `text` is only meaningful when ok.
 *   refs: element id -> SPICE reference (R1, C2, ...)   sources: names of voltage sources
 *   libs: model-library file names the deck needs (the server adds the .include lines)
 * `library` = the model list from the server: [{ kind, name, type, file }]
 */
export function buildCircuitNetlist({ elements, terminalsOf, title = 'circuit', analysis, library = [], pack = null }) {
  const errors = [];
  const warnings = [];
  const cards = [];
  const modelCards = new Map(); // model name -> .model card
  const cardNames = new Map(); // 'TYPE|params' -> model name (identical parameter sets share one card)
  const refs = new Map();
  const sources = [];
  const counters = {};
  const pins = new Map();
  const unsupported = new Map();
  const libs = new Set(); // library files the circuit needs

  const parts = elements.filter((e) => e.type !== 'WireElm' && e.type !== 'GroundElm' && e.type !== 'LabeledNodeElm' && e.type !== 'PortElm' && !ANNOTATION.has(e.type));
  if (!elements.length) errors.push('The circuit is empty.');

  const nodes = analyzeNodes(elements, terminalsOf);
  errors.push(...nodes.labelProblems);
  if (elements.length && !nodes.hasGround && !pack) {
    errors.push('There is no ground. Add one with Draw > Inputs and Sources > Add Ground.');
  }

  const ref = (el, prefix) => {
    counters[prefix] = (counters[prefix] ?? 0) + 1;
    const r = `${prefix}${counters[prefix]}`;
    refs.set(el.id, r);
    return r;
  };
  const use = (...ns) => ns.forEach((x) => { if (x !== '0') pins.set(x, (pins.get(x) ?? 0) + 1); });


  // Library model chosen for a part (el.model), or null for the built-in default.
  const MODEL_TYPE = { DiodeElm: 'D', LEDElm: 'D', ZenerElm: 'D', NTransistorElm: 'NPN', PTransistorElm: 'PNP', NMosfetElm: 'NMOS', PMosfetElm: 'PMOS' };
  const libraryModel = (el, label) => {
    if (!el.model) return null;
    const want = MODEL_TYPE[el.type];
    const entry = library.find((m) => m.kind === 'model' && m.name === el.model);
    if (!entry) {
      errors.push(`${label}: model "${el.model}" was not found in the model library (is the server running, and is the file still in the models folder?).`);
      return undefined;
    }
    if (entry.type !== want) {
      errors.push(`${label}: model "${el.model}" is a ${entry.type} model, but this part needs a ${want} model.`);
      return undefined;
    }
    if (!/^[\w.+\-#$%@!]+$/.test(entry.name)) {
      errors.push(`${label}: model name "${entry.name}" has characters this app does not pass to SPICE.`);
      return undefined;
    }
    libs.add(entry.file);
    return entry.name;
  };

  // ---- generic models: only parameters the user set are written; the rest is SPICE's default ----
  const specifiedParams = (el, label) => {
    const model = [];
    const inst = [];
    for (const fld of PART_PARAMS[el.type]?.fields ?? []) {
      const raw = el.params?.[fld.key];
      if (raw === undefined || String(raw).trim() === '') continue;
      const v = parseValue(raw, '');
      if (!Number.isFinite(v)) { errors.push(`${label}: ${fld.key} is not a number ("${raw}").`); return null; }
      (fld.inst ? inst : model).push([fld.key, num(v)]);
    }
    return { model, inst };
  };
  /** -> { name, inst: 'W=.. L=..' } or undefined after pushing an error. */
  const genericModel = (el, label, type, baseName, base = {}) => {
    const p = specifiedParams(el, label);
    if (!p) return undefined;
    const merged = new Map(Object.entries(base));
    const baseBody = [...merged].map(([k, v]) => `${k}=${v}`).join(' ');
    for (const [k, v] of p.model) merged.set(k, v);
    const body = [...merged].map(([k, v]) => `${k}=${v}`).join(' ');
    const key = `${type}|${baseName}|${body}`;
    if (!cardNames.has(key)) {
      const name = body === baseBody ? baseName : `${baseName}_${cardNames.size + 1}`;
      cardNames.set(key, name);
      modelCards.set(name, `.model ${name} ${type}${body ? `(${body})` : ''}`);
    }
    return { name: cardNames.get(key), inst: p.inst.map(([k, v]) => `${k}=${v}`).join(' ') };
  };
  // numeric field from the part's params, else `fallback` (used by sources whose value label is the old format)
  const fieldNum = (el, key, fallback, unit) => {
    const raw = el.params?.[key];
    return raw === undefined || String(raw).trim() === '' ? fallback : parseValue(raw, unit);
  };
  const opNumber = (el, key, label, what, ok = (v) => v > 0) => {
    const v = parseValue(opampParam(el, key), '');
    if (!Number.isFinite(v) || !ok(v)) { errors.push(`${label}: ${what} (got "${opampParam(el, key)}").`); return undefined; }
    return v;
  };

  const directiveLines = []; // lines from SPICE Directive parts
  const gates = []; // logic gates and flip-flops, wired up with bridges after the loop
  const openNets = new Set(); // nets of unused optional pins (SET, RST, unused Q-bar): no warning for those
  const gateModels = new Map(); // 'd_and|delay' -> model name
  for (const el of parts) {
    const def = getDef(el.type);
    const text = el.value ?? def.value;
    const t = terminalsOf(el).map((_, i) => nodes.nodeOfTerminal(el, i));
    const bad = (what, shown) => errors.push(`${def.label}: ${what}${shown !== undefined ? ` ("${shown}")` : ''}.`);
    const two = (prefix, unit, label, allowZero = false) => {
      const v = parseValue(text, unit);
      if (!Number.isFinite(v) || (allowZero ? v < 0 : v <= 0)) return bad(`${label} must be a positive number`, text);
      use(t[0], t[1]);
      cards.push(`${ref(el, prefix)} ${t[0]} ${t[1]} ${num(v)}`);
    };

    switch (el.type) {
      case 'ResistorElm': two('R', '', 'resistance'); break;
      case 'CapacitorElm':
      case 'PolarCapacitorElm': two('C', 'F', 'capacitance'); break;
      case 'InductorElm': two('L', 'H', 'inductance'); break;
      case 'SwitchElm':
      case 'PushSwitchElm': {
        const open = String(el.params?.open) === 'true';
        use(t[0], t[1]);
        cards.push(`${ref(el, 'R')} ${t[0]} ${t[1]} ${open ? '1e9' : '1m'}`);
        break;
      }

      case 'DCVoltageElm':
      case 'RailElm': {
        const v = parseValue(text, 'V');
        if (!Number.isFinite(v)) { bad('voltage is not a number', text); break; }
        const neg = el.type === 'RailElm' ? '0' : t[1];
        use(t[0], neg);
        const r = ref(el, 'V');
        sources.push(r);
        cards.push(`${r} ${t[0]} ${neg} DC ${num(v)}`);
        break;
      }
      case 'ACVoltageElm':
      case 'ACRailElm': {
        const parsed = parseSourceText(text);
        const amp = fieldNum(el, 'amp', parsed.amp, 'V');
        const freq = fieldNum(el, 'freq', parsed.freq, 'Hz');
        const offset = fieldNum(el, 'offset', 0, 'V');
        const phase = fieldNum(el, 'phase', 0, '');
        if (!Number.isFinite(amp)) { bad('amplitude is not a number', el.params?.amp ?? text); break; }
        if (freq !== undefined && !(freq > 0)) { bad('frequency must be greater than 0', el.params?.freq ?? text); break; }
        if (!Number.isFinite(offset)) { bad('DC offset is not a number', el.params?.offset); break; }
        if (!Number.isFinite(phase)) { bad('phase is not a number', el.params?.phase); break; }
        const neg = el.type === 'ACRailElm' ? '0' : t[1];
        use(t[0], neg);
        const r = ref(el, 'V');
        sources.push(r);
        // SIN for transient; AC 1 = unit stimulus, so an AC sweep reads directly as gain.
        cards.push(`${r} ${t[0]} ${neg} SIN(${num(offset)} ${num(amp)} ${num(freq ?? 40)}${phase ? ` 0 0 ${num(phase)}` : ''}) AC 1`);
        break;
      }
      case 'DirectiveElm': {
        const { lines, problems } = checkDirectives(text);
        problems.forEach((p) => errors.push(`SPICE Directive: ${p}`));
        directiveLines.push(...lines);
        break;
      }
      case 'LogicInputElm': {
        const vh = parseValue(el.params?.vhigh?.trim() ? el.params.vhigh : '5', 'V');
        if (!(vh > 0)) { bad('logic high level must be a positive number', el.params?.vhigh); break; }
        use(t[0]);
        const r = ref(el, 'V');
        sources.push(r);
        cards.push(`${r} ${t[0]} 0 DC ${String(el.params?.high) === 'true' ? num(vh) : '0'}`);
        break;
      }
      case 'LogicOutputElm': { // a lamp: reads its net, adds nothing to the circuit
        const vh = parseValue(el.params?.vhigh?.trim() ? el.params.vhigh : '5', 'V');
        if (!(vh > 0)) { bad('logic high level must be a positive number', el.params?.vhigh); break; }
        use(t[0]);
        break;
      }
      case 'ClockElm': {
        // square wave 0..amp at the given frequency (default 1 kHz) and duty cycle (default 50 %)
        const parsed = parseSourceText(text);
        const amp = fieldNum(el, 'amp', parsed.amp, 'V');
        const f = fieldNum(el, 'freq', parsed.freq ?? 1000, 'Hz');
        const duty = fieldNum(el, 'duty', 50, '');
        if (!Number.isFinite(amp)) { bad('high level is not a number', el.params?.amp ?? text); break; }
        if (!(f > 0)) { bad('frequency must be greater than 0', el.params?.freq ?? text); break; }
        if (!(duty >= 1 && duty <= 99)) { bad('duty cycle must be between 1 and 99 %', el.params?.duty); break; }
        use(t[0]);
        const r = ref(el, 'V');
        sources.push(r);
        const per = 1 / f;
        const edge = per / 1000;
        cards.push(`${r} ${t[0]} 0 PULSE(0 ${num(amp)} 0 ${num(edge)} ${num(edge)} ${num(per * duty / 100 - edge)} ${num(per)})`);
        break;
      }
      case 'AndGateElm': case 'NandGateElm': case 'OrGateElm': case 'NorGateElm':
      case 'XorGateElm': case 'XnorGateElm': case 'InverterElm': case 'BufferElm': {
        const [code, nIn] = GATE_TYPES[el.type];
        const vhigh = parseValue(el.params?.vhigh?.trim() ? el.params.vhigh : '5', 'V');
        if (!(vhigh > 0)) { bad('logic high level must be a positive number', el.params?.vhigh); break; }
        let delay = '';
        if (String(el.params?.delay ?? '').trim() !== '') {
          const d = parseValue(el.params.delay, 's');
          if (!Number.isFinite(d) || d < 0) { bad('propagation delay must be zero or positive', el.params.delay); break; }
          delay = `rise_delay=${num(d)} fall_delay=${num(d)}`;
        }
        const key = `${code}|${delay}`;
        if (!gateModels.has(key)) {
          const name = `G_${code.slice(2).toUpperCase()}${delay ? `_${gateModels.size + 1}` : ''}`;
          gateModels.set(key, name);
          modelCards.set(name, `.model ${name} ${code}${delay ? `(${delay})` : ''}`);
        }
        const ins = t.slice(0, nIn);
        const out = t[nIn];
        use(...ins, out);
        gates.push({ el, ref: ref(el, 'A'), model: gateModels.get(key), vhigh, vec: nIn > 1 ? nIn : 0, ports: [...ins.map((net) => ({ net, dir: 'in' })), { net: out, dir: 'out' }] });
        break;
      }

      // Flip-flops and latches (XSPICE d_dff, d_jkff, d_tff, d_dlatch, d_srlatch).
      case 'DFlipFlopElm': case 'JKFlipFlopElm': case 'TFlipFlopElm': case 'LatchElm': case 'SRLatchElm': {
        const spec = SEQ_TYPES[el.type];
        const vhigh = parseValue(el.params?.vhigh?.trim() ? el.params.vhigh : '5', 'V');
        if (!(vhigh > 0)) { bad('logic high level must be a positive number', el.params?.vhigh); break; }
        const opts = [];
        if (String(el.params?.delay ?? '').trim() !== '') {
          const d = parseValue(el.params.delay, 's');
          if (!Number.isFinite(d) || d < 0) { bad('clock-to-output delay must be zero or positive', el.params.delay); break; }
          opts.push(`clk_delay=${num(d)}`);
        }
        if (String(el.params?.ic ?? '').trim() !== '') {
          const ic = String(el.params.ic).trim();
          if (ic !== '0' && ic !== '1') { bad('initial state must be 0 or 1', ic); break; }
          opts.push(`ic=${ic}`);
        }
        const body = opts.join(' ');
        const key = `${spec.code}|${body}`;
        if (!gateModels.has(key)) {
          const name = `F_${spec.code.slice(2).toUpperCase()}${body ? `_${gateModels.size + 1}` : ''}`;
          gateModels.set(key, name);
          modelCards.set(name, `.model ${name} ${spec.code}${body ? `(${body})` : ''}`);
        }
        use(...t);
        const ports = spec.order.map((idx) => {
          if (idx < 0) return { dir: 'null' };
          const role = spec.roles[idx];
          return { net: t[idx], dir: role === 'q' ? 'out' : 'in', opt: role === 'o' || role === 'q', idx };
        });
        gates.push({ el, ref: ref(el, 'A'), model: gateModels.get(key), vhigh, vec: 0, ports });
        break;
      }

      // A .subckt from the model library: pins come from its definition, in that order.
      case 'SubcktElm': {
        const entry = el.model ? library.find((m) => m.kind === 'subckt' && m.name === el.model) : null;
        if (!el.model) { bad('no subcircuit chosen (double-click the block to pick one from the library)'); break; }
        if (!entry) { bad(`subcircuit "${el.model}" was not found in the model library (is the server running, and is the file still in the models folder?)`); break; }
        if (!/^[\w.+\-#$%@!]+$/.test(entry.name)) { bad(`subcircuit name "${entry.name}" has characters this app does not pass to SPICE`); break; }
        if (t.length !== entry.pins.length) { bad(`the block has ${t.length} pins but ${entry.name} now has ${entry.pins.length}; double-click the block and pick it again`); break; }
        const given = [];
        let okp = true;
        for (const pd of entry.params ?? []) {
          const raw = el.params?.[pd.name];
          if (raw === undefined || String(raw).trim() === '') continue;
          const v = parseValue(raw, '');
          if (!Number.isFinite(v)) { bad(`parameter ${pd.name} is not a number`, raw); okp = false; break; }
          given.push(`${pd.name}=${num(v)}`);
        }
        if (!okp) break;
        use(...t);
        libs.add(entry.file);
        cards.push(`${ref(el, 'X')} ${t.join(' ')} ${entry.name}${given.length ? ` ${given.join(' ')}` : ''}`);
        break;
      }

      case 'CurrentElm': {
        const v = parseValue(text, 'A');
        if (!Number.isFinite(v)) { bad('current is not a number', text); break; }
        use(t[0], t[1]);
        cards.push(`${ref(el, 'I')} ${t[0]} ${t[1]} DC ${num(v)}`);
        break;
      }

      case 'DiodeElm':
      case 'LEDElm': {
        const led = el.type === 'LEDElm';
        let name = libraryModel(el, def.label);
        if (name === undefined) break;
        if (!name) {
          const g = genericModel(el, def.label, 'D', led ? 'DLED' : 'DDEFAULT', led ? { IS: '1e-18', N: '1.9', RS: '2' } : {});
          if (!g) break;
          name = g.name;
        }
        use(t[0], t[1]);
        cards.push(`${ref(el, 'D')} ${t[0]} ${t[1]} ${name}`);
        break;
      }
      case 'ZenerElm': {
        let name = libraryModel(el, def.label);
        if (name === undefined) break;
        if (!name) {
          const bv = parseValue(text, 'V');
          if (!(bv > 0)) { bad('breakdown voltage must be positive', text); break; }
          const g = genericModel(el, def.label, 'D', `DZ${String(num(bv)).replace(/[^0-9a-z]/gi, '_')}`, { BV: num(bv), IBV: '5m' });
          if (!g) break;
          name = g.name;
        }
        use(t[0], t[1]);
        cards.push(`${ref(el, 'D')} ${t[0]} ${t[1]} ${name}`);
        break;
      }

      // terminal order from the symbol: [base, collector, emitter] / [gate, drain, source]
      case 'NTransistorElm':
      case 'PTransistorElm': {
        const npn = el.type === 'NTransistorElm';
        let name = libraryModel(el, def.label);
        if (name === undefined) break;
        if (!name) {
          const g = genericModel(el, def.label, npn ? 'NPN' : 'PNP', npn ? 'QNPN' : 'QPNP');
          if (!g) break;
          name = g.name;
        }
        use(t[0], t[1], t[2]);
        cards.push(`${ref(el, 'Q')} ${t[1]} ${t[0]} ${t[2]} ${name}`);
        break;
      }
      case 'NMosfetElm':
      case 'PMosfetElm': {
        const n = el.type === 'NMosfetElm';
        let name = libraryModel(el, def.label);
        let inst = '';
        if (name === undefined) break;
        if (!name) {
          const g = genericModel(el, def.label, n ? 'NMOS' : 'PMOS', n ? 'NMOD' : 'PMOD', { LEVEL: '1' });
          if (!g) break;
          name = g.name;
          inst = g.inst ? ` ${g.inst}` : '';
        }
        use(t[0], t[1], t[2]);
        cards.push(`${ref(el, 'M')} ${t[1]} ${t[0]} ${t[2]} ${t[2]} ${name}${inst}`);
        break;
      }

      // Ideal op amp: output = clamp(gain * (v+ - v-)) between the min/max output, smoothed with tanh
      // so it stays differentiable for the solver. t = [-, +, out]; the "swap" part has them reversed.
      case 'OpAmpElm':
      case 'OpAmpSwapElm': {
        const label = def.label;
        const vmax = opNumber(el, 'vmax', label, 'Max Output must be a number', Number.isFinite);
        const vmin = opNumber(el, 'vmin', label, 'Min Output must be a number', Number.isFinite);
        const gain = opNumber(el, 'gain', label, 'Gain must be a positive number');
        if (vmax === undefined || vmin === undefined || gain === undefined) break;
        if (!(vmax > vmin)) { errors.push(`${label}: Max Output must be greater than Min Output.`); break; }
        const swap = el.type === 'OpAmpSwapElm';
        const inp = swap ? t[0] : t[1];
        const inn = swap ? t[1] : t[0];
        use(inp, inn, t[2]);
        const mid = (vmax + vmin) / 2;
        const half = (vmax - vmin) / 2;
        cards.push(`${ref(el, 'B')} ${t[2]} 0 V=${num(mid)}+${num(half)}*tanh(${num(gain)}*(v(${inp})-v(${inn}))/${num(half)})`);
        break;
      }

      // Real op amp: one-pole gain stage with slew limit, then a current-limited, clamped output.
      //   gm stage:  I = Isl*tanh(gm*vd/Isl) into node x, which has Rp || Cp to ground
      //              (DC gain = gm*Rp, pole at GBW/gain, slew rate = Isl/Cp)
      //   output:    I = Imax*tanh((clamp(v(x)) - v(out)) / (Rout*Imax)) into the output node
      case 'OpAmpRealElm': {
        const label = def.label;
        const gain = opNumber(el, 'gain', label, 'Open-loop Gain must be a positive number');
        const gbw = opNumber(el, 'gbw', label, 'Gain-Bandwidth Product must be a positive number');
        const slew = opNumber(el, 'slew', label, 'Slew Rate must be a positive number');
        const imax = opNumber(el, 'imax', label, 'Output Current Limit must be a positive number');
        const rout = opNumber(el, 'rout', label, 'Output Resistance must be a positive number');
        const vmax = opNumber(el, 'vmax', label, 'Max Output must be a number', Number.isFinite);
        const vmin = opNumber(el, 'vmin', label, 'Min Output must be a number', Number.isFinite);
        if ([gain, gbw, slew, imax, rout, vmax, vmin].includes(undefined)) break;
        if (!(vmax > vmin)) { errors.push(`${label}: Max Output must be greater than Min Output.`); break; }
        const swap = String(el.params?.swap) === 'true';
        const inp = swap ? t[0] : t[1];
        const inn = swap ? t[1] : t[0];
        use(inp, inn, t[2]);
        const k = (counters.U = (counters.U ?? 0) + 1);
        refs.set(el.id, `U${k}`);
        const x = `z_oa${k}_x`; // internal node; names starting with z_ are hidden from the results list
        const gm = 1e-4;
        const rp = gain / gm;
        const cp = gm / (2 * Math.PI * gbw);
        const isl = slew * 1e6 * cp;
        const mid = (vmax + vmin) / 2;
        const half = (vmax - vmin) / 2;
        cards.push(`Bg${k} 0 ${x} I=${num(isl)}*tanh(${num(gm)}*(v(${inp})-v(${inn}))/${num(isl)})`);
        cards.push(`Rp${k} ${x} 0 ${num(rp)}`);
        cards.push(`Cp${k} ${x} 0 ${num(cp)}`);
        cards.push(`Bo${k} 0 ${t[2]} I=${num(imax)}*tanh(((${num(mid)}+${num(half)}*tanh((v(${x})-(${num(mid)}))/${num(half)}))-v(${t[2]}))/${num(rout * imax)})`);
        break;
      }

      default:
        unsupported.set(def.label, (unsupported.get(def.label) ?? 0) + 1);
    }
  }

  // ---- digital side: one digital shadow node (d_<net>) per net that has a gate pin ----------------
  if (gates.length) {
    const gateIds = new Set(gates.map((g) => g.el.id));
    const analog = new Set(['0']);
    for (const el of parts) {
      if (gateIds.has(el.id)) continue;
      terminalsOf(el).forEach((_, i) => analog.add(nodes.nodeOfTerminal(el, i)));
    }
    const digNodes = new Map(); // net -> { outs: [gate], ins: [gate] }
    const entry = (n) => { if (!digNodes.has(n)) digNodes.set(n, { outs: [], ins: [] }); return digNodes.get(n); };
    const alone = (n) => n !== '0' && pins.get(n) === 1; // a pin that nothing else is connected to
    let open = 0;
    for (const g of gates) {
      for (const p of g.ports) {
        if (p.dir === 'null') continue;
        if (p.opt && alone(p.net)) { p.open = true; openNets.add(p.net); continue; } // unused optional pin: NULL / dummy node
        entry(p.net)[p.dir === 'out' ? 'outs' : 'ins'].push(g);
      }
    }
    const dn = (n) => `d_${n}`;
    const adcModels = new Set();
    const dacModels = new Set();
    let bridge = 0;
    for (const [net, { outs, ins }] of digNodes) {
      if (outs.length > 1) { errors.push(`Net ${net}: ${outs.length} outputs are connected together. Use one driver per net.`); continue; }
      if (outs.length === 1) {
        if (net === '0') { warnings.push('A logic output is connected to ground.'); continue; }
        const v = outs[0].vhigh;
        const m = `DAC_${num(v).replace(/\W/g, '_')}`;
        if (!dacModels.has(m)) { dacModels.add(m); modelCards.set(m, `.model ${m} dac_bridge(out_low=0 out_high=${num(v)})`); }
        cards.push(`Abr${++bridge} [${dn(net)}] [${net}] ${m}`);
        if (ins.some((g) => g.vhigh !== v)) warnings.push(`Net ${net}: parts with different logic levels share a net.`);
      } else if (ins.length) {
        if (!analog.has(net)) { errors.push(`A logic input on net ${net} has nothing driving it. Connect it to a gate output, a source or ground.`); continue; }
        const v = ins[0].vhigh;
        const m = `ADC_${num(v).replace(/\W/g, '_')}`;
        if (!adcModels.has(m)) { adcModels.add(m); modelCards.set(m, `.model ${m} adc_bridge(in_low=${num(0.3 * v)} in_high=${num(0.7 * v)})`); }
        cards.push(`Abr${++bridge} [${net}] [${dn(net)}] ${m}`);
      }
    }
    for (const g of gates) {
      const toks = g.ports.map((p) => (p.dir === 'null' || (p.open && p.dir === 'in') ? 'NULL' : p.open ? `d_nc${++open}` : dn(p.net)));
      const body = g.vec ? [`[${toks.slice(0, g.vec).join(' ')}]`, ...toks.slice(g.vec)] : toks;
      cards.push(`${g.ref} ${body.join(' ')} ${g.model}`);
    }
  }

  for (const [label, n] of unsupported) {
    errors.push(`${label}${n > 1 ? ` (${n}x)` : ''} is not supported by the SPICE export yet. Delete it or replace it with a supported part.`);
  }
  for (const [node, n] of pins) {
    if (n === 1 && !openNets.has(node)) warnings.push(`Node ${node} has only one connection (a loose wire or an unconnected pin).`);
  }
  if (parts.length && !cards.some((c) => /^[VI]/.test(c))) warnings.push('The circuit has no voltage or current source.');

  let command = '';
  if (analysis) {
    const problems = validateParams(analysis.type, analysis.params);
    problems.forEach((p) => errors.push(`Analysis: ${p}`));
    if (!problems.length) {
      if (analysis.type === 'dc' && !sources.includes(String(analysis.params.source).trim())) {
        errors.push(`Analysis: there is no source called "${analysis.params.source}". Sources in this circuit: ${sources.join(', ') || 'none'}.`);
      }
      command = buildCommand(analysis.type, analysis.params);
    }
  }

  const ok = errors.length === 0;
  const safeTitle = String(title).replace(/[\r\n]+/g, ' ').trim() || 'circuit';
  const libFiles = [...libs];
  const libNote = libFiles.map((f) => `* library file (added by the server when it runs): ${f}`);
  if (pack) {
    // Wrap the circuit as a .subckt definition; its pins are the Port parts, top to bottom then left to right.
    if (!/^[A-Za-z][\w]{0,31}$/.test(String(pack.name))) errors.push('Subcircuit name: use letters, digits and _ only, starting with a letter (32 characters at most).');
    const ports = [];
    const portEls = elements.filter((e) => e.type === 'PortElm').map((e) => ({ e, p: terminalsOf(e)[0] }))
      .sort((a, b) => a.p.y - b.p.y || a.p.x - b.p.x);
    for (const { e } of portEls) {
      const nm = nodes.nodeOfTerminal(e, 0);
      if (nm === '0') errors.push('A Subcircuit Port cannot be named 0 or gnd; ground is shared with the outside circuit.');
      else if (!ports.includes(nm)) ports.push(nm);
    }
    if (!ports.length) errors.push('Add at least one Subcircuit Port (Draw > Outputs and Labels) to mark the pins of the block.');
    if (elements.some((e) => e.type === 'SubcktElm')) errors.push('Packing a circuit that contains Subcircuit blocks is not supported yet.');
    if (gates.length) errors.push('Packing circuits with digital parts (gates, flip-flops) is not supported yet.');
    if (libs.size) errors.push('Packing circuits that use library models is not supported yet (the block would need those files).');
    if (directiveLines.length) errors.push('Remove SPICE Directive parts before packing; directives are not allowed inside a subcircuit.');
    const bodyText = [`* ${String(title).replace(/[\r\n]+/g, ' ').trim() || 'circuit'} - packed by circuit-ui`, `.subckt ${pack.name} ${ports.join(' ')}`, ...cards, ...modelCards.values(), `.ends ${pack.name}`, ''].join('\n');
    return { ok: errors.length === 0, text: bodyText, errors, warnings, refs, sources, libs: [], ports };
  }
  const text = [safeTitle, ...libNote, ...cards, ...modelCards.values(), ...directiveLines, command, '.end', ''].join('\n');
  return { ok, text, errors, warnings, refs, sources, libs: libFiles };
}
