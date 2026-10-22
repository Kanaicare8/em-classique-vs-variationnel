"""
================================================================================
ÉTAPE « climat » : régimes climatiques du Cameroun (cas principal)
================================================================================

Plans (une unité par point et par réplication) :
  sous/N=n/rep=r     validation croisée PAR BLOCS : les blocs spatiaux (côté calibré, registre
                     taille_bloc_km) sont répartis entre n_plis plis ; le pli test est tiré pour la
                     réplication ; l'échantillon d'apprentissage de taille n est tiré UNIQUEMENT dans les
                     autres plis ; l'évaluation hors bloc porte sur toutes les cellules du pli test.
                     Aucune cellule de test n'appartient à l'apprentissage (vérifié dans l'unité).
  complet/pli=f      N complet : apprentissage sur tous les plis sauf f, test sur f (chaque pli une fois).
  semi/N=n/rep=r     jeu semi-synthétique tiré du modèle de référence (EM à K = 5 ajusté à N complet,
                     unité « reference ») ; vérité connue : K, partition, paramètres.
  couverture/N=n/rep=r  couverture à 90 % sur le semi-synthétique, INCONDITIONNELLE : une composante vraie
                     sans composante active appariée compte comme non couverte. VB : intervalles de
                     crédibilité (tirages de q). EM : bootstrap non paramétrique avec démarrage chaud au
                     paramètre estimé (le bootstrap mesure la variabilité d'échantillonnage autour de
                     l'optimum atteint, pas les sauts entre optima locaux) et alignement par l'algorithme hongrois.
  sensibilite/...    HC5 : variance de K̂ du VB sur le domaine plausible des hyperparamètres (configurations
                     de la recherche de calibrage dont la vraisemblance de validation est à moins de la marge
                     LL du meilleur) contre variance de K̂ de l'EM-BIC entre graines.
  d20/N=n/rep=r      extension à D = 20, même plan que sous/.
  cartes             ajustements EM-BIC et VB sur toutes les cellules (cartes).
Référence : Köppen-Geiger seul (zonage agro-écologique officiel indisponible).
"""

from __future__ import annotations

import torch

import algorithmes as A
import comparaison as C
import donnees_geo as G
import etapes as E
import hypotheses as HY
import parametres as PARAM
import persistance as PE
import statistique as S

FAMILLE = "climat"
K_REF = 5
EFFECTIFS = (30, 60, 120, 500, 2000)


def _donnees(D: int):
    d = G.charger_climat(D)
    return G.standardiser(d["X"]), d


def _plis(d, rep_graine: int):
    blocs = C.blocs_spatiaux(d["km"], float(PARAM.valeur("taille_bloc_km")))
    n_plis = int(PARAM.valeur("n_plis"))
    return C.plis_par_blocs(blocs, n_plis, rep_graine), n_plis


def _n_init(rapide):
    n = int(PARAM.valeur("n_init")[FAMILLE])
    return min(n, 3) if rapide else n


def _evaluer(sortie, Xtr, Xte, ytr_kg, k_ref, plan, N, rep, D):
    lignes, ajust = [], {}
    for nom, res in sortie.items():
        base = {"plan": plan, "N": str(N), "rep": rep, "bras": nom, "D": D}
        if "echec" in res:
            lignes.append(base | {"echec": True, "degenere": 1.0})
            continue
        est_vb = nom.startswith("VB")
        lignes.append(base | {
            "echec": False, "k_hat": res["k_hat"], "k_ajuste": res["k_ajuste"],
            "ARI_koppen": A.indice_rand_ajuste(ytr_kg, res["labels"]),
            "ll_test": C.logdens_plugin(res, Xte),
            "ll_test_predictive": C.logdens_predictive_vb(res, Xte) if est_vb else float("nan"),
            "degenere": float(res["degenere"]), "petite_composante": float(res.get("petite_composante", False)),
            "plancher_regularisation": float(res.get("plancher_regularisation", False)),
            "converge": float(res["converge"]), "n_iter": res["n_iter"], "temps_s": res["temps_total"]})
        ajust[nom] = PE.resume_ajustement(res)
    return lignes, ajust


