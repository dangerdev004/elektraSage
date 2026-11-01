"""Generate a Falstad (CircuitJS) complementary push-pull (class-B / class-AB) emitter-follower stage."""

import math
import warnings

from ._parts import (DesignWarning, assemble, bjt, cap, dc_rail, gnd, index_of, out_marker,
                     require_positive, res, sine_rail, wire)

VBE_V = 0.65
DEFAULT_INPUT_AMPLITUDE = 1.0
DEFAULT_INPUT_FREQUENCY = 1000.0


def class_b_amp(
    supply_voltage: float = 12.0,
    load_resistor: float = 100.0,
    bias_current: float = None,
    emitter_resistor: float = 1.0,
    beta: float = 100.0,
    input_amplitude: float = DEFAULT_INPUT_AMPLITUDE,
    input_frequency: float = DEFAULT_INPUT_FREQUENCY,
    input_capacitor: float = 1e-5,
) -> str:
    """Generate a Falstad-format complementary push-pull output stage (a class-B / class-AB buffer).

    An NPN emitter follower (collector on +Vs) and a PNP emitter follower (collector on -Vs) share one
    output node, each with a small emitter resistor, driving the load to ground from a split +/-Vs supply.
    The voltage gain is just under 1; the stage supplies current, not voltage gain. The NPN conducts on
    positive half-cycles and the PNP on negative ones.
    With bias_current > 0 the bases are held about two diode drops apart by a diode-connected NPN and PNP
    in series (fed from the rails through two resistors), so both output devices idle at roughly that
    current and the crossover gap is closed (class AB). With bias_current = 0 there is no bias at all
    (pure class B): neither transistor conducts for inputs within about 0.6 V of zero, so the output has a
    dead zone and strong crossover distortion. When bias_current is omitted it is set to 3x the peak base
    current the load needs at full swing, with a 1 mA minimum.

    Args:
        supply_voltage: Rail magnitude Vs in volts; the supplies are +Vs and -Vs.
        load_resistor: Load to ground in ohms.
        bias_current: Current through the bias string in amps; 0 for pure class B. Default: automatic.
        emitter_resistor: Resistor in each emitter in ohms (steadies the idle current).
        beta: Transistor current gain (hFE).
        input_amplitude: Peak amplitude of the input source in volts.
        input_frequency: Frequency of the input source in hertz.
        input_capacitor: Input coupling capacitor in farads.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If any argument is not a finite number > 0 (bias_current may be 0), or the bias string
            does not fit the supply.

    Warns:
        DesignWarning: If the input would clip against the rails, the bias current is too small to drive the
            load at full swing, or the stage is pure class B.
    """
    for name, value in (("supply_voltage", supply_voltage), ("load_resistor", load_resistor),
                        ("emitter_resistor", emitter_resistor), ("beta", beta),
                        ("input_amplitude", input_amplitude), ("input_frequency", input_frequency),
                        ("input_capacitor", input_capacitor)):
        require_positive(name, value)
    if bias_current is not None and (not math.isfinite(bias_current) or bias_current < 0):
        raise ValueError(f"bias_current must be 0 or a finite number > 0, got {bias_current!r}")
    if supply_voltage <= 2 * VBE_V + 0.5:
        raise ValueError(f"supply_voltage {supply_voltage:g} V is too small for a push-pull stage (needs > 1.8 V)")

    vpk_free = supply_voltage - 0.2 - VBE_V
    ib_pk = min(input_amplitude, vpk_free) / load_resistor / beta
    if bias_current is None:
        bias_current = max(3 * ib_pk, 1e-3)
    # the bias resistor also has to feed the base at the peaks, which costs Rb * Ib of the top rail's headroom
    rb_est = (supply_voltage - VBE_V) / bias_current if bias_current > 0 else 0.0
    vpk_max = vpk_free / (1 + rb_est / (load_resistor * beta))
    if bias_current > 0 and 2 * (supply_voltage - 2 * VBE_V) / bias_current < 100:
        raise ValueError("bias_current is too large for this supply: the bias resistors would be under 100 ohm")
    if input_amplitude > vpk_max:
        warnings.warn(f"input amplitude {input_amplitude:g} V is above what the +/-{supply_voltage:g} V rails can "
                      f"deliver (about {vpk_max:.3g} V peak) - the output will clip", DesignWarning, stacklevel=2)
    if bias_current == 0:
        warnings.warn("bias_current is 0: this is pure class B, so the output has a dead zone of about 0.6 V "
                      "either side of zero (crossover distortion)", DesignWarning, stacklevel=2)
    elif bias_current < 2 * ib_pk:
        warnings.warn(f"the bias current ({bias_current:.3g} A) is below twice the peak base current the load "
                      f"needs ({ib_pk:.3g} A): the bias string will sag and distort on peaks",
                      DesignWarning, stacklevel=2)

    xc = 1 / (2 * math.pi * input_frequency * input_capacitor)
    r_in = 1e5
    if xc > r_in / 10:
        warnings.warn(f"input capacitor reactance {xc:.3g} ohm at {input_frequency:g} Hz is not small next to the "
                      f"{r_in:.3g} ohm bias resistance - the signal will be attenuated", DesignWarning, stacklevel=2)

    el = [
        dc_rail(224, 64, 160, 64, supply_voltage),
        wire(224, 64, 352, 64),
        dc_rail(224, 304, 160, 304, -supply_voltage),
        wire(224, 304, 352, 304),
        # output pair
        bjt(320, 128, 352, 128, beta),
        wire(352, 112, 352, 64),
        res(352, 144, 352, 192, emitter_resistor),
        bjt(320, 256, 352, 256, beta, pnp=True),
        res(352, 192, 352, 240, emitter_resistor),
        wire(352, 272, 352, 304),
        # input
        sine_rail(112, 192, 64, 192, input_frequency, input_amplitude),
        cap(112, 192, 160, 192, input_capacitor, 0.0),
        res(160, 192, 160, 256, r_in),
        gnd(160, 256, 160, 272),
        # load and output
        wire(352, 192, 448, 192),
        res(448, 192, 448, 288, load_resistor),
        gnd(448, 288, 448, 320),
        out_marker(448, 192, 512, 192),
    ]
    if bias_current > 0:
        rb = (supply_voltage - VBE_V) / bias_current
        el += [
            res(224, 64, 224, 144, rb),
            bjt(192, 160, 224, 160, beta),
            wire(192, 160, 192, 144),
            wire(192, 144, 224, 144),
            wire(224, 176, 224, 192),
            bjt(192, 208, 224, 208, beta, pnp=True),
            wire(192, 208, 192, 224),
            wire(192, 224, 224, 224),
            res(224, 224, 224, 304, rb),
            wire(160, 192, 224, 192),
            wire(224, 144, 288, 144),
            wire(288, 144, 288, 128),
            wire(288, 128, 320, 128),
            wire(224, 224, 288, 224),
            wire(288, 224, 288, 256),
            wire(288, 256, 320, 256),
        ]
    else:
        el += [
            wire(160, 192, 288, 192),
            wire(288, 128, 288, 192),
            wire(288, 192, 288, 256),
            wire(288, 128, 320, 128),
            wire(288, 256, 320, 256),
        ]
    step = min(5e-6, 1 / (200 * input_frequency))
    src = next(i for i, x in enumerate(el) if x.startswith("R 112 192"))
    return assemble(el, step, [(src, 2 * input_amplitude), (index_of(el, "O"), 2 * input_amplitude)])
