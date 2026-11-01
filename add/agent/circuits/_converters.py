"""Shared design equations and building blocks for the four DC-DC converters (buck, boost, buck-boost, Cuk).

Continuous-conduction averages with the freewheel/blocking diode's forward drop VF included (Falstad's default
diode drops about 0.7 V at the currents used here); the MOSFET switch is nearly ideal (a few milliohms).
"""

import math
from typing import NamedTuple

from ._parts import (DesignWarning, assemble, cap, dc_rail, diode, gnd, ind, index_of, mosfet, out_marker,
                     require_positive, res, wire)

VF = 0.7                    # forward drop of Falstad's default diode at the design current (V)
GATE_HIGH_V = 10.0          # gate drive level
FET_VT = 1.5
FET_BETA = 10.0             # Rds(on) = 1 / (beta (Vgs - Vt)) = about 12 milliohm


class Converter(NamedTuple):
    topology: str
    vin: float
    vout: float            # signed output voltage (negative for buck-boost and Cuk)
    i_load: float
    f_sw: float
    duty: float
    L: float
    L2: float              # second inductor (Cuk) or 0
    C: float               # output capacitor
    C1: float              # coupling capacitor (Cuk) or 0
    r_load: float
    i_ripple: float        # peak-to-peak ripple current in the (first) inductor
    v_ripple: float        # peak-to-peak output ripple
    i_inductor: float      # average current in the (first) inductor
    mode_ok: bool          # stays in continuous conduction at the design load


def check_common(vin, vout, load_current, switching_frequency, ripple_current_fraction, output_ripple_fraction):
    for name, value in (("input_voltage", vin), ("output_voltage", vout), ("load_current", load_current),
                        ("switching_frequency", switching_frequency),
                        ("ripple_current_fraction", ripple_current_fraction),
                        ("output_ripple_fraction", output_ripple_fraction)):
        require_positive(name, value)
    if ripple_current_fraction >= 2:
        raise ValueError("ripple_current_fraction must be below 2")
    if output_ripple_fraction >= 0.5:
        raise ValueError("output_ripple_fraction must be below 0.5")


def diode_drop(amps: float) -> float:
    """Forward drop of Falstad's default diode (Is = 1.714e-7 A, n = 2) at the given current."""
    return 2 * 0.025865 * math.log(max(amps, 1e-6) / 1.7143528192808883e-7 + 1.0)


def design(topology, vin, vout, load_current, f_sw, r_i=0.3, r_v=0.01) -> Converter:
    """Design twice: the first pass finds the diode current, the second uses the drop at that current."""
    first = _design(topology, vin, vout, load_current, f_sw, r_i, r_v, VF)
    i_d = first.i_inductor if topology != "buck" else load_current
    return _design(topology, vin, vout, load_current, f_sw, r_i, r_v, diode_drop(i_d))


def _design(topology, vin, vout, load_current, f_sw, r_i, r_v, VF) -> Converter:
    check_common(vin, vout, load_current, f_sw, r_i, r_v)
    io = load_current
    rl = vout / io
    if topology == "buck":
        if vout >= vin - VF:
            raise ValueError(f"a buck converter needs output_voltage below the input (got {vout:g} V from {vin:g} V)")
        d = (vout + VF) / (vin + VF)
        i_l = io
        di = r_i * i_l
        L = (vin - vout) * d / (f_sw * di)
        c = di / (8 * f_sw * r_v * vout)
        dv = di / (8 * f_sw * c)
        return Converter(topology, vin, vout, io, f_sw, d, L, 0.0, c, 0.0, rl, di, dv, i_l, True)
    if topology == "boost":
        if vout <= vin:
            raise ValueError(f"a boost converter needs output_voltage above the input (got {vout:g} V from {vin:g} V)")
        d = 1 - vin / (vout + VF)
        i_l = io / (1 - d)
        di = r_i * i_l
        L = vin * d / (f_sw * di)
        c = io * d / (f_sw * r_v * vout)
        dv = io * d / (f_sw * c)
        return Converter(topology, vin, vout, io, f_sw, d, L, 0.0, c, 0.0, rl, di, dv, i_l, True)
    if topology == "buck_boost":
        d = (vout + VF) / (vin + vout + VF)
        i_l = io / (1 - d)
        di = r_i * i_l
        L = vin * d / (f_sw * di)
        c = io * d / (f_sw * r_v * vout)
        dv = io * d / (f_sw * c)
        return Converter(topology, vin, -vout, io, f_sw, d, L, 0.0, c, 0.0, rl, di, dv, i_l, True)
    if topology == "cuk":
        if vout <= VF:
            raise ValueError("output_voltage is too small for the diode drop")
        d = (vout + VF) / (vin + vout + VF)
        i_in = io * vout / vin
        di = r_i * i_in
        L1 = vin * d / (f_sw * di)
        di2 = r_i * io
        L2 = vin * d / (f_sw * di2)
        c = di2 / (8 * f_sw * r_v * vout)
        dv = di2 / (8 * f_sw * c)
        c1 = io * d / (f_sw * 0.02 * (vin / (1 - d)))
        return Converter(topology, vin, -vout, io, f_sw, d, L1, L2, c, c1, rl, di, dv, i_in, True)
    raise KeyError(topology)


