"""Écrans hors partie : menu, configuration, jeu en ligne, règles."""

from __future__ import annotations

import math

import pygame

from . import __version__, rules, storage
from .net import ALPHABET, NetSession, code_is_valid, normalize_code
from .ui import (CREAM, FOX_C, G, GOOSE_C, GREEN, INK, INK_SOFT, LINE, RED, WHITE, YELLOW,
                 Button, Segmented, TextInput, box, circle, image, paragraph, stripe, text)

SETUP_LABELS = {k: (int(k.split("-")[0]), int(k.split("-")[1])) for k in rules.SETUP_ORDER}


class Scene:
    def __init__(self, app):
        self.app = app
        self.widgets = []
        self.t = 0.0

    def handle(self, e, mouse):
        for w in self.widgets:
            if w.handle(e, mouse, self.app.audio):
                break

    def update(self, dt):
        self.t += dt
        for w in self.widgets:
            w.update(dt)

    def draw(self, surf):
        for w in self.widgets:
            w.draw(surf)

    def on_resize(self):
        pass

    def leave(self):
        pass


def title_bar(surf, title, subtitle=None):
    text(surf, title, 600, 58, 54, "title", INK, anchor="center", shadow=(255, 250, 225))
    if subtitle:
        text(surf, subtitle, 600, 104, 20, "semi", INK_SOFT, anchor="center")


# --- Menu principal -----------------------------------------------------------------

class MenuScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.save = storage.load_game()
        x, w, h, gap = 430, 340, 66, 16
        y = 292
        self.widgets = [
            Button("Jouer seul contre l'IA", x, y, w, h, lambda: app.go(SetupScene(app, "solo"))),
            Button("Deux joueurs, même écran", x, y + (h + gap), w, h, lambda: app.go(SetupScene(app, "local")),
                   style="secondary", size=22),
            Button("Jouer en ligne entre amis", x, y + 2 * (h + gap), w, h, lambda: app.go(OnlineScene(app)),
                   style="fox", size=22),
        ]
        y2 = y + 3 * (h + gap)
        if self.save:
            self.widgets.append(Button("Continuer la partie", x, y2, w, 56, self.resume, style="secondary", size=20))
            y2 += 56 + gap
        half = (w - gap) / 2
        self.widgets += [
            Button("Règles", x, y2, half, 52, lambda: app.go(RulesScene(app)), style="secondary", size=19),
            Button("Quitter", x + half + gap, y2, half, 52, app.quit, style="secondary", size=19),
        ]
        self.music_btn = Button("", 1010, 24, 166, 44, self.toggle_music, style="secondary", size=15)
        self.sfx_btn = Button("", 1010, 78, 166, 44, self.toggle_sfx, style="secondary", size=15)
        self.widgets += [self.music_btn, self.sfx_btn]
        self._labels()

    def _labels(self):
        s = self.app.settings
        self.music_btn.label = "Musique : " + ("oui" if s["music"] else "non")
        self.sfx_btn.label = "Bruitages : " + ("oui" if s["sfx"] else "non")

    def toggle_music(self):
        self.app.audio.set_music(not self.app.settings["music"])
        self.app.save_settings()
        self._labels()

    def toggle_sfx(self):
        self.app.settings["sfx"] = not self.app.settings["sfx"]
        self.app.save_settings()
        self._labels()

    def resume(self):
        from .game import GameScene
        s = self.save
        try:
            scene = GameScene(self.app, s["mode"], s["setup"], human_side=s.get("human_side"),
                              level=s.get("level", "Moyen"), moves=s["moves"], seconds=s.get("seconds", 0))
        except (KeyError, ValueError):
            storage.delete_game()
            self.app.toast("Sauvegarde illisible, elle a été supprimée.")
            self.app.go(MenuScene(self.app))
            return
        self.app.go(scene)

    def draw(self, surf):
        bob = math.sin(self.t * 1.6)
        # Titre façon affiche de 2023 : grosse étiquette jaune à bord noir
        box(surf, 250, 70, 700, 130, YELLOW, radius=28, border=4, shadow=9)
        text(surf, "FOX AND GEESE", 600, 138, 84, "title", INK, anchor="center")
        text(surf, "Le renard rusé contre la bande d'oies", 600, 238, 21, "semi", INK, anchor="center")
        # Personnages qui flottent
        image(surf, "fox.png", 205, 470 + bob * 10, 270, angle=bob * 3)
        image(surf, "goose.png", 995, 480 - bob * 10, 270, angle=-bob * 3)
        super().draw(surf)
        text(surf, f"Version {__version__} · créé en 2023, remasterisé en 2026",
             600, 770, 15, "regular", INK_SOFT, anchor="center")


