"""
Relevés de prix et écarts au niveau des douze mois, sans PyTorch (même définition que donnees.charger_prix du mémoire).

Un relevé est (marché, denrée, mois, prix XAF/kg). Les sources sont l'extrait du PAM (format de
outils/telecharger_prix_wfp.py, n'importe quelle version) et les relevés saisis dans l'outil ; à (marché, denrée, mois)
égaux, le relevé du PAM l'emporte (le relevé saisi reste en base, il n'est simplement pas utilisé).

Écart de la denrée j, marché m, mois t : e = ln p(t) - moyenne des ln p(u), u = t - fenêtre .. t - 1 relevés, défini
si au moins `releves_min` relevés existent dans la fenêtre ; les pics isolés d'un mois (écart d'au moins ln(facteur)
dans le même sens avec t - 1 et t + 1) sont écartés avant le calcul.
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
from dataclasses import dataclass, field
from pathlib import Path


def mois_index(aaaa_mm: str) -> int:
    """'2023-08' -> 2023 x 12 + 7 (mois consécutifs = entiers consécutifs)."""
    return int(aaaa_mm[:4]) * 12 + int(aaaa_mm[5:7]) - 1


def mois_texte(i: int) -> str:
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


def pics_isoles(serie: dict, facteur: float) -> list[int]:
    s = math.log(facteur)
    out = []
    for t, v in serie.items():
        if t - 1 in serie and t + 1 in serie:
            a, b = v - serie[t - 1], v - serie[t + 1]
            if min(abs(a), abs(b)) >= s and a * b > 0:
                out.append(t)
    return out


@dataclass
class Marche:
    nom: str
    region: str
    lat: float | None = None
    lon: float | None = None


@dataclass
class Releves:
    """Séries de log-prix nettoyées : serie[(marché, denrée)] = {mois : ln p} ; pics écartés listés dans `ecartes`."""
    panier: list
    fenetre: int
    releves_min: int
    facteur_pic: float
    serie: dict = field(default_factory=dict)
    source: dict = field(default_factory=dict)          # (marché, denrée, mois) -> "PAM" ou "saisie"
    marches: dict = field(default_factory=dict)          # nom -> Marche
    ecartes: list = field(default_factory=list)
    sha256: str | None = None

    # -------------------------------------------------------------------- construction
    @classmethod
    def depuis_extrait(cls, chemin: Path | str, panier, fenetre=12, releves_min=3, facteur_pic=3.0, saisies=()):
        return cls.depuis_octets(Path(chemin).read_bytes(), panier, fenetre, releves_min, facteur_pic, saisies)

    @classmethod
    def depuis_octets(cls, brut: bytes, panier, fenetre=12, releves_min=3, facteur_pic=3.0, saisies=()):
        r = cls(list(panier), int(fenetre), int(releves_min), float(facteur_pic), sha256=hashlib.sha256(brut).hexdigest())
        for l in csv.DictReader(io.StringIO(brut.decode("utf-8"))):
            if l["commodity"] not in r.panier or not l["price"]:
                continue
            m, c, t = l["market"], l["commodity"], mois_index(l["date"])
            r.serie.setdefault((m, c), {})[t] = math.log(float(l["price"]))
            r.source[(m, c, t)] = "PAM"
            if m not in r.marches:
                r.marches[m] = Marche(m, l["admin1"], float(l["latitude"] or "nan"), float(l["longitude"] or "nan"))
        for s in saisies:                     # objets ou dict : marche, region, denree, mois (aaaa-mm), prix
            g = s if isinstance(s, dict) else s.__dict__
            m, c, t = g["marche"], g["denree"], mois_index(g["mois"])
            if (m, c, t) in r.source:
                continue
            r.serie.setdefault((m, c), {})[t] = math.log(float(g["prix"]))
            r.source[(m, c, t)] = "saisie"
            r.marches.setdefault(m, Marche(m, g.get("region") or "?"))
        for (m, c), s in r.serie.items():
            for t in pics_isoles(s, r.facteur_pic):
                r.ecartes.append({"marche": m, "denree": c, "mois": mois_texte(t), "prix": round(math.exp(s.pop(t)), 2),
                                  "source": r.source[(m, c, t)]})
        r.ecartes.sort(key=lambda e: (e["mois"], e["marche"], e["denree"]))
        return r

    # -------------------------------------------------------------------- lecture
    def prix(self, marche, denree, t):
        v = self.serie.get((marche, denree), {}).get(t)
        return None if v is None else math.exp(v)

    def niveau(self, marche, denree, t):
        """(niveau des `fenetre` mois avant t en XAF/kg, nombre de relevés) ; niveau None si trop peu de relevés."""
        s = self.serie.get((marche, denree), {})
        passe = [s[u] for u in range(t - self.fenetre, t) if u in s]
        return (math.exp(sum(passe) / len(passe)) if len(passe) >= self.releves_min else None), len(passe)

    def ecart(self, marche, denree, t, prix=None):
        """Écart du log-prix au niveau ; `prix` : prix hypothétique (relevé à évaluer), sinon le relevé du mois t."""
        p = self.prix(marche, denree, t) if prix is None else prix
        niv, _ = self.niveau(marche, denree, t)
        return None if p is None or niv is None or p <= 0 else math.log(p) - math.log(niv)

    def observations(self):
        """[(mois, marché, [e_1, e_2, e_3])] des (marché, mois) dont les trois écarts sont définis, triées comme le mémoire."""
        obs = []
        for m in sorted(self.marches):
            mois = set()
            for c in self.panier:
                mois |= self.serie.get((m, c), {}).keys()
            for t in sorted(mois):
                x = [self.ecart(m, c, t) for c in self.panier]
                if all(v is not None for v in x):
                    obs.append((t, m, x))
        obs.sort(key=lambda o: (o[0], sorted(self.marches).index(o[1])))
        return obs

    def dernier_mois(self):
        return max(t for s in self.serie.values() for t in s)
