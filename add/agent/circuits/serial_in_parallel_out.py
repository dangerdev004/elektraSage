def sipo_shift_register(bits: int) -> str:
    """Generate an N-bit SIPO (serial-in, parallel-out) shift register as Falstad circuit text.

    Layout matches the 4-bit reference circuit (input/output text labels
    omitted): N D flip-flops chained Q -> D, one shared clock bus, a manual
    L/H serial input on the first D, and an output marker on every Q.

    Args:
        bits: Number of register bits. Must be a whole number >= 1.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        TypeError: If bits is not an int (bool, float, str and None are rejected).
        ValueError: If bits < 1.
    """
    if isinstance(bits, bool) or not isinstance(bits, int):
        raise TypeError(f"bits must be a whole number, got {bits!r}")
    if bits < 1:
        raise ValueError(f"bits must be >= 1, got {bits}")

    # ── Layout constants ───────────────────────────────────────────────
    X0 = 448          # x of the first flip-flop's D pin
    Y = 208           # y of the D / Q row
    STEP = 112        # horizontal spacing between flip-flops
    FF_W = 48         # DFlipFlop second point (x1 -> x2)
    Q_OFF = 96        # Q pin is this far right of the D pin
    CLK_DY = 32       # clock pin is this far below the D pin
    BUS_Y = 336       # y of the shared clock bus
    MARK_H = 64       # output marker stem length
    IN_X = 416        # x of the serial-input logic source
    IN_BOTTOM = 416   # y of the bottom end of the serial-input source
    CLK_SRC_X = 368   # x where the clock source meets the bus
    CLK_FREQ = 100    # clock frequency in Hz

    xs = [X0 + i * STEP for i in range(bits)]

    lines: list[str] = []

    # 1. Header
    lines.append('<cir f="1" ts="0.000005" ic="10.20027730826997" cb="50" pb="50" vr="5" mts="5e-11">')

    # 2. D flip-flops
    for x in xs:
        lines.append(f'  <DFlipFlop x="{x} {Y} {x + FF_W} {Y}" f="0"/>')

    # 3. Q -> D inter-FF wires
    for i in range(bits - 1):
        qx = xs[i] + Q_OFF
        lines.append(f'  <w x="{qx} {Y} {xs[i + 1]} {Y}" f="0"/>')

    # 4. Clock source (square wave, 2.5 V) and wire onto the clock bus
    lines.append(
        f'  <R x="{CLK_SRC_X} {BUS_Y} {CLK_SRC_X - 48} {BUS_Y}" f="1" wf="2" '
        f'fr="{CLK_FREQ}" maxv="2.5" bias="2.5"/>'
    )
    lines.append(f'  <w x="{CLK_SRC_X} {BUS_Y} {xs[0]} {BUS_Y}" f="0"/>')

    # 5. Clock bus segments between flip-flops
    for i in range(bits - 1):
        lines.append(f'  <w x="{xs[i]} {BUS_Y} {xs[i + 1]} {BUS_Y}" f="0"/>')

    # 6. Clock drops from the bus up to each flip-flop's clock pin
    for x in xs:
        lines.append(f'  <w x="{x} {BUS_Y} {x} {Y + CLK_DY}" f="0"/>')

    # 7. Serial input (manual L/H toggle) and its wire to the first D
    lines.append(f'  <L x="{IN_X} {Y} {IN_X} {IN_BOTTOM}" f="0"/>')
    lines.append(f'  <w x="{IN_X} {Y} {xs[0]} {Y}" f="0"/>')

    # 8. Output markers on every Q
    for x in xs:
        qx = x + Q_OFF
        lines.append(f'  <M x="{qx} {Y} {qx} {Y - MARK_H}" f="0"/>')

    lines.append('</cir>')

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import sys

    try:
        bits = int(sys.argv[1]) if len(sys.argv) > 1 else 4
        circuit = sipo_shift_register(bits)
    except (ValueError, TypeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"=== {bits}-bit SIPO Shift Register ===", file=sys.stderr)
    print(circuit)
