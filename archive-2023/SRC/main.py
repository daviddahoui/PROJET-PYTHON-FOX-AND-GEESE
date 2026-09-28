import tkinter as tk
from tkinter import ttk
from tkinter import IntVar
from start_page import StartPage
from player_selection_page import PlayerSelectionPage
from animal_selection_page import AnimalSelectionPage
from game_page import GamePage

class Game:
    def __init__(self):
        # Initialisation de la fenêtre principale
        self.window = tk.Tk()
        self.window.geometry("600x600")
        self.window.title("Jeu Fox and Geese")
        self.window.resizable(False, False)

        # Dictionnaire pour stocker les frames/pages
        self.frames = {}

        # Conteneur principal pour les frames/pages
        self.container = ttk.Frame(self.window)
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Variables pour stocker les choix de l'utilisateur concernant le nombre de joueurs, de renards et d'oies
        self.player_count = IntVar()
        self.fox_count = IntVar()
        self.goose_count = IntVar()

        # Initialisation et stockage des pages dans le dictionnaire 'frames'
        for GAME in (StartPage, PlayerSelectionPage, AnimalSelectionPage, GamePage):
            frame = GAME(self.container, self) # Création de chaque frame en passant la fenêtre principale en tant que contrôleur
            self.frames[GAME.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Affichage de la page de démarrage par défaut
        self.show_frame("StartPage")

        # Impressions de diagnostic (peuvent être supprimées plus tard)
        print("Adresse de player_count:", id(self.player_count))
        print("Adresse de fox_count:", id(self.fox_count))
        print("Adresse de goose_count:", id(self.goose_count))

    def show_frame(self, cont):
        """Affiche le frame/page spécifié."""
        frame = self.frames[cont]
        frame.tkraise()
        
        # Redessiner le plateau si le frame actuel est GamePage
        if isinstance(frame, GamePage):
            frame.draw_board(frame.background_canvas)

        # Impressions de diagnostic pour GamePage (peuvent être supprimées plus tard)
        if cont == "GamePage":
            print("Diagnostic fox count (GamePage):", self.fox_count.get())
            print("Diagnostic goose count (GamePage):", self.goose_count.get())

    def start_game(self):
        """Démarre une nouvelle partie."""
        # Crée une nouvelle instance de GamePage lorsque le jeu est sur le point de commencer
        game_frame = GamePage(self.container, self)
        self.frames["GamePage"] = game_frame
        game_frame.grid(row=0, column=0, sticky="nsew")
        self.show_frame("GamePage")

    def run(self):
        """Exécute la boucle principale de l'application."""
        self.window.mainloop()

def main():
    """Fonction principale pour initialiser et exécuter le jeu."""
    game = Game()
    game.run()

if __name__ == "__main__":
    main()
