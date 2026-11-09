"""
================================================================================
OUTIL DE SUIVI DES PRIX ALIMENTAIRES DU CAMEROUN (D-20)
================================================================================

En local :   python outil/web/app.py             puis http://127.0.0.1:8060 (port : variable PORT)
En ligne :   gunicorn --chdir outil/web app:server (voir outil/README.md)

Variables d'environnement :
  DATABASE_URL                Postgres (en ligne) ; à défaut SQLite dans outil/instance/
  OUTIL_SECRET                clé de signature des sessions (obligatoire en ligne)
  OUTIL_ADMIN_EMAIL,
  OUTIL_ADMIN_MOT_DE_PASSE    premier administrateur, créé si la base n'a aucun compte
  OUTIL_COOKIE_SECURISE=1     cookie de session réservé à HTTPS (en ligne)
"""

from __future__ import annotations

import os
import secrets
import sys
import time
from html import escape
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path[:0] = [str(ICI), str(ICI.parent)]

import dash  # noqa: E402
from dash import Dash, Input, Output, dcc, html  # noqa: E402
from flask import Flask, Response, redirect, request, session  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

import acces as AC  # noqa: E402
import base as B  # noqa: E402


def _secret():
    if os.environ.get("OUTIL_SECRET"):
        return os.environ["OUTIL_SECRET"]
    f = ICI.parent / "instance" / "secret.txt"
    f.parent.mkdir(exist_ok=True)
    if not f.exists():
        f.write_text(secrets.token_hex(32), encoding="utf-8")
    return f.read_text(encoding="utf-8").strip()


B.initialiser()
import threading  # noqa: E402

import service as SV  # noqa: E402

threading.Thread(target=SV.etat, daemon=True).start()     # préchauffage : probabilités de toutes les observations
server = Flask(__name__)
server.secret_key = _secret()
server.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                     SESSION_COOKIE_SECURE=os.environ.get("OUTIL_COOKIE_SECURISE") == "1",
                     PERMANENT_SESSION_LIFETIME=12 * 3600, MAX_CONTENT_LENGTH=30 * 1024 * 1024)

POLICES = ("https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,400;0,600;1,400"
           "&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&display=swap")
LIBRES = ("/connexion", "/assets/", "/_favicon", "/sante")

# ------------------------------------------------------------------------------ connexion (Flask)
_echecs: dict = {}


def _trop_d_echecs(ip):
    recents = [t for t in _echecs.get(ip, []) if time.time() - t < 600]
    _echecs[ip] = recents
    return len(recents) >= 8


@server.before_request
def _proteger():
    if request.path.startswith(LIBRES):
        return None
    if AC.utilisateur() is None:
        if request.path.startswith("/_dash"):
            return Response("session expirée", status=401)
        return redirect("/connexion")
    return None


def _page_connexion(erreur=""):
    vide = not _a_des_comptes()
    corps = (f'<p class="message erreur">{escape(erreur)}</p>' if erreur else "") + (
        '<p class="message erreur">Aucun compte : définir OUTIL_ADMIN_EMAIL et OUTIL_ADMIN_MOT_DE_PASSE puis redémarrer.</p>'
        if vide else "")
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Connexion, prix alimentaires du Cameroun</title>
<link rel="stylesheet" href="{POLICES}"><link rel="stylesheet" href="/assets/style.css"></head>
<body><form class="connexion" method="post" action="/connexion">
<h1>Prix alimentaires du Cameroun</h1><p>Suivi des marchés et régime de tension des prix</p>{corps}
<label for="email">Adresse électronique</label><input id="email" name="email" type="email" required autofocus>
<label for="mdp">Mot de passe</label><input id="mdp" name="mdp" type="password" required>
<button class="bouton" type="submit">Se connecter</button></form></body></html>"""


def _a_des_comptes():
    with B.session() as s:
        return bool(s.scalar(select(func.count(B.Utilisateur.id))))


@server.route("/connexion", methods=["GET", "POST"])
def connexion():
    if request.method == "GET":
        return _page_connexion()
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?").split(",")[0].strip()
    if _trop_d_echecs(ip):
        return _page_connexion("Trop d'essais : réessayer dans dix minutes."), 429
    email = (request.form.get("email") or "").strip().lower()
    with B.session() as s:
        u = s.scalar(select(B.Utilisateur).where(B.Utilisateur.email == email))
        if u is None or not u.verifier(request.form.get("mdp") or ""):
            _echecs.setdefault(ip, []).append(time.time())
            return _page_connexion("Adresse ou mot de passe incorrect."), 401
        session.clear()
        session.permanent = True
        session["uid"] = u.id
        B.journaliser(s, u.id, "connexion")
        s.commit()
    return redirect("/")


@server.route("/deconnexion")
def deconnexion():
    session.clear()
    return redirect("/connexion")


@server.route("/sante")
def sante():
    return {"etat": "ok"}


import exports  # noqa: E402

server.add_url_rule("/export/bulletin.csv", "bulletin_csv", exports.csv_bulletin)
server.add_url_rule("/export/bulletin.pdf", "bulletin_pdf", exports.pdf_bulletin)

# ------------------------------------------------------------------------------ application Dash
app = Dash(__name__, server=server, use_pages=True, pages_folder=str(ICI / "pages"), assets_folder=str(ICI / "assets"),
           external_stylesheets=[POLICES], title="Prix alimentaires du Cameroun", update_title=None,
           suppress_callback_exceptions=True)


def _navigation():
    u = AC.utilisateur()
    pages = [p for p in dash.page_registry.values() if u is not None and AC.peut(p.get("droit", "consulter"), u)]
    return html.Nav([dcc.Link(p["name"], href=p["relative_path"], className="nav-lien") for p in pages], className="nav")


def _compte():
    u = AC.utilisateur()
    if u is None:
        return None
    return html.Div([html.Span(f"{u.nom} ({B.ROLES[u.role]})"), html.A("Se déconnecter", href="/deconnexion")],
                    className="compte")


def _gabarit():
    return html.Div([
        dcc.Location(id="url"),
        html.Div([
            html.Div([html.Span("Régime de tension des prix, d'après le mémoire de KANA TIODONG Icare Brichel",
                                className="marque-sur"),
                      html.Span("Prix alimentaires du Cameroun", className="marque")], className="marque-bloc"),
            html.Div([_navigation(), _compte()], style={"display": "flex", "flexDirection": "column",
                                                         "alignItems": "flex-end", "gap": "6px"}),
        ], className="barre"),
        html.Main(dash.page_container, className="contenu"),
        html.Footer([
            html.P(["Données : Programme alimentaire mondial, ", html.Em("Cameroon – Food Prices"),
                    ", Humanitarian Data Exchange, licence CC BY-IGO ; relevés saisis et validés dans l'outil."]),
            html.P("Aide à la lecture des marchés : le régime de tension est une composante d'un mélange gaussien, sans "
                   "vérité terrain. Il ne remplace ni les enquêtes de terrain ni le jugement des analystes."),
        ], className="pied"),
    ])


app.layout = _gabarit


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 8060)), debug=False)
