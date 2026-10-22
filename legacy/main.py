"""
================================================================================
EXPÉRIENCES : comparaison entre l'EM classique et l'EM variationnel
Kana Tiodong Icare Brichel, Master 2 SDIA, ENSPD, Université de Douala
================================================================================

PyTorch + Plotly + Pandas. Aucun modèle prêt à l'emploi n'est utilisé : les
algorithmes sont dans algorithmes.py.

Expériences :
    00  Validation numérique (exemples du chapitre 1, propriétés théoriques)
    01  Comparaison à K = 6 composantes imposées (sections 2.3.1 à 2.3.4)
    02  Sensibilité au prior alpha0 (2.3.5)
    03  Scalabilité (2.3.6)
    04  Nombre de composantes correctement spécifié, K = 3 (2.3.7)
    05  Convergence de l'ELBO (2.3.8)
    06  Robustesse à l'initialisation (2.3.9)
    07  Type de covariance (2.3.10)
    08  Jeu réel Iris (2.3.11)
    09  Valeurs aberrantes (2.3.12)
    10  Sélection de modèle BIC / AIC (2.2.3)
    11  Variantes (SEM, EM online, SVI), Baum-Welch, LDA
    12  Réplication sur jeux de données indépendants, intervalles de confiance

Utilisation :
    python main.py                  # tout exécuter
    python main.py --exp 1 2 5      # seulement certaines expériences
    python main.py --rapide         # tailles et répétitions réduites

Sorties dans resultats/ : tableaux (.csv), figures (.html et .png), journal.txt,
environnement.json. Les figures du texte sont copiées dans figures/.

Bibliothèques : pip install torch pandas plotly kaleido
================================================================================
"""

from __future__ import annotations

import argparse
import math
import re
import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import torch
from plotly.subplots import make_subplots

import algorithmes as A

DOSSIER = Path(__file__).parent
SORTIE = DOSSIER / "resultats"
SORTIE.mkdir(exist_ok=True)

# 
# Charte graphique (NexCQISolutions) : Navy, Blue, Sky ; Montserrat avec repli
# 
NAVY, BLUE, SKY, CLAIR = "#14377B", "#2E86C8", "#38A1E8", "#F7F7FB"
GRIS, ORANGE, VERT = "#7A8CA8", "#E07B39", "#3C9D6E"
PALETTE = [NAVY, BLUE, SKY, GRIS, ORANGE, VERT, "#B8C4D6", "#8E5BA8"]
POLICE = "Montserrat, Helvetica, Arial, sans-serif"
# couleurs bien distinctes pour les composantes d'un mélange (daltonisme : bleu, orange, vert, violet)
COMP = [NAVY, ORANGE, VERT, "#8E5BA8", SKY, GRIS]


def gabarit(fig, titre, largeur=900, hauteur=520, legende="bas", source=None):
    """Gabarit commun : titre, police, légende lisible, note de source en bas de figure."""
    if legende == "droite":
        leg = dict(bgcolor="white", bordercolor=GRIS, borderwidth=1, orientation="v",
                   x=1.02, xanchor="left", y=1, yanchor="top", font=dict(size=12))
    else:
        leg = dict(bgcolor="white", orientation="h", x=0, xanchor="left", y=-0.22, yanchor="top",
                   font=dict(size=13))
    fig.update_layout(title=dict(text=titre, font=dict(color=NAVY, size=18), x=0.01),
                      font=dict(family=POLICE, color=NAVY, size=13), paper_bgcolor="white",
                      plot_bgcolor=CLAIR, width=largeur, height=hauteur, legend=leg,
                      colorway=PALETTE, margin=dict(l=70, r=30 if legende == "bas" else 20, t=90, b=170))
    fig.update_xaxes(gridcolor="white", zeroline=False, showline=True, linecolor=GRIS, ticks="outside")
    fig.update_yaxes(gridcolor="white", zeroline=False, showline=True, linecolor=GRIS, ticks="outside")
    if source:
        fig.add_annotation(text=source, xref="paper", yref="paper", x=0,
                           y=-0.45 if legende == "bas" else -0.2,
                           showarrow=False, xanchor="left", font=dict(size=11, color=GRIS))
    return fig


FIGURES: dict = {}          # nom -> figure Plotly, pour les afficher dans le carnet


def sauver_fig(fig, nom):
    FIGURES[nom] = fig
    fig.write_html(SORTIE / f"{nom}.html", include_plotlyjs="cdn")
    try:
        fig.write_image(SORTIE / f"{nom}.png", scale=2)
    except Exception as e:                      # kaleido absent ou navigateur indisponible
        log(f"  (PNG non produit pour {nom} : {type(e).__name__})")


def sauver_tab(df, nom):
    df.to_csv(SORTIE / f"{nom}.csv", index=False, encoding="utf-8")


# ------------------------------------------------------------------------------
# Journal
# ------------------------------------------------------------------------------
_JOURNAL: list[str] = []


def log(msg=""):
    print(msg)
    _JOURNAL.append(str(msg))


def titre(msg):
    log("\n" + "=" * 78)
    log(msg)
    log("=" * 78)


def arr(t, nd=3):
    return [round(float(v), nd) for v in t]


def ellipse(mu, cov, n_sigma=2.0, n=80):
    vals, vecs = torch.linalg.eigh(cov)
    theta = torch.linspace(0, 2 * math.pi, n)
    cercle = torch.stack([torch.cos(theta), torch.sin(theta)])
    pts = vecs @ (n_sigma * torch.sqrt(vals.clamp(min=0))[:, None] * cercle)
    return (mu[0] + pts[0]).tolist(), (mu[1] + pts[1]).tolist()


def jeu_ref(graine=42):
    return A.jeu_reference(graine)


# ==============================================================================
# 00  VALIDATION DES EXEMPLES NUMÉRIQUES DU CHAPITRE 1
# ==============================================================================

X8 = torch.tensor([0.5, 1.0, 1.2, 1.8, 7.1, 7.5, 8.0, 8.3]).reshape(-1, 1)


