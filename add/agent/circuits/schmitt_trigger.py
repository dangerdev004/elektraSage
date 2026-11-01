"""Generate a Falstad (CircuitJS) inverting Schmitt trigger netlist."""

import warnings

from ._parts import (DesignWarning, assemble, dc_rail, gnd, index_of, opamp, out_marker,
                     require_positive, res, sine_rail, wire)

VSAT_V = 15.0           # op-amp output limits, +/-15 V
DEFAULT_RF = 100000.0
DEFAULT_REFERENCE = 10.0
DEFAULT_FREQUENCY = 40.0
DEFAULT_AMPLITUDE = 5.0


def schmitt_trigger(
    upper_trip_voltage: float,
    lower_trip_voltage: float,
    feedback_resistance: float = DEFAULT_RF,
    reference_voltage: float = DEFAULT_REFERENCE,
    input_frequency: float = DEFAULT_FREQUENCY,
    input_amplitude: float = DEFAULT_AMPLITUDE,
    input_offset: float = None,
) -> str:
    """Generate a Falstad-format inverting Schmitt trigger (comparator with hysteresis).

    The input drives the op-amp's inverting input. The non-inverting input sits on a
    three-resistor node: Rf back to the output (positive feedback, which gives the
    hysteresis), R2 to a reference rail, R3 to ground. With the output saturated at
    +/-15 V, Millman's theorem gives the trip points:
        UTP = (Vsat/Rf + Vref/R2) / (1/Rf + 1/R2 + 1/R3)     (output high)
        LTP = (-Vsat/Rf + Vref/R2) / (1/Rf + 1/R2 + 1/R3)    (output low)
    The input must fall below LTP to force the output high and rise above UTP to force it low;
    in between the output holds. The lower trip point may be zero or negative: when
    UTP + LTP = 0 there is no reference branch at all, and when it is negative the reference
    rail is negative. The ideal comparator does not care how fast the input moves.

    Args:
        upper_trip_voltage: Upper trip point UTP in volts (must be above lower_trip_voltage).
        lower_trip_voltage: Lower trip point LTP in volts.
        feedback_resistance: Rf in ohms.
        reference_voltage: Magnitude of the reference rail in volts (its sign is chosen by the design).
        input_frequency: Frequency of the input sine in hertz.
        input_amplitude: Peak amplitude of the input sine in volts.
        input_offset: DC level the input sine rides on, in volts. Default: halfway between the trip points.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If upper_trip_voltage <= lower_trip_voltage, if a numeric argument that must be
            positive is not, if the trip points are wider than +/-15 V allows, or if no positive R3
            gives these thresholds with this Rf (try a different Rf or a narrower band).

    Warns:
        DesignWarning: If the input sine never crosses both trip points, so the output will not toggle.
    """
    for name, value in (("feedback_resistance", feedback_resistance), ("reference_voltage", reference_voltage),
                        ("input_frequency", input_frequency), ("input_amplitude", input_amplitude)):
        require_positive(name, value)
    utp, ltp = float(upper_trip_voltage), float(lower_trip_voltage)
    if utp <= ltp:
        raise ValueError("upper_trip_voltage must be greater than lower_trip_voltage")
    if abs(utp) >= VSAT_V or abs(ltp) >= VSAT_V:
        raise ValueError(f"trip points must lie inside the +/-{VSAT_V:g} V output limits")
    rf = feedback_resistance
    total = utp + ltp
    if abs(total) < 1e-12:
        r2, vref = None, 0.0
    else:
        vref = reference_voltage if total > 0 else -reference_voltage
        r2 = vref * (utp - ltp) * rf / (total * VSAT_V)
    inv_r3 = (2 * VSAT_V / rf) / (utp - ltp) - 1 / rf - (1 / r2 if r2 else 0.0)
    if inv_r3 <= 1e-12:
        raise ValueError("no positive R3 solves these thresholds with this Rf and reference - try a different "
                         "Rf or a narrower or shifted threshold band")
    r3 = 1 / inv_r3

    offset = (utp + ltp) / 2 if input_offset is None else float(input_offset)
    if offset + input_amplitude <= utp or offset - input_amplitude >= ltp:
        warnings.warn(f"the input swings {offset - input_amplitude:.3g} V to {offset + input_amplitude:.3g} V and does "
                      f"not cross both trip points ({ltp:g} V and {utp:g} V), so the output will not toggle",
                      DesignWarning, stacklevel=2)

    src = sine_rail(224, 192, 128, 192, input_frequency, input_amplitude, offset)
    el = [
        opamp(320, 208, 432, 208, VSAT_V, flags=0),
        wire(432, 208, 432, 272),
        res(432, 272, 288, 272, rf),
        wire(288, 224, 320, 224),
        wire(288, 224, 288, 272),
        res(288, 272, 288, 336, r3),
        gnd(288, 336, 288, 368),
        out_marker(432, 208, 480, 208),
        wire(320, 192, 224, 192),
        src,
    ]
    if r2 is not None:
        el += [wire(288, 224, 288, 144), res(288, 144, 288, 80, r2), dc_rail(288, 80, 288, 48, vref)]
    step = min(5e-6, 1 / (200 * input_frequency))
    return assemble(el, step, [(el.index(src), 2 * (abs(offset) + input_amplitude)), (index_of(el, "O"), 2 * VSAT_V)])
