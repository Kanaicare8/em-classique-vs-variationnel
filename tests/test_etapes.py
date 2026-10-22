"""Tests rapides de l'orchestration : unités bien formées, dépendances résolubles, règles de calibrage."""

import math
import os
import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["ICARE_RAPIDE"] = "1"

import calibrage as K  # noqa: E402
import etapes as E  # noqa: E402
import run  # noqa: E402

ETAPES_SANS_DONNEES_EXTERNES = ["validation", "illustrations", "scenarios", "chronometrage", "calibrage"]


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


def test_var_es_student_formule_fermee():
    import etape_sp500 as SP
    q, es = SP._student_var_es(0.05, 0.0, 1.0, 5.0)
    assert abs(q - (-2.015048)) < 1e-5                       # quantile tabulé de t_5 à 5 %
    with torch.random.fork_rng():
        torch.manual_seed(0)
        x = torch.distributions.StudentT(5.0).sample((2_000_000,)).double()
    assert abs(es - float(x[x <= q].mean())) < 0.01


def test_memo_reprise(tmp_path, monkeypatch):
    monkeypatch.setattr(E, "racine_magasin", lambda rapide: tmp_path)
    appels = []
    u = E.Unite("essai", "u1", "tests.test_etapes", "_unite_jouet")
    E.executer_unite(u, True)
    E.executer_unite(u, True)                                 # déjà faite : rien n'est recalculé
    assert E.magasin("essai", True).lire("u1")["lignes"] == [{"v": 1}]


def _unite_jouet(memo, rapide):
    a = memo("a", lambda: {"v": 1})
    return {"lignes": [a]}
