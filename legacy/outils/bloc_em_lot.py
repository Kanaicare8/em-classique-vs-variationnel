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


ELEMENTS_LOT_MAX = 30_000_000        # taille maximale (éléments) du tenseur (b, K, N, D) traité d'un coup


def _tranches(B: int, K: int, N: int, D: int):
    pas = max(1, int(ELEMENTS_LOT_MAX // max(K * N * D, 1)))
    return [slice(i, min(i + pas, B)) for i in range(0, B, pas)]


def _sel(p: dict, idx) -> dict:
    """Sous-lot d'un dictionnaire de tenseurs indexés par la relance (les valeurs non tensorielles sont conservées)."""
    return {k: (v[idx] if torch.is_tensor(v) else v) for k, v in p.items()}


def _aff(p: dict, idx, sous: dict) -> None:
    for k, v in sous.items():
        if torch.is_tensor(v):
            p[k][idx] = v


def kmeans_lot(X: Tensor, K: int, graines, n_iter: int = 100):
    """
    K-means (Lloyd) avec initialisation k-means++, une graine par relance, itérations de Lloyd en lot.
    Retourne (étiquettes (B,N), centres (B,K,D)).
    """
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
    for _ in range(n_iter):
        idx = actif.nonzero().flatten()
        if len(idx) == 0:
            break
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
    return etiq, centres


def kmeans(X: Tensor, K: int, graine: int = 0, n_iter: int = 100):
    """K-means (Lloyd) avec initialisation k-means++. Retourne (étiquettes, centres)."""
    etiq, centres = kmeans_lot(X, K, [graine], n_iter)
    return etiq[0], centres[0]


def _dispersion_lot(X: Tensor, r: Tensor, centre: Tensor) -> Tensor:
    """S_k = somme_n r_nk (x_n - c_k)(x_n - c_k)^T pour toutes les relances : (B,K,D,D)."""
    B, N, K = r.shape
    D = X.shape[1]
    out = X.new_empty(B, K, D, D)
    for sl in _tranches(B, K, N, D):
        diff = X[None, None] - centre[sl][:, :, None, :]                       # (b,K,N,D)
        w = r[sl].transpose(1, 2)[..., None]                                    # (b,K,N,1)
        out[sl] = (diff * w).transpose(-1, -2) @ diff
    return out


def _log_gauss_lot(X: Tensor, mu: Tensor, cov: Tensor):
    """log N(x_n | mu_bk, cov_bk) via Cholesky : (B,K,N) et masque `ok` (B,) des relances factorisables."""
    D = X.shape[1]
    L, info = torch.linalg.cholesky_ex(cov)
    bon = info == 0
    L = torch.where(bon[..., None, None], L, torch.eye(D, dtype=L.dtype))      # évite les NaN dans le lot
    diff = X[None, None] - mu[:, :, None, :]
    z = torch.linalg.solve_triangular(L, diff.transpose(-1, -2), upper=False)
    logdet = 2.0 * torch.log(torch.diagonal(L, dim1=-2, dim2=-1)).sum(-1)
    lp = -0.5 * (D * LOG2PI + logdet[..., None] + (z ** 2).sum(-2))
    return lp, bon.all(dim=-1)


def _etape_e_lot(X: Tensor, pi: Tensor, mu: Tensor, cov: Tensor):
    """Étape E (1.15) en log-espace pour toutes les relances : (r (B,N,K), log p(x_n | theta) (B,N), ok (B,))."""
    B, K, D = mu.shape
    N = X.shape[0]
    r = X.new_empty(B, N, K)
    ln = X.new_empty(B, N)
    ok = torch.empty(B, dtype=torch.bool)
    for sl in _tranches(B, K, N, D):
        lp, ok[sl] = _log_gauss_lot(X, mu[sl], cov[sl])
        log_r = (torch.log(pi[sl] + 1e-300)[:, :, None] + lp).transpose(1, 2)    # (b,N,K)
        ln[sl] = torch.logsumexp(log_r, dim=2)
        r[sl] = torch.exp(log_r - ln[sl][..., None])
    return r, ln, ok


def _covariances_lot(X, r, mu, Nk, cov_type, reg):
    """Mise à jour des covariances (1.16) selon la contrainte de forme choisie, en lot."""
    B, K, D = mu.shape
    S = _dispersion_lot(X, r, mu)
    I = torch.eye(D, dtype=X.dtype)
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


def _etape_m_lot(X, r, cov_type, reg):
    """Étape M (1.16) : pi_k = N_k/N, mu_k = moyenne pondérée, Sigma_k = covariance pondérée."""
    N = X.shape[0]
    Nk = r.sum(1) + 1e-10
    pi = Nk / N
    mu = torch.einsum("bnk,nd->bkd", r, X) / Nk[..., None]
    return pi, mu, _covariances_lot(X, r, mu, Nk, cov_type, reg)


def _etape_m_map_lot(X, r, pr: "PrioriNW", reg):
    """
    Étape M du MAP-EM (covariance pleine), en lot : mode conjoint de (pi, mu, Sigma) sous le prior
    Dirichlet x Normale-Inverse-Wishart.
      pi_k    proportionnel à N_k + alpha0 - 1
      mu_k  = (beta0 m0 + N_k xbar_k) / (beta0 + N_k)
      Sigma_k = (W0^-1 + S_k + beta0 N_k/(beta0+N_k) (xbar_k-m0)(xbar_k-m0)^T) / (nu0 + N_k + D + 2)
    Exige alpha0 >= 1 (sinon le mode est au bord du simplexe).
    """
    D = X.shape[1]
    Nk = r.sum(1) + 1e-10
    pi = (Nk + pr.alpha0 - 1.0).clamp(min=1e-10)
    pi = pi / pi.sum(-1, keepdim=True)
    xbar = torch.einsum("bnk,nd->bkd", r, X) / Nk[..., None]
    mu = (pr.beta0 * pr.m0 + Nk[..., None] * xbar) / (pr.beta0 + Nk)[..., None]
    S = _dispersion_lot(X, r, xbar)
    d0 = xbar - pr.m0
    couplage = (pr.beta0 * Nk / (pr.beta0 + Nk))[..., None, None] * d0[..., :, None] * d0[..., None, :]
    cov = (pr.W0inv + S + couplage) / (pr.nu0 + Nk + D + 2.0)[..., None, None]
    return pi, mu, cov + reg * torch.eye(D, dtype=X.dtype)


def _init_em_lot(X, K, cov_type, init, graines, reg):
    N, D = X.shape
    B = len(graines)
    if init == "kmeans":
        etiq, _ = kmeans_lot(X, K, graines)
        r0 = torch.nn.functional.one_hot(etiq, K).to(X.dtype)
        return _etape_m_lot(X, r0, cov_type, reg)
    mu = X.new_empty(B, K, D)
    for b, gr in enumerate(graines):                                   # initialisation aléatoire (1.6.2.a)
        mu[b] = X[torch.randperm(N, generator=generateur(gr))[:K]]
    cov0 = torch.cov(X.T).reshape(D, D) + reg * torch.eye(D, dtype=X.dtype)
    return torch.full((B, K), 1.0 / K, dtype=X.dtype), mu, cov0.expand(B, K, D, D).clone()


def _piloter_lot(params: dict, B: int, n_iter: int, tol: float, evaluer, maj, instantane=None, meta=None):
    """
    Boucle commune à l'EM, au MAP-EM et au VB, avec le critère d'arrêt commun (section « Critère d'arrêt »).
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


def _em_lot(X, K, cov_type, n_iter, tol, reg, init, graines, prior=None, instantane=None):
    """EM (prior=None) ou MAP-EM (prior fourni) pour len(graines) relances en lot."""
    N, D = X.shape
    pi, mu, cov = _init_em_lot(X, K, cov_type, init, graines, reg)
    params = {"pi": pi, "mu": mu, "cov": cov}

    def evaluer(sub):
        r, ln, ok = _etape_e_lot(X, sub["pi"], sub["mu"], sub["cov"])
        return r, ln.sum(1), ok, None

    def maj(sub, r, aux):
        p, m, c = (_etape_m_lot(X, r, cov_type, reg) if prior is None else _etape_m_map_lot(X, r, prior, reg))
        return {"pi": p, "mu": m, "cov": c}

    meta = {"algo": "em" if prior is None else "map", "K": K, "N": N, "D": D, "cov": cov_type, "init": init,
            "graines": list(graines), "tol": tol, "n_iter": n_iter, "reg": reg}
    etat = _piloter_lot(params, len(graines), n_iter, tol, evaluer, maj, instantane, meta)
    bons = (~etat["echec"]).nonzero().flatten()
    if len(bons) == 0:
        raise EchecNumerique("EM : toutes les relances ont échoué (covariance non définie positive)")
    r = X.new_zeros(len(graines), N, K)
    r[bons], _, _ = _etape_e_lot(X, params["pi"][bons], params["mu"][bons], params["cov"][bons])
    etat.update(params=params, r=r)
    return etat


def _finaliser_em(lot, X, K, cov_type, t0, prior=None, graines=None):
    N, D = X.shape
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
    pi, mu, cov, r = (lot["params"]["pi"][b], lot["params"]["mu"][b], lot["params"]["cov"][b], lot["r"][b])
    p = nb_parametres(K, D, cov_type)
    Nk = r.sum(0)
    masque = indicateur_degenerescence(cov, Nk, D)
    temps = time.perf_counter() - t0
    res = {"pi": pi, "mu": mu, "cov": cov, "r": r, "loglik": float(ll[b]),
           "ll_hist": lot["hist"][:comp[b], b].tolist(), "n_iter": int(n_it[b]), "converge": bool(lot["converge"][b]),
           "Nk": Nk, "labels": r.argmax(1), "n_params": p, "bic": bic(float(ll[b]), p, N), "aic": aic(float(ll[b]), p),
           "icl": icl(float(ll[b]), p, N, r), "entropie": entropie_affectation(r),
           "degenere": bool(masque.any()), "degenere_composantes": masque, "temps": temps, "cov_type": cov_type,
           "temps_par_iter": temps / max(lot["passages"], 1),
           "relances": {"loglik": ll.tolist(), "n_iter": n_it.tolist(), "converge": lot["converge"].tolist(),
                        "echec": lot["echec"].tolist(), "meilleure": b, "graines": list(graines) if graines else None}}
    if prior is not None and prior.beta0 > 0:
        res["log_posteriori"] = float(score[b])
    return res


def em_classique(X, K, cov_type="full", n_iter=N_ITER_MAX, tol=TOL_REL, reg=REG_EM,
                 init="kmeans", graine=0, n_init=1, instantane=None):
    """
    EM classique pour un mélange de K gaussiennes. Les n_init relances (graines graine, graine+1, ...)
    sont ajustées EN LOT dans un seul tenseur ; on garde la plus grande log-vraisemblance.

    init : "kmeans" (par défaut, comme la pratique courante) ou "aleatoire"
           (K points tirés au hasard, covariance globale, section 1.6.2.a).
    tol, n_iter : critère d'arrêt commun (relatif, sur la log-vraisemblance totale).
    reg : régularisation Sigma_k + reg I (T1.7). C'est un garde-fou contre les singularités
          de la vraisemblance non bornée ; elle fait de l'EM un maximum « restreint ».
    instantane : objet de sauvegarde périodique de l'état de la boucle (reprise exacte), facultatif.
    Retourne aussi bic, aic, icl, degenere, temps_par_iter (temps / passages du lot) et `relances`
    (log-vraisemblance, itérations, convergence et échec de chaque relance).
    """
    t0 = time.perf_counter()
    graines = [graine + s for s in range(n_init)]
    lot = _em_lot(X, K, cov_type, n_iter, tol, reg, init, graines, None, instantane)
    return _finaliser_em(lot, X, K, cov_type, t0, None, graines)


def map_em(X, K, priori: "PrioriNW", n_iter=N_ITER_MAX, tol=TOL_REL, reg=REG_EM,
           init="kmeans", graine=0, n_init=1, instantane=None):
    """
    MAP-EM (covariance pleine) : EM dont l'étape M maximise Q + log p(theta) avec les priors
    conjugués du VB. Isole l'effet du prior de celui de l'inférence bayésienne complète.
    Le critère d'arrêt est le même que pour l'EM (log-vraisemblance totale). On garde la
    relance de plus grand log-posteriori. Exige priori.alpha0 >= 1.
    """
    if priori.alpha0 < 1.0:
        raise ValueError("MAP-EM : alpha0 >= 1 requis (mode du Dirichlet)")
    t0 = time.perf_counter()
    graines = [graine + s for s in range(n_init)]
    lot = _em_lot(X, K, "full", n_iter, tol, reg, init, graines, priori, instantane)
    return _finaliser_em(lot, X, K, "full", t0, priori, graines)


# --- versions « une relance » conservées pour les variantes stochastiques, la validation et les tests ---

def _etape_e(X, pi, mu, cov):
    """Étape E (1.15) pour un seul jeu de paramètres : (r (N,K), log p(x_i | theta) (N,))."""
    r, ln, ok = _etape_e_lot(X, pi[None], mu[None], cov[None])
    if not bool(ok[0]):
        raise EchecNumerique("covariance non définie positive")
    return r[0], ln[0]


def _etape_m(X, r, cov_type, reg):
    pi, mu, cov = _etape_m_lot(X, r[None], cov_type, reg)
    return pi[0], mu[0], cov[0]


def _etape_m_map(X, r, pr: "PrioriNW", reg):
    pi, mu, cov = _etape_m_map_lot(X, r[None], pr, reg)
    return pi[0], mu[0], cov[0]


def _init_em(X, K, cov_type, init, graine, reg):
    pi, mu, cov = _init_em_lot(X, K, cov_type, init, [graine], reg)
    return pi[0], mu[0], cov[0]


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
    lp, ok = _log_gauss_lot(X, mu[None], cov[None])
    log_joint = torch.log(pi)[:, None] + lp[0]                       # (K,N)
    return float((r * log_joint.T).sum() - torch.xlogy(r, r).sum())
