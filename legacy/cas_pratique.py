"""
================================================================================
CAS PRATIQUE : MODÉLISATION DES RENDEMENTS BOURSIERS ET RISQUE DE MARCHÉ
Mélanges gaussiens (EM classique, EM variationnel) et modèle de Markov caché
Kana Tiodong Icare Brichel, Master 2 SDIA, ENSPD, Université de Douala
================================================================================

Contexte (section 3.1.4) : les rendements d'un actif ont des queues plus épaisses
qu'une loi normale. Un mélange de gaussiennes les représente, et l'EM variationnel
donne une loi a posteriori sur les paramètres, donc une incertitude sur la
value-at-risk (VaR) que l'EM classique ne fournit pas directement.

Données : indice S&P 500, cours quotidiens de clôture (source : Federal Reserve Bank of
St. Louis, série FRED SP500, dix dernières années ; fichier mis en cache dans
data/sp500_fred.csv). Rendement = 100 x ln(P_t / P_{t-1}).
Apprentissage : jusqu'au 31 décembre 2021 (crise de 2020 comprise). Évaluation hors
échantillon : depuis le 1er janvier 2022 (hausse des taux, chocs de 2025).
Si le téléchargement échoue, placer un fichier CSV avec les colonnes Date et Close
(ou observation_date et SP500) dans data/sp500_fred.csv.

Hypothèses fixées avant l'analyse :
    H4  Un mélange (K > 1) a une log-vraisemblance hors échantillon supérieure à celle
        de la gaussienne unique.
    H5  La VaR gaussienne à 1 % est franchie plus souvent que prévu (test de Kupiec
        rejeté au seuil de 5 %). L'écart entre mélanges EM et VB n'est PAS une hypothèse :
        il est de l'ordre d'une exception et ne se lit pas comme une différence d'algorithme.
    H6  L'EM variationnel fournit un intervalle de crédibilité de la VaR ; pour l'EM
        classique, seul un bootstrap non paramétrique donne un intervalle comparable.

Utilisation :
    python cas_pratique.py
    python cas_pratique.py --rapide        # moins de tirages et de rééchantillonnages
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import torch
from plotly.subplots import make_subplots

import algorithmes as A
import main as M
import risque as R

DOSSIER = Path(__file__).parent
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500"
FIN_APPRENTISSAGE = "2021-12-31"
NIVEAUX = (0.05, 0.01)
SHA256_ARCHIVE = "551b282c417da2e7fa38ad4da0c5ebc2c907d386272a0752d04f97e16b7c90dc"   # data/sp500_fred.PROVENANCE.txt


# ------------------------------------------------------------------------------
# Données
# ------------------------------------------------------------------------------

def charger_rendements() -> pd.DataFrame:
    chemin = DOSSIER / "data" / "sp500_fred.csv"
    if not chemin.exists():
        erreur = None
        try:
            import urllib.request
            requete = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(requete, timeout=30) as reponse:
                chemin.write_text(reponse.read().decode("utf-8"), encoding="utf-8")
        except Exception as e:
            erreur = f"{type(e).__name__}: {e}"
        if erreur is not None:              # levée hors du bloc except pour garder une trace lisible
            raise RuntimeError(f"Téléchargement impossible ({erreur}). Placer un CSV (colonnes Date et Close) "
                               f"dans {chemin}.")
    import hashlib
    attendu = SHA256_ARCHIVE
    obtenu = hashlib.sha256(chemin.read_bytes()).hexdigest()
    if obtenu != attendu:
        print(f"AVERTISSEMENT : {chemin.name} diffère de l'archive (sha256 {obtenu[:12]}... au lieu de {attendu[:12]}...). "
              "Les résultats ne seront pas ceux du mémoire.")
    brut = pd.read_csv(chemin)
    col_date = next((c for c in brut.columns if c.lower() in ("date", "datetime", "observation_date")), None)
    col_prix = next((c for c in ("SP500", "Close", "Adj Close", "close", "Clôture") if c in brut.columns), None)
    if col_date is None or col_prix is None:
        raise RuntimeError(f"Colonnes Date et Close introuvables dans {chemin} : {list(brut.columns)}. "
                         "Supprimer le fichier pour relancer le téléchargement, ou fournir un CSV valide.")
    df = pd.DataFrame({"date": pd.to_datetime(brut[col_date]),
                       "prix": pd.to_numeric(brut[col_prix], errors="coerce")})
    df = df.dropna().sort_values("date").reset_index(drop=True)
    df["r"] = 100.0 * df.prix.apply(math.log).diff()
    return df.dropna().reset_index(drop=True)


def descriptif(df: pd.DataFrame, nom: str) -> dict:
    r = df.r
    return {"periode": nom, "observations": len(r), "moyenne_pct": round(r.mean(), 4),
            "ecart_type_pct": round(r.std(), 4), "asymetrie": round(r.skew(), 3),
            "kurtosis_excedentaire": round(r.kurt(), 3), "minimum_pct": round(r.min(), 2),
            "maximum_pct": round(r.max(), 2)}


def params_em(res) -> tuple:
    return res["pi"], res["mu"].reshape(-1), res["cov"].reshape(-1).sqrt()


# ------------------------------------------------------------------------------
# Programme
# ------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapide", action="store_true")
    ap.add_argument("--tirages", type=int, default=None)
    ap.add_argument("--bootstrap", type=int, default=None)
    args = ap.parse_args(argv)
    S = args.tirages or (1000 if args.rapide else 4000)
    B = args.bootstrap if args.bootstrap is not None else (100 if args.rapide else 1000)

    M.titre("Cas pratique : rendements du S&P 500 et risque de marché")
    df = charger_rendements()
    app = df[df.date <= FIN_APPRENTISSAGE]
    test = df[df.date > FIN_APPRENTISSAGE]
    x_tr = torch.tensor(app.r.values).reshape(-1, 1)
    x_te = torch.tensor(test.r.values).reshape(-1, 1)
    p_app = f"{app.date.dt.year.min()}-{app.date.dt.year.max()}"
    p_test = f"{test.date.dt.year.min()}-{test.date.dt.year.max()}"
    desc = pd.DataFrame([descriptif(app, f"apprentissage {p_app}"), descriptif(test, f"évaluation {p_test}")])
    M.sauver_tab(desc, "cas_pratique_descriptif")
    M.log(desc.to_string(index=False))

    # --- 1. Estimation : EM classique pour K = 1 à 6, EM variationnel pour Kmax = 6 ----------
    em = {K: A.em_classique(x_tr, K, n_init=10, graine=42) for K in range(1, 7)}
    K_bic = min(em, key=lambda k: em[k]["bic"])
    vb = A.em_variationnel(x_tr, 6, alpha0=1 / 6, n_init=10, graine=42)
    P = vb["P"]
    actives = (vb["Nk"] >= 1).nonzero().flatten()

    def ll_em(res, x):
        return float(A._etape_e(x, res["pi"], res["mu"], res["cov"])[1].mean())

    lignes = []
    for nom, res in [("Gaussienne unique (EM, K = 1)", em[1]),
                     (f"EM classique, K choisi par BIC (K = {K_bic})", em[K_bic]),
                     ("EM classique, K = 6 imposé", em[6])]:
        lignes.append({"modele": nom, "composantes": res["pi"].shape[0],
                       "loglik_moy_apprentissage": round(ll_em(res, x_tr), 4),
                       "loglik_moy_evaluation": round(ll_em(res, x_te), 4), "BIC": round(res["bic"], 1)})
    lignes.append({"modele": f"EM variationnel, Kmax = 6 ({len(actives)} actives), prédictive a posteriori",
                   "composantes": len(actives),
                   "loglik_moy_apprentissage": round(float(R.log_predictive_variationnel(x_tr, P).mean()), 4),
                   "loglik_moy_evaluation": round(float(R.log_predictive_variationnel(x_te, P).mean()), 4),
                   "BIC": None})
    tab_mod = pd.DataFrame(lignes)
    M.sauver_tab(tab_mod, "cas_pratique_modeles")
    M.log(tab_mod.to_string(index=False))
    ll_g = tab_mod.loglik_moy_evaluation[0]
    for i in range(1, len(tab_mod)):
        M.log(f"H4 pour '{tab_mod.modele[i]}' : "
              f"{'soutenue' if tab_mod.loglik_moy_evaluation[i] > ll_g else 'non soutenue'} "
              f"(écart de log-vraisemblance moyenne hors échantillon : {tab_mod.loglik_moy_evaluation[i] - ll_g:+.4f})")

    # --- 2. Value-at-risk, Expected Shortfall, test de Kupiec ------------------------------------
    pi_g, mu_g, sg_g = params_em(em[1])
    pi_b, mu_b, sg_b = params_em(em[K_bic])
    pi_d, mu_d, sg_d = R.echantillonner_posterieur_gmm_1d(P, S, graine=7)
    T = len(x_te)
    r_te = x_te.flatten()
    g_boot = A.generateur(11)
    var_boot = {a: [] for a in NIVEAUX}
    for b in range(B):                                       # bootstrap non paramétrique de l'EM classique
        idx = torch.randint(len(x_tr), (len(x_tr),), generator=g_boot)
        e = A.em_classique(x_tr[idx], K_bic, n_init=1, graine=b)
        pi_e, mu_e, sg_e = params_em(e)
        for a in NIVEAUX:
            var_boot[a].append(float(R.quantile_melange_gauss(a, pi_e, mu_e, sg_e)[0]))

    lignes, var_draws = [], {}
    for a in NIVEAUX:
        sources = []
        for nom, (pi_, mu_, sg_) in [("Gaussienne unique", (pi_g, mu_g, sg_g)),
                                     (f"Mélange EM (K = {K_bic})", (pi_b, mu_b, sg_b))]:
            q = R.quantile_melange_gauss(a, pi_, mu_, sg_)
            es = R.es_melange_gauss(a, q, pi_, mu_, sg_)
            sources.append((nom, float(q[0]), float(es[0]), None))
        draws = R.quantile_melange_gauss(a, pi_d, mu_d, sg_d)               # une VaR par tirage a posteriori
        var_draws[a] = draws
        lo_, hi_ = float(torch.quantile(draws, 0.025)), float(torch.quantile(draws, 0.975))
        # VaR prédictive a posteriori : quantile de la moyenne des fonctions de répartition
        bas, haut = float(draws.min()) - 5.0, float(draws.max()) + 5.0
        for _ in range(100):
            mil = 0.5 * (bas + haut)
            F = float(R.cdf_melange_gauss(torch.full((S,), mil), pi_d, mu_d, sg_d).mean())
            bas, haut = (mil, haut) if F < a else (bas, mil)
        q_pred = 0.5 * (bas + haut)
        # ES prédictive : moyenne sur les tirages de E[X 1{X <= q}] divisée par a (la moyenne des F_s(q) vaut a)
        es_pred = float(R.es_melange_gauss(a, torch.full((S,), q_pred), pi_d, mu_d, sg_d).mean())
        sources.append(("Mélange variationnel (prédictive)", q_pred, es_pred, (lo_, hi_)))
        for nom, q, es, ic in sources:
            x = int((r_te < q).sum())
            lr, pv = R.kupiec(x, T, a)
            lignes.append({"niveau": a, "modele": nom, "VaR_pct": round(q, 3), "ES_pct": round(es, 3),
                           "IC95_VaR": (f"[{ic[0]:.3f} ; {ic[1]:.3f}]" if ic else None),
                           "exceptions": x, "exceptions_attendues": round(a * T, 1),
                           "taux_observe": round(x / T, 4), "Kupiec_LR": round(lr, 2),
                           "Kupiec_p": round(pv, 4)})
        bs = torch.tensor(var_boot[a])
        lignes.append({"niveau": a, "modele": f"Bootstrap EM (K = {K_bic}, B = {B})",
                       "VaR_pct": round(float(bs.mean()), 3), "ES_pct": None,
                       "IC95_VaR": f"[{float(torch.quantile(bs, 0.025)):.3f} ; {float(torch.quantile(bs, 0.975)):.3f}]",
                       "exceptions": None, "exceptions_attendues": None, "taux_observe": None,
                       "Kupiec_LR": None, "Kupiec_p": None})
    tab_var = pd.DataFrame(lignes)
    M.sauver_tab(tab_var, "cas_pratique_var")
    M.log(tab_var.to_string(index=False))
    g1 = tab_var[(tab_var.niveau == 0.01) & (tab_var.modele == "Gaussienne unique")].iloc[0]
    M.log(f"H5 : exceptions de la VaR gaussienne à 1 % : {g1.exceptions} observées pour "
          f"{g1.exceptions_attendues} attendues, p de Kupiec = {g1.Kupiec_p} : "
          f"{'rejet' if g1.Kupiec_p < 0.05 else 'pas de rejet'} au seuil de 5 %.")

    # --- 3. Régimes de marché : Baum-Welch à émissions gaussiennes -------------------------------
    meilleur = max((A.baum_welch([x_tr.flatten()], 2, emission="gauss", n_iter=150, tol=1e-6, graine=s)
                    for s in range(3)), key=lambda d: d["loglik"])
    ordre = torch.argsort(meilleur["var"])                    # état 0 : calme, état 1 : agité
    Am = meilleur["A"][ordre][:, ordre]
    mu_h = meilleur["mu"][ordre]
    var_h = meilleur["var"][ordre]
    pi0 = meilleur["pi0"][ordre]
    stat = torch.linalg.matrix_power(Am, 2000)[0]
    lignes = []
    for k, nom in enumerate(["calme", "agité"]):
        lignes.append({"etat": nom, "moyenne_pct_jour": round(float(mu_h[k]), 4),
                       "volatilite_annualisee_pct": round(float(var_h[k].sqrt()) * math.sqrt(252), 2),
                       "probabilite_stationnaire": round(float(stat[k]), 3),
                       "duree_moyenne_jours": round(1.0 / (1.0 - float(Am[k, k])), 1)})
    tab_h = pd.DataFrame(lignes)
    M.sauver_tab(tab_h, "cas_pratique_hmm")
    M.log(tab_h.to_string(index=False))
    M.log(f"Matrice de transition (calme, agité) : {Am.round(decimals=4).tolist()}")
    tout = torch.tensor(df.r.values)
    logB = -0.5 * (A.LOG2PI + torch.log(var_h)[None] + (tout[:, None] - mu_h[None]) ** 2 / var_h[None])
    gamma, _, _ = A._fb_normalise(Am, logB, pi0)
    df["p_agite"] = gamma[:, 1].numpy()
    M.sauver_tab(df[["date", "r", "p_agite"]].round(4), "cas_pratique_regimes")

    # --- Figures ----------------------------------------------------------------------------------
    grille = torch.linspace(-6, 6, 600)
    fig = go.Figure()
    fig.add_histogram(x=app.r.tolist(), histnorm="probability density", nbinsx=140, name=f"rendements {p_app}",
                      marker=dict(color="#B8C4D6"), opacity=0.9)
    dens_g = torch.exp(R.log_densite_gauss_1d(grille, pi_g, mu_g, sg_g))
    dens_b = torch.exp(R.log_densite_gauss_1d(grille, pi_b, mu_b, sg_b))
    dens_v = torch.exp(R.log_predictive_variationnel(grille.reshape(-1, 1), P))
    fig.add_scatter(x=grille.tolist(), y=dens_g.tolist(), mode="lines", name="gaussienne unique",
                    line=dict(color=M.ORANGE, width=2.5, dash="dash"))
    fig.add_scatter(x=grille.tolist(), y=dens_b.tolist(), mode="lines", name=f"mélange EM (K = {K_bic})",
                    line=dict(color=M.BLUE, width=2.5))
    fig.add_scatter(x=grille.tolist(), y=dens_v.tolist(), mode="lines",
                    name=f"mélange variationnel ({len(actives)} actives), prédictive",
                    line=dict(color=M.NAVY, width=2.5))
    fig.update_xaxes(title_text="rendement journalier (%)", range=[-6, 6])
    fig.update_yaxes(title_text="densité (échelle logarithmique)", type="log", range=[-4, 0.5])
    M.gabarit(fig, "Distribution des rendements du S&P 500 : les queues épaisses exigent un mélange", 1000, 600,
              source=f"N = {len(app)} jours, kurtosis excédentaire {app.r.kurt():.1f} (0 pour une loi normale).")
    M.sauver_fig(fig, "cas_distribution")

    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.12,
                        subplot_titles=("EM classique : critères d'information", "EM variationnel : N_k par composante"))
    Ks = list(em.keys())
    fig.add_scatter(x=Ks, y=[em[k]["bic"] for k in Ks], mode="lines+markers", name="BIC",
                    line=dict(color=M.NAVY, width=2.5), marker=dict(size=9), row=1, col=1)
    fig.add_scatter(x=Ks, y=[em[k]["aic"] for k in Ks], mode="lines+markers", name="AIC",
                    line=dict(color=M.SKY, width=2.5), marker=dict(size=9, symbol="diamond"), row=1, col=1)
    fig.add_scatter(x=[K_bic], y=[em[K_bic]["bic"]], mode="markers", showlegend=False,
                    marker=dict(size=18, symbol="star", color=M.ORANGE), row=1, col=1)
    ordre_nk = torch.argsort(vb["Nk"], descending=True)
    fig.add_bar(x=[f"k={int(k) + 1}" for k in ordre_nk], y=[max(float(vb["Nk"][k]), 1e-3) for k in ordre_nk],
                marker_color=[M.NAVY if float(vb["Nk"][k]) >= 1 else "#B8C4D6" for k in ordre_nk],
                name="N_k", showlegend=False, row=1, col=2)
    fig.add_hline(y=1, line=dict(color=M.ORANGE, dash="dash"), annotation_text="seuil d'activité N_k = 1",
                  annotation_position="top right", row=1, col=2)
    fig.update_xaxes(title_text="nombre de composantes K", dtick=1, row=1, col=1)
    fig.update_xaxes(title_text="composante", row=1, col=2)
    fig.update_yaxes(title_text="critère (plus bas = meilleur)", row=1, col=1)
    fig.update_yaxes(title_text="nombre effectif d'observations N_k", type="log", row=1, col=2)
    M.gabarit(fig, "Choix du nombre de composantes sur les rendements", 1150, 560,
              source="Barres grises : composantes élaguées (N_k < 1). Étoile : minimum du BIC.")
    M.sauver_fig(fig, "cas_selection")

    a = 0.01
    d = var_draws[a].tolist()
    q_em = float(R.quantile_melange_gauss(a, pi_b, mu_b, sg_b)[0])
    q_g = float(R.quantile_melange_gauss(a, pi_g, mu_g, sg_g)[0])
    q_pred = float(tab_var[(tab_var.niveau == a) & (tab_var.modele == "Mélange variationnel (prédictive)")].VaR_pct.iloc[0])
    bs = torch.tensor(var_boot[a])
    emp_te = float(torch.quantile(r_te, a))
    fig = go.Figure()
    fig.add_histogram(x=d, histnorm="probability density", nbinsx=60, name="VaR 1 % sous q(θ) (tirages a posteriori)",
                      marker=dict(color=M.SKY), opacity=0.75)
    fig.add_histogram(x=bs.tolist(), histnorm="probability density", nbinsx=30,
                      name=f"VaR 1 % de l'EM classique, bootstrap (B = {B})", marker=dict(color=M.ORANGE), opacity=0.55)
    for x_, nom, c, dash in [(q_g, "gaussienne unique", M.GRIS, "dot"), (q_em, f"mélange EM (K = {K_bic})", M.BLUE, "dash"),
                             (q_pred, "mélange variationnel (prédictive)", M.NAVY, "solid"),
                             (emp_te, f"quantile empirique {p_test} (ex post)", M.VERT, "dashdot")]:
        fig.add_vline(x=x_, line=dict(color=c, width=2.5, dash=dash))
        fig.add_scatter(x=[None], y=[None], mode="lines", line=dict(color=c, width=2.5, dash=dash), name=nom)
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title_text="VaR à 1 jour au niveau 1 % (rendement, %)")
    fig.update_yaxes(title_text="densité")
    M.gabarit(fig, "Incertitude sur la VaR à 1 % : loi a posteriori contre bootstrap", 1050, 600,
              source=f"Apprentissage {p_app} ; {S} tirages a posteriori. Plus la valeur est négative, plus la perte est forte.")
    M.sauver_fig(fig, "cas_var")

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06, row_heights=[0.6, 0.4])
    fig.add_scatter(x=df.date, y=df.r, mode="lines", line=dict(color=M.NAVY, width=1), name="rendement journalier",
                    row=1, col=1)
    fig.add_scatter(x=df.date, y=df.p_agite, mode="lines", line=dict(color=M.ORANGE, width=1.5),
                    name="probabilité a posteriori de l'état agité", fill="tozeroy", row=2, col=1)
    fig.add_shape(type="line", xref="x", yref="paper", x0=FIN_APPRENTISSAGE, x1=FIN_APPRENTISSAGE, y0=0, y1=1,
                  line=dict(color=M.GRIS, dash="dash", width=2))
    fig.add_annotation(xref="x", yref="paper", x=FIN_APPRENTISSAGE, y=1.0, text="fin de l'apprentissage",
                       showarrow=False, xanchor="right", yanchor="bottom", font=dict(size=11, color=M.GRIS))
    fig.update_yaxes(title_text="rendement (%)", row=1, col=1)
    fig.update_yaxes(title_text="P(état agité | données)", range=[0, 1.02], row=2, col=1)
    fig.update_xaxes(title_text="date", row=2, col=1)
    M.gabarit(fig, "Régimes de marché par Baum-Welch à émissions gaussiennes (deux états)", 1100, 680,
              source=f"Paramètres estimés sur {p_app} puis appliqués à toute la période ; probabilités lissées (forward-backward).")
    M.sauver_fig(fig, "cas_regimes")

    import json
    (M.SORTIE / "cas_pratique_environnement.json").write_text(json.dumps(M.environnement(), indent=2), encoding="utf-8")
    M.log("\nCas pratique terminé. Sorties dans resultats/ (fichiers cas_*).")


if __name__ == "__main__":
    main()
