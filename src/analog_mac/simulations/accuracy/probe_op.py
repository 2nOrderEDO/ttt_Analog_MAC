#!/usr/bin/env python3
"""One-shot DC op probe: print device parameters at a given (k, Iin, Vout).

Generic: devices and their models are parsed from the netlist, the wmul
device is auto-detected. Useful for interactive diagnostics.
"""
import argparse
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SIMDIR = os.path.dirname(HERE)
PARAMS = ["ids", "gds", "vds", "gm"]
EXCLUDE = {"0", "VDD", "VSS", "IN", "OUT", "vbp", "vbn", "vbp2", "vbn2"}


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
        raise SystemExit("could not auto-detect the wmul device(s)")
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
    ap.add_argument("--netlist", default="EMMAC_Accuracy_v3.spice",
                    help="relative to the parent of scripts/")
    ap.add_argument("--k", default="8")
    ap.add_argument("--iin", default="7u")
    ap.add_argument("--vout", default="0.9")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--isrc", default="i0")
    ap.add_argument("--vsrc", default="v2")
    args = ap.parse_args()

    baseline = os.path.join(SIMDIR, args.netlist)
    base = open(baseline).read()
    top = detect_top(base)
    devs = parse_devices(base)
    mdevs = detect_mult_devices(base)

    outdir = args.outdir or os.path.join(HERE, "probe_op")
    os.makedirs(outdir, exist_ok=True)

    lines = [".control", "set noaskquit"]
    for d in mdevs:
        lines.append(f"alter {d}[mult] = {args.k}")
    lines += [f"alter {args.isrc} = {args.iin}",
              f"alter {args.vsrc} = {args.vout}", "op"]
    for num, model in sorted(devs.items(), key=lambda x: int(x[0])):
        for p in PARAMS:
            lines.append(f"print @n.{top}.xm{num}.n{model}[{p}]")
    lines += [".endc", ".end", ""]
    deck = re.sub(r"\.control.*?\.endc", "\n".join(lines), base,
                  flags=re.S, count=1)
    deck_path = os.path.join(outdir, "deck.spice")
    open(deck_path, "w").write(deck)
    r = subprocess.run(["ngspice", "-b", "deck.spice"], cwd=outdir,
                       capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith("@n.") and "=" in line:
            print(line)


if __name__ == "__main__":
    main()
