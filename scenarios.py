"""
================================================================================
ÉTAPE « scenarios » : scénarios synthétiques S1 à S10
================================================================================

Une unité = (scénario, valeur du paramètre, réplication). Les données (apprentissage et test), toutes
les graines (dérivées par rôle : données, test, ajustement) et tous les ajustements sont enregistrés.
Bras : EM-K (K connu), EM-Kmax, EM-BIC, EM-ICL, MAP-EM, MAP-cal, VB-emp, VB-diff, VB-cal, et, pour S3,
VB à Kmax = K choisi. Même critère d'arrêt, même nombre de relances (registre, famille « synthetique »).
Hypothèses confirmatoires : hypotheses.py (famille « scenarios ») ; S8, S9, S10 sont descriptifs.
S7 : l'ARI est calculé sur les seuls points non aberrants (déclaré avant l'analyse).
"""

from __future__ import annotations

import torch

import algorithmes as A
import comparaison as C
import donnees as DO
import etapes as E
import hypotheses as HY
import parametres as PARAM
import persistance as PE
import statistique as S

FAMILLE = "synthetique"


def _plan(rapide: bool):
    """Points du plan d'expérience : (scénario, paramètre, fabrique de données, K vrai, K choisi)."""
    P = []
    for d in (1, 2, 3, 4, 5):
        P.append(("S1", str(d), {"type": "gauss", "n": 300, "centres": ("triangle", d, 2), "sigma": 1.0}, 3, 3))
    P.append(("S2", "80/15/5", {"type": "gauss", "n": 300, "centres": ("triangle", 5, 2), "sigma": 1.0,
                                "poids": [0.8, 0.15, 0.05]}, 3, 3))
    for kv in (4, 5, 6):
        P.append(("S3", f"Kvrai={kv}", {"type": "gauss", "n": 100 * kv, "centres": ("ligne", kv, 4.0), "sigma": 1.0}, kv, 3))
    P.append(("S4", "Student nu=3", {"type": "student", "n": 300, "centres": ("triangle", 5, 2), "sigma": 1.0, "nu": 3.0}, 3, 3))
    for D in (2, 5, 10, 20):
        P.append(("S5", str(D), {"type": "gauss", "n": 300, "centres": ("triangle", 6, D), "sigma": 1.0}, 3, 3))
    for n in (30, 60, 120, 300, 1000):
        P.append(("S6", str(n), {"type": "gauss", "n": n, "n_test": 1000, "centres": ("triangle", 4, 2), "sigma": 1.0}, 3, 3))
    for prop in (0.01, 0.05, 0.1):
        for amp in (5.0, 10.0, 20.0):
            P.append(("S7", f"prop={prop};amp={amp}", {"type": "gauss", "n": 300, "centres": ("triangle", 5, 2), "sigma": 1.0,
                                                        "aberrations": (prop, amp)}, 3, 3))
    return P


def _centres(spec):
    if spec[0] == "triangle":
        return DO.centres_triangle(spec[1], 1.0, spec[2])
    return DO.centres_ligne(spec[1], spec[2])


def fabriquer(f: dict, graine: int, partie: str):
    """Données d'un point du plan. Les aberrations ne touchent que l'apprentissage ; masque des points non aberrants."""
    n = f["n"] if partie == "train" else f.get("n_test", f["n"])
    if f["type"] == "student":
        X, y = DO.gen_student(n, _centres(f["centres"]), f["sigma"], f["nu"], graine=graine)
    else:
        X, y = DO.gen_gauss(n, _centres(f["centres"]), f["sigma"], poids=f.get("poids"), graine=graine)
    propre = torch.ones(n, dtype=torch.bool)
    if partie == "train" and "aberrations" in f:
        prop, amp = f["aberrations"]
        gg = A.generateur(PE.graine(graine, "aberrations"))
        m = int(round(prop * n))
        idx = torch.randperm(n, generator=gg)[:m]
        dirs = torch.randn(m, X.shape[1], generator=gg)
        X[idx] = X.mean(0) + amp * dirs / dirs.norm(dim=1, keepdim=True)
        propre[idx] = False
    return X, y, propre


