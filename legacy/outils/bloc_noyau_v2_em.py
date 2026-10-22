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


def kmeans_lot(X: Tensor, K: int, graines, n_iter: int | None = None):
    """
    K-means (Lloyd) avec initialisation k-means++ (Arthur et Vassilvitskii 2007), une graine par relance,
    itérations de Lloyd en lot. Arrêt quand les centres ne bougent plus (torch.allclose) ou au plafond.
    Retourne (étiquettes (B,N), centres (B,K,D), plafond_atteint (B,)).
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
