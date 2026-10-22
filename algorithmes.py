"""
================================================================================
EM CLASSIQUE ET EM VARIATIONNEL POUR LES MODÈLES DE MÉLANGE (PyTorch pur)
Kana Tiodong Icare Brichel, Master 2 SDIA, ENSPD, Université de Douala
================================================================================

Implémentation sans scikit-learn, sans SciPy et sans NumPy. Seules les opérations
élémentaires de PyTorch sont utilisées (algèbre linéaire, digamma, lgamma) ; les
modèles, les critères et les métriques sont écrits à la main.

Calcul tensoriel par lots : les relances (B) et les composantes (K) d'un ajustement sont
traitées dans un seul tenseur ; la forme quadratique et les dispersions passent par les
statistiques suffisantes (x x^T vectorisés), sans tenseur (B, K, N, D). Les données sont centrées
en interne (sans effet sur la vraisemblance ni sur la partition). L'équivalence avec
l'implémentation séquentielle d'origine est vérifiée par tests/test_equivalence_lots.py.

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
  * test : |c_t - c_(t-1)| <= tol_rel * max(|c_(t-1)|, 1)  (tolérance relative) ;
  * plafond : n_iter_max étapes M ;
  * tol_rel, n_iter_max, reg_covariance et toutes les autres valeurs méthodologiques viennent du
    registre `parametres.py`, où chacune est justifiée (source vérifiée, benchmark ou recherche).
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

import parametres as PARAM

torch.set_default_dtype(torch.float64)

LOG2PI = math.log(2.0 * math.pi)
LN2 = math.log(2.0)
LNPI = math.log(math.pi)
TYPES_COVARIANCE = ("full", "tied", "diag", "spherical")

def a_converge(c_prec: float, c: float, tol: float | None = None) -> bool:
    """Test d'arrêt commun : variation relative du critère total (tolérance du registre par défaut)."""
    tol = float(PARAM.valeur("tol_rel")) if tol is None else tol
    return abs(c - c_prec) <= tol * max(abs(c_prec), 1.0)


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


# kmeans_lot / kmeans : voir le noyau par lots ci-dessous

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
# DISTRIBUTIONS A PRIORI (hyperparamètres du GMM bayésien)
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


# ==============================================================================
# NOYAU TENSORIEL PAR LOTS (relances et composantes traitées en un seul tenseur)
# ==============================================================================
# Convention de dimensions : B relances (lot), K composantes, N observations, D dimensions.
#   pi (B,K)   mu (B,K,D)   cov (B,K,D,D)   r (B,N,K)
# Chaque relance suit exactement la même suite d'opérations que dans une boucle séquentielle :
# un masque `actif` arrête chaque relance au moment où son propre test de convergence ou le
# plafond est atteint (tests/test_equivalence_lots.py compare à l'implémentation séquentielle
# figée). Une relance dont une factorisation de Cholesky échoue est marquée `echec` et exclue ;
# l'ajustement ne lève d'erreur que si TOUTES les relances échouent.

class EchecNumerique(RuntimeError):
    """Toutes les relances d'un ajustement ont échoué (covariance non définie positive)."""


def _elements_lot_max() -> int:
    """Taille maximale (éléments) d'un tenseur (b, K, N) traité d'un coup : réglage de mémoire, sans effet sur les résultats."""
    return int(PARAM.valeur("elements_lot_max"))


