import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import pygame.mixer
import sys
import os

class AnimalSelectionPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        pygame.mixer.init()
        pygame.mixer.music.load(path_to_mp3)
        pygame.mixer.music.play(-1)

        background_image = Image.open(path_to_game_window_image)
        resized_background_image = background_image.resize((600, 600))
        self.background_photo_image = ImageTk.PhotoImage(resized_background_image)

        # Set background color to black
        background_canvas = tk.Canvas(self, width=600, height=600, bg="black")
        background_canvas.grid(sticky="nsew")
        background_canvas.create_image(0, 0, image=self.background_photo_image, anchor="nw")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.controller = controller

        label = tk.Label(self, text="Choisissez le nombre de renards et d'oies", bg='black', fg='white', font=("Helvetica", 24))
        background_canvas.create_window(300, 100, window=label)

        fox_label = tk.Label(self, text="Nombre de renards", bg='black', fg='white', font=("Helvetica", 18))
        background_canvas.create_window(300, 175, window=fox_label)

        # Configure combobox style
        style = ttk.Style()
        style.configure('TCombobox', background='black', foreground='white', fieldbackground='black', font=("Helvetica", 18))
        style.map('TCombobox', fieldbackground=[('readonly', 'black')])

        fox_combobox = ttk.Combobox(self, values=(1, 2), state='readonly')
        fox_combobox.bind("<<ComboboxSelected>>", lambda _: [self.controller.fox_count.set(int(fox_combobox.get())), self.update_goose_values()])
        background_canvas.create_window(300, 215, window=fox_combobox)

        goose_label = tk.Label(self, text="Nombre d'oies", bg='black', fg='white', font=("Helvetica", 18))
        background_canvas.create_window(300, 275, window=goose_label)

        goose_count_combobox = ttk.Combobox(self, values=(13, 15, 17, 20, 27), state='readonly')
        goose_count_combobox.bind("<<ComboboxSelected>>", lambda _: self.controller.goose_count.set(int(goose_count_combobox.get()))) 
        background_canvas.create_window(300, 315, window=goose_count_combobox)

        self.start_game_button = tk.Button(self, text="Commencer le jeu", bd=2, relief="solid", bg="#ffed00", fg="black", command=self.controller.start_game)
        background_canvas.create_window(300, 380, window=self.start_game_button)
        self.start_game_button["state"] = "disabled"

        self.controller.fox_count.trace("w", self.check_start_game_button)
        self.controller.goose_count.trace("w", self.check_start_game_button)

        self.goose_count_combobox = goose_count_combobox

    def update_goose_values(self):
        """Mise à jour des valeurs possibles pour la sélection des oies en fonction du nombre de renards choisi."""
        if self.controller.fox_count.get() == 2:
            self.goose_count_combobox['values'] = (20, 27)
            self.controller.goose_count.set(0)  # Réinitialisez la sélection
        else:
            self.goose_count_combobox['values'] = (13, 15, 17)
            self.controller.goose_count.set(0)  # Réinitialisez la sélection

    def check_start_game_button(self, *args):
        """Vérifier si le bouton de démarrage du jeu doit être activé ou non."""
        fox_count = self.controller.fox_count.get()
        goose_count = self.controller.goose_count.get()
        valid_goose_counts = [13, 15, 17, 20, 27] 

        if fox_count > 0 and goose_count in valid_goose_counts:
            self.start_game_button["state"] = "normal"
        else:
            self.start_game_button["state"] = "disabled"

    def select_foxes(self, event):
        """Sélectionner le nombre de renards en fonction du choix de l'utilisateur."""
        selected_number = int(self.fox_combobox.get())
        self.controller.fox_count.set(selected_number)
        self.check_start_game_button()

    def select_geese(self, event):
        """Sélectionner le nombre d'oies en fonction du choix de l'utilisateur."""
        selected_number = int(self.goose_combobox.get())
        self.controller.goose_count.set(selected_number)
        self.check_start_game_button()

def resource_path(relative_path):
    """ Renvoie le chemin d'accès de la ressource, fonctionne pour le dev et pour l'application compilée """
    try:
        base_path = sys._MEIPASS  # Si l'application est compilée, utilise le répertoire temporaire de PyInstaller
    except Exception:
        base_path = os.path.abspath(".")  # Sinon, utilise le répertoire actuel

    return os.path.join(base_path, relative_path)

path_to_mp3 = resource_path("ASSETS/MUSIQUE_ARRIÈRE_PLAN/background.mp3")
path_to_game_window_image = resource_path("ASSETS/IMAGES/image_fenêtre_jeu.png")