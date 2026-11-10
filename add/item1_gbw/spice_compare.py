#!/usr/bin/env python3
"""Compare the cascade tool's predicted gain / -3 dB corners with real ngspice.

For every ordered pair of the linear circuits (filters, op-amp stages) it
  1. builds the 2-stage CircuitJS netlist with the cascade tool,
  2. converts it to a SPICE netlist (R, C, L, op-amp, AC source, ground),
  3. runs `ngspice -b` for an AC sweep,
  4. extracts peak gain and the -3 dB corners and compares them with the tool's numbers.

Usage (inside the environment where the agent runs, with ngspice installed, e.g. WSL):
    python spice_compare.py --repo ~/Major_Project/elektraSage/add
    python spice_compare.py --repo ... --opamp gbw --gbw 1e6          # real op-amp: single pole
    python spice_compare.py --repo ... --write-only --keep cir_files  # only write .cir files, run nothing
Needs only the standard library plus whatever the agent package already needs.
"""
import argparse, csv, math, os, re, shutil, subprocess, sys, tempfile, warnings

warnings.simplefilter("ignore")
LIN = ["rc_lowpass", "rc_highpass", "rl_lowpass", "rl_highpass", "sallen_key_lowpass", "sallen_key_highpass",
       "butterworth_lowpass", "butterworth_highpass", "allpass_filter", "twin_t_notch_filter", "inverting_amp",
       "non_inverting_amp", "voltage_follower", "integrator", "differentiator", "differential_amplifier"]
FMIN, FMAX, PTS = 0.1, 1e8, 100          # AC sweep: points per decade


def to_spice(text, dump, opamp="ideal", gbw=1e6, a0=1e5, rout=0.0):
    """CircuitJS legacy netlist -> (SPICE text, output node name). Raises ValueError for unsupported parts."""
    nl = dump.parse(text)
    els = nl.elements
    nid = dump.nets(els, merge_ground=True)
    gnd = next((nid[e.p1] for e in els if e.type == "g"), None)
    if gnd is None:
        raise ValueError("no ground symbol")
    ok = {"r", "c", "l", "w", "g", "a", "170", "R", "v", "O"}
    bad = sorted({e.type for e in els if e.type not in ok})
    if bad:
        raise ValueError(f"unsupported element types {bad}")
    srcs = [e for e in els if e.type in ("170", "R", "v")]
    if len(srcs) != 1:
        raise ValueError(f"{len(srcs)} sources")
    outs = [e for e in els if e.type == "O"]
    if not outs:
        raise ValueError("no output marker")
    name = lambda p: "0" if nid[p] == gnd else f"n{nid[p]}"
    L = ["* generated from a CircuitJS netlist by spice_compare.py"]
    k = {"r": 0, "c": 0, "l": 0, "a": 0}
    for e in els:
        if e.type == "r":
            k["r"] += 1; L.append(f"R{k['r']} {name(e.p1)} {name(e.p2)} {float(e.tail[0])!r}")
        elif e.type == "c":
            k["c"] += 1; L.append(f"C{k['c']} {name(e.p1)} {name(e.p2)} {float(e.tail[0])!r}")
        elif e.type == "l":
            k["l"] += 1; L.append(f"L{k['l']} {name(e.p1)} {name(e.p2)} {float(e.tail[0])!r}")
        elif e.type == "a":
            k["a"] += 1; i = k["a"]
            pins = [name(p) for p in dump.terminals(e)]
            # CircuitJS flag bit 0 swaps the two inputs: with it set the FIRST pin is the inverting one,
            # without it the SECOND pin is (the usual '-' on top).  Checked on follower and inverting-amp netlists.
            inv, noninv = (pins[0], pins[1]) if int(e.flags) & 1 else (pins[1], pins[0])
            out = pins[2]
            if opamp == "ideal":
                L.append(f"E{i} {out} 0 {noninv} {inv} 1e6")
            else:                                                       # one-pole op-amp with output resistance
                fp = gbw / a0
                L.append(f"E{i}a x{i} 0 {noninv} {inv} {a0!r}")
                L.append(f"Rp{i} x{i} y{i} 1k")
                L.append(f"Cp{i} y{i} 0 {1 / (2 * math.pi * fp * 1e3)!r}")
                if rout > 0:                                            # optional output resistance
                    L.append(f"E{i}b z{i} 0 y{i} 0 1")
                    L.append(f"Ro{i} z{i} {out} {rout!r}")
                else:
                    L.append(f"E{i}b {out} 0 y{i} 0 1")
    s = srcs[0]
    if s.type == "v":
        L.append(f"V1 {name(s.p2)} {name(s.p1)} DC 0 AC 1")
    else:
        L.append(f"V1 {name(s.p1)} 0 DC 0 AC 1")
    out_e = max(outs, key=lambda e: e.x1)
    onode = name(out_e.p1)
    if onode == "0":
        raise ValueError("output is ground")
    return "\n".join(L), onode


def deck(body, onode, wr):
    return (f"circuit under test\n{body}\n.option noacct\n.control\n"
            f"set wr_vecnames\nac dec {PTS} {FMIN} {FMAX}\nwrdata {wr} mag(v({onode}))\nquit\n.endc\n.end\n")


def read_wrdata(path):
    f, m = [], []
    for ln in open(path):
        p = ln.split()
        if len(p) >= 2:
            try: f.append(float(p[0])); m.append(float(p[1]))
            except ValueError: pass            # header line
    return f, m


def metrics(f, m):
    pk = max(m); i = m.index(pk); thr = pk / math.sqrt(2); lo = hi = None
    for j in range(i, 0, -1):
        if m[j - 1] < thr <= m[j]:
            lo = f[j - 1] + (thr - m[j - 1]) / (m[j] - m[j - 1]) * (f[j] - f[j - 1]); break
    for j in range(i, len(m) - 1):
        if m[j + 1] < thr <= m[j]:
            hi = f[j] + (m[j] - thr) / (m[j] - m[j + 1]) * (f[j + 1] - f[j]); break
    return pk, lo, hi


