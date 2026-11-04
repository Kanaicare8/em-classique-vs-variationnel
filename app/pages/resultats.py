"""Page 4 : résultats du mémoire, lus dans le magasin confirmatoire et les tableaux (lecture seule, aucun réglage)."""

import dash
from dash import Input, Output, callback, dcc, html

import composants as CO
import service as SV

dash.register_page(__name__, path="/resultats", name="Résultats du mémoire", order=4,
                   title="Résultats · Prix alimentaires du Cameroun")

FIGURES = [("prix_selection", "4.1", "Choix de K : BIC de l'EM selon K et poids des composantes du VB-emp à Kmax."),
           ("prix_decisions", "4.2", "Hypothèses HP1 à HP6 : différence moyenne A − B et intervalle bootstrap à 95 % ; "
                                     "bande grise : marge d'équivalence."),
           ("prix_alerte", "4.3", "Trois marchés les plus observés au test : écart du maïs et P(tension) avec bandes à 90 %."),
           ("prix_alerte_mois", "4.4", "Part mensuelle des marchés en alerte selon EM-BIC et VB-emp."),
           ("prix_marches", "4.5", "Marchés suivis, par région ; taille selon le nombre d'observations.")]


def _avancement():
    lignes = []
    for rapide, nom in ((False, "Calcul complet (resultats/magasin)"), (True, "Essai réduit (run.py --rapide)")):
        f, n = SV.avancement(rapide)
        lignes.append({"Magasin": nom, "Unités de l'étape prix": f"{f} / {n}", "État": "terminé" if f == n else "en attente"})
    nc = SV.non_calibres()
    return html.Div([CO.tableau(["Magasin", "Unités de l'étape prix", "État"], lignes,
                                numeriques=("Unités de l'étape prix",)),
                     html.P(("Paramètres non calibrés : " + ", ".join(nc) + ".") if nc else
                            "Tous les paramètres du registre sont calibrés.", className="chapeau")])


def layout(**_):
    return html.Div([
        html.Header([html.P("Page 4", className="surtitre"), html.H1("Résultats du mémoire"),
                     html.P("Cette page n'a aucun réglage : elle affiche ce que la chaîne de calcul a écrit dans le magasin "
                            "confirmatoire (python run.py prix, puis run.py --figures). Les hypothèses ont été déclarées "
                            "dans hypotheses.py avant toute exécution ; les décisions sont prises sur les p-valeurs "
                            "ajustées par la méthode de Holm.", className="question"),
                     _avancement()], className="page-tete"),
        html.Div([html.Label(["Source", dcc.RadioItems(
            [{"label": "calcul complet", "value": "complet"}, {"label": "essai réduit", "value": "rapide"}], "complet",
            id="res-source", inline=True, className="radios")], className="champ")], className="controles"),
        html.Div(id="res-contenu"),
    ])


def _decisions(rapide):
    dec = {l["id"]: l for l in (SV.table_officielle("prix_decisions", rapide) or [])}
    dm = {l["id"]: l for l in (SV.table_officielle("prix_diebold_mariano", rapide) or [])}
    lignes = []
    for h in SV.hypotheses_declarees():
        d = dec.get(h["id"]) or dm.get(h["id"])
        if d is None:            # HP4, HP5, HP6 sont décidées par sous-cas (HP4-N…, HP6-VB-pi…)
            sous = [v for k, v in dec.items() if k.startswith(h["id"] + "-")]
            d = sous[0] if len(sous) == 1 else None
            if len(sous) > 1:
                for s in sous:
                    lignes.append(_ligne({**h, "id": s["id"]}, s))
                continue
        lignes.append(_ligne(h, d))
    cols = ["Hypothèse", "Axe", "Énoncé", "Test", "Estimation", "IC", "p (Holm)", "Décision"]
    return CO.tableau(cols, lignes, classe="serre", numeriques=("Estimation", "IC", "p (Holm)"))


def _ligne(h, d):
    if d is None:
        return {"Hypothèse": h["id"], "Axe": h["axe"], "Énoncé": h["enonce"], "Test": h["test"],
                "Décision": "en attente du calcul", "_classe": "ligne-attente"}
    est = d.get("estimation", d.get("ecart_logscore_moyen"))
    ic = (f"[{CO.nombre(d['ic_bas'], 3)} ; {CO.nombre(d['ic_haut'], 3)}]"
          if isinstance(d.get("ic_bas"), float) and isinstance(d.get("ic_haut"), float) else "–")
    return {"Hypothèse": h["id"], "Axe": h["axe"], "Énoncé": h["enonce"], "Test": h["test"],
            "Estimation": CO.nombre(est, 3) if isinstance(est, float) else "–", "IC": ic,
            "p (Holm)": CO.nombre(d["p_holm"], 4) if isinstance(d.get("p_holm"), float) else "–",
            "Décision": str(d.get("decision", "–"))}


@callback(Output("res-contenu", "children"), Input("res-source", "value"))
def _contenu(source):
    rapide = source == "rapide"
    blocs = [CO.section("4.1", "Hypothèses déclarées et décisions", _decisions(rapide))]
    figs = []
    for nom, numero, legende in FIGURES:
        fig, erreur = SV.figure_officielle(nom, rapide)
        if fig is None:
            figs.append(CO.absent(f"Figure {numero} en attente : l'unité nécessaire n'est pas encore dans le magasin "
                                  f"({erreur})."))
        else:
            hauteur = {"prix_alerte": 640, "prix_marches": 700, "prix_decisions": 620}.get(nom, 460)
            figs.append(CO.graphe(f"res-{nom}", CO.habiller(fig), hauteur, numero=numero, legende=legende))
    blocs.append(CO.section("4.2", "Figures du mémoire", *figs))
    return blocs
