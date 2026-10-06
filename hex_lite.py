#!/usr/bin/env python3
"""hex-lite: 极简 Hex 连接棋。

规则: 菱形棋盘上,红方(先手)把上下两条边连起来,蓝方把左右两条边连起来。
Hex 定理保证满盘必有一方获胜,不会和棋。纯标准库。
"""
import argparse
import heapq
import random
import sys
from collections import deque

EMPTY, P1, P2 = 0, 1, 2
NAMES = {P1: "红", P2: "蓝"}
GLYPH = {EMPTY: "·", P1: "●", P2: "○"}
# 菱形棋盘六邻居(行列偏移)
NEIGH = [(-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0)]
INF = 10 ** 9


class Hex:
    """n x n Hex 棋盘。P1 连上下边, P2 连左右边。"""

    def __init__(self, n=7):
        if n < 3:
            raise ValueError("棋盘至少 3x3")
        self.n = n
        self.board = [[EMPTY] * n for _ in range(n)]
        self.moves = 0
        self.turn = P1

    def in_bounds(self, r, c):
        return 0 <= r < self.n and 0 <= c < self.n

    def legal_moves(self):
        return [(r, c) for r in range(self.n) for c in range(self.n)
                if self.board[r][c] == EMPTY]

    def play(self, r, c):
        """落子,非法抛 ValueError。"""
        if not self.in_bounds(r, c):
            raise ValueError(f"越界: ({r},{c})")
        if self.board[r][c] != EMPTY:
            raise ValueError(f"格子已被占: ({r},{c})")
        self.board[r][c] = self.turn
        self.moves += 1
        self.turn = P2 if self.turn == P1 else P1

    def winner(self):
        """返回获胜方 P1/P2,无胜者返回 None。"""
        edges = {
            P1: ([(0, c) for c in range(self.n)],
                 {(self.n - 1, c) for c in range(self.n)}),
            P2: ([(r, 0) for r in range(self.n)],
                 {(r, self.n - 1) for r in range(self.n)}),
        }
        for player, (starts, targets) in edges.items():
            seen = set()
            dq = deque()
            for r, c in starts:
                if self.board[r][c] == player:
                    seen.add((r, c))
                    dq.append((r, c))
            while dq:
                r, c = dq.popleft()
                if (r, c) in targets:
                    return player
                for dr, dc in NEIGH:
                    nr, nc = r + dr, c + dc
                    if (self.in_bounds(nr, nc) and (nr, nc) not in seen
                            and self.board[nr][nc] == player):
                        seen.add((nr, nc))
                        dq.append((nr, nc))
        return None

    def is_full(self):
        return self.moves >= self.n * self.n


def shortest_path_cost(board, n, player):
    """虚连接距离:己方子代价 0,空格代价 1,敌子不可走。返回最短代价。"""
    foe = P2 if player == P1 else P1
    dist = [[INF] * n for _ in range(n)]
    hq = []
    if player == P1:
        starts, ends = [(0, c) for c in range(n)], {(n - 1, c) for c in range(n)}
    else:
        starts, ends = [(r, 0) for r in range(n)], {(r, n - 1) for r in range(n)}
    for r, c in starts:
        if board[r][c] == foe:
            continue
        cost = 0 if board[r][c] == player else 1
        if cost < dist[r][c]:
            dist[r][c] = cost
            heapq.heappush(hq, (cost, r, c))
    while hq:
        d, r, c = heapq.heappop(hq)
        if d > dist[r][c]:
            continue
        if (r, c) in ends:
            return d
        for dr, dc in NEIGH:
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < n and board[nr][nc] != foe:
                nd = d + (0 if board[nr][nc] == player else 1)
                if nd < dist[nr][nc]:
                    dist[nr][nc] = nd
                    heapq.heappush(hq, (nd, nr, nc))
    return INF