def unite_scenario(memo, rapide, scenario, parametre, fabrique, k_vrai, k_choisi, rep, bras=None):
    n_init = int(PARAM.valeur("n_init")[FAMILLE])
    if rapide:
        n_init = min(n_init, 3)
    kmax = int(PARAM.valeur("k_max")[FAMILLE])
    g_data = PE.graine(scenario, parametre, "donnees", rep)
    g_test = PE.graine(scenario, parametre, "test", rep)
    g_fit = PE.graine(scenario, parametre, "ajustement", rep) % (2 ** 31)
    X, y, propre = fabriquer(fabrique, g_data, "train")
    Xt, yt, _ = fabriquer(fabrique, g_test, "test")
    bras = tuple(bras) if bras else C.BRAS
    sortie = C.bras_protocole(X, k_choisi, kmax, n_init, g_fit, "synthetique", bras=bras, memo=memo)
    if k_choisi < k_vrai and (not bras or "VB-Kmax=K" in bras or bras == C.BRAS):
        try:
            v = memo("VB-Kmax=K", lambda: A.em_variationnel(X, k_choisi, alpha0=1.0 / k_choisi, n_init=n_init, graine=g_fit))
            sortie["VB-Kmax=K"] = dict(v, k_hat=C.k_hat(v["Nk"], X.shape[0]), k_ajuste=k_choisi, temps_total=float(v["temps"]))
        except A.EchecNumerique as e:
            sortie["VB-Kmax=K"] = {"echec": str(e)}
    lignes, artefacts = [], {"X": X, "y": y, "propre": propre, "X_test": Xt, "y_test": yt,
                            "graines": {"donnees": g_data, "test": g_test, "ajustement": g_fit}, "ajustements": {}}
    for nom, res in sortie.items():
        base = {"scenario": scenario, "parametre": parametre, "rep": rep, "bras": nom, "N": X.shape[0], "D": X.shape[1]}
        if "echec" in res:
            lignes.append(base | {"echec": True})
            continue
        est_vb = nom.startswith("VB")
        lab = res["labels"]
        lignes.append(base | {
            "echec": False, "k_hat": res["k_hat"], "k_ajuste": res["k_ajuste"], "erreur_k": abs(res["k_hat"] - k_vrai),
            "minoritaire_perdue": float(res["k_hat"] < k_vrai),
            "ARI": A.indice_rand_ajuste(y[propre], lab[propre]),
            "ll_test": C.logdens_plugin(res, Xt),
            "ll_test_predictive": C.logdens_predictive_vb(res, Xt) if est_vb else float("nan"),
            "degenere": float(res["degenere"]), "petite_composante": float(res.get("petite_composante", False)),
            "plancher_regularisation": float(res.get("plancher_regularisation", False)),
            "converge": float(res["converge"]), "n_iter": res["n_iter"], "temps_s": res["temps_total"]})
        artefacts["ajustements"][nom] = PE.resume_ajustement(res)
    return {"lignes": lignes, "artefacts": artefacts}


# ------------------------------------------------------------------------------ S8, S9, S10 (descriptifs)
def unite_alpha0(memo, rapide, cov, alpha0, rep):
    n_init = min(int(PARAM.valeur("n_init")[FAMILLE]), 3 if rapide else 10 ** 9)
    X, y = DO.gen_gauss(300, DO.centres_triangle(5), 1.0, graine=PE.graine("S8", "donnees", rep))
    pr = A.priori_empirique(X, alpha0)
    v = A.em_variationnel(X, 6, priori=pr, cov_type=cov, n_init=n_init, graine=PE.graine("S8", "ajustement", rep) % 2 ** 31)
    return {"lignes": [{"cov": cov, "alpha0": alpha0, "rep": rep, "k_actif": C.k_hat(v["Nk"], 300), "k_Nk1": v["n_actives"],
                        "ARI": A.indice_rand_ajuste(y, v["labels"]), "converge": float(v["converge"]),
                        "critere": v["critere_nom"]}],
            "artefacts": {"X": X, "y": y, "ajustement": PE.resume_ajustement(v)}}


def _plan_factoriel():
    import itertools
    return [dict(alpha0=a, beta0=b, nu0_plus=n, echelle_w0=e) for a, b, n, e in
            itertools.product((0.1, 1.0, 2.5, 10.0), (1e-3, 1.0, 10.0), (0.0, 5.0), (0.1, 1.0, 10.0))]


def unite_factoriel(memo, rapide, essai, rep):
    e = _plan_factoriel()[essai]
    n_init = min(int(PARAM.valeur("n_init")[FAMILLE]), 3 if rapide else 10 ** 9)
    X, y = DO.gen_gauss(300, DO.centres_triangle(4), 1.0, graine=PE.graine("S9", "donnees", rep))
    D = X.shape[1]
    pr = A.PrioriNW(e["alpha0"], X.mean(0), e["beta0"], e["echelle_w0"] * torch.cov(X.T).reshape(D, D), D + e["nu0_plus"])
    v = A.em_variationnel(X, 6, priori=pr, n_init=n_init, graine=PE.graine("S9", "ajustement", rep) % 2 ** 31)
    return {"lignes": [e | {"essai": essai, "rep": rep, "k_actif": C.k_hat(v["Nk"], 300),
                            "ARI": A.indice_rand_ajuste(y, v["labels"])}],
            "artefacts": {"ajustement": PE.resume_ajustement(v, avec_r=False)}}


