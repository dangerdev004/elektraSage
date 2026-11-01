"""Combiner circuits for parallel paths: a weighted inverting sum of N signals, or a difference of two.

These are not offered to the language model as circuits of their own; `parallel_sum` / `parallel_difference`
build them. Each is the same kind of netlist the other generators emit (legacy dialect, one `R` signal source per
input, an `O` marker on the output), so ports are found by the usual inference and the composer drops the test
sources before wiring the paths in.

Sum:        out = -gain * (w1*V1 + w2*V2 + ... + wN*VN)       one op-amp, N input resistors, one feedback resistor
Difference: out =  gain * (V1 - V2)                           one op-amp, four resistors (R, R, Rf, Rf)
"""

from __future__ import annotations

import math
import warnings

from agent.circuits.resistors_approximation import resistors_approximation

MAX_PATHS = 8
R_TARGET_OHMS = 1000.0
RAIL_V = 15.0
_FMT = repr


class GainErrorWarning(UserWarning):
    """The standard resistor values give a gain different from the request."""


def _check(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite number > 0, got {value!r}")


_E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8,
        7.5, 8.2, 9.1]


def _pick_resistors(gains: list[float]) -> tuple[float, list[float]]:
    """Feedback resistor and input resistors (standard E24 values) that give every input gain as closely as
    possible; among equally good choices the feedback resistor nearest 1 kOhm x the largest gain, which keeps the
    input resistors near 1 kOhm."""
    target = R_TARGET_OHMS * max(gains)
    best = None
    for exp in range(2, 6):
        for base in _E24:
            rf = round(base * 10 ** exp, 6)
            rin = [resistors_approximation(rf / g) for g in gains]
            if min(rin) < 200 or max(rin) > 1e6:
                continue
            err = max(abs(rf / r / g - 1) for r, g in zip(rin, gains))
            key = (round(err, 6), abs(math.log(rf / target)))
            if best is None or key < best[0]:
                best = (key, rf, rin)
    if best is None:
        raise ValueError("the requested gains are too far apart (or too large or small) for standard resistors; "
                         "use gains within about a factor of 1000 of each other")
    return best[1], best[2]


def sum_combiner(n: int, gain_v_per_v: float = 1.0, weights: list[float] | None = None) -> str:
    """Inverting summing amplifier with n inputs: out = -gain * sum(w_i * V_i).

    Input resistor i is the standard value nearest (feedback resistor) / (gain * w_i), so every input's own gain is
    set separately. A GainErrorWarning is issued when a snapped value changes an input's gain by more than 1 %.
    """
    if isinstance(n, bool) or not isinstance(n, int) or not 2 <= n <= MAX_PATHS:
        raise ValueError(f"the number of paths must be a whole number from 2 to {MAX_PATHS}, got {n!r}")
    _check("gain_v_per_v", gain_v_per_v)
    weights = [1.0] * n if weights is None else list(weights)
    if len(weights) != n:
        raise ValueError(f"weights must have one value per path ({n}), got {len(weights)}")
    for k, w in enumerate(weights, 1):
        _check(f"weights[{k}]", w)
    wanted = [gain_v_per_v * w for w in weights]
    rf, rin = _pick_resistors(wanted)
    for k, (g, r) in enumerate(zip(wanted, rin), 1):
        achieved = rf / r
        if not math.isclose(achieved, g, rel_tol=0.01):
            warnings.warn(f"path {k}: requested gain {g:g} V/V, standard resistors give {achieved:.4g} V/V "
                          f"(error {100 * (achieved - g) / g:+.2f}%)", GainErrorWarning, stacklevel=2)

    jy = 192                                                  # summing junction row (op-amp inverting input)
    rows = [jy + 32 * (2 * i - (n - 1)) for i in range(n)]    # 64 apart, centred on the junction
    lines = [
        "$ 1 5e-06 10 57 5.0",
        "a 288 208 432 208 0 15.0 -15.0",
        f"w 288 128 288 {jy}",
        "w 432 208 432 128",
        f"r 288 128 432 128 0 {_FMT(rf)}",
        "w 288 224 288 272",
        "g 288 272 288 304 0",
        f"w 288 {jy} 240 {jy}",
    ]
    stops = sorted({jy, *rows})
    lines += [f"w 240 {a} 240 {b}" for a, b in zip(stops, stops[1:])]
    sources = []
    for row, r in zip(rows, rin):
        lines.append(f"r 240 {row} 176 {row} 0 {_FMT(r)}")
        sources.append(f"R 176 {row} 128 {row} 0 1 1000.0 2.0 0.0")
    lines += sources
    lines.append("O 432 208 496 208 0")
    return _with_scopes(lines)


def difference_combiner(gain_v_per_v: float = 1.0, positive_on_top: bool = True) -> str:
    """Difference amplifier: out = gain * (V_plus - V_minus).

    positive_on_top=True puts the plus input (non-inverting side, with a resistor to ground) on the upper input and
    the minus input below it; False swaps their places, for when the composer stacks the paths the other way up.
    """
    _check("gain_v_per_v", gain_v_per_v)
    r = resistors_approximation(R_TARGET_OHMS)
    rf = resistors_approximation(gain_v_per_v * r)
    achieved = rf / r
    if not math.isclose(achieved, gain_v_per_v, rel_tol=0.01):
        warnings.warn(f"requested gain {gain_v_per_v:g} V/V, standard resistors give {achieved:.4g} V/V "
                      f"(error {100 * (achieved - gain_v_per_v) / gain_v_per_v:+.2f}%)", GainErrorWarning,
                      stacklevel=2)
    if positive_on_top:
        lines = [
            "$ 1 5e-06 10 57 5.0",
            "a 288 208 432 208 1 15.0 -15.0",      # flags=1: upper pin (288,192) non-inverting, lower (288,224) inverting
            "w 240 160 240 192",
            "w 240 192 288 192",
            f"r 240 160 176 160 0 {_FMT(r)}",
            f"r 288 192 288 144 0 {_FMT(rf)}",
            "g 288 144 288 128 0",
            "w 240 224 288 224",
            f"r 240 224 176 224 0 {_FMT(r)}",
            "w 288 224 288 272",
            f"r 288 272 432 272 0 {_FMT(rf)}",
            "w 432 208 432 272",
        ]
    else:
        lines = [
            "$ 1 5e-06 10 57 5.0",
            "a 288 208 432 208 0 15.0 -15.0",      # flags=0: upper pin (288,192) inverting, lower (288,224) non-inverting
            "w 240 160 240 192",
            "w 240 192 288 192",
            f"r 240 160 176 160 0 {_FMT(r)}",
            "w 288 128 288 192",
            f"r 288 128 432 128 0 {_FMT(rf)}",
            "w 432 208 432 128",
            "w 240 224 288 224",
            f"r 240 224 176 224 0 {_FMT(r)}",
            f"r 288 224 288 272 0 {_FMT(rf)}",
            "g 288 272 288 304 0",
        ]
    lines += ["R 176 160 128 160 0 1 1000.0 2.0 0.0", "R 176 224 128 224 0 1 1000.0 2.0 0.0",
              "O 432 208 496 208 0"]
    return _with_scopes(lines)


def _with_scopes(lines: list[str]) -> str:
    """Append one scope per source and the output (scope lines index the elements, not the header)."""
    watch = [i - 1 for i, l in enumerate(lines) if l.startswith(("R ", "O "))]
    scale = {"R": 2.0, "O": 4.0}
    lines = lines + [f"o {i} 64 0 2 {scale[lines[i + 1][0]]} 9.765625E-5" for i in watch]
    return "\n".join(lines) + "\n"
