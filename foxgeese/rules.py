"""Règles du jeu Fox and Geese — logique pure, sans aucun affichage.

Le plateau est la croix classique de 33 intersections, stockée dans une grille 7x7
(49 cases, dont 16 hors plateau). Les lignes orthogonales relient toutes les
intersections ; les diagonales n'existent que sur les points où (ligne + colonne)
est pair, comme sur le plateau traditionnel.

Cette séparation logique / interface permet de réutiliser exactement les mêmes
règles pour l'affichage, l'IA et le mode en ligne (les deux joueurs appliquent
les mêmes coups et obtiennent donc le même plateau).
"""

from __future__ import annotations

from dataclasses import dataclass

SIZE = 7
FOX = "F"
GOOSE = "G"
EMPTY = "."
OFF = " "

# Coup spécial : le renard arrête volontairement une rafle (captures en chaîne)
PASS = (-1, -1)

ORTHO = [(-1, 0), (1, 0), (0, -1), (0, 1)]
DIAG = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
# Les oies avancent vers le haut (vers le renard), jamais en arrière
GOOSE_DIRS = {(-1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1)}


def idx(r: int, c: int) -> int:
    return r * SIZE + c


def rc(i: int) -> tuple[int, int]:
    return divmod(i, SIZE)


def on_board(r: int, c: int) -> bool:
    if not (0 <= r < SIZE and 0 <= c < SIZE):
        return False
    return 2 <= r <= 4 or 2 <= c <= 4


POINTS = [idx(r, c) for r in range(SIZE) for c in range(SIZE) if on_board(r, c)]


def _directions(r: int, c: int) -> list[tuple[int, int]]:
    return ORTHO + DIAG if (r + c) % 2 == 0 else list(ORTHO)


def _build_tables():
    steps, jumps, goose_steps, lines = {}, {}, {}, set()
    for i in POINTS:
        r, c = rc(i)
        steps[i], jumps[i], goose_steps[i] = [], [], []
        for dr, dc in _directions(r, c):
            r1, c1 = r + dr, c + dc
            if not on_board(r1, c1):
                continue
            steps[i].append(idx(r1, c1))
            lines.add(tuple(sorted((i, idx(r1, c1)))))
            if (dr, dc) in GOOSE_DIRS:
                goose_steps[i].append(idx(r1, c1))
            r2, c2 = r + 2 * dr, c + 2 * dc
            if on_board(r2, c2):
                jumps[i].append((idx(r1, c1), idx(r2, c2)))
    return steps, jumps, goose_steps, sorted(lines)


# Tables précalculées une fois pour toutes (accélère énormément l'IA)
STEPS, JUMPS, GOOSE_STEPS, LINES = _build_tables()


# --- Configurations de départ (reprises du projet original de 2023) ---------

def _layout(rows: list[str]) -> list[str]:
    cells = []
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            cells.append(ch if on_board(r, c) else OFF)
    return cells


SETUPS = {
    "1-13": _layout([
        "  ...  ",
        "  ...  ",
        "...F...",
        ".......",
        "GGGGGGG",
        "  GGG  ",
        "  GGG  ",
    ]),
    "1-15": _layout([
        "  ...  ",
        "  ...  ",
        "...F...",
        "G.....G",
        "GGGGGGG",
        "  GGG  ",
        "  GGG  ",
    ]),
    "1-17": _layout([
        "  ...  ",
        "  ...  ",
        "G..F..G",
        "G.....G",
        "GGGGGGG",
        "  GGG  ",
        "  GGG  ",
    ]),
    "2-20": _layout([
        "  ...  ",
        "  F.F  ",
        ".......",
        "GGGGGGG",
        "GGGGGGG",
        "  GGG  ",
        "  GGG  ",
    ]),
    "2-27": _layout([
        "  F.F  ",
        "  ...  ",
        "GGGGGGG",
        "GGGGGGG",
        "GGGGGGG",
        "  GGG  ",
        "  GGG  ",
    ]),
}

SETUP_ORDER = ["1-13", "1-15", "1-17", "2-20", "2-27"]

# Il faut au moins 4 oies pour immobiliser un renard (3 voisines + 1 pour bloquer
# le saut) : en dessous de ce seuil, les oies ne peuvent plus gagner.
GEESE_PER_FOX = 4

REASONS = {
    "fox_trapped": "Le renard est encerclé, il ne peut plus bouger !",
    "geese_stuck": "Les oies sont bloquées, elles ne peuvent plus avancer.",
    "too_few_geese": "Trop d'oies ont été croquées pour piéger le renard.",
    "fox_breakthrough": "Le renard a percé les lignes jusqu'au fond du plateau !",
    "repetition": "Même position trois fois : match nul.",
}


