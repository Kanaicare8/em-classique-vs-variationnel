"""Marchés : carte du mois colorée par P(tension), puis prix et P(tension) d'un marché dans le temps."""

import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html
from plotly.subplots import make_subplots

import acces as AC
import composants as CO
import service as SV
from pages.bulletin import options_versions

dash.register_page(__name__, path="/marches", name="Marchés", order=2, title="Marchés, prix alimentaires du Cameroun")


def layout(**_):
    if not AC.peut("consulter"):
        return CO.absent("Accès refusé.")
    st = SV.etat()
    mois = SV.mois_disponibles(st)
    marches = [m for m in SV.marches_connus(st) if m.nom in set(st["marche"])]
    defaut = max(marches, key=lambda m: st["marche"].count(m.nom)).nom
    return html.Div([
        CO.tete("Marchés", "Situation des marchés",
                "La carte montre, pour un mois, la probabilité du régime de tension de chaque marché observé ; cliquer "
                "sur un marché affiche ses prix et sa probabilité dans le temps."),
        html.Div([
            html.Label(["Mois", dcc.Dropdown([{"label": SV.mois_texte(t), "value": t} for t in mois], mois[0],
                                             id="m-mois", clearable=False)], className="champ"),
            html.Label(["Bras", dcc.RadioItems(["EM-BIC", "VB-emp"], "VB-emp", id="m-bras", inline=True,
                                               className="radios")], className="champ"),
            html.Label(["Modèle", dcc.Dropdown(options_versions(), SV.REFERENCE, id="m-version", clearable=False)],
                       className="champ large"),
        ], className="controles collant"),
        CO.section("Carte du mois", CO.graphe("m-carte", None, 620,
                                               "Marchés observés ce mois-là ; couleur : P(tension) du bras choisi.")),
        CO.section("Détail d'un marché",
                   html.Label(["Marché", dcc.Dropdown([{"label": f"{m.nom}, {m.region}", "value": m.nom} for m in marches],
                                                      defaut, id="m-marche", clearable=False)], className="champ large"),
                   CO.graphe("m-detail", None, 640, "En haut, prix de détail (XAF/kg) ; en bas, P(tension) des deux bras "
                                                    "avec leur intervalle à 90 % ; ligne pointillée : seuil de 0,5.")),
    ])


@callback(Output("m-carte", "figure"), Input("m-mois", "value"), Input("m-bras", "value"), Input("m-version", "value"))
def _carte(t, bras, version):
    st = SV.etat(version)
    rel = st["releves"]
    situe = {n for n, m in rel.marches.items() if m.lat is not None and m.lat == m.lat}     # coordonnées connues
    idx = [i for i, u in enumerate(st["mois"]) if u == t and st["marche"][i] in situe]
    r = st["proba"][bras]
    fig = go.Figure()
    CO.fond_cameroun(fig)
    fig.add_scattergeo(
        lon=[rel.marches[st["marche"][i]].lon for i in idx], lat=[rel.marches[st["marche"][i]].lat for i in idx],
        mode="markers", marker=dict(size=13, color=[float(r["p"][i]) for i in idx], cmin=0, cmax=1,
                                    colorscale=CO.SEQUENTIEL, line=dict(color="#52514e", width=0.8),
                                    colorbar=dict(title="P(tension)", thickness=12, len=0.6)),
        customdata=[[st["marche"][i], float(r["p"][i]), float(r["bas"][i]), float(r["haut"][i])] for i in idx],
        hovertemplate="%{customdata[0]}<br>P %{customdata[1]:.2f} [%{customdata[2]:.2f} ; %{customdata[3]:.2f}]"
                      "<extra></extra>", showlegend=False)
    CO.habiller(fig)
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    return fig


@callback(Output("m-marche", "value"), Input("m-carte", "clickData"), prevent_initial_call=True)
def _clic(clic):
    try:
        return clic["points"][0]["customdata"][0]
    except (TypeError, KeyError, IndexError):
        return dash.no_update


@callback(Output("m-detail", "figure"), Input("m-marche", "value"), Input("m-version", "value"))
def _detail(marche, version):
    st = SV.etat(version)
    rel, fiche = st["releves"], st["modele"].fiche
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.5, 0.5])
    for j, (c, nom) in enumerate(zip(fiche["panier"], fiche["noms"])):
        s = rel.serie.get((marche, c), {})
        ts = sorted(s)
        fig.add_scatter(x=[SV.mois_texte(t) + "-15" for t in ts], y=[rel.prix(marche, c, t) for t in ts],
                        mode="lines+markers", name=nom, line=dict(color=CO.SERIES[[3, 0, 2][j]], width=1.6),
                        marker=dict(size=4, symbol=["diamond" if rel.source.get((marche, c, t)) == "saisie" else "circle"
                                                    for t in ts]),
                        hovertemplate="%{x|%Y-%m}<br>%{y:.0f} XAF/kg<extra>" + nom + "</extra>", row=1, col=1)
    obs = [i for i, m in enumerate(st["marche"]) if m == marche]
    x = [SV.mois_texte(st["mois"][i]) + "-15" for i in obs]
    for b, r in st["proba"].items():
        coul = CO.COULEUR_BRAS.get(b, CO.SERIES[6])
        fig.add_scatter(x=x + x[::-1], y=[float(r["haut"][i]) for i in obs] + [float(r["bas"][i]) for i in obs][::-1],
                        fill="toself", fillcolor=coul, opacity=0.15, line=dict(width=0), hoverinfo="skip",
                        showlegend=False, row=2, col=1)
        fig.add_scatter(x=x, y=[float(r["p"][i]) for i in obs], mode="lines+markers", name=f"P(tension), {b}",
                        line=dict(color=coul, width=2), marker=dict(size=4),
                        hovertemplate="%{x|%Y-%m}<br>P %{y:.2f}<extra>" + b + "</extra>", row=2, col=1)
    fig.add_hline(y=0.5, line=dict(color="#52514e", dash="dash", width=1), row=2, col=1)
    fin = SV.mois_texte(st["fin_apprentissage"]) + "-28"
    fig.add_vline(x=fin, line=dict(color="#52514e", dash="dot", width=1))
    CO.habiller(fig)
    fig.update_yaxes(title_text="XAF/kg", row=1, col=1)
    fig.update_yaxes(title_text="P(tension)", range=[0, 1], row=2, col=1)
    return fig
