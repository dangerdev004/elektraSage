import { useEffect, useRef, useState } from 'react';
import { getDef } from '../canvas/parts.js';
import { PART_PARAMS, OPAMP_PRESETS, opampParam, stepText, withUnit } from '../sim/params.js';

// Minimal "Edit..." dialog: one free-text value per part (shown next to the symbol).
// CircuitJS1's real dialogs have one field per parameter; that comes with the simulator.
// which `.model` TYPE each part accepts
export const MODEL_TYPE = { DiodeElm: 'D', LEDElm: 'D', ZenerElm: 'D', NTransistorElm: 'NPN', PTransistorElm: 'PNP', NMosfetElm: 'NMOS', PMosfetElm: 'PMOS' };

export function EditDialog({ element, library, onOk, onCancel }) {
  const def = getDef(element.type);
  const [value, setValue] = useState(element.value ?? def.value ?? '');
  const wanted = MODEL_TYPE[element.type];
  const choices = wanted ? (library?.models ?? []).filter((m) => m.kind === 'model' && m.type === wanted) : [];
  const [model, setModel] = useState(element.model ?? '');
  // keep a model that is on the part but no longer in the library visible, so it is not silently dropped
  const missing = model && !choices.some((m) => m.name === model);
  const ref = useRef(null);

  useEffect(() => {
    ref.current?.focus();
    ref.current?.select();
  }, []);

  const submit = (e) => {
    e.preventDefault();
    onOk(value.trim(), wanted ? model : undefined);
  };

  return (
    <div className="modal-backdrop" onPointerDown={onCancel}>
      <form className="modal" onPointerDown={(e) => e.stopPropagation()} onSubmit={submit}>
        <h3>Edit {def.label}</h3>
        <label className="field">
          <span>Value (label)</span>
          <input ref={ref} value={value} onChange={(e) => setValue(e.target.value)} />
        </label>
        {wanted && (
          <label className="field">
            <span>Model ({wanted})</span>
            <select value={model} onChange={(ev) => setModel(ev.target.value)}>
              <option value="">Built-in default</option>
              {missing && <option value={model}>{model} (not in library)</option>}
              {choices.map((m) => <option key={m.name} value={m.name}>{m.name}  [{m.file}]</option>)}
            </select>
          </label>
        )}
        {wanted && !choices.length && (
          <p className="hint">
            {library?.error ? `Model library unavailable: ${library.error}` : `No ${wanted} models found. Put a .lib file in the models folder (Simulation > Model Library...).`}
          </p>
        )}
        <div className="modal-buttons">
          <button type="submit">OK</button>
          <button type="button" onClick={onCancel}>Cancel</button>
        </div>
      </form>
    </div>
  );
}


/**
 * Parameter dialog for diodes, transistors and op amps: one labelled field per parameter, with
 * "-" / "+" buttons that step through a 1-2-5 series. Semiconductor fields left empty mean "SPICE
 * default" and are not written to the netlist; op-amp fields start filled with this app's defaults.
 */
