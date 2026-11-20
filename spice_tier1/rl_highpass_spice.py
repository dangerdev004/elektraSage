"""
rl_highpass_spice.py  -  SPICE / ngspice netlist for: RL high-pass: series R, shunt L, output across L.

Run:  python rl_highpass_spice.py                (asks for the values)
      python rl_highpass_spice.py <values...>    (values in the order of the function arguments)
Save: python rl_highpass_spice.py <values...> > rl_highpass.cir
Needs spice_common.py in the same folder.
"""
import math
from spice_common import (_n, _pick, _pos, _sine, _title, _tran, run_cli)


def rl_highpass(cutoff_hz: float = 1000.0, r_ohms: float = 1000.0, vin_peak: float = 1.0,
                analysis: str = "ac") -> str:
    """
    RL high-pass: series R, shunt L, output across L.
        fc = R / (2 pi L)   =>   L = R / (2 pi fc)
    """
    _pos(cutoff_hz=cutoff_hz, r_ohms=r_ohms, vin_peak=vin_peak)
    ind = r_ohms / (2 * math.pi * cutoff_hz)
    sim = _pick(analysis, {
        "ac": f".ac dec 20 {_n(cutoff_hz / 100)} {_n(cutoff_hz * 100)}",
        "tran": _tran(1.0 / cutoff_hz, 5),
    }, "rl_highpass")
    return "\n".join([
        _title(f"RL high-pass filter, fc = {_n(cutoff_hz)} Hz (R = {_n(r_ohms)}, L = {_n(ind)})"),
        f"Vin in 0 {_sine(vin_peak, cutoff_hz)}",
        f"R1 in out {_n(r_ohms)}",
        f"L1 out 0 {_n(ind)}",
        sim,
        ".end",
    ]) + "\n"


def main():
    run_cli(rl_highpass)


if __name__ == "__main__":
    main()
