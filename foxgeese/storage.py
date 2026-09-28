"""Sauvegarde de la partie et des réglages dans le dossier utilisateur.

La version 2023 écrivait game_save.json dans le dossier courant : une fois
compilé en .exe/.app, ce dossier peut être temporaire ou protégé en écriture et la
sauvegarde échouait. On utilise désormais le dossier prévu par chaque système.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_NAME = "FoxAndGeese"


def data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read(name: str) -> dict | None:
    try:
        return json.loads((data_dir() / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write(name: str, data: dict) -> bool:
    try:
        tmp = data_dir() / (name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(data_dir() / name)      # écriture atomique : jamais de fichier à moitié écrit
        return True
    except OSError:
        return False


DEFAULT_SETTINGS = {"music": True, "sfx": True, "name": "", "fullscreen": False}


def load_settings() -> dict:
    return {**DEFAULT_SETTINGS, **(_read("settings.json") or {})}


def save_settings(settings: dict) -> None:
    _write("settings.json", settings)


def load_game() -> dict | None:
    data = _read("savegame.json")
    if not data or data.get("version") != 2:
        return None
    return data


def save_game(data: dict) -> bool:
    return _write("savegame.json", {"version": 2, **data})


def delete_game() -> None:
    try:
        (data_dir() / "savegame.json").unlink()
    except OSError:
        pass
