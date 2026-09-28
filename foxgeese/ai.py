"""Intelligence artificielle : recherche minimax avec élagage alpha-bêta.

L'IA explore les coups possibles quelques tours à l'avance et choisit celui qui
mène à la meilleure position selon une fonction d'évaluation (score positif =
bon pour le renard, négatif = bon pour les oies).
"""

from __future__ import annotations

import random
import time

from .rules import (FOX, GOOSE, JUMPS, POINTS, SIZE, STEPS, State, apply,
                    is_capture, legal_moves, rc)

WIN = 100_000

LEVELS = {
    # nom affiché : (profondeur max, temps max en s, part de coups aléatoires)
    "Facile": (1, 0.3, 0.45),
    "Moyen": (3, 0.8, 0.0),
    "Difficile": (12, 1.6, 0.0),
}


class _Timeout(Exception):
    pass


def evaluate(s: State) -> float:
    if s.winner == FOX:
        return WIN - s.plies
    if s.winner == GOOSE:
        return -WIN + s.plies
    if s.winner == "draw":
        return 0

    cells = s.cells
    score = s.captured * 140.0
    lowest_goose = -1
    for i in POINTS:
        if cells[i] == GOOSE:
            r = rc(i)[0]
            lowest_goose = max(lowest_goose, r)
            # Les oies ont intérêt à avancer groupées vers le haut
            score -= (SIZE - 1 - r) * 4
    for i in POINTS:
        if cells[i] != FOX:
            continue
        r = rc(i)[0]
        steps = sum(1 for t in STEPS[i] if cells[t] == ".")
        threats = sum(1 for over, to in JUMPS[i] if cells[over] == GOOSE and cells[to] == ".")
        score += steps * 7 + threats * 45 + r * 6
        if steps == 0 and threats == 0:
            score -= 90                     # renard immobilisé : dangereux pour lui
        if r > lowest_goose:
            score += 400                    # renard derrière toutes les oies : imprenable
    return score


def _ordered(s: State, moves, best=None):
    def prio(m):
        if m == best:
            return -2
        return -1 if is_capture(m) else 0
    return sorted(moves, key=prio)


class Searcher:
    def __init__(self, time_limit: float):
        self.deadline = time.monotonic() + time_limit
        self.tt: dict[tuple, tuple[int, float, object]] = {}
        self.nodes = 0

    def search(self, s: State, depth: int, alpha: float, beta: float) -> float:
        self.nodes += 1
        if self.nodes & 1023 == 0 and time.monotonic() > self.deadline:
            raise _Timeout
        if depth == 0 or s.winner:
            return evaluate(s)
        key = s.key()
        hit = self.tt.get(key)
        best_hint = None
        if hit:
            if hit[0] >= depth:
                return hit[1]
            best_hint = hit[2]
        moves = legal_moves(s)
        maximizing = s.turn == FOX
        alpha0, beta0 = alpha, beta
        best_val = -float("inf") if maximizing else float("inf")
        best_move = None
        for m in _ordered(s, moves, best_hint):
            v = self.search(apply(s, m), depth - 1, alpha, beta)
            if maximizing:
                if v > best_val:
                    best_val, best_move = v, m
                alpha = max(alpha, v)
            else:
                if v < best_val:
                    best_val, best_move = v, m
                beta = min(beta, v)
            if beta <= alpha:
                break
        # On ne mémorise la valeur que si elle est exacte (ni coupure, ni borne)
        exact = alpha0 < best_val < beta0
        self.tt[key] = (depth if exact else 0, best_val, best_move)
        return best_val


def choose_move(s: State, level: str = "Moyen", rng: random.Random | None = None):
    """Choisit le coup de l'IA pour le camp dont c'est le tour."""
    rng = rng or random.Random()
    max_depth, limit, randomness = LEVELS[level]
    moves = legal_moves(s)
    if not moves:
        return None
    if len(moves) == 1:
        return moves[0]
    if randomness and rng.random() < randomness:
        return rng.choice(moves)

    searcher = Searcher(limit)
    maximizing = s.turn == FOX
    best_move = rng.choice(moves)
    for depth in range(1, max_depth + 1):
        try:
            scored = []
            for m in _ordered(s, moves, best_move):
                scored.append((searcher.search(apply(s, m), depth - 1, -float("inf"), float("inf")), m))
        except _Timeout:
            break
        target = max(v for v, _ in scored) if maximizing else min(v for v, _ in scored)
        # Petite part de hasard entre coups équivalents : l'IA ne joue pas toujours pareil
        best = [m for v, m in scored if abs(v - target) < 1e-6]
        best_move = rng.choice(best)
        if abs(target) > WIN / 2:
            break                            # gain ou perte forcé trouvé : inutile d'aller plus loin
    return best_move
