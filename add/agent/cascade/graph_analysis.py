"""Computed response of a two-branch parallel circuit (see graph.py).

Same solver and the same scope statement as analysis.py: linear parts, ideal op-amp
(no gain-bandwidth limit), other inputs held at 0. Everything is calculated by code;
the language model is only told to relay it.
"""

from __future__ import annotations

import math

from .analysis import (TOL, depth_text, Analysis, NotAnalysable, System, _curve, _peak, find_driver, fmt,
                       metrics)
from .dump import terminals
from .graph import Parallel


def _band(m) -> str:
    if m.stop is not None and not (m.lo or m.hi):
        return (f"stop band {fmt(m.stop[0], 'Hz')} to {fmt(m.stop[1], 'Hz')} (-3 dB edges), deepest near "
                f"{fmt(m.f_notch, 'Hz')} ({depth_text(m.depth_db)})")
    return (f"-3 dB band {fmt(m.lo, 'Hz') if m.lo else 'from low end'} to "
            f"{fmt(m.hi, 'Hz') if m.hi else 'high end'}")


def analyse_parallel(par: Parallel, names: list[list[str]]) -> Analysis:
    nl = par.netlist
    try:
        drv = find_driver(nl)
        System(nl, drv)
    except NotAnalysable as e:
        return Analysis(False, str(e))
    except (ValueError, IndexError) as e:
        return Analysis(False, f"could not read source/element values: {e}")

    freqs = drv.grid()
    amp_nodes = [(i, terminals(e)[2], e) for i, e in enumerate(nl.elements) if e.type == "a"]
    o_nodes = [(e.x1, e.y1) for e in nl.elements if e.type == "O"]
    pts = [par.sum_out, *par.exits, *[n for _, n, _ in amp_nodes], *o_nodes]
    try:
        curves = _curve(nl, drv, freqs, pts)
        alone = []
        for comp, ex in zip(par.comps, par.comp_exits):
            d = find_driver(comp.netlist)
            alone.append(_curve(comp.netlist, d, freqs, [ex])[ex])
    except NotAnalysable as e:
        return Analysis(False, str(e))

    lines, flags, loaded = [], [], []
    worsts: list[float] = []
    headroom: list = []
    m = metrics(freqs, [abs(v) for v in curves[par.sum_out]])
    if m.sloping:
        lines.append(f"shape: {m.shape}; passband gain and -3 dB corners are not meaningful")
    else:
        lines.append(f"shape: {m.shape}; passband gain {m.peak:.3g} (peak near {fmt(m.f_peak, 'Hz')}); "
                     f"{_band(m)}")
    lines.append(f"driving source: {fmt(drv.amp, 'V')} peak, "
                 + (f"sweeping {fmt(drv.sweep[0], 'Hz')} to {fmt(drv.sweep[1], 'Hz')}" if drv.sweep
                    else f"fixed {fmt(drv.f0, 'Hz')}"))

    for k, al in enumerate(alone, 1):
        am = metrics(freqs, [abs(v) for v in al])
        label = " -> ".join(names[k - 1])
        if am.sloping:
            lines.append(f"branch {k} ({label}) alone: {am.shape}")
        else:
            c = []
            if am.lo:
                c.append(f"lower corner {fmt(am.lo, 'Hz')}")
            if am.hi:
                c.append(f"upper corner {fmt(am.hi, 'Hz')}")
            lines.append(f"branch {k} ({label}) alone: {am.shape}, passband gain {am.peak:.3g}"
                         + (", " + ", ".join(c) if c else ""))

    # loading: branch output with the combiner connected vs. the branch on its own
    for k, (ex, al) in enumerate(zip(par.exits, alone), 1):
        pm = [abs(v) for v in al]
        pk = max(pm)
        ratios = [abs(f_) / p for f_, p in zip(curves[ex], pm) if p >= 0.5 * pk and pk > 0]
        if ratios:
            worst = min(ratios)
            worsts.append(worst)
            lines.append(f"junction branch {k} -> combiner: branch {k}'s output is {worst:.2f}x what it "
                         "would be unloaded (worst case within its passband)")
            if worst < 1 - TOL:
                loaded.append(k)
                flags.append(f"Loading: the combiner loads branch {k}, so its output falls to {worst:.2f}x "
                             f"of its unloaded level ({20 * math.log10(worst):.1f} dB).")

    for i, node, e in amp_nodes:
        lim = min(abs(float(e.tail[0])), abs(float(e.tail[1]))) if len(e.tail) >= 2 else None
        vm = [abs(v) for v in curves[node]]
        if drv.sweep:
            idx = [j for j, f in enumerate(freqs) if drv.sweep[0] <= f <= drv.sweep[1]]
            peak = drv.amp * max(vm[j] for j in idx)
        else:
            peak = _peak(drv, freqs, curves[node])
        where = {0: "branch 1", 1: "branch 2", 2: "the combiner"}.get(par.part_of[i], "the circuit")
        txt = f"op-amp in {where}: peak output {fmt(peak, 'V')} for this source"
        if lim:
            txt += f" vs +/-{fmt(lim, 'V')} limit"
            if peak > 0.9 * lim:
                headroom.append((peak, lim))
            if peak > lim:
                flags.append(f"Clipping: the op-amp in {where} would clip ({fmt(peak, 'V')} peak vs "
                             f"+/-{fmt(lim, 'V')} limit).")
            elif peak > 0.9 * lim:
                flags.append(f"Headroom: the op-amp in {where} is within 10% of its limit "
                             f"({fmt(peak, 'V')} vs +/-{fmt(lim, 'V')}).")
        lines.append(txt)

    peaks = {n: _peak(drv, freqs, curves[n]) for n in o_nodes}
    res = Analysis(True, "", lines, flags, None if m.sloping else m.peak, m.lo, m.hi, m.sloping,
                   loaded, m.shape, None, None, peaks)
    res.worst_load = min(worsts) if worsts else None
    res.stop, res.f_notch, res.depth_db = m.stop, m.f_notch, m.depth_db
    res.source_amp = drv.amp
    res.headroom = headroom
    return res
