"""
================================================================================
ÉTAPE « calibrage » : fixe, selon les règles écrites dans parametres.py, toutes les valeurs non mathématiques
================================================================================

Sept vagues, enchaînées par dépendances (une unité ne lit que des valeurs déjà calibrées par une vague antérieure) :
  V1  kmeans/<jeu>, spatial              plafond de Lloyd ; portée du variogramme (taille des blocs spatiaux)
  V2  tolerance/<jeu>                    tolérance relative et plafond d'étapes M
  V3  regularisation/<jeu>               régularisation des covariances (validation croisée)
  V4  n_init/<jeu>, hmm                  nombre de relances par famille ; nombre d'états du HMM (BIC)
  V5  priors/<famille>, texte, variantes recherche aléatoire + divisions successives (successive halving)
  V6  marges/<jeu>, monte_carlo          marges d'équivalence (bruit d'optimisation) ; tailles Monte Carlo
  V7  puissance/pilote/..., puissance    réplications pilotes (graines disjointes) et puissance simulée
Chaque vague se termine par une unité « fin/<id> » qui écrit resultats/calibrage/<id>.json :
  {"valeurs": {...}, "regle": "...", "details": {...}, "date": "..."}
Toutes les évaluations intermédiaires sont conservées dans le magasin (reprise exacte et traçabilité).
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime

import torch

import algorithmes as A
import comparaison as C
import donnees as DO
import etapes as E
import hypotheses as HY
import parametres as PARAM
import persistance as PE
import statistique as S

GRILLE_TOL = (1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9)
TOL_REFERENCE = 1e-10
PLAFOND_REFERENCE = 10_000          # une référence qui l'atteint est exclue (non convergée)
GRILLE_REG = (0.0, 1e-10, 1e-8, 1e-6, 1e-4, 1e-3, 1e-2, 1e-1)
PRECISION_AFFICHAGE = 5e-4          # moitié de la 3e décimale affichée
RELANCES_PILOTE = 200               # relances du pilote de n_init (registre « n_init »)
N_CONFIGS = 64                      # configurations de la recherche aléatoire des priors
N_CONFIGS_TEXTE = 32
N_CONFIGS_VARIANTES = 32
REPETITIONS_MC = 20                 # répétitions pour estimer l'écart-type Monte Carlo d'une borne
PUISSANCE_CIBLE = 0.8
N_SIM_PUISSANCE = 1600              # erreur Monte Carlo de la puissance <= 0,01 : 0,8 x 0,2 / 0,01² = 1600
GRILLE_R = tuple(range(10, 201, 10))
DECALAGE_PILOTE = 100_000           # graines des réplications pilotes, disjointes de celles des étapes confirmatoires


def _g(*role):
    return PE.graine("calibrage", *role) % 2 ** 31


def _ecrire(ident, valeurs, regle, details):
    PARAM.dossier_calibrage().mkdir(parents=True, exist_ok=True)
    f = PARAM.dossier_calibrage() / f"{ident}.json"
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps({"valeurs": valeurs, "regle": regle, "details": details,
                               "date": datetime.now().isoformat(timespec="seconds")}, ensure_ascii=False, indent=1,
                              default=float), encoding="utf-8")
    os.replace(tmp, f)
    return {"lignes": [{"calibrage": ident, **{k: json.dumps(v, default=float) for k, v in valeurs.items()}}],
            "artefacts": {"valeurs": valeurs, "details": details}}


def _mag(rapide):
    return E.magasin("calibrage", rapide)


# ------------------------------------------------------------------------------ jeux du protocole
def _points_scenarios():
    import scenarios as SC
    return [p for p in SC._plan(False) if p[0] in ("S1", "S2", "S3", "S4", "S5", "S6", "S7")]


def jeux(rapide):
    """Noms des jeux de calibrage : (nom, famille)."""
    out = [(f"synthetique/{sc}/{par}", "synthetique") for sc, par, *_ in _points_scenarios()]
    if rapide:
        out = out[:3]
    out += [("iris", "iris"), ("sp500", "sp500")]
    out += [(f"climat/D=5/N={n}", "climat") for n in ((500,) if rapide else (30, 60, 120, 500, 2000))]
    if not rapide:
        out.append(("climat/D=20/N=500", "climat"))
    return out


def charger_jeu(nom, rep=0):
    """(X_apprentissage, X_test, k_ref, kmax, etiquettes ou None). Données tirées avec des graines propres au calibrage."""
    if nom.startswith("synthetique/"):
        import scenarios as SC
        _, sc, par = nom.split("/", 2)
        f, kv, kc = next((f, kv, kc) for s, p, f, kv, kc in _points_scenarios() if s == sc and p == par)
        X, y, _ = SC.fabriquer(f, PE.graine("calibrage", nom, "donnees", rep), "train")
        Xt, _, _ = SC.fabriquer(f, PE.graine("calibrage", nom, "test", rep), "test")
        return X, Xt, kc, int(PARAM.valeur("k_max")["synthetique"]), y
    if nom == "iris":
        X, y = DO.charger_iris()
        perm = torch.randperm(len(X), generator=A.generateur(_g("iris", rep)))
        return X[perm], X[perm], 3, int(PARAM.valeur("k_max")["synthetique"]), y[perm]
    if nom == "sp500":
        import etape_sp500 as SP
        x, xt, _ = SP.donnees()
        return x, xt, 2, int(PARAM.valeur("k_max")["sp500"]), None
    if nom.startswith("climat/"):
        import donnees_geo as G
        D = int(nom.split("/")[1][2:])
        N = int(nom.split("/")[2][2:])
        d = G.charger_climat(D)
        X = G.standardiser(d["X"])
        perm = torch.randperm(len(X), generator=A.generateur(_g(nom, rep)))
        return X[perm[:N]], X[perm[N:N + 2000]], 5, int(PARAM.valeur("k_max")["climat"]), d["koppen"][perm[:N]]
    raise KeyError(nom)


def _taille_pilote(rapide):
    return 3 if rapide else int(PARAM.valeur("taille_pilote"))


# ------------------------------------------------------------------------------ V1 : k-means, spatial
def unite_kmeans(memo, rapide, jeu):
    X, _, k_ref, kmax, _ = charger_jeu(jeu)
    n = 20 if rapide else RELANCES_PILOTE
    its = []
    for K in sorted({k_ref, kmax}):
        _, _, _, it = A.kmeans_lot(X, K, list(range(_g("kmeans", jeu, K), _g("kmeans", jeu, K) + n)),
                                   n_iter=PLAFOND_REFERENCE, retour_iters=True)
        its += [int(v) for v in it]
    return {"lignes": [{"jeu": jeu, "iterations_max": max(its), "iterations_q99": float(torch.quantile(torch.tensor(its, dtype=torch.float64), 0.99))}],
            "artefacts": {"iterations": its}}


def fin_kmeans(memo, rapide):
    its = [i for r in E.resultats("calibrage", rapide, "kmeans/") for i in r["artefacts"]["iterations"]]
    t = torch.tensor(its)
    plafond = 100
    while float((t >= plafond).double().mean()) > 0.01:
        plafond += 100
    return _ecrire("kmeans", {"kmeans_n_iter_max": plafond},
                   "plus petit multiple de 100 tel qu'au plus 1 % des exécutions de Lloyd l'atteignent",
                   {"n_executions": len(its), "iterations_max": int(t.max()), "part_au_plafond": float((t >= plafond).double().mean())})


def unite_spatial(memo, rapide):
    """
    Variogramme empirique EXHAUSTIF (toutes les paires, par blocs de lignes) des variables standardisées (D = 5) :
    gamma(h) = moyenne de ||x_i - x_j||² / (2 D). Pour des variables réduites, le palier vaut 1 (paires indépendantes).
    Portée pratique : plus petite distance où gamma atteint 95 % du palier, cherchée jusqu'à la moitié de la distance maximale.
    Largeur des classes de distance : médiane de la distance au plus proche voisin (pas de la grille).
    """
    import donnees_geo as G
    d = G.charger_climat(5)
    X = G.standardiser(d["X"])
    km = d["km"].double()
    N, D = X.shape
    lot = 256 if not rapide else 64
    idx = range(0, N, lot) if not rapide else range(0, min(N, 2048), lot)
    pp = []
    for i in range(0, N, 2048):
        dd = torch.cdist(km[i:i + 2048], km)
        dd[dd == 0] = float("inf")
        pp.append(dd.min(1).values)
    pas = float(torch.cat(pp).median())
    dmax = float(max(torch.cdist(km[i:i + 2048], km).max() for i in range(0, N, 2048)))
    nb = int(dmax / pas) + 2
    somme = torch.zeros(nb, dtype=torch.float64)
    eff = torch.zeros(nb, dtype=torch.float64)
    for i in idx:
        h = torch.cdist(km[i:i + lot], km)
        sq = torch.cdist(X[i:i + lot], X).pow(2) / (2 * D)
        c = (h / pas).floor().long().clamp(max=nb - 1)
        somme += torch.bincount(c.flatten(), weights=sq.flatten(), minlength=nb)
        eff += torch.bincount(c.flatten(), minlength=nb).double()
    gam = somme / eff.clamp(min=1)
    centres = (torch.arange(nb, dtype=torch.float64) + 0.5) * pas
    utile = (centres <= dmax / 2) & (eff > 0) & (centres > pas)
    ok = (gam >= 0.95) & utile
    portee = float(centres[ok][0] + pas / 2) if ok.any() else dmax / 2
    return {"lignes": [{"pas_km": pas, "portee_km": portee, "distance_max_km": dmax}],
            "artefacts": {"h": centres, "gamma": gam, "effectifs": eff, "pas": pas, "portee": portee}}


def fin_spatial(memo, rapide):
    a = _mag(rapide).lire("spatial")["artefacts"]
    return _ecrire("spatial", {"taille_bloc_km": a["portee"]},
                   "portée pratique du variogramme exhaustif des variables standardisées (95 % du palier unité), "
                   "bornée par la moitié de la distance maximale", {"pas_km": a["pas"]})


# ------------------------------------------------------------------------------ V2 : tolérance
def _ajuster(algo, X, K, kmax, tol, n_iter, reg, graine, priori=None):
    """Ajustement résumé (critère, partition, étapes) ; None si la factorisation échoue."""
    try:
        r = (A.em_classique(X, K, tol=tol, n_iter=n_iter, reg=reg, graine=graine) if algo == "EM"
             else A.em_variationnel(X, kmax, priori=priori, tol=tol, n_iter=n_iter, graine=graine))
    except A.EchecNumerique:
        return {"echec": True}
    return {"echec": False, "critere": r["loglik"] if algo == "EM" else r["elbo"], "labels": r["labels"].to(torch.int16),
            "n_iter": r["n_iter"], "converge": bool(r["converge"])}


def unite_tolerance(memo, rapide, jeu):
    X, _, k_ref, kmax, _ = charger_jeu(jeu)
    pr = A.priori_empirique(X, 1.0 / kmax)
    lignes = []
    for algo, K in (("EM", k_ref), ("EM", kmax), ("VB", kmax)):
        for s in range(_taille_pilote(rapide)):
            g = _g("tolerance", jeu, s)
            ref = memo(f"{algo}/K={K}/s={s}/ref", lambda: _ajuster(algo, X, K, kmax, TOL_REFERENCE, PLAFOND_REFERENCE, 0.0, g, pr))
            if ref["echec"] or not ref["converge"]:
                lignes.append({"jeu": jeu, "algo": algo, "K": K, "graine": s, "reference_exclue": True,
                               "motif": "échec numérique" if ref["echec"] else "plafond atteint"})
                continue
            for tol in GRILLE_TOL:
                r = memo(f"{algo}/K={K}/s={s}/tol={tol}", lambda: _ajuster(algo, X, K, kmax, tol, PLAFOND_REFERENCE, 0.0, g, pr))
                if r["echec"]:
                    lignes.append({"jeu": jeu, "algo": algo, "K": K, "graine": s, "tol": tol, "accord": False, "echec": True})
                    continue
                ecart = abs(r["critere"] - ref["critere"]) / X.shape[0]
                ari = A.indice_rand_ajuste(ref["labels"].long(), r["labels"].long())
                lignes.append({"jeu": jeu, "algo": algo, "K": K, "graine": s, "tol": tol, "ecart_par_obs": ecart,
                               "ARI_reference": ari, "n_iter": r["n_iter"],
                               "accord": bool(ecart < PRECISION_AFFICHAGE and ari >= 0.99)})
    return {"lignes": lignes}


def fin_tolerance(memo, rapide):
    L = [l for l in E.lignes("calibrage", rapide, "tolerance/") if "tol" in l]
    choix, details = min(GRILLE_TOL), {}
    for tol in sorted(GRILLE_TOL, reverse=True):              # de la plus grande à la plus stricte
        ls = [l for l in L if l["tol"] == tol]
        part = sum(l["accord"] for l in ls) / max(len(ls), 1)
        details[str(tol)] = part
        if part >= 0.99:
            choix = tol
            break
    its = [l["n_iter"] for l in L if l["tol"] == choix and "n_iter" in l]
    plafond = int(math.ceil(max(its) / 100.0) * 100)
    return _ecrire("tolerance", {"tol_rel": choix, "n_iter_max": plafond},
                   "plus grande tolérance (de 1e-3 à 1e-9) pour laquelle au moins 99 % des ajustements s'accordent avec la "
                   "référence (tol = 1e-10) : écart du critère par observation < 5e-4 et ARI >= 0,99 entre partitions ; "
                   "plafond = plus petit multiple de 100 supérieur ou égal au nombre maximal d'étapes observé à cette tolérance",
                   {"part_accord_par_tol": details, "iterations_max": max(its), "n_ajustements": len(its),
                    "references_exclues": len([l for l in E.lignes("calibrage", rapide, "tolerance/") if l.get("reference_exclue")])})


# ------------------------------------------------------------------------------ V3 : régularisation
def _plis_jeu(jeu, X, rapide):
    n_plis = int(PARAM.valeur("n_plis"))
    if jeu.startswith("climat/"):
        import donnees_geo as G
        D = int(jeu.split("/")[1][2:])
        N = int(jeu.split("/")[2][2:])
        d = G.charger_climat(D)
        perm = torch.randperm(len(d["X"]), generator=A.generateur(_g(jeu, 0)))[:N]
        blocs = C.blocs_spatiaux(d["km"][perm], float(PARAM.valeur("taille_bloc_km")))
        return C.plis_par_blocs(blocs, n_plis, _g("plis", jeu)), n_plis
    return torch.randperm(len(X), generator=A.generateur(_g("plis", jeu))) % n_plis, n_plis


def unite_regularisation(memo, rapide, jeu):
    X, _, k_ref, kmax, _ = charger_jeu(jeu)
    pli, n_plis = _plis_jeu(jeu, X, rapide)
    lignes = []
    for K in sorted({k_ref, kmax}):
        for s in range(_taille_pilote(rapide)):
            for f in range(n_plis):
                tr, te = X[pli != f], X[pli == f]
                if len(te) == 0 or A.nb_parametres(K, X.shape[1], "full") >= len(tr):
                    continue
                for reg in GRILLE_REG:
                    def score():
                        try:
                            r = A.em_classique(tr, K, reg=reg, graine=_g("reg", jeu, K, s))
                            return {"ll": C.logdens_plugin(r, te)}
                        except A.EchecNumerique:
                            return {"ll": float("-inf")}
                    v = memo(f"K={K}/s={s}/pli={f}/reg={reg}", score)["ll"]
                    lignes.append({"jeu": jeu, "K": K, "graine": s, "pli": f, "reg": reg,
                                   "ll_test": v if v == v else float("-inf")})
    return {"lignes": lignes}


def fin_regularisation(memo, rapide):
    L = E.lignes("calibrage", rapide, "regularisation/")
    groupes = {}
    for l in L:
        groupes.setdefault((l["jeu"], l["K"], l["graine"], l["pli"]), {})[l["reg"]] = l["ll_test"]
    rangs = {r: [] for r in GRILLE_REG}
    for g in groupes.values():
        if len(g) < len(GRILLE_REG):
            continue
        v = torch.tensor([g[r] for r in GRILLE_REG], dtype=torch.float64)
        rg = S._rangs_moyens(-v)                                # rang 1 = meilleure log-vraisemblance hors pli
        for r, x in zip(GRILLE_REG, rg.tolist()):
            rangs[r].append(x)
    moy = {r: sum(v) / len(v) for r, v in rangs.items() if v}
    meilleur = min(moy.values())
    choix = min(r for r, m in moy.items() if m == meilleur)
    return _ecrire("regularisation", {"reg_covariance": choix},
                   "rang moyen minimal de la log-vraisemblance hors pli (validation croisée ; plis spatiaux par blocs pour le "
                   "climat), sur tous les jeux, K de référence et Kmax, graines pilotes ; à égalité, la plus petite valeur",
                   {"rang_moyen": {str(k): v for k, v in moy.items()}, "n_comparaisons": len(rangs[GRILLE_REG[0]])})


# ------------------------------------------------------------------------------ V4 : n_init, HMM
def _p_succes(criteres, tol):
    c = torch.tensor([x for x in criteres if x == x and x != float("-inf")], dtype=torch.float64)
    best = float(c.max())
    return float((c >= best - 10 * tol * abs(best)).double().mean()), len(c)


def _n_requis(p, plafond):
    if p >= 1.0:
        return 1
    if p <= 0.0:
        return plafond
    return min(plafond, int(math.ceil(math.log(0.01) / math.log(1 - p))))


def _configs_aleatoires(n, graine, kmax):
    """Configurations tirées dans « espace_priors » (log-uniforme ; nu0 - D uniforme) ; la première est le jeu empirique."""
    esp = PARAM.valeur("espace_priors")
    g = A.generateur(graine)
    u = torch.rand(n, 4, generator=g, dtype=torch.float64)

    def lu(i, b):
        lo, hi = math.log10(b[0]), math.log10(b[1])
        return 10 ** (lo + float(u[i % n, b[2]]) * (hi - lo))
    out = [{"alpha0": 1.0 / kmax, "beta0": 1.0, "nu0_plus": 0.0, "echelle_w0": 1.0}]
    for i in range(1, n):
        out.append({"alpha0": lu(i, (*esp["alpha0"], 0)), "beta0": lu(i, (*esp["beta0"], 1)),
                    "nu0_plus": esp["nu0_plus"][0] + float(u[i, 2]) * (esp["nu0_plus"][1] - esp["nu0_plus"][0]),
                    "echelle_w0": lu(i, (*esp["echelle_w0"], 3))})
    return out


def priori_config(X, cfg):
    D = X.shape[1]
    return A.PrioriNW(float(cfg["alpha0"]), X.mean(0), float(cfg["beta0"]),
                      float(cfg["echelle_w0"]) * torch.cov(X.T).reshape(D, D), float(D) + float(cfg["nu0_plus"]))


def unite_n_init(memo, rapide, jeu):
    """Pilote : RELANCES_PILOTE relances indépendantes de chaque algorithme, critère de chacune (ajustées en lot)."""
    X, _, k_ref, kmax, _ = charger_jeu(jeu)
    n = 20 if rapide else RELANCES_PILOTE
    tol = float(PARAM.valeur("tol_rel"))
    lignes = []
    cas = [("EM", k_ref, None), ("EM", kmax, None), ("VB-emp", kmax, A.priori_empirique(X, 1.0 / kmax)),
           ("VB-diff", kmax, A.priori_diffus(X, 1.0 / kmax))]
    cas += [(f"VB-cfg{i}", kmax, priori_config(X, c)) for i, c in enumerate(_configs_aleatoires(4, _g("n_init", jeu), kmax)[1:])]
    for nom, K, pr in cas:
        if nom == "EM" and A.nb_parametres(K, X.shape[1], "full") >= len(X):
            continue
        def pilote():
            try:
                r = (A.em_classique(X, K, n_init=n, graine=_g("n_init", jeu, nom, K)) if nom == "EM"
                     else A.em_variationnel(X, K, priori=pr, n_init=n, graine=_g("n_init", jeu, nom, K)))
                return {"criteres": [c if not e else float("-inf") for c, e in
                                     zip(r["relances"]["critere"], r["relances"]["echec"])]}
            except A.EchecNumerique:
                return {"criteres": []}
        cr = memo(f"{nom}/K={K}", pilote)["criteres"]
        if not cr or all(c == float("-inf") for c in cr):
            lignes.append({"jeu": jeu, "algo": nom, "K": K, "p": 0.0, "n_requis": n, "toutes_echouent": True})
            continue
        p, m = _p_succes(cr, tol)
        lignes.append({"jeu": jeu, "algo": nom, "K": K, "p": p, "relances_valides": m, "n_requis": _n_requis(p, n)})
    return {"lignes": lignes}


def unite_n_init_texte(memo, rapide):
    import etape_texte as T
    cor = _corpus(rapide)
    comptes = cor["comptes"].double()
    sel = cor["reservoir"][:200]
    c = comptes[sel]
    n = 10 if rapide else RELANCES_PILOTE
    tol = float(PARAM.valeur("tol_rel"))
    esp = PARAM.valeur("espace_lda")
    lignes = []
    cas = [("pLSA", None)] + [(f"LDA-alpha={a}", a) for a in (esp["alpha"][0], math.sqrt(esp["alpha"][0] * esp["alpha"][1]),
                                                               esp["alpha"][1])]
    for nom, a in cas:
        cr = []
        for s in range(n):
            def f():
                r = (A.plsa_em(c, T.K, graine=_g("n_init_texte", s)) if a is None
                     else A.lda_variationnel(c, T.K, alpha=a, lissage=math.sqrt(esp["lissage"][0] * esp["lissage"][1]),
                                             graine=_g("n_init_texte", s)))
                return {"c": r["ll_hist"][-1] if "ll_hist" in r else r["bornes"][-1]}
            cr.append(memo(f"{nom}/s={s}", f)["c"])
        p, m = _p_succes(cr, tol)
        lignes.append({"jeu": "texte", "algo": nom, "p": p, "relances_valides": m, "n_requis": _n_requis(p, n)})
    return {"lignes": lignes}


FAMILLE_JEU = {"synthetique": "synthetique", "iris": "iris", "sp500": "sp500", "climat": "climat"}


def fin_n_init(memo, rapide):
    L = E.lignes("calibrage", rapide, "n_init/")
    val, det = {}, {}
    for l in L:
        fam = "texte" if l["jeu"] == "texte" else FAMILLE_JEU[l["jeu"].split("/")[0]]
        if l["n_requis"] > val.get(fam, 0):
            val[fam], det[fam] = l["n_requis"], {"jeu": l["jeu"], "algo": l["algo"], "p": l["p"]}
    return _ecrire("n_init", {"n_init": val},
                   "par famille, maximum sur les jeux et les algorithmes de ceil(ln 0,01 / ln(1 - p)), p = part des relances "
                   "pilotes à moins de 10 fois la tolérance (relative) du meilleur critère ; plafond = taille du pilote",
                   {"cas_determinant": det, "taille_pilote": RELANCES_PILOTE})


def unite_hmm(memo, rapide):
    import etape_sp500 as SP
    x, _, _ = SP.donnees()
    x = x.flatten()
    T = len(x)
    n = min(int(PARAM.valeur("n_init")["sp500"]), 3 if rapide else 10 ** 9)
    lignes = []
    for S_ in range(1, 6):
        fits = [memo(f"S={S_}/s={s}", lambda s=s: {"ll": A.baum_welch([x], S_, emission="gauss", graine=_g("hmm", S_, s))["loglik"]})
                for s in range(n)]
        ll = max(f["ll"] for f in fits)
        p = S_ * (S_ - 1) + (S_ - 1) + 2 * S_
        lignes.append({"S": S_, "loglik": ll, "n_parametres": p, "BIC": -2 * ll + p * math.log(T)})
    return {"lignes": lignes}


def fin_hmm(memo, rapide):
    L = E.lignes("calibrage", rapide, "hmm")
    b = min(L, key=lambda l: l["BIC"])
    return _ecrire("hmm", {"hmm_etats": b["S"]}, "nombre d'états minimisant le BIC sur la période d'apprentissage (S = 1 à 5)",
                   {"bic": {str(l["S"]): l["BIC"] for l in L}})


# ------------------------------------------------------------------------------ V5 : recherches heuristiques
def divisions_successives(memo, configs, n_taches, evaluer, m0=1):
    """
    Successive halving (Jamieson et Talwalkar 2016) : toutes les configurations sont évaluées sur m0 tâches, la
    meilleure moitié est gardée et évaluée sur deux fois plus de tâches, etc., jusqu'à une configuration ou
    jusqu'à épuisement des tâches. Score = moyenne des tâches (plus grand = meilleur). Toutes les évaluations sont rendues.
    """
    surv, m, etape, evals = list(range(len(configs))), m0, 0, []
    while True:
        m_eff = min(m, n_taches)
        sc = {}
        for i in surv:
            v = [memo(f"cfg={i}/tache={t}", lambda i=i, t=t: {"v": evaluer(configs[i], t)})["v"] for t in range(m_eff)]
            v = [x if x == x else float("-inf") for x in v]
            sc[i] = sum(v) / len(v)
            evals.append({"indice": i, "config": configs[i], "score": sc[i], "etape": etape, "taches": m_eff})
        if len(surv) == 1 or m_eff == n_taches:
            break
        surv = sorted(surv, key=lambda i: -sc[i])[:max(1, len(surv) // 2)]
        m, etape = 2 * m, etape + 1
    meilleur = max(surv, key=lambda i: sc[i])
    return configs[meilleur], evals


def _taches_priors(famille, rapide):
    """Liste de fonctions t -> (X_app, X_val) ; aucune donnée de test des étapes confirmatoires."""
    if famille == "synthetique":
        noms = [n for n, f in jeux(rapide) if f == "synthetique"]
        return [lambda n=n: charger_jeu(n, rep=1)[:2] for n in noms]
    if famille == "sp500":
        import etape_sp500 as SP
        x, _, _ = SP.donnees()
        n_plis = int(PARAM.valeur("n_plis"))
        b = torch.arange(len(x)) * n_plis // len(x)           # blocs temporels contigus
        return [lambda f=f: (x[b != f], x[b == f]) for f in range(n_plis)]
    import donnees_geo as G
    d = G.charger_climat(5)
    X = G.standardiser(d["X"])
    n_plis = int(PARAM.valeur("n_plis"))
    taches = []
    for rep in range(1 if rapide else 2):
        pli = C.plis_par_blocs(C.blocs_spatiaux(d["km"], float(PARAM.valeur("taille_bloc_km"))), n_plis, _g("priors_plis", rep))
        for f in range(n_plis):
            def t(f=f, rep=rep, pli=pli):
                tr = (pli != f).nonzero().flatten()
                tr = tr[torch.randperm(len(tr), generator=A.generateur(_g("priors_tr", rep, f)))[:2000]]
                return X[tr], X[pli == f]
            taches.append(t)
    return taches


def unite_priors(memo, rapide, famille):
    from risque import log_predictive_variationnel
    kmax = int(PARAM.valeur("k_max")[famille])
    n_init = min(int(PARAM.valeur("n_init")[famille]), 2 if rapide else 10 ** 9)
    configs = _configs_aleatoires(8 if rapide else N_CONFIGS, _g("priors", famille), kmax)
    taches = _taches_priors(famille, rapide)

    def evaluer(cfg, t):
        tr, va = taches[t]()
        try:
            v = A.em_variationnel(tr, kmax, priori=priori_config(tr, cfg), n_init=n_init, graine=_g("priors_fit", famille, t))
            return float(log_predictive_variationnel(va, v["P"]).mean())
        except A.EchecNumerique:
            return float("-inf")
    best, evals = divisions_successives(memo, configs, len(taches), evaluer)
    return {"lignes": [{"famille": famille, **best}], "artefacts": {"meilleure": best, "evaluations": evals}}


def fin_priors(memo, rapide):
    val, ev = {}, {}
    for r in E.resultats("calibrage", rapide, "priors/"):
        fam = r["lignes"][0]["famille"]
        val[fam], ev[fam] = r["artefacts"]["meilleure"], r["artefacts"]["evaluations"]
    return _ecrire("priors", {"priors_vb_calibres": val},
                   "par famille : recherche aléatoire (64 configurations dont le jeu empirique) puis divisions successives, "
                   "score = log-vraisemblance prédictive moyenne de validation (plis spatiaux pour le climat, blocs temporels "
                   "pour le S&P 500, jeux indépendants pour les scénarios)", {"evaluations": ev})


def _corpus(rapide):
    r = _mag(rapide).lire(f"corpus/V={int(PARAM.valeur('vocabulaire')['taille'])}")
    return r["artefacts"]


def unite_texte(memo, rapide):
    import etape_texte as T
    cor = _corpus(rapide)
    comptes = cor["comptes"].double()
    res = cor["reservoir"]
    esp = PARAM.valeur("espace_lda")
    n_init = min(int(PARAM.valeur("n_init")["texte"]), 2 if rapide else 10 ** 9)
    nc = 8 if rapide else N_CONFIGS_TEXTE
    u = torch.rand(nc, 2, generator=A.generateur(_g("texte")), dtype=torch.float64)

    def lu(x, b):
        return 10 ** (math.log10(b[0]) + float(x) * (math.log10(b[1]) - math.log10(b[0])))
    configs = [{"alpha": lu(u[i, 0], esp["alpha"]), "lissage": lu(u[i, 1], esp["lissage"])} for i in range(nc)]
    n_taches = 2 if rapide else int(PARAM.valeur("n_plis"))

    def evaluer(cfg, t):
        perm = res[torch.randperm(len(res), generator=A.generateur(_g("texte_tache", t)))]
        tr, va = comptes[perm[:200]], comptes[perm[200:400]]
        best = None
        for s in range(n_init):
            r = A.lda_variationnel(tr, T.K, alpha=cfg["alpha"], lissage=cfg["lissage"], graine=_g("texte_fit", t, s))
            if best is None or r["bornes"][-1] > best["bornes"][-1]:
                best = r
        obs, ev = T.separer_moitie(va, _g("texte_moitie", t))
        ppl, _ = T.perplexite(T.repli_lda(best["beta"], best["alpha"], obs), best["beta"], ev)
        return -math.log(ppl)
    best, evals = divisions_successives(memo, configs, n_taches, evaluer)
    return _ecrire("texte", {"lda_hyper": best},
                   "recherche aléatoire (32 configurations) puis divisions successives ; score = -log perplexité par complétion "
                   "de 200 documents de validation tirés du réservoir d'apprentissage", {"evaluations": evals})


def unite_variantes(memo, rapide):
    from risque import log_predictive_variationnel
    esp = PARAM.valeur("espace_variantes")
    nc = 6 if rapide else N_CONFIGS_VARIANTES
    u = torch.rand(nc, 8, generator=A.generateur(_g("variantes")), dtype=torch.float64)

    def lu(x, b):
        return 10 ** (math.log10(b[0]) + float(x) * (math.log10(b[1]) - math.log10(b[0])))
    configs = []
    for i in range(nc):
        configs.append({"online_kappa": esp["kappa"][0] + 1e-6 + float(u[i, 0]) * (esp["kappa"][1] - esp["kappa"][0] - 1e-6),
                        "online_t0": lu(u[i, 1], esp["t0"]), "online_lot": int(round(lu(u[i, 2], esp["lot"]))),
                        "svi_kappa": esp["kappa"][0] + 1e-6 + float(u[i, 3]) * (esp["kappa"][1] - esp["kappa"][0] - 1e-6),
                        "svi_tau": lu(u[i, 4], esp["tau"]), "svi_lot": int(round(lu(u[i, 2], esp["lot"]))),
                        "epoques": int(round(lu(u[i, 5], esp["epoques"]))),
                        "sem_n_iter": int(round(lu(u[i, 6], esp["sem_n_iter"])))})
        configs[-1]["sem_burn"] = int(configs[-1]["sem_n_iter"] * (esp["sem_part_burn"][0] + float(u[i, 7]) *
                                                                    (esp["sem_part_burn"][1] - esp["sem_part_burn"][0])))
    noms = [n for n, f in jeux(rapide) if f == "synthetique"][:2 if rapide else 8]
    kmax = int(PARAM.valeur("k_max")["synthetique"])
    out, evals_tout = {}, {}
    for meth in ("sem", "online", "svi"):
        def evaluer(cfg, t, meth=meth):
            tr, va, k, _, _ = charger_jeu(noms[t], rep=2)
            g = _g("variantes_fit", meth, t)
            try:
                if meth == "sem":
                    r = A.em_stochastique(tr, k, n_iter=cfg["sem_n_iter"], burn=cfg["sem_burn"], graine=g)
                    return C.logdens_plugin(r, va)
                if meth == "online":
                    r = A.em_online(tr, k, taille_lot=cfg["online_lot"], n_epoques=cfg["epoques"], kappa=cfg["online_kappa"],
                                    t0=cfg["online_t0"], graine=g)
                    return C.logdens_plugin(r, va)
                r = A.svi_gmm(tr, kmax, A.priori_empirique(tr, 1.0 / kmax), taille_lot=cfg["svi_lot"], n_epoques=cfg["epoques"],
                              tau=cfg["svi_tau"], kappa=cfg["svi_kappa"], graine=g)
                return float(log_predictive_variationnel(va, r["P"]).mean())
            except (A.EchecNumerique, RuntimeError):
                return float("-inf")
        def sous(c, f, meth=meth):
            return memo(f"{meth}/{c}", f)
        best, ev = divisions_successives(sous, configs, len(noms), evaluer)
        evals_tout[meth] = ev
        cles = {"sem": ("sem_n_iter", "sem_burn"), "online": ("online_kappa", "online_t0", "online_lot"),
                "svi": ("svi_kappa", "svi_tau", "svi_lot")}[meth]
        out.update({k: best[k] for k in cles})
        out[f"epoques_{meth}"] = best["epoques"]
    out["epoques"] = max(out.pop("epoques_sem"), out.pop("epoques_online"), out.pop("epoques_svi"))
    return _ecrire("variantes", {"variantes_stochastiques": out},
                   "par méthode : recherche aléatoire (32 configurations) puis divisions successives sur des jeux synthétiques "
                   "du protocole ; score = log-vraisemblance de validation (plug-in pour SEM et EM online, prédictive pour la SVI) ; "
                   "nombre d'époques commun = le plus grand des optima", {"evaluations": evals_tout})


# ------------------------------------------------------------------------------ V6 : marges, Monte Carlo
def unite_marges(memo, rapide, jeu):
    """Deux ajustements de chaque bras sur les MÊMES données, graines d'ajustement différentes."""
    X, Xt, k_ref, kmax, y = charger_jeu(jeu)
    fam = "climat" if jeu.startswith("climat") else "synthetique"
    n_init = min(int(PARAM.valeur("n_init")[fam]), 2 if rapide else 10 ** 9)
    bras = ("EM-BIC", "EM-Kmax", "VB-emp", "VB-cal")
    sorties = [C.bras_protocole(X, k_ref, kmax, n_init, _g("marges", jeu, s), fam, bras=bras,
                                memo=lambda c, f, s=s: memo(f"s={s}/{c}", f)) for s in (0, 1)]
    lignes = []
    for b in bras:
        r0, r1 = sorties[0].get(b, {}), sorties[1].get(b, {})
        if "echec" in r0 or "echec" in r1 or not r0 or not r1:
            continue
        l = {"jeu": jeu, "bras": b, "ecart_LL": abs(C.logdens_plugin(r0, Xt) - C.logdens_plugin(r1, Xt))}
        if y is not None:
            l["ecart_ARI"] = abs(A.indice_rand_ajuste(y, r0["labels"]) - A.indice_rand_ajuste(y, r1["labels"]))
        lignes.append(l)
    return {"lignes": lignes}


