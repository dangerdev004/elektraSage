"""Shared pieces for the op-amp filter generators (not a circuit tool itself).

Every filter here uses the same source and layout conventions as rc_lowpass: a fixed AC
sweep source around the filter's frequency, standard (E24) resistors, decade capacitors,
and an `O` output marker on the op-amp output.
"""

import math
import warnings

from .resistors_approximation import E24, resistors_approximation as snap_resistor

_CAPS = (1e-12, 10e-12, 100e-12, 1e-9, 10e-9, 100e-9, 1e-6, 10e-6)
_R_MIN, _R_MAX = 1e3, 100e3
F_MIN = 1 / (2 * math.pi * _R_MAX * _CAPS[-1])
F_MAX = 1 / (2 * math.pi * _R_MIN * _CAPS[0])

SWEEP_DECADE_SPAN = 10
SWEEP_VOLTAGE = 1.0          # V peak: small enough that a Q of a few does not hit +/-15 V rails
SWEEP_TIME = 0.1
SWEEP_FLAGS = 3
GBW = 1e6
DEFAULT_SUPPLY = 15.0
MAX_TIME_STEP = 5e-6
SAMPLES_PER_PERIOD = 200
MAX_GAIN = 2.9               # gain >= 3 makes a Sallen-Key filter oscillate; 2.9 is Q = 10


class FilterAccuracyWarning(UserWarning):
    """The standard component values give a different frequency, gain or Q than requested."""


def fmt(x: float) -> str:
    return repr(float(x))


