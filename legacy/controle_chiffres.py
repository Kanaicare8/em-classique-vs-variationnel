"""
Contrôle de cohérence texte / code (phase 6) : liste les nombres saisis dans la prose de body.tex.

Usage : python controle_chiffres.py   -> écrit resultats/controle_chiffres.txt et affiche le décompte.

Un nombre dans la prose n'est acceptable que s'il (a) est une définition (paramètre de protocole,
seuil, hypothèse fixée avant l'analyse), (b) renvoie à une section, une équation, une référence, ou
(c) est lu dans un fichier de résultats. Le script signale les candidats (valeurs décimales
avec virgule, pourcentages, rapports « x »), hors mathématiques en ligne, équations et références.
Il faut les relire un à un : ceux de type (c) doivent être remplacés par un renvoi au tableau généré.
"""

import re
from pathlib import Path

RACINE = Path(__file__).parent
texte = RACINE.joinpath("body.tex").read_text(encoding="utf-8").split("\n")
motif = re.compile(r"(?<![\w.])(?:[-+]?\d+,\d+|\d+\s?\\?%|\\times\s?\d[\d,]*|×\s?\d[\d,]*)")
sortie = []
dans_env = 0
for i, l in enumerate(texte, 1):
    if re.match(r"\\begin\{(equation|align|lstlisting|tabular|longtable|table)", l):
        dans_env += 1
    if dans_env == 0 and l and not l.startswith(("\\", "%")):
        brut = re.sub(r"\$[^$]*\$", " ", l)
        brut = re.sub(r"\((?:équation|éq\.)\s*[\d.]+\)|(?:section|sections|tableau|figure|équation|chapitre|annexe)\s+[\d.]+", " ", brut)
        trouves = motif.findall(brut)
        if trouves:
            sortie.append(f"{i}: {', '.join(t.strip() for t in trouves[:8])} | {brut.strip()[:110]}")
    if re.match(r"\\end\{(equation|align|lstlisting|tabular|longtable|table)", l):
        dans_env = max(0, dans_env - 1)
(RACINE / "resultats").mkdir(exist_ok=True)
RACINE.joinpath("resultats", "controle_chiffres.txt").write_text("\n".join(sortie), encoding="utf-8")
print(f"{len(sortie)} lignes de prose contiennent des nombres à vérifier (voir resultats/controle_chiffres.txt)")
