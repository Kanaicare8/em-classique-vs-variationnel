"""Page 5 : évaluer un nouveau relevé de prix (marché, mois, trois prix) avec les modèles ajustés du mémoire."""

import dash
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

import composants as CO
import figures as FG
import service as SV

dash.register_page(__name__, path="/releve", name="Nouveau relevé", order=5,
                   title="Nouveau relevé, prix alimentaires du Cameroun")


def _marches():
    idx = [i for i in range(len(SV.MARCHES)) if SV.N_APP[i] + SV.N_TEST[i] > 0]
    return sorted(idx, key=lambda i: (SV.REGIONS_ORDRE.index(SV.REGIONS[i]), SV.MARCHES[i]))


def _options_mois():
    """Tous les mois des données, puis six mois au-delà du dernier : un relevé futur se saisit comme un relevé passé."""
    fin = SV.MOIS_TOUS[-1]
    return [{"label": SV.DO.mois_texte(t), "value": t} for t in range(fin + 6, SV.MOIS_TOUS[0] - 1, -1)]


def _dernier_prix(marche, denree, t):
    s = SV.PRIX_NETS[denree].get(SV.MARCHES[marche], {})
    avant = [u for u in s if u < t]
    return round(s[max(avant)]) if avant else None


def layout(**_):
    tir = SV.tirages()
    tete = html.Header([
        html.P("Nouveau relevé", className="surtitre"), html.H1("Évaluer un relevé de prix"),
        html.P("Saisir, pour un marché et un mois, le prix de détail des trois denrées (XAF/kg). L'application calcule "
               "l'écart de chaque prix à son niveau des douze mois précédents, comme dans le mémoire, puis la probabilité "
               "du régime de tension selon EM-BIC et VB-emp, avec un intervalle à 90 %.", className="question"),
        CO.note("Les modèles sont ceux du mémoire, ajustés sur avril 2021 à décembre 2023 ; ils ne sont pas réestimés "
                "avec le relevé saisi. Le régime de tension est une composante du mélange, sans vérité terrain : la "
                "lecture est une aide, pas une décision.")], className="page-tete")
    if tir is None:
        return html.Div([tete, CO.absent(["Tirages non calculés. Dans PowerShell, à la racine du projet : ",
                                          html.Code("python app/precalcul.py")])])
    defaut = SV.marche_par_defaut()
    return html.Div([
        tete,
        html.Div([
            html.Label(["Marché", dcc.Dropdown([{"label": f"{SV.MARCHES[i]}, {SV.REGIONS[i]}", "value": i}
                                                for i in _marches()], defaut, id="r-marche", clearable=False)],
                       className="champ large"),
            html.Label(["Mois du relevé", dcc.Dropdown(_options_mois(), SV.MOIS_TOUS[-1] + 1, id="r-mois",
                                                       clearable=False)], className="champ"),
        ], className="controles"),
        html.Div([html.Label([f"{nom} (XAF/kg)", dcc.Input(id=f"r-prix-{j}", type="number", min=1, step=1,
                                                           debounce=True, className="saisie")], className="champ")
                  for j, nom in enumerate(SV.NOMS)], className="controles"),
        CO.section("5.1", "Écart au niveau des douze mois", html.Div(id="r-ecarts")),
        CO.section("5.2", "Probabilité du régime de tension", html.Div(id="r-proba"),
                   CO.graphe("r-historique", None, 420, numero="5.1",
                             legende="P(tension) du marché selon les deux bras (relevés du mémoire), et le relevé saisi "
                                     "(losange, avec son intervalle à 90 %).")),
    ])


@callback(*[Output(f"r-prix-{j}", "value") for j in range(3)], Input("r-marche", "value"), Input("r-mois", "value"))
def _preremplir(m, t):
    return tuple(_dernier_prix(m, c, t) for c in SV.PANIER)


@callback(Output("r-ecarts", "children"), Output("r-proba", "children"), Output("r-historique", "figure"),
          Input("r-marche", "value"), Input("r-mois", "value"), *[Input(f"r-prix-{j}", "value") for j in range(3)])
