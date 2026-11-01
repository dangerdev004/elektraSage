"""Generate a Falstad (CircuitJS) binary-weighted-resistor DAC netlist."""

import warnings

from ._parts import (DesignWarning, assemble, gnd, index_of, logic_input, opamp, out_marker,
                     require_positive, res, wire)

OPAMP_RAIL_V = 15.0
MIN_BITS, MAX_BITS = 2, 8
DEFAULT_CODE = 3
DEFAULT_STEP_V = 1.0

ROW_Y0, ROW_DY = 96, 64
IN_X, BUS_X, AMP_X = 112, 176, 208


def binary_weighted_dac(
    bits: int = 4,
    msb_resistance: float = 100.0,
    output_step: float = None,
    feedback_resistance: float = None,
    code: int = None,
    logic_high_voltage: float = 5.0,
) -> str:
    """Generate a Falstad-format binary-weighted-resistor DAC with an inverting op-amp summer.

    Each digital input drives the op-amp's virtual-ground node through its own resistor, and
    the resistors double from the MSB down (R, 2R, 4R, ...), so the currents are binary
    weighted and
        Vout = -Rf * sum(bit_k * Vlogic / R_k) = -(Rf * Vlogic / (R * 2**(N-1))) * code
    One code step changes the output by step = Rf * Vlogic / (R * 2**(N-1)); the output is
    negative. Give EITHER output_step (Rf is then calculated) OR feedback_resistance; with
    neither, one code step is 1 V. Click the logic inputs to change the code. This circuit
    generates its own levels and has no signal input, so it can only be the first stage of a
    cascade.

    Args:
        bits: Number of bits (2 to 8).
        msb_resistance: Resistor of the most significant bit in ohms; the rest are 2x, 4x, ...
        output_step: Output change per code step in volts (alternative to feedback_resistance).
        feedback_resistance: Feedback resistor Rf in ohms (alternative to output_step).
        code: Starting digital code, 0 to 2**bits - 1. Default 3 (or the top code for few bits).
        logic_high_voltage: Voltage of a logic 1 on the inputs, in volts.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If bits is not a whole number from 2 to 8, if both output_step and
            feedback_resistance are given, if the code is out of range, or if a numeric
            argument that must be positive is not.

    Warns:
        DesignWarning: If the full-scale output reaches the +/-15 V op-amp limit, or 7 or more
            bits need a very wide resistor spread.
    """
    if int(bits) != bits or not (MIN_BITS <= bits <= MAX_BITS):
        raise ValueError(f"bits must be a whole number from {MIN_BITS} to {MAX_BITS}")
    n = int(bits)
    require_positive("msb_resistance", msb_resistance)
    require_positive("logic_high_voltage", logic_high_voltage)
    if output_step is not None and feedback_resistance is not None:
        raise ValueError("give either output_step OR feedback_resistance, not both")
    if output_step is not None:
        require_positive("output_step", output_step)
    if feedback_resistance is not None:
        require_positive("feedback_resistance", feedback_resistance)

    levels = 2 ** n
    scale = msb_resistance * 2 ** (n - 1) / logic_high_voltage
    if feedback_resistance is not None:
        rf = feedback_resistance
    else:
        rf = (output_step if output_step is not None else DEFAULT_STEP_V) * scale
    step = rf / scale
    full_scale = step * (levels - 1)
    if code is None:
        code = min(DEFAULT_CODE, levels - 1)
    if int(code) != code or not (0 <= code < levels):
        raise ValueError(f"code must be a whole number from 0 to {levels - 1} for {n} bits")
    code = int(code)
    if full_scale > OPAMP_RAIL_V:
        warnings.warn(f"full-scale output would be -{full_scale:.4g} V, beyond the op-amp's +/-{OPAMP_RAIL_V:g} V "
                      f"limits - the top codes will clip. Lower the step or Rf", DesignWarning, stacklevel=2)
    if n >= 7:
        warnings.warn(f"{n} bits needs a {2 ** (n - 1)}:1 spread of resistor values - real parts would need very "
                      f"tight tolerances; an R-2R ladder avoids this", DesignWarning, stacklevel=2)

    ys = [ROW_Y0 + ROW_DY * k for k in range(n)]
    y_inv = 64 + 64 * (n // 2)
    y_amp = y_inv + 16
    y_fb = y_inv - 64
    out_x = AMP_X + 112
    el = []
    for k in range(n):
        y = ys[k]
        r = msb_resistance * 2 ** k
        el.append(res(BUS_X, y, IN_X, y, r) if k == 1 else res(IN_X, y, BUS_X, y, r))
        el.append(logic_input(IN_X, y, 80, y, bool((code >> (n - 1 - k)) & 1), logic_high_voltage))
    stops = sorted(set(ys + [y_inv]))
    for a, b in zip(stops, stops[1:]):
        el.append(wire(BUS_X, a, BUS_X, b))
    el.append(wire(AMP_X, y_inv, BUS_X, y_inv))
    el.append(opamp(AMP_X, y_amp, out_x, y_amp, OPAMP_RAIL_V, flags=0))
    el.append(wire(AMP_X, y_fb, AMP_X, y_inv))
    el.append(res(AMP_X, y_fb, out_x, y_fb, rf))
    el.append(wire(out_x, y_amp, out_x, y_fb))
    el.append(wire(AMP_X, y_amp + 16, AMP_X, y_amp + 80))
    el.append(gnd(AMP_X, y_amp + 80, AMP_X, y_amp + 112))
    el.append(out_marker(out_x, y_amp, out_x + 48, y_amp))
    return assemble(el, 5e-6, [(index_of(el, "O"), 2 * max(full_scale, 1.0))])
