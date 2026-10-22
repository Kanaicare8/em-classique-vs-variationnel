"""
================================================================================
PROTOCOLE DE COMPARAISON EM / EM VARIATIONNEL
================================================================================

  bras_protocole()          ajuste les bras EM-K, EM-Kmax, EM-BIC, EM-ICL, MAP-EM, MAP-cal, VB-emp,
                            VB-diff, VB-cal avec le même critère d'arrêt et le même nombre de relances
  k_hat()                   règle UNIQUE pour tous les bras : composantes avec N_k / N >= seuil_actif
  choisir_k_critere()       balayage de K (BIC ou ICL), borné par nb_parametres(K) < N
  priors_bras()             jeux de priors : empiriques, diffus (références documentées) et calibrés
  logdens_plugin(), logdens_predictive_vb()   log-densités moyennes hors échantillon
  simuler_depuis_modele()   jeu semi-synthétique tiré d'un mélange gaussien
  blocs_spatiaux(), plis_par_blocs()          validation croisée par blocs spatiaux
  chronometrer()            temps jusqu'au modèle final et coût par itération (médiane)

Chaque ajustement est passé par `memo` (persistance) : une interruption reprend au bras suivant,
et un long ajustement reprend dans sa boucle grâce à l'instantané.
"""

from __future__ import annotations

import time

import torch
from torch import Tensor

import algorithmes as A
import parametres as PARAM


# ------------------------------------------------------------------------------ règles communes
def k_hat(Nk: Tensor, N: int) -> int:
    """Nombre de composantes actives : N_k / N >= seuil_actif (registre), pour TOUS les bras."""
    return int((Nk / N >= float(PARAM.valeur("seuil_actif"))).sum())


def k_admissibles(N: int, D: int, kmax: int, cov_type: str = "full") -> list[int]:
    """K tels que le nombre de paramètres libres reste strictement inférieur au nombre d'observations."""
    return [K for K in range(1, kmax + 1) if A.nb_parametres(K, D, cov_type) < N]


def priors_bras(X: Tensor, kmax: int, famille: str) -> dict:
    """
    Priors des bras bayésiens :
      emp  : valeurs par défaut de BayesianGaussianMixture (alpha0 = 1/Kmax, beta0 = 1, nu0 = D, W0^-1 = cov. empirique) ;
      diff : beta0 = 1e-3, W0 = I, nu0 = D, alpha0 = 1/Kmax ;
      cal  : hyperparamètres de la recherche de calibrage de la famille (registre « priors_vb_calibres ») ;
      map_emp, map_cal : mêmes priors pour le MAP-EM, avec alpha0 = alpha0_map (= 1, registre).
    """
    D = X.shape[1]
    cov = torch.cov(X.T).reshape(D, D)
    c = PARAM.valeur("priors_vb_calibres")[famille]
    a_map = float(PARAM.valeur("alpha0_map"))
    emp = A.priori_empirique(X, 1.0 / kmax)
    cal = A.PrioriNW(float(c["alpha0"]), X.mean(0), float(c["beta0"]), float(c["echelle_w0"]) * cov,
                     float(D) + float(c["nu0_plus"]))
    return {"emp": emp, "diff": A.priori_diffus(X, 1.0 / kmax), "cal": cal,
            "map_emp": A.PrioriNW(a_map, emp.m0, emp.beta0, emp.W0inv, emp.nu0),
            "map_cal": A.PrioriNW(a_map, cal.m0, cal.beta0, cal.W0inv, cal.nu0)}


def _sans_memo(cle, f):
    return f()


def _inst(memo, cle):
    """Instantané de boucle pour un ajustement long, si la mémoire en fournit (etapes.Memo)."""
    f = getattr(memo, "instantane", None)
    return f(cle) if f else None


def choisir_k_critere(X: Tensor, kmax: int, critere: str, n_init: int, graine: int, memo=_sans_memo, prefixe=""):
    """Balaye les K admissibles par EM ; chaque K est mémorisé. Retourne le meilleur ajustement et le temps total."""
    t0 = time.perf_counter()
    N, D = X.shape
    meilleur, vals, echecs = None, {}, 0
    for K in k_admissibles(N, D, kmax):
        try:
            cle = f"{prefixe}EM/K={K}"
            res = memo(cle, lambda K=K, cle=cle: A.em_classique(X, K, n_init=n_init, graine=graine, instantane=_inst(memo, cle)))
        except A.EchecNumerique:
            echecs += 1
            continue
        vals[K] = float(res[critere])
        if meilleur is None or res[critere] < meilleur[critere]:
            meilleur = res
    if meilleur is None:
        raise A.EchecNumerique("tous les ajustements EM du balayage ont échoué")
    meilleur = dict(meilleur)
    meilleur["temps_balayage"] = time.perf_counter() - t0
    meilleur["critere_par_k"] = {str(k): v for k, v in vals.items()}
    meilleur["k_echecs"] = echecs
    return meilleur