# --- Configuration d'une partie --------------------------------------------------------

def draw_mini_board(surf, setup, cx, cy, step):
    cells = rules.SETUPS[setup]
    for a, b in rules.LINES:
        (r0, c0), (r1, c1) = rules.rc(a), rules.rc(b)
        pygame.draw.line(surf, LINE, G.pt(cx + (c0 - 3) * step, cy + (r0 - 3) * step),
                         G.pt(cx + (c1 - 3) * step, cy + (r1 - 3) * step), max(1, G.p(1.2)))
    for i in rules.POINTS:
        r, c = rules.rc(i)
        x, y = cx + (c - 3) * step, cy + (r - 3) * step
        if cells[i] == rules.FOX:
            circle(surf, INK, x, y, step * 0.42)
            circle(surf, FOX_C, x, y, step * 0.30)
        elif cells[i] == rules.GOOSE:
            circle(surf, INK, x, y, step * 0.42)
            circle(surf, WHITE, x, y, step * 0.30)
        else:
            circle(surf, LINE, x, y, step * 0.12)


class SetupCard:
    def __init__(self, scene, key, x, y, w, h):
        self.scene, self.key, self.x, self.y, self.w, self.h = scene, key, x, y, w, h
        self.hover = False

    def handle(self, e, mouse, audio=None):
        lx, ly = mouse
        inside = self.x <= lx <= self.x + self.w and self.y <= ly <= self.y + self.h
        if e.type == pygame.MOUSEMOTION:
            self.hover = inside
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and inside:
            if audio:
                audio.play("select")
            self.scene.setup = self.key
            return True
        return False

    def update(self, dt):
        pass

    def draw(self, surf):
        selected = self.scene.setup == self.key
        lift = 4 if selected else (2 if self.hover else 0)
        box(surf, self.x, self.y - lift, self.w, self.h, YELLOW if selected else CREAM, radius=18,
            border=4 if selected else 3, shadow=6 + lift)
        draw_mini_board(surf, self.key, self.x + self.w / 2, self.y - lift + 82, 17)
        foxes, geese = SETUP_LABELS[self.key]
        y = self.y - lift + self.h - 34
        image(surf, "fox.png", self.x + 30, y, 30)
        text(surf, f"×{foxes}", self.x + 48, y + 1, 19, "bold", INK, anchor="midleft")
        image(surf, "goose.png", self.x + 108, y, 30)
        text(surf, f"×{geese}", self.x + 126, y + 1, 19, "bold", INK, anchor="midleft")


class SetupScene(Scene):
    TITLES = {"solo": "Jouer seul contre l'IA", "local": "Deux joueurs, même écran",
              "host": "Créer une partie en ligne"}

    def __init__(self, app, mode):
        super().__init__(app)
        self.mode = mode
        self.setup = app.settings.get("last_setup", "1-13")
        cw, gap = 184, 18
        x0 = 600 - (5 * cw + 4 * gap) / 2
        self.widgets = [SetupCard(self, k, x0 + i * (cw + gap), 170, cw, 196) for i, k in enumerate(rules.SETUP_ORDER)]
        self.side = Segmented([(rules.FOX, "Le renard"), (rules.GOOSE, "Les oies")], 250, 452, 330, 58,
                              app.settings.get("last_side", rules.FOX), size=19,
                              colors={rules.FOX: FOX_C, rules.GOOSE: GOOSE_C})
        self.level = Segmented([(k, k) for k in ("Facile", "Moyen", "Difficile")], 620, 452, 330, 58,
                               app.settings.get("last_level", "Moyen"), size=19)
        if mode in ("solo", "host"):
            self.widgets.append(self.side)
        if mode == "solo":
            self.widgets.append(self.level)
        if mode == "host":
            self.side.x = 435
        back = (lambda: app.go(OnlineScene(app))) if mode == "host" else (lambda: app.go(MenuScene(app)))
        label = "Créer la partie" if mode == "host" else "Lancer la partie"
        self.widgets += [
            Button("Retour", 330, 690, 200, 64, back, style="secondary"),
            Button(label, 560, 690, 310, 64, self.start),
        ]

    def start(self):
        s = self.app.settings
        s["last_setup"], s["last_side"], s["last_level"] = self.setup, self.side.value, self.level.value
        self.app.save_settings()
        if self.mode == "host":
            self.app.go(LobbyScene(self.app, "host", setup=self.setup, host_side=self.side.value))
            return
        from .game import GameScene
        self.app.go(GameScene(self.app, self.mode, self.setup, human_side=self.side.value, level=self.level.value))

    def draw(self, surf):
        title_bar(surf, self.TITLES[self.mode], "Choisis la configuration du plateau")
        foxes, geese = SETUP_LABELS[self.setup]
        need = rules.GEESE_PER_FOX * foxes
        if self.mode in ("solo", "host"):
            label_x = self.side.x + self.side.w / 2
            text(surf, "Ton camp", label_x, 430, 19, "bold", INK, anchor="center")
        if self.mode == "solo":
            text(surf, "Difficulté de l'IA", self.level.x + self.level.w / 2, 430, 19, "bold", INK, anchor="center")
        box(surf, 250, 560, 700, 96, CREAM, radius=16, shadow=4, border=2)
        paragraph(surf, f"Le renard commence. Il gagne s'il ne reste que {need - 1} oies ou moins, "
                        f"s'il atteint la dernière rangée ou si les oies sont bloquées. "
                        f"Les oies gagnent en immobilisant {'le renard' if foxes == 1 else 'les deux renards'}.",
                  272, 574, 656, size=16)
        super().draw(surf)


