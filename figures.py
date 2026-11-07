"""
================================================================================
FIGURES : produites UNIQUEMENT depuis le magasin et les tableaux (aucun ajustement n'est relancé)
================================================================================

python run.py --figures   (ou  python figures.py [--rapide])

Chaque figure est une fonction qui lit les artefacts d'une étape ; si l'étape n'est pas terminée, la figure
est signalée « manquante » et les autres sont produites. Sorties : figures/<nom>.png (impression, kaleido)
et figures/html/<nom>.html (version interactive, survol des valeurs). Pas de titre dans l'image : le titre
est la légende LaTeX. Couleurs : palette catégorielle validée (contrôle de vision des couleurs), attribuée
par MÉTHODE et dans un ordre fixe ; le navy est réservé au texte.
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import plotly.graph_objects as go
import torch
from plotly.subplots import make_subplots

import etapes as E
from progression import Barre

RACINE = Path(__file__).parent
SORTIE = RACINE / "figures"

ENCRE, ENCRE_2, GRILLE, FOND = "#14377B", "#52514e", "#e6e8ee", "#fcfcfb"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
COULEUR = {"EM": SERIES[0], "EM-K": SERIES[0], "EM-BIC": SERIES[0], "EM-Kmax": SERIES[6], "EM-ICL": SERIES[7],
           "MAP-EM": SERIES[3], "MAP-cal": SERIES[5], "VB": SERIES[1], "VB-emp": SERIES[1], "VB-diff": SERIES[4],
           "VB-cal": SERIES[2], "pLSA": SERIES[0], "LDA": SERIES[1]}
SEQUENTIEL = [[0.0, "#e8f1fb"], [0.5, "#6aa3e3"], [1.0, "#0d3b7a"]]
POLICE = "Latin Modern Roman, CMU Serif, Times New Roman, serif"


def style(fig, largeur=900, hauteur=520, legende=True):
    fig.update_layout(font=dict(family=POLICE, color=ENCRE, size=14), paper_bgcolor="white", plot_bgcolor=FOND,
                      width=largeur, height=hauteur, showlegend=legende, margin=dict(l=70, r=30, t=40, b=70),
                      legend=dict(orientation="h", x=0, y=-0.18, yanchor="top", bgcolor="rgba(0,0,0,0)",
                                  font=dict(color=ENCRE_2)))
    fig.update_xaxes(gridcolor=GRILLE, zeroline=False, showline=True, linecolor=ENCRE_2, ticks="outside", linewidth=1)
    fig.update_yaxes(gridcolor=GRILLE, zeroline=False, showline=True, linecolor=ENCRE_2, ticks="outside", linewidth=1)
    return fig


def lire_csv(nom, rapide):
    f = E.dossier_tables(rapide) / f"{nom}.csv"
    if not f.exists():
        return None
    with open(f, encoding="utf-8") as h:
        lignes = list(csv.DictReader(h))
    for l in lignes:
        for k, v in l.items():
            try:
                l[k] = float(v)
            except (TypeError, ValueError):
                pass
    return lignes


def _lignes(etape, prefixe, nom_csv, rapide):
    """Lignes d'une étape lues dans le magasin ; à défaut (magasin resté sur l'instance), dans le CSV agrégé."""
    return E.lignes(etape, rapide, prefixe) or lire_csv(nom_csv, rapide) or []


def _unite(etape, cle, rapide):
    r = E.magasin(etape, rapide).lire(cle)
    if r is None:
        raise LookupError(f"{etape}/{cle}")
    return r


def _ellipse(mu, cov, n_sigma=2.0, n=80):
    t = torch.linspace(0, 2 * math.pi, n, dtype=torch.float64)
    L = torch.linalg.cholesky(cov.double())
    p = mu.double()[:, None] + n_sigma * L @ torch.stack([t.cos(), t.sin()])
    return p[0].tolist(), p[1].tolist()


# ------------------------------------------------------------------------------ chapitre 1 et illustrations
def em_8_points(rapide):
    L = _lignes("validation", "tableau_1_2", "validation_tableau_1_2", rapide)
    fig = go.Figure(go.Scatter(x=[l["iteration"] for l in L], y=[l["loglik"] for l in L], mode="lines+markers",
                               line=dict(color=SERIES[0], width=2), marker=dict(size=9), name="log-vraisemblance",
                               hovertemplate="itération %{x}<br>log-vraisemblance %{y:.3f}<extra></extra>"))
    fig.update_xaxes(title_text="itération t", dtick=1)
    fig.update_yaxes(title_text="log-vraisemblance totale")
    return style(fig, legende=False)


def jeu_reference(rapide):
    a = _unite("illustrations", "k6", rapide)["artefacts"]
    X, y = a["X"], a["y"]
    fig = go.Figure()
    for g in range(int(y.max()) + 1):
        m = y == g
        fig.add_scatter(x=X[m, 0].tolist(), y=X[m, 1].tolist(), mode="markers", name=f"groupe {g + 1}",
                        marker=dict(size=8, color=SERIES[[0, 1, 2][g % 3]], opacity=0.8, line=dict(color="white", width=1)))
    fig.update_xaxes(title_text="x₁")
    fig.update_yaxes(title_text="x₂", scaleanchor="x", scaleratio=1)
    return style(fig, 760, 640)


def ellipses(rapide):
    a = _unite("illustrations", "k6", rapide)["artefacts"]
    X = a["X"]
    noms = ("EM (init k-means)", "VB priors empiriques (init k-means)")
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.05,
                        subplot_titles=("EM, K = Kmax", "VB, Kmax, priors empiriques"))
    for col, nom in enumerate(noms, start=1):
        r = a["ajustements"][nom]
        mu = r["mu"] if "mu" in r else r["m"]
        ordre = torch.argsort(r["Nk"], descending=True).tolist()
        for rang, k in enumerate(ordre):
            c = SERIES[rang % len(SERIES)]
            m = r["labels"].long() == k
            nk = float(r["Nk"][k])
            if m.any():
                fig.add_scatter(x=X[m, 0].tolist(), y=X[m, 1].tolist(), mode="markers", showlegend=False,
                                marker=dict(size=6, color=c, opacity=0.6), row=1, col=col,
                                hovertemplate=f"composante {k + 1}, N_k = {nk:.1f}<extra></extra>")
            if nk >= 1:
                ex, ey = _ellipse(mu[k], r["cov"][k])
                fig.add_scatter(x=ex, y=ey, mode="lines", line=dict(color=c, width=2), showlegend=False, row=1, col=col,
                                hoverinfo="skip")
                fig.add_annotation(x=float(mu[k][0]), y=float(mu[k][1]), text=f"π={float(r['pi'][k]):.2f}", showarrow=False,
                                   font=dict(size=11, color=ENCRE), bgcolor="rgba(255,255,255,0.7)", row=1, col=col)
    fig.update_xaxes(title_text="x₁")
    fig.update_yaxes(title_text="x₂", col=1)
    return style(fig, 1200, 600, legende=False)


def poids(rapide):
    a = _unite("illustrations", "k6", rapide)["artefacts"]["ajustements"]
    fig = go.Figure()
    for nom, cle in (("EM", "EM (init k-means)"), ("VB", "VB priors empiriques (init k-means)")):
        p = sorted(a[cle]["pi"].tolist(), reverse=True)
        fig.add_bar(x=[f"{i + 1}" for i in range(len(p))], y=p, name=nom, marker_color=COULEUR[nom],
                    text=[f"{v:.3f}" for v in p], textposition="outside", textfont=dict(color=ENCRE_2))
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
    fig.update_xaxes(title_text="composante (ordre décroissant des poids)")
    fig.update_yaxes(title_text="poids de mélange π_k")
    return style(fig)


def alpha0(rapide):
    L = _lignes("illustrations", "alpha0/", "illustrations_alpha0", rapide)
    if not L:
        raise LookupError("illustrations/alpha0")
    fig = go.Figure()
    for i, (p, sym) in enumerate((("empiriques", "circle"), ("diffus", "diamond"))):
        d = sorted([l for l in L if l["priors"] == p], key=lambda l: l["alpha0"])
        fig.add_scatter(x=[l["alpha0"] for l in d], y=[l["composantes_actives"] for l in d], mode="lines+markers",
                        name=f"priors {p}", line=dict(color=SERIES[i], width=2), marker=dict(size=9, symbol=sym))
    fig.add_hline(y=3, line=dict(color=ENCRE_2, dash="dot"), annotation_text="nombre de groupes simulés",
                  annotation_font_color=ENCRE_2)
    fig.update_xaxes(type="log", title_text="concentration du prior de Dirichlet α₀ (échelle logarithmique)")
    fig.update_yaxes(title_text="composantes actives (N_k / N ≥ seuil)", dtick=1)
    return style(fig)


def bic_aic(rapide):
    L = _lignes("illustrations", "bic_aic", "illustrations_bic_aic", rapide)
    if not L:
        raise LookupError("illustrations/bic_aic")
    fig = go.Figure()
    for i, c in enumerate(("BIC", "AIC", "ICL")):
        fig.add_scatter(x=[l["K"] for l in L], y=[l[c] for l in L], mode="lines+markers", name=c,
                        line=dict(color=SERIES[i], width=2), marker=dict(size=9))
        k = min(L, key=lambda l: l[c])
        fig.add_annotation(x=k["K"], y=k[c], text=f"min {c}", showarrow=True, arrowhead=0, ay=-30, font=dict(color=ENCRE_2))
    fig.update_xaxes(title_text="nombre de composantes K", dtick=1)
    fig.update_yaxes(title_text="critère (plus bas = meilleur)")
    return style(fig)


def convergence(rapide):
    a = _unite("illustrations", "k6", rapide)["artefacts"]["ajustements"]
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.12,
                        subplot_titles=("VB : ELBO", "EM : log-vraisemblance"))
    h = a["VB priors empiriques (init k-means)"]["elbo_hist"]
    fig.add_scatter(x=list(range(1, len(h) + 1)), y=h, mode="lines", line=dict(color=COULEUR["VB"], width=2), row=1, col=1)
    h = a["EM (init k-means)"]["ll_hist"]
    fig.add_scatter(x=list(range(1, len(h) + 1)), y=h, mode="lines", line=dict(color=COULEUR["EM"], width=2), row=1, col=2)
    fig.update_xaxes(title_text="itération")
    return style(fig, 1100, 480, legende=False)


def initialisation(rapide):
    L = lire_csv("illustrations_initialisation", rapide)
    if not L:
        raise LookupError("illustrations_initialisation")
    ks = sorted({int(k.split("_")[1]) for k in L[0] if k.startswith("actives_")})
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.05,
                        subplot_titles=("initialisation k-means", "initialisation aléatoire"))
    for col, ini in enumerate(("kmeans", "aleatoire"), start=1):
        d = [l for l in L if l["initialisation"] == ini]
        for j, k in enumerate(ks):
            fig.add_bar(x=[l["modele"] for l in d], y=[l[f"actives_{k}"] for l in d], name=f"{k} composantes actives",
                        marker=dict(color=SERIES[j % len(SERIES)], line=dict(color="white", width=2)),
                        showlegend=col == 1, legendgroup=str(k), row=1, col=col)
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title_text="nombre d'exécutions", col=1)
    return style(fig, 1100, 560)


def covariance(rapide):
    L = _lignes("illustrations", "covariance/", "illustrations_covariance", rapide)
    if not L:
        raise LookupError("illustrations/covariance")
    fig = go.Figure()
    for nom, cle in (("EM", "EM"), ("VB", "VB priors empiriques")):
        d = [l for l in L if l["modele"] == cle]
        fig.add_bar(x=[l["covariance"] for l in d], y=[l["ARI"] for l in d], name=nom, marker_color=COULEUR[nom],
                    text=[f"{l['ARI']:.2f}" for l in d], textposition="outside", textfont=dict(color=ENCRE_2))
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
    fig.update_xaxes(title_text="contrainte de covariance")
    fig.update_yaxes(title_text="indice de Rand ajusté", range=[0, 1.12])
    return style(fig)


def iris(rapide):
    L = _lignes("illustrations", "iris", "illustrations_iris", rapide)
    fig = go.Figure()
    for i, m in enumerate(("ARI", "silhouette")):
        fig.add_bar(x=[l["modele"] for l in L], y=[l[m] for l in L], name=m, marker_color=SERIES[i],
                    text=[f"{l[m]:.2f}" for l in L], textposition="outside", textfont=dict(color=ENCRE_2))
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
    fig.update_yaxes(title_text="valeur", range=[0, 1.05])
    return style(fig)


def scalabilite(rapide):
    L = lire_csv("chronometrage_scalabilite", rapide)
    if not L:
        raise LookupError("chronometrage_scalabilite")
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.08,
                        subplot_titles=("selon N (D = 2)", "selon D (N = 2001)"))
    for col, sel, x in ((1, lambda l: l["D"] == 2 and l["N"] != 2001, "N"), (2, lambda l: l["N"] == 2001, "D")):
        d = sorted([l for l in L if sel(l)], key=lambda l: l[x])
        for nom, c in (("EM", "temps_em"), ("VB", "temps_vb")):
            fig.add_scatter(x=[l[x] for l in d], y=[l[c] for l in d], mode="lines+markers", name=nom,
                            line=dict(color=COULEUR[nom], width=2), marker=dict(size=8), showlegend=col == 1,
                            legendgroup=nom, row=1, col=col)
    fig.update_yaxes(type="log", title_text="temps médian (s, échelle log)", col=1)
    fig.update_yaxes(type="log", col=2)
    fig.update_xaxes(type="log", title_text="N (échelle log)", col=1)
    fig.update_xaxes(title_text="D", col=2)
    return style(fig, 1100, 520)


# ------------------------------------------------------------------------------ décisions (graphiques en forêt)
def _foret(nom_csv, rapide):
    L = [l for l in (lire_csv(nom_csv, rapide) or []) if l.get("test") in ("equivalence", "difference")]
    if not L:
        raise LookupError(nom_csv)
    fig = go.Figure()
    y = [l["id"] for l in L][::-1]
    for test, c, sym in (("equivalence", SERIES[0], "diamond"), ("difference", SERIES[1], "circle")):
        d = [l for l in L if l["test"] == test]
        fig.add_scatter(x=[l["estimation"] for l in d], y=[l["id"] for l in d], mode="markers",
                        name="équivalence (TOST)" if test == "equivalence" else "différence (Wilcoxon)",
                        marker=dict(size=9, color=c, symbol=sym, line=dict(color="white", width=1)),
                        error_x=dict(type="data", symmetric=False, color=c, thickness=1.5,
                                     array=[l["ic_haut"] - l["estimation"] for l in d],
                                     arrayminus=[l["estimation"] - l["ic_bas"] for l in d]),
                        customdata=[l["decision"] for l in d],
                        hovertemplate="%{y}<br>écart %{x:.3f}<br>%{customdata}<extra></extra>")
        for l in d:
            if l["test"] == "equivalence" and isinstance(l.get("marge"), float):
                fig.add_shape(type="line", x0=-l["marge"], x1=l["marge"], y0=l["id"], y1=l["id"], layer="below",
                              line=dict(color=GRILLE, width=10))
    fig.add_vline(x=0, line=dict(color=ENCRE_2, width=1))
    fig.update_yaxes(categoryorder="array", categoryarray=y, title_text="")
    fig.update_xaxes(title_text="différence moyenne A - B (IC bootstrap à 95 %)")
    return style(fig, 950, max(420, 26 * len(L) + 160))


def decisions_scenarios(rapide):
    return _foret("scenarios_decisions", rapide)


def decisions_prix(rapide):
    return _foret("prix_decisions", rapide)


def decisions_texte(rapide):
    return _foret("texte_decisions", rapide)


# ------------------------------------------------------------------------------ cas pratique : prix alimentaires
SYMBOLES = ["circle", "diamond", "square", "triangle-up", "cross", "star"]


def _alerte(rapide):
    return _unite("prix", "alerte", rapide)["artefacts"]


def prix_marches(rapide):
    """Carte des marchés (longitude, latitude) : couleur et symbole par région, taille selon le nombre d'observations."""
    a = _alerte(rapide)
    n = torch.bincount(a["marche"], minlength=len(a["marches"]))
    regions = sorted({a["regions"][i] for i in range(len(n)) if n[i] > 0},           # régions observées seulement
                     key=lambda r: -sum(int(n[i]) for i, x in enumerate(a["regions"]) if x == r))
    fig = go.Figure()
    for j, reg in enumerate(regions):
        idx = [i for i, x in enumerate(a["regions"]) if x == reg and n[i] > 0]
        fig.add_scatter(x=[float(a["lon"][i]) for i in idx], y=[float(a["lat"][i]) for i in idx], mode="markers", name=reg,
                        marker=dict(size=[8 + 2.5 * math.sqrt(int(n[i])) for i in idx], color=SERIES[j], symbol=SYMBOLES[j],
                                    opacity=0.85, line=dict(color="white", width=2)),
                        customdata=[[a["marches"][i], int(n[i])] for i in idx],
                        hovertemplate="%{customdata[0]}<br>%{customdata[1]} observations<extra>" + reg + "</extra>")
    for i in torch.argsort(n, descending=True)[:6].tolist():
        fig.add_annotation(x=float(a["lon"][i]), y=float(a["lat"][i]), text=a["marches"][i], showarrow=False, yshift=16,
                           font=dict(size=11, color=ENCRE_2))
    fig.update_xaxes(title_text="longitude (°)")
    fig.update_yaxes(title_text="latitude (°)", scaleanchor="x", scaleratio=1)
    return style(fig, 760, 820)


