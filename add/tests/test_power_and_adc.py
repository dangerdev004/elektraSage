"""Full-wave rectifier, the four DC-DC converters and the flash ADC: generators vs the independent simulator,
and their cascade analysis."""
import re
import warnings

import pytest

from agent.cascade.powersources import converter_signal, rectifier_signal
from agent.cascade.tool import _cascade_impl
from agent.circuits import (boost_converter, buck_boost_converter, buck_converter, cuk_converter, flash_adc,
                            full_wave_rectifier)
from tests.transient import simulate

warnings.simplefilter("ignore")


def tail_stats(netlist, t_end, fraction=0.2):
    t, v = simulate(netlist, t_end)
    k = max(int(len(v) * fraction), 1)
    return v[-k:].mean(), v[-k:].max() - v[-k:].min()


def test_rectifier_signal_matches_simulation():
    sig = rectifier_signal({})
    t, v = simulate(full_wave_rectifier(), 0.15)
    tail = v[len(v) // 2:]
    assert sig.v_high == pytest.approx(tail.max(), abs=0.1)
    assert sig.v_low == pytest.approx(tail.min(), abs=0.15)
    assert sig.f0 == 100.0


@pytest.mark.parametrize("fn,name,target,tol", [
    (buck_converter, "buck_converter", 5.0, 0.05),
    (boost_converter, "boost_converter", 12.0, 0.04),
    (buck_boost_converter, "buck_boost_converter", -5.0, 0.04),
    (cuk_converter, "cuk_converter", -5.0, 0.04),
])
def test_converter_reaches_its_target_in_simulation(fn, name, target, tol):
    mean, pp = tail_stats(fn(), 6e-3)
    assert mean == pytest.approx(target, rel=tol)
    assert pp < 0.05 * abs(target)
    assert converter_signal(name, {}).dc == pytest.approx(target)


def test_converter_follows_the_requested_voltage():
    mean, _ = tail_stats(buck_converter(input_voltage=15.0, output_voltage=3.3, load_current=0.3), 6e-3)
    assert mean == pytest.approx(3.3, rel=0.06)


@pytest.mark.parametrize("fn,kw", [
    (buck_converter, dict(output_voltage=20.0)),
    (boost_converter, dict(output_voltage=3.0)),
    (buck_converter, dict(load_current=-1.0)),
    (cuk_converter, dict(switching_frequency=0.0)),
])
def test_converter_refuses_bad_arguments(fn, kw):
    with pytest.raises(ValueError):
        fn(**kw)


@pytest.mark.parametrize("bits", [2, 3])
def test_flash_adc_codes_in_simulation(bits):
    base = flash_adc(bits=bits)
    lines = base.splitlines()
    outs = [i - 1 for i, l in enumerate(lines) if l.startswith("M ")]      # b0, b1 (, b2)
    m, lsb = 2 ** bits, 5.0 / 2 ** bits
    for code in range(m):
        vin = (code + 0.5) * lsb
        net = re.sub(r"^R 96 (\d+) 48 \1 0 3 .*$", lambda g: f"R 96 {g.group(1)} 48 {g.group(1)} 0 0 40.0 {vin} 0.0",
                     base, flags=re.M)
        got = 0
        for weight, idx in enumerate(outs):
            _, v = simulate(net, 2e-4, dt=1e-5, probe_index=idx)
            got |= int(v[-1] > 2.5) << weight
        assert got == code, (bits, vin, got, code)


def test_flash_adc_rejects_unsupported_resolution():
    with pytest.raises(ValueError):
        flash_adc(bits=4)


def test_rectifier_cascade_reports_ripple_and_filtered_level():
    _, text = _cascade_impl([{"circuit": "full_wave_rectifier", "args": {}},
                             {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 20}}])
    assert "supply" in text and "100Hz" in text
    m = re.search(r"output swings ([\d.]+) V to ([\d.]+) V", text)
    assert m and 8.0 < float(m.group(1)) < float(m.group(2)) < 8.5


def test_converter_cascade_marks_the_level_as_a_design_target():
    _, text = _cascade_impl([{"circuit": "buck_converter", "args": {}},
                             {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 5000}}])
    assert "averaging 5V" in text and "design target" in text


def test_adc_at_the_end_of_a_chain_reports_codes_and_clipping():
    _, text = _cascade_impl([{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 100}},
                             {"circuit": "flash_adc", "args": {}}])
    assert "flash_adc" in text and "625mV" in text
    assert "below the ADC's 0 V floor" in text
    _, text = _cascade_impl([{"circuit": "buck_converter", "args": {}},
                             {"circuit": "flash_adc", "args": {"bits": 2}}])
    assert "essentially a DC level" in text and "code 3" in text


def test_flash_adc_no_wire_ends_on_another_wire_and_scope_watches_input():
    from agent.circuits import flash_adc
    for bits in (2, 3):
        text = flash_adc(bits=bits)
        lines = text.splitlines()
        wires = [tuple(map(int, l.split()[1:5])) for l in lines if l.startswith("w ")]
        for a in wires:
            for p in ((a[0], a[1]), (a[2], a[3])):
                for b in wires:
                    if b is a:
                        continue
                    if b[0] == b[2] == p[0] and min(b[1], b[3]) < p[1] < max(b[1], b[3]):
                        raise AssertionError(f"wire end {p} lies inside wire {b}")
                    if b[1] == b[3] == p[1] and min(b[0], b[2]) < p[0] < max(b[0], b[2]):
                        raise AssertionError(f"wire end {p} lies inside wire {b}")
        scope = next(l for l in lines if l.startswith("o "))
        idx = int(scope.split()[1])
        assert lines[1 + idx].split()[:6] == ["R", "96", lines[1 + idx].split()[2], "48", lines[1 + idx].split()[4], "0"] or lines[1 + idx].split()[6] == "3"
