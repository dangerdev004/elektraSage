"""
differentiator_spice.py  -  SPICE / ngspice netlist for: Inverting differentiator. |Vout/Vin| = 2 pi f Rf C, which is 1 at the unity-gain

Run:  python differentiator_spice.py                (asks for the values)
      python differentiator_spice.py <values...>    (values in the order of the function arguments)
Save: python differentiator_spice.py <values...> > differentiator.cir
Needs spice_common.py in the same folder.
"""
import math
from spice_common import (_n, _opamp_subckt, _pick, _pos, _title, _tran, _triangle, _warn_clip, run_cli)


def differentiator(unity_gain_hz: float = 1000.0, rf_ohms: float = 10000.0, vin_peak: float = 1.0,
                   freq_hz: float = 500.0, analysis: str = "tran") -> str:
    """
    Inverting differentiator. |Vout/Vin| = 2 pi f Rf C, which is 1 at the unity-gain
    frequency fu:   C = 1 / (2 pi fu Rf).   Vout(t) = -Rf C dVin/dt.
    The input is a triangle wave, so the output is a square wave of amplitude
    Rf C * 4 Vpk f. The op-amp gain is lowered to 1000 (as in the Falstad export): an ideal
    differentiator with a very high-gain amplifier rings.
    """
    _pos(unity_gain_hz=unity_gain_hz, rf_ohms=rf_ohms, vin_peak=vin_peak, freq_hz=freq_hz)
    c = 1.0 / (2 * math.pi * unity_gain_hz * rf_ohms)
    _warn_clip(rf_ohms * c * 4 * vin_peak * freq_hz, "differentiator")
    sim = _pick(analysis, {"tran": _tran(1.0 / freq_hz, 4, 400), "ac": ".ac dec 20 1 1meg"}, "differentiator")
    return "\n".join([
        _title(f"Inverting differentiator, unity gain at {_n(unity_gain_hz)} Hz (Rf = {_n(rf_ohms)}, C = {_n(c)})"),
        _opamp_subckt(),
        f"Vin in 0 DC 0 AC {_n(vin_peak)} {_triangle(vin_peak, freq_hz)}",
        f"C1 in n1 {_n(c)}",
        f"Rf n1 out {_n(rf_ohms)}",
        "XU1 0 n1 out opamp gain=1000",
        sim,
        ".end",
    ]) + "\n"


def main():
    run_cli(differentiator)


if __name__ == "__main__":
    main()
