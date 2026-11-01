"""Oscillator generators: design formulas against an independent simulation, and their cascade analysis."""
import importlib
import math
import warnings

import re

import pytest

from agent.cascade import dump
from agent.cascade.tool import _cascade_impl
from agent.circuits import (phase_shift_oscillator, sawtooth_oscillator, triangle_oscillator,
                            wien_bridge_oscillator)
from tests.transient import measure, simulate

warnings.simplefilter("ignore")


def calc(name):
    return importlib.import_module(f"agent.circuits.{name}").calculate


# ---- design formulas vs the independent transient simulator -----------------------------
def test_triangle_matches_simulation():
    v = calc("triangle_oscillator")(f_hz=500, vpk_v=4)
    assert v.f_hz == pytest.approx(15 / (4 * 4 * v.Rint * v.C))
    assert v.R1 == pytest.approx(v.Rfb * 4 / 15)
    t, y = simulate(triangle_oscillator(f_hz=500, vpk_v=4), 0.06)
    f, hi, lo = measure(t, y)
    assert f == pytest.approx(500, rel=0.03)
    assert hi == pytest.approx(4, rel=0.03) and lo == pytest.approx(-4, rel=0.03)


def test_sawtooth_matches_simulation():
    v = calc("sawtooth_oscillator")(f_hz=300, rise_fraction=0.8)
    assert v.rise_fraction == pytest.approx(0.8, rel=1e-6)
    t, y = simulate(sawtooth_oscillator(f_hz=300, rise_fraction=0.8), 0.1)
    f, hi, lo = measure(t, y)
    assert f == pytest.approx(300, rel=0.05)
    assert hi == pytest.approx(6, rel=0.05) and lo == pytest.approx(-6, rel=0.05)


def test_wien_matches_simulation():
    v = calc("wien_bridge_oscillator")(f_hz=200, amplitude_v=8)
    assert v.f_hz == pytest.approx(200)
    t, y = simulate(wien_bridge_oscillator(f_hz=200, amplitude_v=8), 1.2, dt=5e-5)
    f, hi, lo = measure(t, y, 0.7)
    assert f == pytest.approx(200, rel=0.03)
    assert hi == pytest.approx(8, rel=0.08)             # the lamp-model amplitude is an estimate


def test_phase_shift_oscillates_near_expected_frequency():
    v = calc("phase_shift_oscillator")()
    assert v.Rf == pytest.approx(29 * 1.1 * v.R)
    # the simulator needs a lower op-amp gain to converge here; the loop gain of 29 is far below it
    t, y = simulate(phase_shift_oscillator(), 0.3, gain=1e3)
    f, hi, lo = measure(t, y, 0.6)
    assert f == pytest.approx(v.f_expected_hz, rel=0.08)
    assert hi > 10 and lo < -10                           # grows until the +/-15 V limits stop it


# ---- argument checks ---------------------------------------------------------------------
@pytest.mark.parametrize("call", [
    lambda: triangle_oscillator(f_hz=100, r_int_ohms=1000),
    lambda: triangle_oscillator(vpk_v=15),
    lambda: sawtooth_oscillator(f_hz=100, r_rise_ohms=1000, r_fall_ohms=1000),
    lambda: sawtooth_oscillator(r_rise_ohms=1000),
    lambda: wien_bridge_oscillator(f_hz=100, r_ohms=1000),
    lambda: wien_bridge_oscillator(rf_ohms=1.0),
    lambda: phase_shift_oscillator(gain_margin=0.9),
    lambda: phase_shift_oscillator(f_hz=100, r_ohms=1000),
])
def test_bad_arguments_are_refused(call):
    with pytest.raises(ValueError):
        call()


@pytest.mark.parametrize("fn", [triangle_oscillator, sawtooth_oscillator, wien_bridge_oscillator,
                                phase_shift_oscillator])
def test_defaults_build_a_legacy_netlist_with_one_output(fn):
    nl = dump.parse(fn())
    assert nl.dialect == "legacy"
    assert sum(e.type == "O" for e in nl.elements) == 1


# ---- cascade analysis --------------------------------------------------------------------
def casc(stages):
    return _cascade_impl(stages, auto_buffer=False)[1]


def test_triangle_into_lowpass_uses_fundamental_and_harmonics():
    text = casc([{"circuit": "triangle_oscillator", "args": {"f_hz": 1000}},
                 {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 500}}])
    fc = 1 / (2 * math.pi * 33000 * 1e-8)
    g = 1 / math.sqrt(1 + (1000 / fc) ** 2)
    assert f"gain of the chain at 1kHz: {g:.3g}" in text
    assert "oscillator with no signal input" in text
    assert "swings -2.08 V to 2.08 V" in text            # matches tests' independent simulation (+/-2.08 V)


def test_oscillator_after_another_stage_is_refused():
    with pytest.raises(ValueError, match="FIRST stage"):
        casc([{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 500}},
              {"circuit": "triangle_oscillator", "args": {}}])


def test_clipping_is_flagged_for_a_large_waveform():
    text = casc([{"circuit": "triangle_oscillator", "args": {"f_hz": 1000, "vpk_v": 4}},
                 {"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000, "amp_supply": 15}}])
    assert "Clipping: the op-amp in stage 2 would clip" in text


def test_chain_prediction_matches_independent_simulation():
    stages = [{"circuit": "sawtooth_oscillator", "args": {"f_hz": 500}},
              {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 2000}}]
    netlist, text = _cascade_impl(stages, auto_buffer=False)
    d = dump.parse(netlist)
    idx = max(i for i, e in enumerate(d.elements) if e.type == "O")
    t, y = simulate(netlist, 0.1, probe_index=idx)
    f, hi, lo = measure(t, y, 0.6)
    assert hi == pytest.approx(5.49, abs=0.2) and lo == pytest.approx(-4.59, abs=0.2)
    plo, phi = map(float, re.search(r"swings (-?[\d.]+) V to (-?[\d.]+) V", text).groups())
    assert plo == pytest.approx(lo, abs=0.2) and phi == pytest.approx(hi, abs=0.2)


def test_reply_describes_the_oscillator():
    from agent.cascade.tool import cascade
    _, sheet = cascade([{"circuit": "wien_bridge_oscillator", "args": {"f_hz": 1000, "amplitude_v": 5}},
                        {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 2000}}])
    assert "Stage 1 is a wien bridge oscillator" in sheet.reply and "an estimate" in sheet.reply


def test_oscillator_branch_in_parallel_is_refused():
    from agent.cascade.tool import _parallel_impl
    with pytest.raises(ValueError, match="takes no signal input"):
        _parallel_impl([[{"circuit": "triangle_oscillator", "args": {}}],
                        [{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 1000}}]], auto_buffer=False)
