// Menu bar content. Labels, order and shortcuts follow CirSim.java (constructor, ~lines 475-695).
// A leaf item is { label, cmd, shortcut?, disabled? }. A submenu has { label, items }.
// '---' is a separator.

import { TOP_PARTS, GROUPS, DRAG_MODES } from './catalog.js';
import { SAMPLE_MENU, SAMPLES } from './samples.js';
import { PART_SHORTCUTS } from './shortcuts.js';

const SEP = '---';
const add = ([id, label]) => ({
  label: `Add ${label}`, cmd: `mode:add:${id}`, ...(PART_SHORTCUTS[id] ? { shortcut: PART_SHORTCUTS[id] } : {}),
});

export const OPTION_ITEMS = [
  // [option key, label]  (CirSim.java ~594-675)
  ['showCurrent', 'Show Current'],
  ['showVoltage', 'Show Voltage'],
  ['showPower', 'Show Power'],
  ['showValues', 'Show Values'],
  ['nodeLabels', 'Label All Nodes'],
  ['smallGrid', 'Small Grid'],
  ['toolbar', 'Toolbar'],
  ['crosshair', 'Show Cursor Cross Hairs'],
  ['euro', 'European Resistors'],
  ['white', 'White Background'],
  ['noEdit', 'Disable Editing'],
  ['wheelEdit', 'Edit Values With Mouse Wheel'],
];

export const DEFAULT_UI_OPTIONS = {
  showCurrent: true,
  showVoltage: true,
  showPower: false,
  showValues: true,
  nodeLabels: false,
  smallGrid: false,
  toolbar: true,
  crosshair: false,
  euro: false,
  iec: false,
  white: false,
  conventional: false,
  noEdit: false,
  wheelEdit: false,
};

// Options that actually change the picture or the editor in this prototype.
export const WORKING_OPTIONS = new Set([
  'showVoltage', 'showPower', 'showValues', 'nodeLabels', 'smallGrid', 'toolbar', 'crosshair', 'euro', 'white',
  'noEdit','wheelEdit',
]);

