#!/usr/bin/env python3
"""Sweep (k, Iin) DC operating points and dump device ids/gds/vds/gm.

Simulation-only diagnostic; no schematic changes. Writes probe_<prefix>.csv
in the accuracy directory plus the ngspice log in probe<prefix>/.
"""
import argparse
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SIMDIR = os.path.dirname(HERE)

PARAMS = ["ids", "gds", "vds", "gm"]


def detect_top(base_text):
    for line in base_text.splitlines():
        m = re.match(r"^(x\w+)\s+.*\bEMMAC_Block\w*\b", line)
        if m:
            return m.group(1)
    raise SystemExit("top-level EMMAC_Block instance not found")


def detect_mult_devices(base_text):
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


def parse_devices(base_text):
    devs = {}
    inside = False
    for line in base_text.splitlines():
        if line.startswith(".subckt EMMAC_Block"):
            inside = True
            continue
        if inside and line.startswith(".ends"):
            break
        if inside:
            m = re.match(r"^XM(\d+)\s+\S+\s+\S+\s+\S+\s+\S+\s+(\S+)", line)
            if m:
                devs[m.group(1)] = m.group(2)
    return devs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--netlist", default="EMMAC_Accuracy_v3.spice")
    ap.add_argument("--prefix", default="_v3")
    ap.add_argument("--vout", default="0.6")
    ap.add_argument("--outdir", default=None,
                    help="base dir for probe<prefix>/ and probe<prefix>.csv")
    ap.add_argument("--mult-device", default=None)
    ap.add_argument("--isrc", default="i0")
    ap.add_argument("--vsrc", default="v2")
    args = ap.parse_args()

    base_path = os.path.join(SIMDIR, args.netlist)
    base = open(base_path).read()
    top = detect_top(base)
    devs = parse_devices(base)
    mdevs = ([d.strip() for d in args.mult_device.split(",")]
             if args.mult_device else detect_mult_devices(base))
    print(f"{len(devs)} devices: {sorted(devs, key=int)}")
    print(f"wmul devices: {mdevs}")

    outdir = args.outdir or HERE
    rundir = os.path.join(outdir, f"probe{args.prefix}")
    os.makedirs(rundir, exist_ok=True)

    lines = [".control", "set noaskquit"]
    for k in range(1, 9):
        for d in mdevs:
            lines.append(f"alter {d}[mult] = {k}")
        for iin in range(-8, 8):
            lines.append(f"alter {args.isrc} = "
                         f"{'0' if iin == 0 else f'{iin}u'}")
            lines.append(f"alter {args.vsrc} = {args.vout}")
            lines.append("op")
            lines.append(f'echo "PT {k} {iin}"')
            for num, model in devs.items():
                path = f"@n.{top}.xm{num}.n{model}"
                for p in PARAMS:
                    lines.append(f"print {path}[{p}]")
    lines += [".endc", ".end", ""]
    control = "\n".join(lines)
    deck = re.sub(r"\.control.*?\.endc", control, base, flags=re.S, count=1)
    deck_path = os.path.join(rundir, "deck.spice")
    open(deck_path, "w").write(deck)
    log = os.path.join(rundir, "ngspice.log")
    with open(log, "w") as fh:
        subprocess.run(["ngspice", "-b", deck_path], cwd=rundir,
                       stdout=fh, stderr=subprocess.STDOUT, check=False)

    pt_re = re.compile(r"^PT\s+(\d+)\s+(-?\d+)")
    pr_re = re.compile(r"^@n\.\S+\.(xm(\d+))\.(\S+)\[(\w+)\] = (\S+)")
    cur = None
    rows = []
    data = {}
    for line in open(log):
        m = pt_re.match(line)
        if m:
            cur = (int(m.group(1)), int(m.group(2)))
            data[cur] = {}
            continue
        m = pr_re.match(line)
        if m and cur is not None:
            dev, num, model, param = m.group(1), m.group(2), m.group(3), m.group(4)
            data[cur].setdefault(num, {})[param] = float(m.group(5))
    out = os.path.join(outdir, f"probe{args.prefix}.csv")
    with open(out, "w") as fh:
        fh.write("k,iin,dev,ids,gds,vds,gm\n")
        for (k, iin), d in sorted(data.items()):
            for num, vals in sorted(d.items(), key=lambda x: int(x[0])):
                fh.write(f"{k},{iin},{num},"
                         f"{vals.get('ids','')},{vals.get('gds','')},"
                         f"{vals.get('vds','')},{vals.get('gm','')}\n")
    print(f"wrote {out} ({len(rows)} rows header)")


if __name__ == "__main__":
    main()
