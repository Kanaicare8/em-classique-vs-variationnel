"""Passe de révision de la section 2.2 et du chapitre 2 expérimental (T5.10, T5.11, T5.12). À exécuter une seule fois."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from outils_patch import Corps

c = Corps()

# ---------------------------------------------------------------- §2.2.1 : dimension
c.sub_ligne("Les deux algorithmes ont donc le même ordre de grandeur asymptotique par itération",
            r"En pratique, pour les valeurs de D rencontrées dans la plupart des applications \(D \$\\leq \$ 50\), ce surcoût reste acceptable au regard des bénéfices obtenus en matière de sélection de modèle\.",
            r"Les mesures de ce mémoire s'arrêtent à $D = 20$ (scénario S5, section 2.3.17) : toute affirmation sur des dimensions supérieures est \\emph{non testée}. Le surcoût doit en outre être évalué en temps total jusqu'au modèle final, et non par itération seule (section 2.2.3).")

# ---------------------------------------------------------------- §2.2.2 : singularités
c.remplacer_ligne("L'EM variationnel, en revanche, est intrinsèquement protégé contre ce type de dégénérescence",
                  r"""L'EM variationnel est, lui, doté d'une régularisation structurelle : le prior Normal-Wishart borne inférieurement la matrice d'échelle $W_k^{-1} \succeq W_0^{-1}$, ce qui empêche $\Lambda_k$ de diverger, et le prior de Dirichlet empêche $\pi_k$ de s'annuler exactement. Cette protection est une propriété du modèle, non un résultat mesuré : elle n'est pas démontrée par une expérience tant que la fréquence des ajustements dégénérés n'est pas comptée. Il faut de plus noter que l'implémentation de l'EM utilisée dans ce mémoire n'est pas non régularisée : elle ajoute $\varepsilon I$ avec $\varepsilon = 10^{-6}$ à chaque covariance (constante \texttt{REG\_EM}). Comparer « EM sans protection » et « VB protégé » serait donc inexact. Le scénario S6 (petit effectif, section 2.3.17) compte, pour chaque algorithme, la part d'ajustements dégénérés, définie par une valeur propre minimale de $\Sigma_k$ inférieure à $10^{-6}$ fois sa trace, ou un effectif $N_k < D+1$. Le tableau~\ref{tab:2_17} classe la robustesse aux singularités selon ce comptage.""")

# ---------------------------------------------------------------- §2.2.3 : ICL et économie de calcul
c.remplacer_ligne("où p(K) désigne le nombre de paramètres libres du modèle à K composantes.",
                  r"""où $p(K)$ désigne le nombre de paramètres libres du modèle à $K$ composantes. L'ICL (Biernacki, Celeux et Govaert, 2000) ajoute au BIC deux fois l'entropie des affectations :
