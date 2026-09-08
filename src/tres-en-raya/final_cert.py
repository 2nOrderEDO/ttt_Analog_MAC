"""Final step: exact int4 layer-2 certification via CP-SAT for fixed features.

Writes the CP-SAT-optimal W2/b2 (given W1/b1/s1) to the output weights file.
This is the last polish applied to the trained network.

    uv run final_cert.py --weights weights.txt --out weights_final.txt --time 420
"""
import argparse
from pathlib import Path

import numpy as np
from ortools.sat.python import cp_model

import int4_net
import oracle

HI, HH, OUT = 9, 16, 9
QMIN, QMAX = -8, 7
HERE = Path(__file__).parent


def constraints(H, ymask, legal, val):
    g = {}
    for r in range(H.shape[0]):
        if val[r] < 0:
            continue
        opt = frozenset(np.where(ymask[r])[0])
        sub = frozenset(i for i in range(9) if legal[r, i]) - opt
        if not sub:
            continue
        key = (H[r].tobytes(), opt, sub)
        g[key] = g.get(key, 0) + (1000 if val[r] == 0 else 50)
    out = []
    for (hb, opt, sub), p in g.items():
        hr = np.frombuffer(hb, dtype=np.int64)
        out.append(([(int(j), int(v)) for j, v in enumerate(hr) if v], sorted(opt), sorted(sub), p))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="weights.txt")
    ap.add_argument("--out", default="weights_final.txt")
    ap.add_argument("--time", type=float, default=420.0)
    args = ap.parse_args()

    ds, _ = oracle.load_or_build_dataset()
    w0 = int4_net.load_weights(args.weights)
    X = np.array([x for x, _, _v in ds], dtype=np.int64)
    H = np.clip((X @ np.array(w0["W1"]).T + np.array(w0["b1"]) + (1 << (w0["s1"] - 1))) >> w0["s1"], 0, QMAX)
    legal = X == 0
    ymask = np.zeros((len(ds), OUT), dtype=bool)
    val = np.zeros(len(ds))
    for i, (_, probs, v) in enumerate(ds):
        for mv in probs:
            ymask[i, mv] = True
        val[i] = v
    cons = constraints(H, ymask, legal, val)
    print(f"{len(cons)} unique constraints", flush=True)

    m = cp_model.CpModel()
    W2 = [[m.NewIntVar(QMIN, QMAX, "") for _ in range(HH)] for _ in range(OUT)]
    b2 = [m.NewIntVar(-2000, 2000, "") for _ in range(OUT)]
    terms, vys = [], []
    for nz, opt, sub, p in cons:
        lv = []
        for c in range(9):
            v = m.NewIntVar(-20000, 20000, "")
            m.Add(v == sum(val_ * W2[c][j] for j, val_ in nz) + b2[c])
            lv.append(v)
        pm, qm = m.NewIntVar(-20000, 20000, ""), m.NewIntVar(-20000, 20000, "")
        m.AddMaxEquality(pm, [lv[c] for c in opt])
        m.AddMaxEquality(qm, [lv[s] for s in sub])
        y = m.NewBoolVar("")
        m.Add(pm - qm >= 1).OnlyEnforceIf(y.Not())
        terms.append(p * y)
        vys.append((y, p))
    m.Minimize(sum(terms))
    Wh = np.array(w0["W2"], dtype=np.int64)
    bh = np.array(w0["b2"], dtype=np.int64)
    for i in range(OUT):
        for j in range(HH):
            m.AddHint(W2[i][j], int(Wh[i][j]))
        m.AddHint(b2[i], int(np.clip(bh[i], -2000, 2000)))

    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = args.time
    s.parameters.num_search_workers = 11
    st = s.Solve(m)
    print("status", s.StatusName(st), "obj", s.ObjectiveValue(), "bound", s.BestObjectiveBound(), flush=True)
    draw_pen = sum(p for y, p in vys if s.Value(y) and p >= 1000)
    win_pen = sum(p for y, p in vys if s.Value(y) and p < 1000)
    print(f"draw-penalty {draw_pen}  win-penalty {win_pen}", flush=True)
    W2v = np.array([[s.Value(W2[i][j]) for j in range(HH)] for i in range(OUT)], dtype=np.int64)
    b2v = np.array([s.Value(b2[i]) for i in range(OUT)], dtype=np.int64)
    lines = ["# tres-en-raya 9-16-9 int4 signed network (see int4_net.py for semantics)",
             f"s1 {w0['s1']}"]
    for name, arr in (("W1", w0["W1"]), ("b1", w0["b1"]), ("W2", W2v), ("b2", b2v)):
        lines.append(f"{name} " + "\n".join(str(int(v)) for v in np.ravel(arr)))
    Path(args.out).write_text("\n".join(lines) + "\n")
    print("wrote", args.out, flush=True)


if __name__ == "__main__":
    main()
