#!/usr/bin/env python3
"""Generate REPORT.md from the accuracy runs."""
import argparse
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util
spec = importlib.util.spec_from_file_location("ra", os.path.join(HERE, "run_accuracy.py"))
ra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ra)


def load_rows(rundir):
    return ra.analyze_nominal(rundir, -1.0)


def fmt_matrix(rows, key, scale=1e6, fmt="{:7.2f}"):
    out = []
    hdr = "| k\\Iin |" + "".join(f"{v:>7} |" for v in range(-8, 8))
    out.append(hdr)
    out.append("|" + "---|" * 17)
    for k in range(1, 9):
        vals = []
        for iin in range(-8, 8):
            r = next(r for r in rows if r["k"] == k and r["iin"] == iin)
            vals.append(scale * float(r[key]))
        out.append(f"| {k} |" + "".join(fmt.format(v) + " |" for v in vals))
    return "\n".join(out)


def common_window(rows, k):
    """Vout array where criterion holds for every Iin at multiplicity k."""
    d = ra.parse_ascii_raw(os.path.join(
        rows[0]["_dir"], f"k{k}", f"i{ra.iin_tag(0)}", "acc.raw"))
    vout = d["v(v-sweep)"]
    ok = [True] * len(vout)
    for iin in range(-8, 8):
        dd = ra.parse_ascii_raw(os.path.join(
            rows[0]["_dir"], f"k{k}", f"i{ra.iin_tag(iin)}", "acc.raw"))
        iout = ra.get_vec(dd, f"i({ra.VSRC})")
        ideal = -(-1.0) * k * iin * 1e-6
        lsb = k * 1e-6
        for j, x in enumerate(iout):
            if abs(x - ideal) >= 0.5 * lsb:
                ok[j] = False
    lo, hi = ra.longest_true_run(ok)
    return (vout[lo], vout[hi]) if lo is not None else (None, None)


