"""Generate a Falstad (CircuitJS) common-emitter amplifier netlist."""

import math
import warnings

from ._parts import (DesignWarning, assemble, bjt, cap, dc_rail, fmt, gnd, index_of,
                     out_marker, require_positive, res, sine_rail, wire)

VBE_V = 0.7            # silicon base-emitter drop used for the bias calculation
DEFAULT_INPUT_AMPLITUDE = 0.5
DEFAULT_INPUT_FREQUENCY = 80.0
DEFAULT_COUPLING_F = 5e-6
DEFAULT_LOAD_OHMS = 1e6


def common_emitter_amp(
    supply_voltage: float,
    collector_current: float,
    collector_resistor: float,
    emitter_resistor: float,
    beta: float = 100.0,
    divider_current: float = None,
    input_amplitude: float = DEFAULT_INPUT_AMPLITUDE,
    input_frequency: float = DEFAULT_INPUT_FREQUENCY,
    input_capacitor: float = DEFAULT_COUPLING_F,
    output_capacitor: float = DEFAULT_COUPLING_F,
    load_resistor: float = DEFAULT_LOAD_OHMS,
) -> str:
    """Generate a Falstad-format voltage-divider-biased common-emitter amplifier.

    An NPN transistor with a base divider (R1 from the supply, R2 to ground), a
    collector resistor Rc, an UNBYPASSED emitter resistor Re, a coupling capacitor
    in at the base and one out at the collector. The output is inverted and the
    voltage gain is roughly -Rc/Re. Bias design (IE = IC, VBE = 0.7 V):
        VE = Ic*Re, VB = VE + 0.7, VC = Vcc - Ic*Rc, VCE = VC - VE
        ID = divider_current (default 10 * Ic/beta), R2 = VB/ID, R1 = (Vcc - VB)/ID
    The input and output capacitors form high-pass filters with the resistance
    around them, so the frequency cannot be chosen freely.

    Args:
        supply_voltage: Supply Vcc in volts.
        collector_current: Quiescent collector current in amps (0.001 = 1 mA).
        collector_resistor: Rc in ohms.
        emitter_resistor: Re in ohms (unbypassed).
        beta: Transistor current gain (hFE).
        divider_current: Current through the base divider in amps. Default 10x the base current.
        input_amplitude: Peak amplitude of the input source in volts.
        input_frequency: Frequency of the input source in hertz.
        input_capacitor: Input coupling capacitor in farads.
        output_capacitor: Output coupling capacitor in farads.
        load_resistor: Load resistor at the output in ohms (1 Mohm in the original circuit).

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If any argument is not a finite number > 0, if the bias point does not
            fit in the supply (VB >= Vcc or VCE <= 0), or if divider_current <= base current.

    Warns:
        DesignWarning: If the estimated output swing exceeds the headroom, or a coupling
            capacitor is too small for the frequency.
    """
    for name, value in (("supply_voltage", supply_voltage), ("collector_current", collector_current),
                        ("collector_resistor", collector_resistor), ("emitter_resistor", emitter_resistor),
                        ("beta", beta), ("input_amplitude", input_amplitude),
                        ("input_frequency", input_frequency), ("input_capacitor", input_capacitor),
                        ("output_capacitor", output_capacitor), ("load_resistor", load_resistor)):
        require_positive(name, value)

    ve = collector_current * emitter_resistor
    vb = ve + VBE_V
    vc = supply_voltage - collector_current * collector_resistor
    vce = vc - ve
    if vb >= supply_voltage:
        raise ValueError(f"VB ({vb:.3g} V) would exceed the supply ({supply_voltage:g} V) - lower the current or Re")
    if vce <= 0:
        raise ValueError(f"VCE would be {vce:.3g} V (saturated) - lower the current, Rc or Re")
    ib = collector_current / beta
    idiv = divider_current if divider_current is not None else 10 * ib
    if idiv <= ib:
        raise ValueError("divider_current must be greater than the base current (collector_current / beta)")
    r2 = vb / idiv
    r1 = (supply_voltage - vb) / idiv

    swing = collector_resistor / emitter_resistor * input_amplitude
    headroom = min(vce, supply_voltage - vce)
    if swing > headroom:
        warnings.warn(f"estimated output swing {swing:.3g} V peak (gain {collector_resistor / emitter_resistor:.3g} x "
                      f"{input_amplitude:g} V) exceeds the headroom {headroom:.3g} V - the output will likely clip",
                      DesignWarning, stacklevel=2)
    r_base = r1 * r2 / (r1 + r2)
    xc_in = 1 / (2 * math.pi * input_frequency * input_capacitor)
    if xc_in > r_base / 10:
        warnings.warn(f"input capacitor reactance {xc_in:.3g} ohm at {input_frequency:g} Hz is not small next to the "
                      f"{r_base:.3g} ohm base divider - the signal will be attenuated", DesignWarning, stacklevel=2)
    xc_out = 1 / (2 * math.pi * input_frequency * output_capacitor)
    if xc_out > load_resistor / 10:
        warnings.warn(f"output capacitor reactance {xc_out:.3g} ohm at {input_frequency:g} Hz is not small next to the "
                      f"{load_resistor:.3g} ohm load - the output will be attenuated", DesignWarning, stacklevel=2)

    el = [
        wire(240, 48, 336, 48),
        res(240, 48, 240, 208, r1),
        res(240, 208, 240, 352, r2),
        bjt(240, 208, 336, 208, beta),
        wire(240, 352, 336, 352),
        gnd(240, 352, 240, 384),
        dc_rail(240, 48, 144, 48, supply_voltage),
        res(336, 48, 336, 192, collector_resistor),
        res(336, 224, 336, 352, emitter_resistor),
        cap(240, 208, 160, 208, input_capacitor, vb),
        sine_rail(160, 208, 112, 208, input_frequency, input_amplitude),
        cap(336, 192, 416, 192, output_capacitor, vc),
        out_marker(416, 192, 464, 192),
        res(416, 192, 416, 272, load_resistor),
        gnd(416, 272, 416, 304),
    ]
    step = min(5e-6, 1 / (200 * input_frequency))
    src = el.index(sine_rail(160, 208, 112, 208, input_frequency, input_amplitude))
    return assemble(el, step, [(src, 2 * input_amplitude), (index_of(el, "O"), 2 * max(swing, input_amplitude))])
