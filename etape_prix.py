"""
================================================================================
ÉTAPE « prix » : régimes de tension des prix alimentaires sur les marchés du Cameroun (cas pratique)
================================================================================

Données : base de prix du PAM (HDX, CC BY-IGO), prix de détail du maïs blanc, du riz importé et du niébé ;
une observation = (marché, mois) ; variables = écarts du log-prix au niveau des 12 mois précédents
(donnees.charger_prix). Validation TEMPORELLE : apprentissage jusqu'à prix_fin_apprentissage, test ensuite.
Standardisation par la moyenne et l'écart-type de l'APPRENTISSAGE seul (appliqués tels quels au test).

Unités :
  reference            EM-BIC sur tout l'apprentissage (K de 1 à Kmax) : K_ref et modèle générateur du semi-synthétique
  sous/N=n/rep=r       n observations tirées dans l'apprentissage ; tous les bras ; évaluation sur TOUT le test
  semi/N=n/rep=r       jeu tiré du modèle de référence : vérité connue (K_ref, partition)
  couverture/N=n/rep=r couverture à 90 %, INCONDITIONNELLE, sur le semi-synthétique (VB : crédibilité ; EM : bootstrap
                       à démarrage chaud, alignement hongrois) ; une indicatrice 0/1 par paramètre scalaire
  sensibilite/rep=r    HP5 : K̂ du VB sur le domaine plausible des priors (calibrage) contre K̂ de l'EM-BIC entre graines
  complet              tous les bras sur tout l'apprentissage ; log-score de chaque observation de test (prévision)
  alerte               probabilité du régime de tension pour chaque observation, avec son intervalle : crédibilité
                       (tirages de q) pour le VB, bootstrap (démarrage chaud) pour l'EM-BIC
Régime de tension : composante ACTIVE dont la moyenne des trois écarts (unités d'origine, log-prix) est la plus
élevée. Hypothèses HP1 à HP6 (famille « prix », Holm) et comparaisons de prévision HPP (famille « prix_prevision »,
Holm), déclarées dans hypotheses.py avant toute exécution.
"""

from __future__ import annotations

import functools

import torch

import algorithmes as A
import comparaison as C
import donnees as DO
import etapes as E
import hypotheses as HY
import parametres as PARAM
import persistance as PE
import risque as R
import statistique as S

FAMILLE = "prix"
EFFECTIFS_SOUS = (30, 60, 120, 250)
EFFECTIFS_SEMI = (30, 60, 120, 250, 500)
N_SENSIBILITE = 250
BRAS_COMPLET = ("EM-K", "EM-BIC", "EM-ICL", "MAP-EM", "MAP-cal", "VB-emp", "VB-cal")
BRAS_ALERTE = ("EM-BIC", "VB-emp")
# Comparaisons de prévision déclarées (A, B) : différence de log-score A - B, moyennée par mois de test
DM_DECLARES = [("EM-BIC (plug-in)", "Gaussienne"), ("VB-emp (prédictive)", "Gaussienne"),
               ("VB-emp (prédictive)", "EM-BIC (plug-in)"), ("VB-emp (prédictive)", "VB-emp (plug-in)"),
               ("VB-cal (prédictive)", "VB-emp (prédictive)"), ("MAP-EM (plug-in)", "EM-BIC (plug-in)")]


@functools.lru_cache(maxsize=1)
def donnees():
    """(X_apprentissage, X_test, informations) en variables standardisées par l'apprentissage."""
    d = DO.charger_prix()
    app = d["mois"] <= DO.mois_index(str(PARAM.valeur("prix_fin_apprentissage")))
    centre, echelle = d["X"][app].mean(0), d["X"][app].std(0)
    Z = (d["X"] - centre) / echelle
    return Z[app], Z[~app], {**d, "app": app, "Z": Z, "centre": centre, "echelle": echelle}


def _n_init(rapide):
    n = int(PARAM.valeur("n_init")[FAMILLE])
    return min(n, 3) if rapide else n


def _kmax():
    return int(PARAM.valeur("k_max")[FAMILLE])