def unite_sous(memo, rapide, N, rep, D=5):
    X, d = _donnees(D)
    pli, n_plis = _plis(d, PE.graine("climat", "plis", D, N, rep))
    f = int(torch.randint(n_plis, (1,), generator=A.generateur(PE.graine("climat", "pli_test", D, N, rep))))
    idx_test = (pli == f).nonzero().flatten()
    pool = (pli != f).nonzero().flatten()
    g = A.generateur(PE.graine("climat", "echantillon", D, N, rep))
    idx = pool if N == "complet" else pool[torch.randperm(len(pool), generator=g)[:int(N)]]
    assert not bool(torch.isin(idx_test, idx).any()), "fuite apprentissage / test"
    sortie = C.bras_protocole(X[idx], K_REF, int(PARAM.valeur("k_max")[FAMILLE]), _n_init(rapide),
                              PE.graine("climat", "ajustement", D, N, rep) % 2 ** 31, FAMILLE, memo=memo)
    lignes, ajust = _evaluer(sortie, X[idx], X[idx_test], d["koppen"][idx], K_REF, "sous" if D == 5 else "d20", N, rep, D)
    return {"lignes": lignes, "artefacts": {"idx_apprentissage": idx, "idx_test": idx_test, "pli_test": f,
                                            "ajustements": ajust}}


def unite_complet(memo, rapide, pli_test):
    X, d = _donnees(5)
    pli, _ = _plis(d, PE.graine("climat", "plis_complet"))
    idx = (pli != pli_test).nonzero().flatten()
    idx_test = (pli == pli_test).nonzero().flatten()
    sortie = C.bras_protocole(X[idx], K_REF, int(PARAM.valeur("k_max")[FAMILLE]), _n_init(rapide),
                              PE.graine("climat", "ajustement", "complet", pli_test) % 2 ** 31, FAMILLE, memo=memo)
    lignes, ajust = _evaluer(sortie, X[idx], X[idx_test], d["koppen"][idx], K_REF, "complet", "complet", pli_test, 5)
    return {"lignes": lignes, "artefacts": {"idx_test": idx_test, "ajustements": ajust}}


def unite_reference(memo, rapide):
    X, _ = _donnees(5)
    n_init = int(PARAM.valeur("n_init")[FAMILLE])
    ref = A.em_classique(X, K_REF, n_init=min(n_init, 3) if rapide else n_init,
                         graine=PE.graine("climat", "reference") % 2 ** 31, instantane=memo.instantane("reference"))
    return {"lignes": [{"loglik": ref["loglik"], "converge": float(ref["converge"]), "relances": len(ref["relances"]["critere"])}],
            "artefacts": {"modele": {"pi": ref["pi"], "mu": ref["mu"], "cov": ref["cov"]}, "ajustement": PE.resume_ajustement(ref)}}


def _reference(rapide, etape="climat"):
    r = E.magasin(etape, rapide).lire("reference")
    if r is None:
        raise RuntimeError("unité « reference » absente : elle est calculée avant le plan semi-synthétique")
    return r["artefacts"]["modele"]


