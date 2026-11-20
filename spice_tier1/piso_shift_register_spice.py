"""
piso_shift_register_spice.py  -  SPICE / ngspice netlist for: Parallel-in, serial-out shift register. While LOAD is high the parallel word is

Run:  python piso_shift_register_spice.py                (asks for the values)
      python piso_shift_register_spice.py <values...>    (values in the order of the function arguments)
Save: python piso_shift_register_spice.py <values...> > piso_shift_register.cir
Needs spice_common.py in the same folder.
"""
from spice_common import (_check_bits, _clock, _dff_models, _n, _pick, _pos, _title, run_cli)


def piso_shift_register(bits: int = 4, clk_hz: float = 1000.0, word: str = "1011", vdd: float = 5.0,
                        analysis: str = "tran") -> str:
    """
    Parallel-in, serial-out shift register. While LOAD is high the parallel word is
    captured on the next clock edge; with LOAD low every edge shifts the word one place
    towards the serial output `sout`.
    `word` is the parallel data, written in the order it comes out: word[0] leaves first.
    Pins: p0 ... p<bits-1> are the parallel inputs (p<bits-1> leaves first,
    so word[0] is applied to p<bits-1>), sout is the serial output.
    """
    if int(bits) != bits or not 1 <= bits <= 16:
        raise ValueError("bits must be a whole number from 1 to 16")
    bits = int(bits)
    _check_bits(word, "word")
    if len(word) != bits:
        raise ValueError(f"word must have exactly {bits} bits")
    _pos(clk_hz=clk_hz, vdd=vdd)
    t = 1.0 / clk_hz
    tr = t / 200
    lines = [
        _title(f"{bits}-bit PISO shift register, clock {_n(clk_hz)} Hz, parallel word {word} (first out: {word[0]})"),
        _dff_models(vdd),
        f"Vdd vdd 0 {_n(vdd)}",
        f"Vclk clk 0 {_clock(vdd, clk_hz, t)}",
        f"Vload load 0 PWL(0 {_n(vdd)} {_n(1.25 * t)} {_n(vdd)} {_n(1.25 * t + tr)} 0)",
    ]
    for k in range(bits):
        level = vdd if word[bits - 1 - k] == "1" else 0.0
        lines.append(f"Vp{k} p{k} 0 {_n(level)}")
    for k in range(bits):
        prev = "0" if k == 0 else f"q{k - 1}"
        lines.append(f"Bd{k} d{k} 0 V=V(load)>{_n(vdd / 2)} ? V(p{k}) : V({prev})")
        lines.append(f"X{k} clk d{k} q{k} qb{k} dff")
    lines.append(f"Esout sout 0 q{bits - 1} 0 1")
    lines.append(".ic " + " ".join(f"V(x{k}.s)=0" for k in range(bits)))
    sim = _pick(analysis, {"tran": f".tran {_n(t / 400)} {_n((bits + 3.5) * t)} uic"}, "piso_shift_register")
    lines += [sim, ".end"]
    return "\n".join(lines) + "\n"


def main():
    run_cli(piso_shift_register)


if __name__ == "__main__":
    main()
