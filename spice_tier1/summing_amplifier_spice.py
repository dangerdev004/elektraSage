"""
summing_amplifier_spice.py  -  SPICE / ngspice netlist for: Inverting summing amplifier. Vout = -Rf (V1/R1 + V2/R2)   =>   R1 = Rf/|g1|, R2 = Rf/|g2|

Run:  python summing_amplifier_spice.py                (asks for the values)
      python summing_amplifier_spice.py <values...>    (values in the order of the function arguments)
Save: python summing_amplifier_spice.py <values...> > summing_amplifier.cir
Needs spice_common.py in the same folder.
"""
from spice_common import (_n, _opamp_subckt, _pick, _pos, _sine, _square, _title, _warn_clip, run_cli)


def summing_amplifier(gain1: float = 1.0, gain2: float = 2.0, rf_ohms: float = 10000.0,
                      v1_peak: float = 1.0, f1_hz: float = 1000.0,
                      v2_peak: float = 0.5, f2_hz: float = 100.0,
                      analysis: str = "tran") -> str:
    """
    Inverting summing amplifier. Vout = -Rf (V1/R1 + V2/R2)   =>   R1 = Rf/|g1|, R2 = Rf/|g2|
    Channel 1 is a sine, channel 2 a square wave.
    """
    gain1, gain2 = abs(gain1), abs(gain2)
    _pos(gain1=gain1, gain2=gain2, rf_ohms=rf_ohms, v1_peak=v1_peak, f1_hz=f1_hz, v2_peak=v2_peak, f2_hz=f2_hz)
    r1, r2 = rf_ohms / gain1, rf_ohms / gain2
    _warn_clip(gain1 * v1_peak + gain2 * v2_peak, "summing_amplifier")
    slow = min(f1_hz, f2_hz)
    fast = max(f1_hz, f2_hz)
    sim = _pick(analysis, {
        "tran": f".tran {_n(1.0 / fast / 200)} {_n(2.0 / slow)}",
        "ac": ".ac dec 20 10 10meg",
    }, "summing_amplifier")
    return "\n".join([
        _title(f"Inverting summing amplifier, gains -{_n(gain1)} and -{_n(gain2)} "
               f"(R1 = {_n(r1)}, R2 = {_n(r2)}, Rf = {_n(rf_ohms)})"),
        _opamp_subckt(),
        f"V1 in1 0 {_sine(v1_peak, f1_hz)}",
        f"V2 in2 0 {_square(v2_peak, f2_hz)}",
        f"R1 in1 n1 {_n(r1)}",
        f"R2 in2 n1 {_n(r2)}",
        f"Rf n1 out {_n(rf_ohms)}",
        "XU1 0 n1 out opamp",
        sim,
        ".end",
    ]) + "\n"


def main():
    run_cli(summing_amplifier)


if __name__ == "__main__":
    main()
