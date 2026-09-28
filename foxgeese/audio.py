"""Musique de fond (celle du projet original) et bruitages synthétisés.

Les bruitages sont générés par calcul au démarrage : aucun fichier son à
fournir, donc aucun souci de droits d'auteur.
"""

from __future__ import annotations

import math
import random
from array import array

import pygame

from .paths import asset

RATE = 44100


def _tone(parts, volume=0.5) -> bytes:
    """parts : liste de (durée s, fréquence début, fréquence fin, forme, bruit)."""
    out = array("h")
    rng = random.Random(7)
    for dur, f0, f1, shape, noise in parts:
        n = int(RATE * dur)
        phase = 0.0
        for k in range(n):
            t = k / n
            f = f0 + (f1 - f0) * t
            phase += 2 * math.pi * f / RATE
            if shape == "sine":
                v = math.sin(phase)
            elif shape == "tri":
                v = 2 / math.pi * math.asin(math.sin(phase))
            else:
                v = 1.0 if math.sin(phase) > 0 else -1.0
                v *= 0.4
            v = v * (1 - noise) + (rng.random() * 2 - 1) * noise
            env = min(1.0, k / (RATE * 0.004)) * (1 - t) ** 2      # attaque douce, fin amortie
            s = int(max(-1, min(1, v * env * volume)) * 32767)
            out.append(s)
            out.append(s)                                        # stéréo
    return out.tobytes()


class Audio:
    def __init__(self, settings: dict):
        self.settings = settings
        self.ok = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            pygame.mixer.init(RATE, -16, 2, 512)
            self.ok = True
        except pygame.error:
            return                                               # pas de carte son : on joue en silence
        spec = {
            "select": [(0.05, 880, 990, "sine", 0.0)],
            "move": [(0.09, 420, 300, "tri", 0.05)],
            "capture": [(0.06, 300, 120, "square", 0.35), (0.14, 700, 1200, "sine", 0.0)],
            "error": [(0.12, 200, 160, "square", 0.1)],
            "win": [(0.12, 523, 523, "tri", 0), (0.12, 659, 659, "tri", 0),
                    (0.12, 784, 784, "tri", 0), (0.35, 1046, 1046, "tri", 0)],
            "lose": [(0.18, 392, 392, "tri", 0), (0.18, 330, 330, "tri", 0), (0.4, 262, 250, "tri", 0)],
            "join": [(0.08, 660, 660, "sine", 0), (0.16, 990, 990, "sine", 0)],
        }
        for name, parts in spec.items():
            self.sounds[name] = pygame.mixer.Sound(buffer=_tone(parts, 0.45))
        try:
            pygame.mixer.music.load(asset("sounds/background.mp3"))
            pygame.mixer.music.set_volume(0.35)
            if settings["music"]:
                pygame.mixer.music.play(-1, fade_ms=1500)
        except pygame.error:
            pass

    def play(self, name: str) -> None:
        if self.ok and self.settings["sfx"] and name in self.sounds:
            self.sounds[name].play()

    def set_music(self, on: bool) -> None:
        self.settings["music"] = on
        if not self.ok:
            return
        if on:
            pygame.mixer.music.play(-1, fade_ms=800)
        else:
            pygame.mixer.music.fadeout(400)
