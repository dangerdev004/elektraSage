"""Generate a Falstad (CircuitJS) op-amp differential amplifier netlist."""

import math
import warnings

from . import _active_filters as af
from .resistors_approximation import resistors_approximation as snap_resistor

R_TARGET_OHMS = 10e3          # input resistors R1 = R2
_CENTRE_HZ = 1000.0           # the sweep covers a decade either side of this
_REFERENCE_HZ = 1000.0        # frequency of the optional second input


def differential_amplifier(
    gain_v_per_v: float,
    reference_amplitude: float = 0.0,
    amp_supply: float = af.DEFAULT_SUPPLY,
) -> str:
    """Generate a Falstad-format differential amplifier (one op-amp, four resistors).

    The output is Vout = gain * (V+ - V-). V+ is the signal input, driven by a 1 V peak AC
    sweep, through R2 into the op-amp's + input with R3 to ground. V- goes through R1 into the
    - input with the feedback resistor Rf from the output. Matched pairs R1 = R2 = 10 kOhm and
    R3 = Rf (the standard value nearest gain * R1) give a gain of Rf / R1 and, ideally, perfect
    rejection of any signal common to both inputs.

    By default V- is tied to ground (reference_amplitude = 0), so the circuit behaves as a
    non-inverting amplifier with the stated gain and, in a cascade, takes its signal from the
    previous stage. Give reference_amplitude > 0 to drive V- with its own 1 kHz sine of that
    peak voltage, to see the subtraction.

    R and Rf are standard (E24) values, so the achieved gain usually differs slightly from the
    request; a FilterAccuracyWarning reports it.

    Args:
        gain_v_per_v: Desired differential gain Rf / R1 (> 0).
        reference_amplitude: Peak volts of the optional second (V-) input source; 0 grounds V-.
        amp_supply: Op-amp output limit in volts, applied as +/- amp_supply.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If gain_v_per_v or amp_supply is not a finite number > 0, or if
            reference_amplitude is negative or not finite.

    Warns:
        FilterAccuracyWarning: If the achieved gain differs from the request.
    """
    af.require_positive("gain_v_per_v", gain_v_per_v)
    af.require_positive("amp_supply", amp_supply)
    if not math.isfinite(reference_amplitude) or reference_amplitude < 0:
        raise ValueError(f"reference_amplitude must be a finite value >= 0, got {reference_amplitude!r}")

    r1 = snap_resistor(R_TARGET_OHMS)
    rf = snap_resistor(gain_v_per_v * r1)
    gain = rf / r1
    if not math.isclose(gain, gain_v_per_v, rel_tol=1e-9):
        warnings.warn(f"requested gain {gain_v_per_v:g}, achieved {gain:.4g} (R1=R2={r1:g} ohm, "
                      f"R3=Rf={rf:g} ohm): error {(gain - gain_v_per_v) / gain_v_per_v * 100:+.2f}%",
                      af.FilterAccuracyWarning, stacklevel=2)

    el = [af.sweep_source(_CENTRE_HZ),
          af.res(240, 160, 336, 160, r1),             # R2 into the + input
          af.res(336, 160, 336, 288, rf),             # R3 to ground
          "g 336 288 336 320 0",
          "w 336 160 480 160 0",
          af.amp_line(480, 176, 624, amp_supply),
          "w 480 192 480 336 0",
          af.res(480, 336, 624, 336, rf),             # Rf
          "w 624 336 624 176 0"]
    if reference_amplitude > 0:
        el += ["v 176 400 176 336 0 1 " + af.fmt(_REFERENCE_HZ) + " " + af.fmt(reference_amplitude) + " 0.0",
               "g 176 400 176 432 0",
               af.res(176, 336, 480, 336, r1)]         # R1 from V- to the - input
    else:
        el += [af.res(272, 336, 480, 336, r1), "g 272 336 272 368 0"]
    el.append("O 624 176 688 176 0")
    return af.assemble(el, _CENTRE_HZ, af.SWEEP_VOLTAGE * max(1.0, gain))
