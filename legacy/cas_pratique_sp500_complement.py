"""
================================================================================
CAS SECONDAIRE S&P 500 : COMPLÉMENTS (phase 4B)
================================================================================

Usage : python cas_pratique_sp500_complement.py [--rapide]

Ajoute à cas_pratique.py :
  * des modèles de référence : gaussienne, Student-t, GARCH(1,1)-t, simulation historique ;
  * pour chaque mélange (EM-BIC, VB) deux évaluations : plug-in (paramètres ponctuels) et
    prédictive (VB seulement), afin d'isoler l'effet de la loi prédictive de l'effet de
    l'inférence bayésienne (la différence prédictive - plug-in du même VB) ;
  * le backtest de la VaR : Kupiec, Christoffersen (indépendance, conditionnel), ES d'Acerbi-Szekely ;
  * Diebold-Mariano sur les log-scores quotidiens (correction de Harvey) ;
  * bootstrap non paramétrique de l'EM avec B >= 1000 (100 avec --rapide) ;
  * HMM à deux états en filtrage forward (aucune information future), VaR conditionnelle.

Convention : rendements en %, VaR et ES négatives. Même fenêtre qu'en cas_pratique.py
(apprentissage jusqu'au 2021-12-31). Les modèles sont ajustés une seule fois sur l'apprentissage
(pas de réestimation glissante) : limite à déclarer. Aucune valeur n'est saisie à la main.
"""

from __future__ import annotations

import argparse
import math

import pandas as pd
import torch

import algorithmes as A
import cas_pratique as CP
import comparaison as C
import risque as R

SORTIE = CP.DOSSIER / "resultats"
NIVEAUX = (0.05, 0.01)


# ------------------------------------------------------------------------------
# lois de référence
# ------------------------------------------------------------------------------

def _student_logpdf(x, mu, s, nu):
    z = (x - mu) / s
    return (torch.lgamma((nu + 1) / 2) - torch.lgamma(nu / 2) - 0.5 * torch.log(nu * math.pi) - torch.log(s)
            - (nu + 1) / 2 * torch.log1p(z ** 2 / nu))


def ajuster_student(x):
    """MLE de la loi de Student à position-échelle (LBFGS). Retourne (mu, s, nu)."""
    x = x.flatten()
    theta = torch.tensor([float(x.mean()), math.log(float(x.std())), math.log(4.0)], requires_grad=True)
    opt = torch.optim.LBFGS([theta], max_iter=200, line_search_fn="strong_wolfe")

    def f():
        opt.zero_grad()
        mu, s, nu = theta[0], torch.exp(theta[1]), 2.05 + torch.exp(theta[2])
        loss = -_student_logpdf(x, mu, s, nu).sum()
        loss.backward()
        return loss
    opt.step(f)
    return theta[0].detach(), torch.exp(theta[1]).detach(), (2.05 + torch.exp(theta[2])).detach()


def _quantile_student_std(p, nu, n=400000, graine=0):
    with torch.random.fork_rng():
        torch.manual_seed(graine)
        z = torch.randn(n)
        chi2 = torch.distributions.Gamma(nu / 2, torch.tensor(0.5)).sample((n,))
    t = z * torch.sqrt(nu / chi2)
    q = torch.quantile(t, p)
    return float(q), float(t[t <= q].mean())


def garch_t_filtre(x, omega, alpha, beta, sigma2_0):
    s2 = torch.empty(len(x) + 1)
    s2[0] = sigma2_0
    for t in range(len(x)):
        s2[t + 1] = omega + alpha * x[t] ** 2 + beta * s2[t]
    return s2                                           # s2[t] = variance prévue pour le jour t (t = 0..len(x))


