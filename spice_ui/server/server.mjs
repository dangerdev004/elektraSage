// Local ngspice backend for circuit-ui. Zero dependencies (Node built-ins only).
//
//   node server/server.mjs            (or: pnpm server)
//
// POST /api/simulate  { netlist: string, libs?: string[] }  ->  { raw: <parsed raw file>, log: string }
//                     libs = file names from the model folder; the server adds the .include lines
// GET  /api/models                          ->  { dir, files, models: [{kind,name,type,file}], problems }
// GET  /api/health                         ->  { ok: true, ngspice: "<first line of --version>" }
//
// It runs   ngspice -b -r out.raw -o out.log circuit.cir   in a fresh temp directory and parses the
// raw file. Settings (environment variables):
//   NGSPICE_BIN   path to the ngspice executable   (default: "ngspice" from PATH)
//   MODELS_DIR    folder with .lib/.model files     (default: <project>/models)
//   PORT          listen port                       (default 3001)
//   SIM_TIMEOUT_MS  kill a run after this long       (default 60000)
//
// Safety: it listens on 127.0.0.1 only, accepts JSON only, refuses cross-site browser requests,
// caps the request size, and rejects netlists that contain ngspice control constructs (.control,
// .include, .lib, shell ...) because those can run commands or read files. The circuit editor never
// generates them. This is a local developer tool, not something to expose to a network.

import http from 'node:http';
import { spawn } from 'node:child_process';
import { mkdtemp, writeFile, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseRaw } from './rawfile.mjs';
import { scanLibrary, safeFileName } from './library.mjs';

const BIN = process.env.NGSPICE_BIN || 'ngspice';
const PORT = Number(process.env.PORT || 3001);
const TIMEOUT = Number(process.env.SIM_TIMEOUT_MS || 60000);
const MAX_BODY = 2 * 1024 * 1024;
// Model library folder: <project>/models unless MODELS_DIR says otherwise.
const MODELS_DIR = process.env.MODELS_DIR || path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'models');

// Anything that lets a netlist run commands, read/write files, or switch to the scripting language.
const FORBIDDEN = /^\s*(\.(control|endc|include|inc|lib|read|csparam|osdi|spinit)\b|shell\b|source\b|codemodel\b|write\b|wrdata\b|load\b|echo\b)/im;

export function checkNetlist(text) {
  if (typeof text !== 'string' || !text.trim()) return 'The netlist is empty.';
  // The first line is the title; ngspice never executes it, so a title like "Load test" is fine.
  const bad = FORBIDDEN.exec(text.split(/\r?\n/).slice(1).join('\n'));
  if (bad) return `Refused: the netlist contains "${bad[0].trim().slice(0, 30)}", which is not allowed by this server.`;
  return null;
}

function run(netlist, libFiles = []) {
  return mkdtemp(path.join(tmpdir(), 'circuit-ui-')).then(async (dir) => {
    try {
      const cir = path.join(dir, 'circuit.cir');
      const raw = path.join(dir, 'out.raw');
      const log = path.join(dir, 'out.log');
      // Library files are added by the server itself (the client may only name files that exist in the
      // model folder), so the netlist the client sends can stay free of .include.
      let deck = netlist;
      if (libFiles.length) {
        const lines = netlist.split(/\r?\n/);
        const inc = libFiles.map((f) => `.include "${path.join(MODELS_DIR, f)}"`);
        deck = [lines[0], ...inc, ...lines.slice(1)].join('\n');
      }
      await writeFile(cir, deck, 'utf8');
      const { code, signal, stderr, spawnError, timedOut } = await new Promise((resolve) => {
        let stderr = '';
        const child = spawn(BIN, ['-b', '-r', raw, '-o', log, cir], { cwd: dir, stdio: ['ignore', 'ignore', 'pipe'] });
        const timer = setTimeout(() => { child.kill('SIGKILL'); resolve({ timedOut: true, stderr }); }, TIMEOUT);
        child.stderr.on('data', (d) => { if (stderr.length < 20000) stderr += d; });
        child.on('error', (e) => { clearTimeout(timer); resolve({ spawnError: e, stderr }); });
        child.on('close', (code, signal) => { clearTimeout(timer); resolve({ code, signal, stderr }); });
      });
      const logText = await readFile(log, 'utf8').catch(() => '');
      if (spawnError) {
        const hint = spawnError.code === 'ENOENT'
          ? ` Could not find "${BIN}". Install ngspice or set NGSPICE_BIN to its full path.` : '';
        throw Object.assign(new Error(`Could not start ngspice: ${spawnError.message}.${hint}`), { status: 500, log: logText });
      }
      if (timedOut) throw Object.assign(new Error(`ngspice did not finish within ${TIMEOUT / 1000} s and was stopped.`), { status: 504, log: logText });
      let rawBuf = null;
      try { rawBuf = await readFile(raw); } catch { /* handled below */ }
      if (!rawBuf || !rawBuf.length) {
        const why = errorLines(logText + '\n' + stderr) || `ngspice exited with code ${code}${signal ? ` (${signal})` : ''} and wrote no results.`;
        throw Object.assign(new Error(why), { status: 422, log: logText || stderr });
      }
      return { raw: parseRaw(rawBuf), log: logText, exitCode: code };
    } finally {
      rm(dir, { recursive: true, force: true }).catch(() => {});
    }
  });
}

