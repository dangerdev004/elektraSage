"""Generate a Falstad (CircuitJS) inverting op-amp circuit netlist."""

import argparse
import math
import sys
import warnings

from . import resistors_approximation

DEFAULT_SUPPLY = 50.0     # V; used as the +/- output clipping limit
DEFAULT_AMPLITUDE = 1e-3  # V, peak
DEFAULT_FREQUENCY = 1e3   # Hz
DEFAULT_GBW = 1e6         # Hz; believed to be the stock CircuitJS default

_MAX_TIME_STEP = 5e-6     # s
_SAMPLES_PER_PERIOD = 200
_EXACT_REL_TOL = 1e-9     # gains closer than this count as exact (float noise)
_HEADROOM_WARN_FRACTION = 0.9  # warn when the output reaches this share of the limit


class GainErrorWarning(UserWarning):
    """The standard resistor values give a gain different from the request."""


class ClippingRiskWarning(UserWarning):
    """The output is close to the op-amp limit (but not beyond it)."""


def _fmt(x: float) -> str:
    """Shortest exact float text (unlike :f, never rounds small values to 0)."""
    return repr(float(x))


def _require_positive(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite value > 0, got {value!r}")


def inverting_amp(
    gain: float,
    res: float,
    amp_supply: float = DEFAULT_SUPPLY,
    input_amplitude: float = DEFAULT_AMPLITUDE,
    input_frequency: float = DEFAULT_FREQUENCY,
    gbw: float = DEFAULT_GBW,
) -> str:
    """Generate a Falstad-format inverting op-amp circuit.

    R is the standard value nearest `res`, and Rf the standard value nearest
    gain * R, both from resistors_approximation. Because standard values are
    discrete, the achieved gain Rf / R usually differs slightly from `gain`;
    when it does, a GainErrorWarning reports the achieved gain and the error.

    The output amplitude (achieved gain * input_amplitude) is compared with
    the op-amp limit: at or beyond it is an error, and within 10% of it is a
    ClippingRiskWarning, because real op amps clip below the rails while the
    netlist models an ideal hard limit.

    Args:
        gain: Desired voltage gain magnitude (Rf / R). The stage always
            inverts, so this must be > 0.
        res: Target input resistor R in ohms.
        amp_supply: Op-amp output limit in volts, applied as +/- amp_supply.
        input_amplitude: Peak amplitude of the input source in volts.
        input_frequency: Frequency of the input source in hertz.
        gbw: Op-amp gain-bandwidth product in hertz.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If any argument is not a finite number > 0, if the
            requested gain would drive the output to the limit, or if the
            standard values chosen would.

    Warns:
        GainErrorWarning: If the achieved gain differs from `gain`.
        ClippingRiskWarning: If the output amplitude is within 10% of
            `amp_supply` (but below it).
    """
    for name, value in (
        ("gain", gain),
        ("res", res),
        ("amp_supply", amp_supply),
        ("input_amplitude", input_amplitude),
        ("input_frequency", input_frequency),
        ("gbw", gbw),
    ):
        _require_positive(name, value)

    max_gain = amp_supply / input_amplitude
    if gain >= max_gain:
        raise ValueError(
            f"gain {gain:g} would drive the output to "
            f"{gain * input_amplitude:g} V, at or beyond the "
            f"+/-{amp_supply:g} V limit (maximum gain here is {max_gain:g})"
        )

    R = resistors_approximation.resistors_approximation(res)
    Rf = resistors_approximation.resistors_approximation(gain * R)
    actual_gain = Rf / R

    if actual_gain >= max_gain:
        raise ValueError(
            f"the standard values R={R:g} ohm, Rf={Rf:g} ohm give gain "
            f"{actual_gain:g}, which drives the output to "
            f"{actual_gain * input_amplitude:g} V, at or beyond the "
            f"+/-{amp_supply:g} V limit"
        )

    if not math.isclose(actual_gain, gain, rel_tol=_EXACT_REL_TOL):
        error = (actual_gain - gain) / gain * 100
        warnings.warn(
            f"requested gain {gain:g}, achieved {actual_gain:.4g} "
            f"(R={R:g} ohm, Rf={Rf:g} ohm): error {error:+.2f}%",
            GainErrorWarning,
            stacklevel=2,
        )

    output_amplitude = actual_gain * input_amplitude
    if output_amplitude >= _HEADROOM_WARN_FRACTION * amp_supply:
        warnings.warn(
            f"output amplitude {output_amplitude:.4g} V is "
            f"{output_amplitude / amp_supply * 100:.1f}% of the "
            f"+/-{amp_supply:g} V limit; real op amps clip below the rails, "
            "so expect clipping on the bench",
            ClippingRiskWarning,
            stacklevel=2,
        )

    time_step = min(_MAX_TIME_STEP, 1 / (input_frequency * _SAMPLES_PER_PERIOD))

    return (
        f"$ 1 {_fmt(time_step)} 10 57 5.0\n"
        f"v 96 256 96 112 0 1 {_fmt(input_frequency)} {_fmt(input_amplitude)} 0.0\n"
        "g 96 256 96 304 0\n"
        f"r 96 112 192 112 0 {_fmt(R)}\n"
        f"r 192 144 336 144 0 {_fmt(Rf)}\n"
        "w 336 144 336 192 0\n"
        "w 192 112 192 144 0\n"
        "w 192 144 192 176 0\n"
        "w 96 256 192 256 0\n"
        "w 192 208 192 256 0\n"
        f"a 192 192 336 192 0 {_fmt(amp_supply)} {_fmt(-amp_supply)} {_fmt(gbw)}\n"
        "O 336 192 400 192 0\n"
        f"o 0 64 0 2 {_fmt(input_amplitude)} 0.025\n"
        f"o 10 64 0 2 {_fmt(output_amplitude)} 9.765625E-5\n"
    )


def _main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate a CircuitJS inverting op-amp netlist on stdout."
    )
    parser.add_argument("gain", type=float, help="absolute gain |Rf/R| (> 0)")
    parser.add_argument("res", type=float, help="target input resistor R (ohms)")
    parser.add_argument(
        "amp_supply", type=float, nargs="?", default=DEFAULT_SUPPLY,
        help=f"output limit, +/- volts (default {DEFAULT_SUPPLY:g})",
    )
    parser.add_argument(
        "input_amplitude", type=float, nargs="?", default=DEFAULT_AMPLITUDE,
        help=f"input peak amplitude, volts (default {DEFAULT_AMPLITUDE:g})",
    )
    parser.add_argument(
        "input_frequency", type=float, nargs="?", default=DEFAULT_FREQUENCY,
        help=f"input frequency, Hz (default {DEFAULT_FREQUENCY:g})",
    )
    parser.add_argument(
        "--gbw", type=float, default=DEFAULT_GBW,
        help=f"op-amp gain-bandwidth, Hz (default {DEFAULT_GBW:g})",
    )
    args = parser.parse_args(argv)

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            netlist = inverting_amp(
                args.gain, args.res, args.amp_supply,
                args.input_amplitude, args.input_frequency, args.gbw,
            )
    except ValueError as exc:
        parser.error(str(exc))
    for w in caught:  # keep stdout clean: netlist only
        print(f"warning: {w.message}", file=sys.stderr)
    print(netlist, end="")


if __name__ == "__main__":
    _main()