def _reference(rapide, etape="prix"):
    r = E.magasin(etape, rapide).lire("reference")
    if r is None:
        raise RuntimeError("unité « reference » absente : elle est calculée avant les plans sous, semi et couverture")
    return r["artefacts"]


def regime_tension(moyennes_std, actives, info) -> int:
    """Indice de la composante active dont la moyenne des écarts (unités d'origine) est la plus élevée."""
    orig = moyennes_std * info["echelle"] + info["centre"]
    score = orig.mean(1).clone()
    score[~actives] = float("-inf")
    return int(score.argmax())


# ------------------------------------------------------------------------------ référence
def unite_reference(memo, rapide):
    Xtr, _, _ = donnees()
    ref = C.choisir_k_critere(Xtr, _kmax(), "bic", _n_init(rapide), PE.graine("prix", "reference") % 2 ** 31, memo)
    K = len(ref["pi"])
    return {"lignes": [{"K_ref": K, "loglik": ref["loglik"], "converge": float(ref["converge"]),
                        **{f"BIC_K={k}": v for k, v in ref["critere_par_k"].items()}}],
            "artefacts": {"K_ref": K, "modele": {"pi": ref["pi"], "mu": ref["mu"], "cov": ref["cov"]},
                          "critere_par_k": ref["critere_par_k"], "ajustement": PE.resume_ajustement(ref)}}


# ------------------------------------------------------------------------------ sous-échantillons réels, hold-out temporel
def unite_sous(memo, rapide, N, rep, etape_reference="prix"):
    Xtr, Xte, _ = donnees()
    K_ref = int(_reference(rapide, etape_reference)["K_ref"])
    idx = torch.randperm(len(Xtr), generator=A.generateur(PE.graine("prix", "echantillon", N, rep)))[:N]
    sortie = C.bras_protocole(Xtr[idx], K_ref, _kmax(), _n_init(rapide), PE.graine("prix", "ajustement", N, rep) % 2 ** 31,
                              FAMILLE, memo=memo)
    lignes, ajust = [], {}
    for nom, res in sortie.items():
        base = {"plan": "sous", "N": str(N), "rep": rep, "bras": nom}
        if "echec" in res:
            lignes.append(base | {"echec": True, "degenere": 1.0})
            continue
        lignes.append(base | {
            "echec": False, "k_hat": res["k_hat"], "k_ajuste": res["k_ajuste"],
            "ll_test": C.logdens_plugin(res, Xte),
            "ll_test_predictive": C.logdens_predictive_vb(res, Xte) if nom.startswith("VB") else float("nan"),
            "degenere": float(res["degenere"]), "petite_composante": float(res.get("petite_composante", False)),
            "plancher_regularisation": float(res.get("plancher_regularisation", False)),
            "converge": float(res["converge"]), "n_iter": res["n_iter"], "temps_s": res["temps_total"]})
        ajust[nom] = PE.resume_ajustement(res, avec_r=False)
    return {"lignes": lignes, "artefacts": {"idx_apprentissage": idx, "ajustements": ajust}}


# ------------------------------------------------------------------------------ semi-synthétique (vérité connue)
def unite_semi(memo, rapide, N, rep, etape_reference="prix"):
    ref = _reference(rapide, etape_reference)
    K_ref = int(ref["K_ref"])
    Xs, z = C.simuler_depuis_modele(ref["modele"], N, PE.graine("prix", "semi", N, rep))
    sortie = C.bras_protocole(Xs, K_ref, _kmax(), _n_init(rapide), PE.graine("prix", "semi_ajustement", N, rep) % 2 ** 31,
                              FAMILLE, bras=("EM-K", "EM-Kmax", "EM-BIC", "EM-ICL", "MAP-EM", "MAP-cal", "VB-emp", "VB-cal"),
                              memo=memo)
    lignes = []
    for nom, res in sortie.items():
        base = {"plan": "semi", "N": str(N), "rep": rep, "bras": nom}
        if "echec" in res:
            lignes.append(base | {"echec": True})
            continue
        lignes.append(base | {"echec": False, "k_hat": res["k_hat"], "erreur_k": abs(res["k_hat"] - K_ref),
                              "ARI": A.indice_rand_ajuste(z, res["labels"]), "degenere": float(res["degenere"]),
                              "temps_s": res["temps_total"]})
    return {"lignes": lignes, "artefacts": {"X": Xs, "z": z, "K_ref": K_ref,
                                            "ajustements": {k: PE.resume_ajustement(v) for k, v in sortie.items() if "echec" not in v}}}


