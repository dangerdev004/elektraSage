"""Parallel branches that meet in a two-input combiner (e.g. a summing amplifier).

Shape (the first graph shape supported; chains stay in compose.py):

        +--- branch A (one or more stages) ---+
  in ---+                                      +--> combiner (2 inputs) --> out
        +--- branch B (one or more stages) ---+

Every branch is first composed as an ordinary chain (compose.compose). The
branches are then stacked vertically, their inputs tied together with one
vertical wire, and their outputs wired to the combiner's two inputs. Only the
first branch keeps its source: it drives both branches. The combiner's own
test sources are removed. Nothing here generates circuit text; it only moves,
joins and drops elements of text the generators already produced.

Joins use straight wires or one 3-segment path with a collision check; when a
path would touch something the composer refuses and says so (that is the job of
the router, which does not exist yet).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .compose import (GAP, Composite, Stage, _ceil_grid, _exit_point, _merge_header,
                      _orphan_grounds, _wire_conflicts, compose, verify)
from .dump import GRID, Element, Netlist, Point, Scope, nets, terminals
from .ports import infer

GAP_Y = 4 * GRID                  # clear vertical space between the two branches
O_STUB = (0, -2 * GRID)


@dataclass
class Parallel:
    netlist: Netlist
    problems: list[str]
    unverified: list[str]
    tie: tuple[Point, Point]                  # (A input node, B input node) joined by one wire
    exits: list[Point]                        # branch output points (A, B)
    combiner_in: list[Point]                  # combiner input nodes (after placement)
    sum_out: Point
    comps: list[Composite]                    # the two branch chains, as composed alone
    comp_exits: list[Point] = field(default_factory=list)   # branch outputs in the branches' own coordinates
    dropped: list[str] = field(default_factory=list)
    part_of: list[int] = field(default_factory=list)   # 0=A, 1=B, 2=combiner, -1=join wire, per element


def _box(elems: list[Element]) -> tuple[int, int, int, int]:
    xs = [v for e in elems for v in (e.x1, e.x2)]
    ys = [v for e in elems for v in (e.y1, e.y2)]
    return min(xs), min(ys), max(xs), max(ys)


def _vwire_conflicts(x: int, ya: int, yb: int, elements: list[Element]) -> list[str]:
    lo, hi = sorted((ya, yb))
    out = []
    for e in elements:
        if e.type == "w" and e.x1 == e.x2 == x:
            if max(lo, min(e.y1, e.y2)) < min(hi, max(e.y1, e.y2)):
                out.append(f"joining wire would overlap wire {e.p1}-{e.p2}")
        for t in terminals(e) or []:
            if t[0] == x and lo < t[1] < hi:
                out.append(f"joining wire would touch a {e.type} terminal at {t}")
    return out


def _wire(a: Point, b: Point, legacy: bool) -> Element:
    return Element("w", a[0], a[1], b[0], b[1], "0", [], None if legacy else {})


def _branch(stages: list[Stage], name: str):
    if not stages:
        raise ValueError(f"{name} has no stages")
    if not stages[0].ports.inputs:
        raise ValueError(f"{name}: its first stage ({stages[0].name}) takes no signal input, so it "
                         "cannot be fed from the shared input")
    comp = compose(stages)
    src = stages[0].ports.inputs[0].element
    if src is None:
        raise ValueError(f"{name}: could not find the source driving {stages[0].name}")
    if not stages[-1].ports.outputs:
        if stages[-1].name == "flash_adc":
            raise ValueError(f"{name}: its last stage is a flash ADC, which has digital outputs and can only be the "
                             "last stage of a whole chain, not of a branch that is summed")
        raise ValueError(f"{name}: its last stage ({stages[-1].name}) has no identifiable output")
    node = stages[-1].ports.outputs[0].node
    dx, dy = comp.offsets[-1]
    exit_pt = _exit_point(comp.netlist.elements, (node[0] + dx, node[1] + dy), 0, 0)
    return comp, src, stages[0].ports.inputs[0].node, exit_pt


def compose_parallel(branches: list[list[Stage]], combiner: Stage) -> Parallel:
    if len(branches) != 2:
        raise ValueError("exactly 2 parallel branches are supported for now")
    if len(combiner.ports.inputs) != 2 or not combiner.ports.outputs:
        raise ValueError(f"the combiner ({combiner.name}) needs exactly 2 signal inputs and an output; "
                         f"found {len(combiner.ports.inputs)} input(s)")
    dialects = {s.nl.dialect for br in branches for s in br} | {combiner.nl.dialect}
    if len(dialects) > 1:
        raise ValueError("cannot combine circuits that use different CircuitJS file formats "
                         f"({sorted(dialects)}); not supported yet. Tell the user.")
    legacy = dialects.pop() == "legacy"

    info = []
    for i, name in enumerate(("branch 1", "branch 2")):
        comp, src, in_pt, exit_pt = _branch(branches[i], name)
        full = list(comp.netlist.elements)
        drop: set[int] = set()
        if i == 1:                          # only branch 1 keeps its source: it drives both branches
            drop = {src} | set(_orphan_grounds(full, {src}))
        keep = [k for k in range(len(full)) if k not in drop]
        info.append(dict(comp=comp, full=full, keep=keep, in_pt=in_pt, exit=exit_pt, src=src))
    dropped = [f"branch 2 source at {info[1]['full'][info[1]['src']].p1} "
               "(branch 1's source drives both branches)"]

    # ---- stack the branches (either one on top); tie their input nets with one vertical wire
    last_problems: list[str] = []
    layout = None
    for top, bot in ((0, 1), (1, 0)):
        T = [info[top]["full"][k].moved(0, 0) for k in info[top]["keep"]]
        Bb = [info[bot]["full"][k] for k in info[bot]["keep"]]
        dyb = _ceil_grid(_box(T)[3] + GAP_Y - _box(Bb)[1])
        nT, nB = nets(T), nets(Bb)
        candT = sorted(q for q, n in nT.items() if n == nT.get(info[top]["in_pt"]))
        candB = sorted(q for q, n in nB.items() if n == nB.get(info[bot]["in_pt"]))
        # prefer the source terminals themselves, then the other points left to right
        candT.sort(key=lambda q: (q != info[top]["in_pt"], q))
        candB.sort(key=lambda q: (q != info[bot]["in_pt"], q))
        for pT in candT:
            for pB in candB:
                dx = pT[0] - pB[0]
                Bm = [e.moved(dx, dyb) for e in Bb]
                pB2 = (pB[0] + dx, pB[1] + dyb)
                if pB2[1] <= pT[1]:
                    continue
                probs = _vwire_conflicts(pT[0], pT[1], pB2[1], T + Bm)
                if not probs:
                    layout = (top, bot, T, Bm, dx, dyb, pT, pB2)
                    break
                last_problems = probs
            if layout:
                break
        if layout:
            break
    if layout is None:
        raise ValueError("cannot tie the two branch inputs with a straight vertical wire: "
                         + "; ".join(last_problems) + " (this combination needs the router)")
    top, bot, T, Bm, dxb, dyb, pT, pB2 = layout
    moved = {top: T, bot: Bm}
    A, B = moved[0], moved[1]                      # branch 1 / branch 2 elements, as placed
    exits = {top: info[top]["exit"], bot: (info[bot]["exit"][0] + dxb, info[bot]["exit"][1] + dyb)}
    exitA, exitB2 = exits[0], exits[1]
    exit_top, exit_bot = exits[top], exits[bot]
    tp, inB2 = pT, pB2
    tie = _wire(tp, inB2, legacy)
    compA, compB = info[0]["comp"], info[1]["comp"]
    keepB = info[1]["keep"]

    # ---- combiner: drop its two source posts; place right of both branches ----------------
    S = list(combiner.nl.elements)
    srcS = {combiner.ports.inputs[0].element, combiner.ports.inputs[1].element}
    if None in srcS:
        raise ValueError(f"could not find the sources of the combiner's inputs ({combiner.name})")
    dropS = set(srcS) | set(_orphan_grounds(S, srcS))
    keepS = [i for i in range(len(S)) if i not in dropS]
    dropped.append(f"combiner test sources at {sorted(S[i].p1 for i in srcS)}")

    right = max(max(max(e.x1, e.x2) for e in A), max(max(e.x1, e.x2) for e in B),
                exitA[0], exitB2[0])
    xc = _ceil_grid(right + 2 * GRID)                    # column for the lower output's vertical run
    in1, in2 = combiner.ports.inputs[0].node, combiner.ports.inputs[1].node
    sx0 = min(v for i in keepS for v in (S[i].x1, S[i].x2))
    dxS = _ceil_grid(xc + 2 * GRID - sx0)
    dyS = exit_top[1] - in1[1]
    Sm = [S[i].moved(dxS, dyS) for i in keepS]
    in1m = (in1[0] + dxS, in1[1] + dyS)
    in2m = (in2[0] + dxS, in2[1] + dyS)
    outS = (combiner.ports.outputs[0].node[0] + dxS, combiner.ports.outputs[0].node[1] + dyS)
    if in2m[1] <= in1m[1]:
        raise ValueError("combiner input 2 must lie below input 1 for the current placement")

    # ---- wires from the branch outputs to the combiner ------------------------------------
    allso_far = A + B + [tie] + Sm
    p = _wire_conflicts(exit_top, in1m, allso_far)
    if p:
        raise ValueError("cannot wire the upper branch to the combiner with a straight wire: "
                         + "; ".join(p) + " (needs the router)")
    w1 = _wire(exit_top, in1m, legacy)
    allso_far.append(w1)

    path = [exit_bot, (xc, exit_bot[1]), (xc, in2m[1]), in2m]
    wires2: list[Element] = []
    for a, b in zip(path, path[1:]):
        if a == b:
            continue
        if a[1] == b[1]:
            conf = _wire_conflicts(a, b, allso_far + wires2)
        else:
            conf = _vwire_conflicts(a[0], a[1], b[1], allso_far + wires2)
        if conf:
            raise ValueError(f"cannot route the lower branch to the combiner ({a} -> {b}): "
                             + "; ".join(conf) + " (needs the router)")
        wires2.append(_wire(a, b, legacy))

    # ---- final-output markers of the branches point up, out of the way --------------------
    def _stub(elems: list[Element], at: Point) -> None:
        for e in elems:
            if e.type == "O" and (e.x1, e.y1) == at:
                e.x2, e.y2 = e.x1 + O_STUB[0], e.y1 + O_STUB[1]
    _stub(A, exitA)
    _stub(B, exitB2)

    # ---- assemble, remapping scopes -----------------------------------------------------
    fused: list[Element] = []
    part_of: list[int] = []
    amap_A = {}
    for i, e in enumerate(A):
        amap_A[i] = len(fused); fused.append(e); part_of.append(0)
    amap_B = {}
    for new_i, old_i in enumerate(keepB):
        amap_B[old_i] = len(fused); fused.append(B[new_i]); part_of.append(1)
    fused.append(tie); part_of.append(-1)
    amap_S = {}
    for new_i, old_i in enumerate(keepS):
        amap_S[old_i] = len(fused); fused.append(Sm[new_i]); part_of.append(2)
    for w in [w1, *wires2]:
        fused.append(w); part_of.append(-1)

    scopes: list[Scope] = []
    for nl_, amap in ((compA.netlist, amap_A), (compB.netlist, amap_B), (combiner.nl, amap_S)):
        for sc in nl_.scopes:
            if sc.index in amap:
                scopes.append(Scope(amap[sc.index], list(sc.tail), sc.xml))

    out = Netlist(dialect="legacy" if legacy else "xml", elements=fused, scopes=scopes, hints=[],
                  options=list(compA.netlist.options))
    # header: smallest timestep of everything; widen the shared source's sweep over both branches
    _merge_header(out, [Stage("A", {}, compA.netlist, branches[0][0].ports),
                        Stage("B", {}, compB.netlist, branches[1][0].ports),
                        Stage("C", {}, combiner.nl, combiner.ports)],
                  fused, [amap_A, amap_B, amap_S])

    part_lists = [A, B, Sm]
    joins = [(tp, inB2), (exit_top, in1m), (exit_bot, in2m)]
    probs = verify(part_lists, fused, joins)
    unverified: list[str] = []
    for tag, elems in (("branch 1", A), ("branch 2", B), ("combiner", Sm)):
        types = sorted({e.type for e in elems if terminals(e) is None and e.type != "x"})
        if types:
            unverified.append(f"{tag} contains {types}: pins unknown, connectivity inside them not checked")

    return Parallel(out, probs, unverified, (tp, inB2), [exitA, exitB2], [in1m, in2m], outS,
                    [compA, compB], [info[0]["exit"], info[1]["exit"]], dropped, part_of)
