"""
================================================================================
ÉTAPE « sp500 » : rendements du S&P 500 et risque de marché (cas secondaire)
================================================================================

Données : clôtures FRED SP500 (archive locale, empreinte SHA-256 vérifiée ; non redistribuable).
Apprentissage jusqu'au 2021-12-31, évaluation ensuite ; paramètres estimés une fois puis figés.

Unités :
  em/K=k (k = 1..Kmax)   EM, n_init relances (famille « sp500 »)
  vb/emp, vb/cal         VB à Kmax, priors empiriques et calibrés
  student                loi de Student (position, échelle, nu) : maximum de vraisemblance par L-BFGS
  garch                  GARCH(1,1) à innovations de Student : maximum de vraisemblance par L-BFGS
  hmm                    HMM gaussien à hmm_etats états (nombre choisi par BIC au calibrage), filtrage forward
  bootstrap/bloc=b       réplicats bootstrap de l'EM (K du BIC) avec démarrage chaud, par blocs de 100
Les optimisations (Student, GARCH) utilisent le critère d'arrêt commun (variation relative de la
log-vraisemblance) et plusieurs points de départ ; la convergence et la dispersion entre départs sont
enregistrées. Hypothèses (famille « finance », Holm) : tests de Diebold-Mariano déclarés ci-dessous.
"""

from __future__ import annotations

import itertools
import math
from datetime import date

import torch

import algorithmes as A
import comparaison as C
import donnees as DO
import etapes as E
import parametres as PARAM
import persistance as PE
import risque as R
import statistique as S

FIN_APPRENTISSAGE = date(2021, 12, 31)
FAMILLE = "sp500"
BLOC_BOOTSTRAP = 100

# Comparaisons de Diebold-Mariano déclarées (A, B) : différence de log-score quotidien A - B
DM_DECLARES = [("EM-BIC (plug-in)", "Gaussienne"), ("VB-emp (prédictive)", "Gaussienne"), ("Student-t", "Gaussienne"),
               ("VB-emp (prédictive)", "VB-emp (plug-in)"), ("VB-emp (prédictive)", "EM-BIC (plug-in)"),
               ("VB-emp (plug-in)", "EM-BIC (plug-in)"), ("EM-BIC (plug-in)", "Student-t"),
               ("VB-emp (prédictive)", "Student-t"), ("GARCH(1,1)-t", "Student-t"), ("GARCH(1,1)-t", "VB-emp (prédictive)"),
               ("HMM filtré", "VB-emp (prédictive)")]


def donnees():
    dates, r = DO.charger_sp500()
    app = torch.tensor([d <= FIN_APPRENTISSAGE for d in dates])
    return r[app].reshape(-1, 1), r[~app].reshape(-1, 1), [d for d, a in zip(dates, app.tolist()) if not a]


def _n_init(rapide):
    n = int(PARAM.valeur("n_init")[FAMILLE])
    return min(n, 3) if rapide else n


def unite_em(memo, rapide, K):
    x, _, _ = donnees()
    res = A.em_classique(x, K, n_init=_n_init(rapide), graine=PE.graine("sp500", "em", K) % 2 ** 31)
    return {"lignes": [{"K": K, "loglik": res["loglik"], "bic": res["bic"], "icl": res["icl"], "converge": float(res["converge"])}],
            "artefacts": {"ajustement": PE.resume_ajustement(res)}}


def unite_vb(memo, rapide, priors):
    x, _, _ = donnees()
    kmax = int(PARAM.valeur("k_max")[FAMILLE])
    pr = C.priors_bras(x, kmax, FAMILLE)["emp" if priors == "emp" else "cal"]
    res = A.em_variationnel(x, kmax, priori=pr, n_init=_n_init(rapide), graine=PE.graine("sp500", "vb", priors) % 2 ** 31)
    return {"lignes": [{"priors": priors, "k_hat": C.k_hat(res["Nk"], len(x)), "elbo": res["elbo"], "converge": float(res["converge"])}],
            "artefacts": {"ajustement": PE.resume_ajustement(res)}}


