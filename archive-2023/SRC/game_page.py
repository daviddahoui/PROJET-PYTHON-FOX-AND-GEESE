import tkinter as tk
from PIL import Image, ImageTk
from tkinter import messagebox
import json
import pygame.mixer
import random
import sys
import os

# Constantes pour représenter le contenu du plateau
INVALID = 0  # Zone non jouable du plateau
FOX = 1      # Position d'un renard sur le plateau
GOOSE = 2    # Position d'une oie sur le plateau
EMPTY = 3    # Case vide sur le plateau

class GamePage(tk.Frame):
    # Ces tableaux définissent les configurations de départ du plateau selon le nombre de renards et d'oies.
    # Chaque tableau est une liste de listes, représentant les lignes du plateau.
    # Chaque élément de la liste interne représente le contenu d'une case.
    
    # Configuration avec 1 renard et 13 oies
    BOARD_1_13 = [
        [INVALID, INVALID, EMPTY, EMPTY, EMPTY, INVALID, INVALID],
        [INVALID, INVALID, EMPTY, EMPTY, EMPTY, INVALID, INVALID],
        [EMPTY, EMPTY, EMPTY, FOX, EMPTY, EMPTY, EMPTY],
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY],
        [GOOSE, GOOSE, GOOSE, GOOSE, GOOSE, GOOSE, GOOSE],
        [INVALID, INVALID, GOOSE, GOOSE, GOOSE, INVALID, INVALID],
        [INVALID, INVALID, GOOSE, GOOSE, GOOSE, INVALID, INVALID]
    ]
    # Configuration avec 1 renard et 15 oies
    BOARD_1_15 = [
        [INVALID, INVALID, EMPTY, EMPTY, EMPTY, INVALID, INVALID],
        [INVALID, INVALID, EMPTY, EMPTY, EMPTY, INVALID, INVALID],
        [EMPTY, EMPTY, EMPTY, FOX, EMPTY, EMPTY, EMPTY],
        [GOOSE, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, GOOSE],
        [GOOSE, GOOSE, GOOSE, GOOSE, GOOSE, GOOSE, GOOSE],
        [INVALID, INVALID, GOOSE, GOOSE, GOOSE, INVALID, INVALID],
        [INVALID, INVALID, GOOSE, GOOSE, GOOSE, INVALID, INVALID]
    ]
    # Configuration avec 1 renard et 17 oies
    BOARD_1_17 = [
        [INVALID, INVALID, EMPTY, EMPTY, EMPTY, INVALID, INVALID],
        [INVALID, INVALID, EMPTY, EMPTY, EMPTY, INVALID, INVALID],
        [GOOSE, EMPTY, EMPTY, FOX, EMPTY, EMPTY, GOOSE],
        [GOOSE, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, GOOSE],
        [GOOSE, GOOSE, GOOSE, GOOSE, GOOSE, GOOSE, GOOSE],
        [INVALID, INVALID, GOOSE, GOOSE, GOOSE, INVALID, INVALID],
        [INVALID, INVALID, GOOSE, GOOSE, GOOSE, INVALID, INVALID]
    ]
    # Configuration avec 2 renard et 20 oies
    BOARD_2_20 = [
        [INVALID, INVALID, EMPTY, EMPTY, EMPTY, INVALID, INVALID],
        [INVALID, INVALID, FOX, EMPTY, FOX, INVALID, INVALID],
        [EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY],
        [GOOSE, GOOSE, GOOSE, GOOSE, GOOSE, GOOSE, GOOSE],
        [GOOSE, GOOSE, GOOSE, GOOSE, GOOSE, GOOSE, GOOSE],
        [INVALID, INVALID, GOOSE, GOOSE, GOOSE, INVALID, INVALID],
        [INVALID, INVALID, GOOSE, GOOSE, GOOSE, INVALID, INVALID]
    ]
    # Configuration avec 2 renard et 27 oies
    BOARD_2_27 = [
        [INVALID, INVALID, FOX, EMPTY, FOX, INVALID, INVALID],
        [INVALID, INVALID, EMPTY, EMPTY, EMPTY, INVALID, INVALID],
        [GOOSE, GOOSE, GOOSE, GOOSE, GOOSE, GOOSE, GOOSE],
        [GOOSE, GOOSE, GOOSE, GOOSE, GOOSE, GOOSE, GOOSE],
        [GOOSE, GOOSE, GOOSE, GOOSE, GOOSE, GOOSE, GOOSE],
        [INVALID, INVALID, GOOSE, GOOSE, GOOSE, INVALID, INVALID],
        [INVALID, INVALID, GOOSE, GOOSE, GOOSE, INVALID, INVALID]
    ]

    def __init__(self, parent, controller):
        """Initialise la page du jeu."""
        tk.Frame.__init__(self, parent)
        self.controller = controller
        
        # Initialisation du mixer pour la musique
        pygame.mixer.init()
        pygame.mixer.music.load(path_to_mp3)
        pygame.mixer.music.play(-1)  # Joue la musique en boucle

        # Détermine si le jeu est contre l'IA en fonction de la sélection du joueur
        self.vs_ai = self.controller.vs_ai if hasattr(self.controller, 'vs_ai') else False

        # Initialisation du canvas
        self.background_canvas = tk.Canvas(self, width=600, height=600, bg="lightgrey")
        self.background_canvas.grid(sticky="nsew")

        # Définir le compte des renards et oies AVANT de dessiner le plateau
        self.fox_count = self.controller.fox_count
        self.goose_count = self.controller.goose_count

        # Le renard commence le jeu
        self.current_player = FOX

        # Sélection du plateau approprié en fonction de la sélection de l'utilisateur
        if self.controller.fox_count.get() == 1 and self.controller.goose_count.get() == 13:
            print("Choosing BOARD_1_13")
            self.board = self.BOARD_1_13
        elif self.controller.fox_count.get() == 1 and self.controller.goose_count.get() == 15:
            print("Choosing BOARD_1_15")
            self.board = self.BOARD_1_15
        elif self.controller.fox_count.get() == 1 and self.controller.goose_count.get() == 17:
            print("Choosing BOARD_1_17")
            self.board = self.BOARD_1_17
        elif self.controller.fox_count.get() == 2 and self.controller.goose_count.get() == 20:
            print("Choosing BOARD_2_20")
            self.board = self.BOARD_2_20
        elif self.controller.fox_count.get() == 2 and self.controller.goose_count.get() == 27:
            print("Choosing BOARD_2_27")
            self.board = self.BOARD_2_27
        else:
            # Tableau par défaut (peut être n'importe lequel, ou un nouveau, ou un message d'erreur)
            print(f"Choosing default board (BOARD_1_13). Fox count: {self.controller.fox_count.get()}, Goose count: {self.controller.goose_count.get()}")
            self.board = self.BOARD_1_13

        # Initialisation des variables du jeu
        self.timer_running = True  # Indicateur pour savoir si le timer est en marche
        self.seconds_elapsed = 0  # Compteur de secondes écoulées depuis le début du jeu
        self.caught_geese = 0  # Nombre d'oies attrapées

        # Création du canvas (zone de dessin) pour le jeu
        self.background_canvas = tk.Canvas(self, width=600, height=600, bg="lightgrey")
        self.background_canvas.grid(sticky="nsew")  # Positionner le canvas

        # Charger l'image de fond
        original_image = Image.open(path_to_game_window_image)

        resized_image = original_image.resize((600, 600), Image.ANTIALIAS)
        self.bg_image = ImageTk.PhotoImage(resized_image)
        # Dessiner l'image de fond sur le canvas
        self.background_canvas.create_image(0, 0, image=self.bg_image, anchor=tk.NW)

        # Dessin du plateau de jeu sur le canvas
        self.draw_board(self.background_canvas)

        # Associer un événement de clic à la fonction on_canvas_click
        self.background_canvas.bind("<Button-1>", self.on_canvas_click)

        # Configurer les lignes et colonnes pour le redimensionnement
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Création des boutons et labels

        # Bouton pour retourner à la page de démarrage
        back_button = tk.Button(self, text="Nouvelle Partie", bd=2, relief="solid", bg="#ffed00", fg="black", command=lambda: controller.show_frame("StartPage"))
        self.background_canvas.create_window(300, 550, window=back_button)

        # Bouton pour mettre le jeu en pause
        pause_button = tk.Button(self, text="Pause", command=self.pause_game, bd=2, relief="solid", bg="#ffed00", fg="black")
        self.background_canvas.create_window(300, 500, window=pause_button)

        # Label pour afficher le temps écoulé
        self.timer_label = tk.Label(self, text="Temps écoulé: 0 secondes")
        self.background_canvas.create_window(300, 50, window=self.timer_label)

        # Label pour afficher le nombre d'oies attrapées
        self.caught_geese_label = tk.Label(self, text="Oies attrapées: 0")
        self.background_canvas.create_window(300, 90, window=self.caught_geese_label)

        # Bouton pour sauvegarder l'état actuel du jeu
        save_button = tk.Button(self, text="SAUVEGARDER", command=self.save_game_state, bd=2, relief="solid", bg="#ffed00", fg="black")
        self.background_canvas.create_window(100, 500, window=save_button)

        # Bouton pour quitter le jeu
        quit_button = tk.Button(self, text="QUITTER", command=self.quit_game, bd=2, relief="solid", bg="#ffed00", fg="black")
        self.background_canvas.create_window(500, 500, window=quit_button)  # Vous pouvez ajuster les coordonnées pour positionner le bouton à l'endroit souhaité.

        # Démarrage du timer du jeu
        self.update_timer()

    def on_canvas_click(self, event):
        # Convertit les coordonnées du clic en lignes et colonnes de la grille
        col = (event.x - 125) // 50
        row = (event.y - 125) // 50

        # Vérifie si le clic est dans les limites de la grille
        if 0 <= row < 7 and 0 <= col < 7:
            if hasattr(self, "selected_piece"):
                # Récupère les mouvements possibles pour la pièce sélectionnée
                moves = self.get_possible_moves(*self.selected_piece)
                
                # Vérifie si le mouvement est valide
                if (row, col) in moves:
                    # Déplace la pièce
                    self.move_piece(row, col)
                    # Vérifie si un joueur a gagné
                    self.check_victory()
                # Désélectionne toutes les pièces
                self.deselect_all()
            # Si aucune pièce n'est sélectionnée et que la pièce sur la case cliquée appartient au joueur actuel, la sélectionne
            elif self.board[row][col] == self.current_player:
                self.select_piece(row, col)

    def select_piece(self, i, j):
        # Désélectionne toutes les pièces
        self.deselect_all()
        
        # Sélectionne la pièce actuelle
        self.selected_piece = (i, j)
        
        # Dessine un rectangle vert autour de la pièce sélectionnée
        self.background_canvas.create_rectangle(125 + j*50, 125 + i*50, 175 + j*50, 175 + i*50, outline='green', width=2, tags="selection")
        
        # Dessine des rectangles jaunes autour des mouvements possibles
        for move_i, move_j in self.get_possible_moves(i, j):
            self.background_canvas.create_rectangle(125 + move_j*50, 125 + move_i*50, 175 + move_j*50, 175 + move_i*50, outline='yellow', width=2, tags="selection")

    def deselect_all(self):
        # Supprime la pièce sélectionnée (si elle existe)
        if hasattr(self, "selected_piece"):
            del self.selected_piece
        
        # Efface les rectangles de sélection sans redessiner tout le plateau
        self.background_canvas.delete("selection")

    def get_possible_moves(self, i, j):
        piece = self.board[i][j]
        moves = []

        # Directions de mouvement pour l'oie et le renard
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1), (1, 0), (0, 1), (-1, 0), (0, -1)]

        if piece == FOX:
            # Boucle pour vérifier les mouvements possibles du renard
            for di, dj in directions:
                # Vérifie que le mouvement ne sort pas du plateau et que la case est vide
                if 0 <= i+di < 7 and 0 <= j+dj < 7 and self.board[i+di][j+dj] == EMPTY:
                    moves.append((i+di, j+dj))
                # Vérification de la capture : si une oie est adjacente et que la case derrière elle est vide
                if 0 <= i+2*di < 7 and 0 <= j+2*dj < 7 and self.board[i+di][j+dj] == GOOSE and self.board[i+2*di][j+2*dj] == EMPTY:
                    moves.append((i+2*di, j+2*dj))

        elif piece == GOOSE:
            # L'oie peut seulement se déplacer vers l'avant (haut) et horizontalement
            forward_and_horizontal_moves = [(-1, 0), (0, 1), (0, -1)]
            for di, dj in forward_and_horizontal_moves:
                # Vérifie que le mouvement ne sort pas du plateau et que la case est vide
                if 0 <= i+di < 7 and 0 <= j+dj < 7 and self.board[i+di][j+dj] == EMPTY:
                    moves.append((i+di, j+dj))

        return moves

    def switch_turn(self):
        """Change le tour du joueur actuel."""
        self.current_player = GOOSE if self.current_player == FOX else FOX

    def move_piece(self, i, j):
        # Vérifie si une pièce a été préalablement sélectionnée
        if hasattr(self, "selected_piece"):
            old_i, old_j = self.selected_piece
            piece = self.board[old_i][old_j]

            # Suivi pour vérifier si une capture a été effectuée
            captured = False

            # Vérifie si le renard peut capturer une oie
            if piece == FOX and abs(i - old_i) in [2, 0] and abs(j - old_j) in [2, 0]:
                mid_i, mid_j = (i + old_i) // 2, (j + old_j) // 2
                if self.board[mid_i][mid_j] == GOOSE:
                    # Capture de l'oie
                    self.board[mid_i][mid_j] = EMPTY
                    self.update_square(mid_i, mid_j)  # Met à jour le carré de l'oie capturée

                    # Mise à jour du compteur des oies capturées
                    self.catch_goose()

                    # Indication qu'une capture a été réalisée
                    captured = True

            # Effectue le déplacement de la pièce
            self.board[i][j], self.board[old_i][old_j] = piece, EMPTY
            self.update_square(old_i, old_j)  # Met à jour le carré précédemment occupé par la pièce
            self.update_square(i, j)  # Met à jour le carré maintenant occupé par la pièce

            # Vérifie si le renard a atteint la dernière rangée
            if self.board[i][j] == FOX and i == 6:
                game_result = self.check_victory()
                if game_result:
                    # Affiche un message si le jeu est terminé
                    self.display_end_game_message(game_result)
                    return

            # Vérifie si le renard peut effectuer une autre capture
            if not captured or not any((new_i, new_j) for new_i, new_j in self.get_possible_moves(i, j) if abs(i - new_i) in [2, 0] and abs(j - new_j) in [2, 0]):
                # Si le renard ne peut pas effectuer une autre capture, change de tour
                self.switch_turn()
            elif captured:
                # Vérifie si une autre capture est possible à partir de la nouvelle position
                possible_captures = [(new_i, new_j) for new_i, new_j in self.get_possible_moves(i, j) if abs(i - new_i) in [2, 0] and abs(j - new_j) in [2, 0]]
                if possible_captures:
                    # Affiche un rappel après 5 secondes si une autre capture est possible
                    self.after(5000, self.show_capture_reminder)

        # Si le jeu est contre une IA et que c'est le tour de l'oie, attend 1 seconde puis effectue le mouvement de l'IA
        if self.vs_ai and self.current_player == GOOSE:
            self.after(1000, self.delayed_ai_move)

        # Désélectionne toutes les pièces
        self.deselect_all()

    def delayed_ai_move(self):
        """Effectue le mouvement de l'IA après un délai."""
        self.ai_move()

    def show_capture_reminder(self):
        # Crée un label pour rappeler au joueur qu'une capture est possible
        reminder_label = tk.Label(self, text="Capture possible!", bg="lightgrey", font=("Arial", 16))
        self.background_canvas.create_window(300, 450, window=reminder_label)
        # Le rappel disparaît après 2 secondes
        self.after(2000, lambda: reminder_label.destroy())

    def update_square(self, i, j):
        # Détermine les coordonnées de la case
        top_left_x = 125 + j * 50
        top_left_y = 125 + i * 50
        bottom_right_x = top_left_x + 50
        bottom_right_y = top_left_y + 50

        # Supprime le contenu actuel de la case
        self.background_canvas.create_rectangle(top_left_x, top_left_y, bottom_right_x, bottom_right_y, fill="lightgrey", outline="black")

        # Dessine le nouvel état de la case
        if self.board[i][j] != INVALID:
            self.background_canvas.create_rectangle(top_left_x, top_left_y, bottom_right_x, bottom_right_y)
            if self.board[i][j] == FOX:
                # Dessine un renard
                self.background_canvas.create_oval(top_left_x + 10, top_left_y + 10, bottom_right_x - 10, bottom_right_y - 10, fill='orange')
            elif self.board[i][j] == GOOSE:
                # Dessine une oie
                self.background_canvas.create_oval(top_left_x + 10, top_left_y + 10, bottom_right_x - 10, bottom_right_y - 10, fill='white')

    def check_victory(self):
        # Obtenir les positions des renards et des oies
        fox_positions = [(i, j) for i in range(7) for j in range(7) if self.board[i][j] == FOX]
        goose_positions = [(i, j) for i in range(7) for j in range(7) if self.board[i][j] == GOOSE]

        # Calculer le nombre de mouvements possibles pour les renards et les oies
        fox_moves = sum([len(self.get_possible_moves(i, j)) for i, j in fox_positions])
        goose_moves = sum([len(self.get_possible_moves(i, j)) for i, j in goose_positions])

        # Conditions de victoire
        if fox_moves == 0:
            # Si les renards n'ont aucun mouvement, les oies gagnent
            messagebox.showinfo("Fin de la partie", "Les oies gagnent !")
            return
        elif any(i == 6 for i, _ in fox_positions):
            # Si un renard atteint la dernière ligne, il gagne
            messagebox.showinfo("Fin de la partie", "Le renard gagne !")
            return
        elif len(goose_positions) <= 3:
            # Si seulement 3 oies (ou moins) restent, le renard gagne
            messagebox.showinfo("Fin de la partie", "Le renard gagne !")
            return
        elif goose_moves == 0:
            # Si les oies n'ont aucun mouvement possible, le renard gagne
            messagebox.showinfo("Fin de la partie", "Le renard gagne !")
            return
        else:
            # Sinon, le jeu continue
            return None

    def draw_board(self, canvas):
        # Parcourir chaque case du plateau
        for i in range(7):
            for j in range(7):
                # Calculer les coordonnées du coin supérieur gauche et du coin inférieur droit pour la case
                top_left_x = 125 + j * 50
                top_left_y = 125 + i * 50
                bottom_right_x = top_left_x + 50
                bottom_right_y = top_left_y + 50
                
                # Vérifier si la case est valide (ni renard, ni oie, ni case invalide)
                if self.board[i][j] != INVALID:
                    # Dessiner la case
                    canvas.create_rectangle(top_left_x, top_left_y, bottom_right_x, bottom_right_y)
                    
                    # Si la case contient un renard, dessiner le renard
                    if self.board[i][j] == FOX:
                        canvas.create_oval(top_left_x + 10, top_left_y + 10, bottom_right_x - 10, bottom_right_y - 10, fill='orange')
                    
                    # Si la case contient une oie, dessiner l'oie
                    elif self.board[i][j] == GOOSE:
                        canvas.create_oval(top_left_x + 10, top_left_y + 10, bottom_right_x - 10, bottom_right_y - 10, fill='white')

        # Dessiner les lignes qui traversent le milieu du plateau
        for i in range(5):  # Pour les 5 cases du milieu
            # Calculer les coordonnées de départ et d'arrivée pour les lignes verticales et horizontales
            start_x = 225 + i * 50
            start_y = 225
            end_x = start_x
            end_y = 375
            
            # Dessiner la ligne verticale
            canvas.create_line(start_x, start_y, end_x, end_y)  
            
            # Dessiner la ligne horizontale
            canvas.create_line(start_y, start_x, end_y, end_x)  

        # Forcer une mise à jour immédiate du canvas pour afficher les changements
        canvas.update_idletasks()

    def update_timer(self):
        # Si le chronomètre est en marche
        if self.timer_running:  
            # Augmenter le temps écoulé d'une seconde
            self.seconds_elapsed += 1  
            # Mettre à jour l'affichage du chronomètre
            self.timer_label.config(text=f"Temps écoulé: {self.seconds_elapsed} secondes")
            # Appeler cette fonction après 1 seconde pour continuer à mettre à jour le temps
            self.after(1000, self.update_timer)

    def pause_game(self):
        # Inverser l'état du chronomètre (si en marche -> arrêté, si arrêté -> en marche)
        self.timer_running = not self.timer_running  
        # Si le chronomètre est en marche, le mettre à jour
        if self.timer_running:  
            self.update_timer()

    def catch_goose(self):
        # Augmenter le nombre d'oies attrapées
        self.caught_geese += 1
        # Mettre à jour le label des oies attrapées
        self.caught_geese_label.config(text=f"Oies attrapées: {self.caught_geese}")

    def start_game(self):
        # Afficher la page du jeu
        self.controller.show_frame("GamePage")
        game_page = self.controller.frames["GamePage"]
        # Dessiner le plateau
        game_page.draw_board(game_page.canvas)

    def set_game_state(self, game_data):
        # Charger les données du jeu à partir des données fournies
        self.board = game_data['board']
        self.current_player = game_data['current_player']
        self.seconds_elapsed = game_data['seconds_elapsed']
        self.caught_foxes = game_data['caught_foxes']
        self.caught_geese = game_data['caught_geese']
        # Mettre à jour le plateau et d'autres éléments de l'interface
        self.draw_board(self.background_canvas)

    def save_game_state(self):
        # Créer un dictionnaire pour stocker les données actuelles du jeu
        game_data = {
            'board': self.board,
            'seconds_elapsed': self.seconds_elapsed,
            'caught_geese': self.caught_geese,
            'current_player': self.current_player
        }
        # Sauvegarder le jeu dans un fichier JSON
        with open('game_save.json', 'w') as file:
            json.dump(game_data, file)
        
        # Afficher une animation pour indiquer que le jeu est sauvegardé
        self.show_save_animation()

    def show_save_animation(self):
        # Créer un label pour afficher le message de sauvegarde
        save_label = tk.Label(self, text="SAUVEGARDE EN COURS...", bg="lightgrey", font=("Arial", 16))
        # Positionner le label sur le canvas
        self.background_canvas.create_window(300, 450, window=save_label)
        # Supprimer le label après 2 secondes
        self.after(2000, lambda: save_label.destroy())

    def initialize_game_from_data(self, game_data):
        # Initialiser le jeu avec les données fournies
        self.board = game_data['board']
        self.seconds_elapsed = game_data['seconds_elapsed']
        self.caught_geese = game_data['caught_geese']
        self.current_player = game_data['current_player']
        # Redessiner le plateau
        self.draw_board(self.background_canvas)
        # Mettre à jour d'autres éléments de l'interface utilisateur
        self.timer_label.config(text=f"Temps écoulé: {self.seconds_elapsed} secondes")
        self.caught_geese_label.config(text=f"Oies attrapées: {self.caught_geese}")

    def quit_game(self):
        # Quitter le jeu et arrêter la musique
        self.controller.window.destroy()
        pygame.mixer.music.stop()

    def ai_move(self):
        # Obtenir tous les mouvements possibles pour les oies et en sélectionner un au hasard
        goose_positions = [(i, j) for i in range(7) for j in range(7) if self.board[i][j] == GOOSE]
        random.shuffle(goose_positions)  # Mélanger pour randomiser l'ordre de traitement des oies

        # Pour chaque oie, obtenir les mouvements possibles
        for goose_i, goose_j in goose_positions:
            possible_moves = self.get_possible_moves(goose_i, goose_j)
            if possible_moves:
                move_i, move_j = random.choice(possible_moves)
                # Déplacer l'oie et mettre à jour le plateau
                self.board[move_i][move_j], self.board[goose_i][goose_j] = GOOSE, EMPTY
                self.update_square(goose_i, goose_j)
                self.update_square(move_i, move_j)
                break  # Effectuer un seul mouvement pour une oie puis quitter la boucle

        # Changer de tour vers le renard après le déplacement de l'IA (OIE)
        self.current_player = FOX

def resource_path(relative_path):
    """ Renvoie le chemin d'accès de la ressource, fonctionne pour le dev et pour l'application compilée """
    try:
        base_path = sys._MEIPASS  # Si l'application est compilée, utilise le répertoire temporaire de PyInstaller
    except Exception:
        base_path = os.path.abspath(".")  # Sinon, utilise le répertoire actuel

    return os.path.join(base_path, relative_path) 

path_to_mp3 = resource_path("ASSETS/MUSIQUE_ARRIÈRE_PLAN/background.mp3")
path_to_game_window_image = resource_path("ASSETS/IMAGES/image_fenêtre_jeu.png")
