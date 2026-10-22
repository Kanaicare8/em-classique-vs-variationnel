"""Tests unitaires (T1.1 à T1.10). Lancer : python -m pytest tests -q  (depuis la racine du dépôt)."""
import math
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import algorithmes as A  # noqa: E402
import risque as R  # noqa: E402


def test_t11_criterie_commun_meme_tolerance():
    """EM et VB arrêtés avec la même tolérance relative sur le jeu de référence ; décompte cohérent."""
    X, _ = A.jeu_reference(42)
    em = A.em_classique(X, 3, graine=0)
    vb = A.em_variationnel(X, 3, alpha0=1 / 3, graine=0)
    for res, hist in ((em, em["ll_hist"]), (vb, vb["hist"])):
        assert res["converge"]
        assert len(hist) == res["n_iter"] + 1
        assert A.a_converge(hist[-2], hist[-1], float(A.PARAM.valeur('tol_rel')))
        assert not A.a_converge(hist[-3], hist[-2], float(A.PARAM.valeur('tol_rel'))) or res["n_iter"] < 2


def test_t11_plafond_non_converge():
    X, _ = A.jeu_reference(42)
    em = A.em_classique(X, 6, n_iter=2, init="aleatoire")
    assert em["n_iter"] == 2 and not em["converge"]


def test_elbo_monotone_covariance_pleine():
    X, _ = A.jeu_reference(42)
    vb = A.em_variationnel(X, 6, alpha0=1 / 6, graine=1)
    h = torch.tensor(vb["elbo_hist"])
    assert bool((h[1:] >= h[:-1] - 1e-8).all())
    assert vb["critere_nom"] == "elbo"
    assert A.em_variationnel(X, 3, alpha0=1 / 3, cov_type="diag")["critere_nom"] == "approximation_log_norm"


def test_loglik_em_monotone():
    X, _ = A.jeu_reference(42)
    h = torch.tensor(A.em_classique(X, 6, init="aleatoire", graine=3)["ll_hist"])
    assert bool((h[1:] >= h[:-1] - 1e-8).all())


def test_t12_prior_plat_redonne_em():
    X, _ = A.jeu_reference(42)
    em = A.em_classique(X, 3, graine=0)
    mp = A.map_em(X, 3, A.priori_plat(2), graine=0)
    assert abs(em["loglik"] - mp["loglik"]) < 1e-6 * abs(em["loglik"])
    assert torch.allclose(em["mu"], mp["mu"], atol=1e-4)


def test_t12_log_posteriori_monotone():
    X, _ = A.jeu_reference(42)
    pr = A.priori_empirique(X, 2.0)
    pr = A.PrioriNW(2.0, pr.m0, pr.beta0, pr.W0inv, pr.nu0)
    N, D = X.shape
    pi, mu, cov = A._init_em(X, 4, "full", "kmeans", 0, 0.0)
    lp = []
    for _ in range(25):
        r, ln = A._etape_e(X, pi, mu, cov)
        lp.append(float(ln.sum()) + A.log_priori_nw(pi, mu, cov, pr))
        pi, mu, cov = A._etape_m_map(X, r, pr, 0.0)
    d = torch.tensor(lp)
    assert bool((d[1:] >= d[:-1] - 1e-8).all())


def test_t13_icl_choisit_3_groupes():
    X, _ = A.jeu_reference(42)
    icls = {K: A.em_classique(X, K, n_init=5, graine=0)["icl"] for K in range(1, 7)}
    assert min(icls, key=icls.get) == 3
    res = A.em_classique(X, 3)
    assert abs(res["icl"] - (res["bic"] + 2 * res["entropie"])) < 1e-9
    assert res["entropie"] >= 0


def test_t14_degenerescence():
    """Deux indicateurs : petite composante (1 <= N_k < D + 1) et effondrement sur le plancher de régularisation."""
    cov = torch.stack([torch.eye(2), torch.diag(torch.tensor([1.0, 1.5e-6]))])
    petite, plancher = A.indicateurs_degenerescence(cov, torch.tensor([50.0, 50.0]), 2, reg=1e-6)
    assert petite.tolist() == [False, False] and plancher.tolist() == [False, True]
    petite, _ = A.indicateurs_degenerescence(cov[:1], torch.tensor([2.0]), 2, reg=1e-6)    # 1 <= N_k < D + 1
    assert petite.tolist() == [True]
    petite, plancher = A.indicateurs_degenerescence(cov, torch.tensor([0.4, 0.2]), 2, reg=1e-6)   # éteintes
    assert petite.tolist() == [False, False] and plancher.tolist() == [False, False]
    X, _ = A.jeu_reference(42)
    assert A.em_classique(X, 3)["degenere"] is False


