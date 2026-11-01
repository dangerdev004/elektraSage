"""What an oscillator stage puts out, worked out from its design parameters.

The four oscillator generators have no signal input, so a cascade treats them as the SOURCE of the
chain. Everything later is analysed with the oscillator replaced by an ideal source at its output
(their outputs are op-amp outputs, so this is exact for the linear parts that follow).

The numbers come from the generators' own design formulas (the `calculate` function of each module),
not from simulating the oscillator. tests/transient.py checks those formulas against an independent
time-domain simulation.
"""

from __future__ import annotations

import cmath
import importlib
import math
from dataclasses import dataclass, field

TIMERS = {"square_wave_generator", "astable_555_generator"}      # periodic 555 sources, 0 V to Vcc
ONE_SHOTS = {"monostable_555_generator"}                          # one pulse per trigger, no steady state
POWER_SOURCES = {"full_wave_rectifier", "buck_converter", "boost_converter", "buck_boost_converter",
                 "cuk_converter"}                                 # supplies: a DC level with ripple (powersources.py)
OSCILLATORS = {"triangle_oscillator", "sawtooth_oscillator", "wien_bridge_oscillator",
               "phase_shift_oscillator", "rc_phaseshift"} | TIMERS | POWER_SOURCES
SAMPLES = 1024
HARMONICS = 64


@dataclass
class Signal:
    name: str
    shape: str                      # "triangle", "sawtooth", "sine"
    f0: float                       # Hz
    v_peak: float                   # largest excursion of the waveform (V)
    phase_fn: object                # phase in [0, 1) -> volts
    approximate: bool = False
    notes: list[str] = field(default_factory=list)
    dc: float = 0.0                 # mean of the waveform (V)
    v_low: float | None = None      # for levels-type waves (square): the two levels
    v_high: float | None = None
    duty: float | None = None
    r_out: float = 0.0              # output resistance behind the ideal source (ohms)
    intro: str | None = None        # replaces 'which makes its own signal' for stages that only switch

    def wave(self, n: int = SAMPLES) -> list[float]:
        return [self.phase_fn(i / n) for i in range(n)]

    def harmonics(self, kmax: int = HARMONICS, n: int = SAMPLES) -> list[complex]:
        """Complex peak coefficient c_k of harmonic k (k = 1..kmax): x(t) = sum Re(c_k e^{j k w t})."""
        w = self.wave(n)
        out = []
        for k in range(1, kmax + 1):
            acc = 0j
            for i, x in enumerate(w):
                acc += x * cmath.exp(-2j * math.pi * k * i / n)
            out.append(2 * acc / n)
        return out

    @property
    def fundamental(self) -> float:
        return abs(self.harmonics(1)[0])


_MODULE_OF = {"square_wave_generator": "squarewave_generator"}


def _module(name: str):
    return importlib.import_module(f"agent.circuits.{_MODULE_OF.get(name, name)}")


def _triangle(v) -> callable:
    def f(p):
        return v.vpk_v * (4 * p - 1) if p < 0.5 else v.vpk_v * (3 - 4 * p)
    return f


def _sawtooth(v) -> callable:
    d = v.rise_fraction

    def f(p):
        return v.vpk_v * (2 * p / d - 1) if p < d else v.vpk_v * (1 - 2 * (p - d) / (1 - d))
    return f


