// import React from "react";
// import "./Sidebar.css";

// export default function Sidebar() {
//   return (
//     <aside className="sidebar">
//       <h3>Options</h3>
//     </aside>
//   );
// }

import React from "react";
import "./Sidebar.css";

export default function Sidebar({ 
  simRunning, 
  onToggleSimulation, 
  onReset,
  speedValue,
  onSpeedChange,
  currentValue,
  onCurrentChange,
  powerValue,
  onPowerChange,
  circuitTitle,
  powerBarEnabled
}) {
  return (
    <aside className="sidebar">
      <h3>Controls</h3>
      
      {/* Reset and Run/Stop Buttons */}
      <div className="button-panel">
        <button 
          className="control-button" 
          onClick={onReset}
        >
          Reset
        </button>
        <button 
          className={`control-button ${simRunning ? 'stop' : 'run'}`}
          onClick={onToggleSimulation}
          dangerouslySetInnerHTML={{
            __html: simRunning 
              ? 'Run&nbsp;/&nbsp;<strong>STOP</strong>' 
              : '<strong>RUN</strong>&nbsp;/&nbsp;Stop'
          }}
        />
      </div>

      {/* Simulation Speed Control */}
      <div className="control-group">
        <label className="control-label">Simulation Speed</label>
        <input
          type="range"
          className="slider"
          min="0"
          max="260"
          value={speedValue}
          onChange={(e) => onSpeedChange(parseInt(e.target.value))}
        />
      </div>

      {/* Current Speed Control */}
      <div className="control-group">
        <label className="control-label">Current Speed</label>
        <input
          type="range"
          className="slider"
          min="1"
          max="100"
          value={currentValue}
          onChange={(e) => onCurrentChange(parseInt(e.target.value))}
        />
      </div>

      {/* Power Brightness Control */}
      <div className="control-group">
        <label 
          className={`control-label ${!powerBarEnabled ? 'disabled' : ''}`}
        >
          Power Brightness
        </label>
        <input
          type="range"
          className="slider"
          min="1"
          max="100"
          value={powerValue}
          onChange={(e) => onPowerChange(parseInt(e.target.value))}
          disabled={!powerBarEnabled}
        />
      </div>

      {/* Circuit Title */}
      <div className="circuit-info">
        <label className="info-label">Current Circuit:</label>
        <div className="circuit-title">
          {circuitTitle || "Untitled Circuit"}
        </div>
      </div>
    </aside>
  );
}