def exp00_validation():
    titre("00  Validation des exemples numériques du chapitre 1")

    #  Tableau 1.2 : EM classique, N = 8, K = 2, init mu=(2,6), sigma=2, pi=0,5 
    pi = torch.tensor([0.5, 0.5]); mu = torch.tensor([[2.0], [6.0]])
    cov = torch.tensor([4.0, 4.0]).reshape(2, 1, 1)
    lignes = [{"iteration": 0, "mu1": 2.0, "mu2": 6.0, "sigma1": 2.0, "sigma2": 2.0,
               "pi1": 0.5, "pi2": 0.5, "loglik": None}]
    for it in range(1, 11):
        r, _ = A._etape_e(X8, pi, mu, cov)
        pi, mu, cov = A._etape_m(X8, r, "full", 0.0)
        _, ln = A._etape_e(X8, pi, mu, cov)               # log-vraisemblance de theta^t (après l'étape M)
        lignes.append({"iteration": it, "mu1": float(mu[0]), "mu2": float(mu[1]),
                       "sigma1": float(cov[0].sqrt()), "sigma2": float(cov[1].sqrt()),
                       "pi1": float(pi[0]), "pi2": float(pi[1]), "loglik": float(ln.sum())})
    df = pd.DataFrame(lignes).round(3)
    sauver_tab(df, "00_tableau_1_2_em_8_points")
    log("Tableau 1.2 recalculé (EM classique, 8 observations) :")
    log(df.to_string(index=False))
    conv = df.iloc[-1]
    fig = go.Figure()
    d = df.iloc[1:]
    fig.add_scatter(x=d.iteration, y=d.loglik, mode="lines+markers+text", line=dict(color=NAVY, width=2.5),
                    marker=dict(size=10), text=[f"{v:.2f}" if i < 3 else "" for i, v in enumerate(d.loglik)],
                    textposition="top center",
                    name="log-vraisemblance \u2113(\u03b8\u1d57)")
    fig.update_xaxes(title_text="itération t", dtick=1, range=[0.5, 10.5])
    fig.update_yaxes(title_text="log-vraisemblance totale")
    gabarit(fig, "EM classique sur 8 observations (K = 2) : croissance de la log-vraisemblance",
            source="Initialisation : mu = (2 ; 6), sigma = 2, poids 0,5. Valeur stationnaire atteinte en 3 itérations.")
    sauver_fig(fig, "00_log_vraisemblance_8_points")
    log("Moyennes empiriques des deux groupes : "
        f"{float(X8[:4].mean()):.3f} et {float(X8[4:].mean()):.3f}")

    #  Équation (1.10) : densité en x = 2,0 
    def dens(x, p1, p2):
        def n(x, m, s):
            return math.exp(-0.5 * ((x - m) / s) ** 2) / (s * math.sqrt(2 * math.pi))
        return 0.5 * n(x, *p1) + 0.5 * n(x, *p2)
    d_recalc = dens(2.0, (float(conv.mu1), float(conv.sigma1)), (float(conv.mu2), float(conv.sigma2)))
    log(f"Densité du mélange ajusté en x = 2,0 (éq. 1.10) : {d_recalc:.4f}")

    #  Exemple Dirichlet (éq. 1.12) --
    a = torch.tensor([1 + 7.0, 1 + 4.0, 1 + 1.0])
    log(f"Dirichlet a posteriori {a.tolist()} ; E[pi] = {arr(a / a.sum())}")

    #  Tableau 1.4 : forward-backward 
    Amat = torch.tensor([[0.7, 0.3], [0.4, 0.6]])
    Bmat = torch.tensor([[0.1, 0.9], [0.8, 0.2]])          # colonnes : Pa (0), NPa (1)
    obs = torch.tensor([1, 0, 0])                          # NPa, Pa, Pa
    fb = A.forward_backward(Amat, Bmat, torch.tensor([0.6, 0.4]), obs)
    t14 = pd.DataFrame({"t": [1, 2, 3], "alpha_B": fb["alpha"][:, 0], "alpha_P": fb["alpha"][:, 1],
                        "beta_B": fb["beta"][:, 0], "beta_P": fb["beta"][:, 1],
                        "gamma_B": fb["gamma"][:, 0], "gamma_P": fb["gamma"][:, 1]}).round(3)
    sauver_tab(t14, "00_tableau_1_4_forward_backward")
    log("Tableau 1.4 recalculé (forward-backward) :")
    log(t14.to_string(index=False))
    log(f"p(O) = {fb['proba']:.4f}")

    #  Tableau 1.5 : EM variationnel, N = 8, Kmax = 3 --
    pr = A.priori_diffus(X8, alpha0=1 / 3, beta0=1e-3)
    sorties = []
    for init in ("prior", "kmeans"):
        for graine in range(5):
            v = A.em_variationnel(X8, 3, priori=pr, init=init, graine=graine)
            ordre = torch.argsort(v["Nk"], descending=True)
            sorties.append({"init": init, "graine": graine, "iterations": v["n_iter"],
                            "alpha": arr(v["alpha"][ordre]), "m": arr(v["m"][ordre].flatten()),
                            "actives": v["n_actives"]})
    dfv = pd.DataFrame(sorties)
    sauver_tab(dfv, "00_tableau_1_5_vb_8_points")
    log("Tableau 1.5 recalculé (EM variationnel, Kmax = 3, alpha0 = 1/3) :")
    log(dfv.to_string(index=False))
    ref = sorties[0]

    #  Propriétés théoriques sur le jeu de référence 
    X, y = jeu_ref()
    em = A.em_classique(X, 6, init="aleatoire", graine=42)
    diffs = torch.tensor(em["ll_hist"])
    mono = bool(((diffs[1:] - diffs[:-1]) > -1e-9).all())
    r, _ = A._etape_e(X, em["pi"], em["mu"], em["cov"])
    F = A.energie_libre_em(X, r, em["pi"], em["mu"], em["cov"])
    log(f"EM : log-vraisemblance croissante à chaque itération : {mono}")
    log(f"Neal et Hinton : F(q*, theta) = {F:.6f} ; log-vraisemblance = {em['loglik']:.6f} "
        f"(écart {abs(F - em['loglik']):.2e})")
    vb = A.em_variationnel(X, 6, alpha0=1 / 6, graine=42)
    h = torch.tensor(vb["elbo_hist"])
    mono_v = bool(((h[1:] - h[:-1]) > -1e-8).all())
    log(f"EM variationnel : ELBO croissant à chaque itération : {mono_v} ; "
        f"ELBO final {vb['elbo']:.2f} <= log-vraisemblance maximale de l'EM {em['loglik']:.2f} : "
        f"{vb['elbo'] <= em['loglik']}")


# ==============================================================================
# 01  COMPARAISON K = 6
# ==============================================================================

def _ligne(nom, res, X, y):
    return {"modele": nom, "composantes_actives": int((res["Nk"] >= 1).sum()),
            "ARI": round(A.indice_rand_ajuste(y, res["labels"]), 3),
            "silhouette": round(A.silhouette(X, res["labels"]), 3),
            "iterations": res["n_iter"], "converge": res["converge"],
            "degenere": res["degenere"], "temps_s": round(res["temps"], 3),
            "poids": arr(res["pi"])}


