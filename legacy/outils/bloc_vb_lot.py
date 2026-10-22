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


def _stats_lot(X, r):
    Nk = r.sum(1) + 1e-10
    xbar = torch.einsum("bnk,nd->bkd", r, X) / Nk[..., None]
    Sk = _dispersion_lot(X, r, xbar) / Nk[..., None, None]
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


def _etape_e_var_lot(X, P):
    """Étape E variationnelle, équation (1.27), avec la forme quadratique (1.30), en lot : (r (B,N,K), log_norm (B,N))."""
    N, D = X.shape
    B, K = P["alpha"].shape
    Elogpi = torch.special.digamma(P["alpha"]) - torch.special.digamma(P["alpha"].sum(-1, keepdim=True))
    Elogdet, Elam = _attendus_lot(P, D)
    r = X.new_empty(B, N, K)
    ln = X.new_empty(B, N)
    for sl in _tranches(B, K, N, D):
        diff = X[None, None] - P["m"][sl][:, :, None, :]                       # (b,K,N,D)
        qd = ((diff @ Elam[sl]) * diff).sum(-1)                                 # (b,K,N)
        quad = D / P["beta"][sl][..., None] + qd
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


def _init_params_var_lot(X, K, pr, cov_type, init, graines):
    """Paramètres variationnels initiaux pour chaque relance. `prior` : paramètres de 1.7.3.d ; `kmeans` : r0 durs, puis étape M."""
    N, D = X.shape
    B = len(graines)
    if init == "kmeans":
        etiq, _ = kmeans_lot(X, K, graines)
        r0 = torch.nn.functional.one_hot(etiq, K).to(X.dtype)
        Nk, xbar, Sk = _stats_lot(X, r0)
        return _etape_m_var_lot(Nk, xbar, Sk, pr, cov_type)
    xbar0 = X.new_empty(B, K, D)
    for b, gr in enumerate(graines):
        xbar0[b] = X[torch.randperm(N, generator=generateur(gr))[:K]]
    Nk0 = torch.full((B, K), N / K, dtype=X.dtype)
    Sk0 = torch.eye(D, dtype=X.dtype).expand(B, K, D, D).clone()
    P = _etape_m_var_lot(Nk0, xbar0, Sk0, pr, cov_type)
    P["m"] = xbar0                                                   # m_k = point de données tiré au hasard
    if cov_type in ("full", "tied"):
        W0, ld0, _ = _inverse_chol(pr.W0inv)
        P["Winv"] = pr.W0inv.expand(B, K, D, D).clone()             # W_k = W_0 (section 1.7.3.d)
        P["W"] = W0.expand(B, K, D, D).clone()
        P["logdetW"] = ld0.expand(B, K).clone()
    return P


def _vb_lot(X, K, pr, cov_type, n_iter, tol, init, graines, instantane=None):
    """
    EM variationnel pour len(graines) relances en lot, critère d'arrêt commun : étape E, évaluation du
    critère (ELBO de (r, q(theta) courant) en covariance pleine ; somme des log-normalisations sinon),
    test d'arrêt, étape M. n_iter compte les étapes M.
    """
    N, D = X.shape
    params = _init_params_var_lot(X, K, pr, cov_type, init, graines)

    def evaluer(sub):
        r, ln = _etape_e_var_lot(X, sub)
        Nk, xbar, Sk = _stats_lot(X, r)
        crit = _elbo_lot(r, Nk, xbar, Sk, sub, pr) if cov_type == "full" else ln.sum(1)
        return r, crit, sub["ok"] & torch.isfinite(crit), (Nk, xbar, Sk)

    def maj(sub, r, aux):
        return _etape_m_var_lot(aux[0], aux[1], aux[2], pr, cov_type)

    meta = {"algo": "vb", "K": K, "N": N, "D": D, "cov": cov_type, "init": init, "graines": list(graines),
            "tol": tol, "n_iter": n_iter, "alpha0": pr.alpha0, "beta0": pr.beta0, "nu0": pr.nu0}
    etat = _piloter_lot(params, len(graines), n_iter, tol, evaluer, maj, instantane, meta)
    bons = (~etat["echec"]).nonzero().flatten()
    if len(bons) == 0:
        raise EchecNumerique("VB : toutes les relances ont échoué (matrice non définie positive)")
    r = X.new_zeros(len(graines), N, K)
    r[bons], _ = _etape_e_var_lot(X, _sel(params, bons))
    etat.update(params=params, r=r)
    return etat