def prix_selection(rapide):
    """BIC de l'EM selon K (référence) et poids des composantes du VB à priors empiriques : deux mesures, deux panneaux."""
    ref = _unite("prix", "reference", rapide)["artefacts"]
    c = _unite("prix", "complet", rapide)["artefacts"]["ajustements"]
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.12,
                        subplot_titles=("EM : BIC selon K (plus bas = meilleur)", "VB-emp : poids des composantes (Kmax)"))
    ks = sorted(int(k) for k in ref["critere_par_k"])
    fig.add_scatter(x=ks, y=[ref["critere_par_k"][str(k)] for k in ks], mode="lines+markers", name="BIC (EM)",
                    line=dict(color=COULEUR["EM-BIC"], width=2), marker=dict(size=9), row=1, col=1)
    fig.add_annotation(x=ref["K_ref"], y=ref["critere_par_k"][str(ref["K_ref"])], text=f"K_ref = {ref['K_ref']}", showarrow=True,
                       arrowhead=0, ay=-30, font=dict(color=ENCRE_2), row=1, col=1)
    if "VB-emp" in c:
        p = sorted(c["VB-emp"]["pi"].tolist(), reverse=True)
        fig.add_bar(x=[str(i + 1) for i in range(len(p))], y=p, name="poids (VB-emp)", marker_color=COULEUR["VB-emp"],
                    text=[f"{v:.3f}" for v in p], textposition="outside", textfont=dict(color=ENCRE_2), row=1, col=2)
    fig.update_xaxes(title_text="K", dtick=1, col=1)
    fig.update_xaxes(title_text="composante (ordre décroissant)", col=2)
    return style(fig, 1150, 520)


