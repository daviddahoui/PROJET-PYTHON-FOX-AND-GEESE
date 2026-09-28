"""Écran de partie : plateau animé, IA, jeu local et en ligne."""

from __future__ import annotations

import math
import random
import threading
import time

import pygame

from . import ai, rules, storage
from .rules import FOX, GOOSE, PASS, Match
from .chat import ChatPanel
from .scenes import MenuScene, Scene
from .ui import (CREAM, FOX_C, G, GOOSE_C, GREEN, INK, INK_SOFT, LINE, PAPER, RED, WHITE, YELLOW,
                 Button, Particles, alpha_circle, box, ease_out, ease_out_back, image, paragraph, stripe, text)

# Géométrie du plateau (coordonnées logiques)
BX, BY = 400, 400        # centre
STEP = 88                 # écart entre deux intersections
CARD = (40, 40, 720, 720)
TOKEN = 35                # rayon d'un pion

SIDE_NAME = {FOX: "Renard", GOOSE: "Oies"}


def pos(i: int) -> tuple[float, float]:
    r, c = rules.rc(i)
    return BX + (c - 3) * STEP, BY + (r - 3) * STEP


def hit_point(lx: float, ly: float) -> int | None:
    c = round((lx - BX) / STEP + 3)
    r = round((ly - BY) / STEP + 3)
    if not rules.on_board(r, c):
        return None
    x, y = pos(rules.idx(r, c))
    if math.hypot(lx - x, ly - y) > STEP * 0.48:
        return None
    return rules.idx(r, c)


# --- Rendus mis en cache (refaits seulement si la fenêtre change de taille) ---

_cache: dict = {}


def board_surface() -> pygame.Surface:
    """Plateau en croix, dessiné en 3x puis réduit : lignes parfaitement lissées."""
    key = ("board", G.z)
    if key in _cache:
        return _cache[key]
    ss = 3
    k = G.z * ss
    x0, y0, w, h = CARD
    surf = pygame.Surface((int(w * k), int(h * k)), pygame.SRCALPHA)

    def P(x, y):
        return int((x - x0) * k), int((y - y0) * k)

    pad, rad = 50, 34
    lo, hi = pos(rules.idx(0, 2)), pos(rules.idx(6, 4))
    left, right = pos(rules.idx(2, 0)), pos(rules.idx(4, 6))
    bands = [
        pygame.Rect(*P(lo[0] - pad, lo[1] - pad), int((hi[0] - lo[0] + 2 * pad) * k), int((hi[1] - lo[1] + 2 * pad) * k)),
        pygame.Rect(*P(left[0] - pad, left[1] - pad), int((right[0] - left[0] + 2 * pad) * k),
                    int((right[1] - left[1] + 2 * pad) * k)),
    ]
    border = int(4 * k)
    for b in bands:
        pygame.draw.rect(surf, INK, b.inflate(border * 2, border * 2), border_radius=int((rad + 4) * k))
    for b in bands:
        pygame.draw.rect(surf, (252, 222, 160), b, border_radius=int(rad * k))
    lw = int(5 * k)
    for a, b in rules.LINES:
        pa, pb = P(*pos(a)), P(*pos(b))
        pygame.draw.line(surf, LINE, pa, pb, lw)
    for i in rules.POINTS:
        pygame.draw.circle(surf, LINE, P(*pos(i)), int(9 * k))
        pygame.draw.circle(surf, (255, 240, 205), P(*pos(i)), int(4 * k))
    out = pygame.transform.smoothscale(surf, (int(w * G.z), int(h * G.z)))
    _cache[key] = out
    return out


