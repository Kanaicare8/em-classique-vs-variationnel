"""
================================================================================
ÉTAPE « illustrations » : expériences descriptives du chapitre 2 (jeu de référence, Iris, variantes, HMM)
================================================================================

Ces unités ILLUSTRENT les mécanismes (élagage, sensibilité aux priors, initialisation, covariance) ; aucune
conclusion confirmatoire n'en est tirée : les hypothèses sont testées par les étapes scenarios, climat, sp500
et texte. Tous les réglages viennent du registre (parametres.py) ; les valeurs propres aux exemples sont
déclarées ci-dessous.

Unités :
  k6                        EM (K = Kmax) et VB (Kmax) : priors empiriques et diffus, initialisations k-means et aléatoire
  k3                        EM (K = 3) et VB (Kmax = 3)
  alpha0/a=i/priors=p       VB à Kmax selon alpha0, grille logarithmique sur les bornes de « espace_priors »
  initialisation/init=i/rep=r  une relance par graine (n_init = 1) : composantes actives selon l'initialisation
  covariance/type=c         EM et VB pour les quatre contraintes de covariance
  iris                      Iris (Fisher 1936) : K = 3 et K = Kmax
  aberrantes                jeu de référence plus des points uniformes (part d'aberrations du scénario S6 du plan)
  bic_aic                   EM pour K = 1..Kmax : log-vraisemblance, BIC, AIC, ICL
  variantes                 EM, SEM, EM online, VB, SVI (réglages du registre « variantes_stochastiques »)
  hmm                       Baum-Welch discret et gaussien sur des chaînes simulées de paramètres connus
"""

from __future__ import annotations

import math
import time

import torch

import algorithmes as A
import donnees as DO
import etapes as E
import parametres as PARAM
import persistance as PE

N_ALPHA0 = 9                       # points de la grille logarithmique de alpha0 (deux par décade sur [1e-3 ; 10], bornes incluses)
N_ABERRANTES = 10                  # 10 points uniformes ajoutés aux 300 du jeu de référence (environ 3 %)
HMM_DISCRET = {"A": ((0.7, 0.3), (0.4, 0.6)), "B": ((0.1, 0.9), (0.8, 0.2)), "pi0": (0.6, 0.4), "T": 1000}
HMM_GAUSS = {"A": ((0.95, 0.05), (0.10, 0.90)), "mu": (0.1, -0.2), "sigma": (0.5, 2.0), "T": 1500}


def _jeu():
    return A.jeu_reference(PE.graine("illustrations", "donnees") % 2 ** 31)


def _kmax():
    return int(PARAM.valeur("k_max")["synthetique"])


def _n_init(rapide):
    n = int(PARAM.valeur("n_init")["synthetique"])
    return min(n, 3) if rapide else n


def _g(*role):
    return PE.graine("illustrations", *role) % 2 ** 31


def _ligne(nom, res, X, y):
    return {"modele": nom, "composantes_actives": int((res["Nk"] / len(X) >= float(PARAM.valeur("seuil_actif"))).sum()),
            "composantes_Nk_1": int((res["Nk"] >= 1).sum()), "ARI": A.indice_rand_ajuste(y, res["labels"]),
            "silhouette": A.silhouette(X, res["labels"]), "iterations": res["n_iter"], "converge": float(res["converge"]),
            "degenere": float(res["degenere"]), "temps_s": res["temps"],
            "poids": [round(float(p), 4) for p in res["pi"]]}


def unite_k6(memo, rapide):
    X, y = _jeu()
    K, n = _kmax(), _n_init(rapide)
    fits = {
        "EM (init k-means)": memo("em", lambda: A.em_classique(X, K, n_init=n, graine=_g("k6"))),
        "EM (init aléatoire)": memo("em_alea", lambda: A.em_classique(X, K, init="aleatoire", n_init=n, graine=_g("k6"))),
        "VB priors empiriques (init k-means)": memo("vb_emp", lambda: A.em_variationnel(
            X, K, priori=A.priori_empirique(X, 1.0 / K), n_init=n, graine=_g("k6"))),
        "VB priors diffus (init k-means)": memo("vb_diff", lambda: A.em_variationnel(
            X, K, priori=A.priori_diffus(X, 1.0 / K), n_init=n, graine=_g("k6"))),
        "VB priors diffus (init prior)": memo("vb_prior", lambda: A.em_variationnel(
            X, K, priori=A.priori_diffus(X, 1.0 / K), init="prior", n_init=n, graine=_g("k6"))),
    }
    return {"lignes": [_ligne(k, v, X, y) for k, v in fits.items()],
            "artefacts": {"X": X, "y": y, "ajustements": {k: PE.resume_ajustement(v) for k, v in fits.items()}}}