def _tranches(B: int, K: int, N: int):
    pas = max(1, _elements_lot_max() // max(K * N, 1))
    return [slice(i, min(i + pas, B)) for i in range(0, B, pas)]


class _Prep:
    """
    Données préparées pour le noyau : X centré (translation qui ne change ni la vraisemblance ni la
    partition, mais limite les erreurs d'annulation) et produits xx^T vectorisés (N, D*D), calculés une fois.
    """
    __slots__ = ("X", "XX", "c", "N", "D")

    def __init__(self, X: Tensor, centrer: bool = True):
        self.c = X.mean(0) if centrer else torch.zeros(X.shape[1], dtype=X.dtype)
        self.X = X - self.c
        self.N, self.D = X.shape
        self.XX = (self.X[:, :, None] * self.X[:, None, :]).reshape(self.N, self.D * self.D)


def _sel(p: dict, idx) -> dict:
    """Sous-lot d'un dictionnaire de tenseurs indexés par la relance (les valeurs non tensorielles sont conservées)."""
    return {k: (v[idx] if torch.is_tensor(v) else v) for k, v in p.items()}


def _aff(p: dict, idx, sous: dict) -> None:
    for k, v in sous.items():
        if torch.is_tensor(v):
            p[k][idx] = v


def kmeans_lot(X: Tensor, K: int, graines, n_iter: int | None = None, retour_iters: bool = False):
    """
    K-means (Lloyd) avec initialisation k-means++ (Arthur et Vassilvitskii 2007), une graine par relance,
    itérations de Lloyd en lot. Arrêt quand les centres ne bougent plus (torch.allclose) ou au plafond.
    Retourne (étiquettes (B,N), centres (B,K,D), plafond_atteint (B,)) et, si retour_iters, le nombre
    d'itérations de Lloyd de chaque relance.
    """
    n_iter = int(PARAM.valeur("kmeans_n_iter_max")) if n_iter is None else n_iter
    N, D = X.shape
    B = len(graines)
    centres = X.new_empty(B, K, D)
    for b, gr in enumerate(graines):
        g = generateur(gr)
        c = X[torch.randint(N, (1,), generator=g)].clone()
        for _ in range(1, K):
            d2 = torch.cdist(X, c).pow(2).min(dim=1).values
            p = d2 / d2.sum() if d2.sum() > 0 else torch.full((N,), 1.0 / N)
            c = torch.cat([c, X[torch.multinomial(p, 1, generator=g)]], dim=0)
        centres[b] = c
    actif = torch.ones(B, dtype=torch.bool)
    iters = torch.zeros(B, dtype=torch.long)
    for _ in range(n_iter):
        idx = actif.nonzero().flatten()
        if len(idx) == 0:
            break
        iters[idx] += 1
        c = centres[idx]
        etiq = torch.cdist(X[None].expand(len(idx), N, D), c).argmin(dim=-1)
        un = torch.nn.functional.one_hot(etiq, K).to(X.dtype)                  # (b,N,K)
        cnt = un.sum(1)
        nouveaux = torch.where(cnt[..., None] > 0,
                               torch.einsum("bnk,nd->bkd", un, X) / cnt.clamp(min=1)[..., None], c)
        conv = ((nouveaux - c).abs() <= 1e-8 + 1e-5 * c.abs()).all(-1).all(-1)    # torch.allclose, par relance
        centres[idx] = torch.where(conv[:, None, None], c, nouveaux)
        actif[idx[conv]] = False
    etiq = torch.cdist(X[None].expand(B, N, D), centres).argmin(dim=-1)
    if retour_iters:
        return etiq, centres, actif.clone(), iters
    return etiq, centres, actif.clone()


def kmeans(X: Tensor, K: int, graine: int = 0, n_iter: int | None = None):
    """K-means (Lloyd) avec initialisation k-means++. Retourne (étiquettes, centres)."""
    etiq, centres, _ = kmeans_lot(X, K, [graine], n_iter)
    return etiq[0], centres[0]


def _dispersion_lot(dp: "_Prep", r: Tensor, xbar: Tensor, Nk: Tensor) -> Tensor:
    """
    S_k = somme_n r_nk (x_n - xbar_k)(x_n - xbar_k)^T = somme_n r_nk x_n x_n^T - N_k xbar_k xbar_k^T
    (statistiques suffisantes, sans tenseur (B,K,N,D)) ; xbar_k doit être la moyenne pondérée.
    """
    B, N, K = r.shape
    D = dp.D
    S = (r.transpose(1, 2) @ dp.XX).reshape(B, K, D, D) - Nk[..., None, None] * xbar[..., :, None] * xbar[..., None, :]
    return 0.5 * (S + S.transpose(-1, -2))


def _forme_quadratique(dp: "_Prep", Lam: Tensor, mu: Tensor) -> Tensor:
    """(x_n - mu_bk)^T Lam_bk (x_n - mu_bk) pour tout (b,k,n), par développement : (B,K,N)."""
    B, K, D, _ = Lam.shape
    q1 = (Lam.reshape(B * K, D * D) @ dp.XX.T).reshape(B, K, dp.N)
    Lmu = (Lam @ mu[..., None]).squeeze(-1)                                   # (B,K,D)
    q2 = Lmu @ dp.X.T                                                         # (B,K,N)
    q3 = (mu * Lmu).sum(-1)                                                   # (B,K)
    return (q1 - 2.0 * q2 + q3[..., None]).clamp(min=0.0)


def _log_gauss_lot(dp: "_Prep", mu: Tensor, cov: Tensor):
    """log N(x_n | mu_bk, cov_bk) via Cholesky : (B,K,N) et masque `ok` (B,) des relances factorisables."""
    D = dp.D
    L, info = torch.linalg.cholesky_ex(cov)
    bon = info == 0
    L = torch.where(bon[..., None, None], L, torch.eye(D, dtype=L.dtype))      # évite les NaN dans le lot
    Lam = torch.cholesky_inverse(L)
    logdet = 2.0 * torch.log(torch.diagonal(L, dim1=-2, dim2=-1)).sum(-1)
    lp = -0.5 * (D * LOG2PI + logdet[..., None] + _forme_quadratique(dp, Lam, mu))
    return lp, bon.all(dim=-1)


def _etape_e_lot(dp: "_Prep", pi: Tensor, mu: Tensor, cov: Tensor):
    """Étape E (1.15) en log-espace pour toutes les relances : (r (B,N,K), log p(x_n | theta) (B,N), ok (B,))."""
    B, K, D = mu.shape
    N = dp.N
    r = dp.X.new_empty(B, N, K)
    ln = dp.X.new_empty(B, N)
    ok = torch.empty(B, dtype=torch.bool)
    for sl in _tranches(B, K, N):
        lp, ok[sl] = _log_gauss_lot(dp, mu[sl], cov[sl])
        log_r = (torch.log(pi[sl] + 1e-300)[:, :, None] + lp).transpose(1, 2)    # (b,N,K)
        ln[sl] = torch.logsumexp(log_r, dim=2)
        r[sl] = torch.exp(log_r - ln[sl][..., None])
    return r, ln, ok


def _moyennes(dp, r):
    Nk = r.sum(1) + 1e-10
    return Nk, torch.einsum("bnk,nd->bkd", r, dp.X) / Nk[..., None]


def _covariances_lot(dp, r, mu, Nk, cov_type, reg):
    """Mise à jour des covariances (1.16) selon la contrainte de forme choisie, en lot."""
    B, K, D = mu.shape
    S = _dispersion_lot(dp, r, mu, Nk)
    I = torch.eye(D, dtype=dp.X.dtype)
    if cov_type == "full":
        cov = S / Nk[..., None, None]
    elif cov_type == "tied":
        cov = (S.sum(1) / Nk.sum(1)[:, None, None])[:, None].expand(B, K, D, D).clone()
    elif cov_type == "diag":
        cov = torch.diag_embed(torch.diagonal(S, dim1=-2, dim2=-1) / Nk[..., None])
    elif cov_type == "spherical":
        v = torch.diagonal(S, dim1=-2, dim2=-1).sum(-1) / (D * Nk)
        cov = v[..., None, None] * I
    else:
        raise ValueError(cov_type)
    return cov + reg * I


def _etape_m_lot(dp, r, cov_type, reg):
    """Étape M (1.16) : pi_k = N_k/N, mu_k = moyenne pondérée, Sigma_k = covariance pondérée."""
    Nk, mu = _moyennes(dp, r)
    return Nk / dp.N, mu, _covariances_lot(dp, r, mu, Nk, cov_type, reg)


def _etape_m_map_lot(dp, r, pr: "PrioriNW", reg):
    """
    Étape M du MAP-EM (covariance pleine), en lot : mode conjoint de (pi, mu, Sigma) sous le prior
    Dirichlet x Normale-Inverse-Wishart (pr exprimé dans les coordonnées centrées de dp).
      pi_k    proportionnel à N_k + alpha0 - 1
      mu_k  = (beta0 m0 + N_k xbar_k) / (beta0 + N_k)
      Sigma_k = (W0^-1 + S_k + beta0 N_k/(beta0+N_k) (xbar_k-m0)(xbar_k-m0)^T) / (nu0 + N_k + D + 2)
    Exige alpha0 >= 1 (sinon le mode est au bord du simplexe).
    """
    D = dp.D
    Nk, xbar = _moyennes(dp, r)
    pi = (Nk + pr.alpha0 - 1.0).clamp(min=1e-10)
    pi = pi / pi.sum(-1, keepdim=True)
    mu = (pr.beta0 * pr.m0 + Nk[..., None] * xbar) / (pr.beta0 + Nk)[..., None]
    S = _dispersion_lot(dp, r, xbar, Nk)
    d0 = xbar - pr.m0
    couplage = (pr.beta0 * Nk / (pr.beta0 + Nk))[..., None, None] * d0[..., :, None] * d0[..., None, :]
    cov = (pr.W0inv + S + couplage) / (pr.nu0 + Nk + D + 2.0)[..., None, None]
    return pi, mu, cov + reg * torch.eye(D, dtype=dp.X.dtype)


def _init_em_lot(dp, K, cov_type, init, graines, reg):
    N, D = dp.N, dp.D
    B = len(graines)
    if init == "kmeans":
        etiq, _, _ = kmeans_lot(dp.X, K, graines)
        r0 = torch.nn.functional.one_hot(etiq, K).to(dp.X.dtype)
        return _etape_m_lot(dp, r0, cov_type, reg)
    mu = dp.X.new_empty(B, K, D)
    for b, gr in enumerate(graines):                                   # initialisation aléatoire (1.6.2.a)
        mu[b] = dp.X[torch.randperm(N, generator=generateur(gr))[:K]]
    cov0 = torch.cov(dp.X.T).reshape(D, D) + reg * torch.eye(D, dtype=dp.X.dtype)
    return torch.full((B, K), 1.0 / K, dtype=dp.X.dtype), mu, cov0.expand(B, K, D, D).clone()


def _piloter_lot(params: dict, B: int, n_iter: int, tol: float, evaluer, maj, instantane=None, meta=None):
    """
    Boucle commune à l'EM, au MAP-EM, au VB, à la LDA et au pLSA, avec le critère d'arrêt commun.
    Une itération = une étape E (évaluer), test d'arrêt, puis une étape M (maj) ; n_iter compte les étapes M.
      evaluer(sous_params) -> (r, critere (b,), ok (b,), aux)
      maj(sous_params, r, aux) -> nouveaux paramètres du sous-lot
    Si `instantane` est fourni (objet avec .lire() et .ecrire(dict), .tous = période en passages), l'état
    complet de la boucle est sauvegardé périodiquement et restauré au démarrage : la reprise après une
    interruption redonne exactement le même résultat (la boucle ne consomme aucun nombre aléatoire).
    """
    hist = torch.full((n_iter + 1, B), float("nan"), dtype=torch.float64)
    compte = torch.zeros(B, dtype=torch.long)
    n_m = torch.zeros(B, dtype=torch.long)
    converge = torch.zeros(B, dtype=torch.bool)
    echec = torch.zeros(B, dtype=torch.bool)
    actif = torch.ones(B, dtype=torch.bool)
    t = 0
    if instantane is not None:
        etat = instantane.lire()
        if etat is not None and etat.get("meta") == meta:
            for k, v in etat["params"].items():
                params[k] = v
            hist, compte, n_m = etat["hist"], etat["compte"], etat["n_m"]
            converge, echec, actif, t = etat["converge"], etat["echec"], etat["actif"], etat["t"]
    while True:
        idx = actif.nonzero().flatten()
        if len(idx) == 0:
            break
        sub = _sel(params, idx)
        r, crit, ok, aux = evaluer(sub)
        if not bool(ok.all()):
            echec[idx[~ok]] = True
            actif[idx[~ok]] = False
        pos_ok = ok.nonzero().flatten()
        bons = idx[pos_ok]
        if len(bons):
            c = crit[pos_ok]
            pos = compte[bons]
            hist[pos, bons] = c
            compte[bons] += 1
            prev = hist[(pos - 1).clamp(min=0), bons]
            conv = (pos >= 1) & ((c - prev).abs() <= tol * prev.abs().clamp(min=1.0))
            converge[bons[conv]] = True
            actif[bons[conv]] = False
            stop = (~conv) & (n_m[bons] >= n_iter)
            actif[bons[stop]] = False
            cont = (~conv) & (~stop)
            if bool(cont.any()):
                sel = pos_ok[cont]
                aux_sel = None if aux is None else tuple(a[sel] for a in aux)
                nouveaux = maj(_sel(sub, sel), r[sel], aux_sel)
                _aff(params, bons[cont], nouveaux)
                n_m[bons[cont]] += 1
        t += 1
        if instantane is not None and t % instantane.tous == 0 and bool(actif.any()):
            instantane.ecrire({"meta": meta, "params": {k: v for k, v in params.items() if torch.is_tensor(v)},
                               "hist": hist, "compte": compte, "n_m": n_m, "converge": converge,
                               "echec": echec, "actif": actif, "t": t})
    return {"hist": hist, "compte": compte, "n_m": n_m, "converge": converge, "echec": echec, "passages": t}


def _em_lot(dp, K, cov_type, n_iter, tol, reg, init, graines, prior=None, instantane=None):
    """EM (prior=None) ou MAP-EM (prior fourni, en coordonnées centrées) pour len(graines) relances en lot."""
    pi, mu, cov = _init_em_lot(dp, K, cov_type, init, graines, reg)
    params = {"pi": pi, "mu": mu, "cov": cov}

    def evaluer(sub):
        r, ln, ok = _etape_e_lot(dp, sub["pi"], sub["mu"], sub["cov"])
        return r, ln.sum(1), ok, None

    def maj(sub, r, aux):
        p, m, c = (_etape_m_lot(dp, r, cov_type, reg) if prior is None else _etape_m_map_lot(dp, r, prior, reg))
        return {"pi": p, "mu": m, "cov": c}

    meta = {"algo": "em" if prior is None else "map", "K": K, "N": dp.N, "D": dp.D, "cov": cov_type, "init": init,
            "graines": list(graines), "tol": tol, "n_iter": n_iter, "reg": reg}
    etat = _piloter_lot(params, len(graines), n_iter, tol, evaluer, maj, instantane, meta)
    bons = (~etat["echec"]).nonzero().flatten()
    if len(bons) == 0:
        raise EchecNumerique("EM : toutes les relances ont échoué (covariance non définie positive)")
    r = dp.X.new_zeros(len(graines), dp.N, K)
    r[bons], _, _ = _etape_e_lot(dp, params["pi"][bons], params["mu"][bons], params["cov"][bons])
    etat.update(params=params, r=r)
    return etat


def indicateurs_degenerescence(cov: Tensor, Nk: Tensor, D: int, reg: float):
    """
    Deux indicateurs distincts, par composante non éteinte (N_k >= 1) :
      petite      : 1 <= N_k < D + 1. Avec moins de D + 1 points, la covariance empirique est de rang
                    au plus N_k - 1 < D : l'estimateur du maximum de vraisemblance est singulier (fait algébrique).
      plancher    : la plus petite valeur propre de Sigma_k est au plus 2 reg, c'est-à-dire que la
                    régularisation (+ reg I) fournit au moins la moitié de la plus petite variance : la
                    composante s'est effondrée sur un sous-espace et n'est tenue que par le plancher.
                    Ce critère n'est défini que si reg > 0 (EM et MAP-EM) ; pour le VB il vaut faux.
    Retourne (petite, plancher), deux masques (K,).
    """
    non_eteinte = Nk >= 1.0
    petite = non_eteinte & (Nk < D + 1)
    if reg > 0:
        vp_min = torch.linalg.eigvalsh(cov).min(dim=-1).values
        plancher = non_eteinte & (vp_min <= 2.0 * reg)
    else:
        plancher = torch.zeros_like(non_eteinte)
    return petite, plancher


def _finaliser_em(lot, dp, K, cov_type, t0, reg, prior=None, graines=None):
    N, D = dp.N, dp.D
    B = lot["compte"].shape[0]
    n_it, comp = lot["n_m"], lot["compte"]
    ll = torch.stack([lot["hist"][comp[b] - 1, b] if comp[b] > 0 else torch.tensor(float("nan")) for b in range(B)])
    score = ll.clone()
    if prior is not None and prior.beta0 > 0:
        for b in range(B):
            if not lot["echec"][b]:
                score[b] = ll[b] + log_priori_nw(lot["params"]["pi"][b], lot["params"]["mu"][b], lot["params"]["cov"][b], prior)
    score[lot["echec"]] = -float("inf")
    b = int(torch.argmax(score))
    pi, mu, cov, r = (lot["params"]["pi"][b], lot["params"]["mu"][b] + dp.c, lot["params"]["cov"][b], lot["r"][b])
    p = nb_parametres(K, D, cov_type)
    Nk = r.sum(0)
    petite, plancher = indicateurs_degenerescence(cov, Nk, D, reg)
    temps = time.perf_counter() - t0
    res = {"pi": pi, "mu": mu, "cov": cov, "r": r, "loglik": float(ll[b]),
           "ll_hist": lot["hist"][:comp[b], b].tolist(), "n_iter": int(n_it[b]), "converge": bool(lot["converge"][b]),
           "Nk": Nk, "labels": r.argmax(1), "n_params": p, "bic": bic(float(ll[b]), p, N), "aic": aic(float(ll[b]), p),
           "icl": icl(float(ll[b]), p, N, r), "entropie": entropie_affectation(r),
           "petite_composante": bool(petite.any()), "plancher_regularisation": bool(plancher.any()),
           "degenere": bool((petite | plancher).any()), "degenere_composantes": petite | plancher,
           "temps": temps, "cov_type": cov_type, "reg": reg, "temps_par_iter": temps / max(lot["passages"], 1),
           "relances": {"critere": ll.tolist(), "n_iter": n_it.tolist(), "converge": lot["converge"].tolist(),
                        "echec": lot["echec"].tolist(), "meilleure": b, "graines": list(graines) if graines else None}}
    if prior is not None and prior.beta0 > 0:
        res["log_posteriori"] = float(score[b])
    return res


def _defauts(tol, n_iter, reg):
    return (float(PARAM.valeur("tol_rel")) if tol is None else tol,
            int(PARAM.valeur("n_iter_max")) if n_iter is None else n_iter,
            float(PARAM.valeur("reg_covariance")) if reg is None else reg)


def em_classique(X, K, cov_type="full", n_iter=None, tol=None, reg=None,
                 init="kmeans", graine=0, n_init=1, instantane=None):
    """
    EM classique pour un mélange de K gaussiennes. Les n_init relances (graines graine, graine+1, ...)
    sont ajustées EN LOT dans un seul tenseur ; on garde la plus grande log-vraisemblance.

    init : "kmeans" (par défaut, comme la pratique courante) ou "aleatoire"
           (K points tirés au hasard, covariance globale, section 1.6.2.a).
    tol, n_iter, reg : par défaut, valeurs du registre `parametres.py` (critère d'arrêt commun,
          régularisation Sigma_k + reg I qui fait de l'EM un maximum « restreint »).
    instantane : objet de sauvegarde périodique de l'état de la boucle (reprise exacte), facultatif.
    Retourne aussi bic, aic, icl, les indicateurs de dégénérescence, temps_par_iter (temps / passages
    du lot) et `relances` (critère, itérations, convergence et échec de chaque relance).
    """
    tol, n_iter, reg = _defauts(tol, n_iter, reg)
    t0 = time.perf_counter()
    graines = [graine + s for s in range(n_init)]
    dp = _Prep(X)
    lot = _em_lot(dp, K, cov_type, n_iter, tol, reg, init, graines, None, instantane)
    return _finaliser_em(lot, dp, K, cov_type, t0, reg, None, graines)


def _priori_centre(pr: "PrioriNW", c: Tensor) -> "PrioriNW":
    return PrioriNW(pr.alpha0, pr.m0 - c, pr.beta0, pr.W0inv, pr.nu0)


def map_em(X, K, priori: "PrioriNW", n_iter=None, tol=None, reg=None,
           init="kmeans", graine=0, n_init=1, instantane=None):
    """
    MAP-EM (covariance pleine) : EM dont l'étape M maximise Q + log p(theta) avec les priors
    conjugués du VB. Isole l'effet du prior de celui de l'inférence bayésienne complète.
    Le critère d'arrêt est le même que pour l'EM (log-vraisemblance totale). On garde la
    relance de plus grand log-posteriori. Exige priori.alpha0 >= 1.
    """
    if priori.alpha0 < 1.0:
        raise ValueError("MAP-EM : alpha0 >= 1 requis (mode du Dirichlet)")
    tol, n_iter, reg = _defauts(tol, n_iter, reg)
    t0 = time.perf_counter()
    graines = [graine + s for s in range(n_init)]
    dp = _Prep(X)
    prc = _priori_centre(priori, dp.c)
    lot = _em_lot(dp, K, "full", n_iter, tol, reg, init, graines, prc, instantane)
    return _finaliser_em(lot, dp, K, "full", t0, reg, prc, graines)


# --- versions « une relance » conservées pour les variantes stochastiques, la validation et l'évaluation ---

def _etape_e(X, pi, mu, cov):
    """Étape E (1.15) pour un seul jeu de paramètres : (r (N,K), log p(x_i | theta) (N,))."""
    dp = _Prep(X)
    r, ln, ok = _etape_e_lot(dp, pi[None], (mu - dp.c)[None], cov[None])
    if not bool(ok[0]):
        raise EchecNumerique("covariance non définie positive")
    return r[0], ln[0]


def _etape_m(X, r, cov_type, reg):
    dp = _Prep(X)
    pi, mu, cov = _etape_m_lot(dp, r[None], cov_type, reg)
    return pi[0], mu[0] + dp.c, cov[0]


def _etape_m_map(X, r, pr: "PrioriNW", reg):
    dp = _Prep(X)
    pi, mu, cov = _etape_m_map_lot(dp, r[None], _priori_centre(pr, dp.c), reg)
    return pi[0], mu[0] + dp.c, cov[0]


def _init_em(X, K, cov_type, init, graine, reg):
    dp = _Prep(X)
    pi, mu, cov = _init_em_lot(dp, K, cov_type, init, [graine], reg)
    return pi[0], mu[0] + dp.c, cov[0]


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


def energie_libre_em(X, r, pi, mu, cov):
    """
    F(q, theta) = E_q[log p(X,Z|theta)] - E_q[log q(Z)] (section 1.2.2).
    Après une étape E, q(Z) = p(Z|X,theta) et F = log-vraisemblance (égalité de Jensen).
    """
    dp = _Prep(X)
    lp, ok = _log_gauss_lot(dp, (mu - dp.c)[None], cov[None])
    log_joint = torch.log(pi)[:, None] + lp[0]                       # (K,N)
    return float((r * log_joint.T).sum() - torch.xlogy(r, r).sum())


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


def em_stochastique(X, K, n_iter=150, reg=None, graine=0, burn=50):
    """
    EM stochastique (Celeux et Diebolt, 1985) : l'étape E devient un tirage
    z_i ~ Categorielle(r_i), l'étape M est faite sur ces affectations dures.
    La log-vraisemblance n'est plus monotone. On renvoie la moyenne des
    paramètres après `burn` itérations, alignés par l'algorithme hongrois (moyenne_alignee) (les composantes vides sont réinitialisées).
    """
    reg = float(PARAM.valeur("reg_covariance")) if reg is None else reg
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


def em_online(X, K, taille_lot=50, n_epoques=5, kappa=0.6, t0=10.0, reg=None, graine=0):
    """
    EM online par statistiques suffisantes (Sato et Ishii 2000, Cappé et Moulines 2009).
    s <- (1 - eta_t) s + eta_t * s_lot avec eta_t = (t + t0)^(-kappa), kappa dans (0.5, 1]
    (conditions de type Robbins-Monro de la section 1.6.5).
    """
    reg = float(PARAM.valeur("reg_covariance")) if reg is None else reg
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
def _ln_B_ld(logdetW, nu, D):
    """ln B(W, nu), constante de normalisation de la Wishart, à partir de ln|W| (stable : fourni par Cholesky)."""
    i = torch.arange(1, D + 1, dtype=torch.float64)
    lg = torch.lgamma((nu[..., None] + 1 - i) / 2).sum(-1)
    return -0.5 * nu * logdetW - (0.5 * nu * D * LN2 + D * (D - 1) / 4 * LNPI + lg)


def _ln_B(W, nu, D):
    """log de la constante de normalisation de la Wishart, ln B(W, nu)."""
    return _ln_B_ld(torch.logdet(W), nu, D)


def _inverse_chol(M):
    """Inverse et ln|M^-1| d'une matrice symétrique définie positive par Cholesky ; `ok` si M est factorisable."""
    D = M.shape[-1]
    L, info = torch.linalg.cholesky_ex(M)
    bon = info == 0
    L = torch.where(bon[..., None, None], L, torch.eye(D, dtype=L.dtype))
    inv = torch.cholesky_inverse(L)
    logdet_inv = -2.0 * torch.log(torch.diagonal(L, dim1=-2, dim2=-1)).sum(-1)
    return inv, logdet_inv, bon


def _stats_lot(dp, r):
    Nk, xbar = _moyennes(dp, r)
    Sk = _dispersion_lot(dp, r, xbar, Nk) / Nk[..., None, None]
    return Nk, xbar, Sk


def _etape_m_var_lot(Nk, xbar, Sk, pr: PrioriNW, cov_type):
    """Étape M variationnelle, équations (1.26) et (1.28), plus les variantes de covariance, en lot."""
    B, K, D = xbar.shape
    beta = pr.beta0 + Nk
    m = (pr.beta0 * pr.m0 + Nk[..., None] * xbar) / beta[..., None]
    d0 = xbar - pr.m0
    terme_prior = pr.beta0 * Nk / (pr.beta0 + Nk)
    sc = Nk[..., None, None] * Sk + terme_prior[..., None, None] * d0[..., :, None] * d0[..., None, :]
    P = {"alpha": pr.alpha0 + Nk, "beta": beta, "m": m, "cov_type": cov_type, "ok": torch.ones(B, dtype=torch.bool)}
    if cov_type == "full":
        P["nu"] = pr.nu0 + Nk
        P["Winv"] = pr.W0inv + sc
        P["W"], P["logdetW"], bon = _inverse_chol(P["Winv"])
        P["ok"] = bon.all(-1)
    elif cov_type == "tied":
        P["nu"] = (pr.nu0 + Nk.sum(1))[:, None].expand(B, K).clone()
        Winv = pr.W0inv + sc.sum(1)                                              # (B,D,D)
        W, ld, bon = _inverse_chol(Winv)
        P["Winv"] = Winv[:, None].expand(B, K, D, D).clone()
        P["W"] = W[:, None].expand(B, K, D, D).clone()
        P["logdetW"] = ld[:, None].expand(B, K).clone()
        P["ok"] = bon
    else:                                       # diag, spherical : priors Gamma sur les précisions
        a0 = pr.nu0 / 2.0
        b0 = 0.5 * torch.diagonal(pr.W0inv)
        sd = torch.diagonal(sc, dim1=-2, dim2=-1)
        if cov_type == "diag":
            P["a"] = (a0 + Nk / 2.0)[..., None].expand(B, K, D).clone()
            P["b"] = b0 + 0.5 * sd
        else:
            P["a"] = (a0 + D * Nk / 2.0)[..., None].expand(B, K, D).clone()
            P["b"] = (b0.mean() + 0.5 * sd.sum(-1))[..., None].expand(B, K, D).clone()
    return P


def _attendus_lot(P, D):
    """E[ln|Lambda_k|] (1.29) et E[Lambda_k] pour chaque composante, en lot."""
    if P["cov_type"] in ("full", "tied"):
        i = torch.arange(1, D + 1, dtype=torch.float64)
        logdetW = P["logdetW"] if "logdetW" in P else torch.logdet(P["W"])
        Elogdet = (torch.special.digamma((P["nu"][..., None] + 1 - i) / 2).sum(-1) + D * LN2 + logdetW)
        Elam = P["nu"][..., None, None] * P["W"]
    else:
        psi = torch.special.digamma(P["a"]) - torch.log(P["b"])
        Elogdet = psi.sum(-1)
        Elam = torch.diag_embed(P["a"] / P["b"])
    return Elogdet, Elam


def _etape_e_var_lot(dp, P):
    """Étape E variationnelle, équation (1.27), avec la forme quadratique (1.30), en lot : (r (B,N,K), log_norm (B,N))."""
    N, D = dp.N, dp.D
    B, K = P["alpha"].shape
    Elogpi = torch.special.digamma(P["alpha"]) - torch.special.digamma(P["alpha"].sum(-1, keepdim=True))
    Elogdet, Elam = _attendus_lot(P, D)
    r = dp.X.new_empty(B, N, K)
    ln = dp.X.new_empty(B, N)
    for sl in _tranches(B, K, N):
        quad = D / P["beta"][sl][..., None] + _forme_quadratique(dp, Elam[sl], P["m"][sl])
        log_rho = (Elogpi[sl][..., None] + 0.5 * Elogdet[sl][..., None] - 0.5 * D * LOG2PI - 0.5 * quad).transpose(1, 2)
        ln[sl] = torch.logsumexp(log_rho, dim=2)
        r[sl] = torch.exp(log_rho - ln[sl][..., None])
    return r, ln


def _elbo_lot(r, Nk, xbar, Sk, P, pr: PrioriNW):
    """
    ELBO du GMM bayésien (équation 1.31, détail dans Bishop 2006, éq. 10.70 à 10.77), en lot :
    un scalaire par relance. Disponible pour la covariance pleine.
    """
    B, K, D = xbar.shape
    alpha, beta, m, nu, W = P["alpha"], P["beta"], P["m"], P["nu"], P["W"]
    Elogpi = torch.special.digamma(alpha) - torch.special.digamma(alpha.sum(-1, keepdim=True))
    Elogdet, _ = _attendus_lot(P, D)
    dm = xbar - m
    t_trace = torch.einsum("bkde,bked->bk", Sk, W)
    t_quad = torch.einsum("bkd,bkde,bke->bk", dm, W, dm)
    e_x = 0.5 * (Nk * (Elogdet - D / beta - nu * t_trace - nu * t_quad - D * LOG2PI)).sum(-1)
    e_z = (Nk * Elogpi).sum(-1)
    a0 = pr.alpha0
    ln_c0 = math.lgamma(K * a0) - K * math.lgamma(a0)
    e_pi = ln_c0 + (a0 - 1.0) * Elogpi.sum(-1)
    W0 = torch.linalg.inv(pr.W0inv)
    d0 = m - pr.m0
    quad_m = torch.einsum("bkd,bkde,bke->bk", d0, W, d0)
    lnB0 = _ln_B(W0, torch.tensor(pr.nu0), D)
    e_muLam = (0.5 * (D * math.log(pr.beta0 / (2 * math.pi)) + Elogdet - D * pr.beta0 / beta
                      - pr.beta0 * nu * quad_m).sum(-1)
               + K * lnB0 + 0.5 * (pr.nu0 - D - 1) * Elogdet.sum(-1)
               - 0.5 * (nu * torch.einsum("de,bked->bk", pr.W0inv, W)).sum(-1))
    q_z = torch.xlogy(r, r).sum((1, 2))
    ln_c = torch.lgamma(alpha.sum(-1)) - torch.lgamma(alpha).sum(-1)
    q_pi = ((alpha - 1.0) * Elogpi).sum(-1) + ln_c
    H = -_ln_B_ld(P["logdetW"] if "logdetW" in P else torch.logdet(W), nu, D) - 0.5 * (nu - D - 1) * Elogdet + 0.5 * nu * D
    q_muLam = (0.5 * Elogdet + 0.5 * D * torch.log(beta / (2 * math.pi)) - 0.5 * D - H).sum(-1)
    return e_x + e_z + e_pi + e_muLam - q_z - q_pi - q_muLam


def _init_params_var_lot(dp, K, pr, cov_type, init, graines):
    """Paramètres variationnels initiaux pour chaque relance. `prior` : paramètres de 1.7.3.d ; `kmeans` : r0 durs, puis étape M."""
    N, D = dp.N, dp.D
    B = len(graines)
    if init == "kmeans":
        etiq, _, _ = kmeans_lot(dp.X, K, graines)
        r0 = torch.nn.functional.one_hot(etiq, K).to(dp.X.dtype)
        Nk, xbar, Sk = _stats_lot(dp, r0)
        return _etape_m_var_lot(Nk, xbar, Sk, pr, cov_type)
    xbar0 = dp.X.new_empty(B, K, D)
    for b, gr in enumerate(graines):
        xbar0[b] = dp.X[torch.randperm(N, generator=generateur(gr))[:K]]
    Nk0 = torch.full((B, K), N / K, dtype=dp.X.dtype)
    Sk0 = torch.eye(D, dtype=dp.X.dtype).expand(B, K, D, D).clone()
    P = _etape_m_var_lot(Nk0, xbar0, Sk0, pr, cov_type)
    P["m"] = xbar0                                                   # m_k = point de données tiré au hasard
    if cov_type in ("full", "tied"):
        W0, ld0, _ = _inverse_chol(pr.W0inv)
        P["Winv"] = pr.W0inv.expand(B, K, D, D).clone()             # W_k = W_0 (section 1.7.3.d)
        P["W"] = W0.expand(B, K, D, D).clone()
        P["logdetW"] = ld0.expand(B, K).clone()
    return P


def _vb_lot(dp, K, pr, cov_type, n_iter, tol, init, graines, instantane=None):
    """
    EM variationnel pour len(graines) relances en lot (pr en coordonnées centrées), critère d'arrêt commun :
    étape E, évaluation du critère (ELBO de (r, q(theta) courant) en covariance pleine ; somme des
    log-normalisations sinon), test d'arrêt, étape M. n_iter compte les étapes M.
    """
    params = _init_params_var_lot(dp, K, pr, cov_type, init, graines)

    def evaluer(sub):
        r, ln = _etape_e_var_lot(dp, sub)
        Nk, xbar, Sk = _stats_lot(dp, r)
        crit = _elbo_lot(r, Nk, xbar, Sk, sub, pr) if cov_type == "full" else ln.sum(1)
        return r, crit, sub["ok"] & torch.isfinite(crit), (Nk, xbar, Sk)

    def maj(sub, r, aux):
        return _etape_m_var_lot(aux[0], aux[1], aux[2], pr, cov_type)

    meta = {"algo": "vb", "K": K, "N": dp.N, "D": dp.D, "cov": cov_type, "init": init, "graines": list(graines),
            "tol": tol, "n_iter": n_iter, "alpha0": pr.alpha0, "beta0": pr.beta0, "nu0": pr.nu0}
    etat = _piloter_lot(params, len(graines), n_iter, tol, evaluer, maj, instantane, meta)
    bons = (~etat["echec"]).nonzero().flatten()
    if len(bons) == 0:
        raise EchecNumerique("VB : toutes les relances ont échoué (matrice non définie positive)")
    r = dp.X.new_zeros(len(graines), dp.N, K)
    r[bons], _ = _etape_e_var_lot(dp, _sel(params, bons))
    etat.update(params=params, r=r)
    return etat


def em_variationnel(X, Kmax, priori: PrioriNW | None = None, alpha0=None, cov_type="full",
                    n_iter=None, tol=None, init="kmeans", graine=0, n_init=1, instantane=None):
    """
    EM variationnel (champ moyen) pour un GMM bayésien (VB : theta aléatoire). Les n_init relances
    (graines graine, graine+1, ...) sont ajustées en lot ; on garde le plus grand critère.

    Priors par défaut : priors empiriques (beta0 = 1, W0^-1 = covariance empirique). Les priors diffus (beta0 = 1e-3, W0 = I)
    s'obtiennent avec priori=priori_diffus(X, alpha0).

    Critère d'arrêt : le même que l'EM (relatif, total, plafond commun). En covariance pleine
    le critère est l'ELBO (clé critere_nom = "elbo"). Pour tied/diag/spherical, l'ELBO n'est
    pas dérivé : le critère est la somme des log-normalisations de l'étape E (ELBO sans le
    terme KL sur theta), non nécessairement monotone (critere_nom = "approximation_log_norm").

    Retourne un dictionnaire avec les poids E[pi_k], les centres m_k, les covariances
    (E[Lambda_k])^-1, les responsabilités, N_k, l'historique du critère, la liste des
    composantes actives (N_k >= 1, section 1.7.4), les indicateurs de dégénérescence et `relances`.
    """
    tol, n_iter, _ = _defauts(tol, n_iter, 0.0)
    t0 = time.perf_counter()
    pr = priori if priori is not None else priori_empirique(X, alpha0, Kmax)
    if alpha0 is not None and priori is not None:
        pr = PrioriNW(alpha0, pr.m0, pr.beta0, pr.W0inv, pr.nu0)
    graines = [graine + s for s in range(n_init)]
    dp = _Prep(X)
    prc = _priori_centre(pr, dp.c)
    N, D = dp.N, dp.D
    lot = _vb_lot(dp, Kmax, prc, cov_type, n_iter, tol, init, graines, instantane)
    B = len(graines)
    comp = lot["compte"]
    crit = torch.stack([lot["hist"][comp[b] - 1, b] if comp[b] > 0 else torch.tensor(float("nan")) for b in range(B)])
    score = crit.clone()
    score[lot["echec"]] = -float("inf")
    b = int(torch.argmax(score))
    P = _sel_un(lot["params"], b)
    P["m"] = P["m"] + dp.c                                            # retour aux coordonnées d'origine
    r = lot["r"][b]
    alpha = P["alpha"]
    if cov_type in ("full", "tied"):
        cov = P["Winv"] / P["nu"][:, None, None]
    else:
        cov = torch.diag_embed(P["b"] / P["a"])
    Nk = r.sum(0)
    petite, plancher = indicateurs_degenerescence(cov, Nk, D, 0.0)
    temps = time.perf_counter() - t0
    hist = lot["hist"][:comp[b], b].tolist()
    return {"P": P, "r": r, "crit": float(crit[b]), "hist": hist, "n_iter": int(lot["n_m"][b]),
            "converge": bool(lot["converge"][b]), "pi": alpha / alpha.sum(), "alpha": alpha, "m": P["m"], "Nk": Nk,
            "cov": cov, "labels": r.argmax(1), "actives": (Nk >= 1.0).nonzero().flatten(),
            "n_actives": int((Nk >= 1.0).sum()),
            "elbo_hist": hist if cov_type == "full" else None, "elbo": float(crit[b]) if cov_type == "full" else None,
            "critere_nom": "elbo" if cov_type == "full" else "approximation_log_norm",
            "petite_composante": bool(petite.any()), "plancher_regularisation": bool(plancher.any()),
            "degenere": bool((petite | plancher).any()), "degenere_composantes": petite | plancher,
            "temps": temps, "temps_par_iter": temps / max(lot["passages"], 1), "priori": pr, "cov_type": cov_type,
            "relances": {"critere": crit.tolist(), "n_iter": lot["n_m"].tolist(), "converge": lot["converge"].tolist(),
                         "echec": lot["echec"].tolist(), "meilleure": b, "graines": graines}}


def _sel_un(P: dict, b: int) -> dict:
    """Paramètres variationnels d'une seule relance (sans dimension de lot)."""
    return {k: (v[b] if torch.is_tensor(v) else v) for k, v in P.items()}


def _lot_un(P: dict) -> dict:
    return {k: (v[None] if torch.is_tensor(v) else v) for k, v in P.items()}


# --- versions « une relance » conservées pour la SVI et les tests (coordonnées d'origine) ---

def _stats(X, r):
    dp = _Prep(X)
    Nk, xbar, Sk = _stats_lot(dp, r[None])
    return Nk[0], xbar[0] + dp.c, Sk[0]


def _etape_m_var(Nk, xbar, Sk, pr: PrioriNW, cov_type):
    return _sel_un(_etape_m_var_lot(Nk[None], xbar[None], Sk[None], pr, cov_type), 0)


def _attendus(P, D):
    Elogdet, Elam = _attendus_lot(_lot_un(P), D)
    return Elogdet[0], Elam[0]


def _etape_e_var(X, P):
    dp = _Prep(X)
    Pc = dict(P)
    Pc["m"] = P["m"] - dp.c
    r, ln = _etape_e_var_lot(dp, _lot_un(Pc))
    return r[0], ln[0]


def elbo_gmm_bayesien(r, Nk, xbar, Sk, P, pr: PrioriNW):
    """ELBO du GMM bayésien (équation 1.31) pour un seul jeu de paramètres variationnels (covariance pleine)."""
    return float(_elbo_lot(r[None], Nk[None], xbar[None], Sk[None], _lot_un(P), pr)[0])


def _init_params_var(X, K, pr, cov_type, init, graine):
    """Retourne (P, None) pour une relance (utilisé par la SVI), en coordonnées d'origine."""
    dp = _Prep(X)
    P = _sel_un(_init_params_var_lot(dp, K, _priori_centre(pr, dp.c), cov_type, init, [graine]), 0)
    P["m"] = P["m"] + dp.c
    return P, None


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


def baum_welch(sequences, S, emission="discrete", V=None, n_iter=None, tol=None, graine=0):
    """
    Baum-Welch : EM classique où l'étape E est forward-backward.
    emission = "discrete" (V symboles) ou "gauss" (observations réelles scalaires).
    Étape M : A_ij = sum xi / sum gamma, B_i(v) = sum_{o_t = v} gamma / sum gamma (discret),
              mu_i, sigma_i^2 = moyennes pondérées par gamma (gaussien), variance planchée à reg_covariance
              (même garde-fou que l'EM du mélange).
    Critère d'arrêt commun (tolérance relative sur la log-vraisemblance totale, plafond d'étapes M).
    """
    tol, n_iter, reg = _defauts(tol, n_iter, None)
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
    hist, n_m, converge = [], 0, False
    while True:
        gam_l, xi_l, ll = [], [], 0.0
        for obs in sequences:
            if emission == "discrete":
                logB = torch.log(B[:, obs].T)
            else:
                logB = -0.5 * (LOG2PI + torch.log(var)[None] + (obs[:, None] - mu[None]) ** 2 / var[None])
            gamma, xi, l = _fb_normalise(A, logB, pi0)
            gam_l.append(gamma); xi_l.append(xi); ll += l
        hist.append(ll)
        if len(hist) > 1 and a_converge(hist[-2], hist[-1], tol):
            converge = True
            break
        if n_m >= n_iter:
            break
        n_m += 1
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
                      for o, g_ in zip(sequences, gam_l)) / tot + reg
    out = {"A": A, "pi0": pi0, "loglik": hist[-1], "ll_hist": hist, "n_iter": n_m, "converge": converge}
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

