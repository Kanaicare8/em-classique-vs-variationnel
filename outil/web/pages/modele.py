"""Modèle et fiabilité : provenance des modèles, régimes appris, confrontation aux épisodes datés, limites."""

import math

import dash
from dash import Input, Output, callback, dcc, html

import acces as AC
import composants as CO
import service as SV
from pages.bulletin import options_versions

dash.register_page(__name__, path="/modele", name="Modèle et fiabilité", order=5,
                   title="Modèle et fiabilité, prix alimentaires du Cameroun")


def layout(**_):
    if not AC.peut("consulter"):
        return CO.absent("Accès refusé.")
    return html.Div([
        CO.tete("Modèle et fiabilité", "D'où viennent les chiffres, et ce qu'ils valent",
                "Le régime de tension est appris sans étiquette : c'est la composante d'un mélange gaussien dont les "
                "écarts de prix moyens sont les plus élevés. Cette page dit quel modèle produit les chiffres, ce qu'il a "
                "appris, et comment il se comporte sur les épisodes connus."),
        html.Div([html.Label(["Modèle", dcc.Dropdown(options_versions(), SV.REFERENCE, id="f-version", clearable=False)],
                             className="champ large")], className="controles"),
        html.Div(id="f-contenu"),
    ])


@callback(Output("f-contenu", "children"), Input("f-version", "value"))
def _contenu(version):
    st = SV.etat(version)
    f = st["modele"].fiche
    prov = CO.section("Provenance", CO.fiche([
        ("Modèle", f["libelle"]), ("Apprentissage", f"{f['apprentissage']['debut']} à {f['apprentissage']['fin']} "
                                                    f"({f['apprentissage']['n']} observations)"),
        ("Écarts", f"fenêtre de {f['ecarts']['fenetre_mois']} mois, au moins {f['ecarts']['releves_min']} relevés, pics "
                   f"isolés d'un facteur {CO.nombre(f['ecarts']['facteur_pic'], 0)} écartés"),
        ("Code", f"commit {f['code']['commit']}" if f["code"].get("commit") else "–"),
        ("Données du modèle", f"{f['donnees']['fichier']} (SHA-256 {f['donnees']['sha256'][:12]}…)"),
        ("Données affichées", f"{st['extrait']['origine']} (SHA-256 {st['extrait']['sha256'][:12]}…)")]),
        html.P(f["description"], className="question"))

    blocs = [prov]
    for b, info in f["bras"].items():
        lignes = []
        for rang, r in enumerate(sorted(info["regimes"], key=lambda r: sum(r["ecart_moyen"])), start=1):
            lignes.append({"Régime": f"R{rang}" + (" (tension)" if r["tension"] else ""),
                           "Poids": CO.pourcent(r["poids"], 1),
                           **{n: CO.pourcent(math.expm1(v), 0, signe=True) for n, v in zip(f["noms"], r["ecart_moyen"])},
                           "_classe": "ligne-tension" if r["tension"] else None})
        blocs.append(CO.section(f"Régimes appris, {b}", CO.tableau(["Régime", "Poids"] + f["noms"], lignes,
                                                                   numeriques=["Poids"] + f["noms"]),
                                html.P(f"Écart moyen de chaque denrée à son niveau des douze mois, en variation de prix. "
                                       f"Intervalle : {info['intervalle']} ({info['n_tirages']}).", className="question")))

    app = [i for i, t in enumerate(st["mois"]) if t <= st["fin_apprentissage"]]
    hors = [i for i, t in enumerate(st["mois"]) if t > st["fin_apprentissage"]]
    lignes = []
    for b, r in st["proba"].items():
        def part(idx):
            return CO.pourcent(sum(float(r["p"][i]) > 0.5 for i in idx) / len(idx), 1) if idx else "–"

        def ambigu(idx):
            return CO.pourcent(sum(float(r["bas"][i]) <= 0.5 <= float(r["haut"][i]) for i in idx) / len(idx), 1) \
                if idx else "–"
        lignes.append({"Bras": b, "Alerte, apprentissage": part(app), "Alerte, hors apprentissage": part(hors),
                       "IC contenant 0,5 (hors apprentissage)": ambigu(hors)})
    cols = ["Bras", "Alerte, apprentissage", "Alerte, hors apprentissage", "IC contenant 0,5 (hors apprentissage)"]
    blocs.append(CO.section("Fréquence des alertes", CO.tableau(cols, lignes, numeriques=cols[1:]), html.P(
        "Une forte différence entre apprentissage et hors apprentissage signale que les prix récents ne ressemblent plus "
        "à ceux de l'apprentissage : c'est le signal pour réestimer le modèle.", className="question")))

    ep = []
    for e in SV.EPISODES:
        t = SV.mois_index(e["mois"])
        idx = [i for i, (u, m) in enumerate(zip(st["mois"], st["marche"])) if u == t and
               st["releves"].marches[m].region == e["region"] and (not e["marches"] or m in e["marches"])]
        for i in idx:
            ep.append({"Épisode": e["texte"], "Sens attendu": e["sens"], "Marché": st["marche"][i],
                       **{f"P {b}": CO.nombre(float(r["p"][i]), 2) for b, r in st["proba"].items()},
                       "_classe": "ligne-tension" if any(float(r["p"][i]) > 0.5 for r in st["proba"].values()) else None})
    cols_e = ["Épisode", "Sens attendu", "Marché"] + [f"P {b}" for b in st["proba"]]
    blocs.append(CO.section("Épisodes datés par les bulletins", CO.tableau(cols_e, ep, numeriques=cols_e[3:]) if ep else
                            CO.absent("Aucune observation pour ces épisodes dans les données affichées."), html.P(
        "Une hausse datée devrait allumer le régime de tension ; une baisse ne le devrait pas. Deux épisodes ne valident "
        "pas un outil : il faut confronter les alertes à d'autres bulletins (PAM, FEWS NET, Système d'alerte précoce) "
        "avant tout usage opérationnel.", className="question")))
    blocs.append(CO.section("Limites", html.Ul([
        html.Li("Pas de vérité terrain : le régime de tension est défini par le modèle, pas par une crise constatée."),
        html.Li("Trois denrées (maïs blanc, riz importé, niébé) ; les marchés suivis sont surtout ceux de l'Extrême-Nord, "
                "de l'Adamaoua et du Nord."),
        html.Li("Le modèle du mémoire est figé sur 2021-2023 ; une réestimation est possible mais ne le remplace pas."),
        html.Li("Un écart se calcule à partir de trois relevés au moins dans les douze mois précédents ; les marchés peu "
                "suivis restent sans lecture."),
    ])))
    return blocs
