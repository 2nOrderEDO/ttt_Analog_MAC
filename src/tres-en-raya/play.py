"""Play tic-tac-toe against the int4 network (pure-integer path, no torch).

    uv run play.py            # net plays O (default)
    uv run play.py --x        # net plays X
Enter cells 1-9:
    1 2 3
    4 5 6
    7 8 9
"""
from __future__ import annotations

import argparse
from pathlib import Path

import int4_net

HERE = Path(__file__).parent
WINS = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
MARK = {0: ".", 1: "X", 2: "O"}


def line_win(board, p):
    return any(board[a] == board[b] == board[c] == p for a, b, c in WINS)


def show(board):
    cells = []
    for i, v in enumerate(board):
        cells.append(MARK[v] if v else str(i + 1))
    print()
    for r in range(3):
        print("  " + " | ".join(cells[3 * r:3 * r + 3]))
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--x", action="store_true", help="net plays X (moves first)")
    ap.add_argument("--weights", default=str(HERE / "weights.txt"))
    args = ap.parse_args()
    w = int4_net.load_weights(args.weights)
    net_player = 1 if args.x else 2
    human = 3 - net_player
    board = [0] * 9
    turn = 1
    print(f"You play {MARK[human]}, the int4 net plays {MARK[net_player]}. Enter 1-9 (q to quit).")
    while True:
        show(board)
        if line_win(board, 1) or line_win(board, 2) or all(board):
            break
        if turn == human:
            s = input(f"your move [{MARK[turn]}] (1-9, q): ").strip().lower()
            if s in ("q", "quit"):
                print("aborting.")
                return
            try:
                mv = int(s) - 1
            except ValueError:
                print("enter 1-9")
                continue
            if not 0 <= mv <= 8 or board[mv]:
                print("illegal cell")
                continue
        else:
            mv = int4_net.choose_action(w, int4_net.encode_self(board, turn), tuple(board), turn)
            print(f"net [{MARK[turn]}] plays cell {mv + 1}")
        board[mv] = turn
        turn = 3 - turn
    show(board)
    if line_win(board, human):
        print("you win!")
    elif line_win(board, net_player):
        print("the net wins.")
    else:
        print("draw.")


if __name__ == "__main__":
    main()
