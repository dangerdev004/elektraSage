"""Snap an arbitrary capacitance to the nearest standard E12 value."""

import math

# One decade of the E12 series; the pattern repeats every power of ten.
E12 = (1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2)


def capacitors_approximation(capacitance: float) -> float:
    """Approximate a given capacitance to the closest standard E12 value.

    Nearest means smallest abs(standard - capacitance), which is equivalent to
    the smallest percentage error against the target.

    Args:
        capacitance: The capacitance value in farads (finite and > 0).

    Returns:
        The closest standard capacitance value in farads.

    Raises:
        ValueError: If capacitance is not a finite number greater than 0.
    """
    if not math.isfinite(capacitance) or capacitance <= 0:
        raise ValueError("capacitance must be a finite value > 0")

    decade = math.floor(math.log10(capacitance))
    # Include the next decade so e.g. 9.7 nF can snap up to 10 nF.
    # float(f"{m}e{e}") parses to the same double as the literal (4.7e-06),
    # so results have no float noise like 4.7000000000000003e-06.
    candidates = [
        float(f"{m}e{e}") 
        for e in (decade, decade + 1) 
        for m in E12
    ]
    return min(candidates, key=lambda v: abs(v - capacitance))