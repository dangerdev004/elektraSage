"""Generate a Falstad (CircuitJS) passive RC high-pass filter netlist."""

import argparse
import math
import sys
import warnings

from . import resistors_approximation

# Preferred capacitor decades tried in order; the first giving R in
# [_R_MIN, _R_MAX] wins. Same range and reasoning as rc_lowpass.py.
_CAPS = (1e-12, 10e-12, 100e-12, 1e-9, 10e-9, 100e-9, 1e-6, 10e-6)
_R_MIN, _R_MAX = 1e3, 100e3

# Everything about the source is fixed rather than exposed as a parameter -
# see rc_lowpass.py's module docstring for the confidence level behind this
# (the sweep element's dump format is confirmed field-for-field against a
# real export; that it needs only one electrical terminal is inferred, not
# confirmed - change _SOURCE to "sine" if that turns out wrong).
_SOURCE = "sweep"
_SWEEP_FLAGS = 3
_SWEEP_DECADE_SPAN = 10  # sweep range is [cutoff/this, cutoff*this]
_SWEEP_MAX_VOLTAGE = 5.0  # V, peak; matches the reference export
_SWEEP_TIME = 0.1  # s, time for one full sweep; matches the reference export
_SINE_AMPLITUDE = 1e-3  # V, peak; only used if _SOURCE = "sine"

_MAX_TIME_STEP = 5e-6  # s
_SAMPLES_PER_PERIOD = 200
_EXACT_REL_TOL = 1e-9  # cutoffs closer than this count as exact (float noise)

_F_MIN = 1 / (2 * math.pi * _R_MAX * _CAPS[-1])
_F_MAX = 1 / (2 * math.pi * _R_MIN * _CAPS[0])


class CutoffErrorWarning(UserWarning):
    """The standard R and C values give a cutoff different from the request."""


def _fmt(x: float) -> str:
    """Shortest exact float text (unlike :f or :e, never rounds values away)."""
    return repr(float(x))


