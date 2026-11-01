"""Generate a Falstad (CircuitJS) emitter-follower (common-collector) netlist."""

import math
import warnings

from ._parts import (DesignWarning, assemble, bjt, cap, dc_rail, gnd, index_of, out_marker,
                     require_positive, res, sine_rail, wire)

VBE_V = 0.7
DEFAULT_INPUT_AMPLITUDE = 1.0
DEFAULT_INPUT_FREQUENCY = 40.0
DEFAULT_INPUT_CAPACITOR = 3e-6


def emitter_follower(
    supply_voltage: float,
    emitter_current: float,
    emitter_resistor: float,
    beta: float = 100.0,
    divider_current: float = None,
    input_amplitude: float = DEFAULT_INPUT_AMPLITUDE,
    input_frequency: float = DEFAULT_INPUT_FREQUENCY,
    input_capacitor: float = DEFAULT_INPUT_CAPACITOR,
) -> str:
    """Generate a Falstad-format emitter follower (common-collector buffer).

    An NPN transistor with its collector on the supply, a base divider (R1 from the
    supply, R2 to ground), an input coupling capacitor, and the output taken at the
    emitter across Re. The voltage gain is just under +1: Re sets the bias point and
    the output impedance, not the gain. The output is DC-coupled, so it sits at
    VE = Ic*Re volts above ground with the signal riding on it. Bias design
    (IE = IC, VBE = 0.7 V): VB = VE + 0.7, R2 = VB/ID, R1 = (Vcc - VB)/ID with
    ID = divider_current (default 10 * Ic/beta).

    Args:
        supply_voltage: Supply Vcc in volts.
        emitter_current: Quiescent emitter current in amps (0.002 = 2 mA).
        emitter_resistor: Re in ohms; the output is taken across it.
        beta: Transistor current gain (hFE).
        divider_current: Current through the base divider in amps. Default 10x the base current.
        input_amplitude: Peak amplitude of the input source in volts.
        input_frequency: Frequency of the input source in hertz.
        input_capacitor: Input coupling capacitor in farads.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If any argument is not a finite number > 0, if the bias does not fit in
            the supply (VB >= Vcc or VCE <= 0), or if divider_current <= base current.

    Warns:
        DesignWarning: If the input amplitude exceeds the headroom around the bias point,
            or the input capacitor is too small for the frequency.
    """
    for name, value in (("supply_voltage", supply_voltage), ("emitter_current", emitter_current),
                        ("emitter_resistor", emitter_resistor), ("beta", beta),
                        ("input_amplitude", input_amplitude), ("input_frequency", input_frequency),
                        ("input_capacitor", input_capacitor)):
        require_positive(name, value)

    ve = emitter_current * emitter_resistor
    vb = ve + VBE_V
    vce = supply_voltage - ve
    if vb >= supply_voltage:
        raise ValueError(f"VB ({vb:.3g} V) would exceed the supply ({supply_voltage:g} V) - lower the current or Re")
    if vce <= 0:
        raise ValueError(f"VCE would be {vce:.3g} V - lower the current or Re")
    ib = emitter_current / beta
    idiv = divider_current if divider_current is not None else 10 * ib
    if idiv <= ib:
        raise ValueError("divider_current must be greater than the base current (emitter_current / beta)")
    r2 = vb / idiv
    r1 = (supply_voltage - vb) / idiv

    headroom = min(ve, vce)
    if input_amplitude > headroom:
        warnings.warn(f"input amplitude {input_amplitude:g} V exceeds the headroom {headroom:.3g} V around the bias "
                      f"point - the output will likely clip; raise the current or Re", DesignWarning, stacklevel=2)
    r_base = r1 * r2 / (r1 + r2)
    xc_in = 1 / (2 * math.pi * input_frequency * input_capacitor)
    if xc_in > r_base / 10:
        warnings.warn(f"input capacitor reactance {xc_in:.3g} ohm at {input_frequency:g} Hz is not small next to the "
                      f"{r_base:.3g} ohm base divider - the signal will be attenuated", DesignWarning, stacklevel=2)

    el = [
        wire(256, 96, 352, 96),
        res(256, 96, 256, 192, r1),
        res(256, 192, 256, 304, r2),
        bjt(256, 192, 352, 192, beta),
        wire(352, 96, 352, 176),
        res(352, 208, 352, 304, emitter_resistor),
        wire(256, 304, 352, 304),
        cap(208, 192, 256, 192, input_capacitor, -vb),
        sine_rail(208, 192, 160, 192, input_frequency, input_amplitude),
        gnd(256, 304, 256, 336),
        dc_rail(256, 96, 160, 96, supply_voltage),
        out_marker(352, 208, 416, 208),
    ]
    step = min(5e-6, 1 / (200 * input_frequency))
    src = el.index(sine_rail(208, 192, 160, 192, input_frequency, input_amplitude))
    return assemble(el, step, [(src, 2 * input_amplitude), (index_of(el, "O"), 2 * input_amplitude)])
