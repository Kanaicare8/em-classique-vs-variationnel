"""Décision D-15 : tolérance jugée sur le critère (arrêt si aucune), relances fixes et leur probabilité, étape E de la LDA plafonnée."""

import math
import sys
from itertools import combinations
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import algorithmes as A  # noqa: E402
import calibrage as C  # noqa: E402


def test_proba_meilleur_exacte():
    assert C.proba_meilleur(200, 0, 20) == 0.0
    assert C.proba_meilleur(10, 3, 10) == 1.0
    assert math.isclose(C.proba_meilleur(200, 1, 20), 0.1)              # une seule bonne relance : n / m
    m, a, n = 7, 2, 3                                                    # dénombrement direct
    ok = sum(any(i < a for i in t) for t in combinations(range(m), n))
    assert math.isclose(C.proba_meilleur(m, a, n), ok / math.comb(m, n))


def _lignes(parts_critere, ari=0.5):
    """Dix ajustements par tolérance ; parts_critere[tol] d'entre eux s'accordent sur le critère, aucun sur l'ARI."""
    out = []
    for tol in C.GRILLE_TOL:
        k = round(10 * parts_critere.get(tol, 0.0))
        for i in range(10):
            out.append({"tol": tol, "ecart_par_obs": 0.0 if i < k else 1.0, "ARI_reference": ari, "n_iter": 150 + i})
    return out


def test_fin_tolerance_critere_seul(monkeypatch):
    ecrit = {}
    monkeypatch.setattr(C.E, "lignes", lambda *a, **k: _lignes({1e-8: 1.0, 1e-9: 1.0}))
    monkeypatch.setattr(C, "_ecrire", lambda ident, val, regle, det: ecrit.update(val=val, det=det))
    C.fin_tolerance(None, False)
    assert ecrit["val"] == {"tol_rel": 1e-8, "n_iter_max": 200}          # ARI à 0,5 partout : il ne décide plus
    assert ecrit["det"]["part_accord_critere_et_ARI_par_tol"]["1e-08"] == 0.0


def test_fin_tolerance_arret_sans_repli(monkeypatch):
    monkeypatch.setattr(C.E, "lignes", lambda *a, **k: _lignes({1e-9: 0.9}))
    monkeypatch.setattr(C, "_ecrire", lambda *a: pytest.fail("aucune tolérance ne doit être écrite"))
    with pytest.raises(RuntimeError):
        C.fin_tolerance(None, False)


def test_lda_etape_e_plafonnee(monkeypatch):
    g = torch.Generator().manual_seed(5)
    c = torch.poisson(torch.rand(20, 30, generator=g, dtype=torch.float64) * 3)
    libre = A.lda_variationnel(c, 3, n_iter=5, tol=1e-12, graine=1)
    assert 0 <= libre["etapes_e_plafonnees"] <= len(libre["bornes"])
    valeur = A.PARAM.valeur
    monkeypatch.setattr(A.PARAM, "valeur", lambda nom: 1 if nom == "lda_iter_e" else valeur(nom))
    r = A.lda_variationnel(c, 3, n_iter=5, tol=1e-12, graine=1)
    assert r["etapes_e_plafonnees"] == len(r["bornes"])                  # une seule itération : jamais convergée
