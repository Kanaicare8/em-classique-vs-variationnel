# COPIE FIGÉE de l.implémentation séquentielle (référence des tests d.équivalence). Ne pas modifier.
"""
================================================================================
EM CLASSIQUE ET EM VARIATIONNEL POUR LES MODÈLES DE MÉLANGE (PyTorch pur)
Kana Tiodong Icare Brichel, Master 2 SDIA, ENSPD, Université de Douala
================================================================================

Implémentation sans scikit-learn, sans SciPy et sans NumPy. Seules les opérations
élémentaires de PyTorch sont utilisées (algèbre linéaire, digamma, lgamma) ; les
modèles, les critères et les métriques sont écrits à la main.

Correspondance entre fonctions, sections et équations du texte :

    Section 1.6   EM classique pour le GMM        em_classique()        (1.15) (1.16) (1.18)
    Section 1.6.5 EM stochastique (SEM)           em_stochastique()
    Section 1.6.5 EM online                       em_online()
    Section 1.6.6 Baum-Welch (HMM)                forward_backward(), baum_welch()
    Section 1.7   EM variationnel pour le GMM     em_variationnel()     (1.26) (1.27) (1.28) (1.29) (1.30)
    Section 1.7.6 ELBO                            elbo_gmm_bayesien()   (1.31)
    Section 1.7.7 Inférence variationnelle stoch. svi_gmm()
    Section 2.2.3 BIC / AIC                       bic(), aic()          (2.4) (2.5)
    Section 3.1.1 LDA variationnel                lda_variationnel()    (3.2)
    Section 2.3.4 ARI, silhouette                 indice_rand_ajuste(), silhouette()

Critère d'arrêt COMMUN (tâche T1.1), appliqué à l'EM classique, au MAP-EM, à l'EM
variationnel et au pLSA, sans exception :

  * grandeur : le critère TOTAL (log-vraisemblance pour l'EM, ELBO total pour l'EM
    variationnel en covariance pleine), jamais divisé par N ;
  * test : |c_t - c_(t-1)| <= TOL_REL * max(|c_(t-1)|, 1)  (tolérance relative) ;
  * plafond : N_ITER_MAX étapes M ;
  * décompte : une itération = une étape E suivie d'une étape M. Le critère est évalué
    après chaque étape E, avant l'étape M ; n_iter est le nombre d'étapes M effectuées
    (hist contient donc n_iter + 1 valeurs). Si le plafond est atteint sans que le test
    soit satisfait, converge vaut False (cas « non convergé »).

Pour les variantes tied/diag/spherique du VB, l'ELBO n'est pas dérivé : le critère est
la somme des log-normalisations de l'étape E, c'est-à-dire l'ELBO privé du terme
KL(q(theta) || p(theta)). Il est étiqueté « approximation » (clé critere_nom).
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

import torch
from torch import Tensor

torch.set_default_dtype(torch.float64)

LOG2PI = math.log(2.0 * math.pi)
LN2 = math.log(2.0)
LNPI = math.log(math.pi)
TYPES_COVARIANCE = ("full", "tied", "diag", "spherical")

# Paramètres d'arrêt et de régularisation communs à tous les algorithmes (T1.1, T1.7).
TOL_REL = 1e-6          # tolérance relative sur le critère total
N_ITER_MAX = 500        # plafond d'étapes M
REG_EM = 1e-6           # régularisation ajoutée à la diagonale des covariances (EM et MAP-EM)
SEUIL_VP_DEGENERE = 1e-6


def a_converge(c_prec: float, c: float, tol: float = TOL_REL) -> bool:
    """Test d'arrêt commun : variation relative du critère total."""
    return abs(c - c_prec) <= tol * max(abs(c_prec), 1.0)


def indicateur_degenerescence(cov: Tensor, Nk: Tensor, D: int,
                              seuil_vp: float = SEUIL_VP_DEGENERE) -> Tensor:
    """
    Masque (K,) des composantes dégénérées (T1.4) : valeur propre minimale de Sigma_k
    inférieure à seuil_vp x trace(Sigma_k), ou N_k < D + 1. Seules les composantes non
    éteintes (N_k >= 1) sont examinées, pour la même règle en EM et en VB : une composante
    élaguée par le VB (ou à effectif négligeable en EM) n'est pas comptée comme dégénérée.
    """
    vp_min = torch.linalg.eigvalsh(cov).min(dim=-1).values
    trace = torch.diagonal(cov, dim1=-2, dim2=-1).sum(-1)
    non_eteinte = Nk >= 1.0           # une composante élaguée (N_k < 1) n'est pas un ajustement dégénéré
    return non_eteinte & ((vp_min < seuil_vp * trace) | (Nk < D + 1))


def entropie_affectation(r: Tensor) -> float:
    """EN(r) = - somme_i somme_k r_ik ln r_ik (entropie totale des affectations)."""
    return float(-torch.xlogy(r, r).sum())


def icl(loglik: float, p: int, N: int, r: Tensor) -> float:
    """
    ICL de Biernacki, Celeux et Govaert (2000), à minimiser : ICL = BIC + 2 EN(r),
    soit -2 ln p(x, z_hat | theta_hat) + p ln N à l'approximation près. Pénalise les
    composantes qui se chevauchent, donc les mélanges dont les affectations sont floues.
    """
    return bic(loglik, p, N) + 2.0 * entropie_affectation(r)


