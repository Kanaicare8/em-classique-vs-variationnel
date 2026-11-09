"""Contenu du bulletin d'un mois (page, CSV et PDF partagent ce calcul)."""

from __future__ import annotations

import composants as CO
import service as SV

MODES = {"accord": "les deux bras en accord", "EM-BIC": "EM-BIC", "VB-emp": "VB-emp"}


def _region(st, m):
    return st["releves"].marches[m].region


def bulletin(st, t, mode):
    rel, fiche = st["releves"], st["modele"].fiche
    obs = [i for i, u in enumerate(st["mois"]) if u == t]
    toutes = []
    for i in sorted(obs, key=lambda i: st["marche"][i]):
        m = st["marche"][i]
        p, bas, haut, lecture, classe = SV.evaluation(st, mode, i)
        prix = [rel.prix(m, c, t) for c in fiche["panier"]]
        toutes.append({
            "i": i, "marche": m, "region": _region(st, m), "p": p, "bas": bas, "haut": haut, "lecture": lecture,
            "classe": classe, "prix": prix, "ecarts": [float(v) for v in st["X"][i]],
            "bras": {b: (float(r["p"][i]), float(r["bas"][i]), float(r["haut"][i])) for b, r in st["proba"].items()},
            "saisie": any(rel.source.get((m, c, t)) == "saisie" for c in fiche["panier"]),
            "p_txt": CO.nombre(p, 2), "ic_txt": f"[{CO.nombre(bas, 2)} ; {CO.nombre(haut, 2)}]",
            "prix_txt": [CO.nombre(v, 0) if v else "–" for v in prix],
            "ecart_mais": CO.ecart_pourcent(float(st["X"][i][0]))})
    alerte = [l for l in toutes if l["lecture"].startswith("alerte")]
    incertains = [l for l in toutes if l["classe"] == "ligne-incertaine" and not l["lecture"].startswith("alerte")]

    regions = []
    for reg in sorted({l["region"] for l in toutes}, key=lambda r: -sum(l["region"] == r for l in toutes)):
        o = [l for l in toutes if l["region"] == reg]
        tous = [i for i, m in enumerate(st["marche"]) if _region(st, m) == reg]
        hab = sum(SV.evaluation(st, mode, i)[3].startswith("alerte") for i in tous) / len(tous) if tous else None
        regions.append({"region": reg, "n": str(len(o)), "alerte": str(sum(l in alerte for l in o)),
                        "incertains": str(sum(l in incertains for l in o)), "habituelle": CO.pourcent(hab, 1)})
    periode = "apprentissage du modèle" if t <= st["fin_apprentissage"] else "hors apprentissage"
    phrase = (f"En {SV.mois_texte(t)}, {len(alerte)} des {len(toutes)} marchés observés sont en alerte selon "
              f"{MODES.get(mode, mode)}, et {len(incertains)} ont une lecture incertaine ({periode}).")
    return {"toutes": toutes, "alerte": alerte, "incertains": incertains, "regions": regions,
            "a_voir": sorted(alerte + incertains, key=lambda l: -l["p"]), "phrase": phrase,
            "mode_texte": MODES.get(mode, mode), "periode": periode}
