"""Page 3 : probabilité du régime de tension par marché et par mois, avec son intervalle (unité « alerte »)."""

import dash
import plotly.graph_objects as go
from dash import Input, Output, State, callback, ctx, dcc, html, no_update
from plotly.subplots import make_subplots

import composants as CO
import figures as FG
import service as SV

dash.register_page(__name__, path="/alerte", name="Alerte", order=3, title="Alerte · Prix alimentaires du Cameroun")

ECHELLE = [[0.0, "#e8f1fb"], [0.5, "#f2c46d"], [1.0, "#c8352f"]]
EPISODE = "rgba(82, 81, 78, 0.10)"


def _mois_defaut():
    """Premier épisode daté (août 2023) : le mois que le jury voudra voir en premier."""
    t = SV.DO.mois_index(SV.EPISODES[0][0])
    return SV.MOIS_TOUS.index(t) if t in SV.MOIS_TOUS else len(SV.MOIS_TOUS) - 1


def _marches_observes():
    idx = [i for i in range(len(SV.MARCHES)) if SV.N_APP[i] + SV.N_TEST[i] > 0]
    return sorted(idx, key=lambda i: (SV.REGIONS_ORDRE.index(SV.REGIONS[i]), SV.MARCHES[i]))


def _etiquette(i):
    return f"{SV.MARCHES[i]} · {SV.REGIONS[i]}"


def _lecture(p, bas, haut):
    if p > 0.5:
        return ("alerte", "ligne-tension") if bas > 0.5 else ("alerte, IC contient 0,5", "ligne-incertaine")
    return ("calme, IC contient 0,5", "ligne-incertaine") if haut >= 0.5 else ("calme", None)


def _episodes(fig, **rc):
    for m, _ in SV.EPISODES:
        fig.add_vrect(x0=m + "-01", x1=m + "-28", fillcolor=EPISODE, line_width=0, layer="below", **rc)


def _part_mensuelle(a):
    fig = go.Figure()
    for nom in SV.BRAS:
        if nom not in a:
            continue
        al = (a[nom]["proba"] > 0.5).double()
        fig.add_scatter(x=[SV.mois_date(t) for t in SV.MOIS_TOUS],
                        y=[float(al[SV.D["mois"] == t].mean()) for t in SV.MOIS_TOUS],
                        customdata=[int((SV.D["mois"] == t).sum()) for t in SV.MOIS_TOUS],
                        mode="lines+markers", name=nom, line=dict(color=FG.COULEUR[nom], width=2), marker=dict(size=6),
                        hovertemplate="%{x|%Y-%m}<br>%{y:.0%} des %{customdata} marchés observés<extra>" + nom + "</extra>")
    fig.add_vline(x=SV.mois_date(SV.FIN_APP), line=dict(color=FG.ENCRE_2, dash="dot", width=1))
    fig.add_annotation(x=SV.mois_date(SV.FIN_APP), y=1, yref="paper", text="fin de l'apprentissage", showarrow=False,
                       xanchor="left", xshift=4, font=dict(color=FG.ENCRE_2, size=11))
    _episodes(fig)
    for m, texte in SV.EPISODES:
        fig.add_annotation(x=m + "-15", y=0.92, yref="paper", text=texte.split(" : ")[0], showarrow=False,
                           font=dict(color=FG.ENCRE_2, size=11), textangle=-90, xshift=-8)
    CO.habiller(fig)
    fig.update_yaxes(title_text="part des marchés en alerte", tickformat=".0%", range=[0, 1])
    return fig


def _synthese(pre):
    lignes = [{"Bras": l["bras"], "Période": l["periode"], "Part en alerte": CO.pourcent(l["part_alerte"], 1),
               "Largeur moyenne de l'IC à 90 %": CO.nombre(l.get("largeur_ic90_moyenne"), 3),
               "IC contenant 0,5": CO.pourcent(l.get("part_ic_chevauche_0.5"), 1)}
              for l in pre["lignes_alerte"] if not l["bras"].startswith("accord")]
    cols = ["Bras", "Période", "Part en alerte", "Largeur moyenne de l'IC à 90 %", "IC contenant 0,5"]
    return CO.tableau(cols, lignes, numeriques=cols[2:])


