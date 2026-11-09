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
    graduations = [0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100]             # libellés lisibles sur l'échelle log
    fig.update_yaxes(type="log", tickvals=graduations, ticktext=[f"{v:g}".replace(".", ",") for v in graduations])
    fig.update_yaxes(title_text="temps médian (s, échelle log)", col=1)
    gn = [500, 1000, 2000, 5000, 10000, 20000]
    fig.update_xaxes(type="log", title_text="N (échelle log)", tickvals=gn, ticktext=[f"{v:,}".replace(",", " ") for v in gn],
                     col=1)
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


# Une grandeur par panneau (jamais deux unités sur un même axe) : préfixes d'identifiants, titre de l'axe, référence
GROUPES_PRIX = [
    (("HP1-",), "|K̂ − K_ref| : VB − EM-BIC (composantes)", 0.0),
    (("HP2-",), "log-vraisemblance de test : VB − EM-BIC", 0.0),
    (("HP3-", "HP7-"), "fréquence d'ajustements dégénérés : VB ou MAP-EM − EM à Kmax", 0.0),
    (("HP5",), "variance de K̂ : VB − EM", 0.0),
    (("HP4-",), "temps EM-BIC / temps d'un VB (rapport)", 1.0),
    (("HP6-diff",), "couverture VB − couverture bootstrap EM-BIC", 0.0),
    (("HP6-VB", "HP6-bootstrap"), "couverture des intervalles à 90 %", 0.9),
]
MARQUE_TEST = {"equivalence": ("diamond", "équivalence (TOST)"), "difference": ("circle", "différence (Wilcoxon)"),
               "intervalle": ("square", "intervalle (bootstrap)")}


def _foret_groupes(nom_csv, groupes, rapide):
    """Graphique en forêt par panneaux : chaque groupe d'hypothèses a son axe, son unité et sa valeur de référence."""
    L = lire_csv(nom_csv, rapide) or []
    blocs = []
    for prefixes, titre, ref in groupes:
        d = [l for l in L if any(str(l["id"]).startswith(p) for p in prefixes) and isinstance(l.get("estimation"), float)]
        if d:
            blocs.append((d, titre, ref))
    if not blocs:
        raise LookupError(nom_csv)
    fig = make_subplots(rows=len(blocs), cols=1, vertical_spacing=0.32 / len(blocs),
                        row_heights=[len(d) + 1.2 for d, _, _ in blocs])
    vus = set()
    for i, (d, titre, ref) in enumerate(blocs, start=1):
        for test, c in (("equivalence", SERIES[0]), ("difference", SERIES[1]), ("intervalle", SERIES[2])):
            e = [l for l in d if l["test"] == test]
            if not e:
                continue
            sym, nom = MARQUE_TEST[test]
            fig.add_scatter(x=[l["estimation"] for l in e], y=[l["id"] for l in e], mode="markers", name=nom,
                            legendgroup=test, showlegend=test not in vus,
                            marker=dict(size=9, color=c, symbol=sym, line=dict(color="white", width=1)),
                            error_x=dict(type="data", symmetric=False, color=c, thickness=1.5,
                                         array=[l["ic_haut"] - l["estimation"] for l in e],
                                         arrayminus=[l["estimation"] - l["ic_bas"] for l in e]),
                            customdata=[l["decision"] for l in e],
                            hovertemplate="%{y}<br>%{x:.3f}<br>%{customdata}<extra></extra>", row=i, col=1)
            vus.add(test)
            for l in e:
                if test == "equivalence" and isinstance(l.get("marge"), float):
                    fig.add_shape(type="line", x0=ref - l["marge"], x1=ref + l["marge"], y0=l["id"], y1=l["id"],
                                  layer="below", line=dict(color=GRILLE, width=10), row=i, col=1)
        fig.add_vline(x=ref, line=dict(color=ENCRE_2, width=1), row=i, col=1)
        fig.update_yaxes(categoryorder="array", categoryarray=[l["id"] for l in d][::-1], title_text="", row=i, col=1)
        fig.update_xaxes(title_text=titre, title_standoff=4, title_font=dict(size=13), row=i, col=1)
    n = sum(len(d) for d, _, _ in blocs)
    return style(fig, 1000, 34 * n + 95 * len(blocs) + 120)


