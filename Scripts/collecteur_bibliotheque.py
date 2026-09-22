import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pdfplumber
import re
import os
import time
import sqlite3
from datetime import datetime
import pytesseract
from pdf2image import convert_from_path

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
CHEMIN_POPPLER = r"C:\Users\sitio\poppler\poppler-26.02.0\Library\bin"

BASE_URL = "https://epreuvesetcorriges.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Classes du secondaire à parcourir pour chaque pays (slug du site → nom de dossier)
CLASSES_COLLEGES = {
    "6eme": "6e",
    "5eme": "5e",
    "4eme": "4e",
    "3eme": "3e",
    "seconde": "Seconde",
    "premiere": "Premiere",
    "terminale": "Terminale",
}

# Configuration des 4 pays : slug du site + code(s) d'examen officiel + classe correspondante
PAYS_CONFIG = {
    "Senegal": {"slug": "senegal", "examens": {"bac": "Terminale", "bfem": "3e"}},
    "Guinee":  {"slug": "guinee",  "examens": {"bac": "Terminale", "bepc": "3e"}},
    "Mali":    {"slug": "mali",    "examens": {"bac": "Terminale", "def": "3e"}},
    "Togo":    {"slug": "togo",    "examens": {"bac": "Terminale", "bepc": "3e"}},
}

# ---------- Recherche des documents ----------

def recuperer_liens_documents(url_page):
    reponse = requests.get(url_page, headers=HEADERS)
    soup = BeautifulSoup(reponse.text, "html.parser")
    liens = []
    for lien in soup.find_all("a", href=True):
        href = lien["href"]
        if ("/examens/" in href or "/colleges/" in href) and any(c.isdigit() for c in href.split("/")[-1][:6]):
            titre = lien.get_text(strip=True)
            url_complete = urljoin(BASE_URL, href)
            # Exclure les liens de navigation (sous-catégories), pas de vrais documents
            libelles_navigation = {"6ème", "5ème", "4ème", "3ème", "seconde", "première", "terminale",
                                   "cap", "bts", "cep", "ci", "cp", "ce1", "ce2", "cm1", "cm2",
                                   "1er trimestre - semestre", "2ème trimestre - semestre", "3ème trimestre"}
            if (titre and titre != "Détails"
                    and titre.lower() not in libelles_navigation
                    and len(titre) > 15  # les vrais titres de documents sont longs
                    and url_complete not in [l[1] for l in liens]):
                liens.append((titre, url_complete))
    return liens

def serie_interessante(titre):
    match = re.search(r"[Ss][ée]rie[s]?\s*([A-Za-z0-9\-–]+)", titre)
    if not match:
        return False
    groupe_serie = match.group(1)
    parties = re.split(r"[-–]", groupe_serie)
    lettres = {p[0].upper() for p in parties if p}
    return bool(lettres & {"C", "D", "A"})

def telecharger_pdf(url_page_detail, titre, dossier_destination):
    os.makedirs(dossier_destination, exist_ok=True)
    url_telechargement = url_page_detail.rstrip("/") + "/download"
    reponse = requests.get(url_telechargement, headers=HEADERS)
    if reponse.status_code == 200 and reponse.headers.get("Content-Type", "").startswith("application/pdf"):
        nom_fichier = "".join(c for c in titre if c.isalnum() or c in " -_")[:100] + ".pdf"
        chemin_complet = os.path.join(dossier_destination, nom_fichier)
        with open(chemin_complet, "wb") as f:
            f.write(reponse.content)
        return chemin_complet
    return None

# ---------- Analyse et classement ----------

def extraire_annee(titre):
    match = re.search(r"(20\d{2})", titre)
    return int(match.group(1)) if match else None

def annee_valide(titre):
    annee = extraire_annee(titre)
    return annee is None or annee >= 2021

