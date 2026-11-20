"""
sipo_shift_register_spice.py  -  SPICE / ngspice netlist for: Serial-in, parallel-out shift register: a chain of D flip-flops, the first one fed with

Run:  python sipo_shift_register_spice.py                (asks for the values)
      python sipo_shift_register_spice.py <values...>    (values in the order of the function arguments)
Save: python sipo_shift_register_spice.py <values...> > sipo_shift_register.cir
Needs spice_common.py in the same folder.
"""
from spice_common import (_check_bits, _clock, _dff_models, _n, _pick, _pos, _pwl_bits, _title, run_cli)


def sipo_shift_register(bits: int = 4, clk_hz: float = 1000.0, data: str = "1011", vdd: float = 5.0,
                        analysis: str = "tran") -> str:
    """
    Serial-in, parallel-out shift register: a chain of D flip-flops, the first one fed with
    the serial data, each next one fed from the Q before it. After `bits` clock pulses the
    word is available on q0 ... q<bits-1>; q0 holds the LAST bit shifted in.
    `data` is the serial bit pattern sent in, first bit first (it is repeated if shorter than
    the simulation).
    """
    if int(bits) != bits or not 1 <= bits <= 16:
        raise ValueError("bits must be a whole number from 1 to 16")
    bits = int(bits)
    _check_bits(data, "data")
    _pos(clk_hz=clk_hz, vdd=vdd)
    t = 1.0 / clk_hz
    pulses = bits + 2
    stream = (data * (pulses // len(data) + 1))[:pulses]
    lines = [
        _title(f"{bits}-bit SIPO shift register, clock {_n(clk_hz)} Hz, serial data {data}"),
        _dff_models(vdd),
        f"Vdd vdd 0 {_n(vdd)}",
        f"Vclk clk 0 {_clock(vdd, clk_hz, t)}",
        f"Vdin din 0 {_pwl_bits(stream, t, t, vdd)}",
    ]
    for k in range(bits):
        d = "din" if k == 0 else f"q{k - 1}"
        lines.append(f"X{k} clk {d} q{k} qb{k} dff")
    lines.append(".ic " + " ".join(f"V(x{k}.s)=0" for k in range(bits)))
    sim = _pick(analysis, {"tran": f".tran {_n(t / 400)} {_n((pulses + 0.5) * t)} uic"}, "sipo_shift_register")
    lines += [sim, ".end"]
    return "\n".join(lines) + "\n"


def main():
    run_cli(sipo_shift_register)


if __name__ == "__main__":
    main()
