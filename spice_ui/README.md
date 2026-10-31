# circuit-ui

A CircuitJS1-style circuit editor front end in React (Vite) with a local **ngspice** as the solver.
You draw a circuit, press RUN, the canvas is turned into a SPICE netlist, ngspice solves it in the
browser, and the results are plotted below the canvas.

CircuitJS1 itself is not modified or used; this project only copies its menu names and layout.

> **Read this first: what has and has not been verified**
>
> * The editor, netlist builder, raw-file parser, server and plot are covered by plain-Node tests
>   (81 in total). The server tests use a **fake ngspice script** that writes a raw file in the
>   documented format, and the result tests use `tests/mock-eecircuit.mjs`, a data fixture that is
>   **not a solver**. **Real ngspice has not been run against this code.**
> * Whether ngspice's numbers are right for your circuit is untested here. Use Simulation > View SPICE
>   Netlist and check against a hand calculation (the RC sample is easy).
> * The versions in `package.json` (`vite ^7`, `@vitejs/plugin-react ^5`) are from memory.

## Local ngspice (recommended): run it in WSL

The browser can't run a native ngspice, so a small Node server (`server/server.mjs`, no extra
dependencies) runs `ngspice -b` on the netlist and sends the parsed result back. This is the only
solver; the earlier browser-WASM option (`eecircuit-engine`) has been removed.

```
# once, in WSL (Ubuntu):
sudo apt install ngspice          # or build your own, see below
node -v ; npm -v                  # Node and npm must be installed inside WSL

# project must live in the WSL filesystem (e.g. ~/circuit-ui), not under /mnt/c
cd ~/circuit-ui
npm install                       # do not copy node_modules from Windows
npm run server                    # terminal 1: http://127.0.0.1:3001
npm run dev                         # terminal 2: open http://localhost:5173 in Windows Chrome
```

* Check the server sees ngspice: open http://127.0.0.1:3001/api/health in a browser; it prints the
  ngspice version line. If it says it can't start ngspice, set `NGSPICE_BIN=/full/path/to/ngspice`.
* To build ngspice from source instead (e.g. the 47 tarball):
  `sudo apt install build-essential bison flex libtool autoconf automake libxaw7-dev`, then in the
  ngspice folder `./configure --with-x=no --disable-debug && make -j4 && sudo make install`.
* Limits: 60 s per run (`SIM_TIMEOUT_MS`), 2 MB netlists, listens on 127.0.0.1 only. The server
  refuses netlists containing `.control`, `.include`, `.lib`, `shell` etc., because those can run
  commands or read files. It is a local developer tool; do not expose it on a network.
* **Verification status:** the server, the raw-file parser (binary and ascii, real and complex) and the
  browser side are tested (12 tests) with a *fake* ngspice script that writes a raw file built to the
  documented format. **Real ngspice has not been run against it.** The most likely first-run problems
  are ngspice naming vectors differently than expected or a flag difference between versions; the
  error text and the "Problems" list will show ngspice's own messages.

```
npm test          # 81 plain-Node tests (editor, netlist builder, results, local server, model library)
npm run build     # production build into dist/
```

## Model library (your own SPICE models)

Put SPICE model files in the `models/` folder next to `package.json` (or set `MODELS_DIR`). Supported
extensions: `.lib .mod .model .cir .sp .spi .inc .txt`. `models/generic.lib` ships as an example; those
are simple generic parameter sets I wrote, **not manufacturer models of real parts**.

1. Add a file, then Simulation > Model Library... > Refresh to see what was found.
2. Double-click a diode, LED, zener, BJT or MOSFET > pick a model in the Edit dialog. The model's type
   must match the part (`D`, `NPN`, `PNP`, `NMOS`, `PMOS`); a mismatch is reported as a problem.
3. RUN. The browser sends only the *file names*; the server adds the `.include` lines itself, and
   refuses names that are not files in the models folder. (View SPICE Netlist shows a comment for each
   library file used.)