def hz(s):
    m = re.fullmatch(r"([\d.]+(?:e[+-]?\d+)?)\s*(m|k|M|G)?Hz", s.strip())
    return None if not m else float(m.group(1)) * {None: 1, "m": 1e-3, "k": 1e3, "M": 1e6, "G": 1e9}[m.group(2)]


def predicted(note):
    m = re.search(r"shape: ([^\n]+)", note)
    if not m: return None
    s = m.group(1)
    if not s.startswith(("low-pass", "high-pass", "band-pass", "flat")): return None
    g = re.search(r"passband gain ([\d.e+-]+)", s)
    b = re.search(r"-3 dB band (?:from low end|([\d.]+\s?\w*Hz)) to ([\d.]+\s?\w*Hz|high end)", s)
    lo = hz(b.group(1)) if b and b.group(1) else None
    hi = None if (not b or b.group(2) == "high end") else hz(b.group(2))
    o = re.search(r"op-amp bandwidth: [^\n]*?down by 3 dB near ([\d.]+\s?\w*Hz)", note)     # limit above the swept range
    if hi is None and o:
        hi = hz(o.group(1))
    return (float(g.group(1)) if g else None), lo, hi


def rel(a, b):
    if a is None and b is None: return 0.0
    if a is None or b is None: return 9.99          # corner present on one side only = counted as a mismatch
    return abs(a - b) / max(abs(b), 1e-12)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="the add/ folder that contains agent/")
    ap.add_argument("--ngspice", default="ngspice")
    ap.add_argument("--opamp", choices=["ideal", "gbw"], default="ideal")
    ap.add_argument("--gbw", type=float, default=1e6)
    ap.add_argument("--rout", type=float, default=0.0, help="op-amp output resistance for --opamp gbw (default 0, like CircuitJS)")
    ap.add_argument("--out", default="spice_results.csv")
    ap.add_argument("--keep", default=None, help="folder to keep the .cir files in")
    ap.add_argument("--write-only", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="only the first N pairs (try 5 first)")
    a = ap.parse_args()
    sys.path.insert(0, os.path.expanduser(a.repo))
    from agent.cascade import tool, conformance as c, dump
    if not a.write_only and not shutil.which(a.ngspice):
        sys.exit(f"cannot find '{a.ngspice}'. Install it (sudo apt install ngspice) or pass --ngspice /path")
    if a.keep: os.makedirs(a.keep, exist_ok=True)
    pairs = [(x, y) for x in LIN for y in LIN]
    if a.limit: pairs = pairs[:a.limit]
    spec = lambda n: {"circuit": n, "args": dict(c.SAMPLES[n])}
    rows, tmp = [], tempfile.mkdtemp()
    for n, (x, y) in enumerate(pairs, 1):
        row = {"stage1": x, "stage2": y, "status": "", "note": ""}
        try:
            net, note = tool._cascade_impl([spec(x), spec(y)])
            pred = predicted(str(note))
            body, onode = to_spice(net, dump, a.opamp, a.gbw, rout=a.rout)
            wr = os.path.join(tmp, "out.txt")
            cir = deck(body, onode, wr.replace("\\", "/"))
            if a.keep: open(os.path.join(a.keep, f"{x}__{y}.cir"), "w").write(cir)
            if a.write_only: row["status"] = "written"; rows.append(row); continue
            if pred is None: row["status"] = "skip"; row["note"] = "not a flat/low/high/band-pass response"; rows.append(row); continue
            p = os.path.join(tmp, "t.cir"); open(p, "w").write(cir)
            if os.path.exists(wr): os.remove(wr)
            r = subprocess.run([a.ngspice, "-b", p], capture_output=True, text=True, timeout=120)
            if not os.path.exists(wr):
                row["status"] = "ngspice_error"; row["note"] = (r.stdout + r.stderr)[-300:].replace("\n", " "); rows.append(row); continue
            f, m = read_wrdata(wr)
            pk, lo, hi = metrics(f, m)
            g, plo, phi = pred
            row.update(status="compared", gain_tool=g, gain_spice=pk, lo_tool=plo, lo_spice=lo, hi_tool=phi, hi_spice=hi,
                       gain_err=rel(pk, g), lo_err=rel(lo, plo), hi_err=rel(hi, phi))
        except (ValueError, subprocess.TimeoutExpired) as e:
            row["status"] = "unsupported"; row["note"] = str(e)[:150]
        except Exception as e:
            row["status"] = "error"; row["note"] = f"{type(e).__name__}: {e}"[:150]
        rows.append(row)
        if n % 25 == 0: print(f"{n}/{len(pairs)}", file=sys.stderr)
    cols = ["stage1", "stage2", "status", "gain_tool", "gain_spice", "lo_tool", "lo_spice", "hi_tool", "hi_spice",
            "gain_err", "lo_err", "hi_err", "note"]
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    cmp_ = [r for r in rows if r["status"] == "compared"]
    print(f"{len(rows)} pairs: " + ", ".join(f"{s}={sum(r['status'] == s for r in rows)}" for s in sorted({r['status'] for r in rows})))
    for k in ("gain_err", "lo_err", "hi_err"):
        v = sorted(r[k] for r in cmp_ if r[k] is not None and r[k] == r[k])
        if v: print(f"{k}: median {v[len(v) // 2]:.4f}  max {v[-1]:.4f}  over 2%: {sum(x > 0.02 for x in v)}")
    print("written to", a.out)


if __name__ == "__main__":
    main()