def fin_marges(memo, rapide):
    L = E.lignes("calibrage", rapide, "marges/")
    val = {}
    for m in ("ARI", "LL"):
        v = torch.tensor([l[f"ecart_{m}"] for l in L if f"ecart_{m}" in l and l[f"ecart_{m}"] == l[f"ecart_{m}"]],
                         dtype=torch.float64)
        val[m] = max(0.001, float(torch.quantile(v, 0.95))) if len(v) else 0.001
    return _ecrire("marges", {"marges_equivalence": val},
                   "quantile à 95 % de l'écart absolu entre deux ajustements du même bras (graines différentes, mêmes données), "
                   "tous jeux et bras confondus ; plancher 0,001", {"n_paires": len(L)})


def _plus_petit(grille, ecart_type_de):
    for n in grille:
        sd = ecart_type_de(n)
        if sd <= PRECISION_AFFICHAGE:
            return n, sd
    return grille[-1], ecart_type_de(grille[-1])


def unite_monte_carlo(memo, rapide):
    import risque as R
    import etape_sp500 as SP
    rep = 5 if rapide else REPETITIONS_MC
    det = {}
    # n_bootstrap_ic : bornes de l'intervalle bootstrap de la moyenne des différences appariées du pilote de marges
    d = [l["ecart_ARI"] for l in E.lignes("calibrage", rapide, "marges/") if "ecart_ARI" in l] or [0.0, 1.0]

    def sd_ic(B):
        b = torch.tensor([S.ic_bootstrap(d, B, graine=_g("mc_ic", B, r))[1:] for r in range(rep)])
        return float(b.std(0).max())
    n_ic, det["n_bootstrap_ic"] = _plus_petit((500, 1000, 2000, 5000, 10000, 20000, 50000), sd_ic)
    # n_tirages_posterieur et n_simulation_var : VB à priors empiriques sur l'apprentissage du S&P 500
    x, _, _ = SP.donnees()
    kmax = int(PARAM.valeur("k_max")["sp500"])
    vb = memo("vb_sp500", lambda: PE.resume_ajustement(A.em_variationnel(x, kmax, priori=A.priori_empirique(x, 1.0 / kmax),
                                                                         n_init=int(PARAM.valeur("n_init")["sp500"]),
                                                                         graine=_g("mc_vb")), avec_r=False))
    a = PARAM.valeur("niveaux_var")[-1]

    def sd_post(n):
        b = []
        for r in range(rep):
            pi, mu, sg = R.echantillonner_posterieur_gmm_1d(vb["P"], n, graine=_g("mc_post", n, r))
            q = R.quantile_melange_gauss(a, pi, mu, sg)
            b.append([float(torch.quantile(q, 0.025)), float(torch.quantile(q, 0.975))])
        return float(torch.tensor(b).std(0).max())
    n_post, det["n_tirages_posterieur"] = _plus_petit((1000, 2000, 4000, 8000, 16000, 32000), sd_post)

    def sd_var(n):
        return float(torch.tensor([R.var_es_student_melange(vb["P"], a, n=n, graine=_g("mc_var", n, r))
                                   for r in range(rep)]).std(0).max())
    n_var, det["n_simulation_var"] = _plus_petit((10_000, 50_000, 200_000, 500_000, 1_000_000, 2_000_000), sd_var)
    # n_bootstrap_modele : pilote de réplicats bootstrap (démarrage chaud) de la VaR, puis rééchantillonnage des réplicats
    em = memo("em_sp500", lambda: PE.resume_ajustement(A.em_classique(x, 2, n_init=int(PARAM.valeur("n_init")["sp500"]),
                                                                      graine=_g("mc_em")), avec_r=False))
    nb = 50 if rapide else 400

    def rep_boot(b):
        ib = torch.randint(len(x), (len(x),), generator=A.generateur(_g("mc_boot", b)))
        eb = C.em_demarrage_chaud(x[ib], em)
        return {"q": float(R.quantile_melange_gauss(a, eb["pi"], eb["mu"].reshape(-1), eb["cov"].reshape(-1).sqrt())[0])}
    pilote = torch.tensor([memo(f"boot/b={b}", lambda b=b: rep_boot(b))["q"] for b in range(nb)], dtype=torch.float64)

    def sd_boot(B):
        b = []
        for r in range(rep):
            e = pilote[torch.randint(nb, (B,), generator=A.generateur(_g("mc_boot_re", B, r)))]
            b.append([float(torch.quantile(e, 0.025)), float(torch.quantile(e, 0.975))])
        return float(torch.tensor(b).std(0).max())
    n_bm, det["n_bootstrap_modele"] = _plus_petit((200, 500, 1000, 2000, 5000, 10000), sd_boot)
    return _ecrire("monte_carlo", {"n_bootstrap_ic": n_ic, "n_tirages_posterieur": n_post, "n_simulation_var": n_var,
                                   "n_bootstrap_modele": n_bm},
                   "plus petite taille de la grille telle que l'écart-type Monte Carlo des bornes (20 répétitions) soit au plus "
                   "5e-4 (moitié de la 3e décimale affichée) ; bootstrap de modèle : rééchantillonnage d'un pilote de 400 réplicats",
                   {"ecart_type_obtenu": det})


