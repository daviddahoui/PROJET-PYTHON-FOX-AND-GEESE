"""Génère l'aperçu animé (GIF) et la capture de victoire du README.

Une vraie partie est jouée par l'IA et rendue image par image, sans fenêtre.
"""

import os
import random
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame  # noqa: E402
from PIL import Image  # noqa: E402

from foxgeese import ai, rules  # noqa: E402
from foxgeese.rules import FOX, GOOSE, PASS  # noqa: E402
from tests.conftest import FakeApp  # noqa: E402

OUT = os.path.join(ROOT, "docs")
FPS = 12
GIF_SIZE = (720, 480)


def pick_seed(setup, n_moves, levels):
    """Cherche une partie où le renard croque au moins une oie assez tôt (plus parlant)."""
    for seed in range(200):
        rng, m = random.Random(seed), rules.Match(setup)
        while len(m.moves) < n_moves and not m.state.winner:
            m.play(ai.choose_move(m.state, levels[m.state.turn], rng))
        if 1 <= m.state.captured and any(rules.is_capture(mv) for mv in m.moves[4:n_moves - 2]):
            return seed, m.moves
    raise RuntimeError("aucune partie intéressante trouvée")


def gif():
    from foxgeese.game import GameScene
    _, moves = pick_seed("1-15", 16, {FOX: "Moyen", GOOSE: "Facile"})
    app = FakeApp(size=(1200, 800))
    scene = GameScene(app, "local", "1-15")
    app.scene = scene
    frames = []

    def film(seconds):
        for _ in range(int(seconds * FPS)):
            app.frame(1 / FPS)
            img = Image.frombytes("RGB", app.surface.get_size(), pygame.image.tobytes(app.surface, "RGB"))
            frames.append(img.resize(GIF_SIZE, Image.LANCZOS))

    film(0.8)
    for mv in moves:
        if mv != PASS and scene.match.state.chain is None:
            scene.selected = mv[0]            # on montre la sélection et les coups possibles
            film(0.55)
        scene.play(mv)
        film(0.75 if rules.is_capture(mv) else 0.45)
    film(1.2)
    palette = frames[len(frames) // 2].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    frames = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    path = os.path.join(OUT, "demo.gif")
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=int(1000 / FPS), loop=0, optimize=True)
    print(f"demo.gif : {len(frames)} images, {os.path.getsize(path) // 1024} Ko")


def victory():
    from foxgeese.game import GameScene
    rng, m = random.Random(2), rules.Match("1-13")
    while not m.state.winner:
        m.play(ai.choose_move(m.state, "Difficile" if m.state.turn == FOX else "Facile", rng))
    app = FakeApp(size=(1200, 800))
    # durée réaliste : ~4 s par coup du joueur, ~1 s pour l'IA
    seconds = sum(4 if i % 2 == 0 else 1 for i in range(len(m.moves)))
    scene = GameScene(app, "solo", "1-13", human_side=FOX, level="Facile", moves=m.moves, seconds=seconds)
    app.scene = scene
    for _ in range(90):
        app.frame(1 / 60)
    path = os.path.join(OUT, "screenshots", "7_victory.png")
    pygame.image.save(app.surface, path)
    print(f"victoire : {m.state.reason}, {len(m.moves)} coups -> {path}")


if __name__ == "__main__":
    gif()
    victory()