def ajuster_garch_t(x):
    """GARCH(1,1) à innovations de Student standardisées, MLE (LBFGS). Retourne dict de paramètres."""
    x = x.flatten()
    v0 = float(x.var())
    theta = torch.tensor([math.log(0.05 * v0), -2.5, 2.0, math.log(5.0)], requires_grad=True)

    def params():
        omega = torch.exp(theta[0])
        alpha = torch.sigmoid(theta[1])
        beta = (1 - alpha) * torch.sigmoid(theta[2])       # alpha + beta < 1
        nu = 2.5 + torch.exp(theta[3])
        return omega, alpha, beta, nu

    def nll():
        omega, alpha, beta, nu = params()
        mu = x.mean()
        e = x - mu
        s2 = torch.tensor(v0)
        ll = 0.0
        sc = torch.sqrt((nu - 2) / nu)
        for t in range(len(e)):
            s = torch.sqrt(s2)
            ll = ll + _student_logpdf(e[t], torch.tensor(0.0), s * sc, nu)
            s2 = omega + alpha * e[t] ** 2 + beta * s2
        return -ll

    opt = torch.optim.Adam([theta], lr=0.05)
    for _ in range(100):
        opt.zero_grad()
        loss = nll()
        loss.backward()
        opt.step()
    omega, alpha, beta, nu = (p.detach() for p in params())
    return {"omega": omega, "alpha": alpha, "beta": beta, "nu": nu, "mu": x.mean(), "v0": v0}


# ------------------------------------------------------------------------------
# prévisions de VaR / ES jour par jour sur la période test
# ------------------------------------------------------------------------------

def previsions_modeles(x_tr, x_te, niveaux, modeles_mix, S, graine=0):
    """Retourne {nom: {niveau: (var[T], es[T], logscore[T])}}."""
    T = len(x_te)
    out = {}
    # gaussienne
    mu, sd = x_tr.mean(), x_tr.std()
    ls = torch.distributions.Normal(mu, sd).log_prob(x_te.flatten())
    out["Gaussienne"] = {a: (torch.full((T,), float(mu + sd * math.sqrt(2) * torch.erfinv(torch.tensor(2 * a - 1.0)))),
                             None, ls) for a in niveaux}
    for a in niveaux:
        q = float(mu + sd * math.sqrt(2) * torch.erfinv(torch.tensor(2 * a - 1.0)))
        z = (q - mu) / sd
        es = float(mu - sd * torch.exp(-0.5 * z ** 2) / math.sqrt(2 * math.pi) / a)
        out["Gaussienne"][a] = (torch.full((T,), q), torch.full((T,), es), ls)
    # Student
    m, s, nu = ajuster_student(x_tr)
    ls = _student_logpdf(x_te.flatten(), m, s, nu)
    out["Student-t"] = {}
    for a in niveaux:
        qz, ez = _quantile_student_std(a, nu)
        out["Student-t"][a] = (torch.full((T,), float(m + s * qz)), torch.full((T,), float(m + s * ez)), ls)
    # simulation historique (apprentissage figé)
    out["Simulation historique"] = {}
    for a in niveaux:
        q = float(torch.quantile(x_tr.flatten(), a))
        es = float(x_tr.flatten()[x_tr.flatten() <= q].mean())
        out["Simulation historique"][a] = (torch.full((T,), q), torch.full((T,), es), None)
    # GARCH(1,1)-t
    g = ajuster_garch_t(x_tr)
    e_tr = x_tr.flatten() - g["mu"]
    s2 = garch_t_filtre(e_tr, g["omega"], g["alpha"], g["beta"], g["v0"])[-1]
    sc = torch.sqrt((g["nu"] - 2) / g["nu"])
    var_t, ls = [], []
    for t in range(T):
        sigma = torch.sqrt(s2)
        ls.append(_student_logpdf(x_te.flatten()[t] - g["mu"], torch.tensor(0.0), sigma * sc, g["nu"]))
        var_t.append(sigma)
        s2 = g["omega"] + g["alpha"] * (x_te.flatten()[t] - g["mu"]) ** 2 + g["beta"] * s2
    sig = torch.stack(var_t)
    out["GARCH(1,1)-t"] = {}
    for a in niveaux:
        qz, ez = _quantile_student_std(a, g["nu"])
        out["GARCH(1,1)-t"][a] = (g["mu"] + sig * sc * qz, g["mu"] + sig * sc * ez, torch.stack(ls))
    # mélanges
    for nom, (mod, P) in modeles_mix.items():
        pi, mu_k, sg_k = mod
        ls_plug = R.log_densite_gauss_1d(x_te.flatten(), pi, mu_k, sg_k)
        out[f"{nom} (plug-in)"] = {}
        for a in niveaux:
            q = R.quantile_melange_gauss(a, pi, mu_k, sg_k)
            es = R.es_melange_gauss(a, q, pi, mu_k, sg_k)
            out[f"{nom} (plug-in)"][a] = (q.expand(T).clone(), es.expand(T).clone(), ls_plug)
        if P is not None:
            ls_pred = R.log_predictive_variationnel(x_te, P)
            out[f"{nom} (prédictive)"] = {}
            for a in niveaux:
                q, es = R.var_es_student_melange(P, a, graine=graine)
                out[f"{nom} (prédictive)"][a] = (torch.full((T,), q), torch.full((T,), es), ls_pred)
    return out


