"""
Composants communs : habillage des figures Plotly (palette de figures.py), barre d'outils complète, tableaux, notes.
"""

from __future__ import annotations

import math

from dash import dcc, html

from emvb import figures as FG

POLICE = "'Source Sans 3', 'Segoe UI', Arial, sans-serif"
ENCRE = "#14432A"                 # vert foncé d'Icare pour le texte des graphiques

# Barre d'outils Plotly complète : zoom, déplacement, sélection, lasso, dessin, survol comparé, export haute définition
CONFIG = {
    "displaylogo": False,
    "displayModeBar": True,
    "scrollZoom": True,
    "responsive": True,
    "modeBarButtonsToAdd": ["drawline", "drawopenpath", "drawrect", "drawcircle", "eraseshape",
                            "hoverclosest", "hovercompare", "toggleSpikelines", "v1hovermode"],
    "toImageButtonOptions": {"format": "png", "scale": 3},
    "topojsonURL": "/assets/topojson/",   # contours des pays servis en local : les cartes marchent sans Internet
}


def fond_cameroun(fig, lon=(8.3, 16.4), lat=(1.6, 13.2)):
    """Carte hors ligne, identique aux figures du mémoire : Cameroun en blanc bordé, voisins grisés (Mercator)."""
    FG._cameroun(fig)
    FG._geo(fig, list(lon), list(lat))
    return fig


def habiller(fig, legende=True):
    """Style du mémoire adapté à l'écran : taille fixée par le conteneur, virgule décimale, survol lisible."""
    fig.update_layout(width=None, height=None, autosize=True, showlegend=legende, separators=", ",
                      font=dict(family=POLICE, color=ENCRE, size=13), paper_bgcolor="white", plot_bgcolor="white",
                      margin=dict(l=64, r=24, t=36, b=56), dragmode="zoom",
                      hoverlabel=dict(bgcolor="white", bordercolor=FG.ENCRE_2, font=dict(family=POLICE, color=ENCRE)),
                      legend=dict(orientation="h", x=0, y=1.0, yanchor="bottom", bgcolor="rgba(0,0,0,0)",
                                  font=dict(color=FG.ENCRE_2)),
                      newshape=dict(line=dict(color=ENCRE, width=2)))
    if any(getattr(a, "yref", None) == "paper" and (a.y or 0) >= 0.99 for a in fig.layout.annotations):
        # titres de sous-graphes au bord haut : la légende passe au-dessus d'eux au lieu de les recouvrir
        fig.update_layout(margin=dict(t=88), legend=dict(y=1.09, yanchor="bottom"))
    fig.update_xaxes(gridcolor=FG.GRILLE, zeroline=False, showline=True, linecolor=FG.ENCRE_2, ticks="outside",
                     automargin=True)
    fig.update_yaxes(gridcolor=FG.GRILLE, zeroline=False, showline=True, linecolor=FG.ENCRE_2, ticks="outside",
                     automargin=True)
    return fig


def graphe(id_, fig=None, hauteur=460, legende=None, numero=None):
    """Figure numérotée avec sa légende ; le bouton « Agrandir » (assets/plein_ecran.js) l'ouvre en plein écran."""
    tete = [html.Span(f"Figure {numero}" if numero else "", className="figure-numero"),
            html.Button("Agrandir", className="bouton-agrandir", title="Plein écran (Échap pour revenir)")]
    return html.Figure(className="figure", children=[
        html.Div(tete, className="figure-tete"),
        dcc.Graph(id=id_, figure=fig if fig is not None else {}, config=CONFIG, style={"height": f"{hauteur}px"},
                  className="graphe"),
        html.Figcaption(legende) if legende else None])


def nombre(x, d=2, signe=False):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    if round(x, d) == 0:
        x = 0.0                                        # pas de « −0 » ni de « +0 » : un écart nul s'écrit 0
        signe = False
    s = f"{x:+.{d}f}" if signe else f"{x:.{d}f}"
    return s.replace(".", ",").replace("-", "−")


def pourcent(x, d=0, signe=False):
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else nombre(100 * x, d, signe) + " %"


def ecart_pourcent(e_log):
    """Écart du log-prix -> variation du prix en % (exp(e) - 1)."""
    return pourcent(math.expm1(e_log), 0, signe=True)


def tableau(colonnes, lignes, classe="", numeriques=()):
    """Tableau HTML sobre ; `numeriques` : colonnes alignées à droite en chiffres tabulaires."""
    tete = html.Thead(html.Tr([html.Th(c, className="num" if c in numeriques else None) for c in colonnes]))
    corps = html.Tbody([html.Tr([html.Td(l.get(c, ""), className="num" if c in numeriques else None) for c in colonnes],
                                className=l.get("_classe"))
                        for l in lignes])
    return html.Div(html.Table([tete, corps], className=f"tableau {classe}"), className="tableau-cadre")


def note(*enfants, classe="note"):
    return html.Div(list(enfants), className=classe)


def section(numero, titre, *enfants):
    return html.Section([html.H2([html.Span(numero, className="h-num"), titre])] + list(enfants), className="section")


def absent(message):
    return html.Div(message, className="absent")


def bandeau_precalcul(pre):
    """Statut des ajustements affichés : exploratoires (essai rapide ou paramètres provisoires) ou calibrés."""
    if pre is None:
        return absent(["Aucun ajustement précalculé. Dans PowerShell, à la racine du projet : ",
                       html.Code("python demo/precalcul.py"), " (ou ", html.Code("--rapide"),
                       " pour un essai de quelques minutes), puis rechargez la page."])
    r = pre["regimes"]
    if pre["rapide"] or r["provisoires"]:
        motif = []
        if pre["rapide"]:
            motif.append("essai rapide (3 relances, 50 réplicats bootstrap, 500 tirages)")
        if r["provisoires"]:
            motif.append(f"{len(r['provisoires'])} paramètres non calibrés ({', '.join(r['provisoires'])})")
        return note(html.Strong("Chiffres exploratoires. "),
                    f"Ajustements précalculés le {r['date']} : " + " ; ".join(motif) + ". Les résultats qui font foi "
                    "sont ceux de la page 4, lus dans le magasin du calcul confirmatoire.", classe="note avertissement")
    return note(f"Ajustements précalculés le {r['date']} avec les paramètres calibrés : mêmes unités et mêmes graines que "
                "le calcul confirmatoire.")
