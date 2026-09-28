"""Boîte à outils graphique : thème, mise à l'échelle, dessin et widgets.

Tout le jeu est pensé dans un espace « logique » de 1200 x 800. Le module convertit
ces coordonnées en pixels réels selon la taille de la fenêtre (écran Retina,
écran 4K, plein écran…), ce qui donne un rendu net partout.
"""

from __future__ import annotations

import math
import random

import pygame

from .paths import asset

W, H = 1200, 800

# --- Palette -----------------------------------------------------------------
INK = (42, 26, 14)
INK_SOFT = (96, 72, 52)
CREAM = (255, 248, 232)
PAPER = (255, 239, 206)
YELLOW = (255, 217, 59)
YELLOW_HI = (255, 229, 110)
ORANGE = (255, 138, 61)
FOX_C = (240, 104, 28)
GOOSE_C = (92, 152, 204)
GREEN = (38, 166, 104)
RED = (226, 56, 70)
WHITE = (255, 255, 255)
BG_A = (255, 224, 92)
BG_B = (255, 128, 66)
LINE = (140, 92, 48)


class Gfx:
    """Conversion logique -> pixels + caches (polices, images, textes)."""

    def __init__(self):
        self.z = 1.0
        self.ox = self.oy = 0
        self._fonts = {}
        self._images = {}
        self._text = {}

    def configure(self, surface: pygame.Surface):
        sw, sh = surface.get_size()
        self.z = min(sw / W, sh / H)
        self.ox = int((sw - W * self.z) / 2)
        self.oy = int((sh - H * self.z) / 2)
        self._fonts.clear()
        self._images.clear()
        self._text.clear()

    # conversions
    def p(self, v: float) -> int:
        return int(round(v * self.z))

    def pt(self, x: float, y: float) -> tuple[int, int]:
        return int(round(self.ox + x * self.z)), int(round(self.oy + y * self.z))

    def r(self, x, y, w, h) -> pygame.Rect:
        x0, y0 = self.pt(x, y)
        x1, y1 = self.pt(x + w, y + h)
        return pygame.Rect(x0, y0, x1 - x0, y1 - y0)

    def to_logical(self, px: float, py: float) -> tuple[float, float]:
        return (px - self.ox) / self.z, (py - self.oy) / self.z

    # ressources
    def font(self, name: str, size: float) -> pygame.font.Font:
        key = (name, self.p(size))
        if key not in self._fonts:
            files = {"title": "LilitaOne-Regular.ttf", "bold": "Poppins-Bold.ttf",
                     "semi": "Poppins-SemiBold.ttf", "regular": "Poppins-Regular.ttf"}
            self._fonts[key] = pygame.font.Font(asset("fonts/" + files[name]), max(6, key[1]))
        return self._fonts[key]

    def image(self, name: str, size: float) -> pygame.Surface:
        key = (name, self.p(size))
        if key not in self._images:
            if name not in self._images:
                self._images[name] = pygame.image.load(asset("images/" + name)).convert_alpha()
            src = self._images[name]
            self._images[key] = pygame.transform.smoothscale(src, (key[1], key[1]))
        return self._images[key]

    def render_text(self, text: str, font: str, size: float, color) -> pygame.Surface:
        key = (text, font, size, tuple(color))
        surf = self._text.get(key)
        if surf is None:
            if len(self._text) > 600:
                self._text.clear()
            surf = self.font(font, size).render(text, True, color)
            self._text[key] = surf
        return surf


G = Gfx()


# --- Dessin ------------------------------------------------------------------

def text(surf, s, x, y, size=24, font="semi", color=INK, anchor="topleft", alpha=255, shadow=None):
    img = G.render_text(s, font, size, color)
    rect = img.get_rect(**{anchor: G.pt(x, y)})
    if shadow:
        sh = G.render_text(s, font, size, shadow)
        surf.blit(sh, rect.move(0, G.p(3)))
    if alpha < 255:
        img = img.copy()
        img.set_alpha(alpha)
    surf.blit(img, rect)
    return rect


def wrap(s: str, font: str, size: float, width: float) -> list[str]:
    f = G.font(font, size)
    lines = []
    for para in s.split("\n"):
        words, line = para.split(" "), ""
        for w in words:
            test = (line + " " + w).strip()
            if f.size(test)[0] <= G.p(width):
                line = test
            else:
                lines.append(line)
                line = w
        lines.append(line)
    return lines


