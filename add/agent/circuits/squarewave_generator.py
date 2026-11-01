"""Generate a Falstad (CircuitJS) 555-timer square-wave oscillator netlist (legacy format)."""

import math
from typing import NamedTuple, Optional, Tuple

from ._parts import assemble, cap, dc_rail, gnd, index_of, out_marker, res, timer555, wire

# Preferred timing-capacitor values (F), used to pick a capacitor for a requested frequency when the
# caller supplies neither `capacitor` nor `timing_resistor`.
_PREFERRED_CAPACITORS = [
    (10.0, 1e-6),      # < 10 Hz      -> 1 uF
    (1_000.0, 1e-7),   # < 1 kHz      -> 100 nF
    (100_000.0, 1e-9), # < 100 kHz    -> 1 nF
    (float("inf"), 1e-10),  # >= 100 kHz -> 100 pF
]

_MIN_PRACTICAL_R = 1_000.0        # 1 kOhm
_MAX_PRACTICAL_R = 10_000_000.0   # 10 MOhm
DEFAULT_R = 1_000_000.0           # 1 MOhm  (the reference circuit)
DEFAULT_C = 3e-7                  # 300 nF
DEFAULT_RF = 10_000.0             # 10 kOhm (the reference circuit)
SWITCH_OHM = 1.0                  # Falstad's 555 output stage: 1 ohm to Vcc or to ground


class SquareDesign(NamedTuple):
    supply_voltage: float
    R: float            # timing resistor, Vcc to the capacitor node
    Rf: float           # feedback resistor, 555 output to the capacitor node
    C: float
    t_high: float
    t_low: float
    f_hz: float
    duty: float
    notes: tuple


def periods(r: float, rf: float, c: float) -> Tuple[float, float]:
    """(t_high, t_low) of this circuit.

    The capacitor node is fed from Vcc through R and from the 555 output through Rf, and the 555 flips
    at 1/3 and 2/3 of Vcc. Output high: the node heads for Vcc through R || Rf, so
        t_high = (R || Rf) C ln 2.
    Output low: it heads for k Vcc with k = Rf / (R + Rf), again through R || Rf, so
        t_low = (R || Rf) C ln((2/3 - k) / (1/3 - k)).
    """
    req = r * rf / (r + rf)
    k = rf / (r + rf)
    if k >= 1 / 3:
        raise ValueError("the feedback resistor is so large next to the timing resistor that the capacitor "
                         "can never discharge to the 555's lower threshold: the circuit would not oscillate "
                         "(Rf must be well below R)")
    return req * c * math.log(2.0), req * c * math.log((2 / 3 - k) / (1 / 3 - k))


def design(
    supply_voltage: float = 10.0,
    timing_resistor: Optional[float] = None,
    capacitor: Optional[float] = None,
    reset_pullup: float = DEFAULT_RF,
    frequency: Optional[float] = None,
) -> SquareDesign:
    """Resolve the component values and the resulting frequency and duty cycle."""
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
    notes = []
    c = capacitor
    r = timing_resistor
    rf = reset_pullup
    if frequency is not None:
        if r is None:
            r = DEFAULT_R
        period = 1.0 / frequency

        def solve(cc):
            lo, hi = 1e-3 * r, r / 3.0 * (1 - 1e-9)
            if sum(periods(r, hi, cc)) < period or sum(periods(r, lo, cc)) > period:
                return None
            for _ in range(200):
                mid = math.sqrt(lo * hi)
                if sum(periods(r, mid, cc)) < period:
                    lo = mid
                else:
                    hi = mid
            return math.sqrt(lo * hi)

        if c is not None:
            cands = [c]
        else:
            cands = [m * 10.0 ** e for e in range(-12, -3) for m in (1.0, 3.3)]
        best = None
        for cc in cands:
            sol = solve(cc)
            if sol is None or (c is None and not 100.0 <= sol <= r / 10.0):
                continue
            score = abs(math.log10(sol / 1e4))           # prefer a feedback resistor near 10 kohm
            if best is None or score < best[0]:
                best = (score, cc, sol)
        if best is None:
            raise ValueError(f"{frequency:g} Hz cannot be reached with R = {r:g} ohm"
                             f"{'' if c is None else f' and C = {c:g} F'} in this circuit; change the "
                             "capacitor or the timing resistor")
        c, rf = best[1], best[2]
        if abs(rf - reset_pullup) > 1e-9 * rf and reset_pullup != DEFAULT_RF:
            notes.append(f"the feedback resistor was re-solved to {rf:.4g} ohm to hit {frequency:g} Hz "
                         "(the frequency is set by it, not by the timing resistor)")
    else:
        c = DEFAULT_C if c is None else c
        r = DEFAULT_R if r is None else r
    if r < _MIN_PRACTICAL_R or r > _MAX_PRACTICAL_R:
        notes.append(f"the timing resistor ({r:.4g} ohm) is outside the practical 1 kohm to 10 Mohm range")
    th, tl = periods(r, rf, c)
    return SquareDesign(supply_voltage, r, rf, c, th, tl, 1.0 / (th + tl), th / (th + tl), tuple(notes))


