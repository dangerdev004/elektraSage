"""Generate a Falstad (CircuitJS) inverting summing amplifier netlist."""

import argparse
import math
import sys
import warnings
from typing import Literal

from . import resistors_approximation

# Waveform codes for the "R" (1-terminal rail source) element's flat-dump
# format - same codes and confidence levels as differentiator.py's "v"
# element: "triangle" (3) confirmed from a real export, "sine" (1) a strong
# inference, "square" (2) an unconfirmed guess.
_WAVEFORMS = {"sine": 1, "square": 2, "triangle": 3}

# Fixed test-signal amplitudes, matching the exported reference exactly.
INPUT1_PEAK_V = 5.0
INPUT2_PEAK_V = 2.0
R_TARGET_OHMS = 1000.0  # both input resistors target this value (equal weighting)
RAIL_V = 15.0  # op-amp max/min output, matching the exported reference

_MAX_TIME_STEP = 5e-6  # s
_SAMPLES_PER_PERIOD = 200
_EXACT_REL_TOL = 1e-9  # gains closer than this count as exact (float noise)


class GainErrorWarning(UserWarning):
    """The standard R and Rf values give a gain different from the request."""


class ClippingRiskWarning(UserWarning):
    """The estimated output peak, if both inputs peaked together, exceeds the op-amp rails."""


def _fmt(x: float) -> str:
    """Shortest exact float text (unlike :f or :e, never rounds values away)."""
    return repr(float(x))