def model_for(name: str, args: dict) -> Signal:
    """The oscillator's output signal for the given generator arguments."""
    if name in POWER_SOURCES:
        from .powersources import power_signal
        return power_signal(name, args)
    if name == "rc_phaseshift":                       # the older phase-shift oscillator generator (no calculate())
        return _legacy_phase_shift_signal(args)
    mod = _module(name)
    v = mod.calculate(**args)
    if name == "triangle_oscillator":
        sig = Signal(name, "triangle", v.f_hz, v.vpk_v, _triangle(v))
        sig.notes.append(f"CircuitJS will show about {v.f_sim_hz:.4g} Hz, a little below the design frequency, "
                         "because the comparator can only switch on a time step")
    elif name == "sawtooth_oscillator":
        sig = Signal(name, "sawtooth", v.f_hz, v.vpk_v, _sawtooth(v))
        sig.notes.append(f"it spends {v.rise_fraction:.1%} of each period rising; CircuitJS will show about "
                         f"{v.f_sim_hz:.4g} Hz and peaks near +{v.peak_hi_v:.3g} V / -{v.peak_lo_v:.3g} V "
                         "because the comparator switches a time step late")
    elif name == "wien_bridge_oscillator":
        a = v.amplitude_v
        sig = Signal(name, "sine", v.f_hz, a, lambda p, a=a: a * math.sin(2 * math.pi * p), approximate=True)
        sig.notes.append(f"the amplitude is an estimate from the lamp model, and takes about {v.settle_s:.2g} s "
                         "of simulated time to settle from start-up")
    elif name == "phase_shift_oscillator":
        a = mod.OPAMP_RAIL_V
        sig = Signal(name, "sine", v.f_expected_hz, a, lambda p, a=a: a * math.sin(2 * math.pi * p),
                     approximate=True)
        sig.notes.append("its output runs into the op-amp's limits, so the real wave is flattened and distorted "
                         "(treated here as a sine of that size, which is only approximate), and its frequency "
                         f"is a few percent below the design value of {v.f_design_hz:.4g} Hz")
    elif name in TIMERS:
        sig = _timer_signal(name, mod, v)
    else:
        raise KeyError(name)
    return sig


def _legacy_phase_shift_signal(args: dict) -> Signal:
    import inspect
    mod = _module("rc_phaseshift")
    params = inspect.signature(mod.rc_phaseshift).parameters
    f_req = float(args.get("frequency_hz", params["frequency_hz"].default))
    supply = float(args.get("amp_supply", params["amp_supply"].default))
    r, _rf, c = mod._solve_rc(f_req)
    f = mod._ladder_frequency(r, c)
    sig = Signal("rc_phaseshift", "sine", f, supply, lambda p, a=supply: a * math.sin(2 * math.pi * p),
                 approximate=True)
    sig.notes.append("its output runs into the op-amp's limits, so the real wave is flattened and distorted "
                     "(treated here as a sine of that size, which is only approximate), and the ladder frequency "
                     f"is {f:.4g} Hz with the standard-value resistors")
    return sig


def _timer_signal(name: str, mod, v) -> Signal:
    vcc, duty = v.supply_voltage, v.duty
    sig = Signal(name, "square", v.f_hz, vcc,
                 lambda p, d=duty, h=vcc: h if p < d else 0.0, dc=vcc * duty, v_low=0.0, v_high=vcc, duty=duty)
    sig.notes.append("the 555's output is modelled as an ideal 0 V to Vcc square wave; the real output has a "
                     "1 ohm switch resistance, which only matters if a later stage loads it heavily")
    return sig


def one_shot(args: dict) -> dict:
    """Facts about the monostable's single pulse."""
    mod = _module("monostable_555_generator")
    import inspect
    sig = inspect.signature(mod.monostable_555_generator)
    a = {k: v for k, v in args.items() if k in sig.parameters}
    text, note = mod.monostable_555_generator(**a)
    import re
    m = re.search(r"R = ([\d.eE+-]+) ohm, C = ([\d.eE+-]+) F, pulse width T = 1.1\*R\*C = ([\d.eE+-]+) s", note)
    vcc = float(args.get("supply_voltage", sig.parameters["supply_voltage"].default))
    return dict(r=float(m.group(1)), c=float(m.group(2)), width=float(m.group(3)), vcc=vcc)


# ---- a CMOS inverter driven by the stage's own source: its output is the static transfer curve applied to it ----
def is_inverter(stage) -> bool:
    """True if the stage holds both a P-channel and an N-channel MOSFET (and no op-amp): a switching gate."""
    fets = [e for e in stage.nl.elements if e.type == "f"]
    return (any(int(e.flags) & 1 for e in fets) and any(not int(e.flags) & 1 for e in fets)
            and not any(e.type == "a" for e in stage.nl.elements))


