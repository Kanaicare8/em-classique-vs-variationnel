"""Le cœur NumPy de l'outil redonne les écarts et les probabilités du mémoire (sans PyTorch).

python -m pytest bulletin/tests      (à la racine du dépôt)
"""

import sys
from pathlib import Path

import numpy as np

OUTIL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(OUTIL))

from coeur.donnees import Releves, mois_texte  # noqa: E402
from coeur.modele import Modele  # noqa: E402

MODELE = Modele("memoire")
CONTROLE = np.load(OUTIL / "modeles" / "memoire" / "controle.npz")
EXTRAIT = OUTIL.parent / "data" / "prix" / "wfp_cmr_panier.csv"


def _releves():
    e = MODELE.fiche["ecarts"]
    return Releves.depuis_extrait(EXTRAIT, MODELE.fiche["panier"], e["fenetre_mois"], e["releves_min"], e["facteur_pic"])


def test_extrait_du_memoire():
    assert _releves().sha256 == MODELE.fiche["donnees"]["sha256"]


def test_ecarts_identiques():
    obs = _releves().observations()
    assert [o[0] for o in obs] == CONTROLE["mois"].tolist()
    assert [o[1] for o in obs] == CONTROLE["marche"].tolist()
    assert np.abs(np.array([o[2] for o in obs]) - CONTROLE["X"]).max() < 1e-12


def test_probabilites_identiques():
    res = MODELE.proba(CONTROLE["X"])
    for nom, r in res.items():
        assert np.abs(r["p"] - CONTROLE[f"{nom}/proba"]).max() < 1e-6, nom
        assert np.abs(r["bas"] - CONTROLE[f"{nom}/ic"][0]).max() < 1e-6, nom
        assert np.abs(r["haut"] - CONTROLE[f"{nom}/ic"][1]).max() < 1e-6, nom


def test_releve_saisi_ne_remplace_pas_le_pam():
    r0 = _releves()
    t, m, _ = r0.observations()[0]
    c = MODELE.fiche["panier"][0]
    r = Releves.depuis_extrait(EXTRAIT, MODELE.fiche["panier"],
                               saisies=[{"marche": m, "denree": c, "mois": mois_texte(t), "prix": 1.0}])
    assert r.prix(m, c, t) == r0.prix(m, c, t) and r.source[(m, c, t)] == "PAM"
