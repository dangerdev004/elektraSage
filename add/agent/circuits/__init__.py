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
from .rc_lowpass_xml import rc_lowpass
from .rc_phaseshift import rc_phaseshift
from .binary_counter import binary_counter

CIRCUIT_TOOLS = [
    inverting_amp,
    non_inverting_amp,
    rc_lowpass,
    rc_phaseshift,
    binary_counter,
]

__all__ = ["CIRCUIT_TOOLS"] + [f.__name__ for f in CIRCUIT_TOOLS]
