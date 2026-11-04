"""
================================================================================
ÉTAPE « calibrage » : fixe, selon les règles écrites dans parametres.py, toutes les valeurs non mathématiques
================================================================================

Sept vagues, enchaînées par dépendances (une unité ne lit que des valeurs déjà calibrées par une vague antérieure) :
  V1  kmeans/<jeu>                       plafond de Lloyd
  V2  tolerance/<jeu>                    tolérance relative et plafond d'étapes M
  V3  regularisation/<jeu>               régularisation des covariances (validation croisée ; blocs temporels pour les prix)
  V4  n_init/<jeu>                       nombre de relances par famille
  V5  priors/<famille>, texte, variantes recherche aléatoire + divisions successives (successive halving)
  V6  marges/<jeu>, monte_carlo          marges d'équivalence (bruit d'optimisation) ; tailles Monte Carlo
  V7  puissance/pilote/..., puissance    réplications pilotes (graines disjointes) et puissance simulée
Chaque vague se termine par une unité « fin/<id> » qui écrit resultats/calibrage/<id>.json :
  {"valeurs": {...}, "regle": "...", "details": {...}, "date": "..."}
Toutes les évaluations intermédiaires sont conservées dans le magasin (reprise exacte et traçabilité).
"""

from __future__ import annotations

import importlib
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
    out += [("iris", "iris")]
    out += [(f"prix/N={n}", "prix") for n in ((250,) if rapide else (60, 120, 250, 562))]
    return out


K_REF_PRIX_CALIBRAGE = 4          # K des pilotes de calibrage pour les prix : les quatre phases usuelles d'alerte (k_max = 2 x 4)


def charger_jeu(nom, rep=0):
    """
    (X_apprentissage, X_test, k_ref, kmax, etiquettes ou None). Données tirées avec des graines propres au calibrage.
    Prix : uniquement la période d'APPRENTISSAGE ; le sous-échantillon est remis dans l'ordre du temps (plis temporels
    contigus) et le « test » du calibrage est le reste de l'apprentissage (jamais la période de test).
    """
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
    if nom.startswith("prix/"):
        import etape_prix as P
        Xtr, _, _ = P.donnees()
        N = min(int(nom.split("=")[1]), len(Xtr))
        perm = torch.randperm(len(Xtr), generator=A.generateur(_g(nom, rep)))
        idx, reste = perm[:N].sort().values, perm[N:]
        return Xtr[idx], Xtr[reste] if len(reste) else Xtr[idx], K_REF_PRIX_CALIBRAGE, int(PARAM.valeur("k_max")["prix"]), None
    raise KeyError(nom)


def _taille_pilote(rapide):
    return 3 if rapide else int(PARAM.valeur("taille_pilote"))


# ------------------------------------------------------------------------------ V1 : k-means
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
    if jeu.startswith("prix/"):
        return plis_temporels(len(X), n_plis), n_plis                      # X est dans l'ordre du temps (charger_jeu)
    return torch.randperm(len(X), generator=A.generateur(_g("plis", jeu))) % n_plis, n_plis


def plis_temporels(n, n_plis):
    """Plis par blocs CONTIGUS d'observations ordonnées dans le temps (validation croisée par blocs, Roberts et al. 2017)."""
    return torch.arange(n) * n_plis // n


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
                   "rang moyen minimal de la log-vraisemblance hors pli (validation croisée ; plis temporels contigus pour les "
                   "prix), sur tous les jeux, K de référence et Kmax, graines pilotes ; à égalité, la plus petite valeur",
                   {"rang_moyen": {str(k): v for k, v in moy.items()}, "n_comparaisons": len(rangs[GRILLE_REG[0]])})


# ------------------------------------------------------------------------------ V4 : n_init
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


def _relance_n_init_texte(rapide, a, s):
    """Une relance du pilote n_init du texte (pLSA si a est None, sinon LDA d'hyperparamètre alpha = a)."""
    import etape_texte as T
    c = _corpus(rapide)["comptes"].double()[_corpus(rapide)["reservoir"][:200]]
    esp = PARAM.valeur("espace_lda")
    r = (A.plsa_em(c, T.K, graine=_g("n_init_texte", s)) if a is None
         else A.lda_variationnel(c, T.K, alpha=a, lissage=math.sqrt(esp["lissage"][0] * esp["lissage"][1]),
                                 graine=_g("n_init_texte", s)))
    return {"c": r["ll_hist"][-1] if "ll_hist" in r else r["bornes"][-1]}


