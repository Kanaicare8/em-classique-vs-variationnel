"""Page 2 : régimes appris par EM-BIC et VB-emp sur l'apprentissage (ajustements précalculés)."""

import math

import dash
import plotly.graph_objects as go
import torch
from dash import Input, Output, callback, dcc, html

import composants as CO
from emvb import figures as FG
import service as SV

dash.register_page(__name__, path="/regimes", name="Régimes", order=2, title="Régimes, prix alimentaires du Cameroun")

PAIRES = [(0, 1), (0, 2), (1, 2)]
INACTIF = "#c4c7cf"


def _bic(pre):
    r = pre["regimes"]
    ks = sorted(int(k) for k in r["critere_par_k"])
    y = [r["critere_par_k"][str(k)] for k in ks]
    fig = go.Figure()
    fig.add_scatter(x=ks, y=y, mode="lines+markers", name="BIC", line=dict(color=FG.COULEUR["EM-BIC"], width=2),
                    marker=dict(size=[13 if k == r["K_ref"] else 8 for k in ks]),
                    hovertemplate="K = %{x}<br>BIC %{y:,.1f}<extra></extra>")
    fig.add_annotation(x=r["K_ref"], y=r["critere_par_k"][str(r["K_ref"])], text=f"K retenu = {r['K_ref']}",
                       showarrow=True, arrowhead=0, ay=-34, font=dict(color=FG.ENCRE))
    CO.habiller(fig, legende=False)
    fig.update_xaxes(title_text="nombre de composantes K", dtick=1)
    fig.update_yaxes(title_text="BIC (plus bas = meilleur)")
    return fig


def _comparaison(pre):
    b = pre["regimes"]["bras"]
    lignes = []
    for nom in SV.BRAS:
        if "echec" in b.get(nom, {"echec": "absent"}):
            lignes.append({"Bras": nom, "K̂ (actives)": "échec"})
            continue
        x = b[nom]
        reg = next(r for r in SV.regimes(nom) if r["tension"])
        part = {l["periode"]: l["part_alerte"] for l in pre["lignes_alerte"] if l["bras"] == nom}
        lignes.append({"Bras": nom, "K ajusté": str(len(x["pi"])), "K̂ (actives)": str(x["k_hat"]),
                       "Itérations": str(x["n_iter"]), "Convergé": "oui" if x["converge"] else "non",
                       "Temps (s)": CO.nombre(x["temps_s"], 1),
                       "Poids du régime de tension": CO.pourcent(reg["poids"], 1),
                       "Alerte apprentissage": CO.pourcent(part.get("apprentissage"), 1),
                       "Alerte test": CO.pourcent(part.get("test"), 1)})
    accord = next((l["part_alerte"] for l in pre["lignes_alerte"] if l["bras"].startswith("accord")), None)
    cols = ["Bras", "K ajusté", "K̂ (actives)", "Itérations", "Convergé", "Temps (s)", "Poids du régime de tension",
            "Alerte apprentissage", "Alerte test"]
    return html.Div([CO.tableau(cols, lignes, numeriques=cols[1:]),
                     html.P(f"Accord des deux bras sur la décision « P(tension) > 0,5 », toutes observations : "
                            f"{CO.pourcent(accord, 1)}.", className="chapeau") if accord is not None else None])