# ------------------------------------------------------------------------------ V7 : puissance
def _cle_replication(h):
    if h.famille == "scenarios":
        return "scenarios"
    if h.famille == "texte":
        return "texte"
    return {"semi": "climat_semi", "sous": "climat_sous", "d20": "climat_d20"}[h.filtre["plan"]]


def unites_pilotes(rapide, dep):
    import scenarios as SC
    R = _taille_pilote(rapide)
    us = [E.Unite("calibrage", "reference", "etape_climat", "unite_reference", depend=dep)]
    pts = {(h.filtre["scenario"], h.filtre.get("parametre")) for h in HY.famille("scenarios")}
    for sc, par, fab, kv, kc in SC._plan(False):
        if (sc, par) in pts or (sc, None) in pts:
            for r in range(R):
                us.append(E.Unite("calibrage", f"puissance/pilote/scenarios/{sc}/{par}/rep={r:03d}", "scenarios", "unite_scenario",
                                  dict(scenario=sc, parametre=par, fabrique=fab, k_vrai=kv, k_choisi=kc,
                                       rep=DECALAGE_PILOTE + r), depend=dep))
    for h in HY.famille("climat"):
        for r in range(R):
            pl, N = h.filtre["plan"], int(h.filtre["N"])
            cle = f"puissance/pilote/climat/{pl}/N={N}/rep={r:03d}"
            if any(u.cle == cle for u in us):
                continue
            if pl == "semi":
                us.append(E.Unite("calibrage", cle, "etape_climat", "unite_semi",
                                  dict(N=N, rep=DECALAGE_PILOTE + r, etape_reference="calibrage"), depend=dep + ("reference",)))
            else:
                us.append(E.Unite("calibrage", cle, "etape_climat", "unite_sous",
                                  dict(N=N, rep=DECALAGE_PILOTE + r, D=20 if pl == "d20" else 5), depend=dep))
    V0 = int(PARAM.valeur("vocabulaire")["taille"])
    for h in HY.famille("texte"):
        for r in range(R):
            us.append(E.Unite("calibrage", f"puissance/pilote/texte/N={h.filtre['N']}/rep={r:03d}", "etape_texte",
                              "unite_echantillon", dict(V=V0, N=int(h.filtre["N"]), rep=DECALAGE_PILOTE + r,
                                                        etape_corpus="calibrage"), depend=dep + (f"corpus/V={V0}",)))
    return us


