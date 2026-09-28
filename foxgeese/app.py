"""Fenêtre, boucle principale et navigation entre les écrans."""

from __future__ import annotations

import os
import sys

# Windows : écran haute définition net au lieu d'être étiré et flou
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from . import storage  # noqa: E402
from .audio import Audio  # noqa: E402
from .paths import asset  # noqa: E402
from .ui import CREAM, G, INK, box, make_background, text  # noqa: E402


class App:
    def __init__(self):
        pygame.init()
        sys.setswitchinterval(0.002)             # l'IA (thread) laisse respirer l'affichage
        self.settings = storage.load_settings()
        desk_w, desk_h = pygame.display.get_desktop_sizes()[0]
        h = int(min(desk_h * 0.86, desk_w * 0.86 / 1.5))
        size = (int(h * 1.5), h)
        self.window = pygame.Window("Fox and Geese", size, resizable=True, allow_high_dpi=True)
        self.window.minimum_size = (720, 480)
        try:
            self.window.set_icon(pygame.image.load(asset("images/icon.png")))
        except Exception:
            pass
        self.surface = self.window.get_surface()
        G.configure(self.surface)
        self.background = make_background(self.surface.get_size())
        self.audio = Audio(self.settings)
        self.clock = pygame.time.Clock()
        self.running = True
        self.fade_from: pygame.Surface | None = None
        self.fade_t = 0.0
        self._toast = None
        from .scenes import MenuScene
        self.scene = MenuScene(self)
        if self.settings.get("fullscreen"):
            self.toggle_fullscreen()

    # --- Navigation -------------------------------------------------------------------------

    def go(self, scene):
        self.fade_from = self.surface.copy()
        self.fade_t = 0.0
        self.scene.leave()
        self.scene = scene

    def quit(self):
        self.running = False

    def toast(self, msg: str):
        self._toast = [msg, 3.0]

    def save_settings(self):
        storage.save_settings(self.settings)

    def toggle_fullscreen(self):
        self.settings["fullscreen"] = not getattr(self, "_fullscreen", False)
        self._fullscreen = self.settings["fullscreen"]
        if self._fullscreen:
            self.window.set_fullscreen(desktop=True)
        else:
            self.window.set_windowed()
        self.save_settings()
        self._resized()

    def _resized(self):
        self.surface = self.window.get_surface()
        G.configure(self.surface)
        self.background = make_background(self.surface.get_size())
        self.fade_from = None
        self.scene.on_resize()

    def mouse(self, pos) -> tuple[float, float]:
        # Événements souris en points écran ; la surface est en pixels (Retina = x2)
        ratio = self.surface.get_width() / max(1, self.window.size[0])
        return G.to_logical(pos[0] * ratio, pos[1] * ratio)

    # --- Boucle -----------------------------------------------------------------------------

    def run(self):
        last_mouse = (0.0, 0.0)
        while self.running:
            dt = min(self.clock.tick(60) / 1000, 0.05)
            for e in pygame.event.get():
                if e.type == pygame.QUIT or (e.type == pygame.WINDOWCLOSE):
                    self.running = False
                elif e.type in (pygame.WINDOWRESIZED, pygame.WINDOWSIZECHANGED):
                    self._resized()
                    continue
                elif e.type == pygame.KEYDOWN and (
                        e.key == pygame.K_F11 or
                        (e.key == pygame.K_f and e.mod & pygame.KMOD_META and e.mod & pygame.KMOD_CTRL)):
                    self.toggle_fullscreen()
                    continue
                if hasattr(e, "pos"):
                    last_mouse = self.mouse(e.pos)
                self.scene.handle(e, last_mouse)
            self.scene.update(dt)
            self.draw(dt)
        self.shutdown()

    def draw(self, dt):
        surf = self.surface
        surf.blit(self.background, (0, 0))
        self.scene.draw(surf)
        if self._toast:
            msg, left = self._toast
            self._toast[1] -= dt
            if self._toast[1] <= 0:
                self._toast = None
            box(surf, 350, 740, 500, 44, CREAM, radius=14, shadow=4)
            text(surf, msg, 600, 762, 16, "semi", INK, anchor="center")
        if self.fade_from is not None:
            self.fade_t += dt
            k = self.fade_t / 0.22
            if k >= 1:
                self.fade_from = None
            else:
                self.fade_from.set_alpha(int(255 * (1 - k)))
                surf.blit(self.fade_from, (0, 0))
        self.window.flip()

    def shutdown(self):
        session = getattr(self.scene, "session", None)
        if session:
            session.close()
        if hasattr(self.scene, "autosave") and getattr(self.scene, "mode", None) != "online":
            try:
                if self.scene.match.moves:
                    self.scene.autosave()
            except Exception:
                pass
        pygame.quit()


def main():
    selftest = os.environ.get("FOXGEESE_SELFTEST")
    if selftest:
        from .selftest import run
        sys.exit(run(selftest))
    App().run()