def require_positive(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite value > 0, got {value!r}")


def pick_rc(frequency: float, label: str = "frequency") -> tuple[float, float, float]:
    """Decade capacitor C and standard resistor R with 1/(2 pi R C) nearest `frequency`.
    Returns (R, C, achieved frequency) and warns when the achieved value differs."""
    require_positive(label, frequency)
    for C in _CAPS:
        r_ideal = 1 / (2 * math.pi * frequency * C)
        if _R_MIN <= r_ideal <= _R_MAX:
            break
    else:
        raise ValueError(f"{label} {frequency:g} Hz is outside the supported range "
                         f"({F_MIN:.2g} Hz to {F_MAX:.2g} Hz)")
    R = snap_resistor(r_ideal)
    actual = 1 / (2 * math.pi * R * C)
    if not math.isclose(actual, frequency, rel_tol=1e-9):
        warnings.warn(f"requested {label} {frequency:g} Hz, achieved {actual:.4g} Hz "
                      f"(R={R:g} ohm, C={C:g} F): error {(actual - frequency) / frequency * 100:+.2f}%",
                      FilterAccuracyWarning, stacklevel=3)
    return R, C, actual


def gain_resistors(gain: float) -> tuple[float | None, float | None, float]:
    """(Rg, Rf, achieved gain) for a non-inverting stage of the given gain. (None, None, 1.0)
    means a plain follower."""
    if math.isclose(gain, 1.0, rel_tol=1e-9):
        return None, None, 1.0
    rg = 10e3
    rf = snap_resistor((gain - 1) * rg)
    return rg, rf, 1 + rf / rg


def best_butterworth_gain() -> tuple[float, float, float]:
    """The standard (Rg, Rf) pair whose gain 1 + Rf/Rg puts an equal-component Sallen-Key
    section closest to Q = 1/sqrt(2). Returns (Rg, Rf, gain)."""
    target = 3 - math.sqrt(2)                       # gain giving Q = 1/sqrt(2)
    best = None
    for dec in (1e3, 1e4):
        for a in E24:
            for b in E24:
                rg, rf = a * dec, b * dec
                k = 1 + rf / rg
                err = abs(k - target)
                if best is None or err < best[0] - 1e-12:
                    best = (err, rg, rf, k)
    return best[1], best[2], best[3]


def gain_for_response(response, gain: float) -> float:
    """Op-amp gain K for a named response or a numeric Q (K = 3 - 1/Q). None keeps `gain`."""
    if response is None:
        return gain
    if isinstance(response, str):
        key = response.strip().lower()
        q = {"butterworth": 2 ** -0.5, "bessel": 3 ** -0.5, "linkwitz-riley": 2 ** -0.5}.get(key)
        if q is None:
            try:
                q = float(key)
            except ValueError:
                raise ValueError("response must be 'butterworth', 'bessel' or a number Q, got "
                                 f"{response!r}") from None
    else:
        q = float(response)
    if not math.isfinite(q) or q < 0.5:
        raise ValueError(f"Q must be at least 0.5 for this circuit (a follower gives 0.5), got {q!r}")
    k = 3 - 1 / q
    if k > MAX_GAIN:
        raise ValueError(f"Q = {q:g} needs a gain of {k:.3f}, beyond the {MAX_GAIN:g} limit "
                         f"(Q about 10)")
    return k


def q_of(gain: float) -> float:
    return 1 / (3 - gain)


def warn_gain(requested: float, achieved: float) -> None:
    if not math.isclose(requested, achieved, rel_tol=1e-9):
        warnings.warn(f"requested gain {requested:g}, achieved {achieved:.4g} "
                      f"(Q {q_of(achieved):.3g}): error {(achieved - requested) / requested * 100:+.2f}%",
                      FilterAccuracyWarning, stacklevel=3)


def amp_line(x1: int, y1: int, x2: int, supply: float) -> str:
    """Op-amp with + input at (x1, y1-16), - input at (x1, y1+16), output at (x2, y1)."""
    return f"a {x1} {y1} {x2} {y1} 1 {fmt(supply)} {fmt(-supply)} {fmt(GBW)}"


def sweep_source(f_actual: float) -> str:
    return (f"170 240 160 208 160 {SWEEP_FLAGS} {fmt(f_actual / SWEEP_DECADE_SPAN)} "
            f"{fmt(f_actual * SWEEP_DECADE_SPAN)} {fmt(SWEEP_VOLTAGE)} {fmt(SWEEP_TIME)}")


def assemble(elements: list[str], f_actual: float, out_scale: float) -> str:
    """Header, elements and the two scopes (source and output marker)."""
    step = min(MAX_TIME_STEP, 1 / (f_actual * SWEEP_DECADE_SPAN * SAMPLES_PER_PERIOD))
    out_index = next(i for i, l in enumerate(elements) if l.startswith("O "))
    lines = [f"$ 1 {fmt(step)} 10 57 5.0", *elements,
             f"o 0 64 0 2 {fmt(SWEEP_VOLTAGE)} 9.765625E-5",
             f"o {out_index} 64 0 2 {fmt(out_scale)} 9.765625E-5"]
    return "\n".join(lines) + "\n"


def res(x1: int, y1: int, x2: int, y2: int, value: float) -> str:
    return f"r {x1} {y1} {x2} {y2} 0 {fmt(value)}"


def cap(x1: int, y1: int, x2: int, y2: int, value: float) -> str:
    return f"c {x1} {y1} {x2} {y2} 0 {fmt(value)} 0.0"


def sallen_key(kind: str, R: float, C: float, f_actual: float, gain: float,
               rg: float | None, rf: float | None, supply: float) -> str:
    """Equal-component Sallen-Key section ('low' or 'high'). R, C are the section's resistor
    and capacitor, `gain` is the achieved non-inverting gain, rg/rf its resistors (None for a
    follower). Low-pass: R series, C to ground, C feedback from the middle node to the output.
    High-pass: the same with R and C swapped."""
    series, shunt = (res, cap) if kind == "low" else (cap, res)
    part = (lambda a, b, c, d: series(a, b, c, d, R if kind == "low" else C))
    shunt_part = (lambda a, b, c, d: shunt(a, b, c, d, C if kind == "low" else R))
    el = [sweep_source(f_actual),
          part(240, 160, 336, 160),
          part(336, 160, 432, 160),
          shunt_part(432, 160, 432, 288),
          "g 432 288 432 320 0",
          "w 432 160 480 160 0",
          "w 336 160 336 96 0",
          shunt_part(336, 96, 624, 96),                     # feedback element, middle node -> output
          "w 624 96 624 176 0",
          amp_line(480, 176, 624, supply),
          "w 480 192 480 240 0",
          "w 624 176 624 240 0"]
    if rf is None:
        el.append("w 480 240 624 240 0")
    else:
        el += [res(480, 240, 624, 240, rf), res(480, 240, 480, 336, rg), "g 480 336 480 368 0"]
    el.append("O 624 176 688 176 0")
    return assemble(el, f_actual, max(SWEEP_VOLTAGE, SWEEP_VOLTAGE * gain))