def _r_requis(d, h, m, alpha):
    """Plus petit R de la grille avec une puissance >= 0,8 au niveau alpha / m (première étape de Holm), par dichotomie."""
    if h.test == "equivalence":
        marge = HY.marge(h)
    else:
        marge = HY.marge(h) if h.marge else float(PARAM.valeur("effet_standardise")) * float(torch.tensor(d).std())
    if marge is None or marge <= 0 or len(d) < 2:
        return GRILLE_R[-1], float("nan"), "pilote sans variance"
    lo, hi = 0, len(GRILLE_R) - 1
    pw = {}

    def p(i):
        if i not in pw:
            pw[i] = S.puissance_simulee(d, GRILLE_R[i], h.test, marge, alpha / m, n_sim=N_SIM_PUISSANCE,
                                        graine=_g("puissance", h.id, GRILLE_R[i]))
        return pw[i]
    if p(hi) < PUISSANCE_CIBLE:
        return GRILLE_R[-1], p(hi), "plafond atteint"
    while lo < hi:
        mi = (lo + hi) // 2
        if p(mi) >= PUISSANCE_CIBLE:
            hi = mi
        else:
            lo = mi + 1
    return GRILLE_R[lo], p(lo), ""


def fin_puissance(memo, rapide):
    alpha = float(PARAM.valeur("alpha_test"))
    lignes = {"scenarios": E.lignes("calibrage", rapide, "puissance/pilote/scenarios/"),
              "climat": E.lignes("calibrage", rapide, "puissance/pilote/climat/"),
              "texte": E.lignes("calibrage", rapide, "puissance/pilote/texte/")}
    for l in lignes["climat"]:
        if l.get("plan") == "semi" and "k_hat" in l:
            l.setdefault("erreur_k", abs(l["k_hat"] - 5))
    val, det = {}, []
    for fam in ("scenarios", "climat", "texte"):
        hs = HY.famille(fam)
        for h in hs:
            d = HY.diffs(h, lignes[fam])
            R, pw, note = _r_requis(d, h, len(hs), alpha)
            cle = _cle_replication(h)
            val[cle] = max(val.get(cle, 0), R)
            det.append({"id": h.id, "cle": cle, "n_pilote": len(d), "R": R, "puissance": pw, "remarque": note})
    val["climat_sensibilite"] = val.get("climat_sous", GRILLE_R[-1])
    return _ecrire("puissance", {"replications": val},
                   "par clé, maximum sur les hypothèses de la famille du plus petit R (grille 10 à 200) donnant une puissance "
                   "simulée >= 0,8 au niveau alpha / m (première étape de Holm) ; équivalence : différences du pilote recentrées "
                   "à 0 ; différence : recentrées à la marge (ou à 0,5 écart-type) ; climat_sensibilite = climat_sous "
                   "(même plan de sous-échantillonnage)", {"hypotheses": det})