# ------------------------------------------------------------------------------ couverture des intervalles
def tirages_q(P, n, graine):
    """Tirages de (pi, mu, Sigma) sous q (covariance pleine) : pi ~ Dir(alpha), Lambda ~ W(W, nu), mu | Lambda ~ N(m, (beta Lambda)^-1)."""
    dist = torch.distributions
    with torch.random.fork_rng():
        torch.manual_seed(graine)
        pis = dist.Dirichlet(P["alpha"]).sample((n,))
        mus, covs = [], []
        for k in range(len(P["alpha"])):
            lam = dist.Wishart(df=P["nu"][k], covariance_matrix=P["W"][k]).sample((n,))
            mus.append(dist.MultivariateNormal(P["m"][k], precision_matrix=P["beta"][k] * lam).sample())
            covs.append(torch.linalg.inv(lam))
    return pis, torch.stack(mus, dim=1), torch.stack(covs, dim=1)


def couverts(ref, pi_inf, pi_sup, mu_inf, mu_sup, actives_centres, actives_idx):
    """Appariement hongrois composantes vraies / actives ; une composante vraie non appariée n'est pas couverte.
    Couverture de mu PAR COORDONNÉE (liste de 0/1) : chaque intervalle marginal à 90 % se compare au niveau nominal."""
    K, D = ref["mu"].shape
    out = []
    if len(actives_idx) == 0:
        return [(k, 0.0, [0.0] * D) for k in range(K)]
    n = max(K, len(actives_idx))
    cout = torch.full((n, n), 1e6, dtype=torch.float64)
    cout[:K, :len(actives_idx)] = torch.cdist(ref["mu"], actives_centres).pow(2)
    col = A.hongrois(cout)
    for k in range(K):
        j = int(col[k])
        if j >= len(actives_idx):
            out.append((k, 0.0, [0.0] * D))
            continue
        jj = actives_idx[j]
        cp = float(pi_inf[jj] <= ref["pi"][k] <= pi_sup[jj])
        cm = ((mu_inf[jj] <= ref["mu"][k]) & (ref["mu"][k] <= mu_sup[jj])).double().tolist()
        out.append((k, cp, cm))
    return out


def lignes_couverture(N, rep, methode, couv):
    lignes = []
    for k, cp, cm in couv:
        lignes.append({"N": str(N), "rep": rep, "methode": methode, "param": "pi", "composante": k, "couvert": cp})
        lignes += [{"N": str(N), "rep": rep, "methode": methode, "param": "mu", "composante": k, "coordonnee": j, "couvert": c}
                   for j, c in enumerate(cm)]
    return lignes


