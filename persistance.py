"""
================================================================================
PERSISTANCE : points de reprise, artefacts et graines
================================================================================

  * Magasin (Store) : un fichier par unité de travail, écrit de façon ATOMIQUE (fichier temporaire
    dans le même dossier, fsync, puis os.replace). Une interruption (erreur, Ctrl+C, coupure) laisse
    soit l'ancien état, soit le nouveau, jamais un fichier à moitié écrit. Au redémarrage, les
    unités déjà présentes sont relues au lieu d'être recalculées.
  * Format : torch.save d'un dictionnaire de tenseurs et de types Python simples, relu avec
    torch.load(weights_only=True) : aucun code arbitraire n'est exécuté à la lecture.
  * Instantané (Instantane) : état complet d'une boucle EM / VB sauvegardé périodiquement, pour
    reprendre un long ajustement exactement où il s'est arrêté (voir algorithmes._piloter_lot).
  * Graines dérivées : graine(*rôle) donne une graine indépendante pour chaque rôle (données,
    ajustement, bootstrap, ...), au lieu de réutiliser la même graine pour plusieurs tirages.
  * Arrêt propre : un premier Ctrl+C (ou SIGTERM) demande l'arrêt après l'unité en cours ; un
    second interrompt immédiatement, sans corrompre le magasin.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import time
from pathlib import Path

import torch

RACINE = Path(__file__).parent
MAGASIN = RACINE / "resultats" / "magasin"


# ------------------------------------------------------------------------------ graines
def graine(*role) -> int:
    """Graine entière (63 bits) dérivée de façon déterministe d'un rôle, par exemple graine("S1", "donnees", 7)."""
    h = hashlib.sha256("|".join(str(r) for r in role).encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big") & ((1 << 62) - 1)


# ------------------------------------------------------------------------------ écriture atomique
def _ecrire_atomique(chemin: Path, ecrire) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tmp = chemin.with_name(chemin.name + f".tmp{os.getpid()}")
    with open(tmp, "wb") as f:
        ecrire(f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, chemin)


def _nettoyer(obj):
    """Convertit un résultat en types acceptés par torch.load(weights_only=True)."""
    if torch.is_tensor(obj):
        return obj.detach().cpu()
    if isinstance(obj, dict):
        return {str(k): _nettoyer(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_nettoyer(v) for v in obj]
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if hasattr(obj, "__dataclass_fields__"):
        return {"__classe__": type(obj).__name__, **{k: _nettoyer(getattr(obj, k)) for k in obj.__dataclass_fields__}}
    if hasattr(obj, "item"):
        return obj.item()
    return str(obj)


def sauver(chemin: Path, obj) -> None:
    _ecrire_atomique(Path(chemin), lambda f: torch.save(_nettoyer(obj), f))


def charger(chemin: Path):
    return torch.load(Path(chemin), weights_only=True)


# ------------------------------------------------------------------------------ magasin
def _nom_fichier(cle: str) -> str:
    sur = re.sub(r"[^A-Za-z0-9_.=,+-]+", "_", cle)
    if len(sur) > 120:
        sur = sur[:80] + "_" + hashlib.sha1(cle.encode()).hexdigest()[:16]
    return sur


class Magasin:
    """Un dossier par étape ; un fichier .pt par unité (clé), écrit atomiquement."""

    def __init__(self, etape: str, racine: Path = MAGASIN):
        self.etape = etape
        self.dossier = Path(racine) / etape

    def chemin(self, cle: str) -> Path:
        parties = cle.split("/")
        return self.dossier.joinpath(*[_nom_fichier(p) for p in parties[:-1]], _nom_fichier(parties[-1]) + ".pt")

    def existe(self, cle: str) -> bool:
        return self.chemin(cle).exists()

    def lire(self, cle: str):
        try:
            return charger(self.chemin(cle))
        except Exception:                       # fichier illisible (disque plein, version) : on recalcule
            return None

    def ecrire(self, cle: str, obj) -> None:
        sauver(self.chemin(cle), obj)

    def memo(self, cle: str, f, *a, **k):
        """Résultat de f(*a, **k) mémorisé : relu s'il existe déjà, sinon calculé puis écrit."""
        if self.existe(cle):
            v = self.lire(cle)
            if v is not None:
                return v
        v = f(*a, **k)
        self.ecrire(cle, v)
        return v

    def cles(self) -> list[str]:
        if not self.dossier.exists():
            return []
        out = []
        for p in self.dossier.rglob("*.pt"):
            rel = str(p.relative_to(self.dossier).with_suffix("")).replace(os.sep, "/")
            if "_instantanes" in rel.split("/") or "_sous" in rel.split("/"):
                continue
            out.append(rel)
        return sorted(out)

    def instantane(self, cle: str, tous: int = 20) -> "Instantane":
        return Instantane(self.dossier / "_instantanes" / (_nom_fichier(cle.replace("/", "__")) + ".pt"), tous)


class Instantane:
    """État d'une boucle d'ajustement sauvegardé tous les `tous` passages (voir algorithmes._piloter_lot)."""

    def __init__(self, chemin: Path, tous: int = 20):
        self.chemin = Path(chemin)
        self.tous = tous

    def lire(self):
        if not self.chemin.exists():
            return None
        try:
            return charger(self.chemin)
        except Exception:
            return None

    def ecrire(self, etat: dict) -> None:
        sauver(self.chemin, etat)

    def effacer(self) -> None:
        try:
            self.chemin.unlink()
        except FileNotFoundError:
            pass


# ------------------------------------------------------------------------------ journal et arrêt propre
class Journal:
    """Journal d'exécution en lignes JSON, un fichier par processus (pas de conflit d'écriture)."""

    def __init__(self, dossier: Path = MAGASIN / "_journal"):
        dossier.mkdir(parents=True, exist_ok=True)
        self.f = dossier / f"journal_{os.getpid()}.jsonl"

    def ecrire(self, **champs):
        champs["t"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(self.f, "a", encoding="utf-8") as h:
            h.write(json.dumps(champs, ensure_ascii=False) + "\n")
            h.flush()
            os.fsync(h.fileno())


_ARRET = {"demande": False}


def installer_arret_propre():
    def gestionnaire(signum, frame):
        if _ARRET["demande"]:
            raise KeyboardInterrupt
        _ARRET["demande"] = True
        print("\nArrêt demandé : fin de l'unité en cours puis sortie (Ctrl+C à nouveau pour interrompre tout de suite).",
              flush=True)
    signal.signal(signal.SIGINT, gestionnaire)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, gestionnaire)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, gestionnaire)


def arret_demande() -> bool:
    return _ARRET["demande"]


# ------------------------------------------------------------------------------ résumé d'un ajustement
def resume_ajustement(res: dict, avec_r: bool = True) -> dict:
    """
    Tout ce qu'il faut pour regénérer tableaux et figures sans réajuster : paramètres, partition,
    responsabilités (float32), historiques, indicateurs et relances.
    """
    garder = ("pi", "mu", "m", "cov", "alpha", "Nk", "loglik", "crit", "elbo", "ll_hist", "hist", "n_iter", "converge",
              "bic", "aic", "icl", "entropie", "n_params", "degenere", "petite_composante", "plancher_regularisation",
              "temps", "temps_par_iter", "cov_type", "critere_nom", "relances", "k_hat", "temps_total", "log_posteriori",
              "critere_par_k", "temps_balayage", "k_echecs", "reg", "echec", "elbo_hist", "n_actives")
    out = {k: res[k] for k in garder if k in res}
    if "labels" in res:
        out["labels"] = res["labels"].to(torch.int16)
    if avec_r and "r" in res:
        out["r"] = res["r"].to(torch.float32)
    if "P" in res:
        out["P"] = {k: v for k, v in res["P"].items() if torch.is_tensor(v) or isinstance(v, str)}
    if "priori" in res:
        out["priori"] = res["priori"]
    return out
