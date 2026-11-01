"""Generate a Falstad (CircuitJS) second-order Sallen-Key high-pass filter netlist."""

import math

from . import _active_filters as af


def sallen_key_highpass(
    cutoff_frequency: float,
    gain: float = 1.0,
    response=None,
    amp_supply: float = af.DEFAULT_SUPPLY,
) -> str:
    """Generate a Falstad-format second-order Sallen-Key high-pass filter (one op-amp).

    The mirror image of sallen_key_lowpass: equal capacitors C and equal resistors R,
    natural frequency f0 = 1 / (2 pi R C), quality factor Q = 1 / (3 - K) set by the
    op-amp's non-inverting gain K. A gain of 1 gives Q = 0.5, K = 1.586 gives the maximally
    flat (Butterworth) response, and K close to 3 peaks sharply and would oscillate. The
    -3 dB corner equals f0 only when Q = 0.707.

    C is a decade value chosen so R lands in 1-100 kOhm, and R is the nearest standard
    (E24) value. The gain-setting resistors are standard values too. A
    FilterAccuracyWarning reports every rounding that matters.

    Args:
        cutoff_frequency: Desired natural frequency f0 in Hz.
        gain: Non-inverting gain K of the op-amp, 1 <= K <= 2.9. Default 1 (follower).
        response: Optional shape instead of gain: 'butterworth' (Q 0.707, maximally flat),
            'bessel' (Q 0.577, best step response) or a number Q (0.5 to about 10). Overrides gain.
        amp_supply: Op-amp output limit in volts, applied as +/- amp_supply.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If an argument is out of range.

    Warns:
        FilterAccuracyWarning: If standard values change the frequency or the gain.
    """
    af.require_positive("amp_supply", amp_supply)
    gain = af.gain_for_response(response, gain)
    if not math.isfinite(gain) or not 1 <= gain <= af.MAX_GAIN:
        raise ValueError(f"gain must be between 1 and {af.MAX_GAIN:g} (a Sallen-Key filter "
                         f"oscillates at 3), got {gain!r}")
    R, C, f_act = af.pick_rc(cutoff_frequency, "cutoff frequency")
    rg, rf, k = af.gain_resistors(gain)
    af.warn_gain(gain, k)
    return af.sallen_key("high", R, C, f_act, k, rg, rf, amp_supply)