def unite_semi(memo, rapide, N, rep, etape_reference="climat"):
    ref = _reference(rapide, etape_reference)
    Xs, z = C.simuler_depuis_modele(ref, N, PE.graine("climat", "semi", N, rep))
    sortie = C.bras_protocole(Xs, K_REF, int(PARAM.valeur("k_max")[FAMILLE]), _n_init(rapide),
                              PE.graine("climat", "semi_ajustement", N, rep) % 2 ** 31, FAMILLE,
                              bras=("EM-K", "EM-Kmax", "EM-BIC", "EM-ICL", "MAP-EM", "MAP-cal", "VB-emp", "VB-cal"), memo=memo)
    lignes = []
    for nom, res in sortie.items():
        base = {"plan": "semi", "N": str(N), "rep": rep, "bras": nom}
        if "echec" in res:
            lignes.append(base | {"echec": True})
            continue
        lignes.append(base | {"echec": False, "k_hat": res["k_hat"], "erreur_k": abs(res["k_hat"] - K_REF),
                              "ARI": A.indice_rand_ajuste(z, res["labels"]), "degenere": float(res["degenere"]),
                              "temps_s": res["temps_total"]})
    return {"lignes": lignes, "artefacts": {"X": Xs, "z": z,
                                            "ajustements": {k: PE.resume_ajustement(v) for k, v in sortie.items() if "echec" not in v}}}


def _tirages_q(P, n, graine):
    """Tirages de (pi, mu) sous q (covariance pleine) : pi ~ Dir(alpha), Lambda ~ W(W, nu), mu | Lambda ~ N(m, (beta Lambda)^-1)."""
    dist = torch.distributions
    with torch.random.fork_rng():
        torch.manual_seed(graine)
        pis = dist.Dirichlet(P["alpha"]).sample((n,))
        mus = []
        for k in range(len(P["alpha"])):
            lam = dist.Wishart(df=P["nu"][k], covariance_matrix=P["W"][k]).sample((n,))
            mus.append(dist.MultivariateNormal(P["m"][k], precision_matrix=P["beta"][k] * lam).sample())
    return pis, torch.stack(mus, dim=1)


def _couverts(ref, pi_inf, pi_sup, mu_inf, mu_sup, actives_centres, actives_idx):
    """Appariement hongrois composantes vraies / actives ; une composante vraie non appariée n'est pas couverte."""
    K = len(ref["pi"])
    out = []
    if len(actives_idx) == 0:
        return [(k, 0.0, 0.0) for k in range(K)]
    n = max(K, len(actives_idx))
    cout = torch.full((n, n), 1e6, dtype=torch.float64)
    cout[:K, :len(actives_idx)] = torch.cdist(ref["mu"], actives_centres).pow(2)
    col = A.hongrois(cout)
    for k in range(K):
        j = int(col[k])
        if j >= len(actives_idx):
            out.append((k, 0.0, 0.0))
            continue
        jj = actives_idx[j]
        cp = float(pi_inf[jj] <= ref["pi"][k] <= pi_sup[jj])
        cm = float(((mu_inf[jj] <= ref["mu"][k]) & (ref["mu"][k] <= mu_sup[jj])).double().mean())
        out.append((k, cp, cm))
    return out


