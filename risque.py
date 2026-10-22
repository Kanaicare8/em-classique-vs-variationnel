"""
================================================================================
OUTILS DE GESTION DU RISQUE POUR LES MÉLANGES GAUSSIENS UNIVARIÉS (PyTorch pur)
Kana Tiodong Icare Brichel, Master 2 SDIA, ENSPD, Université de Douala
================================================================================

    cdf_melange_gauss()                 fonction de répartition d'un mélange gaussien
    quantile_melange_gauss()            quantile (value-at-risk) par dichotomie
    es_melange_gauss()                  perte moyenne au-delà du quantile (Expected Shortfall)
    echantillonner_posterieur_gmm_1d()  tirages de (pi, mu, sigma) sous q(pi) q(mu, Lambda)  (1.23)
    log_predictive_variationnel()       log densité prédictive a posteriori, mélange de lois de Student
                                        (Bishop 2006, éq. 10.81 et 10.82)
    kupiec()                            test de couverture inconditionnelle de Kupiec (1995)
    christoffersen()                    indépendance et couverture conditionnelle (Christoffersen, 1998)
    diebold_mariano()                   comparaison de prévisions (Diebold et Mariano, 1995)
    acerbi_szekely()                    backtest de l'Expected Shortfall, Z1 et Z2 (Acerbi et Szekely, 2014)
    var_es_student_melange()            VaR et ES de la prédictive (mélange de Student), par simulation
"""

from __future__ import annotations

import math

import torch
from torch import Tensor
from torch.distributions import Gamma

from algorithmes import generateur

SQRT2 = math.sqrt(2.0)
SQRT2PI = math.sqrt(2.0 * math.pi)


def _en_2d(*tenseurs):
    return [t if t.dim() == 2 else t[None] for t in tenseurs]


def cdf_melange_gauss(x: Tensor, pi: Tensor, mu: Tensor, sigma: Tensor) -> Tensor:
    """F(x) = somme_k pi_k Phi((x - mu_k) / sigma_k). x : (S,) ; pi, mu, sigma : (S, K) ou (K,)."""
    pi, mu, sigma = _en_2d(pi, mu, sigma)
    z = (x.reshape(-1, 1) - mu) / sigma
    return (pi * 0.5 * (1.0 + torch.erf(z / SQRT2))).sum(-1)


def quantile_melange_gauss(p: float, pi: Tensor, mu: Tensor, sigma: Tensor, n_iter: int = 100) -> Tensor:
    """Quantile d'ordre p de chaque mélange (une ligne par jeu de paramètres), par dichotomie."""
    pi, mu, sigma = _en_2d(pi, mu, sigma)
    bas = (mu - 12.0 * sigma).min(1).values
    haut = (mu + 12.0 * sigma).max(1).values
    for _ in range(n_iter):
        milieu = 0.5 * (bas + haut)
        trop_bas = cdf_melange_gauss(milieu, pi, mu, sigma) < p
        bas = torch.where(trop_bas, milieu, bas)
        haut = torch.where(trop_bas, haut, milieu)
    return 0.5 * (bas + haut)


def es_melange_gauss(p: float, q: Tensor, pi: Tensor, mu: Tensor, sigma: Tensor) -> Tensor:
    """
    ES_p = E[X | X <= q_p] = (1 / p) somme_k pi_k [mu_k Phi(z_k) - sigma_k phi(z_k)], z_k = (q - mu_k) / sigma_k.
    Valeur négative (perte exprimée comme un rendement).
    """
    pi, mu, sigma = _en_2d(pi, mu, sigma)
    z = (q.reshape(-1, 1) - mu) / sigma
    Phi = 0.5 * (1.0 + torch.erf(z / SQRT2))
    phi = torch.exp(-0.5 * z ** 2) / SQRT2PI
    return (pi * (mu * Phi - sigma * phi)).sum(-1) / p


def echantillonner_posterieur_gmm_1d(P: dict, n: int, graine: int = 0):
    """
    Tire n jeux (pi, mu, sigma) de la loi variationnelle q (D = 1) :
        pi ~ Dirichlet(alpha), Lambda_k ~ Wishart(W_k, nu_k) = Gamma(forme nu_k / 2, taux 1 / (2 W_k)),
        mu_k | Lambda_k ~ Normale(m_k, 1 / (beta_k Lambda_k)), sigma_k = Lambda_k^(-1/2).
    P est le dictionnaire de paramètres variationnels renvoyé par em_variationnel() (clé "P").
    """
    g = generateur(graine)
    K = P["alpha"].shape[0]
    # torch.distributions.Gamma n'accepte pas de generator : on fixe la graine globale dans
    # un contexte qui restaure l'état du générateur à la sortie (reproductible, sans effet de bord).
    with torch.random.fork_rng():
        torch.manual_seed(int(graine))
        gam = Gamma(P["alpha"].expand(n, K).contiguous(), torch.ones(n, K)).sample()
        pi = gam / gam.sum(1, keepdim=True)
        W = P["W"].reshape(K)
        lam = Gamma((P["nu"] / 2.0).expand(n, K).contiguous(),
                    (1.0 / (2.0 * W))[None, :].expand(n, K).contiguous()).sample()
    eps = torch.randn(n, K, generator=g)
    mu = P["m"].reshape(K)[None, :] + eps / torch.sqrt(P["beta"][None, :] * lam)
    return pi, mu, 1.0 / torch.sqrt(lam)


