"""Generate a Falstad (CircuitJS) phase-shift oscillator netlist."""

import math
import warnings
from typing import NamedTuple

from ._parts import (DesignWarning, assemble, cap, diode, gnd, index_of, lamp, opamp, out_marker,
                     res, wire)

# Fixed by the exported Falstad circuit.
OPAMP_RAIL_V = 15.0             # op-amp output limits (+/-15 V): this sets the oscillation amplitude
OPAMP_GAIN = 1e5

DEFAULT_C_F = 5e-7              # the exported capacitors (all three the same)
DEFAULT_R_OHM = 1000.0          # the exported resistors (all three the same)
DEFAULT_GAIN_MARGIN = 1.1       # loop gain as a multiple of the minimum needed (the export uses 1.0)
DEFAULT_TIMESTEP_S = 15.625e-6  # the exported simulation timestep
STEPS_PER_PERIOD = 400          # minimum simulation steps per oscillation period

# Minimum gain for equal-R, equal-C three-stage RC ladder with the last R into virtual ground.
MIN_GAIN = 29.0
FREQ_FACTOR = math.sqrt(6.0)    # f = 1 / (2 pi R C sqrt(6))

# Start-up kick: the capacitors cannot start at 0 V, because an ideal circuit sitting at 0 V
# stays at 0 V forever. These are the exported circuit's own stored voltages.
START_VOLTAGES_V = (11.203419848405368, 2.5297194011701425, -0.09856736712198844)


class PhaseShiftValues(NamedTuple):
    R: float               # all three resistors of the phase network (ohm)
    C: float               # all three capacitors (F)
    Rf: float              # op-amp feedback resistor (ohm)
    gain_margin: float     # Rf / (29 R)
    gain: float            # inverting gain Rf / R
    f_design_hz: float     # 1 / (2 pi R C sqrt(6)): frequency of 180 degrees of phase shift
    f_expected_hz: float   # estimate of the frequency actually seen once the output is clipping
    timestep_s: float


def calculate(
    f_hz: float = None,
    c_f: float = DEFAULT_C_F,
    r_ohms: float = None,
    gain_margin: float = DEFAULT_GAIN_MARGIN,
) -> PhaseShiftValues:
    """
    Op-amp phase-shift oscillator: an inverting amplifier whose feedback path is a
    three-stage RC network (series C, shunt R, series C, shunt R, series C, then R into the
    op-amp's virtual ground). Each stage can shift the phase by up to 90 degrees; the
    network gives exactly 180 degrees at

        f = 1 / (2 pi R C sqrt(6))

    and there it attenuates the signal by a factor of 29. The inverting amplifier supplies
    the other 180 degrees, so the loop oscillates when its gain is at least 29:

        Rf >= 29 R            (gain_margin = Rf / (29 R) >= 1)

    Give EITHER f_hz (R is then calculated: R = 1 / (2 pi f C sqrt(6))) OR r_ohms
    (the frequency is then reported). With neither, R = 1 kohm as in the export.

    Gain margin: a margin of exactly 1.0 is the textbook limit and, as in the exported
    circuit, the oscillation then slowly dies away (and would never start from 0 V). A margin
    above 1 lets it start and grow until the op-amp's +/-15 V limits stop it. The price is
    a flattened, distorted waveform and a frequency a little below the design value: roughly
    35 % of the margin excess, so a margin of 1.1 gives a frequency about 3.5 % low. The
    expected frequency printed is an empirical fit to engine simulations (margins 1.05 to 1.5).
    """
    if f_hz is not None and r_ohms is not None:
        raise ValueError("give either the frequency OR R, not both")
    if c_f <= 0:
        raise ValueError("C must be > 0")
    if f_hz is not None and f_hz <= 0:
        raise ValueError("frequency must be > 0")
    if r_ohms is not None and r_ohms <= 0:
        raise ValueError("R must be > 0")
    if gain_margin < 1.0:
        raise ValueError(
            f"gain margin {gain_margin:g} is below 1: the loop gain is less than the 29 needed, so "
            f"the oscillation can never sustain itself"
        )

    if f_hz is not None:
        r = 1.0 / (2.0 * math.pi * f_hz * c_f * FREQ_FACTOR)
    elif r_ohms is not None:
        r = r_ohms
    else:
        r = DEFAULT_R_OHM
    f_design = 1.0 / (2.0 * math.pi * r * c_f * FREQ_FACTOR)
    rf = MIN_GAIN * r * gain_margin
    excess = gain_margin - 1.0
    f_expected = f_design * (1.0 - 0.35 * excess + 0.12 * excess ** 2)   # empirical fit to simulations, good to about 1 %

    if gain_margin < 1.03:
        warnings.warn(
            f"Gain margin {gain_margin:g} is very small: the oscillation will start slowly, may fade "
            f"away instead of holding, and an ideal circuit starting from 0 V would not start at all. "
            f"Use 1.05 to 1.3 for a reliable start.",
            category=DesignWarning, stacklevel=2,
        )
    if gain_margin > 2.0:
        warnings.warn(
            f"Gain margin {gain_margin:g} is large: the output will clip hard (nearly a square wave) "
            f"and the frequency will fall well below the design value (about {f_expected:.4g} Hz).",
            category=DesignWarning, stacklevel=2,
        )
    if r < 100 or r > 1e6:
        warnings.warn(f"R = {r:.4g} ohm is an unusual value for this circuit.", category=DesignWarning, stacklevel=2)
    timestep = min(DEFAULT_TIMESTEP_S, 1.0 / (STEPS_PER_PERIOD * f_design))
    return PhaseShiftValues(r, c_f, rf, gain_margin, rf / r, f_design, f_expected, timestep)


