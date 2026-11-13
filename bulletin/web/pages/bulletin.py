"""Accueil : bulletin du mois. Chiffres clés, carte, évolution, situation par région, marchés à surveiller, exports."""

from urllib.parse import urlencode

import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

import acces as AC
import composants as CO
import service as SV
from bulletin_calc import MODES, bulletin

dash.register_page(__name__, path="/", name="Bulletin", order=1, title="Bulletin, prix alimentaires du Cameroun")


def options_versions():
    return [{"label": f["libelle"], "value": f["version"]} for f in SV.liste_versions()]


def _effectifs(st):
    n = {}
    for t in st["mois"]:
        n[t] = n.get(t, 0) + 1
    return n


def options_mois(st):
    n = _effectifs(st)
    return [{"label": f"{SV.mois_humain(t)} ({n[t]} marché{'s' if n[t] > 1 else ''})", "value": t}
            for t in SV.mois_disponibles(st)]


def mois_par_defaut(st):
    """Dernier mois bien couvert : au moins la moitié du nombre médian de marchés des douze derniers mois (un mois
    qui ne contient encore qu'un ou deux relevés saisis ne doit pas ouvrir le bulletin)."""
    n = _effectifs(st)
    mois = SV.mois_disponibles(st)
    recents = sorted(n[t] for t in mois[:12])
    seuil = max(3, recents[len(recents) // 2] / 2)
    return next((t for t in mois if n[t] >= seuil), mois[0])


def aide_lecture():
    return CO.aide("Comment lire ce bulletin", html.Ul([
        html.Li(["Chaque marché reçoit une ", html.Strong("probabilité de tension"), " : la chance que ses écarts de prix "
                 "du mois ressemblent à ceux des périodes de tension apprises sur 2021-2023. La ", html.Strong("fourchette"),
                 " dit à quel point le modèle est sûr de ce chiffre (90 %)."]),
        html.Li([CO.badge("alerte"), " probabilité au-dessus de 50 %, fourchette comprise ; ", CO.badge("alerte_probable"),
                 " au-dessus de 50 % mais la fourchette descend sous 50 % ; ", CO.badge("surveiller"),
                 " sous 50 % mais la fourchette monte au-dessus ; ", CO.badge("desaccord"),
                 " une seule des deux méthodes voit une tension ; ", CO.badge("calme"), " le reste."]),
        html.Li(["La lecture ", html.Strong("prudente"), " combine les deux méthodes du mémoire : alerte seulement si "
                 "les deux la donnent, désaccord signalé sinon."]),
        html.Li("Écart : prix du mois comparé à son niveau habituel (moyenne des douze mois précédents). Un marché "
                "n'apparaît que si les trois denrées ont un prix ce mois-là et assez de relevés passés."),
        html.Li("Une alerte appelle une vérification sur le terrain : le modèle n'a pas de vérité terrain."),
    ]))


def layout(**_):
    if not AC.peut("consulter"):
        return CO.absent("Accès refusé.")
    st = SV.etat()
    mois = SV.mois_disponibles(st)
    return html.Div([
        CO.tete("Bulletin", "Bulletin mensuel des marchés",
                "Où les prix des denrées de base sortent-ils de leur niveau habituel ce mois-ci ? Maïs blanc, riz importé "
                "et niébé, sur les marchés suivis par le Programme alimentaire mondial et les relevés validés."),
        html.Div([
            html.Label(["Mois", dcc.Dropdown(options_mois(st), mois_par_defaut(st), id="b-mois", clearable=False)],
                       className="champ"),
            html.Label(["Lecture", dcc.Dropdown([{"label": v, "value": k} for k, v in MODES.items()], "accord",
                                                id="b-mode", clearable=False)], className="champ large"),
            html.Div([html.A("Télécharger le PDF", id="b-pdf", className="bouton", href="#"),
                      html.A("CSV", id="b-csv", className="bouton secondaire", href="#")], className="boutons"),
        ], className="controles collant"),
        CO.chargement(html.Div(id="b-contenu")),
        aide_lecture(),
        html.Details([html.Summary("Modèle utilisé"),
                      html.Label(["Modèle", dcc.Dropdown(options_versions(), SV.REFERENCE, id="b-version",
                                                         clearable=False)], className="champ large"),
                      html.P(f"Données : {st['extrait']['origine']}, jusqu'à {SV.mois_humain(max(mois))}.",
                             className="chapeau")], className="aide"),
    ])


def _carte(st, b):
    rel = st["releves"]
    fig = go.Figure()
    CO.fond_cameroun(fig, lon=(8.3, 16.4), lat=(1.6, 13.2))
    for etat in ("calme", "surveiller", "desaccord", "alerte_probable", "alerte"):
        ls = [l for l in b["toutes"] if l["etat"] == etat and rel.marches[l["marche"]].lat == rel.marches[l["marche"]].lat
              and rel.marches[l["marche"]].lat is not None]
        if not ls:
            continue
        libelle, couleur, *_ = SV.ETATS[etat]
        fig.add_scattergeo(lon=[rel.marches[l["marche"]].lon for l in ls], lat=[rel.marches[l["marche"]].lat for l in ls],
                           mode="markers", name=f"{libelle} ({len(ls)})",
                           marker=dict(size=14 if etat != "calme" else 10, color=CO.COULEUR_ETAT[couleur],
                                       line=dict(color="white", width=1.2)),
                           customdata=[[l["marche"], l["p_txt"], l["ic_txt"]] for l in ls],
                           hovertemplate="<b>%{customdata[0]}</b><br>probabilité %{customdata[1]} "
                                         "(fourchette %{customdata[2]})<extra>" + libelle + "</extra>")
    CO.habiller(fig)
    fig.update_layout(margin=dict(l=0, r=0, t=4, b=0), legend=dict(y=-0.02, x=0, yanchor="top", orientation="h"))
    return fig


def _evolution(b, t):
    serie = b["serie"]
    ts = sorted(serie)
    x = [SV.mois_texte(u) + "-15" for u in ts]
    fig = go.Figure()
    fig.add_bar(x=x, y=[serie[u][1] for u in ts], name="en alerte", marker_color=CO.COULEUR_ETAT["rouge"],
                customdata=[SV.mois_humain(u) for u in ts], hovertemplate="%{customdata}<br>%{y} en alerte<extra></extra>")
    fig.add_bar(x=x, y=[serie[u][2] for u in ts], name="à surveiller", marker_color=CO.COULEUR_ETAT["ambre"],
                customdata=[SV.mois_humain(u) for u in ts],
                hovertemplate="%{customdata}<br>%{y} à surveiller<extra></extra>")
    fig.add_vrect(x0=SV.mois_texte(t) + "-01", x1=SV.mois_texte(t) + "-28", fillcolor="#1F7A4D", opacity=0.12,
                  line_width=0)
    CO.habiller(fig)
    fig.update_layout(barmode="stack", bargap=0.15, margin=dict(l=40, r=10, t=30, b=30))
    fig.update_yaxes(title_text="marchés")
    return fig


@callback(Output("b-contenu", "children"), Output("b-pdf", "href"), Output("b-csv", "href"),
          Input("b-mois", "value"), Input("b-mode", "value"), Input("b-version", "value"))
def _afficher(t, mode, version):
    st = SV.etat(version)
    b = bulletin(st, t, mode)
    q = urlencode({"mois": SV.mois_texte(t), "mode": mode, "version": version})
    liens = f"/export/bulletin.pdf?{q}", f"/export/bulletin.csv?{q}"
    if not b["toutes"]:
        return CO.absent("Aucun marché observé ce mois-là."), *liens
    n, na, ns = len(b["toutes"]), len(b["alerte"]), len(b["surveiller"])
    prec = b["precedent"]

    def variation(k, v):
        if prec is None:
            return None
        d = v - prec[k]
        return f"{'+' if d > 0 else '−'}{abs(d)} par rapport à {SV.mois_humain(b['mois_precedent'])}" if d else \
            f"comme en {SV.mois_humain(b['mois_precedent'])}"
    chiffres = CO.tuiles(CO.tuile("Marchés observés", str(n), b["periode"]),
                         CO.tuile("En alerte", str(na), variation(1, na), "rouge"),
                         CO.tuile("À surveiller", str(ns), variation(2, ns), "ambre"),
                         CO.tuile("Calmes", str(n - na - ns), None, "vert"))
    noms = st["modele"].fiche["noms"]
    regions = CO.tableau(["Région", "Marchés", "En alerte", "À surveiller", "D'habitude en alerte"], [
        {"Région": r["region"], "Marchés": str(r["n"]), "En alerte": str(r["alerte"]),
         "À surveiller": str(r["surveiller"]), "D'habitude en alerte": CO.pourcent(r["habituelle"], 0),
         "_classe": "ligne-tension" if r["alerte"] else None} for r in b["regions"]],
        numeriques=["Marchés", "En alerte", "À surveiller", "D'habitude en alerte"])
    vue = html.Div([
        html.Div([html.H2("Carte du mois"), CO.graphe("b-carte", _carte(st, b), 560)]),
        html.Div([html.H2("Par région"), regions,
                  html.P("« D'habitude en alerte » : part des mois où les marchés de la région sont en alerte, pour "
                         "situer le mois choisi.", className="chapeau"),
                  html.H2("Évolution"), CO.graphe("b-evolution", _evolution(b, t), 240,
                                                  "Nombre de marchés en alerte et à surveiller chaque mois ; bande "
                                                  "verte : mois affiché. Cliquer sur un mois pour l'afficher.")]),
    ], className="grille-2")
    if b["a_voir"]:
        cols = ["Marché", "Région", "État", "Probabilité", "Fourchette"] + [f"{n_} (XAF/kg)" for n_ in noms]
        lignes = [{"Marché": [html.Strong(l["marche"])] + ([" ", html.Span("relevé saisi", className="etiquette")]
                                                           if l["saisie"] else []),
                   "Région": l["region"], "État": CO.badge(l["etat"]), "Probabilité": l["p_txt"],
                   "Fourchette": l["ic_txt"],
                   **{f"{n_} (XAF/kg)": html.Span([p, html.Span(f" ({e})", className="hausse" if e.startswith("+")
                                                                else "baisse" if e.startswith("−") else None)])
                      for n_, p, e in zip(noms, l["prix_txt"], l["ecarts_txt"])}} for l in b["a_voir"]]
        a_voir = html.Div([CO.tableau(cols, lignes, numeriques=cols[3:]),
                           html.P("Entre parenthèses : écart du prix à son niveau des douze mois précédents.",
                                  className="chapeau")])
    else:
        a_voir = CO.absent("Aucun marché en alerte ni à surveiller ce mois-là.")
    return [html.P(b["phrase"], className="question", style={"marginTop": "18px"}), chiffres, vue,
            CO.section("Marchés à surveiller", a_voir)], *liens


@callback(Output("b-mois", "value"), Input("b-evolution", "clickData"), prevent_initial_call=True)
def _choisir_mois(clic):
    try:
        x = clic["points"][0]["x"]
        return SV.mois_index(x[:7])
    except (TypeError, KeyError, IndexError):
        return dash.no_update
