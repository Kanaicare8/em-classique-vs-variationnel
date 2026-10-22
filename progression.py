"""
Barre de progression écrite à la main (sans dépendance), en ASCII pour toutes les consoles :

  scenarios  [##########..........]  412/824  50,0 %  12 min 03 s écoulées, reste ~12 min 01 s  S3/K=5/rep=07

Utilisation :
    b = Barre(total, "scenarios")
    for ...:
        b.avancer(info="S3/K=5/rep=07")
    b.fermer()
"""

from __future__ import annotations

import sys
import time


def duree(s: float) -> str:
    s = int(round(s))
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    if h:
        return f"{h} h {m:02d} min"
    if m:
        return f"{m} min {s:02d} s"
    return f"{s} s"


class Barre:
    def __init__(self, total: int, titre: str, largeur: int = 30, flux=sys.stdout):
        self.total = max(int(total), 0)
        self.titre = titre
        self.largeur = largeur
        self.flux = flux
        self.n = 0
        self.t0 = time.time()
        self._afficher("")

    def _afficher(self, info: str):
        frac = self.n / self.total if self.total else 1.0
        plein = int(round(frac * self.largeur))
        ecoule = time.time() - self.t0
        reste = (ecoule / self.n * (self.total - self.n)) if self.n else float("nan")
        txt_reste = f", reste ~{duree(reste)}" if self.n and self.n < self.total else ""
        ligne = (f"\r{self.titre:14s} [{'#' * plein}{'.' * (self.largeur - plein)}] {self.n:>5d}/{self.total:<5d} "
                 f"{100 * frac:5.1f} %  {duree(ecoule)} écoulées{txt_reste}  {info[:40]}")
        self.flux.write(ligne.ljust(150))
        self.flux.flush()

    def avancer(self, k: int = 1, info: str = ""):
        self.n = min(self.total, self.n + k)
        self._afficher(info)

    def message(self, texte: str):
        """Affiche une ligne (erreur, avertissement) sans casser la barre."""
        self.flux.write("\r" + " " * 150 + "\r" + texte + "\n")
        self._afficher("")

    def fermer(self):
        self._afficher("terminé")
        self.flux.write("\n")
        self.flux.flush()
