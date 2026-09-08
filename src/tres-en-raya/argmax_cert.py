"""Layer-2 certification matching EXACT argmax-with-lowest-index-tiebreak semantics.

For each deduped (h, opt, sub) constraint, requires  max_{c in opt} [c wins]
where "c wins" = lg_c >= lg_s for all suboptimal s with (c < s), and lg_c > lg_s
for s < c.  Ties are broken toward the optimal cell when it has the lower index.
"""
import argparse
from pathlib import Path

import numpy as np
from ortools.sat.python import cp_model

import int4_net
import oracle

HI, HH, OUT = 9, 16, 9
HERE = Path(__file__).parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="weights_e2.txt")
    ap.add_argument("--out", default="weights_argmax.txt")
    ap.add_argument("--time", type=float, default=600.0)
    args = ap.parse_args()

    ds, _ = oracle.load_or_build_dataset()
    w0 = int4_net.load_weights(args.weights)
    X = np.array([x for x, _, _v in ds], dtype=np.int64)
    H = np.clip((X @ np.array(w0["W1"]).T + np.array(w0["b1"]) + (1 << (w0["s1"] - 1))) >> w0["s1"], 0, 7)
    legal = X == 0
    ymask = np.zeros((len(ds), OUT), dtype=bool)
    val = np.zeros(len(ds))
    for i, (_, p, v) in enumerate(ds):
        for mv in p:
            ymask[i, mv] = True
        val[i] = v
    g = {}
    for r in range(len(ds)):
        if val[r] < 0:
            continue
        o = frozenset(np.where(ymask[r])[0])
        s = frozenset(i for i in range(9) if legal[r, i]) - o
        if not s:
            continue
        k = (H[r].tobytes(), o, s)
        g[k] = g.get(k, 0) + (1000 if val[r] == 0 else 50)

    m = cp_model.CpModel()
    W2 = [[m.NewIntVar(-8, 8, "") for _ in range(HH)] for _ in range(OUT)]
    b2 = [m.NewIntVar(-2000, 2000, "") for _ in range(OUT)]
    terms, vys = [], []
    for (hb, opt, sub), p in g.items():
        hr = np.frombuffer(hb, dtype=np.int64)
        nz = [(int(j), int(v)) for j, v in enumerate(hr) if v]
        lv = []
        for c in range(9):
            v = m.NewIntVar(-20000, 20000, "")
            m.Add(v == sum(x * W2[c][j] for j, x in nz) + b2[c])
            lv.append(v)
        zs = []
        for c in sorted(opt):
            z = m.NewBoolVar("")
            for s2 in sorted(sub):
                if c < s2:
                    m.Add(lv[c] >= lv[s2]).OnlyEnforceIf(z)
                else:
                    m.Add(lv[c] > lv[s2]).OnlyEnforceIf(z)
            zs.append(z)
        y = m.NewBoolVar("")
        m.AddBoolOr(zs + [y])
        terms.append(p * y)
        vys.append((y, p))
    m.Minimize(sum(terms))
    Wh = np.array(w0["W2"])
    bh = np.array(w0["b2"])
    for i in range(OUT):
        for j in range(HH):
            m.AddHint(W2[i][j], int(Wh[i, j]))
        m.AddHint(b2[i], int(np.clip(bh[i], -2000, 2000)))

    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = args.time
    s.parameters.num_search_workers = 11
    st = s.Solve(m)
    print("status", s.StatusName(st), "obj", s.ObjectiveValue(), "bound", s.BestObjectiveBound(), flush=True)
    draw = sum(p for y, p in vys if s.Value(y) and p >= 1000)
    win = sum(p for y, p in vys if s.Value(y) and p < 1000)
    print(f"draw-pen {draw} win-pen {win}", flush=True)
    W2v = np.array([[s.Value(W2[i][j]) for j in range(HH)] for i in range(OUT)], dtype=np.int64)
    b2v = np.array([s.Value(b2[i]) for i in range(OUT)], dtype=np.int64)
    lines = ["# tres-en-raya 9-16-9 int4 (argmax-exact cert)", f"s1 {w0['s1']}"]
    for name, arr in (("W1", w0["W1"]), ("b1", w0["b1"]), ("W2", W2v), ("b2", b2v)):
        lines.append(f"{name} " + "\n".join(str(int(v)) for v in np.ravel(arr)))
    Path(args.out).write_text("\n".join(lines) + "\n")
    print("wrote", args.out)


if __name__ == "__main__":
    main()