def square_wave_generator(
    supply_voltage: float = 10.0,
    timing_resistor: Optional[float] = None,
    capacitor: Optional[float] = None,
    reset_pullup: float = DEFAULT_RF,
    frequency: Optional[float] = None,
) -> Tuple[str, str]:
    """Generate a Falstad-format 555-timer square-wave oscillator (0 V to the supply, about 50% duty).

    A single 555 whose threshold/trigger pins sit on a capacitor node that is fed from Vcc through the
    timing resistor and ALSO from the 555's own output through a feedback resistor (the discharge pin is
    not used). With the output high the capacitor charges toward Vcc, with it low it discharges through the
    feedback resistor, so the frequency is set mainly by the feedback resistor:
        f = 1 / (t_high + t_low),  t_high = (R || Rf) C ln 2,  t_low = (R || Rf) C ln((2/3 - k)/(1/3 - k)),
        k = Rf / (R + Rf).
    With the defaults (R = 1 Mohm, Rf = 10 kohm, C = 300 nF) this is about 240 Hz at about 50% duty.
    `reset_pullup` is that feedback resistor (the name comes from the original export). Give `frequency` to
    have the feedback resistor solved for it. This circuit generates its own signal and has no signal input,
    so it can only be the FIRST stage of a cascade.

    Args:
        supply_voltage: Vcc rail, in volts. Defaults to 10 V.
        timing_resistor: Resistor from Vcc to the capacitor node, in ohms. Default 1 Mohm.
        capacitor: Timing capacitor from that node to ground, in farads. Default 300 nF (or chosen from
            `frequency`).
        reset_pullup: Feedback resistor from the 555 output to the capacitor node, in ohms. Default 10 kohm.
        frequency: Target oscillation frequency in hertz; the feedback resistor is solved for it.

    Returns:
        A (circuit_text, note) tuple. `circuit_text` is Falstad circuit text ready to load into circuitjs1;
        `note` states the frequency and duty cycle the circuit will have.

    Raises:
        ValueError: If an argument is not positive, the frequency cannot be reached, or the feedback
            resistor is too large for the circuit to oscillate.
    """
    d = design(supply_voltage, timing_resistor, capacitor, reset_pullup, frequency)
    el = [
        wire(112, 192, 112, 224),
        wire(112, 224, 176, 224),
        cap(112, 224, 112, 288, d.C, d.supply_voltage / 3.0),
        gnd(112, 288, 112, 304),
        res(112, 192, 112, 64, d.R),
        wire(112, 64, 240, 64),
        dc_rail(112, 64, 80, 64, d.supply_voltage),
        out_marker(352, 160, 416, 160),
        timer555(176, 96, 192, 96, 6, d.supply_voltage),
        wire(240, 64, 304, 64),
        wire(304, 64, 304, 128),
        wire(352, 160, 304, 160),
        wire(352, 160, 352, 32),
        res(352, 32, 160, 32, d.Rf),
        wire(160, 32, 160, 192),
        wire(112, 192, 160, 192),
        wire(160, 192, 176, 192),
        gnd(272, 256, 272, 272),
    ]
    note = (f"Frequency about {d.f_hz:.4g} Hz at about {d.duty:.1%} duty (high {d.t_high * 1e3:.4g} ms, low "
            f"{d.t_low * 1e3:.4g} ms); the output swings 0 V to {d.supply_voltage:g} V. The frequency is set mainly "
            f"by the feedback resistor ({d.Rf:.4g} ohm) and the capacitor, not by the timing resistor.")
    if d.notes:
        note += " " + "; ".join(n[0].upper() + n[1:] for n in d.notes) + "."
    step = min(5e-6, 1.0 / (400 * d.f_hz))
    return assemble(el, step, [(index_of(el, "O"), 2 * d.supply_voltage, 64)]), note


calculate = design   # public: used by the cascade's oscillator model
