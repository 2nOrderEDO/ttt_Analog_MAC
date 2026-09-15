#!/usr/bin/env python3
"""Create cascode diagnostic netlists from EMMAC_Accuracy_v3.spice.

Variants: c1 (M28/M29/M20 PMOS output+ref), c2 (M23/M24),
          c3 (M12/M13 NMOS output+ref), c4 (M26/M27 multiplier),
          all (c1+c2+c3+c4).
Cascode gates are driven by ideal sources (VBP/VBN/VBN2) inside the subckt.
"""
import argparse
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SIMDIR = os.path.dirname(HERE)

W_P = "w=1u l=0.28u ng=1"       # M35/M36 (quiet branch)
W_PC = "w=4u l=0.28u ng=1"      # output/ref cascodes (hi current)
W_N = "w=1u l=1u ng=1"          # M39
W_NC = "w=2u l=1u ng=1"         # NMOS output cascodes

RECIPES = {
    "c1": [
        ("XM28 net12 net12 VDD VDD sg13_lv_pmos w=1u l=0.28u ng=1",
         "XM28 n28g n28g VDD VDD sg13_lv_pmos w=1u l=0.28u ng=1\n"
         "XM32 net12 vbp n28g VDD sg13_lv_pmos " + W_PC),
        ("XM29 net9 net12 VDD VDD sg13_lv_pmos w=1u l=0.28u ng=1",
         "XM29 n29s n28g VDD VDD sg13_lv_pmos w=1u l=0.28u ng=1\n"
         "XM33 net9 vbp n29s VDD sg13_lv_pmos " + W_PC),
        ("XM20 OUT net16 VDD VDD sg13_lv_pmos w=1u l=0.28u ng=1",
         "XM20 n20s net16 VDD VDD sg13_lv_pmos w=1u l=0.28u ng=1\n"
         "XM34 OUT vbp n20s VDD sg13_lv_pmos " + W_PC),
        ("XM10 net16 net10 net12 VDD sg13_lv_pmos w=1u l=0.28u ng=1",
         "XM10 net16 net10 n28g VDD sg13_lv_pmos w=1u l=0.28u ng=1"),
    ],
    "c2": [
        ("XM23 net4 net4 VDD VDD sg13_lv_pmos w=1u l=0.28u ng=1",
         "XM23 n23g n23g VDD VDD sg13_lv_pmos w=1u l=0.28u ng=1\n"
         "XM35 net4 vbp2 n23g VDD sg13_lv_pmos " + W_P),
        ("XM24 net14 net4 VDD VDD sg13_lv_pmos w=1u l=0.28u ng=1",
         "XM24 n24s n23g VDD VDD sg13_lv_pmos w=1u l=0.28u ng=1\n"
         "XM36 net14 vbp2 n24s VDD sg13_lv_pmos " + W_P),
    ],
    "c3": [
        ("XM12 net9 net9 0 0 sg13_lv_nmos w=1u l=1u ng=1",
         "XM12 n12g n12g 0 0 sg13_lv_nmos w=1u l=1u ng=1\n"
         "XM37 net9 vbn n12g 0 sg13_lv_nmos " + W_NC),
        ("XM13 OUT net17 0 0 sg13_lv_nmos w=1u l=1u ng=1",
         "XM13 n13s net17 0 0 sg13_lv_nmos w=1u l=1u ng=1\n"
         "XM38 OUT vbn n13s 0 sg13_lv_nmos " + W_NC),
        ("XM25 net9 net10 net17 0 sg13_lv_nmos w=1u l=1u ng=1",
         "XM25 n12g net10 net17 0 sg13_lv_nmos w=1u l=1u ng=1"),
    ],
    "c4": [
        ("XM26 net15 net13 0 0 sg13_lv_nmos w=1u l=1u ng=1",
         "XM26 n26s net13 0 0 sg13_lv_nmos w=1u l=1u ng=1\n"
         "XM39 net15 vbn2 n26s 0 sg13_lv_nmos " + W_N),
    ],
}

BIAS = {
    "vbp": "Bbp vbp 0 V = v(n28g) - 0.7",
    "vbp2": "Bbp2 vbp2 0 V = v(n23g) - 0.7",
    "vbn": "Bbn vbn 0 V = v(n12g) + 0.7",
    "vbn2": "Bbn2 vbn2 0 V = v(n26s) + 0.7",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default="c1,c2,c3,c4,all")
    ap.add_argument("--netlist", default="EMMAC_Accuracy_v3.spice",
                    help="base netlist relative to the parent of scripts/")
    ap.add_argument("--outdir", default=None,
                    help="output dir for variant netlists (default: parent)")
    args = ap.parse_args()
    base_path = os.path.join(SIMDIR, args.netlist)
    stem = os.path.splitext(os.path.basename(base_path))[0]
    outdir = args.outdir or os.path.dirname(base_path)
    os.makedirs(outdir, exist_ok=True)
    base = open(base_path).read()
    for tag in args.variants.split(","):
        tags = ["c1", "c2", "c3", "c4"] if tag == "all" else [tag]
        text = base
        for t in tags:
            for old, new in RECIPES[t]:
                if old not in text:
                    raise SystemExit(f"recipe {t}: line not found: {old}")
                text = text.replace(old, new, 1)
        needed = {"c1": ["vbp"], "c2": ["vbp2"], "c3": ["vbn"],
                  "c4": ["vbn2"]}
        bias_lines = []
        for t in tags:
            for b in needed[t]:
                if BIAS[b] not in bias_lines:
                    bias_lines.append(BIAS[b])
        head, sep, tail = text.rpartition(".ends")
        text = head + "\n".join(bias_lines) + "\n" + sep + tail
        out = os.path.join(outdir, f"{stem}_{tag}.spice")
        open(out, "w").write(text)
        print("wrote", out)


if __name__ == "__main__":
    main()
