"""Page 4 : bulletin mensuel des marchés, sous forme utilisable (unité « alerte », aucun calcul nouveau)."""

import csv
import io

import dash
from dash import Input, Output, State, callback, dcc, html

import composants as CO
import service as SV

dash.register_page(__name__, path="/bulletin", name="Bulletin du mois", order=4,
                   title="Bulletin du mois, prix alimentaires du Cameroun")

MODES = {"EM-BIC": "EM-BIC", "VB-emp": "VB-emp", "accord": "Les deux en accord"}


def _options_mois():
    return [{"label": f"{SV.DO.mois_texte(t)} ({'apprentissage' if t <= SV.FIN_APP else 'test'})", "value": t}
            for t in reversed(SV.MOIS_TOUS)]


def _etat(p, bas, haut):
    """Lecture d'une probabilité et de son intervalle à 90 %, comme la page Alerte."""
    if p > 0.5:
        return ("alerte", "ligne-tension") if bas > 0.5 else ("alerte incertaine", "ligne-incertaine")
    return ("calme incertain", "ligne-incertaine") if haut >= 0.5 else ("calme", None)


def _evaluation(a, mode, i):
    """(p, bas, haut, lecture, classe) d'une observation pour le mode choisi ; « accord » : alerte si les deux bras le sont."""
    if mode != "accord":
        p, ic = a[mode]["proba"], a[mode]["ic"]
        lecture, classe = _etat(float(p[i]), float(ic[0, i]), float(ic[1, i]))
        return float(p[i]), float(ic[0, i]), float(ic[1, i]), lecture, classe
    em, vb = (_evaluation(a, b, i) for b in SV.BRAS)
    if em[0] > 0.5 and vb[0] > 0.5:
        lecture, classe = ("alerte (deux bras)", "ligne-tension")
    elif (em[0] > 0.5) != (vb[0] > 0.5):
        lecture, classe = ("désaccord des bras", "ligne-incertaine")
    else:
        lecture, classe = ("calme (deux bras)", None)
    return min(em[0], vb[0]), min(em[1], vb[1]), max(em[2], vb[2]), lecture, classe


def _prix(marche, t):
    """Prix de détail de chaque denrée ce mois-là (XAF/kg, relevés nettoyés comme dans le mémoire)."""
    return {nom: SV.PRIX_NETS[c].get(SV.MARCHES[marche], {}).get(t) for nom, c in zip(SV.NOMS, SV.PANIER)}


def _part_habituelle(a, mode, region):
    obs = [i for i, m in enumerate(SV.MARCHE) if SV.REGIONS[m] == region]
    if not obs:
        return None
    return sum(_evaluation(a, mode, i)[3].startswith("alerte") for i in obs) / len(obs)


def layout(**_):
    pre = SV.precalcul()
    tete = html.Header([
        html.P("Bulletin", className="surtitre"), html.H1("Bulletin mensuel des marchés"),
        html.P("Pour un mois choisi : les marchés observés, ceux que le régime de tension met en alerte, et ceux dont "
               "l'intervalle à 90 % contient le seuil de 0,5 (lecture incertaine). Le bulletin se télécharge en CSV.",
               className="question"),
        CO.note("Outil de démonstration du mémoire : les régimes sont des composantes du mélange, sans vérité terrain. "
                "Il ne constitue pas un dispositif d'alerte opérationnel et ne doit pas servir à des décisions "
                "d'assistance sans validation par les organismes compétents."),
        CO.bandeau_precalcul(pre)], className="page-tete")
    if pre is None:
        return html.Div([tete])
    return html.Div([
        tete,
        html.Div([
            html.Label(["Lecture", dcc.RadioItems([{"label": v, "value": k} for k, v in MODES.items()], "accord",
                                                  id="b-mode", inline=True, className="radios")], className="champ"),
            html.Label(["Mois", dcc.Dropdown(_options_mois(), SV.MOIS_TOUS[-1], id="b-mois", clearable=False)],
                       className="champ large"),
            html.Div([html.Button("Télécharger le bulletin (CSV)", id="b-export", className="bouton-agrandir"),
                      dcc.Download(id="b-fichier")], className="champ"),
        ], className="controles collant"),
        html.Div(id="b-resume"),
        CO.section("4.1", "Par région", html.Div(id="b-regions")),
        CO.section("4.2", "Marchés à surveiller", html.Div(id="b-marches")),
    ])


@callback(Output("b-resume", "children"), Output("b-regions", "children"), Output("b-marches", "children"),
          Input("b-mode", "value"), Input("b-mois", "value"))
