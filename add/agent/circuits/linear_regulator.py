"""Generate a Falstad (CircuitJS) series linear voltage regulator: zener reference, op-amp, NPN pass transistor."""

import warnings

from ._parts import (DesignWarning, assemble, bjt, gnd, index_of, opamp, out_marker, require_positive, res,
                     sine_rail, wire, zener)

VBE_V = 0.7
DROPOUT_V = 1.0          # minimum Vin - Vout the design allows (Vbe plus op-amp output headroom)


def linear_regulator(
    output_voltage: float = 5.0,
    input_voltage: float = 12.0,
    zener_voltage: float = 3.3,
    load_current: float = 0.1,
    zener_current: float = 0.005,
    divider_current: float = 0.001,
    beta: float = 100.0,
    ripple_amplitude: float = 1.0,
    ripple_frequency: float = 100.0,
) -> str:
    """Generate a Falstad-format series linear regulator.

    The input rail (a DC level with a sine ripple on it) feeds an NPN pass transistor whose emitter is the
    output. A zener, biased from the input through a resistor, sets the reference. An op-amp compares that
    reference with the output divider (R1 from the output, R2 to ground) and drives the pass transistor's base,
    so the output settles at
        Vout = Vz (1 + R1 / R2).
    Design: R2 = Vz / divider_current, R1 = (Vout - Vz) / divider_current, Rz = (Vin - Vz) / zener_current, and the
    load is Vout / load_current. The op-amp's output is limited to 0 V and the nominal input voltage.

    Args:
        output_voltage: Regulated output in volts (above the zener voltage).
        input_voltage: Nominal unregulated input in volts; at least 1 V above the output.
        zener_voltage: Reference zener voltage in volts.
        load_current: Output current drawn by the load resistor, in amps.
        zener_current: Bias current of the zener at the nominal input, in amps.
        divider_current: Current in the output divider, in amps.
        beta: Pass transistor current gain.
        ripple_amplitude: Peak amplitude of the ripple on the input in volts.
        ripple_frequency: Ripple frequency in hertz.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If an argument is not a finite number > 0, the zener is not below the output, or the input is
            less than 1 V above the output (no room to regulate).

    Warns:
        DesignWarning: If the input dips below the dropout limit on the ripple troughs, the zener nearly stops
            conducting on the troughs, or the pass transistor would dissipate a lot of power.
    """
    for name, value in (("output_voltage", output_voltage), ("input_voltage", input_voltage),
                        ("zener_voltage", zener_voltage), ("load_current", load_current),
                        ("zener_current", zener_current), ("divider_current", divider_current),
                        ("beta", beta), ("ripple_amplitude", ripple_amplitude),
                        ("ripple_frequency", ripple_frequency)):
        require_positive(name, value)
    if zener_voltage >= output_voltage:
        raise ValueError(f"zener_voltage ({zener_voltage:g} V) must be below output_voltage ({output_voltage:g} V): "
                         "this regulator can only step the reference up")
    if input_voltage < output_voltage + DROPOUT_V:
        raise ValueError(f"input_voltage {input_voltage:g} V must be at least {DROPOUT_V:g} V above the "
                         f"{output_voltage:g} V output, or the pass transistor has no room to regulate")
    r2 = zener_voltage / divider_current
    r1 = (output_voltage - zener_voltage) / divider_current
    rz = (input_voltage - zener_voltage) / zener_current
    rl = output_voltage / load_current
    if input_voltage - ripple_amplitude < output_voltage + DROPOUT_V:
        warnings.warn(f"on the ripple troughs the input falls to {input_voltage - ripple_amplitude:g} V, within "
                      f"{DROPOUT_V:g} V of the output: regulation is lost there (dropout)", DesignWarning, stacklevel=2)
    iz_min = (input_voltage - ripple_amplitude - zener_voltage) / rz
    if iz_min < 0.2 * zener_current:
        warnings.warn("the zener current drops below a fifth of its set value on the ripple troughs, so the "
                      "reference will wobble", DesignWarning, stacklevel=2)
    p_pass = (input_voltage - output_voltage) * load_current
    if p_pass > 1.0:
        warnings.warn(f"the pass transistor dissipates about {p_pass:.3g} W", DesignWarning, stacklevel=2)
    el = [
        sine_rail(112, 96, 64, 96, ripple_frequency, ripple_amplitude, input_voltage),
        wire(112, 96, 160, 96),
        wire(160, 96, 432, 96),
        # reference
        res(160, 96, 160, 160, rz),
        zener(160, 224, 160, 160, zener_voltage),
        gnd(160, 224, 160, 240),
        wire(160, 160, 224, 160),
        wire(224, 160, 224, 192),
        wire(224, 192, 256, 192),
        # error amplifier
        opamp(256, 208, 320, 208, input_voltage, flags=1, rail_low=0.0),
        wire(320, 208, 352, 208),
        wire(352, 208, 352, 176),
        wire(352, 176, 400, 176),
        # pass transistor
        bjt(400, 176, 432, 176, beta),
        wire(432, 160, 432, 96),
        wire(432, 192, 432, 224),
        # divider
        wire(432, 224, 336, 224),
        res(336, 224, 336, 288, r1),
        res(336, 288, 336, 352, r2),
        gnd(336, 352, 336, 368),
        wire(336, 288, 224, 288),
        wire(224, 288, 224, 224),
        wire(224, 224, 256, 224),
        # output and load
        wire(432, 224, 560, 224),
        res(560, 224, 560, 320, rl),
        gnd(560, 320, 560, 336),
        out_marker(560, 224, 624, 224),
    ]
    step = min(5e-6, 1 / (200 * ripple_frequency))
    return assemble(el, step, [(index_of(el, "R"), 2 * (input_voltage + ripple_amplitude)),
                               (index_of(el, "O"), 2 * output_voltage)])