def unite_couverture(memo, rapide, N, rep):
    ref = _reference(rapide)
    Xs, _ = C.simuler_depuis_modele(ref, N, PE.graine("climat", "semi", N, rep))
    n_init = _n_init(rapide)
    g_fit = PE.graine("climat", "semi_ajustement", N, rep) % 2 ** 31
    lignes = []
    # VB : intervalles de crédibilité à 90 %
    vb = memo("VB-emp", lambda: A.em_variationnel(Xs, int(PARAM.valeur("k_max")[FAMILLE]),
                                                   priori=C.priors_bras(Xs, int(PARAM.valeur("k_max")[FAMILLE]), FAMILLE)["emp"],
                                                   n_init=n_init, graine=g_fit))
    act = (vb["Nk"] / N >= float(PARAM.valeur("seuil_actif"))).nonzero().flatten()
    nt = 200 if rapide else int(PARAM.valeur("n_tirages_posterieur"))
    pis, mus = _tirages_q(vb["P"], nt, PE.graine("climat", "tirages", N, rep) % 2 ** 31)
    q = torch.tensor([0.05, 0.95], dtype=torch.float64)
    pi_b = torch.quantile(pis, q, dim=0)
    mu_b = torch.quantile(mus, q, dim=0)
    for k, cp, cm in _couverts(ref, pi_b[0], pi_b[1], mu_b[0], mu_b[1], vb["m"][act], act):
        lignes += [{"N": str(N), "rep": rep, "methode": "VB", "param": "pi", "composante": k, "couvert": cp},
                   {"N": str(N), "rep": rep, "methode": "VB", "param": "mu", "composante": k, "couvert": cm}]
    # EM : bootstrap avec démarrage chaud, même n_init que l'ajustement principal pour l'estimation initiale
    em = memo("EM-K", lambda: A.em_classique(Xs, K_REF, n_init=n_init, graine=g_fit))
    B = 50 if rapide else int(PARAM.valeur("n_bootstrap_modele"))
    pis_b, mus_b = [], []
    for b in range(B):
        ib = torch.randint(N, (N,), generator=A.generateur(PE.graine("climat", "bootstrap", N, rep, b)))
        eb = C.em_demarrage_chaud(Xs[ib], em)
        c = A.hongrois(torch.cdist(em["mu"], eb["mu"]).pow(2))
        pis_b.append(eb["pi"][c])
        mus_b.append(eb["mu"][c])
    pis_b, mus_b = torch.stack(pis_b), torch.stack(mus_b)
    pi_e = torch.quantile(pis_b, q, dim=0)
    mu_e = torch.quantile(mus_b, q, dim=0)
    tous = torch.arange(K_REF)
    for k, cp, cm in _couverts(ref, pi_e[0], pi_e[1], mu_e[0], mu_e[1], em["mu"], tous):
        lignes += [{"N": str(N), "rep": rep, "methode": "bootstrap EM", "param": "pi", "composante": k, "couvert": cp},
                   {"N": str(N), "rep": rep, "methode": "bootstrap EM", "param": "mu", "composante": k, "couvert": cm}]
    return {"lignes": lignes, "artefacts": {"pis_bootstrap": pis_b, "mus_bootstrap": mus_b, "B": B, "tirages_q": nt}}


def unite_sensibilite(memo, rapide, rep):
    """HC5 : K̂ du VB pour chaque configuration plausible (domaine issu du calibrage) et K̂ de l'EM-BIC pour une graine."""
    X, d = _donnees(5)
    g = A.generateur(PE.graine("climat", "sensibilite", rep))
    idx = torch.randperm(len(X), generator=g)[:500]
    Xs = X[idx]
    kmax = int(PARAM.valeur("k_max")[FAMILLE])
    n_init = _n_init(rapide)
    plaus = _configs_plausibles()
    lignes = []
    for i, cfg in enumerate(plaus):
        D = Xs.shape[1]
        pr = A.PrioriNW(cfg["alpha0"], Xs.mean(0), cfg["beta0"], cfg["echelle_w0"] * torch.cov(Xs.T).reshape(D, D), D + cfg["nu0_plus"])
        v = memo(f"VB/cfg={i}", lambda pr=pr: A.em_variationnel(Xs, kmax, priori=pr, n_init=n_init,
                                                               graine=PE.graine("climat", "sens_fit", rep) % 2 ** 31))
        lignes.append({"rep": rep, "source": "VB-priors", "config": i, "k_hat": C.k_hat(v["Nk"], 500)})
    eb = C.choisir_k_critere(Xs, kmax, "bic", n_init, PE.graine("climat", "sens_em", rep) % 2 ** 31, memo)
    lignes.append({"rep": rep, "source": "EM-BIC-graine", "config": -1, "k_hat": C.k_hat(eb["Nk"], 500)})
    return {"lignes": lignes, "artefacts": {"idx": idx, "configs": plaus}}


