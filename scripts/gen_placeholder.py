#!/usr/bin/env python3
"""
Generate a Tiny Tapeout 1x1 custom-GDS *placeholder* macro.

This produces a minimal, pin-compliant macro for slot reservation:
  * die boundary for the 1x1 tile (202.08 x 154.98 um)
  * Metal4 signal stubs at the exact template pin coordinates
  * Metal5 full-height power stripes (VGND / VPWR)
  * Metal4/Metal5 text labels so the pins are electrically identified

It is intentionally minimal -- the real EMMAC + DAC + SPI layout will replace
it in later revisions (same footprint / pinout).

Run with KLayout's bundled python:
    klayout -b -z -nc -rx -r scripts/gen_placeholder.py

Outputs (written relative to the repo root):
    gds/<TOP>.gds
    lef/<TOP>.lef
"""

import pya  # KLayout python API

TOP = "tt_um_ttt_emamac_2nOrderEDO"

# ---------------------------------------------------------------------------
# Geometry constants (all in database units, 1 dbu = 1 nm = 0.001 um)
# ---------------------------------------------------------------------------
DBU_PER_UM = 1000
DIE_W = 202080   # 202.08 um
DIE_H = 154980   # 154.98 um

# GDS layer/datatype for IHP sg13g2 (from libs.tech/klayout/tech/sg13g2.map)
L_METAL4_DRAW = (50, 0)
L_METAL4_TEXT = (50, 25)
L_METAL5_DRAW = (67, 0)
L_METAL5_TEXT = (67, 25)

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

# Power stripes: full-height Metal5 vertical stripes near the left edge,
# matching the shipped tt_um_colorful_stripes LEF geometry.
POWER_STRIPES = [
    # (name, x_min, x_max, use)  -- full height 0..DIE_H, width 2200 nm (>1.2 um rule)
    ("VGND", 16000, 18200, "GROUND"),
    ("VPWR", 20000, 22200, "POWER"),
]


def build():
    ly = pya.Layout()
    ly.dbu = 0.001  # 1 nm
    cell = ly.create_cell(TOP)

    m4 = ly.layer(*L_METAL4_DRAW)
    m4t = ly.layer(*L_METAL4_TEXT)
    m5 = ly.layer(*L_METAL5_DRAW)
    m5t = ly.layer(*L_METAL5_TEXT)

    # -- signal pins -------------------------------------------------------
    for name, x, _dir in SIGNAL_PINS:
        cell.shapes(m4).insert(sig_rect(x))
        # pin label near the stub so netlisting can identify the terminal
        cell.shapes(m4t).insert(pya.Text(name, x, SIG_CY))

    # -- power stripes -----------------------------------------------------
    for name, x0, x1, _use in POWER_STRIPES:
        cell.shapes(m5).insert(pya.Box(x0, 0, x1, DIE_H))
        # label the rail mid-height
        cell.shapes(m5t).insert(pya.Text(name, (x0 + x1) // 2, DIE_H // 2))

    ly.write(f"gds/{TOP}.gds")
    print(f"wrote gds/{TOP}.gds  (cell={TOP}, {len(SIGNAL_PINS)} signal pins, "
          f"{len(POWER_STRIPES)} power stripes)")


def lef():
    """Emit a -pinonly style LEF for the macro."""
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

    # power / ground
    for name, x0, x1, use in POWER_STRIPES:
        a(f"  PIN {name}")
        a("    DIRECTION INOUT ;")
        a(f"    USE {use} ;")
        a("    PORT")
        a("      LAYER Metal5 ;")
        a(f"        RECT {x0/DBU_PER_UM:.3f} 0.000 "
          f"{x1/DBU_PER_UM:.3f} {DIE_H/DBU_PER_UM:.3f} ;")
        a("    END")
        a(f"  END {name}")

    # signals
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
