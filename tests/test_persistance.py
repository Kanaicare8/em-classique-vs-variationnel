"""Points de reprise : écriture atomique, mémorisation, reprise exacte d'un ajustement interrompu, graines dérivées."""
import os
import subprocess
import sys
import textwrap

import torch

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
from emvb import algorithmes as A  # noqa: E402
from emvb import persistance as P  # noqa: E402


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
        from emvb import algorithmes as A, persistance as P
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


def test_fichier_tronque_mis_en_quarantaine(tmp_path):
    """Un fichier d'unité tronqué (coupure pendant une copie, disque plein) n'est pas compté comme fait."""
    m = P.Magasin("essai", tmp_path)
    m.ecrire("u", {"x": torch.arange(1000)})
    assert m.complete("u")
    p = m.chemin("u")
    p.write_bytes(p.read_bytes()[:-30])                    # fin d'archive arrachée
    assert not P.fichier_complet(p)
    assert not m.complete("u") and not p.exists()
    assert len(list((m.dossier / "_quarantaine").iterdir())) == 1
    assert m.cles() == []


def test_temporaires_orphelins_supprimes(tmp_path):
    m = P.Magasin("essai", tmp_path)
    m.ecrire("a", {"x": 1})
    orphelin = m.dossier / "b.pt.tmp1234"
    orphelin.write_bytes(b"partiel")
    os.utime(orphelin, (0, 0))
    assert m.nettoyer_temporaires() == 1 and not orphelin.exists() and m.complete("a")


# ------------------------------------------------------------------------------ orchestrateur : processus tué
def unite_tuee_une_fois(memo, rapide, marque):
    """Meurt brutalement au premier lancement (comme un manque de mémoire ou un plantage natif), réussit ensuite."""
    if not os.path.exists(marque):
        open(marque, "w").close()
        os._exit(9)
    return {"lignes": [{"v": 1}]}


def unite_normale(memo, rapide):
    return {"lignes": [{"v": 2}]}


def test_pool_recree_apres_processus_tue(tmp_path, monkeypatch):
    from emvb import etapes as E
    from emvb import cli as run
    monkeypatch.setenv("ICARE_MAGASIN", str(tmp_path))
    us = [E.Unite("essai", "tuee", __name__, "unite_tuee_une_fois", {"marque": str(tmp_path / "marque")}),
          E.Unite("essai", "normale", __name__, "unite_normale")]
    monkeypatch.setattr(run, "unites_de", lambda etape, rapide: us)
    monkeypatch.setitem(run.MODULES, "essai", __name__)
    assert run.executer_etape("essai", True, travailleurs=2, tentatives=3)
    assert sorted(l["v"] for l in E.lignes("essai", True)) == [1, 2]
    assert "BrokenProcessPool" in (tmp_path / "magasin_rapide" / "_journal" / "erreurs.log").read_text(encoding="utf-8")


def agreger(rapide):
    pass


def test_ecriture_atomique_resiste_au_verrou_passager(tmp_path):
    """Sous Windows, os.replace est refusé tant qu'un lecteur (superviseur, antivirus) tient le fichier ouvert :
    l'écriture attend que le verrou se lève ; un battement bloqué en permanence est sauté sans arrêter le calcul."""
    import threading
    import time as _t
    cible = tmp_path / "_battement.json"
    cible.write_text("{}", encoding="utf-8")
    h = open(cible, "rb")                                   # verrou de lecture, comme le superviseur
    threading.Timer(0.3, h.close).start()                  # levé après 0,3 s
    P._ecrire_atomique(cible, lambda f: f.write(b'{"ok": 1}'))
    assert cible.read_text(encoding="utf-8") == '{"ok": 1}'
    with open(cible, "rb"):                                # verrou permanent pendant le battement
        t0 = _t.time()
        P.battement(tmp_path, actif=True)                  # ne lève pas
        assert _t.time() - t0 < 5
    assert not list(tmp_path.glob("*.tmp*"))               # aucun fichier temporaire orphelin
