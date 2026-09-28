import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from game_page import FOX
import pygame.mixer
import sys
import os

# Définition de la page de sélection du nombre de joueurs
class PlayerSelectionPage(tk.Frame):
    def __init__(self, parent, controller):
        # Initialisation du parent Frame
        tk.Frame.__init__(self, parent)
        
        # Récupération du contrôleur (main window) pour naviguer entre les pages
        self.controller = controller

        # Initialisation du mixer pour la musique de fond
        pygame.mixer.init()
        # Chargement et lecture de la musique d'arrière-plan
        pygame.mixer.music.load(path_to_mp3)
        pygame.mixer.music.play(-1)  # Jouer en boucle

        # Chargement et redimensionnement de l'image d'arrière-plan
        background_image = Image.open(path_to_game_window_image)
        resized_background_image = background_image.resize((600, 600))
        self.background_photo_image = ImageTk.PhotoImage(resized_background_image)

        # Création d'un canvas pour afficher l'image d'arrière-plan
        background_canvas = tk.Canvas(self, width=600, height=600, bg="black")
        background_canvas.grid(sticky="nsew")
        background_canvas.create_image(0, 0, image=self.background_photo_image, anchor="nw")

        # Configuration de la grille pour centrer le contenu
        self.grid_propagate(0)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Ajout d'un label pour indiquer la sélection du nombre de joueurs
        label = tk.Label(self, text="Choisissez le nombre de joueurs", bg='black', fg='white', font=("Helvetica", 24))
        background_canvas.create_window(300, 150, window=label)

        # Configuration du style des boutons
        style = ttk.Style()
        style.configure("TButton", font=("Helvetica", 20), padding=10, relief="solid", background='black', foreground='black')
        style.map('TButton', foreground=[('active', 'black')], background=[('active', '#ffed00')])

        # Création du bouton pour 1 joueur
        one_player_button = ttk.Button(self, text="1 joueur", style="TButton", command=self.select_one_player)
        background_canvas.create_window(300, 250, window=one_player_button) 

        # Création du bouton pour 2 joueurs
        two_players_button = ttk.Button(self, text="2 joueurs", style="TButton", command=self.select_two_players)
        background_canvas.create_window(300, 350, window=two_players_button) 

    # Fonction pour gérer la sélection d'un seul joueur
    def select_one_player(self):
        self.controller.vs_ai = True
        self.controller.player_count.set(1)
        self.controller.current_player = FOX
        self.controller.ai_mode = True  # Activation du mode IA pour le deuxième joueur
        self.controller.show_frame("AnimalSelectionPage")  # Naviguer vers la page de sélection des animaux

    # Fonction pour gérer la sélection de deux joueurs
    def select_two_players(self):
        self.controller.player_count.set(2)
        self.controller.ai_mode = False  # Désactivation du mode IA car il y a deux joueurs humains
        self.controller.show_frame("AnimalSelectionPage")  # Naviguer vers la page de sélection des animaux

def resource_path(relative_path):
    """ Renvoie le chemin d'accès de la ressource, fonctionne pour le dev et pour l'application compilée """
    try:
        base_path = sys._MEIPASS  # Si l'application est compilée, utilise le répertoire temporaire de PyInstaller
    except Exception:
        base_path = os.path.abspath(".")  # Sinon, utilise le répertoire actuel

    return os.path.join(base_path, relative_path)

path_to_mp3 = resource_path("ASSETS/MUSIQUE_ARRIÈRE_PLAN/background.mp3")
path_to_game_window_image = resource_path("ASSETS/IMAGES/image_fenêtre_jeu.png")