// Analysis choices and the SPICE card each one produces. Pure, no DOM.
import { parseValue } from './units.js';

export const ANALYSES = {
  tran: {
    label: 'Transient',
    fields: [
      { id: 'step', label: 'Time step', def: '20u' },
      { id: 'stop', label: 'Final time', def: '20m' },
    ],
  },
  ac: {
    label: 'AC sweep',
    fields: [
      { id: 'sweep', label: 'Sweep', def: 'dec', options: ['dec', 'oct', 'lin'] },
      { id: 'points', label: 'Points per sweep', def: '20' },
      { id: 'fstart', label: 'Start frequency (Hz)', def: '1' },
      { id: 'fstop', label: 'Stop frequency (Hz)', def: '1Meg' },
    ],
  },
  dc: {
    label: 'DC sweep',
    fields: [
      { id: 'source', label: 'Source name', def: 'V1' },
      { id: 'start', label: 'Start', def: '0' },
      { id: 'stop', label: 'Stop', def: '5' },
      { id: 'step', label: 'Step', def: '100m' },
    ],
  },
  op: { label: 'Operating point', fields: [] },
};

export const defaultAnalysis = () => ({ type: 'tran', params: defaultParams('tran') });

export function defaultParams(type) {
  return Object.fromEntries(ANALYSES[type].fields.map((f) => [f.id, f.def]));
}

export function buildCommand(type, p) {
  switch (type) {
    case 'op': return '.op';
    case 'dc': return `.dc ${p.source} ${p.start} ${p.stop} ${p.step}`;
    case 'ac': return `.ac ${p.sweep} ${p.points} ${p.fstart} ${p.fstop}`;
    case 'tran': return `.tran ${p.step} ${p.stop}`;
    default: throw new Error(`Unknown analysis "${type}"`);
  }
}

/** Human-readable problems with the analysis settings; empty list = fine. */
export function validateParams(type, p) {
  const errs = [];
  for (const f of ANALYSES[type].fields) {
    const v = String(p[f.id] ?? '').trim();
    if (!v) { errs.push(`${f.label} is empty.`); continue; }
    if (f.id !== 'source' && f.id !== 'sweep' && Number.isNaN(parseValue(v))) {
      errs.push(`${f.label}: "${v}" is not a number.`);
    }
  }
  if (errs.length) return errs;
  const n = (id) => parseValue(p[id]);
  if (type === 'tran') {
    if (!(n('step') > 0 && n('stop') > 0)) errs.push('Time step and final time must be greater than 0.');
    else if (n('step') > n('stop')) errs.push('Time step is larger than the final time.');
    else if (n('stop') / n('step') > 2e6) errs.push('That is more than 2 million time points; use a larger step.');
  }
  if (type === 'ac') {
    if (!(n('fstart') > 0 && n('fstop') >= n('fstart'))) errs.push('Need 0 < start frequency <= stop frequency.');
    if (!(n('points') >= 1)) errs.push('Points per sweep must be at least 1.');
  }
  if (type === 'dc' && !(n('step') !== 0)) errs.push('DC step must not be 0.');
  return errs;
}
