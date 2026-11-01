"""Pure-Python AC analysis of a composed chain, plus deterministic flags.

Scope (stated honestly in every report): linear parts only - resistors,
capacitors, inductors and an IDEAL op amp (no gain-bandwidth limit, no
clipping in the response curve). Any other element type, or a chain that
starts with a generator, is reported as "not analysed" rather than guessed.
Other signal sources in the circuit are held at 0.

Everything here is computed by code; the LLM is told to relay it, not to
recompute it. Validated against CircuitJS: for the RC high-pass -> RC low-pass
-> inverting amp (gain 10) example CircuitJS measured a 11.538 V peak output
for the 5 V sweep and this solver gives 11.545 V.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .compose import Composite, Stage, compose
from .dc import NotAnalysable, operating_point, small_signal
from .dump import Netlist, Point, terminals
from .ports import infer, is_signal_source

SUPPORTED = {"w", "g", "r", "c", "l", "a", "O", "170", "v", "R", "x", "t", "f", "d", "z"}
POINTS_PER_DECADE = 80
TOL = 0.20                 # corner / gain / loading deviations beyond 20% are flagged


# ---- number formatting ----------------------------------------------------
_SI = [(1e9, "G"), (1e6, "M"), (1e3, "k"), (1, ""), (1e-3, "m"), (1e-6, "u")]


def fmt(x: float, unit: str = "") -> str:
    if x == 0 or not math.isfinite(x):
        return f"{x:g}{unit}"
    for scale, suf in _SI:
        if abs(x) >= scale * 0.9999:
            return f"{x / scale:.3g}{suf}{unit}"
    return f"{x:.3g}{unit}"


# ---- circuit preparation -----------------------------------------------------
class _UF:
    def __init__(self):
        self.p: dict = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


@dataclass
class Driver:
    index: int
    hot: Point
    amp: float                       # peak volts
    sweep: tuple[float, float] | None
    f0: float | None

    def grid(self) -> list[float]:
        if self.sweep:
            lo, hi = self.sweep[0] / 10, self.sweep[1] * 10
        else:
            lo, hi = self.f0 / 100, self.f0 * 100
        n = int(math.ceil(math.log10(hi / lo) * POINTS_PER_DECADE)) + 1
        return [lo * (hi / lo) ** (i / (n - 1)) for i in range(n)]


def find_driver(nl: Netlist) -> Driver:
    ports = infer(nl)
    for p in ports.inputs:
        e = nl.elements[p.element]
        if e.attrs is not None:
            raise NotAnalysable("XML-format circuit")
        if e.type == "170":
            return Driver(p.element, p.node, float(e.tail[2]),
                          (float(e.tail[0]), float(e.tail[1])), None)
        return Driver(p.element, p.node, float(e.tail[2]), None, float(e.tail[1]))
    raise NotAnalysable("no signal source drives it (it starts with a generator)")


class System:
    """Prepared nodal system for one netlist and one driven source."""

    def __init__(self, nl: Netlist, driver: Driver):
        bad = sorted({e.type for e in nl.elements if e.type not in SUPPORTED})
        if bad:
            raise NotAnalysable(f"contains element types without a model: {bad}")
        if any(e.attrs is not None for e in nl.elements):
            raise NotAnalysable("XML-format circuit")
        uf = _UF()
        gnd = ("GND",)
        uf.find(gnd)
        for i, e in enumerate(nl.elements):
            ts = terminals(e)
            for t in ts or []:
                uf.find(t)
            if e.type == "w":
                uf.union(e.p1, e.p2)
            elif e.type == "g":
                uf.union(e.p1, gnd)
            elif e.type in ("v", "R", "170") and i != driver.index:
                # DC supplies and the other inputs: AC-wise a short to ground / across
                uf.union(e.p1, gnd if e.type != "v" else e.p2)
                if e.type == "v" and not is_signal_source(e):
                    uf.union(e.p2, gnd)
        self._ids: dict = {}

        def node(pt):
            r = uf.find(pt)
            return None if r == uf.find(gnd) else self._ids.setdefault(r, len(self._ids))

        self.branches, self.amps = [], []
        for e in nl.elements:
            if e.type in ("r", "c", "l"):
                self.branches.append((node(e.p1), node(e.p2), e.type, float(e.tail[0])))
            elif e.type == "a":
                ts = terminals(e)
                inv, non = (ts[1], ts[0]) if int(e.flags) & 1 == 0 else (ts[0], ts[1])
                self.amps.append((node(inv), node(non), node(ts[2])))
        self.devices = []                       # (node ids of the 3 pins, 3x3 small-signal Jacobian)
        self.op = None
        if any(e.type in ("t", "f", "d", "z") for e in nl.elements):
            self.op = operating_point(nl)
            for _kind, _e, pts, J, _cur in small_signal(nl, self.op):
                self.devices.append(([node(p) for p in pts], J))
        self.src = node(driver.hot)
        self.node = node
        self.n = len(self._ids)
        if self.src is None:
            raise NotAnalysable("driven node is ground")

    def solve(self, f: float) -> list[complex]:
        w = 2 * math.pi * f
        size = self.n + len(self.amps) + 1
        A = [[0j] * size for _ in range(size)]
        b = [0j] * size
        for a, c, kind, v in self.branches:
            y = {"r": 1 / v, "c": 1j * w * v, "l": 1 / (1j * w * v)}[kind]
            for i, j, s in ((a, a, 1), (c, c, 1), (a, c, -1), (c, a, -1)):
                if i is not None and j is not None:
                    A[i][j] += s * y
        for nodes3, J in self.devices:          # transistors, linearised at their DC operating point
            for ti, i in enumerate(nodes3):
                for tj, j in enumerate(nodes3):
                    if i is not None and j is not None:
                        A[i][j] += J[ti][tj]
        for k, (inv, non, out) in enumerate(self.amps):
            row = self.n + k
            if inv is not None:
                A[row][inv] += 1
            if non is not None:
                A[row][non] -= 1
            if out is not None:
                A[out][row] += 1
        srow = size - 1
        A[srow][self.src] = 1
        A[self.src][srow] = 1
        b[srow] = 1
        return _gauss(A, b)

    def v(self, x: list[complex], pt: Point) -> complex:
        i = self.node(pt)
        return 0j if i is None else x[i]


def _gauss(A, b):
    n = len(b)
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(A[r][c]))
        if abs(A[p][c]) < 1e-30:
            raise NotAnalysable("circuit equations are singular (floating node?)")
        A[c], A[p], b[c], b[p] = A[p], A[c], b[p], b[c]
        piv = A[c][c]
        for r in range(c + 1, n):
            m = A[r][c] / piv
            if m:
                A[r] = [x - m * y for x, y in zip(A[r], A[c])]
                b[r] -= m * b[c]
    x = [0j] * n
    for r in range(n - 1, -1, -1):
        x[r] = (b[r] - sum(A[r][j] * x[j] for j in range(r + 1, n))) / A[r][r]
    return x


def depth_text(db: float) -> str:
    """'over 60 dB down' for a numerically perfect notch, else 'at least N dB down' (the sweep grid
    is finite, so the true bottom of a notch can be deeper than the deepest sample)."""
    return "over 60 dB down" if db >= 60 else f"at least {db:.0f} dB down"


# ---- curve metrics -------------------------------------------------------------
@dataclass
class Metrics:
    peak: float
    f_peak: float
    lo: float | None
    hi: float | None
    sloping: bool = False      # gain falls/rises steadily across the grid (integrator-like)
    stop: tuple[float, float] | None = None   # -3 dB edges of a band-stop (notch) response
    f_notch: float | None = None              # frequency of the deepest point of that notch
    depth_db: float | None = None             # how far below the passband gain that point is (>= 0)

    @property
    def shape(self) -> str:
        if self.stop is not None and self.lo is None and self.hi is None:
            return "band-stop (notch)"
        if self.sloping:
            return "sloping (gain changes steadily with frequency, e.g. integrator/differentiator)"
        return {(True, True): "band-pass", (True, False): "high-pass",
                (False, True): "low-pass", (False, False): "flat"}[(self.lo is not None,
                                                                      self.hi is not None)]


def metrics(freqs: list[float], mags: list[float]) -> Metrics:
    pk = max(mags)
    ip = mags.index(pk)
    thr = pk / math.sqrt(2)
    ppd = POINTS_PER_DECADE
    if len(mags) > ppd and (
            (ip == 0 and mags[0] / max(mags[ppd], 1e-300) > 2)
            or (ip == len(mags) - 1 and mags[-1] / max(mags[-1 - ppd], 1e-300) > 2)):
        return Metrics(pk, freqs[ip], None, None, True)     # corners would be grid artifacts

    def cross(i0, i1):                       # log-f interpolation between two samples
        f0, f1, m0, m1 = freqs[i0], freqs[i1], mags[i0], mags[i1]
        t = (thr - m0) / (m1 - m0)
        return math.exp(math.log(f0) + t * (math.log(f1) - math.log(f0)))

    lo = hi = None
    if mags[0] < thr:
        i = next(i for i, m in enumerate(mags) if m >= thr)
        lo = cross(i - 1, i)
    if mags[-1] < thr:
        j = max(i for i, m in enumerate(mags) if m >= thr)
        hi = cross(j, j + 1)
    # an interior dip below -3 dB between two points that pass: a notch
    a = next(i for i, m in enumerate(mags) if m >= thr)
    b = max(i for i, m in enumerate(mags) if m >= thr)
    inner = [i for i in range(a, b + 1) if mags[i] < thr]
    stop = f_notch = depth = None
    if inner:
        im = min(inner, key=lambda i: mags[i])
        i0 = i1 = im
        while i0 > a and mags[i0 - 1] < thr:
            i0 -= 1
        while i1 < b and mags[i1 + 1] < thr:
            i1 += 1
        stop = (cross(i0 - 1, i0), cross(i1, i1 + 1))
        f_notch = freqs[im]
        depth = 20 * math.log10(pk / max(mags[im], 1e-300))
    return Metrics(pk, freqs[ip], lo, hi, False, stop, f_notch, depth)


def _curve(nl, driver, freqs, pts):
    sysm = System(nl, driver)
    out = {p: [] for p in dict.fromkeys(pts)}          # de-duplicated, order kept
    for f in freqs:
        x = sysm.solve(f)
        for p in out:
            out[p].append(sysm.v(x, p))
    return out


# ---- the report ----------------------------------------------------------------------
@dataclass
class Analysis:
    supported: bool
    reason: str = ""
    lines: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    # structured results (used by the scope fix, the fix search and the canned reply)
    gain: float | None = None
    lo: float | None = None
    hi: float | None = None
    sloping: bool = False
    loaded: list[int] = field(default_factory=list)       # junctions (1-based) that load the stage before
    shape: str = ""
    whatif: tuple | None = None                           # (gain, lo, hi) with ideal buffers
    expected_gain: float | None = None                    # product of the stages' own gains
    node_peaks: dict = field(default_factory=dict)        # O-marker node -> peak volts for the real source
    worst_load: float | None = None                       # smallest "x of unloaded level" over all junctions
    stop: tuple | None = None                             # (lo, hi) -3 dB edges when the response is band-stop
    f_notch: float | None = None
    depth_db: float | None = None
    source_amp: float | None = None                       # peak volts of the driving source in this analysis
    headroom: list = field(default_factory=list)          # (peak, limit) of every op-amp at/over 90% of its limit
    comparator: dict | None = None                        # facts about a Schmitt trigger / comparator in the chain
    static: dict | None = None                            # facts about a chain that starts with a DAC (DC levels)
    regulator: dict | None = None                         # facts about a chain whose first stage is a regulator
    oneshot: dict | None = None                           # facts about a chain that starts with a 555 one-shot
    oscillator: dict | None = None                        # facts about a chain that starts with an oscillator
    adc: dict | None = None                               # facts about a chain that ends in a flash ADC

    def to_text(self) -> str:
        if not self.supported and (self.comparator or self.static):
            out = [f"Computed (code-computed; {self.reason}):"] + ["  " + l for l in self.lines]
            out += ["Flags (code-computed, relay each, never recompute):"] + ["  - " + f for f in self.flags] \
                if self.flags else ["Flags: none raised."]
            return "\n".join(out)
        if not self.supported:
            return ("Computed response: NOT ANALYSED (" + self.reason + "). Say plainly that the "
                    "chain's response could not be checked by code.")
        out = ["Computed response of the whole chain (code-computed; linear parts, ideal op-amp "
               "with no bandwidth limit; other inputs held at 0):"] + ["  " + l for l in self.lines]
        out.append("Flags (code-computed, not opinions; relay and explain each, never recompute):"
                   if self.flags else "Flags: none raised.")
        out += ["  - " + f for f in self.flags]
        return "\n".join(out)


def _stage_curves(s: Stage, freqs: list[float]):
    """A stage on its own, driven by an ideal source: complex response at its output
    and at each op-amp output, on the chain's frequency grid."""
    drv = find_driver(s.nl)
    sysm = System(s.nl, drv)
    out = s.ports.outputs[0].node
    amps = [(i, terminals(e)[2], e) for i, e in enumerate(s.nl.elements) if e.type == "a"]
    res = {"out": [], "amps": {i: [] for i, _, _ in amps}}
    for f in freqs:
        x = sysm.solve(f)
        res["out"].append(sysm.v(x, out))
        for i, node, _ in amps:
            res["amps"][i].append(sysm.v(x, node))
    return res, amps


