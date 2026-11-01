"""Generate a Falstad (CircuitJS) Wien bridge oscillator netlist."""

import math
import warnings
from typing import NamedTuple

from ._parts import (DesignWarning, assemble, cap, diode, gnd, index_of, lamp, opamp, out_marker,
                     res, wire)

# Fixed by the exported Falstad circuit.
OPAMP_RAIL_V = 15.0             # op-amp output limits (+/-15 V): they cap the amplitude
OPAMP_GAIN = 1e5

DEFAULT_C_F = 1e-6              # the exported capacitors (both the same)
DEFAULT_R_OHM = 1000.0          # the exported resistors (both the same)
DEFAULT_RF_OHM = 100.0          # the exported fixed feedback resistor
DEFAULT_TIMESTEP_S = 5e-6       # the exported simulation timestep
STEPS_PER_PERIOD = 400          # minimum simulation steps per oscillation period
KICK_V = 0.001                  # start-up kick on both capacitors (an ideal circuit at 0 V never starts)

# The bulb is the exported one: 6 V, 0.5 W. These constants copy Falstad's lamp model
# (LampElm): resistance as a function of filament temperature, and heat balance.
LAMP_NOM_POWER_W = 0.5
LAMP_NOM_VOLTAGE_V = 6.0
LAMP_ROOM_K = 300.0
LAMP_MAX_K = 5390.0                                   # Falstad's formula stops here
LAMP_NOM_R = LAMP_NOM_VOLTAGE_V ** 2 / LAMP_NOM_POWER_W      # 72 ohm
LAMP_COOLING = 2600.0 / LAMP_NOM_POWER_W              # steady state: P = (T - 300) / 5200
DEFAULT_THERMAL_S = 0.04        # the exported warm-up and cool-down time
THERMAL_PERIODS = 5.0           # bulb time constant should be at least this many oscillation periods


def lamp_resistance(temp_k: float) -> float:
    """Filament resistance (ohm) at temperature temp_k, as Falstad computes it."""
    t = min(temp_k, LAMP_MAX_K)
    return LAMP_NOM_R * (1.26104 - 4.90662 * math.sqrt(17.1839 / t - 0.00318794) - 7.8569 / (t - 187.56))


def lamp_power_for_temp(temp_k: float) -> float:
    """Electrical power (W) that holds the filament at temp_k (heat in = heat lost)."""
    return (temp_k - LAMP_ROOM_K) / LAMP_COOLING


def lamp_temp_for_resistance(r_ohm: float) -> float:
    """Filament temperature (K) at which the bulb has resistance r_ohm (bisection)."""
    lo, hi = LAMP_ROOM_K, LAMP_MAX_K
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if lamp_resistance(mid) < r_ohm:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


LAMP_COLD_OHM = lamp_resistance(LAMP_ROOM_K)            # about 3.6 ohm
LAMP_HOT_OHM = lamp_resistance(LAMP_MAX_K)              # about 78 ohm: the most the bulb can ever reach


def _amplitude_for_lamp_ohm(r_lamp: float) -> float:
    """Peak output volts once the bulb has settled at r_lamp (gain 3 => Rf = 2 r_lamp)."""
    p = lamp_power_for_temp(lamp_temp_for_resistance(r_lamp))
    return 3.0 * math.sqrt(2.0 * p * r_lamp)


class WienValues(NamedTuple):
    R: float               # both resistors of the RC network (ohm)
    C: float               # both capacitors (F)
    Rf: float              # fixed feedback resistor above the bulb (ohm)
    f_hz: float            # 1 / (2 pi R C)
    lamp_ohm: float        # bulb resistance once settled: Rf / 2, so the gain is exactly 3
    lamp_cold_ohm: float   # bulb resistance when cold (start-up gain is 1 + Rf / this)
    lamp_temp_k: float     # settled filament temperature
    lamp_power_w: float    # settled bulb power
    amplitude_v: float     # estimated settled output amplitude, peak (V)
    thermal_s: float       # bulb warm-up and cool-down time used (s)
    settle_s: float        # rough time for the amplitude to settle (s)
    timestep_s: float


