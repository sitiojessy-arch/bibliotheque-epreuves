import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import time

BASE_URL = "https://epreuvesetcorriges.com"

# Page de test : BAC Sénégal, section Mathématiques (Terminale)
URL_LISTE = "https://epreuvesetcorriges.com/categories/senegal/examens/bac"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def recuperer_liens_documents(url_page):
    """Récupère les liens vers les pages de détail des documents sur une page de liste"""
    reponse = requests.get(url_page, headers=HEADERS)
    soup = BeautifulSoup(reponse.text, "html.parser")

    liens = []
    for lien in soup.find_all("a", href=True):
        href = lien["href"]
        # Les pages de documents contiennent "/bac/" suivi d'un numéro
        if "/bac/" in href and any(c.isdigit() for c in href.split("/")[-1][:6]):
            titre = lien.get_text(strip=True)
            url_complete = urljoin(BASE_URL, href)
            if titre and titre != "Détails" and url_complete not in [l[1] for l in liens]:
                liens.append((titre, url_complete))
    return liens

def telecharger_pdf(url_page_detail, titre, dossier_destination):
    """Va sur la page de détail, trouve le lien de téléchargement, et télécharge le PDF"""
    url_telechargement = url_page_detail.rstrip("/") + "/download"

    reponse = requests.get(url_telechargement, headers=HEADERS)
    if reponse.status_code == 200 and reponse.headers.get("Content-Type", "").startswith("application/pdf"):
        nom_fichier = "".join(c for c in titre if c.isalnum() or c in " -_")[:100] + ".pdf"
        chemin_complet = os.path.join(dossier_destination, nom_fichier)
        with open(chemin_complet, "wb") as f:
            f.write(reponse.content)
        print(f"✅ Téléchargé : {nom_fichier}")
        return chemin_complet
    else:
        print(f"❌ Échec pour : {titre} (statut {reponse.status_code})")
        return None

if __name__ == "__main__":
    dossier_test = os.path.join("..", "Documents", "Senegal")
    os.makedirs(dossier_test, exist_ok=True)

    import re


    def serie_interessante(titre):
        """Retourne True si le titre mentionne la série C, D ou A"""
        match = re.search(r"[Ss][ée]rie[s]?\s*([A-Za-z0-9\-–]+)", titre)
        if not match:
            return False
        groupe_serie = match.group(1)
        # On découpe sur les tirets pour capter "S2-D", "L-A", etc.
        parties = re.split(r"[-–]", groupe_serie)
        lettres = {p[0].upper() for p in parties if p}
        return bool(lettres & {"C", "D", "A"})

    print("Recherche des documents...")
    liens = recuperer_liens_documents(URL_LISTE)
    print(f"{len(liens)} documents trouvés sur la page.")

    # On teste avec les 3 premiers seulement pour l'instant
    liens_filtres = [(t, h) for t, h in liens if serie_interessante(t)]
    print(f"{len(liens_filtres)} documents correspondent aux séries C/D/A.")

    for titre, href in liens_filtres[:5]:
        print(f"\nTraitement : {titre}")
        telecharger_pdf(href, titre, dossier_test)
        time.sleep(1)
    