"""Generate a Falstad (CircuitJS) RC phase-shift oscillator netlist.

Topology: an inverting op amp whose feedback resistor is Rf, followed by a
three-section RC ladder (three series capacitors C, two shunt resistors R,
and a third R into the op amp's summing node). The ladder alone oscillates at

    f = 1 / (2 * pi * sqrt(6) * R * C)

and start-up needs Rf / R >= 29.
"""

import argparse
import math
import sys
import warnings

import resistors_approximation

DEFAULT_SUPPLY = 15.0  # V; +/- output limit, which also sets the oscillation amplitude
DEFAULT_GBW = 1e6      # Hz; written to the netlist for file-format
                        # compatibility only - CircuitJS ignores this field

# Capacitor decades tried in order; the first giving R in [_R_MIN, _R_MAX] wins.
_CAPS = (1e-12, 10e-12, 100e-12, 1e-9, 10e-9, 100e-9, 1e-6, 10e-6)
_R_MIN, _R_MAX = 1e3, 100e3

# Rf is chosen for a ratio of 32, so that snapping to standard values (which can
# move it by several percent) never lands below the 29 needed for start-up.
_TARGET_RATIO = 32.0
_START_RATIO = 29.0

_MAX_TIME_STEP = 1.5625e-5  # s
_SAMPLES_PER_PERIOD = 200
_EXACT_REL_TOL = 1e-9       # frequencies closer than this count as exact (float noise)

# Kept from the original netlist: capacitor initial voltages (they act as the
# start-up kick), the simulator-state fields after the op-amp GBW, and the tail
# of the $ header line.
_C_INITIAL = (-2.544137674334456, -3.308245117520446, -0.9716832694680744)
_OPAMP_STATE = "0.00006596531227299938 0"
_HEADER_TAIL = "3.046768661252054 58 5 50"

_F_MIN = 1 / (2 * math.pi * math.sqrt(6) * _R_MAX * _CAPS[-1])
_F_MAX = 1 / (2 * math.pi * math.sqrt(6) * _R_MIN * _CAPS[0])


class FrequencyErrorWarning(UserWarning):
    """The standard component values give a frequency different from the request."""


def _fmt(x: float) -> str:
    """Shortest exact float text (unlike :f or :e, never rounds values away)."""
    return repr(float(x))