def layout(**_):
    pre = SV.precalcul()
    tete = html.Header([html.P("Régimes", className="surtitre"), html.H1("Régimes appris sur l'apprentissage"),
                        html.P(f"Les deux bras retenus pour l'alerte sont ajustés sur les "
                               f"{SV.DESCRIPTIF[0]['observations']} observations d'apprentissage ({SV.DESCRIPTIF[0]['debut']} "
                               f"à {SV.DESCRIPTIF[0]['fin']}), variables standardisées par l'apprentissage. Le régime de "
                               "tension est, par la règle déclarée du mémoire, la composante active dont l'écart moyen des "
                               "trois denrées est le plus élevé.", className="question"),
                        CO.bandeau_precalcul(pre)], className="page-tete")
    if pre is None:
        return html.Div([tete])
    return html.Div([
        tete,
        CO.section("2.1", "Choix du nombre de régimes",
                   CO.graphe("r-bic", _bic(pre), 360, numero="2.1",
                             legende="EM classique pour K = 1 à Kmax, dix relances par K : le BIC retient K_ref, qui sert "
                                     "aussi de modèle générateur du plan semi-synthétique.")),
        CO.section("2.2", "Régimes d'un bras",
                   html.Div([html.Label(["Bras", dcc.RadioItems(SV.BRAS, SV.BRAS[0], id="r-bras", inline=True,
                                                                className="radios")], className="champ")],
                            className="controles"),
                   html.Div(id="r-profils"),
                   CO.graphe("r-poids", None, 340, numero="2.2",
                             legende="Poids de toutes les composantes du modèle ajusté. Gris : composantes inactives "
                                     "(N_k / N sous le seuil d'activité). Pour le VB, c'est l'élagage : le modèle part de "
                                     "Kmax composantes et en vide une partie."),
                   CO.graphe("r-3d", None, 620, numero="2.3",
                             legende="Les trois écarts de chaque observation, apprentissage et test, colorés par régime le "
                                     "plus probable. Faites tourner le nuage avec la souris ; cliquez sur un régime de la "
                                     "légende pour le masquer."),
                   html.Div([html.Label(["Projection", dcc.Dropdown(
                       [{"label": f"{SV.NOMS[a]} et {SV.NOMS[b]}", "value": n} for n, (a, b) in enumerate(PAIRES)], 0,
                       id="r-paire", clearable=False)], className="champ large")], className="controles"),
                   CO.graphe("r-ellipses", None, 560, numero="2.4",
                             legende="Projection sur deux denrées ; ellipses à deux écarts-types des régimes actifs "
                                     "(marginales des gaussiennes ajustées).")),
        CO.section("2.3", "EM-BIC et VB-emp côte à côte", _comparaison(pre),
                   CO.note("Ces chiffres décrivent un seul ajustement de chaque bras sur tout l'apprentissage. Les "
                           "comparaisons statistiques (répétitions, tests, correction de Holm) sont à la page 4.")),
    ])


def _couleurs(nom):
    regs = SV.regimes(nom)
    return regs, {r["k"]: r for r in regs}


@callback(Output("r-profils", "children"), Output("r-poids", "figure"), Output("r-3d", "figure"),
          Input("r-bras", "value"))
def _bras(nom):
    pre = SV.precalcul()
    b = pre["regimes"]["bras"][nom]
    regs, par_k = _couleurs(nom)
    lignes = [{"Régime": r["nom"] + (" (tension)" if r["tension"] else ""), "Poids": CO.pourcent(r["poids"], 1),
               **{f"{n}": CO.ecart_pourcent(r["mu"][j]) for j, n in enumerate(SV.NOMS)},
               "Obs. apprentissage": str(r["n_app"]), "Obs. test": str(r["n_test"]),
               "_classe": "ligne-tension" if r["tension"] else None} for r in regs]
    cols = ["Régime", "Poids"] + SV.NOMS + ["Obs. apprentissage", "Obs. test"]
    profils = html.Div([html.H3("Profil des régimes actifs"),
                        html.P("Écart moyen de chaque denrée à son niveau des douze derniers mois, converti en variation "
                               "de prix (exp(écart) − 1). Régimes numérotés par écart moyen croissant.", className="chapeau"),
                        CO.tableau(cols, lignes, numeriques=cols[1:])])

    ordre = sorted(range(len(b["pi"])), key=lambda k: -float(b["pi"][k]))
    poids = go.Figure()
    poids.add_bar(x=[par_k[k]["nom"] if k in par_k else f"c{k + 1}" for k in ordre], y=[float(b["pi"][k]) for k in ordre],
                  marker_color=[par_k[k]["couleur"] if k in par_k else INACTIF for k in ordre],
                  text=[CO.pourcent(float(b["pi"][k]), 1) for k in ordre], textposition="outside",
                  hovertemplate="%{x}<br>poids %{y:.4f}<extra></extra>")
    poids.add_hline(y=pre["regimes"]["seuil_actif"], line=dict(color=FG.ENCRE_2, dash="dash", width=1),
                    annotation_text="seuil d'activité", annotation_position="top right",
                    annotation_font_color=FG.ENCRE_2)
    CO.habiller(poids, legende=False)
    poids.update_xaxes(title_text="composante (ordre décroissant des poids)")
    poids.update_yaxes(title_text="poids π_k", tickformat=".0%")

    aff = b["affectation"].tolist()
    nuage = go.Figure()
    groupes = [(r["k"], r["nom"] + (" (tension)" if r["tension"] else ""), r["couleur"]) for r in regs]
    inactives = sorted(set(aff) - set(par_k))
    if inactives:
        groupes.append((tuple(inactives), "composante inactive", INACTIF))
    for k, etiquette, couleur in groupes:
        ks = set(k) if isinstance(k, tuple) else {k}
        idx = [i for i, a in enumerate(aff) if a in ks]
        nuage.add_scatter3d(x=[float(SV.X[i, 0]) for i in idx], y=[float(SV.X[i, 1]) for i in idx],
                            z=[float(SV.X[i, 2]) for i in idx], mode="markers", name=etiquette,
                            marker=dict(size=3.2, color=couleur, opacity=0.8,
                                        symbol=["circle" if SV.APP[i] else "diamond" for i in idx]),
                            customdata=[[SV.MARCHES[SV.MARCHE[i]], SV.mois_date(SV.MOIS[i])[:7],
                                         "apprentissage" if SV.APP[i] else "test"] for i in idx],
                            hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]} (%{customdata[2]})<br>"
                                          "maïs %{x:.3f}<br>riz %{y:.3f}<br>niébé %{z:.3f}<extra>" + etiquette + "</extra>")
    CO.habiller(nuage)
    axe = dict(gridcolor=FG.GRILLE, backgroundcolor="white", zerolinecolor=FG.ENCRE_2)
    nuage.update_layout(scene=dict(xaxis=dict(title="écart maïs", **axe), yaxis=dict(title="écart riz", **axe),
                                   zaxis=dict(title="écart niébé", **axe), aspectmode="cube"),
                        margin=dict(l=0, r=0, t=30, b=0))
    return profils, poids, nuage