def unite_n_init_texte(memo, rapide):
    n = 10 if rapide else RELANCES_PILOTE
    tol = float(PARAM.valeur("tol_rel"))
    esp = PARAM.valeur("espace_lda")
    lignes = []
    cas = [("pLSA", None)] + [(f"LDA-alpha={a}", a) for a in (esp["alpha"][0], math.sqrt(esp["alpha"][0] * esp["alpha"][1]),
                                                               esp["alpha"][1])]
    E.sous_taches_paralleles(memo, [(f"{nom}/s={s}", "calibrage", "_relance_n_init_texte", dict(rapide=rapide, a=a, s=s))
                                    for nom, a in cas for s in range(n)])
    for nom, a in cas:
        cr = []
        for s in range(n):
            cr.append(memo(f"{nom}/s={s}", lambda a=a, s=s: _relance_n_init_texte(rapide, a, s))["c"])
        p, m = _p_succes(cr, tol)
        lignes.append({"jeu": "texte", "algo": nom, "p": p, "relances_valides": m, "n_requis": _n_requis(p, n)})
    return {"lignes": lignes}


FAMILLE_JEU = {"synthetique": "synthetique", "iris": "iris", "prix": "prix"}


ECART_RELANCES_TEXTE = 1e-3     # écart relatif toléré au meilleur des 200 relances (D-14)
PLAFOND_RELANCES_TEXTE = 20
TIRAGES_RELANCES_TEXTE = 4000


def fin_n_init_texte(memo, rapide):
    """
    Décision D-14 : relances des étapes confirmatoires du texte, par algorithme, à partir des critères des relances
    pilotes déjà calculées (n_init/texte/_sous/<cas>/s=<s>) : plus petit n <= 20 tel que P(meilleur de n relances tirées
    parmi le pilote >= meilleur du pilote - 0,1 % |meilleur|) >= 0,99. Aucun nouvel ajustement.
    """
    n_pil = 10 if rapide else RELANCES_PILOTE
    esp = PARAM.valeur("espace_lda")
    cas = [("pLSA", None)] + [(f"LDA-alpha={a}", a) for a in (esp["alpha"][0], math.sqrt(esp["alpha"][0] * esp["alpha"][1]),
                                                               esp["alpha"][1])]
    mag = _mag(rapide)
    val, det = {}, {}
    for nom, _ in cas:
        c = torch.tensor([mag.lire(f"n_init/texte/_sous/{nom}/s={s}")["c"] for s in range(n_pil)], dtype=torch.float64)
        c = c[torch.isfinite(c)]
        best = float(c.max())
        seuil = best - ECART_RELANCES_TEXTE * abs(best)
        retenu, proba = PLAFOND_RELANCES_TEXTE, None
        probas = {}
        for n in range(1, min(PLAFOND_RELANCES_TEXTE, len(c)) + 1):
            g = A.generateur(_g("n_init_texte_conf", nom, n))
            ok = sum(float(c[torch.randperm(len(c), generator=g)[:n]].max()) >= seuil for _ in range(TIRAGES_RELANCES_TEXTE))
            probas[n] = ok / TIRAGES_RELANCES_TEXTE
            if probas[n] >= 0.99:
                retenu, proba = n, probas[n]
                break
        if proba is None:
            proba = probas[max(probas)]
        algo = "pLSA" if nom == "pLSA" else "LDA"
        if retenu > val.get(algo, 0):
            val[algo] = retenu
        det[nom] = {"n": retenu, "probabilite": proba, "meilleur": best, "relances_pilote": int(len(c)),
                    "part_dans_l_ecart": float((c >= seuil).double().mean())}
    return _ecrire("n_init_texte", {"n_init_texte_confirmatoire": val},
                   "D-14 : par algorithme, plus petit n <= 20 tel que la meilleure de n relances (tirées sans remise parmi les "
                   "relances pilotes) soit à moins de 0,1 % du meilleur critère pilote avec probabilité >= 0,99 ; LDA : "
                   "maximum sur les trois valeurs de alpha", det)


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


