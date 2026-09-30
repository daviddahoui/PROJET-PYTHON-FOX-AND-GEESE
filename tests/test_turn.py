import random

import pygame

from foxgeese import rules
from foxgeese.game import GameScene, pos
from foxgeese.rules import FOX, GOOSE


def click(scene, x, y):
    for t in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        scene.handle(pygame.event.Event(t, button=1, pos=(0, 0)), (x, y))


def frames(app, n=10, dt=1 / 30):
    for _ in range(n):
        app.frame(dt)


def play_one(scene):
    s = scene.match.state
    move = random.Random(1).choice([m for m in rules.legal_moves(s) if m != rules.PASS])
    click(scene, *pos(move[0]))
    click(scene, *pos(move[1]))


class FakeWindow:
    def __init__(self):
        self.focused = False
        self.title = "Fox and Geese"
        self.flashes = 0

    def flash(self, _op):
        self.flashes += 1


def test_banner_when_it_is_my_turn_against_ai(app):
    scene = GameScene(app, "solo", "1-13", human_side=FOX, level="Facile")
    app.scene = scene
    frames(app, 2)
    assert scene.banner and scene.banner[0] == "À toi de jouer !"
    assert "Renard" in scene.banner[1]
    assert "turn" in app.audio.played
    # je joue, l'IA répond, et la bannière revient
    for _ in range(120):
        frames(app, 1)
        if not scene.anim and not scene.queue:
            break
    play_one(scene)
    app.audio.played.clear()
    for _ in range(600):
        frames(app, 1)
        if scene.match.state.turn == FOX and not scene.anim and not scene.queue and scene.ai_thread is None:
            break
    frames(app, 2)
    assert scene.banner and scene.banner[0] == "À toi de jouer !"
    assert "turn" in app.audio.played


def test_no_banner_during_ai_turn(app):
    scene = GameScene(app, "solo", "1-13", human_side=GOOSE, level="Facile")
    app.scene = scene
    frames(app, 2)
    assert scene.banner is None                      # le renard (IA) commence : rien à annoncer


def test_reminder_after_25_seconds(app):
    scene = GameScene(app, "solo", "1-13", human_side=FOX, level="Facile")
    app.scene = scene
    frames(app, 2)
    app.audio.played.clear()
    frames(app, 27 * 10, dt=0.1)
    assert scene.reminded
    assert "turn" in app.audio.played


def test_local_mode_announces_the_right_side(app):
    scene = GameScene(app, "local", "1-13")
    app.scene = scene
    frames(app, 2)
    assert scene.banner[0] == "Au tour du renard"
    play_one(scene)
    frames(app, 30)
    assert scene.banner[0] == "Au tour des oies"


def test_window_flashes_when_in_background(app):
    app.window = FakeWindow()
    scene = GameScene(app, "solo", "1-13", human_side=FOX, level="Facile")
    app.scene = scene
    frames(app, 2)
    assert app.window.flashes == 1
    assert "À toi de jouer" in app.window.title
    app.window.focused = True
    for _ in range(120):
        frames(app, 1)
        if not scene.anim and not scene.queue:
            break
    play_one(scene)
    frames(app, 3)
    assert app.window.title == "Fox and Geese"      # plus mon tour : titre normal
