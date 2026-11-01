import { useEffect, useRef, useState } from 'react';
import { ANALYSES, defaultParams, validateParams } from '../sim/analysis.js';
import { PART_SHORTCUTS, OTHER_KEYS } from '../data/shortcuts.js';
import { getDef } from '../canvas/parts.js';

export function AnalysisDialog({ analysis, sources, onOk, onCancel }) {
  const [type, setType] = useState(analysis.type);
  const [params, setParams] = useState(analysis.params);
  const first = useRef(null);

  useEffect(() => { first.current?.focus(); }, []);

  const changeType = (t) => {
    const p = t === analysis.type ? analysis.params : defaultParams(t);
    if (t === 'dc' && sources.length && !sources.includes(p.source)) p.source = sources[0];
    setType(t);
    setParams(p);
  };
  const errors = validateParams(type, params);
  const fields = ANALYSES[type].fields;

  const submit = (e) => {
    e.preventDefault();
    if (!errors.length) onOk({ type, params });
  };

  return (
    <div className="modal-backdrop" onPointerDown={onCancel}>
      <form className="modal" onPointerDown={(e) => e.stopPropagation()} onSubmit={submit}>
        <h3>Analysis setup</h3>
        <label className="field">
          <span>Analysis</span>
          <select ref={first} value={type} onChange={(e) => changeType(e.target.value)}>
            {Object.entries(ANALYSES).map(([id, a]) => <option key={id} value={id}>{a.label}</option>)}
          </select>
        </label>
        {fields.map((f) => (
          <label className="field" key={f.id}>
            <span>{f.label}</span>
            {f.options ? (
              <select value={params[f.id]} onChange={(e) => setParams({ ...params, [f.id]: e.target.value })}>
                {f.options.map((o) => <option key={o}>{o}</option>)}
              </select>
            ) : (
              <input value={params[f.id] ?? ''} onChange={(e) => setParams({ ...params, [f.id]: e.target.value })} />
            )}
          </label>
        ))}
        {type === 'op' && <p className="hint">Solves the DC operating point and lists every node voltage.</p>}
        {type === 'ac' && <p className="hint">Sources get a 1 V AC stimulus, so a node's dB value is its gain.</p>}
        {type === 'dc' && sources.length > 0 && <p className="hint">Sources in this circuit: {sources.join(', ')}.</p>}
        {errors.length > 0 && <ul className="form-errors">{errors.map((e) => <li key={e}>{e}</li>)}</ul>}
        <div className="modal-buttons">
          <button type="submit" disabled={errors.length > 0}>OK</button>
          <button type="button" onClick={onCancel}>Cancel</button>
        </div>
      </form>
    </div>
  );
}

export function NetlistDialog({ netlist, onClose }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(netlist.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };
  return (
    <div className="modal-backdrop" onPointerDown={onClose}>
      <div className="modal wide" onPointerDown={(e) => e.stopPropagation()}>
        <h3>SPICE netlist</h3>
        {netlist.errors.length > 0 && (
          <ul className="form-errors">{netlist.errors.map((e) => <li key={e}>{e}</li>)}</ul>
        )}
        <pre className="netlist">{netlist.text}</pre>
        {netlist.warnings.length > 0 && <ul className="warn">{netlist.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
        <div className="modal-buttons">
          <button type="button" onClick={copy}>{copied ? 'Copied' : 'Copy'}</button>
          <button type="button" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

export function ModelLibraryDialog({ library, loading, onRefresh, onUpload, onClose }) {
  const [note, setNote] = useState(null); // { ok, message }
  const [pending, setPending] = useState(null); // a file the server already has: { name, content }
  const picker = useRef(null);
  const send = async (name, content, overwrite) => {
    setNote({ ok: true, message: `Uploading ${name}…` });
    const r = await onUpload(name, content, overwrite);
    if (r.exists) { setPending({ name, content }); setNote({ ok: false, message: r.message }); return; }
    setPending(null);
    setNote(r);
  };
  const pick = async (ev) => {
    const files = [...(ev.target.files ?? [])];
    ev.target.value = '';
    for (const f of files) {
      if (f.size > 5 * 1024 * 1024) { setNote({ ok: false, message: `${f.name} is larger than 5 MB.` }); continue; }
      await send(f.name, await f.text(), false);
    }
  };
  const models = (library?.models ?? []).filter((m) => m.kind === 'model');
  const subckts = (library?.models ?? []).filter((m) => m.kind === 'subckt');
  return (
    <div className="modal-backdrop" onPointerDown={onClose}>
      <div className="modal wide" onPointerDown={(e) => e.stopPropagation()}>
        <h3>Model Library</h3>
        {library?.error && <p className="form-errors">{library.error}</p>}
        {library?.dir && <p className="hint">Folder (on the machine running the server): {library.dir}</p>}
        <p>
          {models.length} model{models.length === 1 ? '' : 's'} in {library?.files?.length ?? 0} file{library?.files?.length === 1 ? '' : 's'}
          {subckts.length ? `, plus ${subckts.length} subcircuit${subckts.length === 1 ? '' : 's'} (place them with Draw > Outputs and Labels > Subcircuit)` : ''}.
        </p>
        <pre className="netlist">
          {[...models, ...subckts].map((m) => `${m.name.padEnd(24)} ${m.type.padEnd(8)} ${m.file}`).join('\n') || '(empty)'}
        </pre>
        {(library?.problems ?? []).length > 0 && (
          <ul className="form-errors">{library.problems.map((p) => <li key={p}>{p}</li>)}</ul>
        )}
        <p className="hint">
          Upload a model file here, or copy it into the folder above and press Refresh. Then pick a model in a part's Edit dialog.
          Files may not run scripts, include other files by path, or read data files.
        </p>
        {note && <p className={note.ok ? 'hint' : 'form-errors'}>{note.message}</p>}
        {pending && (
          <div className="modal-buttons">
            <button type="button" onClick={() => send(pending.name, pending.content, true)}>Replace {pending.name}</button>
            <button type="button" onClick={() => { setPending(null); setNote(null); }}>Keep the old one</button>
          </div>
        )}
        <input ref={picker} type="file" multiple hidden accept=".lib,.mod,.model,.cir,.sp,.spi,.inc,.sub,.txt" onChange={pick} />
        <div className="modal-buttons">
          <button type="button" onClick={() => picker.current?.click()}>Upload…</button>
          <button type="button" onClick={onRefresh} disabled={loading}>{loading ? 'Loading…' : 'Refresh'}</button>
          <button type="button" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

/** Export (read-only text + Copy) or Import (paste, then Load) of a circuit as JSON text. */
export function TextDialog({ mode, text, onLoad, onClose }) {
  const [value, setValue] = useState(text ?? '');
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');
  const importing = mode === 'import';
  const copy = async () => {
    try { await navigator.clipboard.writeText(value); setCopied(true); } catch { setError('Copy failed; select the text and copy it by hand.'); }
  };
  const load = () => {
    try { onLoad(value); } catch (e) { setError(e.message); }
  };
  return (
    <div className="modal-backdrop" onPointerDown={onClose}>
      <div className="modal wide" onPointerDown={(e) => e.stopPropagation()}>
        <h3>{importing ? 'Import From Text' : 'Export As Text'}</h3>
        <textarea
          className="netlist textarea"
          value={value}
          readOnly={!importing}
          placeholder={importing ? 'Paste a circuit-ui JSON file here' : ''}
          onChange={(e) => { setValue(e.target.value); setError(''); }}
          rows={14}
        />
        {error && <p className="form-errors">{error}</p>}
        <div className="modal-buttons">
          {importing ? <button type="button" onClick={load} disabled={!value.trim()}>Load</button>
            : <button type="button" onClick={copy}>{copied ? 'Copied' : 'Copy'}</button>}
          <button type="button" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

export function ShortcutsDialog({ onClose }) {
  return (
    <div className="modal-backdrop" onPointerDown={onClose}>
      <div className="modal wide" onPointerDown={(e) => e.stopPropagation()}>
        <h3>Keyboard Shortcuts</h3>
        <p className="hint">Click the canvas first. Part keys pick the tool (same keys as CircuitJS1); Esc or Space returns to Select. Keys are case-sensitive: L, N and P need Shift.</p>
        <pre className="netlist">
          {[
            ...Object.entries(PART_SHORTCUTS).map(([t, k]) => `${k.padEnd(24)} Add ${getDef(t).label}`),
            '',
            ...OTHER_KEYS.map(([k, v]) => `${k.padEnd(24)} ${v}`),
          ].join('\n')}
        </pre>
        <div className="modal-buttons"><button type="button" onClick={onClose}>Close</button></div>
      </div>
    </div>
  );
}
