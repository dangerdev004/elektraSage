// Part definitions: which symbol a class uses, where its terminals are, how big it is.
// Parts without a dedicated symbol are drawn as a labelled box (two terminals), so the whole
// Draw menu can be placed even though only a subset has a proper symbol so far.

import { LABELS } from '../data/catalog.js';

const two = (L) => [{ x: 0, y: 0 }, { x: L, y: 0 }];
const one = () => [{ x: 0, y: 0 }];
const bjt = (L) => [{ x: 0, y: 0 }, { x: L, y: -16 }, { x: L, y: 16 }];
const opamp = (L) => [{ x: 0, y: -16 }, { x: 0, y: 16 }, { x: L, y: 0 }];

const gate2 = (L) => [{ x: 0, y: -16 }, { x: 0, y: 16 }, { x: L, y: 0 }]; // inputs a, b; output

// Chip-style parts (flip-flops, latches): body x = 16..L-16, y = -32..32, pins on the grid.
// A spec entry is { n: label, x, y, side: 'l'|'r'|'t'|'b', clk?, bubble? }; the order is the terminal order.
const chip = (title, pinSpec) => ({
  kind: 'chip', title, pinSpec, minLen: 96, halfH: 52, ext: 0,
  terminals: (L) => pinSpec.map((p) => ({ x: p.x === 'L' ? L : p.x, y: p.y })),
});
const SETRST = [{ n: 'SET', x: 48, y: -48, side: 't' }, { n: 'RST', x: 48, y: 48, side: 'b' }];
const QQ = [{ n: 'Q', x: 'L', y: -16, side: 'r' }, { n: 'Q̅', x: 'L', y: 16, side: 'r' }];

const R = { minLen: 32, terminals: two, halfH: 12, ext: 0 };

