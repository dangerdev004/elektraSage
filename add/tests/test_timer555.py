"""555 generators: formulas against the independent simulator, 555 pin geometry, and their cascade behaviour."""
import warnings

import re

import pytest

from agent.cascade import dump
from agent.cascade.tool import _cascade_impl, _parallel_impl, cascade
from agent.circuits import astable_555_generator, monostable_555_generator, square_wave_generator
from agent.circuits.astable_555_generator import design as astable_design
from agent.circuits.squarewave_generator import design as square_design
from tests.transient import measure, simulate

warnings.simplefilter("ignore")


def duty(y, vcc):
    h = y[len(y) // 2:]
    return float((h > vcc / 2).mean())


@pytest.mark.parametrize("kw", [{}, {"frequency": 1000}, {"frequency": 20000}])
def test_square_wave_matches_simulation(kw):
    d = square_design(**kw)
    t, y = simulate(square_wave_generator(**kw)[0], min(0.3, 40 / d.f_hz))
    f, hi, lo = measure(t, y)
    assert f == pytest.approx(d.f_hz, rel=0.03)
    assert hi == pytest.approx(d.supply_voltage, rel=0.01) and lo == pytest.approx(0, abs=0.05)
    assert duty(y, d.supply_voltage) == pytest.approx(d.duty, abs=0.02)


def test_square_wave_frequency_argument_is_honoured():
    assert square_design(frequency=1000).f_hz == pytest.approx(1000, rel=1e-6)


@pytest.mark.parametrize("kw", [{}, {"frequency": 200, "duty_cycle": 0.75, "supply_voltage": 9},
                                {"ra_ohms": 1e4, "rb_ohms": 47e3, "capacitor": 1e-8}])
def test_astable_matches_simulation(kw):
    d = astable_design(**kw)
    t, y = simulate(astable_555_generator(**kw)[0], min(0.3, 40 / d.f_hz))
    f, hi, lo = measure(t, y)
    assert f == pytest.approx(d.f_hz, rel=0.03)
    assert duty(y, d.supply_voltage) == pytest.approx(d.duty, abs=0.02)
    assert hi == pytest.approx(d.supply_voltage, rel=0.01)


def test_astable_formulas():
    d = astable_design(ra_ohms=10e3, rb_ohms=47e3, capacitor=1e-8)
    assert d.f_hz == pytest.approx(1.44 / ((10e3 + 94e3) * 1e-8), rel=0.01)
    assert d.duty == pytest.approx(57e3 / 104e3, rel=0.01)


def test_monostable_pulse_width_matches_simulation():
    text, _ = monostable_555_generator(timing_resistor=1e4, capacitor=1e-7)
    text = text.replace("L 80 240 48 240 0 1 true", "L 80 240 48 240 0 0 true")      # press the button at t=0
    t, y = simulate(text, 0.006, dt=5e-6)
    hi = t[y > 2.5]
    assert hi.max() - hi.min() == pytest.approx(1.1e-3, rel=0.03)


@pytest.mark.parametrize("call", [
    lambda: astable_555_generator(duty_cycle=0.4), lambda: astable_555_generator(duty_cycle=1.0),
    lambda: astable_555_generator(frequency=-5), lambda: square_wave_generator(frequency=0),
    lambda: square_wave_generator(reset_pullup=-1), lambda: monostable_555_generator(pulse_width=-1),
])
def test_bad_arguments_are_refused(call):
    with pytest.raises(ValueError):
        call()


@pytest.mark.parametrize("fn", [square_wave_generator, monostable_555_generator, astable_555_generator])
def test_defaults_build_legacy_netlist_with_one_output_and_one_timer(fn):
    nl = dump.parse(fn()[0])
    assert nl.dialect == "legacy"
    assert sum(e.type == "O" for e in nl.elements) == 1
    assert sum(e.type == "165" for e in nl.elements) == 1
    assert all(dump.terminals(e) is not None for e in nl.elements)


def test_timer_pin_positions():
    nl = dump.parse(monostable_555_generator()[0])
    e = next(e for e in nl.elements if e.type == "165")
    pins = dict(zip(dump.TIMER_PINS, dump.terminals(e)))
    assert pins["dis"] == (208, 176) and pins["tr"] == (208, 240) and pins["th"] == (208, 272)
    assert pins["vin"] == (272, 112) and pins["out"] == (336, 208) and pins["gnd"] == (304, 304)


def test_astable_into_lowpass_prediction_matches_simulation():
    stages = [{"circuit": "astable_555_generator", "args": {"frequency": 1000, "duty_cycle": 0.7}},
              {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 200}}]
    netlist, text = _cascade_impl(stages, auto_buffer=False)
    d = dump.parse(netlist)
    idx = max(i for i, e in enumerate(d.elements) if e.type == "O")
    t, y = simulate(netlist, 0.1, probe_index=idx)
    _, hi, lo = measure(t, y, 0.6)
    assert lo == pytest.approx(2.83, abs=0.1) and hi == pytest.approx(4.07, abs=0.1)
    plo, phi = map(float, re.search(r"swings (-?[\d.]+) V to (-?[\d.]+) V", text).groups())
    assert plo == pytest.approx(lo, abs=0.1) and phi == pytest.approx(hi, abs=0.1)


def test_square_wave_cascade_reply_and_prediction():
    _, sheet = cascade([{"circuit": "square_wave_generator", "args": {}},
                        {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 50}}])
    assert "swing of 0V to 10V" in sheet.reply and "high for 49.5%" in sheet.reply


def test_monostable_cascade_reports_the_pulse_only():
    _, sheet = cascade([{"circuit": "monostable_555_generator", "args": {"pulse_width": 0.01}},
                        {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 50}}])
    assert "one-shot" in sheet.reply and "10ms" in sheet.reply and "only the pulse is described" in sheet.reply


def test_timer_after_another_stage_is_refused():
    for name in ("astable_555_generator", "monostable_555_generator", "square_wave_generator"):
        with pytest.raises(ValueError, match="FIRST stage"):
            _cascade_impl([{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 500}},
                           {"circuit": name, "args": {}}], auto_buffer=False)


def test_timer_branch_in_parallel_is_refused():
    with pytest.raises(ValueError, match="takes no signal input"):
        _parallel_impl([[{"circuit": "astable_555_generator", "args": {}}],
                        [{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 1000}}]], auto_buffer=False)