def decisions_prix(rapide):
    return _foret_groupes("prix_decisions", GROUPES_PRIX, rapide)


def decisions_texte(rapide):
    """HT1 : écarts de perplexité sur plusieurs ordres de grandeur (probabilités nulles du pLSA) : échelle log."""
    fig = _foret("texte_decisions", rapide)
    fig.update_xaxes(type="log", exponentformat="power",
                     title_text="écart relatif de perplexité pLSA − LDA (moyenne, IC bootstrap à 95 %, échelle log)")
    return fig


# ------------------------------------------------------------------------------ cas pratique : prix alimentaires
SYMBOLES = ["circle", "diamond", "square", "triangle-up", "cross", "star"]


def _alerte(rapide):
    return _unite("prix", "alerte", rapide)["artefacts"]


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


def _geo(fig, lon, lat, **cible):
    """Fond de carte : Cameroun en blanc bordé, pays voisins grisés, projection de Mercator."""
    fig.update_geos(projection_type="mercator", lonaxis_range=lon, lataxis_range=lat, resolution=50, showframe=False,
                    showcountries=True, countrycolor="#a9a8a3", showland=True, landcolor="#ecebe6", showocean=True,
                    oceancolor="#e9f0f7", showlakes=True, lakecolor="#e9f0f7", showcoastlines=True,
                    coastlinecolor="#a9a8a3", **cible)


def _cameroun(fig, **cible):
    fig.add_choropleth(locations=["CMR"], z=[1], colorscale=[[0, "white"], [1, "white"]], showscale=False,
                       marker_line_color=ENCRE_2, marker_line_width=1.2, hoverinfo="skip", showlegend=False, **cible)


def prix_marches(rapide):
    """Carte des marchés : couleur et symbole par région, taille selon le nombre d'observations (marché, mois)."""
    a = _alerte(rapide)
    n = torch.bincount(a["marche"], minlength=len(a["marches"]))
    regions = sorted({a["regions"][i] for i in range(len(n)) if n[i] > 0},           # régions observées seulement
                     key=lambda r: -sum(int(n[i]) for i, x in enumerate(a["regions"]) if x == r))
    fig = go.Figure()
    _cameroun(fig)
    for j, reg in enumerate(regions):
        idx = [i for i, x in enumerate(a["regions"]) if x == reg and n[i] > 0]
        fig.add_scattergeo(lon=[float(a["lon"][i]) for i in idx], lat=[float(a["lat"][i]) for i in idx], mode="markers",
                           name=f"{reg} ({len(idx)} marché{'s' if len(idx) > 1 else ''})",
                           marker=dict(size=[6 + 1.6 * math.sqrt(int(n[i])) for i in idx], color=SERIES[j],
                                       symbol=SYMBOLES[j], opacity=0.9, line=dict(color="white", width=1)),
                           customdata=[[a["marches"][i], int(n[i])] for i in idx],
                           hovertemplate="%{customdata[0]}<br>%{customdata[1]} observations<extra>" + reg + "</extra>")
    villes = {"Garoua": (9.30, 13.40), "Ngaoundéré": (7.32, 13.58), "Bertoua": (4.58, 13.68),
              "Yaoundé": (3.87, 11.52), "Douala": (4.05, 9.70), "Bamenda": (5.96, 10.15)}
    fig.add_scattergeo(lon=[v[1] for v in villes.values()], lat=[v[0] for v in villes.values()], mode="text",
                       text=list(villes), textposition="bottom center", textfont=dict(size=12, color=ENCRE_2),
                       hoverinfo="skip", showlegend=False)
    _geo(fig, [8.3, 16.4], [1.6, 13.2])
    style(fig, 760, 900)
    fig.update_layout(legend=dict(y=-0.02), margin=dict(l=10, r=10, t=10, b=90))
    return fig


