"""
Calculs de l'outil, mis en cache : relevés (extrait actif + relevés saisis validés), écarts, probabilités par modèle.

Extrait actif : le dernier extrait du PAM activé dans l'administration ; à défaut, celui du mémoire
(OUTIL_EXTRAIT, par défaut data/prix/wfp_cmr_panier.csv du dépôt).
"""

from __future__ import annotations

import math
import os
import sys
import threading
from pathlib import Path

import numpy as np

OUTIL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(OUTIL))

import base as B  # noqa: E402
from coeur.donnees import Releves, mois_index, mois_texte  # noqa: E402
from coeur.modele import Modele, versions  # noqa: E402

EXTRAIT_DEFAUT = Path(os.environ.get("OUTIL_EXTRAIT", OUTIL.parent / "data" / "prix" / "wfp_cmr_panier.csv"))
REFERENCE = "memoire"
SEUIL = 0.5

# Épisodes datés par les bulletins (repris du mémoire : donnees.EPISODES_PRIX), pour la page « Fiabilité »
EPISODES = (
    {"mois": "2023-08", "region": "Extrême-Nord", "marches": (), "sens": "hausse",
     "texte": "août 2023 : maïs +24 % en un mois dans l'Extrême-Nord (PAM, 2023)"},
    {"mois": "2026-04", "region": "Extrême-Nord", "marches": ("Kousseri", "Mokolo", "Mora"), "sens": "baisse",
     "texte": "avril 2026 : maïs et sorgho 40 à 50 % moins chers qu'un an plus tôt à Kousseri, Mokolo, Mora (FEWS NET, 2026)"},
)

_verrou = threading.Lock()
_modeles: dict = {}
_cache: dict = {"cle": None, "valeur": None}


def modele(version: str = REFERENCE) -> Modele:
    if version not in _modeles:
        _modeles[version] = Modele(version)
    return _modeles[version]


def liste_versions():
    return versions()


def _extrait():
    e = B.extrait_actif()
    if e is not None:
        return e.contenu, {"origine": e.origine, "sha256": e.sha256, "debut": e.debut, "fin": e.fin,
                           "charge_le": e.charge_le.strftime("%Y-%m-%d"), "memoire": False}
    brut = EXTRAIT_DEFAUT.read_bytes()
    return brut, {"origine": "extrait du mémoire (27/10/2026)", "sha256": None, "memoire": True}


def etat(version: str = REFERENCE) -> dict:
    """Relevés, observations et probabilités de toutes les observations pour un modèle ; recalculé si l'extrait actif,
    les relevés validés ou le modèle changent."""
    e = B.extrait_actif()
    cle = (version, e.sha256 if e else "defaut", B.empreinte_releves())
    with _verrou:
        if _cache["cle"] == cle:
            return _cache["valeur"]
        m = modele(version)
        brut, info = _extrait()
        r = m.fiche["ecarts"]
        rel = Releves.depuis_octets(brut, m.fiche["panier"], r["fenetre_mois"], r["releves_min"], r["facteur_pic"],
                                    saisies=B.releves_valides())
        info["sha256"] = rel.sha256
        obs = rel.observations()
        X = np.array([o[2] for o in obs]) if obs else np.zeros((0, 3))
        proba = m.proba(X) if len(X) else {}
        valeur = {"modele": m, "releves": rel, "extrait": info, "mois": [o[0] for o in obs],
                  "marche": [o[1] for o in obs], "X": X, "proba": proba,
                  "fin_apprentissage": mois_index(m.fiche["apprentissage"]["fin"])}
        _cache.update(cle=cle, valeur=valeur)
        return valeur


# ------------------------------------------------------------------------------ vocabulaire et lecture
# Les méthodes du mémoire, nommées pour un lecteur non spécialiste (le nom technique reste entre parenthèses)
METHODES = {"EM-BIC": "Méthode classique (EM-BIC)", "VB-emp": "Méthode bayésienne (VB)"}
METHODES_COURT = {"EM-BIC": "Classique", "VB-emp": "Bayésienne"}
MODES = {"accord": "Prudente : les deux méthodes", "EM-BIC": "Méthode classique", "VB-emp": "Méthode bayésienne"}

# État d'un marché : (libellé, couleur du badge, en alerte ?, à surveiller ?, explication)
ETATS = {
    "alerte": ("Alerte", "rouge", True, False, "probabilité de tension au-dessus de 50 %, fourchette comprise"),
    "alerte_probable": ("Alerte probable", "orange", True, False,
                        "probabilité au-dessus de 50 %, mais la fourchette descend sous 50 %"),
    "surveiller": ("À surveiller", "ambre", False, True,
                   "probabilité sous 50 %, mais la fourchette monte au-dessus de 50 %"),
    "desaccord": ("Méthodes en désaccord", "ambre", False, True, "une méthode voit une tension, l'autre non"),
    "calme": ("Calme", "vert", False, False, "probabilité et fourchette sous 50 %"),
}


def lecture(p, bas, haut):
    """Code d'état d'une probabilité et de son intervalle à 90 % (clé de ETATS)."""
    if p > SEUIL:
        return "alerte" if bas > SEUIL else "alerte_probable"
    return "surveiller" if haut >= SEUIL else "calme"


def evaluation(st, mode, i):
    """(p, bas, haut, état) de l'observation i ; mode = une méthode, ou « accord » : alerte si les deux méthodes la
    donnent, désaccord si une seule ; P et fourchette affichés sont alors les plus prudents des deux."""
    if mode != "accord":
        r = st["proba"][mode]
        p, bas, haut = float(r["p"][i]), float(r["bas"][i]), float(r["haut"][i])
        return p, bas, haut, lecture(p, bas, haut)
    ev = [evaluation(st, b, i) for b in st["proba"]]
    hauts = [e[0] > SEUIL for e in ev]
    etat = "alerte" if all(hauts) else "desaccord" if any(hauts) else \
        ("surveiller" if any(e[3] == "surveiller" for e in ev) else "calme")
    return min(e[0] for e in ev), min(e[1] for e in ev), max(e[2] for e in ev), etat


def en_alerte(etat):
    return ETATS[etat][2]


def a_surveiller(etat):
    return ETATS[etat][3]


MOIS_FR = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre",
           "décembre")


MOIS_COURT = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc.")


def mois_humain(t, court=False):
    return f"{(MOIS_COURT if court else MOIS_FR)[t % 12]} {t // 12}"


def evaluer_releve(version, marche, t, prix: dict):
    """Relevé hypothétique ({denrée : XAF/kg}) : (écarts, niveaux, {bras : p, bas, haut} ou None). Le relevé n'est pas
    enregistré ; les niveaux viennent des relevés connus (extrait + relevés validés) des douze mois précédents."""
    st = etat(version)
    rel, m = st["releves"], st["modele"]
    niveaux = {c: rel.niveau(marche, c, t) for c in m.fiche["panier"]}
    ecarts = [math.log(prix[c]) - math.log(niveaux[c][0]) if prix.get(c) and niveaux[c][0] else None
              for c in m.fiche["panier"]]
    if any(e is None for e in ecarts):
        return ecarts, niveaux, None
    res = m.proba(np.array([ecarts]))
    return ecarts, niveaux, {b: {k: float(v[0]) for k, v in r.items()} for b, r in res.items()}


def marches_connus(st):
    return sorted(st["releves"].marches.values(), key=lambda m: (m.region, m.nom))


def mois_disponibles(st):
    return sorted(set(st["mois"]), reverse=True)


__all__ = ["etat", "evaluation", "evaluer_releve", "lecture", "mois_index", "mois_texte", "modele", "liste_versions"]