/** Pull the lines that look like errors out of ngspice's log, to show the user. */
function errorLines(text) {
  const out = text.split(/\r?\n/).filter((l) => /error|fatal|singular|no convergence|timestep too small|doesn't exist|unknown|can't|cannot/i.test(l));
  return out.slice(0, 8).join('\n').trim();
}

function send(res, status, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
  res.end(body);
}

export function makeServer() {
  return http.createServer(async (req, res) => {
    try {
      // Cross-site pages must not drive this server; the Vite dev proxy forwards same-origin requests.
      const origin = req.headers.origin;
      if (origin) {
        const host = new URL(origin).hostname;
        if (host !== 'localhost' && host !== '127.0.0.1' && host !== '[::1]') return send(res, 403, { error: 'Cross-site request refused.' });
      }
      if (req.method === 'GET' && req.url === '/api/health') {
        const v = await new Promise((resolve) => {
          let out = '';
          const c = spawn(BIN, ['--version'], { stdio: ['ignore', 'pipe', 'pipe'] });
          c.stdout.on('data', (d) => { out += d; });
          c.stderr.on('data', (d) => { out += d; });
          c.on('error', () => resolve(null));
          c.on('close', () => resolve(out));
        });
        if (v === null) return send(res, 503, { ok: false, error: `Could not start "${BIN}". Install ngspice or set NGSPICE_BIN.` });
        const line = v.split(/\r?\n/).map((s) => s.trim()).find((s) => /ngspice/i.test(s)) ?? v.trim().split(/\r?\n/)[0] ?? '';
        return send(res, 200, { ok: true, ngspice: line });
      }
      if (req.method === 'GET' && req.url === '/api/models') {
        const lib = await scanLibrary(MODELS_DIR);
        return send(res, 200, lib);
      }
      if (req.method === 'POST' && req.url === '/api/simulate') {
        if (!/^application\/json/i.test(req.headers['content-type'] ?? '')) return send(res, 415, { error: 'Send JSON.' });
        let size = 0;
        const chunks = [];
        for await (const c of req) {
          size += c.length;
          if (size > MAX_BODY) return send(res, 413, { error: 'Netlist too large.' });
          chunks.push(c);
        }
        let body;
        try { body = JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch { return send(res, 400, { error: 'Invalid JSON.' }); }
        const problem = checkNetlist(body.netlist);
        if (problem) return send(res, 400, { error: problem });
        let libFiles = [];
        if (body.libs !== undefined) {
          if (!Array.isArray(body.libs) || body.libs.length > 50 || !body.libs.every(safeFileName)) return send(res, 400, { error: 'Invalid library list.' });
          const lib = await scanLibrary(MODELS_DIR);
          const missing = body.libs.filter((f) => !lib.files.includes(f));
          if (missing.length) return send(res, 400, { error: `Model file not found in the model folder: ${missing.join(', ')}. Check ${MODELS_DIR}.` });
          libFiles = [...new Set(body.libs)];
        }
        try {
          return send(res, 200, await run(body.netlist, libFiles));
        } catch (e) {
          return send(res, e.status ?? 500, { error: e.message, log: e.log ?? '' });
        }
      }
      return send(res, 404, { error: 'Not found.' });
    } catch (e) {
      return send(res, 500, { error: e.message });
    }
  });
}

if (import.meta.url === `file://${process.argv[1]}` || process.argv[1]?.endsWith('server.mjs')) {
  makeServer().listen(PORT, '127.0.0.1', () => {
    console.log(`circuit-ui ngspice server on http://127.0.0.1:${PORT}  (ngspice: ${BIN})`);
  });
}