# ------------------------------------------------------------------------------ V5 : recherches heuristiques
def divisions_successives(memo, configs, n_taches, evaluer, m0=1, precalcul=None):
    """
    Successive halving (Jamieson et Talwalkar 2016) : toutes les configurations sont évaluées sur m0 tâches, la
    meilleure moitié est gardée et évaluée sur deux fois plus de tâches, etc., jusqu'à une configuration ou
    jusqu'à épuisement des tâches. Score = moyenne des tâches (plus grand = meilleur). Toutes les évaluations sont rendues.
    precalcul(paires) : calcule d'avance, en parallèle, les évaluations (indice, tâche) d'une division (voir
    etapes.sous_taches_paralleles) ; la boucle les relit ensuite par memo, sans changer le résultat.
    """
    surv, m, etape, evals = list(range(len(configs))), m0, 0, []
    while True:
        m_eff = min(m, n_taches)
        if precalcul is not None:
            precalcul([(i, t) for i in surv for t in range(m_eff)])
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
    if famille == "prix":
        import etape_prix as P
        x, _, _ = P.donnees()                                 # période d'apprentissage seule, dans l'ordre du temps
        n_plis = int(PARAM.valeur("n_plis"))
        b = plis_temporels(len(x), n_plis)
        return [lambda f=f: (x[b != f], x[b == f]) for f in range(n_plis)]
    raise KeyError(famille)


_TACHES_PRIORS = {}


def _evaluer_priors(rapide, famille, cfg, t):
    """Score d'une configuration de priors sur la tâche t (log-vraisemblance prédictive moyenne de validation)."""
    from risque import log_predictive_variationnel
    if (famille, rapide) not in _TACHES_PRIORS:
        _TACHES_PRIORS[(famille, rapide)] = _taches_priors(famille, rapide)
    kmax = int(PARAM.valeur("k_max")[famille])
    n_init = min(int(PARAM.valeur("n_init")[famille]), 2 if rapide else 10 ** 9)
    tr, va = _TACHES_PRIORS[(famille, rapide)][t]()
    try:
        v = A.em_variationnel(tr, kmax, priori=priori_config(tr, cfg), n_init=n_init, graine=_g("priors_fit", famille, t))
        return float(log_predictive_variationnel(va, v["P"]).mean())
    except A.EchecNumerique:
        return float("-inf")


def _evaluation_memo(fonction, **k):
    """Valeur mémorisée d'une évaluation de divisions_successives ({"v": score}), calculée dans un processus de travail."""
    return {"v": globals()[fonction](**k)}


def _precalcul(memo, configs, fonction, prefixe="", **k):
    """precalcul de divisions_successives : les évaluations (indice, tâche) d'une division, en parallèle."""
    return lambda paires: E.sous_taches_paralleles(memo, [
        (f"{prefixe}cfg={i}/tache={t}", "calibrage", "_evaluation_memo", dict(fonction=fonction, cfg=configs[i], t=t, **k))
        for i, t in paires])


def unite_priors(memo, rapide, famille):
    kmax = int(PARAM.valeur("k_max")[famille])
    configs = _configs_aleatoires(8 if rapide else N_CONFIGS, _g("priors", famille), kmax)
    n_taches = len(_taches_priors(famille, rapide))

    def evaluer(cfg, t):
        return _evaluer_priors(rapide, famille, cfg, t)
    best, evals = divisions_successives(memo, configs, n_taches, evaluer,
                                        precalcul=_precalcul(memo, configs, "_evaluer_priors", rapide=rapide, famille=famille))
    return {"lignes": [{"famille": famille, **best}], "artefacts": {"meilleure": best, "evaluations": evals}}


def fin_priors(memo, rapide):
    val, ev = {}, {}
    for r in E.resultats("calibrage", rapide, "priors/"):
        fam = r["lignes"][0]["famille"]
        val[fam], ev[fam] = r["artefacts"]["meilleure"], r["artefacts"]["evaluations"]
    return _ecrire("priors", {"priors_vb_calibres": val},
                   "par famille : recherche aléatoire (64 configurations dont le jeu empirique) puis divisions successives, "
                   "score = log-vraisemblance prédictive moyenne de validation (blocs temporels contigus de la période "
                   "d'apprentissage pour les prix, jeux indépendants pour les scénarios)", {"evaluations": ev})


_CORPUS = {}                        # corpus relu une fois par processus (unité terminée, donc immuable)


def _corpus(rapide):
    cle = f"corpus/V={int(PARAM.valeur('vocabulaire')['taille'])}"
    if (rapide, cle) not in _CORPUS:
        _CORPUS[(rapide, cle)] = _mag(rapide).lire(cle)["artefacts"]
    return _CORPUS[(rapide, cle)]


def _n_init_texte(rapide):
    return min(int(PARAM.valeur("n_init")["texte"]), 2 if rapide else 10 ** 9)


def _tache_texte(rapide, t):
    """Documents d'apprentissage et de validation de la tâche t (200 + 200, tirés du réservoir d'apprentissage)."""
    cor = _corpus(rapide)
    comptes = cor["comptes"].double()
    res = cor["reservoir"]
    perm = res[torch.randperm(len(res), generator=A.generateur(_g("texte_tache", t)))]
    return comptes[perm[:200]], comptes[perm[200:400]]