# ------------------------------------------------------------------------------ optimisation contrôlée
def optimiser(nll, theta0, n_iter=None, tol=None):
    """
    Minimise nll(theta) par L-BFGS (recherche linéaire de Wolfe forte) avec le critère d'arrêt commun :
    variation relative de la valeur <= tol_rel entre deux pas, au plus n_iter_max pas. Retourne (theta, valeur, converge, pas).
    """
    tol, n_iter, _ = A._defauts(tol, n_iter, 0.0)
    th = theta0.clone().requires_grad_(True)
    opt = torch.optim.LBFGS([th], max_iter=20, line_search_fn="strong_wolfe", tolerance_grad=0.0, tolerance_change=0.0)

    def ferm():
        opt.zero_grad()
        v = nll(th)
        v.backward()
        return v

    prec, converge, k = float(nll(th)), False, 0
    for k in range(1, n_iter + 1):
        opt.step(ferm)
        v = float(nll(th))
        if not math.isfinite(v):
            break
        if A.a_converge(prec, v, tol):
            converge = True
            break
        prec = v
    return th.detach(), float(nll(th)), converge, k


def _student_logpdf(x, mu, s, nu):
    z = (x - mu) / s
    return (torch.lgamma((nu + 1) / 2) - torch.lgamma(nu / 2) - 0.5 * torch.log(nu * math.pi) - torch.log(s)
            - (nu + 1) / 2 * torch.log1p(z ** 2 / nu))


def _student_var_es(a, mu, s, nu):
    """
    VaR et ES d'ordre a d'une loi de Student (position mu, échelle s, nu > 1 degrés de liberté), en convention rendement :
    q_a = quantile de t_nu par dichotomie sur la fonction de répartition ; ES_a = -f_nu(q_a) (nu + q_a²) / ((nu - 1) a)
    pour la loi réduite (formule fermée de la moyenne de queue de Student).
    """
    nu = float(nu)
    bas, haut = -1e3, 0.0
    for _ in range(200):
        m = 0.5 * (bas + haut)
        bas, haut = (m, haut) if S.t_cdf(m, nu) < a else (bas, m)
    q = 0.5 * (bas + haut)
    f = math.exp(math.lgamma((nu + 1) / 2) - math.lgamma(nu / 2) - 0.5 * math.log(nu * math.pi)
                 - (nu + 1) / 2 * math.log1p(q * q / nu))
    es = -f * (nu + q * q) / ((nu - 1) * a)
    return float(mu) + float(s) * q, float(mu) + float(s) * es


def unite_student(memo, rapide):
    x, _, _ = donnees()
    x = x.flatten()

    def nll(t):
        return -_student_logpdf(x, t[0], torch.exp(t[1]), 2.0 + torch.exp(t[2])).sum()

    departs = [torch.tensor([float(x.mean()), math.log(float(x.std())) + ds, math.log(nu - 2.0)])
               for ds, nu in itertools.product((-0.5, 0.0), (3.0, 6.0, 30.0))]
    essais = [optimiser(nll, t0) for t0 in departs]
    th, v, conv, _ = min(essais, key=lambda e: e[1])
    return {"lignes": [{"modele": "Student-t", "nll": v, "converge": float(conv),
                        "dispersion_nll_departs": max(e[1] for e in essais) - v}],
            "artefacts": {"mu": th[0], "s": torch.exp(th[1]), "nu": 2.0 + torch.exp(th[2]), "essais": [e[1] for e in essais]}}


def _garch_nll(t, e):
    """GARCH(1,1) : sigma²_t = omega + alpha e²_(t-1) + beta sigma²_(t-1), innovations de Student standardisées."""
    omega = torch.exp(t[0])
    alpha = torch.sigmoid(t[1])
    beta = (1 - alpha) * torch.sigmoid(t[2])                     # stationnarité : alpha + beta < 1
    nu = 2.0 + torch.exp(t[3])
    s2 = e.var()
    sc = torch.sqrt((nu - 2) / nu)
    total = torch.zeros((), dtype=e.dtype)
    for k in range(len(e)):
        total = total - _student_logpdf(e[k], torch.zeros((), dtype=e.dtype), torch.sqrt(s2) * sc, nu)
        s2 = omega + alpha * e[k] ** 2 + beta * s2
    return total


