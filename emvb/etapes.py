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
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from emvb import persistance as PE

from emvb.chemins import RACINE


@dataclass
class Unite:
    etape: str
    cle: str
    module: str
    fonction: str
    kwargs: dict = field(default_factory=dict)
    depend: tuple = ()          # clés d'unités de la même étape qui doivent être terminées avant celle-ci


def charger_module(nom: str):
    """Module d'une étape par son nom court (« etape_prix », « scenarios »...), cherché dans le paquet emvb ; un nom
    qui n'en fait pas partie (module de test) s'importe tel quel."""
    try:
        return importlib.import_module(f"emvb.{nom}")
    except ModuleNotFoundError as e:
        if e.name != f"emvb.{nom}":      # le module existe mais une de ses dépendances manque : ne pas masquer l'erreur
            raise
        return importlib.import_module(nom)


def racine_magasin(rapide: bool) -> Path:
    """Variable ICARE_MAGASIN : autre emplacement (autre disque, tests), hérité par les processus de travail."""
    if os.environ.get("ICARE_MAGASIN"):
        return Path(os.environ["ICARE_MAGASIN"]) / ("magasin_rapide" if rapide else "magasin")
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
    if mag.complete(u.cle):
        return u.cle
    f = getattr(charger_module(u.module), u.fonction)
    t0 = time.perf_counter()
    res = f(Memo(mag, u.cle), rapide=rapide, **u.kwargs)
    res.setdefault("lignes", [])
    res.setdefault("artefacts", {})
    res["cle"] = u.cle
    res["duree_s"] = time.perf_counter() - t0      # durée murale de l'unité (sert au plafond de budget, D-05)
    mag.ecrire(u.cle, res)
    PE.Journal(mag.dossier.parent / "_journal").ecrire(etape=u.etape, unite=u.cle, statut="terminee")
    return u.cle


def _executer_sous_tache(racine: str, etape: str, cle: str, module: str, fonction: str, kwargs: dict) -> str:
    """Calcule une sous-tâche (dans un processus de travail) et l'écrit sous sa clé de mémoire. Ne fait rien si elle existe."""
    import torch
    torch.set_num_threads(1)
    mag = PE.Magasin(etape, Path(racine))
    if not mag.existe(cle):
        mag.ecrire(cle, getattr(charger_module(module), fonction)(**kwargs))
    return cle


def sous_taches_paralleles(memo: Memo, taches: list) -> None:
    """
    Calcule en parallèle les sous-calculs mémorisés d'une unité qui en enchaînerait sinon un grand nombre à la suite
    (relances, configurations d'une recherche) : chaque tâche (cle, module, fonction, kwargs) absente du magasin est
    confiée à un processus, qui écrit fonction(**kwargs) sous memo(cle). La boucle de l'unité relit ensuite ces valeurs
    par memo(cle, ...) : même fonction, même graine, un fil d'exécution par processus, donc mêmes résultats ; seul
    l'ordre d'exécution change. Nombre de processus : ICARE_SOUS_TRAVAILLEURS (défaut : coeurs logiques - 1).
    """
    import concurrent.futures as cf
    import multiprocessing as mp
    import os
    mag = memo.mag
    reste = [(f"{memo.prefixe}/_sous/{c}", m, f, k) for c, m, f, k in taches
             if not mag.existe(f"{memo.prefixe}/_sous/{c}")]
    n = min(len(reste), int(os.environ.get("ICARE_SOUS_TRAVAILLEURS", max(1, (os.cpu_count() or 2) - 1))))
    if n < 1:
        return
    with cf.ProcessPoolExecutor(max_workers=n, mp_context=mp.get_context("spawn"),
                                initializer=PE.ignorer_interruption) as pool:
        futs = [pool.submit(_executer_sous_tache, str(mag.dossier.parent), mag.etape, c, m, f, k)
                for c, m, f, k in reste if not PE.arret_demande()]
        for fu in cf.as_completed(futs):
            fu.result()


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
