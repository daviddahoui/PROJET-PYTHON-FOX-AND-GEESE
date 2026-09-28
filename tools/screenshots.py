"""Rend chaque écran du jeu en PNG, sans fenêtre (vérification visuelle / README)."""

import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

from foxgeese import rules
from foxgeese.ui import G, make_background

OUT = sys.argv[1] if len(sys.argv) > 1 else "screenshots"
os.makedirs(OUT, exist_ok=True)

pygame.init()
pygame.display.set_mode((1, 1))


class FakeAudio:
    def play(self, name): pass
    def set_music(self, on): pass


class FakeApp:
    def __init__(self, scale=2):
        self.surface = pygame.Surface((int(1200 * scale), int(800 * scale)))
        G.configure(self.surface)
        self.background = make_background(self.surface.get_size())
        self.settings = {"music": True, "sfx": True, "name": "Joueur", "fullscreen": False}
        self.audio = FakeAudio()
        self.scene = None

    def go(self, scene): self.scene = scene
    def quit(self): pass
    def toast(self, msg): pass
    def save_settings(self): pass

    def shot(self, name, scene, t=1.0, steps=30):
        for _ in range(steps):
            scene.update(t / steps)
        self.surface.blit(self.background, (0, 0))
        scene.draw(self.surface)
        pygame.image.save(self.surface, os.path.join(OUT, name))
        print("->", name)


app = FakeApp(scale=float(sys.argv[2]) if len(sys.argv) > 2 else 2)
from foxgeese.scenes import MenuScene, OnlineScene, RulesScene, SetupScene  # noqa: E402
from foxgeese.game import GameScene  # noqa: E402

app.shot("1_menu.png", MenuScene(app))
app.shot("2_setup_solo.png", SetupScene(app, "solo"))
app.shot("3_online.png", OnlineScene(app))
app.shot("4_rules.png", RulesScene(app))

g = GameScene(app, "local", "1-13")
m = g.match
# Quelques coups pour montrer une capture possible
for mv in [(17, 10), (29, 22), (10, 16)]:
    if mv in rules.legal_moves(m.state):
        g.play(mv)
app.shot("5_game.png", g, t=3)
st = g.match.state
g.selected = next((i for i in rules.POINTS if st.cells[i] == st.turn and rules.moves_from(st, i)), None)
app.shot("6_game_selected.png", g, t=0.1, steps=2)

g2 = GameScene(app, "solo", "2-20", human_side=rules.FOX, level="Facile")
g2.match.history[-1] = g2.match.state.copy()
s = g2.match.history[-1]
s.winner, s.reason, s.captured = rules.FOX, "too_few_geese", 13
g2.shown = s
app.shot("7_victory.png", g2, t=1.2, steps=40)
g2.paused = False
g3 = GameScene(app, "solo", "1-17", human_side=rules.GOOSE)
g3.toggle_pause()
app.shot("8_pause.png", g3, t=0.2, steps=2)


class FakeSession:
    role, code, peer_name = "host", "K7QM4", "Alex"
    def send(self, msg): pass
    def poll(self): return []
    def close(self): pass


g4 = GameScene(app, "online", "1-15", human_side=rules.FOX, session=FakeSession())
for mv in [(17, 10), (29, 22), (10, 16)]:
    if mv in rules.legal_moves(g4.match.state):
        g4.play(mv)
chat = g4.chat
chat.add("peer", "Salut ! Prêt à te faire encercler ? 😎")
chat.add("me", "Mon renard a faim 🔥🔥")
chat.add("peer", emoji="rire")
chat.add("me", "Attention à ton oie à gauche…")
chat.add("peer", "Nooon 😭 bien joué 👏")
chat.float("feu")
g4.chat.input.value = "GG "
g4.chat.input.focused = True
app.shot("8_online_chat.png", g4, t=0.6, steps=12)