def calculate(
    f_hz: float = None,
    c_f: float = DEFAULT_C_F,
    r_ohms: float = None,
    rf_ohms: float = None,
    amplitude_v: float = None,
    thermal_s: float = None,
) -> WienValues:
    """
    Wien bridge oscillator: a non-inverting op-amp amplifier plus a Wien network
    (series R-C from the output to the + input, parallel R-C from the + input to ground).
    With equal R and equal C the network passes exactly 1/3 of the output, in phase,
    at

        f = 1 / (2 pi R C)

    so the oscillation holds when the amplifier gain is exactly 3. The gain is set by the
    feedback resistor Rf and a light bulb to ground:  gain = 1 + Rf / R_bulb.  The bulb is
    the amplitude control: it heats as the amplitude grows, its resistance rises, the gain
    falls, and the amplitude settles where R_bulb = Rf / 2 (gain 3). So the frequency comes
    from R and C, and the amplitude comes from Rf (the bulb itself is the exported 6 V, 0.5 W one).

    Give EITHER f_hz (R is then calculated: R = 1 / (2 pi f C)) OR r_ohms. With neither,
    R = 1 kohm as in the export.
    Give EITHER rf_ohms OR amplitude_v (the wanted settled peak output voltage, Rf is then
    solved for). With neither, Rf = 100 ohm as in the export (about 11.4 V peak).

    thermal_s is the bulb's warm-up and cool-down time. The bulb's resistance ripples at twice
    the oscillation frequency; that ripple distorts the waveform unless the bulb is slow compared
    with the oscillation. By default the export's 0.04 s is used, lengthened automatically for
    low frequencies so the bulb stays at least 5 oscillation periods slow.
    """
    if f_hz is not None and r_ohms is not None:
        raise ValueError("give either the frequency OR R, not both")
    if rf_ohms is not None and amplitude_v is not None:
        raise ValueError("give either Rf OR the output amplitude, not both")
    if c_f <= 0:
        raise ValueError("C must be > 0")
    if f_hz is not None and f_hz <= 0:
        raise ValueError("frequency must be > 0")
    if r_ohms is not None and r_ohms <= 0:
        raise ValueError("R must be > 0")
    if rf_ohms is not None and rf_ohms <= 0:
        raise ValueError("Rf must be > 0")
    if thermal_s is not None and thermal_s <= 0:
        raise ValueError("bulb warm-up time must be > 0")

    if f_hz is not None:
        r = 1.0 / (2.0 * math.pi * f_hz * c_f)
    elif r_ohms is not None:
        r = r_ohms
    else:
        r = DEFAULT_R_OHM
    f = 1.0 / (2.0 * math.pi * r * c_f)

    if amplitude_v is not None:
        if amplitude_v <= 0:
            raise ValueError("amplitude must be > 0")
        if amplitude_v >= OPAMP_RAIL_V:
            raise ValueError(
                f"amplitude {amplitude_v:g} V is not below the op-amp's +/-{OPAMP_RAIL_V:g} V limits; "
                f"the bulb cannot control an amplitude the op-amp cannot reach"
            )
        lo, hi = LAMP_COLD_OHM, LAMP_HOT_OHM        # amplitude rises with the bulb resistance
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if _amplitude_for_lamp_ohm(mid) < amplitude_v:
                lo = mid
            else:
                hi = mid
        rf = 2.0 * 0.5 * (lo + hi)
    else:
        rf = rf_ohms if rf_ohms is not None else DEFAULT_RF_OHM

    r_lamp = rf / 2.0
    if r_lamp <= LAMP_COLD_OHM:
        raise ValueError(
            f"Rf = {rf:g} ohm is too small: the cold bulb is already {LAMP_COLD_OHM:.2f} ohm, so the "
            f"gain 1 + Rf/R_bulb can never reach 3 and the oscillation can never start (Rf must exceed "
            f"{2 * LAMP_COLD_OHM:.2f} ohm)"
        )
    if r_lamp >= LAMP_HOT_OHM:
        warnings.warn(
            f"Rf = {rf:g} ohm is too large: even a white-hot bulb only reaches {LAMP_HOT_OHM:.1f} ohm "
            f"(Rf must be below {2 * LAMP_HOT_OHM:.1f} ohm), so the gain never falls to 3 and the output "
            f"will be driven into the op-amp limits as a distorted wave.",
            category=DesignWarning, stacklevel=2,
        )
        temp = LAMP_MAX_K
        power = lamp_power_for_temp(temp)
        amp = OPAMP_RAIL_V
    else:
        temp = lamp_temp_for_resistance(r_lamp)
        power = lamp_power_for_temp(temp)
        amp = _amplitude_for_lamp_ohm(r_lamp)
        if amp >= OPAMP_RAIL_V:
            warnings.warn(
                f"At Rf = {rf:g} ohm the bulb would need about {amp:.1f} V peak to settle, beyond the "
                f"op-amp's +/-{OPAMP_RAIL_V:g} V limits: the output will clip and the bulb stops "
                f"controlling the amplitude cleanly. Use a smaller Rf.",
                category=DesignWarning, stacklevel=2,
            )
        elif amp > 0.9 * OPAMP_RAIL_V:
            warnings.warn(
                f"Settled amplitude is about {amp:.1f} V peak, very close to the op-amp's "
                f"+/-{OPAMP_RAIL_V:g} V limits; the peaks may clip.",
                category=DesignWarning, stacklevel=2,
            )
    if r_lamp < 1.3 * LAMP_COLD_OHM:
        warnings.warn(
            f"Rf = {rf:g} ohm leaves almost no start-up gain (cold gain {1 + rf / LAMP_COLD_OHM:.2f}, "
            f"needs more than 3): the oscillation will start very slowly.",
            category=DesignWarning, stacklevel=2,
        )

    if thermal_s is None:
        thermal = max(DEFAULT_THERMAL_S, THERMAL_PERIODS / f)
    else:
        thermal = thermal_s
    ripple_ratio = 1.0 / math.sqrt(1.0 + (4.0 * math.pi * f * thermal) ** 2)   # 2f ripple left in the bulb
    if ripple_ratio > 0.05:
        warnings.warn(
            f"The bulb is too fast for {f:.4g} Hz (warm-up time {thermal:g} s): its resistance follows "
            f"the waveform and distorts it. Use a longer bulb warm-up time (at least {THERMAL_PERIODS / f:.3g} s).",
            category=DesignWarning, stacklevel=2,
        )
    if f < 1.0 or f > 50e3:
        warnings.warn(f"{f:.4g} Hz is far outside the range this circuit was tested in (5 Hz to 20 kHz).",
                      category=DesignWarning, stacklevel=2)
    if r < 100 or r > 1e6:
        warnings.warn(f"R = {r:.4g} ohm is an unusual value for this circuit.", category=DesignWarning, stacklevel=2)

    settle = 8.0 * thermal
    timestep = min(DEFAULT_TIMESTEP_S, 1.0 / (STEPS_PER_PERIOD * f))
    return WienValues(r, c_f, rf, f, r_lamp, LAMP_COLD_OHM, temp, power, amp, thermal, settle, timestep)


