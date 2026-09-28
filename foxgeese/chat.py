"""Chat de la partie en ligne : messages texte et émojis.

Les émojis sont affichés en images (la police du jeu ne sait pas les dessiner). Un
émoji tapé au clavier (😂, 👍…) est reconnu et affiché en image ; les caractères
que la police ne sait pas afficher sont retirés.
"""

from __future__ import annotations

import math
import random
import time

import pygame

from .ui import CREAM, G, INK, INK_SOFT, PAPER, WHITE, YELLOW, box, image, text

EMOJIS = [("rire", "😂"), ("pouce", "👍"), ("wow", "😮"), ("colere", "😡"),
          ("feu", "🔥"), ("bravo", "👏"), ("pleure", "😭"), ("cool", "😎")]
EMOJI_NAMES = {name for name, _ in EMOJIS}
CHAR_TO_EMOJI = {ch: name for name, ch in EMOJIS}
MAX_LEN = 100
MAX_LOG = 120
COOLDOWN = 0.4            # délai minimum entre deux envois (anti-spam)

# Modificateurs invisibles ajoutés par les claviers d'émojis (couleur de peau, variantes)
_IGNORED = {0xFE0F, 0xFE0E, 0x200D} | set(range(0x1F3FB, 0x1F400))


def _allowed(ch: str) -> bool:
    o = ord(ch)
    return (ch in CHAR_TO_EMOJI or (0x20 <= o < 0x7F) or (0xA0 <= o < 0x250)
            or 0x2010 <= o <= 0x2027 or o == 0x20AC)


def clean(raw: str) -> str:
    """Nettoie un message (le sien comme celui reçu du réseau)."""
    out = []
    for ch in str(raw)[:MAX_LEN * 4]:
        if ord(ch) in _IGNORED or not _allowed(ch):
            continue
        out.append(ch)
    return " ".join("".join(out).split())[:MAX_LEN]


def tokens(msg: str) -> list[tuple[str, str]]:
    """Découpe un message en mots ("t", "mot ") et émojis ("e", "rire")."""
    out, word = [], ""
    for ch in msg:
        if ch in CHAR_TO_EMOJI:
            if word:
                out.append(("t", word))
                word = ""
            out.append(("e", CHAR_TO_EMOJI[ch]))
        elif ch == " ":
            out.append(("t", word + " "))
            word = ""
        else:
            word += ch
    if word:
        out.append(("t", word))
    return [t for t in out if t[1]]


def layout(msg: str, width: float, size: float) -> list[list[tuple[str, str, float]]]:
    """Répartit les mots et émojis sur des lignes de largeur max `width` (logique)."""
    font = G.font("regular", size)
    emoji_w = size * 1.35
    lines, line, x = [], [], 0.0
    for kind, val in tokens(msg):
        pieces = [val]
        if kind == "t":
            w = font.size(val)[0] / G.z
            if w > width:                        # mot trop long : on le coupe
                pieces, cur = [], ""
                for ch in val:
                    if font.size(cur + ch)[0] / G.z > width:
                        pieces.append(cur)
                        cur = ""
                    cur += ch
                pieces.append(cur)
        for p in pieces:
            w = emoji_w if kind == "e" else font.size(p)[0] / G.z
            if line and x + w > width and not (kind == "t" and p.strip() == ""):
                lines.append(line)
                line, x = [], 0.0
                if kind == "t":
                    p = p.lstrip()
                    w = font.size(p)[0] / G.z
            line.append((kind, p, w))
            x += w
    if line:
        lines.append(line)
    return lines


def draw_rich(surf, lines, x, y, size, color=INK, line_h=None):
    line_h = line_h or size * 1.45
    for i, line in enumerate(lines):
        cx = x
        cy = y + i * line_h
        for kind, val, w in line:
            if kind == "e":
                image(surf, f"emoji/{val}.png", cx + w / 2, cy + line_h / 2, size * 1.25)
            else:
                text(surf, val, cx, cy + line_h / 2 + 1, size, "regular", color, anchor="midleft")
            cx += w
    return len(lines) * line_h


