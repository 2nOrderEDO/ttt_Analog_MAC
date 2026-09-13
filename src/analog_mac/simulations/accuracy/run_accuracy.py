#!/usr/bin/env python3
"""Accuracy characterization driver for the EMMAC_Block_v2 cell.

Modes:
  nominal : full grid (k=1..8 x Iin=-8..7uA x Vout=0.2..1.6V) at mos_tt
  corner  : same grid for several .lib sections / temperatures
  mc      : mismatch Monte-Carlo, reduced Vout grid, max half-LSB violation per point

Ideal inverting transfer: Iout(measured at V2) = -k*Iin, error = i(v2) + k*Iin.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SIMDIR = os.path.dirname(HERE)
BASE = os.path.join(SIMDIR, "EMMAC_Accuracy.spice")
MULT_DEV = "@n.x2.xm27.nsg13_lv_nmos"

K_VALUES = list(range(1, 9))
IIN_VALUES_UA = list(range(-8, 8))
VOUT_START, VOUT_STOP, VOUT_STEP = 0.2, 1.6, 0.1

CONTROL_RE = re.compile(r"\.control.*?\.endc", re.S)


def detect_mult_device(base_text):
    """Return the ngspice @path of the device driven by wmul."""
    dev = model = top = None
    for line in base_text.splitlines():
        if "m={wmul}" in line:
            toks = line.split()
            dev, model = toks[0].lower(), toks[5]
        m = re.match(r"^(x\w+)\s+.*\bEMMAC_Block\w*\b", line)
        if m:
            top = m.group(1)
    if dev is None or top is None:
        raise SystemExit("could not auto-detect the wmul device; "
                         "use --mult-device")
    return f"@n.{top}.{dev}.n{model}"



def iin_tag(iin):
    return "0" if iin == 0 else f"{iin}u"


def make_deck(base_text, lv, hv, control, temp=None):
    text = base_text.replace(".lib cornerMOSlv.lib mos_tt",
                             f".lib cornerMOSlv.lib {lv}")
    text = text.replace(".lib cornerMOShv.lib mos_tt",
                        f".lib cornerMOShv.lib {hv}")
    text = CONTROL_RE.sub(control, text, count=1)
    if temp is not None:
        head, sep, tail = text.rpartition(".end")
        text = f"{head}.temp {temp}\n{sep}{tail}"
    return text


def nominal_control(outdir):
    iins = " ".join("0" if v == 0 else f"{v}u" for v in IIN_VALUES_UA)
    ks = " ".join(str(k) for k in K_VALUES)
    return f""".control
set noaskquit
set filetype=ascii
option savecurrents
foreach k {ks}
  alter {MULT_DEV}[mult] = $k
  foreach iin {iins}
    alter i0 = $iin
    dc V2 {VOUT_START} {VOUT_STOP} {VOUT_STEP}
    write {outdir}/k$k/i$iin/acc.raw
  end
end
.endc
"""


def mc_control(runs, sign, ks=K_VALUES, iins=IIN_VALUES_UA):
    iins_s = " ".join("0" if v == 0 else f"{v}u" for v in iins)
    ks_s = " ".join(str(k) for k in ks)
    return f""".control