def unite_couverture(memo, rapide, N, rep):
    ref = _reference(rapide)
    K_ref = int(ref["K_ref"])
    vrai = ref["modele"]
    Xs, _ = C.simuler_depuis_modele(vrai, N, PE.graine("prix", "semi", N, rep))
    n_init = _n_init(rapide)
    g_fit = PE.graine("prix", "semi_ajustement", N, rep) % 2 ** 31
    q = torch.tensor([0.05, 0.95], dtype=torch.float64)
    vb = memo("VB-emp", lambda: A.em_variationnel(Xs, _kmax(), priori=C.priors_bras(Xs, _kmax(), FAMILLE)["emp"],
                                                   n_init=n_init, graine=g_fit))
    act = (vb["Nk"] / N >= float(PARAM.valeur("seuil_actif"))).nonzero().flatten()
    nt = 200 if rapide else int(PARAM.valeur("n_tirages_posterieur"))
    pis, mus, _ = tirages_q(vb["P"], nt, PE.graine("prix", "tirages", N, rep) % 2 ** 31)
    pi_b, mu_b = torch.quantile(pis, q, dim=0), torch.quantile(mus, q, dim=0)
    lignes = lignes_couverture(N, rep, "VB", couverts(vrai, pi_b[0], pi_b[1], mu_b[0], mu_b[1], vb["m"][act], act))
    em = memo("EM-K", lambda: A.em_classique(Xs, K_ref, n_init=n_init, graine=g_fit))
    B = 50 if rapide else int(PARAM.valeur("n_bootstrap_modele"))
    pis_b, mus_b = [], []
    for b in range(B):
        ib = torch.randint(N, (N,), generator=A.generateur(PE.graine("prix", "bootstrap", N, rep, b)))
        eb = C.em_demarrage_chaud(Xs[ib], em)
        c = A.hongrois(torch.cdist(em["mu"], eb["mu"]).pow(2))
        pis_b.append(eb["pi"][c])
        mus_b.append(eb["mu"][c])
    pis_b, mus_b = torch.stack(pis_b), torch.stack(mus_b)
    pi_e, mu_e = torch.quantile(pis_b, q, dim=0), torch.quantile(mus_b, q, dim=0)
    lignes += lignes_couverture(N, rep, "bootstrap EM",
                                couverts(vrai, pi_e[0], pi_e[1], mu_e[0], mu_e[1], em["mu"], torch.arange(K_ref)))
    return {"lignes": lignes, "artefacts": {"B": B, "tirages_q": nt}}


# ------------------------------------------------------------------------------ sensibilité aux hyperparamètres
def configs_plausibles():
    """Configurations de la recherche de calibrage dont le score est à moins de la marge LL du meilleur (dernière étape)."""
    import json
    f = PARAM.dossier_calibrage() / "priors.json"
    if not f.exists():
        return [PARAM.valeur("priors_vb_calibres")[FAMILLE]]
    d = json.loads(f.read_text(encoding="utf-8"))
    evals = d["details"]["evaluations"][FAMILLE]
    derniere = max(x["etape"] for x in evals)
    finales = [e for e in evals if e["etape"] == derniere]
    meilleur = max(e["score"] for e in finales)
    marge = float(PARAM.valeur("marges_equivalence")["LL"])
    return [e["config"] for e in finales if e["score"] >= meilleur - marge] or [d["valeurs"]["priors_vb_calibres"][FAMILLE]]


GRAINES_SENSIBILITE = 3


def unite_sensibilite(memo, rapide, rep):
    """
    HP5 (RH2), sur UN sous-échantillon de l'apprentissage par réplication : variance de K̂ du VB entre les configurations
    de priors plausibles (calibrage), et variance de K̂ de l'EM entre ses propres choix (critère BIC ou ICL, trois graines).
    Une ligne par source (bras « VB-priors » et « EM-choix », métrique var_k) : la comparaison est appariée par réplication.
    """
    Xtr, _, _ = donnees()
    idx = torch.randperm(len(Xtr), generator=A.generateur(PE.graine("prix", "sensibilite", rep)))[:N_SENSIBILITE]
    Xs = Xtr[idx]
    D = Xs.shape[1]
    k_vb, k_em, detail = [], [], []
    for i, cfg in enumerate(configs_plausibles()):
        pr = A.PrioriNW(cfg["alpha0"], Xs.mean(0), cfg["beta0"], cfg["echelle_w0"] * torch.cov(Xs.T).reshape(D, D),
                        D + cfg["nu0_plus"])
        v = memo(f"VB/cfg={i}", lambda pr=pr: A.em_variationnel(Xs, _kmax(), priori=pr, n_init=_n_init(rapide),
                                                               graine=PE.graine("prix", "sens_fit", rep) % 2 ** 31))
        k_vb.append(C.k_hat(v["Nk"], len(Xs)))
        detail.append({"source": "VB-priors", "config": i, "k_hat": k_vb[-1]})
    for crit in ("bic", "icl"):
        for s in range(GRAINES_SENSIBILITE):
            eb = C.choisir_k_critere(Xs, _kmax(), crit, _n_init(rapide), PE.graine("prix", "sens_em", rep, s) % 2 ** 31, memo,
                                     prefixe=f"s={s}/")
            k_em.append(C.k_hat(eb["Nk"], len(Xs)))
            detail.append({"source": "EM-choix", "critere": crit, "graine": s, "k_hat": k_em[-1]})

    def var(k):
        return float(torch.tensor(k, dtype=torch.float64).var()) if len(k) > 1 else 0.0
    base = {"plan": "sensibilite", "N": str(N_SENSIBILITE), "rep": rep}
    return {"lignes": [base | {"bras": "VB-priors", "var_k": var(k_vb), "n_valeurs": len(k_vb), "k_moyen": sum(k_vb) / len(k_vb)},
                       base | {"bras": "EM-choix", "var_k": var(k_em), "n_valeurs": len(k_em), "k_moyen": sum(k_em) / len(k_em)}],
            "artefacts": {"idx": idx, "detail": detail}}


