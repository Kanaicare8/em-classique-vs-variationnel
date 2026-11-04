"""Extrait le contour du Cameroun de Natural Earth (domaine public) vers data/climat/frontiere/cameroun.shp."""
from pathlib import Path

import geopandas as gpd

dossier = Path(__file__).resolve().parent.parent / "data" / "climat" / "frontiere"
g = gpd.read_file(dossier / "ne_10m_admin_0_countries.shp")
cam = g[g["ADMIN"] == "Cameroon"]
assert len(cam) == 1, len(cam)
cam[["ADMIN", "geometry"]].to_file(dossier / "cameroun.shp")
print("contour du Cameroun écrit :", cam.total_bounds)
