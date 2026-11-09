"""Marchés : carte du mois, puis fiche d'un marché (dernier état, prix et probabilité dans le temps)."""

import dash
from dash import Input, Output, callback, dcc, html
from plotly.subplots import make_subplots

import acces as AC
import composants as CO
import service as SV
from bulletin_calc import MODES, bulletin
from pages.bulletin import _carte, mois_par_defaut, options_mois, options_versions

dash.register_page(__name__, path="/marches", name="Marchés", order=2, title="Marchés, prix alimentaires du Cameroun")


def layout(**_):
    if not AC.peut("consulter"):
        return CO.absent("Accès refusé.")
    st = SV.etat()
    mois = SV.mois_disponibles(st)
    marches = [m for m in SV.marches_connus(st) if m.nom in set(st["marche"])]
    defaut = max(marches, key=lambda m: st["marche"].count(m.nom)).nom
    return html.Div([
        CO.tete("Marchés", "Suivi d'un marché",
                "Choisir un marché dans la liste ou sur la carte : sa fiche montre son dernier état, ses prix et sa "
                "probabilité de tension mois après mois."),
        html.Div([
            html.Label(["Marché", dcc.Dropdown([{"label": f"{m.nom} ({m.region})", "value": m.nom} for m in marches],
                                               defaut, id="m-marche", clearable=False)], className="champ large"),
            html.Label(["Lecture", dcc.Dropdown([{"label": v, "value": k} for k, v in MODES.items()], "accord",
                                                id="m-mode", clearable=False)], className="champ", style={"minWidth": "290px"}),
        ], className="controles collant"),
        html.Div([
            html.Div(CO.chargement(html.Div(id="m-fiche")), className="carte"),
            html.Div([html.Label(["Carte du mois", dcc.Dropdown(options_mois(st), mois_par_defaut(st), id="m-mois", clearable=False)],
                                 className="champ"),
                      CO.graphe("m-carte", None, 470)]),
        ], className="grille-2", style={"marginTop": "18px"}),
        CO.section("Prix et probabilité dans le temps",
                   CO.chargement(CO.graphe("m-detail", None, 620,
                                           "En haut : prix de détail (XAF/kg), losange = relevé saisi dans l'outil. En "
                                           "bas : probabilité de tension des deux méthodes avec leur fourchette ; "
                                           "pointillés : seuil de 50 % et fin de l'apprentissage du modèle."))),
        dcc.Store(id="m-version", data=SV.REFERENCE),
        html.Details([html.Summary("Modèle utilisé"),
                      dcc.Dropdown(options_versions(), SV.REFERENCE, id="m-version-choix", clearable=False)],
                     className="aide"),
    ])


@callback(Output("m-version", "data"), Input("m-version-choix", "value"))
def _version(v):
    return v


@callback(Output("m-carte", "figure"), Input("m-mois", "value"), Input("m-mode", "value"), Input("m-version", "data"))
def _carte_mois(t, mode, version):
    st = SV.etat(version)
    return _carte(st, bulletin(st, t, mode))


@callback(Output("m-marche", "value"), Input("m-carte", "clickData"), prevent_initial_call=True)
def _clic(clic):
    try:
        return clic["points"][0]["customdata"][0]
    except (TypeError, KeyError, IndexError):
        return dash.no_update


