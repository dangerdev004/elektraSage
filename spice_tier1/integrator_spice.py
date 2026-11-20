"""
integrator_spice.py  -  SPICE / ngspice netlist for: Inverting integrator. |Vout/Vin| = 1 / (2 pi f R C), which is 1 at the unity-gain

Run:  python integrator_spice.py                (asks for the values)
      python integrator_spice.py <values...>    (values in the order of the function arguments)
Save: python integrator_spice.py <values...> > integrator.cir
Needs spice_common.py in the same folder.
"""
import math
from spice_common import (_n, _opamp_subckt, _pick, _pos, _square, _title, _tran, _warn_clip, run_cli)


def integrator(unity_gain_hz: float = 1000.0, r_ohms: float = 10000.0, vin_peak: float = 1.0,
               freq_hz: float = 1000.0, analysis: str = "tran") -> str:
    """
    Inverting integrator. |Vout/Vin| = 1 / (2 pi f R C), which is 1 at the unity-gain
    frequency fu:   C = 1 / (2 pi fu R).   Vout(t) = -(1/RC) integral(Vin dt).
    The input is a square wave, so the output is a triangle of peak Vpk / (4 f R C).
    An ideal integrator has no fixed DC level, so the capacitor is pre-charged to start the output
    at +Vpk/(4 f R C): the triangle then swings symmetrically about 0 V (uic is used).
    """
    _pos(unity_gain_hz=unity_gain_hz, r_ohms=r_ohms, vin_peak=vin_peak, freq_hz=freq_hz)
    c = 1.0 / (2 * math.pi * unity_gain_hz * r_ohms)
    _warn_clip(vin_peak / (4 * freq_hz * r_ohms * c), "integrator")
    v_start = vin_peak / (4 * freq_hz * r_ohms * c)        # input starts high, output ramps down: symmetric about 0 V
    sim = _pick(analysis, {"tran": _tran(1.0 / freq_hz, 4, 200, uic=True), "ac": ".ac dec 20 1 1meg"}, "integrator")
    return "\n".join([
        _title(f"Inverting integrator, unity gain at {_n(unity_gain_hz)} Hz (R = {_n(r_ohms)}, C = {_n(c)})"),
        _opamp_subckt(),
        f"Vin in 0 DC 0 AC {_n(vin_peak)} {_square(vin_peak, freq_hz)}",
        f"R1 in n1 {_n(r_ohms)}",
        f"C1 n1 out {_n(c)} IC={_n(-v_start)}",
        "XU1 0 n1 out opamp",
        f".ic V(out)={_n(v_start)} V(n1)=0",
        sim,
        ".end",
    ]) + "\n"


def main():
    run_cli(integrator)


if __name__ == "__main__":
    main()