def layout(**_):
    pre = SV.precalcul()
    tete = html.Header([html.P("Page 3", className="surtitre"), html.H1("Probabilité du régime de tension"),
                        html.P("Pour chaque marché et chaque mois, probabilité a posteriori d'appartenir au régime de "
                               "tension, avec un intervalle à 90 % : crédibilité (tirages de la loi variationnelle q) pour "
                               "VB-emp, bootstrap à démarrage chaud pour EM-BIC. Le seuil de 0,5 sert à résumer, pas à "
                               "décider : un intervalle qui contient 0,5 signale une observation ambiguë.",
                               className="question"),
                        CO.bandeau_precalcul(pre)], className="page-tete")
    if pre is None:
        return html.Div([tete])
    marches = _marches_observes()
    annees = {i: SV.DO.mois_texte(t)[:4] for i, t in enumerate(SV.MOIS_TOUS) if t % 12 == 0}
    return html.Div([
        tete,
        html.Div([
            html.Label(["Bras", dcc.RadioItems(SV.BRAS, SV.BRAS[1], id="a-bras", inline=True, className="radios")],
                       className="champ"),
            html.Label([html.Span(id="a-mois-texte"),
                        dcc.Slider(0, len(SV.MOIS_TOUS) - 1, 1, value=_mois_defaut(), id="a-mois", marks=annees,
                                   included=False, updatemode="drag")], className="champ large"),
        ], className="controles collant"),

        CO.section("3.1", "Carte du mois",
                   html.Div([
                       CO.graphe("a-carte", None, 520, numero="3.1",
                                 legende="Marchés observés ce mois-là ; couleur : P(tension). Cliquez sur un marché pour "
                                         "afficher son détail (section 3.3)."),
                       html.Div(id="a-table-mois", className="colonne-table"),
                   ], className="deux-colonnes")),

        CO.section("3.2", "Tous les marchés, tous les mois",
                   CO.graphe("a-chaleur", None, max(520, 13 * len(marches) + 140), numero="3.2",
                             legende="P(tension) par marché (lignes, groupées par région) et par mois (colonnes) ; case "
                                     "blanche : pas d'observation complète. Cliquez sur une case pour choisir le marché "
                                     "et le mois.")),

        CO.section("3.3", "Détail d'un marché",
                   html.Div([html.Label(["Marché", dcc.Dropdown([{"label": _etiquette(i), "value": i} for i in marches],
                                                                SV.marche_par_defaut(), id="a-marche", clearable=False)],
                                        className="champ large")], className="controles"),
                   CO.graphe("a-detail", None, 620, numero="3.3",
                             legende="En haut, les trois écarts du marché ; en bas, P(tension) selon les deux bras, bandes "
                                     "à 90 %. Bandes grises verticales : épisodes datés par les bulletins (" +
                                     " ; ".join(t for _, t in SV.EPISODES) + ").")),

        CO.section("3.4", "Part des marchés en alerte",
                   CO.graphe("a-part", _part_mensuelle(pre["alerte"]), 420, numero="3.4",
                             legende="Part mensuelle des observations avec P(tension) > 0,5. La confrontation aux épisodes "
                                     "des bulletins est qualitative : le régime de tension n'a pas de vérité terrain."),
                   _synthese(pre)),
    ])


@callback(Output("a-mois-texte", "children"), Input("a-mois", "value"))
def _mois_texte(j):
    t = SV.MOIS_TOUS[j]
    return f"Mois : {SV.DO.mois_texte(t)} ({'apprentissage' if t <= SV.FIN_APP else 'test'})"


@callback(Output("a-carte", "figure"), Output("a-table-mois", "children"), Input("a-bras", "value"), Input("a-mois", "value"))
def _carte(nom, j):
    a = SV.precalcul()["alerte"]
    t = SV.MOIS_TOUS[j]
    obs = [i for i, m in enumerate(SV.MOIS) if m == t]
    p, ic = a[nom]["proba"], a[nom]["ic"]
    mk = [SV.MARCHE[i] for i in obs]
    fig = go.Figure()
    fig.add_scattermap(lat=[SV.LAT[m] for m in mk], lon=[SV.LON[m] for m in mk], mode="markers",
                       marker=dict(size=15, color=[float(p[i]) for i in obs], colorscale=ECHELLE, cmin=0, cmax=1,
                                   colorbar=dict(title=dict(text="P(tension)", side="right"), thickness=12, len=0.7,
                                                 tickformat=".1f", outlinewidth=0)),
                       customdata=[[m, SV.MARCHES[m], SV.REGIONS[m], float(ic[0, i]), float(ic[1, i])] for m, i in zip(mk, obs)],
                       hovertemplate="<b>%{customdata[1]}</b> (%{customdata[2]})<br>P(tension) %{marker.color:.2f}"
                                     "<br>IC 90 % [%{customdata[3]:.2f} ; %{customdata[4]:.2f}]<extra></extra>",
                       showlegend=False)
    CO.habiller(fig)
    fig.update_layout(map=dict(style="carto-positron", center=dict(lat=7.2, lon=12.7), zoom=4.75),
                      margin=dict(l=0, r=0, t=0, b=0))

    lignes = []
    for i in sorted(obs, key=lambda i: -float(p[i])):
        lecture, classe = _lecture(float(p[i]), float(ic[0, i]), float(ic[1, i]))
        lignes.append({"Marché": SV.MARCHES[SV.MARCHE[i]], "Région": SV.REGIONS[SV.MARCHE[i]],
                       "P(tension)": CO.nombre(float(p[i]), 2),
                       "IC 90 %": f"[{CO.nombre(float(ic[0, i]), 2)} ; {CO.nombre(float(ic[1, i]), 2)}]",
                       "Lecture": lecture, "_classe": classe})
    table = html.Div([html.H3(f"{len(obs)} marchés observés en {SV.DO.mois_texte(t)}"),
                      CO.tableau(["Marché", "Région", "P(tension)", "IC 90 %", "Lecture"], lignes,
                                 numeriques=("P(tension)", "IC 90 %"))]) if obs else CO.absent("Aucun marché observé ce mois-là.")
    return fig, table