def _ajuster_texte(rapide, cfg, t, s):
    """Relance s de la LDA de la configuration cfg sur la tâche t."""
    import etape_texte as T
    tr, _ = _tache_texte(rapide, t)
    return A.lda_variationnel(tr, T.K, alpha=cfg["alpha"], lissage=cfg["lissage"], graine=_g("texte_fit", t, s))


def _borne_texte(rapide, cfg, t, s):
    """Borne finale de la relance s (seule valeur gardée : elle suffit à désigner la meilleure relance)."""
    return {"b": _ajuster_texte(rapide, cfg, t, s)["bornes"][-1]}


def _evaluer_texte(rapide, cfg, t, bornes=None):
    """
    Score d'une configuration LDA sur la tâche t (- log perplexité par complétion de 200 documents de validation),
    calculé sur la meilleure des n_init relances (plus grande borne ; à égalité, la première).
    bornes : bornes finales des relances, déjà calculées (une sous-tâche par relance) ; seule la meilleure est alors
    réajustée, avec sa graine, ce qui redonne exactement le même ajustement.
    """
    import etape_texte as T
    _, va = _tache_texte(rapide, t)
    if bornes is None:
        best = None
        for s in range(_n_init_texte(rapide)):
            r = _ajuster_texte(rapide, cfg, t, s)
            if best is None or r["bornes"][-1] > best["bornes"][-1]:
                best = r
    else:
        s_best = 0
        for s in range(1, len(bornes)):
            if bornes[s] > bornes[s_best]:
                s_best = s
        best = _ajuster_texte(rapide, cfg, t, s_best)
    obs, ev = T.separer_moitie(va, _g("texte_moitie", t))
    ppl, _ = T.perplexite(T.repli_lda(best["beta"], best["alpha"], obs), best["beta"], ev)
    return -math.log(ppl)


def _configs_texte(rapide):
    """Configurations (alpha, lissage) de la recherche LDA, tirées log-uniformément dans « espace_lda »."""
    esp = PARAM.valeur("espace_lda")
    nc = 8 if rapide else N_CONFIGS_TEXTE
    u = torch.rand(nc, 2, generator=A.generateur(_g("texte")), dtype=torch.float64)

    def lu(x, b):
        return 10 ** (math.log10(b[0]) + float(x) * (math.log10(b[1]) - math.log10(b[0])))
    return [{"alpha": lu(u[i, 0], esp["alpha"]), "lissage": lu(u[i, 1], esp["lissage"])} for i in range(nc)]


def _precalcul_texte(memo, configs, rapide):
    """
    precalcul de la recherche LDA, en deux temps, pour qu'aucun calcul ne dure plus d'un ajustement sans être écrit :
    1. chaque relance (configuration, tâche, graine) est une sous-tâche, qui mémorise sa borne finale ;
    2. chaque évaluation réajuste sa meilleure relance (même graine, donc même ajustement) et mémorise son score.
    Avec n_init = 200, une évaluation enchaînait sinon 200 LDA sur un coeur (plusieurs heures sans écriture).
    """
    n = _n_init_texte(rapide)

    def precalcul(paires):
        paires = [(i, t) for i, t in paires if not memo.mag.existe(f"{memo.prefixe}/_sous/cfg={i}/tache={t}")]
        E.sous_taches_paralleles(memo, [(f"relances/cfg={i}/tache={t}/s={s}", "calibrage", "_borne_texte",
                                         dict(rapide=rapide, cfg=configs[i], t=t, s=s)) for i, t in paires for s in range(n)])
        taches = []
        for i, t in paires:
            bornes = [memo.mag.lire(f"{memo.prefixe}/_sous/relances/cfg={i}/tache={t}/s={s}") for s in range(n)]
            if all(b is not None for b in bornes):
                taches.append((f"cfg={i}/tache={t}", "calibrage", "_evaluation_memo",
                               dict(fonction="_evaluer_texte", rapide=rapide, cfg=configs[i], t=t,
                                    bornes=[b["b"] for b in bornes])))
        E.sous_taches_paralleles(memo, taches)
    return precalcul


def unite_texte(memo, rapide):
    configs = _configs_texte(rapide)
    n_taches = 2 if rapide else int(PARAM.valeur("n_plis"))

    def evaluer(cfg, t):
        return _evaluer_texte(rapide, cfg, t)
    best, evals = divisions_successives(memo, configs, n_taches, evaluer,
                                        precalcul=_precalcul_texte(memo, configs, rapide))
    return _ecrire("texte", {"lda_hyper": best},
                   "recherche aléatoire (32 configurations) puis divisions successives ; score = -log perplexité par complétion "
                   "de 200 documents de validation tirés du réservoir d'apprentissage", {"evaluations": evals})