def unite_garch(memo, rapide):
    x, _, _ = donnees()
    mu = x.mean()
    e = (x.flatten() - mu)
    v0 = float(e.var())
    departs = []
    for a, b, nu in itertools.product((0.05, 0.15), (0.80, 0.95), (5.0, 15.0)):
        departs.append(torch.tensor([math.log(v0 * (1 - a - b * (1 - a)) + 1e-12),
                                     math.log(a / (1 - a)), math.log(b / (1 - b)), math.log(nu - 2.0)]))
    essais = [memo(f"depart={i}", lambda t0=t0: dict(zip(("theta", "nll", "converge", "pas"),
                                                           optimiser(lambda t: _garch_nll(t, e), t0))))
              for i, t0 in enumerate(departs)]
    best = min(essais, key=lambda d: d["nll"])
    t = best["theta"]
    alpha = torch.sigmoid(t[1])
    par = {"mu": mu, "omega": torch.exp(t[0]), "alpha": alpha, "beta": (1 - alpha) * torch.sigmoid(t[2]),
           "nu": 2.0 + torch.exp(t[3]), "v0": torch.tensor(v0)}
    return {"lignes": [{"modele": "GARCH(1,1)-t", "nll": best["nll"], "converge": float(best["converge"]),
                        "departs_convergents": sum(float(d["converge"]) for d in essais),
                        "dispersion_nll_departs": max(d["nll"] for d in essais) - best["nll"]}],
            "artefacts": {"parametres": par, "essais": [{"nll": d["nll"], "converge": d["converge"]} for d in essais]}}


def unite_hmm(memo, rapide):
    x, _, _ = donnees()
    S_ = int(PARAM.valeur("hmm_etats"))
    n = _n_init(rapide)
    fits = [A.baum_welch([x.flatten()], S_, emission="gauss", graine=PE.graine("sp500", "hmm", s) % 2 ** 31) for s in range(n)]
    best = max(fits, key=lambda d: d["loglik"])
    return {"lignes": [{"S": S_, "loglik": best["loglik"], "converge": float(best["converge"])}],
            "artefacts": {k: best[k] for k in ("A", "pi0", "mu", "var", "loglik", "ll_hist")}}


def _k_bic(rapide):
    mag = E.magasin("sp500", rapide)
    em = {int(c.split("=")[1]): mag.lire(c) for c in mag.cles() if c.startswith("em/K=")}
    return min(em, key=lambda k: em[k]["lignes"][0]["bic"]), em


def unite_bootstrap(memo, rapide, bloc):
    x, _, _ = donnees()
    K, em = _k_bic(rapide)
    depart = em[K]["artefacts"]["ajustement"]
    out = []
    for b in range(bloc * BLOC_BOOTSTRAP, (bloc + 1) * BLOC_BOOTSTRAP):
        ib = torch.randint(len(x), (len(x),), generator=A.generateur(PE.graine("sp500", "bootstrap", b)))
        eb = C.em_demarrage_chaud(x[ib], depart)
        sg = eb["cov"].reshape(-1).sqrt()
        out.append([float(R.quantile_melange_gauss(a, eb["pi"], eb["mu"].reshape(-1), sg)[0])
                    for a in PARAM.valeur("niveaux_var")])
    return {"lignes": [{"bloc": bloc, "K": K}], "artefacts": {"var_bootstrap": torch.tensor(out)}}


# ------------------------------------------------------------------------------ étape
def unites(rapide: bool):
    kmax = int(PARAM.valeur("k_max")[FAMILLE])
    us = [E.Unite("sp500", f"em/K={k}", "etape_sp500", "unite_em", dict(K=k)) for k in range(1, kmax + 1)]
    us += [E.Unite("sp500", f"vb/{p}", "etape_sp500", "unite_vb", dict(priors=p)) for p in ("emp", "cal")]
    us += [E.Unite("sp500", "student", "etape_sp500", "unite_student"), E.Unite("sp500", "garch", "etape_sp500", "unite_garch"),
           E.Unite("sp500", "hmm", "etape_sp500", "unite_hmm")]
    B = 100 if rapide else int(PARAM.valeur("n_bootstrap_modele"))
    deps = tuple(f"em/K={k}" for k in range(1, kmax + 1))
    us += [E.Unite("sp500", f"bootstrap/bloc={b:03d}", "etape_sp500", "unite_bootstrap", dict(bloc=b), depend=deps)
           for b in range(math.ceil(B / BLOC_BOOTSTRAP))]
    return us


