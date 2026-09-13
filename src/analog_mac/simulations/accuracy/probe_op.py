#!/usr/bin/env python3
"""One-off op probe at k=8, Iin=+7u, Vout=0.9."""
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..", "EMMAC_Accuracy.spice")
base = open(BASE).read()
devs = [(20, "pmos"), (23, "pmos"), (24, "pmos"), (25, "pmos"),
        (28, "pmos"), (29, "pmos"), (12, "nmos"), (13, "nmos"),
        (26, "nmos"), (27, "nmos"), (30, "nmos"), (31, "nmos")]
lines = [".control", "set noaskquit",
         "alter @n.x2.xm27.nsg13_lv_nmos[mult] = 8",
         "alter i0 = 7u", "alter v2 = 0.9", "op"]
for d, t in devs:
    lines.append(f"print @n.x2.xm{d}.nsg13_lv_{t}[ids]")
for node in [9, 10, 11, 12, 13, 14, 15, 16, 17]:
    lines.append(f"print v(x2.net{node})")
lines += [".endc", ".end", ""]
ctrl = "\n".join(lines)
deck = re.sub(r"\.control.*?\.endc", ctrl, base, flags=re.S, count=1)
outdir = "/tmp/opencode/probe2"
os.makedirs(outdir, exist_ok=True)
open(os.path.join(outdir, "deck.spice"), "w").write(deck)
r = subprocess.run(["ngspice", "-b", "deck.spice"], cwd=outdir,
                   capture_output=True, text=True)
for line in r.stdout.splitlines():
    if ("@n." in line or "v(x2.net" in line) and "=" in line:
        print(line)
