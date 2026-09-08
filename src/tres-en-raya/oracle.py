"""Perfect-play tic-tac-toe oracle: game-tree enumeration + minimax policy.

Board is a tuple of 9 ints: 0 empty, 1 X, 2 O. Turn is the player to move.
"""
from __future__ import annotations

import functools
import itertools
import json
from pathlib import Path

WINS = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),  # cols
    (0, 4, 8), (2, 4, 6),             # diags
]

# 8 board symmetries (D4 group) as source-index permutations: tb[i] = b[perm[i]]
def _perm_move(mapper):
    perm = [0] * 9
    for src in range(9):
        dst = mapper(src)
        perm[dst] = src
    return tuple(perm)


_ROT = _perm_move(lambda i: 3 * (i % 3) + (2 - i // 3))   # 90 deg CW
_FLIP = _perm_move(lambda i: 3 * (i // 3) + (2 - i % 3))  # horizontal mirror


def _compose(p1, p2):
    return tuple(p1[p2[i]] for i in range(9))


SYMMETRIES = []
_p = tuple(range(9))
for _ in range(4):
    SYMMETRIES.append(_p)
    SYMMETRIES.append(_compose(_FLIP, _p))
    _p = _compose(_p, _ROT)
SYMMETRIES = list(dict.fromkeys(SYMMETRIES))
assert len(SYMMETRIES) == 8

# self-perspective input encoding (int4)
VAL_SELF, VAL_OPP, VAL_EMPTY = 4, -4, 0


def winner(board: tuple[int, ...]) -> int:
    for a, b, c in WINS:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return 0 if 0 not in board else -1  # 0 = draw, -1 = not terminal


def legal_moves(board: tuple[int, ...]) -> list[int]:
    return [i for i in range(9) if board[i] == 0]


def apply_move(board: tuple[int, ...], mv: int, player: int) -> tuple[int, ...]:
    lst = list(board)
    lst[mv] = player
    return tuple(lst)


def _negamax(board, turn, depth, seen):
    """Score from `turn`'s perspective: win=10-depth, loss=depth-10, draw=0."""
    w = winner(board)
    if w != -1:
        return 0 if w == 0 else (10 - depth if w == turn else depth - 10)
    key = (board, turn)
    if key in seen:
        return seen[key]
    opp = 3 - turn
    best = -99
    for mv in legal_moves(board):
        s = -_negamax(apply_move(board, mv, turn), opp, depth + 1, seen)
        best = max(best, s)
    seen[key] = best
    return best


def optimal_moves(board: tuple[int, ...], turn: int) -> list[int]:
    """Moves achieving the minimax value (prefers quick wins / slow losses)."""
    seen: dict = {}
    w = winner(board)
    if w != -1:
        return []
    opp = 3 - turn
    scores = [-_negamax(apply_move(board, mv, turn), opp, 1, seen) for mv in legal_moves(board)]
    best = max(scores)
    return [mv for mv, s in zip(legal_moves(board), scores) if s == best]


def enumerate_states() -> list[tuple[tuple[int, ...], int, list[int]]]:
    """All reachable non-terminal (board, turn) states with their optimal moves."""
    states: dict[tuple[tuple[int, ...], int], list[int]] = {}
    stack = [((0,) * 9, 1)]
    while stack:
        board, turn = stack.pop()
        if (board, turn) in states:
            continue
        states[(board, turn)] = optimal_moves(board, turn)
        for mv in legal_moves(board):
            nxt = apply_move(board, mv, turn)
            if winner(nxt) == -1:
                stack.append((nxt, 3 - turn))
    return [(b, t, m) for (b, t), m in states.items()]


def encode_self(board: tuple[int, ...], turn: int) -> list[int]:
    """int4 input vector from the perspective of `turn`."""
    return [VAL_SELF if v == turn else VAL_OPP if v else VAL_EMPTY for v in board]


def transform_board(board: tuple[int, ...], perm: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(board[perm[i]] for i in range(9))


def build_dataset() -> list[tuple[tuple[int, ...], tuple[float, ...], int]]:
    """(x, label_prob, state_value) rows. state_value is the minimax score of
    the state from the mover's perspective (>0 win, 0 draw, <0 loss)."""
    out = []
    for board, turn, opts in enumerate_states():
        val = _negamax(board, turn, 0, {})
        for perm in SYMMETRIES:
            tb = transform_board(board, perm)
            to = {perm.index(m) for m in opts}  # map move squares through symmetry
            probs = {m: 1.0 / len(to) for m in to}
            out.append((tuple(encode_self(tb, turn)), probs, val))
    return out


def policy_table() -> dict[str, list[int]]:
    """Perfect-play policy keyed by f'{board_str}{turn}' for the evaluation agent."""
    return {"".join(map(str, b)) + str(t): m for b, t, m in enumerate_states()}


CACHE = Path(__file__).parent / ".oracle_cache.json"
CACHE_VERSION = 2


def load_or_build_dataset(verbose=True):
    """Returns (rows, policy) where rows are (x, probs_dict, state_value)."""
    if CACHE.exists():
        cached = json.loads(CACHE.read_text())
        if cached.get("version") == CACHE_VERSION:
            return ([(tuple(x), {int(k): v for k, v in p.items()}, val)
                     for x, p, val in cached["dataset"]], cached["policy"])
    states = enumerate_states()
    if verbose:
        print(f"{len(states)} reachable non-terminal (state,turn) pairs")
    dataset = build_dataset()
    table = {"".join(map(str, b)) + str(t): m for b, t, m in states}
    if verbose:
        vals = [_negamax(b, t, 0, {}) for b, t, _ in states]
        print(f"dataset rows: {len(dataset)}  |  win/draw/loss states: "
              f"{sum(v > 0 for v in vals)}/{sum(v == 0 for v in vals)}/{sum(v < 0 for v in vals)}")
    CACHE.write_text(json.dumps({
        "version": CACHE_VERSION,
        "dataset": [(list(x), {str(k): v for k, v in p.items()}, val) for x, p, val in dataset],
        "policy": table,
    }))
    return dataset, table


if __name__ == "__main__":
    load_or_build_dataset()
