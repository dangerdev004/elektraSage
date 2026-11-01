"""P-channel MOSFET support and the CMOS inverter stage."""
import warnings

import pytest

from agent.cascade import dc, dump
from agent.cascade.ports import is_signal_source
from agent.cascade.tool import _cascade_impl, _parallel_impl, cascade
from agent.circuits import cmos_inverter
from tests.transient import simulate

warnings.simplefilter("ignore")


def transfer(vin, **kw):
    nl = dump.parse(cmos_inverter(**kw))
    nl.elements = [e for e in nl.elements if not is_signal_source(e)]
    out = next(e for e in nl.elements if e.type == "O").p1
    return dc.operating_point(nl, fixed={(96, 176): vin}).v(out)


def test_pchannel_mirrors_nchannel():
    n = dc.mosfet_currents(1.0, 4.0, 0.0, 1.5, 0.02)
    p = dc.mosfet_currents(-1.0, -4.0, 0.0, 1.5, 0.02, -1.0)
    assert p == pytest.approx(tuple(-x for x in n))
    assert dc.mosfet_currents(-1.0, 0.0, 0.0, 1.5, 0.02, -1.0)[0] == pytest.approx(0, abs=1e-6)   # Vsg = 0: off


def test_pin_geometry():
    nl = dump.parse(cmos_inverter())
    p, n = [e for e in nl.elements if e.type == "f"]
    assert int(p.flags) & 1 and not int(n.flags) & 1
    assert dump.mosfet_pins(p)["s"][1] < dump.mosfet_pins(p)["d"][1]      # P: source up to Vdd
    assert dump.mosfet_pins(n)["d"][1] < dump.mosfet_pins(n)["s"][1]      # N: drain up, source to ground


def test_static_transfer_curve():
    assert transfer(0.0) == pytest.approx(5.0, abs=1e-3)
    assert transfer(5.0) == pytest.approx(0.0, abs=1e-3)
    assert transfer(2.5) == pytest.approx(2.5, abs=0.05)                 # matched devices switch at Vdd/2
    assert transfer(1.5) > 4.9 and transfer(3.5) < 0.1


def test_threshold_follows_supply():
    assert transfer(4.5, supply_voltage=9.0) == pytest.approx(4.5, abs=0.05)


def test_time_domain_switches_rail_to_rail_at_half_duty():
    t, y = simulate(cmos_inverter(), 0.004, dt=5e-6)
    h = y[len(y) // 4:]
    assert h.max() == pytest.approx(5.0, abs=0.01) and h.min() == pytest.approx(0.0, abs=0.01)
    assert (h > 2.5).mean() == pytest.approx(0.5, abs=0.02)


def test_cascade_matches_independent_simulation():
    st = [{"circuit": "cmos_inverter", "args": {}}, {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 200}}]
    nl, text = _cascade_impl(st, auto_buffer=False)
    d = dump.parse(nl)
    idx = max(i for i, e in enumerate(d.elements) if e.type == "O")
    t, y = simulate(nl, 0.05, dt=5e-6, probe_index=idx)
    h = y[len(y) // 2:]
    assert h.max() == pytest.approx(3.22, abs=0.08) and h.min() == pytest.approx(1.78, abs=0.08)
    assert "swings 1.78 V to 3.22 V" in text


def test_reply_says_it_switches():
    _, sheet = cascade([{"circuit": "cmos_inverter", "args": {}},
                        {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 200}}])
    assert "doesn't amplify" in sheet.reply and "on-resistance" in sheet.reply and "quasi-static" in sheet.reply


def test_skewed_bias_changes_duty():
    _, sheet = cascade([{"circuit": "cmos_inverter", "args": {"input_bias": 3.0, "input_amplitude": 2.5}},
                        {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 200}}])
    assert "high for 43" in sheet.reply                 # sin(theta) < -0.2 for 43.5% of the period


def test_inverter_after_another_stage_is_not_analysed():
    _, sheet = cascade([{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 200}},
                        {"circuit": "cmos_inverter", "args": {}}], source_amplitude=2.0)
    assert "switches between its rails" in sheet.reply or "could not be computed" in sheet.reply


def test_inverter_in_parallel_is_not_analysed():
    from agent.cascade.tool import parallel_sum
    _, sheet = parallel_sum([[{"circuit": "cmos_inverter", "args": {}}],
                             [{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 1000}}]])
    assert "inverter" in sheet.reply


@pytest.mark.parametrize("call", [
    lambda: cmos_inverter(supply_voltage=3.0), lambda: cmos_inverter(beta=0),
    lambda: cmos_inverter(input_frequency=-1), lambda: cmos_inverter(load_capacitor=0),
])
def test_bad_arguments_are_refused(call):
    with pytest.raises(ValueError):
        call()
