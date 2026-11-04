"""Page 1 : les données du cas pratique (extrait PAM), sans aucun modèle."""

import math

import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html
from plotly.subplots import make_subplots

import composants as CO
import figures as FG
import service as SV

dash.register_page(__name__, path="/", name="Données", order=1, title="Données · Prix alimentaires du Cameroun")


def _fiche():
    obs = [i for i in range(len(SV.MARCHES)) if SV.N_APP[i] + SV.N_TEST[i] > 0]
    app, test = SV.DESCRIPTIF
    items = [("Observations (marché, mois)", f"{app['observations'] + test['observations']}"),
             ("Apprentissage", f"{app['observations']} ({app['debut']} à {app['fin']})"),
             ("Test", f"{test['observations']} ({test['debut']} à {test['fin']})"),
             ("Marchés observés", f"{len(obs)} dans {len({SV.REGIONS[i] for i in obs})} régions"),
             ("Régions au test", f"{test['regions']}"),
             ("Relevés écartés", f"{len(SV.ECARTES)} (pics isolés d'un mois)")]
    return html.Dl([html.Div([html.Dt(t), html.Dd(v)]) for t, v in items], className="fiche")


def _carte():
    fig = go.Figure()
    for reg in SV.REGIONS_ORDRE:
        idx = [i for i, r in enumerate(SV.REGIONS) if r == reg and SV.N_APP[i] + SV.N_TEST[i] > 0]
        if not idx:
            continue
        fig.add_scattermap(lat=[SV.LAT[i] for i in idx], lon=[SV.LON[i] for i in idx], mode="markers", name=reg,
                           marker=dict(size=[6 + 1.8 * math.sqrt(SV.N_APP[i] + SV.N_TEST[i]) for i in idx],
                                       color=SV.COULEUR_REGION[reg], opacity=0.85),
                           customdata=[[i, SV.MARCHES[i], SV.N_APP[i], SV.N_TEST[i]] for i in idx],
                           hovertemplate="<b>%{customdata[1]}</b><br>apprentissage : %{customdata[2]} obs."
                                         "<br>test : %{customdata[3]} obs.<extra>" + reg + "</extra>")
    CO.habiller(fig)
    fig.update_layout(map=dict(style="carto-positron", center=dict(lat=7.2, lon=12.7), zoom=4.75),
                      margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="v", x=0.01, y=0.99, yanchor="top",
                                                                   bgcolor="rgba(255,255,255,0.85)"))
    return fig


def _distributions():
    fig = make_subplots(rows=1, cols=3, subplot_titles=SV.NOMS, horizontal_spacing=0.06)
    for j, nom in enumerate(SV.NOMS, start=1):
        for periode, couleur, masque in (("apprentissage", FG.SERIES[0], True), ("test", FG.SERIES[1], False)):
            x = [float(SV.X[i, j - 1]) for i in range(len(SV.MOIS)) if SV.APP[i] == masque]
            fig.add_histogram(x=x, name=periode, legendgroup=periode, showlegend=j == 1, marker_color=couleur,
                              opacity=0.55, histnorm="probability density", nbinsx=40, row=1, col=j,
                              hovertemplate="écart %{x}<br>densité %{y:.2f}<extra>" + periode + "</extra>")
    CO.habiller(fig)
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title_text="écart du log-prix", zeroline=True, zerolinecolor=FG.ENCRE_2)
    fig.update_yaxes(title_text="densité", col=1)
    return fig


def _options_marches():
    idx = [i for i in range(len(SV.MARCHES)) if SV.N_APP[i] + SV.N_TEST[i] > 0]
    idx.sort(key=lambda i: (SV.REGIONS_ORDRE.index(SV.REGIONS[i]), SV.MARCHES[i]))
    return [{"label": f"{SV.MARCHES[i]} ({SV.REGIONS[i]})", "value": i} for i in idx]


def _tableau_descriptif():
    lignes = []
    for d in SV.DESCRIPTIF:
        for nom in SV.NOMS:
            lignes.append({"Période": d["periode"], "Denrée": nom, "Moyenne": CO.nombre(d[f"moyenne_{nom}"], 3, True),
                           "Écart-type": CO.nombre(d[f"ecart_type_{nom}"], 3),
                           "Kurtosis en excès": CO.nombre(d[f"kurtosis_exc_{nom}"], 2)})
    return CO.tableau(["Période", "Denrée", "Moyenne", "Écart-type", "Kurtosis en excès"], lignes,
                      numeriques=("Moyenne", "Écart-type", "Kurtosis en excès"))


def _tableau_ecartes():
    noms = dict(zip(SV.PANIER, SV.NOMS))
    lignes = [{"Mois": e["mois"], "Marché": e["marche"], "Denrée": noms.get(e["denree"], e["denree"]),
               "Prix relevé (XAF/kg)": CO.nombre(e["prix"], 0)} for e in SV.ECARTES]
    return CO.tableau(["Mois", "Marché", "Denrée", "Prix relevé (XAF/kg)"], lignes, numeriques=("Prix relevé (XAF/kg)",))


