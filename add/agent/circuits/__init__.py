"""
Registry of all available circuit-generation tools.

Add a new circuit by:
  1. Writing `circuits/<name>.py` with a single public function,
     type-hinted args, and a Google-style docstring (Args/Returns).
  2. Importing it below and adding it to CIRCUIT_TOOLS.

The registry is the single source of truth the agent uses to know
which tools exist — nothing else needs to change to add a circuit.
"""

from .inverting_amp import inverting_amp
from .non_inverting_amp import non_inverting_amp
from .rc_lowpass import rc_lowpass
from .rc_highpass import rc_highpass
from .rc_phaseshift import rc_phaseshift
from .binary_counter import binary_counter
from .rl_highpass import rl_highpass
from .rl_lowpass import rl_lowpass
from .differentiator import differentiator
from .integrator import integrator
from .monostable_555_generator import monostable_555_generator
from .parallel_in_serial_out import piso_shift_register
from .resistors_approximation import resistors_approximation
from .capacitors_approximation import capacitors_approximation
from .serial_in_parallel_out import sipo_shift_register
from .squarewave_generator import square_wave_generator
from .astable_555_generator import astable_555_generator
from .class_b_amp import class_b_amp
from .cmos_inverter import cmos_inverter
from .linear_regulator import linear_regulator
from .full_wave_rectifier import full_wave_rectifier
from .buck_converter import buck_converter
from .boost_converter import boost_converter
from .buck_boost_converter import buck_boost_converter
from .cuk_converter import cuk_converter
from .flash_adc import flash_adc
from .summing_amplifier import summing_amplifier
from .voltage_follower import voltage_follower
from .sallen_key_lowpass import sallen_key_lowpass
from .sallen_key_highpass import sallen_key_highpass
from .butterworth_lowpass import butterworth_lowpass
from .butterworth_highpass import butterworth_highpass
from .allpass_filter import allpass_filter
from .differential_amplifier import differential_amplifier
from .twin_t_notch_filter import twin_t_notch_filter
from .common_emitter_amp import common_emitter_amp
from .emitter_follower import emitter_follower
from .common_source_amp import common_source_amp
from .mosfet_current_mirror import mosfet_current_mirror
from .schmitt_trigger import schmitt_trigger
from .r2r_dac import r2r_dac
from .binary_weighted_dac import binary_weighted_dac
from .triangle_oscillator import triangle_oscillator
from .sawtooth_oscillator import sawtooth_oscillator
from .wien_bridge_oscillator import wien_bridge_oscillator
from .phase_shift_oscillator import phase_shift_oscillator

CIRCUIT_TOOLS = [
    inverting_amp,
    non_inverting_amp,
    rc_lowpass,
    rc_phaseshift,
    binary_counter,
    rc_highpass,
    rl_highpass,
    rl_lowpass,
    differentiator,
    integrator,
    monostable_555_generator,
    piso_shift_register,
    resistors_approximation,
    capacitors_approximation,
    sipo_shift_register,
    square_wave_generator,
    summing_amplifier,
    voltage_follower,
    sallen_key_lowpass,
    sallen_key_highpass,
    butterworth_lowpass,
    butterworth_highpass,
    allpass_filter,
    differential_amplifier,
    twin_t_notch_filter,
    common_emitter_amp,
    emitter_follower,
    common_source_amp,
    mosfet_current_mirror,
    schmitt_trigger,
    r2r_dac,
    binary_weighted_dac,
    triangle_oscillator,
    sawtooth_oscillator,
    wien_bridge_oscillator,
    phase_shift_oscillator,
    astable_555_generator,
    class_b_amp,
    cmos_inverter,
    linear_regulator,
    full_wave_rectifier,
    buck_converter,
    boost_converter,
    buck_boost_converter,
    cuk_converter,
    flash_adc,
]

__all__ = ["CIRCUIT_TOOLS"] + [f.__name__ for f in CIRCUIT_TOOLS]