def exp01_comparaison_k6():
    titre("01  Comparaison K = 6 (sections 2.3.1 à 2.3.4)")
    X, y = jeu_ref()
    fig = go.Figure()
    for g_, nom_g, c in [(0, "groupe centré en (0 ; 0)", NAVY), (1, "groupe centré en (5 ; 5)", ORANGE),
                         (2, "groupe centré en (0 ; 5)", VERT)]:
        m_ = y == g_
        fig.add_scatter(x=X[m_, 0].tolist(), y=X[m_, 1].tolist(), mode="markers", name=nom_g,
                        marker=dict(size=7, color=c, opacity=0.7))
    fig.update_xaxes(title_text="x\u2081")
    fig.update_yaxes(title_text="x\u2082", scaleanchor="x", scaleratio=1)
    gabarit(fig, "Jeu de données synthétique : trois groupes gaussiens de 100 observations",
            800, 640, source="Écart-type de chaque groupe : 0,7 (variance 0,49). Les couleurs indiquent la vérité terrain.")
    sauver_fig(fig, "01_jeu_donnees")
    em = A.em_classique(X, 6, n_init=10, graine=42)
    em_alea = A.em_classique(X, 6, init="aleatoire", graine=42)
    vb_m = A.em_variationnel(X, 6, priori=A.priori_diffus(X, 1 / 6), n_init=10, graine=42)
    vb_s = A.em_variationnel(X, 6, alpha0=1 / 6, n_init=10, graine=42)
    vb_a = A.em_variationnel(X, 6, priori=A.priori_diffus(X, 1 / 6), init="prior", graine=42)
    df = pd.DataFrame([_ligne("EM classique (init k-means, 10 relances)", em, X, y),
                       _ligne("EM classique (init aléatoire, version 3.2.1)", em_alea, X, y),
                       _ligne("EM variationnel (priors diffus, init k-means)", vb_m, X, y),
                       _ligne("EM variationnel (priors empiriques)", vb_s, X, y),
                       _ligne("EM variationnel (init aléatoire, version 3.3.1)", vb_a, X, y)])
    sauver_tab(df, "01_comparaison_k6")
    log(df.to_string(index=False))
    log(f"ELBO final (priors empiriques) : {vb_s['elbo']:.2f} ; log-vraisemblance EM : {em['loglik']:.2f}")

    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.05,
                        subplot_titles=("EM classique (K = 6)", "EM variationnel (Kmax = 6, priors empiriques)"))
    for col, (res, nom, grp) in enumerate([(em, "em", "EM classique"), (vb_s, "vb", "EM variationnel")], start=1):
        mu = res["mu"] if nom == "em" else res["m"]
        ordre = torch.argsort(res["Nk"], descending=True).tolist()
        for rang, k in enumerate(ordre):
            nk, pik = float(res["Nk"][k]), float(res["pi"][k])
            couleur = COMP[rang % len(COMP)]
            masque = res["labels"] == k
            titre_groupe = grp if rang == 0 else None
            if nk < 1:
                fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                                         marker=dict(color="#B8C4D6", symbol="x"),
                                         name=f"k={k+1} élaguée (N_k={nk:.1f})", legendgroup=f"{nom}{k}",
                                         legendgrouptitle_text=titre_groupe), row=1, col=col)
                continue
            fig.add_trace(go.Scatter(x=X[masque, 0].tolist(), y=X[masque, 1].tolist(), mode="markers",
                                     marker=dict(size=6, color=couleur, opacity=0.65),
                                     name=f"k={k+1} : poids {pik:.2f}, N_k={nk:.0f}", legendgroup=f"{nom}{k}",
                                     legendgrouptitle_text=titre_groupe), row=1, col=col)
            ex, ey = ellipse(mu[k], res["cov"][k])
            fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", line=dict(color=couleur, width=2.5),
                                     legendgroup=f"{nom}{k}", showlegend=False, hoverinfo="skip"), row=1, col=col)
            fig.add_trace(go.Scatter(x=[float(mu[k][0])], y=[float(mu[k][1])], mode="markers",
                                     marker=dict(color="white", size=9, symbol="x",
                                                 line=dict(color=couleur, width=2)),
                                     legendgroup=f"{nom}{k}", showlegend=False, hoverinfo="skip"), row=1, col=col)
    fig.update_xaxes(title_text="x\u2081")
    fig.update_yaxes(title_text="x\u2082", col=1)
    gabarit(fig, "Partition obtenue avec 6 composantes : un groupe par couleur, ellipse à deux écarts-types",
            1250, 620, legende="droite",
            source="Jeu de référence : N = 300, trois groupes gaussiens (écart-type 0,7). "
                   "La croix marque le centre de chaque composante.")
    sauver_fig(fig, "01_ellipses")
    noms = [f"k={k+1}" for k in range(6)]
    fig = go.Figure()
    fig.add_bar(x=noms, y=arr(em["pi"]), name="EM classique", marker_color=BLUE,
                text=[f"{v:.2f}" for v in em["pi"]], textposition="outside")
    fig.add_bar(x=noms, y=arr(vb_s["pi"]), name="EM variationnel", marker_color=NAVY,
                text=[f"{v:.3f}" for v in vb_s["pi"]], textposition="outside")
    fig.add_hline(y=1 / 3, line=dict(color=ORANGE, dash="dash"),
                  annotation_text="poids vrai d'un groupe (1/3)", annotation_position="top right")
    fig.update_layout(barmode="group")
    fig.update_xaxes(title_text="composante du mélange")
    fig.update_yaxes(title_text="poids de mélange \u03c0_k", range=[0, 0.42])
    gabarit(fig, "Poids de mélange finaux : l'EM variationnel éteint les composantes en trop",
            source="Poids proche de 0 : composante élaguée (N_k < 1). Composantes ordonnées par numéro, pas par taille.")
    sauver_fig(fig, "01_poids")


# ==============================================================================
# 02  SENSIBILITÉ À alpha0
# ==============================================================================

def exp02_alpha0():
    titre("02  Sensibilité au prior de Dirichlet alpha0 (section 2.3.5)")
    X, y = jeu_ref()
    lignes = []
    for a0 in [0.001, 0.01, 0.1, 1.0, 10.0]:
        for nom, pr in [("priors diffus", A.priori_diffus(X, a0)), ("priors empiriques", A.priori_empirique(X, a0))]:
            v = A.em_variationnel(X, 6, priori=pr, n_init=10, graine=42)
            lignes.append({"alpha0": a0, "priors": nom, "composantes_actives": v["n_actives"],
                           "ARI": round(A.indice_rand_ajuste(y, v["labels"]), 3),
                           "poids": arr(v["pi"]), "iterations": v["n_iter"]})
    df = pd.DataFrame(lignes)
    sauver_tab(df, "02_sensibilite_alpha0")
    log(df.to_string(index=False))
    for a0, att in zip([0.001, 0.01, 0.1, 1.0, 10.0], [3, 3, 3, 6, 6]):
        v = df[(df.alpha0 == a0) & (df.priors == "priors diffus")].composantes_actives.iloc[0]
    fig = go.Figure()
    for nom, c, sym in [("priors diffus (beta0 = 1e-3, W0 = I)", NAVY, "circle"),
                        ("priors empiriques (beta0 = 1, W0 = covariance empirique)", SKY, "diamond")]:
        d = df[df.priors == ("priors diffus" if "diffus" in nom else "priors empiriques")]
        fig.add_scatter(x=d.alpha0, y=d.composantes_actives, mode="lines+markers+text", name=nom,
                        line=dict(color=c, width=2.5), marker=dict(size=10, symbol=sym),
                        text=d.composantes_actives.astype(str), textposition="top center")
    fig.add_hline(y=3, line=dict(color=GRIS, dash="dot"), annotation_text="nombre vrai de groupes",
                  annotation_position="bottom right")
    fig.update_xaxes(type="log", title_text="concentration du prior de Dirichlet \u03b1\u2080 (échelle logarithmique)")
    fig.update_yaxes(title_text="composantes actives (N_k \u2265 1)", range=[0, 7.5], dtick=1)
    gabarit(fig, "Nombre de composantes actives selon \u03b1\u2080 (Kmax = 6)",
            source="Jeu de référence, 10 initialisations, meilleure ELBO retenue.")
    sauver_fig(fig, "02_alpha0")


# ==============================================================================
# 03  SCALABILITÉ
# ==============================================================================

