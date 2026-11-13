"""
================================================================================
EXPORT DU MODÈLE DU MÉMOIRE POUR L'OUTIL (D-20) : seul script de l'outil qui demande PyTorch
================================================================================

python bulletin/exporter_modele.py      (à la racine du dépôt, après python demo/precalcul.py)

Lit resultats/app/releve.pt et regimes.pt (unités « reference » et « alerte » du mémoire, mêmes graines ; leurs
intervalles redonnent exactement ceux du magasin confirmatoire) et écrit bulletin/modeles/memoire/ :
  parametres.npz   paramètres plug-in et tirages de chaque bras (variables standardisées), centre et échelle ;
  controle.npz     écarts X et P(tension), IC 90 % officiels des 1 055 observations : test d'équivalence NumPy ;
  fiche.json       provenance (période, règles des écarts, empreinte des données, commit), régimes lisibles.
Le dossier « memoire » n'est jamais réécrit s'il existe (référence figée) : le supprimer à la main pour l'exporter
de nouveau.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
SORTIE = Path(__file__).resolve().parent / "modeles" / "memoire"


def main():
    if SORTIE.exists():
        raise SystemExit(f"{SORTIE} existe déjà : le modèle du mémoire est figé (le supprimer à la main pour réexporter)")
    from emvb import donnees as DO
    from emvb import etape_prix as EP
    from emvb import parametres as PARAM
    from emvb import persistance as PE

    app = RACINE / "resultats" / "app"
    tir, reg = PE.charger(app / "releve.pt"), PE.charger(app / "regimes.pt")
    if tir.get("rapide") or reg.get("rapide"):
        raise SystemExit("précalcul réduit (--rapide) : exporter le précalcul complet")
    officiel = PE.Magasin("prix", RACINE / "resultats" / "magasin").lire("alerte")["artefacts"]
    _, _, d = EP.donnees()

    tableaux = {"centre": d["centre"].numpy(), "echelle": d["echelle"].numpy()}
    bras = {}
    for nom, t in tir["bras"].items():
        for c in ("pi", "mu", "cov"):
            tableaux[f"{nom}/plugin_{c}"] = t["plugin"][c].numpy()
            tableaux[f"{nom}/tirages_{c}"] = t[c].numpy()
        tableaux[f"{nom}/k_tirage"] = t["k_tirage"].numpy().astype(np.int16)
        r = reg["bras"][nom]
        actives = [int(k) for k in np.flatnonzero(r["actives"].numpy())]
        bras[nom] = {
            "k_tension": int(t["k"]), "p_moyenne_des_tirages": bool(t["moyenne_des_tirages"]),
            "n_tirages": int(len(t["pi"])),
            "intervalle": "quantiles 5 % et 95 % des " + ("tirages de la loi variationnelle q" if t["moyenne_des_tirages"]
                                                         else "réplicats bootstrap à démarrage chaud alignés (D-19)"),
            "regimes": [{"k": k, "tension": k == int(t["k"]), "poids": float(r["pi"][k]),
                         "ecart_moyen": [float(v) for v in r["mu"][k]]} for k in actives]}
        tableaux[f"{nom}/controle_proba"] = officiel[nom]["proba"].double().numpy()
        tableaux[f"{nom}/controle_ic"] = officiel[nom]["ic"].double().numpy()
    SORTIE.mkdir(parents=True)
    np.savez_compressed(SORTIE / "parametres.npz", **{k: v for k, v in tableaux.items() if "/controle" not in k})
    np.savez_compressed(SORTIE / "controle.npz", X=d["X"].numpy(), mois=d["mois"].numpy(),
                        marche=np.array(d["marches"])[d["marche"].numpy()],
                        **{k.replace("/controle_", "/"): v for k, v in tableaux.items() if "/controle" in k})

    csv_prix = DO.DATA / "prix" / "wfp_cmr_panier.csv"
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RACINE, capture_output=True,
                                text=True).stdout.strip() or None
    except OSError:
        commit = None
    fiche = {
        "version": "memoire", "libelle": "Modèle du mémoire (référence figée)",
        "description": "EM-BIC et VB-emp ajustés sur les écarts des prix d'avril 2021 à décembre 2023 ; mémoire de "
                       "KANA TIODONG Icare Brichel, cas pratique des prix alimentaires du Cameroun.",
        "apprentissage": {"debut": DO.mois_texte(int(d["mois"][d["app"]].min())),
                          "fin": str(PARAM.valeur("prix_fin_apprentissage")), "n": int(d["app"].sum())},
        "ecarts": {"fenetre_mois": int(PARAM.valeur("prix_fenetre_mois")),
                   "releves_min": int(PARAM.valeur("prix_releves_min")),
                   "facteur_pic": float(PARAM.valeur("prix_facteur_pic"))},
        "panier": list(DO.PANIER_PRIX), "noms": list(DO.NOMS_PANIER),
        "donnees": {"fichier": "data/prix/wfp_cmr_panier.csv",
                    "sha256": hashlib.sha256(csv_prix.read_bytes()).hexdigest()},
        "seuil_actif": float(reg["seuil_actif"]), "bras": bras,
        "code": {"commit": commit, "unites": ["reference", "alerte"]},
        "exporte_le": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    (SORTIE / "fiche.json").write_text(json.dumps(fiche, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"modèle exporté : {SORTIE.relative_to(RACINE)} "
          f"({sum(f.stat().st_size for f in SORTIE.iterdir()) / 1e6:.1f} Mo)")


if __name__ == "__main__":
    main()
