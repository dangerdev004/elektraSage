import warnings

import numpy as np
import pytest

from agent.cascade import dump
from agent.cascade.compose import Stage, compose, verify
from agent.cascade.conformance import SAMPLES, generate, main as conformance_main
from agent.cascade.ports import ports_for
from agent.cascade.tool import (cascade as _public_cascade, parallel_sum as _public_parallel,
                                _cascade_impl as _cascade_tool, _parallel_impl as _parallel_tool)


def cascade(stages, **kw):                       # most tests look at the circuit exactly as asked
    kw.setdefault("auto_buffer", False)
    return _cascade_tool(stages, **kw)


def parallel_sum(branches, **kw):
    kw.setdefault("auto_buffer", False)
    return _parallel_tool(branches, **kw)


from agent.circuits import CIRCUIT_TOOLS
from tests.mna import solve

warnings.simplefilter("ignore")
HP = {"circuit": "rc_highpass", "args": {"cutoff_frequency": 100}}
LP = {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 5000}}
AMP = {"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000, "amp_supply": 15}}


def test_conformance_clean():
    assert conformance_main() == 0


@pytest.mark.parametrize("fn", [f for f in CIRCUIT_TOOLS if f.__name__ in SAMPLES],
                         ids=lambda f: f.__name__)
def test_every_generator_parses_and_roundtrips(fn):
    text = generate(fn, SAMPLES[fn.__name__])
    nl = dump.parse(text)
    assert dump.parse(nl.to_text()).to_text() == nl.to_text()
    if nl.dialect == "legacy":
        assert nl.to_text() == text          # byte-exact for the classic format


def test_three_stage_chain_structure():
    text, note = cascade([HP, LP, AMP])
    nl = dump.parse(text)
    assert sum(e.type in ("170", "v") for e in nl.elements) == 1   # one source only
    assert [e.type for e in nl.elements if e.type == "a"] == ["a"]
    for sc in nl.scopes:                                           # indices valid
        assert sc.index < len(nl.elements)
    assert "Stage 3: inverting_amp" in note and "op-amp output" in note


def test_scopes_follow_their_elements():
    text, _ = cascade([HP, LP, AMP])
    nl = dump.parse(text)
    types = [nl.elements[s.index].type for s in nl.scopes]
    assert types == ["170", "O", "O", "O"]


def test_stage_hints_are_dropped_in_a_cascade():
    # "h 3 r c" labels show the stage's UNLOADED -3 dB value; wrong in a loaded chain
    assert dump.parse(cascade([HP, LP])[0]).hints == []


def test_sweep_range_and_timestep_cover_all_stages():
    nl = dump.parse(cascade([HP, LP])[0])
    drv = next(e for e in nl.elements if e.type == "170")
    lo, hi = float(drv.tail[0]), float(drv.tail[1])
    assert lo < 100 / 5 and hi > 5000 * 5            # spans both cutoffs
    assert float(nl.header.split()[2]) <= 1 / (hi * 200) * 1.0001


def test_stage_internals_only_translated():
    from agent.circuits import rc_lowpass
    nl2 = dump.parse(cascade([HP, LP])[0])
    alone = dump.parse(rc_lowpass(5000))
    rs = [e for e in nl2.elements if e.type == "r"][1]
    r0 = next(e for e in alone.elements if e.type == "r")
    assert (rs.x2 - rs.x1, rs.y2 - rs.y1, rs.tail) == (r0.x2 - r0.x1, r0.y2 - r0.y1, r0.tail)


# ---- electrical cross-check with the independent solver -----------------
def _hp_lp_amp_expected(f, R1, C1, R2, C2, Rin, Rf):
    s = 2j * np.pi * f
    # nodes a (after C1), b (after R2); amp input loads b with Rin
    A = np.array([[s * C1 + 1 / R1 + 1 / R2, -1 / R2],
                  [-1 / R2, 1 / R2 + s * C2 + 1 / Rin]])
    va, vb = np.linalg.solve(A, np.array([s * C1, 0]))
    return -Rf / Rin * vb


def test_composed_circuit_matches_hand_derived_response():
    text, _ = cascade([HP, LP, AMP])
    nl = dump.parse(text)
    r = [float(e.tail[0]) for e in nl.elements if e.type == "r"]
    c = [float(e.tail[0]) for e in nl.elements if e.type == "c"]
    R1, R2, Rin, Rf = r[0], r[1], r[2], r[3]
    out = next(e for e in nl.elements if e.type == "a").p2
    for f in (10, 100, 1000, 4823, 20000):
        got = solve(text, f)["V"](out)
        want = _hp_lp_amp_expected(f, R1, c[0], R2, c[1], Rin, Rf)
        assert got == pytest.approx(want, rel=1e-9), f


# ---- structural check must actually catch problems ---------------------
def test_verify_flags_accidental_connection():
    from agent.cascade.dump import Element
    from agent.circuits import rc_lowpass
    mk = lambda t: dump.parse(t)
    a, b = mk(rc_lowpass(1000)).elements, mk(rc_lowpass(1000)).elements
    b = [e.moved(400, 0) for e in b]
    short = Element("w", 400, 160, 640, 160, "0")        # stage1 out -> stage2 in (intended)
    bad = Element("w", 400, 288, 800, 288, "0")          # ground-side shorts nets (unintended)
    assert verify([a, b], a + b + [short], [((400, 160), (640, 160))]) == []   # intended join
    assert verify([a, b], a + b, [((400, 160), (640, 160))]) != []             # join missing
    probs = verify([a, b], a + b + [short, bad], [((400, 160), (640, 160))])
    assert any("unintended" in p or "member" in p for p in probs)


# ---- roles, dialects, errors ------------------------------------------
def test_oscillator_first_then_filter():
    text, note = cascade([{"circuit": "rc_phaseshift", "args": {"frequency_hz": 1000}}, LP])
    assert "stage 1 itself" in note
    nl = dump.parse(text)
    assert sum(e.type == "a" for e in nl.elements) == 1


def test_source_in_the_middle_rejected():
    with pytest.raises(ValueError, match="only be the FIRST"):
        cascade([LP, {"circuit": "rc_phaseshift", "args": {"frequency_hz": 1000}}])


@pytest.fixture
def xml_circuit(monkeypatch):
    """No analog generator is XML any more, so fake one to keep the mixed-format guard tested."""
    from agent.cascade import tool as _tool
    xml = ('<cir f="1" ts="0.000005">\n  <R x="48 112 16 112" f="0" wf="1" maxv="5" fr="1000"/>\n'
           '  <r x="48 112 112 112" f="0" r="1000"/>\n  <O x="112 112 176 112" f="0" sc="0"/>\n</cir>\n')

    def fake_xml_circuit() -> tuple:
        """Fake XML-dialect circuit."""
        return xml, "fake"
    orig = _tool._generators
    monkeypatch.setattr(_tool, "_generators", lambda: {**orig(), "fake_xml_circuit": fake_xml_circuit})


def test_mixed_formats_rejected_with_clear_message(xml_circuit):
    with pytest.raises(ValueError, match="different CircuitJS file formats"):
        cascade([{"circuit": "fake_xml_circuit", "args": {}}, LP])


def test_digital_rejected():
    with pytest.raises(ValueError, match="digital"):
        cascade([LP, {"circuit": "binary_counter", "args": {"bits": 4}}])


def test_unknown_and_bad_args_are_retryable_errors():
    with pytest.raises(ValueError, match="unknown circuit"):
        cascade([LP, {"circuit": "nope", "args": {}}])
    with pytest.raises(ValueError, match="bad arguments"):
        cascade([LP, {"circuit": "rc_lowpass", "args": {"wrong": 1}}])
    with pytest.raises(ValueError, match="outside the supported range"):
        cascade([LP, {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 1e12}}])
    with pytest.raises(ValueError, match="at least 2"):
        cascade([LP])


def test_summing_amp_keeps_its_other_source():
    sa = {"circuit": "summing_amplifier", "args": {"gain_v_per_v": 1, "input1_frequency_hz": 1000,
                                                   "input2_frequency_hz": 100}}
    nl = dump.parse(cascade([LP, sa])[0])
    assert sum(e.type == "R" and e.tail[0] != "0" for e in nl.elements) == 1


