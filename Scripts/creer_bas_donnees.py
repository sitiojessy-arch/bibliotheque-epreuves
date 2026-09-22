import sqlite3
import os

# Chemin vers la base de données
chemin_bdd = os.path.join("..", "base_donnees", "epreuves.db")

# Connexion (crée le fichier s'il n'existe pas)
connexion = sqlite3.connect(chemin_bdd)
curseur = connexion.cursor()

# Création de la table
curseur.execute("""
CREATE TABLE IF NOT EXISTS epreuves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pays TEXT NOT NULL,
    ville TEXT,
    etablissement TEXT,
    classe TEXT NOT NULL,
    serie TEXT,
    matiere TEXT NOT NULL,
    type_epreuve TEXT,
    sequence TEXT,
    annee INTEGER,
    lien_original TEXT,
    emplacement_fichier TEXT NOT NULL,
    date_telechargement TEXT,
    a_corrige INTEGER DEFAULT 0
)
""")

connexion.commit()
connexion.close()

print("Base de données créée avec succès !")