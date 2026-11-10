"""Digital cascade: join clocked-logic blocks (and DACs) through typed ports, then check the result.

Port types (a block lists its ports in LSB-first order, bit 0 first):
  * bits   - an ordered bus of N logic nodes (counter Q, SIPO Q, ADC bits / PISO, DAC inputs);
  * serial - one logic node (PISO output, SIPO input);
  * clock  - the block's own square-wave `R` rail (the first block's clock drives the whole chain).

Joining keeps every generator untouched. The downstream block's stimulus (its `L` toggles and its own clock
rail) is dropped, the block is moved to the right of the upstream one, and plain wires are routed between the
exact pin points. A router is not in the repo, so a small one is here: each link is a Z-shaped wire through
a free horizontal channel, checked so that it never passes through another element's pin or overlaps a wire.
After joining, a structural check confirms that the only connections between the two blocks are the intended
ones (the same idea as compose.verify).

The SIPO and PISO generators write the xml file format, which this repo's CircuitJS cannot load (a blank screen), so
they are converted to the legacy format first (to_legacy); every block is then legacy and any listed pair can join.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

from . import digital
from .dump import Element, Netlist, Point, parse
from .digital import CHIPS_D, CHIPS_JK, CHIPS_MUX, Sim, chip_pins, input_level, pins_of, rail_params

GAP = 96
LANE = 16


# --------------------------------------------------------------------------- file format
def _escape(text: str) -> str:
    """CircuitJS text-element escaping (CustomLogicModel.escape in the repo's CircuitJS)."""
    if not text:
        return "\\0"
    return (text.replace("\\", "\\\\").replace("\n", "\\n").replace(" ", "\\s").replace("+", "\\p")
            .replace("=", "\\q").replace("#", "\\h").replace("&", "\\a").replace("\r", "\\r"))


_XML_TO_LEGACY = {"DFlipFlop": "155", "mux": "184", "I": "I", "L": "L", "M": "M", "R": "R", "w": "w", "x": "x"}


def to_legacy(nl: Netlist) -> Netlist:
    """Rewrite an xml-format netlist in the legacy line format.

    The repo's CircuitJS build has no XML loader (CirSim.readCircuit only parses legacy lines), so the xml the
    SIPO / PISO generators write shows up as a blank screen. Only the element kinds those two generators use
    are converted; the token orders come from this repo's element classes (ChipElm.dump, MultiplexerElm.dump,
    InverterElm.dump, LogicInputElm / SwitchElm.dump, LogicOutputElm.dump, TextElm.dump, VoltageElm).
    Anything else raises, so nothing is guessed."""
    if nl.dialect != "xml":
        return nl
    out: list[Element] = []
    for e in nl.elements:
        a = e.attrs or {}
        t = _XML_TO_LEGACY.get(e.type)
        if t is None:
            raise ValueError(f"cannot convert xml element <{e.type}> to the legacy format")
        if e.type == "DFlipFlop":
            tail = ["0.0"]                                       # volts of the one stateful pin (Q)
        elif e.type == "mux":
            tail = [a.get("se", "2")]                            # number of select bits
        elif e.type == "I":
            tail = [a.get("sl", "0.5"), a.get("hi", "5")]
        elif e.type == "L":
            tail = [a.get("p", "0"), "false", "5.0", "0.0"]      # position, momentary, high, low
        elif e.type == "M":
            tail = ["2.5"]                                       # threshold
        elif e.type == "R":
            tail = [a.get("wf", "0"), a.get("fr", "40"), a.get("maxv", "5"), a.get("bias", "0")]
        elif e.type == "x":
            tail = [a.get("si", "24"), _escape(a.get("te", ""))]
        else:
            tail = []
        out.append(Element(t, e.x1, e.y1, e.x2, e.y2, e.flags, tail, None))
    ra = nl.root_attrs
    header = "$ " + " ".join([ra.get("f", "1"), repr(float(ra.get("ts", "5e-6"))), ra.get("ic", "10.2"),
                              ra.get("cb", "50"), ra.get("vr", "5.0")])
    return Netlist(dialect="legacy", header=header, options=[], elements=out, scopes=[], hints=[])


def load_block(text: str) -> Netlist:
    """Parse a generator's output; xml circuits are converted so every block is in the loadable legacy format."""
    return to_legacy(parse(text))


# --------------------------------------------------------------------------- block ports
@dataclass
class Block:
    name: str
    nl: Netlist
    out_bits: list[Point] = field(default_factory=list)      # LSB first
    in_bits: list[int] = field(default_factory=list)         # element indices of the `L` toggles, LSB first
    in_pts: list[Point] = field(default_factory=list)         # the pin points those toggles sat on, same order
    serial_out: Point | None = None
    serial_in: int | None = None                             # element index of the `L`
    load: int | None = None                                  # PISO load/shift toggle (element index)
    clock: int | None = None                                 # element index of the square-wave `R`


def _clock_index(nl: Netlist) -> int | None:
    c = [i for i, e in enumerate(nl.elements) if e.type == "R" and rail_params(e)[0] == "2"]
    return c[0] if len(c) == 1 else None


def _toggles(nl: Netlist) -> list[int]:
    return [i for i, e in enumerate(nl.elements) if e.type == "L"]


def _markers(nl: Netlist) -> list[int]:
    return [i for i, e in enumerate(nl.elements) if e.type == "M"]


def ports_of(name: str, nl: Netlist) -> Block:
    """Typed ports of one of the supported blocks, taken from the generator's own conventions."""
    b = Block(name, nl, clock=_clock_index(nl))
    els = nl.elements
    if name in ("binary_counter", "sipo_shift_register"):
        ms = sorted(_markers(nl), key=lambda i: (els[i].x1, els[i].y1))      # first stage (bit 0) leftmost
        b.out_bits = [els[i].p1 for i in ms]
        if name == "sipo_shift_register":
            t = _toggles(nl)
            b.serial_in = t[0] if len(t) == 1 else None
    elif name == "piso_shift_register":
        sim = Sim(nl)
        inv_in = {sim.net(e.p1) for e in els if e.type == "I"}
        par, ld = [], []
        for i in _toggles(nl):
            (ld if sim.net(els[i].p1) in inv_in else par).append(i)
        b.in_bits = sorted(par, key=lambda i: els[i].x1)                    # first mux = bit 0
        b.load = ld[0] if len(ld) == 1 else None
        ms = _markers(nl)
        b.serial_out = els[ms[0]].p1 if len(ms) == 1 else None
    elif name in ("r2r_dac", "binary_weighted_dac"):
        key = (lambda i: els[i].x1) if name == "r2r_dac" else (lambda i: els[i].y1)
        b.in_bits = sorted(_toggles(nl), key=key)[::-1]                     # generators list the MSB first
    elif name == "flash_adc":
        ms = [i for i in _markers(nl)]                                      # file order: b(n-2) .. b0, then top bit
        n = len(ms)
        order = ms[:-1][::-1] + ms[-1:]
        b.out_bits = [els[i].p1 for i in order]
        assert n >= 2
    b.in_pts = [els[i].p1 for i in b.in_bits]
    return b


# --------------------------------------------------------------------------- routing
def _segments_ok(path: list[Point], allowed: set[Point], pins: set[Point], wires: list[tuple[Point, Point]],
                 used: list[tuple[Point, Point]]) -> bool:
    for a, b in zip(path, path[1:]):
        if a == b:
            return False
        vertical = a[0] == b[0]
        lo, hi = (min(a[1], b[1]), max(a[1], b[1])) if vertical else (min(a[0], b[0]), max(a[0], b[0]))
        for p in pins:
            if p in allowed:
                continue
            if vertical and p[0] == a[0] and lo <= p[1] <= hi:
                return False
            if not vertical and p[1] == a[1] and lo <= p[0] <= hi:
                return False
        for (c, d) in wires + used:                     # collinear overlap with an existing wire
            if vertical and c[0] == d[0] == a[0]:
                l2, h2 = min(c[1], d[1]), max(c[1], d[1])
                if min(hi, h2) > max(lo, l2):
                    return False
            if not vertical and c[1] == d[1] == a[1]:
                l2, h2 = min(c[0], d[0]), max(c[0], d[0])
                if min(hi, h2) > max(lo, l2):
                    return False
    return True


def route(s: Point, t: Point, ybot: int, pins: set[Point], wires, used, slot: int) -> list[Point] | None:
    """A Z-shaped path s -> t: down/up out of s, along a free channel, into t."""
    allowed = {s, t}
    for jog in range(0, 12):
        for yc in (ybot + LANE * (slot + 1 + jog), ):
            for xa in (s[0], s[0] + LANE * (jog + 1), s[0] - LANE * (jog + 1)):
                for xb in (t[0], t[0] + LANE * (jog + 1), t[0] - LANE * (jog + 1)):
                    path = [s]
                    if xa != s[0]:
                        path.append((xa, s[1]))
                    path += [(xa, yc), (xb, yc)]
                    if xb != t[0]:
                        path.append((xb, t[1]))
                    path.append(t)
                    path = [p for i, p in enumerate(path) if i == 0 or p != path[i - 1]]
                    if len(path) >= 2 and _segments_ok(path, allowed, pins, wires, used):
                        return path
    return None


def _bounds(els: list[Element]) -> tuple[int, int, int]:
    xs = [p[0] for e in els for p in pins_of(e) + [e.p2]]
    ys = [p[1] for e in els for p in pins_of(e) + [e.p2]]
    return min(xs), max(xs), max(ys)


def nets(els: list[Element]) -> dict[Point, int]:
    """Net id of every pin point (wires merge points; unlike dump.nets this also knows the chip pins)."""
    parent: dict[Point, Point] = {}

    def find(p):
        parent.setdefault(p, p)
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p

    for e in els:
        for p in pins_of(e):
            find(p)
        if e.type == "w":
            parent[find(e.p1)] = find(e.p2)
    ids: dict[Point, int] = {}
    return {p: ids.setdefault(find(p), len(ids)) for p in list(parent)}


# --------------------------------------------------------------------------- joining
@dataclass
class Chain:
    netlist: Netlist
    blocks: list[Block]            # blocks as placed (indices refer to netlist.elements)
    links: list[str]
    dropped: list[str]
    problems: list[str] = field(default_factory=list)


def _new_wire(a: Point, b: Point, dialect: str) -> Element:
    return Element("w", a[0], a[1], b[0], b[1], "0", [], None if dialect == "legacy" else {})


def _group_pins(els: list[Element]) -> dict[int, set[Point]]:
    n = nets(els)
    g: dict[int, set[Point]] = {}
    for p, k in n.items():
        g.setdefault(k, set()).add(p)
    return g


def join(up: Chain, name: str, down_nl: Netlist, link: str) -> Chain:
    """Append one block (`name`) to the chain's last block through `link` ('bits', 'serial')."""
    last = up.blocks[-1]
    down_nl = to_legacy(down_nl)
    if down_nl.dialect != up.netlist.dialect:
        raise ValueError(f"cannot join {name} ({down_nl.dialect} format) to {last.name} ({up.netlist.dialect} format)")
    down = ports_of(name, down_nl)
    _init_piso(name, down)
    dialect = up.netlist.dialect

    # --- links as (source point, target element index in `down`) --------------------
    pairs: list[tuple[Point, int]] = []
    if link == "bits":
        if not last.out_bits:
            raise ValueError(f"{last.name} has no bit outputs")
        if not down.in_bits:
            raise ValueError(f"{name} has no bit inputs")
        if len(last.out_bits) != len(down.in_bits):
            raise ValueError(f"width mismatch: {last.name} gives {len(last.out_bits)} bits, {name} takes "
                             f"{len(down.in_bits)}")
        pairs = list(zip(last.out_bits, down.in_bits))
    elif link == "serial":
        if last.serial_out is None or down.serial_in is None:
            raise ValueError(f"{last.name} -> {name}: no serial output / serial input to join")
        pairs = [(last.serial_out, down.serial_in)]
    else:
        raise ValueError(f"unknown link {link!r}")

    drop = {i for _, i in pairs}
    dropped = [f"{name}: manual input toggle at {down_nl.elements[i].p1}" for i in sorted(drop)]
    clock_target = None
    if down.clock is not None and last.clock is not None:
        drop.add(down.clock)
        clock_target = down_nl.elements[down.clock].p1
        dropped.append(f"{name}: own clock rail at {clock_target} (the first block's clock drives it)")
    keep = [i for i in range(len(down_nl.elements)) if i not in drop]

    left, right, _ = _bounds(up.netlist.elements)
    dleft = min(p[0] for i in keep for p in pins_of(down_nl.elements[i]) + [down_nl.elements[i].p2])
    dx = -(-(right + GAP - dleft) // 16) * 16
    dy = 0
    moved = [down_nl.elements[i].moved(dx, dy) for i in keep]
    imap = {old: len(up.netlist.elements) + k for k, old in enumerate(keep)}

    combined = list(up.netlist.elements) + moved
    ybot = max(_bounds(up.netlist.elements)[2], _bounds(moved)[2])
    pins = {p for e in combined for p in pins_of(e) + [e.p2]}
    wires = [(e.p1, e.p2) for e in combined if e.type == "w"]
    used: list[tuple[Point, Point]] = []

    targets = [(s, (down_nl.elements[i].p1[0] + dx, down_nl.elements[i].p1[1] + dy), f"{last.name} bit -> {name}")
               for s, i in pairs]
    if clock_target is not None and last.clock is not None:
        targets.append((up.netlist.elements[last.clock].p1,
                        (clock_target[0] + dx, clock_target[1] + dy), "shared clock"))

    new_wires: list[Element] = []
    desc: list[str] = []
    for slot, (s, t, what) in enumerate(targets):
        path = route(s, t, ybot, pins, wires, used, slot)
        if path is None:
            raise ValueError(f"cannot route {what}: no free channel from {s} to {t} (this needs a real router)")
        for a, b in zip(path, path[1:]):
            new_wires.append(_new_wire(a, b, dialect))
            used.append((a, b))
        desc.append(f"{what}: {s} -> {t}")
    combined += new_wires

    # --- scopes / header ----------------------------------------------------------
    out = Netlist(dialect=dialect, elements=combined, scopes=list(up.netlist.scopes),
                  hints=[], options=list(up.netlist.options))
    out.header = up.netlist.header
    out.root_attrs = dict(up.netlist.root_attrs)
    for sc in down_nl.scopes:
        if sc.index in imap:
            from .dump import Scope
            out.scopes.append(Scope(imap[sc.index], list(sc.tail), sc.xml))

    placed = Block(name, out)
    shift = lambda p: (p[0] + dx, p[1] + dy)
    placed.out_bits = [shift(p) for p in down.out_bits]
    placed.in_bits = [imap[i] for i in down.in_bits if i in imap]
    placed.in_pts = [shift(p) for p in down.in_pts]
    placed.serial_out = shift(down.serial_out) if down.serial_out else None
    placed.serial_in = imap.get(down.serial_in) if down.serial_in is not None else None
    placed.load = imap.get(down.load) if down.load is not None else None
    placed.clock = imap.get(down.clock) if down.clock is not None else None

    chain = Chain(out, up.blocks + [placed], up.links + desc, up.dropped + dropped, list(up.problems))
    chain.problems += verify_join(up.netlist.elements, moved, combined, pairs, targets, dx, dy)
    return chain


def verify_join(up_els, moved, combined, pairs, targets, dx, dy) -> list[str]:
    """Only the intended connections may exist: every original net stays intact, and nothing else merges."""
    problems: list[str] = []
    all_n = nets(combined)
    intended = [(s, t) for s, t, _ in targets]
    # group id of each original pin in the combined netlist
    def gid(p): return all_n.get(p)
    merged: dict[int, list[str]] = {}
    for label, els, off in (("up", up_els, (0, 0)), ("down", moved, (0, 0))):
        own = nets(els)
        groups: dict[int, set[Point]] = {}
        for p, k in own.items():
            groups.setdefault(k, set()).add(p)
        for pts in groups.values():
            ids = {gid(p) for p in pts if gid(p) is not None}
            if len(ids) > 1:
                problems.append(f"{label}: a net was split by joining: {sorted(pts)[:3]}")
    want = {}
    for s, t in intended:
        want.setdefault(gid(s), set()).add(gid(t))
    for k, ts in want.items():
        if ts != {k}:
            problems.append(f"intended join {k} -> {ts} is not connected")
    # no accidental merge: nets that contain pins of BOTH blocks must be exactly the intended ones
    up_pts = {p for p in nets(up_els)}
    dn_pts = {p for p in nets(moved)}
    group_blocks: dict[int, set[str]] = {}
    for p in up_pts:
        group_blocks.setdefault(gid(p), set()).add("up")
    for p in dn_pts:
        group_blocks.setdefault(gid(p), set()).add("down")
    cross = {g for g, b in group_blocks.items() if len(b) == 2}
    expect = {gid(s) for s, _ in intended}
    for g in cross - expect:
        problems.append("an unintended connection appeared between the two blocks")
    return problems


def _init_piso(name: str, b: Block) -> None:
    """In this CircuitJS the mux selects input 0 (the previous stage) when its select is low, and the select is the
    inverted load/shift toggle - so toggle = 0 LOADS the parallel inputs and toggle = 1 SHIFTS. Start in load mode."""
    if name == "piso_shift_register" and b.load is not None:
        b.nl.elements[b.load].tail[0] = "0"


def start(name: str, nl_text: str) -> Chain:
    nl = load_block(nl_text)
    b = ports_of(name, nl)
    _init_piso(name, b)
    return Chain(nl, [b], [], [])


# --------------------------------------------------------------------------- checks
def _set_clock(nl: Netlist, idx: int, hz: float) -> None:
    e = nl.elements[idx]
    if e.attrs is not None:
        e.attrs["fr"] = repr(float(hz))
    else:
        e.tail[1] = repr(float(hz))


def _code(bits: list[int]) -> int:
    return sum(b << i for i, b in enumerate(bits))


def _sample(sim: Sim, times: list[float], points: list[Point]) -> list[list[int]]:
    rows, first = [], True
    for t in times:
        val = sim.step(t, first)
        first = False
        rows.append([val.get(sim.net(p), 0) for p in points])
    return rows


def _sink_weights(down: Block) -> list[int]:
    """Bit weight of each of the sink's input pins, from where they physically sit (not from the wiring map):
    both DAC generators list the MSB first (leftmost for r2r, topmost for binary-weighted), so the weight is
    2^(n-1-rank); a register's inputs run LSB first from the left."""
    pts = down.in_pts
    n = len(pts)
    if down.name == "r2r_dac":
        rank = {p: r for r, p in enumerate(sorted(pts, key=lambda p: p[0]))}
        return [1 << (n - 1 - rank[p]) for p in pts]
    if down.name == "binary_weighted_dac":
        rank = {p: r for r, p in enumerate(sorted(pts, key=lambda p: p[1]))}
        return [1 << (n - 1 - rank[p]) for p in pts]
    rank = {p: r for r, p in enumerate(sorted(pts, key=lambda p: p[0]))}
    return [1 << rank[p] for p in pts]


def check_counter_to_bits(chain: Chain, n: int) -> list[str]:
    """counter -> (DAC | register): the sink must see the counter's value, weighted by its own pin positions."""
    up, down = chain.blocks[0], chain.blocks[-1]
    sim = Sim(chain.netlist)
    f = rail_params(chain.netlist.elements[up.clock])[1]
    T, dt = 1.0 / f, 1.0 / f / 20
    times = [k * dt + dt / 3 for k in range(int((2 ** n + 2) * 20))]
    pts = list(up.out_bits) + list(down.in_pts)
    weights = _sink_weights(down)
    rows = _sample(sim, times, pts)
    bad: list[str] = []
    for t, r in zip(times, rows):
        c_up = _code(r[:n])
        c_dn = sum(w for w, b in zip(weights, r[n:2 * n]) if b)
        want = int(t / T + 0.5) % (2 ** n)               # falling-edge counter: first count at T/2
        if c_up != want:
            bad.append(f"counter code {c_up} at t={t:.4f}s, expected {want}")
            break
        if c_dn != c_up:
            bad.append(f"{down.name} reads code {c_dn} where the counter holds {c_up} at t={t:.4f}s "
                       "(bits are wired in the wrong order)")
            break
    return bad


def check_serial_link(chain: Chain, n: int) -> list[str]:
    """PISO -> SIPO on one clock: load a word, shift it across; the SIPO must end up holding the same word."""
    piso, sipo = chain.blocks[0], chain.blocks[-1]
    sim = Sim(chain.netlist)
    f = rail_params(chain.netlist.elements[piso.clock])[1]
    T = 1.0 / f
    word = [(i * 5 + 1) % 3 != 0 for i in range(n)]       # a fixed, non-trivial word (bit i)
    for i, v in zip(piso.in_bits, word):
        sim.drive[i] = (lambda v: lambda t: int(v))(v)
    sim.drive[piso.load] = lambda t: 0 if t < 1.5 * T else 1      # 0 = load, 1 = shift (see _init_piso)
    edges = n + 1                                           # edge 1 loads, then n shifts; the SIPO takes the last bit on edge n+1
    times = [k * T / 20 + T / 60 for k in range(int((edges + 1) * 20))]
    rows = _sample(sim, times, list(sipo.out_bits))
    got = rows[int(edges * 20 + 5)]
    if [bool(b) for b in got] != word:
        return [f"serial link: SIPO holds {got} after {edges} clocks, the PISO was loaded with {[int(w) for w in word]}"]
    return []


FLAGS_ZERO_DELAY = ("Checked with an ideal zero-delay logic model: propagation delay, ripple-counter glitches and "
                    "timing races are NOT modelled, so a clean result means the wiring and bit order are right, "
                    "not that the circuit is glitch-free.")


class DigitalNote(str):
    """The fact sheet the model sees; `.reply` is the user-facing reply written by code."""
    reply: str = ""


_PRETTY = {"binary_counter": "binary counter", "sipo_shift_register": "SIPO shift register",
           "piso_shift_register": "PISO shift register", "r2r_dac": "R-2R DAC",
           "binary_weighted_dac": "binary-weighted DAC", "flash_adc": "flash ADC"}


def build_reply(chain: Chain, checks: dict[str, list[str]], warns: list[str] | None = None) -> str:
    names = " -> ".join(_PRETTY.get(b.name, b.name) for b in chain.blocks)
    lines = [f"Digital cascade: {names}.", ""]
    lines.append("The blocks are your existing generators, joined by wires between their exact pins. "
                 + ("The first block's clock drives the whole chain. " if any("shared clock" in l for l in chain.links) else "")
                 + "The next block's manual input toggles were removed and replaced by the previous block's outputs.")
    if checks:
        lines.append("")
        for k, probs in checks.items():
            lines.append(f"- {k}: " + ("passed." if not probs else "FAILED - " + "; ".join(probs)))
    if chain.problems:
        lines.append("")
        lines += [f"- Wiring problem found: {p}" for p in chain.problems]
    if warns:
        lines.append("")
        lines += [f"- Warning from the {w}" for w in warns]
    lines.append("")
    if chain.blocks[0].name == "flash_adc":
        lines.append("Not checked: the ADC's analog input and comparators, and its bit order (taken from the "
                     "generator's marker order). No DAC output level was computed.")
    elif any(b.name in ("r2r_dac", "binary_weighted_dac") for b in chain.blocks):
        lines.append("Not checked: the DAC's analog output level; only the logic code reaching it.")
    lines.append(FLAGS_ZERO_DELAY)
    return "\n".join(lines)


def build_note(chain: Chain, checks: dict[str, list[str]]) -> str:
    out = ["Digital cascade (code-computed):"]
    out.append("  stages: " + " -> ".join(b.name for b in chain.blocks))
    for l in chain.links:
        out.append(f"  link: {l}")
    for d in chain.dropped:
        out.append(f"  dropped: {d}")
    for k, probs in checks.items():
        out.append(f"  check {k}: " + ("PASS" if not probs else "FAIL - " + "; ".join(probs)))
    for p in chain.problems:
        out.append(f"  structural problem: {p}")
    if chain.blocks[0].name == "flash_adc":
        out.append("  Not simulated: the flash ADC's analog input and comparators. Its bit order comes from the "
                   "generator's marker order (documented, not measured), and no DAC output level was computed.")
    elif any(b.name in ("r2r_dac", "binary_weighted_dac") for b in chain.blocks):
        out.append("  Not simulated: the DAC's analog output level; only the logic code reaching it was checked.")
    out.append("  " + FLAGS_ZERO_DELAY)
    return "\n".join(out)


# --------------------------------------------------------------------------- public API
LINKS = {
    ("binary_counter", "r2r_dac"): "bits",
    ("binary_counter", "binary_weighted_dac"): "bits",
    ("binary_counter", "piso_shift_register"): "bits",
    ("sipo_shift_register", "piso_shift_register"): "bits",
    ("sipo_shift_register", "r2r_dac"): "bits",
    ("sipo_shift_register", "binary_weighted_dac"): "bits",
    ("piso_shift_register", "sipo_shift_register"): "serial",
    ("flash_adc", "r2r_dac"): "bits",
    ("flash_adc", "binary_weighted_dac"): "bits",
    ("flash_adc", "piso_shift_register"): "bits",
}
SUPPORTED = {"binary_counter", "sipo_shift_register", "piso_shift_register", "r2r_dac",
             "binary_weighted_dac", "flash_adc"}


def working_links() -> dict[tuple[str, str], str]:
    """Every pair in LINKS can be built: xml blocks are converted to the legacy format, so formats no longer differ."""
    return dict(LINKS)


def digital_cascade(stages: list[dict], clock_hz: float | None = None) -> tuple[str, str]:
    """stages: [{"circuit": name, "args": {...}}, ...] -> (CircuitJS text, code-computed note)."""
    from .. import circuits as C
    if not isinstance(stages, list) or len(stages) < 2:
        raise ValueError("a digital cascade needs a list of at least two stages, each "
                         "{'circuit': <block name>, 'args': {...}}")
    specs = []
    for k, s in enumerate(stages, 1):
        if not isinstance(s, dict) or not isinstance(s.get("circuit"), str):
            raise ValueError(f"stage {k}: expected {{'circuit': <block name>, 'args': {{...}}}}, got {s!r}. "
                             f"Block names: {sorted(SUPPORTED)}")
        args = s.get("args") or {}
        if not isinstance(args, dict):
            raise ValueError(f"stage {k} ({s['circuit']}): 'args' must be an object such as {{'bits': 4}}, got {args!r}")
        if s["circuit"] not in SUPPORTED:
            raise ValueError(f"stage {k}: {s['circuit']} is not a digital-cascade block (supported: {sorted(SUPPORTED)})")
        specs.append((s["circuit"], args))
    chain = None
    warns: list[str] = []
    for k, (name, args) in enumerate(specs):
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                text = getattr(C, name)(**args)
            warns += [f"{_PRETTY.get(name, name)} generator: {w.message}" for w in caught]
        except TypeError as exc:
            raise ValueError(f"stage {k + 1} ({name}): bad arguments: {exc}. Put every parameter inside "
                             "'args', for example {'circuit': 'binary_counter', 'args': {'bits': 4}}") from None
        except ValueError as exc:
            raise ValueError(f"stage {k + 1} ({name}): {exc}") from None
        if k == 0:
            chain = start(name, text)
            if clock_hz and chain.blocks[0].clock is not None:
                _set_clock(chain.netlist, chain.blocks[0].clock, clock_hz)
            continue
        key = (chain.blocks[-1].name, name)
        if key not in LINKS:
            allowed = sorted(b for a, b in LINKS if a == key[0])
            raise ValueError(f"{key[0]} cannot drive {key[1]}; it can drive: {allowed or 'nothing'}")
        chain = join(chain, name, parse(text), LINKS[key])
    checks: dict[str, list[str]] = {}
    first, last = chain.blocks[0], chain.blocks[-1]
    if len(chain.blocks) == 2 and first.name == "binary_counter" and last.in_pts:
        checks["counter code reaches the sink and counts"] = check_counter_to_bits(chain, len(first.out_bits))
    elif len(chain.blocks) == 2 and (first.name, last.name) == ("piso_shift_register", "sipo_shift_register"):
        checks["PISO word is rebuilt in the SIPO"] = check_serial_link(chain, len(last.out_bits))
    note = DigitalNote(build_note(chain, checks))
    note.reply = build_reply(chain, checks, list(dict.fromkeys(warns)))
    return chain.netlist.to_text(), note
