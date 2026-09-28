import random
import socket
import time

import pygame
import pytest

from foxgeese import rules, storage
from foxgeese.game import GameScene, pos
from foxgeese.rules import FOX, GOOSE, PASS
from foxgeese.scenes import LobbyScene, MenuScene, OnlineScene, RulesScene, SetupScene
from foxgeese.ui import G


def click(scene, x, y):
    for t in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        scene.handle(pygame.event.Event(t, button=1, pos=(0, 0)), (x, y))


def human_play(scene, rng):
    """Joue un coup légal pour l'humain en cliquant sur le plateau comme un joueur."""
    s = scene.match.state
    move = rng.choice(rules.legal_moves(s))
    if move == PASS:
        click(scene, *pos(s.chain))
        return
    if s.chain is None:
        click(scene, *pos(move[0]))
        assert scene.selected == move[0]
    click(scene, *pos(move[1]))


def run_until(app, cond, max_frames=4000):
    for _ in range(max_frames):
        if cond():
            return True
        app.frame()
        if app.scene is not None and getattr(app.scene, "ai_thread", None):
            time.sleep(0.002)
    return cond()


def test_all_menus_render_at_several_sizes(app):
    for size in [(1200, 800), (2400, 1600), (900, 900), (1700, 700)]:
        app.surface = pygame.Surface(size)
        G.configure(app.surface)
        for scene in [MenuScene(app), SetupScene(app, "solo"), SetupScene(app, "local"),
                      SetupScene(app, "host"), OnlineScene(app), RulesScene(app),
                      GameScene(app, "local", "2-27")]:
            app.scene = scene
            app.frame()


@pytest.mark.parametrize("human", [FOX, GOOSE])
def test_solo_game_played_by_clicks(app, human):
    rng = random.Random(4)
    scene = GameScene(app, "solo", "1-13", human_side=human, level="Facile")
    app.scene = scene
    for _ in range(400):
        if scene.match.state.winner:
            break
        assert run_until(app, lambda: scene.match.state.winner or (
            scene.is_human_turn() and not scene.anim and not scene.queue and scene.ai_thread is None))
        if scene.match.state.winner:
            break
        human_play(scene, rng)
    assert run_until(app, lambda: bool(scene.overlay_buttons))
    assert scene.match.state.winner in (FOX, GOOSE, "draw")
    assert storage.load_game() is None              # partie finie : plus de sauvegarde


def test_local_undo_save_resume(app):
    rng = random.Random(1)
    scene = GameScene(app, "local", "1-15")
    app.scene = scene
    for _ in range(6):
        run_until(app, lambda: not scene.anim and not scene.queue)
        human_play(scene, rng)
    run_until(app, lambda: not scene.anim and not scene.queue)
    n = len(scene.match.moves)
    scene.undo()
    assert len(scene.match.moves) == n - 1
    scene.save_and_quit()
    assert isinstance(app.scene, MenuScene)
    saved = storage.load_game()
    assert saved and saved["setup"] == "1-15" and len(saved["moves"]) == n - 1
    menu = MenuScene(app)
    menu.resume()
    assert isinstance(app.scene, GameScene)
    assert app.scene.match.state.cells == scene.match.state.cells


def test_corrupted_save_is_handled(app, isolated_storage):
    (isolated_storage / "savegame.json").write_text('{"version": 2, "mode": "local", "setup": "1-13", "moves": [[0, 1]]}')
    MenuScene(app).resume()
    assert isinstance(app.scene, MenuScene) and app.toasts


def test_clicking_opponent_piece_does_nothing(app):
    scene = GameScene(app, "local", "1-13")
    app.scene = scene
    goose = next(i for i in rules.POINTS if scene.match.state.cells[i] == GOOSE)
    click(scene, *pos(goose))
    assert scene.selected is None and not scene.match.moves


def _online_available():
    try:
        socket.create_connection(("broker.emqx.io", 1883), timeout=3).close()
        return True
    except OSError:
        return False


@pytest.mark.skipif(not _online_available(), reason="pas d'accès internet")
def test_online_full_game_two_players(app):
    from tests.conftest import FakeApp
    host_app, guest_app = app, FakeApp()
    host_app.scene = LobbyScene(host_app, "host", setup="1-13", host_side=GOOSE)
    host_lobby = host_app.scene
    assert run_until(host_app, lambda: host_lobby.code is not None, 2000)
    guest_app.scene = LobbyScene(guest_app, "guest", code=host_lobby.code)

    def both_frames():
        host_app.frame()
        guest_app.frame()
        time.sleep(0.01)

    for _ in range(2000):
        if isinstance(host_app.scene, GameScene) and isinstance(guest_app.scene, GameScene):
            break
        both_frames()
    h, g = host_app.scene, guest_app.scene
    assert isinstance(h, GameScene) and isinstance(g, GameScene)
    assert h.human_side == GOOSE and g.human_side == FOX
    rng = random.Random(9)
    for _ in range(40):
        if h.match.state.winner:
            break
        mover = h if h.is_human_turn() else g
        other = g if mover is h else h
        if not mover.is_human_turn() or mover.anim or mover.queue:
            both_frames()
            continue
        before = len(mover.match.moves)
        human_play(mover, rng)
        for _ in range(600):
            both_frames()
            if len(other.match.moves) == before + 1 and not other.queue and not other.anim:
                break
        assert other.match.state.cells == mover.match.state.cells, "plateaux désynchronisés"
    assert len(h.match.moves) >= 10
    # revanche : les deux la demandent, les camps sont échangés
    h.ask_rematch()
    g.ask_rematch()
    for _ in range(600):
        both_frames()
        if host_app.scene is not h and guest_app.scene is not g:
            break
    h, g = host_app.scene, guest_app.scene
    assert h.human_side == FOX and g.human_side == GOOSE and not h.match.moves
    # départ de l'invité : l'hôte doit être prévenu
    g.quit_to_menu()
    for _ in range(600):
        both_frames()
        if h.net_error:
            break
    assert h.net_error
    h.quit_to_menu()
