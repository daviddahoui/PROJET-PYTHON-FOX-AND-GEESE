import pygame

from foxgeese import rules
from foxgeese.chat import MAX_LEN, clean, layout, tokens
from foxgeese.game import GameScene


class FakeSession:
    role, code, peer_name = "host", "ABCDE", "Ami"

    def __init__(self):
        self.sent = []

    def send(self, msg):
        self.sent.append(msg)

    def poll(self):
        return []

    def close(self):
        pass


def key(scene, k, mouse=(0, 0), text=None):
    scene.handle(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""), mouse)
    if text:
        scene.handle(pygame.event.Event(pygame.TEXTINPUT, text=text), mouse)


def test_clean_filters_unsupported_characters():
    assert clean("Salut 😂 !") == "Salut 😂 !"
    assert clean("👍🏽 ok‍") == "👍 ok"               # teinte de peau retirée
    assert clean("中文 🐙 é") == "é"                        # caractères non affichables retirés
    assert clean("  a   b  ") == "a b"
    assert len(clean("x" * 500)) == MAX_LEN
    assert clean(12345) == "12345"                           # donnée réseau farfelue


def test_tokens_and_layout(app):
    assert tokens("gg 🔥🔥") == [("t", "gg "), ("e", "feu"), ("e", "feu")]
    lines = layout("un message assez long pour tenir sur plusieurs lignes 😂", 120, 15)
    assert len(lines) > 1
    assert layout("x" * 300, 100, 15)                       # mot géant coupé sans planter


def test_typing_in_chat_does_not_trigger_game_shortcuts(app):
    session = FakeSession()
    scene = GameScene(app, "online", "1-13", human_side=rules.FOX, session=session)
    app.scene = scene
    key(scene, pygame.K_RETURN)                              # Entrée ouvre la saisie
    assert scene.chat.input.focused
    key(scene, pygame.K_p, text="p")                         # « p » = pause d'habitude
    key(scene, pygame.K_SPACE, text=" ")
    key(scene, pygame.K_ESCAPE)                              # Échap ferme la saisie, pas de menu
    assert not scene.paused and scene.chat.input.value == "p "
    scene.chat.input.focused = True
    scene.chat.input.value = "Salut 😂"
    key(scene, pygame.K_RETURN)
    assert session.sent[-1] == {"t": "chat", "text": "Salut 😂"}
    assert scene.chat.input.value == "" and scene.chat.log[-1]["who"] == "me"


def test_receiving_chat_and_emoji(app):
    scene = GameScene(app, "online", "1-13", human_side=rules.FOX, session=FakeSession())
    app.scene = scene
    assert scene.chat.receive({"t": "chat", "text": "coucou 🔥\u0000"})
    assert scene.chat.receive({"t": "emoji", "e": "rire"})
    assert scene.chat.receive({"t": "emoji", "e": "../../etc/passwd"})   # ignoré proprement
    assert [m["who"] for m in scene.chat.log] == ["peer", "peer"]
    assert scene.chat.log[0]["text"] == "coucou 🔥" and scene.chat.floaters
    app.frame()


def test_emoji_button_click_sends(app):
    session = FakeSession()
    scene = GameScene(app, "online", "1-13", human_side=rules.FOX, session=session)
    app.scene = scene
    c = scene.chat
    x = c.x + 14 + (c.w - 28) / 8 * 4.5                      # 5e émoji : « feu »
    y = c.emoji_y + 21
    scene.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)), (x, y))
    assert session.sent[-1] == {"t": "emoji", "e": "feu"}
    app.frame()