def _temps_scalabilite(n, d, n_rep):
    """Médiane de n_rep répétitions : temps jusqu'au modèle final, itérations et coût par itération (critère d'arrêt commun)."""
    import comparaison as C
    centres = torch.rand(3, d, generator=A.generateur(0)) * 10 - 5
    X, _ = A.generer_blobs(n // 3, centres, 0.8, 42)
    em = C.chronometrer(lambda: A.em_classique(X, 6, n_init=1, graine=42), n_rep)
    vb = C.chronometrer(lambda: A.em_variationnel(X, 6, alpha0=1 / 6, n_init=1, graine=42), n_rep)
    return em, vb


def exp03_scalabilite(rapide):
    titre("03  Scalabilité (section 2.3.6)")
    n_rep = 3 if rapide else 10
    tailles_n = [300, 1000, 5000] + ([] if rapide else [20000])
    dims = [2, 5, 10, 20] if not rapide else [2, 5, 10]
    lignes = []
    for param, valeurs in (("N (D=2)", tailles_n), ("D (N=2000)", dims)):
        for v in valeurs:
            em, vb = _temps_scalabilite(v if param.startswith("N") else 2001 // 3 * 3, 2 if param.startswith("N") else v, n_rep)
            lignes.append({"parametre": param, "valeur": v, "n_rep": n_rep,
                           "classique_s": round(em["temps_median"], 4), "variationnel_s": round(vb["temps_median"], 4),
                           "ratio": round(vb["temps_median"] / em["temps_median"], 1),
                           "iter_classique": em["iterations_mediane"], "iter_variationnel": vb["iterations_mediane"],
                           "cout_iter_classique_s": round(em["cout_par_iteration"], 5),
                           "cout_iter_variationnel_s": round(vb["cout_par_iteration"], 5),
                           "ratio_cout_iter": round(vb["cout_par_iteration"] / em["cout_par_iteration"], 1)})
    df = pd.DataFrame(lignes)
    sauver_tab(df, "03_scalabilite")
    log(df.to_string(index=False))
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.06,
                        subplot_titles=("Selon le nombre d'observations N (D = 2)", "Selon la dimension D (N = 2000)"))
    for col, p in enumerate(["N (D=2)", "D (N=2000)"], start=1):
        d = df[df.parametre == p]
        fig.add_scatter(x=d.valeur, y=d.classique_s, name="EM classique", mode="lines+markers",
                        line=dict(color=BLUE, width=2.5), marker=dict(size=9), showlegend=col == 1, row=1, col=col)
        fig.add_scatter(x=d.valeur, y=d.variationnel_s, name="EM variationnel", mode="lines+markers+text",
                        line=dict(color=NAVY, width=2.5), marker=dict(size=9), showlegend=col == 1,
                        text=[f"\u00d7{r:.1f}" for r in d.ratio], textposition="top center", row=1, col=col)
    fig.update_yaxes(type="log", tickvals=[0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10],
                     ticktext=["0,05", "0,1", "0,2", "0,5", "1", "2", "5", "10"])
    fig.update_yaxes(title_text="temps d'exécution (s, échelle log)", col=1)
    fig.update_xaxes(type="log", title_text="N (échelle log)", row=1, col=1,
                     tickvals=[300, 1000, 5000, 20000], ticktext=["300", "1 000", "5 000", "20 000"])
    fig.update_xaxes(title_text="D", row=1, col=2, tickvals=df[df.parametre == "D (N=2000)"].valeur.tolist())
    gabarit(fig, "Temps d'exécution des deux algorithmes (PyTorch, CPU)", 1100, 540,
            source="Médiane de répétitions (n_rep dans le tableau), critère d'arrêt commun. Étiquettes : rapport des temps jusqu'au modèle final ; "
                   "le coût par itération et le nombre d'itérations figurent dans le tableau 03_scalabilite.csv.")
    sauver_fig(fig, "03_scalabilite")
    log("Tableau et figure sortent du même run (même dataframe).")


# ==============================================================================
# 04  K = 3
# ==============================================================================

def exp04_k3():
    titre("04  Cas de référence K = 3 (section 2.3.7)")
    X, y = jeu_ref()
    em = A.em_classique(X, 3, n_init=10, graine=42)
    vb = A.em_variationnel(X, 3, alpha0=1 / 3, n_init=10, graine=42)
    df = pd.DataFrame([_ligne("EM classique K=3", em, X, y), _ligne("EM variationnel Kmax=3", vb, X, y)])
    sauver_tab(df, "04_k3")
    log(df.to_string(index=False))


# ==============================================================================
# 05  CONVERGENCE DE L'ELBO
# ==============================================================================

def exp05_elbo():
    titre("05  Convergence de l'ELBO (section 2.3.8)")
    X, y = jeu_ref()
    # mêmes appels que exp01 : un seul décompte d'itérations dans tout le mémoire (T0.1)
    vb = A.em_variationnel(X, 6, alpha0=1 / 6, n_init=10, graine=42)
    em = A.em_classique(X, 6, n_init=10, graine=42)
    h = torch.tensor(vb["elbo_hist"])
    log(f"ELBO : première valeur {h[0]:.2f}, dernière {h[-1]:.2f}, "
        f"croissance stricte : {bool((h[1:] > h[:-1]).all())}, itérations : {vb['n_iter']}")
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.12,
                        subplot_titles=("EM variationnel : ELBO", "EM classique : log-vraisemblance"))
    fig.add_scatter(x=list(range(1, len(h) + 1)), y=vb["elbo_hist"], mode="lines",
                    line=dict(color=NAVY, width=2.5), name="ELBO (éq. 1.31)", row=1, col=1)
    lh = em["ll_hist"]
    fig.add_scatter(x=list(range(1, len(lh) + 1)), y=lh, mode="lines", line=dict(color=BLUE, width=2.5),
                    name="log-vraisemblance \u2113(\u03b8)", row=1, col=2)
    fig.update_xaxes(title_text="itération")
    fig.update_yaxes(title_text="ELBO (valeur totale)", row=1, col=1)
    fig.update_yaxes(title_text="log-vraisemblance (valeur totale)", row=1, col=2)
    gabarit(fig, "Les deux critères croissent à chaque itération (jeu de référence, K = 6)", 1100, 520,
            source="ELBO exacte (éq. 1.31), constantes de normalisation incluses.")
    sauver_fig(fig, "05_convergence")
    sauver_tab(pd.DataFrame({"iteration": range(1, len(h) + 1), "elbo": h.tolist()}), "05_elbo_historique")


# ==============================================================================
# 06  ROBUSTESSE À L'INITIALISATION
# ==============================================================================

