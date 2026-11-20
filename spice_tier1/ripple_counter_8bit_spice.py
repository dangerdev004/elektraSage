"""
ripple_counter_8bit_spice.py  -  SPICE / ngspice netlist for: 8-bit ripple counter (see ripple_counter). Simulates 257 clock pulses by default.

Run:  python ripple_counter_8bit_spice.py                (asks for the values)
      python ripple_counter_8bit_spice.py <values...>    (values in the order of the function arguments)
Save: python ripple_counter_8bit_spice.py <values...> > ripple_counter_8bit.cir
Needs spice_common.py in the same folder.
"""
from spice_common import (ripple_counter, run_cli)


def ripple_counter_8bit(clk_hz: float = 10000.0, vdd: float = 5.0, analysis: str = "tran") -> str:
    """8-bit ripple counter (see ripple_counter). Simulates 257 clock pulses by default."""
    return ripple_counter(8, clk_hz, vdd, analysis)


def main():
    run_cli(ripple_counter_8bit)


if __name__ == "__main__":
    main()
