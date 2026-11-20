"""
timer555_astable_spice.py  -  SPICE / ngspice netlist for: 555 astable (square-wave) oscillator.

Run:  python timer555_astable_spice.py                (asks for the values)
      python timer555_astable_spice.py <values...>    (values in the order of the function arguments)
Save: python timer555_astable_spice.py <values...> > timer555_astable.cir
Needs spice_common.py in the same folder.
"""
from spice_common import (_n, _ne555_subckt, _pick, _pos, _title, _tran, run_cli)


def timer555_astable(freq_hz: float = 1000.0, ra_ohms: float = 1000.0, rb_ohms: float = 10000.0,
                     vcc: float = 5.0, analysis: str = "tran") -> str:
    """
    555 astable (square-wave) oscillator.
        f = 1.44 / ((Ra + 2 Rb) C)   =>   C = 1.44 / (f (Ra + 2 Rb))
        duty = (Ra + Rb) / (Ra + 2 Rb)   (result of Ra, Rb; always above 50 %)
    Ra and Rb are chosen by you, C is solved. Trigger and threshold are tied together
    and the capacitor swings between Vcc/3 and 2Vcc/3.
    """
    _pos(freq_hz=freq_hz, rb_ohms=rb_ohms, vcc=vcc)
    if ra_ohms < 0:
        raise ValueError("Ra must be >= 0")
    c = 1.44 / (freq_hz * (ra_ohms + 2 * rb_ohms))
    duty = (ra_ohms + rb_ohms) / (ra_ohms + 2 * rb_ohms)
    sim = _pick(analysis, {"tran": _tran(1.0 / freq_hz, 10, 400)}, "timer555_astable")
    return "\n".join([
        _title(f"555 astable, f = {_n(freq_hz)} Hz, duty = {duty:.1%} "
               f"(Ra = {_n(ra_ohms)}, Rb = {_n(rb_ohms)}, C = {_n(c)})"),
        _ne555_subckt(),
        f"Vcc vcc 0 {_n(vcc)}",
        f"Ra vcc dis {_n(max(ra_ohms, 1e-3))}",
        f"Rb dis thr {_n(rb_ohms)}",
        f"C1 thr 0 {_n(c)}",
        "Cc ctrl 0 10n",
        "Vrst reset 0 " + _n(vcc),
        "Rtt thr trig 0.001",
        "X1 0 trig out reset ctrl thr dis vcc ne555",
        "Rload out 0 10k",
        ".nodeset V(x1.q)=0",
        sim,
        ".end",
    ]) + "\n"


def main():
    run_cli(timer555_astable)


if __name__ == "__main__":
    main()
