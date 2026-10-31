// The solver: a real, native ngspice running on your own machine behind server/server.mjs.
// Contract used by the UI:  run({ netlist, analysisType }) -> Promise<normalised result>.
// The server returns the parsed ngspice raw file in the shape normalizeRaw() already reads.

import { normalizeRaw } from './results.js';

export class NgspiceServerEngine {
  /** `fetchImpl` and `base` are injectable for tests. */
  constructor({ fetchImpl = (...a) => fetch(...a), base = '' } = {}) {
    this.fetch = fetchImpl;
    this.base = base;
    this.busy = false;
    this.sim = true; // nothing to download before the first run
    this.lastLog = '';
  }

  async run({ netlist, analysisType, libs = [] }) {
    if (this.busy) throw new Error('The simulator is still busy with the previous run.');
    this.busy = true;
    try {
      let res;
      try {
        res = await this.fetch(`${this.base}/api/simulate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ netlist, libs }),
        });
      } catch (e) {
        throw new Error(`Could not reach the local ngspice server (${e.message}). Start it with "npm run server" in the project folder.`);
      }
      let body = null;
      try { body = await res.json(); } catch { /* not JSON */ }
      if (!res.ok || !body || body.error) {
        this.lastLog = body?.log ?? '';
        const detail = body?.error ?? `HTTP ${res.status}`;
        // the dev proxy answers 500/502 with no JSON when nothing is listening on the port
        const hint = !body && res.status >= 500 ? ' Is the ngspice server running? Start it with "npm run server".' : '';
        throw new Error(`ngspice: ${detail}${hint}`);
      }
      this.lastLog = body.log ?? '';
      return normalizeRaw(body.raw, analysisType);
    } finally {
      this.busy = false;
    }
  }
}