def _evaluer(m, t, *prix):
    saisis = {c: (float(p) if p else None) for c, p in zip(SV.PANIER, prix)}
    ecarts, niveaux, res = SV.evaluer_releve(m, t, saisis)
    lignes = []
    for nom, c, e in zip(SV.NOMS, SV.PANIER, ecarts):
        niv, n = niveaux[c]
        lignes.append({"Denrée": nom, "Prix saisi (XAF/kg)": CO.nombre(saisis[c], 0) if saisis[c] else "–",
                       "Niveau des 12 mois (XAF/kg)": CO.nombre(niv, 0) if niv else f"– ({n} relevés, {SV.RELEVES_MIN} requis)",
                       "Écart": CO.ecart_pourcent(e) if e is not None else "–",
                       "_classe": "ligne-incertaine" if e is None else None})
    cols = ["Denrée", "Prix saisi (XAF/kg)", "Niveau des 12 mois (XAF/kg)", "Écart"]
    tab = html.Div([CO.tableau(cols, lignes, numeriques=cols[1:]),
                    html.P("Niveau : moyenne géométrique des relevés des douze mois précédents (pics isolés écartés) ; "
                           "écart : variation du prix saisi par rapport à ce niveau.", className="question")])
    fig = _historique(m, t, res)
    if res is None:
        return tab, CO.absent("Écart non calculable pour au moins une denrée : prix manquant ou moins de "
                              f"{SV.RELEVES_MIN} relevés dans les douze mois précédents."), fig
    lignes_p = []
    for nom, r in res.items():
        p, bas, haut = r["p"], r["bas"], r["haut"]
        lecture = ("alerte" if bas > 0.5 else "alerte incertaine") if p > 0.5 else \
                  ("calme incertain" if haut >= 0.5 else "calme")
        lignes_p.append({"Bras": nom, "P(tension)": CO.nombre(p, 2),
                         "IC 90 %": f"[{CO.nombre(bas, 2)} ; {CO.nombre(haut, 2)}]", "Lecture": lecture,
                         "Tirages": str(r["n_tirages"]),
                         "_classe": "ligne-tension" if lecture == "alerte" else
                                    ("ligne-incertaine" if "incertain" in lecture else None)})
    cols_p = ["Bras", "P(tension)", "IC 90 %", "Lecture", "Tirages"]
    return tab, html.Div([CO.tableau(cols_p, lignes_p, numeriques=cols_p[1:3] + cols_p[4:]),
                          html.P("EM-BIC : probabilité du modèle ajusté, intervalle par bootstrap à démarrage chaud ; "
                                 "VB-emp : moyenne et intervalle sous la loi variationnelle q.", className="question")]), fig


def _historique(m, t, res):
    a = SV.precalcul()["alerte"]
    obs = SV.observations(m)
    x = [SV.mois_date(SV.MOIS[i]) for i in obs]
    fig = go.Figure()
    for nom in SV.BRAS:
        if nom not in a:
            continue
        fig.add_scatter(x=x, y=[float(a[nom]["proba"][i]) for i in obs], mode="lines+markers", name=nom,
                        line=dict(color=FG.COULEUR[nom], width=2), marker=dict(size=5),
                        hovertemplate="%{x|%Y-%m}<br>P %{y:.2f}<extra>" + nom + "</extra>")
        if res and nom in res:
            r = res[nom]
            fig.add_scatter(x=[SV.mois_date(t)], y=[r["p"]], mode="markers", name=f"relevé saisi, {nom}",
                            marker=dict(symbol="diamond", size=13, color=FG.COULEUR[nom], line=dict(color="white", width=1)),
                            error_y=dict(type="data", symmetric=False, array=[r["haut"] - r["p"]],
                                         arrayminus=[r["p"] - r["bas"]], color=FG.COULEUR[nom], thickness=1.5),
                            hovertemplate="relevé saisi<br>P %{y:.2f}<extra>" + nom + "</extra>")
    fig.add_hline(y=0.5, line=dict(color=FG.ENCRE_2, dash="dash", width=1))
    CO.habiller(fig)
    fig.update_yaxes(title_text="P(tension)", range=[0, 1])
    return fig