# --- En ligne ------------------------------------------------------------------------

class OnlineScene(Scene):
    def __init__(self, app, error=None):
        super().__init__(app)
        self.error = error
        self.name = TextInput(450, 150, 300, 58, app.settings.get("name", ""), "Ton pseudo", max_len=14, size=22)
        self.code = TextInput(660, 432, 360, 70, "", "CODE", max_len=5, upper=True, size=34,
                              on_enter=self.join, allowed=ALPHABET + "OIL0")
        self.widgets = [
            self.name, self.code,
            Button("Créer une partie", 180, 530, 360, 66, self.host, style="fox"),
            Button("Rejoindre", 660, 530, 360, 66, self.join, style="goose"),
            Button("Retour", 500, 700, 200, 60, lambda: app.go(MenuScene(app)), style="secondary"),
        ]

    def _remember_name(self) -> str:
        name = self.name.value.strip() or "Joueur"
        self.app.settings["name"] = name
        self.app.save_settings()
        return name

    def host(self):
        self._remember_name()
        self.app.go(SetupScene(self.app, "host"))

    def join(self):
        code = normalize_code(self.code.value)
        if not code_is_valid(code):
            self.error = "Le code doit faire 5 caractères (lettres et chiffres)."
            self.app.audio.play("error")
            return
        self._remember_name()
        self.app.go(LobbyScene(self.app, "guest", code=code))

    def draw(self, surf):
        title_bar(surf, "Jouer en ligne entre amis", "Chacun sur son ordinateur, où qu'il soit : il suffit d'un code")
        text(surf, "Ton pseudo", 600, 137, 17, "bold", INK_SOFT, anchor="center")
        for x, col, title, body in [
            (160, FOX_C, "Créer une partie", "Choisis le plateau et ton camp. Le jeu te donne un code "
                                             "à envoyer à ton ami (SMS, Discord…)."),
            (640, GOOSE_C, "Rejoindre une partie", "Ton ami t'a envoyé un code ? Tape-le ci-dessous."),
        ]:
            box(surf, x, 250, 400, 370, CREAM, radius=22)
            stripe(surf, x, 250, 400, col)
            text(surf, title, x + 200, 300, 28, "title", INK, anchor="center")
            paragraph(surf, body, x + 30, 336, 340, size=17)
        image(surf, "fox.png", 360, 468, 88, angle=math.sin(self.t * 2) * 6)
        if self.error:
            text(surf, self.error, 600, 650, 18, "semi", RED, anchor="center")
        super().draw(surf)


