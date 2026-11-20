"""
cmos_inverter_spice.py  -  SPICE / ngspice netlist for: CMOS inverter: PMOS from Vdd to the output, NMOS from the output to ground, gates tied

Run:  python cmos_inverter_spice.py                (asks for the values)
      python cmos_inverter_spice.py <values...>    (values in the order of the function arguments)
Save: python cmos_inverter_spice.py <values...> > cmos_inverter.cir
Needs spice_common.py in the same folder.
"""
from spice_common import (_n, _pick, _pos, _title, run_cli)


def cmos_inverter(vdd: float = 5.0, vtn: float = 0.7, kp_n: float = 120e-6, kp_p: float = 40e-6,
                  wn_over_l: float = 10.0, load_c_f: float = 100e-15, analysis: str = "dc") -> str:
    """
    CMOS inverter: PMOS from Vdd to the output, NMOS from the output to ground, gates tied
    together (level-1 MOSFET models). The PMOS is sized so the switching threshold sits at
    Vdd/2:
        Vm = (Vtn + r (Vdd - |Vtp|)) / (1 + r),   r = sqrt(kp_p (W/L)p / (kp_n (W/L)n))
        r = 1  =>  (W/L)p = (W/L)n * kp_n / kp_p
    |Vtp| is taken equal to Vtn. analysis="dc" sweeps Vin 0 -> Vdd (the transfer curve),
    "tran" applies a 1 MHz pulse into a load capacitor.
    """
    _pos(vdd=vdd, vtn=vtn, kp_n=kp_n, kp_p=kp_p, wn_over_l=wn_over_l, load_c_f=load_c_f)
    if vdd <= 2 * vtn:
        raise ValueError("Vdd must be above 2 x Vt for the inverter to switch cleanly")
    wp_over_l = wn_over_l * kp_n / kp_p
    um = 1e-6
    sim = _pick(analysis, {
        "dc": f".dc Vin 0 {_n(vdd)} {_n(vdd / 500)}",
        "tran": ".tran 1n 3u",
        "op": ".op",
    }, "cmos_inverter")
    return "\n".join([
        _title(f"CMOS inverter, Vdd = {_n(vdd)} V, (W/L)n = {_n(wn_over_l)}, (W/L)p = {_n(wp_over_l)}"),
        f".model nmos1 nmos(level=1 vto={_n(vtn)} kp={_n(kp_n)} lambda=0.02)",
        f".model pmos1 pmos(level=1 vto={_n(-vtn)} kp={_n(kp_p)} lambda=0.02)",
        f"Vdd vdd 0 {_n(vdd)}",
        f"Vin in 0 PULSE(0 {_n(vdd)} 0.5u 10n 10n 0.5u 1u)",
        f"Mp out in vdd vdd pmos1 W={_n(wp_over_l * um)} L={_n(um)}",
        f"Mn out in 0 0 nmos1 W={_n(wn_over_l * um)} L={_n(um)}",
        f"CL out 0 {_n(load_c_f)}",
        sim,
        ".end",
    ]) + "\n"


def main():
    run_cli(cmos_inverter)


if __name__ == "__main__":
    main()
