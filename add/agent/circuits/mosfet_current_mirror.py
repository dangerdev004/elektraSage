"""Generate a Falstad (CircuitJS) N-MOSFET current-mirror netlist."""

import math
import warnings

from ._parts import (DesignWarning, assemble, dc_rail, gnd, mosfet, require_positive, res, switch, wire)

# Falstad's default MOSFET: square law, no channel-length modulation.
VT_V = 1.5
BETA = 0.02


def _solve_reference(vdd: float, r: float):
    """Diode-connected Q1 fed from vdd through r: returns (I, Vgs)."""
    s = math.sqrt(2 / BETA)
    x = (-s + math.sqrt(s * s + 4 * r * (vdd - VT_V))) / (2 * r)
    return x * x, VT_V + s * x


def _ids(vgs: float, vds: float) -> float:
    if vgs < VT_V:
        return 0.0
    vov = vgs - VT_V
    return BETA * (vov * vds - 0.5 * vds * vds) if vds < vov else 0.5 * BETA * vov * vov


def _solve_output(vout: float, rl: float, vgs: float) -> float:
    if rl <= 0:
        return _ids(vgs, vout)
    lo, hi = 0.0, vout / rl
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        lo, hi = (lo, mid) if mid - _ids(vgs, vout - mid * rl) > 0 else (mid, hi)
    return 0.5 * (lo + hi)


def mosfet_current_mirror(
    supply_voltage: float,
    reference_current: float,
    load_resistor: float = 100.0,
    aux_reference_resistor: float = 100.0,
    output_supply_voltage: float = None,
    reference_switch_closed: bool = False,
    load_switch_closed: bool = False,
) -> str:
    """Generate a Falstad-format 1:1 N-MOSFET current mirror.

    Q1 is diode-connected (gate tied to drain) and fed from the supply through Rref;
    Q2 shares Q1's gate and sinks the output current through the load RL from the output
    supply. With the Falstad default MOSFET (Vt = 1.5 V, beta = 0.02, no channel-length
    modulation) the design is: Vov = sqrt(2*Iref/beta), Vgs = Vt + Vov, Rref = (Vdd - Vgs)/Iref,
    and Iout = Iref as long as Q2 stays saturated (Vdd_out - Iout*RL >= Vov). Two switches
    change the test conditions: the reference switch puts an extra resistor in parallel with
    Rref (raising Iref), and the load switch shorts RL. This is a bias circuit with no signal
    input, so it cannot be cascaded with other stages.

    Args:
        supply_voltage: Reference-side supply Vdd in volts.
        reference_current: Design reference current in amps (0.005 = 5 mA), reference switch open.
        load_resistor: Load resistor on the output side in ohms.
        aux_reference_resistor: Extra resistor the reference switch puts in parallel with Rref, in ohms.
        output_supply_voltage: Output-side supply in volts. Default: same as supply_voltage.
        reference_switch_closed: Start with the reference switch closed.
        load_switch_closed: Start with the load switch closed (shorts the load).

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If any argument is not a finite number > 0, or if Q1 needs a Vgs at or above the
            supply (Rref would be zero or negative).

    Warns:
        DesignWarning: If Q2 leaves saturation in the starting switch state, so the output
            current no longer copies the reference.
    """
    vdd = supply_voltage
    vdd_out = vdd if output_supply_voltage is None else output_supply_voltage
    for name, value in (("supply_voltage", vdd), ("reference_current", reference_current),
                        ("load_resistor", load_resistor), ("aux_reference_resistor", aux_reference_resistor),
                        ("output_supply_voltage", vdd_out)):
        require_positive(name, value)

    vov = math.sqrt(2 * reference_current / BETA)
    vgs = VT_V + vov
    if vgs >= vdd:
        raise ValueError(f"Q1 needs Vgs = {vgs:.4g} V to carry {reference_current:g} A, which is not below the supply "
                         f"({vdd:g} V) - lower the current or raise the supply")
    rref = (vdd - vgs) / reference_current
    r_par = rref * aux_reference_resistor / (rref + aux_reference_resistor)
    i_ref, vgs_now = _solve_reference(vdd, r_par if reference_switch_closed else rref)
    rl_eff = 0.0 if load_switch_closed else load_resistor
    i_out = _solve_output(vdd_out, rl_eff, vgs_now)
    vd2 = vdd_out - i_out * rl_eff
    vov_now = vgs_now - VT_V
    if vd2 < vov_now - 1e-9:
        warnings.warn(f"Q2 leaves saturation: its drain sits at {vd2:.3g} V, below the overdrive {vov_now:.3g} V, so "
                      f"Iout = {i_out * 1e3:.4g} mA no longer copies Iref = {i_ref * 1e3:.4g} mA. Keep the load below "
                      f"about {(vdd_out - vov_now) / i_out:.4g} ohm or raise the output supply",
                      DesignWarning, stacklevel=2)

    el = [
        mosfet(320, 288, 240, 288, VT_V, BETA),
        mosfet(320, 288, 400, 288, VT_V, BETA),
        wire(320, 288, 320, 240),
        wire(320, 240, 240, 240),
        wire(240, 240, 240, 272),
        wire(240, 304, 240, 352),
        wire(240, 352, 320, 352),
        wire(400, 304, 400, 352),
        wire(400, 352, 320, 352),
        gnd(320, 352, 320, 384),
        dc_rail(240, 112, 240, 80, vdd),
        dc_rail(400, 112, 400, 80, vdd_out),
        wire(400, 272, 400, 240),
        res(400, 112, 400, 240, load_resistor),
        wire(400, 112, 448, 112),
        wire(400, 240, 448, 240),
        switch(448, 112, 448, 240, load_switch_closed),
        wire(240, 240, 192, 240),
        wire(240, 112, 192, 112),
        res(240, 112, 240, 240, rref),
        res(192, 112, 192, 176, aux_reference_resistor),
        switch(192, 176, 192, 240, reference_switch_closed),
    ]
    return assemble(el, 5e-6, [])
