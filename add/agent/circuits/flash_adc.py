"""Generate a Falstad (CircuitJS) flash ADC netlist: resistor ladder, comparators, XOR parity encoder."""

from ._parts import (assemble, dc_rail, gnd, opamp, require_positive, res, wire)

LOGIC_V = 5.0           # comparator rails and gate high level
MAX_BITS = 8            # 255 comparators; beyond this the circuit is too large to be useful in CircuitJS
MAX_GATE_INPUTS = 8     # CircuitJS logic gates take at most 8 inputs
PITCH = 48              # vertical distance between comparators (an op-amp is 32 tall, its inputs 32 apart)
GATE_LENGTH = 64
COLUMN = 96             # horizontal step between gates of one parity chain (gate + a short routing channel)


def gate(kind: int, x1, y1, x2, y2, inputs: int) -> str:
    """Logic gate (150 AND, 151 NAND, 152 OR, 153 NOR, 154 XOR): inputs on the left, output at p2."""
    return f"{kind} {x1} {y1} {x2} {y2} 0 {inputs} 0.0 {LOGIC_V!r}"


def logic_output(x1, y1, x2, y2) -> str:
    return f"M {x1} {y1} {x2} {y2} 0 2.5"


def gate_offsets(n: int) -> list[int]:
    """Pin offsets (in 16-unit steps) of an n-input gate: symmetric about the centre, skipping 0 when n is even."""
    offsets, i0 = [], -(n // 2)
    for _ in range(n):
        if i0 == 0 and n % 2 == 0:
            i0 += 1
        offsets.append(i0)
        i0 += 1
    return offsets


def _chain_sizes(inputs: int) -> list[int]:
    """Gate input counts for an XOR chain over `inputs` signals: the first gate takes MAX_GATE_INPUTS signals, every
    later gate takes one fewer plus the previous gate's output."""
    sizes, left, first = [], inputs, True
    while left > 0:
        take = min(MAX_GATE_INPUTS if first else MAX_GATE_INPUTS - 1, left)
        sizes.append(take if first else take + 1)
        left -= take
        first = False
    return sizes


def _plan(bits: int, start: int, comp_rows: dict[int, int]):
    """Place one XOR chain per binary bit (bit 0 .. bits-2; the top bit is the middle comparator itself), the shortest
    chain at the top, in bands that never share a row. Returns (bands, rows free for comparators, next free row)."""
    m = 2 ** bits
    cursor, bands = start, {}
    for j in range(bits - 2, -1, -1):
        sources = [k for k in range(1, m) if k % (2 ** j) == 0]     # bit j = parity of every 2^j-th comparator
        gates = []
        for position, n in enumerate(_chain_sizes(len(sources))):
            yc = cursor + 16 * (n // 2)
            rows = [yc - 16 * o for o in gate_offsets(n)]
            top = min(rows)
            gates.append(dict(n=n, yc=yc, rows=rows, top=top, chain_row=top if position else None))
            cursor = yc + 16 * (n // 2) + 32
        pins = [r for g in gates for r in g["rows"] if r != g["chain_row"]]
        bands[j] = dict(sources=sources, gates=gates, pins=pins)
    return bands, cursor


def _assign(bands, comp_row_owner):
    """Choose which comparator drives which pin. A pin row that equals another comparator's output row is only safe
    when its source lane lies to the right of that comparator's lane (lanes run right-to-left in index order), i.e.
    source <= the comparator that owns the row. Bipartite matching finds a full assignment; None if there isn't one."""
    result = {}
    for j, band in bands.items():
        allowed = {r: [k for k in band["sources"] if r not in comp_row_owner or k <= comp_row_owner[r]]
                   for r in band["pins"]}
        taken: dict[int, int] = {}                                  # source -> pin row

        def place(row, seen):
            for k in allowed[row]:
                if k in seen:
                    continue
                seen.add(k)
                if k not in taken or place(taken[k], seen):
                    taken[k] = row
                    return True
            return False

        for row in sorted(allowed, key=lambda r: len(allowed[r])):
            if not place(row, set()):
                return None
        result.update({row: k for k, row in taken.items()})
    return result


def flash_adc(
    bits: int = 3,
    reference_voltage: float = 5.0,
    input_frequency: float = 20.0,
    ladder_resistor: float = 1000.0,
) -> str:
    """Generate a Falstad-format flash ADC with 2 to 8 bits.

    A ladder of 2^bits equal resistors from the reference to ground makes the 2^bits - 1 thresholds
    k x Vref / 2^bits. One comparator per threshold (an op-amp with no feedback, powered from 0 V to 5 V) turns
    on when the input is above its threshold, giving a thermometer code. An encoder of XOR gates turns the count
    of active comparators into binary: the top bit is the middle comparator, and every lower bit j is the parity of
    the comparators at multiples of 2^j (for 3 bits: b1 = t2 xor t4 xor t6, b0 = t1 xor ... xor t7). Because a gate
    takes at most 8 inputs, a bit with more comparators uses a chain of gates, each passing its parity on to the
    next. The input is a triangle wave sweeping 0 V to the reference, so every code appears, and the binary
    outputs are shown on logic-output indicators.

    Args:
        bits: Resolution, 2 to 8 (a flash ADC needs 2^bits - 1 comparators, so 8 bits is already 255 of them).
        reference_voltage: Full-scale voltage in volts (one LSB is reference_voltage / 2^bits).
        input_frequency: Frequency of the triangle input sweep in hertz.
        ladder_resistor: Value of each ladder resistor in ohms.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If bits is not an integer from 2 to 8, or a number is not a finite number > 0.
    """
    if isinstance(bits, bool) or not isinstance(bits, int) or not 2 <= bits <= MAX_BITS:
        raise ValueError(f"bits must be a whole number from 2 to {MAX_BITS} (a flash ADC needs 2^bits - 1 comparators, "
                         f"so more than {MAX_BITS} bits would make the circuit unreasonably large)")
    for name, value in (("reference_voltage", reference_voltage), ("input_frequency", input_frequency),
                        ("ladder_resistor", ladder_resistor)):
        require_positive(name, value)
    m = 2 ** bits
    yl = lambda j: 80 + PITCH * j                            # ladder node j (0 = reference, m = ground)
    el = [dc_rail(192, yl(0), 144, yl(0), reference_voltage)]
    for j in range(m):
        el.append(res(192, yl(j), 192, yl(j + 1), ladder_resistor))
    el.append(gnd(192, yl(m), 192, yl(m) + 16))

    comp_y = {}                                              # threshold index k -> comparator output row
    for j in range(1, m):
        k = m - j
        y = yl(j)
        el.append(wire(192, y, 320, y))                      # tap to the inverting input
        el.append(opamp(320, y - 16, 384, y - 16, LOGIC_V, flags=1, rail_low=0.0))
        el.append(wire(96, y - 32, 320, y - 32))             # input bus to the non-inverting input
        comp_y[k] = y - 16
    for j in range(1, m - 1):
        el.append(wire(96, yl(j) - 32, 96, yl(j + 1) - 32))
    ybus = yl(m - 1) - 32
    el.append(f"R 96 {ybus} 48 {ybus} 0 3 {input_frequency!r} {reference_voltage / 2!r} {reference_voltage / 2!r}")
    input_index = len(el) - 1                                # the triangle source, not the reference rail

    lane = {k: 400 + 16 * (m - k) for k in comp_y}           # high k nearest the comparators
    x0 = 400 + 16 * m + 32                                   # first gate column, right of every lane
    owner = {y: k for k, y in comp_y.items()}                # row -> comparator whose output sits on it

    plan = None
    for start in range(64, 64 + PITCH * m, 16):              # almost always the first start works
        bands, bottom = _plan(bits, start, comp_y)
        pin_source = _assign(bands, owner)
        if pin_source is not None:
            plan = (bands, bottom, pin_source)
            break
    if plan is None:                                         # pragma: no cover - not reachable for 2..8 bits
        raise RuntimeError("could not route the encoder without overlapping wires")
    bands, bottom, pin_source = plan

    targets = {k: [] for k in comp_y}                        # k -> rows its lane must reach
    pin_x = {}
    for j, band in bands.items():
        for position, g in enumerate(band["gates"]):
            x = x0 + COLUMN * position
            el.append(gate(154, x, g["yc"], x + GATE_LENGTH, g["yc"], g["n"]))
            for row in g["rows"]:
                if row != g["chain_row"]:
                    pin_x[row] = x
                    targets[pin_source[row]].append(row)
            if position:                                     # parity of everything before enters on the top pin
                prev = band["gates"][position - 1]
                xv = x - COLUMN + GATE_LENGTH + 16
                el.append(wire(xv - 16, prev["yc"], xv, prev["yc"]))
                el.append(wire(xv, prev["yc"], xv, g["top"]))
                el.append(wire(xv, g["top"], x, g["top"]))
        last = band["gates"][-1]
        xo = x0 + COLUMN * (len(band["gates"]) - 1) + GATE_LENGTH
        el.append(logic_output(xo, last["yc"], xo + 32, last["yc"]))

    top_k = m // 2                                           # the top bit is that comparator, direct
    out_row = max(bottom, yl(m - 1) + 32)
    out_row += (-out_row) % 16
    targets[top_k].append(out_row)
    xm = x0 + GATE_LENGTH
    el.append(wire(lane[top_k], out_row, xm, out_row))
    el.append(logic_output(xm, out_row, xm + 32, out_row))

    for k, yc in comp_y.items():
        xl = lane[k]
        el.append(wire(384, yc, xl, yc))
        ys = sorted({yc, *targets[k]})
        for a, b in zip(ys, ys[1:]):
            el.append(wire(xl, a, xl, b))
        for row in targets[k]:
            if row != out_row:
                el.append(wire(xl, row, pin_x[row], row))
    step = min(5e-6, 1 / (2000 * input_frequency))
    return assemble(el, step, [(input_index, reference_voltage)])