def token_surface(kind: str, scale: float = 1.0) -> pygame.Surface:
    key = ("token", kind, G.z, round(scale, 2))
    if key in _cache:
        return _cache[key]
    ss = 3
    radius = TOKEN * scale
    size = int(radius * 2 * G.z * ss) + 4
    big = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    fill = (255, 214, 170) if kind == FOX else (226, 240, 252)
    ring = FOX_C if kind == FOX else GOOSE_C
    pygame.draw.circle(big, INK, (c, c), c - 2)
    pygame.draw.circle(big, ring, (c, c), int(c - 2 - 3.2 * G.z * ss))
    pygame.draw.circle(big, fill, (c, c), int(c - 2 - 8 * G.z * ss))
    out = pygame.transform.smoothscale(big, (size // ss, size // ss))
    emoji = G.image("fox.png" if kind == FOX else "goose.png", radius * 1.55)
    out.blit(emoji, emoji.get_rect(center=(out.get_width() // 2, out.get_height() // 2 - int(1 * G.z))))
    _cache[key] = out
    return out


def draw_token(surf, kind, x, y, scale=1.0, lift=0.0, alpha=255):
    # ombre portée (s'éloigne quand le pion est soulevé)
    sh_w, sh_h = G.p(TOKEN * 2 * scale * 0.9), G.p(TOKEN * 0.7 * scale)
    shadow = pygame.Surface((sh_w, sh_h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (42, 26, 14, int(max(40, 90 - lift * 3) * alpha / 255)), shadow.get_rect())
    sx, sy = G.pt(x, y + TOKEN * scale * 0.72 + lift * 0.2)
    surf.blit(shadow, shadow.get_rect(center=(sx, sy)))
    img = token_surface(kind, scale)
    if alpha < 255:
        img = img.copy()
        img.set_alpha(alpha)
    surf.blit(img, img.get_rect(center=G.pt(x, y - lift)))


class Anim:
    def __init__(self, move, before: rules.State, piece: str, duration: float):
        self.move, self.before, self.piece, self.duration = move, before, piece, duration
        self.t = 0.0

    @property
    def done(self):
        return self.t >= self.duration


class GameScene(Scene):
    def __init__(self, app, mode, setup, human_side=FOX, level="Moyen", moves=None, seconds=0.0, session=None,
                 chat_log=None):
        super().__init__(app)
        self.mode, self.setup, self.level = mode, setup, level
        self.human_side = human_side or FOX
        self.session = session
        self.match = Match(setup, moves)
        self.shown = self.match.state            # état affiché (en retard pendant les animations)
        self.queue: list = []                    # coups joués en attente d'animation
        self.anim: Anim | None = None
        self.selected: int | None = None
        self.hover_point: int | None = None
        self.seconds = float(seconds)
        self.paused = False
        self.particles = Particles()
        self.ai_thread: threading.Thread | None = None
        self.ai_result = None
        self.ai_started = 0.0
        self.end_shown = 0.0
        self.end_sound = False
        self.peer_name = session.peer_name if session else None
        # En ligne, les fenêtres (pause, fin) se centrent sur le plateau pour laisser le chat visible
        self.cx = 400 if mode == "online" else 600
        self.chat = ChatPanel(self, 800, 286, 360, 400, chat_log) if mode == "online" else None
        self.rematch_me = self.rematch_peer = False
        self.net_error = None
        self.last_move = self.match.moves[-1] if self.match.moves else None
        self.rng = random.Random()
        self._build_panel()

    # --- Qui joue ? ------------------------------------------------------------------------

    def is_human_turn(self, state=None) -> bool:
        s = state or self.match.state
        if s.winner:
            return False
        if self.mode == "local":
            return True
        return s.turn == self.human_side

    def side_label(self, side) -> str:
        if self.mode == "local":
            return "Joueur " + ("Renard" if side == FOX else "Oies")
        if side == self.human_side:
            return "Toi"
        if self.mode == "solo":
            return f"IA ({self.level})"
        return self.peer_name or "Ton ami"

    # --- Panneau latéral -----------------------------------------------------------------

    def _build_panel(self):
        px = 800
        self.btn_pass = Button("Arrêter la rafle", px, 520, 360, 58, self.pass_chain, style="fox", size=20)
        self.btn_undo = Button("Annuler le coup", px, 600, 174, 58, self.undo, style="secondary", size=17)
        self.btn_menu = Button("Pause", px + 186, 600, 174, 58, self.toggle_pause, style="secondary", size=17)
        if self.mode == "online":
            self.btn_menu = Button("Menu", px, 702, 170, 54, self.toggle_pause, style="secondary", size=17)
            self.btn_pass = Button("Arrêter la rafle", px + 182, 702, 178, 54, self.pass_chain, style="fox", size=16)
        self.panel_buttons = [self.btn_pass, self.btn_menu] + ([self.btn_undo] if self.mode != "online" else [])
        self.overlay_buttons: list = []

    def _pause_buttons(self):
        x, w = self.cx - 160, 320
        if self.mode == "online":
            items = [("Reprendre", self.toggle_pause, "primary"),
                     ("Quitter la partie", self.quit_to_menu, "danger")]
        else:
            items = [("Reprendre", self.toggle_pause, "primary"),
                     ("Recommencer", self.restart, "secondary"),
                     ("Sauvegarder et quitter", self.save_and_quit, "secondary"),
                     ("Menu principal", self.quit_to_menu, "secondary")]
        y0 = 400 - len(items) * 76 / 2 + 50
        return [Button(lbl, x, y0 + i * 76, w, 62, fn, style=st, size=21) for i, (lbl, fn, st) in enumerate(items)]

    def _end_buttons(self):
        if self.mode == "online":
            label = "Revanche !" if not self.rematch_me else "En attente…"
            first = Button(label, self.cx - 170, 560, 200, 62, self.ask_rematch, style="primary", size=21,
                           enabled=not self.rematch_me and not self.net_error)
        else:
            first = Button("Rejouer", self.cx - 170, 560, 200, 62, self.restart, style="primary", size=21)
        return [first, Button("Menu", self.cx + 50, 560, 120, 62, self.quit_to_menu, style="secondary", size=21)]

    # --- Actions -------------------------------------------------------------------------

    def toggle_pause(self):
        if self.match.state.winner and not self.anim:
            return
        self.paused = not self.paused
        self.overlay_buttons = self._pause_buttons() if self.paused else []

    def restart(self):
        storage.delete_game()
        self.app.go(GameScene(self.app, self.mode, self.setup, self.human_side, self.level))

    def quit_to_menu(self):
        if self.session:
            self.session.close()
        elif not self.match.state.winner and self.match.moves:
            self.autosave()
        self.app.go(MenuScene(self.app))

    def save_and_quit(self):
        self.autosave()
        self.app.toast("Partie sauvegardée — reprends-la depuis le menu.")
        self.app.go(MenuScene(self.app))

    def autosave(self):
        if self.mode == "online":
            return
        if self.match.state.winner:
            storage.delete_game()
            return
        storage.save_game({"mode": self.mode, "setup": self.setup, "human_side": self.human_side,
                           "level": self.level, "moves": [list(m) for m in self.match.moves],
                           "seconds": round(self.seconds, 1), "saved_at": time.time()})

    def undo(self):
        if self.anim or self.queue or self.mode == "online" or self.ai_thread:
            return
        if not self.match.moves:
            return
        self.match.undo()
        # En solo, on revient jusqu'au dernier moment où c'était à toi de jouer
        if self.mode == "solo":
            while self.match.moves and not self.is_human_turn():
                self.match.undo()
        self.shown = self.match.state
        self.selected = None
        self.last_move = self.match.moves[-1] if self.match.moves else None
        self.end_shown = 0.0
        self.end_sound = False
        self.app.audio.play("move")
        self.autosave()

    def pass_chain(self):
        if self.match.state.chain is not None and self.is_human_turn() and not self.anim and not self.queue:
            self.play(PASS)

    def ask_rematch(self):
        self.rematch_me = True
        self.session.send({"t": "rematch"})
        self.overlay_buttons = self._end_buttons()
        self._maybe_rematch()

    def _maybe_rematch(self):
        if self.rematch_me and self.rematch_peer and self.session.role == "host":
            new_host_side = GOOSE if self.human_side == FOX else FOX       # on échange les camps
            self.session.send({"t": "start", "setup": self.setup, "host_side": new_host_side})
            self._restart_online(new_host_side)

    def _restart_online(self, my_side):
        scene = GameScene(self.app, "online", self.setup, human_side=my_side, session=self.session,
                          chat_log=self.chat.log)
        scene.chat.system("Revanche ! Les camps sont inversés.")
        self.app.go(scene)

    # --- Jouer un coup ---------------------------------------------------------------------

    def play(self, move, remote=False):
        before = self.match.state
        self.match.play(move)
        self.queue.append((move, before))
        self.selected = None
        if self.mode == "online" and not remote:
            self.session.send({"t": "move", "n": len(self.match.moves) - 1, "m": list(move)})
        if self.mode != "online":
            self.autosave()

    def _start_next_anim(self):
        if self.anim or not self.queue:
            return
        move, before = self.queue.pop(0)
        if move == PASS:
            self.shown = self.match.history[len(self.match.history) - 1 - len(self.queue)]
            self.last_move = move
            return
        piece = before.cells[move[0]]
        dur = 0.34 if rules.is_capture(move) else 0.2
        self.anim = Anim(move, before, piece, dur)
        self.app.audio.play("move")

    def _finish_anim(self):
        a = self.anim
        self.anim = None
        self.shown = self.match.history[len(self.match.history) - 1 - len(self.queue)]
        self.last_move = a.move
        if rules.is_capture(a.move):
            x, y = pos((a.move[0] + a.move[1]) // 2)
            self.particles.burst(x, y, n=26, speed=300)
            self.particles.burst(x, y, n=10, colors=(YELLOW, FOX_C), speed=200, size=5)
            self.app.audio.play("capture")

    # --- Événements ------------------------------------------------------------------------

    def handle(self, e, mouse):
        if self.chat and not self.net_error and self.chat.handle(e, mouse):
            return
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_ESCAPE, pygame.K_p):
                self.toggle_pause()
                return
            if e.key == pygame.K_z and (e.mod & (pygame.KMOD_CTRL | pygame.KMOD_META)) and not self.paused:
                self.undo()
                return
            if e.key == pygame.K_SPACE:
                self.pass_chain()
                return
        if self.overlay_buttons:
            for b in self.overlay_buttons:
                if b.handle(e, mouse, self.app.audio):
                    return
            return
        for b in self.panel_buttons:
            if b.handle(e, mouse, self.app.audio):
                return
        if e.type == pygame.MOUSEMOTION:
            self.hover_point = hit_point(*mouse)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.click(hit_point(*mouse))

    def click(self, p):
        s = self.match.state
        if p is None or self.anim or self.queue or not self.is_human_turn():
            if p is None:
                self.selected = None
            return
        if s.chain is not None:
            if p == s.chain:
                self.play(PASS)                      # cliquer sur le renard = arrêter la rafle
                return
            if (s.chain, p) in rules.legal_moves(s):
                self.play((s.chain, p))
            return
        if self.selected is not None:
            if (self.selected, p) in rules.legal_moves(s):
                self.play((self.selected, p))
                return
            if p == self.selected:
                self.selected = None
                return
        if s.cells[p] == s.turn and rules.moves_from(s, p):
            self.selected = p
            self.app.audio.play("select")
        elif s.cells[p] == s.turn:
            self.selected = None
            self.app.audio.play("error")
        else:
            self.selected = None

    # --- Boucle ----------------------------------------------------------------------------

    def update(self, dt):
        super().update(dt)
        for b in self.panel_buttons + self.overlay_buttons:
            b.update(dt)
        self.particles.update(dt)
        if self.chat:
            self.chat.update(dt)
        s = self.match.state
        self.btn_pass.enabled = s.chain is not None and self.is_human_turn() and not self.anim
        self.btn_undo.enabled = bool(self.match.moves) and not self.anim and self.ai_thread is None
        if self.mode == "solo" and self.match.moves and self.human_side == GOOSE and len(self.match.moves) < 2:
            self.btn_undo.enabled = False

        if self.session:
            self._net_update()

        if not self.paused and not s.winner:
            self.seconds += dt

        # Animations
        if self.anim:
            self.anim.t += dt
            if self.anim.done:
                self._finish_anim()
        self._start_next_anim()

        # Tour de l'IA (calculé dans un thread pour ne pas figer l'affichage)
        if self.mode == "solo" and not self.paused and not s.winner and s.turn != self.human_side:
            if self.ai_thread is None and not self.anim and not self.queue:
                snapshot = s.copy()
                self.ai_result = None
                self.ai_started = time.monotonic()

                def think():
                    self.ai_result = ai.choose_move(snapshot, self.level, self.rng) or PASS

                self.ai_thread = threading.Thread(target=think, daemon=True)
                self.ai_thread.start()
            elif self.ai_thread and not self.ai_thread.is_alive() and time.monotonic() - self.ai_started > 0.45:
                self.ai_thread = None
                if self.ai_result is not None and self.match.state.turn != self.human_side:
                    self.play(self.ai_result)

        # Fin de partie
        if s.winner and not self.anim and not self.queue:
            if not self.end_shown:
                self._on_game_over()
            self.end_shown += dt

    def _on_game_over(self):
        self.end_shown = 0.001
        self.paused = False
        self.overlay_buttons = self._end_buttons()
        if self.mode != "online":
            storage.delete_game()
        s = self.match.state
        won = s.winner == self.human_side or (self.mode == "local" and s.winner != "draw")
        if not self.end_sound:
            self.end_sound = True
            self.app.audio.play("win" if won else "lose")
            if won:
                self.particles.confetti()

    def _net_update(self):
        for e in self.session.poll():
            t = e.get("t")
            if self.chat.receive(e):
                continue
            if t == "move":
                n, m = e.get("n"), tuple(e.get("m", ()))
                if n != len(self.match.moves) or m not in rules.legal_moves(self.match.state) \
                        or self.match.state.turn == self.human_side:
                    self.net_error = "Désynchronisation : la partie ne peut pas continuer."
                    continue
                self.play(m, remote=True)
            elif t == "rematch":
                self.rematch_peer = True
                self.chat.system(f"{self.peer_name or 'Ton ami'} veut une revanche !")
                self._maybe_rematch()
            elif t == "start" and self.session.role == "guest":
                other = GOOSE if e["host_side"] == FOX else FOX
                self._restart_online(other)
            elif t == "bye":
                self.net_error = f"{self.peer_name or 'Ton ami'} a quitté la partie."
            elif t == "lost":
                self.net_error = "Connexion perdue avec ton ami."
            elif t == "status":
                self.chat.system(e["text"])
        if self.net_error and not self.overlay_buttons:
            self.overlay_buttons = [Button("Retour au menu", self.cx - 150, 470, 300, 62, self.quit_to_menu, size=21)]
        elif self.net_error and self.match.state.winner:
            self.overlay_buttons = self._end_buttons()

    # --- Affichage -------------------------------------------------------------------------

    def draw(self, surf):
        box(surf, *CARD, CREAM, radius=34, border=4, shadow=10)
        board = board_surface()
        surf.blit(board, G.pt(CARD[0], CARD[1]))
        self._draw_hints(surf)
        self._draw_pieces(surf)
        self._draw_panel(surf)
        self.particles.draw(surf)
        chat_on_top = self.chat is not None and not self.net_error
        if self.chat:
            self.chat.draw_floaters(surf)
            if not chat_on_top:
                self.chat.draw(surf)
        if self.match.state.winner and not self.anim and not self.queue:
            self._draw_end(surf)
        elif self.paused:
            self._draw_pause(surf)
        if self.net_error and not self.match.state.winner:
            self._draw_net_error(surf)
        if chat_on_top:
            self.chat.draw(surf)          # reste utilisable pendant la pause et après la partie

    def _draw_hints(self, surf):
        s = self.shown
        # Dernier coup joué : traces douces sur départ et arrivée
        if self.last_move and self.last_move != PASS and not self.anim:
            for i in self.last_move:
                alpha_circle(surf, YELLOW, 150, *pos(i), 30)
        if self.anim or self.queue or not self.is_human_turn(s):
            return
        pulse = (math.sin(self.t * 5) + 1) / 2
        focus = s.chain if s.chain is not None else self.selected
        if focus is not None:
            for _, to in rules.moves_from(s, focus):
                if to < 0:
                    continue
                x, y = pos(to)
                if rules.is_capture((focus, to)):
                    alpha_circle(surf, RED, 90, x, y, 24 + pulse * 3)
                    alpha_circle(surf, RED, 255, x, y, 24 + pulse * 3, width=3)
                    ox, oy = pos((focus + to) // 2)
                    alpha_circle(surf, RED, 200, ox, oy, TOKEN + 6, width=4)
                else:
                    alpha_circle(surf, GREEN, 70, x, y, 20 + pulse * 3)
                    alpha_circle(surf, GREEN, 230, x, y, 9)
        elif self.hover_point is not None and s.cells[self.hover_point] == s.turn and rules.moves_from(s, self.hover_point):
            alpha_circle(surf, WHITE, 140, *pos(self.hover_point), TOKEN + 8)

    def _draw_pieces(self, surf):
        a = self.anim
        s = a.before if a else self.shown
        moving_from = a.move[0] if a else None
        captured = (a.move[0] + a.move[1]) // 2 if a and rules.is_capture(a.move) else None
        focus = s.chain if s.chain is not None else self.selected
        for i in rules.POINTS:
            kind = s.cells[i]
            if kind not in (FOX, GOOSE) or i == moving_from:
                continue
            x, y = pos(i)
            if i == captured:
                k = ease_out(a.t / a.duration)
                draw_token(surf, kind, x, y, scale=1 - 0.6 * k, alpha=int(255 * (1 - k)))
                continue
            lift = 0.0
            if i == focus and not a:
                lift = 7 + math.sin(self.t * 6) * 2
                alpha_circle(surf, YELLOW, 255, x, y, TOKEN + 7, width=5)
            elif i == self.hover_point and self.is_human_turn(s) and kind == s.turn and not a:
                lift = 3
            draw_token(surf, kind, x, y, lift=lift)
        if a:
            (x0, y0), (x1, y1) = pos(a.move[0]), pos(a.move[1])
            k = ease_out(a.t / a.duration)
            x, y = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
            hop = math.sin(math.pi * min(1.0, a.t / a.duration)) * (46 if captured is not None else 10)
            draw_token(surf, a.piece, x, y, scale=1 + hop / 400, lift=hop)

    def _draw_panel(self, surf):
        if self.mode == "online":
            return self._draw_panel_online(surf)
        s = self.shown
        px, pw = 800, 360
        # Carte « à qui le tour »
        turn_col = FOX_C if s.turn == FOX else GOOSE_C
        box(surf, px, 40, pw, 170, CREAM, radius=22)
        stripe(surf, px, 40, pw, turn_col)
        image(surf, "fox.png" if s.turn == FOX else "goose.png", px + 70, 128, 96,
              angle=math.sin(self.t * 3) * 4)
        who = self.side_label(s.turn)
        if s.winner:
            head, sub = "Partie terminée", ""
        elif self.mode == "solo" and s.turn != self.human_side:
            head, sub = "L'IA réfléchit" + "." * (1 + int(self.t * 3) % 3), SIDE_NAME[s.turn]
        elif self.mode == "local":
            if s.turn == GOOSE:
                head = "Au tour des oies"
            else:
                head = "Au tour des renards" if s.fox_count > 1 else "Au tour du renard"
            sub = "Clique sur une pièce"
        elif s.turn == self.human_side:
            head, sub = "À toi de jouer !", f"Tu joues : {SIDE_NAME[s.turn]}"
        else:
            head, sub = f"Tour de {who}", SIDE_NAME[s.turn]
        if s.chain is not None and not s.winner:
            sub = "Rafle ! Recapture ou arrête-toi"
        text(surf, head, px + 132, 100, 25, "title", INK, anchor="midleft")
        text(surf, sub, px + 132, 140, 16, "semi", INK_SOFT, anchor="midleft")

        # Statistiques
        box(surf, px, 236, pw, 250, CREAM, radius=22)
        start_geese = rules.SETUPS[self.setup].count(GOOSE)
        left = s.geese_left
        need = rules.GEESE_PER_FOX * s.fox_count
        text(surf, "Oies sur le plateau", px + 24, 256, 16, "bold", INK_SOFT)
        text(surf, f"{left} / {start_geese}", px + pw - 24, 256, 16, "bold", INK, anchor="topright")
        bar = G.r(px + 24, 288, pw - 48, 20)
        pygame.draw.rect(surf, PAPER, bar, border_radius=G.p(10))
        fill = bar.copy()
        fill.width = int(bar.width * left / start_geese)
        pygame.draw.rect(surf, GOOSE_C, fill, border_radius=G.p(10))
        mark = bar.x + int(bar.width * (need - 1) / start_geese)
        pygame.draw.line(surf, RED, (mark, bar.y - G.p(4)), (mark, bar.bottom + G.p(4)), max(1, G.p(3)))
        pygame.draw.rect(surf, INK, bar, max(1, G.p(2)), border_radius=G.p(10))
        text(surf, f"Le renard gagne à {need - 1} oies", px + 24, 316, 13, "regular", INK_SOFT)

        text(surf, "Oies croquées", px + 24, 348, 16, "bold", INK_SOFT)
        n = s.captured
        for k in range(min(n, 10)):
            image(surf, "goose.png", px + 40 + k * 26, 392, 34)
        if n > 10:
            text(surf, f"+{n - 10}", px + 40 + 10 * 26 + 4, 394, 17, "bold", INK, anchor="midleft")
        if n == 0:
            text(surf, "aucune pour l'instant", px + 24, 380, 15, "regular", INK_SOFT)

        m, sec = divmod(int(self.seconds), 60)
        text(surf, f"Temps  {m:02d}:{sec:02d}", px + 24, 440, 17, "bold", INK)
        text(surf, f"Coups  {len(self.match.moves)}", px + pw - 24, 440, 17, "bold", INK, anchor="topright")

        # Boutons
        if self.btn_pass.enabled:
            self.btn_pass.draw(surf)
        else:
            mode = {"solo": f"Solo · IA {self.level}", "local": "Deux joueurs · même écran",
                    "online": f"En ligne · contre {self.peer_name or 'ton ami'}"}[self.mode]
            text(surf, mode, px + pw / 2, 536, 16, "semi", INK, anchor="center")
            if self.mode == "online" and self.session:
                text(surf, f"Code {self.session.code}", px + pw / 2, 562, 14, "regular", INK_SOFT, anchor="center")
        self.btn_menu.draw(surf)
        if self.mode != "online":
            self.btn_undo.draw(surf)
        text(surf, "Échap : pause · Ctrl/Cmd+Z : annuler" if self.mode != "online" else "Échap : menu",
             px + pw / 2, 690, 14, "regular", INK_SOFT, anchor="center")


    def _draw_panel_online(self, surf):
        """Panneau compact : tour, statistiques, puis le chat (dessiné à part)."""
        s = self.shown
        px, pw = 800, 360
        box(surf, px, 40, pw, 100, CREAM, radius=22)
        stripe(surf, px, 40, pw, FOX_C if s.turn == FOX else GOOSE_C)
        image(surf, "fox.png" if s.turn == FOX else "goose.png", px + 50, 94, 64, angle=math.sin(self.t * 3) * 4)
        if s.winner:
            head, sub = "Partie terminée", f"contre {self.peer_name or 'ton ami'}"
        elif s.turn == self.human_side:
            head, sub = "À toi de jouer !", f"Tu joues : {SIDE_NAME[s.turn]}"
        else:
            head, sub = f"Tour de {self.peer_name or 'ton ami'}", SIDE_NAME[s.turn]
        if s.chain is not None and not s.winner:
            sub = "Rafle ! Recapture ou arrête-toi"
        text(surf, head, px + 96, 82, 22, "title", INK, anchor="midleft")
        text(surf, sub, px + 96, 112, 14, "semi", INK_SOFT, anchor="midleft")

        box(surf, px, 156, pw, 114, CREAM, radius=22)
        start_geese = rules.SETUPS[self.setup].count(GOOSE)
        left, need = s.geese_left, rules.GEESE_PER_FOX * s.fox_count
        text(surf, "Oies sur le plateau", px + 22, 170, 14, "bold", INK_SOFT)
        text(surf, f"{left} / {start_geese}", px + pw - 22, 170, 14, "bold", INK, anchor="topright")
        bar = G.r(px + 22, 196, pw - 44, 16)
        pygame.draw.rect(surf, PAPER, bar, border_radius=G.p(8))
        fill = bar.copy()
        fill.width = int(bar.width * left / start_geese)
        pygame.draw.rect(surf, GOOSE_C, fill, border_radius=G.p(8))
        mark = bar.x + int(bar.width * (need - 1) / start_geese)
        pygame.draw.line(surf, RED, (mark, bar.y - G.p(4)), (mark, bar.bottom + G.p(4)), max(1, G.p(3)))
        pygame.draw.rect(surf, INK, bar, max(1, G.p(2)), border_radius=G.p(8))
        m, sec = divmod(int(self.seconds), 60)
        text(surf, f"Croquées  {s.captured}", px + 22, 228, 15, "bold", INK)
        text(surf, f"{m:02d}:{sec:02d}", px + pw / 2 + 10, 228, 15, "bold", INK, anchor="midtop")
        text(surf, f"Coups  {len(self.match.moves)}", px + pw - 22, 228, 15, "bold", INK, anchor="topright")

        self.btn_menu.draw(surf)
        if self.btn_pass.enabled:
            self.btn_pass.draw(surf)
        else:
            text(surf, f"Code {self.session.code}", px + 271, 729, 14, "semi", INK_SOFT, anchor="center")

    def _veil(self, surf, alpha=150):
        veil = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        veil.fill((42, 26, 14, alpha))
        surf.blit(veil, (0, 0))

    def _draw_pause(self, surf):
        self._veil(surf)
        n = len(self.overlay_buttons)
        top = self.overlay_buttons[0].y - 110
        box(surf, self.cx - 200, top, 400, n * 76 + 140, CREAM, radius=26, shadow=10)
        text(surf, "Pause" if self.mode != "online" else "Menu", self.cx, top + 55, 44, "title", INK, anchor="center")
        for b in self.overlay_buttons:
            b.draw(surf)

    def _draw_end(self, surf):
        k = ease_out_back(min(1.0, self.end_shown / 0.45))
        self._veil(surf, int(140 * min(1.0, self.end_shown / 0.3)))
        s = self.match.state
        y = 210 + (1 - k) * 60
        cx = self.cx
        box(surf, cx - 260, y, 520, 400, CREAM, radius=28, shadow=10)
        if s.winner == "draw":
            title, col, icon = "Match nul", INK, "trophy.png"
        elif self.mode == "local":
            title = "Le renard gagne !" if s.winner == FOX else "Les oies gagnent !"
            col, icon = (FOX_C if s.winner == FOX else GOOSE_C), "trophy.png"
        elif s.winner == self.human_side:
            title, col, icon = "Victoire !", GREEN, "trophy.png"
        else:
            title, col, icon = "Défaite…", RED, "fox.png" if s.winner == FOX else "goose.png"
        image(surf, icon, cx, y + 20, 130 * k, angle=math.sin(self.t * 2) * 5)
        text(surf, title, cx, y + 118, 50, "title", col, anchor="center")
        paragraph(surf, rules.REASONS.get(s.reason, ""), cx, y + 160, 440, size=17, align="center")
        m, sec = divmod(int(self.seconds), 60)
        stats = f"{len(self.match.moves)} coups  ·  {s.captured} oie{'s' if s.captured > 1 else ''} croquée" \
                f"{'s' if s.captured > 1 else ''}  ·  {m:02d}:{sec:02d}"
        text(surf, stats, cx, y + 244, 17, "bold", INK_SOFT, anchor="center")
        if self.mode == "online" and self.rematch_peer and not self.rematch_me:
            text(surf, f"{self.peer_name or 'Ton ami'} veut une revanche !", cx, y + 268, 17, "bold",
                 FOX_C, anchor="center")
        if self.net_error:
            text(surf, self.net_error, cx, y + 268, 16, "semi", RED, anchor="center")
        for b in self.overlay_buttons:
            b.y = y + 305
            b.draw(surf)

    def _draw_net_error(self, surf):
        self._veil(surf)
        box(surf, self.cx - 250, 280, 500, 280, CREAM, radius=26, shadow=10)
        text(surf, "Partie interrompue", self.cx, 340, 38, "title", RED, anchor="center")
        paragraph(surf, self.net_error, self.cx, 380, 420, size=18, align="center")
        for b in self.overlay_buttons:
            b.draw(surf)

    def leave(self):
        pass
