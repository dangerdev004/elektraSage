import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Editor } from './canvas/editor.js';
import { CircuitCanvas } from './components/CircuitCanvas.jsx';
import { MenuBar, ContextMenu } from './components/MenuBar.jsx';
import { Toolbar } from './components/Toolbar.jsx';
import { SidePanel } from './components/SidePanel.jsx';
import { ResultsPanel } from './components/ResultsPanel.jsx';
import { EditDialog, ParamDialog, AboutDialog } from './components/EditDialog.jsx';
import { PART_PARAMS } from './sim/params.js';
import { AnalysisDialog, NetlistDialog, ModelLibraryDialog, TextDialog, ShortcutsDialog } from './components/SimDialogs.jsx';
import {
  buildMenus, ELEMENT_MENU, DEFAULT_UI_OPTIONS, WORKING_OPTIONS, OPTION_ITEMS,
} from './data/menus.js';
import { SAMPLES } from './data/samples.js';
import { getDef } from './canvas/parts.js';
import { analyzeNodes, buildCircuitNetlist } from './sim/netlist.js';
import { ANALYSES, defaultAnalysis } from './sim/analysis.js';
import { NgspiceServerEngine } from './sim/engine-server.js';
import { si } from './sim/plotter.js';

const MENUS = buildMenus();

// command -> human label, used for "not wired yet" messages
const LABEL_OF = {};
(function walk(items) {
  for (const it of items) {
    if (it === '---') continue;
    if (it.items) walk(it.items);
    else if (it.cmd) LABEL_OF[it.cmd] = it.label;
  }
})([...MENUS.flatMap((m) => m.items), ...ELEMENT_MENU]);

const NEEDS_SELECTION = new Set([
  'edit.cut', 'edit.copy', 'edit.delete', 'edit.duplicate', 'edit.flipx', 'edit.flipy',
  'edit.flipxy', 'elm.flip',
]);

const READY = { state: 'idle', message: 'Ready' };