export const DEFS = {
  WireElm: { kind: 'wire', minLen: 0, free: true, terminals: two, halfH: 4, ext: 0, label: 'Wire' },
  ResistorElm: { ...R, kind: 'resistor', value: '1 kΩ', label: 'Resistor' },
  CapacitorElm: { ...R, kind: 'capacitor', value: '10 µF', label: 'Capacitor' },
  PolarCapacitorElm: { ...R, kind: 'polcap', value: '10 µF', label: 'Capacitor (polarized)' },
  InductorElm: { ...R, kind: 'inductor', value: '1 H', label: 'Inductor' },
  SwitchElm: { ...R, kind: 'switch', label: 'Switch' },
  PushSwitchElm: { ...R, kind: 'switch', label: 'Push Switch' },
  GroundElm: { kind: 'ground', minLen: 16, terminals: one, halfH: 12, ext: 12, label: 'Ground' },
  DCVoltageElm: { ...R, kind: 'dcvolt', value: '5 V', halfH: 14, label: 'Voltage Source' },
  ACVoltageElm: { ...R, kind: 'acvolt', value: '5 V, 40 Hz', halfH: 16, label: 'A/C Voltage Source' },
  RailElm: { kind: 'rail', minLen: 16, terminals: one, halfH: 12, ext: 22, value: '5 V', label: 'Voltage Rail' },
  ACRailElm: { kind: 'rail', minLen: 16, terminals: one, halfH: 12, ext: 22, value: '5 V, 40 Hz', label: 'A/C Rail' },
  CurrentElm: { ...R, kind: 'current', value: '10 mA', halfH: 16, label: 'Current Source' },
  DiodeElm: { ...R, kind: 'diode', halfH: 12, label: 'Diode' },
  ZenerElm: { ...R, kind: 'zener', halfH: 14, value: '5.1 V', label: 'Zener Diode' },
  LEDElm: { ...R, kind: 'led', halfH: 22, label: 'LED' },
  NTransistorElm: { kind: 'npn', minLen: 32, terminals: bjt, halfH: 20, ext: 0, label: 'NPN Transistor' },
  PTransistorElm: { kind: 'pnp', minLen: 32, terminals: bjt, halfH: 20, ext: 0, label: 'PNP Transistor' },
  NMosfetElm: { kind: 'nmos', minLen: 32, terminals: bjt, halfH: 20, ext: 0, label: 'N-MOSFET' },
  PMosfetElm: { kind: 'pmos', minLen: 32, terminals: bjt, halfH: 20, ext: 0, label: 'P-MOSFET' },
  ClockElm: { kind: 'clock', minLen: 16, terminals: one, halfH: 12, ext: 22, value: '5 V, 1 kHz', label: 'Clock' },
  AndGateElm: { kind: 'gate', shape: 'and', minLen: 64, terminals: gate2, halfH: 24, ext: 0, label: 'AND Gate' },
  NandGateElm: { kind: 'gate', shape: 'and', bubble: true, minLen: 64, terminals: gate2, halfH: 24, ext: 0, label: 'NAND Gate' },
  OrGateElm: { kind: 'gate', shape: 'or', minLen: 64, terminals: gate2, halfH: 24, ext: 0, label: 'OR Gate' },
  NorGateElm: { kind: 'gate', shape: 'or', bubble: true, minLen: 64, terminals: gate2, halfH: 24, ext: 0, label: 'NOR Gate' },
  XorGateElm: { kind: 'gate', shape: 'xor', minLen: 64, terminals: gate2, halfH: 24, ext: 0, label: 'XOR Gate' },
  XnorGateElm: { kind: 'gate', shape: 'xor', bubble: true, minLen: 64, terminals: gate2, halfH: 24, ext: 0, label: 'XNOR Gate' },
  InverterElm: { kind: 'gate', shape: 'buf', bubble: true, minLen: 64, terminals: two, halfH: 18, ext: 0, label: 'Inverter' },
  BufferElm: { kind: 'gate', shape: 'buf', minLen: 64, terminals: two, halfH: 18, ext: 0, label: 'Buffer' },
  DFlipFlopElm: { ...chip('D FF', [{ n: 'D', x: 0, y: -16, side: 'l' }, { n: '', x: 0, y: 16, side: 'l', clk: true }, ...SETRST, ...QQ]), label: 'D Flip-Flop' },
  JKFlipFlopElm: { ...chip('JK FF', [{ n: 'J', x: 0, y: -16, side: 'l' }, { n: 'K', x: 0, y: 16, side: 'l' }, { n: '', x: 0, y: 0, side: 'l', clk: true, bubble: true }, ...SETRST, ...QQ]), label: 'JK Flip-Flop' },
  TFlipFlopElm: { ...chip('T FF', [{ n: 'T', x: 0, y: -16, side: 'l' }, { n: '', x: 0, y: 16, side: 'l', clk: true }, ...SETRST, ...QQ]), label: 'T Flip-Flop' },
  LatchElm: { ...chip('D LATCH', [{ n: 'D', x: 0, y: -16, side: 'l' }, { n: 'EN', x: 0, y: 16, side: 'l' }, ...SETRST, ...QQ]), label: 'Latch' },
  SRLatchElm: { ...chip('SR LATCH', [{ n: 'S', x: 0, y: -16, side: 'l' }, { n: 'R', x: 0, y: 16, side: 'l' }, ...QQ]), label: 'SR Latch' },
  OpAmpElm: { kind: 'opamp', minLen: 64, terminals: opamp, halfH: 34, ext: 0, label: 'Op Amp (ideal)' },
};

// "Op Amp (ideal, + on top)" is the same symbol with the inputs swapped, i.e. mirrored.
DEFS.OpAmpSwapElm = { ...DEFS.OpAmpElm, label: 'Op Amp (+ on top)', swap: true };
DEFS.OpAmpRealElm = { ...DEFS.OpAmpElm, label: 'Op Amp (real)' };

export function getDef(type) {
  const d = DEFS[type];
  if (d) return d;
  return {
    kind: 'box',
    minLen: 48,
    terminals: two,
    halfH: 14,
    ext: 0,
    generic: true,
    label: LABELS[type] ?? type,
  };
}

export const isGeneric = (type) => !DEFS[type];
