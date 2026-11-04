"""Tests rapides de l'orchestration : unités bien formées, dépendances résolubles, règles de calibrage."""

import math
import os
import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import calibrage as K  # noqa: E402
import etapes as E  # noqa: E402
import run  # noqa: E402


@pytest.fixture(autouse=True, scope="module")
def mode_rapide():
    """ICARE_RAPIDE=1 pour les seuls tests de ce fichier (auparavant fixé au chargement, il fuyait dans les fichiers de
    tests suivants)."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("ICARE_RAPIDE", "1")
        yield

ETAPES_SANS_DONNEES_EXTERNES = ["validation", "illustrations", "scenarios", "chronometrage", "prix", "calibrage"]


@pytest.mark.parametrize("etape", ETAPES_SANS_DONNEES_EXTERNES)
@pytest.mark.parametrize("rapide", [True, False])
def test_unites_bien_formees(etape, rapide):
    us = run.unites_de(etape, rapide)
    cles = [u.cle for u in us]
    assert len(cles) == len(set(cles)), "clés d'unités en double"
    connues = set(cles)
    for u in us:
        assert u.etape == etape
        assert all(d in connues for d in u.depend), (u.cle, u.depend)
        assert callable(getattr(__import__(u.module), u.fonction))


def test_graphe_calibrage_sans_cycle():
    us = {u.cle: u for u in K.unites(False)}
    etat = {}

    def visiter(c):
        if etat.get(c) == 1:
            raise AssertionError(f"cycle via {c}")
        if etat.get(c) == 2:
            return
        etat[c] = 1
        for d in us[c].depend:
            visiter(d)
        etat[c] = 2
    for c in us:
        visiter(c)


def test_n_requis():
    assert K._n_requis(1.0, 200) == 1
    assert K._n_requis(0.0, 200) == 200
    assert K._n_requis(0.5, 200) == math.ceil(math.log(0.01) / math.log(0.5))      # 7
    assert K._n_requis(0.01, 200) == 200                                             # plafonné


def test_divisions_successives_trouve_le_maximum():
    configs = [{"x": float(i)} for i in range(16)]
    vu = {}

    def memo(cle, f):
        if cle not in vu:
            vu[cle] = f()
        return vu[cle]
    best, evals = K.divisions_successives(memo, configs, 8, lambda c, t: -(c["x"] - 11.0) ** 2 + 0.01 * t)
    assert best["x"] == 11.0
    assert max(e["etape"] for e in evals) >= 3
    assert len([e for e in evals if e["etape"] == 0]) == 16


def test_configurations_dans_l_espace():
    import parametres as PARAM
    esp = PARAM.valeur("espace_priors")
    cfg = K._configs_aleatoires(64, 3, 6)
    assert cfg[0] == {"alpha0": 1 / 6, "beta0": 1.0, "nu0_plus": 0.0, "echelle_w0": 1.0}
    for c in cfg[1:]:
        for k, (lo, hi) in esp.items():
            assert lo <= c[k] <= hi


def test_prix_regime_tension_et_couverture():
    import etape_prix as P
    info = {"centre": torch.zeros(3, dtype=torch.float64), "echelle": torch.ones(3, dtype=torch.float64)}
    mu = torch.tensor([[0.0, 0.0, 0.0], [2.0, 1.0, 1.0], [5.0, 5.0, 5.0]], dtype=torch.float64)
    assert P.regime_tension(mu, torch.tensor([True, True, False]), info) == 1          # composante inactive ignorée
    ref = {"pi": torch.tensor([0.5, 0.5], dtype=torch.float64),
           "mu": torch.tensor([[0.0, 0.0], [10.0, 10.0]], dtype=torch.float64)}
    out = P.couverts(ref, torch.tensor([0.4]), torch.tensor([0.6]), torch.tensor([[-1.0, 0.5]]), torch.tensor([[1.0, 2.0]]),
                     torch.tensor([[0.0, 1.0]], dtype=torch.float64), torch.tensor([0]))
    assert out == [(0, 1.0, [1.0, 0.0]), (1, 0.0, [0.0, 0.0])]                       # vraie composante 2 non appariée
    assert len(P.lignes_couverture(120, 3, "VB", out)) == 2 * (1 + 2)


def test_prix_dm_par_mois():
    import etape_prix as P
    mois = torch.tensor([0, 0, 1, 1, 2, 2, 3, 3])
    ls = {"Gaussienne": torch.zeros(8, dtype=torch.float64),
          "EM-BIC (plug-in)": torch.tensor([1.0, 1.2, 0.9, 1.1, 1.0, 0.8, 1.3, 1.1], dtype=torch.float64)}
    dm = P.diebold_mariano({"mois_test": mois, "logscores": ls}, 0.05)
    assert len(dm) == 1 and dm[0]["n_mois"] == 4 and dm[0]["decision"] == "A > B"


def test_memo_reprise(tmp_path, monkeypatch):
    monkeypatch.setattr(E, "racine_magasin", lambda rapide: tmp_path)
    appels = []
    u = E.Unite("essai", "u1", __name__, "_unite_jouet")      # nom réel du module (pytest l'importe sans paquet)
    E.executer_unite(u, True)
    E.executer_unite(u, True)                                 # déjà faite : rien n'est recalculé
    assert E.magasin("essai", True).lire("u1")["lignes"] == [{"v": 1}]


def _unite_jouet(memo, rapide):
    a = memo("a", lambda: {"v": 1})
    return {"lignes": [a]}