def test_json_string_stages_accepted():
    import json
    assert cascade(json.dumps([HP, LP]))[0] == cascade([HP, LP])[0]


# ---- service plumbing ---------------------------------------------------
@pytest.fixture
def svc(tmp_path, monkeypatch):
    from agent import service
    monkeypatch.setattr(service, "OUTPUT_DIR", tmp_path)
    return service


def test_service_cascade_returns_fact_sheet_to_model(svc):
    gen = []
    msg = svc.execute_tool_call("cascade", {"stages": [HP, LP]}, gen)
    assert msg.startswith("Generated 'cascade'") and "Stage 2: rc_lowpass" in msg
    assert gen[0]["netlist"].startswith("$ ")


def test_service_handles_tuple_and_number_returns(svc):
    gen = []
    assert "returned" in svc.execute_tool_call("resistors_approximation", {"resistance": 4800}, gen)
    assert "Generated 'square_wave_generator'" in svc.execute_tool_call(
        "square_wave_generator", {}, gen)
    assert len(gen) == 1


def test_description_lists_required_and_optional_args():
    d = _public_cascade.__doc__
    assert "inverting_amp: REQUIRED gain, res; optional (have defaults): amp_supply=" in d
    assert "rc_lowpass: REQUIRED cutoff_frequency" in d
    assert "binary_counter" not in d and "resistors_approximation" not in d
    assert "do NOT ask the user about them" in d


# ---- B2: computed response + flags -----------------------------------------
from agent.cascade import analysis as an                       # noqa: E402
from agent.cascade.compose import Stage as _Stage, compose as _compose   # noqa: E402


def _stages(*specs):
    from agent.cascade.tool import _generators
    out = []
    for sp in specs:
        text = _generators()[sp["circuit"]](**sp["args"])
        nl = dump.parse(text)
        out.append(_Stage(sp["circuit"], sp["args"], nl, ports_for(sp["circuit"], nl)))
    return out


def _analyse(*specs):
    st = _stages(*specs)
    return an.analyse(st, _compose(st)), st


def test_rc_corner_is_minus_3db():
    a, st = _analyse(LP, {"circuit": "rc_highpass", "args": {"cutoff_frequency": 5000}})
    nl = st[0].nl
    drv = an.find_driver(nl)
    out = st[0].ports.outputs[0].node
    mags = [abs(v) for v in an._curve(nl, drv, drv.grid(), [out])[out]]
    m = an.metrics(drv.grid(), mags)
    assert m.hi == pytest.approx(4823, rel=0.01) and m.lo is None