def _drive(wf: int, f: float, amp: float, bias: float):
    """Input voltage as a function of phase in [0, 1), for CircuitJS waveforms 1..4."""
    if wf == 1:
        return lambda p: bias + amp * math.sin(2 * math.pi * p)
    if wf == 2:
        return lambda p: bias + (amp if p < 0.5 else -amp)
    if wf == 3:
        return lambda p: bias + amp * (4 * p - 1 if p < 0.5 else 3 - 4 * p)
    if wf == 4:
        return lambda p: bias + amp * (2 * p - 1)
    raise ValueError(f"waveform {wf} is not handled")


def inverter_signal(stage) -> Signal:
    """The inverter's output waveform for its own source: the static transfer curve (found with the DC solver)
    applied to the input at every phase. Quasi-static: switching delays and capacitances are ignored."""
    import bisect
    from . import dump
    from .dc import operating_point
    from .ports import is_signal_source
    srcs = [(i, e) for i, e in enumerate(stage.nl.elements) if is_signal_source(e)]
    if len(srcs) != 1 or srcs[0][1].type != "R":
        raise ValueError("expected exactly one drive source")
    e = srcs[0][1]
    wf = int(float(e.tail[0]))
    f, amp = float(e.tail[1]), float(e.tail[2])
    bias = float(e.tail[3]) if len(e.tail) > 3 else 0.0
    drive = _drive(wf, f, amp, bias)
    nl = dump.parse(stage.nl.to_text())
    nl.elements = [x for x in nl.elements if not is_signal_source(x)]
    out = stage.ports.outputs[0].node
    hot = stage.ports.inputs[0].node
    vin = [drive(i / 256) for i in range(256)]
    lo_v, hi_v = min(vin), max(vin)
    grid = [lo_v + (hi_v - lo_v) * k / 120 for k in range(121)] if hi_v > lo_v else [lo_v]
    vout = [operating_point(nl, fixed={hot: v}).v(out) for v in grid]

    def curve(v):
        if len(grid) == 1:
            return vout[0]
        k = min(max(bisect.bisect_right(grid, v) - 1, 0), len(grid) - 2)
        t = (v - grid[k]) / (grid[k + 1] - grid[k])
        return vout[k] + t * (vout[k + 1] - vout[k])

    wave = [curve(v) for v in vin]
    wave = [0.0 if abs(w) < 1e-4 else w for w in wave]
    v_low, v_high = min(wave), max(wave)
    mid = 0.5 * (v_low + v_high)
    duty = sum(1 for w in wave if w > mid) / len(wave)
    sig = Signal(stage.name, "square", f, max(abs(v_low), abs(v_high)),
                 lambda p: curve(drive(p % 1.0)), dc=sum(wave) / len(wave), v_low=v_low, v_high=v_high, duty=duty)
    fets = [x for x in nl.elements if x.type == "f"]
    vt = float(fets[0].tail[0])
    beta = max(float(x.tail[1]) for x in fets)
    sig.r_out = 1.0 / (beta * max(v_high - vt, 1e-3))
    sig.intro = (f"stage 1 ({stage.name}) is a switching gate, not an amplifier: its own drive source goes through its "
                 f"DC transfer curve, so the output is a {fmt_v(v_low)} to {fmt_v(v_high)} wave")
    sig.notes.append(f"each transistor's on-resistance is about {sig.r_out:.3g} ohm, which is put in series with the "
                     "output in the analysis below, so a later stage that loads it pulls the levels toward the middle")
    sig.notes.append("this is a quasi-static model: the output follows the DC transfer curve at every instant, with "
                     "no gate or load capacitance, so real edges are slower than shown")
    if v_high - v_low < 0.8 * max(abs(v_high), abs(v_low), 1e-9):
        sig.notes.append("the input never swings far enough to switch the gate fully, so the output stays "
                         "partly in its linear region")
    return sig


def fmt_v(v: float) -> str:
    return f"{v:.3g} V"
