"""Generate a Falstad (CircuitJS) N-MOSFET common-source amplifier netlist."""

import math
import warnings

from ._parts import (DesignWarning, assemble, cap, dc_rail, gnd, index_of, mosfet, out_marker,
                     require_positive, res, sine_rail, wire)

# Falstad's default MOSFET: square law, no channel-length modulation.
VT_V = 1.5
BETA = 0.02
DEFAULT_LOAD_OHMS = 50000.0
DEFAULT_INPUT_AMPLITUDE = 0.05
DEFAULT_INPUT_FREQUENCY = 40.0
DEFAULT_BYPASS_F = 100e-6
DEFAULT_OUTPUT_F = 1e-6


def common_source_amp(
    positive_supply: float,
    negative_supply: float,
    drain_current: float,
    gain: float,
    load_resistor: float = DEFAULT_LOAD_OHMS,
    input_amplitude: float = DEFAULT_INPUT_AMPLITUDE,
    input_frequency: float = DEFAULT_INPUT_FREQUENCY,
    source_bypass_capacitor: float = DEFAULT_BYPASS_F,
    output_capacitor: float = DEFAULT_OUTPUT_F,
) -> str:
    """Generate a Falstad-format N-MOSFET common-source amplifier (dual supply).

    The gate is wired straight to the signal source (DC level 0 V), so the source sits
    below ground at -Vgs with Rs running to the negative supply, and Rs is bypassed by a
    capacitor. The output is taken from the drain through a coupling capacitor into the
    load, and it is inverted. With the Falstad default MOSFET (Vt = 1.5 V, beta = 0.02,
    no channel-length modulation):
        Vov = sqrt(2*Id/beta), gm = beta*Vov, Vgs = Vt + Vov, Rs = (Vss - Vgs)/Id
        |gain| = gm * (Rd || RL)   so   Rd = 1 / (gm/gain - 1/RL)
    The drain must stay in saturation: VD - VS >= Vov.

    Args:
        positive_supply: Positive supply Vdd in volts.
        negative_supply: Magnitude of the negative supply in volts (10 means -10 V).
        drain_current: Quiescent drain current in amps (0.002 = 2 mA).
        gain: Voltage gain magnitude wanted (the output is inverted).
        load_resistor: Load resistor at the output in ohms.
        input_amplitude: Peak amplitude of the input source in volts.
        input_frequency: Frequency of the input source in hertz.
        source_bypass_capacitor: Capacitor across the source resistor in farads.
        output_capacitor: Output coupling capacitor in farads.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If any argument is not a finite number > 0, if Vgs is not below the negative
            supply, if the gain is out of reach for this current and load, or if the drain
            would leave saturation.

    Warns:
        DesignWarning: If the output swing exceeds the headroom, the signal is large next to the
            overdrive voltage (distortion), or a capacitor is too small for the frequency.
    """
    for name, value in (("positive_supply", positive_supply), ("negative_supply", negative_supply),
                        ("drain_current", drain_current), ("gain", abs(gain)), ("load_resistor", load_resistor),
                        ("input_amplitude", input_amplitude), ("input_frequency", input_frequency),
                        ("source_bypass_capacitor", source_bypass_capacitor),
                        ("output_capacitor", output_capacitor)):
        require_positive(name, value)
    gain = abs(gain)

    vov = math.sqrt(2 * drain_current / BETA)
    gm = BETA * vov
    vgs = VT_V + vov
    vs = -vgs
    if vgs >= negative_supply:
        raise ValueError(f"Vgs needed for {drain_current:g} A is {vgs:.4g} V, which is not below the negative supply "
                         f"({negative_supply:g} V) - lower the current or raise the negative supply")
    rs = (negative_supply - vgs) / drain_current
    r_par = gain / gm
    if r_par >= load_resistor:
        raise ValueError(f"gain {gain:g} is out of reach: at {drain_current:g} A, gm = {gm:.4g} S and even an infinite "
                         f"Rd gives at most {gm * load_resistor:.4g}. Raise the current or lower the gain")
    rd = 1 / (1 / r_par - 1 / load_resistor)
    vd = positive_supply - drain_current * rd
    vds = vd - vs
    if vds < vov:
        raise ValueError(f"VDS would be {vds:.4g} V, below the overdrive {vov:.4g} V: the MOSFET leaves saturation. "
                         f"Lower the current or the gain, or raise the positive supply")

    w = 2 * math.pi * input_frequency
    out_peak = gain * input_amplitude
    headroom = min(positive_supply - vd, vd - (vs + vov))
    if out_peak > headroom:
        warnings.warn(f"estimated output swing {out_peak:.3g} V peak exceeds the headroom {headroom:.3g} V around the "
                      f"drain - the output will likely clip", DesignWarning, stacklevel=2)
    if input_amplitude / (4 * vov) > 0.05:
        warnings.warn(f"input {input_amplitude:g} V is large next to the overdrive {vov:.3g} V: about "
                      f"{input_amplitude / (4 * vov) * 100:.1f}% second-harmonic distortion", DesignWarning, stacklevel=2)
    zs = 1 / (1 / rs + 1j * w * source_bypass_capacitor)
    gain_cs = gm * (rd * load_resistor / (rd + load_resistor)) / abs(1 + gm * zs)
    if gain_cs < 0.9 * gain:
        warnings.warn(f"source bypass capacitor is too small at {input_frequency:g} Hz: the gain falls from {gain:g} "
                      f"to about {gain_cs:.3g}", DesignWarning, stacklevel=2)
    fc_out = 1 / (2 * math.pi * (rd + load_resistor) * output_capacitor)
    if 1 / math.sqrt(1 + (fc_out / input_frequency) ** 2) < 0.9:
        warnings.warn(f"output capacitor corner {fc_out:.3g} Hz is close to the {input_frequency:g} Hz signal - the "
                      f"output will be attenuated", DesignWarning, stacklevel=2)

    el = [
        res(208, 176, 208, 272, rs),
        sine_rail(160, 160, 112, 160, input_frequency, input_amplitude),
        dc_rail(208, 32, 160, 32, positive_supply),
        res(208, 32, 208, 144, rd),
        cap(208, 144, 320, 144, output_capacitor, vd),
        res(320, 144, 320, 272, load_resistor),
        gnd(320, 272, 320, 304),
        out_marker(320, 144, 384, 144),
        wire(208, 176, 256, 176),
        cap(256, 176, 256, 272, source_bypass_capacitor, negative_supply + vs),
        wire(208, 272, 256, 272),
        mosfet(160, 160, 208, 160, VT_V, BETA),
        dc_rail(208, 272, 208, 304, -negative_supply),
    ]
    step = min(5e-6, 1 / (200 * input_frequency))
    return assemble(el, step, [(1, 2 * input_amplitude), (index_of(el, "O"), 2 * max(out_peak, input_amplitude))])
