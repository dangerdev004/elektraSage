"""
Shared helpers for the Tier 1 SPICE netlist scripts (issue #18).

Every circuit script in this folder imports from here. It holds:
  * the number / title / analysis helpers,
  * the behavioural models written into the netlist text: OPAMP (gain 1e5, +/-15 V),
    NE555 timer, and DFF (master-slave D flip-flop from switches, no XSPICE needed),
  * run_cli(): the "type values or press Enter for the default" front end used by
    each script's main().
Keep this file in the same folder as the circuit scripts.
"""
import ast
import inspect
import math
import sys
import warnings

OPAMP_RAIL_V = 15.0
OPAMP_GAIN = 1e5

def _n(x: float) -> str:
    """Number text for a netlist."""
    return f"{x:.10g}"


def _pos(**kw):
    for name, value in kw.items():
        if value is None or value <= 0:
            raise ValueError(f"{name} must be > 0")


def _title(text: str) -> str:
    return "* " + text


def _pick(analysis: str, options: dict, circuit: str) -> str:
    """Return the simulation command: a built-in one by name, or the caller's own."""
    if analysis.strip().startswith("."):
        return analysis.strip()
    if analysis not in options:
        raise ValueError(f"{circuit}: analysis must be one of {sorted(options)} or a text starting with '.'")
    return options[analysis]


def _tran(period_s: float, cycles: float = 4, points: int = 200, uic: bool = False) -> str:
    return f".tran {_n(period_s / points)} {_n(period_s * cycles)}" + (" uic" if uic else "")


def _opamp_subckt() -> str:
    return (
        ".subckt opamp inp inn out params: gain=%s vmax=%s\n"
        "Bout out 0 V={vmax}*tanh({gain}*(V(inp)-V(inn))/{vmax})\n"
        "Rd inp inn 1e12\n"
        ".ends opamp" % (_n(OPAMP_GAIN), _n(OPAMP_RAIL_V))
    )


def _warn_clip(peak_out: float, circuit: str):
    if peak_out > OPAMP_RAIL_V:
        warnings.warn(
            f"{circuit}: expected output peak {peak_out:g} V is beyond the +/-{OPAMP_RAIL_V:g} V "
            f"op-amp limits, so the output will clip.",
            stacklevel=3,
        )


def _sine(vpk: float, f: float) -> str:
    return f"DC 0 AC {_n(vpk)} SIN(0 {_n(vpk)} {_n(f)})"


def _square(vpk: float, f: float) -> str:
    """Symmetric square wave between -vpk and +vpk, 50 % duty, 0.1 % edges."""
    t = 1.0 / f
    return f"PULSE({_n(-vpk)} {_n(vpk)} 0 {_n(t / 1000)} {_n(t / 1000)} {_n(t / 2 - t / 1000)} {_n(t)})"


def _triangle(vpk: float, f: float) -> str:
    t = 1.0 / f
    return f"PULSE({_n(-vpk)} {_n(vpk)} 0 {_n(t / 2)} {_n(t / 2)} 0 {_n(t)})"


def _ne555_subckt() -> str:
    """Behavioural 555: divider, two comparators, a set/reset latch (the state is the voltage on a capacitor, charged to Vcc by SET and to 0 by RESET),
    a discharge switch and an output stage. Pins: gnd trig out reset ctrl thr dis vcc."""
    return "\n".join([
        ".model s555 sw(vt=0.5 vh=0.1 ron=10 roff=1e12)",
        ".subckt ne555 gnd trig out reset ctrl thr dis vcc",
        "R1 vcc ctrl 5k",
        "R2 ctrl nd 5k",
        "R3 nd gnd 5k",
        "Bset set gnd V=0.5*(1+tanh(60*(V(nd,gnd)-V(trig,gnd))))",
        "Brst rst gnd V=max(0.5*(1+tanh(60*(V(thr,gnd)-V(ctrl,gnd)))),0.5*(1-tanh(60*(V(reset,gnd)-0.7))))",
        "Cq q gnd 1n",
        "Rq q gnd 1e11",
        "Bq gnd q I=0.1*(V(set,gnd)*(V(vcc,gnd)-V(q,gnd))-V(rst,gnd)*V(q,gnd))+0.02*(0.5*V(vcc,gnd)*(1+tanh(20*(V(q,gnd)-0.5*V(vcc,gnd))))-V(q,gnd))",
        "Bout oi gnd V=V(vcc,gnd)*(0.5+0.5*tanh(20*(V(q,gnd)-0.5*V(vcc,gnd))))",
        "Rout oi out 10",
        "Bqn qn gnd V=1-V(q,gnd)/V(vcc,gnd)",
        "Sdis dis gnd qn gnd s555",
        ".ends ne555",
    ])


