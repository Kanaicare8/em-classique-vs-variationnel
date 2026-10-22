"""Remplace les tableaux saisis à la main de body.tex par les tableaux générés (tables/*.tex). À exécuter une seule fois."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from outils_patch import Corps

c = Corps()
CORRESPONDANCE = {
    "tab:1_2": "t1_2", "tab:1_4": "t1_4", "tab:1_5": "t1_5",
    "tab:2_5": "poids_em", "tab:2_6": "poids_vb", "tab:2_7": "t2_7", "tab:2_8": "t2_8", "tab:2_9": "t2_9",
    "tab:2_10": "t2_10", "tab:2_11": "t2_11", "tab:2_12": "t2_12", "tab:2_13": "t2_13", "tab:2_14": "t2_14",
    "tab:2_15": "t2_15", "tab:2_16": "t2_16",
}
for label, nom in CORRESPONDANCE.items():
    c.remplacer_table(label, "\\tableauGenere{" + nom + "}")
c.sauver()
print(len(CORRESPONDANCE), "tableaux remplacés par des tableaux générés")
