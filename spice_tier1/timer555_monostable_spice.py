"""
timer555_monostable_spice.py  -  SPICE / ngspice netlist for: 555 monostable (one-shot). Output goes high for  T = 1.1 R C   =>   C = T / (1.1 R).

Run:  python timer555_monostable_spice.py                (asks for the values)
      python timer555_monostable_spice.py <values...>    (values in the order of the function arguments)
Save: python timer555_monostable_spice.py <values...> > timer555_monostable.cir
Needs spice_common.py in the same folder.
"""
from spice_common import (_n, _ne555_subckt, _pick, _pos, _title, run_cli)


def timer555_monostable(pulse_width_s: float = 1e-3, r_ohms: float = 10000.0, vcc: float = 5.0,
                        analysis: str = "tran") -> str:
    """
    555 monostable (one-shot). Output goes high for  T = 1.1 R C   =>   C = T / (1.1 R).
    A short low pulse on TRIG starts it (trigger held high otherwise).
    """
    _pos(pulse_width_s=pulse_width_s, r_ohms=r_ohms, vcc=vcc)
    c = pulse_width_s / (1.1 * r_ohms)
    t1 = pulse_width_s * 0.2
    width = pulse_width_s * 0.02
    sim = _pick(analysis, {"tran": f".tran {_n(pulse_width_s / 500)} {_n(pulse_width_s * 3)}"}, "timer555_monostable")
    return "\n".join([
        _title(f"555 monostable, pulse width = {_n(pulse_width_s)} s (R = {_n(r_ohms)}, C = {_n(c)})"),
        _ne555_subckt(),
        f"Vcc vcc 0 {_n(vcc)}",
        f"Vtrig trig 0 PULSE({_n(vcc)} 0 {_n(t1)} {_n(width / 20)} {_n(width / 20)} {_n(width)} {_n(pulse_width_s * 10)})",
        f"R1 vcc thr {_n(r_ohms)}",
        f"C1 thr 0 {_n(c)}",
        "Rtd thr dis 0.001",
        "Cc ctrl 0 10n",
        "Vrst reset 0 " + _n(vcc),
        "X1 0 trig out reset ctrl thr dis vcc ne555",
        "Rload out 0 10k",
        ".nodeset V(x1.q)=0",
        sim,
        ".end",
    ]) + "\n"


def main():
    run_cli(timer555_monostable)


if __name__ == "__main__":
    main()
