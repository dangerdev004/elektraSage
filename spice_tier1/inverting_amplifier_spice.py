"""
inverting_amplifier_spice.py  -  SPICE / ngspice netlist for: Inverting amplifier. Vout / Vin = -Rf / Rin   =>   Rf = |gain| * Rin

Run:  python inverting_amplifier_spice.py                (asks for the values)
      python inverting_amplifier_spice.py <values...>    (values in the order of the function arguments)
Save: python inverting_amplifier_spice.py <values...> > inverting_amplifier.cir
Needs spice_common.py in the same folder.
"""
from spice_common import (_n, _opamp_subckt, _pick, _pos, _sine, _title, _tran, _warn_clip, run_cli)


def inverting_amplifier(gain: float = 3.0, rin_ohms: float = 1000.0, vin_peak: float = 1.0,
                        freq_hz: float = 1000.0, analysis: str = "tran") -> str:
    """
    Inverting amplifier. Vout / Vin = -Rf / Rin   =>   Rf = |gain| * Rin
    `gain` is the wanted magnitude (3 means x3, inverted).
    """
    gain = abs(gain)
    _pos(gain=gain, rin_ohms=rin_ohms, vin_peak=vin_peak, freq_hz=freq_hz)
    rf = gain * rin_ohms
    _warn_clip(gain * vin_peak, "inverting_amplifier")
    sim = _pick(analysis, {"tran": _tran(1.0 / freq_hz), "ac": ".ac dec 20 10 10meg"}, "inverting_amplifier")
    return "\n".join([
        _title(f"Inverting amplifier, gain = -{_n(gain)} (Rin = {_n(rin_ohms)}, Rf = {_n(rf)})"),
        _opamp_subckt(),
        f"Vin in 0 {_sine(vin_peak, freq_hz)}",
        f"Rin in n1 {_n(rin_ohms)}",
        f"Rf n1 out {_n(rf)}",
        "XU1 0 n1 out opamp",
        sim,
        ".end",
    ]) + "\n"


def main():
    run_cli(inverting_amplifier)


if __name__ == "__main__":
    main()
