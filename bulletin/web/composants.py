"""Composants communs de l'outil : formats français, tableaux, notes, figures, fond de carte hors ligne."""

from __future__ import annotations

import math

from dash import dcc, html

POLICE = "'Source Sans 3', 'Segoe UI', Arial, sans-serif"
ENCRE, ENCRE_2, GRILLE = "#14432A", "#52514e", "#e6e8ee"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
COULEUR_BRAS = {"EM-BIC": SERIES[0], "VB-emp": SERIES[1]}
SEQUENTIEL = [[0.0, "#eef2f6"], [0.5, "#eda100"], [1.0, "#c8352f"]]

CONFIG = {"displaylogo": False, "responsive": True, "scrollZoom": False,
          "modeBarButtonsToRemove": ["lasso2d", "select2d"],
          "toImageButtonOptions": {"format": "png", "scale": 3}, "topojsonURL": "/assets/topojson/"}


def nombre(x, d=2, signe=False):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    if round(x, d) == 0:
        x, signe = 0.0, False
    s = f"{x:+,.{d}f}" if signe else f"{x:,.{d}f}"
    return s.replace(",", " ").replace(".", ",").replace("-", "−")


def pourcent(x, d=0, signe=False):
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else nombre(100 * x, d, signe) + " %"


def ecart_pourcent(e_log):
    return "–" if e_log is None else pourcent(math.expm1(e_log), 0, signe=True)


def tableau(colonnes, lignes, numeriques=()):
    tete = html.Thead(html.Tr([html.Th(c, className="num" if c in numeriques else None) for c in colonnes]))
    corps = html.Tbody([html.Tr([html.Td(l.get(c, ""), className="num" if c in numeriques else None) for c in colonnes],
                                className=l.get("_classe")) for l in lignes])
    return html.Div(html.Table([tete, corps], className="tableau"), className="tableau-cadre")


def tete(surtitre, titre, texte=None, *notes):
    return html.Header([html.P(surtitre, className="surtitre"), html.H1(titre)] +
                       ([html.P(texte, className="question")] if texte else []) + list(notes), className="page-tete")


def note(*enfants, avertissement=False):
    return html.Div(list(enfants), className="note avertissement" if avertissement else "note")


def section(titre, *enfants):
    return html.Section([html.H2(titre)] + list(enfants), className="section")


def absent(message):
    return html.Div(message, className="absent")


def message(texte, erreur=False):
    return html.Div(texte, className="message erreur" if erreur else "message")


def fiche(paires):
    return html.Dl([html.Div([html.Dt(a), html.Dd(b)]) for a, b in paires], className="fiche")


def graphe(id_, fig=None, hauteur=440, legende=None):
    return html.Figure(className="figure", children=[
        dcc.Graph(id=id_, figure=fig if fig is not None else {}, config=CONFIG, style={"height": f"{hauteur}px"}),
        html.Figcaption(legende) if legende else None])


def habiller(fig):
    fig.update_layout(autosize=True, separators=", ", font=dict(family=POLICE, color=ENCRE, size=13),
                      paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=60, r=20, t=36, b=50),
                      hoverlabel=dict(bgcolor="white", bordercolor=ENCRE_2, font=dict(family=POLICE, color=ENCRE)),
                      legend=dict(orientation="h", x=0, y=1.0, yanchor="bottom", bgcolor="rgba(0,0,0,0)",
                                  font=dict(color=ENCRE_2)))
    fig.update_xaxes(gridcolor=GRILLE, zeroline=False, showline=True, linecolor=ENCRE_2, ticks="outside", automargin=True)
    fig.update_yaxes(gridcolor=GRILLE, zeroline=False, showline=True, linecolor=ENCRE_2, ticks="outside", automargin=True)
    return fig


COULEUR_ETAT = {"rouge": "#c8352f", "orange": "#e2711d", "ambre": "#c99400", "vert": "#2f8f5b"}


def badge(etat):
    """Étiquette colorée de l'état d'un marché (service.ETATS), avec son explication au survol."""
    import service as SV
    libelle, couleur, *_, aide = SV.ETATS[etat]
    return html.Span(libelle, className=f"badge badge-{couleur}", title=aide)


def tuile(titre, valeur, sous=None, couleur=None):
    return html.Div([html.Div(titre, className="tuile-titre"), html.Div(valeur, className="tuile-valeur"),
                     html.Div(sous, className="tuile-sous") if sous else None],
                    className=f"tuile tuile-{couleur}" if couleur else "tuile")


def tuiles(*enfants):
    return html.Div(list(enfants), className="tuiles")


def chargement(enfant):
    return dcc.Loading(enfant, type="dot", color="#1F7A4D", delay_show=250)


def aide(titre, *enfants):
    """Bloc dépliable « comment lire »."""
    return html.Details([html.Summary(titre)] + list(enfants), className="aide")


def fond_cameroun(fig, lon=(8.3, 16.4), lat=(1.6, 13.2)):
    """Cameroun en blanc bordé, voisins grisés (Mercator), contours servis en local."""
    fig.add_choropleth(locations=["CMR"], z=[1], colorscale=[[0, "white"], [1, "white"]], showscale=False,
                       marker_line_color=ENCRE_2, marker_line_width=1.2, hoverinfo="skip", showlegend=False)
    fig.update_geos(projection_type="mercator", lonaxis_range=list(lon), lataxis_range=list(lat), resolution=50,
                    showframe=False, showcountries=True, countrycolor="#a9a8a3", showland=True, landcolor="#ecebe6",
                    showocean=True, oceancolor="#e9f0f7", showlakes=True, lakecolor="#e9f0f7", showcoastlines=True,
                    coastlinecolor="#a9a8a3")
    return fig
