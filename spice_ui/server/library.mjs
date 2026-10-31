// Scans the model library folder (default: <project>/models) for SPICE model files and lists the
// `.model` and `.subckt` definitions in them. Pure Node, no dependencies.
//
// Only a light text scan: it does not validate the models (ngspice does that when they are used).
// Handles `+` continuation lines, `*` full-line comments and `;` / `$` trailing comments.

import { readdir, readFile, stat } from 'node:fs/promises';
import path from 'node:path';

export const LIB_EXT = new Set(['.lib', '.mod', '.model', '.cir', '.sp', '.spi', '.txt', '.inc']);
const MAX_FILES = 200;
const MAX_BYTES = 5 * 1024 * 1024;

/** File names the client may reference: plain names, no path separators, quotes or control chars. */
export const safeFileName = (n) =>
  typeof n === 'string' && n.length > 0 && n.length < 200 && !/[\\/"'\u0000-\u001f]/.test(n) && n !== '.' && n !== '..';

export function parseLibraryText(text, file) {
  const logical = [];
  for (const raw of String(text).split(/\r?\n/)) {
    if (/^\s*\*/.test(raw)) continue;
    const line = raw.replace(/[;$].*$/, '');
    if (/^\s*\+/.test(line) && logical.length) logical[logical.length - 1] += ` ${line.replace(/^\s*\+/, '')}`;
    else logical.push(line);
  }
  const found = [];
  for (const l of logical) {
    let m = /^\s*\.model\s+(\S+)\s+([a-z]+)/i.exec(l);
    if (m) { found.push({ kind: 'model', name: m[1], type: m[2].toUpperCase(), file }); continue; }
    m = /^\s*\.subckt\s+(\S+)\s*(.*)$/i.exec(l);
    if (m) {
      const pins = [];
      for (const tok of m[2].split(/\s+/).filter(Boolean)) {
        if (/^params:?$/i.test(tok) || tok.includes('=')) break; // everything after PARAMS: is a parameter
        pins.push(tok);
      }
      found.push({ kind: 'subckt', name: m[1], type: 'SUBCKT', pins, file });
    }
  }
  return found;
}

/** -> { dir, files: string[], models: [{kind,name,type,file,pins?}], problems: string[] } */
export async function scanLibrary(dir) {
  const out = { dir, files: [], models: [], problems: [] };
  let names;
  try {
    names = await readdir(dir);
  } catch (e) {
    out.problems.push(`Cannot read the model folder "${dir}": ${e.code === 'ENOENT' ? 'it does not exist' : e.message}.`);
    return out;
  }
  names = names.filter((n) => LIB_EXT.has(path.extname(n).toLowerCase()) && safeFileName(n)).sort().slice(0, MAX_FILES);
  const seen = new Set();
  for (const n of names) {
    const full = path.join(dir, n);
    try {
      const st = await stat(full);
      if (!st.isFile()) continue;
      if (st.size > MAX_BYTES) { out.problems.push(`${n}: skipped, larger than ${MAX_BYTES / 1024 / 1024} MB.`); continue; }
      const defs = parseLibraryText(await readFile(full, 'utf8'), n);
      out.files.push(n);
      for (const d of defs) {
        const key = `${d.kind}:${d.name.toLowerCase()}`;
        if (seen.has(key)) { out.problems.push(`${n}: "${d.name}" is already defined in an earlier file; the first one is used.`); continue; }
        seen.add(key);
        out.models.push(d);
      }
    } catch (e) {
      out.problems.push(`${n}: ${e.message}`);
    }
  }
  return out;
}
