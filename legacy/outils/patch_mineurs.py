"""Corrections mineures du chapitre 1 (relecture) : underflow, concavité en la précision, nature des exemples numériques."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from outils_patch import Corps

c = Corps()
c.sub_ligne("La stabilisation numérique du calcul des responsabilités",
            r"de sorte que exp\(\$a_\{k\}\$\) est numériquement indistinguable de zéro en précision flottante standard, ce qui provoquerait une division par zéro lors du calcul des responsabilités\.",
            r"de sorte que exp($a_{k}$) peut sous-déborder vers zéro. Le seuil dépend de la précision : en double précision (float64) exp($a$) s'annule pour $a \\lesssim -745$, donc -500 ne pose pas de problème ; en simple précision (float32) le seuil est d'environ $-88$ et -500 provoquerait une division par zéro lors du calcul des responsabilités. L'astuce du log-sum-exp reste indispensable dès que les log-densités sont très négatives (grande dimension, composantes éloignées).")
c.sub_ligne("Cette dérivation complète met en évidence un point important",
            r"est concave séparément en chacun des trois blocs de paramètres \(\$\\pi \$, \$\\mu \$, \$\\Sigma \$\)\.",
            r"est concave séparément en $\\pi$ (à contrainte de somme fixée), en $\\mu$ et en la matrice de \\emph{précision} $\\Lambda = \\Sigma^{-1}$ (et non en $\\Sigma$ elle-même).")
c.sub_ligne("Ce parcours théorique n'a pas été conduit de façon purement abstraite",
            r"a été systématiquement illustrée par un exemple numérique entièrement calculé",
            r"a été illustrée par un exemple numérique (calculé à la main pour la densité du GMM et la conjugaison Dirichlet--Catégorielle ; produit par le code et vérifié pour les tableaux 1.2, 1.4 et 1.5)")
c.sauver()
print("corrections mineures appliquées")
