"""Fixes from the all-pairs validation: every pair was built, and its prediction compared with the simulator."""
import re
import warnings

import pytest

from agent.cascade.conformance import SAMPLES
from agent.cascade.tool import _cascade_impl
from tests.transient import simulate

warnings.simplefilter("ignore")


def st(name, **args):
    return {"circuit": name, "args": args or SAMPLES.get(name, {})}


def text_of(*stages):
    return _cascade_impl(list(stages))[1]


def test_rc_phaseshift_first_is_now_analysed_as_an_oscillator():
    t = text_of(st("rc_phaseshift"), st("rc_lowpass", cutoff_frequency=2000))
    assert "NOT ANALYSED" not in t and "gain of the chain at" in t


def test_integrator_after_a_biased_stage_is_analysed_not_singular():
    t = text_of(st("common_emitter_amp"), st("integrator"))
    assert "NOT ANALYSED" not in t and "sloping" in t


def test_second_input_source_of_a_summing_amp_is_reported():
    t = text_of(st("inverting_amp"), st("summing_amplifier"))
    assert "Other sources: stage 2 still has its own square source" in t


def test_regulator_without_headroom_gets_a_useful_reason():
    t = text_of(st("emitter_follower"), st("linear_regulator"))
    assert "NOT ANALYSED" in t and "dropout" in t


def test_square_wave_through_a_follower_has_no_gibbs_overshoot():
    t = text_of(st("square_wave_generator"), st("voltage_follower"))
    m = re.search(r"output swings (-?[\d.]+) V to (-?[\d.]+) V", t)
    assert m and float(m.group(1)) > -0.3 and float(m.group(2)) < 10.3


def test_astable_into_rc_matches_the_simulator():
    t = text_of(st("astable_555_generator"), st("rc_lowpass", cutoff_frequency=1000))
    lo, hi = map(float, re.search(r"output swings (-?[\d.]+) V to (-?[\d.]+) V", t).groups())
    net, _ = _cascade_impl([st("astable_555_generator"), st("rc_lowpass", cutoff_frequency=1000)])
    f = float(re.search(r"wave at ([\d.]+)", t.replace("kHz", "000").replace("Hz", "")).group(1)) or 1000
    _, v = simulate(net, 0.05, dt=2e-6, probe_index=max(i for i, l in enumerate(net.splitlines()[1:]) if l.startswith("O ")))
    seg = v[len(v) // 2:]
    assert seg.max() == pytest.approx(hi, abs=0.15) and seg.min() == pytest.approx(lo, abs=0.15)
