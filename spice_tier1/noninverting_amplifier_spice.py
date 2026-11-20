"""
noninverting_amplifier_spice.py  -  SPICE / ngspice netlist for: Non-inverting amplifier. Vout / Vin = 1 + Rf / Rg   =>   Rf = (gain - 1) * Rg

Run:  python noninverting_amplifier_spice.py                (asks for the values)
      python noninverting_amplifier_spice.py <values...>    (values in the order of the function arguments)
Save: python noninverting_amplifier_spice.py <values...> > noninverting_amplifier.cir
Needs spice_common.py in the same folder.
"""
from spice_common import (_n, _opamp_subckt, _pick, _pos, _sine, _title, _tran, _warn_clip, run_cli)


def noninverting_amplifier(gain: float = 3.0, rg_ohms: float = 1000.0, vin_peak: float = 1.0,
                           freq_hz: float = 1000.0, analysis: str = "tran") -> str:
    """
    Non-inverting amplifier. Vout / Vin = 1 + Rf / Rg   =>   Rf = (gain - 1) * Rg
    gain must be > 1 (gain 1 is the voltage follower).
    """
    if gain <= 1:
        raise ValueError("gain must be > 1 for a non-inverting amplifier (gain 1 is the voltage follower)")
    _pos(rg_ohms=rg_ohms, vin_peak=vin_peak, freq_hz=freq_hz)
    rf = (gain - 1) * rg_ohms
    _warn_clip(gain * vin_peak, "noninverting_amplifier")
    sim = _pick(analysis, {"tran": _tran(1.0 / freq_hz), "ac": ".ac dec 20 10 10meg"}, "noninverting_amplifier")
    return "\n".join([
        _title(f"Non-inverting amplifier, gain = {_n(gain)} (Rg = {_n(rg_ohms)}, Rf = {_n(rf)})"),
        _opamp_subckt(),
        f"Vin in 0 {_sine(vin_peak, freq_hz)}",
        f"Rf out n1 {_n(rf)}",
        f"Rg n1 0 {_n(rg_ohms)}",
        "XU1 in n1 out opamp",
        sim,
        ".end",
    ]) + "\n"


def main():
    run_cli(noninverting_amplifier)


if __name__ == "__main__":
    main()
