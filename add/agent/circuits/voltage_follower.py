"""Generate a Falstad (CircuitJS) voltage follower (unity-gain buffer) netlist."""

from .non_inverting_amp import (
    DEFAULT_AMPLITUDE,
    DEFAULT_FREQUENCY,
    DEFAULT_GBW,
    DEFAULT_SUPPLY,
    non_inverting_amp,
)


def voltage_follower(
    amp_supply: float = DEFAULT_SUPPLY,
    input_amplitude: float = DEFAULT_AMPLITUDE,
    input_frequency: float = DEFAULT_FREQUENCY,
    gbw: float = DEFAULT_GBW,
) -> str:
    """Generate a Falstad-format voltage follower (unity-gain buffer).

    The output of the op amp is wired straight back to its inverting input, so
    the output follows the input with a gain of exactly 1. The input draws
    almost no current and the output is low impedance, which is why a follower
    is used between two stages that would otherwise load each other.

    This reuses the follower that non_inverting_amp generates at gain 1, so the
    netlist is the same tested one.

    Args:
        amp_supply: Op-amp output limit in volts, applied as +/- amp_supply.
        input_amplitude: Peak amplitude of the input source in volts.
        input_frequency: Frequency of the input source in hertz.
        gbw: Op-amp gain-bandwidth product in hertz.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If any argument is not a finite number > 0.
    """
    return non_inverting_amp(
        1.0,
        amp_supply=amp_supply,
        input_amplitude=input_amplitude,
        input_frequency=input_frequency,
        gbw=gbw,
    )
