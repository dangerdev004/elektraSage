"""Legacy-dialect line builders shared by the transistor, DAC and Schmitt generators.

Field layouts were checked against the CircuitJS source (sharpie7/circuitjs1):
  t   x1 y1 x2 y2 flags pnp vbe vbc beta modelName     (base = p1, collector/emitter at p2 -/+16)
  f   x1 y1 x2 y2 flags vt beta                        (gate = p1, source/drain at p2)
  160 x1 y1 x2 y2 flags r_on r_off                     (SPDT analog switch; control >= 2.5 V picks post 2)
  L   x1 y1 x2 y2 flags position momentary hi lo       (position 1 = high)
  s   x1 y1 x2 y2 flags position momentary             (position 1 = open)
  R/v x1 y1 x2 y2 flags waveform freq amp bias         (waveform 0 = DC, 1 = sine)
  181 x1 y1 x2 y2 flags temp nom_power nom_volts warm cool   (incandescent lamp)
  d   x1 y1 x2 y2 flags modelName                      (flags 2 = model name follows; anode = p1)
  165 x1 y1 x2 y2 flags out_volts                      (555 timer; pins dis tr th vin ctl out rst gnd, see dump.timer_pins)
"""

import math


class DesignWarning(UserWarning):
    """A design choice the generator made, or a limit it ran into, that the caller should know."""


def fmt(x: float) -> str:
    return repr(float(x))


def require_positive(name: str, value: float) -> None:
    if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite number > 0, got {value!r}")


def wire(x1, y1, x2, y2) -> str:
    return f"w {x1} {y1} {x2} {y2} 0"


def gnd(x1, y1, x2, y2) -> str:
    return f"g {x1} {y1} {x2} {y2} 0"


def res(x1, y1, x2, y2, ohms) -> str:
    return f"r {x1} {y1} {x2} {y2} 0 {fmt(ohms)}"


def ind(x1, y1, x2, y2, henries, amps=0.0) -> str:
    """Inductor; amps is the initial current flowing from p1 to p2."""
    return f"l {x1} {y1} {x2} {y2} 0 {fmt(henries)} {fmt(amps)}"


def cap(x1, y1, x2, y2, farads, volts=0.0) -> str:
    return f"c {x1} {y1} {x2} {y2} 0 {fmt(farads)} {fmt(volts)}"


def dc_rail(x1, y1, x2, y2, volts) -> str:
    return f"R {x1} {y1} {x2} {y2} 0 0 40.0 {fmt(volts)} 0.0"


def sine_rail(x1, y1, x2, y2, freq, amp, bias=0.0) -> str:
    return f"R {x1} {y1} {x2} {y2} 0 1 {fmt(freq)} {fmt(amp)} {fmt(bias)}"


def out_marker(x1, y1, x2, y2) -> str:
    return f"O {x1} {y1} {x2} {y2} 0"


def bjt(x1, y1, x2, y2, beta, pnp: bool = False, flip: bool = False) -> str:
    """BJT, base at p1. flip swaps the collector/emitter pin positions (the PNP of a push-pull pair needs it)."""
    return f"t {x1} {y1} {x2} {y2} {1 if flip else 0} {-1 if pnp else 1} 0.0 0.0 {fmt(beta)} default"


def mosfet(x1, y1, x2, y2, vt=1.5, beta=0.02, pchannel: bool = False, flip: bool = False) -> str:
    """MOSFET, gate at p1. Flags: 1 = P-channel, 8 = swap drain/source pin positions (a P-channel whose source
    is the top pin needs it). vt is the positive threshold magnitude for both polarities."""
    flags = (1 if pchannel else 0) | (8 if flip else 0)
    return f"f {x1} {y1} {x2} {y2} {flags} {fmt(vt)} {fmt(beta)}"


def analog_switch(x1, y1, x2, y2) -> str:
    return f"160 {x1} {y1} {x2} {y2} 0 20.0 10000000000.0"


def logic_input(x1, y1, x2, y2, high: bool, hi_volts=5.0, momentary: bool = False) -> str:
    return f"L {x1} {y1} {x2} {y2} 0 {1 if high else 0} {'true' if momentary else 'false'} {fmt(hi_volts)} 0.0"


def timer555(x1, y1, x2, y2, flags, out_volts) -> str:
    """555 timer: flags 2 = reset pin, 4 = ground pin (both set = 6); the one trailing number is the output pin's state."""
    return f"165 {x1} {y1} {x2} {y2} {flags} {fmt(out_volts)}"


def switch(x1, y1, x2, y2, closed: bool) -> str:
    return f"s {x1} {y1} {x2} {y2} 0 {0 if closed else 1} false"


def opamp(x1, y1, x2, y2, rail, flags=0, gbw=1e6, rail_low=None) -> str:
    low = -rail if rail_low is None else rail_low
    return f"a {x1} {y1} {x2} {y2} {flags} {fmt(rail)} {fmt(low)} {fmt(gbw)}"


def lamp(x1, y1, x2, y2, temp_k, nom_power_w, nom_volts, warm_s, cool_s) -> str:
    return f"181 {x1} {y1} {x2} {y2} 0 {fmt(temp_k)} {fmt(nom_power_w)} {fmt(nom_volts)} {fmt(warm_s)} {fmt(cool_s)}"


def zener(x1, y1, x2, y2, volts) -> str:
    """Zener, anode at p1, cathode at p2; 0.805904783 is Falstad's default forward-drop parameter."""
    return f"z {x1} {y1} {x2} {y2} 0 0.805904783 {fmt(volts)}"


def diode(x1, y1, x2, y2) -> str:
    return f"d {x1} {y1} {x2} {y2} 2 default"


def assemble(elements: list[str], timestep: float, scopes: list[tuple]) -> str:
    """Header, elements, then one scope line per (element index, volts per division[, steps per pixel])."""
    lines = [f"$ 1 {fmt(timestep)} 10 57 5.0", *elements]
    for sc in scopes:
        idx, scale = sc[0], sc[1]
        speed = sc[2] if len(sc) > 2 else 64
        lines.append(f"o {idx} {speed} 0 2 {fmt(scale)} 9.765625E-5")
    return "\n".join(lines) + "\n"


def index_of(elements: list[str], prefix: str) -> int:
    return next(i for i, line in enumerate(elements) if line.startswith(prefix + " "))