def phase_shift_oscillator(
    f_hz: float = None,
    c_f: float = DEFAULT_C_F,
    r_ohms: float = None,
    gain_margin: float = DEFAULT_GAIN_MARGIN,
) -> str:
    """Generate a Falstad-format op-amp phase-shift (RC ladder) oscillator.

    An inverting amplifier whose feedback path is a three-stage RC network (series C, shunt R, series C,
    shunt R, series C, then R into the virtual ground). The network shifts the phase by exactly 180 degrees
    at f = 1 / (2 pi R C sqrt(6)) and attenuates by 29 there, so the loop oscillates when Rf >= 29 R. Give
    EITHER f_hz (R is solved) OR r_ohms (default 1 kohm). gain_margin is Rf / (29 R): 1.0 is the textbook
    limit, where the oscillation slowly dies away; the default 1.1 starts reliably and grows until the
    +/-15 V op-amp limits stop it, giving a flattened, distorted sine whose frequency is a few percent below
    the design value. This circuit generates its own signal and has no signal input, so it can only be the
    FIRST stage of a cascade. (It is an oscillator, unlike the passive rc_phaseshift filter.)

    Args:
        f_hz: Design frequency in hertz (alternative to r_ohms).
        c_f: Capacitance of all three capacitors in farads.
        r_ohms: Resistance of all three network resistors in ohms (alternative to f_hz).
        gain_margin: Loop gain as a multiple of the minimum needed (at least 1; 1.05 to 1.3 starts reliably).

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If both f_hz and r_ohms are given, the gain margin is below 1, or a value is not positive.

    Warns:
        DesignWarning: If the gain margin is very small or large, or R is an unusual value.
    """
    v = calculate(f_hz, c_f, r_ohms, gain_margin)
    v1, v2, v3 = START_VOLTAGES_V
    g = OPAMP_RAIL_V
    el = [
        cap(144, 368, 208, 368, v.C, v1),                  # C1: output into the network
        cap(208, 368, 272, 368, v.C, v2),                  # C2
        cap(272, 368, 336, 368, v.C, v3),                  # C3
        res(336, 368, 400, 368, v.R),                      # R3: last stage, into the op-amp
        res(208, 368, 208, 448, v.R),                      # R1: shunt after C1
        res(272, 368, 272, 448, v.R),                      # R2: shunt after C2
        gnd(208, 448, 208, 464),
        gnd(272, 448, 272, 464),
        opamp(400, 384, 496, 384, g),
        wire(400, 368, 400, 320),
        res(400, 320, 496, 320, v.Rf),                     # Rf: feedback
        wire(496, 320, 496, 384),
        wire(496, 384, 512, 384),
        wire(512, 384, 512, 288),
        wire(512, 288, 144, 288),
        wire(144, 288, 144, 368),
        gnd(400, 400, 400, 448),
        out_marker(512, 384, 592, 384),
    ]
    return assemble(el, v.timestep_s, [(index_of(el, "O"), 20, 16)])
