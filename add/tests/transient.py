"""Independent time-domain simulator used only by the tests (never by the agent).

It reads the same legacy netlist text the generators produce and integrates it with trapezoidal integration and
Newton iteration. Supported: w g r c a d 181 O. The op-amp is the CircuitJS one without bandwidth
(gain 1e5, output limited to its rails, smoothed with tanh so Newton behaves); the diode is the "default"
model; the lamp copies CircuitJS's LampElm. It exists so a generator's claimed frequency and amplitude
can be checked against a circuit simulation I did not derive them from.
"""
from __future__ import annotations

import math

import numpy as np

from agent.cascade import dump
from agent.cascade.dc import bjt_currents, diode_current, mosfet_currents, zener_voltage

DIODE_IS, DIODE_N, DIODE_VT = 1.7143528192808883e-7, 2.0, 0.025865
GAIN = 1e5


def _lamp_r(temp, nom_r):
    t = min(temp, 5390.0)
    return nom_r * (1.26104 - 4.90662 * math.sqrt(17.1839 / t - 0.00318794) - 7.8569 / (t - 187.56))


def _wave(wf: int, cycles: float) -> float:
    """CircuitJS rail waveforms (unit amplitude) at `cycles` periods of elapsed time: 1 sine, 2 square, 3 triangle,
    4 sawtooth."""
    w = (cycles % 1.0) * 2 * math.pi
    if wf == 2:
        return 1.0 if w <= math.pi else -1.0
    if wf == 3:
        return w * (2 / math.pi) - 1 if w < math.pi else 1 - (w - math.pi) * (2 / math.pi)
    if wf == 4:
        return w / math.pi - 1
    return math.sin(w)


