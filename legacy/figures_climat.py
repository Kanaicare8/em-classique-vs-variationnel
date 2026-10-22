"""
Cartes du cas climatique (PNG pour le mémoire) à partir de resultats/climat/cartes_donnees.csv.
Usage : python figures_climat.py
Sorties : figures/climat_classes.png (référence Köppen-Geiger, EM-BIC, VB), figures/climat_incertitude.png
(responsabilité maximale et entropie d'affectation, EM-BIC et VB). Source des données : WorldClim 2.1
(Fick et Hijmans, 2017) ; référence : Köppen-Geiger (Beck et al., 2018) ; contour : Natural Earth.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

R = Path(__file__).parent
d = pd.read_csv(R / "resultats" / "climat" / "cartes_donnees.csv")
(R / "figures").mkdir(exist_ok=True)
NAVY = "#0B1F4B"


def carte(ax, z, titre, cmap, vmin=None, vmax=None, discret=False):
    sc = ax.scatter(d.lon, d.lat, c=z, s=1.2, cmap=cmap, vmin=vmin, vmax=vmax, marker="s", linewidths=0)
    ax.set_title(titre, fontsize=10, color=NAVY)
    ax.set_xlabel("longitude (°)")
    ax.set_ylabel("latitude (°)")
    ax.set_aspect("equal")
    return sc


fig, axes = plt.subplots(1, 3, figsize=(14, 5.2), constrained_layout=True)
if "koppen" in d.columns:
    carte(axes[0], d["koppen"], "Référence : classes Köppen-Geiger", "tab20")
else:
    axes[0].axis("off")
kb = d["EM-BIC_classe"].nunique()
kv = d["VB-emp_classe"].nunique()
carte(axes[1], d["EM-BIC_classe"], f"EM-BIC : {kb} classes", "tab20")
carte(axes[2], d["VB-emp_classe"], f"VB (priors empiriques, $K_{{max}}$ = 10) : {kv} classes occupées", "tab20")
fig.suptitle("Classes retrouvées sur le climat du Cameroun (WorldClim 2.1, 2,5 minutes d'arc, "
             f"N = {len(d)} cellules)", fontsize=11, color=NAVY)
fig.savefig(R / "figures" / "climat_classes.png", dpi=170)
plt.close(fig)

fig, axes = plt.subplots(2, 2, figsize=(11, 9.5), constrained_layout=True)
for j, nom in enumerate(["EM-BIC", "VB-emp"]):
    s1 = carte(axes[0, j], d[f"{nom}_resp_max"], f"{nom} : responsabilité maximale", "Blues", 0.3, 1.0)
    fig.colorbar(s1, ax=axes[0, j], shrink=0.8)
    s2 = carte(axes[1, j], d[f"{nom}_entropie"], f"{nom} : entropie d'affectation (nat)", "Blues", 0.0, None)
    fig.colorbar(s2, ax=axes[1, j], shrink=0.8)
fig.suptitle("Zones de transition climatique : appartenance souple et entropie d'affectation", fontsize=11, color=NAVY)
fig.savefig(R / "figures" / "climat_incertitude.png", dpi=170)
plt.close(fig)
print("cartes écrites dans figures/")