export function ParamDialog({ element, library, onApply, onOk, onCancel }) {
  const spec = PART_PARAMS[element.type];
  const def = getDef(element.type);
  const isOpamp = !!spec.opamp;
  const seed = spec.initial?.(element); // starting text for fields that come from the old value label
  const initial = () => {
    const v = {};
    for (const f of spec.fields) {
      if (f.kind === 'check') v[f.key] = String(element.params?.[f.key]) === 'true';
      else if (f.kind === 'select') v[f.key] = element.params?.[f.key] ?? f.def;
      else v[f.key] = isOpamp ? opampParam(element, f.key) : (element.params?.[f.key] ?? seed?.[f.key] ?? '');
    }
    return v;
  };
  const [vals, setVals] = useState(initial);
  const [value, setValue] = useState(element.value ?? def.value ?? '');
  const [model, setModel] = useState(element.model ?? '');
  const first = useRef(null);
  useEffect(() => { first.current?.focus(); }, []);

  const choices = spec.modelType ? (library?.models ?? []).filter((m) => m.kind === 'model' && m.type === spec.modelType) : [];
  const missing = model && !choices.some((m) => m.name === model);

  const set = (key, v) => setVals((o) => ({ ...o, [key]: v }));
  const pickPreset = (name) => setVals((o) => ({ ...o, preset: name, ...OPAMP_PRESETS[name] }));

  const patch = () => {
    const params = {};
    for (const f of spec.fields) {
      const v = vals[f.key];
      if (f.kind === 'check') { if (v) params[f.key] = 'true'; } else if (String(v).trim() !== '') params[f.key] = String(v).trim();
    }
    const label = spec.compose ? spec.compose(vals) : spec.valueLabel ? withUnit(value.trim(), spec.valueUnit) : undefined;
    return { value: label, model: spec.modelType ? model : undefined, params };
  };
  const submit = (ev) => { ev.preventDefault(); onOk(patch()); };

  return (
    <div className="modal-backdrop" onPointerDown={onCancel}>
      <form className="modal params" onPointerDown={(e) => e.stopPropagation()} onSubmit={submit}>
        <h3>Edit {spec.title}</h3>
        {spec.valueLabel && (
          <div className="pfield">
            <label>{spec.valueLabel}</label>
            <div className="stepper">
              <button type="button" onClick={() => setValue(stepText(value, -1, spec.valueDef ?? '5', spec.valueUnit === 'Ω' ? '' : spec.valueUnit))}>−</button>
              <input ref={first} value={value} onChange={(ev) => setValue(ev.target.value)} />
              <button type="button" onClick={() => setValue(stepText(value, 1, spec.valueDef ?? '5', spec.valueUnit === 'Ω' ? '' : spec.valueUnit))}>+</button>
            </div>
          </div>
        )}
        {spec.modelType && (
          <div className="pfield">
            <label>Model</label>
            <select value={model} onChange={(ev) => setModel(ev.target.value)}>
              <option value="">Generic (editable parameters below)</option>
              {missing && <option value={model}>{model} (not in library)</option>}
              {choices.map((m) => <option key={m.name} value={m.name}>{m.name}  [{m.file}]</option>)}
            </select>
          </div>
        )}
        {spec.fields.map((f, i) => {
          if (f.kind === 'select') {
            return (
              <div className="pfield" key={f.key}>
                <label>{f.label}</label>
                <select value={vals[f.key]} onChange={(ev) => pickPreset(ev.target.value)}>
                  {f.options.map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
            );
          }
          if (f.kind === 'check') {
            return (
              <label className="pcheck" key={f.key}>
                <input type="checkbox" checked={!!vals[f.key]} onChange={(ev) => set(f.key, ev.target.checked)} /> {f.label}
              </label>
            );
          }
          const disabled = !!model;
          return (
            <div className="pfield" key={f.key}>
              <label>{f.label}</label>
              <div className="stepper">
                <button type="button" disabled={disabled} onClick={() => set(f.key, stepText(vals[f.key], -1, f.def ?? '1'))}>−</button>
                <input
                  ref={i === 0 && !spec.valueLabel ? first : undefined}
                  value={vals[f.key]}
                  placeholder={isOpamp ? '' : 'default'}
                  disabled={disabled}
                  onChange={(ev) => set(f.key, ev.target.value)}
                />
                <button type="button" disabled={disabled} onClick={() => set(f.key, stepText(vals[f.key], 1, f.def ?? '1'))}>+</button>
              </div>
            </div>
          );
        })}
        {model && <p className="hint">A library model is selected, so the generic parameters are not used.</p>}
        {spec.note && !isOpamp && <p className="hint">{spec.note}</p>}
        {spec.modelType && !choices.length && !library?.error && <p className="hint">No {spec.modelType} models in the library folder (optional).</p>}
        <div className="modal-buttons spread">
          <button type="button" onClick={() => onApply(patch())}>Apply</button>
          <button type="submit">OK</button>
          <button type="button" onClick={onCancel}>Cancel</button>
        </div>
      </form>
    </div>
  );
}

export function AboutDialog({ onClose }) {
  return (
    <div className="modal-backdrop" onPointerDown={onClose}>
      <div className="modal" onPointerDown={(e) => e.stopPropagation()}>
        <h3>About</h3>
        <p>
          A CircuitJS1-style circuit editor front end. Menus follow CircuitJS1's CirSim.java. Simulation
          is done by a local ngspice through the server in this project (npm run server).
        </p>
        <div className="modal-buttons"><button type="button" onClick={onClose}>OK</button></div>
      </div>
    </div>
  );
}
