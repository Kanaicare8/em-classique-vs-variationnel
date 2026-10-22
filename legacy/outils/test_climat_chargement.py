"""Vérifie le chargement des données climatiques (N, D, références) avant le calcul long."""
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
import torch

import cas_pratique_climat as CC

d = R / "data" / "climat"
X, km, refs, (lon, lat) = CC.charger(False, str(d / "frontiere" / "cameroun.shp"), str(d / "koppen" / "Beck_KG_V1_present_0p0083.tif"), None)
print("N, D =", tuple(X.shape), "| NaN :", int(torch.isnan(X).sum()))
print("classes Köppen (effectifs) :", torch.bincount(refs["koppen"]).tolist())
print("moyennes :", [round(float(v), 2) for v in X.mean(0)])
