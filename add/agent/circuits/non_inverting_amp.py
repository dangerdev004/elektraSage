"""Generate a Falstad (CircuitJS) non-inverting op-amp circuit netlist."""

import argparse
import math
import sys
import warnings

from . import resistors_approximation

DEFAULT_RES = 1000.0      # ohm; target for the resistor from the - input to ground
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


def non_inverting_amp(
    gain: float,
    res: float = DEFAULT_RES,
    amp_supply: float = DEFAULT_SUPPLY,
    input_amplitude: float = DEFAULT_AMPLITUDE,
    input_frequency: float = DEFAULT_FREQUENCY,
    gbw: float = DEFAULT_GBW,
) -> str:
    """Generate a Falstad-format non-inverting op-amp circuit.

    The gain is 1 + Rf / R. R (from the inverting input to ground) is the
    standard value nearest `res`, and Rf (the feedback resistor) is the
    standard value nearest (gain - 1) * R, both from resistors_approximation.
    Because standard values are discrete, the achieved gain usually differs
    slightly from `gain`; when it does, a GainErrorWarning reports the
    achieved gain and the error.

    A gain of 1 (within float noise) generates a voltage follower: the output
    is wired straight to the inverting input, with no resistors at all.

    The output amplitude (achieved gain * input_amplitude) is compared with
    the op-amp limit: at or beyond it is an error, and within 10% of it is a
    ClippingRiskWarning, because real op amps clip below the rails while the
    netlist models an ideal hard limit.

    Args:
        gain: Desired voltage gain (Vout / Vin). Must be >= 1, because a
            non-inverting stage cannot attenuate.
        res: Target resistance R to ground in ohms. Ignored for a follower.
        amp_supply: Op-amp output limit in volts, applied as +/- amp_supply.
        input_amplitude: Peak amplitude of the input source in volts.
        input_frequency: Frequency of the input source in hertz.
        gbw: Op-amp gain-bandwidth product in hertz.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If any argument is not a finite number > 0, if gain is
            below 1, if the requested gain would drive the output to the
            limit, or if the standard values chosen would.

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

    follower = math.isclose(gain, 1.0, rel_tol=_EXACT_REL_TOL)
    if not follower and gain < 1:
        raise ValueError(
            f"gain must be >= 1 for a non-inverting amplifier "
            f"(it cannot attenuate), got {gain!r}"
        )

    max_gain = amp_supply / input_amplitude
    if gain >= max_gain:
        warnings.warn(
            f"gain {gain:g} would drive the output to "
            f"{gain * input_amplitude:g} V, at or beyond the "
            f"+/-{amp_supply:g} V limit (maximum gain here is {max_gain:g})",
            ClippingRiskWarning,
            stacklevel=2,
        )

    if follower:
        R = Rf = None
        actual_gain = 1.0
    else:
        R = resistors_approximation.resistors_approximation(res)
        Rf = resistors_approximation.resistors_approximation((gain - 1) * R)
        actual_gain = 1 + Rf / R

    if actual_gain >= max_gain:
         warnings.warn(
            f"the standard values R={R:g} ohm, Rf={Rf:g} ohm give gain "
            f"{actual_gain:g}, which drives the output to "
            f"{actual_gain * input_amplitude:g} V, at or beyond the "
            f"+/-{amp_supply:g} V limit",
            ClippingRiskWarning,
            stacklevel=2,
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

    elements = [
        f"v 96 256 96 112 0 1 {_fmt(input_frequency)} {_fmt(input_amplitude)} 0.0",
        "g 96 256 96 304 0",
        "w 192 208 192 256 0",
        f"a 192 192 336 192 1 {_fmt(amp_supply)} {_fmt(-amp_supply)} {_fmt(gbw)}",
        "w 336 192 336 256 0",
    ]
    if follower:
        elements.append("w 192 256 336 256 0")  # output straight to - input
    else:
        elements += [
            f"r 192 256 336 256 0 {_fmt(Rf)}",
            f"r 96 256 192 256 0 {_fmt(R)}",
        ]
    elements += [
        "w 96 112 192 112 0",
        "w 192 112 192 176 0",
        "O 336 192 400 192 0",
    ]
    # Scopes refer to elements by index, and the follower has fewer of them.
    output_index = next(i for i, e in enumerate(elements) if e.startswith("O "))

    lines = [
        f"$ 1 {_fmt(time_step)} 10 57 5.0",
        *elements,
        f"o 0 64 0 2 {_fmt(input_amplitude)} 9.765625E-5",
        f"o {output_index} 64 0 2 {_fmt(output_amplitude)} 9.765625E-5",
    ]
    return "\n".join(lines) + "\n"

class _Parser(argparse.ArgumentParser):
    def format_usage(self):
        return super().format_usage() + "note: enter the absolute gain, without a sign\n"

def _main(argv: list[str] | None = None) -> None:
    parser = _Parser(
        description="Generate a CircuitJS non-inverting op-amp netlist on stdout."
    )
    parser.add_argument("gain", type=float, help="voltage gain (>= 1; 1 = follower)")
    parser.add_argument(
        "res", type=float, nargs="?", default=DEFAULT_RES,
        help=f"target resistor R to ground, ohms (default {DEFAULT_RES:g})",
    )
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
            netlist = non_inverting_amp(
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