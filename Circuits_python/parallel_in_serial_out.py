from typing import List, Optional, Sequence, Union


def piso_shift_register(
    bits: int,
    initial_values: Optional[Union[str, Sequence[bool]]] = None,
) -> str:
    """Generate an N-bit PISO (parallel-in, serial-out) shift register as Falstad circuit text.

    Layout matches the 4-bit reference circuit: N stages, each a 2:1 mux
    (se="1") feeding a D flip-flop. Each mux's I0 pin is a manual parallel
    input toggle; its I1 pin is wired to the previous stage's Q (the first
    stage's I1 is left unconnected, matching the reference, since nothing
    meaningful shifts into it). A single "load/shift" toggle drives an
    inverter whose output forms a shared select (S0) bus across every mux.
    A shared clock bus drives every flip-flop, and a single output marker
    sits on the last stage's Q (the serial output).

    Args:
        bits: Number of register bits. Must be a whole number >= 1.
        initial_values: Optional initial state for each parallel input
            (I0) toggle, most-significant/first-stage bit first. Either a
            string of the same length as `bits` using '1'/'H'/'h' for
            high and '0'/'L'/'l' for low, or a sequence of `bits`
            booleans/truthy values. Defaults to all-high (all True) when
            omitted.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        TypeError: If bits is not an int (bool, float, str and None are rejected).
        ValueError: If bits < 1, or initial_values has the wrong length or
            contains an invalid character/value.
    """
    if isinstance(bits, bool) or not isinstance(bits, int):
        raise TypeError(f"bits must be a whole number, got {bits!r}")
    if bits < 1:
        raise ValueError(f"bits must be >= 1, got {bits}")

    # ── Resolve per-bit initial toggle states ──────────────────────────
    if initial_values is None:
        states: List[bool] = [True] * bits
    elif isinstance(initial_values, str):
        if len(initial_values) != bits:
            raise ValueError(
                f"initial_values string length ({len(initial_values)}) "
                f"must equal bits ({bits})"
            )
        states = []
        for ch in initial_values:
            if ch in "1Hh":
                states.append(True)
            elif ch in "0Ll":
                states.append(False)
            else:
                raise ValueError(f"invalid character {ch!r} in initial_values")
    else:
        values = list(initial_values)
        if len(values) != bits:
            raise ValueError(
                f"initial_values length ({len(values)}) must equal bits ({bits})"
            )
        states = [bool(v) for v in values]

    # ── Layout constants (derived from the 4-bit reference circuit) ────
    Y = 208            # y of the main mux / D-flip-flop row
    X0 = 448           # x of the first flip-flop's D pin
    STEP = 208         # horizontal spacing between stages
    FF_W = 48          # DFlipFlop second point (x1 -> x2)
    Q_OFF = 96         # Q pin is this far right of a flip-flop's D pin
    MUX_W = 32         # mux second point (x1 -> x2)
    MUX_SEL_OFF = 64   # a mux's select (S0) pin is this far right of its x1
    MASTER_OFF = 64    # load/shift switch sits this far left of the first mux
    SEL_Y = Y + 96      # y of the shared select (S0) bus, 304
    IN_Y_OFF = 32       # a mux's I0 pin is this far below the main row
    IN_TAIL = 416       # y of the bottom end of each parallel-input toggle
    CLK_BUS_Y = 336     # y of the shared clock bus
    CLK_PIN_Y_OFF = 32  # a flip-flop's clock pin is this far below its D pin
    CLK_FREQ = 100      # clock frequency in Hz
    MARK_LEN = 64       # output marker stem length

    mux_x = [X0 - Q_OFF + i * STEP for i in range(bits)]
    dff_x = [X0 + i * STEP for i in range(bits)]

    lines: List[str] = []

    # 1. Header
    lines.append('<cir f="1" ts="0.000005" ic="10.20027730826997" cb="50" pb="50" vr="5" mts="5e-11">')

    # 2. Mux + flip-flop pairs, one per stage
    for mx, dx in zip(mux_x, dff_x):
        lines.append(f'  <mux x="{mx} {Y} {mx + MUX_W} {Y}" f="0" se="1"/>')
        lines.append(f'  <DFlipFlop x="{dx} {Y} {dx + FF_W} {Y}" f="0"/>')

    # 3. Shift-feedback wires: previous stage's Q -> this stage's mux I1 pin
    for i in range(1, bits):
        prev_q = dff_x[i - 1] + Q_OFF
        lines.append(f'  <w x="{prev_q} {Y} {mux_x[i]} {Y}" f="0"/>')

    # 4. Parallel (I0) inputs - one manual H/L toggle per bit
    for mx, state in zip(mux_x, states):
        p_attr = ' p="1"' if state else ''
        lines.append(f'  <L x="{mx} {Y + IN_Y_OFF} {mx} {IN_TAIL}" f="0"{p_attr}/>')

    # 5. Clock source and shared clock bus
    clk_src_x = mux_x[0] + 16
    lines.append(
        f'  <R x="{clk_src_x} {CLK_BUS_Y} {clk_src_x - 112} {CLK_BUS_Y}" f="1" wf="2" '
        f'fr="{CLK_FREQ}" maxv="2.5" bias="2.5"/>'
    )
    lines.append(f'  <w x="{clk_src_x} {CLK_BUS_Y} {dff_x[0]} {CLK_BUS_Y}" f="0"/>')
    for i in range(bits - 1):
        lines.append(f'  <w x="{dff_x[i]} {CLK_BUS_Y} {dff_x[i + 1]} {CLK_BUS_Y}" f="0"/>')
    for dx in dff_x:
        lines.append(f'  <w x="{dx} {CLK_BUS_Y} {dx} {Y + CLK_PIN_Y_OFF}" f="0"/>')

    # 6. Load/shift master switch, inverter, and shared select (S0) bus
    master_x = mux_x[0] - MASTER_OFF
    lines.append(f'  <L x="{master_x} {Y} {master_x - 48} {Y}" f="0" p="1"/>')
    lines.append(f'  <I x="{master_x} {Y} {master_x} {SEL_Y}" f="0" sl="0.5" hi="5"/>')
    sel_x = [mx + MUX_SEL_OFF for mx in mux_x]
    lines.append(f'  <w x="{sel_x[0]} {SEL_Y} {master_x} {SEL_Y}" f="0"/>')
    for i in range(bits - 1):
        lines.append(f'  <w x="{sel_x[i]} {SEL_Y} {sel_x[i + 1]} {SEL_Y}" f="0"/>')

    # 7. Serial output marker on the final stage's Q
    last_q = dff_x[-1] + Q_OFF
    lines.append(f'  <M x="{last_q} {Y} {last_q + MARK_LEN} {Y}" f="0"/>')

    # 8. Text labels
    lines.append(f'  <x x="{master_x - 58} {Y - 30} {master_x + 49} {Y - 27}" f="4" si="24" te="load/shift"/>')
    lines.append(f'  <x x="{mux_x[0] - 109} {IN_TAIL + 1} {mux_x[0] - 39} {IN_TAIL + 4}" f="4" si="24" te="inputs"/>')
    lines.append(f'  <x x="{last_q + 33} {Y - 43} {last_q + 109} {Y - 40}" f="4" si="24" te="output"/>')

    lines.append('</cir>')

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import sys

    try:
        bits = int(sys.argv[1]) if len(sys.argv) > 1 else 4
        init = sys.argv[2] if len(sys.argv) > 2 else None
        circuit = piso_shift_register(bits, init)
    except (ValueError, TypeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"=== {bits}-bit PISO Shift Register ===", file=sys.stderr)
    print(circuit)
