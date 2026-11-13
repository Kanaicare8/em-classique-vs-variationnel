"""
Barre de progression écrite à la main (sans dépendance), en ASCII pour toutes les consoles (cmd, PowerShell, VS Code) :

  scenarios [#######.........]  412/824 50,0 % | 12 min 03 s, reste ~12 min | 3 en cours, 57 ajustements

* La ligne est tronquée à la largeur de la fenêtre : elle ne passe jamais à la ligne, de sorte que le retour en début
  de ligne (\\r) la réécrit sur place.
* rafraichir() redessine sans avancer (temps écoulé, unités en cours) : la barre bouge même pendant une longue unité.
* Si la sortie n'est pas une console (redirection vers un fichier), une ligne est écrite à chaque unité terminée et au
  plus une fois par minute sinon, au lieu de réécritures illisibles.

Utilisation :
    b = Barre(total, "scenarios")
    for ...:
        b.avancer(info="S3/K=5/rep=07")
    b.fermer()
"""

from __future__ import annotations

import shutil
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
    def __init__(self, total: int, titre: str, largeur: int = 24, flux=sys.stdout):
        self.total = max(int(total), 0)
        self.titre = titre
        self.largeur = largeur
        self.flux = flux
        self.console = bool(getattr(flux, "isatty", lambda: False)())
        self.n = 0
        self.t0 = time.time()
        self._derniere_ligne = 0.0
        self._etat = ""
        self._afficher("démarrage")

    def _colonnes(self) -> int:
        return max(40, shutil.get_terminal_size((100, 20)).columns - 1)

    def _ligne(self, info: str) -> str:
        frac = self.n / self.total if self.total else 1.0
        plein = int(round(frac * self.largeur))
        ecoule = time.time() - self.t0
        if self.n and self.n < self.total:
            reste = f", reste ~{duree(ecoule / self.n * (self.total - self.n))}"
        elif self.n == 0 and self.total:
            reste = ", estimation après la 1re unité"
        else:
            reste = ""
        tete = (f"{self.titre} [{'#' * plein}{'.' * (self.largeur - plein)}] {self.n}/{self.total} "
                f"{100 * frac:.1f} % | {duree(ecoule)}{reste}")
        return tete + (f" | {info}" if info else "")

    def _afficher(self, info: str, force: bool = True):
        ligne = self._ligne(info)
        if self.console:
            c = self._colonnes()
            self.flux.write("\r" + ligne[:c].ljust(c))
        elif force or time.time() - self._derniere_ligne >= 60:
            self.flux.write(ligne + "\n")
            self._derniere_ligne = time.time()
        self.flux.flush()

    def avancer(self, k: int = 1, info: str = ""):
        self.n = min(self.total, self.n + k)
        self._afficher(info or self._etat)

    def rafraichir(self, info: str = ""):
        """Redessine la barre sans avancer (temps écoulé, travail en cours)."""
        self._etat = info
        self._afficher(info, force=False)

    def message(self, texte: str):
        """Affiche une ligne (erreur, avertissement) sans casser la barre."""
        if self.console:
            self.flux.write("\r" + " " * self._colonnes() + "\r")
        self.flux.write(texte + "\n")
        self._afficher(self._etat)

    def fermer(self):
        self._afficher("terminé")
        if self.console:
            self.flux.write("\n")
        self.flux.flush()
