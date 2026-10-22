"""
================================================================================
INFÉRENCE STATISTIQUE (from scratch, PyTorch)
================================================================================

  wilson()                intervalle de Wilson (1927) d'une proportion
  ic_bootstrap()          intervalle bootstrap percentile, vectorisé
  wilcoxon_exact()        test des rangs signés (Wilcoxon 1945), loi EXACTE de permutation
                          (signes aléatoires, rangs moyens pour les ex aequo, différences nulles écartées)
  t_cdf()                 fonction de répartition de Student via la bêta incomplète régularisée
  tost()                  équivalence par deux tests unilatéraux (Schuirmann 1987), loi de Student
  holm()                  procédure séquentielle de Holm (1979)
  decider_famille()       une décision par hypothèse, APRÈS correction de Holm sur la famille, avec
                          un seul test déclaré à l'avance par hypothèse (équivalence OU différence)
  puissance_simulee()     puissance d'un test déclaré pour n réplications, par rééchantillonnage d'un pilote
  decomposition_variance() part de variance expliquée par chaque facteur (effets principaux)
"""

from __future__ import annotations

import math

import torch

Z975 = 1.959963984540054


def generateur(graine: int) -> torch.Generator:
    g = torch.Generator()
    g.manual_seed(int(graine))
    return g


# ------------------------------------------------------------------------------ proportions et bootstrap
def wilson(k: int, n: int, z: float = Z975):
    """Proportion k/n et intervalle de score de Wilson à 95 %. Retourne (p, bas, haut)."""
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    demi = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, centre - demi), min(1.0, centre + demi)


def ic_bootstrap(valeurs, n_boot: int, niveau: float = 0.95, graine: int = 0, stat: str = "moyenne"):
    """Intervalle bootstrap percentile de la moyenne (ou de la médiane), en un seul tenseur (n_boot, n)."""
    v = torch.as_tensor(valeurs, dtype=torch.float64)
    idx = torch.randint(len(v), (n_boot, len(v)), generator=generateur(graine))
    ech = v[idx]
    s = ech.mean(1) if stat == "moyenne" else ech.median(1).values
    est = v.mean() if stat == "moyenne" else v.median()
    a = (1 - niveau) / 2
    return float(est), float(torch.quantile(s, a)), float(torch.quantile(s, 1 - a))


# ------------------------------------------------------------------------------ Wilcoxon exact
def _rangs_moyens(a: torch.Tensor) -> torch.Tensor:
    ordre = torch.argsort(a)
    tri = a[ordre]
    rangs = torch.empty(len(a), dtype=torch.float64)
    i = 0
    while i < len(a):
        j = i
        while j + 1 < len(a) and tri[j + 1] == tri[i]:
            j += 1
        rangs[ordre[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return rangs


def wilcoxon_exact(diffs):
    """
    Test des rangs signés de Wilcoxon, loi exacte conditionnelle aux rangs observés : sous H0 (symétrie
    autour de 0), chaque signe vaut + ou - avec probabilité 1/2 indépendamment ; la loi de
    W+ = somme des rangs des différences positives s'obtient par programmation dynamique sur les
    rangs doublés (entiers, ex aequo compris). Différences nulles écartées (convention de Wilcoxon).
    Retourne (W+, probabilité critique bilatérale, n retenu).
    """
    d = torch.as_tensor(diffs, dtype=torch.float64)
    d = d[d != 0]
    n = len(d)
    if n == 0:
        return 0.0, 1.0, 0
    r2 = (2.0 * _rangs_moyens(d.abs())).round().long()           # rangs doublés, entiers
    total = int(r2.sum())
    loi = torch.zeros(total + 1, dtype=torch.float64)
    loi[0] = 1.0
    for r in r2.tolist():
        nouvelle = loi.clone()
        nouvelle[r:] += loi[:total + 1 - r]
        loi = nouvelle
    loi = loi / loi.sum()
    w2 = int(r2[d > 0].sum())
    p_bas = float(loi[:w2 + 1].sum())
    p_haut = float(loi[w2:].sum())
    return w2 / 2.0, min(1.0, 2.0 * min(p_bas, p_haut)), n


# ------------------------------------------------------------------------------ Student
def _betacf(a: float, b: float, x: float, iters: int = 300, eps: float = 1e-15) -> float:
    """Fraction continue de la bêta incomplète (algorithme de Lentz modifié)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, iters + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        dl = d * c
        h *= dl
        if abs(dl - 1.0) < eps:
            break
    return h


def beta_incomplete(a: float, b: float, x: float) -> float:
    """Bêta incomplète régularisée I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lbeta) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbeta) * _betacf(b, a, 1 - x) / b


def t_cdf(t: float, nu: float) -> float:
    """Fonction de répartition de la loi de Student à nu degrés de liberté."""
    x = nu / (nu + t * t)
    queue = 0.5 * beta_incomplete(nu / 2.0, 0.5, x)
    return 1.0 - queue if t > 0 else queue