def _dff_models(vdd: float) -> str:
    """Rising-edge D flip-flop from two switch/capacitor latches. The master follows D while
    the clock is below 0.3 Vdd, the slave follows the master while the clock is above 0.7 Vdd
    (the gap means they are never open together)."""
    return "\n".join([
        ".model swd sw(vt=0.5 vh=0.1 ron=100 roff=1e12)",
        ".subckt dff clk d q qb params: vdd=%s" % _n(vdd),
        "Bcn cn 0 V=1-(V(clk)/{vdd}-0.3)/0.4",
        "Bcs cs 0 V=(V(clk)/{vdd}-0.3)/0.4",
        "Sm d m cn 0 swd",
        "Cm m 0 1p",
        "Bmb mb 0 V={vdd}*(0.5+0.5*tanh(50*(V(m)-{vdd}/2)))",
        "Ss mb s cs 0 swd",
        "Cs s 0 1p",
        "Bq q 0 V={vdd}*(0.5+0.5*tanh(50*(V(s)-{vdd}/2)))",
        "Bqb qb 0 V={vdd}-V(q)",
        ".ends dff",
    ])


def _clock(vdd: float, f: float, first_rise_s: float = 0.0) -> str:
    t = 1.0 / f
    tr = t / 200
    return f"PULSE(0 {_n(vdd)} {_n(first_rise_s)} {_n(tr)} {_n(tr)} {_n(t / 2 - tr)} {_n(t)})"


def _pwl_bits(bits: str, period: float, first_rise: float, vdd: float) -> str:
    """Serial data: bit k is valid at the k-th rising clock edge. It changes in the middle of
    the clock's low phase (3/4 of a period after the previous rising edge)."""
    tr = period / 200
    pts = [(0.0, int(bits[0]))]
    for k in range(1, len(bits)):
        t = first_rise + (k - 1) * period + 0.75 * period
        if int(bits[k]) != int(bits[k - 1]):
            pts.append((t, int(bits[k - 1])))
            pts.append((t + tr, int(bits[k])))
    text = " ".join(f"{_n(t)} {_n(vdd * b)}" for t, b in pts)
    return f"PWL({text})"


def _check_bits(bits: str, name: str):
    if not bits or set(bits) - {"0", "1"}:
        raise ValueError(f"{name} must be a string of 0s and 1s")


def ripple_counter(bits: int = 4, clk_hz: float = 1000.0, vdd: float = 5.0, analysis: str = "tran") -> str:
    """
    Asynchronous (ripple) binary up-counter. Every flip-flop toggles (D = Q-bar) and is
    clocked by the Q-bar of the stage before it, so each stage divides the frequency by 2.
        Q0 = clk/2, Q1 = clk/4, ...   count = Q(n-1) ... Q1 Q0
    The count after k clock pulses is k mod 2**bits. All flip-flops start at 0.
    Outputs: q0 (LSB) ... q<bits-1> (MSB).
    """
    if int(bits) != bits or not 1 <= bits <= 16:
        raise ValueError("bits must be a whole number from 1 to 16")
    bits = int(bits)
    _pos(clk_hz=clk_hz, vdd=vdd)
    lines = [
        _title(f"{bits}-bit ripple counter (toggle flip-flops), clock {_n(clk_hz)} Hz, Vdd = {_n(vdd)} V"),
        _dff_models(vdd),
        f"Vdd vdd 0 {_n(vdd)}",
        f"Vclk clk 0 {_clock(vdd, clk_hz, 1.0 / clk_hz)}",
    ]
    for k in range(bits):
        clk = "clk" if k == 0 else f"qb{k - 1}"
        lines.append(f"X{k} {clk} qb{k} q{k} qb{k} dff")
    lines.append(".ic " + " ".join(f"V(x{k}.s)=0 V(x{k}.m)=0" for k in range(bits)))
    sim = _pick(analysis, {"tran": f".tran {_n(1.0 / clk_hz / 400)} {_n((2 ** bits + 1.5) / clk_hz)} uic"}, "ripple_counter")
    lines += [sim, ".end"]
    return "\n".join(lines) + "\n"


def _parse(text: str):
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text


def run_cli(fn):
    """
    Front end for one circuit function.
      python <script>.py                 asks for every value (Enter = default)
      python <script>.py 5 2200          values in the order of the function's parameters
    Prints the netlist; redirect it to a file:  python <script>.py 5 2200 > amp.cir
    """
    params = list(inspect.signature(fn).parameters.values())
    if len(sys.argv) > 1:
        args = [_parse(a) for a in sys.argv[1:]]
    else:
        print(f"{fn.__name__}: enter the values (press Enter to keep the default)")
        args = []
        for p in params:
            text = input(f"  {p.name} [{p.default}]: ").strip()
            if text == "":
                args.append(p.default)
            else:
                args.append(_parse(text))
    print()
    print(fn(*args))

