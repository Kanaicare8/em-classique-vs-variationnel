"""Accueil : bulletin du mois (marchés en alerte, par région, marchés à surveiller), export CSV et PDF."""

from urllib.parse import urlencode

import dash
from dash import Input, Output, callback, dcc, html

import acces as AC
import composants as CO
import service as SV
from bulletin_calc import MODES, bulletin

dash.register_page(__name__, path="/", name="Bulletin", order=1, title="Bulletin, prix alimentaires du Cameroun")


def options_versions():
    return [{"label": f["libelle"], "value": f["version"]} for f in SV.liste_versions()]


def layout(**_):
    if not AC.peut("consulter"):
        return CO.absent("Accès refusé.")
    st = SV.etat()
    mois = SV.mois_disponibles(st)
    return html.Div([
        CO.tete("Bulletin", "Bulletin mensuel des marchés",
                "Pour un mois : les marchés dont les prix relèvent du régime de tension (alerte), ceux dont la lecture "
                "est incertaine (l'intervalle à 90 % contient le seuil de 0,5), et la situation par région.",
                CO.note(f"Données : {st['extrait']['origine']}, jusqu'à {SV.mois_texte(max(mois))} ; relevés saisis "
                        "dans l'outil inclus une fois validés.")),
        html.Div([
            html.Label(["Mois", dcc.Dropdown([{"label": SV.mois_texte(t), "value": t} for t in mois], mois[0],
                                             id="b-mois", clearable=False)], className="champ"),
            html.Label(["Lecture", dcc.RadioItems([{"label": v[0].upper() + v[1:], "value": k} for k, v in MODES.items()],
                                                  "accord", id="b-mode", inline=True, className="radios")],
                       className="champ"),
            html.Label(["Modèle", dcc.Dropdown(options_versions(), SV.REFERENCE, id="b-version", clearable=False)],
                       className="champ large"),
            html.Div([html.A("Bulletin PDF", id="b-pdf", className="bouton", href="#"),
                      html.A("Tableau CSV", id="b-csv", className="bouton secondaire", href="#")], className="boutons"),
        ], className="controles collant"),
        html.Div(id="b-contenu"),
    ])


@callback(Output("b-contenu", "children"), Output("b-pdf", "href"), Output("b-csv", "href"),
          Input("b-mois", "value"), Input("b-mode", "value"), Input("b-version", "value"))
def _afficher(t, mode, version):
    st = SV.etat(version)
    if mode not in st["proba"] and mode != "accord":
        mode = "accord"
    b = bulletin(st, t, mode)
    q = urlencode({"mois": SV.mois_texte(t), "mode": mode, "version": version})
    if not b["toutes"]:
        return CO.absent("Aucun marché observé ce mois-là."), f"/export/bulletin.pdf?{q}", f"/export/bulletin.csv?{q}"
    noms = st["modele"].fiche["noms"]
    resume = html.Div([html.P(b["phrase"], className="chapeau"),
                       CO.fiche([("Marchés observés", str(len(b["toutes"]))), ("En alerte", str(len(b["alerte"]))),
                                 ("Lecture incertaine", str(len(b["incertains"]))), ("Période", b["periode"])])])
    cols_r = ["Région", "Marchés observés", "En alerte", "Incertains", "Part d'alerte habituelle"]
    regions = CO.section("Par région", CO.tableau(cols_r, [
        {"Région": r["region"], "Marchés observés": r["n"], "En alerte": r["alerte"], "Incertains": r["incertains"],
         "Part d'alerte habituelle": r["habituelle"]} for r in b["regions"]], numeriques=cols_r[1:]),
        html.P("Part habituelle : part des observations de la région en alerte sur tous les mois, pour situer le mois.",
               className="question"))
    cols = ["Marché", "Région", "P(tension)", "IC 90 %", "Lecture"] + [f"{n} (XAF/kg)" for n in noms] + ["Écart du maïs"]
    if b["a_voir"]:
        lignes = [{"Marché": [l["marche"]] + ([" ", html.Span("saisi", className="etiquette")] if l["saisie"] else []),
                   "Région": l["region"], "P(tension)": l["p_txt"], "IC 90 %": l["ic_txt"], "Lecture": l["lecture"],
                   **{f"{n} (XAF/kg)": v for n, v in zip(noms, l["prix_txt"])}, "Écart du maïs": l["ecart_mais"],
                   "_classe": l["classe"]} for l in b["a_voir"]]
        a_voir = CO.tableau(cols, lignes, numeriques=cols[2:4] + cols[5:])
    else:
        a_voir = CO.absent("Aucun marché en alerte ni de lecture incertaine ce mois-là.")
    note = ("Lecture « les deux bras en accord » : P et l'intervalle affichés sont les plus prudents des deux bras "
            "(minimum de P, enveloppe des intervalles). " if mode == "accord" else "")
    marches = CO.section("Marchés à surveiller", a_voir, html.P(
        note + "Écart du maïs : prix du mois rapporté à son niveau des douze mois précédents. « saisi » : au moins un "
        "prix vient d'un relevé saisi dans l'outil.", className="question"))
    return [resume, regions, marches], f"/export/bulletin.pdf?{q}", f"/export/bulletin.csv?{q}"