def _noms_variantes(rapide):
    return [n for n, f in jeux(rapide) if f == "synthetique"][:2 if rapide else 8]


def _evaluer_variantes(rapide, meth, cfg, t):
    """Score d'une configuration d'une variante stochastique (sem, online, svi) sur le jeu synthétique t."""
    from risque import log_predictive_variationnel
    kmax = int(PARAM.valeur("k_max")["synthetique"])
    tr, va, k, _, _ = charger_jeu(_noms_variantes(rapide)[t], rep=2)
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


def unite_variantes(memo, rapide):
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
    n_noms = len(_noms_variantes(rapide))
    out, evals_tout = {}, {}
    for meth in ("sem", "online", "svi"):
        def evaluer(cfg, t, meth=meth):
            return _evaluer_variantes(rapide, meth, cfg, t)
        def sous(c, f, meth=meth):
            return memo(f"{meth}/{c}", f)
        best, ev = divisions_successives(sous, configs, n_noms, evaluer,
                                         precalcul=_precalcul(memo, configs, "_evaluer_variantes", prefixe=f"{meth}/",
                                                              rapide=rapide, meth=meth))
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
    fam = "prix" if jeu.startswith("prix") else "synthetique"
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
    """
    Contrôle des marges d'équivalence (décision D-04) : les marges sont fixées a priori dans le registre
    (« marges_equivalence ») ; cette étude mesure seulement le bruit d'optimisation (quantile à 95 % de l'écart absolu
    entre deux ajustements du même bras, graines différentes, mêmes données) et vérifie que chaque marge le dépasse.
    """
    L = E.lignes("calibrage", rapide, "marges/")
    marges = PARAM.valeur("marges_equivalence")
    bruit, controle = {}, {}
    for m in ("ARI", "LL"):
        v = torch.tensor([l[f"ecart_{m}"] for l in L if f"ecart_{m}" in l and l[f"ecart_{m}"] == l[f"ecart_{m}"]],
                         dtype=torch.float64)
        bruit[m] = float(torch.quantile(v, 0.95)) if len(v) else float("nan")
        controle[m] = "marge > bruit" if bruit[m] < float(marges[m]) else "ATTENTION : marge <= bruit d'optimisation"
    return _ecrire("marges", {"bruit_optimisation": bruit},
                   "contrôle seulement (D-04) : quantile à 95 % de l'écart absolu entre deux ajustements du même bras "
                   "(graines différentes, mêmes données), tous jeux et bras confondus, comparé aux marges fixées a priori",
                   {"n_paires": len(L), "marges": marges, "controle": controle})


def _plus_petit(grille, ecart_type_de):
    for n in grille:
        sd = ecart_type_de(n)
        if sd <= PRECISION_AFFICHAGE:
            return n, sd
    return grille[-1], ecart_type_de(grille[-1])


