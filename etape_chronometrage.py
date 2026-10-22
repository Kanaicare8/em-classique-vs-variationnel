"""
================================================================================
ÉTAPE « chronometrage » : coût de calcul, mesuré sans concurrence (un seul processus, un seul fil)
================================================================================

Unités :
  scalabilite/N=n           EM (K = Kmax) et VB (Kmax), une relance, jeu synthétique à trois groupes, D = 2
  scalabilite/D=d           idem, N = 2001
  pipeline/N=n              données climatiques (D = 5) : temps du pipeline EM-BIC (balayage K = 1..Kmax, n_init
                            relances par K) contre un VB (Kmax, n_init relances), sur les mêmes sous-échantillons ;
                            rapport par réplication, médiane et intervalle bootstrap de la médiane (hypothèse HC4)
Grilles du plan : N couvre les effectifs étudiés (jusqu'à l'ordre de la grille climatique complète, 21 846 cellules) ;
D couvre les dimensions étudiées (2 pour les scénarios, 5 et 20 pour le climat) et 10 en intermédiaire.
Le nombre de répétitions est celui du registre (« repetitions_chronometrage »). Chaque répétition est
mémorisée : une interruption ne perd que la mesure en cours.
"""

from __future__ import annotations

import time

import torch

import algorithmes as A
import comparaison as C
import etapes as E
import parametres as PARAM
import persistance as PE
import statistique as S

GRILLE_N = (300, 1000, 2000, 5000, 20000)
GRILLE_D = (2, 5, 10, 20)
N_FIXE = 2001
EFFECTIFS_PIPELINE = (30, 60, 120, 500, 2000)


def _rep(rapide):
    return 3 if rapide else int(PARAM.valeur("repetitions_chronometrage"))


def _mesure(f):
    t0 = time.perf_counter()
    r = f()
    return {"temps": time.perf_counter() - t0, "n_iter": r["n_iter"] if "n_iter" in r else -1}


def unite_scalabilite(memo, rapide, N, D):
    K = int(PARAM.valeur("k_max")["synthetique"])
    g = A.generateur(PE.graine("chronometrage", "centres", D))
    centres = torch.rand(3, D, generator=g, dtype=torch.float64) * 10 - 5
    X, _ = A.generer_blobs(N // 3, centres, 0.8, PE.graine("chronometrage", "donnees", N, D) % 2 ** 31)
    lignes = []
    for r in range(_rep(rapide)):
        gr = PE.graine("chronometrage", "ajustement", N, D, r) % 2 ** 31
        em = memo(f"EM/rep={r}", lambda: _mesure(lambda: A.em_classique(X, K, graine=gr)))
        vb = memo(f"VB/rep={r}", lambda: _mesure(lambda: A.em_variationnel(X, K, alpha0=1.0 / K, graine=gr)))
        lignes.append({"N": N, "D": D, "rep": r, "temps_em": em["temps"], "temps_vb": vb["temps"],
                       "iter_em": em["n_iter"], "iter_vb": vb["n_iter"],
                       "cout_iter_em": em["temps"] / max(em["n_iter"], 1), "cout_iter_vb": vb["temps"] / max(vb["n_iter"], 1)})
    return {"lignes": lignes}


def unite_pipeline(memo, rapide, N):
    import donnees_geo as G
    d = G.charger_climat(5)
    X = G.standardiser(d["X"])
    kmax = int(PARAM.valeur("k_max")["climat"])
    n_init = int(PARAM.valeur("n_init")["climat"])
    n_init = min(n_init, 2) if rapide else n_init
    lignes = []
    for r in range(_rep(rapide)):
        idx = torch.randperm(len(X), generator=A.generateur(PE.graine("chronometrage", "pipeline", N, r)))[:N]
        Xs = X[idx]
        gr = PE.graine("chronometrage", "pipeline_ajustement", N, r) % 2 ** 31

        def em_bic():
            t0 = time.perf_counter()
            C.choisir_k_critere(Xs, kmax, "bic", n_init, gr)
            return {"temps": time.perf_counter() - t0}

        def vb():
            pr = C.priors_bras(Xs, kmax, "climat")["emp"]
            return _mesure(lambda: A.em_variationnel(Xs, kmax, priori=pr, n_init=n_init, graine=gr))
        te = memo(f"EM-BIC/rep={r}", em_bic)
        tv = memo(f"VB-emp/rep={r}", vb)
        lignes.append({"N": N, "rep": r, "temps_em_bic": te["temps"], "temps_vb": tv["temps"],
                       "ratio": te["temps"] / tv["temps"]})
    ratios = [l["ratio"] for l in lignes]
    med, lo, hi = S.ic_bootstrap(ratios, int(PARAM.valeur("n_bootstrap_ic")), graine=PE.graine("chronometrage", "ic", N) % 2 ** 31,
                                 stat="mediane")
    return {"lignes": [{"N": N, "n_rep": len(ratios), "ratio_median": med, "ratio_ic_bas": lo, "ratio_ic_haut": hi,
                        "temps_em_bic_median": float(torch.tensor([l["temps_em_bic"] for l in lignes]).median()),
                        "temps_vb_median": float(torch.tensor([l["temps_vb"] for l in lignes]).median())}],
            "artefacts": {"repetitions": lignes}}


def unites(rapide: bool):
    U = lambda c, f, **k: E.Unite("chronometrage", c, "etape_chronometrage", f, k)
    gn = GRILLE_N[:3] if rapide else GRILLE_N
    us = [U(f"scalabilite/N={n:06d}", "unite_scalabilite", N=n, D=2) for n in gn]
    us += [U(f"scalabilite/D={d:02d}", "unite_scalabilite", N=N_FIXE, D=d) for d in GRILLE_D]
    us += [U(f"pipeline/N={n:05d}", "unite_pipeline", N=n) for n in EFFECTIFS_PIPELINE]
    return us


def agreger(rapide: bool):
    L = E.lignes("chronometrage", rapide, "scalabilite/")
    E.ecrire_csv("chronometrage_brut", L, rapide)
    groupes = {}
    for l in L:
        groupes.setdefault((l["N"], l["D"]), []).append(l)
    out = []
    for (N, D), ls in sorted(groupes.items()):
        med = lambda k: float(torch.tensor([x[k] for x in ls], dtype=torch.float64).median())
        out.append({"N": N, "D": D, "n_rep": len(ls), "temps_em": med("temps_em"), "temps_vb": med("temps_vb"),
                    "ratio_temps": med("temps_vb") / med("temps_em"), "iter_em": med("iter_em"), "iter_vb": med("iter_vb"),
                    "cout_iter_em": med("cout_iter_em"), "cout_iter_vb": med("cout_iter_vb"),
                    "ratio_cout_iter": med("cout_iter_vb") / med("cout_iter_em")})
    E.ecrire_csv("chronometrage_scalabilite", out, rapide)
    E.ecrire_csv("chronometrage_pipeline", E.lignes("chronometrage", rapide, "pipeline/"), rapide)