def _peak(drv: Driver, freqs: list[float], vals: list[complex]) -> float:
    """Peak amplitude at a node for the real driving source."""
    if drv.sweep:
        return drv.amp * max(abs(v) for f, v in zip(freqs, vals)
                             if drv.sweep[0] <= f <= drv.sweep[1])
    i = min(range(len(freqs)), key=lambda j: abs(freqs[j] - drv.f0))
    return drv.amp * abs(vals[i])


def _what_if_buffered(stages, freqs, drv, m, flags, lines):
    """Chain response if every junction had an ideal unity-gain buffer.

    A buffer does not load the stage before it and drives the next one from a
    stiff source, so the buffered chain is exactly the product of each stage's
    own (standalone) response.
    """
    try:
        per = [_stage_curves(s, freqs) for s in stages]
    except (NotAnalysable, IndexError):
        return None
    total = [1 + 0j] * len(freqs)
    for res, _ in per:
        total = [t * v for t, v in zip(total, res["out"])]
    bm = metrics(freqs, [abs(v) for v in total])
    if bm.sloping:
        return None
    band = (f"-3 dB band {fmt(bm.lo, 'Hz') if bm.lo else 'from low end'} to "
            f"{fmt(bm.hi, 'Hz') if bm.hi else 'high end'}")
    lines.append("What-if (code-computed): with an ideal unity-gain buffer at EVERY junction the "
                 f"chain would give passband gain {bm.peak:.3g} (peak near {fmt(bm.f_peak, 'Hz')}); "
                 f"{band}. Only this all-junctions case is computed.")
    prefix = [1 + 0j] * len(freqs)
    for k, (res, amps) in enumerate(per, 1):
        for i, _, e in amps:
            vals = [p * v for p, v in zip(prefix, res["amps"][i])]
            pk = _peak(drv, freqs, vals)
            lim = min(abs(float(e.tail[0])), abs(float(e.tail[1]))) if len(e.tail) >= 2 else None
            txt = f"  buffered: op-amp in stage {k} would peak at {fmt(pk, 'V')}"
            if lim:
                txt += f" vs +/-{fmt(lim, 'V')} limit"
                if pk > lim:
                    txt += " - it WOULD CLIP, so this fix also needs a lower source level or less gain"
                    flags.append(f"Headroom if the loading were removed: the op-amp in stage {k} would peak "
                                 f"at {fmt(pk, 'V')} vs +/-{fmt(lim, 'V')} and clip.")
                elif pk > 0.9 * lim:
                    txt += " - within 10% of the limit, so little headroom"
                    flags.append(f"Headroom if the loading were removed: the op-amp in stage {k} would peak "
                                 f"at {fmt(pk, 'V')} vs +/-{fmt(lim, 'V')}, within 10% of its limit.")
            lines.append(txt)
        prefix = [p * v for p, v in zip(prefix, res["out"])]
    return bm


