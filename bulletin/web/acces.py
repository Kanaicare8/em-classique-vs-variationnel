"""Session et droits : l'utilisateur connecté (cookie signé de Flask) et le contrôle des rôles dans les pages."""

from __future__ import annotations

from flask import has_request_context, session

import base as B

DROITS = {
    "consulter": {"admin", "analyste", "agent"},
    "saisir": {"admin", "analyste", "agent"},
    "valider": {"admin", "analyste"},
    "administrer": {"admin"},
}


def utilisateur():
    """Compte connecté (détaché de la session SQLAlchemy) ou None."""
    if not has_request_context() or "uid" not in session:
        return None
    with B.session() as s:
        u = s.get(B.Utilisateur, session["uid"])
        return u if u is not None and u.actif else None


def peut(droit: str, u=None) -> bool:
    u = u or utilisateur()
    return u is not None and u.role in DROITS[droit]