def paragraph(surf, s, x, y, width, size=18, font="regular", color=INK, spacing=1.45, align="left"):
    """Texte sur plusieurs lignes ; avec align="center", x est le centre du bloc."""
    lines = wrap(s, font, size, width)
    for i, line in enumerate(lines):
        if align == "center":
            text(surf, line, x, y + i * size * spacing, size, font, color, anchor="midtop")
        else:
            text(surf, line, x, y + i * size * spacing, size, font, color)
    return y + len(lines) * size * spacing


def box(surf, x, y, w, h, fill, radius=18, border=3, shadow=6, border_color=INK, alpha=255):
    """Carte au style « brutaliste » : bord foncé + ombre franche décalée."""
    rad = G.p(radius)
    if shadow:
        pygame.draw.rect(surf, INK, G.r(x + shadow * 0.6, y + shadow, w, h), border_radius=rad)
    rect = G.r(x, y, w, h)
    if alpha < 255:
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*fill, alpha), layer.get_rect(), border_radius=rad)
        surf.blit(layer, rect)
    else:
        pygame.draw.rect(surf, fill, rect, border_radius=rad)
    if border:
        pygame.draw.rect(surf, border_color, rect, max(1, G.p(border)), border_radius=rad)
    return rect


def stripe(surf, x, y, w, color):
    """Bandeau de couleur en haut d'une carte (dessiné à l'intérieur du bord)."""
    pygame.draw.rect(surf, color, G.r(x + 14, y + 12, w - 28, 9), border_radius=G.p(5))


def circle(surf, color, x, y, radius, width=0):
    if width:
        pygame.draw.circle(surf, color, G.pt(x, y), G.p(radius), max(1, G.p(width)))
    else:
        pygame.draw.aacircle(surf, color, G.pt(x, y), G.p(radius))


def alpha_circle(surf, color, alpha, x, y, radius, width=0):
    rad = max(1, G.p(radius))
    layer = pygame.Surface((rad * 2 + 4, rad * 2 + 4), pygame.SRCALPHA)
    if width:
        pygame.draw.circle(layer, (*color, alpha), (rad + 2, rad + 2), rad, max(1, G.p(width)))
    else:
        pygame.draw.aacircle(layer, (*color, alpha), (rad + 2, rad + 2), rad)
    cx, cy = G.pt(x, y)
    surf.blit(layer, (cx - rad - 2, cy - rad - 2))


def image(surf, name, x, y, size, anchor="center", alpha=255, angle=0.0):
    img = G.image(name, size)
    if angle:
        img = pygame.transform.rotozoom(img, angle, 1.0)
    if alpha < 255:
        img = img.copy()
        img.set_alpha(alpha)
    rect = img.get_rect(**{anchor: G.pt(x, y)})
    surf.blit(img, rect)
    return rect


