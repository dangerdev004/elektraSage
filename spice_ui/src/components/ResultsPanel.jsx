import { useEffect, useMemo, useRef, useState } from 'react';
import { Plotter, si, interp } from '../sim/plotter.js';
import { buildTraces, colorFor, defaultVisible, measure } from '../sim/results.js';

// Bottom strip: signal list + plot (transient / AC / DC sweep) or a value table (operating point).
// Also shows the "can't simulate" reasons, the engine status, and warnings.
const EDGES = ['n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw'];
const MIN_W = 320;
const MIN_H = 140;

export function ResultsPanel({ height, setHeight, status, result, errors, warnings, analysisLabel, floating, rect, setRect, onToggleDock, onClose }) {
  const drag = useRef(null);
  // floating window: drag by the header, resize from any edge or corner, always kept on screen
  const fdrag = useRef(null);
  const clampRect = (q) => {
    const W = window.innerWidth; const H = window.innerHeight;
    const w = Math.min(Math.max(MIN_W, q.w), W); const h = Math.min(Math.max(MIN_H, q.h), H);
    return { w, h, x: Math.min(Math.max(0, q.x), W - Math.min(w, 80)), y: Math.min(Math.max(0, q.y), H - 30) };
  };
  const fdown = (mode) => (e) => {
    if (e.button !== 0) return;
    if (mode === 'move' && e.target.closest('button')) return;
    fdrag.current = { mode, px: e.clientX, py: e.clientY, r: { ...rect } };
    e.currentTarget.setPointerCapture(e.pointerId);
    e.preventDefault();
  };
  const fmove = (e) => {
    const d = fdrag.current;
    if (!d) return;
    const dx = e.clientX - d.px; const dy = e.clientY - d.py;
    const q = { ...d.r };
    if (d.mode === 'move') { q.x += dx; q.y += dy; } else {
      if (d.mode.includes('e')) q.w = d.r.w + dx;
      if (d.mode.includes('s')) q.h = d.r.h + dy;
      if (d.mode.includes('w')) { q.w = Math.max(MIN_W, d.r.w - dx); q.x = d.r.x + d.r.w - q.w; }
      if (d.mode.includes('n')) { q.h = Math.max(MIN_H, d.r.h - dy); q.y = d.r.y + d.r.h - q.h; }
    }
    setRect(clampRect(q));
  };
  const fup = () => { fdrag.current = null; };

  const down = (e) => { drag.current = { y: e.clientY, h: height }; e.currentTarget.setPointerCapture(e.pointerId); };
  const move = (e) => {
    if (!drag.current) return;
    setHeight(Math.max(90, Math.min(window.innerHeight * 0.75, drag.current.h - (e.clientY - drag.current.y))));
  };
  const up = () => { drag.current = null; };

  return (
    <section className={`results${floating ? ' floating' : ''}`} style={floating ? { left: rect.x, top: rect.y, width: rect.w, height: rect.h } : { height }}>
      {!floating && <div className="scope-handle" onPointerDown={down} onPointerMove={move} onPointerUp={up} title="Drag to resize" />}
      {floating && EDGES.map((m) => (
        <div key={m} className={`win-edge e-${m}`} onPointerDown={fdown(m)} onPointerMove={fmove} onPointerUp={fup} />
      ))}
      <div
        className={`results-head${floating ? ' draggable' : ''}`}
        onPointerDown={floating ? fdown('move') : undefined} onPointerMove={floating ? fmove : undefined} onPointerUp={floating ? fup : undefined}
      >
        <span className="results-title">Results</span>
        <span className="results-sub">{analysisLabel}</span>
        <span className={`results-status ${status.state}`}>{status.message}</span>
        <button type="button" className="win-btn" onClick={onToggleDock} title={floating ? 'Dock to the bottom' : 'Undock into a floating window'}>{floating ? 'Dock' : 'Undock'}</button>
        <button type="button" className="win-btn" onClick={onClose} title="Hide the results (View > Show Results brings it back)">✕</button>
      </div>
      <div className="results-body">
        {errors.length > 0 ? (
          <Problems errors={errors} warnings={warnings} />
        ) : result ? (
          <ResultView key={result.id} result={result} warnings={warnings} />
        ) : (
          <div className="results-empty">
            {status.state === 'running'
              ? 'Simulating…'
              : <>Press <b>RUN</b> (or Ctrl+Enter) to simulate this circuit. Traces appear here.</>}
            {warnings.length > 0 && <ul className="warn">{warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
          </div>
        )}
      </div>
    </section>
  );
}

function Problems({ errors, warnings }) {
  return (
    <div className="problems">
      <div className="problems-title">Can't simulate yet:</div>
      <ul>{errors.map((e) => <li key={e}>{e}</li>)}</ul>
      {warnings.length > 0 && <ul className="warn">{warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
    </div>
  );
}

function ResultView({ result, warnings }) {
  const [visible, setVisible] = useState(() => defaultVisible(result));
  const [showPhase, setShowPhase] = useState(true);
  const [cursors, setCursors] = useState([null, null]);
  const canvasRef = useRef(null);
  const plotter = useRef(null);
  const isOp = result.analysis === 'op';

  const data = useMemo(() => buildTraces(result, visible, { showPhase }), [result, visible, showPhase]);

  useEffect(() => {
    if (isOp || !canvasRef.current) return undefined;
    const p = new Plotter(canvasRef.current, { onCursor: (c) => setCursors([...c]) });
    plotter.current = p;
    return () => { p.destroy(); plotter.current = null; };
  }, [isOp]);

  useEffect(() => {
    plotter.current?.setData(data, [null, null]);
    setCursors([null, null]);
  }, [data]);

  const toggle = (label) => {
    const next = new Set(visible);
    if (next.has(label)) next.delete(label); else next.add(label);
    setVisible(next);
  };

  if (isOp) {
    return (
      <div className="op-table">
        <table>
          <thead><tr><th>Signal</th><th>Value</th></tr></thead>
          <tbody>
            {result.vectors.map((v) => (
              <tr key={v.label}><td>{v.label}</td><td>{si(v.real[0], 4)}{v.unit}</td></tr>
            ))}
          </tbody>
        </table>
        {warnings.length > 0 && <ul className="warn">{warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
      </div>
    );
  }

  const readout = cursors.map((cx, k) => {
    if (cx == null) return null;
    const vals = data.traces.map((t) => `${t.name} = ${si(interp(t.x, t.y, cx), 4)}${t.unit}`).join('   ');
    return <div key={k}>C{k + 1} @ {si(cx, 4)}{result.xUnit}: {vals}</div>;
  });
  const firstVisible = result.vectors.find((v) => visible.has(v.label));
  const stats = firstVisible ? measure(result, firstVisible.label, (x) => `${si(x, 4)}${firstVisible.unit}`) : [];

  return (
    <div className="plot-layout">
      <div className="signals">
        {result.vectors.map((v) => (
          <label key={v.label} className="signal">
            <input type="checkbox" checked={visible.has(v.label)} onChange={() => toggle(v.label)} />
            <span className="swatch" style={{ background: colorFor(result, v.label) }} />
            {v.label}
          </label>
        ))}
        {result.analysis === 'ac' && (
          <label className="signal opt">
            <input type="checkbox" checked={showPhase} onChange={() => setShowPhase(!showPhase)} />
            show phase
          </label>
        )}
      </div>
      <div className="plot-col">
        <div className="plot-wrap"><canvas ref={canvasRef} /></div>
        <div className="plot-notes">
          {readout.some(Boolean)
            ? readout
            : <span>Click the plot to place cursor 1 (Shift-click for cursor 2, right-click clears). Wheel zooms, drag pans, double-click fits.</span>}
          {stats.length > 0 && !readout.some(Boolean) && (
            <div>{firstVisible.label}: {stats.map(([k, v]) => `${k} ${v}`).join('   ')}</div>
          )}
          {warnings.length > 0 && <ul className="warn">{warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
        </div>
      </div>
    </div>
  );
}
