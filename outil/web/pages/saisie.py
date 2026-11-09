"""Saisie d'un relevé de prix : lecture immédiate (écarts, état du marché) puis enregistrement pour validation."""

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

ECART_SUSPECT = 0.7          # |écart| du log-prix : prix multiplié ou divisé par environ 2


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
    formulaire = html.Div([
        html.P("1. Où et quand ?", className="etape"),
        html.Div([
            html.Label(["Marché", dcc.Dropdown([{"label": f"{m.nom} ({m.region})", "value": m.nom} for m in marches],
                                               id="s-marche", placeholder="Taper le nom du marché")],
                       className="champ large"),
            html.Label(["Mois du relevé", dcc.Dropdown([{"label": SV.mois_humain(t), "value": t} for t in mois],
                                                       min(aujourdhui, mois[0]), id="s-mois", clearable=False)],
                       className="champ"),
        ], className="controles"),
        html.P("2. Prix de détail, en francs CFA par kilogramme", className="etape"),
        html.Div([html.Label([n[0].upper() + n[1:], dcc.Input(id=f"s-prix-{j}", type="number", min=1, step=1,
                                                              debounce=True, className="saisie", inputMode="numeric"),
                              html.Span(id=f"s-dernier-{j}", className="tuile-sous")], className="champ")
                  for j, n in enumerate(noms)], className="controles"),
        html.P("3. Commentaire (facultatif)", className="etape"),
        dcc.Textarea(id="s-commentaire", className="saisie", maxLength=500,
                     placeholder="Conditions du relevé, source, remarque…"),
        html.Div([html.Button("Enregistrer le relevé", id="s-enregistrer", className="bouton"),
                  html.Span("Le relevé sera vérifié par un analyste avant d'entrer dans le bulletin."
                            if not AC.peut("valider") else "Votre relevé sera validé d'office.",
                            className="tuile-sous")], className="boutons"),
        html.Div(id="s-message"),
    ])
    return html.Div([
        CO.tete("Saisie", "Saisir un relevé de prix",
                "Dès que les trois prix sont saisis, l'outil les compare à leur niveau habituel et indique l'état du "
                "marché ; rien n'est enregistré avant d'appuyer sur « Enregistrer »."),
        html.Div([formulaire, html.Div(CO.chargement(html.Div(id="s-lecture")), className="carte collante")],
                 className="grille-saisie"),
        CO.section("Mes derniers relevés", html.Div(id="s-mes-releves")),
    ])


@callback(*[Output(f"s-dernier-{j}", "children") for j in range(3)], Input("s-marche", "value"), Input("s-mois", "value"))
def _dernier_prix(marche, t):
    st = SV.etat()
    out = []
    for c in st["modele"].fiche["panier"]:
        s = st["releves"].serie.get((marche, c), {}) if marche else {}
        avant = [u for u in s if u < (t or 0)]
        out.append(f"dernier : {CO.nombre(st['releves'].prix(marche, c, max(avant)), 0)} XAF/kg "
                   f"({SV.mois_humain(max(avant), court=True)})" if avant else ("aucun relevé connu" if marche else ""))
    return tuple(out)


@callback(Output("s-lecture", "children"), Input("s-marche", "value"), Input("s-mois", "value"),
          *[Input(f"s-prix-{j}", "value") for j in range(3)])
def _lire(marche, t, *prix):
    if not marche:
        return [html.H3("Lecture du relevé"), html.P("Choisir un marché, puis saisir les prix.", className="chapeau")]
    st = SV.etat()
    fiche = st["modele"].fiche
    saisis = {c: float(p) for c, p in zip(fiche["panier"], prix) if p}
    ecarts, niveaux, res = SV.evaluer_releve(SV.REFERENCE, marche, t, saisis)
    bloc = [html.H3(f"{marche}, {SV.mois_humain(t)}")]
    lignes, alertes = [], []
    for n, c, e in zip(fiche["noms"], fiche["panier"], ecarts):
        niv, k = niveaux[c]
        lignes.append({"Denrée": n, "Saisi": CO.nombre(saisis.get(c), 0) if c in saisis else "–",
                       "Habituel": CO.nombre(niv, 0) if niv else "–",
                       "Écart": html.Span(CO.ecart_pourcent(e), className="hausse" if e and e > 0.05 else
                                          "baisse" if e and e < -0.05 else None) if e is not None else "–"})
        if niv is None:
            alertes.append(f"{n} : pas de niveau habituel ({k} relevé{'s' if k > 1 else ''} dans les douze mois "
                           f"précédents, 3 requis).")
        elif e is not None and abs(e) > ECART_SUSPECT:
            alertes.append(f"{n} : prix {'plus du double' if e > 0 else 'moins de la moitié'} du niveau habituel. "
                           "Vérifier l'unité (XAF par kg) et le montant.")
    if res is None:
        bloc.append(html.Div([html.Span("En attente", className="badge etiquette"),
                              html.Span("l'état du marché s'affiche dès que les trois prix sont saisis",
                                        className="verdict-texte")], className="verdict"))
    else:
        ev = {b: SV.lecture(r["p"], r["bas"], r["haut"]) for b, r in res.items()}
        hauts = [r["p"] > SV.SEUIL for r in res.values()]
        etat = "alerte" if all(hauts) else "desaccord" if any(hauts) else \
            ("surveiller" if "surveiller" in ev.values() else "calme")
        bloc.append(html.Div([CO.badge(etat), html.Span(SV.ETATS[etat][4], className="verdict-texte")],
                             className="verdict"))
        bloc += [html.Div([html.Span(SV.METHODES[b]), html.Span([f"{CO.pourcent(r['p'], 0)} ",
                                                                  html.Span(f"({CO.pourcent(r['bas'], 0)} à "
                                                                            f"{CO.pourcent(r['haut'], 0)})",
                                                                            className="tuile-sous")])],
                          className="ligne-methode") for b, r in res.items()]
    bloc.append(CO.tableau(["Denrée", "Saisi", "Habituel", "Écart"], lignes, numeriques=["Saisi", "Habituel", "Écart"]))
    bloc += [html.Div(a, className="avertissement-saisie") for a in alertes]
    bloc.append(html.P("Habituel : moyenne des prix des douze mois précédents (XAF/kg). Une alerte appelle une "
                       "vérification sur le terrain.", className="tuile-sous"))
    return bloc