def _ellipse(mu, cov, n_sigma=2.0, n=90):
    t = torch.linspace(0, 2 * math.pi, n, dtype=torch.float64)
    L = torch.linalg.cholesky(cov)
    p = torch.tensor(mu, dtype=torch.float64)[:, None] + n_sigma * L @ torch.stack([t.cos(), t.sin()])
    return p[0].tolist(), p[1].tolist()


@callback(Output("r-ellipses", "figure"), Input("r-bras", "value"), Input("r-paire", "value"))
def _projection(nom, paire):
    a, c = PAIRES[paire]
    b = SV.precalcul()["regimes"]["bras"][nom]
    regs, par_k = _couleurs(nom)
    aff = b["affectation"].tolist()
    fig = go.Figure()
    for r in regs:
        idx = [i for i, x in enumerate(aff) if x == r["k"]]
        etiquette = r["nom"] + (" (tension)" if r["tension"] else "")
        fig.add_scattergl(x=[float(SV.X[i, a]) for i in idx], y=[float(SV.X[i, c]) for i in idx], mode="markers",
                          name=etiquette, legendgroup=r["nom"], marker=dict(size=6, color=r["couleur"], opacity=0.55),
                          customdata=[[SV.MARCHES[SV.MARCHE[i]], SV.mois_date(SV.MOIS[i])[:7]] for i in idx],
                          hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>%{x:.3f} ; %{y:.3f}<extra>"
                                        + etiquette + "</extra>")
        cov = r["cov"][[a, c]][:, [a, c]]
        ex, ey = _ellipse([r["mu"][a], r["mu"][c]], cov)
        fig.add_scatter(x=ex, y=ey, mode="lines", line=dict(color=r["couleur"], width=2), legendgroup=r["nom"],
                        showlegend=False, hoverinfo="skip")
        fig.add_scatter(x=[r["mu"][a]], y=[r["mu"][c]], mode="markers", legendgroup=r["nom"], showlegend=False,
                        marker=dict(symbol="x-thin", size=12, line=dict(width=2, color=r["couleur"])),
                        hovertemplate=f"centre {etiquette}<br>%{{x:.3f}} ; %{{y:.3f}}<extra></extra>")
    CO.habiller(fig)
    fig.update_xaxes(title_text=f"écart {SV.NOMS[a]}", zeroline=True, zerolinecolor=FG.GRILLE)
    fig.update_yaxes(title_text=f"écart {SV.NOMS[c]}", zeroline=True, zerolinecolor=FG.GRILLE, scaleanchor="x",
                     scaleratio=1)
    return fig
