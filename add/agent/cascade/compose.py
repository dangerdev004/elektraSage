"""Place circuit stages left-to-right, join out -> in, and re-emit one netlist.

Per stage k >= 2 the stage's own signal source (the one feeding the joined
input) is dropped; its other inputs keep their sources. Every stage keeps its
internal wiring untouched: the stage is only translated. Scopes and hints
refer to elements by index, so they are remapped (scopes on dropped sources
are dropped). CircuitJS needs one file format, so all stages must share a
dialect.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .dump import GRID, Element, Hint, Netlist, Point, Scope, nets, parse, terminals
from .ports import Ports

GAP = 4 * GRID               # clear space between stages
O_STUB = (0, -2 * GRID)      # intermediate O markers point up, out of the way


@dataclass
class Stage:
    name: str
    args: dict
    nl: Netlist
    ports: Ports
    warnings: list[str] = field(default_factory=list)
    note: str | None = None


@dataclass
class Composite:
    netlist: Netlist
    offsets: list[tuple[int, int]]            # (dx, dy) applied to each stage
    joins: list[tuple[Point, Point]]          # (prev out node, this in node)
    dropped: list[tuple[int, str]]            # (stage, what was dropped)
    unverified: list[str]                     # things the structural check could not see
    problems: list[str]                       # structural check findings (empty = clean)
    owners: list[int] = field(default_factory=list)   # stage index (0-based) per element, -1 = join wire


def _ceil_grid(v: float) -> int:
    return int(math.ceil(v / GRID)) * GRID


def _xs(e: Element) -> list[int]:
    return [e.x1] if e.type == "O" else [e.x1, e.x2]


def _exit_point(moved: list[Element], node: Point, dx: int, dy: int) -> Point:
    """Where the next stage's wire leaves this stage's output net.

    Normally the output node itself. If the net continues to the right (e.g.
    the phase-shift oscillator's feedback stub past the op-amp pin), leave
    from its rightmost point instead, so the wire does not run over the
    stub's own terminals.
    """
    node = (node[0] + dx, node[1] + dy)
    net_of = nets(moved)
    here = net_of.get(node)
    pts = [p for p, n in net_of.items() if n == here]
    return max(pts, key=lambda p: (p[0], p[1] == node[1]))


def _wire_conflicts(a: Point, b: Point, elements: list[Element]) -> list[str]:
    lo, hi = sorted((a[0], b[0]))
    y = a[1]
    out = []
    for e in elements:
        if e.type == "w" and e.y1 == e.y2 == y:
            if max(lo, min(e.x1, e.x2)) < min(hi, max(e.x1, e.x2)):
                out.append(f"joining wire would overlap wire {e.p1}-{e.p2}")
        ts = terminals(e)
        if ts:
            for t in ts:
                if t[1] == y and lo < t[0] < hi:
                    out.append(f"joining wire would touch a {e.type} terminal at {t}")
    return out


def _orphan_grounds(elements: list[Element], drop: set[int]) -> list[int]:
    """Ground symbols that touch nothing once the dropped elements are gone (typically the
    ground a removed source stood on). Left alone when any remaining element has unknown
    pins, because then 'touches nothing' cannot be judged."""
    rest = [i for i in range(len(elements)) if i not in drop]
    if any(terminals(elements[i]) is None and elements[i].type != "x" for i in rest):
        return []
    out = []
    for i in rest:
        e = elements[i]
        if e.type != "g":
            continue
        touched = any(e.p1 in (terminals(elements[j]) or [])
                      for j in rest if j != i and elements[j].type != "x")
        if not touched:
            out.append(i)
    return out


def compose(stages: list[Stage]) -> Composite:
    if not stages:
        raise ValueError("no stages given")
    dialects = {s.nl.dialect for s in stages}
    if len(dialects) > 1:
        detail = ", ".join(f"{i + 1}:{s.name} ({s.nl.dialect})" for i, s in enumerate(stages))
        raise ValueError(
            "cannot cascade circuits that use different CircuitJS file formats "
            f"({detail}); CircuitJS cannot load a mix and no converter exists yet. "
            "Tell the user this combination is not supported yet.")
    dialect = dialects.pop()

    for k, s in enumerate(stages):
        if k == 0:
            if not s.ports.outputs and len(stages) > 1:
                raise ValueError(f"stage 1 ({s.name}) has no identifiable output to connect")
        else:
            if not s.ports.inputs:
                raise ValueError(
                    f"stage {k + 1} ({s.name}) has no signal input: it is a source/generator "
                    "and can only be the FIRST stage")
            if k < len(stages) - 1 and not s.ports.outputs:
                raise ValueError(f"stage {k + 1} ({s.name}) has no identifiable output "
                                 "to connect to the next stage")

    combined: list[Element] = []
    owners: list[int] = []
    per_stage: list[list[Element]] = []
    index_maps: list[dict[int, int]] = []
    offsets: list[tuple[int, int]] = []
    joins: list[tuple[Point, Point]] = []
    dropped: list[tuple[int, str]] = []
    unverified: list[str] = []
    prev_out: Point | None = None

    for k, s in enumerate(stages):
        last = k == len(stages) - 1
        drop: set[int] = set()
        if k > 0:
            src = s.ports.inputs[0].element
            if src is not None:
                drop.add(src)
                dropped.append((k, f"{s.nl.elements[src].type} source at {s.nl.elements[src].p1}"))
                for gi in _orphan_grounds(s.nl.elements, drop):
                    drop.add(gi)
                    dropped.append((k, f"ground at {s.nl.elements[gi].p1} (only the dropped source used it)"))
        keep = [i for i in range(len(s.nl.elements)) if i not in drop]

        if k == 0:
            dx = dy = 0
        else:
            in_node = s.ports.inputs[0].node
            dy = prev_out[1] - in_node[1]
            right = max(x for e in combined for x in _xs(e))
            left = min(x for i in keep for x in _xs(s.nl.elements[i]))
            dx = _ceil_grid(right + GAP - left)
        offsets.append((dx, dy))

        moved = []
        for i in keep:
            e = s.nl.elements[i].moved(dx, dy)
            if e.type == "O" and not last:
                e.x2, e.y2 = e.x1 + O_STUB[0], e.y1 + O_STUB[1]
            moved.append(e)

        if k > 0:
            in_new = (s.ports.inputs[0].node[0] + dx, s.ports.inputs[0].node[1] + dy)
            if in_new[0] - prev_out[0] < GRID:
                raise ValueError(f"stage {k + 1}: no room to wire {prev_out} -> {in_new}")
            problems = _wire_conflicts(prev_out, in_new, combined + moved)
            if problems:
                raise ValueError(
                    f"cannot join stage {k} -> {k + 1} with a straight wire: " + "; ".join(problems)
                    + " (this circuit needs the router)")
            wire = Element("w", prev_out[0], prev_out[1], in_new[0], in_new[1], "0",
                           [], None if dialect == "legacy" else {})
            combined.append(wire)
            owners.append(-1)
            joins.append((prev_out, in_new))

        imap = {}
        for i, e in zip(keep, moved):
            imap[i] = len(combined)
            combined.append(e)
            owners.append(k)
        index_maps.append(imap)
        per_stage.append(moved)

        if any(terminals(e) is None and e.type != "x" for e in moved):
            types = sorted({e.type for e in moved if terminals(e) is None and e.type != "x"})
            unverified.append(f"stage {k + 1} ({s.name}) contains {types}: pins unknown, "
                              "connectivity inside them not checked")
        if s.ports.outputs:
            prev_out = _exit_point(moved, s.ports.outputs[0].node, dx, dy)

    # ---- scopes / hints -------------------------------------------------
    scopes: list[Scope] = []
    hints: list[Hint] = []
    for k, s in enumerate(stages):
        imap = index_maps[k]
        for sc in s.nl.scopes:
            if sc.index in imap:
                scopes.append(Scope(imap[sc.index], list(sc.tail), sc.xml))
        # Stage hints (e.g. "f.3db = ...") are computed from that stage's R and C
        # alone and would show unloaded values in a loaded chain, so they are dropped.

    out = Netlist(dialect=dialect, elements=combined, scopes=scopes, hints=hints,
                  options=list(stages[0].nl.options))
    _merge_header(out, stages, combined, index_maps)

    return Composite(out, offsets, joins, dropped, unverified,
                     verify(per_stage, combined, joins), owners)


def _sweep_sources(stages: list[Stage]):
    return [(k, i, e) for k, s in enumerate(stages)
            for i, e in enumerate(s.nl.elements) if e.type == "170"]


def _merge_header(out: Netlist, stages: list[Stage], combined: list[Element],
                  index_maps: list[dict[int, int]]) -> None:
    first = stages[0].nl
    if out.dialect == "legacy":
        tok = (first.header or "$ 1 5e-06 10 57 5.0").split()
        ts = min(float(s.nl.header.split()[2]) for s in stages if s.nl.header)
        tok[2] = repr(ts)
        out.header = " ".join(tok)
    else:
        out.root_attrs = dict(first.root_attrs)
        out.root_attrs["ts"] = repr(min(float(s.nl.root_attrs.get("ts", "5e-6")) for s in stages))

    # One sweep source drives the chain: widen it to cover every stage's range.
    sweeps = _sweep_sources(stages)
    if sweeps and stages[0].nl.elements and any(k == 0 for k, _, _ in sweeps):
        lo = min(float(e.tail[0]) for _, _, e in sweeps)
        hi = max(float(e.tail[1]) for _, _, e in sweeps)
        k0, i0, _ = next(t for t in sweeps if t[0] == 0)
        drv = combined[index_maps[0][i0]]
        drv.tail[0], drv.tail[1] = repr(lo), repr(hi)


def verify(per_stage: list[list[Element]], combined: list[Element],
           joins: list[tuple[Point, Point]]) -> list[str]:
    """Structural check: stages stay internally intact and only the intended
    joins connect them. Uses only element types whose pins are known."""
    problems: list[str] = []
    all_nets = nets(combined)
    owners: dict[int, set[tuple[int, int]]] = {}
    for k, elems in enumerate(per_stage):
        alone = nets(elems)
        seen_alone: dict[int, int] = {}
        for p, n_alone in alone.items():
            n_comb = all_nets.get(p)
            if n_comb is None:
                problems.append(f"stage {k + 1}: point {p} vanished from the combined circuit")
                continue
            if seen_alone.setdefault(n_alone, n_comb) != n_comb:
                problems.append(f"stage {k + 1}: a net was split in the combined circuit at {p}")
            owners.setdefault(n_comb, set()).add((k, n_alone))
    allowed = set()
    per_net: dict[int, int] = {}
    for j, (a, b) in enumerate(joins):
        if all_nets.get(a) != all_nets.get(b):
            problems.append(f"join {j + 1}: {a} and {b} are not connected")
        allowed.add(all_nets.get(a))
        per_net[all_nets.get(a)] = per_net.get(all_nets.get(a), 0) + 1
    for n_comb, members in owners.items():
        stages_hit = {k for k, _ in members}
        if len(members) > 1 and n_comb not in allowed:
            problems.append(f"unintended connection between stages {sorted(s + 1 for s in stages_hit)} "
                            f"(net {n_comb})")
        if n_comb in allowed and len(members) != per_net[n_comb] + 1:   # k joins tie k + 1 nets together
            problems.append(f"join net has {len(members)} member nets, expected {per_net[n_comb] + 1}")
    return problems