def _configs_plausibles():
    import json
    f = PARAM.dossier_calibrage() / "priors.json"
    if not f.exists():
        return [PARAM.valeur("priors_vb_calibres")[FAMILLE]]
    d = json.loads(f.read_text(encoding="utf-8"))
    evals = d["details"]["evaluations"][FAMILLE]
    meilleur = max(e["score"] for e in evals if e["etape"] == max(x["etape"] for x in evals))
    marge = float(PARAM.valeur("marges_equivalence")["LL"])
    finales = [e for e in evals if e["etape"] == max(x["etape"] for x in evals)]
    return [e["config"] for e in finales if e["score"] >= meilleur - marge] or [d["valeurs"]["priors_vb_calibres"][FAMILLE]]


def unite_cartes(memo, rapide):
    X, d = _donnees(5)
    kmax = int(PARAM.valeur("k_max")[FAMILLE])
    n_init = _n_init(rapide)
    s = C.bras_protocole(X, K_REF, kmax, n_init, PE.graine("climat", "cartes") % 2 ** 31, FAMILLE, bras=("EM-BIC", "VB-emp", "VB-cal"),
                         memo=memo)
    art = {"lon": d["lon"], "lat": d["lat"], "koppen": d["koppen"], "noms": d["noms"]}
    for nom, res in s.items():
        if "echec" in res:
            continue
        r = res["r"]
        art[nom] = {"classe": res["labels"].to(torch.int16), "resp_max": r.max(1).values.float(),
                    "entropie": (-torch.xlogy(r, r).sum(1)).float(), "k_hat": res["k_hat"], "k_ajuste": res["k_ajuste"]}
    return {"lignes": [{"bras": k, "k_hat": v["k_hat"], "k_ajuste": v["k_ajuste"]} for k, v in art.items() if isinstance(v, dict) and "k_hat" in v],
            "artefacts": art}


# ------------------------------------------------------------------------------ étape
def unites(rapide: bool):
    rep = PARAM.valeur("replications")
    R_sous = 2 if rapide else int(rep["climat_sous"])
    R_semi = 2 if rapide else int(rep["climat_semi"])
    R_d20 = 2 if rapide else int(rep["climat_d20"])
    us = [E.Unite("climat", "reference", "etape_climat", "unite_reference")]
    for N in EFFECTIFS:
        for r in range(R_sous):
            us.append(E.Unite("climat", f"sous/N={N}/rep={r:03d}", "etape_climat", "unite_sous", dict(N=N, rep=r)))
        for r in range(R_semi):
            us.append(E.Unite("climat", f"semi/N={N}/rep={r:03d}", "etape_climat", "unite_semi", dict(N=N, rep=r),
                              depend=("reference",)))
            if N >= 120:
                us.append(E.Unite("climat", f"couverture/N={N}/rep={r:03d}", "etape_climat", "unite_couverture",
                                  dict(N=N, rep=r), depend=("reference",)))
    for f in range(int(PARAM.valeur("n_plis"))):
        us.append(E.Unite("climat", f"complet/pli={f}", "etape_climat", "unite_complet", dict(pli_test=f)))
    for N in (120, 500, 2000):
        for r in range(R_d20):
            us.append(E.Unite("climat", f"d20/N={N}/rep={r:03d}", "etape_climat", "unite_sous", dict(N=N, rep=r, D=20)))
    for r in range(2 if rapide else int(rep["climat_sensibilite"])):
        us.append(E.Unite("climat", f"sensibilite/rep={r:03d}", "etape_climat", "unite_sensibilite", dict(rep=r)))
    us.append(E.Unite("climat", "cartes", "etape_climat", "unite_cartes"))
    return us


