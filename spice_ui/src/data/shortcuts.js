// Single-key "add part" shortcuts. These are the defaults read from the CircuitJS1 source (each
// element class's getShortcut()). Only keys I could confirm in that source are listed; CircuitJS1 has
// more for parts this app does not simulate yet. Keys are case-sensitive: "L" is Shift+L.
export const PART_SHORTCUTS = {
  WireElm: 'w',
  ResistorElm: 'r',
  CapacitorElm: 'c',
  InductorElm: 'L',
  GroundElm: 'g',
  DCVoltageElm: 'v',
  DiodeElm: 'd',
  ZenerElm: 'z',
  OpAmpElm: 'a',
  SwitchElm: 's',
  TextElm: 't',
  DirectiveElm: '.',
  NTransistorElm: 'n',
  PTransistorElm: 'p',
  NMosfetElm: 'N',
  PMosfetElm: 'P',
};

export const KEY_TO_PART = Object.fromEntries(Object.entries(PART_SHORTCUTS).map(([type, key]) => [key, type]));

// Other keys the editor handles (shown in Options > Shortcuts...).
export const OTHER_KEYS = [
  ['Space / Esc', 'Select tool (Esc also deselects)'],
  ['Delete / Backspace', 'Delete selection'],
  ['Ctrl+Z / Ctrl+Y', 'Undo / Redo'],
  ['Ctrl+X / C / V / D', 'Cut / Copy / Paste / Duplicate'],
  ['Ctrl+A', 'Select all'],
  ['Ctrl+S / Ctrl+O', 'Save / Open circuit file'],
  ['Ctrl+P', 'Print the circuit'],
  ['Ctrl+Enter', 'Run simulation'],
  ['+ / - / 0', 'Zoom in / out / 100%'],
  ['Alt-drag or middle-drag', 'Pan'],
  ['Shift-click', 'Add to selection'],
];
