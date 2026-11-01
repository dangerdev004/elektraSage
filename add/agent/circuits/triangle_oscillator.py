"""Generate a Falstad (CircuitJS) triangle / square wave oscillator netlist."""

import math
import warnings
from typing import NamedTuple

from ._parts import (DesignWarning, assemble, cap, diode, gnd, index_of, lamp, opamp, out_marker,
                     res, wire)

# Fixed by the exported Falstad circuit.
OPAMP_RAIL_V = 15.0             # both op-amps swing to +/-15 V: this is the square-wave level
OPAMP_GAIN = 1e5

DEFAULT_C_F = 4e-7              # the exported integrator capacitor
DEFAULT_RFB_OHM = 10000.0       # the exported positive-feedback resistor (comparator output to + input)
DEFAULT_VPK_V = 6.0             # the exported triangle peak
DEFAULT_F_HZ = 156.25           # the exported frequency
DEFAULT_TIMESTEP_S = 15.625e-6  # the exported simulation timestep
STEPS_PER_PERIOD = 400          # minimum simulation steps per oscillation period
START_FRACTION = 0.9            # the triangle starts at +this fraction of its peak (the capacitor is pre-charged)


class TriangleValues(NamedTuple):
    Rfb: float             # comparator feedback resistor, comparator output to + input (ohm)
    R1: float              # resistor from the triangle output to the comparator + input (ohm)
    Rint: float            # integrator input resistor (ohm)
    C: float               # integrator capacitor (F)
    vpk_v: float           # triangle peak voltage (+/- this)
    vpp_v: float           # triangle peak-to-peak
    f_hz: float            # ideal oscillation frequency
    f_sim_hz: float        # frequency Falstad will actually show (a little lower: time-step effect)
    period_s: float
    slope_v_per_s: float   # triangle slope = Vsat / (Rint C)
    timestep_s: float


def calculate(
    f_hz: float = None,
    vpk_v: float = DEFAULT_VPK_V,
    c_f: float = DEFAULT_C_F,
    r_int_ohms: float = None,
    rfb_ohms: float = DEFAULT_RFB_OHM,
) -> TriangleValues:
    """
    Triangle / square wave oscillator: a Schmitt-trigger comparator (op-amp 1) driving an
    inverting integrator (op-amp 2) whose output is fed back to the comparator.

        comparator + input  = divider between its own output (through Rfb)
                              and the triangle output (through R1)
        comparator switches when that input crosses 0 V (inverting input is grounded):
            triangle peak  Vpk = Vsat * R1 / Rfb          (Vsat = 15 V op-amp limit)
        integrator slope       = Vsat / (Rint C)
        one period = 4 Vpk / slope, so

            f = Rfb / (4 R1 Rint C) = Vsat / (4 Vpk Rint C)

    Give the peak voltage vpk_v (R1 = Rfb Vpk / Vsat is solved), the capacitor c_f and EITHER
    f_hz (Rint = Vsat / (4 Vpk f C) is solved) OR r_int_ohms (the frequency is then reported).
    With neither f_hz nor r_int_ohms, 156.25 Hz as in the export.
    Rfb only sets the scale of the divider (default 10 kohm); the frequency and peak do not depend on it.

    Both outputs are available in Falstad: the square wave at the comparator output and the
    triangle at the integrator output (the one the export's scope and audio output use).
    """
    if f_hz is not None and r_int_ohms is not None:
        raise ValueError("give either the frequency OR the integrator resistor, not both")
    if c_f <= 0:
        raise ValueError("C must be > 0")
    if rfb_ohms <= 0:
        raise ValueError("Rfb must be > 0")
    if vpk_v <= 0:
        raise ValueError("triangle peak must be > 0")
    if vpk_v >= OPAMP_RAIL_V:
        raise ValueError(
            f"triangle peak {vpk_v:g} V is not below the op-amp's +/-{OPAMP_RAIL_V:g} V limits: "
            f"the comparator threshold is Vsat * R1 / Rfb, which needs R1 < Rfb"
        )
    if f_hz is not None and f_hz <= 0:
        raise ValueError("frequency must be > 0")
    if r_int_ohms is not None and r_int_ohms <= 0:
        raise ValueError("integrator resistor must be > 0")

    r1 = rfb_ohms * vpk_v / OPAMP_RAIL_V
    if r_int_ohms is not None:
        r_int = r_int_ohms
    else:
        f_wanted = f_hz if f_hz is not None else DEFAULT_F_HZ
        r_int = OPAMP_RAIL_V / (4.0 * vpk_v * f_wanted * c_f)
    f = OPAMP_RAIL_V / (4.0 * vpk_v * r_int * c_f)
    slope = OPAMP_RAIL_V / (r_int * c_f)

    if vpk_v < 0.5:
        warnings.warn(f"Peak {vpk_v:g} V is small: the threshold is only {vpk_v / OPAMP_RAIL_V:.3%} of the "
                      f"square-wave level, so offsets and the 1e5 op-amp gain start to matter.", category=DesignWarning, stacklevel=2)
    if vpk_v > 0.9 * OPAMP_RAIL_V:
        warnings.warn(f"Peak {vpk_v:g} V is close to the op-amp's +/-{OPAMP_RAIL_V:g} V limits; the integrator "
                      f"output may touch them.", category=DesignWarning, stacklevel=2)
    if r_int < 100 or r_int > 1e6:
        warnings.warn(f"Integrator R = {r_int:.4g} ohm is an unusual value for this circuit.", category=DesignWarning, stacklevel=2)
    if f < 1.0 or f > 20e3:
        warnings.warn(f"{f:.4g} Hz is outside the range this circuit was tested in (10 Hz to 5 kHz).", category=DesignWarning, stacklevel=2)

    timestep = min(DEFAULT_TIMESTEP_S, 1.0 / (STEPS_PER_PERIOD * f))
    # The comparator can only switch on a time step, so the triangle overshoots its peak by up to
    # one step of slope each half period. That lengthens the period by about 4 steps.
    f_sim = f / (1.0 + 4.0 * f * timestep)
    return TriangleValues(rfb_ohms, r1, r_int, c_f, vpk_v, 2.0 * vpk_v, f, f_sim, 1.0 / f, slope, timestep)