def summing_amplifier(
    gain_v_per_v: float,
    input1_frequency_hz: float,
    input2_frequency_hz: float,
    input1_waveform: Literal["sine", "square", "triangle"] = "sine",
    input2_waveform: Literal["sine", "square", "triangle"] = "square",
) -> str:
    """Generate a Falstad-format inverting summing amplifier circuit.

    Topology: two independent 1-terminal sources, each through its own input
    resistor R, into a common virtual-ground summing junction (the op-amp's
    inverting input); one feedback resistor Rf from that junction to the
    output; non-inverting input grounded (verified by tracing the exported
    reference's wiring, and the transfer function checked numerically).
    Because both input resistors target the same value, both inputs get the
    same weighting: Vout(t) = -(Rf/R) * (V1(t) + V2(t)) - a single overall
    gain on the summed output, not independent per-input gains.

    Unlike differentiator.py/integrator.py, this gain has no frequency
    dependence at all (it's a plain resistor network, not RC), so
    gain_v_per_v applies at every frequency, and waveform shape does not
    change the peak relationship - the output is just a scaled copy of
    whatever comes in.

    R is the standard value nearest R_TARGET_OHMS. Rf is then solved from
    gain_v_per_v and snapped R, then itself snapped to a standard value -
    mirroring inverting_amp.py's R/Rf snapping. Because both are snapped,
    the actual gain usually differs slightly from the request; a
    GainErrorWarning reports it when it does.

    Each input's peak voltage is fixed (INPUT1_PEAK_V, INPUT2_PEAK_V,
    matching the exported reference) rather than exposed here. If the
    estimated output peak, assuming both inputs happened to peak at the same
    instant (a worst-case upper bound, not necessarily reached), would
    exceed the op-amp's rails, a ClippingRiskWarning reports it (this never
    blocks generation).

    Args:
        gain_v_per_v: Desired gain magnitude (V/V) applied to the summed
            inputs: |Vout| = gain_v_per_v * |V1 + V2|.
        input1_frequency_hz: Frequency of the first input in hertz.
        input2_frequency_hz: Frequency of the second input in hertz.
        input1_waveform: Shape of the first input - "sine" (default),
            "square", or "triangle". See module comment for confidence
            level on the "square" code.
        input2_waveform: Shape of the second input - "sine", "square"
            (default), or "triangle".

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If gain_v_per_v, input1_frequency_hz, or
            input2_frequency_hz is not a finite number > 0, or if either
            waveform is not a supported choice.

    Warns:
        GainErrorWarning: If the achieved gain differs from the request.
        ClippingRiskWarning: If the worst-case estimated output peak exceeds
            +/-RAIL_V.
    """
    for waveform, name in (
        (input1_waveform, "input1_waveform"),
        (input2_waveform, "input2_waveform"),
    ):
        if waveform not in _WAVEFORMS:
            raise ValueError(
                f"{name} must be one of {sorted(_WAVEFORMS)}, got {waveform!r}"
            )
    for name, value in (
        ("gain_v_per_v", gain_v_per_v),
        ("input1_frequency_hz", input1_frequency_hz),
        ("input2_frequency_hz", input2_frequency_hz),
    ):
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a finite value > 0, got {value!r}")

    R = resistors_approximation(R_TARGET_OHMS)
    ideal_Rf = gain_v_per_v * R
    Rf = resistors_approximation(ideal_Rf)
    actual_gain = Rf / R

    if not math.isclose(actual_gain, gain_v_per_v, rel_tol=_EXACT_REL_TOL):
        error = (actual_gain - gain_v_per_v) / gain_v_per_v * 100
        warnings.warn(
            f"requested gain {gain_v_per_v:g} V/V, achieved {actual_gain:.4g} V/V "
            f"(R={R:g} ohm, Rf={Rf:g} ohm): error {error:+.2f}%",
            GainErrorWarning,
            stacklevel=2,
        )

    peak_out = actual_gain * (INPUT1_PEAK_V + INPUT2_PEAK_V)
    if peak_out > RAIL_V:
        warnings.warn(
            f"estimated output peak {peak_out:.3g} V (worst case, if both "
            f"inputs peaked together) exceeds the +/-{RAIL_V:g} V op-amp "
            "rails, so the output may clip",
            ClippingRiskWarning,
            stacklevel=2,
        )

    highest_freq = max(input1_frequency_hz, input2_frequency_hz)
    time_step = min(_MAX_TIME_STEP, 1 / (highest_freq * _SAMPLES_PER_PERIOD))

    # Geometry matches the exported reference's coordinates exactly. The
    # op-amp line uses only max/min output (no gbw field) here, matching
    # that reference precisely - gbw has no simulated effect regardless
    # (confirmed earlier), so this is a purely cosmetic difference from the
    # 3-field style used in this project's other op-amp circuits.
    lines = [
        f"$ 1 {_fmt(time_step)} 10 57 5.0",
        "a 288 208 432 208 0 15.0 -15.0",
        "w 288 128 288 192 0",
        "w 432 208 432 128 0",
        f"r 288 128 432 128 0 {_fmt(Rf)}",
        "w 288 224 288 272 0",
        "g 288 272 288 304 0",
        "w 288 192 240 192 0",
        "w 240 192 240 160 0",
        "w 240 192 240 224 0",
        f"r 240 160 176 160 0 {_fmt(R)}",
        f"r 176 224 240 224 0 {_fmt(R)}",
        f"R 176 160 128 160 0 {_WAVEFORMS[input1_waveform]} {_fmt(input1_frequency_hz)} {_fmt(INPUT1_PEAK_V)} 0.0",
        f"R 176 224 128 224 0 {_WAVEFORMS[input2_waveform]} {_fmt(input2_frequency_hz)} {_fmt(INPUT2_PEAK_V)} 0.0",
        "O 432 208 496 208 0",
    ]
    input1_index = next(i for i, l in enumerate(lines[1:]) if l.startswith("R 176 160"))
    input2_index = next(i for i, l in enumerate(lines[1:]) if l.startswith("R 176 224"))
    output_index = next(i for i, l in enumerate(lines[1:]) if l.startswith("O "))
    lines += [
        f"o {input1_index} 64 0 2 {_fmt(INPUT1_PEAK_V)} 9.765625E-5",
        f"o {input2_index} 64 0 2 {_fmt(INPUT2_PEAK_V)} 9.765625E-5",
        f"o {output_index} 64 0 2 {_fmt(INPUT1_PEAK_V + INPUT2_PEAK_V)} 9.765625E-5",
    ]
    return "\n".join(lines) + "\n"


def _main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate a CircuitJS inverting summing amplifier netlist on stdout."
    )
    parser.add_argument("gain_v_per_v", type=float, help="gain of the summed output, V/V (> 0)")
    parser.add_argument("input1_frequency_hz", type=float, help="first input's frequency, Hz (> 0)")
    parser.add_argument("input2_frequency_hz", type=float, help="second input's frequency, Hz (> 0)")
    parser.add_argument(
        "--input1-waveform", choices=sorted(_WAVEFORMS), default="sine",
        help="first input's waveform (default: sine)",
    )
    parser.add_argument(
        "--input2-waveform", choices=sorted(_WAVEFORMS), default="square",
        help="second input's waveform (default: square)",
    )
    args = parser.parse_args(argv)

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            netlist = summing_amplifier(
                args.gain_v_per_v, args.input1_frequency_hz, args.input2_frequency_hz,
                args.input1_waveform, args.input2_waveform,
            )
    except ValueError as exc:
        parser.error(str(exc))
    for w in caught:  # keep stdout clean: netlist only
        print(f"warning: {w.message}", file=sys.stderr)
    print(netlist, end="")


if __name__ == "__main__":
    _main()