def exp06_initialisation(rapide):
    titre("06  Robustesse à l'initialisation (section 2.3.9)")
    X, y = jeu_ref()
    n_rep = 8 if rapide else 20
    lignes = []
    for init_em, init_vb, lib in [("kmeans", "kmeans", "init k-means"), ("aleatoire", "prior", "init aléatoire")]:
        act_em, act_vb, act_vs, ll_em, ari_vb = [], [], [], [], []
        for s in range(n_rep):
            e = A.em_classique(X, 6, init=init_em, graine=s, n_init=1)
            v = A.em_variationnel(X, 6, priori=A.priori_diffus(X, 1 / 6), init=init_vb, graine=s, n_init=1)
            vs = A.em_variationnel(X, 6, alpha0=1 / 6, init=init_vb, graine=s, n_init=1)
            act_vs.append(vs["n_actives"])
            act_em.append(int((e["Nk"] >= 1).sum())); act_vb.append(v["n_actives"])
            ll_em.append(e["loglik"]); ari_vb.append(A.indice_rand_ajuste(y, v["labels"]))
        for nom, act in [("EM classique", act_em), ("EM variationnel (priors diffus)", act_vb),
                         ("EM variationnel (priors empiriques)", act_vs)]:
            lignes.append({"initialisation": lib, "algorithme": nom, "n_repetitions": n_rep,
                           **{f"{c} actives": sum(a == c for a in act) for c in (3, 4, 5, 6)}})
        ll = torch.tensor(ll_em)
        log(f"[{lib}] log-vraisemblance EM : min {ll.min():.2f}, max {ll.max():.2f}, écart-type {ll.std():.2f} ; "
            f"ARI moyen EM variationnel {sum(ari_vb) / n_rep:.3f}")
    df = pd.DataFrame(lignes)
    sauver_tab(df, "06_initialisation")
    log(df.to_string(index=False))
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.05,
                        subplot_titles=("Initialisation par k-means", "Initialisation aléatoire"))
    couleurs = {"3 actives": VERT, "4 actives": SKY, "5 actives": ORANGE, "6 actives": NAVY}
    for col, ini in enumerate(["init k-means", "init aléatoire"], start=1):
        d = df[df.initialisation == ini]
        noms_alg = ["EM classique", "EM variationnel<br>priors diffus", "EM variationnel<br>priors empiriques"]
        for c, cl in couleurs.items():
            fig.add_bar(x=noms_alg, y=d[c].tolist(), name=c.replace("actives", "composantes actives"),
                        marker_color=cl, showlegend=col == 1, row=1, col=col)
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title_text=f"nombre d'exécutions sur {n_rep}", col=1)
    gabarit(fig, "Nombre de composantes actives selon l'algorithme et l'initialisation (Kmax = 6)", 1100, 600,
            source="Une seule initialisation par exécution (n_init = 1). Le vrai nombre de groupes est 3.")
    sauver_fig(fig, "06_initialisation")
    d = df[(df.initialisation == "init aléatoire") & (df.algorithme == "EM variationnel (priors empiriques)")].iloc[0]
    d = df[(df.initialisation == "init aléatoire") & (df.algorithme == "EM variationnel (priors diffus)")].iloc[0]
    d0 = df[(df.initialisation == "init aléatoire") & (df.algorithme == "EM classique")].iloc[0]


# ==============================================================================
# 07  TYPE DE COVARIANCE
# ==============================================================================

def exp07_covariance():
    titre("07  Sensibilité au type de covariance (section 2.3.10)")
    X, y = jeu_ref()
    lignes = []
    for ct in A.TYPES_COVARIANCE:
        e = A.em_classique(X, 6, cov_type=ct, n_init=10, graine=42)
        v = A.em_variationnel(X, 6, alpha0=1 / 6, cov_type=ct, n_init=10, graine=42)
        lignes.append({"covariance": ct, "ARI_classique": round(A.indice_rand_ajuste(y, e["labels"]), 3),
                       "ARI_variationnel": round(A.indice_rand_ajuste(y, v["labels"]), 3),
                       "actives_variationnel": v["n_actives"], "BIC_classique": round(e["bic"], 1)})
    df = pd.DataFrame(lignes)
    sauver_tab(df, "07_covariance")
    log(df.to_string(index=False))
    fig = go.Figure()
    fig.add_bar(x=df.covariance, y=df.ARI_classique, name="EM classique (K = 6)", marker_color=BLUE,
                text=[f"{v:.2f}" for v in df.ARI_classique], textposition="outside")
    fig.add_bar(x=df.covariance, y=df.ARI_variationnel, name="EM variationnel (Kmax = 6)", marker_color=NAVY,
                text=[f"{v:.2f}" for v in df.ARI_variationnel], textposition="outside")
    fig.update_layout(barmode="group")
    fig.update_xaxes(title_text="contrainte sur la covariance")
    fig.update_yaxes(title_text="indice de Rand ajusté (1 = partition parfaite)", range=[0, 1.12])
    gabarit(fig, "Qualité de la partition selon le type de covariance",
            source="Jeu de référence, 10 initialisations. EM variationnel : priors empiriques.")
    sauver_fig(fig, "07_covariance")
    for ct, ac, av in [("full", 0.708, 1.0), ("tied", 0.653, 1.0), ("diag", 0.677, 1.0), ("spherical", 0.677, 1.0)]:
        r = df[df.covariance == ct].iloc[0]
    log("Remarque : les variantes tied, diag et spherical de l'EM variationnel ne sont pas dérivées "
        "ici ; elles utilisent un prior Wishart partagé (tied) ou Gamma (diag, spherical), conjugués.")


# ==============================================================================
# 08  IRIS
# ==============================================================================

def charger_iris():
    chemin = DOSSIER / "data" / "iris.csv"
    if not chemin.exists():
        url = "https://archive.ics.uci.edu/ml/machine-learning-databases/iris/iris.data"
        pd.read_csv(url, header=None, names=["sepal_length", "sepal_width", "petal_length",
                                            "petal_width", "espece"]).to_csv(chemin, index=False)
    df = pd.read_csv(chemin)
    X = torch.tensor(df.iloc[:, :4].values, dtype=torch.float64)
    y = torch.tensor(pd.factorize(df.espece)[0])
    return X, y


def exp08_iris():
    titre("08  Jeu de données réel Iris (section 2.3.11)")
    X, y = charger_iris()
    em6 = A.em_classique(X, 6, n_init=10, graine=42)
    vb6 = A.em_variationnel(X, 6, alpha0=1 / 6, n_init=10, graine=42)
    em3 = A.em_classique(X, 3, n_init=10, graine=42)
    vb3 = A.em_variationnel(X, 3, alpha0=1 / 3, n_init=10, graine=42)
    df = pd.DataFrame([_ligne("EM classique K=6", em6, X, y), _ligne("EM variationnel Kmax=6", vb6, X, y),
                       _ligne("EM classique K=3", em3, X, y), _ligne("EM variationnel Kmax=3", vb3, X, y)])
    sauver_tab(df, "08_iris")
    log(df.to_string(index=False))
    fig = go.Figure()
    fig.add_bar(x=df.modele, y=df.ARI, name="indice de Rand ajusté", marker_color=NAVY,
                text=[f"{v:.2f}" for v in df.ARI], textposition="outside")
    fig.add_bar(x=df.modele, y=df.silhouette, name="silhouette", marker_color=SKY,
                text=[f"{v:.2f}" for v in df.silhouette], textposition="outside")
    fig.update_layout(barmode="group")
    fig.update_xaxes(title_text="modèle")
    fig.update_yaxes(title_text="valeur de la métrique", range=[0, 1.05])
    gabarit(fig, "Jeu de données Iris (N = 150, D = 4) : qualité des partitions",
            source="Les espèces versicolor et virginica se chevauchent : un ARI élevé n'est pas garanti "
                   "même avec le bon nombre de composantes.")
    sauver_fig(fig, "08_iris")


# ==============================================================================
# 09  VALEURS ABERRANTES
# ==============================================================================

