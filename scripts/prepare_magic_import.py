#!/usr/bin/env python3
"""Make an xschem netlist ready for magic's File -> Import SPICE.

Two things magic's PDK import path requires that xschem output does not give:

  1. `w=` / `l=` values without unit suffixes (magic's device generator
     expects plain microns; with `0.15u` it clamps every device to minimum).
  2. An uncommented `.subckt` / `.ends` pair (xschem comments out the
     top-level cell definition, and magic only generates `.subckt` blocks).
     The file stem must equal the subckt name, so this edits in place.

Usage:
    python3 scripts/prepare_magic_import.py src/analog_mac/EMMAC_Block_v3_Layout.spice
"""

import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} <netlist.spice>")
    path = Path(sys.argv[1])
    text = path.read_text()

    unit_tokens = []
    for line in text.splitlines():
        if line.startswith("*"):
            continue
        for token in line.split():
            if token.startswith(("w=", "l=")) and token[-1].isalpha():
                unit_tokens.append(token)
    if unit_tokens:
        raise SystemExit("w/l values still carry units: "
                         + ", ".join(sorted(set(unit_tokens))))

    text, n_sub = re.subn(r"^\*\*(\.subckt\b)", r"\1", text,
                          count=1, flags=re.M)
    text, n_end = re.subn(r"^\*\*(\.ends\b)", r"\1", text,
                          count=1, flags=re.M)
    if not (n_sub and n_end):
        raise SystemExit("commented .subckt/.ends lines not found")

    path.write_text(text)
    print(f"updated {path}")


if __name__ == "__main__":
    main()