def hongrois(cout: Tensor) -> Tensor:
    """
    Algorithme hongrois (Kuhn-Munkres, version en O(n^3)) pour une matrice carrée.
    Retourne un tenseur `col` tel que la ligne i est affectée à la colonne col[i]
    et que somme_i cout[i, col[i]] soit minimale.
    """
    n = cout.shape[0]
    inf = float("inf")
    c = cout.tolist()
    u, v = [0.0] * (n + 1), [0.0] * (n + 1)
    p, way = [0] * (n + 1), [0] * (n + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [inf] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], inf, 0
            for j in range(1, n + 1):
                if not used[j]:
                    cur = c[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    col = [0] * n
    for j in range(1, n + 1):
        col[p[j] - 1] = j - 1
    return torch.tensor(col)


# ==============================================================================
# OUTILS GÉNÉRAUX
# ==============================================================================

def generateur(graine: int) -> torch.Generator:
    g = torch.Generator()
    g.manual_seed(int(graine))
    return g


def logsumexp_stable(a: Tensor, dim: int = 1, keepdim: bool = True) -> Tensor:
    """Équation (1.18) : log sum exp(a_k) = a_max + log sum exp(a_k - a_max)."""
    a_max = a.max(dim=dim, keepdim=True).values
    out = a_max + torch.log(torch.exp(a - a_max).sum(dim=dim, keepdim=True))
    return out if keepdim else out.squeeze(dim)


def generer_blobs(n_par_groupe, centres, ecart_type, graine=42):
    """Mélange de gaussiennes isotropes (écart-type `ecart_type`), groupes de taille égale."""
    g = generateur(graine)
    centres = torch.as_tensor(centres, dtype=torch.float64)
    C, D = centres.shape
    y = torch.arange(C).repeat_interleave(n_par_groupe)
    X = centres[y] + ecart_type * torch.randn(len(y), D, generator=g)
    perm = torch.randperm(len(y), generator=g)
    return X[perm], y[perm]


def jeu_reference(graine=42):
    """Jeu de données du chapitre 2 : N = 300, centres (0,0), (5,5), (0,5), écart-type 0,7."""
    return generer_blobs(100, [[0.0, 0.0], [5.0, 5.0], [0.0, 5.0]], 0.7, graine)


def kmeans(X: Tensor, K: int, graine: int = 0, n_iter: int = 100):
    """K-means (Lloyd) avec initialisation k-means++. Retourne (étiquettes, centres)."""
    g = generateur(graine)
    N, D = X.shape
    centres = X[torch.randint(N, (1,), generator=g)].clone()
    for _ in range(1, K):
        d2 = torch.cdist(X, centres).pow(2).min(dim=1).values
        p = d2 / d2.sum() if d2.sum() > 0 else torch.full((N,), 1.0 / N)
        centres = torch.cat([centres, X[torch.multinomial(p, 1, generator=g)]], dim=0)
    for _ in range(n_iter):
        etiq = torch.cdist(X, centres).argmin(dim=1)
        nouveaux = centres.clone()
        for k in range(K):
            masque = etiq == k
            if masque.any():
                nouveaux[k] = X[masque].mean(dim=0)
        if torch.allclose(nouveaux, centres):
            break
        centres = nouveaux
    return torch.cdist(X, centres).argmin(dim=1), centres


def nb_parametres(K: int, D: int, cov_type: str) -> int:
    """Nombre de paramètres libres p(K) intervenant dans le BIC et l'AIC."""
    cov = {"full": K * D * (D + 1) // 2, "tied": D * (D + 1) // 2,
           "diag": K * D, "spherical": K}[cov_type]
    return cov + K * D + (K - 1)


def bic(loglik: float, p: int, N: int) -> float:
    """Équation (2.4)."""
    return -2.0 * loglik + p * math.log(N)


def aic(loglik: float, p: int) -> float:
    """Équation (2.5)."""
    return -2.0 * loglik + 2.0 * p


def log_gauss(X: Tensor, mu: Tensor, cov: Tensor) -> Tensor:
    """log N(x | mu, cov) pour toutes les lignes de X, via Cholesky (section 2.2.2)."""
    D = X.shape[1]
    L = torch.linalg.cholesky(cov)
    z = torch.linalg.solve_triangular(L, (X - mu).T, upper=False)
    logdet = 2.0 * torch.log(torch.diagonal(L)).sum()
    return -0.5 * (D * LOG2PI + logdet + (z ** 2).sum(dim=0))


# ==============================================================================
# MÉTRIQUES DE PARTITION (écrites à la main)
# ==============================================================================

def indice_rand_ajuste(y_vrai: Tensor, y_pred: Tensor) -> float:
    """ARI de Hubert et Arabie, à partir de la table de contingence."""
    _, a = torch.unique(y_vrai, return_inverse=True)
    _, b = torch.unique(y_pred, return_inverse=True)
    n = len(a)
    cont = torch.zeros(int(a.max()) + 1, int(b.max()) + 1)
    cont.index_put_((a, b), torch.ones(n), accumulate=True)

    def comb2(x):
        return x * (x - 1) / 2.0

    somme_ij = comb2(cont).sum()
    somme_a = comb2(cont.sum(1)).sum()
    somme_b = comb2(cont.sum(0)).sum()
    attendu = somme_a * somme_b / comb2(torch.tensor(float(n)))
    maxi = 0.5 * (somme_a + somme_b)
    if maxi == attendu:
        return 1.0
    return float((somme_ij - attendu) / (maxi - attendu))


def silhouette(X: Tensor, etiq: Tensor) -> float:
    """Score de silhouette moyen (distance euclidienne)."""
    _, e = torch.unique(etiq, return_inverse=True)
    C = int(e.max()) + 1
    if C < 2:
        return 0.0
    dist = torch.cdist(X, X)
    onehot = torch.nn.functional.one_hot(e, C).to(X.dtype)
    tailles = onehot.sum(0)
    somme = dist @ onehot                       # (N, C) : somme des distances à chaque groupe
    N = len(e)
    idx = torch.arange(N)
    taille_propre = tailles[e]
    a = somme[idx, e] / (taille_propre - 1).clamp(min=1)
    moy = somme / tailles.clamp(min=1)
    moy[idx, e] = float("inf")
    b = moy.min(dim=1).values
    s = (b - a) / torch.maximum(a, b)
    s = torch.where(taille_propre > 1, s, torch.zeros_like(s))
    return float(s.mean())


# ==============================================================================
# EM CLASSIQUE POUR LE GMM (sections 1.6.2 et 1.6.3)
# ==============================================================================

def _covariances_em(X, r, mu, Nk, cov_type, reg):
    """Mise à jour des covariances (1.16) selon la contrainte de forme choisie."""
    K, D = mu.shape
    diff = X[None, :, :] - mu[:, None, :]
    S = torch.einsum("nk,knd,kne->kde", r, diff, diff)
    I = torch.eye(D)
    if cov_type == "full":
        cov = S / Nk[:, None, None]
    elif cov_type == "tied":
        cov = (S.sum(0) / Nk.sum()).expand(K, D, D).clone()
    elif cov_type == "diag":
        cov = torch.diag_embed(torch.diagonal(S, dim1=1, dim2=2) / Nk[:, None])
    elif cov_type == "spherical":
        v = torch.diagonal(S, dim1=1, dim2=2).sum(-1) / (D * Nk)
        cov = v[:, None, None] * I
    else:
        raise ValueError(cov_type)
    return cov + reg * I


def _etape_m(X, r, cov_type, reg):
    """Étape M (1.16) : pi_k = N_k/N, mu_k = moyenne pondérée, Sigma_k = covariance pondérée."""
    N = X.shape[0]
    Nk = r.sum(0) + 1e-10
    pi = Nk / N
    mu = (r.T @ X) / Nk[:, None]
    cov = _covariances_em(X, r, mu, Nk, cov_type, reg)
    return pi, mu, cov


def _etape_e(X, pi, mu, cov):
    """Étape E (1.15) en log-espace : retourne (r, log p(x_i | theta))."""
    K = len(pi)
    log_r = torch.stack([torch.log(pi[k] + 1e-300) + log_gauss(X, mu[k], cov[k])
                         for k in range(K)], dim=1)
    log_norm = logsumexp_stable(log_r, dim=1)
    return torch.exp(log_r - log_norm), log_norm.squeeze(1)


def _init_em(X, K, cov_type, init, graine, reg):
    N, D = X.shape
    if init == "kmeans":
        etiq, _ = kmeans(X, K, graine)
        r0 = torch.nn.functional.one_hot(etiq, K).to(X.dtype)
        return _etape_m(X, r0, cov_type, reg)
    g = generateur(graine)                                   # initialisation aléatoire (1.6.2.a)
    idx = torch.randperm(N, generator=g)[:K]
    mu = X[idx].clone()
    cov0 = torch.cov(X.T).reshape(D, D) + reg * torch.eye(D)
    return torch.full((K,), 1.0 / K), mu, cov0.expand(K, D, D).clone()


def _lgamma_multi(a: float, D: int) -> float:
    """ln Gamma_D(a), fonction gamma multivariée."""
    return D * (D - 1) / 4.0 * LNPI + sum(math.lgamma(a + (1 - i) / 2.0) for i in range(1, D + 1))


def priori_plat(D: int) -> PrioriNW:
    """
    Prior impropre « plat » : Dirichlet(1), beta0 = 0, W0^-1 = 0, nu0 = -D - 2. Le MAP-EM
    avec ce prior redonne exactement l'EM (densité a priori constante en (pi, mu, Sigma)).
    """
    return PrioriNW(1.0, torch.zeros(D), 0.0, torch.zeros(D, D), -float(D) - 2.0)


def log_priori_nw(pi: Tensor, mu: Tensor, cov: Tensor, pr: "PrioriNW") -> float:
    """
    Log-densité a priori en (pi, mu_k, Sigma_k) : Dirichlet(alpha0) sur pi et, pour chaque
    k, Normale(m0, Sigma_k / beta0) x Inverse-Wishart(W0^-1, nu0) (densité en Sigma, pas en
    Lambda). Définie pour un prior propre (beta0 > 0, nu0 > D - 1).
    """
    K, D = mu.shape
    out = math.lgamma(K * pr.alpha0) - K * math.lgamma(pr.alpha0) + (pr.alpha0 - 1.0) * torch.log(pi).sum()
    psi = pr.W0inv
    logdet_psi = torch.logdet(psi)
    for k in range(K):
        S = cov[k]
        logdet_S = torch.logdet(S)
        d = mu[k] - pr.m0
        out = out + (-0.5 * D * LOG2PI + 0.5 * D * math.log(pr.beta0) - 0.5 * logdet_S
                     - 0.5 * pr.beta0 * d @ torch.linalg.solve(S, d))
        out = out + (0.5 * pr.nu0 * logdet_psi - 0.5 * pr.nu0 * D * LN2 - _lgamma_multi(pr.nu0 / 2.0, D)
                     - 0.5 * (pr.nu0 + D + 1) * logdet_S
                     - 0.5 * torch.trace(psi @ torch.linalg.inv(S)))
    return float(out)


def _etape_m_map(X, r, pr: "PrioriNW", reg):
    """
    Étape M du MAP-EM (covariance pleine) : mode conjoint de (pi, mu, Sigma) sous le prior
    Dirichlet x Normale-Inverse-Wishart.
      pi_k    proportionnel à N_k + alpha0 - 1
      mu_k  = (beta0 m0 + N_k xbar_k) / (beta0 + N_k)
      Sigma_k = (W0^-1 + S_k + beta0 N_k/(beta0+N_k) (xbar_k-m0)(xbar_k-m0)^T) / (nu0 + N_k + D + 2)
    Exige alpha0 >= 1 (sinon le mode est au bord du simplexe).
    """
    N, D = X.shape
    Nk = r.sum(0) + 1e-10
    pi = (Nk + pr.alpha0 - 1.0).clamp(min=1e-10)
    pi = pi / pi.sum()
    xbar = (r.T @ X) / Nk[:, None]
    mu = (pr.beta0 * pr.m0 + Nk[:, None] * xbar) / (pr.beta0 + Nk)[:, None]
    diff = X[None, :, :] - xbar[:, None, :]
    S = torch.einsum("nk,knd,kne->kde", r, diff, diff)
    d0 = xbar - pr.m0
    couplage = (pr.beta0 * Nk / (pr.beta0 + Nk))[:, None, None] * d0[:, :, None] * d0[:, None, :]
    cov = (pr.W0inv[None] + S + couplage) / (pr.nu0 + Nk + D + 2.0)[:, None, None]
    return pi, mu, cov + reg * torch.eye(D)


def _em_une_fois(X, K, cov_type, n_iter, tol, reg, init, graine, prior=None):
    """Boucle EM / MAP-EM avec le critère d'arrêt commun (voir l'en-tête du module)."""
    N, D = X.shape
    pi, mu, cov = _init_em(X, K, cov_type, init, graine, reg)
    hist, converge, n_m = [], False, 0
    while True:
        r, log_norm = _etape_e(X, pi, mu, cov)
        hist.append(float(log_norm.sum()))
        if len(hist) > 1 and a_converge(hist[-2], hist[-1], tol):
            converge = True
            break
        if n_m >= n_iter:
            break
        pi, mu, cov = _etape_m(X, r, cov_type, reg) if prior is None else _etape_m_map(X, r, prior, reg)
        n_m += 1
    return {"pi": pi, "mu": mu, "cov": cov, "r": r, "loglik": hist[-1],
            "ll_hist": hist, "n_iter": n_m, "converge": converge}


def _finaliser_em(res, X, K, cov_type, t0, prior=None):
    N, D = X.shape
    p = nb_parametres(K, D, cov_type)
    Nk = res["r"].sum(0)
    masque = indicateur_degenerescence(res["cov"], Nk, D)
    res.update({
        "Nk": Nk, "labels": res["r"].argmax(1), "n_params": p,
        "bic": bic(res["loglik"], p, N), "aic": aic(res["loglik"], p),
        "icl": icl(res["loglik"], p, N, res["r"]), "entropie": entropie_affectation(res["r"]),
        "degenere": bool(masque.any()), "degenere_composantes": masque,
        "temps": time.perf_counter() - t0, "cov_type": cov_type})
    res["temps_par_iter"] = res["temps"] / max(res["n_iter"], 1)
    if prior is not None:
        res["log_posteriori"] = res["loglik"] + log_priori_nw(res["pi"], res["mu"], res["cov"], prior)
    return res


def em_classique(X, K, cov_type="full", n_iter=N_ITER_MAX, tol=TOL_REL, reg=REG_EM,
                 init="kmeans", graine=0, n_init=1):
    """
    EM classique pour un mélange de K gaussiennes.

    init : "kmeans" (par défaut, comme la pratique courante) ou "aleatoire"
           (K points tirés au hasard, covariance globale, section 1.6.2.a).
    n_init : nombre de relances, on garde la plus grande log-vraisemblance.
    tol, n_iter : critère d'arrêt commun (relatif, sur la log-vraisemblance totale).
    reg : régularisation Sigma_k + reg I (T1.7). C'est un garde-fou contre les singularités
          de la vraisemblance non bornée ; elle fait de l'EM un maximum « restreint ».
    Retourne aussi bic, aic, icl, degenere et temps_par_iter.
    """
    t0 = time.perf_counter()
    meilleur = None
    for s in range(n_init):
        res = _em_une_fois(X, K, cov_type, n_iter, tol, reg, init, graine + s)
        if meilleur is None or res["loglik"] > meilleur["loglik"]:
            meilleur = res
    return _finaliser_em(meilleur, X, K, cov_type, t0)


def map_em(X, K, priori: "PrioriNW", n_iter=N_ITER_MAX, tol=TOL_REL, reg=REG_EM,
           init="kmeans", graine=0, n_init=1):
    """
    MAP-EM (covariance pleine) : EM dont l'étape M maximise Q + log p(theta) avec les priors
    conjugués du VB. Isole l'effet du prior de celui de l'inférence bayésienne complète.
    Le critère d'arrêt est le même que pour l'EM (log-vraisemblance totale). On garde la
    relance de plus grand log-posteriori. Exige priori.alpha0 >= 1.
    """
    if priori.alpha0 < 1.0:
        raise ValueError("MAP-EM : alpha0 >= 1 requis (mode du Dirichlet)")
    t0 = time.perf_counter()
    meilleur, meilleur_lp = None, -float("inf")
    for s in range(n_init):
        res = _em_une_fois(X, K, "full", n_iter, tol, reg, init, graine + s, prior=priori)
        lp = res["loglik"] + log_priori_nw(res["pi"], res["mu"], res["cov"], priori) if priori.beta0 > 0 else res["loglik"]
        if meilleur is None or lp > meilleur_lp:
            meilleur, meilleur_lp = res, lp
    return _finaliser_em(meilleur, X, K, "full", t0, prior=priori if priori.beta0 > 0 else None)


def energie_libre_em(X, r, pi, mu, cov):
    """
    F(q, theta) = E_q[log p(X,Z|theta)] - E_q[log q(Z)] (section 1.2.2).
    Après une étape E, q(Z) = p(Z|X,theta) et F = log-vraisemblance (égalité de Jensen).
    """
    K = len(pi)
    log_joint = torch.stack([torch.log(pi[k]) + log_gauss(X, mu[k], cov[k]) for k in range(K)], 1)
    return float((r * log_joint).sum() - torch.xlogy(r, r).sum())


# ==============================================================================
# VARIANTES DE L'EM CLASSIQUE (section 1.6.5)
# ==============================================================================

def moyenne_alignee(echantillons):
    """
    Moyenne de paramètres (pi, mu, cov) de mélange après alignement des composantes sur le
    premier échantillon par l'algorithme hongrois (coût = distance au carre entre centres). Sans cet
    alignement, le label switching (K! permutations équivalentes) fausse la moyenne (T1.6).
    """
    pi_r, mu_r, cov_r = echantillons[0]
    pis, mus, covs = [pi_r], [mu_r], [cov_r]
    for pi, mu, cov in echantillons[1:]:
        cout = torch.cdist(mu_r, mu).pow(2)
        col = hongrois(cout)
        pis.append(pi[col]); mus.append(mu[col]); covs.append(cov[col])
    return torch.stack(pis).mean(0), torch.stack(mus).mean(0), torch.stack(covs).mean(0)


def em_stochastique(X, K, n_iter=200, reg=1e-6, graine=0, burn=50):
    """
    EM stochastique (Celeux et Diebolt, 1985) : l'étape E devient un tirage
    z_i ~ Categorielle(r_i), l'étape M est faite sur ces affectations dures.
    La log-vraisemblance n'est plus monotone. On renvoie la moyenne des
    paramètres après `burn` itérations, alignés par l'algorithme hongrois (moyenne_alignee) (les composantes vides sont réinitialisées).
    """
    g = generateur(graine)
    N, D = X.shape
    pi, mu, cov = _init_em(X, K, "full", "kmeans", graine, reg)
    hist, accum = [], []
    for it in range(n_iter):
        r, log_norm = _etape_e(X, pi, mu, cov)
        hist.append(float(log_norm.sum()))
        z = torch.multinomial(r, 1, generator=g).squeeze(1)
        dur = torch.nn.functional.one_hot(z, K).to(X.dtype)
        if (dur.sum(0) < D + 1).any():                          # composante quasi vide : on la ré-ancre
            vides = (dur.sum(0) < D + 1).nonzero().flatten()
            for k in vides:
                mu[k] = X[torch.randint(N, (1,), generator=g)].squeeze(0)
                cov[k] = torch.cov(X.T).reshape(D, D) + reg * torch.eye(D)
            continue
        pi, mu, cov = _etape_m(X, dur, "full", reg)
        if it >= burn:
            accum.append((pi.clone(), mu.clone(), cov.clone()))
    if accum:
        pi, mu, cov = moyenne_alignee(accum)
    r, log_norm = _etape_e(X, pi, mu, cov)
    return {"pi": pi, "mu": mu, "cov": cov, "r": r, "loglik": float(log_norm.sum()),
            "ll_hist": hist, "labels": r.argmax(1)}


def em_online(X, K, taille_lot=50, n_epoques=5, kappa=0.6, t0=10.0, reg=1e-6, graine=0):
    """
    EM online par statistiques suffisantes (Sato et Ishii 2000, Cappé et Moulines 2009).
    s <- (1 - eta_t) s + eta_t * s_lot avec eta_t = (t + t0)^(-kappa), kappa dans (0.5, 1]
    (conditions de type Robbins-Monro de la section 1.6.5).
    """
    g = generateur(graine)
    N, D = X.shape
    sous = X[torch.randperm(N, generator=g)[:min(N, 500)]]
    pi, mu, cov = _init_em(sous, K, "full", "kmeans", graine, reg)
    s0 = pi.clone()
    s1 = pi[:, None] * mu
    s2 = pi[:, None, None] * (cov + mu[:, :, None] * mu[:, None, :])
    hist, t = [], 0
    for _ in range(n_epoques):
        perm = torch.randperm(N, generator=g)
        for debut in range(0, N, taille_lot):
            lot = X[perm[debut:debut + taille_lot]]
            r, _ = _etape_e(lot, pi, mu, cov)
            eta = (t + t0) ** (-kappa)
            s0 = (1 - eta) * s0 + eta * r.mean(0)
            s1 = (1 - eta) * s1 + eta * (r.T @ lot) / len(lot)
            s2 = (1 - eta) * s2 + eta * torch.einsum("nk,nd,ne->kde", r, lot, lot) / len(lot)
            pi = s0 / s0.sum()
            mu = s1 / s0[:, None]
            cov = s2 / s0[:, None, None] - mu[:, :, None] * mu[:, None, :] + reg * torch.eye(D)
            t += 1
        _, ln = _etape_e(X, pi, mu, cov)
        hist.append(float(ln.sum()))
    r, ln = _etape_e(X, pi, mu, cov)
    return {"pi": pi, "mu": mu, "cov": cov, "r": r, "loglik": float(ln.sum()),
            "ll_hist": hist, "labels": r.argmax(1)}


# ==============================================================================
# EM VARIATIONNEL POUR LE GMM BAYÉSIEN (section 1.7)
# ==============================================================================

@dataclass
class PrioriNW:
    """Hyperparamètres : Dirichlet(alpha0) sur pi, Normal-Wishart(m0, beta0, W0, nu0) sur (mu, Lambda)."""
    alpha0: float
    m0: Tensor
    beta0: float
    W0inv: Tensor
    nu0: float


def priori_diffus(X, alpha0=None, K=None, beta0=1e-3):
    """Priors diffus : m0 = moyenne, beta0 = 1e-3, W0 = I, nu0 = D."""
    D = X.shape[1]
    if alpha0 is None:
        alpha0 = 1.0 / K
    return PrioriNW(alpha0, X.mean(0), beta0, torch.eye(D), float(D))


def priori_empirique(X, alpha0=None, K=None):
    """Priors empiriques : beta0 = 1, nu0 = D, W0^-1 = covariance empirique, m0 = moyenne."""
    D = X.shape[1]
    if alpha0 is None:
        alpha0 = 1.0 / K
    return PrioriNW(alpha0, X.mean(0), 1.0, torch.cov(X.T).reshape(D, D), float(D))


def _ln_B(W, nu, D):
    """log de la constante de normalisation de la Wishart, ln B(W, nu)."""
    i = torch.arange(1, D + 1, dtype=torch.float64)
    lg = torch.lgamma((nu[..., None] + 1 - i) / 2).sum(-1)
    return -0.5 * nu * torch.logdet(W) - (0.5 * nu * D * LN2 + D * (D - 1) / 4 * LNPI + lg)


def _stats(X, r):
    Nk = r.sum(0) + 1e-10
    xbar = (r.T @ X) / Nk[:, None]
    diff = X[None, :, :] - xbar[:, None, :]
    Sk = torch.einsum("nk,knd,kne->kde", r, diff, diff) / Nk[:, None, None]
    return Nk, xbar, Sk


def _etape_m_var(Nk, xbar, Sk, pr: PrioriNW, cov_type):
    """Étape M variationnelle, équations (1.26) et (1.28), plus les variantes de covariance."""
    K, D = xbar.shape
    beta = pr.beta0 + Nk
    m = (pr.beta0 * pr.m0 + Nk[:, None] * xbar) / beta[:, None]
    d0 = xbar - pr.m0
    terme_prior = (pr.beta0 * Nk / (pr.beta0 + Nk))
    sc = Nk[:, None, None] * Sk + terme_prior[:, None, None] * d0[:, :, None] * d0[:, None, :]
    P = {"alpha": pr.alpha0 + Nk, "beta": beta, "m": m, "cov_type": cov_type}
    if cov_type == "full":
        P["nu"] = pr.nu0 + Nk
        P["Winv"] = pr.W0inv[None] + sc
        P["W"] = torch.linalg.inv(P["Winv"])
    elif cov_type == "tied":
        P["nu"] = torch.full((K,), pr.nu0 + float(Nk.sum()))
        Winv = pr.W0inv + sc.sum(0)
        P["Winv"] = Winv.expand(K, D, D).clone()
        P["W"] = torch.linalg.inv(Winv).expand(K, D, D).clone()
    else:                                       # diag, spherical : priors Gamma sur les précisions
        a0 = pr.nu0 / 2.0
        b0 = 0.5 * torch.diagonal(pr.W0inv)
        sd = torch.diagonal(sc, dim1=1, dim2=2)
        if cov_type == "diag":
            P["a"] = (a0 + Nk / 2.0)[:, None].expand(K, D).clone()
            P["b"] = b0[None] + 0.5 * sd
        else:
            P["a"] = (a0 + D * Nk / 2.0)[:, None].expand(K, D).clone()
            P["b"] = (b0.mean() + 0.5 * sd.sum(1))[:, None].expand(K, D).clone()
    return P


def _attendus(P, D):
    """E[ln|Lambda_k|] (1.29) et E[Lambda_k] pour chaque composante."""
    if P["cov_type"] in ("full", "tied"):
        i = torch.arange(1, D + 1, dtype=torch.float64)
        Elogdet = (torch.special.digamma((P["nu"][:, None] + 1 - i) / 2).sum(-1)
                   + D * LN2 + torch.logdet(P["W"]))
        Elam = P["nu"][:, None, None] * P["W"]
    else:
        psi = torch.special.digamma(P["a"]) - torch.log(P["b"])
        Elogdet = psi.sum(-1)
        Elam = torch.diag_embed(P["a"] / P["b"])
    return Elogdet, Elam


def _etape_e_var(X, P):
    """Étape E variationnelle, équation (1.27), avec la forme quadratique (1.30)."""
    N, D = X.shape
    Elogpi = torch.special.digamma(P["alpha"]) - torch.special.digamma(P["alpha"].sum())
    Elogdet, Elam = _attendus(P, D)
    diff = X[None, :, :] - P["m"][:, None, :]
    quad = D / P["beta"][None, :] + torch.einsum("knd,kde,kne->nk", diff, Elam, diff)
    log_rho = Elogpi[None] + 0.5 * Elogdet[None] - 0.5 * D * LOG2PI - 0.5 * quad
    log_norm = logsumexp_stable(log_rho, dim=1)
    return torch.exp(log_rho - log_norm), log_norm.squeeze(1)


def elbo_gmm_bayesien(r, Nk, xbar, Sk, P, pr: PrioriNW):
    """
    ELBO du GMM bayésien (équation 1.31, détail dans Bishop 2006, éq. 10.70 à 10.77).
    Disponible pour la covariance pleine.
    """
    K, D = xbar.shape
    alpha, beta, m, nu, W = P["alpha"], P["beta"], P["m"], P["nu"], P["W"]
    Elogpi = torch.special.digamma(alpha) - torch.special.digamma(alpha.sum())
    Elogdet, _ = _attendus(P, D)
    dm = xbar - m
    t_trace = torch.einsum("kde,ked->k", Sk, W)
    t_quad = torch.einsum("kd,kde,ke->k", dm, W, dm)
    e_x = 0.5 * (Nk * (Elogdet - D / beta - nu * t_trace - nu * t_quad - D * LOG2PI)).sum()
    e_z = (Nk * Elogpi).sum()
    a0 = pr.alpha0
    ln_c0 = math.lgamma(K * a0) - K * math.lgamma(a0)
    e_pi = ln_c0 + (a0 - 1.0) * Elogpi.sum()
    W0 = torch.linalg.inv(pr.W0inv)
    d0 = m - pr.m0
    quad_m = torch.einsum("kd,kde,ke->k", d0, W, d0)
    nu0_t = torch.tensor(pr.nu0)
    lnB0 = _ln_B(W0, nu0_t, D)
    e_muLam = (0.5 * (D * math.log(pr.beta0 / (2 * math.pi)) + Elogdet - D * pr.beta0 / beta
                      - pr.beta0 * nu * quad_m).sum()
               + K * lnB0 + 0.5 * (pr.nu0 - D - 1) * Elogdet.sum()
               - 0.5 * (nu * torch.einsum("de,ked->k", pr.W0inv, W)).sum())
    q_z = torch.xlogy(r, r).sum()
    ln_c = torch.lgamma(alpha.sum()) - torch.lgamma(alpha).sum()
    q_pi = ((alpha - 1.0) * Elogpi).sum() + ln_c
    H = -_ln_B(W, nu, D) - 0.5 * (nu - D - 1) * Elogdet + 0.5 * nu * D
    q_muLam = (0.5 * Elogdet + 0.5 * D * torch.log(beta / (2 * math.pi)) - 0.5 * D - H).sum()
    return float(e_x + e_z + e_pi + e_muLam - q_z - q_pi - q_muLam)


def _init_params_var(X, K, pr, cov_type, init, graine):
    """Retourne (P, r0). `prior` : paramètres de 1.7.3.d ; `kmeans` : r0 durs, puis étape M."""
    N, D = X.shape
    if init == "kmeans":
        etiq, _ = kmeans(X, K, graine)
        r0 = torch.nn.functional.one_hot(etiq, K).to(X.dtype)
        Nk, xbar, Sk = _stats(X, r0)
        return _etape_m_var(Nk, xbar, Sk, pr, cov_type), r0
    g = generateur(graine)
    idx = torch.randperm(N, generator=g)[:K]
    Nk0 = torch.full((K,), N / K)
    xbar0 = X[idx].clone()
    Sk0 = torch.eye(D).expand(K, D, D).clone()
    P = _etape_m_var(Nk0, xbar0, Sk0, pr, cov_type)
    P["m"] = xbar0                                   # m_k = point de données tiré au hasard
    if cov_type in ("full", "tied"):
        P["Winv"] = pr.W0inv.expand(K, D, D).clone()    # W_k = W_0 (section 1.7.3.d)
        P["W"] = torch.linalg.inv(pr.W0inv).expand(K, D, D).clone()
    return P, None


def _em_var_une_fois(X, K, pr, cov_type, n_iter, tol, init, graine):
    """
    Boucle EM variationnel avec le critère d'arrêt commun. Structure identique à l'EM :
    étape E, évaluation du critère (ELBO de (r, q(theta) courant) en covariance pleine),
    test d'arrêt, étape M. n_iter compte les étapes M.
    """
    N, D = X.shape
    P, r = _init_params_var(X, K, pr, cov_type, init, graine)
    hist, converge, n_m = [], False, 0
    while True:
        r, log_norm = _etape_e_var(X, P)
        Nk, xbar, Sk = _stats(X, r)
        crit = (elbo_gmm_bayesien(r, Nk, xbar, Sk, P, pr) if cov_type == "full"
                else float(log_norm.sum()))
        hist.append(crit)
        if len(hist) > 1 and a_converge(hist[-2], hist[-1], tol):
            converge = True
            break
        if n_m >= n_iter:
            break
        P = _etape_m_var(Nk, xbar, Sk, pr, cov_type)
        n_m += 1
    return {"P": P, "r": r, "crit": hist[-1], "hist": hist, "n_iter": n_m, "converge": converge}


def em_variationnel(X, Kmax, priori: PrioriNW | None = None, alpha0=None, cov_type="full",
                    n_iter=N_ITER_MAX, tol=TOL_REL, init="kmeans", graine=0, n_init=1):
    """
    EM variationnel (champ moyen) pour un GMM bayésien (VB : theta aléatoire).

    Priors par défaut : priors empiriques (beta0 = 1, W0^-1 = covariance empirique). Les priors diffus (beta0 = 1e-3, W0 = I)
    s'obtiennent avec priori=priori_diffus(X, alpha0).

    Critère d'arrêt : le même que l'EM (relatif, total, plafond commun). En covariance pleine
    le critère est l'ELBO (clé critere_nom = "elbo"). Pour tied/diag/spherical, l'ELBO n'est
    pas dérivé : le critère est la somme des log-normalisations de l'étape E (ELBO sans le
    terme KL sur theta), non nécessairement monotone (critere_nom = "approximation_log_norm").

    Retourne un dictionnaire avec les poids E[pi_k], les centres m_k, les covariances
    (E[Lambda_k])^-1, les responsabilités, N_k, l'historique du critère, la liste des
    composantes actives (N_k >= 1, section 1.7.4) et l'indicateur degenere.
    """
    t0 = time.perf_counter()
    pr = priori if priori is not None else priori_empirique(X, alpha0, Kmax)
    if alpha0 is not None and priori is not None:
        pr = PrioriNW(alpha0, pr.m0, pr.beta0, pr.W0inv, pr.nu0)
    meilleur = None
    for s in range(n_init):
        res = _em_var_une_fois(X, Kmax, pr, cov_type, n_iter, tol, init, graine + s)
        if meilleur is None or res["crit"] > meilleur["crit"]:
            meilleur = res
    P = meilleur["P"]
    D = X.shape[1]
    _, Elam = _attendus(P, D)
    Nk = meilleur["r"].sum(0)
    alpha = P["alpha"]
    cov = torch.linalg.inv(Elam)
    masque = indicateur_degenerescence(cov, Nk, D)
    temps = time.perf_counter() - t0
    meilleur.update({
        "pi": alpha / alpha.sum(), "alpha": alpha, "m": P["m"], "Nk": Nk,
        "cov": cov, "labels": meilleur["r"].argmax(1),
        "actives": (Nk >= 1.0).nonzero().flatten(), "n_actives": int((Nk >= 1.0).sum()),
        "elbo_hist": meilleur["hist"] if cov_type == "full" else None,
        "elbo": meilleur["crit"] if cov_type == "full" else None,
        "critere_nom": "elbo" if cov_type == "full" else "approximation_log_norm",
        "degenere": bool(masque.any()), "degenere_composantes": masque,
        "temps": temps, "temps_par_iter": temps / max(meilleur["n_iter"] * n_init, 1),
        "priori": pr, "cov_type": cov_type})
    return meilleur


def svi_gmm(X, Kmax, priori: PrioriNW, taille_lot=50, n_epoques=10, tau=1.0, kappa=0.7, graine=0):
    """
    Inférence variationnelle stochastique (Hoffman et al., 2013), covariance pleine.
    Les paramètres naturels globaux sont mélangés avec le pas rho_t = (t + tau)^(-kappa) :
    lambda <- (1 - rho) lambda + rho lambda_hat, où lambda_hat est calculé sur un
    mini-lot dont les statistiques sont multipliées par N/B.
    """
    g = generateur(graine)
    N, D = X.shape
    P, _ = _init_params_var(X, Kmax, priori, "full", "prior", graine)
    t = 0
    for _ in range(n_epoques):
        perm = torch.randperm(N, generator=g)
        for debut in range(0, N, taille_lot):
            lot = X[perm[debut:debut + taille_lot]]
            r, _ = _etape_e_var(lot, P)
            Nk, xbar, Sk = _stats(lot, r)
            echelle = N / len(lot)
            cible = _etape_m_var(Nk * echelle, xbar, Sk, priori, "full")
            rho = (t + tau) ** (-kappa)
            alpha = (1 - rho) * P["alpha"] + rho * cible["alpha"]
            beta = (1 - rho) * P["beta"] + rho * cible["beta"]
            nu = (1 - rho) * P["nu"] + rho * cible["nu"]
            bm = (1 - rho) * P["beta"][:, None] * P["m"] + rho * cible["beta"][:, None] * cible["m"]
            # paramètre naturel : W^-1 + beta m m^T
            nat = (1 - rho) * (P["Winv"] + P["beta"][:, None, None] * P["m"][:, :, None] * P["m"][:, None, :]) \
                + rho * (cible["Winv"] + cible["beta"][:, None, None] * cible["m"][:, :, None] * cible["m"][:, None, :])
            m = bm / beta[:, None]
            Winv = nat - beta[:, None, None] * m[:, :, None] * m[:, None, :]
            P = {"alpha": alpha, "beta": beta, "m": m, "nu": nu, "Winv": Winv,
                 "W": torch.linalg.inv(Winv), "cov_type": "full"}
            t += 1
    r, _ = _etape_e_var(X, P)
    _, Elam = _attendus(P, D)
    Nk = r.sum(0)
    return {"pi": P["alpha"] / P["alpha"].sum(), "m": P["m"], "cov": torch.linalg.inv(Elam),
            "Nk": Nk, "r": r, "labels": r.argmax(1), "n_actives": int((Nk >= 1).sum()), "P": P}


# ==============================================================================
# MODÈLE DE MARKOV CACHÉ : FORWARD-BACKWARD ET BAUM-WELCH (section 1.6.6)
# ==============================================================================

def forward_backward(A, B, pi0, obs):
    """
    Forward-backward NON normalisé (tableau 1.4).
    A[i,j] = P(z_{t+1}=j | z_t=i), B[i,v] = P(o_t=v | z_t=i). obs : tenseur d'entiers.
    alpha_t(i) = [sum_j alpha_{t-1}(j) A_ji] B_i(o_t), beta_t(i) = sum_j A_ij B_j(o_{t+1}) beta_{t+1}(j).
    """
    T, S = len(obs), A.shape[0]
    alpha = torch.zeros(T, S)
    beta = torch.ones(T, S)
    alpha[0] = pi0 * B[:, obs[0]]
    for t in range(1, T):
        alpha[t] = (alpha[t - 1] @ A) * B[:, obs[t]]
    for t in range(T - 2, -1, -1):
        beta[t] = A @ (B[:, obs[t + 1]] * beta[t + 1])
    proba = alpha[-1].sum()
    gamma = alpha * beta / proba
    xi = torch.zeros(T - 1, S, S)
    for t in range(T - 1):
        xi[t] = alpha[t][:, None] * A * (B[:, obs[t + 1]] * beta[t + 1])[None, :] / proba
    return {"alpha": alpha, "beta": beta, "gamma": gamma, "xi": xi, "proba": float(proba)}


def _fb_normalise(A, logB, pi0):
    """Forward-backward avec normalisation de Rabiner (stable pour les longues séquences)."""
    T, S = logB.shape
    Bm = torch.exp(logB - logB.max(1, keepdim=True).values)
    decal = logB.max(1).values
    alpha = torch.zeros(T, S)
    c = torch.zeros(T)
    a = pi0 * Bm[0]
    c[0] = a.sum()
    alpha[0] = a / c[0]
    for t in range(1, T):
        a = (alpha[t - 1] @ A) * Bm[t]
        c[t] = a.sum()
        alpha[t] = a / c[t]
    beta = torch.ones(T, S)
    for t in range(T - 2, -1, -1):
        beta[t] = (A @ (Bm[t + 1] * beta[t + 1])) / c[t + 1]
    gamma = alpha * beta
    gamma = gamma / gamma.sum(1, keepdim=True)
    xi = (alpha[:-1, :, None] * A[None] * (Bm[1:] * beta[1:])[:, None, :]) / c[1:, None, None]
    loglik = float(torch.log(c).sum() + decal.sum())
    return gamma, xi, loglik


def baum_welch(sequences, S, emission="discrete", V=None, n_iter=100, tol=1e-6, graine=0):
    """
    Baum-Welch : EM classique où l'étape E est forward-backward.
    emission = "discrete" (V symboles) ou "gauss" (observations réelles scalaires).
    Étape M : A_ij = sum xi / sum gamma, B_i(v) = sum_{o_t = v} gamma / sum gamma (discret),
              mu_i, sigma_i^2 = moyennes pondérées par gamma (gaussien).
    """
    g = generateur(graine)
    A = torch.rand(S, S, generator=g) + 1.0
    A = A / A.sum(1, keepdim=True)
    pi0 = torch.ones(S) / S
    if emission == "discrete":
        B = torch.rand(S, V, generator=g) + 1.0
        B = B / B.sum(1, keepdim=True)
    else:
        tout = torch.cat([s for s in sequences])
        q = torch.sort(tout).values
        mu = q[(torch.arange(S) * 2 + 1) * len(q) // (2 * S)].clone()
        var = torch.full((S,), float(tout.var()))
    hist = []
    for it in range(n_iter):
        gam_l, xi_l, ll = [], [], 0.0
        for obs in sequences:
            if emission == "discrete":
                logB = torch.log(B[:, obs].T)
            else:
                logB = -0.5 * (LOG2PI + torch.log(var)[None] + (obs[:, None] - mu[None]) ** 2 / var[None])
            gamma, xi, l = _fb_normalise(A, logB, pi0)
            gam_l.append(gamma); xi_l.append(xi); ll += l
        hist.append(ll)
        if it > 0 and abs(hist[-1] - hist[-2]) < tol:
            break
        pi0 = torch.stack([g_[0] for g_ in gam_l]).mean(0)
        num = sum(x.sum(0) for x in xi_l)
        den = sum(g_[:-1].sum(0) for g_ in gam_l)
        A = num / den[:, None]
        tot = sum(g_.sum(0) for g_ in gam_l)
        if emission == "discrete":
            Bn = torch.zeros(S, V)
            for obs, g_ in zip(sequences, gam_l):
                Bn.index_add_(1, obs, g_.T)
            B = Bn / tot[:, None]
        else:
            mu = sum((g_ * o[:, None]).sum(0) for o, g_ in zip(sequences, gam_l)) / tot
            var = sum((g_ * (o[:, None] - mu[None]) ** 2).sum(0)
                      for o, g_ in zip(sequences, gam_l)) / tot + 1e-9
    out = {"A": A, "pi0": pi0, "loglik": hist[-1], "ll_hist": hist, "n_iter": len(hist)}
    out.update({"B": B} if emission == "discrete" else {"mu": mu, "var": var})
    return out


def simuler_hmm(A, B, pi0, T, graine=0):
    g = generateur(graine)
    z = torch.multinomial(pi0, 1, generator=g).item()
    obs = []
    for _ in range(T):
        obs.append(torch.multinomial(B[z], 1, generator=g).item())
        z = torch.multinomial(A[z], 1, generator=g).item()
    return torch.tensor(obs)


# ==============================================================================
# LDA VARIATIONNEL (section 3.1.1, équations 3.1 et 3.2)
# ==============================================================================

def lda_variationnel(comptes: Tensor, K: int, alpha=0.1, n_iter=N_ITER_MAX, n_iter_doc=50,
                     tol=TOL_REL, graine=0, lissage=1e-3):
    """
    LDA de Blei, Ng et Jordan (2003) par EM variationnel.

    comptes : (D, V) nombres d'occurrences de chaque mot dans chaque document.
    Étape E (par document) : phi_{vk} proportionnel à beta_{kv} exp(E[log theta_k])   (éq. 3.2)
                             gamma_k = alpha + sum_v comptes_v phi_{vk}
    Étape M : beta_{kv} proportionnel à sum_d comptes_{dv} phi_{dvk}.
    Retourne aussi la borne variationnelle L(gamma, phi ; alpha, beta) à chaque itération.
    """
    g = generateur(graine)
    D, V = comptes.shape
    beta = torch.rand(K, V, generator=g) + 1.0
    beta = beta / beta.sum(1, keepdim=True)
    Nd = comptes.sum(1)
    gamma = alpha + Nd[:, None] / K
    digam = torch.special.digamma
    bornes, converge = [], False
    for it in range(n_iter):
        logbeta = torch.log(beta)
        for _ in range(n_iter_doc):
            Elog = digam(gamma) - digam(gamma.sum(1, keepdim=True))                # (D,K)
            logphi = Elog[:, None, :] + logbeta.T[None, :, :]                      # (D,V,K)
            phi = torch.softmax(logphi, dim=2)
            gamma_new = alpha + (comptes[:, :, None] * phi).sum(1)
            delta = (gamma_new - gamma).abs().max()
            gamma = gamma_new
            if delta < 1e-8:
                break
        Elog = digam(gamma) - digam(gamma.sum(1, keepdim=True))
        phi = torch.softmax(Elog[:, None, :] + logbeta.T[None, :, :], dim=2)
        c = comptes[:, :, None]
        L = (math.lgamma(K * alpha) - K * math.lgamma(alpha)
             + ((alpha - 1) * Elog).sum()
             + (c * phi * Elog[:, None, :]).sum()
             + (c * phi * logbeta.T[None]).sum()
             - (torch.lgamma(gamma.sum(1)) - torch.lgamma(gamma).sum(1)).sum()
             - ((gamma - 1) * Elog).sum()
             - (c * torch.xlogy(phi, phi)).sum())
        bornes.append(float(L))
        beta = (c * phi).sum(0).T + lissage
        beta = beta / beta.sum(1, keepdim=True)
        if it > 0 and a_converge(bornes[-2], bornes[-1], tol):
            converge = True
            break
    theta = gamma / gamma.sum(1, keepdim=True)
    return {"beta": beta, "gamma": gamma, "theta": theta, "bornes": bornes, "n_iter": len(bornes),
            "converge": converge, "alpha": alpha}


# ==============================================================================
# pLSA PAR EM (Hofmann, 1999) : comparateur « EM classique » de la LDA
# ==============================================================================

def plsa_em(comptes: Tensor, K: int, n_iter=N_ITER_MAX, tol=TOL_REL, graine=0, tempering=1.0):
    """
    pLSA par EM : p(w | d) = somme_k theta_dk phi_kw, estimé par maximum de vraisemblance,
    sans prior (theta ponctuel, phi ponctuel). Même critère d'arrêt que le reste du module
    (log-vraisemblance totale, tolérance relative, plafond d'étapes M).

    comptes : (D, V). tempering = beta de l'EM tempéré (Hofmann 2001) : l'étape E élève
    p(z | d, w) à la puissance beta ; beta = 1 est l'EM standard (log-vraisemblance monotone),
    beta < 1 régularise (la monotonie n'est alors plus garantie).
    """
    g = generateur(graine)
    Dn, V = comptes.shape
    theta = torch.rand(Dn, K, generator=g) + 1.0
    theta = theta / theta.sum(1, keepdim=True)
    phi = torch.rand(K, V, generator=g) + 1.0
    phi = phi / phi.sum(1, keepdim=True)
    hist, converge, n_m = [], False, 0
    while True:
        melange = theta @ phi                                           # (D, V)
        hist.append(float(torch.xlogy(comptes, melange).sum()))
        if len(hist) > 1 and a_converge(hist[-2], hist[-1], tol):
            converge = True
            break
        if n_m >= n_iter:
            break
        if tempering == 1.0:
            ratio = comptes / melange.clamp(min=1e-300)
            phi_n = phi * (theta.T @ ratio)                             # sum_d c_dv p(z|d,v)
            theta_n = theta * (ratio @ phi.T)                           # sum_v c_dv p(z|d,v)
        else:
            post = (theta[:, None, :] * phi.T[None, :, :]).pow(tempering)
            post = post / post.sum(-1, keepdim=True).clamp(min=1e-300)
            poids = comptes[:, :, None] * post
            phi_n = poids.sum(0).T
            theta_n = poids.sum(1)
        phi = phi_n / phi_n.sum(1, keepdim=True).clamp(min=1e-300)
        theta = theta_n / theta_n.sum(1, keepdim=True).clamp(min=1e-300)
        n_m += 1
    return {"theta": theta, "phi": phi, "loglik": hist[-1], "ll_hist": hist,
            "n_iter": n_m, "converge": converge}
