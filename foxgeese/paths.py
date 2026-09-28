"""Chemin des ressources, que le jeu soit lancé depuis le code ou compilé (PyInstaller)."""

import sys
from pathlib import Path


def asset(relative: str) -> str:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return str(base / "foxgeese" / "assets" / relative)