def exp09_aberrantes():
    titre("09  Valeurs aberrantes (section 2.3.12)")
    X, y = jeu_ref()
    g = A.generateur(7)
    bruit = torch.rand(10, 2, generator=g) * 25 - 10
    Xa = torch.cat([X, bruit])
    em = A.em_classique(Xa, 6, n_init=10, graine=42)
    vb = A.em_variationnel(Xa, 6, alpha0=1 / 6, n_init=10, graine=42)
    lignes = []
    for nom, res in [("EM classique", em), ("EM variationnel", vb)]:
        traces = torch.stack([torch.trace(c) for c in res["cov"]])
        actif = res["Nk"] >= 1
        lignes.append({"modele": nom, "ARI_hors_aberrantes": round(A.indice_rand_ajuste(y, res["labels"][:300]), 3),
                       "composantes_actives": int(actif.sum()),
                       "trace_covariance_max": round(float(traces[actif].max()), 1),
                       "poids_plus_petit": round(float(res["pi"][actif].min()), 4)})
    df = pd.DataFrame(lignes)
    sauver_tab(df, "09_aberrantes")
    log(df.to_string(index=False))


# ==============================================================================
# 10  BIC / AIC
# ==============================================================================

def exp10_bic_aic():
    titre("10  Sélection de modèle par BIC et AIC (section 2.2.3)")
    X, y = jeu_ref()
    lignes = []
    for K in range(1, 9):
        e = A.em_classique(X, K, n_init=10, graine=42)
        lignes.append({"K": K, "loglik": round(e["loglik"], 2), "BIC": round(e["bic"], 2), "AIC": round(e["aic"], 2)})
    df = pd.DataFrame(lignes)
    sauver_tab(df, "10_bic_aic")
    log(df.to_string(index=False))
    kb, ka = int(df.K[df.BIC.idxmin()]), int(df.K[df.AIC.idxmin()])
    log(f"K* selon BIC : {kb} ; K* selon AIC : {ka}")
    fig = go.Figure()
    fig.add_scatter(x=df.K, y=df.BIC, name="BIC (éq. 2.4)", mode="lines+markers",
                    line=dict(color=NAVY, width=2.5), marker=dict(size=9))
    fig.add_scatter(x=df.K, y=df.AIC, name="AIC (éq. 2.5)", mode="lines+markers",
                    line=dict(color=SKY, width=2.5), marker=dict(size=9, symbol="diamond"))
    for crit, kk, c in [("BIC", kb, NAVY), ("AIC", ka, SKY)]:
        fig.add_scatter(x=[kk], y=[float(df.loc[df.K == kk, crit].iloc[0])], mode="markers", showlegend=False,
                        marker=dict(size=18, symbol="star", color=ORANGE, line=dict(color=c, width=1.5)))
    fig.add_vline(x=3, line=dict(color=GRIS, dash="dot"), annotation_text="K vrai = 3",
                  annotation_position="top right")
    fig.update_xaxes(title_text="nombre de composantes K", dtick=1)
    fig.update_yaxes(title_text="critère d'information (plus bas = meilleur)")
    gabarit(fig, "Sélection de K par BIC et AIC (EM classique)",
            source="Étoile : minimum de chaque critère. 10 initialisations par valeur de K, soit 80 exécutions de l'EM.")
    sauver_fig(fig, "10_bic_aic")


# ==============================================================================
# 11  VARIANTES, BAUM-WELCH, LDA
# ==============================================================================

CORPUS = [
    "le chat mange des croquettes et dort sur le canape",
    "le chien joue dans le jardin avec la balle",
    "le chat et le chien dorment ensemble le soir",
    "la bourse chute apres l annonce des taux d interet",
    "les actions technologiques progressent sur le marche financier",
    "la banque centrale releve son taux directeur cette semaine",
    "l equipe de football remporte le match a l exterieur",
    "le joueur marque un but decisif en fin de rencontre",
    "le championnat de football reprend ce week end",
    "le chat observe les oiseaux depuis la fenetre du salon",
    "les investisseurs surveillent la reaction des marches financiers",
    "l entraineur felicite ses joueurs apres la victoire",
]
THEME_VRAI = [0, 0, 0, 1, 1, 1, 2, 2, 2, 0, 1, 2]       # animaux, finance, football
MOTS_VIDES = {"le", "la", "les", "de", "des", "et", "en", "du", "un", "une", "ce", "cette", "son",
              "ses", "a", "sur", "dans", "avec", "depuis", "apres", "d", "l"}


def matrice_comptes(corpus):
    """Table document x mot (mots d'au moins 2 caractères, hors mots vides), construite avec pandas."""
    docs = [[m for m in re.findall(r"\b\w\w+\b", d.lower()) if m not in MOTS_VIDES] for d in corpus]
    df = pd.DataFrame([pd.Series(d).value_counts() for d in docs]).fillna(0.0)
    return df[sorted(df.columns)]