def _previsions(rapide):
    """VaR, ES et log-scores quotidiens de chaque modèle sur la période d'évaluation."""
    x_tr, x_te, _ = donnees()
    r = x_te.flatten()
    T = len(r)
    mag = E.magasin("sp500", rapide)
    niveaux = PARAM.valeur("niveaux_var")
    nsim = 20000 if rapide else int(PARAM.valeur("n_simulation_var"))
    prev = {}
    mu, sd = x_tr.mean(), x_tr.std()
    ls = torch.distributions.Normal(mu, sd).log_prob(r)
    prev["Gaussienne"] = {}
    for a in niveaux:
        q = mu + sd * math.sqrt(2) * torch.erfinv(torch.tensor(2 * a - 1.0))
        z = (q - mu) / sd
        es = mu - sd * torch.exp(-0.5 * z ** 2) / math.sqrt(2 * math.pi) / a
        prev["Gaussienne"][a] = (torch.full((T,), float(q)), torch.full((T,), float(es)), ls)
    st = mag.lire("student")["artefacts"]
    ls = _student_logpdf(r, st["mu"], st["s"], st["nu"])
    prev["Student-t"] = {}
    for a in niveaux:
        q, es = _student_var_es(a, st["mu"], st["s"], st["nu"])
        prev["Student-t"][a] = (torch.full((T,), q), torch.full((T,), es), ls)
    prev["Simulation historique"] = {}
    xt = x_tr.flatten()
    for a in niveaux:
        q = float(torch.quantile(xt, a))
        prev["Simulation historique"][a] = (torch.full((T,), q), torch.full((T,), float(xt[xt <= q].mean())), None)
    g = mag.lire("garch")["artefacts"]["parametres"]
    e_tr = xt - g["mu"]
    s2 = g["v0"]
    for k in range(len(e_tr)):
        s2 = g["omega"] + g["alpha"] * e_tr[k] ** 2 + g["beta"] * s2
    sc = torch.sqrt((g["nu"] - 2) / g["nu"])
    sig, lsg = [], []
    for k in range(T):
        s = torch.sqrt(s2)
        sig.append(s)
        lsg.append(_student_logpdf(r[k] - g["mu"], torch.tensor(0.0, dtype=torch.float64), s * sc, g["nu"]))
        s2 = g["omega"] + g["alpha"] * (r[k] - g["mu"]) ** 2 + g["beta"] * s2
    sig = torch.stack(sig)
    prev["GARCH(1,1)-t"] = {}
    for a in niveaux:
        qz, ez = _student_var_es(a, 0.0, 1.0, g["nu"])
        prev["GARCH(1,1)-t"][a] = (g["mu"] + sig * sc * qz, g["mu"] + sig * sc * ez, torch.stack(lsg))
    K, em = _k_bic(rapide)
    fe = em[K]["artefacts"]["ajustement"]
    pi, m, sg = fe["pi"], fe["mu"].reshape(-1), fe["cov"].reshape(-1).sqrt()
    ls = R.log_densite_gauss_1d(r, pi, m, sg)
    prev["EM-BIC (plug-in)"] = {}
    for a in niveaux:
        q = R.quantile_melange_gauss(a, pi, m, sg)
        prev["EM-BIC (plug-in)"][a] = (q.expand(T).clone(), R.es_melange_gauss(a, q, pi, m, sg).expand(T).clone(), ls)
    vb = mag.lire("vb/emp")["artefacts"]["ajustement"]
    piv, mv, sv = vb["pi"], vb["m"].reshape(-1), vb["cov"].reshape(-1).sqrt()
    ls = R.log_densite_gauss_1d(r, piv, mv, sv)
    prev["VB-emp (plug-in)"] = {}
    prev["VB-emp (prédictive)"] = {}
    lsp = R.log_predictive_variationnel(x_te, vb["P"])
    for a in niveaux:
        q = R.quantile_melange_gauss(a, piv, mv, sv)
        prev["VB-emp (plug-in)"][a] = (q.expand(T).clone(), R.es_melange_gauss(a, q, piv, mv, sv).expand(T).clone(), ls)
        qp, ep = R.var_es_student_melange(vb["P"], a, n=nsim, graine=PE.graine("sp500", "vb_var", a) % 2 ** 31)
        prev["VB-emp (prédictive)"][a] = (torch.full((T,), qp), torch.full((T,), ep), lsp)
    h = mag.lire("hmm")["artefacts"]
    prev["HMM filtré"] = _hmm_filtre(h, x_tr, x_te, niveaux)
    return prev, K


def _hmm_filtre(h, x_tr, x_te, niveaux):
    """Prédiction d'un pas : P(z_t | x_1..x_(t-1)) par filtrage forward, sans information future."""
    mu, sd, Am = h["mu"], h["var"].sqrt(), h["A"]
    p = h["pi0"]
    for t in range(len(x_tr)):
        f = torch.exp(-0.5 * ((x_tr[t, 0] - mu) / sd) ** 2) / sd
        p = (p @ Am if t > 0 else p) * f
        p = p / p.sum()
    xs = x_te.flatten()
    T = len(xs)
    var = {a: torch.empty(T, dtype=torch.float64) for a in niveaux}
    es = {a: torch.empty(T, dtype=torch.float64) for a in niveaux}
    ls = torch.empty(T, dtype=torch.float64)
    for t in range(T):
        pp = p @ Am
        for a in niveaux:
            q = R.quantile_melange_gauss(a, pp, mu, sd)
            var[a][t] = q[0]
            es[a][t] = R.es_melange_gauss(a, q, pp, mu, sd)[0]
        ls[t] = R.log_densite_gauss_1d(xs[t:t + 1], pp, mu, sd)[0]
        f = torch.exp(-0.5 * ((xs[t] - mu) / sd) ** 2) / sd
        p = pp * f
        p = p / p.sum()
    return {a: (var[a], es[a], ls) for a in niveaux}