@dataclass
class State:
    cells: list[str]
    turn: str = FOX
    chain: int | None = None      # renard en pleine rafle (doit re-capturer ou passer)
    captured: int = 0
    fox_count: int = 1
    winner: str | None = None     # FOX, GOOSE, ou "draw"
    reason: str | None = None
    plies: int = 0

    @classmethod
    def new(cls, setup: str) -> "State":
        cells = list(SETUPS[setup])
        return cls(cells=cells, fox_count=cells.count(FOX))

    def copy(self) -> "State":
        return State(list(self.cells), self.turn, self.chain, self.captured,
                     self.fox_count, self.winner, self.reason, self.plies)

    @property
    def geese_left(self) -> int:
        return self.cells.count(GOOSE)

    def key(self) -> tuple:
        """Identifiant de position (pour la règle de répétition et l'IA)."""
        return ("".join(self.cells), self.turn, self.chain)

    def to_dict(self) -> dict:
        return {"cells": "".join(self.cells), "turn": self.turn, "chain": self.chain,
                "captured": self.captured, "fox_count": self.fox_count,
                "winner": self.winner, "reason": self.reason, "plies": self.plies}


def fox_moves(s: State, i: int, captures_only: bool = False) -> list[tuple[int, int]]:
    cells = s.cells
    moves = [(i, to) for over, to in JUMPS[i] if cells[over] == GOOSE and cells[to] == EMPTY]
    if not captures_only:
        moves += [(i, to) for to in STEPS[i] if cells[to] == EMPTY]
    return moves


def goose_moves(s: State, i: int) -> list[tuple[int, int]]:
    cells = s.cells
    return [(i, to) for to in GOOSE_STEPS[i] if cells[to] == EMPTY]


def legal_moves(s: State) -> list[tuple[int, int]]:
    if s.winner:
        return []
    if s.turn == FOX:
        if s.chain is not None:
            return fox_moves(s, s.chain, captures_only=True) + [PASS]
        moves = []
        for i in POINTS:
            if s.cells[i] == FOX:
                moves += fox_moves(s, i)
        return moves
    moves = []
    for i in POINTS:
        if s.cells[i] == GOOSE:
            moves += goose_moves(s, i)
    return moves


def moves_from(s: State, i: int) -> list[tuple[int, int]]:
    """Coups jouables par la pièce située en i (pour l'affichage des cibles)."""
    return [m for m in legal_moves(s) if m[0] == i]


def is_capture(m: tuple[int, int]) -> bool:
    if m == PASS:
        return False
    (r0, c0), (r1, c1) = rc(m[0]), rc(m[1])
    return max(abs(r1 - r0), abs(c1 - c0)) == 2


def apply(s: State, m: tuple[int, int]) -> State:
    """Renvoie le nouvel état après le coup m (l'état d'origine n'est pas modifié)."""
    n = s.copy()
    n.plies += 1
    if m == PASS:
        n.chain = None
        _end_turn(n)
        return n
    frm, to = m
    piece = n.cells[frm]
    n.cells[frm], n.cells[to] = EMPTY, piece
    if piece == FOX and is_capture(m):
        over = (frm + to) // 2
        n.cells[over] = EMPTY
        n.captured += 1
        if n.geese_left < GEESE_PER_FOX * n.fox_count:
            _finish(n, FOX, "too_few_geese")
            return n
        if fox_moves(n, to, captures_only=True):
            n.chain = to           # rafle : le même renard peut recapturer
            return n
    n.chain = None
    _end_turn(n)
    return n


def _finish(s: State, winner: str, reason: str) -> None:
    s.winner, s.reason, s.chain = winner, reason, None


def _end_turn(s: State) -> None:
    if any(s.cells[idx(SIZE - 1, c)] == FOX for c in range(SIZE)):
        return _finish(s, FOX, "fox_breakthrough")
    s.turn = GOOSE if s.turn == FOX else FOX
    if not legal_moves(s):
        if s.turn == FOX:
            _finish(s, GOOSE, "fox_trapped")
        else:
            _finish(s, FOX, "geese_stuck")


class Match:
    """Une partie complète : état courant + historique (annuler, sauvegarde, répétition)."""

    def __init__(self, setup: str, moves: list | None = None):
        self.setup = setup
        self.history: list[State] = [State.new(setup)]
        self.moves: list[tuple[int, int]] = []
        self.keys: list[tuple] = [self.state.key()]
        self.seen: dict[tuple, int] = {self.keys[0]: 1}
        for m in moves or []:
            self.play(tuple(m))

    @property
    def state(self) -> State:
        return self.history[-1]

    def play(self, m: tuple[int, int]) -> State:
        if m not in legal_moves(self.state):
            raise ValueError(f"Coup illégal : {m}")
        n = apply(self.state, m)
        k = n.key()
        self.seen[k] = self.seen.get(k, 0) + 1
        if not n.winner and self.seen[k] >= 3:
            _finish(n, "draw", "repetition")
        self.keys.append(k)
        self.history.append(n)
        self.moves.append(m)
        return n

    def undo(self) -> bool:
        if len(self.history) <= 1:
            return False
        self.seen[self.keys.pop()] -= 1
        self.history.pop()
        self.moves.pop()
        return True
