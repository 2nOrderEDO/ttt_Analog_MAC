#!/usr/bin/env python3
"""Accuracy characterization driver for the EMMAC cell.

Modes:
  nominal : full grid (k=1..8 x Iin=-8..7uA x Vout sweep) at mos_tt
  corner  : same grid for several .lib sections / temperatures
  mc      : mismatch Monte-Carlo, max half-LSB violation per point

Ideal transfer: Iout(measured at V2) = -sign*k*Iin, error = i(v2)+sign*k*Iin.

Parallelism:
  --jobs N  grid modes run one ngspice per (corner, k) task; MC runs one
  ngspice per chunk. Each worker gets OMP_NUM_THREADS=1.

Server layout:
  --netlist is resolved against the parent directory of this script
  (e.g. --netlist circuits/EMMAC_Accuracy_v3.spice when scripts/ and
  circuits/ are siblings). Outputs go under --results-dir.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
SIMDIR = os.path.dirname(HERE)

K_VALUES = list(range(1, 9))
IIN_VALUES_UA = list(range(-8, 8))
VOUT_START, VOUT_STOP, VOUT_STEP = 0.1, 1.3, 0.1
MC_VOUT = "0.2 1.1 0.45"

CONTROL_RE = re.compile(r"\.control.*?\.endc", re.S)
MEAS_RE = re.compile(r"^\S+\s+=\s+(\S+)(?:\s+at=\s+(\S+))?")
MC_RE = re.compile(r"^MC\s+(\d+)\s+(\d+)\s+(\S+)")

WORKER_THREADS = 1  # OMP threads per ngspice worker (set from --worker-threads)
ISRC = "i0"         # testbench input current source name (--isrc)
VSRC = "v2"         # testbench output voltage source name (--vsrc)


def detect_mult_devices(base_text):
    """Return ngspice @paths of all devices driven by wmul."""
    found = []
    top = None
    for line in base_text.splitlines():
        if "m={wmul}" in line:
            toks = line.split()
            found.append((toks[0].lower(), toks[5]))
        m = re.match(r"^(x\w+)\s+.*\bEMMAC_Block\w*\b", line)
        if m:
            top = m.group(1)
    if not found or top is None:
        raise SystemExit("could not auto-detect the wmul device(s); "
                         "use --mult-device")
    return [f"@n.{top}.{dev}.n{model}" for dev, model in found]


def iin_tag(iin):
    return "0" if iin == 0 else f"{iin}u"


def iins_arg(values=None):
    values = IIN_VALUES_UA if values is None else values
    return " ".join("0" if v == 0 else f"{v}u" for v in values)


def make_deck(base_text, lv, hv, control, temp=None):
    text = base_text.replace(".lib cornerMOSlv.lib mos_tt",
                             f".lib cornerMOSlv.lib {lv}")
    text = text.replace(".lib cornerMOShv.lib mos_tt",
                        f".lib cornerMOShv.lib {hv}")
    dio = lv.replace("mos_", "dio_")
    text = text.replace(".lib cornerDIO.lib dio_tt",
                        f".lib cornerDIO.lib {dio}")
    text = CONTROL_RE.sub(control, text, count=1)
    if temp is not None:
        head, sep, tail = text.rpartition(".end")
        text = f"{head}.temp {temp}\n{sep}{tail}"
    return text


def nominal_control(outdir, devs, isrc, vsrc):
    ks = " ".join(str(k) for k in K_VALUES)
    alts = "\n".join(f"  alter {d}[mult] = $k" for d in devs)
    return f""".control
set noaskquit
set filetype=ascii
option savecurrents
save all
foreach k {ks}
{alts}
  foreach iin {iins_arg()}
    alter {isrc} = $iin
    dc {vsrc} {VOUT_START} {VOUT_STOP} {VOUT_STEP}
    write {outdir}/k$k/i$iin/acc.raw
  end
end
.endc
"""


def nominal_control_k(outdir, devs, k, isrc, vsrc):
    alts = "\n".join(f"alter {d}[mult] = {k}" for d in devs)
    return f""".control
