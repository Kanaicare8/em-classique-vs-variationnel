"""
Télécharge les prix alimentaires du Cameroun (base de prix du PAM / WFP, diffusée sur HDX) et écrit l'extrait du mémoire.

  data/prix/brut/wfp_food_prices_cmr.csv   fichier complet (non versionné ; HDX le remplace chaque mois)
  data/prix/wfp_cmr_panier.csv             extrait versionné : prix de DÉTAIL, en XAF par kg, des trois denrées du panier
  data/prix/PROVENANCE.txt                 URL, date, empreintes SHA-256 du fichier complet et de l'extrait

Licence : Creative Commons Attribution for Intergovernmental Organisations (CC BY-IGO) ; source à citer :
« World Food Programme, Cameroon - Food Prices, Humanitarian Data Exchange ». Redistribution autorisée avec attribution.
L'empreinte de l'extrait est figée dans donnees.SHA256_PRIX : un nouveau téléchargement (nouvelle version HDX) ne
change pas les résultats du mémoire tant que cette constante n'est pas mise à jour délibérément.
"""
import csv
import hashlib
import io
import sys
import time
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
from emvb import donnees as DO  # noqa: E402

URL = ("https://data.humdata.org/dataset/f6ed9f06-36b9-43b2-97f3-fc0b8e16d155/resource/"
       "9deec824-1e42-4a91-b704-b73fd250ec5a/download/wfp_food_prices_cmr.csv")
COLONNES = ("date", "admin1", "admin2", "market", "market_id", "latitude", "longitude", "commodity", "unit", "price")

def telecharger(url, essais=5):
    """Lecture par blocs avec relances (le serveur HDX coupe parfois les transferts longs)."""
    for i in range(1, essais + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=120) as r:
                morceaux = []
                while True:
                    b = r.read(1 << 16)
                    if not b:
                        return b"".join(morceaux)
                    morceaux.append(b)
        except OSError as ex:
            print(f"essai {i}/{essais} échoué : {ex}")
            time.sleep(10 * i)
    raise SystemExit("téléchargement impossible : télécharger le fichier à la main puis --fichier <chemin>")


dossier = RACINE / "data" / "prix"
(dossier / "brut").mkdir(parents=True, exist_ok=True)
# --fichier <chemin> : fichier complet déjà téléchargé depuis l'URL ci-dessus (même traitement, même provenance)
brut = Path(sys.argv[sys.argv.index("--fichier") + 1]).read_bytes() if "--fichier" in sys.argv else telecharger(URL)
(dossier / "brut" / "wfp_food_prices_cmr.csv").write_bytes(brut)
lignes = [l for l in csv.DictReader(io.StringIO(brut.decode("utf-8"))) if not l["date"].startswith("#")]
garde = [l for l in lignes if l["pricetype"] == "Retail" and l["currency"] == "XAF" and l["unit"] == "KG"
         and l["commodity"] in DO.PANIER_PRIX]
garde.sort(key=lambda l: (l["market"], l["commodity"], l["date"]))
sortie = io.StringIO(newline="")
w = csv.writer(sortie, lineterminator="\n")
w.writerow(COLONNES)
for l in garde:
    w.writerow([l[c] for c in COLONNES])
extrait = sortie.getvalue().encode("utf-8")
(dossier / "wfp_cmr_panier.csv").write_bytes(extrait)
(dossier / "PROVENANCE.txt").write_text(
    f"url : {URL}\ntéléchargé le : {time.strftime('%Y-%m-%d')}\n"
    f"sha256 fichier complet : {hashlib.sha256(brut).hexdigest()}\n"
    f"sha256 extrait (wfp_cmr_panier.csv) : {hashlib.sha256(extrait).hexdigest()}\n"
    f"lignes du fichier complet : {len(lignes)} ; lignes de l'extrait : {len(garde)}\n"
    f"période : {min(l['date'] for l in lignes)} à {max(l['date'] for l in lignes)}\n"
    "licence : CC BY-IGO ; source : World Food Programme, Cameroon - Food Prices, Humanitarian Data Exchange\n",
    encoding="utf-8")
print(f"extrait écrit : {len(garde)} lignes ; sha256 {hashlib.sha256(extrait).hexdigest()}")