def unite_k3(memo, rapide):
    X, y = _jeu()
    n = _n_init(rapide)
    em = A.em_classique(X, 3, n_init=n, graine=_g("k3"))
    vb = A.em_variationnel(X, 3, alpha0=1.0 / 3, n_init=n, graine=_g("k3"))
    return {"lignes": [_ligne("EM K=3", em, X, y), _ligne("VB Kmax=3", vb, X, y)],
            "artefacts": {"em": PE.resume_ajustement(em), "vb": PE.resume_ajustement(vb)}}


def grille_alpha0():
    lo, hi = PARAM.valeur("espace_priors")["alpha0"]
    return [10 ** (math.log10(lo) + i * (math.log10(hi) - math.log10(lo)) / (N_ALPHA0 - 1)) for i in range(N_ALPHA0)]


def unite_alpha0(memo, rapide, i, priors):
    X, y = _jeu()
    a0 = grille_alpha0()[i]
    pr = A.priori_empirique(X, a0) if priors == "empiriques" else A.priori_diffus(X, a0)
    v = A.em_variationnel(X, _kmax(), priori=pr, n_init=_n_init(rapide), graine=_g("alpha0", i))
    l = _ligne(f"VB priors {priors}", v, X, y)
    l.update(alpha0=a0, priors=priors)
    return {"lignes": [l], "artefacts": {"ajustement": PE.resume_ajustement(v, avec_r=False)}}


def unite_initialisation(memo, rapide, init, rep):
    X, y = _jeu()
    K = _kmax()
    g = _g("initialisation", rep)
    e = A.em_classique(X, K, init="kmeans" if init == "kmeans" else "aleatoire", graine=g)
    iv = "kmeans" if init == "kmeans" else "prior"
    vd = A.em_variationnel(X, K, priori=A.priori_diffus(X, 1.0 / K), init=iv, graine=g)
    ve = A.em_variationnel(X, K, priori=A.priori_empirique(X, 1.0 / K), init=iv, graine=g)
    lignes = []
    for nom, r in (("EM", e), ("VB priors diffus", vd), ("VB priors empiriques", ve)):
        l = _ligne(nom, r, X, y)
        l.update(initialisation=init, rep=rep, critere=r.get("loglik", r.get("elbo")))
        lignes.append(l)
    return {"lignes": lignes}


def unite_covariance(memo, rapide, cov_type):
    X, y = _jeu()
    K, n = _kmax(), _n_init(rapide)
    e = A.em_classique(X, K, cov_type=cov_type, n_init=n, graine=_g("covariance"))
    v = A.em_variationnel(X, K, alpha0=1.0 / K, cov_type=cov_type, n_init=n, graine=_g("covariance"))
    le, lv = _ligne("EM", e, X, y), _ligne("VB priors empiriques", v, X, y)
    le.update(covariance=cov_type, BIC=e["bic"])
    lv.update(covariance=cov_type)
    return {"lignes": [le, lv]}


def unite_iris(memo, rapide):
    X, y = DO.charger_iris()
    K, n = _kmax(), _n_init(rapide)
    fits = {f"EM K={K}": A.em_classique(X, K, n_init=n, graine=_g("iris")),
            f"VB Kmax={K}": A.em_variationnel(X, K, alpha0=1.0 / K, n_init=n, graine=_g("iris")),
            "EM K=3": A.em_classique(X, 3, n_init=n, graine=_g("iris")),
            "VB Kmax=3": A.em_variationnel(X, 3, alpha0=1.0 / 3, n_init=n, graine=_g("iris"))}
    return {"lignes": [_ligne(k, v, X, y) for k, v in fits.items()],
            "artefacts": {k: PE.resume_ajustement(v) for k, v in fits.items()}}


