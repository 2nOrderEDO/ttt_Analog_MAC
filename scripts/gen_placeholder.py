#!/usr/bin/env python3
"""
Generate a Tiny Tapeout 1x1 custom-GDS *placeholder* macro (ihp-sg13g2, ttihp26b).

This produces a minimal, pin-compliant macro for slot reservation. It satisfies
the Tiny Tapeout precheck rules for the ihp-sg13g2 / tt_block_1x1_pgvdd template:

  * prBoundary.boundary (189/4) rectangle covering the full die
  * Metal4 signal stubs at the exact template pin coordinates
      - drawing  (50/0)
      - pin      (50/2)   <- required by pin_check
      - label    (50/25)
  * TopMetal1 full-height power stripes (VGND / VPWR)
      - drawing  (126/0)
      - pin      (126/2)  <- required by pin_check / power_pin_check
      - label    (126/25)
      (width >= 2.1 um, within 10 um of top and bottom edges)

The real EMMAC + DAC + SPI macro will replace this in later revisions with the
same footprint / pinout.

Run with KLayout's bundled python:
    klayout -b -z -nc -rx -r scripts/gen_placeholder.py

Outputs (relative to repo root):
    gds/<TOP>.gds
    lef/<TOP>.lef
"""

import pya  # KLayout python API

TOP = "tt_um_ttt_emamac_2nOrderEDO"

# ---------------------------------------------------------------------------
# Geometry constants (dbu = 1 nm = 0.001 um)
# ---------------------------------------------------------------------------
DBU_PER_UM = 1000
DIE_W = 202080   # 202.08 um
DIE_H = 154980   # 154.98 um

# GDS layer/datatype for IHP sg13g2 (libs.tech/klayout/tech/sg13g2.map / .lyp)
L_M4_DRAW = (50, 0)
L_M4_PIN = (50, 2)
L_M4_TEXT = (50, 25)
L_TM1_DRAW = (126, 0)
L_TM1_PIN = (126, 2)
L_TM1_TEXT = (126, 25)
L_PRBOUND = (189, 4)

# Signal pin geometry from tt_block_1x1_pgvdd.def:
#   LAYER Metal4 (-150 -500)(150 500) PLACED (x 154480) N
# => 300 nm wide (x) by 1000 nm tall (y), top edge at die top.
SIG_HALF_W = 150
SIG_HALF_H = 500
SIG_CY = 154480  # pin center y


def sig_rect(x):
    return pya.Box(x - SIG_HALF_W, SIG_CY - SIG_HALF_H,
                   x + SIG_HALF_W, SIG_CY + SIG_HALF_H)


# (name, x_center_nm, direction) -- x positions copied verbatim from the DEF.
SIGNAL_PINS = [
    ("clk",        187200, "INPUT"),
    ("ena",        191040, "INPUT"),
    ("rst_n",      183360, "INPUT"),
    ("ui_in[0]",   179520, "INPUT"),
    ("ui_in[1]",   175680, "INPUT"),
    ("ui_in[2]",   171840, "INPUT"),
    ("ui_in[3]",   168000, "INPUT"),
    ("ui_in[4]",   164160, "INPUT"),
    ("ui_in[5]",   160320, "INPUT"),
    ("ui_in[6]",   156480, "INPUT"),
    ("ui_in[7]",   152640, "INPUT"),
    ("uio_in[0]",  148800, "INPUT"),
    ("uio_in[1]",  144960, "INPUT"),
    ("uio_in[2]",  141120, "INPUT"),
    ("uio_in[3]",  137280, "INPUT"),
    ("uio_in[4]",  133440, "INPUT"),
    ("uio_in[5]",  129600, "INPUT"),
    ("uio_in[6]",  125760, "INPUT"),
    ("uio_in[7]",  121920, "INPUT"),
    ("uio_oe[0]",   56640, "OUTPUT"),
    ("uio_oe[1]",   52800, "OUTPUT"),
    ("uio_oe[2]",   48960, "OUTPUT"),
    ("uio_oe[3]",   45120, "OUTPUT"),
    ("uio_oe[4]",   41280, "OUTPUT"),
    ("uio_oe[5]",   37440, "OUTPUT"),
    ("uio_oe[6]",   33600, "OUTPUT"),
    ("uio_oe[7]",   29760, "OUTPUT"),
    ("uio_out[0]",  87360, "OUTPUT"),
    ("uio_out[1]",  83520, "OUTPUT"),
    ("uio_out[2]",  79680, "OUTPUT"),
    ("uio_out[3]",  75840, "OUTPUT"),
    ("uio_out[4]",  72000, "OUTPUT"),
    ("uio_out[5]",  68160, "OUTPUT"),
    ("uio_out[6]",  64320, "OUTPUT"),
    ("uio_out[7]",  60480, "OUTPUT"),
    ("uo_out[0]",  118080, "OUTPUT"),
    ("uo_out[1]",  114240, "OUTPUT"),
    ("uo_out[2]",  110400, "OUTPUT"),
    ("uo_out[3]",  106560, "OUTPUT"),
    ("uo_out[4]",  102720, "OUTPUT"),
    ("uo_out[5]",   98880, "OUTPUT"),
    ("uo_out[6]",   95040, "OUTPUT"),
    ("uo_out[7]",   91200, "OUTPUT"),
]