class ChatInput:
    """Champ de saisie du chat (texte + émojis en images, défilement horizontal)."""

    def __init__(self, x, y, w, h, on_enter):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.value = ""
        self.focused = False
        self.on_enter = on_enter
        self.blink = 0.0

    def contains(self, lx, ly):
        return self.x <= lx <= self.x + self.w and self.y <= ly <= self.y + self.h

    def insert(self, s: str):
        s = "".join(ch for ch in s if ord(ch) not in _IGNORED and _allowed(ch))
        self.value = (self.value + s)[:MAX_LEN]

    def handle(self, e, mouse) -> bool:
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.focused = self.contains(*mouse)
            return self.focused
        if not self.focused:
            return False
        if e.type == pygame.TEXTINPUT:
            self.insert(e.text)
            return True
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.on_enter()
            elif e.key == pygame.K_ESCAPE:
                self.focused = False
            elif e.key == pygame.K_v and (e.mod & (pygame.KMOD_CTRL | pygame.KMOD_META)):
                try:
                    self.insert(pygame.scrap.get_text() or "")
                except Exception:
                    pass
            return True
        return False

    def update(self, dt):
        self.blink = (self.blink + dt) % 1.0

    def draw(self, surf):
        box(surf, self.x, self.y, self.w, self.h, WHITE, radius=12, shadow=3, border=3 if self.focused else 2)
        size = 15
        if not self.value:
            hint = "Écris un message…" if self.focused else "Entrée pour écrire…"
            text(surf, hint, self.x + 14, self.y + self.h / 2 + 1, size, "regular", (170, 155, 135), anchor="midleft")
            end_x = self.x + 14
        else:
            # On n'affiche que la fin du texte si elle déborde
            inner = self.w - 28
            shown = self.value
            while shown and sum(w for line in layout(shown, 10_000, size) for _, _, w in line) > inner:
                shown = shown[1:]
            lines = layout(shown, 10_000, size)
            draw_rich(surf, lines, self.x + 14, self.y + (self.h - size * 1.45) / 2, size)
            end_x = self.x + 14 + sum(w for line in lines for _, _, w in line)
        if self.focused and self.blink < 0.55:
            pygame.draw.rect(surf, (240, 104, 28), G.r(end_x + 1, self.y + 12, 2.5, self.h - 24))


