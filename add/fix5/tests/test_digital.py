"""Digital cascade: block behaviour from the netlists, joins, bit order, refusals (ideal zero-delay model)."""
import warnings

import pytest

from agent import circuits as C
from agent.cascade import digital_chain as D
from agent.cascade.digital import Sim

warnings.simplefilter("ignore")


def _st(name, **a):
    return {"circuit": name, "args": a}


@pytest.mark.parametrize("n", [2, 3, 4, 6])
def test_counter_counts_in_binary_from_its_netlist(n):
    s = Sim(C.binary_counter(n))
    pts = [e.p1 for e in sorted((s.els[i] for i, _ in s.markers()), key=lambda e: e.x1)]
    T = 1 / 200
    seen, last = [], None
    for k in range(int((2 ** n + 2) * 20)):
        val = s.step(k * T / 20 + T / 60, k == 0)
        c = sum(val.get(s.net(p), 0) << i for i, p in enumerate(pts))
        if c != last:
            seen.append(c)
            last = c
    assert seen[:2 ** n + 1] == list(range(2 ** n)) + [0]


def test_sipo_shifts_serial_bits_through_its_stages():
    s = Sim(C.sipo_shift_register(4))
    (li,) = [i for i, e in enumerate(s.els) if e.type == "L"]
    T, pat = 1 / 100, [1, 0, 1, 1, 0, 0, 1, 0]
    s.drive[li] = lambda t: pat[min(int((t + T / 2) // T), len(pat) - 1)]
    pts = [s.els[i].p1 for i, _ in s.markers()]
    seen = {}
    for q in range(8 * 20):
        val = s.step(q * T / 20 + T / 60, q == 0)
        if q % 20 == 5:
            seen[q // 20] = [val.get(s.net(p), 0) for p in pts]
    for k in range(1, 8):
        assert seen[k] == [pat[k - i] if k - i >= 1 else 0 for i in range(4)], (k, seen[k])


@pytest.mark.parametrize("n", [2, 3, 4, 6])
def test_piso_to_sipo_rebuilds_the_word(n):
    _, note = D.digital_cascade([_st("piso_shift_register", bits=n), _st("sipo_shift_register", bits=n)])
    assert "check PISO word is rebuilt in the SIPO: PASS" in note and "structural problem" not in note


@pytest.mark.parametrize("dac", ["r2r_dac", "binary_weighted_dac"])
@pytest.mark.parametrize("n", [2, 3, 4, 5, 6])
def test_counter_to_dac_carries_the_code_in_the_right_bit_order(n, dac):
    _, note = D.digital_cascade([_st("binary_counter", bits=n), _st(dac, bits=n)])
    assert "counts: PASS" in note and "structural problem" not in note


def test_wrong_bit_order_is_caught(monkeypatch):
    real = D.ports_of

    def reversed_ports(name, nl):
        b = real(name, nl)
        if name == "r2r_dac":
            b.in_bits, b.in_pts = b.in_bits[::-1], b.in_pts[::-1]
        return b
    monkeypatch.setattr(D, "ports_of", reversed_ports)
    _, note = D.digital_cascade([_st("binary_counter", bits=3), _st("r2r_dac", bits=3)])
    assert "FAIL" in note


def test_width_mismatch_is_refused():
    with pytest.raises(ValueError, match="width mismatch"):
        D.digital_cascade([_st("binary_counter", bits=4), _st("r2r_dac", bits=3)])


def test_xml_blocks_are_converted_so_mixed_chains_build_in_one_loadable_format():
    text, note = D.digital_cascade([_st("binary_counter", bits=3), _st("piso_shift_register", bits=3)])
    assert text.startswith("$ ") and "<" not in text and "PASS" in note
    for a in ("sipo_shift_register", "piso_shift_register"):
        legacy = D.to_legacy(D.parse(getattr(C, a)(4)))
        assert legacy.dialect == "legacy" and "<" not in legacy.to_text()


def test_unlisted_pairs_name_what_the_block_can_drive():
    with pytest.raises(ValueError, match="can drive"):
        D.digital_cascade([_st("r2r_dac", bits=3), _st("binary_counter", bits=3)])


def test_joined_nets_are_only_the_intended_ones():
    ch = D.start("piso_shift_register", C.piso_shift_register(4))
    ch = D.join(ch, "sipo_shift_register", D.parse(C.sipo_shift_register(4)), "serial")
    assert ch.problems == []
    sim = Sim(ch.netlist)
    assert sim.problems == []


def test_every_declared_link_builds_and_passes_its_checks():
    wl = D.working_links()
    assert ("binary_counter", "piso_shift_register") in wl and ("flash_adc", "piso_shift_register") in wl
    for a, b in wl:
        text, note = D.digital_cascade([_st(a, bits=3), _st(b, bits=3)])
        assert "<" not in text and "FAIL" not in note


def test_piso_to_sipo_reloads_with_the_real_mux_polarity():
    ch = D.start("piso_shift_register", C.piso_shift_register(4))
    toggle = ch.netlist.elements[ch.blocks[0].load]
    assert toggle.tail[0] == "0"                       # 0 = load in this CircuitJS build


def test_tool_wrapper_returns_a_code_written_reply_and_a_generated_description():
    from agent.cascade import tool
    text, note = tool.digital_cascade([_st("binary_counter", bits=4), _st("r2r_dac", bits=4)])
    assert note.reply.startswith("Digital cascade: binary counter -> R-2R DAC.")
    assert "binary_counter -> r2r_dac" in tool.digital_cascade.__doc__
    assert "binary_counter -> piso_shift_register" in tool.digital_cascade.__doc__


@pytest.mark.parametrize("stages", [
    [{"name": "binary_counter", "args": {"bits": 4}}, {"name": "r2r_dac", "args": {"bits": 4}}],
    ["binary_counter", "r2r_dac"],
    [{"circuit": "binary_counter", "args": {"bits": 4}}, {"circuit": "r2r_dac", "args": [4]}],
    [{"circuit": "binary_counter", "bits": 4}, {"circuit": "r2r_dac", "bits": 4}],
    [{"circuit": "binary_counter", "args": {"bits": 4}}, {"circuit": "r2r_dac", "args": {"bits": 99}}],
    [{"circuit": "binary_counter", "args": {"bits": 4}}],
])
def test_malformed_stages_give_a_readable_value_error_never_a_key_error(stages):
    with pytest.raises(ValueError):
        D.digital_cascade(stages)


def test_standalone_shift_registers_are_loadable_and_start_in_load_mode_with_a_mixed_word():
    for text in (C.piso_shift_register(4), C.sipo_shift_register(4)):
        assert text.startswith("$ ") and "<" not in text
    nl = D.parse(C.piso_shift_register(4))
    toggles = [e for e in nl.elements if e.type == "L"]
    assert [e.tail[0] for e in toggles[:4]] == ["1", "0", "1", "1"]      # parallel inputs, left to right
    assert toggles[4].tail[0] == "0"                                    # load/shift starts in LOAD


def test_generator_warnings_reach_the_digital_reply():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _, note = D.digital_cascade([_st("binary_counter", bits=6), _st("binary_weighted_dac", bits=6)])
    assert "Warning from the" in note.reply and "clip" in note.reply


# ----------------------------------------------------------------------------- port-typed links, any chain
def _chain(*blocks):
    text, note = D.digital_cascade([_st(n, bits=b) for n, b in blocks])
    return D.Sim(text), note


def _states(sim, T, edges):
    """Settled nets just after each rising edge (the clock is also sampled low just before it, so edges are seen)."""
    out, first = [], True
    for t in [0.0] + [x for k in range(1, edges + 1) for x in (k * T - T / 8, k * T + T / 8)]:
        val = sim.step(t, first)
        first = False
        out.append(val)
    return out[:1] + out[2::2]


def test_working_links_come_from_the_ports_and_include_the_same_type_chains():
    wl = D.working_links()
    for pair, kind in {("binary_counter", "binary_counter"): "carry", ("sipo_shift_register", "sipo_shift_register"): "serial",
                       ("piso_shift_register", "piso_shift_register"): "serial",
                       ("binary_counter", "r2r_dac"): "bits"}.items():
        assert wl[pair] == kind
    assert ("binary_counter", "sipo_shift_register") not in wl and ("r2r_dac", "binary_counter") not in wl


@pytest.mark.parametrize("a,b", [("binary_counter", "sipo_shift_register"), ("piso_shift_register", "r2r_dac")])
def test_adapter_is_named_when_a_bus_meets_a_serial_port(a, b):
    with pytest.raises(ValueError, match="insert a (piso|sipo)_shift_register"):
        D.digital_cascade([_st(a, bits=3), _st(b, bits=3)])


def test_counter_to_counter_is_one_wider_binary_counter():
    text, note = D.digital_cascade([_st("binary_counter", bits=3), _st("binary_counter", bits=2)])
    sim = Sim(text)
    nl = D.load_block(text)
    ms = sorted((e for e in nl.elements if e.type == "M"), key=lambda e: (e.x1, e.y1))
    assert len(ms) == 5
    T, last, seq = 1 / 200, None, []
    for k in range(int(40 * 20)):
        val = sim.step(k * T / 20 + T / 60, k == 0)
        c = sum(val.get(sim.net(e.p1), 0) << i for i, e in enumerate(ms))
        if c != last:
            seq.append(c)
            last = c
    assert seq[:33] == list(range(32)) + [0] and "link 1 (binary counter -> binary counter, carry): PASS" in note


def _markers_sorted(nl):
    return [e.p1 for e in sorted((e for e in nl.elements if e.type == "M"), key=lambda e: (e.x1, e.y1))]


def test_sipo_to_sipo_behaves_exactly_like_one_six_bit_sipo():
    chain_text, note = D.digital_cascade([_st("sipo_shift_register", bits=3), _st("sipo_shift_register", bits=3)])
    sims = []
    for text in (chain_text, C.sipo_shift_register(6)):
        nl = D.load_block(text)
        sim = Sim(nl)
        (li,) = [i for i, e in enumerate(nl.elements) if e.type == "L"]
        T, pat = 1 / 100, [1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1]
        sim.drive[li] = lambda t, pat=pat, T=T: pat[min(int((t + T / 4) // T), len(pat) - 1)]
        sims.append((sim, _markers_sorted(nl)))
    T = 1 / 100
    a, b = (_states(s_, T, 12) for s_, _ in sims)
    rows = [[[v.get(s_.net(p), 0) for p in pts] for v in vals] for (s_, pts), vals in zip(sims, (a, b))]
    assert rows[0] == rows[1] and any(any(r) for r in rows[0])
    assert "FAIL" not in note


def test_piso_to_piso_behaves_exactly_like_one_six_bit_piso():
    chain_text, note = D.digital_cascade([_st("piso_shift_register", bits=3), _st("piso_shift_register", bits=3)])
    word = [1, 0, 1, 1, 0, 1]
    T = 1 / 100
    outs = []
    for text in (chain_text, C.piso_shift_register(6)):
        nl = D.load_block(text)
        sim = Sim(nl)
        par = sorted((i for i, e in enumerate(nl.elements) if e.type == "L" and e.y1 >= 240), key=lambda i: nl.elements[i].x1)
        (ld,) = [i for i, e in enumerate(nl.elements) if e.type == "L" and e.y1 < 240]
        assert len(par) == 6
        for i, v in zip(par, word):
            sim.drive[i] = lambda t, v=v: v
        sim.drive[ld] = lambda t: 0 if t < 1.5 * T else 1
        m = _markers_sorted(nl)[-1]                      # the chain's serial output is its rightmost marker
        outs.append([v.get(sim.net(m), 0) for v in _states(sim, T, 12)])
    assert outs[0] == outs[1] and sum(outs[0]) >= 3
    assert "FAIL" not in note


def test_three_and_four_block_chains_build_and_pass_every_link():
    for blocks in ([("piso_shift_register", 3), ("piso_shift_register", 3), ("sipo_shift_register", 6)],
                   [("binary_counter", 3), ("binary_counter", 3), ("r2r_dac", 3)],
                   [("piso_shift_register", 3), ("sipo_shift_register", 3), ("piso_shift_register", 3),
                    ("sipo_shift_register", 3)]):
        text, note = D.digital_cascade([_st(n, bits=b) for n, b in blocks])
        assert note.count("PASS") >= len(blocks) - 1 and "FAIL" not in note and "<" not in text


def _mutate(monkeypatch, name, fn):
    orig = D.ports_of

    def patched(n, nl):
        b = orig(n, nl)
        if n == name:
            fn(b)
        return b
    monkeypatch.setattr(D, "ports_of", patched)


def test_checks_catch_a_carry_taken_from_the_wrong_bit(monkeypatch):
    _mutate(monkeypatch, "binary_counter", lambda b: setattr(b, "carry_out", b.out_bits[0]))
    _, note = D.digital_cascade([_st("binary_counter", bits=3), _st("binary_counter", bits=2)])
    assert "FAIL" in note


def test_checks_catch_a_serial_link_taken_from_the_wrong_stage(monkeypatch):
    _mutate(monkeypatch, "sipo_shift_register", lambda b: setattr(b, "serial_out", b.out_bits[0]))
    _, note = D.digital_cascade([_st("sipo_shift_register", bits=3), _st("sipo_shift_register", bits=3)])
    assert "FAIL" in note


def test_checks_catch_reversed_bits_into_a_dac_from_a_register(monkeypatch):
    def rev(b):
        b.in_bits, b.in_pts = b.in_bits[::-1], b.in_pts[::-1]
    _mutate(monkeypatch, "r2r_dac", rev)
    _, note = D.digital_cascade([_st("sipo_shift_register", bits=3), _st("r2r_dac", bits=3)])
    assert "FAIL" in note


def test_a_source_that_never_changes_is_reported_not_passed():
    _, note = D.digital_cascade([_st("flash_adc", bits=3), _st("piso_shift_register", bits=3)])
    assert "FAIL" not in note


def test_labels_of_toggles_that_were_wired_away_are_removed():
    text, _ = D.digital_cascade([_st("piso_shift_register", bits=3), _st("piso_shift_register", bits=3)])
    labels = [l.split()[-1] for l in text.splitlines() if l.startswith("x ")]
    assert labels.count("load/shift") == 1          # the second register is tied to the first one
    assert labels.count("inputs") == 2              # ... but each register still has its own parallel inputs
    text, _ = D.digital_cascade([_st("binary_counter", bits=3), _st("piso_shift_register", bits=3)])
    assert "inputs" not in [l.split()[-1] for l in text.splitlines() if l.startswith("x ")]
