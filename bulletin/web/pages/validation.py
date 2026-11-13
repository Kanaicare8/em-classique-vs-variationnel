"""Validation des relevés saisis par les agents (analystes et administrateurs)."""

import dash
from dash import ALL, Input, Output, State, callback, ctx, dcc, html
from sqlalchemy import select

import acces as AC
import base as B
import composants as CO
import service as SV
from pages.saisie import ECART_SUSPECT

dash.register_page(__name__, path="/validation", name="Validation", order=4, droit="valider",
                   title="Validation des relevés, prix alimentaires du Cameroun")


def layout(**_):
    if not AC.peut("valider"):
        return CO.absent("Accès refusé.")
    return html.Div([
        CO.tete("Validation", "Relevés en attente de validation",
                "Un relevé validé entre dans le bulletin et dans le niveau des douze mois des relevés suivants ; un "
                "relevé rejeté reste dans le journal. L'écart indiqué aide à repérer une erreur de saisie (unité, zéro "
                "en trop)."),
        html.Div([html.Button("Valider tous les relevés sans écart à vérifier", id="v-tout", className="bouton")],
                 className="boutons"),
        html.Div(id="v-message"),
        dcc.Store(id="v-signal", data=0),
        html.Div(id="v-liste"),
    ])


@callback(Output("v-message", "children"), Output("v-signal", "data"),
          Input({"type": "v-valider", "index": ALL}, "n_clicks"), Input({"type": "v-rejeter", "index": ALL}, "n_clicks"),
          Input("v-tout", "n_clicks"), State("v-signal", "data"), prevent_initial_call=True)
def _decider(_, __, tout, signal):
    """Action seule : la liste est redessinée par _liste quand le signal change (les boutons recréés, n_clicks vide,
    ne déclenchent rien)."""
    u = AC.utilisateur()
    t = ctx.triggered_id
    if t == "v-tout" and tout and AC.peut("valider", u):
        st = SV.etat()
        n = 0
        with B.session() as s:
            for r in s.scalars(select(B.Releve).where(B.Releve.statut == "en_attente")).all():
                e = st["releves"].ecart(r.marche, r.denree, SV.mois_index(r.mois), prix=r.prix)
                if e is not None and abs(e) <= ECART_SUSPECT:
                    r.statut, r.valide_par_id, r.valide_le = "valide", u.id, B.maintenant()
                    n += 1
            if n:
                B.journaliser(s, u.id, "relevés validés en lot", f"{n} relevés sans écart à vérifier")
            s.commit()
        return CO.message(f"{n} relevé{'s' if n > 1 else ''} validé{'s' if n > 1 else ''} ; les relevés à vérifier "
                          "ou sans niveau habituel restent en attente."), (signal or 0) + 1
    if not (isinstance(t, dict) and AC.peut("valider", u) and any(x["value"] for x in ctx.triggered)):
        return dash.no_update, dash.no_update
    with B.session() as s:
        r = s.get(B.Releve, t["index"])
        if r is None or r.statut != "en_attente":
            return dash.no_update, (signal or 0) + 1
        r.statut = "valide" if t["type"] == "v-valider" else "rejete"
        r.valide_par_id, r.valide_le = u.id, B.maintenant()
        B.journaliser(s, u.id, f"relevé {B.STATUTS[r.statut]}", f"n° {r.id} {r.marche} {r.mois} {r.denree}")
        s.commit()
        return CO.message(f"Relevé n° {r.id} {B.STATUTS[r.statut]}."), (signal or 0) + 1


@callback(Output("v-liste", "children"), Input("v-signal", "data"))
def _liste(_):
    if not AC.peut("valider"):
        return CO.absent("Accès refusé.")
    st = SV.etat()
    noms = dict(zip(st["modele"].fiche["panier"], st["modele"].fiche["noms"]))
    with B.session() as s:
        rs = s.scalars(select(B.Releve).where(B.Releve.statut == "en_attente").order_by(B.Releve.saisi_le)).all()
        auteurs = {r.id: r.saisi_par.nom for r in rs}
    if not rs:
        return CO.absent("Aucun relevé en attente.")
    tete = html.Thead(html.Tr([html.Th(c) for c in ("N°", "Saisi le", "Par", "Marché", "Mois", "Denrée", "Prix (XAF/kg)",
                                                     "Écart au niveau", "Commentaire", "")]))
    lignes = []
    for r in rs:
        e = st["releves"].ecart(r.marche, r.denree, SV.mois_index(r.mois), prix=r.prix)
        suspect = e is None or abs(e) > ECART_SUSPECT
        lignes.append(html.Tr([
            html.Td(str(r.id)), html.Td(r.saisi_le.strftime("%d/%m/%Y")), html.Td(auteurs[r.id]), html.Td(r.marche),
            html.Td(SV.mois_humain(SV.mois_index(r.mois))), html.Td(noms.get(r.denree, r.denree)), html.Td(CO.nombre(r.prix, 0), className="num"),
            html.Td([CO.ecart_pourcent(e), " ", html.Span("à vérifier", className="badge badge-ambre")] if suspect
                    else CO.ecart_pourcent(e), className="num"),
            html.Td(r.commentaire or ""),
            html.Td(html.Div([html.Button("Valider", id={"type": "v-valider", "index": r.id}, className="bouton"),
                              html.Button("Rejeter", id={"type": "v-rejeter", "index": r.id}, className="bouton danger")],
                             className="boutons"))], className="ligne-incertaine" if suspect else None))
    return html.Div(html.Table([tete, html.Tbody(lignes)], className="tableau"), className="tableau-cadre")
