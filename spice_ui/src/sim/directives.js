// "SPICE Directive" text blocks: free text that goes into the netlist, but only a safe subset.
//
// A directive can set parameters and options, define models and functions, set initial conditions or ask for
// measurements. It cannot read or write files, run scripts, define circuit elements (draw those) or choose the
// analysis (use Simulation > Analysis Setup). The server refuses the dangerous commands again on its own, so
// this check is for clear messages, not the only line of defence.

export const ALLOWED_DIRECTIVES = ['param', 'model', 'options', 'option', 'ic', 'nodeset', 'temp', 'global', 'func', 'meas', 'measure'];
const ANALYSIS = new Set(['op', 'tran', 'ac', 'dc', 'noise', 'tf', 'pz', 'sens', 'disto', 'four', 'step']);
// words that make ngspice open files, whichever command carries them (".model x d_source(input_file=...)")
const FILE_WORDS = /\b(input_file|file|include|inc|lib|source|write|wrdata|load|shell|echo|spinit|codemodel)\b\s*(=|\()?/i;

/** Join "+" continuation lines and drop comments; returns [{ text, lineNo }]. */
export function logicalLines(text) {
  const out = [];
  String(text ?? '').split(/\r?\n/).forEach((raw, i) => {
    const line = raw.replace(/\s*[;$].*$/, '').trimEnd();
    if (!line.trim() || /^\s*\*/.test(line)) return;
    if (/^\s*\+/.test(line) && out.length) out[out.length - 1].text += ` ${line.replace(/^\s*\+/, '').trim()}`;
    else out.push({ text: line.trim(), lineNo: i + 1 });
  });
  return out;
}

/** -> { lines: string[], problems: string[] } — the lines to put in the netlist and what is wrong with the rest. */
export function checkDirectives(text) {
  const problems = [];
  const lines = [];
  for (const { text: l, lineNo } of logicalLines(text)) {
    const where = `line ${lineNo}`;
    if (/["'\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(l)) { problems.push(`${where}: quotes and control characters are not allowed.`); continue; }
    const m = /^\.(\w+)/.exec(l);
    if (!m) {
      problems.push(`${where}: "${l.slice(0, 24)}" is not a directive. Circuit elements are drawn on the canvas; directives start with a dot (.param, .model, .options...).`);
      continue;
    }
    const cmd = m[1].toLowerCase();
    if (ANALYSIS.has(cmd)) { problems.push(`${where}: .${cmd} is set in Simulation > Analysis Setup, not here.`); continue; }
    if (!ALLOWED_DIRECTIVES.includes(cmd)) {
      problems.push(`${where}: .${cmd} is not allowed. Allowed: ${ALLOWED_DIRECTIVES.map((c) => `.${c}`).join(' ')}. Model files are added through the Model Library.`);
      continue;
    }
    if (FILE_WORDS.test(l.slice(m[0].length))) { problems.push(`${where}: this line mentions a file or script command, which is not allowed.`); continue; }
    lines.push(l);
  }
  return { lines, problems };
}