BRAS = ("EM-K", "EM-Kmax", "EM-BIC", "EM-ICL", "MAP-EM", "MAP-cal", "VB-emp", "VB-diff", "VB-cal")


def bras_protocole(X: Tensor, k_ref: int, kmax: int, n_init: int, graine: int, famille: str, bras=BRAS, memo=_sans_memo):
    """
    Ajuste les bras demandés avec le même critère d'arrêt, le même nombre de relances et la même graine
    d'ajustement. Chaque résultat porte "k_hat" (règle unique), "k_ajuste" (K du modèle) et "temps_total".
    Un bras qui échoue numériquement est renvoyé sous la forme {"echec": message}.
    Les ajustements EM à K fixé sont partagés entre EM-K, EM-Kmax et les balayages (même clé de mémoire).
    """
    N = X.shape[0]
    pri = priors_bras(X, kmax, famille)
    sortie = {}

    def essayer(nom, ajuster, k_ajuste):
        t0 = time.perf_counter()
        try:
            r = dict(ajuster())
            r.update(k_hat=k_hat(r["Nk"], N), k_ajuste=k_ajuste(r),
                     temps_total=float(r.get("temps_balayage", r.get("temps", time.perf_counter() - t0))))
            sortie[nom] = r
        except A.EchecNumerique as e:
            sortie[nom] = {"echec": str(e)[:120]}

    def fixe(K):
        cle = f"EM/K={K}"
        return memo(cle, lambda: A.em_classique(X, K, n_init=n_init, graine=graine, instantane=_inst(memo, cle)))
    if "EM-K" in bras:
        essayer("EM-K", lambda: fixe(k_ref), lambda r: k_ref)
    if "EM-Kmax" in bras:
        essayer("EM-Kmax", lambda: fixe(kmax), lambda r: kmax)
    for nom, crit in (("EM-BIC", "bic"), ("EM-ICL", "icl")):
        if nom in bras:
            essayer(nom, lambda crit=crit: choisir_k_critere(X, kmax, crit, n_init, graine, memo), lambda r: len(r["pi"]))
    for nom, cle in (("MAP-EM", "map_emp"), ("MAP-cal", "map_cal")):
        if nom in bras:
            essayer(nom, lambda cle=cle, nom=nom: memo(nom, lambda: A.map_em(X, kmax, pri[cle], n_init=n_init, graine=graine,
                                                                            instantane=_inst(memo, nom))),
                    lambda r: kmax)
    for nom, cle in (("VB-emp", "emp"), ("VB-diff", "diff"), ("VB-cal", "cal")):
        if nom in bras:
            essayer(nom, lambda cle=cle, nom=nom: memo(nom, lambda: A.em_variationnel(X, kmax, priori=pri[cle],
                                                                                         n_init=n_init, graine=graine,
                                                                                         instantane=_inst(memo, nom))),
                    lambda r: kmax)
    return sortie


# ------------------------------------------------------------------------------ évaluation
def params_plugin(res: dict) -> dict:
    """Paramètres plug-in : (pi, mu, cov) pour l'EM et le MAP-EM ; (E[pi], m, E[Lambda]^-1) pour le VB."""
    return {"pi": res["pi"], "mu": res["mu"] if "mu" in res else res["m"], "cov": res["cov"]}


def logdens_plugin(res: dict, X: Tensor) -> float:
    """Log-densité moyenne par observation, paramètres plug-in ; NaN si l'évaluation échoue."""
    p = params_plugin(res)
    try:
        _, ln = A._etape_e(X, p["pi"], p["mu"], p["cov"])
        return float(ln.mean())
    except A.EchecNumerique:
        return float("nan")


def logdens_predictive_vb(res: dict, X: Tensor) -> float:
    """Log-densité prédictive moyenne du VB (mélange de Student, Bishop 2006, éq. 10.81)."""
    from risque import log_predictive_variationnel
    try:
        return float(log_predictive_variationnel(X, res["P"]).mean())
    except Exception:
        return float("nan")