def _marches_suivis(a, n=3):
    """Les n marchés les plus observés pendant la période de test."""
    t = torch.bincount(a["marche"][~a["app"]], minlength=len(a["marches"]))
    return torch.argsort(t, descending=True)[:n].tolist()


def prix_alerte(rapide):
    """
    Pour trois marchés : en haut, l'écart du prix du maïs à son niveau récent ; en bas, la probabilité du régime de
    tension (EM-BIC : bootstrap ; VB-emp : crédibilité ; bandes à 90 %). Deux mesures, deux rangées : pas de double axe.
    """
    import donnees as DO
    a = _alerte(rapide)
    choix = _marches_suivis(a)
    fin = DO.mois_texte(int(a["mois"][a["app"]].max()))
    fig = make_subplots(rows=2, cols=len(choix), shared_xaxes=True, vertical_spacing=0.08, horizontal_spacing=0.05,
                        subplot_titles=[a["marches"][m] for m in choix], row_heights=[0.4, 0.6])
    for j, m in enumerate(choix, start=1):
        sel = (a["marche"] == m).nonzero().flatten()
        x = [DO.mois_texte(int(t)) + "-15" for t in a["mois"][sel]]
        fig.add_scatter(x=x, y=a["X_origine"][sel, 0].tolist(), mode="lines+markers", name="écart du maïs (log)",
                        line=dict(color=SERIES[2], width=2), marker=dict(size=8), showlegend=j == 1, legendgroup="mais",
                        row=1, col=j)
        for nom in ("EM-BIC", "VB-emp"):
            if nom not in a:
                continue
            p, ic = a[nom]["proba"][sel], a[nom]["ic"][:, sel]
            fig.add_scatter(x=x + x[::-1], y=ic[1].tolist() + ic[0].tolist()[::-1], fill="toself", mode="lines",
                            line=dict(width=0), fillcolor=COULEUR[nom], opacity=0.18, hoverinfo="skip", showlegend=False,
                            legendgroup=nom, row=2, col=j)
            fig.add_scatter(x=x, y=p.tolist(), mode="lines+markers", name=f"P(tension), {nom}", legendgroup=nom,
                            line=dict(color=COULEUR[nom], width=2), marker=dict(size=8), showlegend=j == 1, row=2, col=j,
                            hovertemplate="%{x|%Y-%m}<br>P(tension) %{y:.2f}<extra>" + nom + "</extra>")
        for r in (1, 2):
            fig.add_vline(x=fin + "-28", line=dict(color=ENCRE_2, dash="dot", width=1), row=r, col=j)
    fig.add_hline(y=0.5, line=dict(color=ENCRE_2, dash="dash", width=1), row=2, col="all")
    fig.update_yaxes(title_text="écart (log)", col=1, row=1)
    fig.update_yaxes(range=[0, 1], row=2)
    fig.update_yaxes(title_text="probabilité", row=2, col=1)
    return style(fig, 1350, 680)


