"""Generate a Falstad (CircuitJS) flash ADC netlist: resistor ladder, comparators, XOR encoder."""

from ._parts import (assemble, dc_rail, gnd, opamp, require_positive, res, wire)

LOGIC_V = 5.0           # comparator rails and gate high level


def gate(kind: int, x1, y1, x2, y2, inputs: int) -> str:
    """Logic gate (150 AND, 151 NAND, 152 OR, 153 NOR, 154 XOR): inputs on the left, output at p2."""
    return f"{kind} {x1} {y1} {x2} {y2} 0 {inputs} 0.0 {LOGIC_V!r}"


def logic_output(x1, y1, x2, y2) -> str:
    return f"M {x1} {y1} {x2} {y2} 0 2.5"


def flash_adc(
    bits: int = 3,
    reference_voltage: float = 5.0,
    input_frequency: float = 20.0,
    ladder_resistor: float = 1000.0,
) -> str:
    """Generate a Falstad-format flash ADC with 2 or 3 bits.

    A ladder of 2^bits equal resistors from the reference to ground makes the 2^bits - 1 thresholds
    k x Vref / 2^bits. One comparator per threshold (an op-amp with no feedback, powered from 0 V to 5 V) turns
    on when the input is above its threshold, giving a thermometer code. An encoder of XOR gates turns the count
    of active comparators into binary: the top bit is the middle comparator, and every lower bit is the parity
    of the comparators at its weights (for 3 bits: b1 = t2 xor t4 xor t6, b0 = t1 xor ... xor t7). The input is
    a triangle wave sweeping 0 V to the reference, so every code appears, and the three binary outputs are
    shown on logic-output indicators.

    Args:
        bits: Resolution, 2 or 3 (the gate model allows at most 8 inputs per gate, so 4 bits cannot be encoded
            this way).
        reference_voltage: Full-scale voltage in volts (one LSB is reference_voltage / 2^bits).
        input_frequency: Frequency of the triangle input sweep in hertz.
        ladder_resistor: Value of each ladder resistor in ohms.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If bits is not 2 or 3, or a number is not a finite number > 0.
    """
    if bits not in (2, 3):
        raise ValueError("bits must be 2 or 3 (the encoder uses multi-input XOR gates, which allow at most 8 inputs)")
    for name, value in (("reference_voltage", reference_voltage), ("input_frequency", input_frequency),
                        ("ladder_resistor", ladder_resistor)):
        require_positive(name, value)
    m = 2 ** bits
    yl = lambda j: 80 + 48 * j                               # ladder node j (0 = reference, m = ground)
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

    gates = {}                                               # output bit -> (rows, y centre)
    if bits == 3:
        gates[0] = ([1, 2, 3, 4, 5, 6, 7], 224)
        gates[1] = ([2, 4, 6], 432)
        top = 4
    else:
        gates[0] = ([1, 2, 3], 240)
        top = 2
    lane = {k: 400 + 16 * (m - k) for k in comp_y}   # high k nearest the comparators: no stub runs along another net's wire
    xg = 400 + 16 * m + 32
    targets = {k: [] for k in comp_y}                        # k -> rows it must reach
    outputs = []
    for bit, (ks, yc) in sorted(gates.items()):
        n = len(ks)
        el.append(gate(154, xg, yc, xg + 64, yc, n))
        for i, k in enumerate(ks):
            row = yc - 16 * (-(n // 2) + i)                  # input i sits at y1 - 16 * i0
            targets[k].append(row)
        el.append(logic_output(xg + 64, yc, xg + 96, yc))
        outputs.append((bit, yc))
    out_row = 480                                            # direct output of the top bit
    targets[top].append(out_row)
    el.append(wire(lane[top], out_row, xg + 64, out_row))
    el.append(logic_output(xg + 64, out_row, xg + 96, out_row))
    for k, yc in comp_y.items():
        xl = lane[k]
        el.append(wire(384, yc, xl, yc))
        ys = sorted([yc] + targets[k])
        for a, b in zip(ys, ys[1:]):
            if a != b:
                el.append(wire(xl, a, xl, b))
        for row in targets[k]:
            if row == out_row and k == top:
                continue
            el.append(wire(xl, row, xg, row))
    step = min(5e-6, 1 / (2000 * input_frequency))
    return assemble(el, step, [(input_index, reference_voltage)])
