"""Generate a Falstad (CircuitJS) sawtooth / pulse oscillator netlist."""

import math
import warnings
from typing import NamedTuple

from ._parts import (DesignWarning, assemble, cap, diode, gnd, index_of, lamp, opamp, out_marker,
                     res, wire)

# Fixed by the exported Falstad circuit.
OPAMP_RAIL_V = 15.0             # both op-amps swing to +/-15 V: this is the square-wave level
OPAMP_GAIN = 1e5

DEFAULT_C_F = 2e-7              # the exported integrator capacitor
DEFAULT_RFB_OHM = 100000.0      # the exported positive-feedback resistor (comparator output to + input)
DEFAULT_VPK_V = 6.0             # the exported triangle peak (R1 = 40 kohm on Rfb = 100 kohm)
DEFAULT_R_RISE_OHM = 40000.0    # the exported slow path: used while the triangle rises
DEFAULT_R_FALL_OHM = 1500.0     # the exported fast path: used while the triangle falls
DEFAULT_RISE_FRACTION = 0.96    # share of the period spent rising, used when only a frequency is given
EXPORT_TIMESTEP_S = 15.625e-6   # the exported simulation timestep
# Normal time step: the export's, shortened only when the waveform needs it.
STEPS_PER_PERIOD = 400          # minimum simulation steps per oscillation period
STEPS_PER_FAST_EDGE = 15        # minimum simulation steps on the fast edge (the export has 16)
# Fine time step (fine_step=True): min(export step / 4, fast edge / 240, period / 1600). On 24 random
# designs my test engine failed to converge on 6 with the normal step and on none with this one.
FINE_MAX_TIMESTEP_S = EXPORT_TIMESTEP_S / 4.0
FINE_STEPS_PER_PERIOD = 1600
FINE_STEPS_PER_FAST_EDGE = 240
SCOPE_PERIODS = 6.6             # the scope window is set to show about this many periods (the export: 6.6)
SCOPE_WIDTH_PX = 1433           # scope width of the screen the export was seen on; only sets the sweep speed
START_FRACTION = 0.9            # the triangle starts at +this fraction of its peak (capacitor pre-charged)

# Falstad's "default" diode model: I = Is (exp(V / (n Vt)) - 1), no series resistance.
DIODE_IS_A = 1.7143528192808883e-7
DIODE_N = 2.0
DIODE_VT_V = 0.025865


def diode_drop(i_a: float) -> float:
    """Forward voltage (V) of the default diode at current i_a."""
    return DIODE_N * DIODE_VT_V * math.log(i_a / DIODE_IS_A + 1.0)


def path_current(r_ohm: float) -> float:
    """Current (A) through diode + r_ohm when the comparator output (+/-15 V) drives the
    integrator's virtual ground:  Vsat = I R + Vd(I)   (solved by bisection)."""
    lo, hi = 0.0, OPAMP_RAIL_V / r_ohm
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if mid * r_ohm + diode_drop(mid) < OPAMP_RAIL_V:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def path_resistance(i_a: float) -> float:
    """Resistor that gives current i_a through diode + resistor from the +/-15 V output."""
    return (OPAMP_RAIL_V - diode_drop(i_a)) / i_a


class SawtoothValues(NamedTuple):
    Rfb: float             # comparator feedback resistor, comparator output to + input (ohm)
    R1: float              # resistor from the triangle output to the comparator + input (ohm)
    R_rise: float          # resistor in the path used while the output rises (ohm)
    R_fall: float          # resistor in the path used while the output falls (ohm)
    C: float               # integrator capacitor (F)
    vpk_v: float           # waveform peak voltage (+/- this)
    t_rise_s: float        # ideal rise time, -Vpk to +Vpk
    t_fall_s: float        # ideal fall time, +Vpk to -Vpk
    f_hz: float            # ideal oscillation frequency
    rise_fraction: float   # t_rise / period
    f_sim_hz: float        # frequency Falstad will actually show (a little lower: time-step effect)
    peak_hi_v: float       # high peak Falstad will show (a little above +Vpk)
    peak_lo_v: float       # low peak magnitude Falstad will show (a little beyond Vpk)
    i_rise_a: float        # current charging the capacitor while rising
    i_fall_a: float        # current while falling
    vd_rise_v: float       # diode drop in the rising path
    vd_fall_v: float       # diode drop in the falling path
    timestep_s: float
    scope_speed: int       # scope sweep speed (steps per pixel) chosen to show about 6.6 periods


