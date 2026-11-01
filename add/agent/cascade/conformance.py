"""Run every registered generator and report whether it can be cascaded.

    python -m agent.cascade.conformance

Exit status 1 if any circuit that is expected to be cascadable is not.
"""

from __future__ import annotations

import sys
import warnings

from agent.circuits import CIRCUIT_TOOLS

from . import dump
from .ports import ports_for

# Representative arguments per generator (used only for this check).
SAMPLES: dict[str, dict] = {
    "inverting_amp": dict(gain=10, res=10000),
    "non_inverting_amp": dict(gain=10),
    "rc_lowpass": dict(cutoff_frequency=1000),
    "rc_highpass": dict(cutoff_frequency=1000),
    "rl_lowpass": dict(cutoff_frequency=1000),
    "rl_highpass": dict(cutoff_frequency=1000),
    "rc_phaseshift": dict(frequency_hz=1000),
    "integrator": dict(gain_v_per_v=1, input_resistor_ohms=10000),
    "differentiator": dict(gain_v_per_v=1, feedback_resistor_ohms=10000),
    "voltage_follower": dict(),
    "sallen_key_lowpass": dict(cutoff_frequency=1000),
    "sallen_key_highpass": dict(cutoff_frequency=1000),
    "butterworth_lowpass": dict(cutoff_frequency=1000),
    "butterworth_highpass": dict(cutoff_frequency=1000),
    "allpass_filter": dict(center_frequency=1000),
    "differential_amplifier": dict(gain_v_per_v=10),
    "twin_t_notch_filter": dict(notch_frequency=1000),
    "common_emitter_amp": dict(supply_voltage=12, collector_current=0.001, collector_resistor=4700,
                               emitter_resistor=1000),
    "emitter_follower": dict(supply_voltage=12, emitter_current=0.002, emitter_resistor=3000),
    "common_source_amp": dict(positive_supply=15, negative_supply=10, drain_current=0.002, gain=5),
    "mosfet_current_mirror": dict(supply_voltage=10, reference_current=0.005),
    "schmitt_trigger": dict(upper_trip_voltage=6, lower_trip_voltage=4),
    "r2r_dac": dict(),
    "binary_weighted_dac": dict(),
    "triangle_oscillator": dict(),
    "sawtooth_oscillator": dict(),
    "wien_bridge_oscillator": dict(),
    "phase_shift_oscillator": dict(),
    "summing_amplifier": dict(gain_v_per_v=1, input1_frequency_hz=1000,
                              input2_frequency_hz=100),
    "binary_counter": dict(bits=4),
    "sipo_shift_register": dict(bits=4),
    "piso_shift_register": dict(bits=4),
    "square_wave_generator": dict(),
    "monostable_555_generator": dict(),
    "astable_555_generator": dict(),
    "class_b_amp": dict(),
    "cmos_inverter": dict(),
    "linear_regulator": dict(),
    "full_wave_rectifier": dict(),
    "buck_converter": dict(),
    "boost_converter": dict(),
    "buck_boost_converter": dict(),
    "cuk_converter": dict(),
    "flash_adc": dict(),
}
HELPERS = {"resistors_approximation", "capacitors_approximation"}
# Digital circuits need a port-kind system (clock / bit / bus) that the analog
# stage model does not have; reported but not counted as failures yet.
DEFERRED = {"binary_counter", "sipo_shift_register", "piso_shift_register"}
# Bias circuits with no signal port at all: they are built on their own and cannot be chained.
STANDALONE = {"mosfet_current_mirror"}


def generate(fn, args) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = fn(**args)
    return out[0] if isinstance(out, tuple) else out


def dialect_text_differs(text: str, nl: dump.Netlist) -> bool:
    return text.strip() != nl.to_text().strip()


def check(name: str, text: str) -> list[str]:
    """Return a list of problems (empty = cascadable by inference)."""
    nl = dump.parse(text)
    problems = list(ports_for(name, nl).problems)
    again = dump.parse(nl.to_text()).to_text()
    if again != nl.to_text():
        problems.append("parse/serialise round trip not stable")
    if dialect_text_differs(text, nl):
        problems.append("info: re-serialised text differs from generator text "
                        "(formatting only; checked by re-parse equality)")
    off = [e.line() for e in nl.elements
           if any(v % dump.GRID for v in (e.x1, e.y1, e.x2, e.y2))
           and e.type not in ("O", "R", "170", "a", "x")]
    if off:
        problems.append(f"{len(off)} element(s) off the {dump.GRID}-unit grid, e.g. {off[0]!r}")
    unknown = sorted({e.type for e in nl.elements if dump.terminals(e) is None})
    if unknown:
        problems.append(f"info: pins unknown for types {unknown} (connectivity unchecked inside them)")
    return problems


def main() -> int:
    bad = 0
    for fn in CIRCUIT_TOOLS:
        name = fn.__name__
        if name in HELPERS:
            continue
        if name not in SAMPLES:
            print(f"{name:28s} NO SAMPLE ARGS"); bad += 1; continue
        try:
            text = generate(fn, SAMPLES[name])
        except Exception as exc:                       # noqa: BLE001
            print(f"{name:28s} GENERATOR FAILED: {exc}"); bad += 1; continue
        problems = check(name, text)
        hard = [p for p in problems if not p.startswith("info:")]
        nl = dump.parse(text); ports = ports_for(name, nl)
        status = ("OK  " if not hard else "STAND" if name in STANDALONE else
                  "DEFER" if name in DEFERRED else "FAIL")
        print(f"{name:26s} {status:5s} [{nl.dialect:6s}] role={ports.role:6s} "
              f"in={[p.node for p in ports.inputs]} out={[p.node for p in ports.outputs]}")
        for p in problems:
            print(f"    - {p}")
        bad += bool(hard) and name not in DEFERRED and name not in STANDALONE
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