def exp11_variantes_hmm_lda(rapide):
    titre("11  Variantes de l'EM, Baum-Welch et LDA")
    X, y = jeu_ref()

    #  Variantes (tableau 1.3, sections 1.6.5 et 1.7.7) 
    lignes = []
    t0 = time.perf_counter(); e = A.em_classique(X, 3, n_init=3, graine=0); t = time.perf_counter() - t0
    lignes.append({"methode": "EM standard (batch)", "loglik": round(e["loglik"], 1),
                   "ARI": round(A.indice_rand_ajuste(y, e["labels"]), 3), "temps_s": round(t, 3)})
    t0 = time.perf_counter(); s = A.em_stochastique(X, 3, n_iter=150, graine=0); t = time.perf_counter() - t0
    ll = torch.tensor(s["ll_hist"]); non_mono = int((ll[1:] < ll[:-1] - 1e-9).sum())
    lignes.append({"methode": f"EM stochastique (SEM), {non_mono} baisses de log-vraisemblance",
                   "loglik": round(s["loglik"], 1), "ARI": round(A.indice_rand_ajuste(y, s["labels"]), 3),
                   "temps_s": round(t, 3)})
    t0 = time.perf_counter(); o = A.em_online(X, 3, taille_lot=30, n_epoques=5, graine=0); t = time.perf_counter() - t0
    lignes.append({"methode": "EM online (statistiques suffisantes)", "loglik": round(o["loglik"], 1),
                   "ARI": round(A.indice_rand_ajuste(y, o["labels"]), 3), "temps_s": round(t, 3)})
    pr = A.priori_empirique(X, 1 / 6)
    t0 = time.perf_counter(); vb = A.em_variationnel(X, 6, priori=pr, graine=42, n_init=3); t = time.perf_counter() - t0
    lignes.append({"methode": f"EM variationnel batch (Kmax=6, {vb['n_actives']} actives)", "loglik": None,
                   "ARI": round(A.indice_rand_ajuste(y, vb["labels"]), 3), "temps_s": round(t, 3)})
    t0 = time.perf_counter(); sv = A.svi_gmm(X, 6, pr, taille_lot=30, n_epoques=15, graine=0); t = time.perf_counter() - t0
    lignes.append({"methode": f"SVI (Kmax=6, {sv['n_actives']} actives)", "loglik": None,
                   "ARI": round(A.indice_rand_ajuste(y, sv["labels"]), 3), "temps_s": round(t, 3)})
    df = pd.DataFrame(lignes)
    sauver_tab(df, "11_variantes")
    log(df.to_string(index=False))

    #  Baum-Welch (section 1.6.6) -
    Amat = torch.tensor([[0.7, 0.3], [0.4, 0.6]])
    Bmat = torch.tensor([[0.1, 0.9], [0.8, 0.2]])
    T = 1000 if not rapide else 400
    obs = A.simuler_hmm(Amat, Bmat, torch.tensor([0.6, 0.4]), T, graine=1)
    _, _, ll_vrai = A._fb_normalise(Amat, torch.log(Bmat[:, obs].T), torch.tensor([0.6, 0.4]))
    bw = max((A.baum_welch([obs], 2, emission="discrete", V=2, n_iter=100 if not rapide else 60, tol=1e-9, graine=s_)
              for s_ in range(3)), key=lambda d: d["loglik"])
    perm = [0, 1] if bw["B"][0, 1] > bw["B"][1, 1] else [1, 0]      # états définis à une permutation près
    A_est = bw["A"][perm][:, perm]; B_est = bw["B"][perm]
    ll_hist = torch.tensor(bw["ll_hist"])
    log(f"Baum-Welch discret (T={T}) : log-vraisemblance croissante : "
        f"{bool(((ll_hist[1:] - ll_hist[:-1]) > -1e-8).all())}, {bw['n_iter']} itérations")
    log(f"  log-vraisemblance estimée {bw['loglik']:.2f} contre {ll_vrai:.2f} aux vrais paramètres "
        "(le maximum de vraisemblance peut dépasser la vraie valeur sur une séquence courte)")
    log(f"  A vrai {Amat.tolist()}  estimé {A_est.round(decimals=3).tolist()}")
    log(f"  B vrai {Bmat.tolist()}  estimé {B_est.round(decimals=3).tolist()}")
    g = A.generateur(5)
    z, r_ = 0, []
    Ag = torch.tensor([[0.95, 0.05], [0.10, 0.90]])
    sig = torch.tensor([0.5, 2.0]); mug = torch.tensor([0.1, -0.2])
    for _ in range(1500):
        r_.append(float(mug[z] + sig[z] * torch.randn(1, generator=g)))
        z = int(torch.multinomial(Ag[z], 1, generator=g))
    bg = A.baum_welch([torch.tensor(r_)], 2, emission="gauss", n_iter=200, tol=1e-8, graine=0)
    ordre = torch.argsort(bg["var"])
    log(f"Baum-Welch gaussien : sigma estimés {bg['var'][ordre].sqrt().round(decimals=3).tolist()} (vrais 0,5 et 2,0), "
        f"A estimée {bg['A'][ordre][:, ordre].round(decimals=3).tolist()} (vraie {Ag.tolist()})")

    #  LDA (section 3.1.1) --
    comptes_df = matrice_comptes(CORPUS)
    C = torch.tensor(comptes_df.values, dtype=torch.float64)
    mots = list(comptes_df.columns)
    meilleur = None
    for graine in range(10):
        res = A.lda_variationnel(C, 3, alpha=0.1, graine=graine)
        if meilleur is None or res["bornes"][-1] > meilleur["bornes"][-1]:
            meilleur = res
    b = torch.tensor(meilleur["bornes"])
    log(f"LDA : borne variationnelle croissante : {bool(((b[1:] - b[:-1]) > -1e-6).all())} ; "
        f"{meilleur['n_iter']} itérations ; meilleure borne {b[-1]:.2f} (10 graines)")
    lignes_t = []
    for k in range(3):
        top = [mots[i] for i in torch.argsort(meilleur["beta"][k], descending=True)[:6]]
        log(f"  Thème {k} : {', '.join(top)}")
        lignes_t.append({"theme": k, "mots": ", ".join(top)})
    sauver_tab(pd.DataFrame(lignes_t), "11_lda_themes")
    theta = pd.DataFrame(meilleur["theta"].numpy().round(2), columns=["T0", "T1", "T2"])
    theta.insert(0, "document", CORPUS)
    theta["theme_dominant"] = meilleur["theta"].argmax(1).tolist()
    theta["theme_vrai"] = THEME_VRAI
    sauver_tab(theta, "11_lda_documents")
    log(theta.drop(columns="document").to_string())
    dom = meilleur["theta"].argmax(1).tolist()
    purete = sum(max(sum(1 for d, v in zip(dom, THEME_VRAI) if d == k and v == t) for t in range(3))
                 for k in range(3)) / len(CORPUS)
    log(f"Pureté des documents (thème dominant contre thème vrai) : {purete:.2f}")


# ==============================================================================
# OUTILS STATISTIQUES (intervalles de confiance, écrits à la main)
# ==============================================================================

def ic_bootstrap(valeurs, n_boot=5000, niveau=0.95, graine=0):
    """Moyenne et intervalle de confiance bootstrap (percentiles) à 95 %."""
    v = torch.as_tensor(list(valeurs), dtype=torch.float64)
    idx = torch.randint(len(v), (n_boot, len(v)), generator=A.generateur(graine))
    moy = v[idx].mean(1)
    a = (1 - niveau) / 2
    return float(v.mean()), float(torch.quantile(moy, a)), float(torch.quantile(moy, 1 - a))


def ic_wilson(k, n, z=1.96):
    """Intervalle de Wilson à 95 % pour une proportion k / n."""
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    demi = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return p, max(0.0, centre - demi), min(1.0, centre + demi)


def environnement():
    """Informations de reproductibilité enregistrées avec les résultats."""
    import platform
    import sys
    import plotly
    return {"python": sys.version.split()[0], "torch": torch.__version__, "pandas": pd.__version__,
            "plotly": plotly.__version__, "systeme": platform.platform(),
            "cpu_threads": torch.get_num_threads(), "precision": str(torch.get_default_dtype())}


# ==============================================================================
# 12  RÉPLICATION STATISTIQUE (étude de type Monte-Carlo, limite reconnue en 2.5)
# ==============================================================================