def calculate(
    f_hz: float = None,
    rise_fraction: float = None,
    vpk_v: float = DEFAULT_VPK_V,
    c_f: float = DEFAULT_C_F,
    r_rise_ohms: float = None,
    r_fall_ohms: float = None,
    rfb_ohms: float = DEFAULT_RFB_OHM,
    timestep_s: float = None,
    fine_step: bool = False,
) -> SawtoothValues:
    """
    Sawtooth / pulse oscillator: the triangle oscillator (Schmitt-trigger comparator + inverting
    integrator) with the integrator's input resistor split into two diode paths:

        comparator output high (+15 V)  ->  diode + R_fall  -> integrator output FALLS
        comparator output low  (-15 V)  ->  diode + R_rise  -> integrator output RISES

    Each ramp has its own slope, so the triangle becomes a sawtooth. The peak is set only by the
    comparator, Vpk = 15 V * R1 / Rfb. The slope of each ramp is the current in its path over C,
    where the current comes from  15 V = I R + Vd(I)  and Vd is the diode drop (the default
    diode: n = 2, Is = 1.7e-7 A, so about 0.4 V at 0.4 mA and 0.55 V at 10 mA):

        t_rise = 2 Vpk C / I_rise            t_fall = 2 Vpk C / I_fall
        f = 1 / (t_rise + t_fall)            rise_fraction = t_rise / (t_rise + t_fall)

    Two ways to set it (or neither: the export's 40 kohm / 1.5 kohm):
      * f_hz and rise_fraction (default 0.96, a slow rise and a fast fall like the export):
        both resistors are calculated;
      * r_rise_ohms and r_fall_ohms (both): the frequency and rise fraction are reported.
    A rise fraction below 0.5 gives the opposite sawtooth (slow fall, fast rise); 0.5 is a triangle.

    Time step: by default the export's 15.625 us, shortened only for fast edges (about 15 steps per
    fast edge, at least 400 per period). The default design therefore runs exactly like your export.
    That is coarse, though: the comparator switches up to 0.7 V late, with the diodes changing over at
    the same moment. In MY test engine the solver then often fails to converge ("convergence failed
    after 5000 iterations") on that switch, and it does so on your own export too (6 of 24 random
    designs failed; at a quarter of the step none did). The real Falstad ran your export fine, so
    this may only be my engine, but if you see that message, or the waveform freezes, use
    fine_step=True (a quarter of the step or finer: safer, but 4x or more steps, so it runs more slowly and
    in slow motion), or give timestep_s yourself. The scope sweep speed is set from the time step so
    the scope always shows about 6.6 periods, as the export does.
    """
    by_f = f_hz is not None or rise_fraction is not None
    by_r = r_rise_ohms is not None or r_fall_ohms is not None
    if by_f and by_r:
        raise ValueError("give either the frequency (and rise fraction) OR the two resistors, not both")
    if by_r and (r_rise_ohms is None or r_fall_ohms is None):
        raise ValueError("give both resistors, R_rise and R_fall")
    if by_f and f_hz is None:
        raise ValueError("a rise fraction needs a frequency too")
    if c_f <= 0:
        raise ValueError("C must be > 0")
    if rfb_ohms <= 0:
        raise ValueError("Rfb must be > 0")
    if vpk_v <= 0:
        raise ValueError("peak must be > 0")
    if vpk_v >= OPAMP_RAIL_V:
        raise ValueError(
            f"peak {vpk_v:g} V is not below the op-amp's +/-{OPAMP_RAIL_V:g} V limits: "
            f"the comparator threshold is Vsat * R1 / Rfb, which needs R1 < Rfb"
        )
    r1 = rfb_ohms * vpk_v / OPAMP_RAIL_V

    if by_f:
        if f_hz <= 0:
            raise ValueError("frequency must be > 0")
        d = DEFAULT_RISE_FRACTION if rise_fraction is None else rise_fraction
        if not 0.0 < d < 1.0:
            raise ValueError("rise fraction must be between 0 and 1 (0.5 = triangle)")
        t_rise = d / f_hz
        t_fall = (1.0 - d) / f_hz
        i_rise = 2.0 * vpk_v * c_f / t_rise
        i_fall = 2.0 * vpk_v * c_f / t_fall
        r_rise = path_resistance(i_rise)
        r_fall = path_resistance(i_fall)
        if r_rise <= 0 or r_fall <= 0:
            raise ValueError("this frequency and rise fraction need a negative resistor: lower the "
                             "frequency, use a smaller C or a smaller peak")
    else:
        r_rise = DEFAULT_R_RISE_OHM if r_rise_ohms is None else r_rise_ohms
        r_fall = DEFAULT_R_FALL_OHM if r_fall_ohms is None else r_fall_ohms
        if r_rise <= 0 or r_fall <= 0:
            raise ValueError("resistors must be > 0")
        i_rise = path_current(r_rise)
        i_fall = path_current(r_fall)
        t_rise = 2.0 * vpk_v * c_f / i_rise
        t_fall = 2.0 * vpk_v * c_f / i_fall

    period = t_rise + t_fall
    f = 1.0 / period
    d_out = t_rise / period
    t_fast = min(t_rise, t_fall)
    if timestep_s is not None and timestep_s <= 0:
        raise ValueError("timestep must be > 0")
    if timestep_s is not None:
        timestep = timestep_s
    else:
        if fine_step:
            timestep = min(FINE_MAX_TIMESTEP_S, t_fast / FINE_STEPS_PER_FAST_EDGE, 1.0 / (FINE_STEPS_PER_PERIOD * f))
        else:
            timestep = min(EXPORT_TIMESTEP_S, t_fast / STEPS_PER_FAST_EDGE, 1.0 / (STEPS_PER_PERIOD * f))
    # scope sweep speed (Falstad uses powers of two): one pixel per 'sp' steps
    sp = 2 ** max(0, round(math.log2(SCOPE_PERIODS * period / (SCOPE_WIDTH_PX * timestep))))
    # The comparator can only switch on a time step, about one step late. The output keeps ramping
    # past each peak for that step, and the opposite ramp has to win that distance back:
    #   T = T0 + ts * (2 + t_rise/t_fall + t_fall/t_rise)
    f_sim = 1.0 / (period + timestep * (2.0 + t_rise / t_fall + t_fall / t_rise))
    # The falling edge overshoots its low peak by about one step of its slope (the rising edge does
    # the same at the high peak): the peaks Falstad will show are a little beyond +/-Vpk.
    peak_hi = vpk_v + 2.0 * vpk_v / t_rise * timestep
    peak_lo = vpk_v + 2.0 * vpk_v / t_fall * timestep

    if d_out < 0.02 or d_out > 0.98:
        warnings.warn(f"Rise fraction {d_out:.3f} is extreme: the fast edge lasts only "
                      f"{t_fast * 1e6:.3g} us, so the simulation needs a very small time step.", category=DesignWarning, stacklevel=2)
    if timestep < 5e-7:
        warnings.warn(f"Time step {timestep:.3g} s is very small: the simulation will run slowly.", category=DesignWarning, stacklevel=2)
    if max(i_rise, i_fall) > 0.05:
        warnings.warn(f"The fast path would carry {max(i_rise, i_fall) * 1e3:.3g} mA: far more than the "
                      f"few mA the diodes and op-amp of the export handle. Use a larger R or a smaller C.",
                      category=DesignWarning, stacklevel=2)
    if min(r_rise, r_fall) < 100 or max(r_rise, r_fall) > 1e7:
        warnings.warn(f"A resistor of {min(r_rise, r_fall):.4g} / {max(r_rise, r_fall):.4g} ohm is an unusual "
                      f"value for this circuit.", category=DesignWarning, stacklevel=2)
    if vpk_v < 0.5:
        warnings.warn(f"Peak {vpk_v:g} V is small: the threshold is only {vpk_v / OPAMP_RAIL_V:.3%} of the "
                      f"square-wave level, so offsets and the 1e5 op-amp gain start to matter.", category=DesignWarning, stacklevel=2)
    if vpk_v > 0.9 * OPAMP_RAIL_V:
        warnings.warn(f"Peak {vpk_v:g} V is close to the op-amp's +/-{OPAMP_RAIL_V:g} V limits; the integrator "
                      f"output may touch them.", category=DesignWarning, stacklevel=2)

    return SawtoothValues(rfb_ohms, r1, r_rise, r_fall, c_f, vpk_v, t_rise, t_fall, f, d_out, f_sim,
                          peak_hi, peak_lo, i_rise, i_fall, diode_drop(i_rise), diode_drop(i_fall), timestep, sp)