# ------------------------------------------------------------------------------ apprentissage complet : prévision
def _logscores(res, X, predictive):
    """Log-densité de chaque observation : plug-in (pi, mu, Sigma) ou prédictive du VB (mélange de Student)."""
    if predictive:
        return R.log_predictive_variationnel(X, res["P"])
    p = C.params_plugin(res)
    return A._etape_e(X, p["pi"], p["mu"], p["cov"])[1]


def unite_complet(memo, rapide):
    Xtr, Xte, d = donnees()
    K_ref = int(_reference(rapide)["K_ref"])
    g = PE.graine("prix", "complet") % 2 ** 31
    sortie = C.bras_protocole(Xtr, K_ref, _kmax(), _n_init(rapide), g, FAMILLE, bras=BRAS_COMPLET, memo=memo)
    gauss = memo("EM/K=1", lambda: A.em_classique(Xtr, 1, n_init=1, graine=g))
    ls = {"Gaussienne": _logscores(gauss, Xte, False)}
    lignes = []
    for nom, res in sortie.items():
        if "echec" in res:
            lignes.append({"bras": nom, "echec": True})
            continue
        ls[f"{nom} (plug-in)"] = _logscores(res, Xte, False)
        if nom.startswith("VB"):
            ls[f"{nom} (prédictive)"] = _logscores(res, Xte, True)
        lignes.append({"bras": nom, "echec": False, "k_hat": res["k_hat"], "k_ajuste": res["k_ajuste"],
                       "ll_apprentissage": float(_logscores(res, Xtr, False).mean()),
                       "ll_test": float(ls[f"{nom} (plug-in)"].mean()),
                       "ll_test_predictive": float(ls[f"{nom} (prédictive)"].mean()) if nom.startswith("VB") else float("nan"),
                       "poids_actifs": " ; ".join(f"{float(p):.3f}" for p in sorted(res["pi"].tolist(), reverse=True)
                                                  if p * len(Xtr) >= float(PARAM.valeur("seuil_actif")) * len(Xtr)),
                       "converge": float(res["converge"]), "temps_s": res["temps_total"]})
    return {"lignes": lignes, "artefacts": {"logscores": ls, "mois_test": d["mois"][~d["app"]],
                                            "ajustements": {k: PE.resume_ajustement(v, avec_r=False)
                                                            for k, v in sortie.items() if "echec" not in v}}}


# ------------------------------------------------------------------------------ alerte : probabilité du régime de tension
def _proba_composante(X, pi, mu, cov, k, lot=256):
    """P(z = k | x, theta) pour un lot de paramètres (S, K, ...) : tenseur (S, N), calculé par paquets de tirages."""
    out = []
    for s0 in range(0, len(pi), lot):
        sl = slice(s0, s0 + lot)
        dist = torch.distributions.MultivariateNormal(mu[sl][:, :, None, :], covariance_matrix=cov[sl][:, :, None, :, :])
        lp = dist.log_prob(X[None, None, :, :]) + torch.log(pi[sl].clamp(min=1e-300))[:, :, None]
        out.append(torch.softmax(lp, dim=1)[:, k, :])
    return torch.cat(out)