set noaskquit
foreach run {runs}
  reset
  foreach k {ks_s}
    alter {MULT_DEV}[mult] = $k
    foreach iin {iins_s}
      alter i0 = $iin
      dc V2 0.4 1.4 0.5
      let aerr = abs(v2#branch + {sign}*$k*$iin)
      let viol = aerr - 0.5*$k*1e-6
      meas dc vmax MAX viol
      echo "MC $run $k $iin"
    end
  end
end
.endc
"""


def prepare_grid(outdir):
    for k in K_VALUES:
        for iin in IIN_VALUES_UA:
            os.makedirs(os.path.join(outdir, f"k{k}", f"i{iin_tag(iin)}"),
                        exist_ok=True)


def parse_ascii_raw(path):
    with open(path) as fh:
        lines = fh.read().splitlines()
    nvars = npoints = var_start = val_start = None
    for i, line in enumerate(lines):
        if line.startswith("No. Variables:"):
            nvars = int(line.split(":")[1])
        elif line.startswith("No. Points:"):
            npoints = int(line.split(":")[1])
        elif line.startswith("Variables:"):
            var_start = i + 1
        elif line.startswith("Values:"):
            val_start = i + 1
            break
    names = []
    for j in range(nvars):
        parts = lines[var_start + j].split("\t")
        names.append(parts[2] if len(parts) > 2 else parts[-1])
    data = {n: [] for n in names}
    i = val_start
    for _ in range(npoints):
        while i < len(lines) and not lines[i].strip():
            i += 1
        row = lines[i].split("\t")
        vals = [row[1]] if len(row) > 1 else [row[0]]
        i += 1
        while len(vals) < nvars:
            while i < len(lines) and not lines[i].strip():
                i += 1
            vals.append(lines[i].split("\t")[-1])
            i += 1
        for n, v in zip(names, vals):
            data[n].append(float(v))
    return data


def longest_true_run(vals):
    best = (0, -1)
    start = None
    for i, v in enumerate(vals + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start > best[1] - best[0] + 1:
                best = (start, i - 1)
            start = None
    if best[1] < best[0]:
        return None, None
    return best


def analyze_nominal(rundir, sign):
    rows = []
    for k in K_VALUES:
        for iin in IIN_VALUES_UA:
            path = os.path.join(rundir, f"k{k}", f"i{iin_tag(iin)}", "acc.raw")
            d = parse_ascii_raw(path)
            vout = d["v(v-sweep)"]
            iout = d["i(v2)"]
            vin = d["v(net2)"]
            ideal = -sign * k * iin * 1e-6
            err = [x - ideal for x in iout]
            lsb = k * 1e-6
            ok = [abs(e) < 0.5 * lsb for e in err]
            lo, hi = longest_true_run(ok)
            mid = min(range(len(vout)), key=lambda j: abs(vout[j] - 0.9))
            rows.append(dict(k=k, iin=iin, vout_mid=vout[mid],
                             iout_mid=iout[mid], err_mid=err[mid],
                             err_mid_lsb=err[mid] / lsb,
                             max_err=max(abs(e) for e in err),
                             max_err_lsb=max(abs(e) for e in err) / lsb,
                             win_lo=(vout[lo] if lo is not None else None),
                             win_hi=(vout[hi] if hi is not None else None),
                             vin_mid=vin[mid]))
    return rows


def print_nominal_summary(rows, sign):
    print(f"ideal transfer: Iout = {-sign}*k*Iin  (sign={sign})")
    print(f"{'k':>2} {'max|err|/LSB':>12} {'max|err|(uA)':>13} "
          f"{'err@0.9V(k=1..)':>15} {'compliance window (V)':>22}")
    for k in K_VALUES:
        kr = [r for r in rows if r["k"] == k]
        worst = max(kr, key=lambda r: r["max_err"])
        emid = max(abs(r["err_mid"]) for r in kr) * 1e6
        los = [r["win_lo"] for r in kr if r["win_lo"] is not None]
        his = [r["win_hi"] for r in kr if r["win_hi"] is not None]
        nok = sum(1 for r in kr if r["win_lo"] is not None)
        win = f"{min(los):.2f} .. {max(his):.2f} ({nok}/16)" if los else "none"
        print(f"{k:>2} {worst['max_err_lsb']:>12.3f} "
              f"{worst['max_err']*1e6:>13.3f} {emid:>15.3f} {win:>22}")
    bad = [r for r in rows if r["win_lo"] is None]
    if bad:
        print(f"\nFAIL: {len(bad)} (k,Iin) combos never meet the half-LSB "
              f"criterion over the Vout sweep:")
        for r in sorted(bad, key=lambda r: (r["k"], r["iin"]))[:16]:
            print(f"  k={r['k']} Iin={r['iin']:>3}uA  "
                  f"max|err|={r['max_err']*1e6:.3f}uA "
                  f"({r['max_err_lsb']:.2f} LSB)  vout=0.9: "
                  f"{r['err_mid']*1e6:+.3f}uA")
    else:
        print("\nPASS: half-LSB criterion met somewhere in the sweep for all "
              "(k,Iin).")


def run_nominal(args):
    rundir = os.path.join(HERE, args.outdir or f"nominal{args.prefix}")
    if not args.analyze_only:
        shutil.rmtree(rundir, ignore_errors=True)
        os.makedirs(rundir)
        prepare_grid(rundir)
        deck = make_deck(open(BASE).read(), args.lv, args.hv,
                         nominal_control(rundir), args.temp)
        deck_path = os.path.join(rundir, "deck.spice")
        open(deck_path, "w").write(deck)
        log = os.path.join(rundir, "ngspice.log")
        with open(log, "w") as fh:
            subprocess.run(["ngspice", "-b", deck_path], cwd=rundir,
                           stdout=fh, stderr=subprocess.STDOUT, check=False)
    rows = analyze_nominal(rundir, args.sign)
    csv = os.path.join(rundir, "summary.csv")
    with open(csv, "w") as fh:
        keys = list(rows[0].keys())
        fh.write(",".join(keys) + "\n")
        for r in rows:
            fh.write(",".join(str(r[k]) for k in keys) + "\n")
    print_nominal_summary(rows, args.sign)
    print(f"\nresults: {rundir}")


def run_corners(args):
    sections = ["mos_tt", "mos_ss", "mos_ff", "mos_sf", "mos_fs"]
    temps = args.temps.split(",") if args.temps else [None]
    for sec in sections:
        for temp in temps:
            tag = sec.replace("mos_", "") + (f"_t{temp}" if temp else "")
            outdir = os.path.join(HERE, f"corner{args.prefix}_{tag}")
            shutil.rmtree(outdir, ignore_errors=True)
            os.makedirs(outdir)
            prepare_grid(outdir)
            deck = make_deck(open(BASE).read(), sec, sec,
                             nominal_control(outdir), temp)
            deck_path = os.path.join(outdir, "deck.spice")
            open(deck_path, "w").write(deck)
            log = os.path.join(outdir, "ngspice.log")
            with open(log, "w") as fh:
                subprocess.run(["ngspice", "-b", deck_path], cwd=outdir,
                               stdout=fh, stderr=subprocess.STDOUT, check=False)
            rows = analyze_nominal(outdir, args.sign)
            with open(os.path.join(outdir, "summary.csv"), "w") as fh:
                keys = list(rows[0].keys())
                fh.write(",".join(keys) + "\n")
                for r in rows:
                    fh.write(",".join(str(r[k]) for k in keys) + "\n")
            bad = [r for r in rows if r["win_lo"] is None]
            warn = sum(1 for r in rows if r["max_err_lsb"] >= 1.0)
            print(f"{tag:>10}: combos never meeting criterion: {len(bad):>3}, "
                  f"max|err|>1LSB: {warn:>3}, "
                  f"worst LSB err: {max(r['max_err_lsb'] for r in rows):.2f}")


def run_mc(args):
    rundir = os.path.join(HERE, args.outdir or f"mc{args.prefix}")
    os.makedirs(rundir, exist_ok=True)
    chunk = args.chunk_size or args.runs
    if args.mc_set == "reduced":
        ks = [1, 2, 4, 8]
        iins = [-4, -1, 0, 1, 4]
    else:
        ks = K_VALUES
        iins = IIN_VALUES_UA
    results = {}
    meas_re = re.compile(r"^\S+\s+=\s+(\S+)(?:\s+at=\s+(\S+))?")
    mc_re = re.compile(r"^MC\s+(\d+)\s+(\d+)\s+(\S+)")
    nchunks = (args.runs + chunk - 1) // chunk
    for c in range(nchunks):
        lo = c * chunk + 1
        hi = min(args.runs, lo + chunk - 1)
        cdir = os.path.join(rundir, f"chunk_{c:02d}")
        os.makedirs(cdir, exist_ok=True)
        runs = " ".join(str(i) for i in range(1, hi - lo + 2))
        deck = make_deck(open(BASE).read(), "mos_tt_mismatch",
                         "mos_tt_mismatch",
                         mc_control(runs, args.sign, ks, iins), args.temp)
        deck_path = os.path.join(cdir, "deck.spice")
        open(deck_path, "w").write(deck)
        log = os.path.join(cdir, "ngspice.log")
        with open(log, "w") as fh:
            subprocess.run(["ngspice", "-b", deck_path], cwd=cdir,
                           stdout=fh, stderr=subprocess.STDOUT, check=False)
        cur = None
        for line in open(log):
            m = mc_re.match(line)
            if m:
                cur = (int(m.group(1)) + lo - 1, int(m.group(2)),
                       m.group(3))
                continue
            m = meas_re.match(line)
            if m and cur:
                results[cur] = float(m.group(1))
                cur = None
        print(f"chunk {c + 1}/{nchunks} done "
              f"(runs {lo}..{hi}), {len(results)} points total",
              flush=True)
    if not results:
        print("no MC results parsed; check", rundir)
        sys.exit(1)
    runs_done = sorted({r for r, _, _ in results})
    per_run_max = {r: max(v for (rr, _, _), v in results.items() if rr == r)
                   for r in runs_done}
    viol = [v for v in per_run_max.values() if v > 0]
    yield_pct = 100.0 * (len(runs_done) - len(viol)) / len(runs_done)
    worst = max(results.values())
    print(f"MC runs: {len(runs_done)}  sign={args.sign}")
    print(f"runs with any half-LSB violation: {len(viol)} "
          f"({100 - yield_pct:.2f}%)")
    print(f"worst violation: {worst*1e6:+.3f} uA "
          f"(positive = out of spec)")
    k_viol = {}
    for (r, k, iin), v in results.items():
        if v > 0:
            k_viol.setdefault(k, 0)
            k_viol[k] += 1
    if k_viol:
        print("violations per k:", {k: k_viol[k] for k in sorted(k_viol)})
    with open(os.path.join(rundir, "mc_results.csv"), "w") as fh:
        fh.write("run,k,iin,violation\n")
        for (r, k, iin), v in sorted(results.items()):
            fh.write(f"{r},{k},{iin},{v}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["nominal", "corners", "mc"],
                    default="nominal")
    ap.add_argument("--lv", default="mos_tt")
    ap.add_argument("--hv", default="mos_tt")
    ap.add_argument("--temp", type=float, default=None)
    ap.add_argument("--temps", default=None,
                    help="comma separated temperatures for --mode corners")
    ap.add_argument("--runs", type=int, default=200)
    ap.add_argument("--mc-set", choices=["full", "reduced"], default="full",
                    help="reduced: k in {1,2,4,8}, Iin in {-4,-1,0,1,4}")
    ap.add_argument("--chunk-size", type=int, default=20,
                    help="runs per ngspice invocation (MC mode)")
    ap.add_argument("--sign", type=float, default=1.0,
                    help="1.0 if ideal v2#branch = -k*Iin, -1.0 otherwise")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--prefix", default="",
                    help="suffix for default output dirs, e.g. '_v3'")
    ap.add_argument("--netlist", default="EMMAC_Accuracy.spice",
                    help="netlist path relative to simulations/")
    ap.add_argument("--mult-device", default=None,
                    help="ngspice @path of the wmul device (auto-detected)")
    ap.add_argument("--analyze-only", action="store_true")
    args = ap.parse_args()
    global BASE, MULT_DEV
    BASE = os.path.join(SIMDIR, args.netlist)
    base_text = open(BASE).read()
    MULT_DEV = args.mult_device or detect_mult_device(base_text)
    print(f"netlist: {BASE}\nwmul device: {MULT_DEV}")
    if args.mode == "nominal":
        run_nominal(args)
    elif args.mode == "corners":
        run_corners(args)
    else:
        run_mc(args)


if __name__ == "__main__":
    main()