class LobbyScene(Scene):
    """Salle d'attente : connexion au relais, affichage du code, appairage."""

    def __init__(self, app, role, code=None, setup=None, host_side=None, session=None, peer_name=None):
        super().__init__(app)
        self.role, self.setup, self.host_side = role, setup, host_side
        self.status = "Connexion…"
        self.error = None
        self.code = code
        self.session = session or NetSession(role, app.settings.get("name") or "Joueur", code)
        if not session:
            self.session.start()
        self.copied = 0.0
        self.copy_btn = Button("Copier le code", 470, 470, 260, 56, self.copy, style="secondary", size=19)
        self.widgets = [Button("Annuler", 500, 690, 200, 60, self.cancel, style="secondary")]

    def copy(self):
        try:
            pygame.scrap.put_text(self.code)
            self.copied = 2.0
        except Exception:
            pass

    def cancel(self):
        self.session.close()
        self.app.go(OnlineScene(self.app))

    def leave(self):
        pass

    def update(self, dt):
        super().update(dt)
        self.copied = max(0.0, self.copied - dt)
        for e in self.session.poll():
            t = e["t"]
            if t == "status":
                self.status = e["text"]
            elif t == "error":
                self.error = e["text"]
                self.app.audio.play("error")
            elif t == "hosting":
                self.code = e["code"]
                self.status = "En attente de ton ami…"
                self.widgets.append(self.copy_btn)
            elif t == "joined":
                self.app.audio.play("join")
                if self.role == "host":
                    self.status = f"{e['name']} a rejoint la partie !"
                    self.session.send({"t": "start", "setup": self.setup, "host_side": self.host_side})
                    self._launch(self.setup, self.host_side)
                else:
                    self.status = f"Connecté à {e['name']}, lancement…"
            elif t == "start" and self.role == "guest":
                other = rules.GOOSE if e["host_side"] == rules.FOX else rules.FOX
                self._launch(e["setup"], other)
            elif t in ("bye", "lost"):
                self.error = "Ton ami s'est déconnecté."

    def _launch(self, setup, my_side):
        from .game import GameScene
        self.app.go(GameScene(self.app, "online", setup, human_side=my_side, session=self.session))

    def draw(self, surf):
        title_bar(surf, "Partie en ligne", "Créer une partie" if self.role == "host" else "Rejoindre une partie")
        box(surf, 300, 170, 600, 470, CREAM, radius=24)
        if self.error:
            text(surf, "Oups !", 600, 250, 44, "title", RED, anchor="center")
            paragraph(surf, self.error, 600, 310, 500, size=20, align="center")
        elif self.role == "host" and self.code:
            text(surf, "Code de la partie", 600, 222, 22, "bold", INK_SOFT, anchor="center")
            for i, ch in enumerate(self.code):
                x = 600 - 2.5 * 84 + i * 84 + 6
                box(surf, x, 262, 72, 92, YELLOW, radius=14, shadow=5)
                text(surf, ch, x + 36, 309, 52, "title", INK, anchor="center")
            if self.copied:
                text(surf, "Copié !", 600, 548, 18, "bold", GREEN, anchor="center")
            dots = "." * (1 + int(self.t * 2) % 3)
            text(surf, self.status.rstrip("…") + dots, 600, 400, 21, "semi", INK, anchor="center")
            text(surf, "Envoie ce code à ton ami : il le tape dans « Rejoindre ».", 600, 590, 17,
                 "regular", INK_SOFT, anchor="center")
        else:
            if self.role == "guest":
                text(surf, self.code or "", 600, 250, 60, "title", INK, anchor="center")
            spin = self.t * 5
            for k in range(8):
                a = spin + k * math.tau / 8
                circle(surf, INK, 600 + math.cos(a) * 34, 380 + math.sin(a) * 34, 3 + k * 0.7)
            text(surf, self.status, 600, 470, 21, "semi", INK, anchor="center")
        super().draw(surf)


# --- Règles ----------------------------------------------------------------------------

RULES_TEXT = [
    ("Le but", "Le renard veut croquer des oies. Les oies veulent l'encercler pour qu'il ne puisse plus bouger."),
    ("Déplacements", "Chaque pièce avance d'une intersection en suivant les lignes du plateau. "
                     "Les diagonales n'existent que là où elles sont dessinées. Le renard va dans toutes "
                     "les directions ; les oies ne reculent jamais (vers l'avant ou sur le côté)."),
    ("Captures", "Le renard saute par-dessus une oie voisine si la case derrière est libre : l'oie est "
                 "croquée. S'il peut enchaîner, il continue sa rafle (ou clique sur lui-même pour s'arrêter). "
                 "Les oies ne capturent jamais."),
    ("Victoire du renard", "Il reste trop peu d'oies pour le piéger (moins de 4 par renard), il atteint la "
                           "dernière rangée, ou les oies ne peuvent plus bouger."),
    ("Victoire des oies", "Au tour du renard, aucun renard ne peut bouger."),
    ("Match nul", "La même position revient trois fois."),
]


class RulesScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.widgets = [Button("Retour", 500, 712, 200, 60, lambda: app.go(MenuScene(app)), style="secondary")]

    def draw(self, surf):
        title_bar(surf, "Règles du jeu", "Fox and Geese, un jeu de plateau joué en Europe depuis le Moyen Âge")
        box(surf, 90, 135, 1020, 555, CREAM, radius=24)
        y = 160
        for title, body in RULES_TEXT:
            text(surf, title, 125, y, 22, "title", FOX_C if "renard" in title.lower() else INK)
            y = paragraph(surf, body, 125, y + 30, 950, size=17) + 12
        text(surf, "Astuce : Échap met la partie en pause · F11 bascule le plein écran", 600, 668, 15,
             "regular", INK_SOFT, anchor="center")
        super().draw(surf)