@callback(Output("a-chaleur", "figure"), Input("a-bras", "value"))
def _chaleur(nom):
    a = SV.precalcul()["alerte"]
    p = a[nom]["proba"]
    marches = _marches_observes()
    ligne = {m: r for r, m in enumerate(marches)}
    col = {t: c for c, t in enumerate(SV.MOIS_TOUS)}
    z = [[None] * len(SV.MOIS_TOUS) for _ in marches]
    for i, (m, t) in enumerate(zip(SV.MARCHE, SV.MOIS)):
        z[ligne[m]][col[t]] = float(p[i])
    fig = go.Figure(go.Heatmap(z=z, x=[SV.mois_date(t) for t in SV.MOIS_TOUS], y=[_etiquette(m) for m in marches],
                               colorscale=ECHELLE, zmin=0, zmax=1, xgap=1, ygap=1, hoverongaps=False,
                               colorbar=dict(title=dict(text="P(tension)", side="right"), thickness=12, len=0.5,
                                             y=1, yanchor="top", outlinewidth=0),
                               hovertemplate="%{y}<br>%{x|%Y-%m}<br>P(tension) %{z:.2f}<extra>" + nom + "</extra>"))
    fig.add_vline(x=SV.mois_date(SV.FIN_APP), line=dict(color=FG.ENCRE, dash="dot", width=1.5))
    CO.habiller(fig, legende=False)
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(size=10), title_text="")
    fig.update_xaxes(showgrid=False, side="top")
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=20))
    return fig


@callback(Output("a-marche", "value"), Output("a-mois", "value"),
          Input("a-carte", "clickData"), Input("a-chaleur", "clickData"), State("a-mois", "value"),
          prevent_initial_call=True)
def _clics(clic_carte, clic_chaleur, mois):
    if ctx.triggered_id == "a-carte" and clic_carte:
        return int(clic_carte["points"][0]["customdata"][0]), no_update
    if ctx.triggered_id == "a-chaleur" and clic_chaleur:
        pt = clic_chaleur["points"][0]
        par_nom = {_etiquette(i): i for i in _marches_observes()}
        t = SV.DO.mois_index(str(pt["x"])[:7])
        return par_nom.get(pt["y"], no_update), SV.MOIS_TOUS.index(t) if t in SV.MOIS_TOUS else mois
    return no_update, no_update


@callback(Output("a-detail", "figure"), Input("a-marche", "value"))
def _detail(m):
    a = SV.precalcul()["alerte"]
    obs = SV.observations(m)
    x = [SV.mois_date(SV.MOIS[i]) for i in obs]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.07, row_heights=[0.42, 0.58])
    for j, nom in enumerate(SV.NOMS):
        y = [float(SV.X[i, j]) for i in obs]
        fig.add_scatter(x=x, y=y, mode="lines+markers", name=f"écart {nom}", line=dict(color=SV.COULEUR_DENREE[nom], width=2),
                        marker=dict(size=6), customdata=[CO.ecart_pourcent(v) for v in y],
                        hovertemplate="%{x|%Y-%m}<br>%{y:.3f} (prix %{customdata})<extra>" + nom + "</extra>", row=1, col=1)
    for nom in SV.BRAS:
        if nom not in a:
            continue
        p, ic = a[nom]["proba"], a[nom]["ic"]
        bas, haut = [float(ic[0, i]) for i in obs], [float(ic[1, i]) for i in obs]
        fig.add_scatter(x=x + x[::-1], y=haut + bas[::-1], fill="toself", mode="lines", line=dict(width=0),
                        fillcolor=FG.COULEUR[nom], opacity=0.18, hoverinfo="skip", legendgroup=nom, showlegend=False,
                        row=2, col=1)
        fig.add_scatter(x=x, y=[float(p[i]) for i in obs], mode="lines+markers", name=f"P(tension), {nom}",
                        legendgroup=nom, line=dict(color=FG.COULEUR[nom], width=2), marker=dict(size=6),
                        customdata=list(zip(bas, haut)),
                        hovertemplate="%{x|%Y-%m}<br>P %{y:.2f} [%{customdata[0]:.2f} ; %{customdata[1]:.2f}]<extra>"
                                      + nom + "</extra>", row=2, col=1)
    for r in (1, 2):
        fig.add_vline(x=SV.mois_date(SV.FIN_APP), line=dict(color=FG.ENCRE_2, dash="dot", width=1), row=r, col=1)
        _episodes(fig, row=r, col=1)
    fig.add_hline(y=0, line=dict(color=FG.ENCRE_2, width=1), row=1, col=1)
    fig.add_hline(y=0.5, line=dict(color=FG.ENCRE_2, dash="dash", width=1), row=2, col=1)
    CO.habiller(fig)
    fig.update_yaxes(title_text="écart du log-prix", row=1, col=1)
    fig.update_yaxes(title_text="P(tension)", range=[0, 1], row=2, col=1)
    fig.update_layout(title=dict(text=_etiquette(m), x=0, font=dict(size=15)), margin=dict(t=70))
    return fig
