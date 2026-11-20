"""
ripple_counter_4bit_spice.py  -  SPICE / ngspice netlist for: 4-bit ripple counter (see ripple_counter).

Run:  python ripple_counter_4bit_spice.py                (asks for the values)
      python ripple_counter_4bit_spice.py <values...>    (values in the order of the function arguments)
Save: python ripple_counter_4bit_spice.py <values...> > ripple_counter_4bit.cir
Needs spice_common.py in the same folder.
"""
from spice_common import (ripple_counter, run_cli)


def ripple_counter_4bit(clk_hz: float = 1000.0, vdd: float = 5.0, analysis: str = "tran") -> str:
    """4-bit ripple counter (see ripple_counter)."""
    return ripple_counter(4, clk_hz, vdd, analysis)


def main():
    run_cli(ripple_counter_4bit)


if __name__ == "__main__":
    main()
