"""Génère l'icône de l'application (renard sur fond jaune, style du jeu)."""

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "foxgeese", "assets", "images")

pygame.init()
pygame.display.set_mode((1, 1))
S = 1024
big = pygame.Surface((S * 2, S * 2), pygame.SRCALPHA)
m = 200                                      # marge façon icône macOS
pygame.draw.rect(big, (42, 26, 14), (m + 24, m + 60, S * 2 - 2 * m, S * 2 - 2 * m), border_radius=380)
pygame.draw.rect(big, (255, 217, 59), (m, m, S * 2 - 2 * m, S * 2 - 2 * m), border_radius=380)
pygame.draw.rect(big, (42, 26, 14), (m, m, S * 2 - 2 * m, S * 2 - 2 * m), 36, border_radius=380)
fox = pygame.transform.smoothscale(pygame.image.load(os.path.join(IMG, "fox.png")), (1100, 1100))
big.blit(fox, fox.get_rect(center=(S, S - 20)))
icon = pygame.transform.smoothscale(big, (S, S))
pygame.image.save(icon, os.path.join(IMG, "icon.png"))
print("icône écrite")