def unite_seuil(memo, rapide, alpha0, rep):
    n_init = min(int(PARAM.valeur("n_init")[FAMILLE]), 3 if rapide else 10 ** 9)
    X, y = DO.gen_gauss(300, DO.centres_triangle(4), 1.0, graine=PE.graine("S10", "donnees", rep))
    v = A.em_variationnel(X, 6, alpha0=alpha0, n_init=n_init, graine=PE.graine("S10", "ajustement", rep) % 2 ** 31)
    Nk = v["Nk"]
    return {"lignes": [{"alpha0": alpha0, "rep": rep, "N_k_ge_1": int((Nk >= 1).sum()),
                        "pct_0.5": int((Nk / 300 >= 0.005).sum()), "pct_1": int((Nk / 300 >= 0.01).sum()),
                        "pct_5": int((Nk / 300 >= 0.05).sum()),
                        "Nk_tries": " ".join(f"{x:.2f}" for x in sorted(Nk.tolist(), reverse=True))}],
            "artefacts": {"Nk": Nk}}


# ------------------------------------------------------------------------------ étape
def unites(rapide: bool):
    R = 3 if rapide else int(PARAM.valeur("replications")["scenarios"])
    us = []
    for sc, par, fab, kv, kc in _plan(rapide):
        for r in range(R):
            us.append(E.Unite("scenarios", f"{sc}/{par}/rep={r:03d}", "scenarios", "unite_scenario",
                              dict(scenario=sc, parametre=par, fabrique=fab, k_vrai=kv, k_choisi=kc, rep=r)))
    for cov in ("full", "diag", "spherical"):
        for a0 in (1.0, 1.5, 2.0, 2.5, 3.0, 5.0, 10.0):
            for r in range(R):
                us.append(E.Unite("scenarios", f"S8/{cov}/a0={a0}/rep={r:03d}", "scenarios", "unite_alpha0",
                                  dict(cov=cov, alpha0=a0, rep=r)))
    for i in range(len(_plan_factoriel())):
        for r in range(R):
            us.append(E.Unite("scenarios", f"S9/essai={i:02d}/rep={r:03d}", "scenarios", "unite_factoriel", dict(essai=i, rep=r)))
    for a0 in (1 / 6, 1.0, 2.5, 10.0):
        for r in range(R):
            us.append(E.Unite("scenarios", f"S10/a0={a0:.4f}/rep={r:03d}", "scenarios", "unite_seuil", dict(alpha0=a0, rep=r)))
    return us


def _moy(v):
    v = [x for x in v if x == x]
    return sum(v) / len(v) if v else float("nan")


def agreger(rapide: bool):
    L = [l for l in E.lignes("scenarios", rapide) if "scenario" in l]
    E.ecrire_csv("scenarios_brut", L, rapide)
    resume = {}
    for l in L:
        if l.get("echec"):
            continue
        k = (l["scenario"], l["parametre"], l["bras"])
        resume.setdefault(k, []).append(l)
    lignes_res = []
    for (sc, par, br), ls in sorted(resume.items()):
        lignes_res.append({"scenario": sc, "parametre": par, "bras": br, "n": len(ls),
                           **{m: _moy([x[m] for x in ls]) for m in ("k_hat", "erreur_k", "ARI", "ll_test", "ll_test_predictive",
                                                                      "degenere", "petite_composante",
                                                                      "plancher_regularisation", "converge", "temps_s")}})
    E.ecrire_csv("scenarios_resume", lignes_res, rapide)
    # décisions confirmatoires : famille « scenarios », un test déclaré par hypothèse, Holm sur la famille
    hyp = [{"id": h.id, "axe": h.axe, "enonce": h.enonce, "test": h.test, "marge": HY.marge(h),
            "diffs": HY.diffs(h, L)} for h in HY.famille("scenarios")]
    dec = S.decider_famille(hyp, float(PARAM.valeur("alpha_test")), int(PARAM.valeur("n_bootstrap_ic")))
    E.ecrire_csv("scenarios_decisions", dec, rapide)
    for nom, prefixe in (("S8_alpha0", "S8/"), ("S9_factoriel", "S9/"), ("S10_seuil", "S10/")):
        E.ecrire_csv(nom, E.lignes("scenarios", rapide, prefixe), rapide)
    L9 = E.lignes("scenarios", rapide, "S9/")
    if L9:
        dv = S.decomposition_variance([l["k_actif"] for l in L9],
                                      {f: [l[f] for l in L9] for f in ("alpha0", "beta0", "nu0_plus", "echelle_w0")})
        E.ecrire_csv("S9_decomposition_variance", [{"facteur": k, "part_variance": v} for k, v in dv.items()], rapide)