def log_predictive_variationnel(X: Tensor, P: dict) -> Tensor:
    """
    log p(x | X_train) = log somme_k E[pi_k] St(x | m_k, L_k, nu_k + 1 - D),
    L_k = ((nu_k + 1 - D) beta_k / (1 + beta_k)) W_k  (Bishop 2006, éq. 10.81 et 10.82).
    """
    N, D = X.shape
    Epi = P["alpha"] / P["alpha"].sum()
    dof = P["nu"] + 1.0 - D
    L = (dof * P["beta"] / (1.0 + P["beta"]))[:, None, None] * P["W"]
    diff = X[None, :, :] - P["m"][:, None, :]
    maha = torch.einsum("knd,kde,kne->kn", diff, L, diff)
    cste = (torch.lgamma((dof + D) / 2.0) - torch.lgamma(dof / 2.0) + 0.5 * torch.logdet(L)
            - 0.5 * D * torch.log(dof * math.pi))
    log_st = cste[:, None] - 0.5 * (dof + D)[:, None] * torch.log1p(maha / dof[:, None])
    return torch.logsumexp(torch.log(Epi)[:, None] + log_st, dim=0)


def log_densite_gauss_1d(x: Tensor, pi: Tensor, mu: Tensor, sigma: Tensor) -> Tensor:
    """log de la densité d'un mélange gaussien univarié, évaluée en chaque x."""
    z = (x.reshape(-1, 1) - mu[None, :]) / sigma[None, :]
    lg = torch.log(pi)[None, :] - torch.log(sigma)[None, :] - 0.5 * z ** 2 - math.log(SQRT2PI)
    return torch.logsumexp(lg, dim=1)


def kupiec(exceptions: int, T: int, p: float):
    """
    Test de Kupiec : sous H0 le taux d'exceptions vaut p ; LR = -2 ln [L(p) / L(x/T)] suit un khi-deux à
    1 degré de liberté. La probabilité critique vaut erfc(sqrt(LR / 2)).
    Retourne (statistique LR, probabilité critique).
    """
    x = exceptions
    ph = x / T

    def ll(q):
        terme = (T - x) * math.log(1.0 - q)
        return terme + (x * math.log(q) if x > 0 else 0.0)

    lr = max(-2.0 * (ll(p) - ll(ph)), 0.0)
    return lr, math.erfc(math.sqrt(lr / 2.0))


def _khi2_sf(x: float, ddl: int) -> float:
    """Probabilité critique d'un khi-deux à 1 ou 2 degrés de liberté."""
    if ddl == 1:
        return math.erfc(math.sqrt(x / 2.0))
    if ddl == 2:
        return math.exp(-x / 2.0)
    raise ValueError("ddl 1 ou 2")


def comptes_transitions(I) -> tuple:
    """(n00, n01, n10, n11) : nombres de transitions de la suite d'exceptions I (0/1)."""
    I = [int(v) for v in I]
    n = [[0, 0], [0, 0]]
    for a, b in zip(I[:-1], I[1:]):
        n[a][b] += 1
    return n[0][0], n[0][1], n[1][0], n[1][1]


def _xlogy(x: float, y: float) -> float:
    return 0.0 if x == 0 else x * math.log(y)


def lr_independance(n00: int, n01: int, n10: int, n11: int) -> float:
    """LR_ind = -2 ln [L(pi) / L(pi01, pi11)], khi-deux à 1 ddl sous H0 (Christoffersen, 1998)."""
    n0, n1 = n00 + n01, n10 + n11
    pi01 = n01 / n0 if n0 else 0.0
    pi11 = n11 / n1 if n1 else 0.0
    pi = (n01 + n11) / (n0 + n1)
    ll_h1 = (_xlogy(n00, 1 - pi01) + _xlogy(n01, pi01) + _xlogy(n10, 1 - pi11) + _xlogy(n11, pi11))
    ll_h0 = _xlogy(n00 + n10, 1 - pi) + _xlogy(n01 + n11, pi)
    return max(-2.0 * (ll_h0 - ll_h1), 0.0)


