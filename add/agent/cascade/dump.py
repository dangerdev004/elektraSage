"""Parse and serialise CircuitJS (Falstad) circuit dumps - both dialects.

Dialects seen in this codebase:
  * "legacy": one line per element, `type x1 y1 x2 y2 flags tail...`, then
    `o <element-index> ...` scope lines and `h <type> <i> <j>` hint lines;
  * "xml": `<cir ...>` wrapping `<type x="x1 y1 x2 y2" f=".." attr=".."/>`
    elements, `<o en="<index>"...>` scopes and `<h t i1 i2/>` hints.
CircuitJS cannot load a file mixing the two, and the per-type attribute
mapping between them is not known here, so a cascade must be single-dialect.

Only what cascading needs is modelled: coordinates (the only fields
translation touches), element order (scopes/hints refer to elements BY
INDEX = position among element lines/tags), and a few attributes for source
detection. Everything else is carried through verbatim.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

GRID = 16
Point = tuple[int, int]


@dataclass
class Element:
    type: str
    x1: int
    y1: int
    x2: int
    y2: int
    flags: str = "0"
    tail: list[str] = field(default_factory=list)       # legacy payload
    attrs: dict[str, str] | None = None                  # xml payload (None = legacy)

    @property
    def p1(self) -> Point:
        return (self.x1, self.y1)

    @property
    def p2(self) -> Point:
        return (self.x2, self.y2)

    def moved(self, dx: int, dy: int) -> "Element":
        return Element(self.type, self.x1 + dx, self.y1 + dy, self.x2 + dx,
                       self.y2 + dy, self.flags, list(self.tail),
                       None if self.attrs is None else dict(self.attrs))

    def line(self) -> str:                               # legacy form
        parts = [self.type, self.x1, self.y1, self.x2, self.y2, self.flags, *self.tail]
        return " ".join(str(p) for p in parts)

    def tail_float(self, i: int, default: float | None = None) -> float | None:
        try:
            return float(self.tail[i])
        except (IndexError, ValueError):
            return default

    def attr(self, name: str, default: str | None = None) -> str | None:
        return default if self.attrs is None else self.attrs.get(name, default)


@dataclass
class Scope:
    index: int                                  # element index it displays
    tail: list[str] = field(default_factory=list)       # legacy: tokens after index
    xml: ET.Element | None = None                       # xml: the <o> subtree


@dataclass
class Hint:
    kind: str
    indices: list[int]
    xml: ET.Element | None = None


@dataclass
class Netlist:
    dialect: str = "legacy"
    header: str | None = None                   # legacy '$' line
    root_attrs: dict[str, str] = field(default_factory=dict)   # xml <cir> attrs
    options: list[str] = field(default_factory=list)    # legacy '%' lines
    elements: list[Element] = field(default_factory=list)
    scopes: list[Scope] = field(default_factory=list)
    hints: list[Hint] = field(default_factory=list)

    def to_text(self) -> str:
        return self._to_xml() if self.dialect == "xml" else self._to_legacy()

    def _to_legacy(self) -> str:
        lines = []
        if self.header:
            lines.append(self.header)
        lines += self.options
        lines += [e.line() for e in self.elements]
        lines += ["o " + " ".join([str(s.index), *s.tail]) for s in self.scopes]
        lines += ["h " + " ".join([h.kind, *map(str, h.indices)]) for h in self.hints]
        return "\n".join(lines) + "\n"

    def _to_xml(self) -> str:
        root = ET.Element("cir", dict(self.root_attrs))
        for e in self.elements:
            a = {"x": f"{e.x1} {e.y1} {e.x2} {e.y2}", "f": e.flags}
            a.update(e.attrs or {})
            ET.SubElement(root, e.type, a)
        for s in self.scopes:
            node = ET.fromstring(ET.tostring(s.xml))
            node.set("en", str(s.index))
            root.append(node)
        for h in self.hints:
            node = ET.fromstring(ET.tostring(h.xml))
            for key, idx in zip(("i1", "i2"), h.indices):
                node.set(key, str(idx))
            root.append(node)
        ET.indent(root, space="  ")
        return ET.tostring(root, encoding="unicode") + "\n"


def parse(text: str) -> Netlist:
    return _parse_xml(text) if text.lstrip().startswith("<") else _parse_legacy(text)


def _parse_xml(text: str) -> Netlist:
    root = ET.fromstring(text)
    nl = Netlist(dialect="xml", root_attrs=dict(root.attrib))
    for ch in root:
        if ch.tag == "o":
            nl.scopes.append(Scope(int(ch.get("en", "0")), xml=ch))
        elif ch.tag == "h":
            idx = [int(ch.get(k)) for k in ("i1", "i2") if ch.get(k) is not None]
            nl.hints.append(Hint(ch.get("t", ""), idx, xml=ch))
        else:
            try:
                x1, y1, x2, y2 = (int(v) for v in ch.get("x", "").split())
            except ValueError:
                raise ValueError(f"<{ch.tag}> has no four-number x attribute: {ch.attrib}")
            rest = {k: v for k, v in ch.attrib.items() if k not in ("x", "f")}
            nl.elements.append(Element(ch.tag, x1, y1, x2, y2, ch.get("f", "0"), [], rest))
    return nl


def _parse_legacy(text: str) -> Netlist:
    nl = Netlist()
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        tok = line.split()
        t = tok[0]
        if t == "$":
            nl.header = line
        elif t == "%":
            nl.options.append(line)
        elif t == "o":
            nl.scopes.append(Scope(int(tok[1]), tok[2:]))
        elif t == "h":
            nl.hints.append(Hint(tok[1], [int(v) for v in tok[2:]]))
        else:
            try:
                x1, y1, x2, y2 = (int(v) for v in tok[1:5])
            except (ValueError, IndexError):
                raise ValueError(f"line {n}: cannot read coordinates in {line!r}")
            nl.elements.append(
                Element(t, x1, y1, x2, y2, tok[5] if len(tok) > 5 else "0", tok[6:]))
    return nl


# --- electrical terminals ------------------------------------------------
# Terminal positions for the element types the cascader needs to reason about.
# Anything not listed returns None ("unknown pins"): it is carried through
# untouched, but connectivity checks cannot see inside it.

_TWO_TERMINAL = {"w", "r", "c", "l", "v", "d", "z", "181"}
GATE_TYPES = {"150", "151", "152", "153", "154"}
_ONE_TERMINAL = {"g", "O", "R", "170", "M"}   # 170 = AC sweep (single post, per author)


def _geom(e: Element):
    dx, dy = e.x2 - e.x1, e.y2 - e.y1
    n = math.hypot(dx, dy) or 1.0
    dsign = (1 if dx >= 0 else -1) if dy == 0 else (1 if dy > 0 else -1)
    return (dy / n, -dx / n), dsign


def bjt_pins(e: Element) -> dict[str, Point]:
    """BJT `t` (a PNP swaps collector and emitter): base at p1; collector / emitter at p2 +/- 16 along the perpendicular (CircuitJS geometry)."""
    (wx, wy), dsign = _geom(e)
    if int(e.flags) & 1:
        dsign = -dsign
    if e.tail and float(e.tail[0]) < 0:          # CircuitJS: hs2 = hs * dsign * pnp, so a PNP swaps its pins
        dsign = -dsign
    h = 16 * dsign
    return {"b": e.p1, "c": (round(e.x2 + h * wx), round(e.y2 + h * wy)),
            "e": (round(e.x2 - h * wx), round(e.y2 - h * wy))}


def mosfet_pins(e: Element) -> dict[str, Point]:
    """N-MOSFET `f`: gate at p1; source / drain at p2 -/+ 16 along the perpendicular."""
    (wx, wy), dsign = _geom(e)
    if int(e.flags) & 8:
        dsign = -dsign
    h = 16 * dsign
    return {"g": e.p1, "s": (round(e.x2 - h * wx), round(e.y2 - h * wy)),
            "d": (round(e.x2 + h * wx), round(e.y2 + h * wy))}


def switch2_pins(e: Element) -> dict[str, Point]:
    """SPDT analog switch `160`: common at p1, two throws at p2 +/- 16, control at mid + 16."""
    (wx, wy), _ = _geom(e)
    mx, my = (e.x1 + e.x2) / 2, (e.y1 + e.y2) / 2
    return {"common": e.p1, "post1": (round(e.x2 + 16 * wx), round(e.y2 + 16 * wy)),
            "post2": (round(e.x2 - 16 * wx), round(e.y2 - 16 * wy)),
            "ctl": (round(mx + 16 * wx), round(my + 16 * wy))}


TIMER_PINS = ("dis", "tr", "th", "vin", "ctl", "out", "rst", "gnd")


def timer_pins(e: Element) -> dict[str, Point]:
    """555 `165`: pin posts, from CircuitJS's ChipElm geometry (3 wide, 5 tall, size 2 unless flag 1 is set)."""
    fl = int(e.flags)
    cspc = 8 if fl & 1 else 16
    c2 = 2 * cspc
    x0, y0 = e.x1 + c2, e.y1
    ys = 5 * c2
    xs = 3 * c2
    # (flip flags 1024 / 2048 are not used by any generator here and are not handled)
    spec = {"dis": ("W", 1), "tr": ("W", 3), "th": ("W", 4), "vin": ("N", 1), "ctl": ("S", 1),
            "out": ("E", 2), "rst": ("E", 1), "gnd": ("S", 2)}
    out = {}
    for name, (side, pos) in spec.items():
        if side == "N":
            px, py = x0 + c2 * pos, y0 - c2
        elif side == "S":
            px, py = x0 + c2 * pos, y0 + ys - c2 + c2
        elif side == "W":
            px, py = x0 - c2, y0 + c2 * pos
        else:
            px, py = x0 + xs - c2 + c2, y0 + c2 * pos
        out[name] = (px, py)
    return out