def exp12_replication(rapide):
    """
    Hypothèses testées, fixées avant l'analyse :
      H1 : à K = 6 imposé, l'ARI moyen de l'EM variationnel dépasse celui de l'EM classique.
      H2 : l'EM variationnel retrouve exactement 3 composantes actives dans la majorité des jeux.
      H3 : le résultat de H1 et H2 dépend du choix des priors (priors diffus contre priors empiriques).
    Plan : R jeux de données indépendants (graines 1000 à 1000+R-1), mêmes paramètres génératifs,
    mêmes réglages algorithmiques, 10 initialisations par ajustement.
    """
    titre("12  Réplication statistique sur jeux de données indépendants")
    R = 8 if rapide else 30
    lignes = []
    for r in range(R):
        X, y = A.jeu_reference(1000 + r)
        essais = [("EM classique", A.em_classique(X, 6, n_init=10, graine=r)),
                  ("EM variationnel (priors diffus)",
                   A.em_variationnel(X, 6, priori=A.priori_diffus(X, 1 / 6), n_init=10, graine=r)),
                  ("EM variationnel (priors empiriques)",
                   A.em_variationnel(X, 6, alpha0=1 / 6, n_init=10, graine=r))]
        for nom, res in essais:
            lignes.append({"graine_donnees": 1000 + r, "modele": nom,
                           "ARI": A.indice_rand_ajuste(y, res["labels"]),
                           "silhouette": A.silhouette(X, res["labels"]),
                           "composantes_actives": int((res["Nk"] >= 1).sum()),
                           "iterations": res["n_iter"], "converge": res["converge"],
                           "degenere": res["degenere"], "temps_s": res["temps"]})
    brut = pd.DataFrame(lignes)
    sauver_tab(brut.round(4), "12_replication_brut")
    resume = []
    for nom, d in brut.groupby("modele", sort=False):
        m_ari, lo_ari, hi_ari = ic_bootstrap(d.ARI)
        m_sil, lo_sil, hi_sil = ic_bootstrap(d.silhouette)
        k3 = int((d.composantes_actives == 3).sum())
        p3, lo3, hi3 = ic_wilson(k3, len(d))
        resume.append({"modele": nom, "R": len(d), "ARI_moyen": round(m_ari, 3),
                       "ARI_IC95": f"[{lo_ari:.3f} ; {hi_ari:.3f}]", "ARI_ecart_type": round(float(d.ARI.std()), 3),
                       "silhouette_moyenne": round(m_sil, 3), "silhouette_IC95": f"[{lo_sil:.3f} ; {hi_sil:.3f}]",
                       "part_exactement_3_actives": round(p3, 3), "part_IC95_Wilson": f"[{lo3:.3f} ; {hi3:.3f}]",
                       "actives_moyennes": round(float(d.composantes_actives.mean()), 2),
                       "iterations_moyennes": round(float(d.iterations.mean()), 1),
                       "temps_moyen_s": round(float(d.temps_s.mean()), 3)})
    res_df = pd.DataFrame(resume)
    sauver_tab(res_df, "12_replication_resume")
    log(res_df.to_string(index=False))

    # différences appariées (même jeu de données) : EM variationnel moins EM classique
    piv = brut.pivot(index="graine_donnees", columns="modele", values="ARI")
    diffs = []
    for nom in [c for c in piv.columns if c != "EM classique"]:
        dlt = piv[nom] - piv["EM classique"]
        m, lo, hi = ic_bootstrap(dlt, graine=1)
        diffs.append({"comparaison": f"{nom} moins EM classique (ARI)", "difference_moyenne": round(m, 3),
                      "IC95_bootstrap": f"[{lo:.3f} ; {hi:.3f}]",
                      "jeux_ou_variationnel_meilleur": f"{int((dlt > 0).sum())} sur {len(dlt)}"})
    diff_df = pd.DataFrame(diffs)
    sauver_tab(diff_df, "12_replication_differences")
    log(diff_df.to_string(index=False))
    h1 = [float(x.split(" ; ")[0].strip("[")) > 0 for x in diff_df.IC95_bootstrap]
    for nom_c, ok in zip(diff_df.comparaison, h1):
        log(f"H1 pour {nom_c} : {'soutenue (IC95 strictement positif)' if ok else 'non soutenue (IC95 contient 0 ou est négatif)'}")
    # figure : distribution de l'ARI par modèle, avec les points individuels
    couleurs = {"EM classique": BLUE, "EM variationnel (priors diffus)": ORANGE,
                "EM variationnel (priors empiriques)": NAVY}
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.10,
                        subplot_titles=("Indice de Rand ajusté (1 = partition parfaite)",
                                        "Nombre de composantes actives (vrai : 3)"))
    for nom, d in brut.groupby("modele", sort=False):
        fig.add_trace(go.Box(y=d.ARI.tolist(), name=nom.replace("EM variationnel (", "EM variationnel<br>(")
                             .replace("EM classique", "EM<br>classique"),
                             boxpoints="all", jitter=0.4, pointpos=0,
                             marker=dict(color=couleurs[nom], size=5), line=dict(color=couleurs[nom]),
                             boxmean=True, showlegend=False), row=1, col=1)
    for nom, d in brut.groupby("modele", sort=False):
        comptes = d.composantes_actives.value_counts(normalize=True).sort_index()
        fig.add_trace(go.Bar(x=[f"{k}" for k in comptes.index], y=comptes.tolist(), name=nom,
                             marker_color=couleurs[nom]), row=1, col=2)
    fig.update_layout(barmode="group")
    fig.update_xaxes(title_text="algorithme", row=1, col=1)
    fig.update_xaxes(title_text="composantes actives (N_k \u2265 1)", row=1, col=2)
    fig.update_yaxes(title_text="ARI", row=1, col=1)
    fig.update_yaxes(title_text="part des jeux de données", row=1, col=2, range=[0, 1.05])
    gabarit(fig, f"Réplication sur {R} jeux de données indépendants (K = 6 imposé)", 1250, 600,
            source=f"Chaque point : un jeu de N = 300 (graines 1000 à {999 + R}), 10 initialisations. "
                   "Boîte : médiane et quartiles ; trait pointillé : moyenne.")
    sauver_fig(fig, "12_replication")


# Correspondance entre figures du texte (figures/figNN.png) et figures produites par les expériences
FIGURES_TEXTE = {"fig01": "00_log_vraisemblance_8_points", "fig02": "10_bic_aic", "fig03": "01_jeu_donnees",
               "fig04": "01_ellipses", "fig05": "01_poids", "fig06": "02_alpha0", "fig07": "03_scalabilite",
               "fig08": "05_convergence", "fig09": "06_initialisation", "fig10": "07_covariance",
               "fig11": "08_iris", "fig12": "12_replication", "fig13": "cas_distribution",
               "fig14": "cas_selection", "fig15": "cas_var", "fig16": "cas_regimes"}


def exporter_figures():
    """Copie les PNG produits vers figures/figNN.png."""
    import shutil
    dest = DOSSIER / "figures"
    dest.mkdir(exist_ok=True)
    for nom_m, nom_s in FIGURES_TEXTE.items():
        src = SORTIE / f"{nom_s}.png"
        if src.exists():
            shutil.copyfile(src, dest / f"{nom_m}.png")


# ==============================================================================
# PROGRAMME PRINCIPAL
# ==============================================================================

def main():
    ap = argparse.ArgumentParser(description="Expériences EM classique et EM variationnel (PyTorch, Plotly, Pandas)")
    ap.add_argument("--exp", type=int, nargs="*", help="numéros des expériences à exécuter (0 à 12)")
    ap.add_argument("--rapide", action="store_true", help="tailles et répétitions réduites")
    args = ap.parse_args()
    choix = set(args.exp) if args.exp else set(range(13))
    taches = {0: exp00_validation, 1: exp01_comparaison_k6, 2: exp02_alpha0,
              3: lambda: exp03_scalabilite(args.rapide), 4: exp04_k3, 5: exp05_elbo,
              6: lambda: exp06_initialisation(args.rapide), 7: exp07_covariance,
              8: exp08_iris, 9: exp09_aberrantes, 10: exp10_bic_aic,
              11: lambda: exp11_variantes_hmm_lda(args.rapide),
              12: lambda: exp12_replication(args.rapide)}
    debut = time.perf_counter()
    for i in sorted(choix):
        t0 = time.perf_counter()
        taches[i]()
        log(f"[exp {i:02d} terminée en {time.perf_counter() - t0:.1f} s]")
    exporter_figures()
    import json
    (SORTIE / "environnement.json").write_text(json.dumps(environnement(), indent=2), encoding="utf-8")
    (SORTIE / "journal.txt").write_text("\n".join(_JOURNAL), encoding="utf-8")
    log(f"\nTerminé en {time.perf_counter() - debut:.1f} s. Résultats dans {SORTIE}")


if __name__ == "__main__":
    main()
