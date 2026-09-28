"""Auto-test de l'application compilée (.exe / .app), lancé par GitHub Actions.

Variable d'environnement FOXGEESE_SELFTEST=<fichier résultat> : le jeu démarre, ouvre
une partie contre l'IA, se connecte au relais en ligne, puis se ferme tout seul et écrit
un rapport JSON. Cela vérifie que l'exécutable contient bien tout ce qu'il faut
(polices, images, musique, certificats réseau) sur un vrai Windows / Mac.
"""

from __future__ import annotations

import json
import time
import traceback

import pygame

from .rules import GOOSE


def run(out_path: str) -> int:
    report = {"ok": False, "steps": []}

    def step(name):
        report["steps"].append(name)

    try:
        from .app import App
        from .game import GameScene
        from .net import NetSession

        app = App()
        step("fenêtre et ressources chargées")
        app.go(GameScene(app, "solo", "1-13", human_side=GOOSE, level="Moyen"))
        session = NetSession("host", "selftest")
        session.start()
        deadline = time.monotonic() + 25
        hosted = False
        clock = pygame.time.Clock()
        while time.monotonic() < deadline and not (hosted and app.scene.match.moves):
            dt = clock.tick(60) / 1000
            pygame.event.pump()
            app.scene.update(dt)
            app.draw(dt)
            for e in session.poll():
                hosted = hosted or e["t"] == "hosting"
        session.close()
        if app.scene.match.moves:
            step("l'IA a joué un coup")
        if hosted:
            step("relais en ligne joignable")
        report["ok"] = bool(app.scene.match.moves) and hosted
        pygame.quit()
    except Exception:
        report["error"] = traceback.format_exc()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    return 0 if report["ok"] else 1