def unite_aberrantes(memo, rapide):
    X, y = _jeu()
    lo, hi = X.min(0).values, X.max(0).values
    etendue = hi - lo
    u = torch.rand(N_ABERRANTES, X.shape[1], generator=A.generateur(_g("aberrantes")), dtype=torch.float64)
    bruit = lo - etendue + 3 * etendue * u              # boîte trois fois plus large que les données, centrée sur elles
    Xa = torch.cat([X, bruit])
    K, n = _kmax(), _n_init(rapide)
    lignes = []
    for nom, res in (("EM", A.em_classique(Xa, K, n_init=n, graine=_g("aberrantes"))),
                     ("VB priors empiriques", A.em_variationnel(Xa, K, alpha0=1.0 / K, n_init=n, graine=_g("aberrantes")))):
        actif = res["Nk"] / len(Xa) >= float(PARAM.valeur("seuil_actif"))
        traces = torch.stack([torch.trace(c) for c in res["cov"]])
        lignes.append({"modele": nom, "ARI_hors_aberrantes": A.indice_rand_ajuste(y, res["labels"][:len(X)]),
                       "composantes_actives": int(actif.sum()), "trace_covariance_max": float(traces[actif].max()),
                       "poids_plus_petit_actif": float(res["pi"][actif].min())})
    return {"lignes": lignes, "artefacts": {"bruit": bruit}}


def unite_bic_aic(memo, rapide):
    X, _ = _jeu()
    lignes = []
    for K in range(1, _kmax() + 1):
        e = memo(f"K={K}", lambda K=K: A.em_classique(X, K, n_init=_n_init(rapide), graine=_g("bic")))
        lignes.append({"K": K, "loglik": e["loglik"], "BIC": e["bic"], "AIC": e["aic"], "ICL": e["icl"]})
    return {"lignes": lignes}


def unite_variantes(memo, rapide):
    X, y = _jeu()
    v = PARAM.valeur("variantes_stochastiques")
    K, Kmax = 3, _kmax()
    pr = A.priori_empirique(X, 1.0 / Kmax)
    lignes = []

    def chrono(f):
        t0 = time.perf_counter()
        r = f()
        return r, time.perf_counter() - t0
    e, t = chrono(lambda: A.em_classique(X, K, n_init=_n_init(rapide), graine=_g("variantes")))
    lignes.append({"methode": "EM (lot complet)", "loglik": e["loglik"], "ARI": A.indice_rand_ajuste(y, e["labels"]),
                   "temps_s": t, "baisses_loglik": 0})
    s, t = chrono(lambda: A.em_stochastique(X, K, n_iter=int(v["sem_n_iter"]), burn=int(v["sem_burn"]), graine=_g("variantes")))
    ll = torch.tensor(s["ll_hist"])
    lignes.append({"methode": "EM stochastique (SEM)", "loglik": s["loglik"], "ARI": A.indice_rand_ajuste(y, s["labels"]),
                   "temps_s": t, "baisses_loglik": int((ll[1:] < ll[:-1]).sum())})
    o, t = chrono(lambda: A.em_online(X, K, taille_lot=int(v["online_lot"]), n_epoques=int(v["epoques"]),
                                      kappa=float(v["online_kappa"]), t0=float(v["online_t0"]), graine=_g("variantes")))
    lignes.append({"methode": "EM online", "loglik": o["loglik"], "ARI": A.indice_rand_ajuste(y, o["labels"]), "temps_s": t})
    b, t = chrono(lambda: A.em_variationnel(X, Kmax, priori=pr, n_init=_n_init(rapide), graine=_g("variantes")))
    lignes.append({"methode": f"VB (lot complet, Kmax={Kmax})", "ARI": A.indice_rand_ajuste(y, b["labels"]), "temps_s": t,
                   "actives": int((b["Nk"] / len(X) >= float(PARAM.valeur("seuil_actif"))).sum())})
    sv, t = chrono(lambda: A.svi_gmm(X, Kmax, pr, taille_lot=int(v["svi_lot"]), n_epoques=int(v["epoques"]),
                                     tau=float(v["svi_tau"]), kappa=float(v["svi_kappa"]), graine=_g("variantes")))
    lignes.append({"methode": f"SVI (Kmax={Kmax})", "ARI": A.indice_rand_ajuste(y, sv["labels"]), "temps_s": t,
                   "actives": int((sv["Nk"] / len(X) >= float(PARAM.valeur("seuil_actif"))).sum())})
    return {"lignes": lignes, "artefacts": {"sem_ll_hist": s["ll_hist"], "online_ll_hist": o["ll_hist"]}}