def lda_variationnel(comptes: Tensor, K: int, alpha=None, lissage=None, n_iter=None, tol=None, graine=0):
    """
    LDA de Blei, Ng et Jordan (2003) par EM variationnel (theta_d aléatoire, beta ponctuel).

    comptes : (D, V) nombres d'occurrences de chaque mot dans chaque document.
    Étape E (par document) : point fixe phi_{vk} prop. à beta_{kv} exp(E[log theta_k])   (éq. 3.2)
                             gamma_k = alpha + sum_v comptes_v phi_{vk},
                             jusqu'à variation relative max de gamma <= tol (même tolérance que le critère commun).
    Critère : borne L(gamma, phi ; alpha, beta) + lissage * somme log beta, c'est-à-dire l'objectif exact
              maximisé quand l'étape M ajoute le pseudo-compte `lissage` (mode a posteriori de beta sous un
              Dirichlet(1 + lissage)) : il est donc croissant. Le terme ln Gamma(K alpha) - K ln Gamma(alpha)
              de E[log p(theta_d | alpha)] est compté une fois PAR DOCUMENT.
    Étape M : beta_{kv} proportionnel à sum_d comptes_{dv} phi_{dvk} + lissage.
    Boucle : étape E, critère, test d'arrêt commun, étape M ; n_iter compte les étapes M.
    """
    hyp = PARAM.valeur("lda_hyper")
    alpha = float(hyp["alpha"]) if alpha is None else alpha
    lissage = float(hyp["lissage"]) if lissage is None else lissage
    tol, n_iter, _ = _defauts(tol, n_iter, 0.0)
    g = generateur(graine)
    Dn, V = comptes.shape
    beta = torch.rand(K, V, generator=g) + 1.0
    beta = beta / beta.sum(1, keepdim=True)
    Nd = comptes.sum(1)
    gamma = alpha + Nd[:, None] / K
    digam = torch.special.digamma
    c = comptes[:, :, None]
    bornes, converge, n_m = [], False, 0
    const_doc = math.lgamma(K * alpha) - K * math.lgamma(alpha)
    while True:
        logbeta = torch.log(beta)
        for _ in range(n_iter):
            Elog = digam(gamma) - digam(gamma.sum(1, keepdim=True))                # (D,K)
            phi = torch.softmax(Elog[:, None, :] + logbeta.T[None, :, :], dim=2)   # (D,V,K)
            gamma_new = alpha + (c * phi).sum(1)
            fini = ((gamma_new - gamma).abs() <= tol * gamma.abs().clamp(min=1.0)).all()
            gamma = gamma_new
            if bool(fini):
                break
        Elog = digam(gamma) - digam(gamma.sum(1, keepdim=True))
        phi = torch.softmax(Elog[:, None, :] + logbeta.T[None, :, :], dim=2)
        L = (Dn * const_doc
             + ((alpha - 1) * Elog).sum()
             + (c * phi * Elog[:, None, :]).sum()
             + (c * phi * logbeta.T[None]).sum()
             - (torch.lgamma(gamma.sum(1)) - torch.lgamma(gamma).sum(1)).sum()
             - ((gamma - 1) * Elog).sum()
             - (c * torch.xlogy(phi, phi)).sum()
             + lissage * logbeta.sum())
        bornes.append(float(L))
        if len(bornes) > 1 and a_converge(bornes[-2], bornes[-1], tol):
            converge = True
            break
        if n_m >= n_iter:
            break
        beta = (c * phi).sum(0).T + lissage
        beta = beta / beta.sum(1, keepdim=True)
        n_m += 1
    theta = gamma / gamma.sum(1, keepdim=True)
    return {"beta": beta, "gamma": gamma, "theta": theta, "bornes": bornes, "n_iter": n_m,
            "converge": converge, "alpha": alpha, "lissage": lissage}


# ==============================================================================
# pLSA PAR EM (Hofmann, 1999) : comparateur « EM classique » de la LDA
# ==============================================================================

def plsa_em(comptes: Tensor, K: int, n_iter=None, tol=None, graine=0, tempering=1.0):
    """
    pLSA par EM : p(w | d) = somme_k theta_dk phi_kw, estimé par maximum de vraisemblance,
    sans prior (theta ponctuel, phi ponctuel). Même critère d'arrêt que le reste du module
    (log-vraisemblance totale, tolérance relative, plafond d'étapes M).

    comptes : (D, V). tempering = beta de l'EM tempéré (Hofmann 2001) : l'étape E élève
    p(z | d, w) à la puissance beta ; beta = 1 est l'EM standard (log-vraisemblance monotone),
    beta < 1 régularise (la monotonie n'est alors plus garantie).
    """
    tol, n_iter, _ = _defauts(tol, n_iter, 0.0)
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