def unite_monte_carlo(memo, rapide):
    import etape_prix as P
    rep = 5 if rapide else REPETITIONS_MC
    det = {}
    # n_bootstrap_ic : bornes de l'intervalle bootstrap de la moyenne des différences appariées du pilote de marges
    d = [l["ecart_ARI"] for l in E.lignes("calibrage", rapide, "marges/") if "ecart_ARI" in l] or [0.0, 1.0]

    def sd_ic(B):
        b = torch.tensor([S.ic_bootstrap(d, B, graine=_g("mc_ic", B, r))[1:] for r in range(rep)])
        return float(b.std(0).max())
    n_ic, det["n_bootstrap_ic"] = _plus_petit((500, 1000, 2000, 5000, 10000, 20000, 50000), sd_ic)
    # n_tirages_posterieur : bornes à 5 % et 95 % des poids pi_k sous q (VB à priors empiriques, apprentissage des prix)
    x, _, _ = P.donnees()
    kmax = int(PARAM.valeur("k_max")["prix"])
    n_init = int(PARAM.valeur("n_init")["prix"])
    vb = memo("vb_prix", lambda: PE.resume_ajustement(A.em_variationnel(x, kmax, priori=A.priori_empirique(x, 1.0 / kmax),
                                                                       n_init=n_init, graine=_g("mc_vb")), avec_r=False))
    q90 = torch.tensor([0.05, 0.95], dtype=torch.float64)

    def sd_post(n):
        b = []
        for r in range(rep):
            pis, _, _ = P.tirages_q(vb["P"], n, _g("mc_post", n, r))
            b.append(torch.quantile(pis, q90, dim=0).flatten())
        return float(torch.stack(b).std(0).max())
    n_post, det["n_tirages_posterieur"] = _plus_petit((1000, 2000, 4000, 8000, 16000, 32000), sd_post)
    # n_bootstrap_modele : pilote de réplicats bootstrap (démarrage chaud, alignement hongrois) des poids de l'EM à
    # K_REF_PRIX_CALIBRAGE, puis rééchantillonnage des réplicats
    em = memo("em_prix", lambda: PE.resume_ajustement(A.em_classique(x, K_REF_PRIX_CALIBRAGE, n_init=n_init,
                                                                     graine=_g("mc_em")), avec_r=False))
    nb = 50 if rapide else 400

    def rep_boot(b):
        ib = torch.randint(len(x), (len(x),), generator=A.generateur(_g("mc_boot", b)))
        eb = C.em_demarrage_chaud(x[ib], em)
        return {"pi": eb["pi"][A.hongrois(torch.cdist(em["mu"], eb["mu"]).pow(2))]}
    pilote = torch.stack([memo(f"boot/b={b}", lambda b=b: rep_boot(b))["pi"] for b in range(nb)])

    def sd_boot(B):
        b = []
        for r in range(rep):
            e = pilote[torch.randint(nb, (B,), generator=A.generateur(_g("mc_boot_re", B, r)))]
            b.append(torch.quantile(e, q90, dim=0).flatten())
        return float(torch.stack(b).std(0).max())
    n_bm, det["n_bootstrap_modele"] = _plus_petit((200, 500, 1000, 2000, 5000, 10000), sd_boot)
    return _ecrire("monte_carlo", {"n_bootstrap_ic": n_ic, "n_tirages_posterieur": n_post, "n_bootstrap_modele": n_bm},
                   "plus petite taille de la grille telle que l'écart-type Monte Carlo des bornes (20 répétitions) soit au plus "
                   "5e-4 (moitié de la 3e décimale affichée) ; bornes à 5 et 95 % des poids (couverture à 90 %) ; bootstrap de "
                   "modèle : rééchantillonnage d'un pilote de 400 réplicats", {"ecart_type_obtenu": det})


# ------------------------------------------------------------------------------ V7 : puissance
def _cle_replication(h):
    if h.famille == "scenarios":
        return "scenarios"
    if h.famille == "texte":
        return "texte"
    return {"semi": "prix_semi", "sous": "prix_sous", "sensibilite": "prix_sensibilite"}[h.filtre["plan"]]


def unites_pilotes(rapide, dep):
    import scenarios as SC
    R = _taille_pilote(rapide)
    us = [E.Unite("calibrage", "reference", "etape_prix", "unite_reference", depend=dep)]
    pts = {(h.filtre["scenario"], h.filtre.get("parametre")) for h in HY.famille("scenarios")}
    for sc, par, fab, kv, kc in SC._plan(False):
        if (sc, par) in pts or (sc, None) in pts:
            for r in range(R):
                us.append(E.Unite("calibrage", f"puissance/pilote/scenarios/{sc}/{par}/rep={r:03d}", "scenarios", "unite_scenario",
                                  dict(scenario=sc, parametre=par, fabrique=fab, k_vrai=kv, k_choisi=kc,
                                       rep=DECALAGE_PILOTE + r), depend=dep))
    for h in HY.famille("prix"):
        for r in range(R):
            pl = h.filtre["plan"]
            if pl == "sensibilite":
                cle = f"puissance/pilote/prix/sensibilite/rep={r:03d}"
                if not any(u.cle == cle for u in us):
                    us.append(E.Unite("calibrage", cle, "etape_prix", "unite_sensibilite", dict(rep=DECALAGE_PILOTE + r),
                                      depend=dep))
                continue
            N = int(h.filtre["N"])
            cle = f"puissance/pilote/prix/{pl}/N={N}/rep={r:03d}"
            if any(u.cle == cle for u in us):
                continue
            us.append(E.Unite("calibrage", cle, "etape_prix", "unite_semi" if pl == "semi" else "unite_sous",
                              dict(N=N, rep=DECALAGE_PILOTE + r, etape_reference="calibrage"), depend=dep + ("reference",)))
    V0 = int(PARAM.valeur("vocabulaire")["taille"])
    for h in HY.famille("texte"):
        for r in range(R):
            us.append(E.Unite("calibrage", f"puissance/pilote/texte/N={h.filtre['N']}/rep={r:03d}", "etape_texte",
                              "unite_echantillon", dict(V=V0, N=int(h.filtre["N"]), rep=DECALAGE_PILOTE + r,
                                                        etape_corpus="calibrage"), depend=dep + (f"corpus/V={V0}",)))
    return us


