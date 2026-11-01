// "SPICE Directive" text blocks: free text that goes into the netlist, but only a safe subset.
//
// A directive can set parameters and options, define models and functions, set initial conditions or ask for
// measurements. It cannot read or write files, run scripts, define circuit elements (draw those) or choose the
// analysis only through .op / .tran / .ac / .dc (as in LTspice, such a line replaces Simulation > Analysis Setup).
// The server refuses the dangerous commands again on its own, so this check is for clear messages, not the only
// line of defence.

export const ALLOWED_DIRECTIVES = ['param', 'model', 'options', 'option', 'ic', 'nodeset', 'temp', 'global', 'func', 'meas', 'measure'];
export const ANALYSIS_COMMANDS = ['op', 'tran', 'ac', 'dc'];
const UNSUPPORTED_ANALYSIS = new Set(['noise', 'tf', 'pz', 'sens', 'disto', 'four']);
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

/** -> { lines, problems, analysis: [{ type, text }] } — lines for the netlist, what is wrong with the rest, and any analysis command. */
export function checkDirectives(text) {
  const problems = [];
  const lines = [];
  const analysis = [];
  for (const { text: l, lineNo } of logicalLines(text)) {
    const where = `line ${lineNo}`;
    if (/["'\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(l)) { problems.push(`${where}: quotes and control characters are not allowed.`); continue; }
    const m = /^\.(\w+)/.exec(l);
    if (!m) {
      problems.push(`${where}: "${l.slice(0, 24)}" is not a directive. Circuit elements are drawn on the canvas; directives start with a dot (.param, .model, .options...).`);
      continue;
    }
    const cmd = m[1].toLowerCase();
    if (ANALYSIS_COMMANDS.includes(cmd)) {
      if (FILE_WORDS.test(l.slice(m[0].length))) { problems.push(`${where}: this line mentions a file or script command, which is not allowed.`); continue; }
      analysis.push({ type: cmd, text: l });
      continue;
    }
    if (cmd === 'step') { problems.push(`${where}: .step is not available: ngspice itself has no .step command. Use .dc to sweep a source, or run once per value (a .param you edit).`); continue; }
    if (UNSUPPORTED_ANALYSIS.has(cmd)) { problems.push(`${where}: .${cmd} is not supported yet. Supported analyses: ${ANALYSIS_COMMANDS.map((c) => `.${c}`).join(' ')}.`); continue; }
    if (!ALLOWED_DIRECTIVES.includes(cmd)) {
      problems.push(`${where}: .${cmd} is not allowed. Allowed: ${ALLOWED_DIRECTIVES.map((c) => `.${c}`).join(' ')}. Model files are added through the Model Library.`);
      continue;
    }
    if (FILE_WORDS.test(l.slice(m[0].length))) { problems.push(`${where}: this line mentions a file or script command, which is not allowed.`); continue; }
    lines.push(l);
  }
  return { lines, problems, analysis };
}

/** Names declared with ".param name=value" in directive text (lower case). */
export function declaredParams(text) {
  const names = new Set();
  for (const { text: l } of logicalLines(text)) {
    if (!/^\.param\b/i.test(l)) continue;
    for (const m of l.slice(6).matchAll(/([A-Za-z_]\w*)\s*=/g)) names.add(m[1].toLowerCase());
  }
  return names;
}

/** The analysis a circuit's directive parts ask for: { type, text } or null (several = the first; the netlist builder reports that). */
export function directiveAnalysis(elements) {
  for (const el of elements) {
    if (el.type !== 'DirectiveElm') continue;
    const found = checkDirectives(el.value ?? '').analysis;
    if (found.length) return found[0];
  }
  return null;
}
