"""Output waveforms of circuits that make their own DC-ish supply: the bridge rectifier and the DC-DC converters.

Like the oscillators, they have no signal input, so a cascade replaces them by an ideal source at their output
carrying the waveform computed here. The rectifier waveform comes from integrating the bridge-plus-capacitor
equations with Falstad's diode model; the converters use the standard continuous-conduction averages (with the
diode drop included) and a triangular ripple. tests/transient.py checks both against a time-domain simulation.
"""

from __future__ import annotations

import math

from .dc import D_IS, D_N, VT
from .oscillators import POWER_SOURCES as _P, Signal

RECTIFIERS = {"full_wave_rectifier"}
CONVERTERS = {"buck_converter", "boost_converter", "buck_boost_converter", "cuk_converter"}
POWER_SOURCES = RECTIFIERS | CONVERTERS
assert POWER_SOURCES == _P


def _diode_i(x: float) -> float:
    """Current through two series default diodes dropping x volts in total."""
    return D_IS * (math.exp(min(x / (2 * D_N * VT), 80.0)) - 1.0) if x > 0 else 0.0


def rectifier_signal(args: dict) -> Signal:
    import inspect
    from agent.circuits import full_wave_rectifier as gen
    from agent.circuits.full_wave_rectifier import full_wave_rectifier
    sig = inspect.signature(full_wave_rectifier)
    a = {k: v for k, v in args.items() if k in sig.parameters}
    vpk = float(a.get("peak_voltage", sig.parameters["peak_voltage"].default))
    f = float(a.get("frequency", sig.parameters["frequency"].default))
    rl = float(a.get("load_resistor", sig.parameters["load_resistor"].default))
    c = a.get("capacitor")
    if c is None:
        c = 1.0 / (2 * f * rl * float(a.get("ripple_fraction", sig.parameters["ripple_fraction"].default)))
    c = float(c)
    per = 1.0 / f
    n_per = 1000                                          # steps per line period
    dt = per / n_per
    vc = max(vpk - 1.5, 0.0)
    last = []
    for period in range(12 if rl * c > 3 * per else 6):
        last = []
        for k in range(n_per):
            vs = abs(vpk * math.sin(2 * math.pi * (k + 1) / n_per))
            lo, hi = 0.0, max(vs, vc)
            for _ in range(60):                           # implicit step: vcn - vc = dt/C (i(vs - vcn) - vcn/RL)
                mid = 0.5 * (lo + hi)
                if mid - vc - dt / c * (_diode_i(vs - mid) - mid / rl) < 0:
                    lo = mid
                else:
                    hi = mid
            vc = 0.5 * (lo + hi)
            last.append(vc)
    half = n_per // 2
    wave = last[half:] if len(last) >= n_per else last     # the second half-cycle of the last period
    m = len(wave)

    def phase_fn(p):
        x = (p % 1.0) * m
        i = int(x) % m
        return wave[i] + (x - int(x)) * (wave[(i + 1) % m] - wave[i])

    sig = Signal("full_wave_rectifier", "rectified", 2 * f, max(wave), phase_fn, dc=sum(wave) / m,
                 v_low=min(wave), v_high=max(wave))
    sig.notes.append(f"the output is the rectified, smoothed mains: its ripple is at {2 * f:g} Hz, twice the "
                     f"line frequency, and the bridge drops the peak by about {vpk - max(wave):.2g} V "
                     "(two diodes in series carrying the capacitor's charging pulses)")
    sig.notes.append("the load resistor in the rectifier circuit is already counted; a later stage that draws "
                     "extra current from this node would sag the output further, which this model ignores")
    return sig


def converter_signal(name: str, args: dict) -> Signal:
    """DC level (the design target) with the triangular ripple at the switching frequency."""
    import inspect
    from agent import circuits
    from agent.circuits._converters import design
    fn = getattr(circuits, name)
    params = inspect.signature(fn).parameters
    a = {k: float(args.get(k, p.default)) for k, p in params.items()}
    topo = {"buck_converter": "buck", "boost_converter": "boost", "buck_boost_converter": "buck_boost",
            "cuk_converter": "cuk"}[name]
    cv = design(topo, a["input_voltage"], a["output_voltage"], a["load_current"], a["switching_frequency"],
                a["ripple_current_fraction"], a["output_ripple_fraction"])
    dc, half = cv.vout, cv.v_ripple / 2

    def tri(p):
        return dc + half * (4 * p - 1 if p < 0.5 else 3 - 4 * p)

    sig = Signal(name, "dc_ripple", cv.f_sw, abs(dc) + half, tri, dc=dc, v_low=dc - half, v_high=dc + half, duty=cv.duty)
    sig.intro = None
    sig.notes.append(f"it runs at a duty cycle of {cv.duty:.1%} with a {cv.L * 1e6:.3g} uH inductor"
                     + (f" and {cv.L2 * 1e6:.3g} uH second inductor" if cv.L2 else "")
                     + f" and {cv.C * 1e6:.3g} uF output capacitor, assuming continuous conduction")
    sig.notes.append("the level is the design target; the circuit as built comes out a couple of percent lower "
                     "from the switch and diode losses, and a later stage that draws extra current from this "
                     "node would pull it down further, which is not modelled")
    if name in ("buck_boost_converter", "cuk_converter"):
        sig.notes.append("the output is inverting, so the level is negative")
    return sig


def power_signal(name: str, args: dict) -> Signal:
    return rectifier_signal(args) if name in RECTIFIERS else converter_signal(name, args)
