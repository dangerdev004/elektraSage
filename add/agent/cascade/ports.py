"""Infer a circuit's input/output ports from its CircuitJS dump.

Convention the generators already follow (checked by conformance.py):
  * a *signal source* (v / R rail with an AC-type waveform / 170 sweep) drives
    the circuit; its hot terminal is the INPUT node. The hot terminal of a
    two-terminal source is the one NOT on the ground net; for the
    single-post sources (R, 170) it is the post itself;
  * an `O` marker sits on the OUTPUT node.
DC rails (waveform 0) are supplies, not inputs, and are left alone.

Circuits that break the convention get an entry in PORT_OVERRIDES (L2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .dump import Element, Netlist, Point, nets, terminals

SIGNAL_SOURCE_TYPES = {"v", "R", "170"}


@dataclass
class Port:
    name: str
    node: Point
    element: int | None   # index of the source (inputs) / O marker (outputs), if any


@dataclass
class Ports:
    inputs: list[Port] = field(default_factory=list)
    outputs: list[Port] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)   # "info:" prefix = soft

    @property
    def role(self) -> str:
        """stage (in+out), source (out only: oscillator/generator), sink, none."""
        if self.inputs and self.outputs:
            return "stage"
        if self.outputs:
            return "source"
        if self.inputs:
            return "sink"
        return "none"

    @property
    def hard_problems(self) -> list[str]:
        return [p for p in self.problems if not p.startswith("info:")]


def waveform(e: Element) -> str:
    if e.attrs is not None:                    # xml dialect
        return e.attrs.get("wf", "0")
    return e.tail[0] if e.tail else "0"        # legacy dialect


def is_signal_source(e: Element) -> bool:
    if e.type == "170":
        return True
    if e.type in ("v", "R"):
        return waveform(e) != "0"              # waveform 0 = DC = supply rail
    return False


def infer(nl: Netlist) -> Ports:
    ports = Ports()
    net_of = nets(nl.elements)
    gnd_nets = {net_of[e.p1] for e in nl.elements if e.type == "g"}

    for i, e in enumerate(nl.elements):
        if not is_signal_source(e):
            continue
        if e.type in ("R", "170"):
            hot = e.p1
        else:
            cand = [p for p in (e.p1, e.p2) if net_of.get(p) not in gnd_nets]
            if len(cand) != 1:
                ports.problems.append(
                    f"source #{i} ({e.type}): cannot tell which terminal is hot "
                    f"({len(cand)} candidates not on the ground net)")
                continue
            hot = cand[0]
        ports.inputs.append(Port(f"in{len(ports.inputs) + 1}", hot, i))

    for i, e in enumerate(nl.elements):
        if e.type == "O":
            ports.outputs.append(Port(f"out{len(ports.outputs) + 1}", e.p1, i))

    # Each node must actually touch something else, or the port is imaginary.
    # Elements whose pins we cannot see (chips) make this unverifiable, so
    # the finding is downgraded to a soft "info:" note in that case.
    blind = any(terminals(e) is None and e.type != "x" for e in nl.elements)
    for p in ports.inputs + ports.outputs:
        touching = [j for j, e in enumerate(nl.elements)
                    if j != p.element and e.type not in ("g", "O")
                    and (ts := terminals(e)) is not None
                    and any(net_of.get(t) == net_of.get(p.node) for t in ts)]
        if not touching:
            note = f"{p.name} at {p.node} touches no element with known pins"
            ports.problems.append(("info: " + note + " (chips present)") if blind
                                  else note)
    if not ports.inputs and not ports.outputs:
        ports.problems.append("neither a signal source nor an `O` output marker found")
    return ports


# L2: per-circuit port overrides for generators that break the convention.
# name -> callable(Netlist) -> Ports.  Filled in once conformance shows which
# circuits need one.
def _phaseshift(nl: Netlist) -> Ports:
    """rc_phaseshift is an oscillator: no source, no `O`; output = op-amp output."""
    amps = [i for i, e in enumerate(nl.elements) if e.type == "a"]
    if len(amps) != 1:
        return Ports(problems=[f"expected exactly one op amp, found {len(amps)}"])
    return Ports(outputs=[Port("out1", nl.elements[amps[0]].p2, None)])


def _outputs_only(nl: Netlist) -> Ports:
    """Power supplies drive themselves (a floating gate or mains source): only the `O` markers are ports."""
    ports = infer(nl)
    ports.inputs = []
    ports.problems = [p for p in ports.problems if not p.startswith("source #")]
    return ports


PORT_OVERRIDES: dict[str, Callable[[Netlist], Ports]] = {
    "rc_phaseshift": _phaseshift,
    "full_wave_rectifier": _outputs_only,
    "buck_converter": _outputs_only,
    "boost_converter": _outputs_only,
    "buck_boost_converter": _outputs_only,
    "cuk_converter": _outputs_only,
}


def ports_for(name: str, nl: Netlist) -> Ports:
    if name in PORT_OVERRIDES:
        return PORT_OVERRIDES[name](nl)
    return infer(nl)
