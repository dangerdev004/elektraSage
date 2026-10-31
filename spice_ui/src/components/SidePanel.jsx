// Right-hand panel. Same controls and order as CirSim.java ~733-789:
// Reset, RUN / Stop, Simulation Speed, Current Speed, Power Brightness, Current Circuit.
//
// What they do here: RUN runs the chosen analysis once in the WASM ngspice engine (it is a
// batch solver, not CircuitJS1's endless animation), Stop abandons a run in progress, Reset clears
// the results. The two speed sliders and Power Brightness are not connected to anything yet.

import { useRef, useState } from 'react';
import { ChatPanel } from './ChatPanel.jsx';

const MIN_W = 150;
const load = () => {
  try { const s = JSON.parse(localStorage.getItem('circuit-ui.side') ?? 'null'); if (s && Number.isFinite(s.w)) return { w: s.w, collapsed: !!s.collapsed }; } catch { /* ignore */ }
  return { w: 260, collapsed: false };
};

export function SidePanel({
  running, onReset, onToggleRun, sliders, setSliders, powerEnabled, title,
  analysisLabel, onSetup, status, getNetlist,
}) {
  const [state, setState] = useState(load);
  const drag = useRef(null);
  const update = (patch) => setState((s) => {
    const n = { ...s, ...patch };
    try { localStorage.setItem('circuit-ui.side', JSON.stringify(n)); } catch { /* ignore */ }
    return n;
  });
  const maxW = () => Math.max(MIN_W, Math.floor(window.innerWidth * 0.6));
  const down = (e) => { drag.current = { x: e.clientX, w: state.w }; e.currentTarget.setPointerCapture(e.pointerId); e.preventDefault(); };
  const move = (e) => { if (drag.current) update({ w: Math.round(Math.min(maxW(), Math.max(MIN_W, drag.current.w - (e.clientX - drag.current.x)))) }); };
  const up = () => { drag.current = null; };
  if (state.collapsed) {
    return (
      <aside className="side collapsed">
        <button type="button" className="mini" title="Show the side panel" onClick={() => update({ collapsed: false })}>«</button>
      </aside>
    );
  }
  const set = (k) => (e) => setSliders({ ...sliders, [k]: Number(e.target.value) });
  return (
    <aside className="side" style={{ width: Math.min(state.w, maxW()) }}>
      <div className="side-grip" onPointerDown={down} onPointerMove={move} onPointerUp={up} title="Drag to resize" />
      <button type="button" className="mini collapse" title="Hide the side panel" onClick={() => update({ collapsed: true })}>»</button>
      <div className="side-buttons">
        <button type="button" className="top-button" onClick={onReset}>Reset</button>
        <button type="button" className="top-button" onClick={onToggleRun}>
          {running ? <>RUN / <strong>Stop</strong></> : <><strong>RUN</strong> / Stop</>}
        </button>
      </div>

      <label className="side-label">Analysis</label>
      <button type="button" className="top-button wide" onClick={onSetup} title="Choose the analysis and its settings">
        {analysisLabel} …
      </button>
      <div className={`side-status ${status.state}`}>{status.message}</div>

      <label className="side-label">Current Circuit:</label>
      <div className="circuit-title">{title}</div>

      <ChatPanel getNetlist={getNetlist} />
    </aside>
  );
}