Limits: only `.model` cards can be assigned to parts. `.subckt` definitions (most op-amp, regulator and
vendor MOSFET models) are listed but cannot be used yet, because that needs a pin-mapping step per part.
The server does not validate a library file; ngspice's own error is shown if one is broken. Library files
are trusted: anything in them (including `.include`) is run by ngspice, so only put files you trust there.

## Files

* **Save/Open:** File > Save As... (Ctrl+S) downloads `<title>.circuit.json`; Open File... (Ctrl+O)
  loads one. Export/Import As Text does the same through a text box. The format is plain JSON
  (`format: "circuit-ui"`, `version: 1`); a file with another format or a bad part is rejected with a
  message and your current circuit is left alone.
* The app **starts blank**. Samples are under the Circuits menu.
* Moving a part drags the ends of wires attached to its pins (they can become diagonal, as in CircuitJS1).

## How to simulate

1. Draw a circuit, or load one from the **Circuits** menu. It needs at least one **Ground** part.
2. **Simulation > Analysis Setup...** (or the Analysis button in the right panel) to pick
   Transient, AC sweep, DC sweep or Operating point and set its parameters.
3. **RUN** (right panel, Simulation menu, or Ctrl+Enter).
4. Results appear in the strip under the canvas. Signal checkboxes toggle traces; click the plot to
   place a cursor (Shift-click for a second), wheel zooms, drag pans, double-click fits.
   Operating-point results are a table, and hovering a wire shows `node nX = value`.
5. **Simulation > View SPICE Netlist...** shows exactly what was sent to ngspice, with a Copy button.

If you edit the circuit after a run, the status turns to "Circuit changed since this run" so you
don't read stale numbers as current.

## How the canvas becomes a netlist

* Nodes are found by merging terminals and wire ends that share a grid coordinate. All Ground parts are
  node `0`; other nodes are named `n1`, `n2`, ... in order of first appearance.
* **A wire that merely passes over a pin does not connect to it.** Connections happen at wire ends and
  part terminals only. Loose pins (a terminal connected to nothing) produce a warning.
* Values are parsed with units: `1k`, `4.7 kΩ`, `100n`, `10 uF`, `1 F` (one farad, not femto).
  `M`/`m` follow engineering convention in the dialog (capital M = mega), which differs from SPICE.
  Use `Meg` if in doubt.

| Part | SPICE |
|---|---|
| Resistor / Capacitor / Inductor | `R` / `C` / `L` |
| DC voltage source, Rail | `V n+ n- DC v` (terminal 1 = + side) |
| AC voltage source | `V n+ n- SIN(0 amp freq) AC 1` (default 40 Hz) |
| Current source | `I` |
| Diode, LED, Zener | `D` + a generic `.model` (see below) |
| NPN / PNP | `Q c b e` + generic `.model` |
| N/P MOSFET | `M d g s s` + generic level-1 `.model`; W and L go on the instance |
| Op amp (ideal) | `B out 0 V=mid+half*tanh(gain*(v(+)-v(-))/half)`: gain, Max/Min output |
| Op amp (real) | one-pole gain stage (`Bg`, `Rp`, `Cp`) with slew limit, then a current-limited, clamped output (`Bo`) |
| Switch, push switch | treated as **closed** (1 mΩ), with a warning |
| Text / box / line annotations | ignored |
| Anything else (gates, ICs, the generic labelled boxes, ...) | **error: not supported yet** |

## Generic models and parameters

Every diode, transistor and op amp is a generic SPICE model. **Double-click a part** for its parameter
dialog (fields with − / + buttons that step 1-2-5).

* **Diode / LED / Zener, NPN / PNP, MOSFET:** a field left **empty** is not written to the `.model` card,
  so ngspice uses its own default, like other SPICE editors. A part with no parameters gets a bare card
  such as `.model QNPN NPN`. Identical parameter sets share one card. Exceptions: the LED has a built-in
  generic set (`IS=1e-18 N=1.9 RS=2`) so it lights at about 2 V; the zener takes BV from its value; the
  MOSFET always gets `LEVEL=1`. Consequence to know about: SPICE's default MOSFET has VTO = 0 V and KP = 20 µA/V²,
  so set VTO (and KP, W, L) for a real enhancement device.