def wien_bridge_oscillator(
    f_hz: float = None,
    c_f: float = DEFAULT_C_F,
    r_ohms: float = None,
    rf_ohms: float = None,
    amplitude_v: float = None,
    thermal_s: float = None,
) -> str:
    """Generate a Falstad-format Wien bridge sine oscillator with a light-bulb amplitude control.

    A non-inverting op-amp amplifier plus a Wien network (series R-C from the output to the + input,
    parallel R-C from the + input to ground). With equal R and equal C the network passes 1/3 of the output,
    in phase, at f = 1 / (2 pi R C), so oscillation holds when the gain is exactly 3. The gain is
    1 + Rf / R_bulb with a 6 V, 0.5 W lamp to ground: the lamp heats as the amplitude grows, its resistance
    rises, the gain falls and the amplitude settles where R_bulb = Rf / 2. So frequency comes from R and C,
    amplitude from Rf. Give EITHER f_hz (R is solved) OR r_ohms (default 1 kohm); and EITHER rf_ohms
    (default 100 ohm, about 11 V peak) OR amplitude_v (the settled peak output; Rf is solved). The amplitude
    is an estimate from the lamp model and takes a few tenths of a second of simulated time to settle. This
    circuit generates its own signal and has no signal input, so it can only be the FIRST stage of a cascade.

    Args:
        f_hz: Oscillation frequency in hertz (alternative to r_ohms).
        c_f: Capacitance of both Wien capacitors in farads.
        r_ohms: Resistance of both Wien resistors in ohms (alternative to f_hz).
        rf_ohms: Feedback resistor above the lamp in ohms (alternative to amplitude_v).
        amplitude_v: Wanted settled peak output in volts (alternative to rf_ohms).
        thermal_s: Lamp warm-up and cool-down time in seconds (default lengthened for low frequencies).

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If both members of a pair are given, a value is out of range, or Rf is so small that
            the oscillation can never start.

    Warns:
        DesignWarning: If Rf is too large for the lamp, the amplitude is near the 15 V limits, the lamp is
            too fast for the frequency, or a value is outside the tested range.
    """
    v = calculate(f_hz, c_f, r_ohms, rf_ohms, amplitude_v, thermal_s)
    kick = KICK_V
    g = OPAMP_RAIL_V
    el = [
        lamp(160, 112, 240, 112, LAMP_ROOM_K, LAMP_NOM_POWER_W, LAMP_NOM_VOLTAGE_V, v.thermal_s, v.thermal_s),
        res(240, 112, 368, 112, v.Rf),                     # Rf: output to - input
        opamp(240, 160, 368, 160, g),
        wire(240, 112, 240, 144),
        wire(368, 112, 368, 160),
        cap(160, 176, 208, 176, v.C, kick),                # Cp: + input to ground
        res(160, 224, 208, 224, v.R),                      # Rp
        wire(208, 176, 208, 224),
        wire(160, 176, 160, 224),
        wire(160, 176, 160, 112),
        wire(240, 176, 240, 224),
        wire(240, 224, 208, 224),
        gnd(160, 224, 160, 256),
        res(240, 224, 320, 224, v.R),                      # Rs: output to + input
        cap(320, 224, 368, 224, v.C, kick),                # Cs
        wire(368, 160, 368, 224),                          # output wire
        out_marker(368, 160, 432, 160),
    ]
    # two scopes on the output: the waveform, and a slow one (about 0.5 s across) that shows the whole
    # amplitude settling, which takes several lamp time constants
    slow = max(8, 2 ** round(math.log2(max(0.5 / (900 * v.timestep_s), 1.0))))
    return assemble(el, v.timestep_s, [(index_of(el, "O"), 20, 8), (index_of(el, "O"), 20, slow)])
