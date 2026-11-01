"""Diode / zener support in the DC solver and the linear regulator stage."""
import math
import warnings

import pytest

from agent.cascade import dc, dump
from agent.cascade.tool import _cascade_impl, cascade
from agent.circuits import linear_regulator
from tests.transient import simulate

warnings.simplefilter("ignore")

ZENER_DIVIDER = """$ 1 5e-06 10 57 5.0
R 64 64 32 64 0 0 40.0 12.0 0.0
r 64 64 128 64 0 1740.0
w 128 64 128 96 0
z 128 160 128 96 0 0.805904783 3.3
g 128 160 128 176 0
O 128 96 192 96 0
"""


def vout(nl):
    d = dump.parse(nl)
    return dc.operating_point(d).v(next(e for e in d.elements if e.type == "O").p1)


def test_zener_model_hits_five_milliamps_at_its_voltage():
    assert dc.diode_current(-3.3, 3.3) == pytest.approx(-0.005, rel=0.02)
    assert dc.diode_current(0.5, 3.3) > 0 and dc.diode_current(-1.0, 3.3) == pytest.approx(0, abs=1e-6)


def test_zener_regulates_in_dc_and_in_the_simulator():
    assert vout(ZENER_DIVIDER) == pytest.approx(3.3, abs=0.01)
    t, y = simulate(ZENER_DIVIDER, 0.0005, dt=5e-6)
    assert y[-1] == pytest.approx(3.3, abs=0.01)


def test_plain_diode_forward_drop_matches_falstad_default():
    nl = "$ 1 5e-06 10 57 5.0\nR 64 64 32 64 0 0 40.0 5.0 0.0\nr 64 64 128 64 0 1000.0\nd 128 64 128 128 2 default\ng 128 128 128 144 0\nO 128 64 192 64 0\n"
    assert vout(nl) == pytest.approx(0.0517 * math.log(4.45e-3 / 1.714e-7), abs=0.03)


@pytest.mark.parametrize("vin", [12.0, 9.0, 6.5])
def test_regulator_holds_its_output_for_any_input_above_dropout(vin):
    assert vout(linear_regulator(input_voltage=vin)) == pytest.approx(5.0, abs=0.01)


def test_output_follows_the_divider_formula():
    assert vout(linear_regulator(output_voltage=7.5, zener_voltage=3.3, input_voltage=15)) == pytest.approx(7.5, abs=0.02)


def test_ripple_rejection_matches_independent_simulation():
    nl = linear_regulator()
    t, y = simulate(nl, 0.05, dt=5e-6)
    h = y[len(y) // 2:]
    sim_ripple = (h.max() - h.min()) / 2
    _, text = _cascade_impl([{"circuit": "linear_regulator", "args": {}},
                             {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 1000}}], auto_buffer=False)
    pred = float([l for l in text.splitlines() if "passband gain" in l][0].split("passband gain ")[1].split()[0])
    assert pred == pytest.approx(sim_ripple / 1.0, rel=0.05)


def test_cascade_reply_reports_regulation_facts():
    _, sheet = cascade([{"circuit": "linear_regulator", "args": {}},
                        {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 1000}}])
    r = sheet.reply
    assert "holds its output at 5 V" in r and "dB of rejection" in r and "mV per volt" in r


def test_trough_dropout_is_flagged():
    _, sheet = cascade([{"circuit": "linear_regulator", "args": {"input_voltage": 6.5, "ripple_amplitude": 1.0}},
                        {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 1000}}])
    assert "Dropout" in sheet.reply


@pytest.mark.parametrize("call", [
    lambda: linear_regulator(zener_voltage=6.0, output_voltage=5.0),
    lambda: linear_regulator(input_voltage=5.5, output_voltage=5.0),
    lambda: linear_regulator(load_current=0), lambda: linear_regulator(beta=-1),
])
def test_bad_arguments_are_refused(call):
    with pytest.raises(ValueError):
        call()


def test_op_amp_that_must_leave_its_rails_still_solves():
    # input 6.0 V is only 1 V above the output: the ideal-op-amp attempt cannot settle, the saturating one does
    assert vout(linear_regulator(input_voltage=6.0)) == pytest.approx(5.0, abs=0.01)