def _bulletin(mode, t):
    a = SV.precalcul()["alerte"]
    obs = [i for i, m in enumerate(SV.MOIS) if m == t]
    if not obs:
        return CO.absent("Aucun marché observé ce mois-là."), None, None
    ev = {i: _evaluation(a, mode, i) for i in obs}
    alerte = [i for i in obs if ev[i][3].startswith("alerte")]
    incertains = [i for i in obs if ev[i][4] == "ligne-incertaine" and i not in alerte]
    lecture = (f"En {SV.DO.mois_texte(t)}, {len(alerte)} des {len(obs)} marchés observés sont en alerte selon "
               f"{MODES[mode] if mode != 'accord' else 'les deux bras à la fois'}, et {len(incertains)} ont une lecture "
               f"incertaine.")
    resume = html.Div([
        html.P(lecture, className="chapeau"),
        html.Dl([html.Div([html.Dt(t_), html.Dd(v)]) for t_, v in
                 (("Marchés observés", str(len(obs))), ("En alerte", str(len(alerte))),
                  ("Lecture incertaine", str(len(incertains))),
                  ("Période", "apprentissage" if t <= SV.FIN_APP else "test"))], className="fiche")])

    lignes_r = []
    for reg in SV.REGIONS_ORDRE:
        o = [i for i in obs if SV.REGIONS[SV.MARCHE[i]] == reg]
        if not o:
            continue
        lignes_r.append({"Région": reg, "Marchés observés": str(len(o)),
                         "En alerte": str(sum(i in alerte for i in o)),
                         "Incertains": str(sum(i in incertains for i in o)),
                         "Part d'alerte habituelle de la région": CO.pourcent(_part_habituelle(a, mode, reg), 1)})
    cols_r = ["Région", "Marchés observés", "En alerte", "Incertains", "Part d'alerte habituelle de la région"]
    regions = html.Div([CO.tableau(cols_r, lignes_r, numeriques=cols_r[1:]),
                        html.P("Part habituelle : observations de la région en alerte sur tous les mois, pour situer "
                               "le mois choisi.", className="question")])

    a_voir = sorted(alerte + incertains, key=lambda i: -ev[i][0])
    if not a_voir:
        return resume, regions, CO.absent("Aucun marché en alerte ni de lecture incertaine ce mois-là.")
    lignes = []
    for i in a_voir:
        m = SV.MARCHE[i]
        p, bas, haut, lecture_i, classe = ev[i]
        prix = _prix(m, t)
        lignes.append({"Marché": SV.MARCHES[m], "Région": SV.REGIONS[m], "P(tension)": CO.nombre(p, 2),
                       "IC 90 %": f"[{CO.nombre(bas, 2)} ; {CO.nombre(haut, 2)}]", "Lecture": lecture_i,
                       **{f"{n} (XAF/kg)": CO.nombre(prix[n], 0) if prix[n] else "–" for n in SV.NOMS},
                       "Écart du maïs à 12 mois": CO.ecart_pourcent(float(SV.X[i, 0])), "_classe": classe})
    cols = ["Marché", "Région", "P(tension)", "IC 90 %", "Lecture"] + [f"{n} (XAF/kg)" for n in SV.NOMS] + \
           ["Écart du maïs à 12 mois"]
    note_accord = (" En lecture « les deux en accord », P et l'intervalle affichés sont les plus prudents des deux bras "
                   "(minimum de P, enveloppe des intervalles).") if mode == "accord" else ""
    return resume, regions, html.Div([CO.tableau(cols, lignes, numeriques=cols[2:4] + cols[5:]),
                                      html.P("Écart du maïs : prix du mois rapporté à son niveau des douze mois "
                                             "précédents." + note_accord, className="question")])


@callback(Output("b-fichier", "data"), Input("b-export", "n_clicks"), State("b-mode", "value"), State("b-mois", "value"),
          prevent_initial_call=True)
def _export(_, mode, t):
    a = SV.precalcul()["alerte"]
    f = io.StringIO()
    w = csv.writer(f, delimiter=";")
    w.writerow(["mois", "marche", "region", "lecture_choisie"] +
               [f"{b}_{c}" for b in SV.BRAS for c in ("p_tension", "ic90_bas", "ic90_haut")] +
               [f"prix_{n}_xaf_kg" for n in SV.NOMS] + [f"ecart_{n}" for n in SV.NOMS])
    for i in sorted((i for i, m in enumerate(SV.MOIS) if m == t), key=lambda i: SV.MARCHES[SV.MARCHE[i]]):
        m = SV.MARCHE[i]
        prix = _prix(m, t)
        w.writerow([SV.DO.mois_texte(t), SV.MARCHES[m], SV.REGIONS[m], _evaluation(a, mode, i)[3]] +
                   [f"{v:.4f}" for b in SV.BRAS for v in (float(a[b]["proba"][i]), float(a[b]["ic"][0, i]),
                                                           float(a[b]["ic"][1, i]))] +
                   [f"{prix[n]:.0f}" if prix[n] else "" for n in SV.NOMS] + [f"{float(SV.X[i, j]):.4f}" for j in range(3)])
    return dcc.send_string(f.getvalue(), f"bulletin_{SV.DO.mois_texte(t)}_{mode}.csv")