def test_chain_response_matches_circuitjs_measurement():
    """CircuitJS showed Max = 11.538 V at the output for the 5 V sweep (user screenshot)."""
    text, _ = cascade([HP, LP, {"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000}}])
    nl = dump.parse(text)
    drv = an.find_driver(nl)
    sysm = an.System(nl, drv)
    out = next(e for e in nl.elements if e.type == "a").p2
    peak = max(abs(sysm.v(sysm.solve(f), out)) for f in drv.grid()
               if drv.sweep[0] <= f <= drv.sweep[1]) * drv.amp
    assert peak == pytest.approx(11.538, rel=0.005)


def test_flags_name_loading_and_corner_shift():
    a, _ = _analyse(HP, LP, {"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000}})
    assert a.supported
    joined = " | ".join(a.flags)
    assert "2.31" in joined and "the stages on their own would give 10" in joined
    assert "lower -3 dB corner is 135Hz" in joined and "upper -3 dB corner is 21kHz" in joined
    assert "stage 3 loads stage 2" in joined and "stage 3 loads stage 2" in joined
    assert not any("clip" in f for f in a.flags)          # +/-50 V default: 11.5 V is fine


def test_clipping_flags_follow_the_op_amp_limit():
    def amp(sup):
        return {"circuit": "inverting_amp",
                "args": {"gain": 10, "res": 10000, "amp_supply": sup}}
    assert any("would clip" in f for f in _analyse(HP, LP, amp(10))[0].flags)
    assert any("within 10%" in f for f in _analyse(HP, LP, amp(12))[0].flags)
    real = [f for f in _analyse(HP, LP, amp(50))[0].flags if not f.startswith("Headroom if")]
    assert not any("clip" in f or "10%" in f for f in real)
    # ...but the headroom that fixing the loading would cost IS flagged
    assert any(f.startswith("Headroom if the loading were removed")
               for f in _analyse(HP, LP, amp(50))[0].flags)


def test_benign_chain_raises_no_flags():
    # op-amp output is low impedance, so the RC after it loads nothing
    a, _ = _analyse({"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000, "amp_supply": 15}},
                    {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 5000}})
    assert a.supported and a.flags == []


def test_generator_first_is_reported_not_analysed(monkeypatch):
    from agent.cascade import oscillators
    monkeypatch.setattr(oscillators, "OSCILLATORS", oscillators.OSCILLATORS - {"rc_phaseshift"})
    a, _ = _analyse({"circuit": "rc_phaseshift", "args": {"frequency_hz": 1000}}, LP)
    assert not a.supported and "NOT ANALYSED" in a.to_text()


def test_summing_amp_stage_is_analysable():
    sa = {"circuit": "summing_amplifier", "args": {"gain_v_per_v": 1, "input1_frequency_hz": 1000,
                                                   "input2_frequency_hz": 100}}
    a, _ = _analyse(LP, sa)
    assert a.supported and a.lines


def test_fact_sheet_has_merged_sweep_and_computed_block():
    _, note = cascade([HP, LP])
    assert "frequency sweep 9.947-48.23k Hz" in note.split("Stage 1")[0]
    assert "Computed response of the whole chain" in note


def test_analysis_failure_never_breaks_the_cascade(monkeypatch):
    import agent.cascade.tool as tool

    def boom(*a, **k):
        raise RuntimeError("kaput")
    monkeypatch.setattr(tool, "analyse", boom)
    text, note = cascade([HP, LP])
    assert text.startswith("$") and "NOT ANALYSED" in note and "kaput" in note


def test_sloping_responses_do_not_invent_corners():
    integ = {"circuit": "integrator", "args": {"gain_v_per_v": 1, "input_resistor_ohms": 10000}}
    a, _ = _analyse(integ, LP)
    assert a.supported
    txt = a.to_text()
    assert "sloping" in txt and "not meaningful" in txt
    assert not any("-3 dB corner" in f or "passband gain" in f for f in a.flags)


# ---- C: buffered what-if + available fixes ----------------------------------
AMP10 = {"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000}}


def test_buffered_what_if_matches_analytic_product():
    text, note = cascade([HP, LP, AMP10])
    nl = dump.parse(text)
    R = [float(e.tail[0]) for e in nl.elements if e.type == "r"]
    C = [float(e.tail[0]) for e in nl.elements if e.type == "c"]
    f = np.logspace(0, 6, 5000)
    s_ = 2j * np.pi * f
    H = (s_ * R[0] * C[0] / (1 + s_ * R[0] * C[0])) * (1 / (1 + s_ * R[1] * C[1])) * (R[3] / R[2])
    mag = np.abs(H)
    pk = mag.max()
    thr = pk / np.sqrt(2)
    lo, hi = f[np.argmax(mag >= thr)], f[len(f) - 1 - np.argmax(mag[::-1] >= thr)]
    line = next(l for l in note.splitlines() if l.strip().startswith("What-if"))
    got_gain = float(line.split("passband gain ")[1].split()[0])
    assert got_gain == pytest.approx(pk, rel=0.01)
    a, _ = _analyse(HP, LP, AMP10)
    txt = a.to_text()
    assert "-3 dB band 95.6Hz to 5.02kHz" in txt                    # solver
    assert lo == pytest.approx(95.6, rel=0.02) and hi == pytest.approx(5020, rel=0.02)   # analytic


def test_what_if_reports_headroom_cost_of_the_fix():
    a, _ = _analyse(HP, LP, AMP10)                                   # +/-50 V rails
    assert "op-amp in stage 3 would peak at 49V vs +/-50V limit - within 10% of the limit" in a.to_text()
    amp15 = {"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000, "amp_supply": 15}}
    assert "it WOULD CLIP" in _analyse(HP, LP, amp15)[0].to_text()


def test_no_what_if_when_nothing_is_loaded():
    a, _ = _analyse({"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000, "amp_supply": 15}},
                    {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 5000}})
    assert "What-if" not in a.to_text()


def test_sheet_says_no_buffer_when_none_registered_and_names_it_when_one_is(monkeypatch):
    import agent.cascade.tool as tool
    real = tool._generators
    monkeypatch.setattr(tool, "_generators",
                        lambda: {k: v for k, v in real().items() if k != "voltage_follower"})
    _, note = cascade([HP, LP])
    assert "NONE for loading" in note and "Do not offer" in note
    monkeypatch.setattr(tool, "_generators", real)
    _, note = cascade([HP, LP])
    assert "Automatic fixes available through your tools: voltage_follower" in note


# ---- scope fix + code-written reply (option 1) ------------------------------------

def _scale(netlist, elem_index):
    for l in netlist.splitlines():
        t = l.split()
        if t[0] == "o" and int(t[1]) == elem_index:
            return float(t[5])


def test_output_scope_scale_follows_computed_peak():
    nl, _ = cascade([{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 1000}},
                     {"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000}}])
    lines = [l for l in nl.splitlines() if l and l.split()[0] not in "o%$"]
    last_o = max(i for i, l in enumerate(lines) if l.startswith("O "))
    s = _scale(nl, last_o)
    assert 19.2 / 2.5 <= s <= 19.2 and s != 0.01      # was 0.01 (1 mV leftover)
    assert _scale(nl, 0) == 5.0                        # source scope untouched


def test_reply_is_code_written_and_matches_numbers():
    _, sheet = cascade([{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 1000}},
                        {"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000}}])
    r = sheet.reply
    assert "3.85" in r and "0.38x" in r and "Written by code" in r
    assert "Fix with a buffer" in r and "`res`" in r         # real, checked fixes
    assert "Do not offer" not in r


def test_reply_clean_chain_has_no_flags_and_no_fix():
    _, sheet = cascade([{"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000}},
                        {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 5000}}])
    assert "nothing worth flagging" in sheet.reply and "A fix you can make now" not in sheet.reply


def test_reply_never_offers_buffer_when_none_registered():
    _, sheet = cascade([{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 1000}},
                        {"circuit": "summing_amplifier", "args": {
                            "gain_v_per_v": 1, "input1_frequency_hz": 1000,
                            "input2_frequency_hz": 100}}])
    r = sheet.reply
    assert "Fix with a buffer" in r or "no automatic fix" in r.lower() or "can't add a buffer" in r


def test_reply_for_unanalysed_chain_is_honest(monkeypatch):
    from agent.cascade import oscillators
    monkeypatch.setattr(oscillators, "OSCILLATORS", oscillators.OSCILLATORS - {"rc_phaseshift"})
    _, sheet = cascade([{"circuit": "rc_phaseshift", "args": {"frequency_hz": 1000}},
                        {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 2000}}])
    assert "couldn't be computed" in sheet.reply


def test_run_turn_uses_code_reply_for_cascade_and_skips_model_prose(svc, monkeypatch):
    from types import SimpleNamespace as NS
    calls = []

    def fake_chat(**kw):
        calls.append(1)
        tc = NS(function=NS(name="cascade", arguments={"stages": [
            {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 1000}},
            {"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000}}]}))
        return NS(message=NS(content="MODEL PROSE THAT MUST NOT APPEAR", tool_calls=[tc]))

    monkeypatch.setattr(svc, "client", NS(chat=fake_chat))
    text, gen = svc.run_turn(svc.new_conversation() + [{"role": "user", "content": "x"}])
    assert len(calls) == 1                                # no second model call
    assert "MODEL PROSE" not in text and "Written by code" in text
    assert gen[0]["circuit"] == "cascade" and "Saved to" in text


def test_run_turn_single_circuit_is_now_code_written(svc, monkeypatch):
    from types import SimpleNamespace as NS
    calls = []

    def chat(**kw):
        calls.append(1)
        return NS(message=NS(content="MODEL PROSE", tool_calls=[NS(function=NS(
            name="rc_lowpass", arguments={"cutoff_frequency": 1000}))]))

    monkeypatch.setattr(svc, "client", NS(chat=chat))
    text, gen = svc.run_turn(svc.new_conversation() + [{"role": "user", "content": "x"}])
    assert len(calls) == 1 and "MODEL PROSE" not in text
    assert "Here's your RC low-pass filter (cutoff_frequency 1000)" in text
    assert "16k\u03a9 resistor" in text and "10nF capacitor" in text and "rolls off above 995Hz" in text
    assert "One thing to know" in text and "994.7" in text      # the generator's own warning
    assert "Written by code" in text and "Saved to" in text


# ---- v1.6: claim-without-tool guard -------------------------------------------------

def _fake(svc, monkeypatch, replies):
    from types import SimpleNamespace as NS
    seen = []
    it = iter(replies)

    def chat(**kw):
        seen.append([m if isinstance(m, dict) else m for m in kw["messages"]])
        content, calls = next(it)
        tcs = [NS(function=NS(name=n, arguments=a)) for n, a in calls] if calls else None
        return NS(message=NS(content=content, tool_calls=tcs))

    monkeypatch.setattr(svc, "client", NS(chat=chat))
    return seen


CASCADE_CALL = ("cascade", {"stages": [
    {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 1000}},
    {"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000}}]})


def test_claim_without_tool_is_nudged_then_built(svc, monkeypatch):
    _fake(svc, monkeypatch, [("Your cascade has been generated.", None),
                              ("", [CASCADE_CALL])])
    msgs = svc.new_conversation() + [{"role": "user", "content": "x"}]
    text, gen = svc.run_turn(msgs)
    assert "chained them" in text and "has been generated" not in text and gen
    assert not any(isinstance(m, dict) and m.get("content") == svc.NUDGE for m in msgs)


def test_claim_after_nudge_gets_a_warning(svc, monkeypatch):
    _fake(svc, monkeypatch, [("Your cascade has been generated.", None),
                              ("Here is your circuit.", None)])
    text, gen = svc.run_turn(svc.new_conversation() + [{"role": "user", "content": "x"}])
    assert not gen and "no circuit was produced" in text


def test_clarifying_question_is_left_alone(svc, monkeypatch):
    seen = _fake(svc, monkeypatch, [("What cutoff frequency do you want?", None)])
    text, gen = svc.run_turn(svc.new_conversation() + [{"role": "user", "content": "x"}])
    assert text == "What cutoff frequency do you want?" and len(seen) == 1


def test_failed_tool_then_claim_warns_without_nudging(svc, monkeypatch):
    bad = ("cascade", {"stages": [{"circuit": "nope", "args": {}}, {"circuit": "rc_lowpass", "args": {}}]})
    seen = _fake(svc, monkeypatch, [("", [bad]), ("The circuit has been created.", None)])
    text, gen = svc.run_turn(svc.new_conversation() + [{"role": "user", "content": "x"}])
    assert not gen and "no circuit was produced" in text and len(seen) == 2


def test_already_generated_pointing_at_old_file_is_caught(svc, monkeypatch):
    stale = ("The requested cascade has already been generated:\n\nThe circuit file is saved "
             "as `output/cascade_old.txt`. Let me know if you'd like adjustments.")
    _fake(svc, monkeypatch, [(stale, None), ("", [CASCADE_CALL])])
    text, gen = svc.run_turn(svc.new_conversation() + [{"role": "user", "content": "x"}])
    assert gen and "chained them" in text and "already been generated" not in text


def test_claim_patterns_do_not_match_ordinary_questions():
    from agent.service import _CLAIM
    for ok in ("What cutoff frequency do you want?", "I need the gain and the input resistor.",
               "Which supply voltage should the op-amp use?"):
        assert not _CLAIM.search(ok)
    for bad in ("It has already been built.", "The file is saved as x.", "Cascade has been created."):
        assert _CLAIM.search(bad)


# ---- v1.7+: option 2 (every successful tool call) ---------------------------------

def test_number_tools_get_code_replies(svc, monkeypatch):
    from types import SimpleNamespace as NS
    monkeypatch.setattr(svc, "client", NS(chat=lambda **kw: NS(message=NS(
        content="", tool_calls=[NS(function=NS(name="resistors_approximation",
                                               arguments={"resistance": 4800}))]))))
    text, gen = svc.run_turn(svc.new_conversation() + [{"role": "user", "content": "x"}])
    assert "4.7k\u03a9" in text and "E24" in text and not gen


def test_555_note_and_xml_format_are_reported(svc):
    entry, canned = [], []
    svc.execute_tool_call("monostable_555_generator", {}, entry, canned)
    assert canned and "Note from the generator" in canned[0] and "1.1 s" in canned[0]


def test_every_registered_circuit_gets_a_code_reply_or_a_clean_fallback(svc):
    # whatever a generator returns, the reply builder must not raise
    from agent.cascade.conformance import SAMPLES
    for name, args in SAMPLES.items():
        gen, canned = [], []
        out = svc.execute_tool_call(name, dict(args), gen, canned)
        assert canned and "Written by code" in canned[0], (name, out)


def test_tool_errors_still_go_to_the_model(svc, monkeypatch):
    from types import SimpleNamespace as NS
    seq = iter([
        NS(message=NS(content="", tool_calls=[NS(function=NS(name="rc_lowpass", arguments={}))])),
        NS(message=NS(content="What cutoff frequency do you want?", tool_calls=None)),
    ])
    monkeypatch.setattr(svc, "client", NS(chat=lambda **kw: next(seq)))
    text, gen = svc.run_turn(svc.new_conversation() + [{"role": "user", "content": "x"}])
    assert text == "What cutoff frequency do you want?" and not gen


def test_partial_failure_keeps_the_code_reply(svc, monkeypatch):
    from types import SimpleNamespace as NS
    seq = iter([
        NS(message=NS(content="", tool_calls=[
            NS(function=NS(name="rc_lowpass", arguments={"cutoff_frequency": 1000})),
            NS(function=NS(name="rc_highpass", arguments={}))])),
        NS(message=NS(content="The high-pass needs a cutoff frequency.", tool_calls=None)),
    ])
    monkeypatch.setattr(svc, "client", NS(chat=lambda **kw: next(seq)))
    text, gen = svc.run_turn(svc.new_conversation() + [{"role": "user", "content": "x"}])
    assert "Here's your RC low-pass filter" in text and "needs a cutoff" in text


# ---- v1.5 tests restored, in the chat wording -------------------------------------

LP_AMP = [{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 1000}},
          {"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000}}]


def test_fix_restores_expected_gain_and_says_what_it_changed():
    r = cascade(LP_AMP)[1].reply
    assert "`res`" in r and "`gain`" in r and "bring the chain gain toward 10" in r
    assert "After that change" in r


def test_loading_flag_no_longer_offers_a_buffer():
    r = cascade(LP_AMP)[1].reply
    flag = [l for l in r.splitlines() if "loads stage" in l][0]
    assert "buffer" not in flag


def test_headroom_cost_of_fixing_loading_is_a_flag():
    r = cascade(LP_AMP)[1].reply
    assert "Headroom if the loading were removed" in r.split("**A fix")[0]


def test_replies_read_as_chat_not_as_a_spec_sheet():
    from agent.cascade.tool import render_single
    r = cascade(LP_AMP)[1].reply
    assert r.startswith("I've chained them into one circuit")
    assert "**Computed response**" not in r and "Driven by" not in r
    s = render_single("rc_lowpass", {"cutoff_frequency": 1000},
                      __import__("agent.circuits", fromlist=["x"]).rc_lowpass(1000), None, [])
    assert s.startswith("Here's your RC low-pass filter") and "- parts:" not in s


# ---- A: polish --------------------------------------------------------------------

def _no_buffer(monkeypatch):
    import agent.cascade.tool as tool
    real = tool._generators
    monkeypatch.setattr(tool, "_generators",
                        lambda: {k: v for k, v in real().items() if k != "voltage_follower"})


def test_impractical_fix_is_refused_with_a_reason(monkeypatch):
    _no_buffer(monkeypatch)
    r = cascade([{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 2000}},
                 {"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000}}])[1].reply
    assert "can't fix this sensibly" in r and "A fix you can make now" not in r


def test_practical_fix_is_still_offered(monkeypatch):
    _no_buffer(monkeypatch)
    r = cascade(LP_AMP)[1].reply
    assert "A fix you can make now" in r


def test_flags_are_plain_language_with_labels():
    r = cascade(LP_AMP)[1].reply
    for label in ("- Gain:", "- Cutoff:", "- Loading:", "- Headroom if the loading were removed:"):
        assert label in r
    assert "differs from the product" not in r


def test_short_replies_have_no_long_footer():
    from agent.cascade.tool import render_number
    assert "language model" not in render_number("resistors_approximation", {"resistance": 4800}, 4700)


# ---- B: voltage follower -----------------------------------------------------------

def test_voltage_follower_is_registered_and_equals_non_inverting_gain_1():
    from agent.circuits import CIRCUIT_TOOLS, non_inverting_amp, voltage_follower
    assert voltage_follower in CIRCUIT_TOOLS
    assert voltage_follower() == non_inverting_amp(1.0)


def test_buffer_between_stages_removes_the_loading_and_restores_the_gain():
    S = lambda c, **a: {"circuit": c, "args": a}
    nl, sheet = cascade([S("rc_lowpass", cutoff_frequency=1000), S("voltage_follower"),
                         S("inverting_amp", gain=10, res=10000)])
    r = sheet.reply
    assert "gain of about 10" in r and "995Hz" in r
    assert "- Loading:" not in r and "- Gain:" not in r
    assert "Fix with a buffer" not in r                    # nothing left to fix


def test_reply_inserts_and_verifies_a_buffer_fix():
    r = cascade(LP_AMP)[1].reply
    assert "**Fix with a buffer:**" in r and "voltage follower" in r
    assert "To build it, ask for:" in r and "then voltage follower, then inverting amplifier" in r


def test_buffer_fix_replaces_the_impractical_resistor_advice():
    r = cascade([{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 2000}},
                 {"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000}}])[1].reply
    assert "Fix with a buffer" in r and "can't fix this sensibly" not in r and "5.8" not in r


def test_without_a_buffer_circuit_the_reply_says_it_cannot_add_one(monkeypatch):
    _no_buffer(monkeypatch)
    r = cascade(LP_AMP)[1].reply
    assert "I can't add a buffer for you" in r and "Fix with a buffer" not in r


def test_follower_single_circuit_reply():
    import agent.service as svc_mod
    entry, canned = [], []
    svc_mod.execute_tool_call("voltage_follower", {}, entry, canned)
    assert canned and "voltage follower" in canned[0] and "passband gain of about 1" in canned[0]


def test_a_reply_writing_bug_never_loses_the_circuit(monkeypatch):
    import agent.cascade.tool as tool
    monkeypatch.setattr(tool, "_render_reply", lambda *a, **k: 1 / 0)
    nl, sheet = cascade(LP_AMP)
    assert nl.startswith("$ ") and "couldn't write the detailed summary" in sheet.reply


def test_every_composable_pair_gets_a_full_reply():
    """Sweep: no ordered pair of registered circuits may hit the reply fallback or crash."""
    from agent.cascade.conformance import SAMPLES
    from agent.cascade.tool import NOT_CASCADABLE, NOT_CIRCUITS, _generators
    names = [n for n in _generators() if n not in NOT_CIRCUITS | NOT_CASCADABLE]
    built = 0
    for a in names:
        for b in names:
            try:
                r = cascade([{"circuit": a, "args": SAMPLES[a]},
                             {"circuit": b, "args": SAMPLES[b]}])[1].reply
            except ValueError:
                continue                                  # refused on purpose (format/role)
            built += 1
            assert "couldn't write the detailed summary" not in r, (a, b)
    assert built >= 100


def test_no_floating_ground_is_left_behind_by_a_dropped_source():
    """The follower's only ground belonged to its source; once the source is dropped
    that ground must go too (it showed up floating in CircuitJS)."""
    from agent.cascade.conformance import SAMPLES
    from agent.cascade.dump import terminals
    from agent.cascade.tool import NOT_CASCADABLE, NOT_CIRCUITS, _generators
    names = [n for n in _generators() if n not in NOT_CIRCUITS | NOT_CASCADABLE]
    checked = 0
    for a in names:
        for b in names:
            try:
                nl = dump.parse(cascade([{"circuit": a, "args": SAMPLES[a]},
                                         {"circuit": b, "args": SAMPLES[b]}])[0])
            except ValueError:
                continue
            if nl.dialect != "legacy":
                continue
            els = nl.elements
            for i, e in enumerate(els):
                if e.type == "g":
                    assert any(j != i and e.p1 in (terminals(x) or []) for j, x in enumerate(els)), \
                        (a, b, e.p1)
            checked += 1
    assert checked >= 80


# ---- C: two parallel branches summed ----------------------------------------------------

def _S(c, **a):
    return {"circuit": c, "args": a}


LP1K = _S("rc_lowpass", cutoff_frequency=1000)
HP100 = _S("rc_highpass", cutoff_frequency=100)


def test_parallel_structure_is_clean_and_has_one_source():
    nl_text, _ = parallel_sum([[LP1K], [HP100]])
    nl = dump.parse(nl_text)
    sources = [e for e in nl.elements if e.type in ("170", "v", "R")]
    assert len(sources) == 1 and sources[0].type == "170"            # one source drives both
    assert sum(1 for e in nl.elements if e.type == "a") == 1          # just the summing op-amp


def test_parallel_matches_the_independent_solver():
    import numpy as np
    from agent.cascade.analysis import System, find_driver
    text, _ = parallel_sum([[LP1K], [HP100]])
    nl = dump.parse(text)
    drv = find_driver(nl)
    sysm = System(nl, drv)
    out = [(e.x1, e.y1) for e in nl.elements if e.type == "O"][-1]
    for f in (50.0, 500.0, 3000.0):
        a = abs(sysm.v(sysm.solve(f), out))
        b = abs(solve(text, f)["V"](out))
        assert np.isclose(a, b, rtol=1e-6), (f, a, b)


def test_parallel_flags_loading_and_buffer_fix_is_verified():
    _, sheet = parallel_sum([[LP1K], [HP100]])
    r = sheet.reply
    assert "Loading: the combiner loads branch 1" in r and "Loading: the combiner loads branch 2" in r
    assert "**Fix with a buffer:**" in r and "voltage follower" in r and "nothing else is flagged" in r
    assert "path 1: RC low-pass filter" in r                         # says how to ask for it


def test_buffered_parallel_has_no_loading_and_gain_near_two():
    from agent.cascade.tool import _build_parallel
    br = [[LP1K, _S("voltage_follower")], [HP100, _S("voltage_follower")]]
    *_, an = _build_parallel(br, 1.0)
    assert an.supported and not an.loaded and 1.6 < an.gain < 2.05    # LP + HP in the mid band ~ 2


def test_multi_stage_branches_build_and_stay_clean():
    from agent.cascade.tool import _build_parallel
    br = [[LP1K, LP1K], [HP100]]
    *_, par, an = _build_parallel(br, 1.0)
    assert not par.problems and an.supported


def test_parallel_refusals():
    with pytest.raises(ValueError, match="exactly TWO"):
        parallel_sum([[LP1K]])
    with pytest.raises(ValueError, match="takes no signal input"):
        parallel_sum([[_S("rc_phaseshift", frequency_hz=1000)], [HP100]])
    with pytest.raises(ValueError, match="digital"):
        parallel_sum([[LP1K], [_S("binary_counter", bits=4)]])
    with pytest.raises(ValueError, match="takes no signal input"):
        parallel_sum([[LP1K], [_S("square_wave_generator")]])


def test_parallel_accepts_json_text_and_reply_is_chatty():
    import json
    _, sheet = parallel_sum(json.dumps([[LP1K], [HP100]]))
    assert sheet.reply.startswith("I've split the input into two parallel paths")
    assert "Path 1:" in sheet.reply and "Written by code" in sheet.reply


def test_parallel_output_scopes_follow_computed_peaks():
    text, _ = parallel_sum([[LP1K], [HP100]])
    nl = dump.parse(text)
    o_scopes = [float(sc.tail[3]) for sc in nl.scopes if nl.elements[sc.index].type == "O"]
    assert o_scopes and all(v > 0 for v in o_scopes)
    assert 0.2 < o_scopes[-1] < 20


def test_no_floating_ground_in_parallel_circuits():
    from agent.cascade.dump import terminals
    for br in ([[LP1K], [HP100]], [[HP100], [LP1K]], [[_S("inverting_amp", gain=10, res=10000)], [LP1K]]):
        nl = dump.parse(parallel_sum(br)[0])
        els = nl.elements
        for i, e in enumerate(els):
            if e.type == "g":
                assert any(j != i and e.p1 in (terminals(x) or []) for j, x in enumerate(els)), br


def test_op_amp_branch_goes_below_so_its_input_is_reachable():
    from agent.cascade.tool import _build_parallel
    *_, par, an = _build_parallel([[_S("inverting_amp", gain=10, res=10000)], [LP1K]], 1.0)
    assert not par.problems and an.supported


def test_every_composable_parallel_pair_gets_a_full_reply():
    from agent.cascade.conformance import SAMPLES
    from agent.cascade.tool import NOT_CASCADABLE, NOT_CIRCUITS, _generators
    names = [n for n in _generators() if n not in NOT_CIRCUITS | NOT_CASCADABLE]
    built = 0
    for a in names:
        for b in names:
            try:
                r = parallel_sum([[_S(a, **SAMPLES[a])], [_S(b, **SAMPLES[b])]])[1].reply
            except ValueError:
                continue
            built += 1
            assert "couldn't write the detailed summary" not in r, (a, b)
    assert built >= 60


def test_service_runs_parallel_sum_and_uses_the_code_reply(svc, monkeypatch):
    from types import SimpleNamespace as NS
    calls = []

    def chat(**kw):
        calls.append(1)
        return NS(message=NS(content="MODEL PROSE", tool_calls=[NS(function=NS(
            name="parallel_sum", arguments={"branches": [[LP1K], [HP100]]}))]))

    monkeypatch.setattr(svc, "client", NS(chat=chat))
    text, gen = svc.run_turn(svc.new_conversation() + [{"role": "user", "content": "x"}])
    assert len(calls) == 1 and "MODEL PROSE" not in text
    assert "I've split the input" in text and gen and gen[0]["circuit"] == "parallel_sum"
    assert "parallel_sum" in svc.available_functions


# ---- v1.14: wording, note order, remembered buffer fix ----------------------------------

def test_band_pass_says_peak_gain_but_low_pass_keeps_passband_gain():
    buffered = [[LP1K, _S("voltage_follower")], [HP100, _S("voltage_follower")]]
    r = parallel_sum(buffered)[1].reply
    assert "band-pass response with a peak gain of about" in r and "passband gain" not in r
    r2 = cascade([{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 1000}},
                  {"circuit": "voltage_follower", "args": {}}])[1].reply
    assert "passband gain of about" in r2


def test_rounding_notes_come_after_the_result():
    for r in (parallel_sum([[LP1K], [HP100]])[1].reply,
              cascade(LP_AMP)[1].reply):
        if "One thing to know" in r:
            assert r.index("One thing to know") > r.index("Overall")
            assert r.index("One thing to know") < r.index("Not modelled")


def test_fix_call_is_offered_only_when_a_fix_exists():
    fx = parallel_sum([[LP1K], [HP100]])[1].fix_call
    assert fx and fx[0] == "parallel_sum" and all(b[-1]["circuit"] == "voltage_follower" for b in fx[1]["branches"])
    assert parallel_sum([[LP1K, _S("voltage_follower")], [HP100, _S("voltage_follower")]])[1].fix_call is None
    cf = cascade([{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 2000}},
                  {"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000}}])[1].fix_call
    assert cf and cf[0] == "cascade" and any(s["circuit"] == "voltage_follower" for s in cf[1]["stages"])


def _as_asked(svc, monkeypatch):
    """Service tools that behave as before v1.15 (no automatic buffering)."""
    monkeypatch.setitem(svc.available_functions, "cascade", lambda **kw: _cascade_tool(auto_buffer=False, **kw))
    monkeypatch.setitem(svc.available_functions, "parallel_sum",
                        lambda **kw: _parallel_tool(auto_buffer=False, **kw))


def test_apply_fix_rebuilds_with_the_remembered_arguments(svc, monkeypatch):
    _as_asked(svc, monkeypatch)
    conv = svc.new_conversation()
    tok = svc._CURRENT.set(conv)
    try:
        gen, canned = [], []
        svc.execute_tool_call("parallel_sum", {"branches": [[LP1K], [HP100]]},
                              gen, canned)
        assert conv.pending_fix and "apply the buffer fix" in canned[0]
        gen2, canned2 = [], []
        msg = svc.execute_tool_call("apply_fix", {}, gen2, canned2)
        assert msg.startswith("Generated 'parallel_sum'")
        assert gen2[0]["circuit"] == "parallel_sum" and gen2[0]["netlist"].count("\na ") == 3
        assert "band-pass response with a peak gain of about 1.8" in canned2[0] and "Loading" not in canned2[0]
        assert conv.pending_fix is None                               # fix used up
        again = svc.execute_tool_call("apply_fix", {}, [], [])
        assert again.startswith("Error: there is nothing to apply")
    finally:
        svc._CURRENT.reset(tok)


def test_apply_fix_without_a_session_or_offer_is_an_error(svc):
    assert svc.execute_tool_call("apply_fix", {}, [], []).startswith("Error: there is nothing to apply")


def test_fix_follows_a_cascade_too_and_run_turn_uses_it(svc, monkeypatch):
    _as_asked(svc, monkeypatch)
    from types import SimpleNamespace as NS
    seq = iter([
        NS(message=NS(content="", tool_calls=[NS(function=NS(name="cascade", arguments={"stages": [
            {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 2000}},
            {"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000}}]}))])),
        NS(message=NS(content="MODEL PROSE", tool_calls=[NS(function=NS(name="apply_fix", arguments={}))])),
    ])
    monkeypatch.setattr(svc, "client", NS(chat=lambda **kw: next(seq)))
    conv = svc.new_conversation()
    conv.append({"role": "user", "content": "rc low-pass 2k then inverting amp x10"})
    t1, g1 = svc.run_turn(conv)
    assert "Fix with a buffer" in t1 and conv.pending_fix
    conv.append({"role": "user", "content": "apply the buffer fix"})
    t2, g2 = svc.run_turn(conv)
    assert "MODEL PROSE" not in t2 and "Fix with a buffer" not in t2
    assert g2 and g2[0]["circuit"] == "cascade" and "voltage_follower" in str(g2[0]["arguments"])


# ---- v1.15: severe loading is buffered automatically, announced, and can be undone --------

def test_severe_loading_is_buffered_by_default_and_says_so():
    r = _parallel_tool([[LP1K], [HP100]])[1].reply
    assert r.startswith("As asked, the combiner would load the paths badly")
    assert "build it without the buffers" in r and "Loading: the combiner loads branch 1" in r
    assert "band-pass response with a peak gain of about 1.8" in r and "Fix with a buffer" not in r


def test_auto_buffer_false_gives_the_circuit_as_asked():
    r = _parallel_tool([[LP1K], [HP100]], auto_buffer=False)[1].reply
    assert not r.startswith("As asked") and "Fix with a buffer" in r


def test_mild_loading_is_not_changed_behind_the_users_back():
    from agent.cascade.tool import _build_parallel, _severe
    *_, an_ = _build_parallel([[LP1K], [HP100]], 1.0)
    assert _severe(an_)                                    # 0.06x: severe
    an_.worst_load = 0.8
    assert not _severe(an_)                                # 0.8x: flagged at most, never auto-changed


def test_auto_cascade_buffer_matches_the_manual_one():
    spec = [{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 2000}},
            {"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000}}]
    auto_nl, sheet = _cascade_tool(spec)
    manual_nl, _ = _cascade_tool([spec[0], {"circuit": "voltage_follower", "args": {"amp_supply": 50.0}}, spec[1]],
                                 auto_buffer=False)
    assert sheet.reply.startswith("As asked, this chain would be badly loaded")
    assert sheet.alt_call and sheet.alt_call[1]["auto_buffer"] is False
    assert auto_nl.count("\na ") == manual_nl.count("\na ") == 2


def test_added_buffer_takes_the_op_amp_limit_of_the_circuit():
    nl, sheet = _parallel_tool([[LP1K], [HP100]])
    limits = {float(l.split()[6]) for l in nl.splitlines() if l.startswith("a ")}
    assert limits == {15.0}                                # summer's +/-15 V, followers matched to it
    assert "amp_supply 15" in sheet.reply or "amp_supply" in sheet.reply


def test_build_without_buffers_returns_the_loaded_circuit_and_clears(svc):
    conv = svc.new_conversation()
    tok = svc._CURRENT.set(conv)
    try:
        gen, canned = [], []
        svc.execute_tool_call("parallel_sum", {"branches": [[LP1K], [HP100]]}, gen, canned)
        assert conv.pending_alt and gen[0]["netlist"].count("\na ") == 3
        gen2, canned2 = [], []
        msg = svc.execute_tool_call("build_without_buffers", {}, gen2, canned2)
        assert msg.startswith("Generated 'parallel_sum'") and gen2[0]["netlist"].count("\na ") == 1
        assert "Fix with a buffer" in canned2[0] and conv.pending_alt is None
        assert svc.execute_tool_call("build_without_buffers", {}, [], []).startswith("Error: there is nothing to undo")
    finally:
        svc._CURRENT.reset(tok)


# ---- v1.16: headroom fix -----------------------------------------------------------------

LP2K_AMP10 = [{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 2000}},
              {"circuit": "inverting_amp", "args": {"gain": 10, "res": 10000}}]


def test_headroom_fix_is_offered_and_verified():
    sheet = _cascade_tool(LP2K_AMP10)[1]
    assert "**Fix for the headroom:** lower the source from 5V to 2V" in sheet.reply
    assert "nothing else is flagged" in sheet.reply and 'say "apply the fix"' in sheet.reply
    name, args = sheet.fix_call
    assert name == "cascade" and args["source_amplitude"] == 2.0


def test_applying_the_headroom_fix_clears_the_flag_and_keeps_the_response():
    from agent.cascade.tool import _build
    first = _cascade_tool(LP2K_AMP10)[1]
    _, args = first.fix_call
    nl, sheet = _cascade_tool(**args)
    assert "Headroom" not in sheet.reply.split("One thing to know")[0] and sheet.fix_call is None
    src = [l for l in nl.splitlines() if l.startswith("170 ")][0].split()
    assert float(src[8]) == 2.0                                    # sweep amplitude
    *_, a_new = _build(args["stages"], 2.0)
    *_, a_old = _build(args["stages"], 5.0)
    assert a_new.headroom == [] and a_old.headroom
    assert abs(a_new.gain - a_old.gain) < 1e-9 and a_new.lo == a_old.lo and a_new.hi == a_old.hi


def test_headroom_fix_scales_peaks_and_source_scope_linearly():
    from agent.cascade.tool import _build
    stg = _cascade_tool(LP2K_AMP10)[1].fix_call[1]["stages"]
    *_, a5 = _build(stg, 5.0)
    *_, a2 = _build(stg, 2.0)
    for k, v in a5.node_peaks.items():
        assert abs(a2.node_peaks[k] - v * 0.4) < 1e-9 * max(1, v)


def test_no_headroom_fix_when_nothing_is_flagged():
    assert cascade([LP, {"circuit": "voltage_follower", "args": {}}, HP])[1].fix_call is None


def test_clipping_in_parallel_gets_a_verified_source_fix():
    sheet = _parallel_tool([[LP1K], [HP100]], gain_v_per_v=3)[1]
    assert "**Fix for the clipping:**" in sheet.reply and "estimated output peak" not in sheet.reply
    name, args = sheet.fix_call
    assert name == "parallel_sum" and args["source_amplitude"] == 1.0
    sheet2 = _parallel_tool(args["branches"], gain_v_per_v=3, source_amplitude=1.0)[1]
    assert "Clipping" not in sheet2.reply


def test_user_given_source_amplitude_is_respected():
    from agent.cascade.tool import _build
    *_, a = _build(LP2K_AMP10, 1.0)
    assert a.source_amp == 1.0 and not a.headroom


def test_apply_fix_through_the_service_applies_the_headroom_fix(svc, monkeypatch):
    _as_asked(svc, monkeypatch)
    conv = svc.new_conversation()
    tok = svc._CURRENT.set(conv)
    try:
        gen, canned = [], []
        svc.execute_tool_call("cascade", {"stages": LP2K_AMP10}, gen, canned)
        # unbuffered: loading comes first, so the buffer fix is the one offered
        assert conv.pending_fix and "voltage_follower" in str(conv.pending_fix)
        svc.execute_tool_call("apply_fix", {}, [], canned)
        assert conv.pending_fix and conv.pending_fix[1]["source_amplitude"] == 2.0   # now the headroom fix
        gen3, canned3 = [], []
        svc.execute_tool_call("apply_fix", {}, gen3, canned3)
        assert "2 V peak" in canned3[0] and conv.pending_fix is None
    finally:
        svc._CURRENT.reset(tok)


def test_the_model_cannot_switch_off_the_automatic_buffers():
    import inspect
    for fn in (_public_cascade, _public_parallel):
        assert "auto_buffer" not in inspect.signature(fn).parameters
        assert "auto_buffer" not in (fn.__doc__ or "")
    with pytest.raises(TypeError):
        _public_cascade(LP_AMP, auto_buffer=False)
    assert _public_cascade(LP_AMP)[1].reply.startswith("As asked")


def test_remembered_undo_still_reaches_the_code_only_switch(svc):
    conv = svc.new_conversation()
    tok = svc._CURRENT.set(conv)
    try:
        canned = []
        svc.execute_tool_call("cascade", {"stages": LP_AMP}, [], canned)
        assert conv.pending_alt and canned[0].startswith("As asked")
        c2 = []
        assert svc.execute_tool_call("build_without_buffers", {}, [], c2).startswith("Generated 'cascade'")
        assert not c2[0].startswith("As asked")
    finally:
        svc._CURRENT.reset(tok)


# ---- v1.18: op-amp filters (Sallen-Key, Butterworth, all-pass) ----------------------------

NEW_FILTERS = ["sallen_key_lowpass", "sallen_key_highpass", "butterworth_lowpass",
               "butterworth_highpass", "allpass_filter"]


def _gen(name, **kw):
    import agent.circuits as c
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return getattr(c, name)(**kw)


def _H(text, f):
    nl = dump.parse(text)
    out = [(e.x1, e.y1) for e in nl.elements if e.type == "O"][-1]
    return solve(text, f)["V"](out)


def _parts(text):
    nl = dump.parse(text)
    R = float([e for e in nl.elements if e.type == "r"][0].tail[0])
    C = float([e for e in nl.elements if e.type == "c"][0].tail[0])
    fb = [e for e in nl.elements if e.type == "r" and e.p1 == (480, 240)]
    K = 1.0
    if len(fb) == 2:
        K = 1 + float([e for e in fb if e.p2 == (624, 240)][0].tail[0]) / \
            float([e for e in fb if e.p2 == (480, 336)][0].tail[0])
    return R, C, K


def _sk_theory(kind, K, f0, f):
    u = 1j * f / f0
    den = u * u + (3 - K) * u + 1
    return K / den if kind == "low" else K * u * u / den


@pytest.mark.parametrize("name,kind,kw", [
    ("sallen_key_lowpass", "low", dict(cutoff_frequency=1000)),
    ("sallen_key_lowpass", "low", dict(cutoff_frequency=1000, gain=2.0)),
    ("sallen_key_highpass", "high", dict(cutoff_frequency=1000, gain=1.5)),
    ("sallen_key_highpass", "high", dict(cutoff_frequency=250)),
    ("butterworth_lowpass", "low", dict(cutoff_frequency=1000)),
    ("butterworth_highpass", "high", dict(cutoff_frequency=1000)),
])
def test_second_order_filters_match_their_exact_transfer_function(name, kind, kw):
    text = _gen(name, **kw)
    R, C, K = _parts(text)
    f0 = 1 / (2 * np.pi * R * C)
    for f in (f0 / 30, f0 / 3, f0 / 1.3, f0, f0 * 1.7, f0 * 5, f0 * 40):
        assert np.isclose(_H(text, f), _sk_theory(kind, K, f0, f), rtol=1e-9)


@pytest.mark.parametrize("name", ["butterworth_lowpass", "butterworth_highpass"])
def test_butterworth_is_maximally_flat_with_its_corner_at_the_cutoff(name):
    text = _gen(name, cutoff_frequency=1000)
    R, C, K = _parts(text)
    f0 = 1 / (2 * np.pi * R * C)
    assert abs(1 / (3 - K) - 2 ** -0.5) / 2 ** -0.5 < 0.005          # Q within 0.5% of 0.7071
    ref = abs(_H(text, f0 / 100 if name.endswith("lowpass") else f0 * 100))
    assert np.isclose(abs(_H(text, f0)) / ref, 2 ** -0.5, rtol=0.01)  # -3 dB at the cutoff


def test_allpass_has_unit_gain_everywhere_and_minus_90_degrees_at_its_centre():
    text = _gen("allpass_filter", center_frequency=1000)
    R, C, _ = _parts(text)
    f0 = 1 / (2 * np.pi * R * C)
    for f in (3, 100, f0, 5000, 80000):
        assert np.isclose(abs(_H(text, f)), 1.0, rtol=1e-9)
    assert np.isclose(np.degrees(np.angle(_H(text, f0))), -90.0, atol=1e-6)
    assert np.degrees(np.angle(_H(text, f0 / 1000))) > -1 and np.degrees(np.angle(_H(text, f0 * 1000))) < -179


def test_filter_arguments_are_validated_and_roundings_reported():
    import agent.circuits as c
    from agent.circuits._active_filters import FilterAccuracyWarning
    for bad in (0.5, 3.0, float("nan")):
        with pytest.raises(ValueError, match="gain must be between"):
            c.sallen_key_lowpass(1000, gain=bad)
    with pytest.raises(ValueError):
        c.butterworth_highpass(-5)
    with pytest.raises(ValueError, match="amp_supply"):
        c.allpass_filter(1000, amp_supply=0)
    with pytest.warns(FilterAccuracyWarning, match="achieved"):
        c.sallen_key_highpass(5000, gain=1.7)


def test_new_filters_are_registered_documented_and_named():
    import agent.circuits as c
    from agent.cascade.tool import _PRETTY
    d = _public_cascade.__doc__
    for n in NEW_FILTERS:
        assert n in [f.__name__ for f in c.CIRCUIT_TOOLS] and f"{n}: REQUIRED" in d and n in _PRETTY


@pytest.mark.parametrize("name", NEW_FILTERS)
def test_new_filter_composes_cleanly_after_and_before_another(name):
    spec = {"circuit": name, "args": SAMPLES[name]}
    for chain in ([LP, spec], [spec, HP], [spec, spec]):
        nl, sheet = cascade(chain)
        assert "couldn't write the detailed summary" not in sheet.reply
        assert len([l for l in nl.splitlines() if l.startswith("170 ")]) == 1


def test_cascade_response_of_an_active_filter_chain_matches_the_independent_solver():
    from agent.cascade.analysis import System, find_driver
    chain = [{"circuit": "rc_highpass", "args": {"cutoff_frequency": 100}},
             {"circuit": "butterworth_lowpass", "args": {"cutoff_frequency": 2000}}]
    nl_text, sheet = cascade(chain)
    nl = dump.parse(nl_text)
    sysm = System(nl, find_driver(nl))
    out = [(e.x1, e.y1) for e in nl.elements if e.type == "O"][-1]
    for f in (20.0, 100.0, 700.0, 2000.0, 9000.0):
        assert np.isclose(abs(sysm.v(sysm.solve(f), out)), abs(_H(nl_text, f)), rtol=1e-6)
    assert "band-pass circuit with a peak gain of about 1.5" in sheet.reply


def test_every_pair_with_a_new_filter_builds_or_refuses_for_a_stated_reason():
    from agent.cascade.tool import NOT_CASCADABLE, NOT_CIRCUITS, _generators
    names = [n for n in _generators() if n not in NOT_CIRCUITS | NOT_CASCADABLE]
    built = 0
    for a in names:
        for b in names:
            if a not in NEW_FILTERS and b not in NEW_FILTERS:
                continue
            try:
                r = cascade([{"circuit": a, "args": SAMPLES[a]}, {"circuit": b, "args": SAMPLES[b]}])[1].reply
            except ValueError as e:
                assert "file formats" in str(e) or "no signal input" in str(e) or "can only be the last stage" in str(e), (a, b, str(e))
                continue
            built += 1
            assert "couldn't write the detailed summary" not in r, (a, b)
    assert built >= 120


def test_no_floating_grounds_or_dangling_wires_in_the_new_filters():
    from agent.cascade.dump import nets, terminals
    for n in NEW_FILTERS:
        els = dump.parse(_gen(n, **SAMPLES[n])).elements
        net = nets(els)
        for i, e in enumerate(els):
            if e.type in ("g", "r", "c", "w"):
                for t in terminals(e):
                    touching = sum(1 for j, x in enumerate(els) if j != i and t in (terminals(x) or []))
                    assert touching >= 1, (n, e.type, t)


def test_allpass_single_reply_talks_about_phase_not_a_passband():
    import agent.circuits as c
    text = _gen("allpass_filter", center_frequency=1000)
    from agent.cascade.tool import render_single
    r = render_single("allpass_filter", {"center_frequency": 1000}, text, None, [])
    assert "gain stays at about 1" in r and "-90 degrees at the centre frequency" in r and "passband" not in r


# ---- v1.19: differential amplifier, twin-T notch, band-stop analysis ----------------------

def test_twin_t_matches_its_closed_form_and_notches_exactly():
    text = _gen("twin_t_notch_filter", notch_frequency=1000)
    nl = dump.parse(text)
    R = float([e for e in nl.elements if e.type == "r"][0].tail[0])
    C = float([e for e in nl.elements if e.type == "c"][0].tail[0])
    f0 = 1 / (2 * np.pi * R * C)
    for f in (10, 100, 500, 0.9 * f0, 1.1 * f0, 3000, 50000):
        u = f / f0
        assert np.isclose(_H(text, f), (1 - u * u) / (1 - u * u + 4j * u), rtol=1e-9)
    assert abs(_H(text, f0)) < 1e-9


def test_metrics_finds_notches_and_leaves_other_shapes_alone():
    from agent.cascade.analysis import metrics
    f = [10 ** (k / 80) for k in range(-160, 481)]
    g = lambda x: abs((1 - x * x) / (1 - x * x + 4j * x))
    m = metrics(f, [g(x) for x in f])                                   # centred at f = 1
    assert m.shape == "band-stop (notch)" and m.lo is None and m.hi is None
    assert 0.2 < m.stop[0] < 0.3 and 3 < m.stop[1] < 5 and abs(m.f_notch - 1) < 0.1 and m.depth_db > 30
    lp = metrics(f, [1 / abs(1 + 1j * x / 100) for x in f])
    assert lp.shape == "low-pass" and lp.stop is None
    both = metrics(f, [g(x) / abs(1 + 1j * x / 30) for x in f])         # notch inside a low-pass
    assert both.shape == "low-pass" and both.stop is not None and both.hi is not None


def test_notch_replies_say_rejects_and_never_quote_absurd_depths():
    from agent.cascade.tool import render_single
    r = render_single("twin_t_notch_filter", {"notch_frequency": 1000},
                      _gen("twin_t_notch_filter", notch_frequency=1000), None, [])
    assert "band-stop (notch) circuit" in r and "rejects roughly" in r and "over 60 dB down" in r
    assert "322" not in r


def test_notch_inside_a_chain_is_reported_and_is_not_blamed_on_loading():
    r = cascade([{"circuit": "rc_lowpass", "args": {"cutoff_frequency": 20000}},
                 {"circuit": "voltage_follower", "args": {}},
                 {"circuit": "twin_t_notch_filter", "args": {"notch_frequency": 1000}}])[1].reply
    assert "with a notch near" in r and "Cutoff:" not in r and "nothing worth flagging" in r
    r2 = cascade([{"circuit": "twin_t_notch_filter", "args": {"notch_frequency": 1000}},
                  {"circuit": "voltage_follower", "args": {}},
                  {"circuit": "rc_lowpass", "args": {"cutoff_frequency": 5000}}])[1].reply
    assert "Cutoff:" not in r2


def test_differential_amplifier_gain_and_subtraction():
    d = _gen("differential_amplifier", gain_v_per_v=10)
    assert np.isclose(_H(d, 1000), 10.0, rtol=1e-9)                     # V- grounded: gain on V+
    both = _gen("differential_amplifier", gain_v_per_v=10, reference_amplitude=0.5)
    lines = both.splitlines()
    sweep = next(l for l in lines if l.startswith("170 "))
    vsrc = next(l for l in lines if l.startswith("v "))
    swapped = [vsrc if l == sweep else sweep if l == vsrc else l for l in lines]   # solver drives the first source
    assert np.isclose(_H("\n".join(swapped) + "\n", 1000), -10.0, rtol=1e-9)        # V- sees -gain
    assert np.isclose(_H(both, 1000), 10.0, rtol=1e-9)                              # V+ sees +gain


def test_differential_amplifier_validates_and_reports_rounding():
    import agent.circuits as c
    from agent.circuits._active_filters import FilterAccuracyWarning
    with pytest.raises(ValueError):
        c.differential_amplifier(0)
    with pytest.raises(ValueError, match="reference_amplitude"):
        c.differential_amplifier(5, reference_amplitude=-1)
    with pytest.warns(FilterAccuracyWarning, match="achieved"):
        c.differential_amplifier(4.2)


def test_both_new_circuits_are_registered_documented_and_clean():
    import agent.circuits as c
    from agent.cascade.tool import _PRETTY
    d = _public_cascade.__doc__
    for n in ("differential_amplifier", "twin_t_notch_filter"):
        assert n in [f.__name__ for f in c.CIRCUIT_TOOLS] and n in _PRETTY and f"{n}: REQUIRED" in d
        text = _gen(n, **SAMPLES[n])
        els = dump.parse(text).elements
        from agent.cascade.dump import terminals
        for i, e in enumerate(els):
            if e.type in ("g", "r", "c", "w", "v"):
                for t in terminals(e):
                    assert any(j != i and t in (terminals(x) or []) for j, x in enumerate(els)), (n, e.type, t)


def test_every_series_and_parallel_pair_with_the_new_circuits_has_a_full_reply():
    from agent.cascade.tool import NOT_CASCADABLE, NOT_CIRCUITS, _generators
    names = [n for n in _generators() if n not in NOT_CIRCUITS | NOT_CASCADABLE]
    new = ("differential_amplifier", "twin_t_notch_filter")
    built = 0
    for a in names:
        for b in names:
            if a not in new and b not in new:
                continue
            sa, sb = {"circuit": a, "args": SAMPLES[a]}, {"circuit": b, "args": SAMPLES[b]}
            for fn, arg in ((cascade, [sa, sb]), (parallel_sum, [[sa], [sb]])):
                try:
                    r = fn(arg)[1].reply
                except ValueError as e:
                    assert any(k in str(e) for k in ("file formats", "no signal input", "takes no signal input", "can only be the last stage", "can only be the last stage of a whole chain")), str(e)
                    continue
                built += 1
                assert "couldn't write the detailed summary" not in r, (a, b)
    assert built >= 120
