"""Three or more parallel paths, weighted sums and differences: every result is checked against an independent
AC solver (tests/mna.py) applied to each path on its own."""
import warnings

import pytest

from agent.cascade import dump
from agent.cascade.combiners import MAX_PATHS, difference_combiner, sum_combiner
from agent.cascade.tool import _build_parallel, _cascade_impl, parallel_difference, parallel_sum
from tests.adc_check import check_geometry
from tests.mna import solve

warnings.simplefilter("ignore")


def st(circuit, **args):
    return {"circuit": circuit, "args": args}


VF = st("voltage_follower")
LP = st("rc_lowpass", cutoff_frequency=1000)
HP = st("rc_highpass", cutoff_frequency=100)
BAND = [st("rc_highpass", cutoff_frequency=300), st("rc_lowpass", cutoff_frequency=3000)]
AMP = st("inverting_amp", gain=2, res=10000)


def alone(branch, f):
    """Response of one path by itself (a follower is appended to single-stage paths: it changes nothing and lets
    the cascade tool accept them)."""
    stages = list(branch) if len(branch) > 1 else [*branch, VF]
    net = _cascade_impl(stages)[0]
    out = [e for e in dump.parse(net).elements if e.type == "O"][-1]
    return solve(net, f)["V"]((out.x1, out.y1))


def expected(branches, f, gain, weights, difference):
    h = [alone(b, f) for b in branches]
    if difference:
        return gain * (h[0] - h[1])
    w = weights or [1] * len(h)
    return -gain * sum(wi * hi for wi, hi in zip(w, h))


CASES = [
    ("three paths", [[LP, VF], [HP, VF], [*BAND, VF]], 1.0, None, False),
    ("four paths, one with an op-amp", [[LP, VF], [HP, VF], [*BAND, VF], [AMP]], 1.0, None, False),
    ("two paths weighted 2:1", [[LP, VF], [HP, VF]], 1.0, [2, 1], False),
    ("three paths, gain 2, weights 1:2:0.5", [[LP, VF], [HP, VF], [*BAND, VF]], 2.0, [1, 2, 0.5], False),
    ("eight paths", [[LP, VF]] * 8, 1.0, None, False),
    ("difference", [[LP, VF], [HP, VF]], 2.0, None, True),
    ("difference, op-amp path first (stacked the other way up)", [[AMP], [LP, VF]], 1.0, None, True),
    ("difference, op-amp path second", [[LP, VF], [AMP]], 1.0, None, True),
]


@pytest.mark.parametrize("label,branches,gain,weights,difference", CASES, ids=[c[0] for c in CASES])
def test_combined_output_matches_the_paths_on_their_own(label, branches, gain, weights, difference):
    _, _, par, analysis = _build_parallel(branches, gain, None, weights, difference)
    assert not par.problems and analysis.supported
    text = par.netlist.to_text()
    assert check_geometry(text) == 0
    for f in (30, 300, 3000):
        want = expected(branches, f, gain, weights, difference)
        got = solve(text, f)["V"](par.sum_out)
        assert got == pytest.approx(want, rel=0.02, abs=1e-3), (label, f)


def test_one_source_drives_every_path_and_only_one_combiner_op_amp_is_added():
    text, _ = parallel_sum([[LP, VF], [HP, VF], [*BAND, VF]])
    nl = dump.parse(text)
    assert sum(1 for e in nl.elements if e.type == "R" and e.tail[0] != "0") + \
        sum(1 for e in nl.elements if e.type in ("170", "v")) == 1
    assert sum(1 for e in nl.elements if e.type == "a") == 4          # three followers + the summing op-amp


def test_replies_name_the_number_of_paths_and_the_weights():
    _, sheet = parallel_sum([[LP, VF], [HP, VF], [*BAND, VF]], weights=[1, 2, 3])
    assert sheet.reply.startswith("I've split the input into three parallel paths")
    assert "Path 3:" in sheet.reply and "path weights 1, 2, 3" in sheet.reply
    assert "every path" in sheet.reply and "weighted" in sheet.reply
    _, sheet = parallel_difference([[LP, VF], [HP, VF]])
    assert "subtracted" in sheet.reply and "path 1 minus path 2" in sheet.reply


def test_fix_calls_remember_the_right_tool_and_weights():
    _, sheet = parallel_sum([[LP], [HP]], weights=[2, 1])
    name, args = sheet.fix_call or sheet.alt_call
    assert name == "parallel_sum" and args.get("weights") == [2, 1]
    _, sheet = parallel_difference([[LP], [HP]])
    name, args = sheet.fix_call or sheet.alt_call
    assert name == "parallel_difference" and "weights" not in args


@pytest.mark.parametrize("call,match", [
    (lambda: parallel_sum([[LP]] * 9), "from 2 to 8 paths"),
    (lambda: parallel_sum([[LP], [HP]], weights=[1]), "one number per path"),
    (lambda: parallel_sum([[LP], [HP]], weights=[1, 0]), "weights"),
    (lambda: parallel_sum([[LP], [HP]], weights=[1, -2]), "weights"),
    (lambda: parallel_difference([[LP], [HP], [LP]]), "exactly TWO"),
    (lambda: parallel_sum([[LP], [HP], [st("binary_counter", bits=4)]]), "digital"),
    (lambda: parallel_sum([[LP], [HP], [st("square_wave_generator")]]), "takes no signal input"),
])
def test_bad_requests_are_refused_clearly(call, match):
    with pytest.raises(ValueError, match=match):
        call()


def test_equal_weights_of_one_are_the_plain_sum():
    a, _ = parallel_sum([[LP, VF], [HP, VF]])
    b, _ = parallel_sum([[LP, VF], [HP, VF]], weights=[1, 1])
    assert a == b


def test_combiner_generators_validate_their_arguments():
    for bad in (1, MAX_PATHS + 1, 2.5, True):
        with pytest.raises(ValueError):
            sum_combiner(bad)
    with pytest.raises(ValueError):
        sum_combiner(3, gain_v_per_v=0)
    with pytest.raises(ValueError):
        sum_combiner(3, weights=[1, 2])
    with pytest.raises(ValueError):
        difference_combiner(float("nan"))
    with pytest.raises(ValueError, match="too far apart"):
        sum_combiner(2, weights=[1, 1e7])


def test_service_exposes_the_new_tool_and_runs_it(monkeypatch):
    from agent import service
    assert "parallel_difference" in service.available_functions
    assert "parallel_difference" in service.INTERNAL
    gen: list = []
    msg = service.execute_tool_call("parallel_sum", {"branches": [[LP, VF], [HP, VF], [*BAND, VF]]}, gen, [])
    assert msg.startswith("Generated 'parallel_sum'") and gen and gen[0]["circuit"] == "parallel_sum"
