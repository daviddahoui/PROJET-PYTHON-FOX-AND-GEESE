import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402
import pytest  # noqa: E402

from foxgeese import storage  # noqa: E402
from foxgeese.ui import G, make_background  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))


class FakeAudio:
    def __init__(self):
        self.played = []

    def play(self, name):
        self.played.append(name)

    def set_music(self, on):
        pass


class FakeApp:
    def __init__(self, size=(1200, 800)):
        self.surface = pygame.Surface(size)
        G.configure(self.surface)
        self.background = make_background(size)
        self.settings = dict(storage.DEFAULT_SETTINGS, name="Testeur")
        self.audio = FakeAudio()
        self.scene = None
        self.toasts = []

    def go(self, scene):
        self.scene = scene

    def quit(self):
        pass

    def toast(self, msg):
        self.toasts.append(msg)

    def save_settings(self):
        pass

    def frame(self, dt=1 / 60):
        self.scene.update(dt)
        self.surface.blit(self.background, (0, 0))
        self.scene.draw(self.surface)


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "data_dir", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def app():
    return FakeApp()