def _marge_puissance(d, h):
    """Écart vrai de l'analyse de puissance : la marge déclarée, sinon 0,5 écart-type des différences pilotes."""
    if h.test == "equivalence" or h.marge:
        return HY.marge(h)
    return float(PARAM.valeur("effet_standardise")) * float(torch.tensor(d, dtype=torch.float64).std()) if len(d) >= 2 else None


def _puissance(d, h, m, alpha, marge, R):
    return S.puissance_simulee(d, R, h.test, marge, alpha / m, n_sim=N_SIM_PUISSANCE, graine=_g("puissance", h.id, R))


def _r_requis(d, h, m, alpha):
    """
    Plus petit R de la grille avec une puissance >= 0,8 au niveau alpha / m (première étape de Holm), par dichotomie.
    Rend (R, puissance, remarque). R = None si les différences pilotes sont toutes identiques (décision D-05, option B) :
    l'hypothèse est alors décidée sans ambiguïté par le TOST (cas se = 0) ou rapportée « sans variance », et ne fixe pas R.
    """
    if len(d) >= 2 and float(torch.tensor(d, dtype=torch.float64).std()) == 0.0:
        return None, float("nan"), "sans variance : exclue du maximum (D-05)"
    marge = _marge_puissance(d, h)
    if marge is None or marge <= 0 or len(d) < 2:
        return GRILLE_R[-1], float("nan"), "pilote insuffisant"
    lo, hi = 0, len(GRILLE_R) - 1
    pw = {}

    def p(i):
        if i not in pw:
            pw[i] = _puissance(d, h, m, alpha, marge, GRILLE_R[i])
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
              "prix": E.lignes("calibrage", rapide, "puissance/pilote/prix/"),
              "texte": E.lignes("calibrage", rapide, "puissance/pilote/texte/")}
    val, det, hyp = {}, [], []
    for fam in ("scenarios", "prix", "texte"):
        hs = HY.famille(fam)
        for h in hs:
            d = HY.diffs(h, lignes[fam])
            R, pw, note = _r_requis(d, h, len(hs), alpha)
            cle = _cle_replication(h)
            val[cle] = max(val.get(cle, GRILLE_R[0]), R if R is not None else GRILLE_R[0])
            hyp.append((h, d, len(hs), cle))
            det.append({"id": h.id, "cle": cle, "n_pilote": len(d), "R_requis": R, "puissance_requise": pw, "remarque": note})
    val.setdefault("prix_sensibilite", val.get("prix_sous", GRILLE_R[-1]))
    durees = {c: [r.get("duree_s") for r in E.resultats("calibrage", rapide, f"puissance/pilote/{p}")]
              for c, p in (("scenarios", "scenarios/"), ("texte", "texte/"), ("prix_sous", "prix/sous/"),
                           ("prix_semi", "prix/semi/"), ("prix_sensibilite", "prix/sensibilite/"))}
    val, budget = _plafond_budget(val, durees)
    for (h, d, m, cle), x in zip(hyp, det):                  # puissance obtenue au R retenu
        x["R_retenu"] = val[cle]
        marge = _marge_puissance(d, h)
        x["puissance_obtenue"] = (_puissance(d, h, m, alpha, marge, val[cle])
                                  if x["R_requis"] is not None and marge and marge > 0 and len(d) >= 2 else float("nan"))
    return _ecrire("puissance", {"replications": val},
                   "par clé, maximum sur les hypothèses de la famille du plus petit R (grille 10 à 200) donnant une puissance "
                   "simulée >= 0,8 au niveau alpha / m (première étape de Holm), hors hypothèses sans variance pilote ; "
                   "puis plafond commun par le budget de temps « budget_replications » (D-05) ; équivalence : différences "
                   "du pilote recentrées à 0 ; différence : recentrées à la marge (ou à 0,5 écart-type)",
                   {"hypotheses": det, "budget": budget})


_UNITES_REPLIQUEES = {"scenarios": ("scenarios", ("",)), "prix_sous": ("etape_prix", ("sous/",)),
                      "prix_semi": ("etape_prix", ("semi/", "couverture/")),
                      "prix_sensibilite": ("etape_prix", ("sensibilite/",)), "texte": ("etape_texte", ("V=",))}