def em_variationnel(X, Kmax, priori: PrioriNW | None = None, alpha0=None, cov_type="full",
                    n_iter=N_ITER_MAX, tol=TOL_REL, init="kmeans", graine=0, n_init=1, instantane=None):
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
    composantes actives (N_k >= 1, section 1.7.4), l'indicateur degenere et `relances`.
    """
    t0 = time.perf_counter()
    pr = priori if priori is not None else priori_empirique(X, alpha0, Kmax)
    if alpha0 is not None and priori is not None:
        pr = PrioriNW(alpha0, pr.m0, pr.beta0, pr.W0inv, pr.nu0)
    graines = [graine + s for s in range(n_init)]
    N, D = X.shape
    lot = _vb_lot(X, Kmax, pr, cov_type, n_iter, tol, init, graines, instantane)
    B = len(graines)
    comp = lot["compte"]
    crit = torch.stack([lot["hist"][comp[b] - 1, b] if comp[b] > 0 else torch.tensor(float("nan")) for b in range(B)])
    score = crit.clone()
    score[lot["echec"]] = -float("inf")
    b = int(torch.argmax(score))
    P = _sel_un(lot["params"], b)
    r = lot["r"][b]
    alpha = P["alpha"]
    if cov_type in ("full", "tied"):
        cov = P["Winv"] / P["nu"][:, None, None]
    else:
        cov = torch.diag_embed(P["b"] / P["a"])
    Nk = r.sum(0)
    masque = indicateur_degenerescence(cov, Nk, D)
    temps = time.perf_counter() - t0
    hist = lot["hist"][:comp[b], b].tolist()
    return {"P": P, "r": r, "crit": float(crit[b]), "hist": hist, "n_iter": int(lot["n_m"][b]),
            "converge": bool(lot["converge"][b]), "pi": alpha / alpha.sum(), "alpha": alpha, "m": P["m"], "Nk": Nk,
            "cov": cov, "labels": r.argmax(1), "actives": (Nk >= 1.0).nonzero().flatten(),
            "n_actives": int((Nk >= 1.0).sum()),
            "elbo_hist": hist if cov_type == "full" else None, "elbo": float(crit[b]) if cov_type == "full" else None,
            "critere_nom": "elbo" if cov_type == "full" else "approximation_log_norm",
            "degenere": bool(masque.any()), "degenere_composantes": masque,
            "temps": temps, "temps_par_iter": temps / max(lot["passages"], 1), "priori": pr, "cov_type": cov_type,
            "relances": {"critere": crit.tolist(), "n_iter": lot["n_m"].tolist(), "converge": lot["converge"].tolist(),
                         "echec": lot["echec"].tolist(), "meilleure": b, "graines": graines}}


def _sel_un(P: dict, b: int) -> dict:
    """Paramètres variationnels d'une seule relance (sans dimension de lot)."""
    return {k: (v[b] if torch.is_tensor(v) else v) for k, v in P.items()}


# --- versions « une relance » conservées pour la SVI et les tests ---

def _stats(X, r):
    Nk, xbar, Sk = _stats_lot(X, r[None])
    return Nk[0], xbar[0], Sk[0]


def _etape_m_var(Nk, xbar, Sk, pr: PrioriNW, cov_type):
    P = _etape_m_var_lot(Nk[None], xbar[None], Sk[None], pr, cov_type)
    return _sel_un(P, 0)


def _attendus(P, D):
    Elogdet, Elam = _attendus_lot({k: (v[None] if torch.is_tensor(v) else v) for k, v in P.items()}, D)
    return Elogdet[0], Elam[0]


def _etape_e_var(X, P):
    r, ln = _etape_e_var_lot(X, {k: (v[None] if torch.is_tensor(v) else v) for k, v in P.items()})
    return r[0], ln[0]


def elbo_gmm_bayesien(r, Nk, xbar, Sk, P, pr: PrioriNW):
    """ELBO du GMM bayésien (équation 1.31) pour un seul jeu de paramètres variationnels (covariance pleine)."""
    Pb = {k: (v[None] if torch.is_tensor(v) else v) for k, v in P.items()}
    return float(_elbo_lot(r[None], Nk[None], xbar[None], Sk[None], Pb, pr)[0])


def _init_params_var(X, K, pr, cov_type, init, graine):
    """Retourne (P, None) pour une relance (utilisé par la SVI)."""
    return _sel_un(_init_params_var_lot(X, K, pr, cov_type, init, [graine]), 0), None