def christoffersen(I, p: float) -> dict:
    """
    Tests de Christoffersen (1998) sur la suite d'exceptions I (1 = rendement sous la VaR) :
    LR_uc (Kupiec), LR_ind (indépendance, khi-deux à 1 ddl) et LR_cc = LR_uc + LR_ind
    (couverture conditionnelle, khi-deux à 2 ddl).
    """
    I = [int(v) for v in I]
    lr_uc, p_uc = kupiec(sum(I), len(I), p)
    lr_ind = lr_independance(*comptes_transitions(I))
    lr_cc = lr_uc + lr_ind
    return {"lr_uc": lr_uc, "p_uc": p_uc, "lr_ind": lr_ind, "p_ind": _khi2_sf(lr_ind, 1),
            "lr_cc": lr_cc, "p_cc": _khi2_sf(lr_cc, 2)}


def diebold_mariano(d, h: int = 1, harvey: bool = True) -> tuple:
    """
    Test de Diebold-Mariano sur la suite de différentielles de perte d_t = L(A)_t - L(B)_t.
    Variance de long terme de Newey-West à noyau de Bartlett, h - 1 retards ; correction de
    petit échantillon de Harvey, Leybourne et Newbold (1997) si harvey. Loi normale (p bilatérale).
    Retourne (statistique, probabilité critique). Statistique > 0 : B meilleur que A.
    """
    d = torch.as_tensor(d, dtype=torch.float64)
    T = len(d)
    dbar = d.mean()
    e = d - dbar
    var = (e @ e) / T
    for lag in range(1, h):
        gam = (e[lag:] @ e[:-lag]) / T
        var = var + 2.0 * (1.0 - lag / h) * gam
    stat = float(dbar / torch.sqrt(var / T))
    if harvey:
        stat *= math.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
    return stat, math.erfc(abs(stat) / SQRT2)


def acerbi_szekely(x: Tensor, var: Tensor, es: Tensor, p: float) -> dict:
    """
    Statistiques d'Acerbi et Szekely (2014) pour des rendements x et des VaR / ES prévues
    var, es (valeurs négatives, convention rendement). I_t = 1{x_t < var_t}.
      Z1 = moyenne sur les exceptions de x_t / es_t, moins 1  (calibration de la queue)
      Z2 = (1/T) somme_t x_t I_t / (p es_t), moins 1           (calibration globale)
    (x_t / es_t > 0 car rendements et ES sont négatifs.) Espérance nulle sous H0 ; une valeur
    POSITIVE signale un risque sous-estimé (pertes réalisées dans la queue plus grandes que prévu).
    """
    I = (x < var).to(x.dtype)
    nb = float(I.sum())
    z1 = float((x * I / es).sum() / nb - 1.0) if nb > 0 else float("nan")
    z2 = float((x * I / (p * es)).mean() - 1.0)
    return {"z1": z1, "z2": z2, "n_exceptions": int(nb)}


def pvalue_z2_monte_carlo(z2_obs: float, tirer, var: Tensor, es: Tensor, p: float,
                          n_sim: int = 2000, graine: int = 0) -> float:
    """
    Probabilité critique unilatérale de Z2 par simulation sous H0 (Z2 grand = risque sous-estimé) : `tirer(t, g)` renvoie un
    rendement tiré de la prédictive du jour t. p = P(Z2_sim >= Z2_obs).
    """
    g = generateur(graine)
    T = len(var)
    z2 = torch.empty(n_sim)
    for s in range(n_sim):
        x = torch.stack([tirer(t, g) for t in range(T)])
        z2[s] = acerbi_szekely(x, var, es, p)["z2"]
    return float((z2 >= z2_obs).to(torch.float64).mean())


def var_es_student_melange(P: dict, p: float, n: int = 200000, graine: int = 0):
    """
    VaR et ES d'ordre p de la loi prédictive du VB (D = 1), mélange de lois de Student
    (Bishop 2006, éq. 10.81 et 10.82), évalués par simulation : composante k tirée avec
    probabilité E[pi_k], x = m_k + t_dof / sqrt(L_k), L_k = (dof beta / (1 + beta)) W_k,
    dof = nu_k. Le quantile et la moyenne de queue sont ceux de l'échantillon simulé
    (erreur de Monte Carlo décroissant en 1 / sqrt(n p)). Retourne (VaR, ES), négatifs.
    """
    with torch.random.fork_rng():
        torch.manual_seed(int(graine))
        K = P["alpha"].shape[0]
        Epi = P["alpha"] / P["alpha"].sum()
        k = torch.multinomial(Epi, n, replacement=True)
        dof = (P["nu"] + 1.0 - 1.0)[k]
        L = ((P["nu"]) * P["beta"] / (1.0 + P["beta"]) * P["W"].reshape(K))[k]
        z = torch.randn(n)
        chi2 = Gamma(dof / 2.0, torch.full_like(dof, 0.5)).sample()
        x = P["m"].reshape(K)[k] + z * torch.sqrt(dof / chi2) / torch.sqrt(L)
    q = torch.quantile(x, p)
    return float(q), float(x[x <= q].mean())
