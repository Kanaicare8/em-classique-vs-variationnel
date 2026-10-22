"""Points de reprise : écriture atomique, mémorisation, reprise exacte d'un ajustement interrompu, graines dérivées."""
import os
import subprocess
import sys
import textwrap

import torch

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
import algorithmes as A  # noqa: E402
import persistance as P  # noqa: E402


def test_graines_independantes_et_stables():
    assert P.graine("S1", "donnees", 3) == P.graine("S1", "donnees", 3)
    assert P.graine("S1", "donnees", 3) != P.graine("S1", "ajustement", 3)
    assert 0 <= P.graine("x") < 2 ** 62


def test_magasin_memo(tmp_path):
    m = P.Magasin("essai", tmp_path)
    appels = []

    def f(x):
        appels.append(x)
        return {"t": torch.arange(3) * x, "s": "ok", "l": [1, 2.5, None]}

    a = m.memo("u/1", f, 2)
    b = m.memo("u/1", f, 2)
    assert appels == [2] and torch.equal(a["t"], b["t"]) and b["s"] == "ok"
    assert m.cles() == ["u/1"]


def test_pas_de_fichier_partiel(tmp_path):
    m = P.Magasin("essai", tmp_path)
    m.ecrire("a", {"x": torch.zeros(10)})
    assert not any(p.name.endswith(tuple(f".tmp{i}" for i in range(100000))) for p in tmp_path.rglob("*"))


def test_reprise_exacte_apres_interruption_brutale(tmp_path):
    """Un processus est tué en plein ajustement ; un second processus reprend depuis l'instantané et donne
    exactement le même résultat qu'un ajustement ininterrompu."""
    X, _ = A.jeu_reference(42)
    ref = A.em_classique(X, 6, init="aleatoire", graine=1, n_init=4)
    script = textwrap.dedent(f"""
        import sys, os
        sys.path.insert(0, {RACINE!r})
        import algorithmes as A, persistance as P
        class Coupe(P.Instantane):
            def ecrire(self, e):
                super().ecrire(e)
                if e["t"] >= 40:
                    os._exit(3)          # mort brutale, sans nettoyage
        X, _ = A.jeu_reference(42)
        inst = Coupe({str(tmp_path / 'inst.pt')!r}, tous=10)
        A.em_classique(X, 6, init="aleatoire", graine=1, n_init=4, instantane=inst)
    """)
    code = subprocess.run([sys.executable, "-c", script]).returncode
    assert code == 3
    inst = P.Instantane(tmp_path / "inst.pt", tous=10)
    assert inst.lire()["t"] == 40
    repris = A.em_classique(X, 6, init="aleatoire", graine=1, n_init=4, instantane=inst)
    assert repris["n_iter"] == ref["n_iter"]
    assert repris["loglik"] == ref["loglik"]
    assert torch.equal(repris["mu"], ref["mu"])
