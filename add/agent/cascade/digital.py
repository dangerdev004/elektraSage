"""Digital (clocked-logic) evaluation of a CircuitJS netlist, for the digital cascade.

The analog engine solves AC nodal equations; that is meaningless for clocked logic, so digital chains get
their own checker: read the finished netlist, work out which pins touch, and step the logic clock edge by
clock edge. What is modelled (an ideal, zero-delay logic simulation):

  * `R` rails: DC (wf 0) or square wave (wf 2) with its frequency, high level and low level;
  * `L` logic inputs (a fixed level), `M` logic outputs (observed), wires, ground;
  * D flip-flop (`155` / `DFlipFlop`): latches D into Q on the rising clock edge;
  * JK flip-flop (`156` / `JKFlipFlop`): falling-edge, J = K = 1 toggles (J/K read from the nets);
  * 2:1 mux (`mux`): see MUX_ROWS - the pin order is taken from the generator's documented design;
  * inverter (`I`) and logic gates (150 AND, 151 NAND, 152 OR, 153 NOR, 154 XOR).

Not modelled: propagation delay, glitches, set/reset pins, analog loading. A zero-delay model is therefore
blind to ripple-counter glitches and to sampling races; the cascade reports those as flags, never as proof.

Pin geometry (CircuitJS ChipElm with size 2, checked against the generators' own constants): west pins at x1,
east pins at x1 + 96, rows 32 apart starting at y1. The mux select sits at x1 + 64, y1 + 96.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .dump import Element, Netlist, Point, parse, terminals

ROW = 32
EAST = 96
GATES = {"150": "and", "151": "nand", "152": "or", "153": "nor", "154": "xor"}

# Mux pin rows (west side). The PISO generator documents "I0 = parallel input toggle, I1 = previous Q" and
# wires the toggle to row 1 and the previous Q to row 0, so row 1 is selected when S0 = 0, row 0 when S0 = 1.
MUX_ROWS = {0: 1, 1: 0}

CHIPS_D = {"155", "DFlipFlop"}
CHIPS_JK = {"156", "JKFlipFlop"}
CHIPS_MUX = {"mux"}


def _is(e: Element, names) -> bool:
    return e.type in names


def chip_pins(e: Element) -> dict[str, Point] | None:
    """Named pin points of the chips this module understands (None for anything else)."""
    x, y = e.x1, e.y1
    if _is(e, CHIPS_D):
        return {"d": (x, y), "clk": (x, y + ROW), "q": (x + EAST, y), "qn": (x + EAST, y + ROW)}
    if _is(e, CHIPS_JK):
        return {"j": (x, y), "clk": (x, y + ROW), "k": (x, y + 2 * ROW),
                "q": (x + EAST, y), "qn": (x + EAST, y + 2 * ROW)}
    if _is(e, CHIPS_MUX):
        return {"r0": (x, y), "r1": (x, y + ROW), "s": (x + 64, y + 3 * ROW), "out": (x + EAST, y)}
    if e.type == "I":
        return {"in": e.p1, "out": e.p2}
    return None


def pins_of(e: Element) -> list[Point]:
    p = chip_pins(e)
    if p is not None:
        return list(p.values())
    ts = terminals(e)
    return list(ts) if ts is not None else [e.p1]


def waveform(e: Element) -> str:
    return e.attr("wf", "0") if e.attrs is not None else (e.tail[0] if e.tail else "0")


def rail_params(e: Element) -> tuple[str, float, float, float]:
    """(waveform, frequency, max, bias) of an `R` rail, legacy or xml."""
    if e.attrs is not None:
        return (e.attr("wf", "0"), float(e.attr("fr", "40")), float(e.attr("maxv", "5")), float(e.attr("bias", "0")))
    t = e.tail
    return (t[0], float(t[1]), float(t[2]), float(t[3]))


def input_level(e: Element) -> bool:
    """Level of an `L` toggle: legacy tail[0] / xml attribute p (1 = high)."""
    if e.attrs is not None:
        return e.attr("p", "0") == "1"
    return bool(e.tail) and e.tail[0] == "1"


@dataclass
class Trace:
    times: list[float] = field(default_factory=list)
    rows: dict[str, list[int]] = field(default_factory=dict)      # label -> sampled logic levels


class Sim:
    """Zero-delay logic simulation of one netlist."""

    def __init__(self, nl: Netlist | str, thresholds: float = 2.5):
        self.nl = parse(nl) if isinstance(nl, str) else nl
        self.els = self.nl.elements
        self.parent: dict[Point, Point] = {}
        for e in self.els:
            for p in pins_of(e):
                self._find(p)
            if e.type == "w":
                self._union(e.p1, e.p2)
        self.state: dict[int, int] = {}              # element index -> stored Q
        self.last_clk: dict[int, int] = {}
        for i, e in enumerate(self.els):
            if _is(e, CHIPS_D | CHIPS_JK):
                self.state[i] = 0
        self.clock_sources = [(i, rail_params(e)) for i, e in enumerate(self.els)
                              if e.type == "R" and rail_params(e)[0] == "2"]
        self.drive: dict[int, object] = {}           # element index of an `L` -> callable(t) -> 0/1
        self.problems: list[str] = []
        self._check_drivers()

    def _find(self, p: Point) -> Point:
        self.parent.setdefault(p, p)
        while self.parent[p] != p:
            self.parent[p] = self.parent[self.parent[p]]
            p = self.parent[p]
        return p

    def _union(self, a: Point, b: Point) -> None:
        self.parent[self._find(a)] = self._find(b)

    def net(self, p: Point) -> Point:
        return self._find(p)

    def _check_drivers(self) -> None:
        """Every net with an input pin must have exactly one driver."""
        drivers: dict[Point, list[str]] = {}
        for i, e in enumerate(self.els):
            for name, p in self._outputs(i):
                drivers.setdefault(self.net(p), []).append(f"{e.type}#{i}.{name}")
        for n, d in drivers.items():
            if len(d) > 1:
                self.problems.append(f"net {n} has several drivers: {', '.join(d)}")

    def _outputs(self, i: int):
        e = self.els[i]
        if e.type == "R" or e.type == "L":
            yield ("out", e.p1)
        elif _is(e, CHIPS_D | CHIPS_JK):
            p = chip_pins(e)
            yield ("q", p["q"])
            yield ("qn", p["qn"])
        elif _is(e, CHIPS_MUX):
            yield ("out", chip_pins(e)["out"])
        elif e.type == "I":
            yield ("out", e.p2)
        elif e.type in GATES:
            yield ("out", e.p2)

    # ----- one settle pass -------------------------------------------------
    def _rail_value(self, e: Element, t: float) -> int:
        wf, f, mx, bias = rail_params(e)
        if wf == "2":
            period = 1.0 / f
            high = (t % period) < period / 2
            return int((bias + (mx if high else -mx)) > 2.5)
        return int((bias + mx) > 2.5) if wf == "0" else 0

    def _eval(self, t: float) -> dict[Point, int]:
        """Settled level of every net at time t, given the flip-flop states."""
        val: dict[Point, int] = {}
        for i, e in enumerate(self.els):
            if e.type == "R":
                val[self.net(e.p1)] = self._rail_value(e, t)
            elif e.type == "L":
                f = self.drive.get(i)
                val[self.net(e.p1)] = int(f(t)) if f is not None else int(input_level(e))
            elif e.type == "g":
                val.setdefault(self.net(e.p1), 0)
        for _ in range(len(self.els) + 5):
            changed = False
            for i, e in enumerate(self.els):
                new = None
                if _is(e, CHIPS_D | CHIPS_JK):
                    p = chip_pins(e)
                    for nm, pt in (("q", p["q"]), ("qn", p["qn"])):
                        v = self.state[i] if nm == "q" else 1 - self.state[i]
                        if val.get(self.net(pt)) != v:
                            val[self.net(pt)] = v
                            changed = True
                    continue
                if _is(e, CHIPS_MUX):
                    p = chip_pins(e)
                    s = val.get(self.net(p["s"]), 0)
                    row = "r0" if s else "r1"
                    new = (self.net(p["out"]), val.get(self.net(p[row]), 0))
                elif e.type == "I":
                    new = (self.net(e.p2), 1 - val.get(self.net(e.p1), 0))
                elif e.type in GATES:
                    ts = terminals(e)
                    ins = [val.get(self.net(q), 0) for q in ts[:-1]]
                    k = GATES[e.type]
                    v = {"and": all(ins), "nand": not all(ins), "or": any(ins), "nor": not any(ins),
                         "xor": sum(ins) % 2 == 1}[k]
                    new = (self.net(e.p2), int(v))
                if new is not None and val.get(new[0]) != new[1]:
                    val[new[0]] = new[1]
                    changed = True
            if not changed:
                break
        return val

    def _edges(self, val: dict[Point, int], first: bool) -> bool:
        """Apply clocked updates; True if any state changed."""
        changed = False
        pending: dict[int, int] = {}
        for i, e in enumerate(self.els):
            if _is(e, CHIPS_D):
                p = chip_pins(e)
                clk = val.get(self.net(p["clk"]), 0)
                if not first and clk and not self.last_clk.get(i, 0):
                    pending[i] = val.get(self.net(p["d"]), 0)
                self.last_clk[i] = clk
            elif _is(e, CHIPS_JK):
                p = chip_pins(e)
                clk = val.get(self.net(p["clk"]), 0)
                if not first and (not clk) and self.last_clk.get(i, 0):
                    j, k = val.get(self.net(p["j"]), 0), val.get(self.net(p["k"]), 0)
                    q = self.state[i]
                    pending[i] = 1 if (j and not k) else 0 if (k and not j) else (1 - q) if (j and k) else q
                self.last_clk[i] = clk
        for i, v in pending.items():
            if self.state[i] != v:
                self.state[i] = v
                changed = True
        return changed

    def step(self, t: float, first: bool = False) -> dict[Point, int]:
        """Advance to time t: settle, take clock edges, ripple until quiet, return the settled nets."""
        val = self._eval(t)
        for _ in range(4 * len(self.els) + 8):           # ripple: one flip-flop's Q can clock the next
            if not self._edges(val, first):
                break
            first = False
            val = self._eval(t)
        return val

    # ----- observation -----------------------------------------------------
    def markers(self) -> list[tuple[int, Point]]:
        """Logic-output markers (`M`) in left-to-right, top-to-bottom order."""
        ms = [(i, e.p1) for i, e in enumerate(self.els) if e.type == "M"]
        return sorted(ms, key=lambda m: (m[1][0], m[1][1]))

    def run(self, duration: float, dt: float, watch: list[tuple[str, Point]]) -> Trace:
        tr = Trace(rows={n: [] for n, _ in watch})
        t, first = 0.0, True
        while t <= duration + 1e-12:
            val = self.step(t, first)
            first = False
            tr.times.append(t)
            for n, p in watch:
                tr.rows[n].append(val.get(self.net(p), 0))
            t += dt
        return tr
