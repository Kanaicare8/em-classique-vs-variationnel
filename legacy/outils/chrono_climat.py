"""Chronomètre un ajustement du protocole complet pour dimensionner les calculs du cas climatique."""
import sys
import time
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
import torch

import algorithmes as A
import cas_pratique_climat as CC
import comparaison as C

d = R / "data" / "climat"
X, km, refs, _ = CC.charger(False, str(d / "frontiere" / "cameroun.shp"), str(d / "koppen" / "Beck_KG_V1_present_0p0083.tif"), None)
X = CC.standardiser(X)
for N in (120, 500, 2000, "complet"):
    idx = torch.arange(len(X)) if N == "complet" else C.echantillon_espace(km, N, 15.0, 1)[0]
    t0 = time.perf_counter()
    out = C.protocole_cinq_em_plus_vb(X[idx], 5, kmax=10, n_init=10, graine=1)
    print(N, round(time.perf_counter() - t0, 1), "s ;", {k: v.get("k_hat") for k, v in out.items()}, flush=True)
