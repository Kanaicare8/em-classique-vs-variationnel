"""
================================================================================
PRÉCALCUL DE L'APPLICATION : ajustements du cas des prix alimentaires, dans un magasin séparé
================================================================================

python demo/precalcul.py            paramètres du registre (calibrés s'ils existent, provisoires sinon)
python demo/precalcul.py --rapide   essai réduit (3 relances, 50 réplicats bootstrap, 500 tirages a posteriori)

Exécute les unités OFFICIELLES « reference » et « alerte » de etape_prix (même code, mêmes graines) dans
resultats/app/ (variable ICARE_MAGASIN) : le magasin confirmatoire resultats/magasin/ n'est ni lu ni écrit.
Reprenable comme run.py : une unité terminée n'est pas recalculée, un ajustement mémorisé n'est pas refait.
Écrit ensuite resultats/app/regimes[_rapide].pt : paramètres des bras EM-BIC et VB-emp en unités d'origine et
affectation de chaque observation (apprentissage et test), pour la page « Régimes ».

Une fois le calibrage terminé, supprimer resultats/app/ et relancer ce script redonne les unités du calcul
confirmatoire à l'identique (mêmes graines, mêmes paramètres).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_APP = RACINE / "resultats" / "app"
os.environ["ICARE_MAGASIN"] = str(DOSSIER_APP)        # avant tout import du projet : etapes.magasin() le lit
sys.path.insert(0, str(RACINE))


def chemin_regimes(rapide: bool) -> Path:
    return DOSSIER_APP / ("regimes_rapide.pt" if rapide else "regimes.pt")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[2])
    ap.add_argument("--rapide", action="store_true", help="essai réduit, quelques minutes")
    rapide = ap.parse_args().rapide

    print("Chargement de PyTorch (une à deux minutes sur ce poste)...", flush=True)
    import torch
    from emvb import algorithmes as A
    from emvb import comparaison as C
    from emvb import etape_prix as EP
    from emvb import etapes as E
    from emvb import parametres as PARAM
    from emvb import persistance as PE
    torch.set_num_threads(max(1, (os.cpu_count() or 2) - 1))

    mag = E.magasin("prix", rapide)
    for cle, f in (("reference", EP.unite_reference), ("alerte", EP.unite_alerte)):
        if mag.complete(cle):
            print(f"unité {cle} : déjà calculée")
            continue
        print(f"unité {cle} : calcul en cours...", flush=True)
        t0 = time.perf_counter()
        res = f(E.Memo(mag, cle), rapide=rapide)
        res["cle"] = cle
        mag.ecrire(cle, res)
        print(f"unité {cle} : terminée en {time.perf_counter() - t0:.0f} s", flush=True)

    # Mêmes arguments que unite_alerte : les ajustements sont relus depuis sa mémoire, rien n'est recalculé
    Xtr, _, d = EP.donnees()
    ref = mag.lire("reference")["artefacts"]
    sortie = C.bras_protocole(Xtr, int(ref["K_ref"]), EP._kmax(), EP._n_init(rapide), PE.graine("prix", "complet") % 2 ** 31,
                              EP.FAMILLE, bras=EP.BRAS_ALERTE, memo=E.Memo(mag, "alerte"))
    seuil = float(PARAM.valeur("seuil_actif"))
    e, c = d["echelle"], d["centre"]
    bras = {}
    for nom, res in sortie.items():
        if "echec" in res:
            bras[nom] = {"echec": res["echec"]}
            continue
        p = C.params_plugin(res)
        actives = res["Nk"] / len(Xtr) >= seuil
        r, _ = A._etape_e(d["Z"], p["pi"], p["mu"], p["cov"])
        bras[nom] = {"pi": p["pi"], "mu": p["mu"] * e + c, "cov": p["cov"] * e[:, None] * e[None, :],
                     "actives": actives, "k_hat": res["k_hat"], "k_tension": EP.regime_tension(p["mu"], actives, d),
                     "affectation": r.argmax(1), "n_iter": res["n_iter"], "converge": bool(res["converge"]),
                     "temps_s": float(res["temps_total"])}
    PE.sauver(chemin_regimes(rapide), {"K_ref": int(ref["K_ref"]), "critere_par_k": ref["critere_par_k"], "bras": bras,
                                      "seuil_actif": seuil, "provisoires": PARAM.provisoires(), "rapide": rapide,
                                      "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
    print(f"résumé écrit : {chemin_regimes(rapide).relative_to(RACINE)}")

    # Tirages de l'unité « alerte » (même code, mêmes graines) pour la page « Nouveau relevé » : VB, tirages de q ;
    # EM-BIC, réplicats bootstrap à démarrage chaud alignés (D-19). Contrôle : ils redonnent les intervalles officiels.
    chemin_tir = DOSSIER_APP / ("releve_rapide.pt" if rapide else "releve.pt")
    if not chemin_tir.exists():
        tirages = {}
        for nom, res in sortie.items():
            if "echec" in res:
                continue
            p = C.params_plugin(res)
            k = EP.regime_tension(p["mu"], res["Nk"] / len(Xtr) >= seuil, d)
            if nom.startswith("VB"):
                nt = 500 if rapide else int(PARAM.valeur("n_tirages_posterieur"))
                pis, mus, covs = EP.tirages_q(res["P"], nt, PE.graine("prix", "alerte_tirages") % 2 ** 31)
                ks = torch.full((len(pis),), k)
            else:
                B = 50 if rapide else int(PARAM.valeur("n_bootstrap_modele"))
                print(f"{nom} : {B} réplicats bootstrap (une seule fois)...", flush=True)
                reps, ks = [], []
                for b in range(B):
                    ib = torch.randint(len(Xtr), (len(Xtr),), generator=A.generateur(PE.graine("prix", "alerte_boot", b)))
                    eb = C.em_demarrage_chaud(Xtr[ib], res)
                    reps.append(eb)
                    ks.append(int(C.aligner_bootstrap(Xtr, res, eb)[k]))
                pis, mus, covs = (torch.stack([r[c] for r in reps]) for c in ("pi", "mu", "cov"))
                ks = torch.tensor(ks)
            tirages[nom] = {"pi": pis, "mu": mus, "cov": covs, "k_tirage": ks, "k": k,
                            "plugin": {"pi": p["pi"], "mu": p["mu"], "cov": p["cov"]},
                            "moyenne_des_tirages": nom.startswith("VB")}
        PE.sauver(chemin_tir, {"bras": tirages, "centre": d["centre"], "echelle": d["echelle"], "rapide": rapide,
                               "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
        print(f"tirages écrits : {chemin_tir.relative_to(RACINE)}")
    tir = PE.charger(chemin_tir)
    officiel = mag.lire("alerte")["artefacts"]
    for nom, t in tir["bras"].items():
        ps = torch.stack([EP._proba_composante(d["Z"], t["pi"][i][None], t["mu"][i][None], t["cov"][i][None],
                                               int(t["k_tirage"][i]))[0] for i in range(len(t["pi"]))])
        ic = torch.quantile(ps, torch.tensor([0.05, 0.95], dtype=torch.float64), dim=0)
        print(f"contrôle {nom} : écart max à l'IC officiel = {float((ic.float() - officiel[nom]['ic']).abs().max()):.2e}")
    if PARAM.provisoires():
        print("paramètres provisoires utilisés (chiffres exploratoires) : " + ", ".join(PARAM.provisoires()))


if __name__ == "__main__":
    main()
