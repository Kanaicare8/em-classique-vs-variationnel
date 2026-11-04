"""Relances mémorisées une à une (etape_texte._meilleur) : même ajustement qu'en une seule boucle, avec ou sans reprise."""

import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import algorithmes as A  # noqa: E402
import etape_texte as T  # noqa: E402
import etapes as E  # noqa: E402
import persistance as PE  # noqa: E402


def _comptes():
    g = torch.Generator().manual_seed(3)
    return torch.poisson(torch.rand(30, 40, generator=g, dtype=torch.float64) * 3)


def _f(c):
    return lambda graine: A.plsa_em(c, 3, n_iter=40, tol=1e-8, graine=graine)


def _identiques(a, b):
    return all(torch.equal(a[k], b[k]) for k in ("theta", "phi")) and a["ll_hist"] == b["ll_hist"]


def test_meilleur_memorise_identique(tmp_path):
    c = _comptes()
    ref = T._meilleur(_f(c), 6, 100)
    memo = E.Memo(PE.Magasin("texte", tmp_path), "unite")
    assert _identiques(T._meilleur(_f(c), 6, 100, memo, "pLSA"), ref)          # premier passage, sans interruption
    assert _identiques(T._meilleur(_f(c), 6, 100, memo, "pLSA"), ref)          # tout relu : meilleure réajustée


def test_meilleur_reprise_partielle(tmp_path):
    c = _comptes()
    ref = T._meilleur(_f(c), 6, 100)
    memo = E.Memo(PE.Magasin("texte", tmp_path), "unite")
    T._meilleur(_f(c), 3, 100, memo, "pLSA")                                   # arrêt après 3 relances
    assert _identiques(T._meilleur(_f(c), 6, 100, memo, "pLSA"), ref)


def test_meilleur_egalite_garde_la_premiere(tmp_path):
    vus = []

    def f(graine):
        vus.append(graine)
        return {"bornes": [1.0 if graine in (11, 13) else 0.0], "graine": graine}
    memo = E.Memo(PE.Magasin("texte", tmp_path), "unite")
    assert T._meilleur(f, 4, 10)["graine"] == 11
    assert T._meilleur(f, 4, 10, memo, "LDA")["graine"] == 11
    vus.clear()
    assert T._meilleur(f, 4, 10, memo, "LDA")["graine"] == 11 and vus == [11]  # relu : seule la meilleure est refaite
