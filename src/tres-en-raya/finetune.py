"""Warm-start QAT fine-tune from an exported int4 weights file.

Standard cross-entropy on the oracle, weighting draw-critical states heavily
(the only mistakes that lose games vs perfect play).  Simple and final.

    uv run finetune.py --from weights_e2.txt --steps 15000
"""
import argparse
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

import oracle
import int4_net
from train import Qnet, wce, opt_rate, check_bit_exact, HI, HH, OUT, QMAX

HERE = Path(__file__).parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", default="weights_e2.txt")
    ap.add_argument("--steps", type=int, default=15000)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--batch", type=int, default=1024)
    ap.add_argument("--draw-weight", type=float, default=8.0)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    torch.manual_seed(args.seed); random.seed(args.seed); np.random.seed(args.seed)

    w = int4_net.load_weights(args.src)
    model = Qnet()
    # float = 7*W_int with a=7: round(W/7)=W_int exactly (int grid -8..7 all
    # map back to themselves), and a 7-unit gap sits between float grid points
    # so Adam steps move the quantized weights.
    with torch.no_grad():
        model.auto_scale = False
        model.a1.fill_(float(QMAX))
        model.a2.fill_(float(QMAX))
        model.W1.copy_(torch.tensor(np.array(w["W1"], dtype=np.float32) * QMAX))
        model.W2.copy_(torch.tensor(np.array(w["W2"], dtype=np.float32) * QMAX))
        model.b1.copy_(torch.tensor(np.array(w["b1"], dtype=np.float32)))
        model.b2.copy_(torch.tensor(np.array(w["b2"], dtype=np.float32)))
        model.s1 = w["s1"]
        model.max_acc = float((1 << w["s1"]) * QMAX - 1)
    def dump(path):
        from train import export_weights as _ew
        _ew(model.int_export(), path)

    # sanity: export must equal input file
    dump(HERE / "_sanity.txt")
    same = int4_net.load_weights("_sanity.txt")
    for k in ("W1", "b1", "W2", "b2", "s1"):
        assert np.array_equal(np.array(same[k]), np.array(w[k])), f"roundtrip broke {k}"
    (HERE / "_sanity.txt").unlink()
    print("roundtrip exact")


    dataset, _ = oracle.load_or_build_dataset()
    y_opt = [set(p.keys()) for _, p, _v in dataset]
    X = torch.tensor([x for x, _, _v in dataset], dtype=torch.float32)
    Y = torch.zeros(len(dataset), OUT)
    Wt = torch.zeros(len(dataset))
    for i, (_, probs, val) in enumerate(dataset):
        for mv, p in probs.items():
            Y[i, mv] = p
        Wt[i] = 0.02 if val < 0 else (args.draw_weight if val == 0 else 1.0)
    M = (X == 0).float()

    print(f"before: {opt_rate(model, X, M, y_opt)*100:.2f}% argmax-optimal")
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.steps)
    for step in range(1, args.steps + 1):
        idx = torch.randint(0, X.shape[0], (args.batch,))
        model.train()
        logits, _ = model(X[idx], M[idx])
        loss = wce(logits, Y[idx], Wt[idx])
        opt.zero_grad(); loss.backward(); sched.step(); opt.step()
        if step % 2500 == 0 or step == args.steps:
            print(f"step {step:6d} loss {loss.item():.4f} int-optimal {opt_rate(model, X, M, y_opt)*100:.2f}%")
    acc = opt_rate(model, X, M, y_opt)
    print(f"after: {acc*100:.2f}%")
    torch.save(model.state_dict(), HERE / "model_ft.pt")
    dump(HERE / "weights.txt")
    check_bit_exact(model)


if __name__ == "__main__":
    main()
