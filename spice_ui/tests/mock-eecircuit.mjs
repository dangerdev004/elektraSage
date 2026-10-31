// TEST DOUBLE ONLY. This is NOT a circuit solver. It stands in for the `eecircuit-engine` package
// so the netlist -> engine -> results -> plot pipeline can be tested without downloading ngspice.
// It reads the analysis card and node names from the netlist and returns made-up but
// deterministic data in the shape the real package is expected to return.

const parse = (s) => {
  const m = /^([\d.]+(?:e[+-]?\d+)?)\s*(meg|[kmunpf])?/i.exec(s);
  const mult = { meg: 1e6, k: 1e3, m: 1e-3, u: 1e-6, n: 1e-9, p: 1e-12, f: 1e-15 };
  return parseFloat(m[1]) * (m[2] ? mult[m[2].toLowerCase()] : 1);
};

export class Simulation {
  constructor() { this.started = false; this.netlist = ''; Simulation.starts = (Simulation.starts ?? 0) + 1; }
  async start() { this.started = true; }
  setNetList(t) { this.netlist = t; }
  async runSim() {
    if (!this.started) throw new Error('not started');
    await new Promise((r) => setTimeout(r, globalThis.__mockDelay ?? 0)); // lets browser tests exercise Stop
    const nodes = [...new Set(this.netlist.match(/\bn\d+\b/g) ?? [])];
    const src = (this.netlist.match(/^V\d+/gm) ?? [])[0]?.toLowerCase();
    const card = this.netlist.split('\n').find((l) => /^\.(tran|ac|dc|op)\b/i.test(l)) ?? '';
    const [kind, ...a] = card.trim().split(/\s+/);
    const k = kind.toLowerCase();
    if (k === '.op') {
      return {
        header: 'Operating Point', numVariables: nodes.length, numPoints: 1, dataType: 'real',
        variableNames: nodes,
        data: [...nodes.map((n, i) => ({ name: n, type: 'voltage', values: [i + 1] })),
          ...(src ? [{ name: `${src}#branch`, type: 'current', values: [-0.001] }] : [])],
      };
    }
    if (k === '.tran') {
      const step = parse(a[0]); const stop = parse(a[1]);
      const n = Math.round(stop / step) + 1;
      const t = Array.from({ length: n }, (_, i) => i * step);
      return {
        header: 'Transient', numVariables: nodes.length + 1, numPoints: n, dataType: 'real',
        variableNames: ['time', ...nodes],
        data: [{ name: 'time', type: 'time', values: t },
          ...nodes.map((nm, j) => ({ name: nm, type: 'voltage', values: t.map((x) => (j + 1) * (1 - Math.exp(-x / (stop / 5)))) })),
          ...(src ? [{ name: `${src}#branch`, type: 'current', values: t.map(() => -0.001) }] : [])],
      };
    }
    if (k === '.ac') {
      const per = parse(a[1]); const f0 = parse(a[2]); const f1 = parse(a[3]);
      const dec = Math.log10(f1 / f0);
      const n = Math.round(dec * per) + 1;
      const f = Array.from({ length: n }, (_, i) => f0 * 10 ** (i / per));
      const fc = 159.155;
      const H = (x) => { const d = 1 + (x / fc) ** 2; return { real: 1 / d, img: -(x / fc) / d }; };
      return {
        header: 'AC', numVariables: nodes.length + 1, numPoints: n, dataType: 'complex',
        variableNames: ['frequency', ...nodes],
        data: [{ name: 'frequency', type: 'frequency', values: f.map((x) => ({ real: x, img: 0 })) },
          ...nodes.map((nm) => ({ name: nm, type: 'voltage', values: f.map(H) }))],
      };
    }
    if (k === '.dc') {
      const lo = parse(a[1]); const hi = parse(a[2]); const st = parse(a[3]);
      const n = Math.round((hi - lo) / st) + 1;
      const x = Array.from({ length: n }, (_, i) => lo + i * st);
      return {
        header: 'DC', numVariables: nodes.length + 1, numPoints: n, dataType: 'real',
        variableNames: [`${a[0]}-sweep`, ...nodes],
        data: [{ name: `${a[0]}-sweep`, type: 'voltage', values: x },
          ...nodes.map((nm, j) => ({ name: nm, type: 'voltage', values: x.map((v) => v / (j + 2)) }))],
      };
    }
    throw new Error(`mock: no analysis card in netlist:\n${this.netlist}`);
  }
}
