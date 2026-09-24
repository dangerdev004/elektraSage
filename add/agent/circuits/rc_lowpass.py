import math
def rc_lowpass(cutoff_frequency: float, resistance: float) -> str:
    """Generate a Falstad-format RC low-pass filter circuit.

    Args:
        cutoff_frequency: Desired cutoff frequency in Hz.
        resistance: Resistance value in ohms.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.
    """
    if cutoff_frequency <= 0:
        raise ValueError("cutoff_frequency must be > 0")
    if resistance <= 0:
        raise ValueError("resistance must be > 0")

    capacitance = 1 / (2 * math.pi * cutoff_frequency * resistance)

    return (
        "$ 1 5.0E-6 10 57 5.0\n"
        "v 96 256 96 112 0 1 1000.0 0.001 0.0\n"
        "g 96 256 96 304 0\n"
        "w 192 208 192 256 0\n"
        "a 192 192 336 192 1\n"
        "w 336 192 336 256 0\n"
        f"r 96 256 192 256 0 {resistance:f}\n"
        f"c  336 256 336 304 0 {capacitance:f}\n"
        "w 336 304 192 304 0\n"
        "w 192 304 192 256 0\n" 
         "w 96 112 192 112 0\n"
        "w 192 112 192 176 0\n"
        "O 336 192 400 192 0\n"
        "o 0 64 0 2 5.0 9.765625E-5\n"
        "o 9 64 0 2 10.0 9.765625E-5\n"
    )