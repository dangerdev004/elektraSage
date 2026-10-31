"""Generate a Falstad (CircuitJS) inverting op-amp integrator netlist."""

import argparse
import math
import sys
import warnings
from typing import Literal

from . import resistors_approximation
from . import capacitors_approximation

# Waveform codes for the "v" (voltage source) element's flat-dump format -
# duplicated from differentiator.py rather than shared, matching this
# project's self-contained-files convention. "triangle" (3) is confirmed
# from a real export, "sine" (1) is a strong inference, "square" (2) is an
# unconfirmed guess - see differentiator.py's comment for details.
_WAVEFORMS = {"sine": 1, "square": 2, "triangle": 3}

# Fixed test-signal values, matching differentiator.py's style: one source.
# gain_v_per_v is defined AT this frequency (see integrator()'s docstring),
# so it isn't just a test detail - it's part of what the gain number means.
SOURCE_PEAK_V = 5.0
SOURCE_FREQ_HZ = 40.0
RAIL_V = 15.0  # op-amp max/min output, matching the exported reference

# Exact peak/(gain*A) ratio, by waveform. Unlike differentiator.py's square
# case, all three are exact here, because integration suppresses harmonics
# rather than amplifying them (verified numerically, and for triangle also
# analytically via its Fourier series and the Dirichlet beta value pi^3/32).
_SHAPE_CONSTANTS = {"sine": 1.0, "square": math.pi / 2, "triangle": math.pi / 4}

_MAX_TIME_STEP = 5e-6  # s
_SAMPLES_PER_PERIOD = 200
_EXACT_REL_TOL = 1e-9  # gains closer than this count as exact (float noise)


class GainErrorWarning(UserWarning):
    """The standard R and C values give a gain (at SOURCE_FREQ_HZ) different from the request."""


class ClippingRiskWarning(UserWarning):
    """The estimated output peak, for the fixed test signal, exceeds the op-amp rails."""


def _fmt(x: float) -> str:
    """Shortest exact float text (unlike :f or :e, never rounds values away)."""
    return repr(float(x))


def _estimate_peak_output(gain: float, waveform: str) -> float:
    """Exact output peak for the fixed test tone, given the achieved gain
    (at SOURCE_FREQ_HZ): peak = gain * SOURCE_PEAK_V * _SHAPE_CONSTANTS[waveform].

    For a sine input this is exact by definition of a frequency response
    (sine in -> sine out, scaled by the gain at that frequency). Square and
    triangle are also exact here (unlike differentiator.py's square case),
    because integration suppresses higher harmonics rather than amplifying
    them, so their shape constants are clean closed forms too.
    """
    return gain * SOURCE_PEAK_V * _SHAPE_CONSTANTS[waveform]