def _stage_metrics(s: Stage):
    try:
        drv = find_driver(s.nl)
        freqs = drv.grid()
        out = s.ports.outputs[0].node
        c = _curve(s.nl, drv, freqs, [out])[out]
        return metrics(freqs, [abs(v) for v in c])
    except (NotAnalysable, IndexError):
        return None



# ---- transistors, comparators and DAC levels --------------------------------------------
def _device_report(nl, comp, dev_data, op, curves, freqs, drv, lines, flags) -> None:
    """Bias point, headroom and linearity of every transistor, for the real driving source."""
    lines.insert(0, "transistors are linearised at their DC operating point (Falstad's own transistor "
                    "equations): the response below is a small-signal estimate, and the checks under it "
                    "compare the signal swing with the room around the bias point")
    stage_of = {i: comp.owners[i] for i in range(len(comp.owners))}
    polarity = lambda x: float(x.tail[0]) if x.type == "t" and x.tail else 1.0       # noqa: E731
    pushpull = {stage_of.get(next(i for i, y in enumerate(nl.elements) if y is e), -1)
                for kind, e, *_ in dev_data if kind == "t" and polarity(e) < 0}
    pushpull &= {stage_of.get(next(i for i, y in enumerate(nl.elements) if y is e), -1)
                 for kind, e, *_ in dev_data if kind == "t" and polarity(e) > 0}
    for kind, e, pts, J, cur in dev_data:
        if kind in ("d", "z"):
            continue                                           # diodes are linearised silently
        idx = next(i for i, x in enumerate(nl.elements) if x is e)
        sk = stage_of.get(idx, -1) + 1
        a, b, c = (curves[p] for p in pts)                     # collector/drain, base/gate, emitter/source
        va, vb, vc = (op.v(p) for p in pts)
        i_ac = [J[0][0] * x + J[0][1] * y + J[0][2] * z for x, y, z in zip(a, b, c)]
        v_main = _peak(drv, freqs, [x - z for x, z in zip(a, c)])      # VCE / VDS swing
        v_ctl = _peak(drv, freqs, [y - z for y, z in zip(b, c)])       # VBE / VGS swing
        i_pk = _peak(drv, freqs, i_ac)
        if kind == "t":
            pol = polarity(e)
            vce, vbe, ic = pol * (va - vc), pol * (vb - vc), pol * cur[0]
            pp = (sk - 1) in pushpull
            lines.append(f"transistor in stage {sk} ({'NPN' if pol > 0 else 'PNP'}): rests at Ic = {fmt(ic, 'A')}, VCE = {vce:.3g} V, "
                         f"VBE = {vbe:.3g} V; signal swings VCE by {fmt(v_main, 'V')}, VBE by {fmt(v_ctl, 'V')}, "
                         f"Ic by {fmt(i_pk, 'A')} (peaks for this source)")
            if vce < 0.2:
                flags.append(f"Bias: the transistor in stage {sk} is saturated at rest (VCE {vce:.2g} V).")
            elif vce - v_main < 0.2:
                flags.append(f"Clipping: the transistor in stage {sk} would be driven into saturation: its VCE "
                             f"rests at {vce:.3g} V and the signal swings it by {fmt(v_main, 'V')} peak.")
            if pp and ic < 1e-6 and pol > 0:
                flags.append(f"Crossover: in the push-pull pair of stage {sk} neither transistor conducts at rest "
                             f"(Ic {fmt(ic, 'A')}), so there is a dead zone of about 0.6 V either side of zero "
                             f"where the output does not follow the input. Treat the small-signal gain above as "
                             f"unreliable: it is computed around that off state and understates the real gain "
                             f"for larger signals; the real output is the input minus about 0.6 V on each half.")
            elif pp and ic < 1e-6:
                pass                                           # the NPN already reported the dead zone for the pair
            elif pp:
                if pol > 0:
                    lines.append(f"push-pull pair in stage {sk}: both transistors idle at about {fmt(ic, 'A')}; the "
                                 f"gain above is for small signals around that idle point, and for larger signals "
                                 f"it rises toward RL/(RL + Re) as one device takes over each half-cycle")
            elif i_pk > ic > 0:
                flags.append(f"Clipping: the transistor in stage {sk} would be driven into cutoff: the signal "
                             f"current ({fmt(i_pk, 'A')} peak) exceeds its resting current ({fmt(ic, 'A')}).")
            if v_ctl > 0.01 and not pp:
                flags.append(f"Linearity: the base-emitter signal of the transistor in stage {sk} is "
                             f"{fmt(v_ctl, 'V')} peak. Above about 10 mV its exponential curve distorts the "
                             f"waveform, so the computed gain is only approximate.")
        else:
            vt = float(e.tail[0])
            vds, vgs, idc = va - vc, vb - vc, cur[0]
            vov = vgs - vt
            lines.append(f"MOSFET in stage {sk} (N-channel): rests at Id = {fmt(idc, 'A')}, VGS = {vgs:.3g} V, "
                         f"VDS = {vds:.3g} V (overdrive {vov:.3g} V); signal swings VDS by {fmt(v_main, 'V')}, "
                         f"VGS by {fmt(v_ctl, 'V')} (peaks for this source)")
            if vov <= 0:
                flags.append(f"Bias: the MOSFET in stage {sk} is off at rest (VGS {vgs:.3g} V is not above its "
                             f"threshold {vt:g} V).")
            elif vds < vov:
                flags.append(f"Bias: the MOSFET in stage {sk} is in the triode region at rest "
                             f"(VDS {vds:.3g} V is below the overdrive {vov:.3g} V), so it is not an amplifier.")
            else:
                if vds - v_main < vov + v_ctl:
                    flags.append(f"Clipping: the MOSFET in stage {sk} would leave saturation: its VDS rests at "
                                 f"{vds:.3g} V (overdrive {vov:.3g} V) and the signal swings it by "
                                 f"{fmt(v_main, 'V')} peak.")
                if v_ctl > vov:
                    flags.append(f"Clipping: the MOSFET in stage {sk} would be cut off on the negative half: "
                                 f"the gate signal ({fmt(v_ctl, 'V')} peak) exceeds the overdrive ({vov:.3g} V).")
                if v_ctl / (4 * vov) > 0.05:
                    flags.append(f"Linearity: the gate signal ({fmt(v_ctl, 'V')} peak) is large next to the "
                                 f"overdrive ({vov:.3g} V), giving about {v_ctl / (4 * vov) * 100:.1f}% "
                                 f"second-harmonic distortion.")


