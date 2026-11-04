"""
Télécharge les cinq zones agro-écologiques officielles du Cameroun (IRAD 2005) vers data/climat/zae/zae_irad.geojson.

Source : Ministère de la Recherche Scientifique et de l'Innovation, Institut de Recherche Agricole pour le
Développement (IRAD), 2005, diffusé par la FAO (portail GAEZ, « Zones Agroecologiques de Cameroun »,
élément e35781b50b8c4dccb8f4b18dbb6b0d5f). Licence non précisée par la FAO : usage académique, citer la source,
ne pas redistribuer le fichier sans accord. Une provenance (URL, date, SHA-256) est écrite à côté du fichier.
"""
import hashlib
import json
import time
import urllib.request
from pathlib import Path

URL = ("https://services5.arcgis.com/sjP4Ugu5s0dZWLjd/arcgis/rest/services/Zones_Agroecologiques_de_Cameroun/"
       "FeatureServer/0/query?where=1%3D1&outFields=AEZ&outSR=4326&f=geojson")
dossier = Path(__file__).resolve().parent.parent / "data" / "climat" / "zae"
dossier.mkdir(parents=True, exist_ok=True)
brut = urllib.request.urlopen(URL, timeout=120).read()
g = json.loads(brut)
noms = [f["properties"]["AEZ"] for f in g["features"]]
assert len(noms) == 5, noms
(dossier / "zae_irad.geojson").write_bytes(brut)
(dossier / "zae_irad.PROVENANCE.txt").write_text(
    f"url : {URL}\ntéléchargé le : {time.strftime('%Y-%m-%d')}\nsha256 : {hashlib.sha256(brut).hexdigest()}\n"
    f"zones : {' | '.join(noms)}\nsource : IRAD (2005), diffusion FAO GAEZ\n", encoding="utf-8")
print("zones agro-écologiques écrites :", noms)
