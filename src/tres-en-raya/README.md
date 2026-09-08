# tres-en-raya — int4 quantised tic-tac-toe MLP

A tiny 9→16→9 multilayer perceptron, trained quantisation-aware to **signed
4-bit integers** (`[-8, 7]`), that plays tic-tac-toe decently:

| opponent | win | draw | loss |
|---|---|---|---|
| random | 82.5 % | 14.8 % | 2.7 % |
| greedy (win/block) | 0 % | 100 % | 0 % |
| perfect minimax | 0 % | 83 % | 17 % |

The final forward pass is pure integer arithmetic (see `int4_net.py`) so it
maps directly onto the EMMAC array: two MAC rows, int32 accumulators, and a
saturating ReLU.

## Network spec

```
x      ∈ {-4, 0, +4}^9         cell encoding, self-perspective:
                                +4 = my stone, -4 = opponent, 0 = empty
acc1   = W1 @ x + b1           W1: 16x9 int4, b1: 16 int32   (int32 acc)
h      = clamp((acc1 + 2^(s1-1)) >> s1, 0, 7)                (int4, sat-ReLU)
logits = W2 @ h + b2           W2: 9x16 int4, b2: 9 int32    (int32 acc)
move   = argmax over EMPTY cells (ties: lowest index)
```

`weights.txt` stores `s1` plus `W1 b1 W2 b2` as whitespace-separated ints.
The network plays **both sides**: encode from whoever is to move.

## Files

| file | role |
|---|---|
| `oracle.py` | perfect-play minimax over all 4520 reachable states → training labels |
| `train.py` | QAT: fp32 warm-up → int4 QAT (CE distillation) → hinge polish → exact-int greedy coordinate descent; exports `weights.txt` and verifies bit-exactness |
| `finetune.py` | warm-start QAT fine-tune from an exported `weights.txt` (draw-state weighting) |
| `final_cert.py`, `argmax_cert.py` | exact int4 layer-2 re-solve via CP-SAT (margin-1 / exact-tiebreak variants) |
| `int4_net.py` | the pure-integer reference implementation (what the analog must reproduce) |
| `eval_play.py` | plays thousands of games vs random / greedy / perfect |
| `play.py` | terminal game vs the net (`uv run play.py`, enter 1-9) |

## Reproduce

```bash
uv run python oracle.py                    # builds .oracle_cache.json (one-off)
uv run python train.py                     # ~1 h, writes weights.txt + model_qat.pt
uv run python argmax_cert.py --weights weights.txt --out weights.txt --time 500
uv run python eval_play.py --games 5000
```

## How it was trained

1. **Oracle distillation**: every legal state × 8 symmetries, CE against the
   uniform-over-optimal-moves target; states that are already lost get
   weight ~0 (no point learning them).
2. **QAT**: per-tensor symmetric int4 fake-quant with STE on the weights;
   hidden activations pass through the exact fixed-point path above with STE
   rounding (so training matches silicon).
3. **Integer polish**: greedy coordinate descent / CP-SAT directly on the
   deployed int weights — the objective evaluated is exactly what the chip
   will compute.

Known limitation: int4 hidden features (16 × 3 effective bits) are the
bottleneck — a few distinct states share one hidden vector ("collisions"),
which no output layer can separate; that caps perfect-play draws at ~83 %.
A second hidden layer or 5–6-bit h would close it if the silicon ever wants
more.