def simulate(netlist: str, t_end: float, dt: float | None = None, probe_index: int | None = None,
             continuation: bool = False, gain: float = GAIN):
    """Return (times, voltages) of the node the O marker (or probe_index element's p1) sits on."""
    nl = dump.parse(netlist)
    els = nl.elements
    if dt is None:
        dt = float(nl.header.split()[2]) if nl.header else 5e-6
    parent: dict = {}

    def find(p):
        parent.setdefault(p, p)
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p

    gnd = ("GND",)
    find(gnd)
    for e in els:
        for t in dump.terminals(e) or []:
            find(t)
        if e.type == "w":
            parent[find(e.p1)] = find(e.p2)
        elif e.type == "g":
            parent[find(e.p1)] = find(gnd)
    ids: dict = {}

    def node(p):
        r = find(p)
        if r == find(gnd):
            return -1
        return ids.setdefault(r, len(ids))

    for e in els:                                    # fix numbering before sizing
        for t in dump.terminals(e) or []:
            node(t)
    n = len(ids)
    amps = [e for e in els if e.type == "a"]
    # (size is fixed below, once the rails are known)
    probe = next(e for e in els if e.type == "O") if probe_index is None else els[probe_index]
    pn = node(probe.p1)

    res = [(node(e.p1), node(e.p2), float(e.tail[0])) for e in els if e.type == "r"]
    caps = [[node(e.p1), node(e.p2), float(e.tail[0]), float(e.tail[1]), 0.0] for e in els if e.type == "c"]
    inds = [[node(e.p1), node(e.p2), float(e.tail[0]), float(e.tail[1]) if len(e.tail) > 1 else 0.0, 0.0]
            for e in els if e.type == "l"]                # [a, b, L, current, v_prev]
    dios = [(node(e.p1), node(e.p2)) for e in els if e.type == "d"]
    lamps = [dict(a=node(e.p1), b=node(e.p2), temp=float(e.tail[0]), pw=float(e.tail[1]),
                  nv=float(e.tail[2]), warm=float(e.tail[3]), cool=float(e.tail[4])) for e in els if e.type == "181"]
    timers = []
    for e in els:
        if e.type == "165":
            ts = dump.terminals(e)
            pins = dict(zip(dump.TIMER_PINS, (node(t) for t in ts)))
            timers.append(dict(pins=pins, ground=bool(int(e.flags) & 4), reset=bool(int(e.flags) & 6), out=False))
    bjts = []
    for e in els:
        if e.type == "t":
            pn_ = dump.bjt_pins(e)
            bjts.append(dict(n=[node(pn_["c"]), node(pn_["b"]), node(pn_["e"])], pol=float(e.tail[0]),
                             beta=float(e.tail[3]) if len(e.tail) > 3 else 100.0))
    fets = []
    for e in els:
        if e.type == "f":
            pn_ = dump.mosfet_pins(e)
            fets.append(dict(n=[node(pn_["d"]), node(pn_["g"]), node(pn_["s"])], vt=float(e.tail[0]),
                             beta=float(e.tail[1]), pol=-1.0 if int(e.flags) & 1 else 1.0))
    for e in els:
        if e.type == "z":
            fets.append(dict(n=[node(e.p1), node(e.p2)], vz=zener_voltage(e)))
    vsrcs = []
    for e in els:
        if e.type == "v":
            t_ = [float(x) for x in e.tail]
            vsrcs.append(dict(a=node(e.p1), b=node(e.p2), wf=int(t_[0]), f=t_[1], amp=t_[2],
                              bias=t_[3] if len(t_) > 3 else 0.0, duty=t_[5] if len(t_) > 5 else 0.5))
    rails = []                                         # (node, volts): DC rails and logic inputs
    for e in els:
        if e.type == "R":
            wf = int(float(e.tail[0]))
            bias = float(e.tail[3]) if len(e.tail) > 3 else 0.0
            if wf == 0:
                rails.append((node(e.p1), float(e.tail[2]) + bias))
            else:                                              # periodic source: (freq, amp, bias, waveform)
                rails.append((node(e.p1), (float(e.tail[1]), float(e.tail[2]), bias, wf)))
        elif e.type == "L":
            hi = float(e.tail[2]) if len(e.tail) > 2 else 5.0
            lo = float(e.tail[3]) if len(e.tail) > 3 else 0.0
            rails.append((node(e.p1), hi if int(float(e.tail[0])) == 1 else lo))
    ampd = []
    for e in amps:
        ts = dump.terminals(e)
        inv, non = (ts[1], ts[0]) if int(e.flags) & 1 == 0 else (ts[0], ts[1])
        ampd.append((node(inv), node(non), node(ts[2]), (float(e.tail[0]), float(e.tail[1]))))

    gates = []
    for e in els:
        if e.type in dump.GATE_TYPES:
            ts = [node(t) for t in dump.terminals(e)]
            gates.append(dict(ins=ts[:-1], out=ts[-1], kind=int(e.type), high=float(e.tail[2]) if len(e.tail) > 2 else 5.0))
    size = n + len(amps) + len(rails) + len(vsrcs) + len(gates)

    def stamp_g(M, a, b, g):
        if a >= 0:
            M[a, a] += g
        if b >= 0:
            M[b, b] += g
        if a >= 0 and b >= 0:
            M[a, b] -= g
            M[b, a] -= g

    base = np.zeros((size, size))
    for a, b, r in res:
        stamp_g(base, a, b, 1.0 / r)
    for a, b, c, *_ in caps:
        stamp_g(base, a, b, 2 * c / dt)
    for a, b, L_, *_ in inds:
        stamp_g(base, a, b, dt / (2 * L_))

    for tm in timers:
        pn_ = tm["pins"]
        g_ = pn_["gnd"] if tm["ground"] else -1
        tm["g"] = g_
        stamp_g(base, pn_["vin"], pn_["ctl"], 1 / 5000.0)
        stamp_g(base, pn_["ctl"], g_, 1 / 10000.0)

    x = np.zeros(size)
    times, out = [], []
    steps = int(round(t_end / dt))
    for k in range(steps):
        rhs0 = np.zeros(size)
        for cp in caps:                               # trapezoidal companion current source
            a, b, c, vprev, iprev = cp
            ieq = 2 * c / dt * vprev + iprev
            if a >= 0:
                rhs0[a] += ieq
            if b >= 0:
                rhs0[b] -= ieq
        for ip in inds:                               # trapezoidal inductor: i = g v + (i_prev + g v_prev)
            a, b, L_, iprev, vprev = ip
            ieq = iprev + dt / (2 * L_) * vprev
            if a >= 0:
                rhs0[a] -= ieq
            if b >= 0:
                rhs0[b] += ieq
        def v_(i):
            return x[i] if i >= 0 else 0.0
        for tm in timers:                              # TimerElm.startIteration
            pn_ = tm["pins"]
            g_ = v_(tm["g"])
            o_ = v_(pn_["out"]) > v_(pn_["vin"]) / 2
            if v_(pn_["th"]) > v_(pn_["ctl"]):
                o_ = False
            if v_(pn_["ctl"]) / 2 > v_(pn_["tr"]):
                o_ = True
            if tm["reset"] and v_(pn_["rst"]) < 0.7 + g_:
                o_ = False
            tm["out"] = o_
        lamp_g = []
        for lp in lamps:
            nom_r = lp["nv"] ** 2 / lp["pw"]
            lamp_g.append(1.0 / _lamp_r(lp["temp"], nom_r))
        def newton(x, gain, iters):
            for it in range(iters):
                M = base.copy()
                rhs = rhs0.copy()
                for lp, g in zip(lamps, lamp_g):
                    stamp_g(M, lp["a"], lp["b"], g)
                for tm in timers:
                    pn_ = tm["pins"]
                    if not tm["out"]:
                        stamp_g(M, pn_["dis"], tm["g"], 1 / 10.0)
                    stamp_g(M, pn_["vin"] if tm["out"] else tm["g"], pn_["out"], 1.0)
                for j, (rn, rv) in enumerate(rails):
                    row = n + len(amps) + j
                    if rn >= 0:
                        M[rn, row] += 1.0
                        M[row, rn] += 1.0
                    rhs[row] += rv if not isinstance(rv, tuple) else rv[2] + rv[1] * _wave(rv[3], rv[0] * (k + 1) * dt)
                for a, b in dios:
                    va = x[a] if a >= 0 else 0.0
                    vb = x[b] if b >= 0 else 0.0
                    vd = min(va - vb, 1.0)
                    ex = math.exp(vd / (DIODE_N * DIODE_VT))
                    gd = DIODE_IS * ex / (DIODE_N * DIODE_VT) + 1e-12
                    ieq = DIODE_IS * (ex - 1.0) - gd * vd
                    stamp_g(M, a, b, gd)
                    if a >= 0:
                        rhs[a] -= ieq
                    if b >= 0:
                        rhs[b] += ieq
                for j, vs_ in enumerate(vsrcs):
                    row = n + len(amps) + len(rails) + j
                    w_ = 2 * math.pi * vs_["f"] * (k + 1) * dt
                    if vs_["wf"] == 0:
                        val = vs_["amp"] + vs_["bias"]
                    elif vs_["wf"] == 1:
                        val = vs_["bias"] + vs_["amp"] * math.sin(w_)
                    else:                                              # square: +amp for `duty` of the period
                        val = vs_["bias"] + (vs_["amp"] if (w_ % (2 * math.pi)) <= 2 * math.pi * vs_["duty"] else -vs_["amp"])
                    if vs_["b"] >= 0:
                        M[vs_["b"], row] += 1.0
                        M[row, vs_["b"]] += 1.0
                    if vs_["a"] >= 0:
                        M[vs_["a"], row] -= 1.0
                        M[row, vs_["a"]] -= 1.0
                    rhs[row] += val
                for j, g_ in enumerate(gates):                    # ideal logic: output follows inputs vs half the high level
                    row = n + len(amps) + len(rails) + len(vsrcs) + j
                    bits_ = [(x[i] if i >= 0 else 0.0) > g_["high"] / 2 for i in g_["ins"]]
                    if g_["kind"] == 154:
                        f_ = sum(bits_) % 2 == 1
                    elif g_["kind"] in (150, 151):
                        f_ = all(bits_)
                    else:
                        f_ = any(bits_)
                    if g_["kind"] in (151, 153):
                        f_ = not f_
                    if g_["out"] >= 0:
                        M[g_["out"], row] += 1.0
                        M[row, g_["out"]] += 1.0
                    rhs[row] += g_["high"] if f_ else 0.0
                for bj in bjts + fets:
                    t3 = bj["n"]
                    v0 = [x[i] if i >= 0 else 0.0 for i in t3]
                    if "vz" in bj:
                        dev = lambda *v, bj=bj: (diode_current(v[0] - v[1], bj["vz"]), -diode_current(v[0] - v[1], bj["vz"]))
                    elif "vt" in bj:
                        dev = lambda *v, bj=bj: mosfet_currents(*v, bj["vt"], bj["beta"], bj["pol"])
                    else:
                        dev = lambda *v, bj=bj: bjt_currents(*v, bj["beta"], bj["pol"])
                    cur = dev(*v0)
                    h = 1e-7
                    for tj, j in enumerate(t3):
                        if j < 0:
                            continue
                        vp = v0[:]
                        vp[tj] += h
                        cp = dev(*vp)
                        for ti, i in enumerate(t3):
                            if i >= 0:
                                g = (cp[ti] - cur[ti]) / h
                                M[i, j] += g
                                rhs[i] += g * v0[tj]
                    for ti, i in enumerate(t3):
                        if i >= 0:
                            rhs[i] -= cur[ti]
                for j, (inv, non, o, rail) in enumerate(ampd):
                    row = n + j
                    vi = x[inv] if inv >= 0 else 0.0
                    vn = x[non] if non >= 0 else 0.0
                    vo = x[o]
                    mid, half = 0.5 * (rail[0] + rail[1]), 0.5 * (rail[0] - rail[1])
                    u = gain * (vn - vi) / half
                    f = mid + half * math.tanh(u)
                    df = gain / math.cosh(max(min(u, 300.0), -300.0)) ** 2
                    if o >= 0:
                        M[o, row] += 1.0                  # amp output current injected at the node
                    M[row, o] += 1.0
                    if non >= 0:
                        M[row, non] -= df
                    if inv >= 0:
                        M[row, inv] += df
                    rhs[row] += f - df * (vn - vi)
                try:
                    xn = np.linalg.solve(M, rhs)
                except np.linalg.LinAlgError:
                    xn = np.linalg.lstsq(M, rhs, rcond=None)[0]
                delta = xn - x
                lim = np.max(np.abs(delta[:n])) if n else 0.0
                if lim > 2.0:                              # damp big Newton jumps
                    delta *= 2.0 / lim
                x = x + delta
                if lim < 1e-7:
                    return x, True
            return x, False
        x0 = x.copy()
        x, ok = newton(x, gain, 200)
        if not ok and continuation:                    # continuation on the op-amp gain (loses latched states)
            x = x0
            for g in (1e2, 1e3, 1e4, 1e5):
                x, ok = newton(x, g, 200)
        for cp in caps:
            a, b, c, vprev, iprev = cp
            vnew = (x[a] if a >= 0 else 0.0) - (x[b] if b >= 0 else 0.0)
            cp[4] = 2 * c / dt * (vnew - vprev) - iprev
            cp[3] = vnew
        for ip in inds:
            a, b, L_, iprev, vprev = ip
            vnew = (x[a] if a >= 0 else 0.0) - (x[b] if b >= 0 else 0.0)
            ip[3] = iprev + dt / (2 * L_) * (vprev + vnew)
            ip[4] = vnew
        for lp in lamps:
            va = x[lp["a"]] if lp["a"] >= 0 else 0.0
            vb = x[lp["b"]] if lp["b"] >= 0 else 0.0
            nom_r = lp["nv"] ** 2 / lp["pw"]
            p = (va - vb) ** 2 / _lamp_r(lp["temp"], nom_r)
            cap = 1.57e-4 * lp["pw"]
            capw, capc = cap * lp["warm"] / 0.4, cap * lp["cool"] / 0.4
            lp["temp"] += p * dt / capw
            lp["temp"] -= dt * (lp["temp"] - 300.0) / (capc * 2600.0 / lp["pw"])
            lp["temp"] = max(lp["temp"], 300.0)
        times.append((k + 1) * dt)
        out.append(x[pn] if pn >= 0 else 0.0)
    return np.array(times), np.array(out)


def measure(times, v, skip_fraction=0.5):
    """(frequency from rising zero crossings of the mean-removed signal, max, min) over the last part."""
    i0 = int(len(v) * skip_fraction)
    t, y = times[i0:], v[i0:]
    mid = 0.5 * (y.max() + y.min())
    yc = y - mid
    cross = [t[i - 1] + (t[i] - t[i - 1]) * (-yc[i - 1]) / (yc[i] - yc[i - 1])
             for i in range(1, len(yc)) if yc[i - 1] < 0 <= yc[i]]
    f = (len(cross) - 1) / (cross[-1] - cross[0]) if len(cross) >= 3 else float("nan")
    return f, float(y.max()), float(y.min())
