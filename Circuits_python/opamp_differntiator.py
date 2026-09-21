import math
import sys
import warnings
from typing import NamedTuple

# Fixed values taken from the exported Falstad circuit.
# The input is a triangle wave: peak volts and frequency.
SOURCE_PEAK_V = 5.0
SOURCE_FREQ_HZ = 40.0
RAIL_V = 15.0  # op-amp element: ma="15" / mi="-15"


class DifferentiatorValues(NamedTuple):
    Rf: float                  # feedback resistor (ohm)
    C: float                   # input capacitor (farad)
    tau: float                 # time constant Rf*C (seconds)
    unity_gain_freq_hz: float  # frequency where |gain| = 1


def calculate(unity_gain_freq_hz: float, feedback_resistor_ohms: float) -> DifferentiatorValues:
    """
    Rf is taken directly as the feedback resistor supplied by the user.
    C is solved from the ideal inverting-differentiator gain magnitude:
        |Vout / Vin| = 2 * pi * f * Rf * C
    which equals 1 at the unity-gain frequency f_u, so:
        f_u = 1 / (2 * pi * Rf * C)  =>  C = 1 / (2 * pi * f_u * Rf)
    Time-domain form: Vout(t) = -(Rf * C) * d(Vin)/dt.
    """
    if unity_gain_freq_hz <= 0 or feedback_resistor_ohms <= 0:
        raise ValueError("unity-gain frequency and feedback resistor must be > 0")
    Rf = feedback_resistor_ohms
    C = 1 / (2 * math.pi * unity_gain_freq_hz * Rf)
    return DifferentiatorValues(Rf, C, Rf * C, unity_gain_freq_hz)


def estimate_peak_output(tau: float) -> float:
    """
    Estimate of the output peak for the fixed input: a triangle wave of peak A
    and frequency f has slope 4*A*f (volts per second), so the output is a
    square wave of amplitude tau * 4 * A * f.
    """
    return tau * 4 * SOURCE_PEAK_V * SOURCE_FREQ_HZ


def generate_netlist(v: DifferentiatorValues) -> str:
    """
    Everything except r="..." and c="..." is fixed layout / display state,
    copied from the exported Falstad differentiator.

    Topology: source -> C -> (-) input node; Rf from the output back to the (-)
    input node; (+) input to ground. The op-amp uses the low-gain setting
    (f="4", ga="1000"), exactly as in the export. The capacitor's stored
    voltage is reset to vd="0" so the simulation starts clean.
    """
    peak_out = estimate_peak_output(v.tau)
    if peak_out > RAIL_V:
        warnings.warn(
            f"Estimated output peak {peak_out:.3g} V exceeds the +/-{RAIL_V:g} V "
            f"op-amp rails, so the output will probably clip. Use a higher "
            f"unity-gain frequency (or a smaller Rf).",
            stacklevel=2,
        )

    return f"""<cir f="1" ts="0.000005" ic="10.20027730826997" cb="57" pb="50" vr="5" mts="5e-11">
  <v x="112 256 112 96" f="0" wf="3" fr="40" maxv="5"/>
  <g x="112 256 112 304" f="0"/>
  <w x="352 128 352 192" f="0"/>
  <w x="208 128 208 176" f="0"/>
  <w x="112 256 208 256" f="0"/>
  <w x="208 208 208 256" f="0"/>
  <a x="208 192 352 192" f="4" ma="15" mi="-15" ga="1000"/>
  <c x="112 96 208 96" f="0" c="{v.C:.10g}" iv="0.001" sr="0" vd="0"/>
  <r x="208 128 352 128" f="0" r="{v.Rf:.12g}"/>
  <w x="208 96 208 128" f="0"/>
  <O x="352 192 416 192" f="0" sc="0"/>
  <o en="0" sp="32" f="x2" p="0">
    <p v="0" sc="10"/>
    <p v="3" sc="0.0125"/>
  </o>
  <o en="10" sp="32" f="x2" p="0">
    <p v="0" sc="20"/>
  </o>
</cir>
"""


def generate_differentiator_file(unity_gain_freq_hz: float, feedback_resistor_ohms: float):
    """
    Main entry point: computes C and builds the Falstad text.
    Returns (DifferentiatorValues, netlist_text).
    """
    values = calculate(unity_gain_freq_hz, feedback_resistor_ohms)
    netlist = generate_netlist(values)
    return values, netlist


def main():
    if len(sys.argv) >= 3:
        # Command-line mode: python opamp_differentiator_falstad.py <f_unity> <Rf>
        f_unity = float(sys.argv[1])
        rf = float(sys.argv[2])
    else:
        # No arguments given (e.g. run from an IDE / double-click): ask instead.
        print("Enter the differentiator values:")
        f_unity = float(input("  Unity-gain frequency (Hz): "))
        rf = float(input("  Feedback resistor Rf (ohm): "))

    values, netlist = generate_differentiator_file(f_unity, rf)

    print(f"\nRf   = {values.Rf} ohm")
    print(f"C    = {values.C} F")
    print(f"Rf*C = {values.tau} s")
    print(f"Unity-gain frequency = {values.unity_gain_freq_hz} Hz")
    print()
    print(netlist)


if __name__ == "__main__":
    main()