def pass_vs_vout(rundir):
    """ok[k][iin] = list of bool per Vout point (half-LSB)."""
    ok = {}
    vout = None
    for k in range(1, 9):
        for iin in range(-8, 8):
            d = ra.parse_ascii_raw(os.path.join(
                rundir, f"k{k}", f"i{ra.iin_tag(iin)}", "acc.raw"))
            vout = d["v(v-sweep)"]
            iout = ra.get_vec(d, f"i({ra.VSRC})")
            ideal = k * iin * 1e-6
            lsb = k * 1e-6
            ok[(k, iin)] = [abs(x - ideal) < 0.5 * lsb for x in iout]
    return vout, ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="",
                    help="suffix used by run_accuracy.py, e.g. '_v3'")
    ap.add_argument("--results-dir", default=None,
                    help="base dir with nominal/corner_*/mc outputs")
    ap.add_argument("--name", default=None,
                    help="label for the report title (default: from --prefix)")
    ap.add_argument("--vsrc", default="v2",
                    help="testbench output voltage source name (default v2)")
    args = ap.parse_args()
    ra.VSRC = args.vsrc
    prefix = args.prefix
    resdir = args.results_dir or HERE
    rundir = os.path.join(resdir, f"nominal{prefix}")
    rows = load_rows(rundir)
    for r in rows:
        r["_dir"] = rundir
    version = args.name or prefix.strip("_") or "v2"
    lines = []
    lines.append(f"# EMMAC_Block_{version} accuracy characterization\n")
    lines.append(f"Testbench: `EMMAC_Accuracy{prefix}.sch` / "
                 f"`simulations/EMMAC_Accuracy{prefix}.spice`\n")
    lines.append("Criterion: |Iout - k*Iin| < 0.5*k*1uA (half-LSB), "
                 "Iout measured as current into V2 at the OUT pin.\n")
    lines.append("Measured polarity is **non-inverting** in this testbench "
                 "(Iout ~ +k*Iin), so errors below are vs +k*Iin. If the MAC "
                 "input convention is 'positive code sinks current', read the "
                 "signs inverted.\n")
    lines.append("## Transfer at Vout = 0.9 V (uA)\n")
    lines.append(fmt_matrix(rows, "iout_mid"))
    lines.append("\nIdeal (k*Iin) is the same for every k row: "
                 + "-8..7 uA times k.\n")
    lines.append("## Error vs ideal +k*Iin at Vout = 0.9 V (uA)\n")
    lines.append(fmt_matrix(rows, "err_mid"))
    lines.append("\n## Worst |error| in LSB units over the Vout sweep\n")
    lines.append("| k | worst LSB err | combos never meeting criterion | "
                 "common window Vout (all 16 Iin) |")
    lines.append("|---|---|---|---|")
    for k in range(1, 9):
        kr = [r for r in rows if r["k"] == k]
        worst = max(r["max_err_lsb"] for r in kr)
        nbad = sum(1 for r in kr if r["win_lo"] is None)
        lo, hi = common_window(rows, k)
        win = f"{lo:.2f} .. {hi:.2f} V" if lo is not None else "none"
        lines.append(f"| {k} | {worst:.2f} | {nbad}/16 | {win} |")
    vout, ok = pass_vs_vout(rundir)
    lines.append("\n## Half-LSB pass count vs output bias "
                 "(out of 128 k,Iin combos)\n")
    lines.append("| Vout (V) | passing |")
    lines.append("|---|---|")
    for j, v in enumerate(vout):
        n = sum(1 for key in ok if ok[key][j])
        lines.append(f"| {v:.2f} | {n}/128 |")
    lines.append("\n## Level separability at Vout = 0.4 V "
                 "(16 input levels per k)\n")
    lines.append("| k | monotonic | min adjacent gap (uA) | ideal step (uA) | "
                 "gap/step |")
    lines.append("|---|---|---|---|---|")
    for k in range(1, 9):
        levels = []
        for iin in range(-8, 8):
            d = ra.parse_ascii_raw(os.path.join(
                rundir, f"k{k}", f"i{ra.iin_tag(iin)}", "acc.raw"))
            vo = d["v(v-sweep)"]
            io = ra.get_vec(d, f"i({ra.VSRC})")
            j = min(range(len(vo)), key=lambda q: abs(vo[q] - 0.4))
            levels.append(io[j])
        mono = all(b > a for a, b in zip(levels, levels[1:]))
        gaps = [b - a for a, b in zip(levels, levels[1:])]
        ming = min(gaps)
        step = k * 1e-6
        lines.append(f"| {k} | {'yes' if mono else 'no'} | "
                     f"{ming * 1e6:.3f} | {step * 1e6:.0f} | "
                     f"{ming / step:.2f} |")
    lines.append("\n## Corner summary (worst LSB error over full sweep)\n")
    lines.append("| corner | combos failing | combos >1 LSB | worst LSB |")
    lines.append("|---|---|---|---|")
    for tag in ["tt", "ss", "ff", "sf", "fs"]:
        cdir = os.path.join(resdir, f"corner{prefix}_{tag}")
        if not os.path.isdir(cdir):
            continue
        crows = load_rows(cdir)
        nbad = sum(1 for r in crows if r["win_lo"] is None)
        nwarn = sum(1 for r in crows if r["max_err_lsb"] >= 1.0)
        lines.append(f"| {tag} | {nbad}/128 | {nwarn}/128 | "
                     f"{max(r['max_err_lsb'] for r in crows):.2f} |")
    mc = os.path.join(resdir, f"mc{prefix}", "mc_results.csv")
    lines.append("\n## Mismatch Monte Carlo\n")
    if os.path.exists(mc):
        vals = []
        for line in open(mc).read().splitlines()[1:]:
            _, k, _, v = line.split(",")
            vals.append((int(k), float(v)))
        runs = sorted({int(l.split(",")[0]) for l in
                       open(mc).read().splitlines()[1:]})
        per_run = {}
        for line in open(mc).read().splitlines()[1:]:
            r, k, _, v = line.split(",")
            per_run.setdefault(int(r), []).append(float(v))
        bad_runs = sum(1 for v in per_run.values() if max(v) > 0)
        ks = sorted({k for k, _ in vals})
        iins = sorted({int(l.split(",")[2].replace("u", ""))
                       for l in open(mc).read().splitlines()[1:]})
        lines.append(f"- matrix: k in {ks}, Iin in {iins} uA, "
                     f"Vout {ra.MC_VOUT.replace(' ', '/')} V")
        lines.append(f"- runs: {len(runs)}, runs with any violation: "
                     f"{bad_runs} ({100*bad_runs/len(runs):.1f}%)")
        lines.append(f"- worst violation over all runs: "
                     f"{max(v for _, v in vals)*1e6:+.2f} uA")
    else:
        lines.append("- (still running or not executed)")
    lines.append("\n## Findings\n")
    best_j = max(range(len(vout)),
                 key=lambda j: sum(1 for key in ok if ok[key][j]))
    best_n = sum(1 for key in ok if ok[key][best_j])
    bad = sum(1 for r in rows if r["win_lo"] is None)
    worst_mid = max(abs(float(r["err_mid_lsb"])) for r in rows)
    lines.append(f"- Best common output bias: Vout = {vout[best_j]:.2f} V, "
                 f"{best_n}/128 (k,Iin) combos within half-LSB.")
    lines.append(f"- {bad}/128 combos never meet half-LSB anywhere in the "
                 f"{vout[0]:.2f}..{vout[-1]:.2f} V sweep.")
    lines.append(f"- Worst error at Vout = 0.9 V: {worst_mid:.2f} LSB.")
    lines.append("- Measured polarity is non-inverting in this testbench "
                 "(Iout ~ +k*Iin).")
    lines.append("- Residual error is an odd (S-shaped) compression that "
                 "grows with k; mismatch is secondary.\n")
    out = os.path.join(resdir, f"REPORT{prefix}.md")
    open(out, "w").write("\n".join(lines) + "\n")
    print("wrote", out)
    print("\n".join(lines[:8]))


if __name__ == "__main__":
    main()
