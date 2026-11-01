"""Facts about a series linear regulator stage (zener reference + op-amp + pass transistor).

Everything comes from the same DC solver and small-signal solver the rest of the cascade uses: the output level
from the operating point, ripple rejection and line regulation from the AC solution at the ripple frequency and
near DC, load regulation from re-solving with a different load, and the trough check from re-solving with the
input lowered by the ripple amplitude.
"""

from __future__ import annotations

import math

from . import dump
from .dc import NotAnalysable, operating_point
from .ports import is_signal_source


def is_regulator(stage) -> bool:
    kinds = {e.type for e in stage.nl.elements}
    return {"z", "a", "t"} <= kinds and stage.ports.role == "stage"


def _load_resistor(nl, out_pt):
    """Index of the resistor from the output net to ground (the load), if there is exactly one."""
    net_of = dump.nets(nl.elements, merge_ground=True)
    gnd = {net_of[e.p1] for e in nl.elements if e.type == "g"}
    o = net_of.get(out_pt)
    hits = [i for i, e in enumerate(nl.elements) if e.type == "r"
            and {net_of[e.p1], net_of[e.p2]} in ({o, g} for g in gnd)]
    return hits[0] if len(hits) == 1 else None


def regulator_facts(stage) -> dict:
    from .analysis import System, find_driver
    nl = dump.parse(stage.nl.to_text())
    src_i = next(i for i, e in enumerate(nl.elements) if is_signal_source(e))
    src = nl.elements[src_i]
    f_rip, a_rip = float(src.tail[1]), float(src.tail[2])
    vin = float(src.tail[3]) if len(src.tail) > 3 else 0.0
    out = stage.ports.outputs[0].node
    op = operating_point(nl)
    vout = op.v(out)
    drv = find_driver(nl)
    sysm = System(nl, drv)
    g_rip = abs(sysm.v(sysm.solve(f_rip), out))
    g_dc = abs(sysm.v(sysm.solve(1e-3), out))
    facts = dict(vin=vin, vout=vout, f_ripple=f_rip, ripple_in=a_rip, ripple_gain=g_rip,
                 ripple_out=a_rip * g_rip, line_reg_mv_per_v=g_dc * 1e3, i_load=None, load_reg_mv=None,
                 trough_ok=None, vout_trough=None)

    def solve_with(mod):
        n2 = dump.parse(stage.nl.to_text())
        mod(n2)
        return operating_point(n2).v(out)

    li = _load_resistor(nl, out)
    if li is not None:
        rl = float(nl.elements[li].tail[0])
        facts["i_load"] = vout / rl if rl else None

        def lighter(n2):
            n2.elements[li].tail[0] = repr(rl * 10)
        try:
            facts["load_reg_mv"] = (solve_with(lighter) - vout) * 1e3          # light load minus nominal
        except NotAnalysable:
            pass

    def lower_input(n2):                      # the op-amp's own supply is taken from the input, so it dips too
        n2.elements[src_i].tail[3] = repr(vin - a_rip)
        for e in n2.elements:
            if e.type == "a" and len(e.tail) >= 2:
                e.tail[0] = repr(min(float(e.tail[0]), vin - a_rip))
    try:
        vt = solve_with(lower_input)
        facts["vout_trough"] = vt
        facts["trough_ok"] = abs(vt - vout) < 0.01 * max(abs(vout), 1e-9)
    except NotAnalysable:
        pass
    return facts