def positive_feedback_only(nl: Netlist, amp_index: int) -> bool:
    """True if the op-amp's output feeds its non-inverting input through passive parts but never its
    inverting input: a comparator with hysteresis rather than an amplifier."""
    from .dump import nets
    net_of = nets(nl.elements, merge_ground=True)
    gnd = {net_of[e.p1] for e in nl.elements if e.type == "g"}
    e = nl.elements[amp_index]
    ts = terminals(e)
    inv, non = (ts[1], ts[0]) if int(e.flags) & 1 == 0 else (ts[0], ts[1])
    adj: dict[int, set[int]] = {}
    for x in nl.elements:
        if x.type in ("r", "c", "l"):
            a_, b_ = net_of[x.p1], net_of[x.p2]
            if a_ in gnd or b_ in gnd:
                continue
            adj.setdefault(a_, set()).add(b_)
            adj.setdefault(b_, set()).add(a_)
    seen, todo = {net_of[ts[2]]}, [net_of[ts[2]]]
    while todo:
        for nb in adj.get(todo.pop(), ()):
            if nb not in seen:
                seen.add(nb)
                todo.append(nb)
    return net_of[non] in seen and net_of[inv] not in seen


def comparator_stage(stage: Stage) -> int | None:
    """Element index of a positive-feedback-only op-amp in the stage, if any."""
    for i, e in enumerate(stage.nl.elements):
        if e.type == "a" and positive_feedback_only(stage.nl, i):
            return i
    return None


def trip_points(stage: Stage, amp_index: int) -> tuple[float, float]:
    """(upper, lower) trip voltage of a comparator stage: the voltage at its non-inverting input with the
    output held at +limit / -limit."""
    e = stage.nl.elements[amp_index]
    ts = terminals(e)
    non = ts[1] if int(e.flags) & 1 else ts[0]
    lim = abs(float(e.tail[0]))
    hi = operating_point(stage.nl, ignore_amps=True, fixed={ts[2]: lim}).v(non)
    lo = operating_point(stage.nl, ignore_amps=True, fixed={ts[2]: -lim}).v(non)
    return hi, lo


def _analyse_comparator(stages, comp, k: int, amp_index: int) -> Analysis:
    stg = stages[k]
    name = stg.name
    try:
        utp, ltp = trip_points(stg, amp_index)
        lim = abs(float(stg.nl.elements[amp_index].tail[0]))
        nl = comp.netlist
        drv = find_driver(nl)
        freqs = drv.grid()
        op = operating_point(nl, ignore_amps=True) if any(e.type in ("t", "f", "d", "z") for e in nl.elements) \
            else operating_point(nl)
        if k == 0:
            hot = drv.hot
        else:
            hot = comp.joins[k - 1][0]
        curves = _curve(nl, drv, freqs, [hot])[hot]
        pk = _peak(drv, freqs, curves)
        dc = op.v(hot)
    except (NotAnalysable, ValueError, IndexError, KeyError) as e:
        return Analysis(False, f"stage {k + 1} is a comparator and its input level could not be computed ({e})")
    toggles = dc + pk > utp and dc - pk < ltp
    info = dict(stage=k + 1, name=name, utp=utp, ltp=ltp, swing_lo=dc - pk, swing_hi=dc + pk,
                limit=lim, toggles=toggles, after=len(stages) - k - 1)
    lines = [f"stage {k + 1} ({name}) is a comparator with hysteresis: it switches its output between "
             f"+/-{fmt(lim, 'V')} and has no gain or frequency response",
             f"trip points: upper {utp:.3g} V, lower {ltp:.3g} V (hysteresis {utp - ltp:.3g} V)",
             f"signal at its input for this source: {dc - pk:.3g} V to {dc + pk:.3g} V "
             f"({fmt(pk, 'V')} peak around {dc:.3g} V DC)"]
    flags = []
    if not toggles:
        need = []
        if dc + pk <= utp:
            need.append(f"never rises above the upper trip point ({utp:.3g} V)")
        if dc - pk >= ltp:
            need.append(f"never falls below the lower trip point ({ltp:.3g} V)")
        flags.append(f"Switching: the signal at stage {k + 1}'s input spans {dc - pk:.3g} V to {dc + pk:.3g} V, "
                     f"which {' and '.join(need)}, so its output will not toggle. It must cross both.")
    if info["after"]:
        flags.append(f"Not analysed: the {info['after']} stage(s) after the comparator are driven by a switched "
                     f"+/-{fmt(lim, 'V')} square wave, which the small-signal analysis does not cover.")
    res = Analysis(False, f"stage {k + 1} is a comparator, which switches rather than amplifies", lines, flags)
    res.comparator = info
    return res


def _analyse_static(stages, comp) -> Analysis | None:
    """Chain that starts with a DAC: DC levels at the DAC output and at the end of the chain."""
    nl = comp.netlist
    try:
        op = operating_point(nl)
        dac_out = comp.joins[0][0] if comp.joins else None
        end = (lambda o: (o[0] + comp.offsets[-1][0], o[1] + comp.offsets[-1][1]))(stages[-1].ports.outputs[0].node)
        first = [e for e in stages[0].nl.elements if e.type == "L"]
        code = int("".join("1" if int(float(e.tail[0])) == 1 else "0" for e in first), 2) if first else None
        v_dac = op.v(dac_out) if dac_out else op.v(end)
        v_end = op.v(end)
    except (NotAnalysable, ValueError, IndexError, KeyError) as e:
        return Analysis(False, f"the chain starts with a DAC and its DC levels could not be computed ({e})")
    flags, lines = [], []
    lines.append(f"stage 1 ({stages[0].name}) is a DAC with no signal input: at code {code} (bits "
                 f"{''.join('1' if int(float(e.tail[0])) == 1 else '0' for e in first)}) its output sits at "
                 f"{v_dac:.4g} V DC")
    lines.append(f"DC level at the end of the chain: {v_end:.4g} V")
    stage_of = {i: comp.owners[i] for i in range(len(comp.owners))}
    for i, e in enumerate(nl.elements):
        if e.type == "a" and len(e.tail) >= 2:
            node = terminals(e)[2]
            lim = min(abs(float(e.tail[0])), abs(float(e.tail[1])))
            lv = abs(op.v(node))
            sk = stage_of.get(i, -1) + 1
            if sk > 1:
                lines.append(f"op-amp in stage {sk}: DC output {op.v(node):.4g} V vs +/-{fmt(lim, 'V')} limit")
                if lv > lim:
                    flags.append(f"Clipping: the op-amp in stage {sk} would sit at {op.v(node):.3g} V DC, "
                                 f"beyond its +/-{fmt(lim, 'V')} limit.")
                elif lv > 0.9 * lim:
                    flags.append(f"Headroom: the op-amp in stage {sk} sits at {op.v(node):.3g} V DC, within 10% "
                                 f"of its +/-{fmt(lim, 'V')} limit.")
    res = Analysis(False, "the chain starts with a DAC, so there is no swept signal to measure; only DC levels "
                          "were computed", lines, flags)
    res.static = dict(dac=stages[0].name, code=code, v_dac=v_dac, v_end=v_end, stages=len(stages))
    return res


