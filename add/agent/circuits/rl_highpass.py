"""Generate a Falstad (CircuitJS) passive RL high-pass filter netlist."""

import argparse
import math
import sys
import warnings

from . import resistors_approximation

# Preferred inductor decades tried in order; the first giving R in
# [_R_MIN, _R_MAX] wins. Confined to this file, mirroring rc_phaseshift.py's
# _CAPS - no shared "inductors_approximation" helper exists (or is assumed).
_INDUCTORS = (1e-6, 10e-6, 100e-6, 1e-3, 10e-3, 100e-3, 1.0)  # H
_R_MIN, _R_MAX = 1e3, 100e3

# Everything about the source is fixed rather than exposed as a parameter -
# see rc_lowpass.py's module docstring for the confidence level behind this.
_SOURCE = "sweep"
_SWEEP_FLAGS = 3
_SWEEP_DECADE_SPAN = 10  # sweep range is [cutoff/this, cutoff*this]
_SWEEP_MAX_VOLTAGE = 5.0  # V, peak; matches the reference export
_SWEEP_TIME = 0.1  # s, time for one full sweep; matches the reference export
_SINE_AMPLITUDE = 1e-3  # V, peak; only used if _SOURCE = "sine"

_MAX_TIME_STEP = 5e-6  # s
_SAMPLES_PER_PERIOD = 200
_EXACT_REL_TOL = 1e-9  # cutoffs closer than this count as exact (float noise)

_F_MIN = _R_MIN / (2 * math.pi * _INDUCTORS[-1])
_F_MAX = _R_MAX / (2 * math.pi * _INDUCTORS[0])


class CutoffErrorWarning(UserWarning):
    """The standard R and L values give a cutoff different from the request."""


def _fmt(x: float) -> str:
    """Shortest exact float text (unlike :f or :e, never rounds values away)."""
    return repr(float(x))


def rl_highpass(cutoff_frequency: float) -> str:
    """Generate a Falstad-format passive RL high-pass filter circuit.

    A plain two-component divider: R in series from the source, then L from
    that junction to ground, output taken at the junction (no op amp, no
    buffering):

        Vout/Vin = j*2*pi*f*L / (R + j*2*pi*f*L),  f_c = R / (2*pi*L)

    An inductor shorts low frequencies to ground and blocks high ones (the
    opposite of a capacitor), so this is a high-pass filter even though the
    geometry mirrors rc_highpass.py's - R takes the series position C held
    there, and L takes the shunt position R held there.

    L is a preferred decade value (see _INDUCTORS) chosen so the resulting R
    lands in a practical 1 kOhm-100 kOhm range; R is then the standard value
    nearest that ideal value, via the same resistors_approximation used
    throughout this codebase. Because R is snapped, the actual cutoff
    usually differs slightly from the request; a CutoffErrorWarning reports
    it when it does.

    The source, its amplitude/voltage, and (for the sweep source) its
    frequency range are all fixed internally rather than exposed here -
    see the module-level constants if you need to change them.

    Args:
        cutoff_frequency: Desired -3 dB cutoff frequency in Hz.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If cutoff_frequency is not a finite number > 0, or is
            outside the range the preferred inductor list can cover.

    Warns:
        CutoffErrorWarning: If the achieved cutoff differs from the request.
    """
    if not math.isfinite(cutoff_frequency) or cutoff_frequency <= 0:
        raise ValueError(
            f"cutoff_frequency must be a finite value > 0, got {cutoff_frequency!r}"
        )

    for L in _INDUCTORS:
        R_ideal = 2 * math.pi * cutoff_frequency * L
        if _R_MIN <= R_ideal <= _R_MAX:
            break
    else:
        raise ValueError(
            f"cutoff_frequency {cutoff_frequency:g} Hz is outside the "
            f"supported range ({_F_MIN:.2g} Hz to {_F_MAX:.2g} Hz)"
        )
    R = resistors_approximation.resistors_approximation(R_ideal)
    actual_cutoff = R / (2 * math.pi * L)

    if not math.isclose(actual_cutoff, cutoff_frequency, rel_tol=_EXACT_REL_TOL):
        error = (actual_cutoff - cutoff_frequency) / cutoff_frequency * 100
        warnings.warn(
            f"requested cutoff {cutoff_frequency:g} Hz, achieved "
            f"{actual_cutoff:.4g} Hz (R={R:g} ohm, L={L:g} H): "
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

    # R takes the series position, L takes the shunt-to-ground position -
    # the reverse of rc_highpass.py. Coordinates match its reference export.
    # The inductor's flat-dump trailing field (initial current) is inferred
    # by analogy with the capacitor's single trailing state field - not
    # independently confirmed the way the sweep source's fields were.
    lines = [f"$ 1 {_fmt(time_step)} 10 57 5.0", source_line]
    if _SOURCE == "sweep":
        lines += [
            f"r 240 160 400 160 0 {_fmt(R)}",
            f"l 400 160 400 288 0 {_fmt(L)} 0.0",
            "g 400 288 400 320 0",
            "O 400 160 512 160 0",
        ]
    else:
        lines += [
            "g 96 256 96 304 0",
            "w 96 112 192 112 0",
            f"r 192 112 336 112 0 {_fmt(R)}",
            f"l 336 112 336 208 0 {_fmt(L)} 0.0",
            "g 336 208 336 240 0",
            "O 336 112 432 112 0",
        ]
    output_index = next(i for i, l in enumerate(lines[1:]) if l.startswith("O "))
    r_index = next(i for i, l in enumerate(lines[1:]) if l.startswith("r "))
    l_index = next(i for i, l in enumerate(lines[1:]) if l.startswith("l "))
    lines += [
        f"o 0 64 0 2 {_fmt(scope_scale)} 9.765625E-5",
        f"o {output_index} 64 0 2 {_fmt(scope_scale)} 9.765625E-5",
        # HINT_3DB_L (type 5): the R/L equivalent of rc_highpass.py's
        # HINT_3DB_C (type 3) hint, by name/number match against the same
        # simulator source enum - not independently confirmed by a matching
        # real RL export the way HINT_3DB_C was confirmed twice. Cosmetic
        # only; delete this line if it causes any issue on load.
        f"h 5 {r_index} {l_index}",
    ]
    return "\n".join(lines) + "\n"


def _main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate a CircuitJS passive RL high-pass filter netlist on stdout."
    )
    parser.add_argument("cutoff_frequency", type=float, help="cutoff frequency, Hz (> 0)")
    args = parser.parse_args(argv)

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            netlist = rl_highpass(args.cutoff_frequency)
    except ValueError as exc:
        parser.error(str(exc))
    for w in caught:  # keep stdout clean: netlist only
        print(f"warning: {w.message}", file=sys.stderr)
    print(netlist, end="")


if __name__ == "__main__":
    _main()