def terminals(e: Element) -> list[Point] | None:
    if e.type == "165":
        p = timer_pins(e)
        return [p[n] for n in TIMER_PINS]
    if e.type == "t":
        p = bjt_pins(e)
        return [p["b"], p["c"], p["e"]]
    if e.type == "f":
        p = mosfet_pins(e)
        return [p["g"], p["s"], p["d"]]
    if e.type == "160":
        p = switch2_pins(e)
        return [p["common"], p["post1"], p["post2"], p["ctl"]]
    if e.type == "L":
        return [e.p1]
    if e.type in _TWO_TERMINAL:
        return [e.p1, e.p2]
    if e.type in _ONE_TERMINAL:
        return [e.p1]
    if e.type in GATE_TYPES:                    # logic gate: inputs left of the output at p2, 16 apart
        dx, dy = e.x2 - e.x1, e.y2 - e.y1
        n_ = max(abs(dx), abs(dy)) or 1
        ux, uy = dx / n_, dy / n_
        cnt = int(float(e.tail[0])) if e.tail else 2
        i0, pts = -(cnt // 2), []
        for i in range(cnt):
            if i0 == 0 and cnt % 2 == 0:
                i0 += 1
            pts.append((round(e.x1 + 16 * i0 * uy), round(e.y1 - 16 * i0 * ux)))
            i0 += 1
        return pts + [e.p2]
    if e.type == "a":  # op amp: two inputs at p1 +/- offset, output at p2
        dx, dy = e.x2 - e.x1, e.y2 - e.y1
        n = max(abs(dx), abs(dy)) or 1
        ux, uy = dx / n, dy / n
        off = 8 if int(e.flags) & 2 else 16
        nx, ny = -uy * off, ux * off
        return [(round(e.x1 + nx), round(e.y1 + ny)),
                (round(e.x1 - nx), round(e.y1 - ny)), e.p2]
    return None


def nets(elements: list[Element], merge_ground: bool = False) -> dict[Point, int]:
    """Union-find over wires (and optionally ground symbols).

    Returns {point: net_id} for every known terminal point. Two points are on
    the same net if connected through wires. Non-wire elements do not merge
    nets (their terminals are distinct nodes). With merge_ground, every point
    carrying a `g` symbol is one net (CircuitJS ground is global).
    """
    parent: dict[Point, Point] = {}

    def find(p: Point) -> Point:
        parent.setdefault(p, p)
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p

    def union(a: Point, b: Point) -> None:
        parent[find(a)] = find(b)

    gnd: Point | None = None
    for e in elements:
        ts = terminals(e)
        if ts is None:
            continue
        for p in ts:
            find(p)
        if e.type == "w":
            union(e.p1, e.p2)
        elif e.type == "g" and merge_ground:
            if gnd is None:
                gnd = e.p1
            union(gnd, e.p1)
    ids: dict[Point, int] = {}
    out: dict[Point, int] = {}
    for p in list(parent):
        out[p] = ids.setdefault(find(p), len(ids))
    return out