@callback(Output("m-fiche", "children"), Input("m-marche", "value"), Input("m-mode", "value"), Input("m-version", "data"))
def _fiche(marche, mode, version):
    st = SV.etat(version)
    fiche, rel = st["modele"].fiche, st["releves"]
    obs = [i for i, m in enumerate(st["marche"]) if m == marche]
    if not obs:
        return CO.absent("Pas d'observation complète pour ce marché.")
    i = max(obs, key=lambda i: st["mois"][i])
    t = st["mois"][i]
    p, bas, haut, etat = SV.evaluation(st, mode, i)
    alertes = sum(SV.en_alerte(SV.evaluation(st, mode, j)[3]) for j in obs)
    lignes = [{"Denrée": n, "Prix (XAF/kg)": CO.nombre(rel.prix(marche, c, t), 0),
               "Écart": CO.ecart_pourcent(float(st["X"][i][k]))} for k, (n, c) in enumerate(zip(fiche["noms"],
                                                                                              fiche["panier"]))]
    return [html.H3(f"{marche} ({rel.marches[marche].region})"),
            html.P(f"Dernier mois complet : {SV.mois_humain(t)}", className="tuile-sous"),
            html.Div([CO.badge(etat), html.Span(f"probabilité {CO.pourcent(p, 0)} (fourchette {CO.pourcent(bas, 0)} à "
                                                f"{CO.pourcent(haut, 0)})", className="verdict-texte")],
                     className="verdict"),
            CO.tableau(["Denrée", "Prix (XAF/kg)", "Écart"], lignes, numeriques=["Prix (XAF/kg)", "Écart"]),
            html.P(f"En alerte {alertes} mois sur {len(obs)} observés depuis {SV.mois_humain(st['mois'][obs[0]])}.",
                   className="chapeau")]


@callback(Output("m-detail", "figure"), Input("m-marche", "value"), Input("m-version", "data"))
def _detail(marche, version):
    st = SV.etat(version)
    rel, fiche = st["releves"], st["modele"].fiche
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.5, 0.5])
    for j, (c, nom) in enumerate(zip(fiche["panier"], fiche["noms"])):
        s = rel.serie.get((marche, c), {})
        ts = sorted(s)
        fig.add_scatter(x=[SV.mois_texte(t) + "-15" for t in ts], y=[rel.prix(marche, c, t) for t in ts],
                        mode="lines+markers", name=nom, line=dict(color=CO.SERIES[[3, 0, 2][j]], width=1.6),
                        marker=dict(size=[9 if rel.source.get((marche, c, t)) == "saisie" else 4 for t in ts],
                                    symbol=["diamond" if rel.source.get((marche, c, t)) == "saisie" else "circle"
                                            for t in ts]),
                        customdata=[SV.mois_humain(t) for t in ts],
                        hovertemplate="%{customdata}<br>%{y:.0f} XAF/kg<extra>" + nom + "</extra>", row=1, col=1)
    obs = [i for i, m in enumerate(st["marche"]) if m == marche]
    x = [SV.mois_texte(st["mois"][i]) + "-15" for i in obs]
    for b, r in st["proba"].items():
        coul = CO.COULEUR_BRAS.get(b, CO.SERIES[6])
        fig.add_scatter(x=x + x[::-1], y=[float(r["haut"][i]) for i in obs] + [float(r["bas"][i]) for i in obs][::-1],
                        fill="toself", fillcolor=coul, opacity=0.15, line=dict(width=0), hoverinfo="skip",
                        showlegend=False, row=2, col=1)
        fig.add_scatter(x=x, y=[float(r["p"][i]) for i in obs], mode="lines+markers", name=SV.METHODES[b],
                        line=dict(color=coul, width=2), marker=dict(size=4),
                        customdata=[[SV.mois_humain(st["mois"][i]), float(r["bas"][i]), float(r["haut"][i])] for i in obs],
                        hovertemplate="%{customdata[0]}<br>%{y:.0%} (%{customdata[1]:.0%} à %{customdata[2]:.0%})"
                                      "<extra>" + SV.METHODES_COURT[b] + "</extra>", row=2, col=1)
    fig.add_hline(y=0.5, line=dict(color="#52514e", dash="dash", width=1), row=2, col=1)
    fig.add_vline(x=SV.mois_texte(st["fin_apprentissage"]) + "-28", line=dict(color="#52514e", dash="dot", width=1))
    CO.habiller(fig)
    fig.update_yaxes(title_text="XAF/kg", row=1, col=1)
    fig.update_yaxes(title_text="probabilité de tension", range=[0, 1], tickformat=".0%", row=2, col=1)
    return fig