def extraire_matiere(titre):
    matieres = {
        "Mathematiques": ["mathematiques", "maths"],
        "Physique-Chimie": ["physique-chimie", "physique chimie", "sciences physiques", "physique"],
        "SVT": ["svt", "sciences de la vie", "sciences naturelles"],
        "Francais": ["francais", "français"],
        "Anglais": ["anglais"],
        "Philosophie": ["philosophie"],
        "Histoire-Geographie": ["histoire-geographie", "histoire geographie", "histoire", "geographie"],
        "Espagnol": ["espagnol"],
        "Portugais": ["portugais"],
        "Allemand": ["allemand"],
        "Economie": ["economie", "eco-droit", "economie generale"],
        "Comptabilite": ["comptabilite", "gestion"],
        "Education-Civique": ["education civique", "ecm", "eps"],
        "Informatique": ["informatique", "tic"],
        "Arabe": ["arabe"],
        "Dessin": ["dessin", "arts plastiques"],
    }
    titre_normalise = titre.lower()
    for matiere, mots_cles in matieres.items():
        for mot in mots_cles:
            if mot in titre_normalise:
                return matiere
    return "Autre"

def extraire_matiere_depuis_pdf(chemin_pdf):
    # 1. Essai avec le texte natif du PDF (rapide)
    try:
        with pdfplumber.open(chemin_pdf) as pdf:
            texte = pdf.pages[0].extract_text() or ""
        resultat = extraire_matiere(texte)
        if resultat != "Autre":
            return resultat
    except Exception:
        pass

    # 2. Secours : OCR sur l'image de la première page (pour les scans)
    try:
        images = convert_from_path(chemin_pdf, first_page=1, last_page=1, poppler_path=CHEMIN_POPPLER, dpi=200)
        texte_ocr = pytesseract.image_to_string(images[0], lang="fra")
        return extraire_matiere(texte_ocr)
    except Exception as e:
        print(f"  (OCR échoué : {e})")
        return "Autre"

def extraire_serie(titre):
    match = re.search(r"[Ss][ée]rie[s]?\s*([A-Z][0-9]?(?:[-–][A-Z][0-9]?)*)", titre)
    return match.group(1) if match else None

def extraire_type_epreuve(titre):
    t = titre.lower()
    if "blanc" in t:
        return "Examen blanc"
    elif "bac" in t or "baccalaureat" in t or "baccalauréat" in t or "bfem" in t or "bepc" in t or "def" in t:
        return "Examen officiel"
    elif "corrige" in t or "corrigé" in t:
        return "Corrige"
    return "Autre"

def a_un_corrige(titre):
    return 1 if ("corrige" in titre.lower() or "corrigé" in titre.lower()) else 0

def classer_fichier(chemin_fichier_actuel, titre, pays, classe, est_examen_officiel=False):
    matiere = extraire_matiere(titre)
    if matiere == "Autre":
        matiere = extraire_matiere_depuis_pdf(chemin_fichier_actuel)
    annee = extraire_annee(titre)
    serie = extraire_serie(titre)
    type_epreuve = extraire_type_epreuve(titre)
    corrige = a_un_corrige(titre)

    dossier_matiere = os.path.join("..", "Documents", pays, classe, matiere)

    if est_examen_officiel:
        dossier_destination = os.path.join(dossier_matiere, "Examens")
        os.makedirs(dossier_destination, exist_ok=True)
        prefixe = "Corrige" if corrige else "Examen"
        existants = [f for f in os.listdir(dossier_destination) if f.startswith(prefixe + "_")]
        prochain_numero = len(existants) + 1
        extension = os.path.splitext(chemin_fichier_actuel)[1]
        nom_fichier = f"{prefixe}_{prochain_numero}{extension}"
    else:
        # Les devoirs/séquences sont numérotés automatiquement : Sequence_1, Sequence_2, ...
        os.makedirs(dossier_matiere, exist_ok=True)
        sequences_existantes = [
            d for d in os.listdir(dossier_matiere)
            if os.path.isdir(os.path.join(dossier_matiere, d)) and d.startswith("Sequence_")
        ]
        prochain_numero = len(sequences_existantes) + 1
        dossier_destination = os.path.join(dossier_matiere, f"Sequence_{prochain_numero}")
        os.makedirs(dossier_destination, exist_ok=True)
        extension = os.path.splitext(chemin_fichier_actuel)[1]
        nom_fichier = f"Sequence_{prochain_numero}{extension}"

    nouveau_chemin = os.path.join(dossier_destination, nom_fichier)
    os.replace(chemin_fichier_actuel, nouveau_chemin)

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
    print(f"📁 {pays} | {classe} | {matiere} | {'Examen' if est_examen_officiel else 'Séquence'} | {annee}")