def _episodes_marche(region, marche):
    import donnees as DO
    return [e for e in DO.EPISODES_PRIX if e["region"] == region and (not e["marches"] or marche in e["marches"])]


def prix_alerte(rapide):
    """
    Pour trois marchés : en haut, le prix du maïs (XAF/kg) et son niveau des douze mois précédents, dont l'écart est la
    variable du modèle ; en bas, la probabilité du régime de tension (EM-BIC : bootstrap ; VB-emp : crédibilité ;
    bandes à 90 %). Bandes grisées : épisodes datés par les bulletins. Deux mesures, deux rangées : pas de double axe.
    """
    import donnees as DO
    import parametres as PARAM
    a = _alerte(rapide)
    choix = _marches_suivis(a)
    fin = DO.mois_texte(int(a["mois"][a["app"]].max()))
    fen, rmin = int(PARAM.valeur("prix_fenetre_mois")), int(PARAM.valeur("prix_releves_min"))
    prix = DO.prix_bruts()
    fig = make_subplots(rows=2, cols=len(choix), shared_xaxes=True, vertical_spacing=0.08, horizontal_spacing=0.06,
                        subplot_titles=[f"{a['marches'][m]} ({a['regions'][m]})" for m in choix], row_heights=[0.45, 0.55])
    for j, m in enumerate(choix, start=1):
        nom = a["marches"][m]
        sel = (a["marche"] == m).nonzero().flatten()
        t0, t1 = int(a["mois"][sel].min()), int(a["mois"][sel].max())
        s = prix.get(nom, {})
        ts = [t for t in sorted(s) if t0 <= t <= t1]
        niv = []
        for t in ts:
            passe = [math.log(s[u]) for u in range(t - fen, t) if u in s]
            niv.append(math.exp(sum(passe) / len(passe)) if len(passe) >= rmin else None)
        xt = [DO.mois_texte(t) + "-15" for t in ts]
        fig.add_scatter(x=xt, y=[s[t] for t in ts], mode="lines+markers", name="prix du maïs (XAF/kg)",
                        line=dict(color=SERIES[2], width=2), marker=dict(size=6), showlegend=j == 1, legendgroup="prix",
                        hovertemplate="%{x|%Y-%m}<br>%{y:.0f} XAF/kg<extra>" + nom + "</extra>", row=1, col=j)
        fig.add_scatter(x=xt, y=niv, mode="lines", name="niveau des 12 mois précédents", connectgaps=False,
                        line=dict(color=ENCRE_2, width=1.5, dash="dash"), showlegend=j == 1, legendgroup="niveau",
                        hovertemplate="%{x|%Y-%m}<br>niveau %{y:.0f} XAF/kg<extra>" + nom + "</extra>", row=1, col=j)
        x = [DO.mois_texte(int(t)) + "-15" for t in a["mois"][sel]]
        for meth in ("EM-BIC", "VB-emp"):
            if meth not in a:
                continue
            p, ic = a[meth]["proba"][sel], a[meth]["ic"][:, sel]
            fig.add_scatter(x=x + x[::-1], y=ic[1].tolist() + ic[0].tolist()[::-1], fill="toself", mode="lines",
                            line=dict(width=0), fillcolor=COULEUR[meth], opacity=0.18, hoverinfo="skip", showlegend=False,
                            legendgroup=meth, row=2, col=j)
            fig.add_scatter(x=x, y=p.tolist(), mode="lines+markers", name=f"P(tension), {meth}", legendgroup=meth,
                            line=dict(color=COULEUR[meth], width=2), marker=dict(size=6), showlegend=j == 1, row=2, col=j,
                            hovertemplate="%{x|%Y-%m}<br>P(tension) %{y:.2f}<extra>" + meth + "</extra>")
        for e in _episodes_marche(a["regions"][m], nom):
            for r in (1, 2):
                fig.add_vrect(x0=e["mois"] + "-01", x1=e["mois"] + "-28", fillcolor=ENCRE_2, opacity=0.15, line_width=0,
                              layer="below", row=r, col=j)
            fig.add_annotation(x=e["mois"] + "-15", y=1, xref=f"x{j}" if j > 1 else "x",
                               yref=f"y{j} domain" if j > 1 else "y domain", yanchor="top", text=e["sens"], xanchor="left",
                               showarrow=False, font=dict(size=11, color=ENCRE_2))
        for r in (1, 2):
            fig.add_vline(x=fin + "-28", line=dict(color=ENCRE_2, dash="dot", width=1), row=r, col=j)
    fig.add_hline(y=0.5, line=dict(color=ENCRE_2, dash="dash", width=1), row=2, col="all")
    fig.update_yaxes(title_text="maïs (XAF/kg)", col=1, row=1)
    fig.update_yaxes(range=[0, 1], row=2)
    fig.update_yaxes(title_text="P(tension)", row=2, col=1)
    return style(fig, 1350, 700)


