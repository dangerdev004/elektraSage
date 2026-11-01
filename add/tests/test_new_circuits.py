"""Tests for the transistor, DAC, Schmitt and mirror circuits and their cascade analysis."""
import warnings

import pytest

from agent.cascade import dump
from agent.cascade.analysis import analyse
from agent.cascade.dc import operating_point
from agent.cascade.tool import _cascade_impl
from agent.circuits import (binary_weighted_dac, common_emitter_amp, common_source_amp,
                            emitter_follower, mosfet_current_mirror, r2r_dac, schmitt_trigger,
                            sallen_key_lowpass)
from agent.circuits import _active_filters as af

warnings.simplefilter("ignore")


def casc(stages):
    return _cascade_impl(stages, auto_buffer=False)


def out_volts(netlist):
    nl = dump.parse(netlist)
    op = operating_point(nl)
    o = next(e for e in nl.elements if e.type == "O")
    return op.v(dump.terminals(o)[0])


@pytest.mark.parametrize("bits,code", [(4, 3), (4, 10), (3, 5)])
def test_binary_dac_dc_output(bits, code):
    nl = binary_weighted_dac(bits=bits, output_step=0.5, code=code)
    assert out_volts(nl) == pytest.approx(-0.5 * code, abs=1e-3)


@pytest.mark.parametrize("code", [0, 1, 6, 15])
def test_r2r_dac_dc_output(code):
    nl = r2r_dac(bits=4, reference_voltage=16, output_step=1.0, code=code)
    assert out_volts(nl) == pytest.approx(-code, rel=2e-3, abs=2e-3)


def test_dac_bad_arguments():
    with pytest.raises(ValueError):
        r2r_dac(bits=4, code=16)
    with pytest.raises(ValueError):
        binary_weighted_dac(output_step=1, feedback_resistance=1000)


def test_schmitt_trip_points_and_generalised_range():
    for utp, ltp in ((6, 4), (1, -1), (2, -3)):
        nl = dump.parse(schmitt_trigger(utp, ltp))
        assert nl.elements
    with pytest.raises(ValueError):
        schmitt_trigger(2, 3)
    with pytest.warns(Warning):
        schmitt_trigger(6, 4, input_amplitude=0.5, input_offset=0)


def _schmitt_chain(utp, ltp):
    return casc([{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 1000}},
                 {"circuit": "schmitt_trigger",
                  "args": {"upper_trip_voltage": utp, "lower_trip_voltage": ltp}}])[1]


def test_schmitt_toggle_flag_in_cascade():
    good = _schmitt_chain(1, -1)
    assert "comparator with hysteresis" in good and "will not toggle" not in good
    assert "upper 1 V, lower -1 V" in good
    bad = _schmitt_chain(6, 4)
    assert "will not toggle" in bad and "upper 6 V, lower 4 V" in bad


def test_mirror_is_standalone():
    nl = dump.parse(mosfet_current_mirror(supply_voltage=10, reference_current=0.001))
    assert nl.elements
    with pytest.raises(ValueError, match="no signal input or output"):
        casc([{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 100}},
              {"circuit": "mosfet_current_mirror", "args": {"supply_voltage": 10, "reference_current": 0.001}}])


def test_ce_amp_biases_and_gain():
    nl = common_emitter_amp(supply_voltage=12, collector_current=0.001, collector_resistor=4700,
                            emitter_resistor=1000)
    d = dump.parse(nl)
    op = operating_point(d)
    t = next(e for e in d.elements if e.type == "t")
    b, c, e = dump.terminals(t)
    ic = (12 - op.v(c)) / 4700
    assert 0.8e-3 < ic < 1.1e-3               # Falstad's real VBE is ~0.6 V, not 0.7 V
    assert op.v(e) - 0 > 0.7                   # emitter sits about Ic*Re above ground


def test_ce_in_cascade_reports_clipping_when_overdriven():
    out = casc([{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 5000}},
                {"circuit": "common_emitter_amp",
                 "args": {"supply_voltage": 12, "collector_current": 0.001, "collector_resistor": 4700,
                          "emitter_resistor": 1000, "input_amplitude": 2.0}}])
    text = out[1].lower()
    assert "linearised" in text and ("clip" in text or "saturat" in text)


def test_follower_and_source_chain_builds():
    out = casc([{"circuit": "common_emitter_amp",
                 "args": {"supply_voltage": 12, "collector_current": 0.001, "collector_resistor": 4700,
                          "emitter_resistor": 1000, "input_amplitude": 0.01}},
                {"circuit": "emitter_follower",
                 "args": {"supply_voltage": 12, "emitter_current": 0.002, "emitter_resistor": 3000,
                          "beta": 100, "divider_current": 0.0002}}])
    assert out[0].strip() and "emitter_follower" in out[1]


def test_sallen_key_response_option():
    assert af.gain_for_response("butterworth", 1) == pytest.approx(3 - 2 ** 0.5)
    assert af.gain_for_response("bessel", 1) == pytest.approx(3 - 3 ** 0.5)
    assert af.gain_for_response(None, 1.7) == 1.7
    assert af.gain_for_response(2, 1) == pytest.approx(2.5)
    for bad in ("nonsense", 0.3, 50):
        with pytest.raises(ValueError):
            af.gain_for_response(bad, 1)
    a = sallen_key_lowpass(1000, response="butterworth")
    b = sallen_key_lowpass(1000, gain=1.59)
    assert dump.parse(a).elements and len(a) > 0 and len(b) > 0


def test_parallel_refuses_to_analyse_a_comparator_branch():
    from agent.cascade.tool import _parallel_impl
    out = _parallel_impl([[{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 1000}}],
                          [{"circuit": "schmitt_trigger",
                            "args": {"upper_trip_voltage": 1, "lower_trip_voltage": -1}}]], auto_buffer=False)
    assert "NOT ANALYSED" in out[1] and "comparator" in out[1]


def test_coupling_capacitors_start_charged():
    ce = [l.split() for l in common_emitter_amp(12, 0.001, 4700, 1000).splitlines() if l.startswith("c ")]
    assert [float(c[-1]) for c in ce] == pytest.approx([1.7, 7.3])
    ef = [l.split() for l in emitter_follower(12, 0.002, 3000, 100, 0.0002).splitlines() if l.startswith("c ")]
    assert float(ef[0][-1]) < 0
