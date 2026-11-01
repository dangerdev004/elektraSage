// Scans the model library folder (default: <project>/models) for SPICE model files and lists the
// `.model` and `.subckt` definitions in them. Pure Node, no dependencies.
//
// Only a light text scan: it does not validate the models (ngspice does that when they are used).
// Handles `+` continuation lines, `*` full-line comments and `;` / `$` trailing comments.

import { readdir, readFile, stat } from 'node:fs/promises';
import path from 'node:path';

export const LIB_EXT = new Set(['.lib', '.mod', '.model', '.cir', '.sp', '.spi', '.txt', '.inc', '.sub']);
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
      const toks = m[2].split(/\s+/).filter(Boolean);
      const rest = toks.slice(pins.length).join(' ');
      const params = [];
      for (const pm of rest.matchAll(/([A-Za-z_][\w]*)\s*=\s*(\S+)/g)) params.push({ name: pm[1], def: pm[2] });
      found.push({ kind: 'subckt', name: m[1], type: 'SUBCKT', pins, params, file });
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

// ---- uploads -----------------------------------------------------------------------------------
// A library file the browser sends is checked before it is saved. Model files are plain SPICE text, so
// anything that runs commands or reaches outside the models folder is refused.
const UPLOAD_DANGEROUS = /^\s*(\.(control|endc|csparam|osdi|spinit|read)\b|shell\b|source\b|codemodel\b|write\b|wrdata\b|load\b|echo\b)/im;
const UPLOAD_PATHY = /^\s*\.(include|inc|lib)\b[^\n]*([\\/]|\.\.|\b[a-z]:)/im; // .include with a path, "..", or a drive letter
const UPLOAD_FILE_ARG = /\b(input_file|file)\s*=/i;
export const MAX_UPLOAD = 5 * 1024 * 1024;

/** -> null when the file may be saved, else the reason it was refused. */
export function checkLibraryUpload(name, text) {
  if (!safeFileName(name)) return 'Use a plain file name (no folders, quotes or special characters).';
  if (!LIB_EXT.has(path.extname(name).toLowerCase())) return `Use one of these file types: ${[...LIB_EXT].join(' ')}.`;
  if (typeof text !== 'string' || !text.trim()) return 'The file is empty.';
  if (Buffer.byteLength(text, 'utf8') > MAX_UPLOAD) return `The file is larger than ${MAX_UPLOAD / 1024 / 1024} MB.`;
  if (text.includes('\u0000')) return 'This looks like a binary file, not SPICE text.';
  if (UPLOAD_DANGEROUS.test(text)) return 'The file contains a script or file command (.control, shell, write, source, load ...), which is not allowed.';
  if (UPLOAD_PATHY.test(text)) return 'The file includes another file by path. Only plain file names in the same folder are allowed.';
  if (UPLOAD_FILE_ARG.test(text)) return 'The file has a model that reads a data file (file= / input_file=), which is not allowed.';
  return null;
}