def agreger(rapide: bool):
    L = []
    for p in ("sous/", "complet/", "semi/", "d20/"):
        L += E.lignes("climat", rapide, p)
    E.ecrire_csv("climat_brut", L, rapide)
    alpha = float(PARAM.valeur("alpha_test"))
    nb = int(PARAM.valeur("n_bootstrap_ic"))
    hyp = [{"id": h.id, "axe": h.axe, "enonce": h.enonce, "test": h.test, "marge": HY.marge(h),
            "diffs": HY.diffs(h, L)} for h in HY.famille("climat")]
    dec = S.decider_famille(hyp, alpha, nb)
    # HC4 (coût) : rapport des temps médians EM-BIC / VB-emp, mesurés par l'étape « chronometrage » (sans concurrence)
    for l in E.lignes("chronometrage", rapide, "pipeline/"):
        dec.append({"id": f"HC4-N{l['N']}", "axe": "Coût", "test": "intervalle",
                    "enonce": "Temps du pipeline EM-BIC divisé par le temps d'un VB (ratio > 1 : EM-BIC plus coûteux)",
                    "estimation": l["ratio_median"], "ic_bas": l["ratio_ic_bas"], "ic_haut": l["ratio_ic_haut"],
                    "decision": "ratio > 1" if l["ratio_ic_bas"] > 1 else ("ratio < 1" if l["ratio_ic_haut"] < 1 else "non tranché")})
    # HC5 : variances de K̂
    Ls = E.lignes("climat", rapide, "sensibilite/")
    if Ls:
        kv = torch.tensor([l["k_hat"] for l in Ls if l["source"] == "VB-priors"], dtype=torch.float64)
        ke = torch.tensor([l["k_hat"] for l in Ls if l["source"] == "EM-BIC-graine"], dtype=torch.float64)
        dec.append({"id": "HC5", "axe": "Hyperparamètres", "test": "descriptif",
                    "enonce": "Variance de K̂ du VB sur le domaine plausible des hyperparamètres contre variance de K̂ de l'EM-BIC entre graines",
                    "estimation": float(kv.var()) if len(kv) > 1 else float("nan"),
                    "ic_bas": float(ke.var()) if len(ke) > 1 else float("nan"), "ic_haut": float("nan"),
                    "decision": "Var VB >= Var EM" if len(kv) > 1 and len(ke) > 1 and kv.var() >= ke.var() else "Var VB < Var EM"})
    # HC6 : couverture
    Lc = E.lignes("climat", rapide, "couverture/")
    E.ecrire_csv("climat_couverture_brut", Lc, rapide)
    for meth in ("VB", "bootstrap EM"):
        for par in ("pi", "mu"):
            v = [l["couvert"] for l in Lc if l["methode"] == meth and l["param"] == par]
            if not v:
                continue
            k = sum(v)
            p, lo, hi = S.wilson(round(k), len(v))
            dec.append({"id": f"HC6-{meth}-{par}", "axe": "Incertitude", "test": "intervalle",
                        "enonce": f"Couverture à 90 % ({meth}, {par}), inconditionnelle", "estimation": p, "ic_bas": lo,
                        "ic_haut": hi, "n": len(v),
                        "decision": "< 90 %" if hi < 0.9 else (">= 90 %" if lo >= 0.9 else "compatible avec 90 %")})
    E.ecrire_csv("climat_decisions", dec, rapide)
    resume = {}
    for l in L:
        if l.get("echec"):
            continue
        resume.setdefault((l["plan"], l["N"], l["bras"]), []).append(l)
    out = []
    for (pl, N, br), ls in sorted(resume.items()):
        def m(c):
            v = [x[c] for x in ls if c in x and x[c] == x[c]]
            return sum(v) / len(v) if v else float("nan")
        out.append({"plan": pl, "N": N, "bras": br, "n": len(ls), "k_hat": m("k_hat"), "erreur_k": m("erreur_k"),
                    "ARI": m("ARI"), "ARI_koppen": m("ARI_koppen"), "ll_test": m("ll_test"),
                    "ll_test_predictive": m("ll_test_predictive"), "degenere": m("degenere"), "temps_s": m("temps_s")})
    E.ecrire_csv("climat_resume", out, rapide)
    c = E.magasin("climat", rapide).lire("cartes")
    if c is not None:
        E.ecrire_csv("climat_cartes_k", c["lignes"], rapide)
