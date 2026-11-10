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