def sawtooth_oscillator(
    f_hz: float = None,
    rise_fraction: float = None,
    vpk_v: float = DEFAULT_VPK_V,
    c_f: float = DEFAULT_C_F,
    r_rise_ohms: float = None,
    r_fall_ohms: float = None,
    rfb_ohms: float = DEFAULT_RFB_OHM,
    timestep_s: float = None,
    fine_step: bool = False,
) -> str:
    """Generate a Falstad-format sawtooth / pulse oscillator (the triangle oscillator with two diode ramp paths).

    A Schmitt comparator drives an inverting integrator through two parallel diode + resistor paths, one
    for each polarity of the comparator output, so the output rises and falls at different slopes:
        t_rise = 2 Vpk C / I_rise        t_fall = 2 Vpk C / I_fall        f = 1 / (t_rise + t_fall)
    where each current solves 15 V = I R + Vd(I) with the default diode. The peak is Vpk = 15 V * R1 / Rfb.
    Set it with f_hz and rise_fraction (share of the period spent rising, default 0.96; 0.5 is a triangle;
    below 0.5 the sawtooth is reversed), OR with both ramp resistors r_rise_ohms and r_fall_ohms;
    with none of them the circuit is 40 kohm / 1.5 kohm. The output is the sawtooth (the integrator output,
    +/- vpk_v). The coarse default time step can make some solvers fail at the diode switch-over: use
    fine_step=True (a quarter of the step or finer, slower) if the waveform freezes. This circuit
    generates its own signal and has no signal input, so it can only be the FIRST stage of a cascade.

    Args:
        f_hz: Oscillation frequency in hertz (needs no resistors; alternative to the two resistors).
        rise_fraction: Share of the period spent rising, 0 to 1 (only with f_hz).
        vpk_v: Peak voltage, +/- this many volts (below 15).
        c_f: Integrator capacitor in farads.
        r_rise_ohms: Resistor of the rising-ramp path in ohms (give with r_fall_ohms).
        r_fall_ohms: Resistor of the falling-ramp path in ohms (give with r_rise_ohms).
        rfb_ohms: Comparator feedback resistor in ohms; only sets the divider's scale.
        timestep_s: Simulation time step in seconds (default chosen from the waveform).
        fine_step: Use a 4x finer time step.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If both a frequency and the resistors are given, a value is out of range, or the
            requested speed needs a negative resistor.

    Warns:
        DesignWarning: If the rise fraction is extreme, the time step very small, the ramp current very
            large, or the peak tiny or near the limits.
    """
    v = calculate(f_hz, rise_fraction, vpk_v, c_f, r_rise_ohms, r_fall_ohms, rfb_ohms, timestep_s, fine_step)
    start = -START_FRACTION * v.vpk_v
    g = OPAMP_RAIL_V
    el = [
        opamp(176, 368, 288, 368, g),                      # comparator
        wire(176, 384, 176, 448),
        wire(176, 448, 288, 448),
        res(288, 368, 288, 448, v.Rfb),                    # Rfb
        opamp(400, 384, 512, 384, g),                      # integrator
        res(288, 448, 368, 448, v.R1),                     # R1
        wire(368, 448, 512, 448),
        wire(512, 448, 512, 384),
        wire(512, 384, 512, 320),
        cap(400, 320, 512, 320, v.C, start),               # integrator C, pre-charged
        wire(400, 320, 400, 368),
        gnd(400, 400, 400, 416),
        wire(176, 352, 144, 352),
        gnd(144, 352, 144, 384),
        res(400, 320, 336, 320, v.R_fall),                 # R_fall (comparator high)
        res(400, 368, 336, 368, v.R_rise),                 # R_rise (comparator low)
        diode(288, 320, 336, 320),                         # comparator high -> R_fall
        diode(336, 368, 288, 368),                         # R_rise -> comparator low
        wire(288, 320, 288, 368),
        out_marker(512, 384, 576, 384),                    # sawtooth output
    ]
    scale = 10 if v.vpk_v <= 8 else 20
    return assemble(el, v.timestep_s, [(index_of(el, "O"), scale, v.scope_speed)])