# Power stripes (TopMetal1), full height minus 2 um (0..152980) so they stay
# within 10 um of both the top and bottom edges as the precheck requires.
# Width 2200 nm >= 2.1 um minimum. X positions follow the shipped template.
PWR_TOP = 152980
POWER_STRIPES = [
    # (name, x_min, x_max, use)
    ("VGND", 16000, 18200, "GROUND"),
    ("VPWR", 20000, 22200, "POWER"),
]


def build():
    ly = pya.Layout()
    ly.dbu = 0.001  # 1 nm
    cell = ly.create_cell(TOP)

    prb = ly.layer(*L_PRBOUND)
    m4 = ly.layer(*L_M4_DRAW)
    m4p = ly.layer(*L_M4_PIN)
    m4t = ly.layer(*L_M4_TEXT)
    tm1 = ly.layer(*L_TM1_DRAW)
    tm1p = ly.layer(*L_TM1_PIN)
    tm1t = ly.layer(*L_TM1_TEXT)

    # -- die boundary ------------------------------------------------------
    cell.shapes(prb).insert(pya.Box(0, 0, DIE_W, DIE_H))

    # -- signal pins -------------------------------------------------------
    for name, x, _dir in SIGNAL_PINS:
        r = sig_rect(x)
        cell.shapes(m4).insert(r)          # drawing
        cell.shapes(m4p).insert(r)         # pin (precheck containment)
        cell.shapes(m4t).insert(pya.Text(name, x, SIG_CY))

    # -- power stripes -----------------------------------------------------
    for name, x0, x1, _use in POWER_STRIPES:
        r = pya.Box(x0, 0, x1, PWR_TOP)
        cell.shapes(tm1).insert(r)
        cell.shapes(tm1p).insert(r)
        cell.shapes(tm1t).insert(pya.Text(name, (x0 + x1) // 2, PWR_TOP // 2))

    ly.write(f"gds/{TOP}.gds")
    print(f"wrote gds/{TOP}.gds  (cell={TOP}, {len(SIGNAL_PINS)} signal pins, "
          f"{len(POWER_STRIPES)} power stripes, boundary)")


def lef():
    """Emit a -pinonly style LEF for the macro (26b rules)."""
    lines = []
    a = lines.append
    a("VERSION 5.7 ;")
    a("  NOWIREEXTENSIONATPIN ON ;")
    a('  DIVIDERCHAR "/" ;')
    a('  BUSBITCHARS "[]" ;')
    a(f"MACRO {TOP}")
    a("  CLASS BLOCK ;")
    a(f"  FOREIGN {TOP} ;")
    a("  ORIGIN 0.000 0.000 ;")
    a(f"  SIZE {DIE_W/DBU_PER_UM:.3f} BY {DIE_H/DBU_PER_UM:.3f} ;")

    # power / ground on TopMetal1
    for name, x0, x1, use in POWER_STRIPES:
        a(f"  PIN {name}")
        a("    DIRECTION INOUT ;")
        a(f"    USE {use} ;")
        a("    PORT")
        a("      LAYER TopMetal1 ;")
        a(f"        RECT {x0/DBU_PER_UM:.3f} 0.000 "
          f"{x1/DBU_PER_UM:.3f} {PWR_TOP/DBU_PER_UM:.3f} ;")
        a("    END")
        a(f"  END {name}")

    # signals on Metal4, rect exactly matching the DEF template
    for name, x, direction in SIGNAL_PINS:
        a(f"  PIN {name}")
        a(f"    DIRECTION {direction} ;")
        a("    USE SIGNAL ;")
        a("    PORT")
        a("      LAYER Metal4 ;")
        x0 = (x - SIG_HALF_W) / DBU_PER_UM
        x1 = (x + SIG_HALF_W) / DBU_PER_UM
        y0 = (SIG_CY - SIG_HALF_H) / DBU_PER_UM
        y1 = (SIG_CY + SIG_HALF_H) / DBU_PER_UM
        a(f"        RECT {x0:.3f} {y0:.3f} {x1:.3f} {y1:.3f} ;")
        a("    END")
        a(f"  END {name}")

    a(f"END {TOP}")
    a("END LIBRARY")

    with open(f"lef/{TOP}.lef", "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote lef/{TOP}.lef")


if __name__ == "__main__":
    build()
    lef()
