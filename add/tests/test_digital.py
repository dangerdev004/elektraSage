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


def test_mixed_file_formats_are_refused_with_the_reason():
    with pytest.raises(ValueError, match="different|mix of its two file formats"):
        D.digital_cascade([_st("binary_counter", bits=3), _st("piso_shift_register", bits=3)])


def test_unlisted_pairs_name_what_the_block_can_drive():
    with pytest.raises(ValueError, match="can drive"):
        D.digital_cascade([_st("r2r_dac", bits=3), _st("binary_counter", bits=3)])


def test_joined_nets_are_only_the_intended_ones():
    ch = D.start("piso_shift_register", C.piso_shift_register(4))
    ch = D.join(ch, "sipo_shift_register", D.parse(C.sipo_shift_register(4)), "serial")
    assert ch.problems == []
    sim = Sim(ch.netlist)
    assert sim.problems == []


def test_working_links_are_only_same_format_pairs():
    wl = D.working_links()
    assert ("binary_counter", "r2r_dac") in wl and ("piso_shift_register", "sipo_shift_register") in wl
    assert ("binary_counter", "piso_shift_register") not in wl and ("flash_adc", "piso_shift_register") not in wl
    for a, b in wl:
        D.digital_cascade([_st(a, bits=3), _st(b, bits=3)]) if a != "flash_adc" else None


def test_tool_wrapper_returns_a_code_written_reply_and_a_generated_description():
    from agent.cascade import tool
    text, note = tool.digital_cascade([_st("binary_counter", bits=4), _st("r2r_dac", bits=4)])
    assert note.reply.startswith("Digital cascade: binary counter -> R-2R DAC.")
    assert "binary_counter -> r2r_dac" in tool.digital_cascade.__doc__
    assert "binary_counter -> piso_shift_register" not in tool.digital_cascade.__doc__
