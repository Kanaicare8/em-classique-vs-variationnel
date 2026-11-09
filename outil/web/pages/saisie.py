"""Saisie d'un relevé de prix : évaluation immédiate (écarts, P(tension)) puis enregistrement pour validation."""

from datetime import date

import dash
from dash import Input, Output, State, callback, ctx, dcc, html
from sqlalchemy import select

import acces as AC
import base as B
import composants as CO
import service as SV

dash.register_page(__name__, path="/saisie", name="Saisie", order=3, droit="saisir",
                   title="Saisie d'un relevé, prix alimentaires du Cameroun")


def _mois_saisissables(st):
    """Des 24 mois avant le dernier mois des données jusqu'au mois en cours."""
    aujourdhui = SV.mois_index(date.today().strftime("%Y-%m"))
    fin = max(aujourdhui, st["releves"].dernier_mois())
    return list(range(fin, st["releves"].dernier_mois() - 24, -1))


def layout(**_):
    if not AC.peut("saisir"):
        return CO.absent("Accès refusé.")
    st = SV.etat()
    noms = st["modele"].fiche["noms"]
    marches = SV.marches_connus(st)
    aujourdhui = SV.mois_index(date.today().strftime("%Y-%m"))
    mois = _mois_saisissables(st)
    return html.Div([
        CO.tete("Saisie", "Saisir un relevé de prix",
                "Prix de détail en francs CFA par kilogramme, relevés sur un marché pour un mois. L'outil calcule "
                "aussitôt l'écart de chaque prix à son niveau des douze mois précédents et la probabilité du régime de "
                "tension ; le relevé entre dans le bulletin une fois validé par un analyste.",
                CO.note("Le niveau des douze mois s'appuie sur les relevés connus (PAM et relevés validés) ; il faut au "
                        "moins trois relevés de la denrée dans les douze mois précédents. Un relevé du PAM du même "
                        "marché, de la même denrée et du même mois l'emporte sur un relevé saisi.")),
        html.Div([
            html.Label(["Marché", dcc.Dropdown([{"label": f"{m.nom}, {m.region}", "value": m.nom} for m in marches],
                                               id="s-marche", placeholder="Choisir un marché")], className="champ large"),
            html.Label(["Mois du relevé", dcc.Dropdown([{"label": SV.mois_texte(t), "value": t} for t in mois],
                                                       min(aujourdhui, mois[0]), id="s-mois", clearable=False)],
                       className="champ"),
        ], className="controles"),
        html.Div([html.Label([f"{n} (XAF/kg)", dcc.Input(id=f"s-prix-{j}", type="number", min=1, step=1, debounce=True,
                                                         className="saisie")], className="champ")
                  for j, n in enumerate(noms)], className="controles"),
        html.Label(["Commentaire (facultatif : conditions du relevé, source)",
                    dcc.Textarea(id="s-commentaire", className="saisie", maxLength=500)], className="champ large"),
        html.Div([html.Button("Enregistrer le relevé", id="s-enregistrer", className="bouton")], className="boutons"),
        html.Div(id="s-message"),
        CO.section("Lecture du relevé", html.Div(id="s-lecture")),
        CO.section("Mes derniers relevés", html.Div(id="s-mes-releves")),
    ])


@callback(*[Output(f"s-prix-{j}", "placeholder") for j in range(3)], Input("s-marche", "value"), Input("s-mois", "value"))
def _dernier_prix(marche, t):
    st = SV.etat()
    out = []
    for c in st["modele"].fiche["panier"]:
        s = st["releves"].serie.get((marche, c), {}) if marche else {}
        avant = [u for u in s if u < (t or 0)]
        out.append(f"dernier : {CO.nombre(st['releves'].prix(marche, c, max(avant)), 0)} ({SV.mois_texte(max(avant))})"
                   if avant else "")
    return tuple(out)


@callback(Output("s-lecture", "children"), Input("s-marche", "value"), Input("s-mois", "value"),
          *[Input(f"s-prix-{j}", "value") for j in range(3)])