def hmm_filtre_forward(x_tr, x_te, niveaux, graine=0):
    """HMM gaussien à 2 états ajusté sur l'apprentissage ; filtrage forward sur le test (aucun lissage). VaR conditionnelle : mélange des deux états pondéré par P(z_t | x_1..x_(t-1)) (prédiction d'un pas)."""
    best = max((A.baum_welch([x_tr.flatten()], 2, emission="gauss", n_iter=150, graine=s) for s in range(3)), key=lambda d: d["loglik"])
    mu, var, Am = best["mu"], best["var"], best["A"]
    sd = var.sqrt()
    T = len(x_te)
    # filtre : p_pred_t = p_filt_(t-1) @ A ; p_filt_t proportionnel à p_pred_t * f(x_t)
    p_filt = best["pi0"]
    xs = x_te.flatten()
    varL = {a: torch.empty(T) for a in niveaux}
    esL = {a: torch.empty(T) for a in niveaux}
    ls = torch.empty(T)
    # état initial : filtre sur la fin de l'apprentissage
    for t in range(len(x_tr)):
        f = torch.exp(-0.5 * ((x_tr[t, 0] - mu) / sd) ** 2) / sd
        p_filt = (p_filt @ Am if t > 0 else p_filt) * f
        p_filt = p_filt / p_filt.sum()
    for t in range(T):
        p_pred = p_filt @ Am
        for a in niveaux:
            q = R.quantile_melange_gauss(a, p_pred, mu, sd)
            varL[a][t] = q[0]
            esL[a][t] = R.es_melange_gauss(a, q, p_pred, mu, sd)[0]
        ls[t] = R.log_densite_gauss_1d(xs[t:t + 1], p_pred, mu, sd)[0]
        f = torch.exp(-0.5 * ((xs[t] - mu) / sd) ** 2) / sd
        p_filt = p_pred * f
        p_filt = p_filt / p_filt.sum()
    return {a: (varL[a], esL[a], ls) for a in niveaux}