def test_hongrois_optimal():
    cout = torch.tensor([[4., 1., 3.], [2., 0., 5.], [3., 2., 2.]])
    col = A.hongrois(cout).tolist()
    total = sum(float(cout[i, c]) for i, c in enumerate(col))
    meilleur = min(sum(float(cout[i, p[i]]) for i in range(3))
                   for p in __import__("itertools").permutations(range(3)))
    assert abs(total - meilleur) < 1e-12


def test_t16_sem_label_switching():
    """Échantillons identiques à une permutation près : la moyenne alignée redonne l'original."""
    pi = torch.tensor([0.2, 0.3, 0.5])
    mu = torch.tensor([[0., 0.], [5., 5.], [0., 5.]])
    cov = torch.stack([torch.eye(2) * (k + 1) for k in range(3)])
    perms = [[0, 1, 2], [2, 0, 1], [1, 2, 0], [0, 2, 1]]
    ech = [(pi[p], mu[p], cov[p]) for p in perms]
    pi_m, mu_m, cov_m = A.moyenne_alignee(ech)
    assert torch.allclose(pi_m, pi) and torch.allclose(mu_m, mu) and torch.allclose(cov_m, cov)
    # sans alignement la moyenne est fausse
    assert not torch.allclose(torch.stack([e[1] for e in ech]).mean(0), mu)


def test_t110_plsa_monotone():
    g = A.generateur(0)
    comptes = torch.poisson(torch.rand(30, 40, generator=g) * 3.0, generator=g)
    res = A.plsa_em(comptes, 3, graine=1)
    h = torch.tensor(res["ll_hist"])
    assert bool((h[1:] >= h[:-1] - 1e-8).all())
    assert torch.allclose(res["theta"].sum(1), torch.ones(30)) and torch.allclose(res["phi"].sum(1), torch.ones(3))


# --- risque.py (T0.5, T1.8) ---------------------------------------------------

def test_kupiec_valeur_connue():
    lr, p = R.kupiec(0, 250, 0.01)
    assert abs(lr - (-2 * 250 * math.log(0.99))) < 1e-9
    assert abs(p - 0.0250) < 5e-4


def test_christoffersen_independance_nulle():
    # pi01 = pi11 = 0,25 : LR_ind = 0
    assert abs(R.lr_independance(6, 2, 3, 1)) < 1e-12
    # dépendance forte : LR > seuil à 5 % (3,84)
    assert R.lr_independance(80, 2, 2, 8) > 3.84


def test_christoffersen_cc_somme():
    I = [0] * 40 + [1, 1, 1] + [0] * 50 + [1] + [0] * 20
    r = R.christoffersen(I, 0.05)
    assert abs(r["lr_cc"] - (r["lr_uc"] + r["lr_ind"])) < 1e-12
    assert abs(R._khi2_sf(5.991, 2) - 0.05) < 1e-3
    assert abs(R._khi2_sf(3.841, 1) - 0.05) < 1e-3


def test_diebold_mariano_valeur_connue():
    # d = 1..5 : moyenne 3, variance (div. T) 2, h = 1 -> stat = 3 / sqrt(2 / 5)
    s, p = R.diebold_mariano([1, 2, 3, 4, 5], h=1, harvey=False)
    assert abs(s - 3 / math.sqrt(2 / 5)) < 1e-9
    s2, _ = R.diebold_mariano([1, 2, 3, 4, 5], h=1, harvey=True)
    assert abs(s2 - s * math.sqrt(4 / 5)) < 1e-9


def test_acerbi_szekely_calibre():
    # rendements N(0,1) : VaR et ES exactes à 5 % => Z1 et Z2 proches de 0
    g = A.generateur(0)
    x = torch.randn(200000, generator=g)
    p = 0.05
    var = torch.full_like(x, -1.6448536269514722)
    es = torch.full_like(x, -2.0627128075074257)
    z = R.acerbi_szekely(x, var, es, p)
    assert abs(z["z1"]) < 0.03 and abs(z["z2"]) < 0.03


def test_posterieur_et_student_reproductibles():
    X = torch.randn(300, 1, generator=A.generateur(0))
    vb = A.em_variationnel(X, 3, alpha0=1 / 3)
    a = R.echantillonner_posterieur_gmm_1d(vb["P"], 50, graine=3)
    b = R.echantillonner_posterieur_gmm_1d(vb["P"], 50, graine=3)
    assert all(torch.equal(u, v) for u, v in zip(a, b))
    var, es = R.var_es_student_melange(vb["P"], 0.05, n=100000)
    assert es < var < 0
    # proche du quantile gaussien (N(0,1)) pour N = 300
    assert abs(var + 1.645) < 0.25