def _unites_par_replication(cle):
    """
    (unités confirmatoires par réplication, unités en nombre fixe) pour une clé de « replications ». Texte (D-14) : seules
    les unités de la taille de vocabulaire principale suivent R ; celles des tailles de sensibilité sont en nombre fixe.
    """
    module, prefixes = _UNITES_REPLIQUEES[cle]
    us = importlib.import_module(module).unites(False)
    if cle == "texte":
        p0 = f"V={int(PARAM.valeur('vocabulaire')['taille'])}/"
        par = sum(1 for u in us if u.cle.endswith("rep=000") and u.cle.startswith(p0))
        fixe = sum(1 for u in us if u.cle.startswith("V=") and not u.cle.startswith(p0))
        return par, fixe
    return sum(1 for u in us if u.cle.endswith("rep=000") and u.cle.startswith(prefixes)), 0


def _plafond_budget(val, durees):
    """
    Décision D-05, option C. Temps estimé d'une réplication d'une clé = unités confirmatoires par réplication x durée
    moyenne des unités pilotes de la clé (durées mesurées par etapes.executer_unite). Si le temps total dépasse
    « budget_replications », toutes les clés sont réduites dans la même proportion (arrondi inférieur à la grille,
    au moins GRILLE_R[0]). Approximation déclarée : les unités sans pilote (S8 à S10, couverture) sont comptées à la
    durée moyenne des unités pilotes de leur clé. Rend (valeurs retenues, détail).
    """
    b = PARAM.valeur("budget_replications")
    budget_s = float(b["heures_instance"]) * 3600 * int(b["travailleurs"])
    cout, fixe = {}, 0.0
    for cle in val:
        d = [x for x in durees.get(cle, []) if x is not None]
        if not d:
            return val, {"budget_s": budget_s, "remarque": f"durées pilotes absentes ({cle}) : aucun plafond appliqué"}
        par, n_fixe = _unites_par_replication(cle)
        cout[cle] = par * sum(d) / len(d)
        fixe += n_fixe * sum(d) / len(d)
    total = fixe + sum(val[c] * cout[c] for c in val)
    det = {"budget_s": budget_s, "cout_par_replication_s": cout, "cout_fixe_s": fixe, "total_requis_s": total,
           "R_requis": dict(val)}
    if total <= budget_s:
        det["facteur"] = 1.0
        return val, det
    f = max(0.0, budget_s - fixe) / (total - fixe)
    det["facteur"] = f
    return {c: max([g for g in GRILLE_R if g <= f * R] or [GRILLE_R[0]]) for c, R in val.items()}, det


# ------------------------------------------------------------------------------ étape
def unites(rapide: bool):
    U = lambda c, f, dep=(), **k: E.Unite("calibrage", c, "calibrage", f, k, depend=tuple(dep))
    J = [n for n, _ in jeux(rapide)]
    us = [U(f"kmeans/{j}", "unite_kmeans", jeu=j) for j in J]
    us += [U("fin/kmeans", "fin_kmeans", dep=[f"kmeans/{j}" for j in J])]
    v1 = ("fin/kmeans",)
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
    v4 = v3 + ("fin/n_init",)
    us += [U(f"priors/{f}", "unite_priors", dep=v4, famille=f) for f in ("synthetique", "prix")]
    us.append(U("fin/priors", "fin_priors", dep=[f"priors/{f}" for f in ("synthetique", "prix")]))
    us += [U("fin/texte", "unite_texte", dep=v4 + (f"corpus/V={V0}",)), U("fin/variantes", "unite_variantes", dep=v4)]
    v5 = v4 + ("fin/priors", "fin/texte", "fin/variantes")
    Jm = [j for j in J if j.startswith(("synthetique/", "prix/"))]          # écart d'ARI (synthétique) et de LL (tous)
    us += [U(f"marges/{j}", "unite_marges", dep=v5, jeu=j) for j in Jm]
    us.append(U("fin/marges", "fin_marges", dep=[f"marges/{j}" for j in Jm]))
    us.append(U("fin/monte_carlo", "unite_monte_carlo", dep=v5 + ("fin/marges",)))
    us.append(U("fin/n_init_texte", "fin_n_init_texte", dep=("n_init/texte",)))         # D-14, avant les pilotes texte
    v6 = v5 + ("fin/marges", "fin/monte_carlo", "fin/n_init_texte")
    pil = unites_pilotes(rapide, v6)
    us += pil
    us.append(U("fin/puissance", "fin_puissance", dep=[u.cle for u in pil]))
    return us


def agreger(rapide: bool):
    E.ecrire_csv("calibrage_registre", PARAM.tableau(), rapide)
    for pre in ("tolerance/", "regularisation/", "n_init/", "marges/"):
        L = E.lignes("calibrage", rapide, pre)
        if L:
            E.ecrire_csv("calibrage_" + pre.strip("/"), L, rapide)