set noaskquit
set filetype=ascii
option savecurrents
save all
{alts}
foreach iin {iins_arg()}
  alter {isrc} = $iin
  dc {vsrc} {VOUT_START} {VOUT_STOP} {VOUT_STEP}
  write {outdir}/k{k}/i$iin/acc.raw
end
.endc
"""


def mc_control(runs, sign, devs, ks, iins, isrc, vsrc):
    ks_s = " ".join(str(k) for k in ks)
    alts = "\n".join(f"    alter {d}[mult] = $k" for d in devs)
    return f""".control
set noaskquit
foreach run {runs}
  reset
  foreach k {ks_s}
{alts}
    foreach iin {iins_arg(iins)}
      alter {isrc} = $iin
      dc {vsrc} {MC_VOUT}
      let aerr = abs({vsrc}#branch + {sign}*$k*$iin)
      let viol = aerr - 0.5*$k*1e-6
      meas dc vmax MAX viol
      echo "MC $run $k $iin"
    end
  end
end
.endc
"""


def prepare_grid(outdir, ks=None):
    for k in (K_VALUES if ks is None else ks):
        for iin in IIN_VALUES_UA:
            os.makedirs(os.path.join(outdir, f"k{k}", f"i{iin_tag(iin)}"),
                        exist_ok=True)


def resolve_out(args, default_name):
    if args.outdir:
        return (args.outdir if os.path.isabs(args.outdir)
                else os.path.join(HERE, args.outdir))
    return os.path.join(args.results_dir or HERE, default_name)


def run_ngspice(deck_text, cwd, worker_threads=1):
    """Write deck.spice in cwd and run ngspice single-threaded."""
    os.makedirs(cwd, exist_ok=True)
    deck_path = os.path.join(cwd, "deck.spice")
    with open(deck_path, "w") as fh:
        fh.write(deck_text)
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = str(worker_threads)
    log = os.path.join(cwd, "ngspice.log")
    with open(log, "w") as fh:
        subprocess.run(["ngspice", "-b", deck_path], cwd=cwd, env=env,
                       stdout=fh, stderr=subprocess.STDOUT, check=False)
    return log


def grid_task(task):
    """Run one (base_text, lv, hv, temp, outdir, dev, k) grid task."""
    control = nominal_control_k(task["outdir"], task["devs"], task["k"],
                                task["isrc"], task["vsrc"])
    deck = make_deck(task["base_text"], task["lv"], task["hv"], control,
                     task["temp"])
    return run_ngspice(deck, os.path.join(task["outdir"],
                                          f"_task_k{task['k']}"),
                       task["worker_threads"])


def corner_task(task):
    """Run one whole corner (all k) in a single ngspice process."""
    control = nominal_control(task["outdir"], task["devs"],
                              task["isrc"], task["vsrc"])
    deck = make_deck(task["base_text"], task["lv"], task["hv"], control,
                     task["temp"])
    return run_ngspice(deck, os.path.join(task["outdir"], "_task_corner"),
                       task["worker_threads"])


def mc_chunk_task(task):
    """Run one MC chunk and return {(run,k,iin): violation}."""
    runs = " ".join(str(i) for i in range(1, task["hi"] - task["lo"] + 2))
    control = mc_control(runs, task["sign"], task["devs"], task["ks"],
                         task["iins"], task["isrc"], task["vsrc"])
    deck = make_deck(task["base_text"], "mos_tt_mismatch",
                     "mos_tt_mismatch", control, task["temp"])
    log = run_ngspice(deck, task["cdir"], task["worker_threads"])
    return parse_mc_log(log, task["lo"])


def parse_mc_log(log, run_offset):
    results = {}
    cur = None
    for line in open(log):
        m = MC_RE.match(line)
        if m:
            cur = (int(m.group(1)) + run_offset - 1, int(m.group(2)),
                   m.group(3))
            continue
        m = MEAS_RE.match(line)
        if m and cur:
            results[cur] = float(m.group(1))
            cur = None
    return results


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


def get_vec(data, name):
    """Case-insensitive lookup of a raw vector name."""
    if name in data:
        return data[name]
    low = name.lower()
    for key, val in data.items():
        if key.lower() == low:
            return val
    raise KeyError(f"{name} not in raw (have {list(data)[:5]}...)")


def analyze_nominal(rundir, sign):
    rows = []
    for k in K_VALUES:
        for iin in IIN_VALUES_UA:
            path = os.path.join(rundir, f"k{k}", f"i{iin_tag(iin)}", "acc.raw")
            d = parse_ascii_raw(path)
            vout = d["v(v-sweep)"]
            iout = get_vec(d, f"i({VSRC})")
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


def write_csv(rows, path):
    with open(path, "w") as fh:
        keys = list(rows[0].keys())
        fh.write(",".join(keys) + "\n")
        for r in rows:
            fh.write(",".join(str(r[k]) for k in keys) + "\n")


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


def run_tasks(tasks, worker, jobs):
    if jobs and jobs > 1:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            for res in ex.map(worker, tasks):
                yield res
    else:
        for t in tasks:
            yield worker(t)


def run_nominal(args):
    rundir = resolve_out(args, f"nominal{args.prefix}")
    if not args.analyze_only:
        shutil.rmtree(rundir, ignore_errors=True)
        os.makedirs(rundir)
        prepare_grid(rundir)
        base_text = open(args.base).read()
        tasks = [dict(base_text=base_text, lv=args.lv, hv=args.hv,
                      temp=args.temp, outdir=rundir, devs=args.mult_devs,
                      isrc=args.isrc, vsrc=args.vsrc,
                      worker_threads=args.worker_threads, k=k)
                 for k in K_VALUES]
        for _ in run_tasks(tasks, grid_task, args.jobs):
            pass
    rows = analyze_nominal(rundir, args.sign)
    write_csv(rows, os.path.join(rundir, "summary.csv"))
    print_nominal_summary(rows, args.sign)
    print(f"\nresults: {rundir}")


def run_corners(args):
    sections = ["mos_tt", "mos_ss", "mos_ff", "mos_sf", "mos_fs"]
    temps = args.temps.split(",") if args.temps else [None]
    resdir = args.results_dir or HERE
    base_text = open(args.base).read()
    tasks = []
    for sec in sections:
        for temp in temps:
            tag = sec.replace("mos_", "") + (f"_t{temp}" if temp else "")
            outdir = os.path.join(resdir, f"corner{args.prefix}_{tag}")
            shutil.rmtree(outdir, ignore_errors=True)
            os.makedirs(outdir)
            prepare_grid(outdir)
            if args.granularity == "corner":
                tasks.append(dict(base_text=base_text, lv=sec, hv=sec,
                                  temp=temp, outdir=outdir,
                                  devs=args.mult_devs, tag=tag,
                                  isrc=args.isrc, vsrc=args.vsrc,
                                  worker_threads=args.worker_threads))
            else:
                for k in K_VALUES:
                    tasks.append(dict(base_text=base_text, lv=sec, hv=sec,
                                      temp=temp, outdir=outdir,
                                      devs=args.mult_devs, k=k, tag=tag,
                                      isrc=args.isrc, vsrc=args.vsrc,
                                      worker_threads=args.worker_threads))
    worker = grid_task if args.granularity == "k" else corner_task
    for _ in run_tasks(tasks, worker, args.jobs):
        pass
    for sec in sections:
        for temp in temps:
            tag = sec.replace("mos_", "") + (f"_t{temp}" if temp else "")
            outdir = os.path.join(resdir, f"corner{args.prefix}_{tag}")
            rows = analyze_nominal(outdir, args.sign)
            write_csv(rows, os.path.join(outdir, "summary.csv"))
            bad = [r for r in rows if r["win_lo"] is None]
            warn = sum(1 for r in rows if r["max_err_lsb"] >= 1.0)
            print(f"{tag:>10}: combos never meeting criterion: {len(bad):>3}, "
                  f"max|err|>1LSB: {warn:>3}, "
                  f"worst LSB err: {max(r['max_err_lsb'] for r in rows):.2f}")


def run_mc(args):
    rundir = resolve_out(args, f"mc{args.prefix}")
    os.makedirs(rundir, exist_ok=True)
    chunk = args.chunk_size or args.runs
    if args.mc_set == "reduced":
        ks = [1, 2, 4, 8]
        iins = [-4, -1, 0, 1, 4]
    else:
        ks = K_VALUES
        iins = IIN_VALUES_UA
    base_text = open(args.base).read()
    nchunks = (args.runs + chunk - 1) // chunk
    tasks = []
    for c in range(nchunks):
        lo = c * chunk + 1
        hi = min(args.runs, lo + chunk - 1)
        tasks.append(dict(base_text=base_text, cdir=os.path.join(
            rundir, f"chunk_{c:02d}"), lo=lo, hi=hi, sign=args.sign,
            devs=args.mult_devs, ks=ks, iins=iins, temp=args.temp, c=c,
            isrc=args.isrc, vsrc=args.vsrc,
            worker_threads=args.worker_threads))
    results = {}
    for c, chunk_res in enumerate(run_tasks(tasks, mc_chunk_task, args.jobs)):
        results.update(chunk_res)
        print(f"chunk {c + 1}/{nchunks} done, {len(results)} points total",
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
    print(f"worst violation: {worst*1e6:+.3f} uA (positive = out of spec)")
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
    ap.add_argument("--outdir", default=None,
                    help="explicit output dir (overrides --results-dir)")
    ap.add_argument("--results-dir", default=None,
                    help="base output dir (default: directory of this script)")
    ap.add_argument("--prefix", default="",
                    help="suffix for default output dirs, e.g. '_v3'")
    ap.add_argument("--jobs", type=int, default=1,
                    help="parallel ngspice tasks (grid: per (corner,k), "
                         "MC: per chunk)")
    ap.add_argument("--worker-threads", type=int, default=1,
                    help="OMP_NUM_THREADS per ngspice worker (default 1; "
                         "on many-core servers keep 1 and raise --jobs)")
    ap.add_argument("--granularity", choices=["k", "corner"], default="k",
                    help="corner grid task size: 'k' (one ngspice per k, "
                         "best with many cores) or 'corner' (one ngspice per "
                         "corner, best with --worker-threads>1)")
    ap.add_argument("--netlist", default="EMMAC_Accuracy.spice",
                    help="netlist path relative to the parent of scripts/")
    ap.add_argument("--mult-device", default=None,
                    help="comma-separated ngspice @paths of the wmul "
                         "device(s); auto-detected if omitted")
    ap.add_argument("--isrc", default="i0",
                    help="testbench input current source name (default i0)")
    ap.add_argument("--vsrc", default="v2",
                    help="testbench output voltage source name (default v2)")
    ap.add_argument("--analyze-only", action="store_true")
    args = ap.parse_args()
    global WORKER_THREADS, ISRC, VSRC
    WORKER_THREADS = args.worker_threads
    ISRC, VSRC = args.isrc, args.vsrc
    os.environ["OMP_NUM_THREADS"] = str(WORKER_THREADS)
    args.base = os.path.join(SIMDIR, args.netlist)
    base_text = open(args.base).read()
    if args.mult_device:
        args.mult_devs = [d.strip() for d in args.mult_device.split(",")]
    else:
        args.mult_devs = detect_mult_devices(base_text)
    print(f"netlist: {args.base}\nwmul devices: {args.mult_devs}"
          f"\nsources: isrc={ISRC} vsrc={VSRC}")
    if args.mode == "nominal":
        run_nominal(args)
    elif args.mode == "corners":
        run_corners(args)
    else:
        run_mc(args)


if __name__ == "__main__":
    main()
