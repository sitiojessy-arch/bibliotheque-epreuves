import sqlite3
import os

chemin_bdd = os.path.join("..", "base_donnees", "epreuves.db")
connexion = sqlite3.connect(chemin_bdd)
curseur = connexion.cursor()

curseur.execute("SELECT COUNT(*) FROM epreuves")
total = curseur.fetchone()[0]
print(f"TOTAL de documents enregistrés : {total}\n")

print("=== Répartition par pays ===")
curseur.execute("SELECT pays, COUNT(*) FROM epreuves GROUP BY pays ORDER BY pays")
for pays, nb in curseur.fetchall():
    print(f"  {pays} : {nb}")

print("\n=== Répartition par pays + classe ===")
curseur.execute("SELECT pays, classe, COUNT(*) FROM epreuves GROUP BY pays, classe ORDER BY pays, classe")
for pays, classe, nb in curseur.fetchall():
    print(f"  {pays} | {classe} : {nb}")

print("\n=== Documents avec corrigé ===")
curseur.execute("SELECT COUNT(*) FROM epreuves WHERE a_corrige = 1")
print(f"  {curseur.fetchone()[0]} sur {total}")

print("\n=== Combinaisons pays/classe sans aucun document ===")
pays_liste = ["Senegal", "Guinee", "Mali", "Togo"]
classes_liste = ["6e", "5e", "4e", "3e", "Seconde", "Premiere", "Terminale"]
curseur.execute("SELECT DISTINCT pays, classe FROM epreuves")
combos_existantes = set(curseur.fetchall())
for pays in pays_liste:
    for classe in classes_liste:
        if (pays, classe) not in combos_existantes:
            print(f"  MANQUANT : {pays} | {classe}")

connexion.close()