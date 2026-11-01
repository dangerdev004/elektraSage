"""Generate a Falstad (CircuitJS) first-order all-pass filter netlist."""

from . import _active_filters as af


def allpass_filter(
    center_frequency: float,
    amp_supply: float = af.DEFAULT_SUPPLY,
) -> str:
    """Generate a Falstad-format first-order all-pass filter (one op-amp).

    The gain is 1 at every frequency; only the phase changes, from 0 degrees at low
    frequencies through -90 degrees at the centre frequency f = 1 / (2 pi R C) to -180
    degrees at high frequencies. The signal goes to the + input through R, with C to
    ground, and to the - input through Ra, with an equal feedback resistor Rb = Ra.

    C is a decade value chosen so R lands in 1-100 kOhm, and R is the nearest standard
    (E24) value, so the centre frequency differs slightly from the request. Ra = Rb =
    10 kOhm exactly, so the gain really is 1. A FilterAccuracyWarning reports the
    rounding.

    Args:
        center_frequency: Desired frequency of the -90 degree phase shift in Hz.
        amp_supply: Op-amp output limit in volts, applied as +/- amp_supply.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If an argument is out of range.

    Warns:
        FilterAccuracyWarning: If standard values change the centre frequency.
    """
    af.require_positive("amp_supply", amp_supply)
    R, C, f_act = af.pick_rc(center_frequency, "centre frequency")
    ra = 10e3
    el = [af.sweep_source(f_act),
          af.res(240, 160, 336, 160, R),
          af.cap(336, 160, 336, 288, C),
          "g 336 288 336 320 0",
          "w 336 160 480 160 0",
          af.amp_line(480, 176, 624, amp_supply),
          "w 240 160 240 368 0",
          af.res(240, 368, 384, 368, ra),
          "w 384 368 480 368 0",
          "w 480 368 480 192 0",
          af.res(480, 368, 624, 368, ra),
          "w 624 368 624 176 0",
          "O 624 176 688 176 0"]
    return af.assemble(el, f_act, af.SWEEP_VOLTAGE)