def analyse(stages: list[Stage], comp: Composite) -> Analysis:
    if len(stages) >= 2 and stages[-1].name == "flash_adc":
        return _analyse_adc(stages)
    from .oscillators import OSCILLATORS
    from .oscillators import ONE_SHOTS, inverter_signal, is_inverter
    if any(is_inverter(s) for s in stages[1:]):
        return Analysis(False, "a CMOS inverter after another stage switches between its rails instead of "
                               "amplifying, so a small-signal response would be meaningless; only an inverter as "
                               "the first stage (driven by its own source) is analysed")
    if is_inverter(stages[0]):
        try:
            sig = inverter_signal(stages[0])
        except Exception as e:
            return Analysis(False, f"the inverter's output could not be worked out ({type(e).__name__}: {e})")
        if len(stages) < 2:
            return Analysis(False, "an inverter on its own has nothing after it to analyse")
        return _analyse_oscillator(stages, comp, sig)
    if stages[0].name in OSCILLATORS:
        return _analyse_oscillator(stages, comp)
    if stages[0].name in ONE_SHOTS:
        return _analyse_one_shot(stages, comp)
    res = _analyse_chain(stages, comp)
    from .regulator import is_regulator, regulator_facts
    if res.supported and is_regulator(stages[0]):
        try:
            res.regulator = regulator_facts(stages[0])
        except Exception:                                    # advisory only
            res.regulator = None
        if res.regulator and res.regulator["trough_ok"] is False:
            r = res.regulator
            res.flags.append(f"Dropout: when the input dips to {r['vin'] - r['ripple_in']:.3g} V on the ripple troughs "
                             f"the output falls to {r['vout_trough']:.3g} V, so regulation is lost there.")
    return res


def _analyse_adc(stages: list[Stage]) -> Analysis:
    """A chain ending in a flash ADC: the chain before it is analysed as usual, then its output level at the
    converter's input is turned into codes. The comparators' inputs draw no current, so they do not load it."""
    adc, sub = stages[-1], list(stages[:-1])
    try:
        comp_sub = compose(sub)
    except Exception as e:
        return Analysis(False, f"the chain before the ADC could not be composed ({e})")
    from .oscillators import OSCILLATORS, model_for
    direct = None
    if len(sub) == 1 and sub[0].name in OSCILLATORS:         # a generator straight into the ADC
        try:
            sig = model_for(sub[0].name, sub[0].args)
        except Exception as e:
            return Analysis(False, f"the generator's output could not be worked out ({type(e).__name__}: {e})")
        w = sig.wave()
        direct = (max(w), min(w))
        res = Analysis(True, lines=[f"stage 1 ({sub[0].name}) makes its own signal: {sig.shape} at {fmt(sig.f0, 'Hz')}, "
                                    f"average {fmt(sig.dc, 'V')}"] + [f"note: {n}" for n in sig.notes])
    else:
        res = analyse(sub, comp_sub)
    if not res.supported:
        return res
    import inspect
    from agent.circuits.flash_adc import flash_adc
    params = inspect.signature(flash_adc).parameters
    bits = int(adc.args.get("bits", params["bits"].default))
    vref = float(adc.args.get("reference_voltage", params["reference_voltage"].default))
    codes, lsb = 2 ** bits, vref / 2 ** bits
    note = None
    if direct:
        hi, lo = direct
    elif res.oscillator:
        hi, lo = res.oscillator["out_hi"], res.oscillator["out_lo"]
    else:
        nl = comp_sub.netlist
        try:
            drv = find_driver(nl)
            sysm = System(nl, drv)
            dx, dy = comp_sub.offsets[-1]
            o = sub[-1].ports.outputs[0].node
            out_node = (o[0] + dx, o[1] + dy)
            freqs = drv.grid()
            mags = [abs(sysm.v(sysm.solve(f), out_node)) for f in freqs]
            k = max(range(len(mags)), key=mags.__getitem__)
            peak = drv.amp * mags[k]
            src = nl.elements[drv.index]
            bias = float(src.tail[3]) if src.type == "R" and len(src.tail) > 3 else 0.0
            if sysm.op is not None:
                dc = sysm.op.v(out_node)
            else:
                dc = bias * abs(sysm.v(sysm.solve(1e-6), out_node))
            hi, lo = dc + peak, dc - peak
            if drv.sweep:
                note = f"taken at {fmt(freqs[k], 'Hz')}, where the chain passes the most of the sweep"
        except Exception as e:                               # advisory only
            return Analysis(False, f"the signal reaching the ADC could not be worked out ({type(e).__name__}: {e})")

    def code(v):
        return min(max(int(math.floor(v / lsb + 1e-9)), 0), codes - 1)

    c_lo, c_hi = code(lo), code(hi)
    used = (min(hi, vref) - max(lo, 0.0)) / vref if hi > lo else 0.0
    lines = [f"stage {len(stages)} (flash_adc): {bits}-bit, reference {fmt(vref, 'V')}, so one step is {fmt(lsb, 'V')} "
             f"and the input range is 0 V to {fmt(vref, 'V')}",
             f"the signal at its input swings {lo:.3g} V to {hi:.3g} V"
             + (f" ({note})" if note else "") + f", which reads as codes {c_lo} to {c_hi} of 0 to {codes - 1}"]
    flags = list(res.flags)
    if hi > vref + 1e-9:
        flags.append(f"Clipping: the input rises to {hi:.3g} V, above the ADC's {fmt(vref, 'V')} full scale, so the "
                     f"top code {codes - 1} saturates.")
    if lo < -1e-9:
        flags.append(f"Clipping: the input falls to {lo:.3g} V, below the ADC's 0 V floor (it only reads positive "
                     f"voltages), so the bottom of the wave reads as code 0.")
    elif hi - lo < 0.05 * lsb:
        lines[-1] = (f"the signal at its input is essentially a DC level of {0.5 * (hi + lo):.4g} V"
                     + (f" ({note})" if note else "") + f", which reads as code {c_lo} of 0 to {codes - 1}")
    elif 0 < used < 0.25:
        flags.append(f"Resolution: the signal uses only {used:.0%} of the ADC's range, about "
                     f"{max(math.log2(max(c_hi - c_lo + 1, 1)), 0):.1f} of its {bits} bits.")
    res.lines = list(res.lines) + lines
    res.flags = flags
    res.adc = dict(bits=bits, vref=vref, lsb=lsb, lo=lo, hi=hi, code_lo=c_lo, code_hi=c_hi, used=used,
                   clips=any(f.startswith("Clipping") for f in flags))
    return res


