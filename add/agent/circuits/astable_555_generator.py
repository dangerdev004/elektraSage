"""Generate a Falstad (CircuitJS) classic 555 astable (Ra, Rb, C) as legacy circuit text."""

import math
from typing import NamedTuple, Optional, Tuple

from ._parts import assemble, cap, dc_rail, gnd, index_of, out_marker, res, timer555, wire

LN2 = math.log(2.0)
DISCHARGE_OHM = 10.0          # Falstad's 555 pulls the discharge pin to ground through 10 ohm
_MIN_PRACTICAL_R = 1_000.0
_MAX_PRACTICAL_R = 10_000_000.0


class AstableDesign(NamedTuple):
    supply_voltage: float
    Ra: float
    Rb: float
    C: float
    t_high: float
    t_low: float
    f_hz: float
    duty: float
    notes: tuple


def timing(ra: float, rb: float, c: float) -> Tuple[float, float]:
    """(t_high, t_low): charge through Ra+Rb, discharge through Rb (plus the 10 ohm switch)."""
    return LN2 * (ra + rb) * c, LN2 * (rb + DISCHARGE_OHM) * c


def design(supply_voltage: float = 5.0, ra_ohms: Optional[float] = None, rb_ohms: Optional[float] = None,
           capacitor: Optional[float] = None, frequency: Optional[float] = None,
           duty_cycle: Optional[float] = None) -> AstableDesign:
    for name, v in (("supply_voltage", supply_voltage), ("ra_ohms", ra_ohms), ("rb_ohms", rb_ohms),
                    ("capacitor", capacitor), ("frequency", frequency)):
        if v is not None and v <= 0:
            raise ValueError(f"{name} must be > 0, got {v}")
    if duty_cycle is not None and not 0.5 < duty_cycle < 1.0:
        raise ValueError(f"duty_cycle must be between 0.5 and 1 (exclusive), got {duty_cycle}: a 555 astable's "
                         "output is high at least as long as it is low")
    notes = []
    if ra_ohms is not None and rb_ohms is not None and capacitor is not None:
        ra, rb, c = ra_ohms, rb_ohms, capacitor
        if frequency is not None or duty_cycle is not None:
            notes.append("frequency and duty_cycle were ignored because Ra, Rb and C were all given")
    else:
        f = 1000.0 if frequency is None else frequency
        d = 0.6 if duty_cycle is None else duty_cycle
        period = 1.0 / f
        if capacitor is None:
            best = None
            for e in range(-11, -4):
                for m in (1.0, 2.2, 4.7):
                    cc = m * 10.0 ** e
                    rb_, ra_ = (1 - d) * period / (LN2 * cc), (2 * d - 1) * period / (LN2 * cc)
                    if ra_ < _MIN_PRACTICAL_R:
                        continue
                    score = abs(math.log10(rb_ / 1e4))
                    if best is None or score < best[0]:
                        best = (score, cc)
            if best is None:
                raise ValueError("no capacitor value gives a practical Ra for this frequency and duty cycle; "
                                 "give the resistors and capacitor directly")
            c = best[1]
        else:
            c = capacitor
        rb = (1 - d) * period / (LN2 * c) - DISCHARGE_OHM if rb_ohms is None else rb_ohms
        ra = period / (LN2 * c) - 2 * rb - DISCHARGE_OHM if ra_ohms is None else ra_ohms   # t_high + t_low = period
        if rb_ohms is not None and ra_ohms is None and ra <= 0:
            raise ValueError("that Rb is too large for the requested frequency with this capacitor")
        if ra <= 0 or rb <= 0:
            raise ValueError("the requested frequency and capacitor leave no room for Ra and Rb; use a smaller "
                             "capacitor or a lower frequency")
    for nm, v in (("Ra", ra), ("Rb", rb)):
        if v < _MIN_PRACTICAL_R or v > _MAX_PRACTICAL_R:
            notes.append(f"{nm} ({v:.4g} ohm) is outside the practical 1 kohm to 10 Mohm range")
    th, tl = timing(ra, rb, c)
    return AstableDesign(supply_voltage, ra, rb, c, th, tl, 1.0 / (th + tl), th / (th + tl), tuple(notes))


def astable_555_generator(
    supply_voltage: float = 5.0,
    ra_ohms: Optional[float] = None,
    rb_ohms: Optional[float] = None,
    capacitor: Optional[float] = None,
    frequency: Optional[float] = None,
    duty_cycle: Optional[float] = None,
) -> Tuple[str, str]:
    """Generate the classic 555 astable multivibrator (Ra, Rb, C) as Falstad circuit text.

    Vcc - Ra - [discharge pin] - Rb - [threshold and trigger pins, capacitor to ground]. The output is a
    rectangular wave between 0 V and Vcc with
        t_high = 0.693 (Ra + Rb) C,  t_low = 0.693 Rb C,  f = 1.44 / ((Ra + 2 Rb) C),
        duty = (Ra + Rb) / (Ra + 2 Rb)   (always above 50%).
    Give `frequency` and `duty_cycle` (and optionally `capacitor`) and Ra and Rb are solved; or give Ra, Rb and
    C directly. It makes its own signal and has no input, so it can only be the FIRST stage of a cascade.

    Args:
        supply_voltage: Vcc, in volts. Default 5 V.
        ra_ohms: Resistor from Vcc to the discharge pin, ohms. Solved from frequency and duty if omitted.
        rb_ohms: Resistor from the discharge pin to the capacitor, ohms. Solved if omitted.
        capacitor: Timing capacitor, farads. Chosen to suit the frequency if omitted.
        frequency: Target frequency, Hz (default 1000 when Ra/Rb/C are not all given).
        duty_cycle: Target fraction of the period the output is high, between 0.5 and 1 (default 0.6).

    Returns:
        A (circuit_text, note) tuple; `note` states the resolved Ra, Rb, C, frequency and duty cycle.

    Raises:
        ValueError: If an argument is not positive, duty_cycle is not between 0.5 and 1, or the values leave
            no room for the resistors.
    """
    d = design(supply_voltage, ra_ohms, rb_ohms, capacitor, frequency, duty_cycle)
    el = [
        timer555(176, 96, 192, 96, 6, d.supply_voltage),
        dc_rail(112, 64, 80, 64, d.supply_voltage),
        wire(112, 64, 240, 64),
        wire(240, 64, 304, 64),
        wire(304, 64, 304, 128),
        res(112, 64, 112, 128, d.Ra),
        wire(112, 128, 176, 128),
        res(112, 128, 112, 192, d.Rb),
        wire(112, 192, 112, 224),
        wire(112, 192, 176, 192),
        wire(112, 224, 176, 224),
        cap(112, 224, 112, 288, d.C, d.supply_voltage / 3.0),
        gnd(112, 288, 112, 304),
        gnd(272, 256, 272, 272),
        out_marker(304, 160, 368, 160),
    ]
    note = (f"Ra = {d.Ra:.4g} ohm, Rb = {d.Rb:.4g} ohm, C = {d.C:.4g} F: about {d.f_hz:.4g} Hz at "
            f"{d.duty:.1%} duty (high {d.t_high * 1e3:.4g} ms, low {d.t_low * 1e3:.4g} ms), swinging 0 V to "
            f"{d.supply_voltage:g} V.")
    if d.notes:
        note += " " + "; ".join(n[0].upper() + n[1:] for n in d.notes) + "."
    step = min(5e-6, 1.0 / (400 * d.f_hz))
    return assemble(el, step, [(index_of(el, "O"), 2 * d.supply_voltage, 64)]), note


calculate = design   # public: used by the cascade's oscillator model