def unite_alerte(memo, rapide):
    Xtr, _, d = donnees()
    Z = d["Z"]
    K_ref = int(_reference(rapide)["K_ref"])
    g = PE.graine("prix", "complet") % 2 ** 31
    sortie = C.bras_protocole(Xtr, K_ref, _kmax(), _n_init(rapide), g, FAMILLE, bras=BRAS_ALERTE, memo=memo)
    seuil = float(PARAM.valeur("seuil_actif"))
    art = {"mois": d["mois"], "marche": d["marche"], "app": d["app"], "X_origine": d["X"], "marches": d["marches"],
           "regions": d["regions"], "lat": d["lat"], "lon": d["lon"], "variables": d["variables"]}
    lignes = []
    for nom, res in sortie.items():
        if "echec" in res:
            continue
        p = C.params_plugin(res)
        actives = res["Nk"] / len(Xtr) >= seuil
        k = regime_tension(p["mu"], actives, d)
        if nom.startswith("VB"):
            nt = 500 if rapide else int(PARAM.valeur("n_tirages_posterieur"))
            pis, mus, covs = tirages_q(res["P"], nt, PE.graine("prix", "alerte_tirages") % 2 ** 31)
            tir = _proba_composante(Z, pis, mus, covs, k)
            proba = tir.mean(0)                                  # probabilité a posteriori moyenne sous q
        else:
            B = 50 if rapide else int(PARAM.valeur("n_bootstrap_modele"))
            tir = []
            for b in range(B):
                ib = torch.randint(len(Xtr), (len(Xtr),), generator=A.generateur(PE.graine("prix", "alerte_boot", b)))
                eb = C.em_demarrage_chaud(Xtr[ib], res)
                c = A.hongrois(torch.cdist(res["mu"], eb["mu"]).pow(2))
                tir.append(_proba_composante(Z, eb["pi"][None], eb["mu"][None], eb["cov"][None], int(c[k]))[0])
            tir = torch.stack(tir)
            proba = _proba_composante(Z, p["pi"][None], p["mu"][None], p["cov"][None], k)[0]
        ic = torch.quantile(tir, torch.tensor([0.05, 0.95], dtype=torch.float64), dim=0)
        moy_orig = p["mu"][k] * d["echelle"] + d["centre"]
        art[nom] = {"proba": proba.float(), "ic": ic.float(), "k_tension": k, "k_hat": res["k_hat"],
                    "moyenne_tension": moy_orig, "poids_tension": float(p["pi"][k])}
        for periode, m in (("apprentissage", d["app"]), ("test", ~d["app"])):
            lignes.append({"bras": nom, "periode": periode, "k_hat": res["k_hat"], "poids_tension": float(p["pi"][k]),
                           **{f"moyenne_{v}": float(x) for v, x in zip(DO.NOMS_PANIER, moy_orig)},
                           "part_alerte": float((proba[m] > 0.5).double().mean()),
                           "largeur_ic90_moyenne": float((ic[1] - ic[0])[m].mean()),
                           "part_ic_chevauche_0.5": float(((ic[0] <= 0.5) & (ic[1] >= 0.5))[m].double().mean())})
    if all(n in art for n in BRAS_ALERTE):
        a, b = art["EM-BIC"]["proba"] > 0.5, art["VB-emp"]["proba"] > 0.5
        lignes.append({"bras": "accord EM-BIC / VB-emp", "periode": "toutes", "part_alerte": float((a == b).double().mean())})
    return {"lignes": lignes, "artefacts": art}


