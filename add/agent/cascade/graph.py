"""Parallel branches that meet in an N-input combiner (e.g. a summing amplifier).

Shape (chains stay in compose.py):

        +--- branch 1 (one or more stages) ---+
  in ---+--- branch 2 ...                     +--> combiner (N inputs) --> out
        +--- branch N ...---------------------+

Every branch is first composed as an ordinary chain (compose.compose). The
branches are then stacked vertically, their inputs tied together with
vertical wires, and their outputs wired to the combiner's N inputs. Only the
first branch keeps its source: it drives all branches. The combiner's own
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
    tie: tuple[Point, Point]                  # first pair of branch input nodes joined by a wire (see `ties`)
    exits: list[Point]                        # branch output points, in branch order
    combiner_in: list[Point]                  # combiner input nodes (after placement)
    sum_out: Point
    comps: list[Composite]                    # the two branch chains, as composed alone
    comp_exits: list[Point] = field(default_factory=list)   # branch outputs in the branches' own coordinates
    dropped: list[str] = field(default_factory=list)
    part_of: list[int] = field(default_factory=list)   # branch index, N = combiner, -1 = join wire, per element
    ties: list[tuple[Point, Point]] = field(default_factory=list)   # every pair of input nodes tied together


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


def _stacking_orders(n: int) -> list[list[int]]:
    """Top-to-bottom orders to try: as given, then reversed, then every other order (all of them for up to 4
    branches, rotations for more). Which branch sits where decides whether a straight tie wire is free."""
    from itertools import permutations
    natural, reverse = list(range(n)), list(range(n))[::-1]
    orders = [natural, reverse]
    rest = (list(p) for p in permutations(range(n))) if n <= 4 else \
        ([*natural[k:], *natural[:k]] for k in range(1, n))
    orders += [o for o in rest if o not in orders]
    return orders


def compose_parallel(branches: list[list[Stage]], combiner) -> Parallel:
    """Wire N parallel branches into an N-input combiner. `combiner` is a Stage, or a function taking the
    top-to-bottom order of the branches (indices) and returning the Stage whose k-th input receives the k-th
    branch of that order (needed when the inputs carry different weights)."""
    n = len(branches)
    if n < 2:
        raise ValueError("at least 2 parallel branches are needed")
    make = combiner if callable(combiner) else (lambda order: combiner)
    probe = make(list(range(n)))
    if len(probe.ports.inputs) != n or not probe.ports.outputs:
        raise ValueError(f"the combiner ({probe.name}) needs exactly {n} signal inputs and an output; "
                         f"found {len(probe.ports.inputs)} input(s)")
    dialects = {s.nl.dialect for br in branches for s in br} | {probe.nl.dialect}
    if len(dialects) > 1:
        raise ValueError("cannot combine circuits that use different CircuitJS file formats "
                         f"({sorted(dialects)}); not supported yet. Tell the user.")
    legacy = dialects.pop() == "legacy"

    info = []
    for i in range(n):
        comp, src, in_pt, exit_pt = _branch(branches[i], f"branch {i + 1}")
        full = list(comp.netlist.elements)
        drop: set[int] = set()
        if i >= 1:                          # only branch 1 keeps its source: it drives every branch
            drop = {src} | set(_orphan_grounds(full, {src}))
        keep = [k for k in range(len(full)) if k not in drop]
        info.append(dict(comp=comp, full=full, keep=keep, in_pt=in_pt, exit=exit_pt, src=src))
    drives = "both branches" if n == 2 else "every branch"
    dropped = [f"branch {i + 1} source at {info[i]['full'][info[i]['src']].p1} "
               f"(branch 1's source drives {drives})" for i in range(1, n)]

    # ---- stack the branches (trying several orders); tie neighbouring input nets with vertical wires
    def lay_out(order: list[int]):
        """Place the branches top to bottom in this order and tie their inputs; (placed, ties) or None, with
        the reason left in `last_problems`."""
        nonlocal last_problems
        first = order[0]
        placed = {first: ([info[first]["full"][k].moved(0, 0) for k in info[first]["keep"]], (0, 0))}
        ties: list[tuple[Point, Point]] = []
        for prev, b in zip(order, order[1:]):
            every = [e for els, _ in placed.values() for e in els]
            Bb = [info[b]["full"][k] for k in info[b]["keep"]]
            dyb = _ceil_grid(_box(every)[3] + GAP_Y - _box(Bb)[1])
            odx, ody = placed[prev][1]
            in_prev = (info[prev]["in_pt"][0] + odx, info[prev]["in_pt"][1] + ody)
            # every point of the shared input net so far (all placed branches and the ties between them)
            nT, nB = nets(every + [_wire(a, c, legacy) for a, c in ties]), nets(Bb)
            candT = sorted(q for q, k in nT.items() if k == nT.get(in_prev))
            candB = sorted(q for q, k in nB.items() if k == nB.get(info[b]["in_pt"]))
            # prefer the source terminals themselves, then the other points left to right
            candT.sort(key=lambda q: (q != in_prev, q))
            candB.sort(key=lambda q: (q != info[b]["in_pt"], q))
            found = None
            for pT in candT:
                for pB in candB:
                    dx = pT[0] - pB[0]
                    Bm = [e.moved(dx, dyb) for e in Bb]
                    pB2 = (pB[0] + dx, pB[1] + dyb)
                    if pB2[1] <= pT[1]:
                        continue
                    probs = _vwire_conflicts(pT[0], pT[1], pB2[1],
                                             every + [_wire(a, c, legacy) for a, c in ties] + Bm)
                    if not probs:
                        found = (Bm, (dx, dyb), pT, pB2)
                        break
                    last_problems = probs
                if found:
                    break
            if not found:
                return None
            Bm, off, pT, pB2 = found
            placed[b] = (Bm, off)
            ties.append((pT, pB2))
        return placed, ties

    def _finish(order, placed, ties):
        exits = {b: (info[b]["exit"][0] + placed[b][1][0], info[b]["exit"][1] + placed[b][1][1]) for b in range(n)}
        tie_wires = [_wire(a, c, legacy) for a, c in ties]
        exit_top = exits[order[0]]

        # ---- combiner: drop its source posts; place right of every branch ---------------------
        comb = make(order)
        S = list(comb.nl.elements)
        srcS = {p.element for p in comb.ports.inputs}
        if None in srcS:
            raise ValueError(f"could not find the sources of the combiner's inputs ({comb.name})")
        dropS = set(srcS) | set(_orphan_grounds(S, srcS))
        keepS = [i for i in range(len(S)) if i not in dropS]
        comb_dropped = f"combiner test sources at {sorted(S[i].p1 for i in srcS)}"

        all_placed = [e for els, _ in placed.values() for e in els]
        right = max(max(max(e.x1, e.x2) for e in all_placed), *[p[0] for p in exits.values()])
        xc = _ceil_grid(right + 2 * GRID)                    # first column for a lower output's vertical run
        columns = n - 1
        in_nodes = [p.node for p in comb.ports.inputs]
        sx0 = min(v for i in keepS for v in (S[i].x1, S[i].x2))
        dxS = _ceil_grid(xc + GRID * (columns - 1) + 2 * GRID - sx0)
        dyS = exit_top[1] - in_nodes[0][1]
        Sm = [S[i].moved(dxS, dyS) for i in keepS]
        in_m = [(q[0] + dxS, q[1] + dyS) for q in in_nodes]
        outS = (comb.ports.outputs[0].node[0] + dxS, comb.ports.outputs[0].node[1] + dyS)
        if any(b[1] <= a[1] for a, b in zip(in_m, in_m[1:])):
            raise ValueError("the combiner inputs must lie one below the other in order for the current placement")

        # ---- wires from the branch outputs to the combiner ------------------------------------
        allso_far = all_placed + tie_wires + Sm
        p = _wire_conflicts(exit_top, in_m[0], allso_far)
        if p:
            raise ValueError("cannot wire the upper branch to the combiner with a straight wire: "
                             + "; ".join(p) + " (needs the router)")
        w1 = _wire(exit_top, in_m[0], legacy)
        allso_far.append(w1)

        cols_asc = [xc + GRID * t for t in range(columns)]
        first_failure = None
        wires2: list[Element] = []
        for cols in (cols_asc, cols_asc[::-1]):
            trial: list[Element] = []
            failure = None
            for pos in range(1, n):
                ex, xcol, dst = exits[order[pos]], cols[pos - 1], in_m[pos]
                path = [ex, (xcol, ex[1]), (xcol, dst[1]), dst]
                for a, b in zip(path, path[1:]):
                    if a == b:
                        continue
                    if a[1] == b[1]:
                        conf = _wire_conflicts(a, b, allso_far + trial)
                    else:
                        conf = _vwire_conflicts(a[0], a[1], b[1], allso_far + trial)
                    if conf:
                        failure = (f"cannot route the {'lower branch' if n == 2 else f'path {order[pos] + 1}'} to the "
                                   f"combiner ({a} -> {b}): " + "; ".join(conf) + " (needs the router)")
                        break
                    trial.append(_wire(a, b, legacy))
                if failure:
                    break
            if failure is None:
                wires2 = trial
                first_failure = None
                break
            first_failure = first_failure or failure
        if first_failure:
            raise ValueError(first_failure)

        # ---- final-output markers of the branches point up, out of the way --------------------
        def _stub(elems: list[Element], at: Point) -> None:
            for e in elems:
                if e.type == "O" and (e.x1, e.y1) == at:
                    e.x2, e.y2 = e.x1 + O_STUB[0], e.y1 + O_STUB[1]
        for b in range(n):
            _stub(placed[b][0], exits[b])

        # ---- assemble, remapping scopes -----------------------------------------------------
        fused: list[Element] = []
        part_of: list[int] = []
        amaps: list[dict[int, int]] = []
        for b in range(n):
            amap: dict[int, int] = {}
            for new_i, old_i in enumerate(info[b]["keep"]):
                amap[old_i] = len(fused); fused.append(placed[b][0][new_i]); part_of.append(b)
            amaps.append(amap)
        for tw in tie_wires:
            fused.append(tw); part_of.append(-1)
        amap_S = {}
        for new_i, old_i in enumerate(keepS):
            amap_S[old_i] = len(fused); fused.append(Sm[new_i]); part_of.append(n)
        for w in [w1, *wires2]:
            fused.append(w); part_of.append(-1)

        scopes: list[Scope] = []
        for nl_, amap in [*((info[b]["comp"].netlist, amaps[b]) for b in range(n)), (comb.nl, amap_S)]:
            for sc in nl_.scopes:
                if sc.index in amap:
                    scopes.append(Scope(amap[sc.index], list(sc.tail), sc.xml))

        out = Netlist(dialect="legacy" if legacy else "xml", elements=fused, scopes=scopes, hints=[],
                      options=list(info[0]["comp"].netlist.options))
        # header: smallest timestep of everything; widen the shared source's sweep over every branch
        _merge_header(out, [Stage(f"B{b}", {}, info[b]["comp"].netlist, branches[b][0].ports) for b in range(n)]
                      + [Stage("C", {}, comb.nl, comb.ports)], fused, [*amaps, amap_S])

        part_lists = [placed[b][0] for b in range(n)] + [Sm]
        joins = [*ties, *[(exits[order[pos]], in_m[pos]) for pos in range(n)]]
        probs = verify(part_lists, fused, joins)
        unverified: list[str] = []
        for tag, elems in [*((f"branch {b + 1}", placed[b][0]) for b in range(n)), ("combiner", Sm)]:
            types = sorted({e.type for e in elems if terminals(e) is None and e.type != "x"})
            if types:
                unverified.append(f"{tag} contains {types}: pins unknown, connectivity inside them not checked")

        return Parallel(out, probs, unverified, ties[0], [exits[b] for b in range(n)], in_m, outS,
                        [info[b]["comp"] for b in range(n)], [info[b]["exit"] for b in range(n)], [*dropped, comb_dropped], part_of,
                        list(ties))

    last_problems: list[str] = []
    failures: list[str] = []
    for order in _stacking_orders(n):
        laid = lay_out(order)
        if laid is None:
            failures.append("cannot tie the branch inputs with straight vertical wires: "
                            + "; ".join(last_problems) + " (this combination needs the router)")
            continue
        try:
            return _finish(order, *laid)
        except ValueError as exc:
            failures.append(str(exc))
    raise ValueError(failures[0])

