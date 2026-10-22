"""
================================================================================
CADRE DES ÉTAPES : unités de travail, mémoire par unité, résultats agrégés
================================================================================

Une ÉTAPE (calibrage, scénarios, climat, ...) est une liste d'UNITÉS indépendantes. Une unité est
une fonction `f(memo, **kwargs) -> {"lignes": [dict, ...], "artefacts": {...}}` :
  * `lignes`    : lignes de tableau (une par bras, par mesure...), agrégées ensuite en CSV ;
  * `artefacts` : tout ce qu'il faut pour regénérer les figures sans recalculer (données, ajustements).
L'unité terminée est écrite atomiquement dans le magasin ; ses calculs intermédiaires passent par
`memo(cle, f)` (un fichier par ajustement) et `memo.instantane(cle)` (état des longues boucles) :
une interruption ne perd au plus que l'ajustement en cours, et celui-ci reprend dans sa boucle.

Deux magasins séparés : resultats/magasin (exécution complète) et resultats/magasin_rapide (essais).
"""

from __future__ import annotations

import csv
import importlib
from dataclasses import dataclass, field
from pathlib import Path

import persistance as PE

RACINE = Path(__file__).parent


@dataclass
class Unite:
    etape: str
    cle: str
    module: str
    fonction: str
    kwargs: dict = field(default_factory=dict)
    depend: tuple = ()          # clés d'unités de la même étape qui doivent être terminées avant celle-ci


def racine_magasin(rapide: bool) -> Path:
    return RACINE / "resultats" / ("magasin_rapide" if rapide else "magasin")


def dossier_tables(rapide: bool) -> Path:
    d = RACINE / "resultats" / ("tables_rapide" if rapide else "tables")
    d.mkdir(parents=True, exist_ok=True)
    return d


def magasin(etape: str, rapide: bool) -> PE.Magasin:
    return PE.Magasin(etape, racine_magasin(rapide))


class Memo:
    """Mémoire des calculs intermédiaires d'une unité (sous-dossier _sous/ de l'unité)."""

    def __init__(self, mag: PE.Magasin, cle_unite: str):
        self.mag = mag
        self.prefixe = cle_unite

    def __call__(self, cle: str, f):
        return self.mag.memo(f"{self.prefixe}/_sous/{cle}", f)

    def instantane(self, cle: str, tous: int = 20) -> PE.Instantane:
        return self.mag.instantane(f"{self.prefixe}/{cle}", tous)


def executer_unite(u: Unite, rapide: bool) -> str:
    """Exécute une unité (dans un processus de travail) et l'écrit atomiquement. Ne fait rien si elle existe."""
    import torch
    torch.set_num_threads(1)
    mag = magasin(u.etape, rapide)
    if mag.existe(u.cle):
        return u.cle
    f = getattr(importlib.import_module(u.module), u.fonction)
    res = f(Memo(mag, u.cle), rapide=rapide, **u.kwargs)
    res.setdefault("lignes", [])
    res.setdefault("artefacts", {})
    res["cle"] = u.cle
    mag.ecrire(u.cle, res)
    PE.Journal(mag.dossier.parent / "_journal").ecrire(etape=u.etape, unite=u.cle, statut="terminee")
    return u.cle


def resultats(etape: str, rapide: bool, prefixe: str = "") -> list[dict]:
    """Toutes les unités terminées d'une étape (dans l'ordre des clés)."""
    mag = magasin(etape, rapide)
    return [r for c in mag.cles() if c.startswith(prefixe) for r in [mag.lire(c)] if r is not None]


def lignes(etape: str, rapide: bool, prefixe: str = "") -> list[dict]:
    out = []
    for r in resultats(etape, rapide, prefixe):
        out.extend(r.get("lignes", []))
    return out


def ecrire_csv(nom: str, lignes_: list[dict], rapide: bool) -> Path:
    """Écrit un CSV (utf-8) avec l'union ordonnée des colonnes."""
    chemin = dossier_tables(rapide) / f"{nom}.csv"
    colonnes = list(dict.fromkeys(k for l in lignes_ for k in l))
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colonnes)
        w.writeheader()
        for l in lignes_:
            w.writerow({k: _cellule(v) for k, v in l.items()})
    return chemin


def _cellule(v):
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, (list, tuple)):
        return " ; ".join(str(_cellule(x)) for x in v)
    return v
