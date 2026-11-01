"""Generate a Falstad (CircuitJS) buck-boost (inverting) DC-DC converter netlist."""

from ._converters import build, converter_warnings, design


def buck_boost_converter(
    input_voltage: float = 12.0,
    output_voltage: float = 5.0,
    load_current: float = 0.5,
    switching_frequency: float = 50000.0,
    ripple_current_fraction: float = 0.3,
    output_ripple_fraction: float = 0.01,
) -> str:
    """Generate a Falstad-format buck-boost (inverting) converter, designed from the specification and started at its
    expected steady state.

    Inverting: the output is negative, with magnitude input x D / (1 - D) (less the diode drop), which can be above or below the input.

    The switch is an N-channel MOSFET driven by a floating square source (0 to 10 V, duty cycle chosen so the
    output meets the target allowing for the diode's 0.7 V drop); the diode is Falstad's default. The inductor
    is sized for the ripple current, the output capacitor for the output ripple. The load is a resistor of
    output_voltage / load_current.

    Args:
        input_voltage: Supply voltage in volts.
        output_voltage: Target output voltage magnitude in volts, produced as a negative voltage.
        load_current: Load current in amps.
        switching_frequency: Switching frequency in hertz.
        ripple_current_fraction: Peak-to-peak inductor ripple current as a fraction of its average current.
        output_ripple_fraction: Peak-to-peak output ripple as a fraction of the output voltage.

    Returns:
        The Falstad circuit text, ready to load into circuitjs1.

    Raises:
        ValueError: If an argument is not a finite number > 0, or the voltages do not suit this topology.

    Warns:
        DesignWarning: If the duty cycle is extreme or the inductor is very small.
    """
    cv = design("buck_boost", input_voltage, output_voltage, load_current, switching_frequency,
                ripple_current_fraction, output_ripple_fraction)
    converter_warnings(cv)
    return build(cv)