def tost(diffs, marge: float):
    """
    Équivalence de la moyenne des différences appariées à 0 dans [-marge, +marge] par deux tests
    unilatéraux de Student (Schuirmann 1987) : p = max(p_bas, p_haut). Si toutes les différences
    sont égales, la décision est déterministe (p = 0 si |moyenne| < marge, 1 sinon).
    """
    d = torch.as_tensor(diffs, dtype=torch.float64)
    n = len(d)
    m = float(d.mean())
    if n < 2:
        return {"moyenne": m, "p": 1.0}
    se = float(d.std(unbiased=True)) / math.sqrt(n)
    if se == 0.0:
        return {"moyenne": m, "p": 0.0 if abs(m) < marge else 1.0}
    p_bas = 1.0 - t_cdf((m + marge) / se, n - 1)          # H0 : moyenne <= -marge
    p_haut = t_cdf((m - marge) / se, n - 1)               # H0 : moyenne >= +marge
    return {"moyenne": m, "p": max(p_bas, p_haut)}


# ------------------------------------------------------------------------------ familles d'hypothèses
def holm(pvalues):
    """p-valeurs ajustées de Holm (1979), dans l'ordre d'entrée."""
    p = list(pvalues)
    m = len(p)
    ordre = sorted(range(m), key=lambda i: p[i])
    aj = [0.0] * m
    courant = 0.0
    for rang, i in enumerate(ordre):
        courant = max(courant, min(1.0, (m - rang) * p[i]))
        aj[i] = courant
    return aj


def tester(diffs, test: str, marge: float | None = None):
    """Un test DÉCLARÉ : 'equivalence' (TOST à la marge) ou 'difference' (Wilcoxon exact bilatéral)."""
    d = torch.as_tensor(diffs, dtype=torch.float64)
    if test == "equivalence":
        return tost(d, marge)["p"]
    if test == "difference":
        return wilcoxon_exact(d)[1]
    raise ValueError(test)


def decider_famille(hypotheses: list[dict], alpha: float, n_boot: int, graine: int = 0) -> list[dict]:
    """
    hypotheses : liste de {"id", "axe", "enonce", "test" ('equivalence' | 'difference'), "marge", "diffs"}.
    Pour chaque hypothèse, le seul test déclaré est appliqué ; la correction de Holm porte sur toute la
    famille ; la décision est prise sur la p-valeur AJUSTÉE :
      equivalence : « équivalent » si p_holm < alpha, sinon « équivalence non démontrée » ;
      difference  : « A > B » ou « A < B » (signe de la moyenne) si p_holm < alpha, sinon « différence non démontrée ».
    L'intervalle rapporté est le bootstrap percentile à 95 % de la moyenne des différences.
    """
    p = [tester(h["diffs"], h["test"], h.get("marge")) if len(h["diffs"]) else 1.0 for h in hypotheses]
    aj = holm(p)
    sortie = []
    for h, pb, pa in zip(hypotheses, p, aj):
        d = torch.as_tensor(h["diffs"], dtype=torch.float64)
        est, bas, haut = ic_bootstrap(d, n_boot, graine=graine) if len(d) else (float("nan"),) * 3
        if h["test"] == "equivalence":
            decision = "équivalent" if pa < alpha else "équivalence non démontrée"
        else:
            decision = ("A > B" if est > 0 else "A < B") if pa < alpha else "différence non démontrée"
        sortie.append({k: v for k, v in h.items() if k != "diffs"} |
                      {"n": len(d), "estimation": est, "ic_bas": bas, "ic_haut": haut, "p": pb, "p_holm": pa,
                       "decision": decision})
    return sortie


def puissance_simulee(diffs_pilote, n: int, test: str, marge: float | None, alpha: float,
                      n_sim: int = 2000, graine: int = 0) -> float:
    """
    Puissance du test déclaré pour n réplications, estimée par rééchantillonnage du pilote :
      equivalence : différences recentrées à 0 (équivalence vraie) ; proportion de TOST significatifs ;
      difference  : différences recentrées à `marge` (écart vrai égal à la plus petite différence d'intérêt) ;
                    proportion de Wilcoxon significatifs.
    """
    d = torch.as_tensor(diffs_pilote, dtype=torch.float64)
    d = d - d.mean() + (0.0 if test == "equivalence" else marge)
    g = generateur(graine)
    ok = 0
    for _ in range(n_sim):
        e = d[torch.randint(len(d), (n,), generator=g)]
        if tester(e, test, marge) < alpha:
            ok += 1
    return ok / n_sim


def decomposition_variance(valeurs, niveaux: dict):
    """
    Part de variance de `valeurs` expliquée par chaque facteur (effets principaux, sommes de carrés de
    type I sur un plan complet équilibré) : eta² = SC_facteur / SC_totale ; le résidu contient les interactions.
    """
    y = torch.as_tensor(valeurs, dtype=torch.float64)
    moy = y.mean()
    sct = float(((y - moy) ** 2).sum())
    out, expl = {}, 0.0
    for nom, niv in niveaux.items():
        niv = list(niv)
        sc = 0.0
        for v in set(niv):
            m = torch.tensor([i for i, x in enumerate(niv) if x == v])
            sc += len(m) * float((y[m].mean() - moy) ** 2)
        out[nom] = sc / sct if sct > 0 else 0.0
        expl += out[nom]
    out["residu"] = max(0.0, 1.0 - expl)
    return out
