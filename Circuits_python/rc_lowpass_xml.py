import math


def rc_lowpass(cutoff_freq_hz: float, load_resistor_ohms: float) -> str:
    """Generate a Falstad-format (XML) single-pole RC low-pass filter.

    R is taken directly as the supplied load resistor. C is solved from
    the standard cutoff formula: fc = 1 / (2*pi*R*C) => C = 1 / (2*pi*fc*R).

    Args:
        cutoff_freq_hz: Desired cutoff frequency in Hz.
        load_resistor_ohms: Load resistor value in ohms.

    Returns:
        The Falstad circuit text (XML format), ready to load into circuitjs1.
    """
    R = load_resistor_ohms
    C = 1 / (2 * math.pi * cutoff_freq_hz * R)

    return (
        '<cir f="1" ts="0.000005" ic="6.450009306485578" cb="50" pb="50" vr="5" mts="5e-11">\n'
        '  <O x="400 160 512 160" f="0" sc="0"/>\n'
        '  <g x="400 288 400 320" f="0"/>\n'
        f'  <r x="240 160 400 160" f="0" r="{R:.0f}"/>\n'
        f'  <c x="400 160 400 288" f="0" c="{C:e}" iv="0.001" sr="0" vd="0"/>\n'
        '  <sw x="240 160 208 160" f="3" mi="20" ma="1000" mv="5" sw="0.1"/>\n'
        '  <o en="4" sp="32" f="x2" p="0">\n'
        '    <p v="0" sc="5"/>\n'
        '    <p v="3" sc="0.00009765625"/>\n'
        '  </o>\n'
        '  <o en="0" sp="32" f="x2" p="1">\n'
        '    <p v="0" sc="5"/>\n'
        '  </o>\n'
        '  <h t="3" i1="2" i2="3"/>\n'
        '</cir>\n'
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python rc_lowpass_xml.py <cutoffFrequencyHz> <loadResistorOhms>")
        raise SystemExit(1)

    cutoff = float(sys.argv[1])
    load_r = float(sys.argv[2])
    R = load_r
    C = 1 / (2 * math.pi * cutoff * R)

    netlist = rc_lowpass(cutoff, load_r)
    print(f"R = {R} ohm")
    print(f"C = {C} F")
    print("\nGenerated Netlist:\n")
    print(netlist)