* **Op amp (ideal):** Max Output 15 V, Min Output −15 V, Gain 100k by default (editable). The output is
  smoothly clamped between the limits, so a comparator saturates instead of going to megavolts.
* **Op amp (real):** Model (Generic or LM741), Swap Inputs, Slew Rate, Output Current Limit, Open-loop
  Gain, Gain-Bandwidth Product, Output Resistance, Max/Min Output. The LM741 preset uses the slew rate
  and current limit from the CircuitJS1 dialog; **none of these numbers are datasheet-verified**. The
  op amps have no supply pins; the supply is represented by Max/Min Output. The macromodel's internal
  node is named `z_oa1_x`, and names starting with `z_` are hidden from the results list.
* A library model picked in the dialog (see Model library) overrides the generic parameters.
* **Not verified against real ngspice:** the `B`-source expressions (`tanh`, `v(a)-v(b)`, `v(0)`) are
  standard ngspice syntax as far as I know, but the op-amp macromodels have never been run, and
  circuits with feedback around them may need convergence tuning. Check them against a hand calculation.

## Keyboard shortcuts

Click the canvas first. Part keys are the CircuitJS1 defaults, taken from its source: `w` wire, `r` resistor,
`c` capacitor, `L` (Shift+L) inductor, `g` ground, `v` voltage source, `d` diode, `z` zener, `a` op amp,
`s` switch, `t` text, `n` NPN, `p` PNP, `N` N-MOSFET, `P` P-MOSFET. `Space` or `Esc` = select tool.
Plus Ctrl+Z/Y/X/C/V/D/A, Ctrl+S/O, Ctrl+Enter, Delete, `+` `-` `0`. Options > Shortcuts... lists them. Keys
for CircuitJS1 parts this app does not have are not included.

## Editing

* **Drag an end** of any part or wire to stretch it (wires go in any direction; other parts stay on
  their axis and keep a minimum length). Wires attached to a pin follow. Shrinking a wire to zero length
  deletes it. Where a wire meets a pin, the part's end is grabbed first; select the wire first to grab its end.
* **Options > Label All Nodes** writes the SPICE node names (`n1`, `n2`, ...) on the canvas, the same names the
  results list uses. Numbering follows first appearance, so names can change when you edit.
* The "view in scope" items and the Scopes menu were removed; results are shown in the panel below.

AC analysis uses a unit stimulus (`AC 1`) on the sources, so the plotted dB is the gain from the
source to each node and phase is relative to it, not the absolute source amplitude.

## Known limitations (be critical of these)

* **Only the basics are modelled.** No gates, logic, transformers, relays, transmission lines,
  subcircuits, or switch state. Most of the ~150 catalogue entries can be *drawn* but not simulated, and
  the run stops with a clear error naming them rather than guessing.
* **Generic transistor, diode and MOSFET models.** Real device behaviour (e.g. a specific 2N3904) needs
  `.model` cards or a library, which this does not have yet.
* **Op amp is ideal and unlimited**, so output saturation at the supply rails is not shown.
* **No live animation.** The three right-hand sliders are disabled; nothing animates current or
  voltage like CircuitJS1 does. This is batch simulation, not a continuous one.
* **Stop does not cancel ngspice.** It discards the result when it arrives; ngspice keeps running until
  it finishes or the 60 s server timeout kills it.
* **Convergence failures** come back as ngspice errors in the Problems list. There is no automatic
  retry with relaxed tolerances or `.options`.
* **Large sweeps** are plotted fully without decimation; tens of thousands of points are fine, millions
  will not be.
* **Node labels are generated** (`n1`, `n2`), not user-named. There are no probes or net labels yet.
* **Hover node values** only appear after an Operating-point run.

## What works in the editor