def converter_warnings(cv: Converter):
    import warnings
    if cv.duty > 0.9 or cv.duty < 0.1:
        warnings.warn(f"the duty cycle comes out at {cv.duty:.0%}, which is hard to realise and makes the "
                      "average model rough", DesignWarning, stacklevel=3)
    if cv.L < 1e-6:
        warnings.warn(f"the inductor comes out at {cv.L:.3g} H, which is very small", DesignWarning, stacklevel=3)


def step_for(f_sw: float, duty: float = 0.5) -> float:
    """100 steps per switching period (aligning the on-time to whole steps was tried and gave a larger spread of
    output errors, so the plain step is kept)."""
    return min(1e-6, 1.0 / (100 * f_sw))


def gate_drive(x1, y1, x2, y2, f_sw, duty) -> str:
    """Floating square source, p2 positive: 0 V to GATE_HIGH_V above p1, high for `duty` of each period."""
    return (f"v {x1} {y1} {x2} {y2} 0 2 {f_sw!r} {GATE_HIGH_V / 2!r} {GATE_HIGH_V / 2!r} 0.0 {duty!r}")


def _fet(x, y):
    return mosfet(x, y, x + 32, y, FET_VT, FET_BETA)


def build(cv: Converter) -> str:
    """The netlist for a designed converter, started at its expected steady state."""
    vo = abs(cv.vout)
    t = cv.topology
    if t == "buck":
        el = [dc_rail(96, 64, 48, 64, cv.vin), wire(96, 64, 224, 64), wire(224, 64, 224, 80),
              _fet(192, 96), wire(224, 112, 224, 128), gate_drive(192, 128, 192, 96, cv.f_sw, cv.duty),
              wire(192, 128, 224, 128), ind(224, 128, 352, 128, cv.L, cv.i_inductor),
              diode(224, 192, 224, 128), gnd(224, 192, 224, 208),
              cap(352, 128, 352, 192, cv.C, cv.vout), gnd(352, 192, 352, 208),
              wire(352, 128, 432, 128), res(432, 128, 432, 192, cv.r_load), gnd(432, 192, 432, 208),
              out_marker(352, 128, 352, 80)]
    elif t == "boost":
        el = [dc_rail(96, 128, 48, 128, cv.vin), ind(96, 128, 224, 128, cv.L, cv.i_inductor),
              wire(224, 128, 224, 160), _fet(192, 176), gnd(224, 192, 224, 208),
              gate_drive(192, 208, 192, 176, cv.f_sw, cv.duty), gnd(192, 208, 192, 224),
              diode(224, 128, 352, 128), cap(352, 128, 352, 192, cv.C, cv.vout), gnd(352, 192, 352, 208),
              wire(352, 128, 432, 128), res(432, 128, 432, 192, cv.r_load), gnd(432, 192, 432, 208),
              out_marker(352, 128, 352, 80)]
    elif t == "buck_boost":
        el = [dc_rail(96, 64, 48, 64, cv.vin), wire(96, 64, 224, 64), wire(224, 64, 224, 80),
              _fet(192, 96), wire(224, 112, 224, 128), gate_drive(192, 128, 192, 96, cv.f_sw, cv.duty),
              wire(192, 128, 224, 128), ind(224, 128, 224, 192, cv.L, cv.i_inductor), gnd(224, 192, 224, 208),
              diode(352, 128, 224, 128), cap(352, 128, 352, 192, cv.C, cv.vout), gnd(352, 192, 352, 208),
              wire(352, 128, 432, 128), res(432, 128, 432, 192, cv.r_load), gnd(432, 192, 432, 208),
              out_marker(352, 128, 352, 80)]
    else:                                                    # cuk
        el = [dc_rail(96, 128, 48, 128, cv.vin), ind(96, 128, 224, 128, cv.L, cv.i_inductor),
              wire(224, 128, 224, 160), _fet(192, 176), gnd(224, 192, 224, 208),
              gate_drive(192, 208, 192, 176, cv.f_sw, cv.duty), gnd(192, 208, 192, 224),
              cap(224, 128, 352, 128, cv.C1, cv.vin + vo), diode(352, 128, 352, 192), gnd(352, 192, 352, 208),
              ind(352, 128, 432, 128, cv.L2, -cv.i_load), cap(432, 128, 432, 192, cv.C, cv.vout),
              gnd(432, 192, 432, 208), wire(432, 128, 512, 128), res(512, 128, 512, 192, cv.r_load),
              gnd(512, 192, 512, 208), out_marker(432, 128, 432, 80)]
    return assemble(el, step_for(cv.f_sw, cv.duty), [(index_of(el, "O"), max(1.0, round(vo / 4)))])
