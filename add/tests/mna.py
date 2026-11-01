"""Tiny independent AC nodal solver (test-only) for r, c, l, ideal op amp.

Deliberately re-derives nodes from raw coordinates (wires merge points, `g`
points are ground) instead of using agent.cascade, so a composer bug cannot
hide behind shared code. Drives the first sweep/AC source's hot node with 1 V.
"""

import numpy as np

from agent.cascade import dump


def solve(netlist_text: str, freq: float) -> dict:
    nl = dump.parse(netlist_text)
    parent = {}

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
    for e in nl.elements:
        if e.type == "w":
            union(e.p1, e.p2)
        if e.type == "g":
            union(e.p1, gnd)
    # Sources other than the driven one are held at 0 V (their hot node is shorted to ground).
    first = True
    for e in nl.elements:
        if e.type in ("170", "v", "R") and (e.type == "170" or e.tail[0] != "0"):
            if first:
                first = False
            else:
                union(e.p1 if e.type != "v" else e.p2, gnd)
    w = 2 * np.pi * freq
    node_ids = {}

    def n(p):
        r = find(p)
        if r == find(gnd):
            return None
        return node_ids.setdefault(r, len(node_ids))

    # collect branches first so the matrix size is known
    stamps, amps, src = [], [], None
    for e in nl.elements:
        if e.type in ("r", "c", "l"):
            val = float(e.tail[0])
            y = {"r": 1 / val, "c": 1j * w * val, "l": 1 / (1j * w * val)}[e.type]
            stamps.append((n(e.p1), n(e.p2), y))
        elif e.type == "a":
            off = 8 if int(e.flags) & 2 else 16
            a = (e.x1, e.y1 + off)
            b = (e.x1, e.y1 - off)
            inv, non = (b, a) if int(e.flags) & 1 == 0 else (a, b)
            amps.append((n(inv), n(non), n(e.p2)))
        elif e.type in ("170", "v", "R") and src is None and (e.type == "170" or e.tail[0] != "0"):
            hot = e.p1 if e.type != "v" else e.p2
            src = n(hot)
    size = len(node_ids)
    A = np.zeros((size + len(amps) + 1, size + len(amps) + 1), dtype=complex)
    z = np.zeros(size + len(amps) + 1, dtype=complex)
    for a, b, y in stamps:
        for i, j, s in ((a, a, 1), (b, b, 1), (a, b, -1), (b, a, -1)):
            if i is not None and j is not None:
                A[i, j] += s * y
    for k, (inv, non, out) in enumerate(amps):       # ideal: V+ = V-, output sources current
        row = size + k
        if inv is not None:
            A[row, inv] += 1
        if non is not None:
            A[row, non] -= 1
        if out is not None:
            A[out, row] += 1
    srow = size + len(amps)                           # source: V(hot) = 1
    A[srow, src] = 1
    A[src, srow] = 1            # source current enters its node's KCL
    z[srow] = 1
    x = np.linalg.solve(A, z)
    return {"V": lambda p: 0 if n(p) is None else x[n(p)]}
