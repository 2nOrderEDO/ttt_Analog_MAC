"""Quantisation-aware training of a 9-16-9 int4 tic-tac-toe policy.

Three-phase recipe:
  A) full-precision warm-up distilling the minimax oracle (importance-weighted:
     already-lost states barely matter);
  B) QAT fine-tune with CE against oracle+teacher mixture;
  C) QAT polish with a hinge margin on the *integer* logits so argmax order is
     strictly enforced at int4 hardware precision.

Exported model is bit-identical to int4_net.py (verified on every dataset row).
Usage:  uv run train.py [--steps-a 15000] [--steps-b 20000] [--steps-c 20000]
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

import oracle

HERE = Path(__file__).parent
HI, HH, OUT = 9, 16, 9
QMIN, QMAX = -8, 7
W_LOST = 0.05
TEACHER_MIX = 0.5
TEACHER_T = 2.0
HINGE_MARGIN = 1.0


def ste_round(x: torch.Tensor) -> torch.Tensor:
    return x + (x.round() - x).detach()


class Qnet(torch.nn.Module):
    def __init__(self):
        super().__init__()
        g = torch.Generator().manual_seed(0)
        self.W1 = torch.nn.Parameter(torch.randn(HH, HI, generator=g) * 0.5)
        self.b1 = torch.nn.Parameter(torch.zeros(HH))
        self.W2 = torch.nn.Parameter(torch.randn(OUT, HH, generator=g) * 0.5)
        self.b2 = torch.nn.Parameter(torch.zeros(OUT))
        self.logit_scale = torch.nn.Parameter(torch.zeros(()))
        self.s1 = 4
        self.max_acc = 0.0
        self.auto_scale = True
        self.register_buffer("a1", torch.tensor(1.0))
        self.register_buffer("a2", torch.tensor(1.0))

    def _gain(self):
        return F.softplus(self.logit_scale) + 1e-2

    def scale1(self):
        if not self.auto_scale:
            return self.a1
        self.a1.copy_((self.W1.abs().amax().clamp(min=1e-8) / QMAX).detach())
        return self.a1

    def scale2(self):
        if not self.auto_scale:
            return self.a2
        self.a2.copy_((self.W2.abs().amax().clamp(min=1e-8) / QMAX).detach())
        return self.a2

    def forward(self, x, mask, quant=True):
        """Returns (softmax_logits, raw_logits). raw is pre-gain: the integer
        accumulator values the hardware would produce (fake-quantised)."""
        if not quant:
            h = F.relu(x @ self.W1.T + self.b1)
            raw = h @ self.W2.T + self.b2
            lg = raw * self._gain()
        else:
            a1 = self.scale1()
            acc = x @ ste_round(self.W1 / a1).T + ste_round(self.b1)
            if self.training:
                with torch.no_grad():
                    m = acc.detach().amax().item()
                    if m > self.max_acc:
                        self.max_acc = m
                    s = 0
                    while int(self.max_acc) >> s > QMAX:
                        s += 1
                    self.s1 = s
            half = (1 << (self.s1 - 1)) if self.s1 > 0 else 0
            p = (acc + half) / float(1 << self.s1)
            h = p + (p.clamp(0, QMAX).round() - p).detach()
            a2 = self.scale2()
            raw = h @ ste_round(self.W2 / a2).T + ste_round(self.b2)
            lg = raw * self._gain()
        m = mask
        return lg * m + (m - 1) * 1e9, raw * m + (m - 1) * 1e9

    def int_export(self):
        with torch.no_grad():
            a1 = self.scale1()
            a2 = self.scale2()
            return {
                "s1": self.s1,
                "W1": (self.W1 / a1).round().clamp(QMIN, QMAX).cpu().numpy().astype(np.int64),
                "b1": self.b1.round().cpu().numpy().astype(np.int64),
                "W2": (self.W2 / a2).round().clamp(QMIN, QMAX).cpu().numpy().astype(np.int64),
                "b2": self.b2.round().cpu().numpy().astype(np.int64),
            }


def wce(logits, y, w):
    ce = -(y * F.log_softmax(logits, 1)).sum(1)
    return (ce * w).sum() / w.sum()


# ------------------------------------------------------- phase D: integer search
class IntModel:
    """Vectorised exact integer forward of the exported net (numpy)."""

    def __init__(self, X, M, W1, b1, W2, b2, s1):
        self.x = X.numpy().astype(np.int64)          # (N,9)
        self.m = M.numpy().astype(bool)              # (N,9)
        self.W1 = W1.copy()
        self.b1 = b1.copy()
        self.W2 = W2.copy()
        self.b2 = b2.copy()
        self.s1 = int(s1)

    def hidden(self):
        acc = self.x @ self.W1.T + self.b1
        half = (1 << (self.s1 - 1)) if self.s1 > 0 else 0
        return np.clip((acc + half) >> self.s1, 0, QMAX)

    def logits(self):
        h = self.hidden()
        lg = h @ self.W2.T + self.b2
        return np.where(self.m, lg, -10**9)

    def err_count(self, yopt_list):
        mv = self.logits().argmax(1)
        return sum(1 for i, s in enumerate(yopt_list) if mv[i] not in s)

    def hinge_obj(self, Y, Wt, margin=2.0):
        lg = self.logits()
        pos = (Y.numpy() > 0)
        neg = (Y.numpy() == 0) & self.m
        pmax = np.where(pos, lg, -10**9).max(1)
        nmax = np.where(neg, lg, -10**9).max(1)
        viol = np.maximum(0.0, margin - (pmax - nmax))
        has = neg.any(1)
        w = Wt.numpy() * has
        return float((viol * w).sum() / max(w.sum(), 1e-9))


def greedy_polish(intm, Y, Wt, y_opt, sweeps=8, verbose=True):
    """Coordinate descent on int4 weights + biases minimizing hinge err."""
    def obj():
        return intm.hinge_obj(Y, Wt)
    cur = obj()
    for sw in range(sweeps):
        improved = 0
        # W1 entries
        for i in range(HH):
            for j in range(HI):
                for d in (+1, -1, +2, -2):
                    v = intm.W1[i, j] + d
                    if not (QMIN <= v <= QMAX):
                        continue
                    old = intm.W1[i, j]; intm.W1[i, j] = v
                    new = obj()
                    if new < cur - 1e-12:
                        cur = new; improved += 1
                    else:
                        intm.W1[i, j] = old
        for name in ("b1", "b2"):
            arr = getattr(intm, name)
            for i in range(len(arr)):
                for d in (+8, +4, +2, +1, -1, -2, -4, -8):
                    arr[i] += d
                    new = obj()
                    if new < cur - 1e-12:
                        cur = new; improved += 1
                    else:
                        arr[i] -= d
        # W2 entries
        for i in range(OUT):
            for j in range(HH):
                for d in (+1, -1, +2, -2):
                    v = intm.W2[i, j] + d
                    if not (QMIN <= v <= QMAX):
                        continue
                    old = intm.W2[i, j]; intm.W2[i, j] = v
                    new = obj()
                    if new < cur - 1e-12:
                        cur = new; improved += 1
                    else:
                        intm.W2[i, j] = old
        if verbose:
            print(f"[D] sweep {sw+1}: hinge obj {cur:.4f} ({improved} flips) "
                  f"err {intm.err_count(y_opt)}")
        if improved == 0:
            break
    return cur


def hinge(raw, y, w, margin=HINGE_MARGIN):
    """Penalise until every optimal cell beats every non-optimal legal cell by
    `margin` integer units."""
    pos = y > 0
    neg = (y == 0) & (raw > -1e8)
    pmax = raw.masked_fill(~pos, -1e9).max(1, keepdim=True).values
    nmax = raw.masked_fill(~neg, -1e9).max(1, keepdim=True).values
    viol = F.relu(margin - (pmax - nmax)).squeeze(1)
    has = (neg.any(1)).float()
    return (viol * has * w).sum() / (has * w).sum().clamp(min=1e-9)


@torch.no_grad()
def int_argmaxes(model, X, M):
    Xi = torch.round(X)
    W1q = (model.W1 / model.scale1()).round().clamp(QMIN, QMAX)
    acc = (Xi @ W1q.T + model.b1.round()).long()
    half = (1 << (model.s1 - 1)) if model.s1 > 0 else 0
    h = ((acc + half) >> model.s1).clamp(0, QMAX)
    W2q = (model.W2 / model.scale2()).round().clamp(QMIN, QMAX).long()
    lg = (h @ W2q.T + model.b2.round().long()).float()
    return (lg * M + (M - 1) * 1e9).argmax(1).numpy()


def opt_rate(model, X, M, y_opt):
    mv = int_argmaxes(model, X, M)
    return np.mean([mv[i] in y_opt[i] for i in range(len(mv))])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps-a", type=int, default=15000)
    ap.add_argument("--steps-b", type=int, default=20000)
    ap.add_argument("--steps-c", type=int, default=20000)
    ap.add_argument("--lr-a", type=float, default=3e-3)
    ap.add_argument("--lr-b", type=float, default=5e-4)
    ap.add_argument("--lr-c", type=float, default=1e-4)
    ap.add_argument("--batch", type=int, default=1024)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--resume", action="store_true", help="load model_qat.pt, skip A/B")
    ap.add_argument("--steps-d", type=int, default=6, help="phase D greedy sweeps (0=off)")
    args = ap.parse_args()
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    np.random.seed(args.seed)

    dataset, policy = oracle.load_or_build_dataset()
    y_opt = [set(p.keys()) for _, p, _v in dataset]
    X = torch.tensor([x for x, _, _v in dataset], dtype=torch.float32)
    Y = torch.zeros(len(dataset), OUT)
    for i, (_, probs, _v) in enumerate(dataset):
        for mv, p in probs.items():
            Y[i, mv] = p
    M = (X == 0).float()
    Wt = torch.ones(len(dataset))
    for i, (_, probs, val) in enumerate(dataset):
        nlegal = int(M[i].sum())
        crit = len(probs) <= max(1, nlegal // 3)
        Wt[i] = W_LOST if val < 0 else (2.0 if crit and nlegal >= 3 else 1.0)
    print(f"dataset {X.shape[0]} rows, mean weight {Wt.mean():.2f}")

    model = Qnet()
    Ymix = Y
    start_c = args.steps_c
    if args.resume:
        model.load_state_dict(torch.load(HERE / "model_qat.pt"))
    else:
        # -------- phase A: full precision
        opt = torch.optim.Adam(model.parameters(), lr=args.lr_a)
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.steps_a)
        for step in range(1, args.steps_a + 1):
            idx = torch.randint(0, X.shape[0], (args.batch,))
            model.train()
            logits, _ = model(X[idx], M[idx], quant=False)
            loss = wce(logits, Y[idx], Wt[idx])
            opt.zero_grad(); loss.backward(); sched.step(); opt.step()
            if step % 3000 == 0 or step == args.steps_a:
                model.eval()
                with torch.no_grad():
                    mv = model(X, M, quant=False)[0].argmax(1).numpy()
                hit = np.mean([mv[i] in y_opt[i] for i in range(len(mv))])
                print(f"[A] step {step:6d} loss {loss.item():.4f} fp32 optimal {hit*100:.2f}%")
        with torch.no_grad():
            model.eval()
            teacher = F.softmax(model(X, M, quant=False)[0] / TEACHER_T, 1)
        Ymix = (1 - TEACHER_MIX) * Y + TEACHER_MIX * teacher
        Ymix = Ymix * M
        Ymix = Ymix / Ymix.sum(1, keepdim=True).clamp(min=1e-9)

        # -------- phase B: QAT CE
        model.max_acc = 0.0
        opt = torch.optim.Adam(model.parameters(), lr=args.lr_b)
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.steps_b)
        for step in range(1, args.steps_b + 1):
            idx = torch.randint(0, X.shape[0], (args.batch,))
            model.train()
            logits, raw = model(X[idx], M[idx])
            loss = wce(logits, Ymix[idx], Wt[idx])
            opt.zero_grad(); loss.backward(); sched.step(); opt.step()
            if step % 5000 == 0 or step == args.steps_b:
                print(f"[B] step {step:6d} loss {loss.item():.4f} int optimal {opt_rate(model, X, M, y_opt)*100:.2f}% s1={model.s1}")

    # -------- phase C: QAT hinge polish (argmax order at integer precision)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr_c)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, start_c)
    lam = 3.0
    for step in range(1, start_c + 1):
        idx = torch.randint(0, X.shape[0], (args.batch,))
        model.train()
        logits, raw = model(X[idx], M[idx])
        loss = wce(logits, Y[idx], Wt[idx]) + lam * hinge(raw, Y[idx], Wt[idx])
        opt.zero_grad(); loss.backward(); sched.step(); opt.step()
        if step % 2000 == 0 or step == start_c:
            print(f"[C] step {step:6d} loss {loss.item():.4f} int optimal {opt_rate(model, X, M, y_opt)*100:.2f}% s1={model.s1}")

    acc = opt_rate(model, X, M, y_opt)
    print(f"phase C int4 argmax-optimal: {acc*100:.2f}%")
    torch.save(model.state_dict(), HERE / "model_qat.pt")

    # -------- phase D: exact integer greedy coordinate descent
    if args.steps_d:
        we = model.int_export()
        intm = IntModel(X, M, we["W1"], we["b1"], we["W2"], we["b2"], we["s1"])
        greedy_polish(intm, Y, Wt, y_opt, sweeps=args.steps_d)
        err = intm.err_count(y_opt)
        print(f"phase D int argmax-optimal: {(1 - err/len(y_opt))*100:.2f}%")
        we = {"s1": intm.s1, "W1": intm.W1, "b1": intm.b1, "W2": intm.W2, "b2": intm.b2}
    else:
        we = model.int_export()
    export_weights(we)
    check_bit_exact(model, we)


def export_weights(w, path=HERE / "weights.txt"):
    lines = ["# tres-en-raya 9-16-9 int4 signed network (see int4_net.py for semantics)",
             f"s1 {w['s1']}"]
    for name in ("W1", "b1", "W2", "b2"):
        arr = np.ravel(w[name])
        lines.append(f"{name} " + "\n".join(str(int(v)) for v in arr))
    path.write_text("\n".join(lines) + "\n")
    n = sum(int(np.ravel(w[k]).size) for k in ("W1", "b1", "W2", "b2"))
    print(f"wrote {path} ({n} ints: W1 144, b1 16, W2 144, b2 9)")


def check_bit_exact(model, w_int=None):
    """int4_net.py python forward must equal torch integer path on all rows."""
    import int4_net
    w = int4_net.load_weights(HERE / "weights.txt")
    if w_int is not None:  # verify exported dict matches file parse
        assert np.array_equal(np.ravel(w_int["W1"]), np.ravel(w["W1"]))
    dataset, _ = oracle.load_or_build_dataset()
    X = torch.tensor([x for x, _, _v in dataset], dtype=torch.float32).round()
    with torch.no_grad():
        if w_int is None:
            W1q = (model.W1 / model.scale1()).round().clamp(QMIN, QMAX)
            W2q = (model.W2 / model.scale2()).round().clamp(QMIN, QMAX)
            b1, b2, s1 = model.b1.round(), model.b2.round(), model.s1
        else:
            W1q = torch.tensor(w_int["W1"]); W2q = torch.tensor(w_int["W2"])
            b1, b2, s1 = torch.tensor(w_int["b1"]), torch.tensor(w_int["b2"]), int(w_int["s1"])
        acc = torch.round(X @ W1q.float().T + b1.float()).long()
        half = (1 << (s1 - 1)) if s1 > 0 else 0
        h = ((acc + half) >> s1).clamp(0, QMAX)
        lt = torch.round(h.float() @ W2q.float().T + b2.float()).long()
    n_bad = sum(1 for i in range(X.shape[0])
                if int4_net.forward(w, [int(v) for v in X[i]]) != [int(v) for v in lt[i]])
    print(f"bit-exact check (python vs torch int path): {X.shape[0]-n_bad}/{X.shape[0]} identical")
    assert n_bad == 0


if __name__ == "__main__":
    main()