# ------------------------------------------------------------------------------ étape
def unites(rapide: bool):
    rep = PARAM.valeur("replications")
    R_sous = 2 if rapide else int(rep["prix_sous"])
    R_semi = 2 if rapide else int(rep["prix_semi"])
    dep = ("reference",)
    us = [E.Unite("prix", "reference", "etape_prix", "unite_reference")]
    for N in EFFECTIFS_SOUS:
        us += [E.Unite("prix", f"sous/N={N:04d}/rep={r:03d}", "etape_prix", "unite_sous", dict(N=N, rep=r), depend=dep)
               for r in range(R_sous)]
    for N in EFFECTIFS_SEMI:
        for r in range(R_semi):
            us.append(E.Unite("prix", f"semi/N={N:04d}/rep={r:03d}", "etape_prix", "unite_semi", dict(N=N, rep=r), depend=dep))
            if N >= 120:
                us.append(E.Unite("prix", f"couverture/N={N:04d}/rep={r:03d}", "etape_prix", "unite_couverture",
                                  dict(N=N, rep=r), depend=dep))
    us += [E.Unite("prix", f"sensibilite/rep={r:03d}", "etape_prix", "unite_sensibilite", dict(rep=r))
           for r in range(2 if rapide else int(rep["prix_sensibilite"]))]
    us += [E.Unite("prix", "complet", "etape_prix", "unite_complet", depend=dep),
           E.Unite("prix", "alerte", "etape_prix", "unite_alerte", depend=dep)]
    return us


def _descriptif():
    _, _, d = donnees()
    out = []
    for periode, m in (("apprentissage", d["app"]), ("test", ~d["app"])):
        X = d["X"][m]
        l = {"periode": periode, "observations": int(m.sum()), "marches": len(set(d["marche"][m].tolist())),
             "regions": len({d["regions"][i] for i in d["marche"][m].tolist()}),
             "debut": DO.mois_texte(int(d["mois"][m].min())), "fin": DO.mois_texte(int(d["mois"][m].max()))}
        for j, v in enumerate(DO.NOMS_PANIER):
            x = X[:, j]
            z = (x - x.mean()) / x.std()
            l.update({f"moyenne_{v}": float(x.mean()), f"ecart_type_{v}": float(x.std()),
                      f"kurtosis_exc_{v}": float((z ** 4).mean() - 3.0)})
        out.append(l)
    return out


