"""Administration : comptes, extraits du PAM (téléchargement HDX ou dépôt d'un fichier), journal des actions."""

import base64
import secrets

import dash
from dash import ALL, Input, Output, State, callback, ctx, dcc, html
from sqlalchemy import select, update

import acces as AC
import base as B
import composants as CO
import service as SV
from coeur import source_pam

dash.register_page(__name__, path="/administration", name="Administration", order=6, droit="administrer",
                   title="Administration, prix alimentaires du Cameroun")


def layout(**_):
    if not AC.peut("administrer"):
        return CO.absent("Accès refusé.")
    return html.Div([
        CO.tete("Administration", "Comptes, données et journal"),
        CO.section("Comptes",
                   html.Div([
                       html.Label(["Adresse électronique", dcc.Input(id="a-email", type="email", className="saisie")],
                                  className="champ"),
                       html.Label(["Nom", dcc.Input(id="a-nom", className="saisie")], className="champ"),
                       html.Label(["Organisation", dcc.Input(id="a-org", className="saisie")], className="champ"),
                       html.Label(["Rôle", dcc.Dropdown([{"label": v, "value": k} for k, v in B.ROLES.items()], "agent",
                                                        id="a-role", clearable=False)], className="champ"),
                       html.Button("Créer le compte", id="a-creer", className="bouton"),
                   ], className="controles"),
                   html.Div(id="a-message-comptes"), html.Div(id="a-comptes")),
        CO.section("Données du PAM",
                   html.P("Le PAM publie sa base de prix du Cameroun chaque mois sur HDX. Un nouvel extrait est filtré "
                          "comme dans le mémoire (prix de détail en XAF/kg des trois denrées) puis activé : le bulletin "
                          "couvre alors les nouveaux mois, avec le modèle choisi.", className="question"),
                   html.Div([html.Button("Télécharger le dernier extrait (HDX)", id="a-hdx", className="bouton"),
                             dcc.Upload(html.Button("Déposer un fichier CSV du PAM", className="bouton secondaire"),
                                        id="a-depot", accept=".csv"),
                             html.Button("Revenir à l'extrait du mémoire", id="a-memoire", className="bouton secondaire")],
                            className="boutons"),
                   dcc.Loading(html.Div(id="a-message-donnees")), html.Div(id="a-extraits")),
        CO.section("Journal", html.Div(id="a-journal")),
    ])


# ------------------------------------------------------------------------------ comptes
@callback(Output("a-message-comptes", "children"), Output("a-comptes", "children"),
          Input("a-creer", "n_clicks"), Input({"type": "a-actif", "index": ALL}, "n_clicks"),
          Input({"type": "a-mdp", "index": ALL}, "n_clicks"),
          State("a-email", "value"), State("a-nom", "value"), State("a-org", "value"), State("a-role", "value"))
def _comptes(_, __, ___, email, nom, org, role):
    u = AC.utilisateur()
    if not AC.peut("administrer", u):
        return CO.absent("Accès refusé."), None
    msg = None
    t = ctx.triggered_id
    declenche = bool(ctx.triggered and ctx.triggered[0]["value"])
    with B.session() as s:
        if t == "a-creer" and declenche:
            email = (email or "").strip().lower()
            if "@" not in email or not (nom or "").strip():
                msg = CO.message("Adresse et nom obligatoires.", erreur=True)
            elif s.scalar(select(B.Utilisateur).where(B.Utilisateur.email == email)):
                msg = CO.message("Ce compte existe déjà.", erreur=True)
            else:
                mdp = secrets.token_urlsafe(9)
                s.add(B.Utilisateur(email=email, nom=nom.strip(), role=role, organisation=(org or "").strip() or None,
                                    mot_de_passe=B.hacher(mdp)))
                B.journaliser(s, u.id, "compte créé", f"{email} ({role})")
                s.commit()
                msg = CO.message(["Compte créé. Mot de passe provisoire, à transmettre à la personne : ",
                                  html.Code(mdp), " (il ne sera plus affiché)."])
        elif isinstance(t, dict) and declenche:
            v = s.get(B.Utilisateur, t["index"])
            if v is not None and v.id != u.id:
                if t["type"] == "a-actif":
                    v.actif = not v.actif
                    B.journaliser(s, u.id, "compte " + ("réactivé" if v.actif else "désactivé"), v.email)
                    msg = CO.message(f"Compte {v.email} {'réactivé' if v.actif else 'désactivé'}.")
                else:
                    mdp = secrets.token_urlsafe(9)
                    v.mot_de_passe = B.hacher(mdp)
                    B.journaliser(s, u.id, "mot de passe réinitialisé", v.email)
                    msg = CO.message([f"Nouveau mot de passe provisoire de {v.email} : ", html.Code(mdp)])
                s.commit()
        comptes = s.scalars(select(B.Utilisateur).order_by(B.Utilisateur.role, B.Utilisateur.nom)).all()
    lignes = [html.Tr([html.Td(c.nom), html.Td(c.email), html.Td(c.organisation or ""), html.Td(B.ROLES[c.role]),
                       html.Td("actif" if c.actif else "désactivé"),
                       html.Td(html.Div([] if c.id == u.id else [
                           html.Button("Désactiver" if c.actif else "Réactiver", id={"type": "a-actif", "index": c.id},
                                       className="bouton secondaire"),
                           html.Button("Nouveau mot de passe", id={"type": "a-mdp", "index": c.id},
                                       className="bouton secondaire")], className="boutons"))])
              for c in comptes]
    tab = html.Div(html.Table([html.Thead(html.Tr([html.Th(x) for x in ("Nom", "Adresse", "Organisation", "Rôle", "État",
                                                                        "")])), html.Tbody(lignes)], className="tableau"),
                   className="tableau-cadre")
    return msg, tab


