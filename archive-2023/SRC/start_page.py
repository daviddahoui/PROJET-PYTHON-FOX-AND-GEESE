import tkinter as tk
from PIL import Image, ImageTk
from tkinter import messagebox
import json
import os
import pygame.mixer
import sys

class StartPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        # Récupérer le contrôleur (fenêtre principale) pour naviguer entre les pages
        self.controller = controller

        pygame.mixer.init()
        pygame.mixer.music.load(path_to_mp3)
        pygame.mixer.music.play(-1)  # Le -1 signifie que la musique sera jouée en boucle indéfiniment

        background_image = Image.open(path_to_start_page_image)
        resized_background_image = background_image.resize((600, 600))  # Redimensionnez l'image pour qu'elle corresponde à la taille de la fenêtre
        self.background_photo_image = ImageTk.PhotoImage(resized_background_image)  # Convertir l'image PIL en image Tkinter

        # Créer un canvas pour l'image d'arrière-plan et positionner l'image dessus
        background_canvas = tk.Canvas(self, width=600, height=600)
        background_canvas.pack(fill="both", expand=True)
        background_canvas.create_image(0, 0, image=self.background_photo_image, anchor="nw")

        # Centrer le contenu sur la page
        self.pack_propagate(0)
        self.pack(fill='both', expand=True)

        # Création du bouton "Commencer le jeu"
        start_game_button = tk.Button(self, text="    Commencer le jeu    ", bg="#ffed00", fg="black", bd=6, relief="solid", command=lambda: controller.show_frame("PlayerSelectionPage"), font=("Helvetica", 20), height=2, width=15)
        background_canvas.create_window(300, 300, window=start_game_button) 

        # Création du bouton "CHARGER" pour charger une partie sauvegardée
        load_button = tk.Button(self, text="    CHARGER    ", command=self.load_game_state, bd=2, relief="solid", bg="#ffed00", fg="black")
        background_canvas.create_window(300, 400, window=load_button)

        # Création du bouton "SUPPRIMER SAUVEGARDE" pour supprimer une partie sauvegardée
        delete_save_button = tk.Button(self, text="    SUPPRIMER SAUVEGARDE    ", command=self.delete_save, bd=2, relief="solid", bg="#ffed00", fg="black")
        background_canvas.create_window(300, 450, window=delete_save_button)

    def load_game_state(self):
        """Charge l'état du jeu depuis un fichier sauvegardé."""
        print("Tentative de chargement du jeu...")  
        try:
            # Ouvrir et lire le fichier de sauvegarde
            with open('game_save.json', 'r') as file:
                game_data = json.load(file)
                print("Données du jeu chargées:", game_data)

                # Initialiser la page du jeu avec les données chargées
                game_page = self.controller.frames["GamePage"]
                game_page.initialize_game_from_data(game_data)

                # Naviguer vers la page du jeu
                self.controller.show_frame("GamePage")

        except FileNotFoundError:
            print("Aucun jeu sauvegardé trouvé")
            messagebox.showerror("Erreur", "Aucune partie sauvegardée trouvée.")
        except Exception as e:
            print("Erreur lors du chargement du jeu:", str(e))
            messagebox.showerror("Erreur", "Une erreur s'est produite lors du chargement de la partie.")

    def delete_save(self):
        """Supprime la sauvegarde du jeu."""
        try:
            # Supprimer le fichier de sauvegarde
            os.remove('game_save.json')
            messagebox.showinfo("Succès", "Sauvegarde supprimée avec succès.")
        except FileNotFoundError:
            messagebox.showwarning("Avertissement", "Aucune sauvegarde trouvée.")
        except Exception as e:
            print("Erreur lors de la suppression de la sauvegarde:", str(e))
            messagebox.showerror("Erreur", "Une erreur s'est produite lors de la suppression de la sauvegarde.")

def resource_path(relative_path):
    """ Renvoie le chemin d'accès de la ressource, fonctionne pour le dev et pour l'application compilée """
    try:
        base_path = sys._MEIPASS  # Si l'application est compilée, utilise le répertoire temporaire de PyInstaller
    except Exception:
        base_path = os.path.abspath(".")  # Sinon, utilise le répertoire actuel

    return os.path.join(base_path, relative_path)

path_to_mp3 = resource_path("ASSETS/MUSIQUE_ARRIÈRE_PLAN/background.mp3")
path_to_start_page_image = resource_path("ASSETS/IMAGES/image_start_page.png")