def _analyse_oscillator(stages: list[Stage], comp: Composite, sig=None) -> Analysis:
    """Chain that starts with an oscillator: the oscillator becomes an ideal source at its output.

    The linear analysis runs at the waveform's fundamental; the peaks at the op-amp outputs are then
    rebuilt from the first 64 harmonics, since a triangle or sawtooth is not a sine.
    """
    from .oscillators import HARMONICS, model_for
    try:
        sig = sig if sig is not None else model_for(stages[0].name, stages[0].args)
    except Exception as e:                                   # advisory only
        return Analysis(False, f"the oscillator's frequency and amplitude could not be worked out "
                               f"({type(e).__name__}: {e})")
    if len(stages) < 2:
        return Analysis(False, "an oscillator on its own has nothing after it to analyse")
    x, y = stages[0].ports.outputs[0].node
    a1 = sig.fundamental
    if sig.r_out:                                            # source behind its output resistance
        text = (f"$ 1 1e-05 10 57 5.0\nR {x - 64} {y} {x - 80} {y} 0 1 {sig.f0!r} {a1!r} {sig.dc!r}\n"
                f"r {x - 64} {y} {x} {y} 0 {sig.r_out!r}\nO {x} {y} {x + 48} {y} 0\n")
    else:
        text = (f"$ 1 1e-05 10 57 5.0\nR {x} {y} {x + 16} {y} 0 1 {sig.f0!r} {a1!r} {sig.dc!r}\n"
                f"O {x} {y} {x + 48} {y} 0\n")
    from . import dump as _dump
    sur_nl = _dump.parse(text)
    from .ports import infer
    sur = Stage(stages[0].name, dict(stages[0].args), sur_nl, infer(sur_nl), [], None)    # the surrogate has a plain source and an `O`
    chain = [sur] + list(stages[1:])
    comp_s = compose(chain)
    res = _analyse_chain(chain, comp_s)
    if not res.supported:
        return res
    nl_s = comp_s.netlist
    drv = find_driver(nl_s)
    sysm = System(nl_s, drv)
    coeffs = sig.harmonics(HARMONICS)
    freqs = [sig.f0 * (k + 1) for k in range(HARMONICS)]
    dx, dy = comp_s.offsets[-1]
    o = chain[-1].ports.outputs[0].node
    out_node = (o[0] + dx, o[1] + dy)
    amp_nodes = [(i, terminals(e)[2], e) for i, e in enumerate(nl_s.elements) if e.type == "a"]
    nodes = [out_node] + [n for _, n, _ in amp_nodes]
    tf = {n: [] for n in dict.fromkeys(nodes)}
    for f in freqs:
        sol = sysm.solve(f)
        for n in tf:
            tf[n].append(sysm.v(sol, n))
    thetas = [2 * math.pi * i / 256 for i in range(256)]
    dc_gain = {}
    if sysm.op is None and sig.dc:                           # passive chain: DC level = source mean x gain at ~0 Hz
        sol0 = sysm.solve(1e-6)
        dc_gain = {n: sysm.v(sol0, n).real for n in tf}

    def synth(n):
        dc = sysm.op.v(n) if sysm.op is not None else sig.dc * dc_gain.get(n, 0.0)
        # Lanczos sigma factors: summing 64 harmonics of a square wave overshoots by ~9% (Gibbs) even through a
        # flat chain; the factors remove that ringing and barely touch smooth waveforms
        sig_k = [1.0 if k == 0 else math.sin(math.pi * k / (HARMONICS + 1)) / (math.pi * k / (HARMONICS + 1))
                 for k in range(1, HARMONICS + 1)]
        vals = [dc + sum((sg * c * h * complex(math.cos(k * th), math.sin(k * th))).real
                         for k, (sg, c, h) in enumerate(zip(sig_k, coeffs, tf[n]), 1)) for th in thetas]
        return max(vals), min(vals), dc

    stage_of = dict(enumerate(comp_s.owners))
    lines = [l for l in res.lines if not l.startswith("op-amp in stage")]
    flags = [f for f in res.flags if not f.startswith(("Clipping: the op-amp in stage",
                                                        "Headroom: the op-amp in stage"))]
    headroom = []
    head = [(sig.intro + ": " if sig.intro else
             f"stage 1 ({stages[0].name}) is a supply with no signal input, so it drives the chain: "
             if sig.shape in ("rectified", "dc_ripple") else
             f"stage 1 ({stages[0].name}) is an oscillator with no signal input, "
             "so it drives the chain: ")
            + (f"output ripple at {fmt(sig.f0, 'Hz')}, " if sig.shape in ("rectified", "dc_ripple")
               else f"{sig.shape} wave at {fmt(sig.f0, 'Hz')}, ")
            + (f"swinging {fmt(sig.v_low, 'V')} to {fmt(sig.v_high, 'V')}, high for {sig.duty:.1%} of each period"
               if sig.shape == "square" else
               f"averaging {fmt(sig.dc, 'V')} and swinging {fmt(sig.v_low, 'V')} to {fmt(sig.v_high, 'V')}"
               if sig.shape in ("rectified", "dc_ripple") else f"peaks +/-{fmt(sig.v_peak, 'V')}")
            + (" (approximate)" if sig.approximate else ""),
            "the chain below is analysed at that frequency, with the oscillator replaced by an ideal source "
            + ("(a logic-style output has a finite on-resistance, so a later stage that loads it heavily would "
               "pull the levels in)" if sig.shape == "square" else
               "(a later stage that draws current from it would pull the level down, which is not modelled)"
               if sig.shape in ("rectified", "dc_ripple") else
               "(its output is an op-amp output, so later stages do not load it)")]
    head += [f"note: {n}" for n in sig.notes]
    mag = [abs(c) for c in coeffs]
    harm = [k + 1 for k in range(HARMONICS) if mag[k] > 0.02 * mag[0] and k > 0][:6]
    if harm:
        head.append("harmonics in the oscillator's own output (relative to the fundamental): "
                    + ", ".join(f"{k}x {mag[k - 1] / mag[0]:.2g}" for k in harm))
    h_out = tf[out_node]
    g1 = abs(h_out[0])
    thd = math.sqrt(sum((mag[k] * abs(h_out[k])) ** 2 for k in range(1, HARMONICS))) / max(mag[0] * g1, 1e-30)
    hi, lo, dc = synth(out_node)
    head.append(f"gain of the chain at {fmt(sig.f0, 'Hz')}: {g1:.3g}; the steady-state output swings "
                f"{lo:.3g} V to {hi:.3g} V (first {HARMONICS} harmonics summed)"
                + (f", and its harmonic content relative to its fundamental is {thd * 100:.2g}%"
                   if sig.shape != "sine" else ""))
    for (i, node, e) in amp_nodes:
        lim = min(abs(float(e.tail[0])), abs(float(e.tail[1]))) if len(e.tail) >= 2 else None
        hi_n, lo_n, dc_n = synth(node)
        peak = max(abs(hi_n), abs(lo_n))
        sk = stage_of.get(i, -1) + 1
        txt = f"op-amp in stage {sk}: peak output {fmt(peak, 'V')} for this waveform"
        if abs(dc_n) > 0.05:
            txt += f" (including {fmt(abs(dc_n), 'V')} of DC)"
        if lim:
            txt += f" vs +/-{fmt(lim, 'V')} limit"
            if peak > 0.9 * lim:
                headroom.append((peak, lim))
            if peak > lim:
                flags.append(f"Clipping: the op-amp in stage {sk} would clip ({fmt(peak, 'V')} peak vs "
                             f"+/-{fmt(lim, 'V')} limit).")
            elif peak > 0.9 * lim:
                flags.append(f"Headroom: the op-amp in stage {sk} is within 10% of its limit "
                             f"({fmt(peak, 'V')} vs +/-{fmt(lim, 'V')}).")
        lines.append(txt)
    if g1 * sig.fundamental < 0.02 * sig.fundamental or g1 < 0.05:
        flags.append(f"Attenuation: the chain passes only {g1:.2g}x of the oscillator's {fmt(sig.f0, 'Hz')} signal, "
                     f"so very little of it reaches the output.")
    res.lines = head + [l for l in lines if not l.startswith("stage 1 (")]
    res.flags = flags
    res.headroom = headroom
    res.source_amp = None                                   # the oscillator's size is not adjustable here
    res.oscillator = dict(name=stages[0].name, shape=sig.shape, f0=sig.f0, v_peak=sig.v_peak, intro=sig.intro,
                          v_low=sig.v_low, v_high=sig.v_high, duty=sig.duty,
                          approximate=sig.approximate, gain=g1, out_hi=hi, out_lo=lo, thd=thd, notes=sig.notes,
                          clips=any(f.startswith("Clipping") for f in flags))
    return res


