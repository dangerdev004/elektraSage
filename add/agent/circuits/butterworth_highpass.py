"""Generate a Falstad (CircuitJS) second-order Butterworth high-pass filter netlist."""

import warnings

from . import _active_filters as af


def butterworth_highpass(
    cutoff_frequency: float,
    amp_supply: float = af.DEFAULT_SUPPLY,
) -> str:
    """Generate a Falstad-format second-order (12 dB/octave) Butterworth high-pass filter.

    A Sallen-Key section with equal resistors and equal capacitors whose op-amp gain is
    set for the maximally flat response, Q = 1/sqrt(2) = 0.707, so the -3 dB corner is the
    cutoff frequency. The gain-setting resistors are the standard (E24) pair whose gain
    1 + Rf/Rg lands closest to the ideal 1.586, so the achieved Q is within a fraction of a
    percent; the passband gain is therefore about 1.59, not 1.

    C is a decade value chosen so R lands in 1-100 kOhm, and R is the nearest standard
    value, so the cutoff differs slightly from the request. A FilterAccuracyWarning
    reports the rounding.

    Args:
        cutoff_frequency: Desired -3 dB cutoff frequency in Hz.
        amp_supply: Op-amp output limit in volts, applied as +/- amp_supply.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If an argument is out of range.

    Warns:
        FilterAccuracyWarning: If standard values change the cutoff frequency or Q.
    """
    af.require_positive("amp_supply", amp_supply)
    R, C, f_act = af.pick_rc(cutoff_frequency, "cutoff frequency")
    rg, rf, k = af.best_butterworth_gain()
    q = af.q_of(k)
    if abs(q - 2 ** -0.5) / 2 ** -0.5 > 0.01:
        warnings.warn(f"achieved Q {q:.4g} instead of 0.7071 (Rg={rg:g} ohm, Rf={rf:g} ohm)",
                      af.FilterAccuracyWarning, stacklevel=2)
    return af.sallen_key("high", R, C, f_act, k, rg, rf, amp_supply)
