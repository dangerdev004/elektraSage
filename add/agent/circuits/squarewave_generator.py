from typing import Optional, Tuple


# Preferred timing-capacitor values (F), used to pick a capacitor for a
# requested frequency when the caller supplies neither `capacitor` nor
# `timing_resistor`. Chosen so the solved resistor tends to land in a
# practical ~1 kOhm - 10 MOhm range across the corresponding frequency band.
_PREFERRED_CAPACITORS = [
    (10.0, 1e-6),      # < 10 Hz      -> 1 uF
    (1_000.0, 1e-7),   # < 1 kHz      -> 100 nF
    (100_000.0, 1e-9), # < 100 kHz    -> 1 nF
    (float("inf"), 1e-10),  # >= 100 kHz -> 100 pF
]

_MIN_PRACTICAL_R = 1_000.0        # 1 kOhm
_MAX_PRACTICAL_R = 10_000_000.0   # 10 MOhm


def square_wave_generator(
    supply_voltage: float = 10.0,
    timing_resistor: Optional[float] = None,
    capacitor: Optional[float] = None,
    reset_pullup: float = 10_000.0,
    frequency: Optional[float] = None,
) -> Tuple[str, str]:
    """Generate a 555-timer square-wave (astable) oscillator as Falstad circuit text.

    Layout matches the reference circuit: a single 555 Timer with `dis`
    wired to the same node as `tr`/`th` (not through a separate discharge
    resistor). Because of that, the timing capacitor charges through
    `timing_resistor` but discharges almost instantly through the 555's
    internal transistor, giving a sawtooth capacitor waveform and an
    output that is fixed near-100% high with brief low pulses. Duty cycle
    is NOT independently tunable in this topology — see the returned
    note.

    Component values are resolved with minimal-input-friendly defaults:
    any of `timing_resistor`, `capacitor` you supply are used exactly as
    given. For any of the two you leave as None, `frequency` (if given)
    is used to derive it from f ~= 1.44 / (R * C); if neither is given
    and `frequency` is given, a capacitor is picked from a preferred-value
    table sized to the requested frequency and the resistor is solved
    from it. If `frequency` is also None, both fall back to the baseline
    defaults (1 MOhm, 300 nF) matching the reference circuit.

    Args:
        supply_voltage: Vcc rail, in volts. Defaults to 10 V.
        timing_resistor: Charging resistor from Vcc to the RC node, in
            ohms. If None, derived from `frequency` or defaulted.
        capacitor: Timing capacitor from the RC node to ground, in
            farads. If None, derived from `frequency` or defaulted.
        reset_pullup: Resistor tying `rst` to Vcc, in ohms. Defaults to
            10 kOhm.
        frequency: Target oscillation frequency, in hertz. Only consulted
            to fill in `timing_resistor` and/or `capacitor` when they are
            left as None; ignored (aside from a consistency note) if both
            are already given explicitly.

    Returns:
        A (circuit_text, note) tuple. `circuit_text` is Falstad circuit
        text ready to load into circuitjs1. `note` always explains the
        fixed near-100% duty cycle of this topology, and additionally
        flags when a solved `timing_resistor` falls outside a practical
        ~1 kOhm-10 MOhm range.

    Raises:
        ValueError: If `supply_voltage`, `reset_pullup`, an explicitly
            given `timing_resistor`/`capacitor`, or `frequency` is not a
            positive number.
    """
    if supply_voltage <= 0:
        raise ValueError(f"supply_voltage must be > 0, got {supply_voltage}")
    if reset_pullup <= 0:
        raise ValueError(f"reset_pullup must be > 0, got {reset_pullup}")
    if timing_resistor is not None and timing_resistor <= 0:
        raise ValueError(f"timing_resistor must be > 0, got {timing_resistor}")
    if capacitor is not None and capacitor <= 0:
        raise ValueError(f"capacitor must be > 0, got {capacitor}")
    if frequency is not None and frequency <= 0:
        raise ValueError(f"frequency must be > 0, got {frequency}")

    # ── Baseline defaults (match the reference circuit exactly) ────────
    DEFAULT_R = 1_000_000.0  # 1 MOhm
    DEFAULT_C = 3e-7         # 300 nF

    notes = []

    # ── Resolve timing_resistor / capacitor ─────────────────────────────
    if timing_resistor is not None and capacitor is not None:
        # Both given explicitly: used as-is. If frequency was also given,
        # just note the mismatch rather than overriding either value.
        if frequency is not None:
            actual_f = 1.44 / (timing_resistor * capacitor)
            if abs(actual_f - frequency) / frequency > 0.05:
                notes.append(
                    f"Note: with the given timing_resistor and capacitor the "
                    f"actual frequency is ~{actual_f:.4g} Hz, not the "
                    f"requested {frequency:.4g} Hz (both explicit values were "
                    f"kept as given)."
                )
        resolved_r = timing_resistor
        resolved_c = capacitor
    elif timing_resistor is not None:
        # R given, solve C from frequency (or default C if no frequency).
        resolved_r = timing_resistor
        resolved_c = (1.44 / (frequency * resolved_r)) if frequency is not None else DEFAULT_C
    elif capacitor is not None:
        # C given, solve R from frequency (or default R if no frequency).
        resolved_c = capacitor
        resolved_r = (1.44 / (frequency * resolved_c)) if frequency is not None else DEFAULT_R
    elif frequency is not None:
        # Neither given: pick C from the preferred-value table, solve R.
        for threshold, cap_value in _PREFERRED_CAPACITORS:
            if frequency < threshold:
                resolved_c = cap_value
                break
        resolved_r = 1.44 / (frequency * resolved_c)
    else:
        # Nothing given at all: baseline defaults.
        resolved_r = DEFAULT_R
        resolved_c = DEFAULT_C

    if resolved_r < _MIN_PRACTICAL_R or resolved_r > _MAX_PRACTICAL_R:
        notes.append(
            f"Warning: solved timing_resistor ({resolved_r:.4g} ohm) falls "
            f"outside the practical ~{_MIN_PRACTICAL_R:.0f} ohm - "
            f"{_MAX_PRACTICAL_R:.0f} ohm range; consider fixing capacitor "
            f"or frequency to a different value."
        )

    notes.append(
        "Note: dis is tied to the tr/th node (no separate discharge "
        "resistor), so the capacitor discharges almost instantly through "
        "the 555's internal transistor. Duty cycle is fixed near-100% "
        "high with brief low pulses and is not independently tunable in "
        "this topology."
    )

    # ── Layout constants (from the reference circuit, all fixed) ───────
    lines = [
        '<cir f="1" ts="0.000005" ic="5.023272298708815" cb="64" pb="50" vr="7" mts="5e-11">',
        '  <w x="112 192 112 224" f="0"/>',
        '  <w x="112 224 176 224" f="0"/>',
        f'  <c x="112 224 112 288" f="0" c="{resolved_c}" iv="0.001" sr="0" vd="6.1877519531796015"/>',
        '  <g x="112 288 112 304" f="0"/>',
        f'  <r x="112 192 112 64" f="0" r="{resolved_r}"/>',
        '  <w x="112 64 240 64" f="0"/>',
        f'  <R x="112 64 80 64" f="0" wf="0" maxv="{supply_voltage}"/>',
        '  <O x="352 160 416 160" f="0" sc="0"/>',
        '  <Timer x="176 96 192 96" f="6" v5="9.999618813313987"/>',
        '  <w x="240 64 304 64" f="0"/>',
        '  <w x="304 64 304 128" f="0"/>',
        '  <w x="352 160 304 160" f="0"/>',
        '  <w x="352 160 352 32" f="0"/>',
        f'  <r x="352 32 160 32" f="0" r="{reset_pullup}"/>',
        '  <w x="160 32 160 192" f="0"/>',
        '  <w x="112 192 160 192" f="0"/>',
        '  <w x="160 192 176 192" f="0"/>',
        '  <g x="272 256 272 272" f="0"/>',
        '</cir>',
    ]

    circuit_text = "\n".join(lines) + "\n"
    note = " ".join(notes)

    return circuit_text, note


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Generate a 555-timer square-wave oscillator as Falstad circuit text."
    )
    parser.add_argument(
        "--supply-voltage", type=float, default=10.0,
        help="Vcc rail, in volts (default: 10)",
    )
    parser.add_argument(
        "--timing-resistor", type=float, default=None,
        help="Charging resistor, in ohms. Derived from --frequency if omitted.",
    )
    parser.add_argument(
        "--capacitor", type=float, default=None,
        help="Timing capacitor, in farads. Derived from --frequency if omitted.",
    )
    parser.add_argument(
        "--reset-pullup", type=float, default=10_000.0,
        help="Resistor tying rst to Vcc, in ohms (default: 10000)",
    )
    parser.add_argument(
        "--frequency", type=float, default=None,
        help="Target oscillation frequency, in hertz. Used to fill in "
             "--timing-resistor/--capacitor when they're omitted.",
    )
    parser.add_argument(
        "-o", "--output", type=str, default=None,
        help="Write the circuit text to this file instead of stdout.",
    )

    args = parser.parse_args()

    try:
        circuit, note = square_wave_generator(
            supply_voltage=args.supply_voltage,
            timing_resistor=args.timing_resistor,
            capacitor=args.capacitor,
            reset_pullup=args.reset_pullup,
            frequency=args.frequency,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print("=== 555 Square Wave Generator ===", file=sys.stderr)
    print(note, file=sys.stderr)

    if args.output:
        with open(args.output, "w") as f:
            f.write(circuit)
        print(f"Circuit written to {args.output}", file=sys.stderr)
    else:
        print(circuit)