def _analyse_one_shot(stages: list[Stage], comp: Composite) -> Analysis:
    """Chain that starts with a 555 monostable: one pulse per trigger, so there is no steady state to solve.

    Reports the pulse (width, height) and the chain's gain at the pulse's own rate 1/(2T), as a rough guide to
    how much of the pulse gets through.
    """
    from .oscillators import one_shot
    try:
        info = one_shot(stages[0].args)
    except Exception as e:
        return Analysis(False, f"the one-shot's pulse could not be worked out ({type(e).__name__}: {e})")
    if len(stages) < 2:
        return Analysis(False, "a one-shot on its own has nothing after it to analyse")
    f_eq = 1.0 / (2.0 * info["width"])
    x, y = stages[0].ports.outputs[0].node
    text = f"$ 1 1e-05 10 57 5.0\nR {x} {y} {x + 16} {y} 0 1 {f_eq!r} 1.0 0.0\nO {x} {y} {x + 48} {y} 0\n"
    from . import dump as _dump
    from .ports import ports_for
    sur_nl = _dump.parse(text)
    sur = Stage(stages[0].name, dict(stages[0].args), sur_nl, ports_for(stages[0].name, sur_nl), [], None)
    chain = [sur] + list(stages[1:])
    res = _analyse_chain(chain, compose(chain))
    gain = res.gain if res.supported else None
    res = Analysis(False, "the chain starts with a one-shot, which fires one pulse per trigger, so there is no "
                          "steady-state signal to measure; only the pulse and a rough gain were computed",
                   [f"stage 1 ({stages[0].name}) is a 555 one-shot: after a trigger its output goes to "
                    f"{fmt(info['vcc'], 'V')} for T = 1.1RC = {fmt(info['width'], 's')}, then returns to 0 V"]
                   + ([f"the rest of the chain has a gain of {gain:.3g} at {fmt(f_eq, 'Hz')} (the pulse's own rate, "
                       f"1/(2T)): a rough guide to how much of the pulse gets through"] if gain is not None else []),
                   [f for f in (res.flags if res.supported else []) if f.startswith(("Attenuation", "Loading"))])
    res.oneshot = dict(width=info["width"], vcc=info["vcc"], f_eq=f_eq, gain=gain)
    return res


def _other_sources(nl, comp, drv, out_node, flags) -> None:
    """A later stage can keep a second input source (a summing amplifier's other input). The response above is for
    the chain's own source alone, so say what each leftover source adds at the output."""
    names = {"1": "sine", "2": "square", "3": "triangle", "4": "sawtooth", "5": "pulse"}
    for p in infer(nl).inputs:
        if p.element == drv.index:
            continue
        e = nl.elements[p.element]
        if e.type != "R" or len(e.tail) < 3:
            continue
        try:
            other = Driver(p.element, p.node, float(e.tail[2]), None, float(e.tail[1]))
            sysm = System(nl, other)
            gain = abs(sysm.v(sysm.solve(other.f0), out_node))
        except Exception:
            continue
        k = (comp.owners[p.element] + 1) if p.element < len(comp.owners) else 0
        wave = names.get(str(e.tail[0]), "periodic")
        flags.append(f"Other sources: stage {k} still has its own {wave} source ({fmt(other.amp, 'V')} peak at "
                     f"{fmt(other.f0, 'Hz')}) that the response above leaves out; alone it would put about "
                     f"{other.amp * gain:.3g} V peak at the output (gain {gain:.3g}), so the real output is the sum "
                     f"of both signals.")


