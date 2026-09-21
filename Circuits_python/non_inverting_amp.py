def non_inverting_amp(gain: float) -> str:
    """Generate a Falstad-format non-inverting op-amp circuit.

    Args:
        gain: Desired voltage gain (Vout / Vin).

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.
    """
    R = 1000.0
    Rf = (gain - 1) * R

    return (
        "$ 1 5.0E-6 10 57 5.0\n"
        "v 96 256 96 112 0 1 1000.0 0.001 0.0\n"
        "g 96 256 96 304 0\n"
        "w 192 208 192 256 0\n"
        "a 192 192 336 192 1\n"
        "w 336 192 336 256 0\n"
        f"r 192 256 336 256 0 {Rf:f}\n"
        f"r 96 256 192 256 0 {R:f}\n"
        "w 96 112 192 112 0\n"
        "w 192 112 192 176 0\n"
        "O 336 192 400 192 0\n"
        "o 0 64 0 2 5.0 9.765625E-5\n"
        "o 9 64 0 2 10.0 9.765625E-5\n"
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python non_inverting_amp.py <gain>")
        raise SystemExit(1)

    netlist = non_inverting_amp(float(sys.argv[1]))
    print("Generated Netlist:\n")
    print(netlist)