def _start_v(vpk_v: float) -> float:
    """Starting triangle voltage: close to the +peak, so it reaches the threshold almost at once."""
    return START_FRACTION * vpk_v


def triangle_oscillator(
    f_hz: float = None,
    vpk_v: float = DEFAULT_VPK_V,
    c_f: float = DEFAULT_C_F,
    r_int_ohms: float = None,
    rfb_ohms: float = DEFAULT_RFB_OHM,
) -> str:
    """Generate a Falstad-format triangle / square wave oscillator (Schmitt comparator + inverting integrator).

    Op-amp 1 is a Schmitt trigger whose + input sees its own output through Rfb and the triangle
    through R1; op-amp 2 integrates the comparator's +/-15 V square wave into a triangle that is fed
    back to the comparator. The comparator flips when the + input crosses 0 V, so
        triangle peak  Vpk = 15 V * R1 / Rfb          (R1 = Rfb * Vpk / 15 is solved)
        frequency      f = 15 V / (4 Vpk Rint C)       (independent of Rfb)
    Give the peak vpk_v and the capacitor c_f, and EITHER f_hz (Rint is solved) OR r_int_ohms (the
    frequency is then reported); with neither, 156.25 Hz. The output is the triangle (the integrator
    output, +/- vpk_v); the square wave is inside the circuit at the comparator. The integrator capacitor
    starts pre-charged so the triangle begins at +0.9 Vpk. This circuit generates its own signal and has
    no signal input, so it can only be the FIRST stage of a cascade.

    Args:
        f_hz: Oscillation frequency in hertz (alternative to r_int_ohms).
        vpk_v: Triangle peak voltage, +/- this many volts (below 15).
        c_f: Integrator capacitor in farads.
        r_int_ohms: Integrator input resistor in ohms (alternative to f_hz).
        rfb_ohms: Comparator feedback resistor in ohms; only sets the divider's scale.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If both f_hz and r_int_ohms are given, or a value is out of range.

    Warns:
        DesignWarning: If the peak is tiny or near the 15 V limits, or the frequency or resistor is outside
            the tested range.
    """
    v = calculate(f_hz, vpk_v, c_f, r_int_ohms, rfb_ohms)
    start = -_start_v(v.vpk_v)
    g = OPAMP_RAIL_V
    el = [
        opamp(160, 368, 272, 368, g),                      # comparator
        wire(160, 384, 160, 448),
        wire(160, 448, 272, 448),
        res(272, 368, 272, 448, v.Rfb),                    # Rfb: square -> + input
        opamp(384, 384, 496, 384, g),                      # integrator
        res(272, 448, 352, 448, v.R1),                     # R1: triangle -> + input
        wire(352, 448, 496, 448),
        wire(496, 448, 496, 384),
        wire(496, 384, 496, 320),
        cap(384, 320, 496, 320, v.C, start),               # integrator C, pre-charged
        wire(384, 320, 384, 368),
        res(272, 368, 384, 368, v.Rint),                   # Rint
        gnd(384, 400, 384, 416),
        wire(160, 352, 128, 352),
        gnd(128, 352, 128, 384),
        out_marker(496, 384, 592, 384),                    # triangle output
    ]
    scale = 10 if v.vpk_v <= 8 else 20
    return assemble(el, v.timestep_s, [(index_of(el, "O"), scale, 4)])