class ChatPanel:
    def __init__(self, scene, x, y, w, h, log=None):
        self.scene = scene
        self.x, self.y, self.w, self.h = x, y, w, h
        self.log: list[dict] = log if log is not None else []
        self.input = ChatInput(x + 14, y + h - 58, w - 28, 44, self.send_text)
        self.emoji_y = y + h - 108
        self.hover_emoji: int | None = None
        self.floaters: list[list] = []
        self.scroll = 0.0
        self.last_sent = 0.0

    # --- Envoi / réception ------------------------------------------------------------

    def _can_send(self) -> bool:
        now = time.monotonic()
        if now - self.last_sent < COOLDOWN:
            return False
        self.last_sent = now
        return True

    def add(self, who: str, msg: str = "", emoji: str | None = None):
        self.log.append({"who": who, "text": msg, "emoji": emoji})
        del self.log[:-MAX_LOG]
        self.scroll = 0.0

    def system(self, msg: str):
        self.add("sys", msg)

    def send_text(self):
        msg = clean(self.input.value)
        if not msg or not self._can_send():
            return
        self.input.value = ""
        self.scene.session.send({"t": "chat", "text": msg})
        self.add("me", msg)
        self.scene.app.audio.play("chat")

    def send_emoji(self, name: str):
        if not self._can_send():
            return
        self.scene.session.send({"t": "emoji", "e": name})
        self.add("me", emoji=name)
        self.float(name)
        self.scene.app.audio.play("chat")

    def receive(self, msg: dict) -> bool:
        t = msg.get("t")
        if t == "chat":
            txt = clean(msg.get("text", ""))
            if txt:
                self.add("peer", txt)
                self.scene.app.audio.play("chat")
            return True
        if t == "emoji":
            name = msg.get("e")
            if name in EMOJI_NAMES:
                self.add("peer", emoji=name)
                self.float(name)
                self.scene.app.audio.play("chat")
            return True
        return False

    def float(self, name: str):
        """Grand émoji qui monte au-dessus du plateau."""
        if len(self.floaters) < 12:
            self.floaters.append([name, random.uniform(160, 640), 0.0, random.uniform(0, math.tau)])

    # --- Événements -----------------------------------------------------------------

    def _emoji_at(self, lx, ly):
        if not (self.emoji_y <= ly <= self.emoji_y + 42):
            return None
        cell = (self.w - 28) / len(EMOJIS)
        i = int((lx - self.x - 14) // cell)
        return i if 0 <= i < len(EMOJIS) else None

    def handle(self, e, mouse) -> bool:
        if self.input.handle(e, mouse):
            return True
        lx, ly = mouse
        inside = self.x <= lx <= self.x + self.w and self.y <= ly <= self.y + self.h
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.input.focused = True               # Entrée : on ouvre la saisie
            return True
        if e.type == pygame.MOUSEMOTION:
            self.hover_emoji = self._emoji_at(lx, ly) if inside else None
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and inside:
            i = self._emoji_at(lx, ly)
            if i is not None:
                self.send_emoji(EMOJIS[i][0])
            return True
        elif e.type == pygame.MOUSEWHEEL and inside:
            self.scroll = max(0.0, self.scroll + e.y * 30)
            return True
        return False

    def update(self, dt):
        self.input.update(dt)
        for f in self.floaters:
            f[2] += dt
        self.floaters = [f for f in self.floaters if f[2] < 2.2]

    # --- Affichage ------------------------------------------------------------------

    def draw(self, surf):
        box(surf, self.x, self.y, self.w, self.h, CREAM, radius=22)
        peer = self.scene.peer_name or "ton ami"
        text(surf, f"Chat avec {peer}", self.x + 20, self.y + 16, 17, "bold", INK)
        self._draw_log(surf)
        cell = (self.w - 28) / len(EMOJIS)
        for i, (name, _) in enumerate(EMOJIS):
            cx = self.x + 14 + cell * (i + 0.5)
            hover = self.hover_emoji == i
            if hover:
                pygame.draw.circle(surf, PAPER, G.pt(cx, self.emoji_y + 21), G.p(20))
            image(surf, f"emoji/{name}.png", cx, self.emoji_y + 21 - (3 if hover else 0), 34 if hover else 30)
        self.input.draw(surf)

    def _draw_log(self, surf):
        top, bottom = self.y + 46, self.emoji_y - 8
        clip = G.r(self.x + 6, top, self.w - 12, bottom - top)
        old = surf.get_clip()
        surf.set_clip(clip)
        size, inner = 15, self.w - 110
        y = bottom + self.scroll
        for item in reversed(self.log):
            who = item["who"]
            if who == "sys":
                h = 26
                y -= h
                text(surf, item["text"], self.x + self.w / 2, y + h / 2, 13, "semi", INK_SOFT, anchor="center")
                continue
            mine = who == "me"
            if item["emoji"]:
                h = 50
                y -= h + 4
                ex = self.x + self.w - 46 if mine else self.x + 46
                image(surf, f"emoji/{item['emoji']}.png", ex, y + h / 2, 44)
            else:
                lines = layout(item["text"], inner, size)
                bw = max(sum(w for _, _, w in line) for line in lines) + 26
                h = len(lines) * size * 1.45 + 14
                y -= h + 6
                bx = self.x + self.w - 16 - bw if mine else self.x + 16
                fill = YELLOW if mine else (226, 240, 252)
                pygame.draw.rect(surf, fill, G.r(bx, y, bw, h), border_radius=G.p(12))
                pygame.draw.rect(surf, INK, G.r(bx, y, bw, h), max(1, G.p(2)), border_radius=G.p(12))
                draw_rich(surf, lines, bx + 13, y + 7, size)
            if y < top - 200:
                break
        if not self.log:
            mid = (top + bottom) / 2
            text(surf, "Dis bonjour, ou envoie un émoji !", self.x + self.w / 2, mid - 10, 14,
                 "semi", INK_SOFT, anchor="center")
            text(surf, "Messages non chiffrés : ne partage rien de personnel.", self.x + self.w / 2, mid + 14,
                 12, "regular", INK_SOFT, anchor="center")
        # Pas de défilement au-delà du plus ancien message
        if y > top:
            self.scroll = max(0.0, self.scroll - (y - top))
        surf.set_clip(old)

    def draw_floaters(self, surf):
        for name, x, t, phase in self.floaters:
            k = t / 2.2
            y = 700 - 480 * (1 - (1 - k) ** 2)
            alpha = int(255 * min(1.0, (1 - k) * 3))
            size = 70 + 20 * math.sin(min(1.0, t * 4) * math.pi / 2)
            image(surf, f"emoji/{name}.png", x + math.sin(t * 5 + phase) * 14, y, size, alpha=alpha,
                  angle=math.sin(t * 4 + phase) * 12)
