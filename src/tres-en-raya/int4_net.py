"""Pure-integer int4 inference for the 9-16-9 tres-en-raya network.

This is the exact fixed-point spec the analog MAC array must reproduce:
  x      : 9 values in {-4, 0, +4}  (self=+4, opponent=-4, empty=0)
  acc1   : W1 @ x + b1              int32 accumulator, W1 in [-8, 7]
  h      : clamp((acc1 + 2^(s1-1)) >> s1, 0, 7)   saturating ReLU, int4
  logits : W2 @ h + b2              int32 accumulator (compared for argmax)

Weights file (weights.txt): whitespace ints, sections in order W1 b1 W2 b2.
"""
from __future__ import annotations

import re
from pathlib import Path

QMIN, QMAX = -8, 7
HI, HIDDEN, OUT = 9, 16, 9


def load_weights(path: str | Path) -> dict:
    text = Path(path).read_text()
    s1 = int(re.search(r"^s1\s+(-?\d+)", text, re.M).group(1))
    arrays = {}
    for name in ("W1", "b1", "W2", "b2"):
        m = re.search(rf"{name}\s+([\s\-0-9]+?)(?=\n\s*(?:W1|b1|W2|b2|s1)\b|\Z)", text)
        vals = [int(t) for t in m.group(1).split()]
        arrays[name] = vals
    w = {"s1": s1,
         "W1": [arrays["W1"][i * HI:(i + 1) * HI] for i in range(HIDDEN)],
         "b1": arrays["b1"],
         "W2": [arrays["W2"][i * HIDDEN:(i + 1) * HIDDEN] for i in range(OUT)],
         "b2": arrays["b2"]}
    assert len(w["b1"]) == HIDDEN and len(w["b2"]) == OUT
    return w


def forward(w: dict, x: list[int]) -> list[int]:
    """x: 9 ints in [-8, 7]. Returns 9 integer logits."""
    s1 = w["s1"]
    half = 1 << (s1 - 1) if s1 > 0 else 0
    h = []
    for row, b in zip(w["W1"], w["b1"]):
        acc = sum(wi * xi for wi, xi in zip(row, x)) + b
        val = (acc + half) >> s1 if s1 > 0 else acc + half
        h.append(min(max(val, 0), QMAX))
    return [sum(wi * hi for wi, hi in zip(row, h)) + b for row, b in zip(w["W2"], w["b2"])]


def legal_mask(x: list[int]) -> list[int]:
    """A cell is playable iff it is empty (encoding 0 in self-view)."""
    return [1 if xi == 0 else 0 for xi in x]


def choose_action(w: dict, x: list[int], board: tuple[int, ...], turn: int) -> int:
    """Argmax over empty cells, lowest-index tie-break."""
    logits = forward(w, x)
    best, best_mv = None, None
    for i in range(9):
        if board[i] != 0:
            continue
        if best is None or logits[i] > best:
            best, best_mv = logits[i], i
    if best_mv is None:
        raise ValueError("no legal move")
    return best_mv


def encode_self(board: tuple[int, ...], turn: int) -> list[int]:
    return [4 if v == turn else -4 if v else 0 for v in board]