# ------------------------------------------------------------------------------ étape
def unites(rapide: bool):
    U = lambda c, f, dep=(), **k: E.Unite("calibrage", c, "calibrage", f, k, depend=tuple(dep))
    J = [n for n, _ in jeux(rapide)]
    us = [U(f"kmeans/{j}", "unite_kmeans", jeu=j) for j in J] + [U("spatial", "unite_spatial")]
    us += [U("fin/kmeans", "fin_kmeans", dep=[f"kmeans/{j}" for j in J]), U("fin/spatial", "fin_spatial", dep=["spatial"])]
    v1 = ("fin/kmeans", "fin/spatial")
    us += [U(f"tolerance/{j}", "unite_tolerance", dep=v1, jeu=j) for j in J]
    us.append(U("fin/tolerance", "fin_tolerance", dep=[f"tolerance/{j}" for j in J]))
    v2 = v1 + ("fin/tolerance",)
    us += [U(f"regularisation/{j}", "unite_regularisation", dep=v2, jeu=j) for j in J]
    us.append(U("fin/regularisation", "fin_regularisation", dep=[f"regularisation/{j}" for j in J]))
    v3 = v2 + ("fin/regularisation",)
    V0 = int(PARAM.valeur("vocabulaire")["taille"])
    us.append(E.Unite("calibrage", f"corpus/V={V0}", "etape_texte", "unite_corpus", dict(V=V0)))
    us += [U(f"n_init/{j}", "unite_n_init", dep=v3, jeu=j) for j in J]
    us.append(U("n_init/texte", "unite_n_init_texte", dep=v3 + (f"corpus/V={V0}",)))
    us.append(U("fin/n_init", "fin_n_init", dep=[f"n_init/{j}" for j in J] + ["n_init/texte"]))
    v4a = v3 + ("fin/n_init",)
    us += [U("hmm", "unite_hmm", dep=v4a), U("fin/hmm", "fin_hmm", dep=["hmm"])]
    v4 = v4a + ("fin/hmm",)
    us += [U(f"priors/{f}", "unite_priors", dep=v4, famille=f) for f in ("synthetique", "climat", "sp500")]
    us.append(U("fin/priors", "fin_priors", dep=[f"priors/{f}" for f in ("synthetique", "climat", "sp500")]))
    us += [U("fin/texte", "unite_texte", dep=v4 + (f"corpus/V={V0}",)), U("fin/variantes", "unite_variantes", dep=v4)]
    v5 = v4 + ("fin/priors", "fin/texte", "fin/variantes")
    Jm = [j for j in J if j.startswith(("synthetique/", "climat/"))]        # jeux munis d'une partition de référence
    us += [U(f"marges/{j}", "unite_marges", dep=v5, jeu=j) for j in Jm]
    us.append(U("fin/marges", "fin_marges", dep=[f"marges/{j}" for j in Jm]))
    us.append(U("fin/monte_carlo", "unite_monte_carlo", dep=v5 + ("fin/marges",)))
    v6 = v5 + ("fin/marges", "fin/monte_carlo")
    pil = unites_pilotes(rapide, v6)
    us += pil
    us.append(U("fin/puissance", "fin_puissance", dep=[u.cle for u in pil]))
    return us


def agreger(rapide: bool):
    E.ecrire_csv("calibrage_registre", PARAM.tableau(), rapide)
    for pre in ("tolerance/", "regularisation/", "n_init/", "marges/", "hmm"):
        L = E.lignes("calibrage", rapide, pre)
        if L:
            E.ecrire_csv("calibrage_" + pre.strip("/"), L, rapide)
    sp = _mag(rapide).lire("spatial")
    if sp is not None:
        a = sp["artefacts"]
        E.ecrire_csv("calibrage_variogramme", [{"h_km": float(h), "gamma": float(g), "paires": float(e)}
                                               for h, g, e in zip(a["h"], a["gamma"], a["effectifs"]) if e > 0], rapide)
