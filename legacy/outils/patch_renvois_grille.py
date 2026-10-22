"""Relie chaque avantage et chaque inconvénient du chapitre 1 à une ligne de la grille du tableau 2.17 (phase 6). À exécuter une seule fois."""
from pathlib import Path

R = Path(__file__).resolve().parent.parent

# 1. deux lignes supplémentaires dans la grille
p = R / "tex_tables.py"
s = p.read_text(encoding="utf-8")
ancre = '        ("Optima locaux de l\'ELBO", "Fréquence des optima locaux du VB", None, "non testé", "—"),'
assert ancre in s
s = s.replace(ancre, '        ("Initialisation", "Sensibilité du nombre de composantes actives à l\'initialisation (20 graines)", ("06_initialisation.csv", None), "expérience unique", "§2.3.9"),\n'
              '        ("Consistance de la sélection de $K$", "Garantie de consistance du champ moyen pour $K$", None, "non testé", "§1.7.9 ; théorie sur le posterior exact seulement"),\n' + ancre, 1)
p.write_text(s, encoding="utf-8")

# 2. paragraphes de renvoi après chacune des quatre listes
b = R / "body.tex"
L = b.read_text(encoding="utf-8").split("\n")


def apres_liste(titre, texte):
    i = next(k for k, l in enumerate(L) if l.startswith(titre))
    j = next(k for k in range(i, len(L)) if L[k].startswith(r"\end{itemize}"))
    L[j + 1:j + 1] = [texte]


apres_liste(r"\subsection{Avantages de l'EM classique}",
            r"\par\noindent\emph{Renvois à la grille du tableau~\ref{tab:2_17} :} garantie de croissance $\to$ ligne « Monotonie du critère » (théorème, tests unitaires) ; efficacité par itération et convergence rapide loin de l'optimum $\to$ « Coût de calcul » ; simplicité, applicabilité universelle et données incomplètes $\to$ affirmations qualitatives ou théoriques sans ligne expérimentale (« non testé » dans ce mémoire).")
apres_liste(r"\subsection{Inconvénients et limites de l'EM classique}",
            r"\par\noindent\emph{Renvois à la grille du tableau~\ref{tab:2_17} :} optima locaux $\to$ « Initialisation » (expérience unique) ; $K$ à fixer $\to$ « Sélection de $K$ », « Sous-estimation de $K$ » ; incertitude non native $\to$ « Incertitude » ; singularités $\to$ « Singularités, petit $N$ » et « Convergence de l'EM pour le GMM » ; lenteur et scalabilité $\to$ « Coût de calcul ».")
apres_liste(r"\subsection{Avantages de l'EM variationnel}",
            r"\par\noindent\emph{Renvois à la grille du tableau~\ref{tab:2_17} :} incertitude $\to$ « Incertitude » et « Gestion du risque » ; sélection automatique de $K$ $\to$ « Sélection de $K$ », « Seuil d'élagage » ; régularisation et robustesse $\to$ « Singularités, petit $N$ », « Valeurs aberrantes » ; ELBO et monotonie $\to$ « Monotonie du critère » ; extensibilité (VAE, flux normalisants) $\to$ « Vitesse de VAE, flux normalisants, gradient naturel » (non testé).")
apres_liste(r"\subsection{Inconvénients et limites de l'EM variationnel}",
            r"\par\noindent\emph{Renvois à la grille du tableau~\ref{tab:2_17} :} biais d'approximation $\to$ « Biais d'approximation » et « Incertitude » (couverture) ; sensibilité aux priors $\to$ « Sensibilité aux priors », « Seuil d'élagage » ; optima locaux de l'ELBO $\to$ « Optima locaux de l'ELBO » (non testé) ; coût par itération $\to$ « Coût de calcul » ; irréversibilité de l'élagage, dépendance à $K_{\max}$, consistance, double usage des données $\to$ lignes homonymes (« non testé » ou « expérience unique ») ; complexité d'implémentation et conjugaison $\to$ affirmations qualitatives sans ligne expérimentale.")
b.write_text("\n".join(L), encoding="utf-8")
print("renvois à la grille ajoutés")
