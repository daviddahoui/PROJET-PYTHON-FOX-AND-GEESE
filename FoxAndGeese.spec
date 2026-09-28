# Recette PyInstaller — une seule recette pour Mac (.app) et Windows (.exe)
#   Mac     : pyinstaller FoxAndGeese.spec   -> dist/Fox and Geese.app
#   Windows : pyinstaller FoxAndGeese.spec   -> dist/FoxAndGeese/FoxAndGeese.exe (dossier, livré en .zip)
import os
import sys

sys.path.insert(0, os.path.abspath(SPECPATH))

from foxgeese import __version__

a = Analysis(
    ["main.py"],
    datas=[("foxgeese/assets", "foxgeese/assets")],
    excludes=["tkinter", "numpy", "PIL", "pytest"],
)
pyz = PYZ(a.pure)
ICON = "foxgeese/assets/images/icon.png"

if sys.platform == "darwin":
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="FoxAndGeese", console=False, icon=ICON)
    coll = COLLECT(exe, a.binaries, a.datas, name="FoxAndGeese")
    app = BUNDLE(
        coll,
        name="Fox and Geese.app",
        icon=ICON,
        bundle_identifier="io.github.foxandgeese",
        info_plist={
            "CFBundleDisplayName": "Fox and Geese",
            "CFBundleShortVersionString": __version__,
            "NSHighResolutionCapable": True,
            "LSApplicationCategoryType": "public.app-category.board-games",
        },
    )
else:
    # Windows : dossier (onedir) plutôt qu'un .exe unique qui se décompresse au lancement,
    # comportement que les antivirus confondent souvent avec celui d'un logiciel malveillant.
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="FoxAndGeese", console=False, icon=ICON, upx=False)
    coll = COLLECT(exe, a.binaries, a.datas, name="FoxAndGeese", upx=False)
