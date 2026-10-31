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
from .summing_amplifier import summing_amplifier

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
]

__all__ = ["CIRCUIT_TOOLS"] + [f.__name__ for f in CIRCUIT_TOOLS]
