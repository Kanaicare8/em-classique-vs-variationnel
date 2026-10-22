"""
================================================================================
ÉTAPE « validation » : exemples numériques du chapitre 1 et propriétés théoriques
================================================================================

Unités :
  tableau_1_2         EM classique sur les 8 observations du texte (K = 2, initialisation du texte), 10 itérations
  tableau_1_4         forward-backward sur l'exemple du texte (matrices A, B et loi initiale du texte)
  tableau_1_5         EM variationnel sur les 8 observations (Kmax = 3, alpha0 = 1/3, priors diffus), deux initialisations
  proprietes/graine=s propriétés vérifiées sur le jeu de référence, une relance par graine :
                      monotonie de la log-vraisemblance (EM) et de l'ELBO (VB), identité de Neal et Hinton
                      F(q*, theta) = l(theta), ELBO <= log-vraisemblance maximale
Les valeurs des exemples (données, initialisations) sont celles imprimées dans le texte : elles ne sont pas des réglages.
Le nombre de graines des propriétés est celui des relances de la famille « synthetique » (registre n_init).
"""

from __future__ import annotations

import math

import torch

import algorithmes as A
import etapes as E
import parametres as PARAM
import persistance as PE

X8 = torch.tensor([0.5, 1.0, 1.2, 1.8, 7.1, 7.5, 8.0, 8.3], dtype=torch.float64).reshape(-1, 1)
INIT_1_2 = {"pi": (0.5, 0.5), "mu": (2.0, 6.0), "sigma": (2.0, 2.0)}
ITERATIONS_1_2 = 10
HMM_A = ((0.7, 0.3), (0.4, 0.6))
HMM_B = ((0.1, 0.9), (0.8, 0.2))        # colonnes : Pa (0), NPa (1)
HMM_PI0 = (0.6, 0.4)
HMM_OBS = (1, 0, 0)                     # NPa, Pa, Pa
KMAX_1_5 = 3
GRAINES_1_5 = 5


def unite_tableau_1_2(memo, rapide):
    pi = torch.tensor(INIT_1_2["pi"], dtype=torch.float64)
    mu = torch.tensor(INIT_1_2["mu"], dtype=torch.float64).reshape(2, 1)
    cov = (torch.tensor(INIT_1_2["sigma"], dtype=torch.float64) ** 2).reshape(2, 1, 1)
    _, ln = A._etape_e(X8, pi, mu, cov)
    lignes = [{"iteration": 0, "mu1": float(mu[0]), "mu2": float(mu[1]), "sigma1": float(cov[0].sqrt()),
               "sigma2": float(cov[1].sqrt()), "pi1": float(pi[0]), "pi2": float(pi[1]), "loglik": float(ln.sum())}]
    for it in range(1, ITERATIONS_1_2 + 1):
        r, _ = A._etape_e(X8, pi, mu, cov)
        pi, mu, cov = A._etape_m(X8, r, "full", 0.0)
        _, ln = A._etape_e(X8, pi, mu, cov)
        lignes.append({"iteration": it, "mu1": float(mu[0]), "mu2": float(mu[1]), "sigma1": float(cov[0].sqrt()),
                       "sigma2": float(cov[1].sqrt()), "pi1": float(pi[0]), "pi2": float(pi[1]), "loglik": float(ln.sum())})
    f = lignes[-1]

    def n(x, m, s):
        return math.exp(-0.5 * ((x - m) / s) ** 2) / (s * math.sqrt(2 * math.pi))
    densite = f["pi1"] * n(2.0, f["mu1"], f["sigma1"]) + f["pi2"] * n(2.0, f["mu2"], f["sigma2"])
    return {"lignes": lignes, "artefacts": {"X": X8, "densite_x2": densite,
                                            "moyennes_groupes": (float(X8[:4].mean()), float(X8[4:].mean()))}}


def unite_tableau_1_4(memo, rapide):
    fb = A.forward_backward(torch.tensor(HMM_A), torch.tensor(HMM_B), torch.tensor(HMM_PI0), torch.tensor(HMM_OBS))
    lignes = [{"t": t + 1, "alpha_B": float(fb["alpha"][t, 0]), "alpha_P": float(fb["alpha"][t, 1]),
               "beta_B": float(fb["beta"][t, 0]), "beta_P": float(fb["beta"][t, 1]),
               "gamma_B": float(fb["gamma"][t, 0]), "gamma_P": float(fb["gamma"][t, 1])} for t in range(len(HMM_OBS))]
    return {"lignes": lignes, "artefacts": {"proba": float(fb["proba"])}}


