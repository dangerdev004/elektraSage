"""
rc_lowpass_spice.py  -  SPICE / ngspice netlist for: RC low-pass: series R, shunt C, output across C.

Run:  python rc_lowpass_spice.py                (asks for the values)
      python rc_lowpass_spice.py <values...>    (values in the order of the function arguments)
Save: python rc_lowpass_spice.py <values...> > rc_lowpass.cir
Needs spice_common.py in the same folder.
"""
import math
from spice_common import (_n, _pick, _pos, _sine, _title, _tran, run_cli)


def rc_lowpass(cutoff_hz: float = 1000.0, r_ohms: float = 1000.0, vin_peak: float = 1.0,
               analysis: str = "ac") -> str:
    """
    RC low-pass: series R, shunt C, output across C.
        fc = 1 / (2 pi R C)   =>   C = 1 / (2 pi fc R)
    """
    _pos(cutoff_hz=cutoff_hz, r_ohms=r_ohms, vin_peak=vin_peak)
    c = 1.0 / (2 * math.pi * cutoff_hz * r_ohms)
    sim = _pick(analysis, {
        "ac": f".ac dec 20 {_n(cutoff_hz / 100)} {_n(cutoff_hz * 100)}",
        "tran": _tran(1.0 / cutoff_hz, 5),
    }, "rc_lowpass")
    return "\n".join([
        _title(f"RC low-pass filter, fc = {_n(cutoff_hz)} Hz (R = {_n(r_ohms)}, C = {_n(c)})"),
        f"Vin in 0 {_sine(vin_peak, cutoff_hz)}",
        f"R1 in out {_n(r_ohms)}",
        f"C1 out 0 {_n(c)}",
        sim,
        ".end",
    ]) + "\n"


def main():
    run_cli(rc_lowpass)


if __name__ == "__main__":
    main()