@callback(Output("s-message", "children"), Output("s-mes-releves", "children"),
          *[Output(f"s-prix-{j}", "value") for j in range(3)], Output("s-commentaire", "value"),
          Input("s-enregistrer", "n_clicks"), State("s-marche", "value"), State("s-mois", "value"),
          *[State(f"s-prix-{j}", "value") for j in range(3)], State("s-commentaire", "value"))
def _enregistrer(_, marche, t, p0, p1, p2, commentaire):
    u = AC.utilisateur()
    garder = (dash.no_update,) * 4
    if ctx.triggered_id != "s-enregistrer" or not AC.peut("saisir", u):
        return None, _mes_releves(u), *garder
    st = SV.etat()
    fiche = st["modele"].fiche
    prix = {c: float(p) for c, p in zip(fiche["panier"], (p0, p1, p2)) if p}
    if not marche or not prix:
        return CO.message("Choisir un marché et saisir au moins un prix.", erreur=True), _mes_releves(u), *garder
    if any(p <= 0 or p > 100000 for p in prix.values()):
        return CO.message("Prix hors des bornes plausibles (1 à 100 000 XAF/kg).", erreur=True), _mes_releves(u), *garder
    mois = SV.mois_texte(t)
    region = st["releves"].marches[marche].region
    statut = "valide" if u.role in ("admin", "analyste") else "en_attente"
    faits, ignores = [], []
    with B.session() as s:
        for c, p in prix.items():
            nom = fiche["noms"][fiche["panier"].index(c)]
            deja = s.scalar(select(B.Releve).where(B.Releve.marche == marche, B.Releve.denree == c,
                                                   B.Releve.mois == mois, B.Releve.statut != "rejete"))
            if deja is not None:
                ignores.append(f"{nom} (déjà saisi pour ce mois)")
                continue
            r = B.Releve(marche=marche, region=region, denree=c, mois=mois, prix=p, statut=statut,
                         commentaire=(commentaire or "").strip() or None, saisi_par_id=u.id)
            if statut == "valide":
                r.valide_par_id, r.valide_le = u.id, B.maintenant()
            s.add(r)
            faits.append(nom)
        if faits:
            B.journaliser(s, u.id, "relevé saisi", f"{marche} {mois} : {', '.join(faits)} ({statut})")
        s.commit()
    if not faits:
        return CO.message("Rien d'enregistré : " + ", ".join(ignores) + ".", erreur=True), _mes_releves(u), *garder
    texte = (f"Relevé de {marche} ({SV.mois_humain(t)}) enregistré : {', '.join(faits)}. "
             + ("Validé d'office." if statut == "valide" else "Un analyste le vérifiera."))
    if ignores:
        texte += " Non enregistré : " + ", ".join(ignores) + "."
    return CO.message(texte), _mes_releves(u), None, None, None, ""


def _mes_releves(u):
    if u is None:
        return None
    noms = dict(zip(SV.modele().fiche["panier"], SV.modele().fiche["noms"]))
    with B.session() as s:
        rs = s.scalars(select(B.Releve).where(B.Releve.saisi_par_id == u.id).order_by(B.Releve.saisi_le.desc())
                       .limit(30)).all()
    if not rs:
        return CO.absent("Aucun relevé saisi pour l'instant.")
    couleurs = {"en_attente": "ambre", "valide": "vert", "rejete": "rouge"}
    cols = ["Saisi le", "Marché", "Mois", "Denrée", "Prix (XAF/kg)", "Statut"]
    return CO.tableau(cols, [{"Saisi le": r.saisi_le.strftime("%d/%m/%Y %H:%M"), "Marché": r.marche,
                              "Mois": SV.mois_humain(SV.mois_index(r.mois)), "Denrée": noms.get(r.denree, r.denree),
                              "Prix (XAF/kg)": CO.nombre(r.prix, 0),
                              "Statut": html.Span(B.STATUTS[r.statut], className=f"badge badge-{couleurs[r.statut]}")}
                             for r in rs], numeriques=["Prix (XAF/kg)"])
