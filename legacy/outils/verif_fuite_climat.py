"""Vérifie, pour chaque effectif, si l'évaluation « hors bloc » du cas climatique est réellement hors échantillon."""
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
import torch

import algorithmes as A
import cas_pratique_climat as CC
import comparaison as C

d = R / "data" / "climat"
X, km, refs, _ = CC.charger(False, str(d / "frontiere" / "cameroun.shp"), str(d / "koppen" / "Beck_KG_V1_present_0p0083.tif"), None)
blocs = C.blocs_spatiaux(km, 100.0)
print("cellules", len(X), "blocs", int(blocs.max()) + 1)
for N in (30, 60, 120, 500, 2000, "complet"):
    for r in range(3):
        graine = CC.GRAINE0 + r
        idx = torch.arange(len(X)) if N == "complet" else C.echantillon_espace(km, N, 15.0, graine)[0]
        pris = torch.unique(blocs[idx])
        test = (~torch.isin(blocs, pris)).nonzero().flatten()
        repli = len(test) < 50
        if repli:
            test = torch.randperm(len(X), generator=A.generateur(graine))[:2000]
        fuite = int(torch.isin(test, idx).sum())
        print(f"N={N!s:8s} rep={r} blocs pris {len(pris):3d}/{int(blocs.max()) + 1}  repli={repli}  test={len(test)}  "
              f"points de test présents dans l'apprentissage : {fuite}")