export default function App() {
  const [editor] = useState(() => new Editor());
  const [engine] = useState(() => new NgspiceServerEngine());
  const [st, setSt] = useState(editor.state());
  const [opts, setOpts] = useState(DEFAULT_UI_OPTIONS);
  const [sliders, setSliders] = useState({ speed: 3, current: 50, power: 50 });
  const [title, setTitle] = useState('Blank circuit');
  const [toast, setToast] = useState('');
  const [ctxMenu, setCtxMenu] = useState(null);
  const [editing, setEditing] = useState(null);
  const [about, setAbout] = useState(false);
  const [panelH, setPanelH] = useState(240);

  const [analysis, setAnalysis] = useState(defaultAnalysis);
  const [status, setStatus] = useState(READY);
  const [result, setResult] = useState(null);
  const [errors, setErrors] = useState([]);
  const [warnings, setWarnings] = useState([]);
  const [setupOpen, setSetupOpen] = useState(false);
  const [netlistView, setNetlistView] = useState(null);
  const [library, setLibrary] = useState({ models: [], files: [], problems: [], dir: '' });
  const [libLoading, setLibLoading] = useState(false);
  const [libOpen, setLibOpen] = useState(false);
  const [textDlg, setTextDlg] = useState(null);
  const [keysOpen, setKeysOpen] = useState(false);
  const fileInput = useRef(null);

  const toastTimer = useRef(0);
  const runToken = useRef(0);
  const resultCount = useRef(0);
  const nodeCache = useRef({ key: '', nodes: null });
  const resultRef = useRef(null);
  resultRef.current = result;

  const running = status.state === 'running';

  const notify = useCallback((text) => {
    setToast(text);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(''), 2800);
  }, []);

  const makeNetlist = useCallback((an = analysis) => buildCircuitNetlist({
    elements: editor.els, terminalsOf: (e) => editor.terminals(e), title, analysis: an, library: library.models,
  }), [editor, analysis, title, library]);

  const refreshLibrary = useCallback(async () => {
    setLibLoading(true);
    try {
      const r = await fetch('/api/models');
      const body = await r.json();
      if (!r.ok) throw new Error(body.error ?? `HTTP ${r.status}`);
      setLibrary({ ...body, error: '' });
    } catch (e) {
      setLibrary((l) => ({ ...l, models: [], error: `Could not read the model library (${e.message}). Is the server running? Start it with "npm run server".` }));
    } finally {
      setLibLoading(false);
    }
  }, []);
  useEffect(() => { refreshLibrary(); }, [refreshLibrary]);

  const saveFile = useCallback(() => {
    const text = JSON.stringify(editor.toDocument(title), null, 2);
    const url = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(title || 'circuit').replace(/[^\w.\- ]+/g, '_')}.circuit.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }, [editor, title]);


  const clearResults = useCallback(() => {
    runToken.current += 1; // abandon anything in flight
    setResult(null);
    setErrors([]);
    setWarnings([]);
    setStatus(READY);
  }, []);

  const loadText = useCallback((text) => {
    let doc;
    try { doc = JSON.parse(text); } catch { throw new Error('That is not valid JSON.'); }
    const t = editor.loadDocument(doc);
    setTitle(t || 'Untitled circuit');
    clearResults();
  }, [editor, clearResults]);

  const runSim = useCallback(async () => {
    const nl = makeNetlist();
    setWarnings(nl.warnings);
    if (!nl.ok) {
      runToken.current += 1;
      setErrors(nl.errors);
      setResult(null);
      setStatus({ state: 'error', message: `Can't simulate: ${nl.errors.length} problem${nl.errors.length > 1 ? 's' : ''}` });
      return;
    }
    setErrors([]);
    const token = ++runToken.current;
    setStatus({
      state: 'running',
      message: 'Running ngspice…',
    });
    try {
      const res = await engine.run({ netlist: nl.text, analysisType: analysis.type, libs: nl.libs });
      if (token !== runToken.current) return; // stopped or reset while it ran
      resultCount.current += 1;
      const points = res.x ? res.x.length : 1;
      setResult({ ...res, id: resultCount.current, snapshot: editor.snapshot() });
      setStatus({ state: 'done', message: `Done: ${points} point${points === 1 ? '' : 's'}` });
    } catch (e) {
      if (token !== runToken.current) return;
      console.error(e);
      setResult(null);
      setErrors([e.message]);
      setStatus({ state: 'error', message: 'Simulation failed' });
    }
  }, [editor, engine, makeNetlist, analysis]);

  const stopSim = useCallback(() => {
    if (!running) return;
    runToken.current += 1;
    setStatus({ state: 'idle', message: 'Stopped (the engine finishes in the background; its result is discarded)' });
  }, [running]);

  // Clicking a switch re-runs the simulation, but only once there is a result on screen to refresh.
  const hasResult = useRef(false);
  useEffect(() => { hasResult.current = !!result; }, [result]);
  useEffect(() => {
    editor.onToggle = () => { if (hasResult.current) runSim(); };
    return () => { editor.onToggle = null; };
  }, [editor, runSim]);

  // wire the editor's callbacks once, and load the starting circuit
  useEffect(() => {
    editor.onChange = setSt;
    editor.onNotice = notify;
    editor.onContextMenu = setCtxMenu;
    editor.onEdit = (el) => setEditing(el);
    editor.loadElements([]);
    return () => {
      editor.onChange = null;
      editor.onNotice = null;
      editor.onContextMenu = null;
      editor.onEdit = null;
      editor.onShortcut = null;
      editor.describeExtra = null;
    };
  }, [editor, notify]);

  // hover text: which SPICE node a wire belongs to (and its value after an operating-point run)
  useEffect(() => {
    editor.describeExtra = (el) => {
      if (el.type === 'GroundElm') return 'node 0';
      if (el.type !== 'WireElm') return '';
      const key = editor.snapshot();
      if (nodeCache.current.key !== key) {
        nodeCache.current = { key, nodes: analyzeNodes(editor.els, (e) => editor.terminals(e)) };
      }
      const node = nodeCache.current.nodes.nodeOfTerminal(el, 0);
      const r = resultRef.current;
      const v = r && r.analysis === 'op' ? r.vectors.find((x) => x.label === `v(${node})`) : null;
      return v ? `node ${node} = ${si(v.real[0], 4)}V` : `node ${node}`;
    };
  }, [editor]);

  // node labels: the same n1, n2, ... names that appear in the results list
  useEffect(() => {
    let cache = { rev: -1, labels: [] };
    editor.nodeLabelProvider = () => {
      if (cache.rev !== editor.rev) {
        const nodes = analyzeNodes(editor.els, (e) => editor.terminals(e));
        const seen = new Set();
        const labels = [];
        for (const el of editor.els) {
          editor.terminals(el).forEach((p, i) => {
            const name = nodes.nodeOfTerminal(el, i);
            if (name === '0' || seen.has(name)) return;
            seen.add(name);
            labels.push({ x: p.x, y: p.y, text: name });
          });
        }
        cache = { rev: editor.rev, labels };
      }
      return cache.labels;
    };
    return () => { editor.nodeLabelProvider = null; };
  }, [editor]);

  // options that change the editor
  useEffect(() => {
    editor.setOptions({
      showValues: opts.showValues, smallGrid: opts.smallGrid, euro: opts.euro,
      white: opts.white, crosshair: opts.crosshair, noEdit: opts.noEdit, nodeLabels: opts.nodeLabels,
    });
  }, [editor, opts]);

  const run = useCallback((cmd) => {
    if (cmd.startsWith('opt:')) {
      const key = cmd.slice(4);
      setOpts((o) => {
        const next = { ...o, [key]: !o[key] };
        // Show Voltage and Show Power are mutually exclusive (CirSim.java ~596-610)
        if (key === 'showVoltage' && next.showVoltage) next.showPower = false;
        if (key === 'showPower' && next.showPower) next.showVoltage = false;
        return next;
      });
      if (!WORKING_OPTIONS.has(key)) {
        notify(`"${OPTION_ITEMS.find((x) => x[0] === key)?.[1]}" only changes the checkbox for now.`);
      }
      return;
    }
    if (cmd.startsWith('sample:')) {
      const s = SAMPLES[cmd.slice(7)];
      editor.loadElements(s.elements);
      setTitle(s.title);
      clearResults();
      return;
    }
    switch (cmd) {
      case 'options.shortcuts': return setKeysOpen(true);
      case 'sim.models': refreshLibrary(); return setLibOpen(true);
      case 'file.exportaslocalfile': return saveFile();
      case 'file.importfromlocalfile': return void fileInput.current?.click();
      case 'file.exportastext': return setTextDlg({ mode: 'export', text: JSON.stringify(editor.toDocument(title), null, 2) });
      case 'file.importfromtext': return setTextDlg({ mode: 'import', text: '' });
      case 'sim.run': return void runSim();
      case 'sim.stop': return stopSim();
      case 'sim.setup': return setSetupOpen(true);
      case 'sim.clear': return clearResults();
      case 'sim.netlist': return setNetlistView(makeNetlist());
      case 'file.about': return setAbout(true);
      case 'view.fullscreen':
        if (document.fullscreenElement) document.exitFullscreen?.();
        else document.documentElement.requestFullscreen?.();
        return undefined;
      case 'elm.edit': {
        const el = editor.selected().find((e) => getDef(e.type).kind !== 'wire');
        if (el) setEditing(el); else notify('Select a part first (wires have no value to edit).');
        return undefined;
      }
      default:
    }
    if (editor.exec(cmd)) {
      if (cmd === 'file.newblankcircuit') { setTitle('Blank circuit'); clearResults(); }
      return undefined;
    }
    notify(`"${LABEL_OF[cmd] ?? cmd}" is not wired up yet.`);
    return undefined;
  }, [editor, notify, runSim, stopSim, clearResults, makeNetlist, refreshLibrary, saveFile, title]);

  // after a dialog closes, give the keyboard back to the canvas so part keys (r, w, d ...) work again
  const anyDialog = !!(editing || setupOpen || netlistView || libOpen || textDlg || keysOpen || about);
  const wasDialog = useRef(false);
  useEffect(() => {
    if (wasDialog.current && !anyDialog) editor.canvas?.focus();
    wasDialog.current = anyDialog;
  }, [anyDialog, editor]);

  // keyboard shortcuts that belong to the app rather than the editor (Ctrl+Enter, Ctrl+S, Ctrl+O)
  useEffect(() => {
    editor.onShortcut = (cmd) => run(cmd);
  }, [editor, run]);

  const ctx = useMemo(() => ({
    run,
    isChecked(cmd) {
      if (cmd.startsWith('opt:')) return !!opts[cmd.slice(4)];
      if (cmd.startsWith('mode:')) return st.mode === cmd.slice(5);
      return undefined;
    },
    isDisabled(cmd) {
      if (!cmd) return false;
      if (cmd === 'edit.undo') return !st.canUndo;
      if (cmd === 'edit.redo') return !st.canRedo;
      if (cmd === 'edit.paste') return !st.canPaste;
      if (cmd === 'sim.stop') return !running;
      if (NEEDS_SELECTION.has(cmd)) return st.selCount === 0;
      return false;
    },
  }), [run, opts, st, running]);

  const closeCtx = useCallback(() => setCtxMenu(null), []);

  // results belong to the circuit as it was when RUN was pressed; say so when it has changed
  const stale = !!result && result.snapshot !== editor.snapshot();
  const shownStatus = stale && status.state === 'done'
    ? { state: 'stale', message: 'Circuit changed since this run. Press RUN again.' }
    : status;

  return (
    <div className="app">
      <MenuBar menus={MENUS} ctx={ctx} />
      {opts.toolbar && <Toolbar mode={st.mode} run={run} />}

      <div className="main">
        <div className="work">
          <div className="canvas-area">
            <CircuitCanvas editor={editor} />
            <div className="info">
              <div className="info-hover">{st.info || ' '}</div>
              <div className="info-dim">
                zoom {st.zoom}% · {st.count} parts{st.selCount ? ` · ${st.selCount} selected` : ''}
              </div>
            </div>
            {toast && <div className="toast" role="status">{toast}</div>}
          </div>
          <ResultsPanel
            height={panelH}
            setHeight={setPanelH}
            status={shownStatus}
            result={result}
            errors={errors}
            warnings={warnings}
            analysisLabel={ANALYSES[analysis.type].label}
          />
        </div>

        <SidePanel
          running={running}
          onReset={clearResults}
          onToggleRun={() => (running ? stopSim() : runSim())}
          sliders={sliders}
          setSliders={setSliders}
          powerEnabled={opts.showPower}
          title={title}
          analysisLabel={ANALYSES[analysis.type].label}
          onSetup={() => setSetupOpen(true)}
          status={shownStatus}
        />
      </div>

      {ctxMenu && (
        <ContextMenu
          x={ctxMenu.x}
          y={ctxMenu.y}
          items={ctxMenu.onElement ? ELEMENT_MENU : MENUS.find((m) => m.label === 'Draw').items}
          ctx={ctx}
          close={closeCtx}
        />
      )}
      {editing && (PART_PARAMS[editing.type] ? (
        <ParamDialog
          key={editing.id}
          element={editing}
          library={library}
          onApply={(p) => editor.setProps(editing.id, p)}
          onOk={(p) => { editor.setProps(editing.id, p); setEditing(null); }}
          onCancel={() => setEditing(null)}
        />
      ) : (
        <EditDialog
          element={editing}
          library={library}
          onOk={(v, model) => { editor.setValue(editing.id, v, model); setEditing(null); }}
          onCancel={() => setEditing(null)}
        />
      ))}
      {setupOpen && (
        <AnalysisDialog
          analysis={analysis}
          sources={makeNetlist(analysis).sources}
          onOk={(a) => { setAnalysis(a); setSetupOpen(false); }}
          onCancel={() => setSetupOpen(false)}
        />
      )}
      {keysOpen && <ShortcutsDialog onClose={() => setKeysOpen(false)} />}
      {libOpen && <ModelLibraryDialog library={library} loading={libLoading} onRefresh={refreshLibrary} onClose={() => setLibOpen(false)} />}
      {textDlg && (
        <TextDialog
          mode={textDlg.mode}
          text={textDlg.text}
          onLoad={(t) => { loadText(t); setTextDlg(null); }}
          onClose={() => setTextDlg(null)}
        />
      )}
      <input
        ref={fileInput}
        type="file"
        accept=".json,application/json"
        style={{ display: 'none' }}
        onChange={async (ev) => {
          const f = ev.target.files?.[0];
          ev.target.value = '';
          if (!f) return;
          if (f.size > 5 * 1024 * 1024) { notify('That file is larger than 5 MB; not loading it.'); return; }
          try { loadText(await f.text()); notify(`Opened ${f.name}`); } catch (e) { notify(`Could not open ${f.name}: ${e.message}`); }
        }}
      />
      {netlistView && <NetlistDialog netlist={netlistView} onClose={() => setNetlistView(null)} />}
      {about && <AboutDialog onClose={() => setAbout(false)} />}
    </div>
  );
}
