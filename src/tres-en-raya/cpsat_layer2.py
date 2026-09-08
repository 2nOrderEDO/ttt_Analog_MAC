"""Exact int4 layer-2 solve via CP-SAT, given fixed W1/b1/s1 (hidden features).

For every dataset row (non-lost state with a real choice), some optimal cell's
integer logit must exceed every sub-optimal legal cell's logit by >= 1.  With
W1 fixed, h is constant per row, so this is integer LINEAR feasibility in
(W2, b2).  Duplicate constraint rows are merged.  Penalties: draw-state
violation 1000x, winning-state violation 50x.

    uv run cpsat_layer2.py [--time 300]
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
from ortools.sat.python import cp_model

import oracle
import int4_net

HI, HH, OUT = 9, 16, 9
QMIN, QMAX = -8, 7
B2LIM = 1000
HERE = Path(__file__).parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default=str(HERE / "weights.txt"))
    ap.add_argument("--out", default=str(HERE / "weights_cpsat.txt"))
    ap.add_argument("--time", type=float, default=240.0)
    ap.add_argument("--hint", action="store_true", help="hint CP-SAT with current W2/b2")
    ap.add_argument("--hard-draw", action="store_true", help="draw constraints are hard (feasibility probe)")
    ap.add_argument("--only-draw", action="store_true", help="drop winning-state constraints entirely")
    args = ap.parse_args()
    t0 = time.time()

    dataset, _ = oracle.load_or_build_dataset()
    w0 = int4_net.load_weights(args.weights)
    W1 = np.array(w0["W1"], dtype=np.int64)
    b1 = np.array(w0["b1"], dtype=np.int64)
    s1 = int(w0["s1"])
    X = np.array([x for x, _, _v in dataset], dtype=np.int64)
    half = (1 << (s1 - 1)) if s1 > 0 else 0
    H = np.clip((X @ W1.T + b1 + half) >> s1, 0, QMAX)

    groups = Counter()
    for r, (x, probs, val) in enumerate(dataset):
        if val < 0:
            continue
        legal = frozenset(i for i in range(9) if x[i] == 0)
        opt = frozenset(probs)
        sub = legal - opt
        if not sub:
            continue
        if args.only_draw and val != 0:
            continue
        key = (H[r].tobytes(), opt, sub)
        groups[key] += (1000 if val == 0 else 50)
    # rebuild nz coefficient lists per unique h
    uniq = {}
    cons = []
    for (hb, opt, sub), pen in groups.items():
        if hb not in uniq:
            hrow = np.frombuffer(hb, dtype=np.int64)
            uniq[hb] = [(int(j), int(v)) for j, v in enumerate(hrow) if v]
        cons.append((hb, sorted(opt), sorted(sub), pen))
    print(f"{len(cons)} unique constraints ({len(uniq)} distinct h), built {time.time()-t0:.1f}s")
    sys.stdout.flush()

    m = cp_model.CpModel()
    W2 = [[m.NewIntVar(QMIN, QMAX, f"w2_{i}_{j}") for j in range(HH)] for i in range(OUT)]
    b2 = [m.NewIntVar(-B2LIM, B2LIM, f"b2_{i}") for i in range(OUT)]

    def lg_expr(nz, cell):
        return sum(v * W2[cell][j] for j, v in nz) + b2[cell]

    terms = []
    for n, (hb, opt, sub, pen) in enumerate(cons):
        if n % 20000 == 0:
            print(f"  building {n}/{len(cons)}  {time.time()-t0:.0f}s")
            sys.stdout.flush()
        nz = uniq[hb]
        hard = args.hard_draw and pen >= 1000
        y = m.NewBoolVar(f"y_{n}")
        if not hard:
            terms.append(pen * y)
        zs = []
        for c in opt:
            z = m.NewBoolVar(f"z_{n}_{c}")
            ec = lg_expr(nz, c)
            for q in sub:
                m.Add(ec - lg_expr(nz, q) >= 1).OnlyEnforceIf(z)
            zs.append(z)
        if hard:
            m.AddBoolOr(zs)
        else:
            m.AddBoolOr(zs + [y])
    m.Minimize(sum(terms))
    if args.hint:
        W2h = np.array(w0["W2"], dtype=np.int64)
        b2h = np.array(w0["b2"], dtype=np.int64)
        for i in range(OUT):
            for j in range(HH):
                m.AddHint(W2[i][j], int(W2h[i][j]))
            m.AddHint(b2[i], int(np.clip(b2h[i], -B2LIM, B2LIM)))
    print(f"model built {time.time()-t0:.0f}s, solving {args.time:.0f}s")
    sys.stdout.flush()

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = args.time
    solver.parameters.num_search_workers = 11
    solver.parameters.log_search_progress = False
    st = solver.Solve(m)
    print("status:", solver.StatusName(st), f"({time.time()-t0:.0f}s)")
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return
    print(f"objective {solver.ObjectiveValue():.0f} bestbound {solver.BestObjectiveBound():.0f}")

    W2v = np.array([[solver.Value(W2[i][j]) for j in range(HH)] for i in range(OUT)], dtype=np.int64)
    b2v = np.array([solver.Value(b2[i]) for i in range(OUT)], dtype=np.int64)
    lines = ["# tres-en-raya 9-16-9 int4 signed network (layer2 solved by CP-SAT)",
             f"s1 {s1}"]
    for name, arr in (("W1", W1), ("b1", b1), ("W2", W2v), ("b2", b2v)):
        lines.append(f"{name} " + "\n".join(str(int(v)) for v in np.ravel(arr)))
    Path(args.out).write_text("\n".join(lines) + "\n")
    print(f"wrote {args.out}")

    wv = int4_net.load_weights(args.out)
    bad = 0
    for r, (x, probs, val) in enumerate(dataset):
        if val < 0:
            continue
        lg = int4_net.forward(wv, list(x))
        legal = [i for i in range(9) if x[i] == 0]
        mv = max(legal, key=lambda i: (lg[i], -i))
        if mv not in probs:
            bad += 1
    print(f"python check: {bad} wrong among non-lost rows")


if __name__ == "__main__":
    main()
