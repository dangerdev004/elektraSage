"""
rl_lowpass_spice.py  -  SPICE / ngspice netlist for: RL low-pass: series L, shunt R, output across R.

Run:  python rl_lowpass_spice.py                (asks for the values)
      python rl_lowpass_spice.py <values...>    (values in the order of the function arguments)
Save: python rl_lowpass_spice.py <values...> > rl_lowpass.cir
Needs spice_common.py in the same folder.
"""
import math
from spice_common import (_n, _pick, _pos, _sine, _title, _tran, run_cli)


def rl_lowpass(cutoff_hz: float = 1000.0, r_ohms: float = 1000.0, vin_peak: float = 1.0,
               analysis: str = "ac") -> str:
    """
    RL low-pass: series L, shunt R, output across R.
        fc = R / (2 pi L)   =>   L = R / (2 pi fc)
    """
    _pos(cutoff_hz=cutoff_hz, r_ohms=r_ohms, vin_peak=vin_peak)
    ind = r_ohms / (2 * math.pi * cutoff_hz)
    sim = _pick(analysis, {
        "ac": f".ac dec 20 {_n(cutoff_hz / 100)} {_n(cutoff_hz * 100)}",
        "tran": _tran(1.0 / cutoff_hz, 5),
    }, "rl_lowpass")
    return "\n".join([
        _title(f"RL low-pass filter, fc = {_n(cutoff_hz)} Hz (R = {_n(r_ohms)}, L = {_n(ind)})"),
        f"Vin in 0 {_sine(vin_peak, cutoff_hz)}",
        f"L1 in out {_n(ind)}",
        f"R1 out 0 {_n(r_ohms)}",
        sim,
        ".end",
    ]) + "\n"


def main():
    run_cli(rl_lowpass)


if __name__ == "__main__":
    main()