def _lire(marche, t, *prix):
    if not marche:
        return CO.absent("Choisir un marché et saisir les prix.")
    st = SV.etat()
    fiche = st["modele"].fiche
    saisis = {c: float(p) for c, p in zip(fiche["panier"], prix) if p}
    ecarts, niveaux, res = SV.evaluer_releve(SV.REFERENCE, marche, t, saisis)
    lignes = []
    for n, c, e in zip(fiche["noms"], fiche["panier"], ecarts):
        niv, k = niveaux[c]
        lignes.append({"Denrée": n, "Prix saisi": CO.nombre(saisis.get(c), 0) if c in saisis else "–",
                       "Niveau des 12 mois": CO.nombre(niv, 0) if niv else f"– ({k} relevés, 3 requis)",
                       "Écart": CO.ecart_pourcent(e), "_classe": "ligne-incertaine" if e is None else None})
    cols = ["Denrée", "Prix saisi", "Niveau des 12 mois", "Écart"]
    bloc = [CO.tableau(cols, lignes, numeriques=cols[1:])]
    if res is None:
        bloc.append(CO.absent("Probabilité non calculable : il faut les trois prix et assez de relevés passés."))
        return bloc
    lignes_p = []
    for b, r in res.items():
        lec, classe = SV.lecture(r["p"], r["bas"], r["haut"])
        lignes_p.append({"Bras": b, "P(tension)": CO.nombre(r["p"], 2),
                         "IC 90 %": f"[{CO.nombre(r['bas'], 2)} ; {CO.nombre(r['haut'], 2)}]", "Lecture": lec,
                         "_classe": classe})
    bloc += [CO.tableau(["Bras", "P(tension)", "IC 90 %", "Lecture"], lignes_p, numeriques=["P(tension)", "IC 90 %"]),
             html.P("Modèle du mémoire (référence). Une alerte appelle une vérification sur le terrain.",
                    className="question")]
    return bloc


@callback(Output("s-message", "children"), Output("s-mes-releves", "children"),
          Input("s-enregistrer", "n_clicks"), State("s-marche", "value"), State("s-mois", "value"),
          *[State(f"s-prix-{j}", "value") for j in range(3)], State("s-commentaire", "value"))
def _enregistrer(_, marche, t, p0, p1, p2, commentaire):
    u = AC.utilisateur()
    message = None
    if ctx.triggered_id == "s-enregistrer" and AC.peut("saisir", u):
        st = SV.etat()
        fiche = st["modele"].fiche
        prix = {c: float(p) for c, p in zip(fiche["panier"], (p0, p1, p2)) if p}
        if not marche or not prix:
            message = CO.message("Choisir un marché et saisir au moins un prix.", erreur=True)
        elif any(p <= 0 or p > 100000 for p in prix.values()):
            message = CO.message("Prix hors des bornes plausibles (1 à 100 000 XAF/kg).", erreur=True)
        else:
            mois = SV.mois_texte(t)
            region = st["releves"].marches[marche].region
            statut = "valide" if u.role in ("admin", "analyste") else "en_attente"
            faits, ignores = [], []
            with B.session() as s:
                for c, p in prix.items():
                    deja = s.scalar(select(B.Releve).where(B.Releve.marche == marche, B.Releve.denree == c,
                                                           B.Releve.mois == mois, B.Releve.statut != "rejete"))
                    if deja is not None:
                        ignores.append(f"{fiche['noms'][fiche['panier'].index(c)]} (déjà saisi)")
                        continue
                    r = B.Releve(marche=marche, region=region, denree=c, mois=mois, prix=p, statut=statut,
                                 commentaire=(commentaire or "").strip() or None, saisi_par_id=u.id)
                    if statut == "valide":
                        r.valide_par_id, r.valide_le = u.id, B.maintenant()
                    s.add(r)
                    faits.append(fiche["noms"][fiche["panier"].index(c)])
                if faits:
                    B.journaliser(s, u.id, "relevé saisi", f"{marche} {mois} : {', '.join(faits)} ({statut})")
                s.commit()
            texte = (f"Relevé enregistré ({', '.join(faits)}), "
                     + ("validé d'office." if statut == "valide" else "en attente de validation par un analyste.")
                     if faits else "Rien d'enregistré.")
            if ignores:
                texte += " Non enregistrés : " + ", ".join(ignores) + "."
            message = CO.message(texte, erreur=not faits)
    return message, _mes_releves(u)


def _mes_releves(u):
    if u is None:
        return None
    noms = dict(zip(SV.modele().fiche["panier"], SV.modele().fiche["noms"]))
    with B.session() as s:
        rs = s.scalars(select(B.Releve).where(B.Releve.saisi_par_id == u.id).order_by(B.Releve.saisi_le.desc())
                       .limit(30)).all()
    if not rs:
        return CO.absent("Aucun relevé saisi pour l'instant.")
    cols = ["Saisi le", "Marché", "Mois", "Denrée", "Prix (XAF/kg)", "Statut"]
    return CO.tableau(cols, [{"Saisi le": r.saisi_le.strftime("%d/%m/%Y %H:%M"), "Marché": r.marche, "Mois": r.mois,
                              "Denrée": noms.get(r.denree, r.denree), "Prix (XAF/kg)": CO.nombre(r.prix, 0),
                              "Statut": B.STATUTS[r.statut],
                              "_classe": "ligne-incertaine" if r.statut == "en_attente" else None} for r in rs],
                      numeriques=["Prix (XAF/kg)"])
