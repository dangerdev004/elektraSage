"""Snap an arbitrary resistance to the nearest standard E24 value."""

import math

# One decade of the E24 series; the pattern repeats every power of ten.
E24 = (
    1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
    3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1,
)


def resistors_approximation(resistance: float) -> float:
    """Approximate a given resistance to the closest standard E24 value.

    Nearest means smallest |standard - resistance|, which is equivalent to
    the smallest percentage error against the target.

    Args:
        resistance: The resistance value in ohms (finite and > 0).

    Returns:
        The closest standard resistance value in ohms.

    Raises:
        ValueError: If resistance is not a finite number greater than 0.
    """
    if not math.isfinite(resistance) or resistance <= 0:
        raise ValueError("resistance must be a finite value > 0")

    decade = math.floor(math.log10(resistance))
    # Include the next decade so e.g. 9.7 kOhm can snap up to 10 kOhm.
    # float(f"{m}e{e}") parses to the same double as the literal (4.7e+03),
    # so results have no float noise like 4700.000000000001.
    candidates = [float(f"{m}e{e}") for e in (decade, decade + 1) for m in E24]
    return min(candidates, key=lambda v: abs(v - resistance))