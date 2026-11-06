"""Sous-tâches des relances du texte (D-17) : résultats identiques bit à bit, jamais hors de l'étape texte, processus <= coeurs."""

import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import etape_texte as T  # noqa: E402
import etapes as E  # noqa: E402
import run  # noqa: E402

V, N, CLE = 30, 20, "V=30/N=20/rep=000"


@pytest.fixture(autouse=True)
def un_fil():
    """Comme etapes.executer_unite : un fil d'exécution par processus."""
    avant = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(avant)


def _corpus():
    g = torch.Generator().manual_seed(5)
    perm = torch.randperm(60, generator=g)
    return {"lignes": [], "artefacts": {"comptes": torch.poisson(torch.rand(60, V, generator=g) * 3, generator=g).float(),
                                        "y": torch.arange(60) % T.K, "vocab": [f"m{i}" for i in range(V)],
                                        "test": perm[:20], "reservoir": perm[20:]}}


def _unite(monkeypatch, racine, sous, etape="texte"):
    monkeypatch.setenv("ICARE_MAGASIN", str(racine))
    monkeypatch.delenv("ICARE_RAPIDE", raising=False)
    if sous:
        monkeypatch.setenv("ICARE_SOUS_TRAVAILLEURS", str(sous))
    else:
        monkeypatch.delenv("ICARE_SOUS_TRAVAILLEURS", raising=False)
    mag = E.magasin(etape, False)
    mag.ecrire(f"corpus/V={V}", _corpus())
    return T.unite_echantillon(E.Memo(mag, CLE), False, V, N, 0, etape_corpus=etape), mag


def _relances(mag, algo):
    d = mag.dossier / CLE / "_sous" / algo / "relances"
    return {p.stem: torch.load(p, weights_only=True)["c"] for p in d.glob("s=*.pt")}


def test_identique_bit_a_bit(tmp_path, monkeypatch):
    ref, m0 = _unite(monkeypatch, tmp_path / "sans", 0)
    res, m1 = _unite(monkeypatch, tmp_path / "avec", 2)
    assert repr(res["lignes"]) == repr(ref["lignes"])
    assert ref["artefacts"].keys() == res["artefacts"].keys()
    for k in ref["artefacts"]:
        assert torch.equal(ref["artefacts"][k], res["artefacts"][k]), k
    for algo in ("pLSA", "LDA"):
        assert _relances(m0, algo) == _relances(m1, algo) != {}


@pytest.mark.parametrize("etape,sous", [("calibrage", 2), ("chronometrage", 2), ("texte", 0), ("texte", 1)])
def test_sans_sous_processus(tmp_path, monkeypatch, etape, sous):
    def interdit(*a, **k):
        raise AssertionError("sous-tâches lancées")
    monkeypatch.setattr(E, "sous_taches_paralleles", interdit)
    _unite(monkeypatch, tmp_path, sous, etape)


@pytest.mark.parametrize("travailleurs,sous,attendu",
                         [(31, 2, 16), (31, 3, 10), (31, 32, 1), (6, 2, 6), (31, None, 31), (31, 1, 31)])
def test_processus_pas_plus_que_coeurs(monkeypatch, travailleurs, sous, attendu):
    if sous is None:
        monkeypatch.delenv("ICARE_SOUS_TRAVAILLEURS", raising=False)
    else:
        monkeypatch.setenv("ICARE_SOUS_TRAVAILLEURS", str(sous))
    assert run._travailleurs_texte(travailleurs, 32) == attendu


def test_trop_de_sous_taches_refuse(monkeypatch):
    monkeypatch.setenv("ICARE_SOUS_TRAVAILLEURS", "33")
    with pytest.raises(ValueError):
        run._travailleurs_texte(31, 32)