# ------------------------------------------------------------------------------ extraits
def _enregistrer_extrait(s, brut, origine, uid):
    extrait, info = source_pam.extraire(brut, SV.modele().fiche["panier"])
    e = s.scalar(select(B.Extrait).where(B.Extrait.sha256 == info["sha256"]))
    if e is None:
        e = B.Extrait(sha256=info["sha256"], contenu=extrait, lignes=info["lignes"], debut=info["debut"], fin=info["fin"],
                      origine=origine, charge_par_id=uid)
        s.add(e)
        s.flush()
    s.execute(update(B.Extrait).values(actif=False))
    e.actif = True
    B.journaliser(s, uid, "extrait activé", f"{origine} : {info['lignes']} lignes, {info['debut']} à {info['fin']}")
    return info


@callback(Output("a-message-donnees", "children"), Output("a-extraits", "children"),
          Input("a-hdx", "n_clicks"), Input("a-depot", "contents"), Input("a-memoire", "n_clicks"),
          Input({"type": "a-activer", "index": ALL}, "n_clicks"), State("a-depot", "filename"))
def _extraits(_, depot, __, ___, nom_fichier):
    u = AC.utilisateur()
    if not AC.peut("administrer", u):
        return CO.absent("Accès refusé."), None
    msg = None
    t = ctx.triggered_id
    declenche = bool(ctx.triggered and ctx.triggered[0]["value"])
    try:
        with B.session() as s:
            if t == "a-hdx" and declenche:
                info = _enregistrer_extrait(s, source_pam.telecharger(), "HDX, " + B.maintenant().strftime("%d/%m/%Y"), u.id)
                msg = CO.message(f"Extrait HDX activé : {info['lignes']} relevés, {info['debut']} à {info['fin']}.")
            elif t == "a-depot" and depot:
                brut = base64.b64decode(depot.split(",", 1)[1])
                info = _enregistrer_extrait(s, brut, f"fichier {nom_fichier}", u.id)
                msg = CO.message(f"Fichier activé : {info['lignes']} relevés, {info['debut']} à {info['fin']}.")
            elif t == "a-memoire" and declenche:
                s.execute(update(B.Extrait).values(actif=False))
                B.journaliser(s, u.id, "extrait du mémoire réactivé")
                msg = CO.message("Extrait du mémoire réactivé.")
            elif isinstance(t, dict) and declenche:
                s.execute(update(B.Extrait).values(actif=False))
                e = s.get(B.Extrait, t["index"])
                e.actif = True
                B.journaliser(s, u.id, "extrait activé", e.origine)
                msg = CO.message(f"Extrait activé : {e.origine}.")
            s.commit()
    except (RuntimeError, ValueError, KeyError, UnicodeDecodeError) as ex:
        msg = CO.message(f"Échec : {ex}", erreur=True)
    with B.session() as s:
        es = s.scalars(select(B.Extrait).order_by(B.Extrait.charge_le.desc())).all()
    actif = next((e for e in es if e.actif), None)
    lignes = [{"Origine": "extrait du mémoire (27/10/2026)", "Période": "jusqu'à 2026-08", "Relevés": "7 654",
               "État": "actif" if actif is None else ""}]
    lignes += [{"Origine": e.origine, "Période": f"{e.debut} à {e.fin}", "Relevés": CO.nombre(e.lignes, 0),
                "État": "actif" if e.actif else html.Button("Activer", id={"type": "a-activer", "index": e.id},
                                                            className="bouton secondaire")} for e in es]
    return msg, CO.tableau(["Origine", "Période", "Relevés", "État"], lignes, numeriques=["Relevés"])


@callback(Output("a-journal", "children"), Input("a-message-donnees", "children"), Input("a-message-comptes", "children"))
def _journal(*_):
    if not AC.peut("administrer"):
        return None
    with B.session() as s:
        js = s.scalars(select(B.Journal).order_by(B.Journal.quand.desc()).limit(50)).all()
        lignes = [{"Quand (UTC)": j.quand.strftime("%d/%m/%Y %H:%M"), "Qui": j.utilisateur.nom if j.utilisateur else "–",
                   "Action": j.action, "Détail": j.detail or ""} for j in js]
    return CO.tableau(["Quand (UTC)", "Qui", "Action", "Détail"], lignes)