def prix_alerte_mois(rapide):
    """Part mensuelle des observations en alerte (P(tension) > 0,5), tous marchés, selon EM-BIC et VB-emp."""
    import donnees as DO
    a = _alerte(rapide)
    mois = torch.unique(a["mois"])
    fig = go.Figure()
    for nom in ("EM-BIC", "VB-emp"):
        if nom in a:
            al = (a[nom]["proba"] > 0.5).double()
            fig.add_scatter(x=[DO.mois_texte(int(t)) + "-15" for t in mois], y=[float(al[a["mois"] == t].mean()) for t in mois],
                            mode="lines+markers", name=nom, line=dict(color=COULEUR[nom], width=2), marker=dict(size=8),
                            hovertemplate="%{x|%Y-%m}<br>part en alerte %{y:.0%}<extra>" + nom + "</extra>")
    fig.add_vline(x=DO.mois_texte(int(a["mois"][a["app"]].max())) + "-28", line=dict(color=ENCRE_2, dash="dot", width=1),
                  annotation_text="fin de l'apprentissage", annotation_font_color=ENCRE_2)
    fig.update_xaxes(title_text="mois")
    fig.update_yaxes(title_text="part des marchés en alerte", tickformat=".0%", range=[0, 1])
    return style(fig, 1100, 500)


