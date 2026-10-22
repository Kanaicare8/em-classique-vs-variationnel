"""
Équivalence du noyau tensoriel par lots avec l'implémentation séquentielle figée
(tests/algorithmes_reference.py) : mêmes relances, mêmes nombres d'itérations, mêmes paramètres
à la précision numérique près. Tout écart signalerait que la vectorisation a changé l'algorithme.
"""
import importlib.util
import os
import sys

import pytest
import torch

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
import algorithmes as A  # noqa: E402

spec = importlib.util.spec_from_file_location("ref", os.path.join(RACINE, "tests", "algorithmes_reference.py"))
REF = importlib.util.module_from_spec(spec)
sys.modules["ref"] = REF            # requis par les dataclasses
spec.loader.exec_module(REF)

TOL = 1e-7


@pytest.fixture(scope="module")
def jeu():
    return A.jeu_reference(42)[0]


def ordonner(res, cle_mu="mu"):
    """Réordonne les composantes (label switching) par abscisse puis ordonnée du centre."""
    mu = res[cle_mu]
    o = torch.argsort(mu[:, 0] * 1e6 + mu[:, 1])
    return o


def proche(a, b, tol=TOL):
    return torch.allclose(a, b, rtol=tol, atol=tol)


def test_kmeans_identique(jeu):
    for g in (0, 3, 11):
        e1, c1 = A.kmeans(jeu, 6, g)
        e2, c2 = REF.kmeans(jeu, 6, g)
        assert torch.equal(e1, e2) and proche(c1, c2, 1e-10)


@pytest.mark.parametrize("cov_type", ["full", "tied", "diag", "spherical"])
@pytest.mark.parametrize("init", ["kmeans", "aleatoire"])
def test_em_equivalent(jeu, cov_type, init):
    a = A.em_classique(jeu, 5, cov_type=cov_type, init=init, graine=3, n_init=4)
    b = REF.em_classique(jeu, 5, cov_type=cov_type, init=init, graine=3, n_init=4)
    assert a["n_iter"] == b["n_iter"] and a["converge"] == b["converge"]
    assert abs(a["loglik"] - b["loglik"]) < 1e-8 * abs(b["loglik"])
    oa, ob = ordonner(a), ordonner(b)
    assert proche(a["pi"][oa], b["pi"][ob]) and proche(a["mu"][oa], b["mu"][ob]) and proche(a["cov"][oa], b["cov"][ob])
    assert abs(a["bic"] - b["bic"]) < 1e-5 and abs(a["icl"] - b["icl"]) < 1e-5
    assert len(a["ll_hist"]) == len(b["ll_hist"])


@pytest.mark.parametrize("cov_type", ["full", "tied", "diag", "spherical"])
@pytest.mark.parametrize("init", ["kmeans", "prior"])
def test_vb_equivalent(jeu, cov_type, init):
    a = A.em_variationnel(jeu, 6, alpha0=1 / 6, cov_type=cov_type, init=init, graine=2, n_init=4)
    b = REF.em_variationnel(jeu, 6, alpha0=1 / 6, cov_type=cov_type, init=init, graine=2, n_init=4)
    assert a["n_iter"] == b["n_iter"] and a["converge"] == b["converge"]
    assert abs(a["crit"] - b["crit"]) < 1e-7 * abs(b["crit"])
    oa, ob = ordonner(a, "m"), ordonner(b, "m")
    assert proche(a["alpha"][oa], b["alpha"][ob], 1e-6) and proche(a["m"][oa], b["m"][ob], 1e-6)
    assert a["n_actives"] == b["n_actives"]
    assert proche(a["cov"][oa], b["cov"][ob], 1e-5)


def test_map_em_equivalent(jeu):
    pr = A.priori_empirique(jeu, 2.0)
    pr = A.PrioriNW(2.0, pr.m0, pr.beta0, pr.W0inv, pr.nu0)
    a = A.map_em(jeu, 6, pr, graine=1, n_init=3)
    b = REF.map_em(jeu, 6, pr, graine=1, n_init=3)
    assert a["n_iter"] == b["n_iter"]
    assert abs(a["loglik"] - b["loglik"]) < 1e-8 * abs(b["loglik"])
    assert abs(a["log_posteriori"] - b["log_posteriori"]) < 1e-6 * abs(b["log_posteriori"])


def test_relance_en_echec_est_exclue(jeu):
    """Une relance dont la covariance n'est pas définie positive est marquée en échec ; les autres sont intactes."""
    pi = torch.full((3, 2), 0.5)
    mu = jeu[:2].expand(3, 2, 2).clone()
    cov = torch.eye(2).expand(3, 2, 2, 2).clone()
    cov[1, 0] = torch.tensor([[1.0, 2.0], [2.0, 1.0]])           # valeurs propres 3 et -1 : non définie positive
    r, ln, ok = A._etape_e_lot(A._Prep(jeu, centrer=False), pi, mu, cov)
    assert ok.tolist() == [True, False, True]
    assert torch.isfinite(ln[0]).all() and torch.equal(ln[0], ln[2])
    with pytest.raises(A.EchecNumerique):
        A._etape_e(jeu, pi[1], mu[1], cov[1])


def test_instantane_reprise_exacte(jeu, tmp_path):
    """Interrompre la boucle puis la reprendre depuis l'instantané redonne exactement le même résultat."""
    class Inst:
        tous = 5

        def __init__(self):
            self.etat = None
            self.n = 0

        def lire(self):
            return self.etat

        def ecrire(self, e):
            self.n += 1
            self.etat = {k: (v.clone() if torch.is_tensor(v) else (dict((a, b.clone() if torch.is_tensor(b) else b) for a, b in v.items()) if isinstance(v, dict) else v)) for k, v in e.items()}

    complet = A.em_classique(jeu, 6, init="aleatoire", graine=1, n_init=3)
    inst = Inst()
    A.em_classique(jeu, 6, init="aleatoire", graine=1, n_init=3, instantane=inst)
    assert inst.n >= 1
    # simule une interruption : repart de l'état sauvegardé en cours de route
    inst.etat["t"] = inst.etat["t"]
    repris = A.em_classique(jeu, 6, init="aleatoire", graine=1, n_init=3, instantane=inst)
    assert repris["n_iter"] == complet["n_iter"] and proche(repris["mu"], complet["mu"], 1e-12)
    assert repris["loglik"] == pytest.approx(complet["loglik"], rel=1e-12)
