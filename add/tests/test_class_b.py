"""Class-B / class-AB push-pull stage and the PNP support behind it."""
import warnings

import pytest

from agent.cascade import dc, dump
from agent.cascade.tool import _cascade_impl, cascade
from agent.circuits import class_b_amp
from tests.transient import simulate

warnings.simplefilter("ignore")


def run(**kw):
    t, y = simulate(class_b_amp(**kw), 0.004, dt=5e-6)
    return y[len(y) // 2:]


def test_pnp_currents_mirror_the_npn():
    n = dc.bjt_currents(5.0, 0.7, 0.0, 100.0, 1.0)
    p = dc.bjt_currents(-5.0, -0.7, 0.0, 100.0, -1.0)
    assert p == pytest.approx(tuple(-x for x in n))
    assert n[0] > 0 and p[0] < 0                      # a PNP's collector current flows out of the collector


def test_pin_geometry_of_the_pair():
    nl = dump.parse(class_b_amp(bias_current=0.0))
    t = [e for e in nl.elements if e.type == "t"]
    npn, pnp = dump.bjt_pins(t[0]), dump.bjt_pins(t[1])
    assert npn["c"][1] < npn["e"][1]                  # NPN: collector up to +Vs, emitter down
    assert pnp["e"][1] < pnp["c"][1]                  # PNP (CircuitJS swaps its pins): emitter up to the output, collector down to -Vs


def test_idle_point_is_balanced():
    nl = dump.parse(class_b_amp(bias_current=0.003, emitter_resistor=1.0))
    op = dc.operating_point(nl)
    out = next(e for e in nl.elements if e.type == "O").p1
    assert op.v(out) == pytest.approx(0.0, abs=0.05)
    ics = [abs(dc.bjt_currents(*[op.v(p) for p in (dump.bjt_pins(e)[k] for k in "cbe")], 100.0,
                               float(e.tail[0]))[0]) for e in nl.elements if e.type == "t"]
    assert all(1e-3 < i < 1e-2 for i in ics)           # all four devices idle in the mA range


def test_class_ab_follows_the_input_with_small_loss():
    y = run(input_amplitude=3)
    assert y.max() == pytest.approx(2.85, abs=0.15) and y.min() == pytest.approx(-2.85, abs=0.15)
    assert (abs(y) < 0.1).mean() < 0.06                # no flat dead zone


def test_pure_class_b_has_a_dead_zone_and_loses_a_diode_drop():
    y = run(input_amplitude=3, bias_current=0.0)
    assert y.max() == pytest.approx(3 - 0.7, abs=0.15)
    assert (abs(y) < 0.1).mean() > 0.10                # crossover gap


def test_clips_at_the_rails():
    y = run(supply_voltage=5.0, input_amplitude=4.5)
    assert 2.5 < y.max() < 4.0                        # clipped well below the 4.5 V input; the bias resistor costs headroom


@pytest.mark.parametrize("call", [
    lambda: class_b_amp(supply_voltage=1.0), lambda: class_b_amp(load_resistor=0),
    lambda: class_b_amp(bias_current=-1), lambda: class_b_amp(supply_voltage=3, bias_current=0.1),
])
def test_bad_arguments_are_refused(call):
    with pytest.raises(ValueError):
        call()


def test_cascade_class_ab_prediction_is_conservative_but_close():
    nl, text = _cascade_impl([{"circuit": "class_b_amp", "args": {"input_amplitude": 3}},
                              {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 5000}}], auto_buffer=False)
    assert "passband gain of about 0.87" in cascade([{"circuit": "class_b_amp", "args": {"input_amplitude": 3}},
                                                     {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 5000}}])[1].reply
    assert "PNP" in text


def test_cascade_flags_crossover_once_and_refuses_a_gain_figure():
    _, sheet = cascade([{"circuit": "class_b_amp", "args": {"input_amplitude": 3, "bias_current": 0}},
                        {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 5000}}])
    assert sheet.reply.count("Crossover:") == 1
    assert "can't give a meaningful small-signal gain" in sheet.reply
    assert "passband gain" not in sheet.reply