def make_background(size) -> pygame.Surface:
    """Dégradé jaune -> orange (l'identité du jeu de 2023) + halos flous."""
    sw, sh = size
    small = pygame.Surface((64, 64))
    for yy in range(64):
        for xx in range(64):
            t = (xx * 0.65 + yy * 0.35) / 63
            small.set_at((xx, yy), [int(BG_A[k] + (BG_B[k] - BG_A[k]) * t) for k in range(3)])
    bg = pygame.transform.smoothscale(small, (sw, sh))
    glow = pygame.Surface((sw // 4 + 1, sh // 4 + 1), pygame.SRCALPHA)
    rng = random.Random(3)
    for _ in range(14):
        r = rng.randint(sh // 40, sh // 9)
        col = rng.choice([(255, 255, 255, 38), (255, 240, 170, 50), (255, 170, 90, 45)])
        pygame.draw.circle(glow, col, (rng.randint(0, sw // 4), rng.randint(0, sh // 4)), r)
    glow = pygame.transform.gaussian_blur(glow, max(2, sh // 120))
    bg.blit(pygame.transform.smoothscale(glow, (sw, sh)), (0, 0))
    return bg


# --- Animation -----------------------------------------------------------------

def ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_out_back(t: float) -> float:
    t = max(0.0, min(1.0, t))
    c = 1.70158
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


class Particles:
    """Plumes, confettis et étincelles."""

    def __init__(self):
        self.items = []

    def burst(self, x, y, n=18, colors=(WHITE, CREAM, (230, 230, 230)), speed=260, life=0.9, size=6, gravity=380):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            v = random.uniform(0.3, 1.0) * speed
            self.items.append([x, y, math.cos(a) * v, math.sin(a) * v - speed * 0.3,
                               life, life, random.choice(colors), size * random.uniform(0.6, 1.3), gravity,
                               random.uniform(0, 360), random.uniform(-400, 400)])

    def confetti(self, n=140):
        colors = [YELLOW, ORANGE, FOX_C, GOOSE_C, GREEN, RED, WHITE]
        for _ in range(n):
            self.items.append([random.uniform(0, W), random.uniform(-200, -10), random.uniform(-60, 60),
                               random.uniform(80, 260), 4.0, 4.0, random.choice(colors),
                               random.uniform(7, 12), 60, random.uniform(0, 360), random.uniform(-300, 300)])

    def update(self, dt):
        for p in self.items:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += p[8] * dt
            p[2] *= 0.99
            p[4] -= dt
            p[9] += p[10] * dt
        self.items = [p for p in self.items if p[4] > 0 and p[1] < H + 40]

    def draw(self, surf):
        for x, y, _, _, life, total, col, size, _, ang, _ in self.items:
            a = int(255 * min(1.0, life / (total * 0.4)))
            s = max(2, G.p(size))
            piece = pygame.Surface((s, s * 0.6 + 1), pygame.SRCALPHA)
            piece.fill((*col, a))
            piece = pygame.transform.rotate(piece, ang)
            surf.blit(piece, piece.get_rect(center=G.pt(x, y)))


# --- Widgets ---------------------------------------------------------------------

class Button:
    STYLES = {
        "primary": (YELLOW, YELLOW_HI, INK),
        "secondary": (CREAM, WHITE, INK),
        "fox": (FOX_C, (255, 130, 60), WHITE),
        "goose": (GOOSE_C, (120, 178, 225), WHITE),
        "danger": (RED, (240, 90, 100), WHITE),
        "dark": (INK, INK_SOFT, CREAM),
    }

    def __init__(self, label, x, y, w, h, on_click, style="primary", size=24, icon=None, enabled=True, hint=None):
        self.label, self.x, self.y, self.w, self.h = label, x, y, w, h
        self.on_click, self.style, self.size, self.icon = on_click, style, size, icon
        self.enabled, self.hint = enabled, hint
        self.hover = self.pressed = False
        self.lift = 0.0

    def contains(self, lx, ly):
        return self.x <= lx <= self.x + self.w and self.y <= ly <= self.y + self.h

    def handle(self, e, mouse, audio=None) -> bool:
        if not self.enabled:
            self.hover = False
            return False
        if e.type == pygame.MOUSEMOTION:
            self.hover = self.contains(*mouse)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.contains(*mouse):
            self.pressed = True
            return True
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            fire = self.pressed and self.contains(*mouse)
            self.pressed = False
            if fire:
                if audio:
                    audio.play("select")
                self.on_click()
                return True
        return False

    def update(self, dt):
        target = 3.0 if self.hover and not self.pressed else 0.0
        self.lift += (target - self.lift) * min(1.0, dt * 18)

    def draw(self, surf):
        base, hi, fg = self.STYLES[self.style]
        if not self.enabled:
            base, hi, fg = (225, 214, 196), (225, 214, 196), (160, 140, 120)
        press = 4 if self.pressed else 0
        shadow = 6 - press
        y = self.y - self.lift + press
        pygame.draw.rect(surf, INK, G.r(self.x + 2, self.y + 6, self.w, self.h), border_radius=G.p(16))
        rect = G.r(self.x, y + (6 - shadow) * 0, self.w, self.h)
        pygame.draw.rect(surf, hi if self.hover else base, rect, border_radius=G.p(16))
        pygame.draw.rect(surf, INK, rect, max(1, G.p(3)), border_radius=G.p(16))
        cx = self.x + self.w / 2
        if self.icon:
            label_w = G.font("bold", self.size).size(self.label)[0] / G.z
            icon_size = self.size * 1.6
            total = icon_size + 10 + label_w
            image(surf, self.icon, cx - total / 2 + icon_size / 2, y + self.h / 2, icon_size)
            text(surf, self.label, cx - total / 2 + icon_size + 10, y + self.h / 2 + 1,
                 self.size, "bold", fg, anchor="midleft")
        else:
            text(surf, self.label, cx, y + self.h / 2 + 1, self.size, "bold", fg, anchor="center")


class Segmented:
    """Choix unique parmi plusieurs options (ex. niveau de difficulté)."""

    def __init__(self, options, x, y, w, h, value, on_change=None, size=19, colors=None):
        self.options, self.x, self.y, self.w, self.h = options, x, y, w, h
        self.value, self.on_change, self.size = value, on_change, size
        self.colors = colors or {}
        self.hover = None

    def _cell(self, i):
        cw = self.w / len(self.options)
        return self.x + i * cw, cw

    def handle(self, e, mouse, audio=None):
        lx, ly = mouse
        inside = self.y <= ly <= self.y + self.h and self.x <= lx <= self.x + self.w
        idx = int((lx - self.x) / (self.w / len(self.options))) if inside else None
        if e.type == pygame.MOUSEMOTION:
            self.hover = idx
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and idx is not None:
            key = self.options[idx][0]
            if key != self.value:
                self.value = key
                if audio:
                    audio.play("select")
                if self.on_change:
                    self.on_change(key)
            return True
        return False

    def update(self, dt):
        pass

    def draw(self, surf):
        pygame.draw.rect(surf, INK, G.r(self.x + 2, self.y + 5, self.w, self.h), border_radius=G.p(14))
        pygame.draw.rect(surf, CREAM, G.r(self.x, self.y, self.w, self.h), border_radius=G.p(14))
        for i, (key, label) in enumerate(self.options):
            cx, cw = self._cell(i)
            if key == self.value:
                col = self.colors.get(key, YELLOW)
                pygame.draw.rect(surf, col, G.r(cx + 5, self.y + 5, cw - 10, self.h - 10), border_radius=G.p(10))
                pygame.draw.rect(surf, INK, G.r(cx + 5, self.y + 5, cw - 10, self.h - 10), max(1, G.p(2)),
                                 border_radius=G.p(10))
            elif self.hover == i:
                pygame.draw.rect(surf, PAPER, G.r(cx + 5, self.y + 5, cw - 10, self.h - 10), border_radius=G.p(10))
            fg = WHITE if key == self.value and key in self.colors else INK
            text(surf, label, cx + cw / 2, self.y + self.h / 2 + 1, self.size, "semi", fg, anchor="center")
        pygame.draw.rect(surf, INK, G.r(self.x, self.y, self.w, self.h), max(1, G.p(3)), border_radius=G.p(14))


class TextInput:
    def __init__(self, x, y, w, h, value="", placeholder="", max_len=16, upper=False, size=26, on_enter=None,
                 allowed=None):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.value, self.placeholder, self.max_len = value, placeholder, max_len
        self.upper, self.size, self.on_enter, self.allowed = upper, size, on_enter, allowed
        self.focused = False
        self.blink = 0.0

    def handle(self, e, mouse, audio=None):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            lx, ly = mouse
            self.focused = self.x <= lx <= self.x + self.w and self.y <= ly <= self.y + self.h
            return self.focused
        if not self.focused:
            return False
        if e.type == pygame.TEXTINPUT:
            for ch in e.text:
                if self.upper:
                    ch = ch.upper()
                if self.allowed and ch not in self.allowed:
                    continue
                if len(self.value) < self.max_len and ch.isprintable():
                    self.value += ch
            return True
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.on_enter:
                self.on_enter()
            elif e.key == pygame.K_v and (e.mod & (pygame.KMOD_CTRL | pygame.KMOD_META)):
                try:
                    pasted = pygame.scrap.get_text() if hasattr(pygame.scrap, "get_text") else ""
                except Exception:
                    pasted = ""
                for ch in pasted or "":
                    ch = ch.upper() if self.upper else ch
                    if (not self.allowed or ch in self.allowed) and len(self.value) < self.max_len:
                        self.value += ch
            return True
        return False

    def update(self, dt):
        self.blink = (self.blink + dt) % 1.0

    def draw(self, surf):
        box(surf, self.x, self.y, self.w, self.h, WHITE, radius=14, shadow=5,
            border_color=FOX_C if self.focused else INK)
        shown = self.value or self.placeholder
        color = INK if self.value else (175, 160, 140)
        r = text(surf, shown, self.x + self.w / 2, self.y + self.h / 2 + 1, self.size, "bold", color, anchor="center")
        if self.focused and self.blink < 0.55:
            cx = (r.right if self.value else r.centerx - G.p(2)) + G.p(3)
            pygame.draw.rect(surf, FOX_C, (cx, r.top + G.p(4), max(2, G.p(3)), r.height - G.p(8)))