def _analyse_chain(stages: list[Stage], comp: Composite) -> Analysis:
    nl = comp.netlist
    for k, st_ in enumerate(stages):
        ai = comparator_stage(st_)
        if ai is not None:
            return _analyse_comparator(stages, comp, k, ai)
    if any(e.type in ("160", "L") for e in stages[0].nl.elements):
        res_static = _analyse_static(stages, comp)
        if res_static is not None:
            return res_static
    try:
        drv = find_driver(nl)
        System(nl, drv)                                  # raises if unsupported
    except NotAnalysable as e:
        why = str(e)
        if "did not converge" in why and any(st_.name == "linear_regulator" for st_ in stages):
            why += (" - for a chain with a regulator this usually means the voltage reaching it is below its "
                    "output plus dropout, or negative, so it cannot hold its set point")
        return Analysis(False, why)
    except (ValueError, IndexError) as e:                # malformed numbers etc.
        return Analysis(False, f"could not read source/element values: {e}")

    freqs = drv.grid()
    dx, dy = comp.offsets[-1]
    o = stages[-1].ports.outputs[0].node
    out_node = (o[0] + dx, o[1] + dy)
    amp_nodes = [(i, terminals(e)[2], e) for i, e in enumerate(nl.elements) if e.type == "a"]
    join_nodes = [j[0] for j in comp.joins]
    sysm0 = System(nl, drv)
    dev_data = small_signal(nl, sysm0.op) if sysm0.op is not None else []
    dev_nodes = [p_ for _k, _e, pts, _J, _c in dev_data for p_ in pts]
    try:
        o_nodes = [(e.x1, e.y1) for e in nl.elements if e.type == "O"]
        curves = _curve(nl, drv, freqs, [out_node] + join_nodes + [n for _, n, _ in amp_nodes] + o_nodes
                        + dev_nodes)
    except NotAnalysable as e:
        return Analysis(False, str(e))

    mags = [abs(v) for v in curves[out_node]]
    m = metrics(freqs, mags)
    lines, flags, loaded, exp_gain_out, bm = [], [], [], None, None
    worsts: list[float] = []
    headroom: list = []
    interacts = False
    if m.sloping:
        lines.append(f"shape: {m.shape}; passband gain and -3 dB corners are not meaningful")
    else:
        band = (f"-3 dB band {fmt(m.lo, 'Hz') if m.lo else 'from low end'} to "
                f"{fmt(m.hi, 'Hz') if m.hi else 'high end'}")
        if m.stop is not None and m.lo is None and m.hi is None:
            band = (f"stop band {fmt(m.stop[0], 'Hz')} to {fmt(m.stop[1], 'Hz')} (-3 dB edges), deepest near "
                    f"{fmt(m.f_notch, 'Hz')} ({depth_text(m.depth_db)})")
        if m.stop is not None and (m.lo or m.hi):
            band += (f"; notch near {fmt(m.f_notch, 'Hz')} ({fmt(m.stop[0], 'Hz')} to {fmt(m.stop[1], 'Hz')}, "
                     f"{depth_text(m.depth_db)})")
        lines.append(f"shape: {m.shape}; passband gain {m.peak:.3g} (peak near {fmt(m.f_peak, 'Hz')}); {band}")
    lines.append(f"driving source: {fmt(drv.amp, 'V')} peak, "
                 + (f"sweeping {fmt(drv.sweep[0], 'Hz')} to {fmt(drv.sweep[1], 'Hz')}" if drv.sweep
                    else f"fixed {fmt(drv.f0, 'Hz')}"))

    # --- each stage on its own (standalone, its own source) vs. the chain ---------------
    alone = [_stage_metrics(s) for s in stages]
    for k, a in enumerate(alone, 1):
        if a is None:
            lines.append(f"stage {k} ({stages[k - 1].name}) alone: not analysed")
        else:
            c = []
            if a.lo:
                c.append(f"lower corner {fmt(a.lo, 'Hz')}")
            if a.hi:
                c.append(f"upper corner {fmt(a.hi, 'Hz')}")
            if a.stop is not None:
                c.append(f"stop band {fmt(a.stop[0], 'Hz')} to {fmt(a.stop[1], 'Hz')}")
            lines.append(f"stage {k} ({stages[k - 1].name}) alone: {a.shape}"
                         + ("" if a.sloping else f", passband gain {a.peak:.3g}")
                         + (", " + ", ".join(c) if c else ""))
    if all(a is not None and not a.sloping for a in alone) and not m.sloping:
        exp_gain = math.prod(a.peak for a in alone)
        exp_gain_out = exp_gain
        los = [a.lo for a in alone if a.lo]
        his = [a.hi for a in alone if a.hi]
        if any(a.stop is not None for a in alone) or m.stop is not None:
            los = his = []          # a notch reshapes the response by design: corners are not a loading symptom
        if abs(m.peak / exp_gain - 1) > TOL:
            interacts = True
            flags.append(f"Gain: {m.peak:.3g} overall, but the stages on their own would give "
                         f"{exp_gain:.3g} ({m.peak / exp_gain:.2f}x), because they load each other.")
        for label, got, exp in (("lower", m.lo, max(los) if los else None),
                                ("upper", m.hi, min(his) if his else None)):
            if exp is None:
                continue
            if got is None:
                interacts = True
                flags.append(f"Cutoff: the {label} -3 dB corner expected near {fmt(exp, 'Hz')} (from the "
                             "stages on their own) is missing from the chain response.")
            elif abs(got / exp - 1) > TOL:
                interacts = True
                flags.append(f"Cutoff: the {label} -3 dB corner is {fmt(got, 'Hz')} in the chain but "
                             f"{fmt(exp, 'Hz')} for the stage on its own ({got / exp - 1:+.0%}).")

    # --- loading at each junction: signal at stage k's output with vs. without later stages
    for k, node in enumerate(join_nodes, 1):
        try:
            sub = compose(stages[:k])
            sd = find_driver(sub.netlist)
            prefix = _curve(sub.netlist, sd, freqs, [node])[node]
        except (NotAnalysable, ValueError):
            continue
        pm = [abs(v) for v in prefix]
        pk = max(pm)
        if pk <= 0:
            continue
        ratios = [abs(f_) / p for f_, p in zip(curves[node], pm) if p >= 0.5 * pk]
        if ratios:
            worst = min(ratios)
            worsts.append(worst)
            lines.append(f"junction {k} (stage {k} -> {k + 1}): signal at stage {k}'s output is "
                         f"{worst:.2f}x what it would be unloaded (worst case within its passband)")
            if worst < 1 - TOL:
                loaded.append(k)
                interacts = True
                flags.append(f"Loading: stage {k + 1} loads stage {k}, so stage {k}'s output falls to "
                             f"{worst:.2f}x of its unloaded level ({20 * math.log10(worst):.1f} dB).")

    # --- op-amp output vs. its limit, for the real driving source ------------------------
    stage_of = {}
    for i in range(len(comp.owners)):
        stage_of[i] = comp.owners[i]
    for (i, node, e) in amp_nodes:
        lim = min(abs(float(e.tail[0])), abs(float(e.tail[1]))) if len(e.tail) >= 2 else None
        vm = [abs(v) for v in curves[node]]
        if drv.sweep:
            lo_i = [j for j, f in enumerate(freqs) if drv.sweep[0] <= f <= drv.sweep[1]]
            peak = drv.amp * max(vm[j] for j in lo_i)
        else:
            peak = drv.amp * abs(System(nl, drv).v(System(nl, drv).solve(drv.f0), node))
        sk = stage_of.get(i, -1) + 1
        dc_level = sysm0.op.v(node) if sysm0.op is not None else 0.0
        if abs(dc_level) > 0.05:
            peak = peak + abs(dc_level)          # DC offset and signal add on one half-cycle
        txt = f"op-amp in stage {sk}: peak output {fmt(peak, 'V')} for this source"
        if abs(dc_level) > 0.05:
            txt += f" (including {fmt(abs(dc_level), 'V')} of DC)"
        if lim:
            txt += f" vs +/-{fmt(lim, 'V')} limit"
            if peak > 0.9 * lim:
                headroom.append((peak, lim))
            if peak > lim:
                flags.append(f"Clipping: the op-amp in stage {sk} would clip ({fmt(peak, 'V')} peak vs "
                             f"+/-{fmt(lim, 'V')} limit).")
            elif peak > 0.9 * lim:
                flags.append(f"Headroom: the op-amp in stage {sk} is within 10% of its limit "
                             f"({fmt(peak, 'V')} vs +/-{fmt(lim, 'V')}).")
        lines.append(txt)
    _other_sources(nl, comp, drv, out_node, flags)
    if dev_data:
        _device_report(nl, comp, dev_data, sysm0.op, curves, freqs, drv, lines, flags)
    if interacts and len(stages) > 1:
        bm = _what_if_buffered(stages, freqs, drv, m, flags, lines)
    peaks = {n: _peak(drv, freqs, curves[n]) for n in o_nodes}
    res = Analysis(True, "", lines, flags, None if m.sloping else m.peak, m.lo, m.hi,
                   m.sloping, loaded, m.shape, (bm.peak, bm.lo, bm.hi) if bm else None,
                   exp_gain_out, peaks)
    res.worst_load = min(worsts) if worsts else None
    res.stop, res.f_notch, res.depth_db = m.stop, m.f_notch, m.depth_db
    res.source_amp = drv.amp
    res.headroom = headroom
    return res