* **Menu bar**: File, Edit, Draw, Simulation, Options, AI Assistant, Microcontroller,
  Circuits, with labels, order, shortcuts and submenus read from `CirSim.java`.
* **Toolbar** (Options > Toolbar hides it) and **right panel** (Reset, RUN/Stop, Analysis, sliders,
  Current Circuit).
* **Canvas**: grid snapping, placing parts, wires at any angle, select / shift-select / rubber band,
  move, pan, wheel zoom, double-click to edit a value, right-click menus.
* **Edit menu**: Undo/Redo, Cut/Copy/Paste/Duplicate, Select All, Centre, Zoom, Flip X/Y/XY, Swap
  Terminals, Delete.
* **Parts**: all ~150 Draw-menu entries can be placed; about 20 have proper symbols and ~16 simulate.
* Anything not implemented (Export As Text, Print, other Drag modes, ...) says
  "... is not wired up yet." instead of silently doing nothing.

## Where things are

| Path | What |
|---|---|
| `src/data/menus.js` | menu bar, right-click menus, toolbar contents, option list |
| `src/data/catalog.js` | Draw-menu parts catalogue (from `CirSim.composeMainMenu`) |
| `src/data/samples.js` | five small example circuits (my own, not CircuitJS1's library) |
| `src/canvas/editor.js` | the editor: model, undo, mouse/keyboard, drawing. No React inside |
| `src/canvas/symbols.js`, `parts.js` | symbol drawings, terminals, sizes |
| `src/sim/units.js` | value parsing (`4.7k`, `10 µF`, ...) |
| `src/sim/netlist.js` | canvas -> nodes -> SPICE netlist, errors and warnings |
| `server/library.mjs` | scans `models/` for `.model` / `.subckt` definitions |
| `src/sim/analysis.js` | analysis types, defaults, validation, the `.tran/.ac/.dc/.op` card |
| `src/sim/engine-server.js` | adapter that calls the local ngspice server |
| `server/server.mjs`, `server/rawfile.mjs` | local ngspice runner and raw-file parser |
| `src/sim/results.js` | normalises the engine result into named vectors, builds plot traces |
| `src/sim/plotter.js` | canvas plot with log axes, cursors, zoom/pan |
| `src/components/*` | menu bar, toolbar, side panel, results panel, dialogs, canvas wrapper |
| `tests/` | unit tests, plus `mock-eecircuit.mjs` (a data fixture, not a solver) |

To use a different solver, implement the same interface as `NgspiceServerEngine` in
`src/sim/engine-server.js`: `run({ netlist, analysisType })` returning `{ analysis, x, vectors }`.

## Other things I guessed or could not check

* **Toolbar contents and button style.** `Toolbar.java` was not available, so the 14 toolbar parts are
  my pick, not a copy.
* **Circuits menu.** CircuitJS1 loads its list from a file I don't have; mine has five examples.
* **Colours, fonts, spacing** approximate how CircuitJS1 looks; they were not measured. No icons,
  fonts or images from CircuitJS1 are used.
* **Vite was not run** when I built this. I bundled the same source with esbuild and React 19 and
  exercised it in headless Chrome; `npm run dev` is the first run of the Vite setup.
* **Licence.** CircuitJS1 is open source (I believe GPL; check the LICENSE in your copy). This project
  copies no code from it. ngspice has its own licence terms; check them before distributing it with anything.

## Digital logic (step 1)

AND, NAND, OR, NOR, XOR, XNOR, Inverter, Buffer and a Clock source are simulated with ngspice's
XSPICE code models (`d_and`, `d_nand`, ...). These come with Debian's ngspice and are loaded by its own
start-up file, so nothing needs configuring (check `ls /usr/lib/x86_64-linux-gnu/ngspice/digital.cm`).

- **Bridges are automatic.** Wire gates to anything. A net that only touches gates stays digital; where a net
  touches analog parts the netlist gets `adc_bridge` / `dac_bridge` cards for you. Every net a gate drives is
  also shown as an ordinary analog node (`n3` ...), which is what you plot. The internal digital copies
  (`d_n3`) are hidden.
- **Parameters** (Edit dialog): logic-high level (default 5 V; input thresholds are 30 % / 70 % of it) and
  propagation delay (empty = XSPICE default, 1 ns).
- **Clock**: value text like `5 V, 1 kHz`, 50 % duty, 0 to the amplitude.
- **Errors you may see**: two gate outputs on one net; a gate input with nothing driving it.
- **Not done yet**: counters as chips, tri-state, logic input/output probes, ADC/DAC parts.
- Not yet run against real ngspice from this side: use a clock into a NAND with a 5 V rail on the other input,
  transient 0 to 3 ms, and plot the gate output node.

## Flip-flops and latches (step 2)

D, JK and T flip-flops, a D latch and an SR latch use XSPICE `d_dff`, `d_jkff`, `d_tff`, `d_dlatch` and
`d_srlatch`. Registers and counters are built by wiring flip-flops (shift register: Q to the next D; ripple
counter: Q-bar to D with the next stage clocked by Q).

- Pins left unconnected are handled for you: SET / RST (active high) and enable become `NULL`, and an unused
  Q or Q-bar goes to a dummy node. A required input (D, J, K, T, CLK) with nothing driving it is an error.
- Edit dialog: logic-high level, clock-to-output delay (empty = 1 ns default) and initial state (0 or 1).
  Without an initial state, ngspice starts Q at 0.
- **Clock edge, from memory and not yet verified here:** `d_dff` triggers on the rising edge and `d_jkff` on
  the falling edge (the JK symbol shows an inversion bubble). The `d_tff` edge is not confirmed, so its
  symbol shows no bubble. Check each against a clock in a real run before relying on it.
- SR latch: enable, SET and RESET are left open (`NULL`); only S and R are used.

## Parameter dialogs and switches

Every part we simulate now opens a parameter dialog with +/- steppers (1-2-5 steps): resistor, capacitor,
inductor, DC source, rail, current source, A/C source and rail (amplitude, frequency, DC offset, phase), clock
(level, frequency, duty cycle), switches, diodes, transistors, op amps, gates, flip-flops and latches. The
value typed for R/C/L/sources gets its unit added to the label ("1k" shows as 1kΩ).

Switches have a state. Closed is drawn with a flat lever and simulates as 1 mΩ; open is drawn with a raised
lever and simulates as 1 GΩ. Click a switch to toggle it (one undo step). If a result is already on screen,
the circuit re-runs automatically. There is no live switching during a single run.

Not in the dialogs yet: capacitor/inductor initial conditions, ESR and series resistance, source waveforms
other than sine and clock.

Example: Circuits > Digital > D flip-flop (clocked sampling). Set Analysis to Transient, step 20u, stop 20m.
Pull-down resistors on SET and RST matter: an open switch is 1 GOhm to 5 V, which a logic input still reads
as HIGH unless something pulls the net down.

## Export and print

File > Export As Image saves a PNG (2x size), Copy Circuit Image to Clipboard puts the same PNG on the clipboard,
Export As SVG saves a vector file, and Print (Ctrl+P) prints the circuit as a vector page. All of them redraw the
circuit in black on white with no grid, selection colour or drag handles, with a margin around it. Value labels
and node labels follow the same options as the canvas. Copying to the clipboard needs localhost or https and a
browser that allows it; Export As Image is the fallback.

## Logic Input and Logic Output

Logic Input is a clickable source: click it to toggle 0 / 1 (it drives its net with 0 V or the logic high level,
default 5 V). Logic Output is a lamp that reads its net from the last result: lit with a 1 when the net is above
half the logic level, 0 when below, and "?" when there is no result or the circuit has changed since the run.
For a transient run the lamp shows the value at the last time point. Clicking an input re-runs the simulation
when a result is already on screen. Example: Circuits > Digital > NAND gate with logic inputs (run it once
with Analysis set to Operating Point).

## SPICE directives

Draw > Outputs and Labels > SPICE Directive (shortcut `.`) places a text block. Double-click it to edit. Only these
commands are accepted: `.param .model .options .option .ic .nodeset .temp .global .func .meas .measure`. Lines
starting with `+` continue the previous line; `*` starts a comment. Analysis commands (`.tran`, `.ac`, ...) are
refused because the analysis comes from Simulation > Analysis Setup; element lines are refused too. The same check
runs in the editor and in the netlist builder, and the server independently refuses `.control`, `.include`, shell
and file-access constructs.

## Model library files

Simulation > Model Library lists every `.model` and `.subckt` found in the `models/` folder. Upload... adds files
(`.lib .mod .model .cir .sp .spi .inc .txt`, up to 5 MB); a name that already exists asks before replacing. Uploads
containing `.control`, `.include` with a path, `file=` or similar are refused. You can also copy files into the
folder and press Refresh.

## Subcircuits from the library

Draw > Outputs and Labels > Subcircuit (from library) places a block. Double-click it and pick a `.subckt`; the
block's pins are taken from the definition, in SPICE order (first half down the left side, the rest down the right),
and `PARAMS:` values can be overridden (blank = the subcircuit's default). The netlist gets
`X1 <nodes> NAME param=value` and the server includes the library file. The pin list is saved in the circuit file;
if the library file later changes its pin count the netlist builder asks you to pick the subcircuit again.
Limits: pins are not reordered or moved around, parameters must be numbers, and nested subcircuits work only inside
the library file's own definitions. Packing your own circuit into a block is the next step.

## Labeled nodes

Draw > Outputs and Labels > Labeled Node is a one-pin flag. Double-click it to set the name. Labels with the same
name are the same net even with no wire between them (names are case-insensitive, as in SPICE), and that name is used
in the netlist and results (`v(vcc)` instead of `v(n3)`). A label named `0` or `gnd` connects to ground. Errors are
reported for an empty or invalid name, a name like `n3` / `d_x` / `z_x` (reserved for automatic names), and a wire
that joins two different label names. Unlabeled nets keep the automatic names n1, n2, ...

## Packing your own circuit as a subcircuit

Mark the pins with Draw > Outputs and Labels > Subcircuit Port (name each one; ports with the same name are one pin),
then File > Pack As Subcircuit... Choose a name and Save to library: the circuit is written as `<name>.lib` in the
models folder as a `.subckt` whose pins are the ports, top to bottom then left to right (the preview shows the text).
It then appears in the Subcircuit block's list. No ground is needed inside the circuit; ground (0) is shared with the
outside. Not supported yet: circuits that contain Subcircuit blocks, digital parts, library models or SPICE
Directives (all refused with a message). The block keeps no link to the canvas: edit the circuit, pack again with the
same name and choose Replace. Existing blocks pick up the new definition on the next run; if the pin count changed,
re-pick it in the block's dialog.

## Results window

The results area is hidden until you press RUN. It then opens as a floating window: drag the header to move it,
drag any edge or corner to resize it, **Dock** snaps it to the bottom of the canvas (drag its top edge to resize),
**Undock** floats it again, and ✕ hides it. View > Show Results toggles it. Floating/docked state, position and size
are remembered in the browser (localStorage) between sessions.

## Side panel and chat

Drag the left edge of the side panel to resize it (150 px up to 60% of the window); » folds it away completely and «
brings it back. Width and collapsed state are remembered. The chat at the bottom of the panel talks to your own
model through the local server, which forwards to an OpenAI-compatible endpoint (Ollama, LM Studio, llama.cpp, vLLM, ...):

    CHAT_URL=http://localhost:11434/v1/chat/completions CHAT_MODEL=llama3 npm run server

`CHAT_API_KEY` is optional (sent as a Bearer token). The endpoint is set only by these environment variables, never by the
browser. "Send circuit netlist" attaches the current netlist as context. The reply is read from
`choices[0].message.content` (Ollama's `message.content` also works); no streaming yet. The conversation is kept in memory
only. If your agent uses a different request format, change `askModel` in `server/server.mjs`.
