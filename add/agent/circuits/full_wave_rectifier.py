"""Generate a Falstad (CircuitJS) bridge rectifier with a smoothing capacitor and a load."""

import warnings

from ._parts import DesignWarning, assemble, cap, diode, gnd, index_of, out_marker, require_positive, res, wire

DIODE_DROP_V = 0.7          # typical drop of Falstad's default diode at a few hundred mA


def full_wave_rectifier(
    peak_voltage: float = 10.0,
    frequency: float = 50.0,
    load_resistor: float = 100.0,
    capacitor: float = None,
    ripple_fraction: float = 0.1,
) -> str:
    """Generate a Falstad-format full-wave bridge rectifier with a smoothing capacitor across the load.

    A floating AC source feeds a four-diode bridge; the positive output node carries a capacitor and the load
    resistor to ground. The output is the rectified, smoothed voltage: about Vpk - 2 Vd with a sawtooth ripple
    at twice the line frequency, ripple about I / (2 f C). When `capacitor` is omitted it is sized for the
    requested ripple: C = 1 / (2 f R ripple_fraction). It makes its own signal and has no input, so it can only
    be the FIRST stage of a cascade.

    Args:
        peak_voltage: Peak of the AC source in volts.
        frequency: Line frequency in hertz.
        load_resistor: Load resistance in ohms.
        capacitor: Smoothing capacitor in farads. Chosen for `ripple_fraction` if omitted.
        ripple_fraction: Target peak-to-peak ripple as a fraction of the output (used when no capacitor is given).

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If an argument is not a finite number > 0, ripple_fraction is not below 1, or the source peak
            is under 1.4 V (the bridge would not conduct).

    Warns:
        DesignWarning: If the capacitor leaves more than 50% ripple.
    """
    for name, value in (("peak_voltage", peak_voltage), ("frequency", frequency),
                        ("load_resistor", load_resistor), ("ripple_fraction", ripple_fraction)):
        require_positive(name, value)
    if ripple_fraction >= 1:
        raise ValueError(f"ripple_fraction must be below 1, got {ripple_fraction}")
    if peak_voltage <= 2 * DIODE_DROP_V:
        raise ValueError(f"peak_voltage {peak_voltage:g} V is not above the two diode drops (about "
                         f"{2 * DIODE_DROP_V:g} V), so the bridge would not conduct")
    if capacitor is None:
        capacitor = 1.0 / (2 * frequency * load_resistor * ripple_fraction)
    else:
        require_positive("capacitor", capacitor)
        ripple = 1.0 / (2 * frequency * load_resistor * capacitor)
        if ripple > 0.5:
            warnings.warn(f"this capacitor leaves about {ripple:.0%} ripple (the estimate I/(2fC) is rough above "
                          "20%)", DesignWarning, stacklevel=2)
    el = [
        f"v 192 160 272 160 0 1 {frequency!r} {peak_voltage!r} 0.0 0.0 0.5",
        diode(192, 160, 192, 96),
        diode(192, 224, 192, 160),
        diode(272, 160, 272, 96),
        diode(272, 224, 272, 160),
        wire(192, 96, 272, 96),
        wire(192, 224, 272, 224),
        gnd(272, 224, 272, 240),
        wire(272, 96, 352, 96),
        cap(352, 96, 352, 224, capacitor),
        wire(352, 224, 416, 224),
        wire(272, 224, 352, 224),
        wire(352, 96, 416, 96),
        res(416, 96, 416, 224, load_resistor),
        out_marker(352, 96, 352, 48),
    ]
    step = min(5e-6, 1 / (800 * frequency))
    return assemble(el, step, [(index_of(el, "v"), 2 * peak_voltage), (index_of(el, "O"), 2 * peak_voltage)])
