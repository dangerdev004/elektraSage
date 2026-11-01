"""Generate a Falstad (CircuitJS) R-2R ladder DAC netlist."""

import warnings

from ._parts import (DesignWarning, analog_switch, assemble, dc_rail, gnd, index_of, logic_input,
                     opamp, out_marker, require_positive, res, wire)

SWITCH_RON_OHM = 20.0       # Falstad analog switch on-resistance
OPAMP_RAIL_V = 20.0
MIN_BITS, MAX_BITS = 2, 8
DEFAULT_CODE = 6

SW_X0, SW_DX = 80, 80
TOP_Y, SW_TOP_Y, SW_BOT_Y, BUS_Y = 80, 144, 240, 256


def r2r_dac(
    bits: int = 4,
    reference_voltage: float = 16.0,
    ladder_resistance: float = 50000.0,
    output_step: float = None,
    feedback_resistance: float = None,
    code: int = None,
) -> str:
    """Generate a Falstad-format voltage-mode R-2R ladder DAC with an inverting op-amp summer.

    The reference drives the first ladder node; every node has a 2R leg down to an analog
    switch that connects the leg either to ground (bit = 0) or to the op-amp's virtual
    ground (bit = 1). Each node sits at half the voltage of the one before it, so the leg
    currents are binary weighted and
        Vout = -Rf * sum(bit_k * Vref / (2R * 2**k)) = -(Rf * Vref / (R * 2**N)) * code
    One code step changes the output by step = Vref * Rf / (R * 2**N); the output is negative.
    Give EITHER output_step (Rf is then calculated) OR feedback_resistance; with neither,
    Rf = R. The simulated output differs from the ideal by about 0.02% because the switches
    have 20 ohm on-resistance. The leftmost leg is the MSB; click the logic inputs to change
    the code. This circuit generates its own levels and has no signal input, so it can only
    be the first stage of a cascade.

    Args:
        bits: Number of bits (2 to 8).
        reference_voltage: Reference voltage Vref in volts.
        ladder_resistance: Ladder resistor R in ohms (2R is derived).
        output_step: Output change per code step in volts (alternative to feedback_resistance).
        feedback_resistance: Feedback resistor Rf in ohms (alternative to output_step).
        code: Starting digital code, 0 to 2**bits - 1. Default 6 (or the top code for few bits).

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If bits is not a whole number from 2 to 8, if both output_step and
            feedback_resistance are given, if the code is out of range, or if a numeric
            argument that must be positive is not.

    Warns:
        DesignWarning: If the full-scale output reaches the +/-20 V op-amp limit, or the switch
            resistance is large next to 2R.
    """
    if int(bits) != bits or not (MIN_BITS <= bits <= MAX_BITS):
        raise ValueError(f"bits must be a whole number from {MIN_BITS} to {MAX_BITS}")
    n = int(bits)
    require_positive("reference_voltage", reference_voltage)
    require_positive("ladder_resistance", ladder_resistance)
    if output_step is not None and feedback_resistance is not None:
        raise ValueError("give either output_step OR feedback_resistance, not both")
    if output_step is not None:
        require_positive("output_step", output_step)
    if feedback_resistance is not None:
        require_positive("feedback_resistance", feedback_resistance)

    levels = 2 ** n
    r = ladder_resistance
    if output_step is not None:
        rf = output_step * r * levels / reference_voltage
    else:
        rf = feedback_resistance if feedback_resistance is not None else r
    step = reference_voltage * rf / (r * levels)
    full_scale = step * (levels - 1)
    if code is None:
        code = min(DEFAULT_CODE, levels - 1)
    if int(code) != code or not (0 <= code < levels):
        raise ValueError(f"code must be a whole number from 0 to {levels - 1} for {n} bits")
    code = int(code)
    if full_scale > OPAMP_RAIL_V:
        warnings.warn(f"full-scale output would be -{full_scale:.4g} V, beyond the op-amp's +/-{OPAMP_RAIL_V:g} V "
                      f"limits - the top codes will clip. Lower the step, Vref or Rf", DesignWarning, stacklevel=2)
    err_lsb = SWITCH_RON_OHM / (2 * r) * levels
    if err_lsb > 0.25:
        warnings.warn(f"the {SWITCH_RON_OHM:g} ohm switch resistance is large next to 2R = {2 * r:g} ohm and shifts "
                      f"the top codes by about {err_lsb:.2g} of one step. Use a larger R or fewer bits",
                      DesignWarning, stacklevel=2)

    bits_hi = [(code >> (n - 1 - k)) & 1 for k in range(n)]
    x = [SW_X0 + SW_DX * k for k in range(n)]
    xl = x[-1]
    ox = xl + 96
    el = []
    for k in range(n):
        el.append(analog_switch(x[k], SW_TOP_Y, x[k], SW_BOT_Y))
        el.append(gnd(x[k] - 16, SW_BOT_Y, x[k] - 16, 288))
        el.append(wire(x[k] + 16, 192, x[k] + 32, 192))
        el.append(wire(x[k] + 32, 192, x[k] + 32, 320))
        el.append(logic_input(x[k] + 32, 320, x[k] + 32, 352, bool(bits_hi[k])))
        el.append(wire(x[k] + 16, SW_BOT_Y, x[k] + 16, BUS_Y))
    for k in range(n - 1):
        el.append(wire(x[k] + 16, BUS_Y, x[k + 1] + 16, BUS_Y))
    el.append(wire(xl + 16, BUS_Y, ox, BUS_Y))
    el.append(res(x[0], TOP_Y, x[0], SW_TOP_Y, 2 * r))
    for k in range(1, n):
        el.append(res(x[k], SW_TOP_Y, x[k], TOP_Y, 2 * r))
    el.append(res(x[1], TOP_Y, x[0], TOP_Y, r))
    for k in range(1, n - 1):
        el.append(res(x[k], TOP_Y, x[k + 1], TOP_Y, r))
    el.append(res(xl, TOP_Y, xl + 80, TOP_Y, 2 * r))
    el.append(gnd(xl + 80, TOP_Y, xl + 80, 112))
    el.append(dc_rail(x[0], TOP_Y, 32, TOP_Y, reference_voltage))
    el.append(wire(ox, BUS_Y, ox, 224))
    el.append(res(ox, 224, ox + 112, 224, rf))
    el.append(wire(ox + 112, 224, ox + 112, 272))
    el.append(out_marker(ox + 112, 272, ox + 176, 272))
    el.append(gnd(ox, 288, ox, 320))
    el.append(opamp(ox, 272, ox + 112, 272, OPAMP_RAIL_V, flags=0))
    return assemble(el, 5e-6, [(index_of(el, "O"), 2 * max(full_scale, 1.0))])
