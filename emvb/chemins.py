"""Emplacements du projet, définis une seule fois : tout le code les importe d'ici."""

from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent      # racine du dépôt (le dossier qui contient emvb/)
DATA = RACINE / "data"                               # données publiques et leur provenance
RESULTATS = RACINE / "resultats"                     # tableaux produits par le code ; le magasin d'artefacts n'est pas versionné
MEMOIRE = RACINE / "memoire"                         # sources LaTeX, tableaux et figures inclus dans le mémoire
