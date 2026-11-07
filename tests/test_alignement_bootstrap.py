"""Alignement des réplicats bootstrap (D-19). Lancer : python -m pytest tests -q  (depuis la racine du dépôt)."""
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import algorithmes as A  # noqa: E402
import comparaison as C  # noqa: E402


def _melange_centres_proches(n=600, graine=0):
    """Deux composantes aux centres voisins, l'une étroite (90 %), l'autre large (10 %) : le cas du régime de tension."""
    modele = {"pi": torch.tensor([0.9, 0.1], dtype=torch.float64),
              "mu": torch.tensor([[0.0, 0.0], [0.15, 0.0]], dtype=torch.float64),
              "cov": torch.stack([0.05 * torch.eye(2, dtype=torch.float64), 1.0 * torch.eye(2, dtype=torch.float64)])}
    X, _ = C.simuler_depuis_modele(modele, n, graine)
    return X, modele


def test_alignement_permutation_retrouvee():
    """Un réplicat dont les composantes sont permutées est réaligné sur l'original."""
    X, m = _melange_centres_proches()
    perm = torch.tensor([1, 0])
    rep = {"pi": m["pi"][perm], "mu": m["mu"][perm], "cov": m["cov"][perm]}
    assert C.aligner_bootstrap(X, m, rep).tolist() == [1, 0]
    assert C.aligner_bootstrap(X, m, m).tolist() == [0, 1]


def test_bootstrap_demarrage_chaud_garde_ses_composantes():
    """
    Démarrage chaud : chaque réplicat garde les composantes de l'ajustement d'origine. L'appariement par
    responsabilités les retrouve toutes ; l'appariement sur les moyennes seules en échange une partie (défaut corrigé).
    """
    X, _ = _melange_centres_proches()
    em = A.em_classique(X, 2, n_init=5, graine=1)
    a_resp = a_moy = 0
    B = 40
    for b in range(B):
        ib = torch.randint(len(X), (len(X),), generator=A.generateur(1000 + b))
        eb = C.em_demarrage_chaud(X[ib], em)
        a_resp += C.aligner_bootstrap(X, em, eb).tolist() == [0, 1]
        a_moy += A.hongrois(torch.cdist(em["mu"], eb["mu"]).pow(2)).tolist() == [0, 1]
    assert a_resp == B
    assert a_moy < B