def ai_choose(game, player, rng):
    """1 步前瞻:优先即时胜,否则最大化(对手虚连接距离 - 己方虚连接距离)。"""
    moves = game.legal_moves()
    if not moves:
        return None
    n = game.n
    foe = P2 if player == P1 else P1
    best, best_score = None, -INF
    for r, c in moves:
        game.board[r][c] = player
        win = game.winner() == player
        if win:
            game.board[r][c] = EMPTY
            return (r, c)
        mine = shortest_path_cost(game.board, n, player)
        theirs = shortest_path_cost(game.board, n, foe)
        game.board[r][c] = EMPTY
        score = theirs - mine + rng.random() * 0.01
        if score > best_score:
            best, best_score = (r, c), score
    return best


def render(game):
    """文本棋盘(菱形缩进)。"""
    n = game.n
    lines = []
    for r in range(n):
        pad = " " * r
        row = " ".join(GLYPH[game.board[r][c]] for c in range(n))
        lines.append(f"{pad}{r:2d} {row}")
    head = "   " + " ".join(f"{c:2d}" for c in range(n))
    return head + "\n" + "\n".join(lines)


def play_auto(n=7, seed=42, verbose=False):
    """AI 对 AI 一局,返回 (winner, moves)。"""
    rng = random.Random(seed)
    game = Hex(n)
    while True:
        w = game.winner()
        if w or game.is_full():
            return w, game.moves
        mv = ai_choose(game, game.turn, rng)
        if mv is None:
            return game.winner(), game.moves
        if verbose:
            print(f"{NAMES[game.turn]} 走 {mv}")
            game.play(*mv)
            print(render(game))
        else:
            game.play(*mv)


def play_interactive(n=7, seed=None):
    """人机对战:人类执红先手,AI 执蓝。"""
    if not sys.stdin.isatty():
        print("交互模式需要终端;无头演示请用 --auto", file=sys.stderr)
        sys.exit(2)
    rng = random.Random(seed)
    game = Hex(n)
    print(f"Hex {n}x{n}: 红(你,●)连上下边, 蓝(AI,○)连左右边。输入如 '3 4',q 退出。")
    while True:
        print(render(game))
        w = game.winner()
        if w:
            print(f"{NAMES[w]}方获胜!")
            return
        if game.is_full():
            print("满盘(按定理必有一方已胜,此处为兜底)。")
            return
        if game.turn == P1:
            try:
                s = input("你走 (行 列): ").strip()
            except EOFError:
                print()
                return
            if s.lower() in ("q", "quit", "退出"):
                return
            try:
                r, c = map(int, s.split())
                game.play(r, c)
            except (ValueError, IndexError) as e:
                print(f"非法走法: {e}")
        else:
            mv = ai_choose(game, P2, rng)
            print(f"AI 走 {mv}")
            game.play(*mv)


def main(argv=None):
    ap = argparse.ArgumentParser(description="hex-lite: 极简 Hex 连接棋")
    ap.add_argument("--size", type=int, default=7, help="棋盘边长(默认7,标准11)")
    ap.add_argument("--auto", action="store_true", help="AI 对 AI 自动演示")
    ap.add_argument("--games", type=int, default=10, help="自动演示局数")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--verbose", action="store_true", help="自动演示打印每步")
    args = ap.parse_args(argv)
    if args.auto:
        w1 = w2 = draws = 0
        for i in range(args.games):
            w, mv = play_auto(args.size, args.seed + i, args.verbose)
            if w == P1:
                w1 += 1
            elif w == P2:
                w2 += 1
            else:
                draws += 1
            print(f"第 {i + 1}/{args.games} 局: "
                  f"{NAMES[w] + '胜' if w else '和棋'} ({mv} 手)")
        print(f"总计: 红胜 {w1}, 蓝胜 {w2}, 和棋 {draws}")
    else:
        play_interactive(args.size, args.seed)


if __name__ == "__main__":
    main()
