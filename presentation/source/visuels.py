"""
Visuels de la présentation d'Icare (écran, gros caractères, palette verte).

Figures RÉELLES : re-tracées depuis les résultats déjà calculés (emvb.figures lit le magasin, aucun ajustement relancé),
avec une autre palette et des polices lisibles à distance. Illustrations CONCEPTUELLES (un point contre une loi, les
deux effets de la KL inverse) : calculées en forme close, étiquetées « illustration », elles ne portent aucun résultat.

Usage : python visuels.py [concept|reel]   (écrit visuels/*.png ; les figures réelles demandent le magasin de résultats)
"""
import math
import os
import sys
from pathlib import Path

ICARE = Path(__file__).resolve().parents[2]          # racine du dépôt (presentation/source/ -> racine)
sys.path.insert(0, str(ICARE))
os.environ.setdefault("PYTHONUTF8", "1")

import plotly.graph_objects as go  # noqa: E402
from plotly.subplots import make_subplots  # noqa: E402

from emvb import figures as FG  # noqa: E402

SORTIE = Path(__file__).resolve().parent / "visuels"
SORTIE.mkdir(exist_ok=True)

FONCE, VERT, CLAIR, AMBRE, ROUGE, GRIS, PALE = "#14432A", "#1F7A4D", "#2E9E64", "#E0A030", "#B03A2E", "#6F747A", "#DCE6DF"
POLICE = "Segoe UI, Arial, sans-serif"

# palette du mémoire remplacée par la palette verte (lue à chaque appel par emvb.figures)
FG.SERIES = [FONCE, CLAIR, AMBRE, ROUGE, "#7A9E8A", VERT, GRIS, "#C9D6CD"]
FG.COULEUR.update({"EM": FONCE, "VB": CLAIR, "EM-K": FONCE, "EM-BIC": FONCE, "VB-emp": CLAIR})
FG.ENCRE, FG.ENCRE_2, FG.GRILLE, FG.FOND = FONCE, GRIS, "#E9EEEA", "white"
FG.SEQUENTIEL = [[0.0, "#EEF5F0"], [0.5, CLAIR], [1.0, FONCE]]


def ecrire(fig, nom, largeur, hauteur, essais=4):
    chemin = str(SORTIE / f"{nom}.png")
    for i in range(1, essais + 1):
        try:
            fig.write_image(chemin, width=largeur, height=hauteur, scale=2)
            print("écrit", nom)
            return
        except Exception as ex:          # le navigateur sans interface échoue parfois à se fermer
            if i == essais:
                raise
            print("relance", nom, type(ex).__name__)


def sobre(fig, taille=22):
    fig.update_layout(font=dict(family=POLICE, size=taille, color=FONCE), paper_bgcolor="white", plot_bgcolor="white",
                      showlegend=False, margin=dict(l=70, r=30, t=60, b=70), title=None)
    fig.update_xaxes(gridcolor="#E9EEEA", linecolor=GRIS, tickfont=dict(size=taille - 2), title_font=dict(size=taille))
    fig.update_yaxes(gridcolor="#E9EEEA", linecolor=GRIS, tickfont=dict(size=taille - 2), title_font=dict(size=taille))
    return fig


# ------------------------------------------------------------------------------ figures réelles
def reelles():
    f = FG.FIGURES["fig03"](False)                                   # jeu de référence : trois groupes
    sobre(f, 24)
    f.update_traces(marker=dict(size=11, opacity=0.9, line=dict(color="white", width=1.5)))
    f.update_xaxes(title_text="", showticklabels=False, showgrid=False)
    f.update_yaxes(title_text="", showticklabels=False, showgrid=False)
    ecrire(f, "groupes", 1000, 860)

    f = FG.FIGURES["fig04"](False)                                   # EM contre VB, mêmes données, K = Kmax
    sobre(f, 26)
    for a in f.layout.annotations:
        if a.text.startswith("EM, K"):
            a.update(text="<b>EM classique</b>", font=dict(size=30, color=FONCE))
        elif a.text.startswith("VB"):
            a.update(text="<b>EM variationnel</b>", font=dict(size=30, color=VERT))
        elif a.text.startswith("π="):
            a.update(text="", showarrow=False)
    f.update_xaxes(title_text="", showticklabels=False, showgrid=False)
    f.update_yaxes(title_text="", showticklabels=False, showgrid=False)
    f.update_layout(margin=dict(l=20, r=20, t=90, b=20))
    ecrire(f, "ellipses", 1800, 760)

    f = FG.FIGURES["fig05"](False)                                   # poids : l'EM garde tout, le VB élague
    sobre(f, 34)
    f.update_traces(textfont=dict(size=32, color=FONCE), cliponaxis=False)
    f.update_layout(showlegend=True, legend=dict(orientation="h", x=0.5, xanchor="center", y=1.08, font=dict(size=36)),
                    margin=dict(l=110, r=30, t=120, b=110))
    f.update_xaxes(title_text="composantes, par poids décroissant")
    f.update_yaxes(title_text="poids", range=[0, 0.4])
    ecrire(f, "poids", 1500, 760)

    f = FG.FIGURES["fig06"](False)                                   # nombre de composantes selon le prior (S8)
    sobre(f, 34)
    f.update_layout(showlegend=True, legend=dict(orientation="h", x=0.5, xanchor="center", y=1.1, font=dict(size=34)),
                    margin=dict(l=110, r=40, t=130, b=130))
    f.update_xaxes(title_text="concentration du prior de Dirichlet (échelle log)")
    f.update_yaxes(title_text="composantes retenues")
    f.layout.annotations = [a for a in f.layout.annotations if "groupes simulés" not in (a.text or "")] + [
        dict(x=0, xref="paper", y=3, yref="y", text="3 groupes simulés", showarrow=False, xanchor="left", yanchor="bottom",
             font=dict(size=30, color=GRIS))]
    ecrire(f, "priors", 1500, 760)

    f = FG.FIGURES["prix_carte_alerte"](False)                       # carte d'alerte, deux mois documentés
    f.update_layout(paper_bgcolor="white", font=dict(family=POLICE, size=30, color=FONCE), margin=dict(l=10, r=10, t=130, b=10))
    for a in f.layout.annotations:
        a.update(font=dict(size=36, color=FONCE))
    for t in f.data:
        if "text" in (getattr(t, "mode", "") or ""):
            t.update(textfont=dict(size=26, color=FONCE))
    ecrire(f, "carte", 2000, 760)


