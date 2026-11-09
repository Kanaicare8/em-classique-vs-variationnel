"""
Modèle exporté (outil/modeles/<version>/) et probabilité du régime de tension, en NumPy.

Pour un vecteur d'écarts x (unités d'origine) : z = (x - centre) / échelle ; pour chaque jeu de paramètres
(pi, mu, cov), P(z = k | x) = pi_k N(z; mu_k, cov_k) / somme_j pi_j N(z; mu_j, cov_j) ; P(tension) est celle du
modèle plug-in (EM-BIC) ou la moyenne sur les tirages de q (VB) ; intervalle à 90 % = quantiles 5 % et 95 % des
tirages (interpolation linéaire, comme torch.quantile). Identique au calcul du mémoire : voir outil/tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

DOSSIER_MODELES = Path(__file__).resolve().parent.parent / "modeles"
_LOG_2PI = np.log(2 * np.pi)


def _prepare(pi, mu, cov):
    """Quantités fixes d'un lot de paramètres, calculées une fois au chargement : inverse du facteur de Cholesky,
    constante de normalisation et log des poids."""
    L = np.linalg.cholesky(cov)                                           # (S, K, d, d)
    logdet = 2 * np.log(np.diagonal(L, axis1=-2, axis2=-1)).sum(-1)      # (S, K)
    const = -0.5 * (mu.shape[-1] * _LOG_2PI + logdet) + np.log(np.clip(pi, 1e-300, None))
    return {"Linv": np.linalg.inv(L), "mu": mu, "const": const}


def _proba(Z, prep, k, lot=512):
    """P(z = k | x) pour S jeux de paramètres préparés : (S, N) ; k (S,) ou entier."""
    Linv, mu, const = prep["Linv"], prep["mu"], prep["const"]
    S, N = len(mu), len(Z)
    k = np.broadcast_to(np.asarray(k), (S,))
    out = np.empty((S, N))
    for s0 in range(0, S, lot):
        sl = slice(s0, s0 + lot)
        diff = Z[None, None, :, :] - mu[sl][:, :, None, :]                # (s, K, N, d)
        y = np.einsum("skij,sknj->skni", Linv[sl], diff)
        lp = const[sl][:, :, None] - 0.5 * (y * y).sum(-1)
        lp -= lp.max(1, keepdims=True)
        p = np.exp(lp)
        p /= p.sum(1, keepdims=True)
        out[sl] = p[np.arange(p.shape[0]), k[sl], :]
    return out


class Modele:
    def __init__(self, version: str = "memoire", dossier: Path | None = None):
        self.dossier = Path(dossier or DOSSIER_MODELES / version)
        self.fiche = json.loads((self.dossier / "fiche.json").read_text(encoding="utf-8"))
        a = np.load(self.dossier / "parametres.npz")
        self.centre, self.echelle = a["centre"], a["echelle"]
        self.bras = {}
        for nom, info in self.fiche["bras"].items():
            self.bras[nom] = {**info, "k_tirage": a[f"{nom}/k_tirage"].astype(int),
                              "tirages": _prepare(a[f"{nom}/tirages_pi"], a[f"{nom}/tirages_mu"], a[f"{nom}/tirages_cov"]),
                              "plugin": _prepare(a[f"{nom}/plugin_pi"][None], a[f"{nom}/plugin_mu"][None],
                                                 a[f"{nom}/plugin_cov"][None])}
        self._memo = {}                 # écarts (octets exacts) -> {bras : (p, bas, haut)} : seul le neuf est calculé

    @property
    def version(self):
        return self.fiche["version"]

    def _calculer(self, X):
        Z = (X - self.centre) / self.echelle
        out = {}
        for nom, b in self.bras.items():
            ps = _proba(Z, b["tirages"], b["k_tirage"])
            p = ps.mean(0) if b["p_moyenne_des_tirages"] else _proba(Z, b["plugin"], b["k_tension"])[0]
            bas, haut = np.quantile(ps, [0.05, 0.95], axis=0)
            out[nom] = (p, bas, haut)
        return out

    def proba(self, X) -> dict:
        """X : (N, 3) écarts en unités d'origine -> {bras : {"p", "bas", "haut"}} (tableaux (N,)). Les lignes déjà
        calculées sont relues de la mémoire : ajouter un relevé ne recalcule que les observations qu'il change."""
        X = np.atleast_2d(np.asarray(X, dtype=np.float64))
        cles = [x.tobytes() for x in X]
        neuves = sorted({i for i, c in enumerate(cles) if c not in self._memo}, key=lambda i: i)
        neuves = list({cles[i]: i for i in neuves}.values())
        if neuves:
            res = self._calculer(X[neuves])
            for j, i in enumerate(neuves):
                self._memo[cles[i]] = {nom: (float(r[0][j]), float(r[1][j]), float(r[2][j])) for nom, r in res.items()}
        return {nom: {k: np.array([self._memo[c][nom][n] for c in cles]) for n, k in enumerate(("p", "bas", "haut"))}
                for nom in self.bras}


def versions() -> list[dict]:
    """Fiches des modèles disponibles, la référence du mémoire en premier puis les réestimations par date."""
    fiches = [json.loads(f.read_text(encoding="utf-8")) for f in DOSSIER_MODELES.glob("*/fiche.json")]
    return sorted(fiches, key=lambda f: (f["version"] != "memoire", f.get("exporte_le", "")))
