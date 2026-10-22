"""Outils de modification de body.tex : remplacement de lignes ou de fragments avec vérification d'unicité."""
import re
from pathlib import Path

CHEMIN = Path(__file__).parent / "body.tex"


class Corps:
    def __init__(self):
        self.lignes = CHEMIN.read_text(encoding="utf-8").split("\n")

    def _idx(self, prefixe):
        trouves = [i for i, l in enumerate(self.lignes) if l.startswith(prefixe)]
        assert len(trouves) == 1, f"{len(trouves)} lignes pour : {prefixe[:70]}"
        return trouves[0]

    def remplacer_ligne(self, prefixe, nouveau):
        self.lignes[self._idx(prefixe)] = nouveau

    def apres(self, prefixe, texte):
        i = self._idx(prefixe)
        self.lignes[i + 1:i + 1] = texte.split("\n")

    def avant(self, prefixe, texte):
        i = self._idx(prefixe)
        self.lignes[i:i] = texte.split("\n")

    def ajouter_fin_ligne(self, prefixe, texte):
        i = self._idx(prefixe)
        self.lignes[i] = self.lignes[i] + texte

    def sub_ligne(self, prefixe, motif, remplacement, flags=0):
        i = self._idx(prefixe)
        nouveau, n = re.subn(motif, remplacement, self.lignes[i], flags=flags)
        assert n >= 1, f"motif absent : {motif[:60]}"
        self.lignes[i] = nouveau

    def sub_global(self, motif, remplacement, attendu=None):
        s = "\n".join(self.lignes)
        s, n = re.subn(motif, remplacement, s)
        assert n >= 1 and (attendu is None or n == attendu), f"{n} occurrences de {motif[:60]}"
        self.lignes = s.split("\n")

    def remplacer_table(self, label, texte):
        """Remplace l'environnement table qui porte le label donné par `texte`."""
        bs = chr(92)
        i = next(k for k, l in enumerate(self.lignes) if (bs + "label{" + label + "}") in l)
        d = max(k for k in range(i) if self.lignes[k].startswith(bs + "begin{table}"))
        f = min(k for k in range(i, len(self.lignes)) if self.lignes[k].startswith(bs + "end{table}"))
        self.lignes[d:f + 1] = texte.split(chr(10))

    def remplacer_entre(self, debut, fin, texte):
        """Remplace les lignes de `debut` (inclus) à `fin` (exclu) ; les deux préfixes doivent être uniques."""
        i, j = self._idx(debut), self._idx(fin)
        assert i < j, "ordre inversé"
        self.lignes[i:j] = texte.split(chr(10))

    def remplacer_jusqua_suivant(self, debut, fin_prefixe, texte):
        """Remplace de `debut` (unique, inclus) jusqu'à la première ligne suivante commençant par `fin_prefixe` (exclue)."""
        i = self._idx(debut)
        j = next(k for k in range(i + 1, len(self.lignes)) if self.lignes[k].startswith(fin_prefixe))
        self.lignes[i:j] = texte.split(chr(10))

    def sauver(self):
        CHEMIN.write_text("\n".join(self.lignes), encoding="utf-8")