def rc_highpass(cutoff_frequency: float) -> str:
    """Generate a Falstad-format passive RC high-pass filter circuit.

    A plain two-component divider - the mirror image of rc_lowpass.py's
    circuit, with C and R swapped: C in series from the source, then R from
    that junction to ground, output taken at the junction (no op amp, no
    buffering):

        Vout/Vin = j*2*pi*f*R*C / (1 + j*2*pi*f*R*C),  f_c = 1 / (2*pi*R*C)

    This attenuates low frequencies and passes high ones, the opposite of
    rc_lowpass.py's response, using the same cutoff formula.

    C is a preferred decade value chosen so the resulting R lands in a
    practical 1 kOhm-100 kOhm range; R is then the standard value nearest
    that ideal value. Because R is snapped, the actual cutoff usually
    differs slightly from the request; a CutoffErrorWarning reports it
    when it does.

    The source, its amplitude/voltage, and (for the sweep source) its
    frequency range are all fixed internally rather than exposed here -
    see the module-level constants if you need to change them.

    Args:
        cutoff_frequency: Desired -3 dB cutoff frequency in Hz.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If cutoff_frequency is not a finite number > 0, or is
            outside the range the preferred capacitor list can cover.

    Warns:
        CutoffErrorWarning: If the achieved cutoff differs from the request.
    """
    if not math.isfinite(cutoff_frequency) or cutoff_frequency <= 0:
        raise ValueError(
            f"cutoff_frequency must be a finite value > 0, got {cutoff_frequency!r}"
        )

    for C in _CAPS:
        R_ideal = 1 / (2 * math.pi * cutoff_frequency * C)
        if _R_MIN <= R_ideal <= _R_MAX:
            break
    else:
        raise ValueError(
            f"cutoff_frequency {cutoff_frequency:g} Hz is outside the "
            f"supported range ({_F_MIN:.2g} Hz to {_F_MAX:.2g} Hz)"
        )
    R = resistors_approximation.resistors_approximation(R_ideal)
    actual_cutoff = 1 / (2 * math.pi * R * C)

    if not math.isclose(actual_cutoff, cutoff_frequency, rel_tol=_EXACT_REL_TOL):
        error = (actual_cutoff - cutoff_frequency) / cutoff_frequency * 100
        warnings.warn(
            f"requested cutoff {cutoff_frequency:g} Hz, achieved "
            f"{actual_cutoff:.4g} Hz (R={R:g} ohm, C={C:g} F): "
            f"error {error:+.2f}%",
            CutoffErrorWarning,
            stacklevel=2,
        )

    if _SOURCE == "sweep":
        sweep_min = actual_cutoff / _SWEEP_DECADE_SPAN
        sweep_max = actual_cutoff * _SWEEP_DECADE_SPAN
        source_line = (
            f"170 240 160 208 160 {_SWEEP_FLAGS} {_fmt(sweep_min)} "
            f"{_fmt(sweep_max)} {_fmt(_SWEEP_MAX_VOLTAGE)} {_fmt(_SWEEP_TIME)}"
        )
        scope_scale = _SWEEP_MAX_VOLTAGE
        highest_freq = sweep_max
    else:
        source_line = (
            f"v 96 256 96 112 0 1 {_fmt(cutoff_frequency)} {_fmt(_SINE_AMPLITUDE)} 0.0"
        )
        scope_scale = _SINE_AMPLITUDE
        highest_freq = cutoff_frequency

    time_step = min(
        _MAX_TIME_STEP,
        1 / (max(highest_freq, actual_cutoff) * _SAMPLES_PER_PERIOD),
    )

    # C and R swap positions relative to rc_lowpass.py: C is now in series
    # (source to junction), R is now the shunt to ground. Coordinates match
    # the reference export exactly.
    lines = [f"$ 1 {_fmt(time_step)} 10 57 5.0", source_line]
    if _SOURCE == "sweep":
        lines += [
            f"c 240 160 400 160 0 {_fmt(C)} 0.0",
            f"r 400 160 400 288 0 {_fmt(R)}",
            "g 400 288 400 320 0",
            "O 400 160 512 160 0",
        ]
    else:
        lines += [
            "g 96 256 96 304 0",
            "w 96 112 192 112 0",
            f"c 192 112 336 112 0 {_fmt(C)} 0.0",
            f"r 336 112 336 208 0 {_fmt(R)}",
            "g 336 208 336 240 0",
            "O 336 112 432 112 0",
        ]
    output_index = next(i for i, l in enumerate(lines[1:]) if l.startswith("O "))
    r_index = next(i for i, l in enumerate(lines[1:]) if l.startswith("r "))
    c_index = next(i for i, l in enumerate(lines[1:]) if l.startswith("c "))
    lines += [
        f"o 0 64 0 2 {_fmt(scope_scale)} 9.765625E-5",
        f"o {output_index} 64 0 2 {_fmt(scope_scale)} 9.765625E-5",
        # HINT_3DB_C: tells the simulator to display this R/C pair's -3 dB
        # frequency on the schematic. Format confirmed from two matching
        # reference exports (same "h 3 <r> <c>" pattern in both); purely a
        # display hint, so removing this line changes nothing electrically.
        f"h 3 {r_index} {c_index}",
    ]
    return "\n".join(lines) + "\n"


def _main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate a CircuitJS passive RC high-pass filter netlist on stdout."
    )
    parser.add_argument("cutoff_frequency", type=float, help="cutoff frequency, Hz (> 0)")
    args = parser.parse_args(argv)

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            netlist = rc_highpass(args.cutoff_frequency)
    except ValueError as exc:
        parser.error(str(exc))
    for w in caught:  # keep stdout clean: netlist only
        print(f"warning: {w.message}", file=sys.stderr)
    print(netlist, end="")


if __name__ == "__main__":
    _main()