def unite_tableau_1_5(memo, rapide):
    pr = A.priori_diffus(X8, alpha0=1.0 / KMAX_1_5)
    lignes, fits = [], []
    for init in ("prior", "kmeans"):
        for g in range(GRAINES_1_5):
            v = A.em_variationnel(X8, KMAX_1_5, priori=pr, init=init, graine=g)
            o = torch.argsort(v["Nk"], descending=True)
            lignes.append({"init": init, "graine": g, "iterations": v["n_iter"], "converge": float(v["converge"]),
                           "alpha": [round(float(a), 3) for a in v["alpha"][o]],
                           "m": [round(float(m), 3) for m in v["m"][o].flatten()], "actives": v["n_actives"],
                           "elbo": v["elbo"]})
            fits.append(PE.resume_ajustement(v))
    return {"lignes": lignes, "artefacts": {"ajustements": fits}}


def unite_proprietes(memo, rapide, graine):
    X, _ = A.jeu_reference(PE.graine("validation", "donnees") % 2 ** 31)
    kmax = int(PARAM.valeur("k_max")["synthetique"])
    em = A.em_classique(X, kmax, init="aleatoire", graine=graine)
    h = torch.tensor(em["ll_hist"])
    r, _ = A._etape_e(X, em["pi"], em["mu"], em["cov"])
    F = A.energie_libre_em(X, r, em["pi"], em["mu"], em["cov"])
    vb = A.em_variationnel(X, kmax, alpha0=1.0 / kmax, graine=graine)
    hv = torch.tensor(vb["elbo_hist"])
    em_best = A.em_classique(X, kmax, n_init=int(PARAM.valeur("n_init")["synthetique"]), graine=graine)
    return {"lignes": [{"graine": graine,
                        "baisse_max_loglik": float((h[:-1] - h[1:]).clamp(min=0).max()) if len(h) > 1 else 0.0,
                        "baisse_max_elbo": float((hv[:-1] - hv[1:]).clamp(min=0).max()) if len(hv) > 1 else 0.0,
                        "ecart_neal_hinton": abs(F - em["loglik"]), "elbo": vb["elbo"],
                        "loglik_max_em": em_best["loglik"], "elbo_inferieur": float(vb["elbo"] <= em_best["loglik"]),
                        "converge_em": float(em["converge"]), "converge_vb": float(vb["converge"])}],
            "artefacts": {"ll_hist": em["ll_hist"], "elbo_hist": vb["elbo_hist"]}}


def unites(rapide: bool):
    n = 3 if rapide else int(PARAM.valeur("n_init")["synthetique"])
    us = [E.Unite("validation", c, "etape_validation", f"unite_{c}") for c in ("tableau_1_2", "tableau_1_4", "tableau_1_5")]
    us += [E.Unite("validation", f"proprietes/graine={g:03d}", "etape_validation", "unite_proprietes", dict(graine=g))
           for g in range(n)]
    return us


def agreger(rapide: bool):
    for c in ("tableau_1_2", "tableau_1_4", "tableau_1_5"):
        E.ecrire_csv(f"validation_{c}", E.lignes("validation", rapide, c), rapide)
    L = E.lignes("validation", rapide, "proprietes/")
    E.ecrire_csv("validation_proprietes", L, rapide)
    t12 = E.magasin("validation", rapide).lire("tableau_1_2")["artefacts"]
    t14 = E.magasin("validation", rapide).lire("tableau_1_4")["artefacts"]
    E.ecrire_csv("validation_resume", [
        {"mesure": "densite du melange ajuste en x = 2,0 (eq. 1.10)", "valeur": t12["densite_x2"]},
        {"mesure": "moyenne empirique du premier groupe", "valeur": t12["moyennes_groupes"][0]},
        {"mesure": "moyenne empirique du second groupe", "valeur": t12["moyennes_groupes"][1]},
        {"mesure": "p(O) forward-backward", "valeur": t14["proba"]},
        {"mesure": "baisse maximale de la log-vraisemblance (toutes graines)", "valeur": max(l["baisse_max_loglik"] for l in L)},
        {"mesure": "baisse maximale de l'ELBO (toutes graines)", "valeur": max(l["baisse_max_elbo"] for l in L)},
        {"mesure": "ecart maximal de Neal et Hinton", "valeur": max(l["ecart_neal_hinton"] for l in L)},
        {"mesure": "part des graines avec ELBO <= log-vraisemblance maximale", "valeur": sum(l["elbo_inferieur"] for l in L) / len(L)},
    ], rapide)