# ------------------------------------------------------------------------------ illustrations conceptuelles
def gauss(x, m, s):
    return math.exp(-0.5 * ((x - m) / s) ** 2) / (s * math.sqrt(2 * math.pi))


def point_et_loi():
    xs = [i / 40 for i in range(-160, 161)]
    f = make_subplots(rows=1, cols=2, horizontal_spacing=0.12,
                      subplot_titles=("<b>EM classique</b> : un point", "<b>EM variationnel</b> : une loi"))
    f.add_scatter(x=[0, 0], y=[0, 1.0], mode="lines", line=dict(color=FONCE, width=8), row=1, col=1)
    f.add_scatter(x=[0], y=[1.0], mode="markers", marker=dict(size=34, color=FONCE), row=1, col=1)
    f.add_scatter(x=xs, y=[gauss(x, 0, 0.9) / gauss(0, 0, 0.9) for x in xs], mode="lines", fill="tozeroy",
                  line=dict(color=VERT, width=5), fillcolor="rgba(46,158,100,0.35)", row=1, col=2)
    f.update_xaxes(visible=False, range=[-4, 4])
    f.update_yaxes(visible=False, range=[0, 1.25])
    sobre(f, 26)
    f.update_annotations(font=dict(size=36, color=FONCE))
    f.add_annotation(text="θ", x=0, y=1.0, xref="x", yref="y", showarrow=False, xshift=44, font=dict(size=40, color=FONCE), row=1, col=1)
    f.add_annotation(text="q(θ)", x=1.4, y=0.75, xref="x2", yref="y2", showarrow=False, font=dict(size=36, color=VERT))
    f.update_layout(margin=dict(l=20, r=20, t=90, b=20))
    ecrire(f, "point_loi", 1700, 620)


def deux_effets():
    xs = [i / 40 for i in range(-200, 201)]
    f = make_subplots(rows=1, cols=2, horizontal_spacing=0.1,
                      subplot_titles=("<b>Un seul mode</b>", "<b>Une variance trop petite</b>"))
    p1 = [0.5 * gauss(x, -2, 0.7) + 0.5 * gauss(x, 2, 0.7) for x in xs]
    q1 = [0.5 * gauss(x, 2, 0.7) for x in xs]
    p2 = [gauss(x, 0, 1.0) for x in xs]
    q2 = [gauss(x, 0, 0.55) for x in xs]
    for col, (p, q) in enumerate(((p1, q1), (p2, q2)), start=1):
        f.add_scatter(x=xs, y=p, mode="lines", fill="tozeroy", fillcolor="rgba(111,116,122,0.22)",
                      line=dict(color=GRIS, width=4), row=1, col=col)
        f.add_scatter(x=xs, y=q, mode="lines", line=dict(color=VERT, width=7), row=1, col=col)
    f.update_xaxes(visible=False)
    f.update_yaxes(visible=False, range=[0, 0.78])
    sobre(f, 26)
    f.update_annotations(font=dict(size=38, color=FONCE))
    f.add_annotation(text="loi exacte", x=-2, y=0.42, xref="x", yref="y", showarrow=False, font=dict(size=32, color=GRIS))
    f.add_annotation(text="approximation", x=2.6, y=0.5, xref="x", yref="y", showarrow=False, font=dict(size=32, color=VERT))
    f.add_annotation(text="loi exacte", x=-1.9, y=0.28, xref="x2", yref="y2", showarrow=False, font=dict(size=32, color=GRIS))
    f.add_annotation(text="approximation", x=0.95, y=0.40, xref="x2", yref="y2", showarrow=False, xanchor="left", font=dict(size=32, color=VERT))
    f.update_layout(margin=dict(l=20, r=20, t=90, b=20))
    ecrire(f, "deux_effets", 1700, 640)


if __name__ == "__main__":
    cible = sys.argv[1] if len(sys.argv) > 1 else "tout"
    if cible in ("tout", "concept"):
        point_et_loi()
        deux_effets()
    if cible in ("tout", "reel"):
        reelles()
