"""DC operating point and small-signal data for netlists with transistors, DACs and comparators.

Works on the legacy dialect only. Supported: r, l (short), c (open), w, g, R / v / 170 sources
(their DC part), L logic inputs, 160 analog switches, ideal op-amps (V+ = V-), NPN `t` and
N-channel `f` devices with Falstad's own equations:

  BJT (default model): Ebers-Moll, Is = 1e-13 A, Vt = 25.865 mV, betaR = 1, no Early effect.
  MOSFET: square law, Vt and beta from the file, no channel-length modulation, source and
          drain swap when the terminals reverse.

Anything else raises NotAnalysable. The Newton solver steps the sources up from zero so the
exponential junctions converge.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache

from . import dump
from .dump import Element, Netlist, Point, bjt_pins, mosfet_pins, switch2_pins, terminals


class NotAnalysable(Exception):
    pass


VT = 0.025865
IS = 1e-13
GMIN = 1e-12
G_CAP_LEAK = 1e-9
G_SHORT = 1e3          # an inductor at DC
SWITCH_THRESHOLD = 2.5
DC_TYPES = {"w", "g", "r", "c", "l", "a", "O", "170", "v", "R", "x", "t", "f", "L", "160", "d", "z"}
D_IS = 1.7143528192808883e-7     # Falstad's default diode model
D_N = 2.0
ZENER_DEFAULT_V = 5.6            # the "default-zener" model


# ---- device equations ----------------------------------------------------------------
def bjt_currents(vc: float, vb: float, ve: float, beta: float, pol: float = 1.0) -> tuple[float, float, float]:
    """Currents INTO the collector, base and emitter (Falstad default model); pol = -1 for a PNP."""
    vbe, vbc = pol * (vb - ve), pol * (vb - vc)
    ebe = math.exp(min(vbe / VT, 60.0))
    ebc = math.exp(min(vbc / VT, 60.0))
    cbe = IS * (ebe - 1) + GMIN * vbe
    cbc = IS * (ebc - 1) + GMIN * vbc
    ic = cbe - cbc - cbc          # betaR = 1
    ib = cbe / beta + cbc
    return pol * ic, pol * ib, -pol * (ic + ib)


def zener_voltage(e) -> float:
    """Breakdown voltage of a `d` (none) or `z` element: `z ... 0 fwdrop vz` or `z ... 2 modelName`."""
    if e.type != "z":
        return 0.0
    if int(e.flags) & 2:
        return ZENER_DEFAULT_V if "zener" in (e.tail[0] if e.tail else "") else 0.0
    return float(e.tail[1]) if len(e.tail) > 1 else ZENER_DEFAULT_V


def _exp_lin(x: float, cap: float = 40.0) -> float:
    """exp(x), continued linearly above `cap` so the slope never vanishes (keeps Newton's steps finite)."""
    return math.exp(x) if x <= cap else math.exp(cap) * (1.0 + x - cap)


def diode_current(vd: float, vz: float = 0.0) -> float:
    """Current from anode to cathode (Falstad's diode / zener model, with its gmin)."""
    coef = 1.0 / (D_N * VT)
    gmin = D_IS * 0.01
    if vd >= 0 or vz == 0:
        return D_IS * (_exp_lin(vd * coef) - 1.0) + gmin * vd
    zoff = vz - VT * math.log(0.005 / D_IS - 1.0)
    return (D_IS * (_exp_lin(vd * coef) - _exp_lin((-vd - zoff) / VT) - 1.0)) + gmin * vd


def mosfet_currents(vd: float, vg: float, vs: float, vt: float, beta: float,
                    pol: float = 1.0) -> tuple[float, float, float]:
    """Currents INTO the drain-terminal, gate and source-terminal; pol = -1 for a P-channel device."""
    if pol < 0:                                  # mirror image: negate every voltage and current
        return tuple(-x for x in mosfet_currents(-vd, -vg, -vs, vt, beta))
    d, s, sign = (vd, vs, 1.0) if vs <= vd else (vs, vd, -1.0)   # lower terminal acts as the source
    vgs, vds = vg - s, d - s
    gds = 1e-8
    if vgs < vt:
        ids = vds * gds
    elif vds < vgs - vt:
        ids = beta * ((vgs - vt) * vds - 0.5 * vds * vds)
    else:
        ids = 0.5 * beta * (vgs - vt) ** 2 + (vds - (vgs - vt)) * gds
    return sign * ids, 0.0, -sign * ids


def check_supported(nl: Netlist) -> None:
    if nl.dialect != "legacy":
        raise NotAnalysable("XML-format circuit")
    bad = sorted({e.type for e in nl.elements if e.type not in DC_TYPES})
    if bad:
        raise NotAnalysable(f"contains element types without a model: {bad}")
    for e in nl.elements:
        if e.type == "t" and (not e.tail or float(e.tail[0]) not in (1.0, -1.0)):
            raise NotAnalysable("unrecognised transistor polarity")


# ---- the operating point ---------------------------------------------------------------
@dataclass
class OperatingPoint:
    volts: dict[Point, float] = field(default_factory=dict)      # every known terminal point
    iterations: int = 0

    def v(self, pt: Point) -> float:
        return self.volts.get(pt, 0.0)


def _solve_real(A: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    A = [row[:] for row in A]
    b = b[:]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(A[r][c]))
        if abs(A[p][c]) < 1e-300:
            raise NotAnalysable("DC equations are singular (floating node?)")
        A[c], A[p], b[c], b[p] = A[p], A[c], b[p], b[c]
        piv = A[c][c]
        for r in range(c + 1, n):
            m = A[r][c] / piv
            if m:
                A[r] = [x - m * y for x, y in zip(A[r], A[c])]
                b[r] -= m * b[c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (b[r] - sum(A[r][j] * x[j] for j in range(r + 1, n))) / A[r][r]
    return x


def operating_point(nl: Netlist, ignore_amps: bool = False,
                    fixed: dict[Point, float] | None = None) -> OperatingPoint:
    return _op(nl.to_text(), ignore_amps, tuple(sorted((fixed or {}).items())))


@lru_cache(maxsize=64)
def _op_cached(text: str, ignore_amps: bool, fixed: tuple) -> OperatingPoint:
    return _compute(dump.parse(text), ignore_amps, dict(fixed))


def _op(text, ignore_amps, fixed):
    return _op_cached(text, ignore_amps, fixed)


def _compute(nl: Netlist, ignore_amps: bool, extra_fixed: dict[Point, float]) -> OperatingPoint:
    """Ideal op-amps first (V+ = V-). If Newton cannot settle (typically an op-amp that would have to leave its
    rails), solve again with each op-amp as a gain-1e5 stage limited to its rails, scaled up with the sources."""
    try:
        return _compute_once(nl, ignore_amps, extra_fixed, False)
    except _NoConvergence:
        if not any(e.type == "a" for e in nl.elements) or ignore_amps:
            raise NotAnalysable("the DC solution did not converge")
    try:
        return _compute_once(nl, ignore_amps, extra_fixed, True)
    except _NoConvergence:
        raise NotAnalysable("the DC solution did not converge")


class _NoConvergence(Exception):
    pass


def _compute_once(nl: Netlist, ignore_amps: bool, extra_fixed: dict[Point, float],
                  saturating: bool) -> OperatingPoint:
    check_supported(nl)
    parent: dict[Point, Point] = {}

    def find(p):
        parent.setdefault(p, p)
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p

    def union(a, b):
        parent[find(a)] = find(b)

    gnd = ("GND",)
    find(gnd)
    pins: list[tuple[Element, dict]] = []
    for e in nl.elements:
        if e.type == "t":
            pins.append((e, bjt_pins(e)))
        elif e.type == "f":
            pins.append((e, mosfet_pins(e)))
        elif e.type == "160":
            pins.append((e, switch2_pins(e)))
        elif e.type in ("d", "z"):
            pins.append((e, {"a": e.p1, "k": e.p2}))
        else:
            for t in terminals(e) or []:
                find(t)
        if e.type == "w":
            union(e.p1, e.p2)
        elif e.type == "g":
            union(e.p1, gnd)
    for _, pn in pins:
        for t in pn.values():
            find(t)

    ids: dict[Point, int] = {}

    def node(p):
        r = find(p)
        return None if r == find(gnd) else ids.setdefault(r, len(ids))

    # everything first so ids are stable
    for pt in list(parent):
        node(pt)

    # constraint list: (node_a, node_b, value) meaning V(a) - V(b) = value*scale (b None = ground)
    cons: list[tuple[int | None, int | None, float]] = []
    conds: list[tuple[int | None, int | None, float]] = []    # fixed conductances
    amps: list[tuple[int | None, int | None, int | None]] = []
    devices: list[tuple[str, Element, dict]] = []
    switches: list[tuple[Element, dict]] = []
    for e in nl.elements:
        t = e.type
        if t == "r":
            conds.append((node(e.p1), node(e.p2), 1.0 / float(e.tail[0])))
        elif t == "c":                      # a gigaohm of leakage: an integrator then drifts to a rail, as it would
            conds.append((node(e.p1), node(e.p2), G_CAP_LEAK))   # in the simulator, instead of leaving the node undefined
        elif t == "l":
            conds.append((node(e.p1), node(e.p2), G_SHORT))
        elif t == "R":
            wf = int(float(e.tail[0]))
            amp, bias = float(e.tail[2]), float(e.tail[3]) if len(e.tail) > 3 else 0.0
            cons.append((node(e.p1), None, (amp if wf == 0 else 0.0) + bias))
        elif t == "v":
            wf = int(float(e.tail[0]))
            amp, bias = float(e.tail[2]), float(e.tail[3]) if len(e.tail) > 3 else 0.0
            cons.append((node(e.p2), node(e.p1), (amp if wf == 0 else 0.0) + bias))
        elif t == "170":
            cons.append((node(e.p1), None, 0.0))
        elif t == "L":
            pos = int(float(e.tail[0]))
            hi = float(e.tail[2]) if len(e.tail) > 2 else 5.0
            lo = float(e.tail[3]) if len(e.tail) > 3 else 0.0
            cons.append((node(e.p1), None, hi if pos == 1 else lo))
        elif t == "a" and not ignore_amps:
            ts = terminals(e)
            inv, non = (ts[1], ts[0]) if int(e.flags) & 1 == 0 else (ts[0], ts[1])
            hi_, lo_ = (float(e.tail[0]), float(e.tail[1])) if len(e.tail) >= 2 else (1e3, -1e3)
            amps.append((node(inv), node(non), node(ts[2]), hi_, lo_))
    for pt, v in extra_fixed.items():
        cons.append((node(pt), None, v))
    for e, pn in pins:
        if e.type == "160":
            switches.append((e, pn))
        else:
            devices.append((e.type, e, pn))

    n = len(ids)
    k = len(cons) + len(amps)
    size = n + k

    def switch_states(volts: list[float]) -> list[bool]:
        out = []
        for e, pn in switches:
            c = node(pn["ctl"])
            out.append(volts[c] >= SWITCH_THRESHOLD if c is not None else False)
        return out

    def assemble(x: list[float], scale: float, hi_ctl: list[bool]):
        A = [[0.0] * size for _ in range(size)]
        F = [0.0] * size

        def g_stamp(a, b, g):
            va = x[a] if a is not None else 0.0
            vb_ = x[b] if b is not None else 0.0
            i = g * (va - vb_)
            for p, q, s in ((a, a, 1), (b, b, 1), (a, b, -1), (b, a, -1)):
                if p is not None and q is not None:
                    A[p][q] += s * g
            if a is not None:
                F[a] += i
            if b is not None:
                F[b] -= i

        for a, b, g in conds:
            g_stamp(a, b, g)
        for i in range(n):
            g_stamp(i, None, GMIN)
        for (e, pn), sel in zip(switches, hi_ctl):
            on, off = float(e.tail[0]), float(e.tail[1])
            g_stamp(node(pn["common"]), node(pn["post1"]), 1 / (on if sel else off))
            g_stamp(node(pn["common"]), node(pn["post2"]), 1 / (off if sel else on))
        for row, (a, b, val) in enumerate(cons):
            r = n + row
            va = x[a] if a is not None else 0.0
            vb_ = x[b] if b is not None else 0.0
            ik = x[r]
            if a is not None:
                A[a][r] += 1
                F[a] += ik
                A[r][a] += 1
            if b is not None:
                A[b][r] -= 1
                F[b] -= ik
                A[r][b] -= 1
            F[r] = va - vb_ - val * scale
        for j, (inv, non, out, hi_, lo_) in enumerate(amps):
            r = n + len(cons) + j
            ik = x[r]
            if out is not None:
                A[out][r] += 1
                F[out] += ik
            vi = x[inv] if inv is not None else 0.0
            vn = x[non] if non is not None else 0.0
            if saturating:                              # vo = mid + half tanh(G (v+ - v-) / half), rails scaled
                mid, half = 0.5 * (hi_ + lo_) * scale, max(0.5 * (hi_ - lo_) * scale, 1e-9)
                gain = 10.0 ** (1.0 + 4.0 * scale)               # the gain is ramped up with the sources
                u = max(min(gain * (vn - vi) / half, 300.0), -300.0)
                f, df = mid + half * math.tanh(u), gain / math.cosh(u) ** 2
                vo = x[out] if out is not None else 0.0
                if out is not None:
                    A[r][out] += 1
                if non is not None:
                    A[r][non] -= df
                if inv is not None:
                    A[r][inv] += df
                F[r] = vo - f
            else:
                if non is not None:
                    A[r][non] += 1
                if inv is not None:
                    A[r][inv] -= 1
                F[r] = vn - vi
        for kind, e, pn in devices:
            if kind in ("d", "z"):
                t3 = [node(pn["a"]), node(pn["k"])]
                vz = zener_voltage(e)
                fn = lambda v, vz=vz: (diode_current(v[0] - v[1], vz), -diode_current(v[0] - v[1], vz))
            elif kind == "t":
                t3 = [node(pn["c"]), node(pn["b"]), node(pn["e"])]
                beta = float(e.tail[3]) if len(e.tail) > 3 else 100.0
                pol = float(e.tail[0])
                fn = lambda v, beta=beta, pol=pol: bjt_currents(v[0], v[1], v[2], beta, pol)
            else:
                t3 = [node(pn["d"]), node(pn["g"]), node(pn["s"])]
                vt, beta = float(e.tail[0]), float(e.tail[1])
                pol = -1.0 if int(e.flags) & 1 else 1.0
                fn = lambda v, vt=vt, beta=beta, pol=pol: mosfet_currents(v[0], v[1], v[2], vt, beta, pol)
            v0 = [x[i] if i is not None else 0.0 for i in t3]
            cur = fn(v0)
            for ti, i in enumerate(t3):
                if i is not None:
                    F[i] += cur[ti]
            for tj, j in enumerate(t3):
                if j is None:
                    continue
                h = 1e-7
                vp, vm = v0[:], v0[:]
                vp[tj] += h
                vm[tj] -= h
                cp, cm = fn(vp), fn(vm)
                for ti, i in enumerate(t3):
                    if i is not None:
                        A[i][j] += (cp[ti] - cm[ti]) / (2 * h)
        return A, F

    nonlinear = bool(devices)
    steps = (60 if saturating else 24) if nonlinear else 1
    x = [0.0] * size
    iters = 0
    states = [False] * len(switches)
    resid = 0.0
    for step in range(1, steps + 1):
        scale = step / steps
        for _outer in range(4):                       # switch states settle in one or two passes
            for it in range(200):
                A, F = assemble(x, scale, states)
                dx = _solve_real(A, [-f for f in F])
                lim = max(abs(d) for d in dx[:n]) if n else 0.0
                damp = 1.0 if (not nonlinear or lim <= 0.7) else 0.7 / lim
                for kind_, e_, pn_ in devices:                       # keep every junction's step small
                    if kind_ in ("d", "z"):
                        pairs = [(node(pn_["a"]), node(pn_["k"]))]
                    elif kind_ == "t":
                        pairs = [(node(pn_["b"]), node(pn_["e"])), (node(pn_["b"]), node(pn_["c"]))]
                    else:
                        continue
                    for ia, ib in pairs:
                        dj = abs((dx[ia] if ia is not None else 0.0) - (dx[ib] if ib is not None else 0.0))
                        if dj * damp > 0.1:
                            damp = 0.1 / dj
                if saturating and it > 3:                             # backtrack if the step makes things worse
                    f0 = max(abs(f) for f in F)
                    for _bt in range(8):
                        xt = [xi + damp * di for xi, di in zip(x, dx)]
                        if max(abs(f) for f in assemble(xt, scale, states)[1]) <= f0 * (1 + 1e-9) or f0 < 1e-12:
                            break
                        damp *= 0.5
                x = [xi + damp * di for xi, di in zip(x, dx)]
                iters += 1
                resid = max(abs(f) for f in F) if F else 0.0
                if lim * damp < 1e-10 and max(abs(f) for f in F[:n]) < 1e-9:
                    break
                if not nonlinear and it >= 0:
                    break
            new_states = switch_states(x)
            if new_states == states:
                break
            states = new_states
        else:
            pass
    if nonlinear and (resid > 1e-3 or not all(math.isfinite(v) for v in x)):
        raise _NoConvergence()
    op = OperatingPoint(iterations=iters)
    for pt in list(parent):
        i = node(pt)
        op.volts[pt] = x[i] if i is not None else 0.0
    return op


def small_signal(nl: Netlist, op: OperatingPoint):
    """[(kind, element, terminal points (3), 3x3 Jacobian dI_i/dV_j)] for every t / f device,
    terminals ordered (collector, base, emitter) or (drain, gate, source)."""
    out = []
    for e in nl.elements:
        if e.type in ("d", "z"):
            pts = [e.p1, e.p2]
            vz = zener_voltage(e)
            fn = lambda v, vz=vz: (diode_current(v[0] - v[1], vz), -diode_current(v[0] - v[1], vz))
        elif e.type == "t":
            pn = bjt_pins(e)
            pts = [pn["c"], pn["b"], pn["e"]]
            beta = float(e.tail[3]) if len(e.tail) > 3 else 100.0
            pol = float(e.tail[0])
            fn = lambda v, beta=beta, pol=pol: bjt_currents(v[0], v[1], v[2], beta, pol)
        elif e.type == "f":
            pn = mosfet_pins(e)
            pts = [pn["d"], pn["g"], pn["s"]]
            vt, beta = float(e.tail[0]), float(e.tail[1])
            pol = -1.0 if int(e.flags) & 1 else 1.0
            fn = lambda v, vt=vt, beta=beta, pol=pol: mosfet_currents(v[0], v[1], v[2], vt, beta, pol)
        else:
            continue
        v0 = [op.v(p) for p in pts]
        m = len(pts)
        J = [[0.0] * m for _ in range(m)]
        h = 1e-7
        for j in range(m):
            vp, vm = v0[:], v0[:]
            vp[j] += h
            vm[j] -= h
            cp, cm = fn(vp), fn(vm)
            for i in range(m):
                J[i][j] = (cp[i] - cm[i]) / (2 * h)
        out.append((e.type, e, pts, J, fn(v0)))
    return out