def unite_hmm(memo, rapide):
    n = _n_init(rapide)
    Am, Bm, p0 = (torch.tensor(HMM_DISCRET[k], dtype=torch.float64) for k in ("A", "B", "pi0"))
    obs = A.simuler_hmm(Am, Bm, p0, HMM_DISCRET["T"], graine=_g("hmm", "discret"))
    _, _, ll_vrai = A._fb_normalise(Am, torch.log(Bm[:, obs].T), p0)
    bw = max((A.baum_welch([obs], 2, emission="discrete", V=2, graine=_g("hmm", "bw", s)) for s in range(n)),
             key=lambda d: d["loglik"])
    perm = [0, 1] if bw["B"][0, 1] > bw["B"][1, 1] else [1, 0]           # états identifiés à une permutation près
    hd = torch.tensor(bw["ll_hist"])
    Ag = torch.tensor(HMM_GAUSS["A"], dtype=torch.float64)
    g = A.generateur(_g("hmm", "gauss"))
    z, r_ = 0, []
    for _ in range(HMM_GAUSS["T"]):
        r_.append(HMM_GAUSS["mu"][z] + HMM_GAUSS["sigma"][z] * float(torch.randn(1, generator=g, dtype=torch.float64)))
        z = int(torch.multinomial(Ag[z], 1, generator=g))
    bg = max((A.baum_welch([torch.tensor(r_, dtype=torch.float64)], 2, emission="gauss", graine=_g("hmm", "bg", s))
              for s in range(n)), key=lambda d: d["loglik"])
    o = torch.argsort(bg["var"])
    hg = torch.tensor(bg["ll_hist"])
    lignes = [{"modele": "discret", "loglik": bw["loglik"], "loglik_vrais_parametres": float(ll_vrai),
               "baisse_max": float((hd[:-1] - hd[1:]).clamp(min=0).max()), "iterations": bw["n_iter"],
               "converge": float(bw["converge"]), "A_estimee": bw["A"][perm][:, perm].tolist(), "A_vraie": HMM_DISCRET["A"],
               "B_estimee": bw["B"][perm].tolist(), "B_vraie": HMM_DISCRET["B"]},
              {"modele": "gaussien", "loglik": bg["loglik"], "baisse_max": float((hg[:-1] - hg[1:]).clamp(min=0).max()),
               "iterations": bg["n_iter"], "converge": float(bg["converge"]),
               "sigma_estimes": bg["var"][o].sqrt().tolist(), "sigma_vrais": HMM_GAUSS["sigma"],
               "A_estimee": bg["A"][o][:, o].tolist(), "A_vraie": HMM_GAUSS["A"]}]
    return {"lignes": lignes}


def unites(rapide: bool):
    U = lambda c, f, **k: E.Unite("illustrations", c, "etape_illustrations", f, k)
    us = [U("k6", "unite_k6"), U("k3", "unite_k3"), U("iris", "unite_iris"), U("aberrantes", "unite_aberrantes"),
          U("bic_aic", "unite_bic_aic"), U("variantes", "unite_variantes"), U("hmm", "unite_hmm")]
    us += [U(f"alpha0/a={i}/priors={p}", "unite_alpha0", i=i, priors=p) for i in range(N_ALPHA0)
           for p in ("empiriques", "diffus")]
    R = 3 if rapide else int(PARAM.valeur("replications")["scenarios"])
    us += [U(f"initialisation/init={i}/rep={r:03d}", "unite_initialisation", init=i, rep=r)
           for i in ("kmeans", "aleatoire") for r in range(R)]
    us += [U(f"covariance/type={c}", "unite_covariance", cov_type=c) for c in A.TYPES_COVARIANCE]
    return us


def agreger(rapide: bool):
    for c in ("k6", "k3", "iris", "aberrantes", "bic_aic", "variantes", "hmm"):
        E.ecrire_csv(f"illustrations_{c}", E.lignes("illustrations", rapide, c), rapide)
    E.ecrire_csv("illustrations_alpha0", E.lignes("illustrations", rapide, "alpha0/"), rapide)
    E.ecrire_csv("illustrations_covariance", E.lignes("illustrations", rapide, "covariance/"), rapide)
    L = E.lignes("illustrations", rapide, "initialisation/")
    E.ecrire_csv("illustrations_initialisation_brut", L, rapide)
    resume = {}
    for l in L:
        resume.setdefault((l["initialisation"], l["modele"]), []).append(l["composantes_actives"])
    E.ecrire_csv("illustrations_initialisation", [
        {"initialisation": i, "modele": m, "n": len(a), **{f"actives_{k}": sum(x == k for x in a) for k in range(1, _kmax() + 1)}}
        for (i, m), a in resume.items()], rapide)
