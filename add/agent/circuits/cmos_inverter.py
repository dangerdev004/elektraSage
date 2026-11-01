"""Generate a Falstad (CircuitJS) CMOS inverter netlist (P-channel above N-channel)."""

import warnings

from ._parts import (DesignWarning, assemble, cap, dc_rail, gnd, index_of, mosfet, out_marker,
                     require_positive, sine_rail, wire)

DEFAULT_THRESHOLD_V = 1.5       # Falstad's MOSFET default
DEFAULT_BETA = 0.02             # A/V^2, Falstad's default


def cmos_inverter(
    supply_voltage: float = 5.0,
    threshold_voltage: float = DEFAULT_THRESHOLD_V,
    beta: float = DEFAULT_BETA,
    input_amplitude: float = None,
    input_frequency: float = 1000.0,
    input_bias: float = None,
    load_capacitor: float = None,
) -> str:
    """Generate a Falstad-format CMOS inverter: a P-channel MOSFET from Vdd and an N-channel MOSFET to
    ground, gates joined to the input and drains joined to the output.

    Matched devices (same threshold and beta), so the switching threshold sits at Vdd/2. It is a switch, not
    an amplifier: the output is Vdd for an input below about Vdd/2 and 0 V above it, changing over a narrow
    input range around that point. The drive is a sine source swinging around `input_bias` (default Vdd/2) with
    peak `input_amplitude` (default Vdd/2, i.e. rail to rail), so the output is a rail-to-rail square wave.
    Each device's on-resistance is about 1/(beta (Vdd - Vt)) while it conducts.

    Args:
        supply_voltage: Vdd in volts (must exceed twice the threshold for both devices to ever be off).
        threshold_voltage: Vt of both devices in volts (positive number; the P-channel uses its magnitude).
        beta: Transconductance parameter of both devices in A/V^2.
        input_amplitude: Peak amplitude of the input sine in volts (default Vdd/2).
        input_frequency: Frequency of the input in hertz.
        input_bias: DC level the input swings around, in volts (default Vdd/2).
        load_capacitor: Optional capacitor from the output to ground in farads.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If an argument is not a finite number > 0, or Vdd <= 2 Vt.

    Warns:
        DesignWarning: If the input never crosses the switching threshold, or never reaches the logic levels.
    """
    for name, value in (("supply_voltage", supply_voltage), ("threshold_voltage", threshold_voltage),
                        ("beta", beta), ("input_frequency", input_frequency)):
        require_positive(name, value)
    if supply_voltage <= 2 * threshold_voltage:
        raise ValueError(f"supply_voltage {supply_voltage:g} V must exceed twice the threshold "
                         f"({2 * threshold_voltage:g} V), or both devices conduct at once around the switching point")
    amp = supply_voltage / 2 if input_amplitude is None else input_amplitude
    bias = supply_voltage / 2 if input_bias is None else input_bias
    require_positive("input_amplitude", amp)
    if load_capacitor is not None:
        require_positive("load_capacitor", load_capacitor)
    if bias - amp > threshold_voltage or bias + amp < supply_voltage - threshold_voltage:
        warnings.warn("the input never crosses the switching region, so the output will not switch fully "
                      "(it needs to go below Vdd - Vt and above Vt)", DesignWarning, stacklevel=2)
    if bias - amp < -1e-9 or bias + amp > supply_voltage + 1e-9:
        warnings.warn("the input goes outside 0 V to Vdd; the gate is driven beyond the rails",
                      DesignWarning, stacklevel=2)
    el = [
        dc_rail(224, 64, 160, 64, supply_voltage),
        wire(224, 64, 352, 64),
        wire(352, 112, 352, 64),
        mosfet(320, 128, 352, 128, threshold_voltage, beta, pchannel=True, flip=True),
        wire(352, 144, 352, 176),
        wire(352, 176, 352, 208),
        mosfet(320, 224, 352, 224, threshold_voltage, beta),
        wire(352, 240, 352, 272),
        gnd(352, 272, 352, 288),
        wire(320, 128, 288, 128),
        wire(288, 128, 288, 176),
        wire(288, 176, 288, 224),
        wire(288, 224, 320, 224),
        sine_rail(96, 176, 48, 176, input_frequency, amp, bias),
        wire(96, 176, 288, 176),
        wire(352, 176, 448, 176),
        out_marker(448, 176, 512, 176),
    ]
    if load_capacitor is not None:
        el += [cap(448, 176, 448, 240, load_capacitor), gnd(448, 240, 448, 256)]
    step = min(5e-6, 1 / (200 * input_frequency))
    src = next(i for i, x in enumerate(el) if x.startswith("R 96 176"))
    return assemble(el, step, [(src, 2 * max(supply_voltage, bias + amp)), (index_of(el, "O"), 2 * supply_voltage)])