def simuler_depuis_modele(modele: dict, n: int, graine: int):
    """Tire n points du mélange gaussien (pi, mu, cov). Retourne (X, z)."""
    g = A.generateur(graine)
    z = torch.multinomial(modele["pi"], n, replacement=True, generator=g)
    L = torch.linalg.cholesky(modele["cov"])
    eps = torch.randn(n, modele["mu"].shape[1], generator=g)
    return modele["mu"][z] + torch.einsum("nde,ne->nd", L[z], eps), z


def em_demarrage_chaud(X: Tensor, depart: dict, cov_type: str = "full") -> dict:
    """
    EM démarré au paramètre `depart` (une seule relance), critère d'arrêt commun. Sert au bootstrap :
    chaque réplicat repart de l'optimum atteint sur l'échantillon d'origine, de sorte que le bootstrap mesure
    la variabilité d'échantillonnage autour de cet optimum et non les sauts entre optima locaux ; le même
    ajustement initial (n_init relances) sert aux deux méthodes comparées.
    """
    tol, n_iter, reg = A._defauts(None, None, None)
    dp = A._Prep(X)
    params = {"pi": depart["pi"][None].clone(), "mu": (depart["mu"] - dp.c)[None].clone(), "cov": depart["cov"][None].clone()}

    def evaluer(sub):
        r, ln, ok = A._etape_e_lot(dp, sub["pi"], sub["mu"], sub["cov"])
        return r, ln.sum(1), ok, None

    def maj(sub, r, aux):
        p, m, cv = A._etape_m_lot(dp, r, cov_type, reg)
        return {"pi": p, "mu": m, "cov": cv}

    etat = A._piloter_lot(params, 1, n_iter, tol, evaluer, maj)
    if bool(etat["echec"][0]):
        raise A.EchecNumerique("bootstrap : covariance non définie positive")
    return {"pi": params["pi"][0], "mu": params["mu"][0] + dp.c, "cov": params["cov"][0],
            "converge": bool(etat["converge"][0]), "n_iter": int(etat["n_m"][0])}


# ------------------------------------------------------------------------------ spatial
def blocs_spatiaux(coords_km: Tensor, taille_bloc: float) -> Tensor:
    """Identifiant de bloc carré (côté taille_bloc, en km) de chaque point."""
    ij = torch.floor((coords_km - coords_km.min(0).values) / taille_bloc).to(torch.int64)
    _, inv = torch.unique(ij, dim=0, return_inverse=True)
    return inv


def plis_par_blocs(blocs: Tensor, n_plis: int, graine: int) -> Tensor:
    """Pli de chaque point : les BLOCS sont répartis au hasard entre les plis (validation croisée par blocs)."""
    ub = torch.unique(blocs)
    perm = torch.randperm(len(ub), generator=A.generateur(graine))
    pli_bloc = torch.empty(int(ub.max()) + 1, dtype=torch.long)
    pli_bloc[ub[perm]] = torch.arange(len(ub)) % n_plis
    return pli_bloc[blocs]


def variogramme(X: Tensor, coords_km: Tensor, pas_km: float, n_paires: int, graine: int):
    """
    Variogramme empirique moyen des variables standardisées : gamma(h) = moyenne de ||x_i - x_j||² / (2 D)
    sur des paires tirées au hasard, par classe de distance de largeur pas_km. Retourne (h, gamma, effectifs).
    """
    g = A.generateur(graine)
    N, D = X.shape
    i = torch.randint(N, (n_paires,), generator=g)
    j = torch.randint(N, (n_paires,), generator=g)
    h = (coords_km[i] - coords_km[j]).norm(dim=1)
    sq = ((X[i] - X[j]) ** 2).sum(1) / (2 * D)
    classe = (h / pas_km).floor().long()
    nb = int(classe.max()) + 1
    eff = torch.bincount(classe, minlength=nb).double()
    gam = torch.bincount(classe, weights=sq, minlength=nb) / eff.clamp(min=1)
    return (torch.arange(nb) + 0.5) * pas_km, gam, eff


# ------------------------------------------------------------------------------ temps
def chronometrer(f, n_rep: int):
    """Exécute f() n_rep fois ; médianes du temps jusqu'au modèle final, des itérations et du coût par itération."""
    temps, iters = [], []
    for _ in range(n_rep):
        t0 = time.perf_counter()
        res = f()
        temps.append(time.perf_counter() - t0)
        iters.append(res["n_iter"])
    t = torch.tensor(temps)
    it = torch.tensor(iters, dtype=torch.float64)
    return {"temps_median": float(t.median()), "temps_min": float(t.min()), "temps_max": float(t.max()),
            "iterations_mediane": float(it.median()),
            "cout_par_iteration": float((t / it.clamp(min=1)).median()), "n_rep": n_rep}