def integrator(
    gain_v_per_v: float,
    input_resistor_ohms: float,
    waveform: Literal["sine", "square", "triangle"] = "square",
) -> str:
    """Generate a Falstad-format inverting op-amp integrator circuit.

    Topology: Vin -> R -> inverting input; C feedback from output to the
    inverting input; non-inverting input grounded - the mirror of
    differentiator.py's R/C roles, reusing the same proven geometry. Ideal
    gain magnitude is 1/(2*pi*f*R*C) - for an integrator this genuinely
    depends on frequency (decreasing with f, the opposite of a
    differentiator), so `gain_v_per_v` is defined specifically as the gain
    at the fixed test frequency SOURCE_FREQ_HZ:
    gain_v_per_v = 1/(2*pi*SOURCE_FREQ_HZ*R*C). In the time domain,
    Vout(t) = -(1/(R*C)) * integral of Vin dt.

    R is the standard value nearest `input_resistor_ohms`. C is then solved
    from gain_v_per_v and snapped R, then itself snapped to a standard
    value - mirroring differentiator.py's Rf/C snapping. Because both are
    snapped, the actual gain (at SOURCE_FREQ_HZ) usually differs slightly
    from the request; a GainErrorWarning reports it when it does.

    The test signal (waveform aside) is fixed rather than exposed here: peak
    voltage SOURCE_PEAK_V and frequency SOURCE_FREQ_HZ. If the estimated
    output peak for that fixed tone would exceed the op-amp's rails, a
    ClippingRiskWarning reports it (this never blocks generation).

    Args:
        gain_v_per_v: Desired gain magnitude (V/V) at SOURCE_FREQ_HZ.
        input_resistor_ohms: Target input resistor R in ohms.
        waveform: Test-signal shape - "sine", "square" (default, matching
            the exported reference), or "triangle". See module comment for
            confidence level on the "square" code.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If gain_v_per_v or input_resistor_ohms is not a finite
            number > 0, or if waveform is not a supported choice.

    Warns:
        GainErrorWarning: If the achieved gain (at SOURCE_FREQ_HZ) differs
            from the request.
        ClippingRiskWarning: If the estimated output peak for the fixed test
            tone exceeds +/-RAIL_V.
    """
    if waveform not in _WAVEFORMS:
        raise ValueError(
            f"waveform must be one of {sorted(_WAVEFORMS)}, got {waveform!r}"
        )
    for name, value in (
        ("gain_v_per_v", gain_v_per_v),
        ("input_resistor_ohms", input_resistor_ohms),
    ):
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a finite value > 0, got {value!r}")

    R = resistors_approximation.resistors_approximation(input_resistor_ohms)
    ideal_C = 1 / (2 * math.pi * SOURCE_FREQ_HZ * gain_v_per_v * R)
    C = capacitors_approximation.capacitors_approximation(ideal_C)
    actual_gain = 1 / (2 * math.pi * SOURCE_FREQ_HZ * R * C)

    if not math.isclose(actual_gain, gain_v_per_v, rel_tol=_EXACT_REL_TOL):
        error = (actual_gain - gain_v_per_v) / gain_v_per_v * 100
        warnings.warn(
            f"requested gain {gain_v_per_v:g} V/V at {SOURCE_FREQ_HZ:g} Hz, achieved "
            f"{actual_gain:.4g} V/V (R={R:g} ohm, C={C:g} F): error {error:+.2f}%",
            GainErrorWarning,
            stacklevel=2,
        )

    peak_out = _estimate_peak_output(actual_gain, waveform)
    if peak_out > RAIL_V:
        warnings.warn(
            f"estimated output peak {peak_out:.3g} V exceeds the +/-{RAIL_V:g} V "
            f"op-amp rails for the fixed {SOURCE_FREQ_HZ:g} Hz/{SOURCE_PEAK_V:g} V "
            "test tone, so the output will probably clip",
            ClippingRiskWarning,
            stacklevel=2,
        )

    time_step = min(_MAX_TIME_STEP, 1 / (SOURCE_FREQ_HZ * _SAMPLES_PER_PERIOD))

    # Geometry matches differentiator.py's proven layout exactly, with R and
    # C swapped: R is now the input element, C the feedback element (the
    # only topological change between an integrator and a differentiator).
    lines = [
        f"$ 1 {_fmt(time_step)} 10 57 5.0",
        f"v 96 256 96 112 0 {_WAVEFORMS[waveform]} {_fmt(SOURCE_FREQ_HZ)} {_fmt(SOURCE_PEAK_V)} 0.0",
        "g 96 256 96 304 0",
        f"r 96 112 192 112 0 {_fmt(R)}",
        f"c 192 144 336 144 0 {_fmt(C)} 0.0",
        "w 336 144 336 192 0",
        "w 192 112 192 144 0",
        "w 192 144 192 176 0",
        "w 96 256 192 256 0",
        "w 192 208 192 256 0",
        "a 192 192 336 192 0 15.0 -15.0 1000000.0",
        "O 336 192 400 192 0",
        f"o 0 64 0 2 {_fmt(SOURCE_PEAK_V)} 9.765625E-5",
        f"o 10 64 0 2 {_fmt(SOURCE_PEAK_V)} 9.765625E-5",
    ]
    return "\n".join(lines) + "\n"


def _main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate a CircuitJS inverting integrator netlist on stdout."
    )
    parser.add_argument("gain_v_per_v", type=float, help=f"gain in V/V at {SOURCE_FREQ_HZ:g} Hz (> 0)")
    parser.add_argument("input_resistor_ohms", type=float, help="target R, ohms (> 0)")
    parser.add_argument(
        "--waveform", choices=sorted(_WAVEFORMS), default="square",
        help="test-signal waveform (default: square)",
    )
    args = parser.parse_args(argv)

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            netlist = integrator(args.gain_v_per_v, args.input_resistor_ohms, args.waveform)
    except ValueError as exc:
        parser.error(str(exc))
    for w in caught:  # keep stdout clean: netlist only
        print(f"warning: {w.message}", file=sys.stderr)
    print(netlist, end="")


if __name__ == "__main__":
    _main()