# ---------- Boucle principale ----------

if __name__ == "__main__":
    MAX_DOCS_PAR_CATEGORIE = 6  # limite par catégorie vu le nombre de combinaisons

    chemin_bdd = os.path.join("..", "base_donnees", "epreuves.db")
    conn_reset = sqlite3.connect(chemin_bdd)
    conn_reset.execute("DELETE FROM epreuves")
    conn_reset.commit()
    conn_reset.close()

    for pays, config in PAYS_CONFIG.items():
        slug = config["slug"]

        # 1. Documents de classe (devoirs, séquences, compositions) pour les 7 niveaux
        for slug_classe, nom_classe in CLASSES_COLLEGES.items():
            url_liste = f"{BASE_URL}/categories/{slug}/colleges/{slug_classe}"
            print(f"\n=== {pays} — {nom_classe} ===")
            try:
                liens = recuperer_liens_documents(url_liste)
            except Exception as e:
                print(f"Erreur de connexion pour {url_liste} : {e}")
                continue

            liens_filtres = [(t, h) for t, h in liens if serie_interessante(t) and annee_valide(t)]
            if nom_classe in ["6e", "5e", "4e", "3e"] or not liens_filtres:
                liens_filtres = [(t, h) for t, h in liens if annee_valide(t)]

            print(f"{len(liens_filtres)} documents retenus (sur {len(liens)} trouvés).")
            dossier_temp = os.path.join("..", "Documents", pays)
            for titre, href in liens_filtres[:MAX_DOCS_PAR_CATEGORIE]:
                try:
                    chemin = telecharger_pdf(href, titre, dossier_temp)
                    if chemin:
                        classer_fichier(chemin, titre, pays, nom_classe, est_examen_officiel=False)
                    else:
                        print(f"❌ Échec : {titre}")
                except Exception as e:
                    print(f"Erreur sur '{titre}' : {e}")
                time.sleep(1)

        # 2. Examens officiels (BAC, BFEM/BEPC/DEF)
        for code_examen, nom_classe in config["examens"].items():
            url_liste = f"{BASE_URL}/categories/{slug}/examens/{code_examen}"
            print(f"\n=== {pays} — {code_examen.upper()} (officiel) ===")
            try:
                liens = recuperer_liens_documents(url_liste)
            except Exception as e:
                print(f"Erreur de connexion pour {url_liste} : {e}")
                continue

            liens_filtres = [(t, h) for t, h in liens if serie_interessante(t) and annee_valide(t)]
            if nom_classe == "3e" or not liens_filtres:
                liens_filtres = [(t, h) for t, h in liens if annee_valide(t)]

            print(f"{len(liens_filtres)} documents retenus (sur {len(liens)} trouvés).")
            dossier_temp = os.path.join("..", "Documents", pays)
            for titre, href in liens_filtres[:MAX_DOCS_PAR_CATEGORIE]:
                try:
                    chemin = telecharger_pdf(href, titre, dossier_temp)
                    if chemin:
                        classer_fichier(chemin, titre, pays, nom_classe, est_examen_officiel=True)
                    else:
                        print(f"❌ Échec : {titre}")
                except Exception as e:
                    print(f"Erreur sur '{titre}' : {e}")
                time.sleep(1)

    print("\n✅ Collecte terminée pour les 4 pays, toutes classes du secondaire.")