# ------------------------------------------------------------------------------ production
FIGURES = {
    "fig01": em_8_points, "fig02": bic_aic, "fig03": jeu_reference, "fig04": ellipses, "fig05": poids, "fig06": alpha0,
    "fig07": scalabilite, "fig08": convergence, "fig09": initialisation, "fig10": covariance, "fig11": iris,
    "fig12": decisions_scenarios, "prix_marches": prix_marches, "prix_selection": prix_selection,
    "prix_alerte": prix_alerte, "prix_alerte_mois": prix_alerte_mois, "prix_decisions": decisions_prix,
    "texte_decisions": decisions_texte,
}


def _ecrire_png(fig, chemin, essais=3):
    """Export PNG par kaleido (navigateur sans interface) : le navigateur échoue parfois à se fermer ; on relance."""
    for i in range(1, essais + 1):
        try:
            fig.write_image(chemin, scale=2)
            return
        except RuntimeError:
            if i == essais:
                raise


def produire(rapide: bool = False):
    (SORTIE / "html").mkdir(parents=True, exist_ok=True)
    dest = SORTIE if not rapide else SORTIE / "rapide"
    dest.mkdir(parents=True, exist_ok=True)
    barre = Barre(len(FIGURES), "figures")
    manquantes = []
    for nom, f in FIGURES.items():
        try:
            fig = f(rapide)
            fig.write_html(SORTIE / "html" / f"{nom}{'_rapide' if rapide else ''}.html", include_plotlyjs="cdn")
            _ecrire_png(fig, dest / f"{nom}.png")
        except (LookupError, KeyError, TypeError) as ex:
            manquantes.append(f"{nom} ({type(ex).__name__}: {ex})")
        except Exception as ex:                       # une figure en échec ne bloque pas les autres
            manquantes.append(f"{nom} (ERREUR {type(ex).__name__}: {str(ex)[:200]})")
        barre.avancer(info=nom)
    barre.fermer()
    if manquantes:
        print("figures manquantes (étape non terminée) :\n  " + "\n  ".join(manquantes))


if __name__ == "__main__":
    produire("--rapide" in sys.argv)
