def binary_counter(bits: int) -> str:
    """Generate an N-bit ripple binary counter as Falstad circuit text.

    Verified against 4-bit, 6-bit, and 12-bit reference circuits (ported
    1:1 from the original Java generator's layout constants).

    Args:
        bits: Number of counter bits. Must be >= 1.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.
    """
    if bits < 1:
        raise ValueError("bits must be >= 1")

    # ── Layout constants (same meaning as the Java version) ────────────
    Y = 208
    STEP = 128
    Q_OFF = 96
    CLK_DY = 32
    K_DY = 64
    VCC_DY = 112
    PROBE_RIGHT_X = 656

    x1_first = 528 - (bits - 1) * STEP

    lines: list[str] = []

    # 1. Header
    lines.append("$ 1 5.0E-6 10.20027730826997 50 5.0")

    # 2. JK flip-flops
    for i in range(bits):
        x1 = x1_first + i * STEP
        bw = 48 if i == 0 else (16 if i == bits - 1 else 32)
        lines.append(f"156 {x1} {Y} {x1 + bw} {Y} 0 5.0")

    # 3. Q -> CLK inter-FF wires
    for i in range(bits - 1):
        qx = x1_first + i * STEP + Q_OFF
        clk_x = x1_first + (i + 1) * STEP
        lines.append(f"w {qx} {Y} {qx} {Y + CLK_DY} 0")
        lines.append(f"w {qx} {Y + CLK_DY} {clk_x} {Y + CLK_DY} 0")

    # 4. /Q feedback + VCC bus wiring
    _append_style_a(lines, x1_first, Y, K_DY, VCC_DY)
    if bits >= 2:
        _append_style_a(lines, x1_first + STEP, Y, K_DY, VCC_DY)

    for i in range(2, bits - 1, 2):
        x1_l = x1_first + i * STEP
        x1_r = x1_first + (i + 1) * STEP
        rx = x1_l + Q_OFF + 16
        lx = x1_l - 16

        lines.append(f"w {rx} {Y} {rx} {Y + K_DY} 0")
        lines.append(f"w {rx} {Y + K_DY} {x1_r} {Y + K_DY} 0")
        lines.append(f"w {rx} {Y + K_DY} {rx} {Y + VCC_DY} 0")
        lines.append(f"w {lx} {Y + VCC_DY} {lx} {Y + K_DY} 0")
        lines.append(f"w {lx} {Y + K_DY} {x1_l} {Y + K_DY} 0")
        lines.append(f"w {lx} {Y + K_DY} {lx} {Y} 0")
        lines.append(f"w {lx} {Y} {x1_l} {Y} 0")
        lines.append(f"w {rx} {Y} {x1_r} {Y} 0")

    if bits >= 3 and bits % 2 == 1:
        _append_style_a(lines, x1_first + (bits - 1) * STEP, Y, K_DY, VCC_DY)

    # 5. VCC bus: connect all taps along Y + VCC_DY
    taps = set()
    taps.add(x1_first - 16)
    if bits >= 2:
        taps.add(x1_first + STEP - 16)
    for i in range(2, bits - 1, 2):
        x1_l = x1_first + i * STEP
        taps.add(x1_l - 16)
        taps.add(x1_l + Q_OFF + 16)
    if bits >= 3 and bits % 2 == 1:
        taps.add(x1_first + (bits - 1) * STEP - 16)

    tap_arr = sorted(taps)
    for a, b in zip(tap_arr, tap_arr[1:]):
        lines.append(f"w {a} {Y + VCC_DY} {b} {Y + VCC_DY} 0")

    # 6. Clock source (200 Hz square wave, 2.5 V)
    lines.append(
        f"R {x1_first} {Y + CLK_DY} {x1_first - 48} {Y + CLK_DY} 1 2 200.0 2.5 2.5"
    )

    # 7. VCC supply (+5 V DC)
    vcc_x = x1_first - 16
    lines.append(f"R {vcc_x} {Y + VCC_DY} {vcc_x - 48} {Y + VCC_DY} 0 0 40.0 5.0 0.0")

    # 8. Oscilloscope probe wires + M markers
    for i in range(bits):
        qx = x1_first + i * STEP + Q_OFF
        probe_y = Y - (bits - i) * 32
        lines.append(f"w {qx} {Y} {qx} {probe_y} 0")
        lines.append(f"M {qx} {probe_y} {PROBE_RIGHT_X} {probe_y} 2")

    # 9. Oscilloscope trace definitions
    for i in range(bits):
        lines.append(f"o {i} 64 0 6 5.0 9.765625E-5 0")

    return "\n".join(lines) + "\n"


def _append_style_a(lines: list[str], x1: int, y: int, k_dy: int, vcc_dy: int) -> None:
    """Left-side stub wiring for a single flip-flop (mirrors appendStyleA)."""
    lx = x1 - 16
    lines.append(f"w {x1} {y} {lx} {y} 0")
    lines.append(f"w {lx} {y} {lx} {y + k_dy} 0")
    lines.append(f"w {lx} {y + k_dy} {x1} {y + k_dy} 0")
    lines.append(f"w {lx} {y + k_dy} {lx} {y + vcc_dy} 0")


if __name__ == "__main__":
    import sys

    bits = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    print(f"=== {bits}-bit Binary Counter ===")
    print(binary_counter(bits))