def _require_positive(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite value > 0, got {value!r}")


def _ladder_frequency(R: float, C: float) -> float:
    return 1 / (2 * math.pi * math.sqrt(6) * R * C)


def _solve_rc(frequency_hz: float) -> tuple[float, float, float]:
    """Pick a preferred capacitor so R lands in [1k, 100k]; snap R and Rf."""
    for C in _CAPS:
        R_ideal = 1 / (2 * math.pi * math.sqrt(6) * frequency_hz * C)
        if _R_MIN <= R_ideal <= _R_MAX:
            break
    else:
        raise ValueError(
            f"frequency {frequency_hz:g} Hz is outside the supported range "
            f"({_F_MIN:.2g} Hz to {_F_MAX:.2g} Hz)"
        )
    R = resistors_approximation.resistors_approximation(R_ideal)
    Rf = resistors_approximation.resistors_approximation(_TARGET_RATIO * R)
    return R, Rf, C


def rc_phaseshift(
    frequency_hz: float,
    amp_supply: float = DEFAULT_SUPPLY,
    gbw: float = DEFAULT_GBW,
) -> str:
    """Generate a Falstad-format RC phase-shift oscillator circuit.

    C is a preferred decade value, R is the standard value nearest the ideal
    R for that C, and Rf is the standard value nearest 32 * R (32 rather than
    the theoretical 29, so that snapping cannot drop the ratio below the
    start-up requirement). Because R is snapped, the ladder frequency usually
    differs slightly from the request; a FrequencyErrorWarning reports it.

    There is no check for the op amp's bandwidth. An earlier version of this
    function estimated one, but the CircuitJS op-amp element's "gbw" field
    has no effect on the simulation in the current simulator (confirmed from
    its source) - it is written to the netlist only to keep the file format
    consistent. A real op amp's finite bandwidth can still stop this circuit
    oscillating at high frequency; this function just can't warn you when
    that applies, since the simulator won't reproduce it either.

    Args:
        frequency_hz: Desired oscillation frequency in Hz.
        amp_supply: Op-amp output limit in volts, applied as +/- amp_supply.
            The oscillation clips at this level, so it sets the amplitude.
        gbw: Written into the netlist for file-format compatibility, but the
            simulator ignores it; changing this has no effect on the result.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If an argument is not a finite number > 0, if the
            frequency is outside the range the capacitor list can cover, or
            if the standard values give a ratio below the start-up
            requirement.

    Warns:
        FrequencyErrorWarning: If the ladder frequency differs from the request.
    """
    for name, value in (
        ("frequency_hz", frequency_hz),
        ("amp_supply", amp_supply),
        ("gbw", gbw),
    ):
        _require_positive(name, value)

    R, Rf, C = _solve_rc(frequency_hz)
    ratio = Rf / R
    if ratio < _START_RATIO:
        raise ValueError(
            f"the standard values R={R:g} ohm, Rf={Rf:g} ohm give Rf/R = "
            f"{ratio:.3g}, below the {_START_RATIO:g} needed to start "
            "oscillating; resistors_approximation may be too coarse a series"
        )

    actual_frequency = _ladder_frequency(R, C)

    if not math.isclose(actual_frequency, frequency_hz, rel_tol=_EXACT_REL_TOL):
        error = (actual_frequency - frequency_hz) / frequency_hz * 100
        warnings.warn(
            f"requested {frequency_hz:g} Hz, ladder gives {actual_frequency:.4g} Hz "
            f"(R={R:g} ohm, Rf={Rf:g} ohm, C={C:g} F): error {error:+.2f}%",
            FrequencyErrorWarning,
            stacklevel=2,
        )

    time_step = min(_MAX_TIME_STEP, 1 / (actual_frequency * _SAMPLES_PER_PERIOD))
    v1, v2, v3 = _C_INITIAL

    lines = [
        f"$ 1 {_fmt(time_step)} {_HEADER_TAIL}",
        f"c 144 368 208 368 0 {_fmt(C)} {_fmt(v1)}",
        f"c 208 368 272 368 0 {_fmt(C)} {_fmt(v2)}",
        f"c 272 368 336 368 0 {_fmt(C)} {_fmt(v3)}",
        f"r 336 368 400 368 0 {_fmt(R)}",
        f"r 208 368 208 448 0 {_fmt(R)}",
        f"r 272 368 272 448 0 {_fmt(R)}",
        "g 208 448 208 464 0",
        "g 272 448 272 464 0",
        f"a 400 384 496 384 0 {_fmt(amp_supply)} {_fmt(-amp_supply)} {_fmt(gbw)} {_OPAMP_STATE}",
        "w 400 368 400 320 0",
        f"r 400 320 496 320 0 {_fmt(Rf)}",
        "w 496 320 496 384 0",
        "w 496 384 512 384 0",
        "w 512 384 512 288 0",
        "w 512 288 144 288 0",
        "w 144 288 144 368 0",
        "g 400 400 400 448 0",
    ]
    return "\n".join(lines) + "\n"


def _main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Generate a CircuitJS RC phase-shift oscillator netlist on stdout."
    )
    parser.add_argument("frequency", type=float, help="oscillation frequency, Hz (> 0)")
    parser.add_argument(
        "amp_supply", type=float, nargs="?", default=DEFAULT_SUPPLY,
        help=f"output limit, +/- volts (default {DEFAULT_SUPPLY:g})",
    )
    parser.add_argument(
        "--gbw", type=float, default=DEFAULT_GBW,
        help=(
            f"op-amp gain-bandwidth, Hz (default {DEFAULT_GBW:g}) - written to "
            "the netlist for file-format compatibility only; CircuitJS ignores "
            "this value, so changing it has no effect on the simulation"
        ),
    )
    args = parser.parse_args(argv)

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            netlist = rc_phaseshift(args.frequency, args.amp_supply, args.gbw)
    except ValueError as exc:
        parser.error(str(exc))
    for w in caught:  # keep stdout clean: netlist only
        print(f"warning: {w.message}", file=sys.stderr)
    print(netlist, end="")


if __name__ == "__main__":
    _main()