// Parser for SPICE3 / ngspice "raw" output files (binary or ascii), as written by `ngspice -r file`.
// Pure Node, no dependencies. Returns the same shape the browser engine layer expects:
//   { header, numPoints, dataType: 'real'|'complex', variableNames: string[],
//     data: [{ name, type, values: number[] | {real, img}[] }] }
//
// Format (from the ngspice manual / SPICE3 rawfile description): a text header
//   Title: / Date: / Plotname: / Flags: real|complex / No. Variables: N / No. Points: M /
//   Variables:\n\t0\tname\ttype ... / Binary:\n   (or Values:\n for ascii)
// followed by M points. Binary points are N doubles each (2N doubles when complex).
// A file may hold several plots back to back; only the LAST plot is returned, because a netlist
// with one analysis card writes one plot and, with .op plus another analysis, the later one is the
// interesting one.

export function parseRaw(buf) {
  const plots = [];
  let pos = 0;
  while (pos < buf.length) {
    const plot = parsePlot(buf, pos);
    if (!plot) break;
    plots.push(plot.result);
    pos = plot.end;
    // skip stray whitespace between plots
    while (pos < buf.length && (buf[pos] === 0x0a || buf[pos] === 0x0d || buf[pos] === 0x20)) pos++;
  }
  if (!plots.length) throw new Error('No plot found in the ngspice raw file (is it empty?).');
  return plots[plots.length - 1];
}

function parsePlot(buf, start) {
  const head = {};
  const vars = [];
  let pos = start;
  let mode = null; // 'binary' | 'ascii'
  let inVars = false;

  while (pos < buf.length) {
    let eol = buf.indexOf(0x0a, pos);
    if (eol < 0) eol = buf.length;
    const line = buf.toString('latin1', pos, eol).replace(/\r$/, '');
    pos = eol + 1;
    if (inVars && /^\s/.test(line) && line.trim()) {
      const f = line.trim().split(/\s+/);
      if (f.length >= 3) vars.push({ index: Number(f[0]), name: f[1], type: f[2] });
      continue;
    }
    const m = /^([^:]+):\s?(.*)$/.exec(line);
    if (!m) { if (!line.trim()) continue; throw new Error(`Unexpected line in raw file header: "${line.slice(0, 60)}"`); }
    const key = m[1].trim().toLowerCase();
    if (key === 'variables') { inVars = true; continue; }
    if (key === 'binary') { mode = 'binary'; break; }
    if (key === 'values') { mode = 'ascii'; break; }
    inVars = false;
    head[key] = m[2].trim();
  }
  if (!mode) return null;

  const nVars = Number(head['no. variables']);
  const nPoints = Number(head['no. points']);
  if (!Number.isInteger(nVars) || !Number.isInteger(nPoints) || vars.length !== nVars) {
    throw new Error(`Raw file header is inconsistent (variables ${vars.length} of ${head['no. variables']}, points ${head['no. points']}).`);
  }
  const complex = /complex/i.test(head.flags ?? '');
  const per = complex ? 2 : 1;
  const columns = vars.map(() => new Array(nPoints));
  let end;

  if (mode === 'binary') {
    const need = nPoints * nVars * per * 8;
    if (buf.length - pos < need) throw new Error(`Raw file is truncated (need ${need} data bytes, have ${buf.length - pos}).`);
    let p = pos;
    for (let k = 0; k < nPoints; k++) {
      for (let v = 0; v < nVars; v++) {
        const re = buf.readDoubleLE(p); p += 8;
        if (complex) { const im = buf.readDoubleLE(p); p += 8; columns[v][k] = { real: re, img: im }; } else columns[v][k] = re;
      }
    }
    end = p;
  } else {
    const rest = buf.toString('latin1', pos);
    const tokens = rest.split(/\s+/).filter(Boolean);
    let t = 0;
    const readNum = (s) => Number(s.split(',')[0]);
    for (let k = 0; k < nPoints; k++) {
      t++; // point index
      for (let v = 0; v < nVars; v++) {
        if (complex) {
          const [a, b] = tokens[t++].split(',');
          columns[v][k] = { real: Number(a), img: Number(b) };
        } else columns[v][k] = readNum(tokens[t++]);
      }
    }
    end = buf.length; // ascii plots are not chained by this parser
  }

  return {
    end,
    result: {
      header: head.plotname ?? '',
      numPoints: nPoints,
      dataType: complex ? 'complex' : 'real',
      variableNames: vars.map((x) => x.name),
      data: vars.map((x, i) => ({ name: x.name, type: x.type, values: columns[i] })),
    },
  };
}