export function buildMenus() {
  const file = [
    { label: 'New Blank Circuit', cmd: 'file.newblankcircuit' },
    { label: 'Open File...', cmd: 'file.importfromlocalfile', shortcut: 'Ctrl+O' },
    { label: 'Import From Text...', cmd: 'file.importfromtext' },
    { label: 'Save As...', cmd: 'file.exportaslocalfile', shortcut: 'Ctrl+S' },
    { label: 'Export As Text...', cmd: 'file.exportastext' },
    { label: 'Pack As Subcircuit...', cmd: 'file.packsubckt' },
    { label: 'Export As Image...', cmd: 'file.exportasimage' },
    { label: 'Copy Circuit Image to Clipboard', cmd: 'file.copypng' },
    { label: 'Export As SVG...', cmd: 'file.exportassvg' },
    { label: 'Print...', cmd: 'file.print', shortcut: 'Ctrl+P' },
    SEP,
    { label: 'Show Results', cmd: 'view.results' },
    { label: 'Toggle Full Screen', cmd: 'view.fullscreen' },
    SEP,
    { label: 'About...', cmd: 'file.about' },
  ];

  const edit = [
    { label: 'Undo', cmd: 'edit.undo', shortcut: 'Ctrl+Z' },
    { label: 'Redo', cmd: 'edit.redo', shortcut: 'Ctrl+Y' },
    SEP,
    { label: 'Cut', cmd: 'edit.cut', shortcut: 'Ctrl+X' },
    { label: 'Copy', cmd: 'edit.copy', shortcut: 'Ctrl+C' },
    { label: 'Paste', cmd: 'edit.paste', shortcut: 'Ctrl+V' },
    { label: 'Duplicate', cmd: 'edit.duplicate', shortcut: 'Ctrl+D' },
    SEP,
    { label: 'Select All', cmd: 'edit.selectAll', shortcut: 'Ctrl+A' },
    SEP,
    { label: 'Find Component...', cmd: 'edit.search', shortcut: '/' },
    { label: 'Centre Circuit', cmd: 'edit.centrecircuit' },
    { label: 'Zoom 100%', cmd: 'zoom.zoom100', shortcut: '0' },
    { label: 'Zoom In', cmd: 'zoom.zoomin', shortcut: '+' },
    { label: 'Zoom Out', cmd: 'zoom.zoomout', shortcut: '-' },
    { label: 'Flip X', cmd: 'edit.flipx' },
    { label: 'Flip Y', cmd: 'edit.flipy' },
    { label: 'Flip XY', cmd: 'edit.flipxy' },
  ];

  const drawItems = [
    ...TOP_PARTS.map(add),
    ...GROUPS.map((g) => ({ label: g.title, items: g.items.map(add) })),
    { label: 'Subcircuits', items: [{ label: '(none yet)', cmd: 'noop', disabled: true }] },
    {
      label: 'Drag',
      items: DRAG_MODES.map(([id, label, sc]) => ({
        label, cmd: id === 'DragAll' ? 'mode:dragAll' : `mode:${id}`, shortcut: sc,
      })),
    },
    { label: 'Select/Drag Sel', cmd: 'mode:select', shortcut: '(space or Shift-drag)' },
  ];

  const simulation = [
    { label: 'Run Simulation', cmd: 'sim.run', shortcut: 'Ctrl+Enter' },
    { label: 'Stop', cmd: 'sim.stop' },
    SEP,
    { label: 'Analysis Setup...', cmd: 'sim.setup' },
    { label: 'View SPICE Netlist...', cmd: 'sim.netlist' },
    { label: 'Model Library...', cmd: 'sim.models' },
    { label: 'Clear Results', cmd: 'sim.clear' },
  ];


  const options = [
    ...OPTION_ITEMS.map(([key, label]) => ({ label, cmd: `opt:${key}` })),
  ];

  // The real Circuits menu comes from a file I don't have; these are my own few examples.
  const circuits = SAMPLE_MENU.map((f) => ({
    label: f.folder,
    items: f.keys.map((k) => ({ label: SAMPLES[k].title, cmd: `sample:${k}` })),
  }));

  return [
    { label: 'File', items: file },
    { label: 'Edit', items: edit },
    { label: 'Draw', items: drawItems },
    { label: 'Simulation', items: simulation },
    { label: 'Options', items: options },
    { label: 'Circuits', items: circuits },
  ];
}

// Right-click menus (CirSim.java ~835-848 for a part; the Draw menu otherwise).
export const ELEMENT_MENU = [
  { label: 'Edit...', cmd: 'elm.edit' },
  { label: 'Cut', cmd: 'edit.cut' },
  { label: 'Copy', cmd: 'edit.copy' },
  { label: 'Delete', cmd: 'edit.delete' },
  { label: 'Duplicate', cmd: 'edit.duplicate' },
  { label: 'Swap Terminals', cmd: 'elm.flip' },
  { label: 'Flip X', cmd: 'edit.flipx' },
  { label: 'Flip Y', cmd: 'edit.flipy' },
  { label: 'Flip XY', cmd: 'edit.flipxy' },
  { label: 'Split Wire', cmd: 'elm.split', shortcut: 'Ctrl+click' },
  { label: 'Sliders...', cmd: 'elm.sliders' },
];

// Parts shown in the toolbar under the menu bar. CirSim.java doesn't contain Toolbar.java, so
// this selection is my guess at a sensible set, not a copy of CircuitJS1's.
export const TOOLBAR_ITEMS = [
  ['WireElm', 'Wire'],
  ['ResistorElm', 'Resistor'],
  ['CapacitorElm', 'Capacitor'],
  ['InductorElm', 'Inductor'],
  ['SwitchElm', 'Switch'],
  ['GroundElm', 'Ground'],
  ['DCVoltageElm', 'DC Source'],
  ['ACVoltageElm', 'AC Source'],
  ['CurrentElm', 'Current'],
  ['DiodeElm', 'Diode'],
  ['LEDElm', 'LED'],
  ['NTransistorElm', 'NPN'],
  ['NMosfetElm', 'N-MOS'],
  ['OpAmpElm', 'Op Amp'],
];
