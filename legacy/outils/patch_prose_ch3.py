"""Commentaires du chapitre 3 (cas climatique, S&P 500, pLSA contre LDA) rédigés après lecture des tableaux générés.
Les nombres cités sont ceux des tableaux ; les décisions suivent les critères fixés avant l'analyse. À exécuter une seule fois."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from outils_patch import Corps

c = Corps()

# ----------------------------------------------------------------------- cas climatique
c.remplacer_ligne(r"\textbf{Résultats. }Les décisions sont lues dans la grille générée",
                  r"""\textbf{Résultats. }Les moyennes par effectif et par bras figurent au tableau~\ref{tab:climat_sous} (données réelles) et au tableau~\ref{tab:climat_semi} (jeu semi-synthétique) ; les décisions sur H1 à H8 sont au tableau~\ref{tab:climat_grille} et la couverture des intervalles au tableau~\ref{tab:climat_couverture}. Les écarts aux effectifs prévus sont les suivants : 40 sous-échantillons par effectif au lieu de 100, 60 jeux semi-synthétiques par effectif (15 à $N=2\,000$) au lieu de 200, 50 réplicats de bootstrap pour la couverture, par limite de temps de calcul ; les sous-échantillons de $D=19$ sont au nombre de 20 pour trois effectifs seulement. Les cartes sont à la figure~\ref{fig:climat_cartes}.""")
c.apres(r"\tableauGenere{climat_grille}", r"""
\tableauGenere{climat_sous}
\tableauGenere{climat_semi}

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{figures/climat_classes.png}
\caption{Classes de Köppen--Geiger (référence) et classes retrouvées par EM-BIC et par le VB à priors empiriques sur les 21\,846 cellules du Cameroun (WorldClim 2.1, 2,5 minutes d'arc). Contour : Natural Earth ; couleurs arbitraires, non comparables d'une carte à l'autre.}
\label{fig:climat_cartes}
\end{figure}
\begin{figure}[H]
\centering
\includegraphics[width=0.9\textwidth]{figures/climat_incertitude.png}
\caption{Responsabilité maximale (haut) et entropie d'affectation (bas) de EM-BIC et du VB : les zones de transition climatique ont une entropie élevée.}
\label{fig:climat_incertitude}
\end{figure}

\textbf{Lecture. }(i) \emph{Cohérence avec le zonage.} L'ARI contre Köppen--Geiger est faible pour tous les bras et tous les effectifs (de l'ordre de 0,1 à 0,17, tableau~\ref{tab:climat_sous}) : aucune des méthodes ne retrouve la structure de Köppen--Geiger à partir de ces cinq variables, et la différence entre méthodes est petite devant ce niveau commun. La référence est définie par des seuils sur des climatologies mensuelles, non par des amas gaussiens de $(\mathrm{bio1}, \mathrm{bio4}, \log\mathrm{bio12}, \mathrm{bio15}, \text{altitude})$ ; à $N \geq 500$, BIC et ICL retiennent le $K_{\max} = 10$ tout entier, ce qui indique que le critère continue de décroître au-delà de la plage testée (borne supérieure à repousser, non testé). Les cartes montrent des classes organisées par l'altitude et le gradient nord-sud, avec une entropie d'affectation élevée dans les zones de transition. Le zonage agro-écologique officiel étant indisponible, la comparaison avec lui n'a pas pu être faite.

(ii) \emph{Sélection de $K$ (H1).} Sur le jeu semi-synthétique ($K_{\text{réf}}=5$), l'erreur $\lvert\hat K-5\rvert$ du VB à priors empiriques est inférieure à celle de EM-BIC et EM-ICL aux effectifs 30 et 60 (ces deux critères retiennent presque $K_{\max}$), supérieure à $N=120$, et équivalente (nulle) à $N \geq 500$, où tous retrouvent $K=5$. Le VB n'est donc pas supérieur : son avantage se limite aux très petits effectifs, où tous les ajustements sont dégénérés (H3) et où l'ARI est faible pour toutes les méthodes (tableau~\ref{tab:climat_semi}).

(iii) \emph{Qualité à grand $N$ (H2).} À $N=2\,000$ sur les données réelles, EM-BIC est supérieur au VB à priors empiriques pour l'ARI contre Köppen--Geiger (écart faible) et pour la log-vraisemblance hors bloc (écart de l'ordre de 0,3 nat par observation) : l'équivalence est rejetée dans le sens défavorable au VB. L'écart tient vraisemblablement à la flexibilité de EM-BIC, qui utilise les dix composantes avec une régularisation $\varepsilon I$, alors que les priors empiriques du VB contraignent chaque composante (explication non testée). À $N$ complet, il n'y a qu'une exécution (descriptif).

(iv) \emph{Petit $N$ et dégénérescence (H3).} Pour $N \leq 120$, presque tous les ajustements des deux familles ont au moins une composante dégénérée ($N_k < D+1$) : la différence n'est pas décidable (H3 non soutenue, tableau~\ref{tab:climat_grille}). Les VB à priors diffus sont moins touchés à $N=120$ (tableau~\ref{tab:climat_sous}), mais cette comparaison n'était pas celle qui a été fixée. En revanche, la log-vraisemblance hors bloc de l'EM est catastrophique aux petits effectifs (valeurs très négatives), alors que MAP-EM et VB restent raisonnables : les priors suffisent à stabiliser l'estimation, ce que montre déjà le MAP-EM (même régularisation, sans distribution sur $\theta$). Le VB à loi prédictive de Student a ensuite une log-vraisemblance supérieure à son évaluation plug-in aux petits effectifs : l'effet de la loi prédictive est séparé de celui des priors.

(v) \emph{Coût (H4).} Le temps médian du pipeline EM-BIC est supérieur à celui d'un VB à dix initialisations pour tous les effectifs, avec des intervalles bootstrap au-dessus de 1 (rapport de 1,1 à 4,1 selon $N$ ; à $N$ complet, une exécution donne un rapport voisin de 8). L'économie de calcul du VB sur la sélection de $K$ est donc établie ici, à la condition que la baseline soit un balayage complet avec dix initialisations par valeur de $K$.

(vi) \emph{Hyperparamètres (H5).} La variance de $\hat K$ due aux priors (plan factoriel) est supérieure à celle de EM-BIC due à l'initialisation : le VB ne supprime pas la sensibilité, il la déplace vers les hyperparamètres (expérience unique à $N=500$).

(vii) \emph{Incertitude (H6).} Voir le tableau~\ref{tab:climat_couverture} : sous-couverture des poids du VB, couverture compatible avec 90 \% pour ses moyennes, bootstrap de l'EM plus proche du nominal.

(viii) \emph{Chevauchement et dimension (H7, H8).} À $N=2\,000$, le VB à priors empiriques ne fusionne pas plus de composantes que EM-BIC ($\hat K = 5$ pour tous, hors EM-$K_{\max}$ et MAP-EM) : H7 n'est pas soutenue sur le jeu semi-synthétique ; elle n'a pas pu être testée sur les zones réelles. H8 est traitée pour la dégénérescence seule à $D=19$ (lignes H8 du tableau~\ref{tab:climat_grille}) ; l'accroissement de la dépendance aux priors n'a pas été testé à $D=19$.

\textbf{Conclusion du cas. }Sur ces données, le VB n'améliore ni la cohérence avec Köppen--Geiger ni la qualité à grand $N$ ; il se distingue par un pipeline moins coûteux que EM-BIC en temps total, par une stabilité de l'estimation aux petits effectifs qui est largement due à la régularisation par les priors (le MAP-EM l'obtient aussi), et par une incertitude dont la couverture est insuffisante pour les poids.""")

# ----------------------------------------------------------------------- S&P 500 : lecture
c.remplacer_ligne(r"\textbf{Lecture. }Les décisions se lisent dans les tableaux générés",
                  r"""\textbf{Lecture. }(H4) Les mélanges (EM-BIC à $K=4$ en plug-in, VB en loi prédictive) et la loi de Student obtiennent une log-vraisemblance moyenne hors échantillon supérieure à celle de la gaussienne d'environ 0,04 à 0,05 nat par jour ; les tests de Diebold--Mariano (tableau~\ref{tab:sp500_dm}) ne rejettent pas l'égalité au seuil de 5 \% (probabilités critiques de 0,08 à 0,12, supérieures après correction de Holm) : \emph{H4 n'est pas soutenue}, la direction est celle attendue mais l'écart n'est pas significatif. Le GARCH(1,1) à innovations de Student est nettement supérieur à tous les modèles i.i.d., mélanges compris. L'évaluation prédictive du VB ne diffère pas de son évaluation plug-in (différence nulle à la précision du tableau, DM non significatif) : l'avantage supposé de la loi prédictive n'apparaît pas sur ces données.

(H5) La VaR gaussienne à 1 \% est franchie 20 fois pour 11,9 attendues, et le test de Kupiec la rejette au seuil de 5 \% (probabilité critique de 0,032) : H5 est soutenue. À 1 \%, les mélanges sont trop prudents (5 ou 6 exceptions pour 11,9 attendues) ; le test de Kupiec rejette la prédictive du VB (5 exceptions) mais pas le plug-in du VB ni l'EM (6 exceptions, probabilité critique de 0,056) : une exception d'écart suffit à franchir le seuil, de sorte que l'affirmation antérieure « VB mieux calibré à 1 \% » est retirée. À 5 \%, les mélanges sont bien calibrés (Kupiec non rejeté) alors que la gaussienne est trop prudente (41 exceptions pour 59,7 attendues) ; la Student et le GARCH-t sont, eux, trop souvent franchis à 5 \% (Kupiec rejeté). Le test d'indépendance de Christoffersen rejette à 1 \% la gaussienne, la Student, la simulation historique, EM et VB (exceptions groupées), et ne rejette ni le GARCH-t ni le HMM filtré, dont la couverture conditionnelle n'est pas rejetée. Pour l'ES (Acerbi--Székely), les statistiques $Z_2$ des mélanges, de la Student et de la simulation historique sont négatives à 1 \% (ES surestimée, prudence) et celle de la gaussienne positive (queue sous-estimée) ; elles ne sont pas accompagnées de probabilité critique.

Ces résultats se lisent avec le changement de régime : la kurtosis excédentaire passe de 22,7 (apprentissage, krach de 2020 compris) à 6,5 (évaluation), de sorte qu'une VaR calée sur 2016-2021 est prudente par construction. Les modèles à volatilité conditionnelle (GARCH-t, HMM filtré) sont les mieux calibrés à 1 \% (couverture conditionnelle non rejetée) : la volatilité en grappes explique plus que le choix entre EM et VB.

(H6) L'intervalle de crédibilité à 95 \% de la VaR à 1 \% du VB est plus étroit que l'intervalle bootstrap de l'EM (1 000 réplicats) d'environ un tiers, aux deux niveaux (tableau~\ref{tab:sp500_int}). Les deux objets diffèrent et la couverture n'est pas évaluée sur ces données ; elle l'est, pour les poids et les moyennes, sur le jeu semi-synthétique du cas climatique, où le VB sous-couvre les poids.""")

# ----------------------------------------------------------------------- texte : lecture
c.apres(r"\tableauGenere{texte_grille}", r"""
\textbf{Lecture. }L'hypothèse est soutenue en ce qui concerne le surapprentissage mesuré par l'écart relatif entre perplexité hors échantillon et perplexité d'apprentissage : le pLSA sur-apprend davantage que la LDA à chaque taille, l'écart relatif diminue quand $N$ croît, et la différence appariée (pLSA moins LDA) est significative aux trois tailles (tableau~\ref{tab:texte_grille} ; la plus petite probabilité critique atteignable avec 10 réplications est de 0,005). À $N=50$, la perplexité hors échantillon du pLSA est plus de sept fois celle de la LDA, avec une part de mots à probabilité nulle (plancher) de l'ordre de 12 \%. En revanche, le pLSA n'est pas moins bon en tout : à $N=1\,000$, sa perplexité hors échantillon est \emph{inférieure} à celle de la LDA, et sa cohérence NPMI et sa pureté sont supérieures à celles de la LDA aux trois tailles (tableau~\ref{tab:texte}). Deux réserves s'imposent. D'abord, la LDA du code lisse $\beta$ (constante de lissage de $10^{-3}$) et le pLSA ne le fait pas ; une partie de l'écart à $N=50$ vient des probabilités nulles du pLSA et non seulement du prior sur $\theta_d$. Ensuite, une part des exécutions du pLSA n'est pas convergée au plafond de 150 étapes M (colonne « Non convergés »), et seules dix réplications par taille ont été faites.""")
c.sauver()
print("prose du chapitre 3 rédigée")