def agreger(rapide: bool):
    E.ecrire_csv("prix_descriptif", _descriptif(), rapide)
    E.ecrire_csv("prix_releves_ecartes", donnees()[2]["ecartes"], rapide)
    ref = E.magasin("prix", rapide).lire("reference")
    if ref is not None:
        E.ecrire_csv("prix_reference", [{"K": int(k), "BIC": v, "retenu": int(k) == ref["artefacts"]["K_ref"]}
                                        for k, v in ref["artefacts"]["critere_par_k"].items()], rapide)
    L = E.lignes("prix", rapide, "sous/") + E.lignes("prix", rapide, "semi/") + E.lignes("prix", rapide, "sensibilite/")
    E.ecrire_csv("prix_brut", L, rapide)
    alpha = float(PARAM.valeur("alpha_test"))
    nb = int(PARAM.valeur("n_bootstrap_ic"))
    hyp = [{"id": h.id, "axe": h.axe, "enonce": h.enonce, "test": h.test, "marge": HY.marge(h),
            "diffs": HY.diffs(h, L), "exclues": HY.exclusions(h, L)} for h in HY.famille("prix")]
    dec = S.decider_famille(hyp, alpha, nb)
    # HP4 (coût) : rapport des temps médians EM-BIC / VB-emp, mesurés par l'étape « chronometrage » (sans concurrence)
    for l in E.lignes("chronometrage", rapide, "pipeline/"):
        dec.append({"id": f"HP4-N{l['N']}", "axe": "Coût", "test": "intervalle",
                    "enonce": "Temps du pipeline EM-BIC divisé par le temps d'un VB (ratio > 1 : EM-BIC plus coûteux)",
                    "estimation": l["ratio_median"], "ic_bas": l["ratio_ic_bas"], "ic_haut": l["ratio_ic_haut"],
                    "decision": "ratio > 1" if l["ratio_ic_bas"] > 1 else ("ratio < 1" if l["ratio_ic_haut"] < 1 else "non tranché")})
    # HP6 : couverture inconditionnelle ; IC bootstrap PAR GRAPPES (réplications), les indicatrices d'une même
    # réplication étant dépendantes
    Lc = E.lignes("prix", rapide, "couverture/")
    E.ecrire_csv("prix_couverture_brut", Lc, rapide)
    for meth in ("VB", "bootstrap EM"):
        for par in ("pi", "mu"):
            v = [l for l in Lc if l["methode"] == meth and l["param"] == par]
            if not v:
                continue
            grappes = {}
            for l in v:
                grappes.setdefault((l["N"], l["rep"]), []).append(float(l["couvert"]))
            p, lo, hi = S.ic_bootstrap([sum(g) / len(g) for g in grappes.values()], nb,
                                       graine=PE.graine("prix", "HP6", meth, par) % 2 ** 31)
            dec.append({"id": f"HP6-{meth}-{par}", "axe": "Incertitude", "test": "intervalle",
                        "enonce": f"Couverture à 90 % ({meth}, {par}), inconditionnelle", "estimation": p, "ic_bas": lo,
                        "ic_haut": hi, "n": len(v), "n_grappes": len(grappes),
                        "decision": "< 90 %" if hi < 0.9 else (">= 90 %" if lo >= 0.9 else "compatible avec 90 %")})
    for d in dec:
        d["rh"], d["attendu"] = HY.rattachement(d["id"])
    E.ecrire_csv("prix_decisions", dec, rapide)
    resume = {}
    for l in L:
        if not l.get("echec") and l["plan"] != "sensibilite":
            resume.setdefault((l["plan"], l["N"], l["bras"]), []).append(l)
    out = []
    for (pl, N, br), ls in sorted(resume.items(), key=lambda t: (t[0][0], int(t[0][1]), t[0][2])):
        def m(c):
            v = [x[c] for x in ls if c in x and x[c] == x[c]]
            return sum(v) / len(v) if v else float("nan")
        out.append({"plan": pl, "N": N, "bras": br, "n": len(ls), "k_hat": m("k_hat"), "erreur_k": m("erreur_k"),
                    "ARI": m("ARI"), "ll_test": m("ll_test"), "ll_test_predictive": m("ll_test_predictive"),
                    "degenere": m("degenere"), "temps_s": m("temps_s")})
    E.ecrire_csv("prix_resume", out, rapide)
    c = E.magasin("prix", rapide).lire("complet")
    if c is not None:
        E.ecrire_csv("prix_complet", c["lignes"], rapide)
        E.ecrire_csv("prix_diebold_mariano", diebold_mariano(c["artefacts"], alpha), rapide)
    a = E.magasin("prix", rapide).lire("alerte")
    if a is not None:
        E.ecrire_csv("prix_alerte", a["lignes"], rapide)


def diebold_mariano(art, alpha):
    """
    Comparaisons de prévision déclarées (famille « prix_prevision », Holm). Les observations de test d'un même mois
    partagent les chocs communs : la différence de log-score est d'abord MOYENNÉE PAR MOIS, puis le test de
    Diebold-Mariano (correction de Harvey et al. 1997) porte sur la série mensuelle.
    """
    mois = art["mois_test"]
    ordre = torch.unique(mois)
    dm = []
    for i, (a_, b_) in enumerate(DM_DECLARES, start=1):
        if a_ not in art["logscores"] or b_ not in art["logscores"]:
            continue
        d = art["logscores"][a_] - art["logscores"][b_]
        serie = torch.stack([d[mois == m].mean() for m in ordre])
        s, p = R.diebold_mariano(serie, h=1)
        dm.append({"id": f"HPP{i}", "rh": HY.rattachement(f"HPP{i}")[0], "A": a_, "B": b_,
                   "ecart_logscore_moyen": float(d.mean()), "n_mois": len(serie),
                   "n_observations": len(d), "DM": s, "p": p})
    for l, ph in zip(dm, S.holm([l["p"] for l in dm])):
        l["p_holm"] = ph
        l["decision"] = ("A > B" if l["ecart_logscore_moyen"] > 0 else "A < B") if ph < alpha else "différence non démontrée"
    return dm