# ------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapide", action="store_true")
    args = ap.parse_args(argv)
    B = 100 if args.rapide else 1000
    S = 1000 if args.rapide else 4000
    SORTIE.mkdir(exist_ok=True)
    df = CP.charger_rendements()
    app, test = df[df.date <= CP.FIN_APPRENTISSAGE], df[df.date > CP.FIN_APPRENTISSAGE]
    x_tr = torch.tensor(app.r.values).reshape(-1, 1)
    x_te = torch.tensor(test.r.values).reshape(-1, 1)
    T = len(x_te)

    em = {K: A.em_classique(x_tr, K, n_init=10, graine=42) for K in range(1, 7)}
    K_bic = min(em, key=lambda k: em[k]["bic"])
    K_icl = min(em, key=lambda k: em[k]["icl"])
    vb = A.em_variationnel(x_tr, 6, alpha0=1 / 6, n_init=10, graine=42)
    pi_v, mu_v, sg_v = vb["pi"], vb["m"].reshape(-1), vb["cov"].reshape(-1).sqrt()
    mixtes = {f"EM-BIC (K={K_bic})": (CP.params_em(em[K_bic]), None),
              f"VB-emp": ((pi_v, mu_v, sg_v), vb["P"])}
    prev = previsions_modeles(x_tr, x_te, NIVEAUX, mixtes, S)
    for a, v in hmm_filtre_forward(x_tr, x_te, NIVEAUX).items():
        prev.setdefault("HMM 2 états (filtrage forward)", {})[a] = v

    # --- backtests ---------------------------------------------------------------------------
    lignes = []
    r = x_te.flatten()
    for nom, par_niveau in prev.items():
        for a, (var, es, ls) in par_niveau.items():
            I = (r < var).to(torch.int64).tolist()
            cc = R.christoffersen(I, a)
            ligne = {"modele": nom, "niveau": a, "exceptions": sum(I), "attendues": round(a * T, 1),
                     "Kupiec_p": round(cc["p_uc"], 4), "Christoffersen_ind_p": round(cc["p_ind"], 4),
                     "Christoffersen_cc_p": round(cc["p_cc"], 4),
                     "logscore_moyen": None if ls is None else round(float(ls.mean()), 4)}
            if es is not None:
                z = R.acerbi_szekely(r, var, es, a)
                ligne.update(AS_Z1=round(z["z1"], 3) if z["z1"] == z["z1"] else None, AS_Z2=round(z["z2"], 3))
            lignes.append(ligne)
    tab = pd.DataFrame(lignes)
    tab.to_csv(SORTIE / "sp500_backtests.csv", index=False)

    # --- Diebold-Mariano sur les log-scores quotidiens (A - B > 0 : A meilleur) ------------------
    paires = [(f"EM-BIC (K={K_bic}) (plug-in)", "Gaussienne"), ("VB-emp (prédictive)", "Gaussienne"), ("Student-t", "Gaussienne"),
              ("VB-emp (prédictive)", "VB-emp (plug-in)"), ("VB-emp (prédictive)", f"EM-BIC (K={K_bic}) (plug-in)"),
              ("VB-emp (plug-in)", f"EM-BIC (K={K_bic}) (plug-in)"), (f"EM-BIC (K={K_bic}) (plug-in)", "Student-t"),
              ("VB-emp (prédictive)", "Student-t"), ("GARCH(1,1)-t", "Student-t"), ("GARCH(1,1)-t", "VB-emp (prédictive)")]
    dm = []
    for a_, b_ in paires:
        la, lb = prev[a_][0.05][2], prev[b_][0.05][2]
        d = (la - lb)
        s, p = R.diebold_mariano(d, h=1)
        dm.append({"A": a_, "B": b_, "ecart_logscore_moyen": round(float(d.mean()), 4), "DM": round(s, 3), "p": round(p, 4)})
    dm = pd.DataFrame(dm)
    dm["p_holm"] = C.holm(dm.p.tolist())[0]
    dm.to_csv(SORTIE / "sp500_diebold_mariano.csv", index=False)

    # --- bootstrap EM (B >= 1000) : VaR 1 % ------------------------------------------------------
    g = A.generateur(11)
    vb_boot = {a: [] for a in NIVEAUX}
    for b in range(B):
        idx = torch.randint(len(x_tr), (len(x_tr),), generator=g)
        e = A.em_classique(x_tr[idx], K_bic, n_init=1, graine=b)
        pe, me, se = CP.params_em(e)
        for a in NIVEAUX:
            vb_boot[a].append(float(R.quantile_melange_gauss(a, pe, me, se)[0]))
    rows = []
    pi_d, mu_d, sg_d = R.echantillonner_posterieur_gmm_1d(vb["P"], S, graine=7)
    for a in NIVEAUX:
        bs = torch.tensor(vb_boot[a])
        post = R.quantile_melange_gauss(a, pi_d, mu_d, sg_d)
        rows.append({"niveau": a, "B": B,
                     "IC95_bootstrap_EM": f"[{float(torch.quantile(bs, .025)):.3f} ; {float(torch.quantile(bs, .975)):.3f}]",
                     "largeur_bootstrap": round(float(torch.quantile(bs, .975) - torch.quantile(bs, .025)), 3),
                     "IC95_credible_VB": f"[{float(torch.quantile(post, .025)):.3f} ; {float(torch.quantile(post, .975)):.3f}]",
                     "largeur_VB": round(float(torch.quantile(post, .975) - torch.quantile(post, .025)), 3),
                     "note": "objets différents (variabilité d'estimateur contre crédibilité a posteriori) ; couverture non évaluée ici : voir le jeu semi-synthétique du climat"})
    pd.DataFrame(rows).to_csv(SORTIE / "sp500_intervalles.csv", index=False)
    print(tab.to_string(index=False)); print(dm.to_string(index=False))


if __name__ == "__main__":
    main()
