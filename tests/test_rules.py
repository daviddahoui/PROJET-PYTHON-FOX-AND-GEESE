import random

import pytest

from foxgeese import ai, rules
from foxgeese.rules import EMPTY, FOX, GOOSE, PASS, Match, State, idx, legal_moves


def empty_state(fox_at, geese, turn=FOX):
    cells = [rules.OFF] * 49
    for i in rules.POINTS:
        cells[i] = EMPTY
    for i in fox_at:
        cells[i] = FOX
    for i in geese:
        cells[i] = GOOSE
    return State(cells=cells, turn=turn, fox_count=len(fox_at))


def test_board_shape():
    assert len(rules.POINTS) == 33
    # 3 bras x 2 + centre : chaque configuration a le bon nombre de pièces
    for key, cells in rules.SETUPS.items():
        foxes, geese = map(int, key.split("-"))
        assert cells.count(FOX) == foxes and cells.count(GOOSE) == geese


def test_diagonals_only_on_even_points():
    # (2,3) est un point « impair » : pas de diagonale
    assert sorted(rules.STEPS[idx(2, 3)]) == sorted([idx(1, 3), idx(3, 3), idx(2, 2), idx(2, 4)])
    # le centre (3,3) a 8 voisins
    assert len(rules.STEPS[idx(3, 3)]) == 8


def test_geese_never_move_backwards():
    s = empty_state([idx(0, 3)], [idx(3, 3)], turn=GOOSE)
    targets = {to for _, to in legal_moves(s)}
    assert idx(4, 3) not in targets and idx(4, 2) not in targets
    assert idx(2, 3) in targets


def test_capture_and_chain_then_pass():
    extra = [idx(4, 5), idx(4, 6), idx(3, 6), idx(2, 6)]
    s = empty_state([idx(2, 2)], [idx(3, 2), idx(5, 2)] + extra)
    n = rules.apply(s, (idx(2, 2), idx(4, 2)))
    assert n.cells[idx(3, 2)] == EMPTY and n.captured == 1
    # le renard peut enchaîner sur (5,2) : c'est encore son tour, rafle en cours
    assert n.turn == FOX and n.chain == idx(4, 2)
    assert sorted(legal_moves(n)) == sorted([(idx(4, 2), idx(6, 2)), PASS])
    after = rules.apply(n, PASS)
    assert after.turn == GOOSE and after.chain is None


def test_trap_detected():
    # renard en (0,3) : voisins (0,2), (0,4) occupés, saut vers (2,3) bloqué ;
    # l'oie (1,2) glisse en (1,3) et ferme la cage
    s = empty_state([idx(0, 3)], [idx(0, 2), idx(0, 4), idx(1, 2), idx(2, 3), idx(5, 3)], turn=GOOSE)
    n = rules.apply(s, (idx(1, 2), idx(1, 3)))
    assert n.winner == GOOSE and n.reason == "fox_trapped"


def test_too_few_geese():
    s = empty_state([idx(3, 3)], [idx(3, 4), idx(5, 3), idx(6, 3), idx(6, 2)])
    n = rules.apply(s, (idx(3, 3), idx(3, 5)))
    assert n.winner == FOX and n.reason == "too_few_geese"


def test_breakthrough():
    s = empty_state([idx(5, 3)], [idx(2, 0), idx(2, 1), idx(2, 5), idx(2, 6), idx(3, 0)])
    n = rules.apply(s, (idx(5, 3), idx(6, 3)))
    assert n.winner == FOX and n.reason == "fox_breakthrough"


def test_match_undo_and_replay():
    m = Match("1-13")
    rng = random.Random(0)
    for _ in range(20):
        if m.state.winner:
            break
        m.play(rng.choice(legal_moves(m.state)))
    replay = Match("1-13", [list(x) for x in m.moves])
    assert replay.state.cells == m.state.cells
    n = len(m.moves)
    m.undo()
    assert len(m.moves) == n - 1
    with pytest.raises(ValueError):
        m.play((0, 0))


def test_repetition_draw():
    m = Match("1-13")
    m.play((idx(2, 3), idx(1, 3)))
    m.play((idx(4, 0), idx(3, 0)))
    # renard et oie font des allers-retours : la même position revient 3 fois
    cycle = [(idx(1, 3), idx(2, 3)), (idx(3, 0), idx(3, 1)), (idx(2, 3), idx(1, 3)), (idx(3, 1), idx(3, 0))]
    for _ in range(3):
        for mv in cycle:
            if not m.state.winner:
                m.play(mv)
    assert m.state.winner == "draw" and m.state.reason == "repetition"


@pytest.mark.parametrize("level", list(ai.LEVELS))
def test_ai_returns_legal_move(level):
    for setup in rules.SETUP_ORDER:
        s = State.new(setup)
        assert ai.choose_move(s, level) in legal_moves(s)
        s2 = rules.apply(s, legal_moves(s)[0])
        assert ai.choose_move(s2, level) in legal_moves(s2)


def test_ai_takes_winning_capture():
    s = empty_state([idx(3, 3)], [idx(3, 4), idx(5, 3), idx(6, 3), idx(6, 2)])
    assert ai.choose_move(s, "Moyen") == (idx(3, 3), idx(3, 5))