def agreger(rapide: bool):
    x_tr, x_te, _ = donnees()
    r = x_te.flatten()
    T = len(r)
    E.ecrire_csv("sp500_descriptif", [_descr(x_tr.flatten(), "apprentissage"), _descr(r, "évaluation")], rapide)
    E.ecrire_csv("sp500_selection", [l for c in E.resultats("sp500", rapide, "em/") for l in c["lignes"]]
                 + [l for c in E.resultats("sp500", rapide, "vb/") for l in c["lignes"]], rapide)
    E.ecrire_csv("sp500_optimisation", E.lignes("sp500", rapide, "student") + E.lignes("sp500", rapide, "garch")
                 + E.lignes("sp500", rapide, "hmm"), rapide)
    prev, K = _previsions(rapide)
    bt = []
    for nom, par in prev.items():
        for a, (var, es, ls) in par.items():
            I = (r < var).to(torch.int64).tolist()
            cc = R.christoffersen(I, a)
            l = {"modele": nom, "niveau": a, "exceptions": sum(I), "attendues": a * T, "Kupiec_p": cc["p_uc"],
                 "Christoffersen_ind_p": cc["p_ind"], "Christoffersen_cc_p": cc["p_cc"],
                 "logscore_moyen": float(ls.mean()) if ls is not None else float("nan")}
            z = R.acerbi_szekely(r, var, es, a)
            l.update(AS_Z1=z["z1"], AS_Z2=z["z2"])
            bt.append(l)
    E.ecrire_csv("sp500_backtests", bt, rapide)
    a0 = PARAM.valeur("niveaux_var")[0]
    dm = []
    for A_, B_ in DM_DECLARES:
        d = prev[A_][a0][2] - prev[B_][a0][2]
        s, p = R.diebold_mariano(d, h=1)
        dm.append({"A": A_, "B": B_, "ecart_logscore_moyen": float(d.mean()), "DM": s, "p": p})
    for l, ph in zip(dm, S.holm([l["p"] for l in dm])):
        l["p_holm"] = ph
        l["decision"] = (("A > B" if l["ecart_logscore_moyen"] > 0 else "A < B") if ph < float(PARAM.valeur("alpha_test"))
                         else "différence non démontrée")
    E.ecrire_csv("sp500_diebold_mariano", dm, rapide)
    vb = E.magasin("sp500", rapide).lire("vb/emp")["artefacts"]["ajustement"]
    nt = 1000 if rapide else int(PARAM.valeur("n_tirages_posterieur"))
    pi_d, mu_d, sg_d = R.echantillonner_posterieur_gmm_1d(vb["P"], nt, graine=PE.graine("sp500", "posterieur") % 2 ** 31)
    boot = torch.cat([c["artefacts"]["var_bootstrap"] for c in E.resultats("sp500", rapide, "bootstrap/")])
    lignes = []
    for i, a in enumerate(PARAM.valeur("niveaux_var")):
        post = R.quantile_melange_gauss(a, pi_d, mu_d, sg_d)
        bs = boot[:, i]
        lignes.append({"niveau": a, "B": len(bs), "tirages_posterieur": nt, "K_bic": K,
                       "IC95_bootstrap_bas": float(torch.quantile(bs, .025)), "IC95_bootstrap_haut": float(torch.quantile(bs, .975)),
                       "IC95_credible_bas": float(torch.quantile(post, .025)), "IC95_credible_haut": float(torch.quantile(post, .975))})
    E.ecrire_csv("sp500_intervalles", lignes, rapide)


def _descr(r, nom):
    m, s = float(r.mean()), float(r.std())
    z = (r - m) / s
    return {"periode": nom, "observations": len(r), "moyenne_pct": m, "ecart_type_pct": s,
            "asymetrie": float((z ** 3).mean()), "kurtosis_excedentaire": float((z ** 4).mean() - 3.0),
            "minimum_pct": float(r.min()), "maximum_pct": float(r.max())}
