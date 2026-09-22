import re
import sqlite3
import os
from datetime import datetime

def extraire_annee(titre):
    match = re.search(r"(20\d{2})", titre)
    return int(match.group(1)) if match else None

def extraire_matiere(titre):
    matieres = {
        "Mathematiques": ["mathematiques", "maths"],
        "Physique-Chimie": ["physique-chimie", "physique chimie", "sciences physiques", "physique"],
        "SVT": ["svt", "sciences de la vie"],
        "Francais": ["francais", "français"],
        "Anglais": ["anglais"],
        "Philosophie": ["philosophie"],
        "Histoire-Geographie": ["histoire-geographie", "histoire geographie", "histoire"],
        "Espagnol": ["espagnol"],
        "Portugais": ["portugais"],
    }
    titre_normalise = titre.lower()
    for matiere, mots_cles in matieres.items():
        for mot in mots_cles:
            if mot in titre_normalise:
                return matiere
    return "Autre"

def extraire_serie(titre):
    match = re.search(r"[Ss][ée]rie[s]?\s*([A-Z][0-9]?(?:[-–][A-Z][0-9]?)*)", titre)
    return match.group(1) if match else None

def extraire_type_epreuve(titre):
    titre_normalise = titre.lower()
    if "blanc" in titre_normalise:
        return "Examen blanc"
    elif "bac" in titre_normalise or "baccalaureat" in titre_normalise or "baccalauréat" in titre_normalise:
        return "Examen officiel"
    elif "corrige" in titre_normalise or "corrigé" in titre_normalise:
        return "Corrige"
    else:
        return "Autre"

def a_un_corrige(titre):
    return 1 if ("corrige" in titre.lower() or "corrigé" in titre.lower()) else 0

def classer_fichier(chemin_fichier_actuel, titre, pays="Senegal", classe="Terminale"):
    matiere = extraire_matiere(titre)
    annee = extraire_annee(titre)
    serie = extraire_serie(titre)
    type_epreuve = extraire_type_epreuve(titre)
    corrige = a_un_corrige(titre)

    # Créer le dossier de destination : Documents/Pays/Classe/Matiere/
    dossier_destination = os.path.join("..", "Documents", pays, classe, matiere)
    os.makedirs(dossier_destination, exist_ok=True)

    # Déplacer le fichier
    nom_fichier = os.path.basename(chemin_fichier_actuel)
    nouveau_chemin = os.path.join(dossier_destination, nom_fichier)
    os.replace(chemin_fichier_actuel, nouveau_chemin)

    # Enregistrer en base de données
    chemin_bdd = os.path.join("..", "base_donnees", "epreuves.db")
    connexion = sqlite3.connect(chemin_bdd)
    curseur = connexion.cursor()
    curseur.execute("""
        INSERT INTO epreuves (pays, classe, matiere, type_epreuve, serie, annee,
                               emplacement_fichier, date_telechargement, a_corrige)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (pays, classe, matiere, type_epreuve, serie, annee,
          nouveau_chemin, datetime.now().strftime("%Y-%m-%d"), corrige))
    connexion.commit()
    connexion.close()

    print(f"📁 Classé : {matiere} | Série {serie} | {annee} → {nouveau_chemin}")

if __name__ == "__main__":
    dossier_source = os.path.join("..", "Documents", "Senegal")
    for nom_fichier in os.listdir(dossier_source):
        chemin_complet = os.path.join(dossier_source, nom_fichier)
        if os.path.isfile(chemin_complet) and nom_fichier.endswith(".pdf"):
            titre = nom_fichier.replace(".pdf", "")
            classer_fichier(chemin_complet, titre)