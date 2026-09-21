import math

_CAPS = [1e-12, 10e-12, 100e-12, 1e-9, 10e-9, 100e-9, 1e-6, 10e-6]
_GAIN = 30


def _solve_rc(freq_hz: float) -> tuple[float, float, float]:
    """Pick a capacitor from the preferred list so R lands in [1k, 100k]."""
    for C in _CAPS:
        R = 1 / (2 * math.pi * math.sqrt(6) * freq_hz * C)
        if 1e3 <= R <= 100e3:
            return R, _GAIN * R, C

    # Fallback: no preferred cap gives an R in range, use 1uF anyway.
    C = 1e-6
    R = 1 / (2 * math.pi * math.sqrt(6) * freq_hz * C)
    return R, _GAIN * R, C


def rc_phaseshift(frequency_hz: float) -> str:
    """Generate a Falstad-format RC phase-shift oscillator circuit.

    Args:
        frequency_hz: Desired oscillation frequency in Hz.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.
    """
    R, Rf, C = _solve_rc(frequency_hz)

    return (
        "$ 1 0.000015625 3.046768661252054 58 5 50\n"
        f"c 144 368 208 368 0 {C:e} -2.544137674334456\n"
        f"c 208 368 272 368 0 {C:e} -3.308245117520446\n"
        f"c 272 368 336 368 0 {C:e} -0.9716832694680744\n"
        f"r 336 368 400 368 0 {R:f}\n"
        f"r 208 368 208 448 0 {R:f}\n"
        f"r 272 368 272 448 0 {R:f}\n"
        "g 208 448 208 464 0\n"
        "g 272 448 272 464 0\n"
        "a 400 384 496 384 0 15 -15 1000000 0.00006596531227299938 0\n"
        "w 400 368 400 320 0\n"
        f"r 400 320 496 320 0 {Rf:f}\n"
        "w 496 320 496 384 0\n"
        "w 496 384 512 384 0\n"
        "w 512 384 512 288 0\n"
        "w 512 288 144 288 0\n"
        "w 144 288 144 368 0\n"
        "g 400 400 400 448 0\n"
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python rc_phaseshift.py <frequency>")
        raise SystemExit(1)

    freq = float(sys.argv[1])
    netlist = rc_phaseshift(freq)
    print("Generated Netlist:\n")
    print(netlist)
