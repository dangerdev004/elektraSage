import math
import sys
import warnings
from typing import NamedTuple

# Fixed values taken from the exported Falstad circuit.
# The input signal is two square-wave sources in series: (peak volts, Hz).
SOURCES = ((5.0, 40.0), (2.0, 80.0))
RAIL_V = 15.0  # op-amp element: ma="15" / mi="-15"


class IntegratorValues(NamedTuple):
    R: float                  # input resistor (ohm)
    C: float                  # feedback capacitor (farad)
    tau: float                # time constant R*C (seconds)
    unity_gain_freq_hz: float # frequency where |gain| = 1


def calculate(unity_gain_freq_hz: float, input_resistor_ohms: float) -> IntegratorValues:
    """
    R is taken directly as the input resistor supplied by the user.
    C is solved from the ideal inverting-integrator gain magnitude:
        |Vout / Vin| = 1 / (2 * pi * f * R * C)
    which equals 1 at the unity-gain frequency f_u, so:
        f_u = 1 / (2 * pi * R * C)  =>  C = 1 / (2 * pi * f_u * R)
    Time-domain form: Vout(t) = -(1 / (R*C)) * integral of Vin dt.
    """
    if unity_gain_freq_hz <= 0 or input_resistor_ohms <= 0:
        raise ValueError("unity-gain frequency and input resistor must be > 0")
    R = input_resistor_ohms
    C = 1 / (2 * math.pi * unity_gain_freq_hz * R)
    return IntegratorValues(R, C, R * C, unity_gain_freq_hz)


def estimate_peak_output(tau: float) -> float:
    """
    Worst-case estimate of the output peak for the fixed input: a square wave
    of amplitude A and frequency f integrates to a triangle of peak A/(4*f*tau).
    The two sources are summed, so their peaks are added (an upper bound).
    """
    return sum(a / (4 * f * tau) for a, f in SOURCES)


def generate_netlist(v: IntegratorValues) -> str:
    """
    Everything except r="..." and c="..." is fixed layout / display state,
    copied from the exported Falstad integrator.

    Topology: source -> R -> (-) input node; C from the output back to the (-)
    input node; (+) input to ground. The capacitor's stored voltage is reset
    to vd="0" so the simulation starts clean.
    """
    peak_out = estimate_peak_output(v.tau)
    if peak_out > RAIL_V:
        warnings.warn(
            f"Estimated output peak {peak_out:.3g} V exceeds the +/-{RAIL_V:g} V "
            f"op-amp rails, so the output will probably clip. Use a lower "
            f"unity-gain frequency (or a larger R).",
            stacklevel=2,
        )

    return f"""<cir f="1" ts="0.000005" ic="10.20027730826997" cb="57" pb="50" vr="5" mts="5e-11">
  <g x="96 224 96 272" f="0"/>
  <w x="336 112 336 160" f="0"/>
  <w x="192 80 192 112" f="0"/>
  <w x="192 112 192 144" f="0"/>
  <w x="192 176 192 224" f="0"/>
  <a x="192 160 336 160" f="0" ma="15" mi="-15" ga="100000"/>
  <c x="192 112 336 112" f="0" c="{v.C:.10g}" iv="0.001" sr="0" vd="0"/>
  <O x="336 160 400 160" f="0" sc="0"/>
  <v x="96 224 96 144" f="0" wf="2" fr="40" maxv="5" phaseShift="3.141592653589793"/>
  <v x="96 144 96 80" f="0" wf="2" fr="80" maxv="2"/>
  <p x="128 224 128 80" f="0" me="0" sc="0" re="0"/>
  <w x="96 224 128 224" f="0"/>
  <w x="128 224 192 224" f="0"/>
  <w x="96 80 128 80" f="0"/>
  <r x="128 80 192 80" f="0" r="{v.R:.12g}"/>
  <o en="10" sp="32" f="x2" p="0" x="input">
    <p v="0" sc="10"/>
  </o>
  <o en="7" sp="32" f="x2" p="1" x="integral">
    <p v="0" sc="11"/>
  </o>
</cir>
"""


def generate_integrator_file(unity_gain_freq_hz: float, input_resistor_ohms: float):
    """
    Main entry point: computes C and builds the Falstad text.
    Returns (IntegratorValues, netlist_text).
    """
    values = calculate(unity_gain_freq_hz, input_resistor_ohms)
    netlist = generate_netlist(values)
    return values, netlist


def main():
    if len(sys.argv) >= 3:
        # Command-line mode: python opamp_integrator_falstad.py <f_unity> <R>
        f_unity = float(sys.argv[1])
        r_in = float(sys.argv[2])
    else:
        # No arguments given (e.g. run from an IDE / double-click): ask instead.
        print("Enter the integrator values:")
        f_unity = float(input("  Unity-gain frequency (Hz): "))
        r_in = float(input("  Input resistor R (ohm): "))

    values, netlist = generate_integrator_file(f_unity, r_in)

    print(f"\nR   = {values.R} ohm")
    print(f"C   = {values.C} F")
    print(f"R*C = {values.tau} s")
    print(f"Unity-gain frequency = {values.unity_gain_freq_hz} Hz")
    print()
    print(netlist)


if __name__ == "__main__":
    main()
    