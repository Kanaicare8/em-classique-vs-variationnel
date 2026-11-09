"""
Téléchargement et filtrage de la base de prix du PAM (HDX), comme outils/telecharger_prix_wfp.py du mémoire.

Licence : CC BY-IGO ; source à citer : « World Food Programme, Cameroon - Food Prices, Humanitarian Data Exchange ».
"""

from __future__ import annotations

import csv
import hashlib
import io
import time
import urllib.request

URL = ("https://data.humdata.org/dataset/f6ed9f06-36b9-43b2-97f3-fc0b8e16d155/resource/"
       "9deec824-1e42-4a91-b704-b73fd250ec5a/download/wfp_food_prices_cmr.csv")
COLONNES = ("date", "admin1", "admin2", "market", "market_id", "latitude", "longitude", "commodity", "unit", "price")
AGENT = "outil-prix-cameroun/1.0"


def telecharger(url: str = URL, essais: int = 3) -> bytes:
    derniere = None
    for i in range(1, essais + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": AGENT}), timeout=120) as r:
                return r.read()
        except OSError as ex:
            derniere = ex
            time.sleep(5 * i)
    raise RuntimeError(f"téléchargement HDX impossible : {derniere}")


def extraire(brut: bytes, panier) -> tuple[bytes, dict]:
    """Fichier complet du PAM -> (extrait au format du mémoire, description). Accepte aussi un extrait déjà filtré."""
    lignes = [l for l in csv.DictReader(io.StringIO(brut.decode("utf-8-sig"))) if not l["date"].startswith("#")]
    complet = "pricetype" in (lignes[0] if lignes else {})
    garde = [l for l in lignes if l["commodity"] in panier and l.get("unit", "KG") == "KG"
             and (not complet or (l["pricetype"] == "Retail" and l["currency"] == "XAF"))]
    if not garde:
        raise ValueError("aucun relevé de détail en XAF/kg pour les denrées du panier dans ce fichier")
    garde.sort(key=lambda l: (l["market"], l["commodity"], l["date"]))
    sortie = io.StringIO(newline="")
    w = csv.writer(sortie, lineterminator="\n")
    w.writerow(COLONNES)
    for l in garde:
        w.writerow([l.get(c, "") for c in COLONNES])
    extrait = sortie.getvalue().encode("utf-8")
    dates = [l["date"] for l in garde]
    return extrait, {"sha256": hashlib.sha256(extrait).hexdigest(), "lignes": len(garde),
                     "debut": min(dates)[:7], "fin": max(dates)[:7], "sha256_source": hashlib.sha256(brut).hexdigest()}