def prix_carte_alerte(rapide):
    """
    Extrême-Nord, mois des deux épisodes datés : P(tension) de chaque marché observé selon l'EM-BIC et le VB-emp, une
    carte par (épisode, méthode). Même échelle de couleur partout ; contour épais et nom : alerte (P > 0,5) ; noms
    aussi pour les marchés cités par le bulletin.
    """
    import donnees as DO
    a = _alerte(rapide)
    meths = [m for m in ("EM-BIC", "VB-emp") if m in a]
    cartes = [(e, meth) for e in DO.EPISODES_PRIX for meth in meths]
    fig = make_subplots(rows=1, cols=len(cartes), specs=[[{"type": "geo"}] * len(cartes)], horizontal_spacing=0.01,
                        subplot_titles=[f"{meth}<br>{e['mois']} ({e['sens']})" for e, meth in cartes])
    for j, (e, meth) in enumerate(cartes, start=1):
        t = DO.mois_index(e["mois"])
        sel = [k for k in (a["mois"] == t).nonzero().flatten().tolist() if a["regions"][int(a["marche"][k])] == e["region"]]
        mk = [int(a["marche"][k]) for k in sel]
        lon, lat = [float(a["lon"][m]) for m in mk], [float(a["lat"][m]) for m in mk]
        p = [float(a[meth]["proba"][k]) for k in sel]
        ic = a[meth]["ic"]
        _cameroun(fig, row=1, col=j)
        fig.add_scattergeo(lon=lon, lat=lat, mode="markers",
                           marker=dict(size=13, color=p, cmin=0, cmax=1, colorscale=SEQUENTIEL,
                                       line=dict(color=[ENCRE if v > 0.5 else "white" for v in p],
                                                 width=[3 if v > 0.5 else 1 for v in p]),
                                       showscale=j == 1, colorbar=dict(title=dict(text="P(tension)", side="right"),
                                                                       len=0.8, x=1.01, tickformat=".1f")),
                           customdata=[[a["marches"][m], float(ic[0, k]), float(ic[1, k])] for m, k in zip(mk, sel)],
                           hovertemplate="%{customdata[0]}<br>P(tension) %{marker.color:.2f}"
                                         "<br>IC à 90 % [%{customdata[1]:.2f} ; %{customdata[2]:.2f}]<extra>" + meth
                                         + "</extra>", showlegend=False, row=1, col=j)
        fig.add_scattergeo(lon=lon, lat=lat, mode="text", textposition="middle right",
                           text=["  " + a["marches"][m] if (a["marches"][m] in e["marches"] or v > 0.5) else ""
                                 for m, v in zip(mk, p)],
                           textfont=dict(size=11, color=ENCRE_2), hoverinfo="skip", showlegend=False, row=1, col=j)
    _geo(fig, [13.2, 15.8], [9.9, 13.1])
    style(fig, 1300, 520, legende=False)
    fig.update_layout(margin=dict(l=5, r=70, t=60, b=5))
    return fig


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
    "prix_alerte": prix_alerte, "prix_carte_alerte": prix_carte_alerte, "prix_alerte_mois": prix_alerte_mois, "prix_decisions": decisions_prix,
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
