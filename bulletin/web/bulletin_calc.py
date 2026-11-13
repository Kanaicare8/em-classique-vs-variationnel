"""Contenu du bulletin d'un mois (page, CSV et PDF partagent ce calcul)."""

from __future__ import annotations

import composants as CO
import service as SV

MODES = SV.MODES


def _region(st, m):
    return st["releves"].marches[m].region


def comptes_par_mois(st, mode):
    """{mois : (observés, en alerte, à surveiller)} : évolution du bulletin, pour la frise et la comparaison."""
    out = {}
    for i, t in enumerate(st["mois"]):
        etat = SV.evaluation(st, mode, i)[3]
        n, a, s = out.get(t, (0, 0, 0))
        out[t] = (n + 1, a + SV.en_alerte(etat), s + SV.a_surveiller(etat))
    return out


def bulletin(st, t, mode):
    rel, fiche = st["releves"], st["modele"].fiche
    obs = [i for i, u in enumerate(st["mois"]) if u == t]
    toutes = []
    for i in sorted(obs, key=lambda i: st["marche"][i]):
        m = st["marche"][i]
        p, bas, haut, etat = SV.evaluation(st, mode, i)
        prix = [rel.prix(m, c, t) for c in fiche["panier"]]
        ecarts = [float(v) for v in st["X"][i]]
        toutes.append({
            "i": i, "marche": m, "region": _region(st, m), "p": p, "bas": bas, "haut": haut, "etat": etat,
            "lecture": SV.ETATS[etat][0], "prix": prix, "ecarts": ecarts,
            "bras": {b: (float(r["p"][i]), float(r["bas"][i]), float(r["haut"][i])) for b, r in st["proba"].items()},
            "saisie": any(rel.source.get((m, c, t)) == "saisie" for c in fiche["panier"]),
            "p_txt": CO.pourcent(p, 0), "ic_txt": f"{CO.pourcent(bas, 0)} à {CO.pourcent(haut, 0)}",
            "prix_txt": [CO.nombre(v, 0) if v else "–" for v in prix],
            "ecarts_txt": [CO.ecart_pourcent(e) for e in ecarts], "ecart_mais": CO.ecart_pourcent(ecarts[0])})
    alerte = [l for l in toutes if SV.en_alerte(l["etat"])]
    surveiller = [l for l in toutes if SV.a_surveiller(l["etat"])]

    regions = []
    for reg in sorted({l["region"] for l in toutes}, key=lambda r: -sum(l["region"] == r for l in toutes)):
        o = [l for l in toutes if l["region"] == reg]
        tous = [i for i, m in enumerate(st["marche"]) if _region(st, m) == reg]
        hab = sum(SV.en_alerte(SV.evaluation(st, mode, i)[3]) for i in tous) / len(tous) if tous else None
        regions.append({"region": reg, "n": len(o), "alerte": sum(l in alerte for l in o),
                        "surveiller": sum(l in surveiller for l in o), "habituelle": hab})

    serie = comptes_par_mois(st, mode)
    avant = max((u for u in serie if u < t), default=None)
    periode = "apprentissage du modèle" if t <= st["fin_apprentissage"] else "après l'apprentissage du modèle"
    phrase = (f"En {SV.mois_humain(t)}, {len(alerte)} marché{'s' if len(alerte) > 1 else ''} sur {len(toutes)} "
              f"{'sont' if len(alerte) > 1 else 'est'} en alerte et {len(surveiller)} à surveiller "
              f"(lecture {MODES[mode].split(' :')[0].lower()}).")
    return {"toutes": toutes, "alerte": alerte, "surveiller": surveiller, "regions": regions,
            "a_voir": sorted(alerte + surveiller, key=lambda l: -l["p"]), "phrase": phrase, "mode_texte": MODES[mode],
            "periode": periode, "serie": serie, "mois_precedent": avant,
            "precedent": serie.get(avant) if avant is not None else None}
