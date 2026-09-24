from typing import Optional, Tuple


# Fixed trigger network taken from the exported Falstad circuit (100 ohm +
# 10 uF RC differentiator feeding a pushbutton/logic input). Not tunable.
_TRIGGER_R = 100
_TRIGGER_C = 0.00001

# Preferred timing-capacitor values (F), used to pick a capacitor for a
# requested pulse width when the caller supplies neither `timing_resistor`
# nor `capacitor`. Chosen so the solved resistor tends to land in a
# practical ~1 kOhm - 10 MOhm range across each pulse-width band.
_PREFERRED_CAPACITORS = [
    (1e-4, 1e-9),           # < 100 us   -> 1 nF
    (1e-2, 1e-7),           # < 10 ms    -> 100 nF
    (1.0, 1e-6),            # < 1 s      -> 1 uF
    (100.0, 1e-5),          # < 100 s    -> 10 uF
    (float("inf"), 1e-4),   # >= 100 s   -> 100 uF
]

_MIN_PRACTICAL_R = 1_000.0        # 1 kOhm
_MAX_PRACTICAL_R = 10_000_000.0   # 10 MOhm

_K = 1.1  # 555 monostable constant: T = 1.1 * R * C


def monostable_555_generator(
    supply_voltage: float = 5.0,
    timing_resistor: Optional[float] = None,
    capacitor: Optional[float] = None,
    pulse_width: Optional[float] = None,
) -> Tuple[str, str]:
    """Generate a 555-timer monostable (one-shot) circuit as Falstad circuit text.

    Layout matches the reference circuit: a single 555 Timer whose timing
    resistor runs from Vcc to the threshold/discharge node and whose timing
    capacitor runs from that node to ground. A fixed trigger network
    (100 ohm + 10 uF RC differentiator driven by a pushbutton logic input)
    is kept exactly as exported and is not tunable. The timing capacitor's
    initial voltage is reset to 0 so the simulation starts clean.

    The output pulse width follows T = 1.1 * R * C.

    Component values are resolved with minimal-input-friendly defaults:
    any of `timing_resistor`, `capacitor` you supply are used exactly as
    given. For whichever you leave as None, `pulse_width` (if given) is
    used to derive it; if neither is given but `pulse_width` is, a
    capacitor is picked from a preferred-value table sized to the requested
    pulse width and the resistor is solved from it. If `pulse_width` is
    also None, the missing values fall back to baseline defaults
    (100 kOhm, 10 uF -> ~1.1 s pulse).

    Args:
        supply_voltage: Vcc rail, in volts. Defaults to 5 V.
        timing_resistor: Timing resistor from Vcc to the RC node, in ohms.
            If None, derived from `pulse_width` or defaulted.
        capacitor: Timing capacitor from the RC node to ground, in farads.
            If None, derived from `pulse_width` or defaulted.
        pulse_width: Target output HIGH pulse duration, in seconds. Only
            consulted to fill in `timing_resistor` and/or `capacitor` when
            they are left as None; ignored (aside from a consistency note)
            if both are already given explicitly.

    Returns:
        A (circuit_text, note) tuple. `circuit_text` is Falstad circuit
        text ready to load into circuitjs1. `note` reports the resolved
        R, C and resulting pulse width, and flags when the resistor falls
        outside a practical ~1 kOhm-10 MOhm range or when explicit values
        don't match the requested pulse width.

    Raises:
        ValueError: If `supply_voltage`, an explicitly given
            `timing_resistor`/`capacitor`, or `pulse_width` is not a
            positive number.
    """
    if supply_voltage <= 0:
        raise ValueError(f"supply_voltage must be > 0, got {supply_voltage}")
    if timing_resistor is not None and timing_resistor <= 0:
        raise ValueError(f"timing_resistor must be > 0, got {timing_resistor}")
    if capacitor is not None and capacitor <= 0:
        raise ValueError(f"capacitor must be > 0, got {capacitor}")
    if pulse_width is not None and pulse_width <= 0:
        raise ValueError(f"pulse_width must be > 0, got {pulse_width}")

    # ── Baseline defaults ──────────────────────────────────────────────
    DEFAULT_R = 100_000.0  # 100 kOhm
    DEFAULT_C = 1e-5       # 10 uF

    notes = []

    # ── Resolve timing_resistor / capacitor ─────────────────────────────
    if timing_resistor is not None and capacitor is not None:
        resolved_r = timing_resistor
        resolved_c = capacitor
        if pulse_width is not None:
            actual_t = _K * resolved_r * resolved_c
            if abs(actual_t - pulse_width) / pulse_width > 0.05:
                notes.append(
                    f"Note: with the given timing_resistor and capacitor the "
                    f"actual pulse width is ~{actual_t:.4g} s, not the "
                    f"requested {pulse_width:.4g} s (both explicit values "
                    f"were kept as given)."
                )
    elif timing_resistor is not None:
        resolved_r = timing_resistor
        resolved_c = (pulse_width / (_K * resolved_r)) if pulse_width is not None else DEFAULT_C
    elif capacitor is not None:
        resolved_c = capacitor
        resolved_r = (pulse_width / (_K * resolved_c)) if pulse_width is not None else DEFAULT_R
    elif pulse_width is not None:
        for threshold, cap_value in _PREFERRED_CAPACITORS:
            if pulse_width < threshold:
                resolved_c = cap_value
                break
        resolved_r = pulse_width / (_K * resolved_c)
    else:
        resolved_r = DEFAULT_R
        resolved_c = DEFAULT_C

    resolved_t = _K * resolved_r * resolved_c

    if resolved_r < _MIN_PRACTICAL_R or resolved_r > _MAX_PRACTICAL_R:
        notes.append(
            f"Warning: timing_resistor ({resolved_r:.4g} ohm) falls "
            f"outside the practical ~{_MIN_PRACTICAL_R:.0f} ohm - "
            f"{_MAX_PRACTICAL_R:.0f} ohm range; consider fixing capacitor "
            f"or pulse_width to a different value."
        )

    notes.insert(
        0,
        f"Resolved values: R = {resolved_r:.6g} ohm, C = {resolved_c:.6g} F, "
        f"pulse width T = 1.1*R*C = {resolved_t:.6g} s.",
    )
    notes.append(
        "Note: the trigger network (100 ohm + 10 uF RC with pushbutton "
        "input) is fixed; click the pushbutton in the simulator to fire "
        "the one-shot."
    )

    # ── Layout constants (from the reference circuit, all fixed) ───────
    lines = [
        '<cir f="1" ts="0.000005" ic="10.20027730826997" cb="56" pb="50" vr="5" mts="5e-11">',
        '  <Timer x="208 144 320 144" f="4"/>',
        '  <w x="208 176 208 272" f="0"/>',
        '  <w x="208 176 176 176" f="0"/>',
        '  <w x="208 240 128 240" f="0"/>',
        '  <w x="176 176 176 272" f="0"/>',
        f'  <c x="176 272 176 320" f="0" c="{resolved_c:.10g}" iv="0.001" sr="0" vd="0"/>',
        '  <g x="176 320 176 336" f="0"/>',
        f'  <r x="176 176 176 112" f="0" r="{resolved_r:.12g}"/>',
        '  <w x="176 112 272 112" f="0"/>',
        f'  <R x="128 112 48 112" f="0" wf="0" maxv="{supply_voltage:g}"/>',
        '  <O x="336 208 400 208" f="0" sc="0"/>',
        f'  <r x="128 112 128 240" f="0" r="{_TRIGGER_R:g}"/>',
        '  <w x="128 112 176 112" f="0"/>',
        f'  <c x="128 240 80 240" f="0" c="{_TRIGGER_C:.10g}" iv="0.001" sr="0" vd="0"/>',
        '  <L x="80 240 48 240" f="0" p="1" mm="true"/>',
        '  <g x="304 304 304 320" f="0"/>',
        '  <w x="272 112 336 112" f="0"/>',
        '  <w x="336 112 336 176" f="0"/>',
        '  <o en="14" sp="64" f="x6" p="0">',
        '    <p v="0" sc="5"/>',
        '    <p v="3" sc="0.00009765625"/>',
        '  </o>',
        '  <o en="10" sp="64" f="x6" p="0">',
        '    <p v="0" sc="0.0000762939453125"/>',
        '  </o>',
        '  <h t="2" i1="7" i2="5"/>',
        '</cir>',
    ]

    circuit_text = "\n".join(lines) + "\n"
    note = " ".join(notes)

    return circuit_text, note


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Generate a 555-timer monostable circuit as Falstad circuit text."
    )
    parser.add_argument(
        "--supply-voltage", type=float, default=5.0,
        help="Vcc rail, in volts (default: 5)",
    )
    parser.add_argument(
        "--timing-resistor", type=float, default=None,
        help="Timing resistor, in ohms. Derived from --pulse-width if omitted.",
    )
    parser.add_argument(
        "--capacitor", type=float, default=None,
        help="Timing capacitor, in farads. Derived from --pulse-width if omitted.",
    )
    parser.add_argument(
        "--pulse-width", type=float, default=None,
        help="Target output pulse width, in seconds. Used to fill in "
             "--timing-resistor/--capacitor when they're omitted.",
    )
    parser.add_argument(
        "-o", "--output", type=str, default=None,
        help="Write the circuit text to this file instead of stdout.",
    )

    args = parser.parse_args()

    try:
        circuit, note = monostable_555_generator(
            supply_voltage=args.supply_voltage,
            timing_resistor=args.timing_resistor,
            capacitor=args.capacitor,
            pulse_width=args.pulse_width,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print("=== 555 Monostable ===", file=sys.stderr)
    print(note, file=sys.stderr)

    if args.output:
        with open(args.output, "w") as f:
            f.write(circuit)
        print(f"Circuit written to {args.output}", file=sys.stderr)
    else:
        print(circuit)
