// A few small example circuits so the canvas has something to show. These are my own
// placeholders, NOT CircuitJS1's circuit library (that list lives in a file I haven't seen).
// Each element: [type, x1, y1, x2, y2, value?]
// Sources: point 1 is the + terminal (the long plate / the end with the + sign).

export const SAMPLES = {
  rc: {
    title: 'RC low-pass filter',
    elements: [
      ['ACVoltageElm', 128, 160, 128, 256, '5 V, 100 Hz'],
      ['WireElm', 128, 160, 192, 160],
      ['ResistorElm', 192, 160, 288, 160, '1 kΩ'],
      ['WireElm', 288, 160, 352, 160],
      ['CapacitorElm', 352, 160, 352, 256, '1 µF'],
      ['WireElm', 128, 256, 352, 256],
      ['GroundElm', 128, 256, 128, 272],
      ['WireElm', 352, 160, 432, 160],
    ],
  },
  divider: {
    title: 'Resistor divider',
    elements: [
      ['DCVoltageElm', 112, 160, 112, 256, '10 V'],
      ['WireElm', 112, 160, 208, 160],
      ['ResistorElm', 208, 160, 208, 224, '1 kΩ'],
      ['ResistorElm', 208, 224, 208, 288, '2 kΩ'],
      ['WireElm', 208, 224, 288, 224],
      ['WireElm', 112, 256, 112, 288],
      ['WireElm', 112, 288, 208, 288],
      ['GroundElm', 208, 288, 208, 304],
    ],
  },
  led: {
    title: 'LED with series resistor',
    elements: [
      ['DCVoltageElm', 112, 160, 112, 256, '5 V'],
      ['WireElm', 112, 160, 192, 160],
      ['ResistorElm', 192, 160, 272, 160, '330 Ω'],
      ['LEDElm', 272, 160, 352, 160],
      ['WireElm', 352, 160, 352, 256],
      ['WireElm', 352, 256, 112, 256],
      ['GroundElm', 112, 256, 112, 272],
    ],
  },
  rectifier: {
    title: 'Half-wave rectifier',
    elements: [
      ['ACVoltageElm', 112, 160, 112, 256, '10 V, 50 Hz'],
      ['WireElm', 112, 160, 176, 160],
      ['DiodeElm', 176, 160, 256, 160],
      ['WireElm', 256, 160, 320, 160],
      ['ResistorElm', 320, 160, 320, 256, '1 kΩ'],
      ['WireElm', 320, 256, 112, 256],
      ['GroundElm', 112, 256, 112, 272],
    ],
  },
  amp: {
    title: 'Inverting amplifier',
    elements: [
      ['ACVoltageElm', 96, 176, 96, 256, '1 V, 1 kHz'],
      ['GroundElm', 96, 256, 96, 272],
      ['WireElm', 96, 176, 128, 176],
      ['ResistorElm', 128, 176, 208, 176, '1 kΩ'],
      ['WireElm', 208, 176, 224, 176],
      ['WireElm', 224, 176, 256, 176],
      ['OpAmpElm', 256, 192, 320, 192],
      ['WireElm', 224, 176, 224, 128],
      ['ResistorElm', 224, 128, 336, 128, '10 kΩ'],
      ['WireElm', 336, 128, 336, 192],
      ['WireElm', 320, 192, 336, 192],
      ['WireElm', 336, 192, 384, 192],
      ['WireElm', 256, 208, 256, 240],
      ['GroundElm', 256, 240, 256, 256],
    ],
  },
  dff: {
    title: 'D flip-flop (clocked sampling)',
    // DATA clock (130 Hz) and CLK clock (1 kHz). Q takes the value of D at each rising CLK edge.
    // SET and RST each come from a 5 V rail through a switch, with a 10 k pull-down so an OPEN switch
    // reads LOW. Click a switch to close it (SET or RST goes HIGH) and the result re-runs.
    // Analysis: Transient, step 20u, stop 20m. Plot n-nodes of D, CLK, Q.
    elements: [
      ['ClockElm', 192, 112, 176, 112, '5 V, 130 Hz'],
      ['WireElm', 192, 112, 224, 112],
      ['ClockElm', 192, 144, 176, 144, '5 V, 1 kHz'],
      ['WireElm', 192, 144, 224, 144],
      ['DFlipFlopElm', 224, 128, 320, 128],
      // SET input: rail - switch - SET pin, pull-down to ground
      ['RailElm', 272, 32, 272, 16, '5 V'],
      ['SwitchElm', 272, 32, 272, 64, undefined, { open: 'true' }],
      ['WireElm', 272, 64, 272, 80],
      ['ResistorElm', 272, 64, 240, 64, '10 kΩ'],
      ['GroundElm', 240, 64, 240, 80],
      // RST input
      ['WireElm', 272, 176, 272, 192],
      ['SwitchElm', 272, 192, 272, 224, undefined, { open: 'true' }],
      ['RailElm', 272, 224, 272, 240, '5 V'],
      ['ResistorElm', 272, 192, 240, 192, '10 kΩ'],
      ['GroundElm', 240, 192, 240, 208],
      // Q and Q-bar LEDs
      ['WireElm', 320, 112, 352, 112],
      ['ResistorElm', 352, 112, 416, 112, '1 kΩ'],
      ['LEDElm', 416, 112, 480, 112],
      ['GroundElm', 480, 112, 480, 128],
      ['WireElm', 320, 144, 352, 144],
      ['ResistorElm', 352, 144, 416, 144, '1 kΩ'],
      ['LEDElm', 416, 144, 480, 144],
      ['GroundElm', 480, 144, 480, 160],
    ],
  },
};

export const SAMPLE_MENU = [
  { folder: 'Basics', keys: ['rc', 'divider', 'led'] },
  { folder: 'Diodes', keys: ['rectifier'] },
  { folder: 'Digital', keys: ['dff'] },
  { folder: 'Op-Amps', keys: ['amp'] },
];
