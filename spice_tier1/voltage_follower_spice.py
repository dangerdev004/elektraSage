"""
voltage_follower_spice.py  -  SPICE / ngspice netlist for: Voltage follower (unity-gain buffer): the output is wired to the inverting input,

Run:  python voltage_follower_spice.py                (asks for the values)
      python voltage_follower_spice.py <values...>    (values in the order of the function arguments)
Save: python voltage_follower_spice.py <values...> > voltage_follower.cir
Needs spice_common.py in the same folder.
"""
from spice_common import (_n, _opamp_subckt, _pick, _pos, _sine, _title, _tran, run_cli)


def voltage_follower(rload_ohms: float = 1000.0, vin_peak: float = 1.0, freq_hz: float = 1000.0,
                     analysis: str = "tran") -> str:
    """
    Voltage follower (unity-gain buffer): the output is wired to the inverting input,
    so Vout = Vin whatever the load. Rload is only a load resistor to ground.
    """
    _pos(rload_ohms=rload_ohms, vin_peak=vin_peak, freq_hz=freq_hz)
    sim = _pick(analysis, {"tran": _tran(1.0 / freq_hz), "ac": ".ac dec 20 10 10meg"}, "voltage_follower")
    return "\n".join([
        _title(f"Voltage follower (buffer), load {_n(rload_ohms)} ohm"),
        _opamp_subckt(),
        f"Vin in 0 {_sine(vin_peak, freq_hz)}",
        "XU1 in out out opamp",
        f"Rload out 0 {_n(rload_ohms)}",
        sim,
        ".end",
    ]) + "\n"


def main():
    run_cli(voltage_follower)


if __name__ == "__main__":
    main()
