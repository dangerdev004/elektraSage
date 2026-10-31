// Right-hand panel. Same controls and order as CirSim.java ~733-789:
// Reset, RUN / Stop, Simulation Speed, Current Speed, Power Brightness, Current Circuit.
//
// What they do here: RUN runs the chosen analysis once in the WASM ngspice engine (it is a
// batch solver, not CircuitJS1's endless animation), Stop abandons a run in progress, Reset clears
// the results. The two speed sliders and Power Brightness are not connected to anything yet.

export function SidePanel({
  running, onReset, onToggleRun, sliders, setSliders, powerEnabled, title,
  analysisLabel, onSetup, status,
}) {
  const set = (k) => (e) => setSliders({ ...sliders, [k]: Number(e.target.value) });
  return (
    <aside className="side">
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

      <label className="side-label">Simulation Speed</label>
      <input type="range" min="0" max="260" value={sliders.speed} onChange={set('speed')} disabled />

      <label className="side-label">Current Speed</label>
      <input type="range" min="1" max="100" value={sliders.current} onChange={set('current')} disabled />

      <label className={`side-label${powerEnabled ? '' : ' dim'}`}>Power Brightness</label>
      <input
        type="range" min="1" max="100" value={sliders.power}
        onChange={set('power')} disabled
      />

      <label className="side-label">Current Circuit:</label>
      <div className="circuit-title">{title}</div>

      <p className="side-note">
        The three sliders are greyed out because there is no animated simulation yet.
      </p>
    </aside>
  );
}