\begin{equation}
\mathrm{ICL}(K) = \mathrm{BIC}(K) + 2\,\mathrm{EN}(K), \qquad \mathrm{EN}(K) = -\sum_{i=1}^{N}\sum_{k=1}^{K} r_{ik}\log r_{ik} \geq 0,
\tag{2.5b}
\label{eq:2_5b}
\end{equation}
ce qui pénalise les mélanges dont les composantes se chevauchent. Ces critères pénalisent la complexité du modèle, mais exigent un ajustement EM par valeur de $K$ candidate (et, en pratique, plusieurs initialisations par valeur). L'EM variationnel produit une solution en une exécution avec $K_{\max}$ fixé. Cette économie n'est toutefois pas acquise : une exécution variationnelle peut coûter plusieurs fois une exécution de l'EM, de sorte que le gain dépend du rapport entre le nombre d'ajustements EM d'un balayage et le surcoût d'un ajustement variationnel. Il se mesure en \emph{temps total jusqu'au modèle final}, balayage EM-BIC complet contre un ajustement variationnel (hypothèse H4, tableau~\ref{tab:cout_selection}), et non par une proportion du nombre de valeurs de $K$.""")
c.remplacer_ligne("Les deux critères atteignent leur minimum exactement à K = 3",
                  r"""Les deux critères atteignent leur minimum à $K = 3$ (valeur réelle) sur ce jeu, de sorte que la sélection externe par BIC ou AIC fonctionne lorsqu'elle est appliquée avec soin. Cette figure fixe la \emph{baseline pertinente} pour la suite : la comparaison utile n'est pas « EM avec $K = 6$ imposé contre VB avec $K_{\max} = 6$ » (situation volontairement défavorable à l'EM, section 2.3.7), mais « EM avec $K$ choisi par BIC ou ICL contre VB ». Le coût de cette baseline (un ajustement EM par valeur de $K$ et par initialisation) est comparé au coût d'un ajustement variationnel en temps total, jamais en proportion du nombre de valeurs de $K$ testées.""")

# ---------------------------------------------------------------- §2.3.1 : protocole commun
c.remplacer_ligne("Critère d'arrêt ($\\varepsilon $)",
                  r"Critère d'arrêt & Identique pour tous les algorithmes : variation relative du critère total $\leq 10^{-6}$ (log-vraisemblance pour l'EM et le MAP-EM, ELBO pour le VB en covariance pleine) \\")
c.remplacer_ligne("Nombre maximal d'itérations &",
                  r"Nombre maximal d'itérations & 500 étapes M pour tous les algorithmes ; une exécution qui atteint le plafond est marquée « non convergée » \\")
c.remplacer_ligne("Composante active &",
                  r"Composante active & $N_k \geq 1$ (convention historique, sensibilité mesurée au tableau~\ref{tab:S10}) et $N_k/N \geq 1\,\%$ dans les scénarios \\")
c.remplacer_ligne("Priors Normal-Wishart (empiriques) &",
                  r"Priors Normal-Wishart (« empiriques », Bayes empirique) & $m_{0}$ = moyenne des données, $\beta _{0}$ = 1, $\nu _{0}$ = D, $W_{0}^{-1}$ = covariance empirique : les données servent deux fois (priors et vraisemblance) \\")

# ---------------------------------------------------------------- §2.3.12 : aberrations
c.remplacer_ligne("Les deux algorithmes retrouvent une partition quasi parfaite sur les points non aberrants",
                  r"""Cette expérience, fondée sur un seul tirage (graine 7), n'est pas un test de robustesse : c'est une \emph{illustration d'un artefact de l'indicateur}. Avec $K = 6$ imposé, les composantes excédentaires de l'EM fragmentent les trois groupes réels sur données propres (ARI du tableau 2.7) ; en présence d'aberrations, elles sont absorbées par ces points isolés, et les trois groupes ne sont plus fragmentés. L'ARI hors aberrations remonte alors pour une raison qui tient à ce que font les composantes en trop, non à la qualité de l'algorithme. Il serait faux de lire dans le tableau 2.14 que « les deux algorithmes sont robustes » ou que le VB « absorbe mieux » les aberrations : la trace de sa composante diffuse est un résultat ambigu. Un test de robustesse exige au moins 30 tirages, des proportions et des amplitudes d'aberrations variées, et une comparaison avec la baseline EM-BIC (et, idéalement, une composante uniforme de fond) : c'est le scénario S7 de la section 2.3.18.""")

# ---------------------------------------------------------------- §2.3.13 : réplication
c.remplacer_ligne(r"\subsection{Réplication sur des jeux de données indépendants}",
                  r"\subsection{Réplication sur 30 tirages d'un même générateur}")
c.ajouter_fin_ligne("H1 est soutenue pour les deux jeux de priors",
                    r""" \par\medskip\noindent\textbf{Portée de ces hypothèses. }H1 et H2 sont quasi tautologiques et ne sont pas des tests de la thèse de ce mémoire : H2 compare le VB à un EM dont $K = 6$ est imposé, qui ne peut pas retrouver trois composantes par construction ; H1 porte sur 30 différences toutes de même signe, pour lesquelles un intervalle bootstrap n'apporte rien. Les 30 jeux proviennent en outre d'un seul générateur (trois gaussiennes isotropes séparées) : il s'agit d'une réplication statistique, non d'une réplication sur des schémas de génération différents. Les priors diffus (taux de succès inférieur) sont ceux qu'on utiliserait sans connaissance préalable, et le résultat des priors empiriques n'est pas une propriété du VB seul. Les hypothèses informatives sont celles des sections 2.3.14 à 2.3.19, qui comparent le VB à EM-BIC, EM-ICL et MAP-EM sur plusieurs générateurs, avec test apparié et marge d'équivalence.""")

# ---------------------------------------------------------------- nouvelles sous-sections 2.3.14 à 2.3.20
c.avant("\\section{Analyse des résultats et synthèse}", r"""\subsection{Grille de $\alpha_0$ autour du seuil $d/2$ (scénario S8)}
La grille du tableau 2.8 (0,001 à 10) saute la zone de transition. La grille $\alpha_0 \in \{1;\,1{,}5;\,2;\,2{,}5;\,3;\,5;\,10\}$ est donc évaluée pour les trois types de covariance, dont les seuils théoriques de Rousseau et Mengersen (2011) sont $d/2 = 2{,}5$ (pleine), $2$ (diagonale) et $1{,}5$ (sphérique) en dimension 2. L'hypothèse testée est que le nombre de composantes actives change de régime autour de ces seuils ; la théorie portant sur le posterior exact, l'observation d'un seuil ailleurs n'est pas une réfutation de la théorie mais une propriété du champ moyen. Résultats : tableau~\ref{tab:S8}. Le tableau indique la part d'exécutions non convergées, et pour les covariances non pleines le critère est une approximation (section 3.2.2).

\tableauGenere{S8_alpha0}

\subsection{Couverture des intervalles de crédibilité (hypothèse H6)}
La sous-estimation de variance du champ moyen (section 1.5.4) ne peut être jugée que par la couverture empirique des intervalles à 90 \% sur des jeux dont les paramètres vrais sont connus. Cette mesure est faite sur le jeu semi-synthétique du cas climatique (section 3.1.1), pour le VB et pour le bootstrap de l'EM ; la couverture empirique est rapportée avec son intervalle de Wilson au tableau~\ref{tab:climat_couverture}. Les intervalles de crédibilité et de confiance ne mesurent pas le même objet : leur couverture sur la valeur vraie est une comparaison de calibration, non de justesse bayésienne.

\tableauGenere{climat_couverture}

\subsection{Baseline EM-BIC, chevauchement, déséquilibre et sous-estimation de $K$ (S1 à S3)}
Chaque scénario compte au moins 30 réplications et compare, par test apparié, EM-$K$, EM-$K_{\max}$, EM-BIC, EM-ICL, MAP-EM et le VB (priors empiriques et diffus), avec le critère d'arrêt de la figure~\ref{fig:boucle_arret} (protocole de la figure~\ref{fig:protocole}). S1 fait varier la séparation de 1 à 5 écarts-types ; S2 fixe des poids de 80, 15 et 5 \% ; S3 impose un $K$ choisi (3) inférieur au $K$ vrai (4 à 6), ce qui borne aussi le $K_{\max}$ du VB. Les équivalences sont jugées par TOST avec une marge de 0,03 en ARI ; la correction de Holm est appliquée sur l'ensemble des tests de la grille.

\input{figures_tikz/protocole_comparaison}
\input{figures_tikz/boucle_arret}

\tableauGenere{S1_chevauchement}
\tableauGenere{S2_desequilibre}
\tableauGenere{S3_sous_estimation}

\subsection{Queues épaisses, dimension croissante et petit effectif (S4 à S6)}
S4 génère des composantes de Student à 3 degrés de liberté ; S5 fait varier $D$ dans $\{2, 5, 10, 20\}$ ; S6 fait varier $N$ de 30 à 1\,000 et rapporte le taux d'ajustements dégénérés (valeur propre minimale de $\Sigma_k$ inférieure à $10^{-6}$ fois sa trace, ou $N_k < D+1$) pour chaque algorithme. Comme le code de l'EM ajoute $\varepsilon I$ avec $\varepsilon = 10^{-6}$ (section 3.2.1), le taux mesuré est celui de l'EM régularisé.

\tableauGenere{S4_queues_epaisses}
\tableauGenere{S5_dimension}
\tableauGenere{S6_petit_N}

\subsection{Aberrations : proportion et amplitude variées (S7)}
Le scénario S7 remplace l'unique tirage de la section 2.3.12 par 30 tirages ou plus pour chaque couple (proportion, amplitude), avec la baseline EM-BIC.

\tableauGenere{S7_aberrations}

\subsection{Plan factoriel sur les priors et seuil d'activité (S9 et S10)}
Le plan factoriel fait varier $\alpha_0$, $\beta_0$, $\nu_0$ et l'échelle de $W_0$ ; la part de variance du nombre de composantes actives expliquée par chaque facteur est rapportée (tableau~\ref{tab:S9}). Le scénario S10 montre la sensibilité du nombre de composantes actives au seuil (0,5 \%, 1 \%, 5 \% de $N$, et $N_k \geq 1$) : tant que ce nombre dépend du seuil, il ne constitue pas une mesure fiable de $\hat K$.

\tableauGenere{S9_decomposition_variance}
\tableauGenere{S10_seuil_activite}

\subsection{Coût de la sélection de $K$ en temps total}
\tableauGenere{cout_selection}

\subsection{Métriques sans étiquette}
L'ARI suppose une vérité terrain et dépend du nombre de composantes. La silhouette n'est comparable qu'à $K$ égal. Le tableau des scénarios rapporte donc aussi la log-vraisemblance moyenne hors échantillon (plug-in pour tous les bras ; prédictive de Student en plus pour le VB, afin d'isoler l'effet de la loi prédictive) et le taux d'ajustements dégénérés.

""")

# ---------------------------------------------------------------- synthèse et grille (T5.12)
c.remplacer_ligne("L'étude expérimentale conduite dans ce chapitre confirme, sur un exemple concret et reproductible",
                  r"""L'étude conduite dans ce chapitre ne désigne pas un meilleur algorithme : elle décrit des déplacements. Le VB transfère la sélection de $K$ vers le choix de $K_{\max}$, des hyperparamètres et du seuil d'activité ; il fournit une incertitude approchée dont la couverture est mesurée ; il coûte plus par ajustement que l'EM, ce qui n'établit pas un coût plus élevé que le pipeline EM-BIC en temps total. Lorsque $K$ est correctement spécifié, les deux algorithmes sont de qualité comparable (à confirmer par équivalence, tableaux des scénarios S1 à S3). La comparaison à $K = 6$ imposé est défavorable à l'EM par construction et ne sert que d'illustration du mécanisme d'élagage.""")
c.remplacer_ligne("Le tableau 2.17 propose une synthèse globale",
                  r"Le tableau~\ref{tab:2_17} remplace les anciennes listes d'avantages et d'inconvénients par une grille « axe $\times$ preuve » : chaque ligne renvoie à une expérience, à un théorème, ou porte la mention « non testé ».")
c.remplacer_table("tab:2_17", r"\tableauGenere{grille_axe_preuve}")
c.sub_ligne("Cette synthèse met en évidence que le choix entre les deux algorithmes", r"\s*$", r" Aucune ligne de la grille n'autorise à parler de supériorité.")
c.apres("Une quatrième limite, de nature plus méthodologique", r"""
Une cinquième série de limites n'était pas reconnue dans la première version de ce chapitre et conditionne la lecture des sections 2.3.2 à 2.3.13 : (i) la baseline EM-BIC/ICL et le MAP-EM manquaient ; (ii) les critères d'arrêt de l'EM et du VB n'étaient pas comparables, ce qui affectait les nombres d'itérations et les temps (désormais harmonisés, section 2.3.1) ; (iii) le seuil $N_k \geq 1$ pour déclarer une composante active est arbitraire, et le nombre de composantes actives n'est pas une mesure fiable (S10) ; (iv) l'ARI à $K = 6$ est un artefact de la fragmentation des composantes excédentaires ; (v) les expériences sur les aberrations reposaient sur un seul tirage ; (vi) les singularités n'étaient pas comptées, et l'EM utilise une régularisation $\varepsilon I$ ; (vii) le seuil théorique $d/2$ de $\alpha_0$ n'avait pas été confronté à une grille adaptée.""")
c.sauver()
print("chapitre 2 révisé")
