"""Valeurs de référence connues pour les tests statistiques écrits à la main."""
import itertools
import math
import os
import sys

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import statistique as S  # noqa: E402


def test_t_cdf_quantiles_classiques():
    # quantiles tabulés de Student : t_{0,975 ; 9} = 2,2622 ; t_{0,975 ; 29} = 2,0452 ; t_{0,95 ; 4} = 2,1318
    assert abs(S.t_cdf(2.262157, 9) - 0.975) < 1e-6
    assert abs(S.t_cdf(2.045230, 29) - 0.975) < 1e-6
    assert abs(S.t_cdf(2.131847, 4) - 0.95) < 1e-6
    assert abs(S.t_cdf(0.0, 7) - 0.5) < 1e-12
    assert abs(S.t_cdf(-1.5, 12) + S.t_cdf(1.5, 12) - 1.0) < 1e-12


def test_wilcoxon_exact_par_enumeration():
    """La loi par programmation dynamique coïncide avec l'énumération des 2^n signes (ex aequo compris)."""
    for d in ([1.0, 2.0, 3.0, -4.0, 5.0, 6.0, -0.5, 7.0], [1.0, 1.0, -2.0, 2.0, 3.0, -3.0, 3.0]):
        w, p, n = S.wilcoxon_exact(d)
        a = torch.tensor(d)
        r = S._rangs_moyens(a.abs())
        wobs = float(r[a > 0].sum())
        tous = [float((r * torch.tensor(s)).sum()) for s in itertools.product([0.0, 1.0], repeat=len(d))]
        pb = sum(x <= wobs + 1e-9 for x in tous) / len(tous)
        ph = sum(x >= wobs - 1e-9 for x in tous) / len(tous)
        assert abs(p - min(1.0, 2 * min(pb, ph))) < 1e-12 and abs(w - wobs) < 1e-12


def test_wilcoxon_dix_positifs():
    # 10 différences positives : p bilatérale exacte = 2 / 2^10
    assert abs(S.wilcoxon_exact(list(range(1, 11)))[1] - 2 / 1024) < 1e-15


def test_tost_et_holm():
    d = [0.01, -0.005, 0.002, 0.0, 0.004, -0.003] * 5
    assert S.tost(d, 0.03)["p"] < 1e-6
    assert S.tost([0.05] * 10, 0.03)["p"] == 1.0
    assert S.holm([0.01, 0.04, 0.03]) == [0.03, 0.06, 0.06]


def test_decision_apres_holm():
    """Une p brute < 0,05 mais une p ajustée > 0,05 ne donne PAS de décision positive."""
    hyp = [{"id": "a", "test": "difference", "diffs": [1.0] * 6},          # p exacte = 2/64 = 0,03125
           {"id": "b", "test": "difference", "diffs": [1.0] * 6}]
    out = S.decider_famille(hyp, 0.05, 500)
    assert all(abs(h["p"] - 2 / 64) < 1e-12 and h["p_holm"] == 0.0625 for h in out)
    assert all(h["decision"] == "différence non démontrée" for h in out)


def test_wilson():
    p, b, h = S.wilson(90, 100)
    assert abs(b - 0.8256) < 1e-3 and abs(h - 0.9448) < 1e-3
