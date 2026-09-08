"""Evaluate the int4 net by playing games vs fixed opponents."""
from __future__ import annotations

import argparse
import random
from collections import Counter

import int4_net
import oracle

WINS3 = oracle.WINS


def line_win(board, p):
    return any(board[a] == board[b] == board[c] == p for a, b, c in WINS3)


def greedy_move(board, turn):
    opp = 3 - turn
    empty = [i for i in range(9) if board[i] == 0]
    for p in (turn, opp):
        for mv in empty:
            b2 = list(board); b2[mv] = p
            if line_win(b2, p):
                return mv
    for pref in (4, 0, 2, 6, 8, 1, 3, 5, 7):
        if board[pref] == 0:
            return pref
    return empty[0]


class Opponent:
    def __init__(self, kind, policy):
        self.kind = kind
        self.policy = policy

    def move(self, board, turn, rng):
        if self.kind == "random":
            return rng.choice([i for i in range(9) if board[i] == 0])
        if self.kind == "greedy":
            return greedy_move(board, turn)
        if self.kind == "perfect":
            return rng.choice(self.policy["".join(map(str, board)) + str(turn)])
        raise ValueError(self.kind)


def play_game(w, opponent, net_player, rng):
    board = [0] * 9
    turn = 1
    while True:
        if line_win(board, 1):
            return "X"
        if line_win(board, 2):
            return "O"
        if all(board):
            return "D"
        if turn == net_player:
            mv = int4_net.choose_action(w, int4_net.encode_self(board, turn), tuple(board), turn)
        else:
            mv = opponent.move(tuple(board), turn, rng)
        board[mv] = turn
        turn = 3 - turn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="weights.txt")
    ap.add_argument("--games", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=123)
    args = ap.parse_args()
    w = int4_net.load_weights(args.weights)
    _, policy = oracle.load_or_build_dataset()
    rng = random.Random(args.seed)

    for kind in ("random", "greedy", "perfect"):
        opp = Opponent(kind, policy)
        tally = Counter()
        for g in range(args.games):
            net_player = 1 if g % 2 else 2
            r = play_game(w, opp, net_player, rng)
            if r == "D":
                tally["draw"] += 1
            elif (r == "X") == (net_player == 1):
                tally["win"] += 1
            else:
                tally["loss"] += 1
        t = args.games
        print(f"vs {kind:8s}: win {tally['win']/t*100:5.1f}%  draw {tally['draw']/t*100:5.1f}%  "
              f"loss {tally['loss']/t*100:5.1f}%")


if __name__ == "__main__":
    main()