def layout(**_):
    return html.Div([
        html.Header([
            html.P("Cas pratique du chapitre 3", className="surtitre"),
            html.H1("Régimes de tension des prix alimentaires sur les marchés du Cameroun"),
            html.P("Un mélange gaussien peut-il apprendre des régimes de prix à partir des données, sans seuils fixés à "
                   "l'avance, et attacher à chaque marché et à chaque mois une probabilité d'être en régime de tension, "
                   "avec une incertitude sur cette probabilité ?", className="question"),
            _fiche(),
        ], className="page-tete"),

        CO.section("1.1", "Marchés suivis",
                   html.P("Base de prix du PAM (HDX, licence CC BY-IGO). Taille du point : nombre d'observations retenues. "
                          "Cliquez sur un marché pour afficher ses séries ci-dessous.", className="chapeau"),
                   CO.graphe("d-carte", _carte(), 560, numero="1.1",
                             legende="Marchés du panier maïs blanc, riz importé, niébé ; couleur par région.")),

        CO.section("1.2", "Séries d'un marché",
                   html.Div([
                       html.Label(["Marché", dcc.Dropdown(_options_marches(), SV.marche_par_defaut(), id="d-marche",
                                                          clearable=False)], className="champ large"),
                       html.Label(["Denrées", dcc.Checklist(SV.NOMS, SV.NOMS, id="d-denrees", inline=True,
                                                            className="cases")], className="champ"),
                   ], className="controles"),
                   CO.graphe("d-prix", None, 400, numero="1.2",
                             legende="Prix de détail relevés, en francs CFA par kilogramme. Croix : relevés écartés par "
                                     "la règle de nettoyage déclarée. Trait pointillé : fin de l'apprentissage (décembre 2023)."),
                   CO.graphe("d-ecarts", None, 400, numero="1.3",
                             legende="Variables du modèle : écart du log-prix du mois à la moyenne des log-prix des douze "
                                     "mois précédents. Un écart de +0,30 correspond à un prix environ 35 % au-dessus de "
                                     "son niveau récent.")),

        CO.section("1.3", "Apprentissage et test ne suivent pas la même loi",
                   CO.graphe("d-distrib", _distributions(), 380, numero="1.4",
                             legende="Distribution des écarts par denrée, apprentissage (2021-2023) et test (2024-2026)."),
                   _tableau_descriptif(),
                   CO.note("La période de test ne couvre que trois régions et sa distribution diffère de celle de "
                           "l'apprentissage : c'est une limite déclarée du mémoire (section 2.5).")),

        CO.section("1.4", "Relevés écartés",
                   html.P("Règle fixée avant tout ajustement : un relevé est écarté s'il diffère d'un facteur au moins 3, "
                          "dans le même sens, des relevés du mois précédent et du mois suivant. Parce qu'elle utilise le mois "
                          "suivant, cette règle convient à une analyse rétrospective, pas à une alerte en temps réel.",
                          className="chapeau"),
                   html.Details([html.Summary(f"Afficher les {len(SV.ECARTES)} relevés écartés"), _tableau_ecartes()])),
    ])


@callback(Output("d-marche", "value"), Input("d-carte", "clickData"), prevent_initial_call=True)
def _clic_carte(clic):
    return int(clic["points"][0]["customdata"][0])


@callback(Output("d-prix", "figure"), Output("d-ecarts", "figure"), Input("d-marche", "value"), Input("d-denrees", "value"))
def _series(i, choix):
    m = SV.MARCHES[i]
    fin = SV.mois_date(SV.FIN_APP)
    prix = go.Figure()
    legende_ecart = True
    for nom, com in zip(SV.NOMS, SV.PANIER):
        if nom not in choix:
            continue
        ecartes = {e["mois"] for e in SV.ECARTES if e["marche"] == m and e["denree"] == com}
        s = SV.PRIX.get((m, com), [])
        gardes = [(t, p) for t, p in s if t not in ecartes]
        prix.add_scatter(x=[t + "-15" for t, _ in gardes], y=[p for _, p in gardes], mode="lines+markers", name=nom,
                         line=dict(color=SV.COULEUR_DENREE[nom], width=2), marker=dict(size=6),
                         hovertemplate="%{x|%Y-%m}<br>%{y:,.0f} XAF/kg<extra>" + nom + "</extra>")
        hors = [(t, p) for t, p in s if t in ecartes]
        if hors:
            prix.add_scatter(x=[t + "-15" for t, _ in hors], y=[p for _, p in hors], mode="markers", name="relevé écarté",
                             marker=dict(symbol="x", size=10, color=FG.ENCRE_2), showlegend=legende_ecart,
                             legendgroup="ecarte", hovertemplate="%{x|%Y-%m}<br>%{y:,.0f} XAF/kg (écarté)<extra>" + nom + "</extra>")
            legende_ecart = False
    prix.add_vline(x=fin, line=dict(color=FG.ENCRE_2, dash="dot", width=1))
    CO.habiller(prix)
    prix.update_yaxes(title_text="XAF / kg", rangemode="tozero")

    obs = SV.observations(i)
    ec = go.Figure()
    x = [SV.mois_date(SV.MOIS[o]) for o in obs]
    for j, nom in enumerate(SV.NOMS):
        if nom not in choix:
            continue
        y = [float(SV.X[o, j]) for o in obs]
        ec.add_scatter(x=x, y=y, mode="lines+markers", name=nom, line=dict(color=SV.COULEUR_DENREE[nom], width=2),
                       marker=dict(size=6), customdata=[CO.ecart_pourcent(v) for v in y],
                       hovertemplate="%{x|%Y-%m}<br>écart %{y:.3f} (prix %{customdata})<extra>" + nom + "</extra>")
    ec.add_hline(y=0, line=dict(color=FG.ENCRE_2, width=1))
    ec.add_vline(x=fin, line=dict(color=FG.ENCRE_2, dash="dot", width=1))
    CO.habiller(ec)
    ec.update_yaxes(title_text="écart du log-prix")
    if not obs:
        ec.add_annotation(text="aucune observation complète (trois écarts définis) pour ce marché", showarrow=False,
                          xref="paper", yref="paper", x=0.5, y=0.5, font=dict(color=FG.ENCRE_2))
    return prix, ec
