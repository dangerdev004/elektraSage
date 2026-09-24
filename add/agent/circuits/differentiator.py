"""Generate a Falstad (CircuitJS) inverting op-amp differentiator netlist."""

import argparse
import math
import sys
import warnings
from typing import Literal

from . import resistors_approximation
from . import capacitors_approximation

# Waveform codes for the "v" (voltage source) element's flat-dump format.
# "triangle" is confirmed from a real exported differentiator circuit. "sine"
# is a strong inference: used unprompted, without correction, in every "v"
# line generated across this whole project. "square" is an unconfirmed guess
# (2), based on a plausible dropdown ordering (DC, sine, square, triangle)
# consistent with both confirmed values - verify against the simulator's own
# Edit dialog if it matters, and fix this one line if it's wrong.
_WAVEFORMS = {"sine": 1, "square": 2, "triangle": 3}

# Fixed test-signal values, matching the exported reference circuit exactly.
# gain_v_per_v is defined AT this frequency (see differentiator()'s
# docstring), so SOURCE_FREQ_HZ isn't just a test detail - it's part of what
# the gain number means.
SOURCE_PEAK_V = 5.0
SOURCE_FREQ_HZ = 40.0
RAIL_V = 15.0  # op-amp max/min output, matching the exported reference

_MAX_TIME_STEP = 5e-6  # s
_SAMPLES_PER_PERIOD = 200
_EXACT_REL_TOL = 1e-9  # frequencies closer than this count as exact (float noise)


class GainErrorWarning(UserWarning):
    """The standard Rf and C values give a gain (at SOURCE_FREQ_HZ) different from the request."""


class ClippingRiskWarning(UserWarning):
    """The estimated output peak, for the fixed test signal, exceeds the op-amp rails."""


def _fmt(x: float) -> str:
    """Shortest exact float text (unlike :f or :e, never rounds values away)."""
    return repr(float(x))


def _estimate_peak_output(gain: float, waveform: str) -> float:
    """Ideal-differentiator output peak at the fixed test tone, given the
    achieved gain (at SOURCE_FREQ_HZ). Because gain = 2*pi*f*Rf*C, the
    SOURCE_FREQ_HZ dependence cancels algebraically for triangle and sine,
    leaving an exact closed form in terms of gain alone (verified
    numerically against differentiating each waveform directly):

        triangle: peak = gain * 2*SOURCE_PEAK_V / pi
        sine:     peak = gain * SOURCE_PEAK_V

    A square wave's derivative is, ideally, an impulse at each edge; its
    simulated spike height depends on the timestep and the op-amp's own
    limitations, not simply on gain. There is no equally clean formula for
    it, so the triangle formula is used as a rough, likely-optimistic
    (i.e. not guaranteed conservative) stand-in - treat any square-wave
    result as a loose indicator, not a precise estimate.
    """
    if waveform == "sine":
        return gain * SOURCE_PEAK_V
    return gain * 2 * SOURCE_PEAK_V / math.pi  # triangle (exact) or square (rough stand-in)


def differentiator(
    gain_v_per_v: float,
    feedback_resistor_ohms: float,
    waveform: Literal["sine", "square", "triangle"] = "triangle",
) -> str:
    """Generate a Falstad-format inverting op-amp differentiator circuit.

    Topology: Vin -> C -> inverting input; Rf feedback from output to the
    inverting input; non-inverting input grounded (verified by tracing the
    exported reference's wiring). Ideal gain magnitude is 2*pi*f*Rf*C - for a
    differentiator this genuinely depends on frequency, so `gain_v_per_v`
    is defined specifically as the gain at the fixed test frequency
    SOURCE_FREQ_HZ: gain_v_per_v = 2*pi*SOURCE_FREQ_HZ*Rf*C. In the time
    domain, Vout(t) = -(Rf*C) * d(Vin)/dt.

    Rf is the standard value nearest `feedback_resistor_ohms`. C is then
    solved from gain_v_per_v and snapped Rf, then itself snapped to a
    standard value - mirroring how inverting_amp.py snaps both R and Rf.
    Because both are snapped, the actual gain (at SOURCE_FREQ_HZ) usually
    differs slightly from the request; a GainErrorWarning reports it when
    it does.

    The test signal (waveform aside) is fixed rather than exposed here: peak
    voltage SOURCE_PEAK_V and frequency SOURCE_FREQ_HZ, both matching the
    exported reference. If the estimated output peak for that fixed tone
    would exceed the op-amp's rails, a ClippingRiskWarning reports it (this
    never blocks generation - see module docstring).

    Args:
        gain_v_per_v: Desired gain magnitude (V/V) at SOURCE_FREQ_HZ.
        feedback_resistor_ohms: Target feedback resistor Rf in ohms.
        waveform: Test-signal shape - "sine", "square", or "triangle"
            (default). See module comment for confidence level on the
            "square" code.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If gain_v_per_v or feedback_resistor_ohms is not a
            finite number > 0, or if waveform is not a supported choice.

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
        ("feedback_resistor_ohms", feedback_resistor_ohms),
    ):
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a finite value > 0, got {value!r}")

    Rf = resistors_approximation.resistors_approximation(feedback_resistor_ohms)
    ideal_C = gain_v_per_v / (2 * math.pi * SOURCE_FREQ_HZ * Rf)
    C = capacitors_approximation.capacitors_approximation(ideal_C)
    actual_gain = 2 * math.pi * SOURCE_FREQ_HZ * Rf * C

    if not math.isclose(actual_gain, gain_v_per_v, rel_tol=_EXACT_REL_TOL):
        error = (actual_gain - gain_v_per_v) / gain_v_per_v * 100
        warnings.warn(
            f"requested gain {gain_v_per_v:g} V/V at {SOURCE_FREQ_HZ:g} Hz, achieved "
            f"{actual_gain:.4g} V/V (Rf={Rf:g} ohm, C={C:g} F): error {error:+.2f}%",
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

    # Geometry matches inverting_amp.py's proven layout, with the input
    # resistor replaced by the input capacitor (the only topological change
    # between an inverting amplifier and an inverting differentiator).
    lines = [
        f"$ 1 {_fmt(time_step)} 10 57 5.0",
        f"v 96 256 96 112 0 {_WAVEFORMS[waveform]} {_fmt(SOURCE_FREQ_HZ)} {_fmt(SOURCE_PEAK_V)} 0.0",
        "g 96 256 96 304 0",
        f"c 96 112 192 112 0 {_fmt(C)} 0.0",
        f"r 192 144 336 144 0 {_fmt(Rf)}",
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
        description="Generate a CircuitJS inverting differentiator netlist on stdout."
    )
    parser.add_argument("gain_v_per_v", type=float, help=f"gain in V/V at {SOURCE_FREQ_HZ:g} Hz (> 0)")
    parser.add_argument("feedback_resistor_ohms", type=float, help="target Rf, ohms (> 0)")
    parser.add_argument(
        "--waveform", choices=sorted(_WAVEFORMS), default="triangle",
        help="test-signal waveform (default: triangle)",
    )
    args = parser.parse_args(argv)

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            netlist = differentiator(
                args.gain_v_per_v, args.feedback_resistor_ohms, args.waveform
            )
    except ValueError as exc:
        parser.error(str(exc))
    for w in caught:  # keep stdout clean: netlist only
        print(f"warning: {w.message}", file=sys.stderr)
    print(netlist, end="")


if __name__ == "__main__":
    _main()