"""Passe de révision du chapitre 3 (T5.13) : climat du Cameroun en cas principal, S&P 500 en cas secondaire,
pLSA contre LDA, vision, bio-informatique et recommandation en revue de littérature. À exécuter une seule fois."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from outils_patch import Corps

c = Corps()

# ------------------------------------------------------------------ cadrage de la section
c.remplacer_ligne("Les modèles à variables latentes ajustés par EM, sous sa forme classique ou variationnelle, trouvent des applications",
                  r"""Ce chapitre distingue trois statuts de preuve. Le \emph{cas principal} (régimes climatiques du Cameroun) est conçu pour tester ensemble les avantages et les inconvénients du sujet sur des données réelles à structure chevauchante, déséquilibrée et non gaussienne. Le \emph{cas secondaire} (rendements du S\&P 500) évalue la gestion du risque avec des données réelles mais une période de test marquée par un changement de régime. Une \emph{comparaison pLSA contre LDA} sur corpus réel traite le cadre des modèles de thèmes. Les autres domaines (vision, bio-informatique, recommandation) sont présentés en \emph{revue de la littérature} : aucune expérience n'y est conduite, et les affirmations qui n'ont ni source ni test sont signalées comme « non testé ».""")
c.remplacer_ligne("Le fil conducteur de cette revue applicative est le même que celui qui a guidé l'ensemble de ce mémoire",
                  r"""Le fil conducteur est la thèse de ce mémoire : le VB ne « bat » pas l'EM ; il déplace la sélection de $K$ vers le choix des hyperparamètres, apporte une incertitude approchée, au prix d'un coût et d'une sensibilité aux priors. Le choix entre les deux dépend des contraintes opérationnelles (temps de calcul, confiance dans $K$, besoin d'une incertitude en aval, robustesse requise), et chaque lien entre une contrainte et un algorithme doit être soutenu par la grille du tableau~\ref{tab:2_17}.""")

# ------------------------------------------------------------------ cas principal : climat du Cameroun
c.apres("Le fil conducteur est la thèse de ce mémoire", r"""
\subsection{Cas principal : régimes climatiques du Cameroun}
\textbf{Question. }Le Cameroun est officiellement découpé en cinq zones agro-écologiques (soudano-sahélienne, hautes savanes guinéennes, hauts plateaux de l'Ouest, forêt à pluviométrie monomodale, forêt à pluviométrie bimodale). À partir de variables climatiques et d'altitude seulement, sans connaître $K$, (i) l'EM classique, avec $K$ choisi par BIC ou ICL, et l'EM variationnel avec élagage retrouvent-ils une structure cohérente avec un zonage ? (ii) Dans quelles conditions (effectif, dimension, chevauchement, déséquilibre, besoin d'incertitude, budget de calcul) l'un est-il préférable ? (iii) Les intervalles de crédibilité du VB sont-ils fiables (couverture) ou trop étroits ? Ce cas teste ensemble les avantages et les inconvénients du sujet sur des données réelles à structure chevauchante, déséquilibrée et non gaussienne.

\textbf{Données. }Climat : WorldClim 2.1 (climatologies 1970-2000, résolution de 2,5 minutes d'arc, soit environ 4,6 km), archives GeoTIFF \texttt{wc2.1\_2.5m\_bio.zip} et \texttt{wc2.1\_2.5m\_elev.zip} (Fick et Hijmans, 2017). La licence autorise l'usage académique et non commercial et \emph{interdit la redistribution sans autorisation} : les fichiers ne sont pas versionnés avec le code, que le script \texttt{cas\_pratique\_climat.py --preparer} télécharge, en journalisant la date et l'empreinte SHA-256 des archives. Variables ($D=5$) : température moyenne annuelle (bio1), saisonnalité de la température (bio4), précipitations annuelles en logarithme (bio12), saisonnalité des précipitations (bio15), altitude ; extension à $D=19$ (toutes les variables bioclimatiques et l'altitude). Les données sont standardisées et identiques pour tous les algorithmes.

\textbf{Références. }(a) Les zones agro-écologiques officielles ($K_{\text{réf}}=5$) : aucun shapefile téléchargeable n'a été trouvé (une carte de l'IRAD, 2005, n'est publiée qu'en figure) ; le script accepte un fichier fourni par l'utilisateur (option \texttt{--zones}) et, \emph{à défaut, la référence est Köppen--Geiger seul}, ce que les tableaux indiquent. (b) Köppen--Geiger (Beck et al., 2018), carte à 1 km, dont la licence doit être confirmée sur la page de distribution avant tout dépôt. Les étiquettes sont elles-mêmes définies à partir du climat : l'ARI mesure la cohérence avec un zonage, non une vérité ; c'est pourquoi la log-vraisemblance hors bloc, sans étiquette, est rapportée.

\textbf{Bras. }EM-5 ($K$ connu), EM-10 ($K$ trop grand), EM-BIC et EM-ICL ($K$ de 1 à 10), MAP-EM (mêmes priors que le VB, $K=10$), VB à priors empiriques et à priors diffus ($K_{\max}=10$, $\alpha_0 = 1/K_{\max}$), et une grille de VB sur $(\alpha_0, \beta_0, \nu_0, W_0)$. Mêmes critère d'arrêt (figure~\ref{fig:boucle_arret}), 10 initialisations par ajustement, covariance pleine, graines fixées. Une composante est active si $N_k/N \geq 1\,\%$ (sensibilité aux seuils de 0,5, 1 et 5 \%, et $N_k \geq 1$).

\textbf{Plan d'échantillonnage. }Les cellules voisines sont corrélées : pour $N \in \{30, 60, 120, 500, 2\,000\}$ et le jeu complet, 100 sous-échantillons espacés d'une distance minimale sont tirés, et l'évaluation hors échantillon se fait par blocs d'environ 100 km (figure~\ref{fig:echant_spatial}). Un jeu semi-synthétique complète le dispositif : un modèle à $K=5$ est ajusté à $N$ complet, puis 200 jeux de taille $N$ sont simulés à partir de lui, de sorte que la vérité (paramètres, chevauchement, déséquilibre) est connue et réaliste.

\input{figures_tikz/echantillonnage_spatial}

\textbf{Hypothèses, fixées avant les résultats. }Chacune peut être rejetée dans un sens ou dans l'autre, l'équivalence est une issue légitime, et la correction de Holm est appliquée sur l'ensemble des tests.

\begin{table}[H]
\centering
\small
\setlength{\tabcolsep}{0.1cm}
\begin{tabular}{|p{0.9cm}|p{2.6cm}|p{5.4cm}|p{5.6cm}|}
\hline
\textbf{N°} & \textbf{Axe} & \textbf{Hypothèse} & \textbf{Critère de décision} \\
\hline
H1 & Sélection de $K$ & VB et EM-BIC/ICL ne diffèrent pas de plus de 0,5 composante de $K_{\text{réf}}=5$ (semi-synthétique) & IC bootstrap à 95 \% de la différence de $\lvert\hat K - K_{\text{réf}}\rvert$ dans $[-0{,}5;\,0{,}5]$, Wilcoxon apparié \\
\hline
H2 & Qualité à $N$ complet & ARI et log-vraisemblance hors bloc équivalents (marges $\pm0{,}03$ en ARI, $\pm0{,}02$ nat par observation) & TOST, IC par blocs spatiaux \\
\hline
H3 & Petit $N$ & VB : moins d'ajustements dégénérés que EM-10 pour $N \leq 120$ & Test exact de Fisher, par $N$ \\
\hline
H4 & Coût & Le pipeline EM-BIC (K de 1 à 10, 10 initialisations) coûte plus qu'un VB à 10 initialisations & Rapport des temps médians avec IC ; décision si le ratio est supérieur à 1 \\
\hline
H5 & Hyperparamètres & La variance de $\hat K$ du VB due aux priors est au moins égale à celle de l'EM due à l'initialisation & Décomposition de variance sur le plan factoriel \\
\hline
H6 & Incertitude & Couverture des intervalles de crédibilité à 90 \% du VB inférieure à 90 \% ; le bootstrap de l'EM est plus proche du nominal & Couverture empirique, IC de Wilson, 200 jeux semi-synthétiques \\
\hline
H7 & Chevauchement & Le VB fusionne plus de zones voisines que EM-BIC & Matrice de confusion, nombre de zones fusionnées, ARI par zone \\
\hline
H8 & Dimension & À $D=19$, l'avantage du VB en dégénérescence croît, au prix d'une dépendance accrue aux priors & Mêmes mesures que H3 et H5 \\
\hline
\end{tabular}
\caption{Hypothèses du cas climatique et critères de décision (fixés avant l'analyse)}
\label{tab:climat_hypotheses}
\end{table}

\textbf{Résultats. }Les décisions sont lues dans la grille générée (tableau~\ref{tab:climat_grille}) ; la couverture des intervalles est au tableau~\ref{tab:climat_couverture}. Les cartes des classes, des responsabilités et de l'entropie d'affectation sont produites par le script (dossier \texttt{resultats/climat/}) ; elles montrent les zones de transition climatique, où l'incertitude d'affectation est élevée. Une composante n'est pas « une zone » par construction : toute lecture agronomique reste à valider avec un expert du domaine.

\tableauGenere{climat_grille}

\textbf{Limites. }La dépendance spatiale viole l'hypothèse i.i.d. du mélange (l'espacement et les blocs l'atténuent sans la supprimer) ; la circularité partielle des étiquettes est traitée par le critère hors bloc ; certaines variables restent bornées ou asymétriques malgré le logarithme ; un grand nombre de cellules rend les tests très puissants, d'où les marges d'équivalence ; les résultats portent sur le Cameroun et ne se généralisent pas par défaut à l'Afrique centrale (à tester). Si le zonage officiel n'est pas disponible, seul Köppen--Geiger sert de référence.
""")

# ------------------------------------------------------------------ NLP : pLSA contre LDA
c.remplacer_entre(r"\subsection{Traitement automatique du langage naturel}", r"\subsection{Vision par ordinateur}", r"""\subsection{Cas : pLSA contre LDA sur un corpus réel}
\textbf{Niveaux d'inférence. }La LDA de Blei, Ng et Jordan (2003) est présentée à tort comme un exact analogue du GMM bayésien. Au sens de la figure~\ref{fig:trois_niveaux}, la LDA du code est un \emph{EM variationnel à $\theta$ ponctuel} : $q(\theta_d)$ est un Dirichlet (paramètres $\gamma_d$), mais les distributions de mots par thème $\beta_k$ sont des paramètres ponctuels estimés à l'étape M et $\alpha$ est fixé. Elle n'est pas un VB complet. La correspondance avec le GMM est donc partielle : $\gamma_k \leftrightarrow \alpha_k$ vaut pour les poids de mélange ($\theta_d$ joue le rôle de $\pi$ par document), mais $\beta_k$ n'a pas de prior (contrairement à $(\mu_k,\Lambda_k)$ dans le GMM bayésien). Le comparateur « EM classique » de la LDA est le pLSA (Hofmann, 1999), qui estime $\theta_d$ et $\phi_k$ par maximum de vraisemblance sans prior.

\input{figures_tikz/plsa_lda}

\textbf{Hypothèse, fixée avant l'analyse. }Le pLSA sur-apprend davantage que la LDA quand le nombre de documents $N$ est petit (le prior de Dirichlet sur $\theta_d$ est la raison d'être de la LDA) ; l'écart se réduit quand $N$ croît. Elle est testée par la différence appariée, par $N \in \{50, 200, 1\,000\}$, de l'écart relatif entre perplexité hors échantillon et perplexité sur les documents d'apprentissage.

\textbf{Données et protocole. }Sous-ensemble de 20 Newsgroups (quatre groupes : \texttt{sci.space}, \texttt{rec.sport.baseball}, \texttt{talk.politics.mideast}, \texttt{comp.graphics}), obtenu par \texttt{sklearn.datasets.fetch\_20newsgroups} ; jeu de diffusion libre pour la recherche, sans licence explicite (à citer : Lang, 1995). Prétraitement : minuscules, suppression des en-têtes, citations et signatures, ponctuation et chiffres, mots vides (liste anglaise de scikit-learn), racinisation de Porter, vocabulaire de 1\,500 mots présents dans au moins cinq documents. La perplexité hors échantillon est calculée par complétion de document (la moitié des mots d'un document sert à estimer $\theta_d$, l'autre à l'évaluer, de façon identique pour les deux modèles) ; la cohérence des thèmes est mesurée par le NPMI des dix premiers mots ; la pureté est calculée par rapport aux étiquettes du corpus. Les deux modèles partagent le critère d'arrêt de la figure~\ref{fig:boucle_arret}. Les probabilités sont planchées à $10^{-12}$ et la part de mots planchés est rapportée.

\tableauGenere{texte_plsa_lda}
\tableauGenere{texte_grille}

Cette expérience remplace la démonstration sur douze phrases des versions précédentes de ce travail, qui ne comparait pas deux algorithmes et dont les thèmes étaient instables. Le corpus de test est un seul tirage de 600 documents ; les résultats dépendent du prétraitement et du nombre de thèmes ($K=4$, égal au nombre de groupes), ce qui borne leur portée.

""")

# ------------------------------------------------------------------ vision et bio-informatique : revue de littérature
c.remplacer_entre(r"\subsection{Vision par ordinateur}", r"\subsection{Finance}", r"""\subsection{Domaines d'usage : vision, bio-informatique (revue de la littérature)}
Ces deux domaines ne font l'objet d'aucune expérience dans ce mémoire. Ce qui suit est une revue : toute affirmation sans source est marquée « non testé ».

\textbf{Vision par ordinateur. }Les mélanges gaussiens servent à la segmentation d'images (chaque pixel est décrit par sa couleur ou une texture, $D=3$ ou davantage) ; le nombre $N$ de pixels peut dépasser le million, ce qui replace la scalabilité au centre du choix de l'algorithme. Dans l'algorithme de soustraction de fond de Stauffer et Grimson (1999), chaque pixel est modélisé par un petit mélange de gaussiennes mis à jour de façon incrémentale par une heuristique inspirée de l'EM online (et non exactement l'EM online) : le taux d'apprentissage $\rho$ est fixé et les composantes de poids élevé et de faible variance sont classées comme fond. Cette règle utilise l'interprétation des poids comme fréquences d'occurrence (section 1.6.2.c). L'affirmation que l'EM classique convient mieux au temps réel et l'EM variationnel à la segmentation hors ligne n'a pas été testée ici : \emph{non testé}.

\textbf{Bio-informatique. }Les modèles de mélange servent à identifier des sous-populations dans des données d'expression génique (cellule unique), pour lesquelles le nombre de sous-populations est souvent l'objet de l'étude. La dimension ($D$ de l'ordre du millier de gènes) rend la covariance pleine impraticable pour les deux algorithmes : le coût est en $KD^3$ et les effectifs $N_k < D+1$ conduisent à des covariances singulières (section 2.5). En pratique la dimension est réduite au préalable ou les covariances sont contraintes (diagonales). Les mélanges infinis (processus de Dirichlet, Rasmussen, 2000) constituent un mécanisme différent du VB à $K_{\max}$ fini étudié ici. L'affirmation selon laquelle l'EM variationnel serait « largement préféré » dans ce domaine n'est ni sourcée ni testée ici : \emph{non testé}. Les modèles de Markov cachés ajustés par Baum-Welch (section 1.6.6) restent une référence pour l'annotation de séquences, sans que ce mémoire en mesure les délais pour des génomes entiers : \emph{non testé}.

""")

# ------------------------------------------------------------------ Finance -> cas secondaire corrigé (S&P 500)
c.remplacer_entre(r"\subsection{Finance}", r"\subsection{Systèmes de recommandation}", r"""\subsection{Cas secondaire : rendements du S\&P 500 et risque de marché}
Le rendement d'un actif est $r_t = 100\,\ln(P_t/P_{t-1})$, en pourcentage. La loi de ces rendements a des queues plus épaisses qu'une gaussienne ; un mélange de gaussiennes les représente, et le VB propose en outre une loi sur les paramètres, d'où une loi prédictive de Student et un intervalle de crédibilité de la VaR. Ce cas est secondaire : la période d'évaluation (de janvier 2022 à octobre 2026) diffère fortement de la période d'apprentissage (octobre 2016 à décembre 2021, krach de 2020 compris) ; la kurtosis excédentaire des deux périodes (tableau~\ref{tab:3_cas_desc}) est calculée par le code. Toute VaR calée sur la période 2020 est prudente par construction sur une période plus calme : le backtest mesure alors autant le changement de régime que la qualité de l'algorithme.

\textbf{Hypothèses, fixées avant l'analyse. }(H4) Un mélange ($K>1$) a une log-vraisemblance moyenne hors échantillon supérieure à celle de la gaussienne unique et de la Student-t ; décidée par un test de Diebold--Mariano avec la correction de Harvey, Leybourne et Newbold, sur les log-scores quotidiens. (H5) La VaR gaussienne à 1 \% est franchie plus souvent que prévu, ce que l'on décide par le test de Kupiec au seuil de 5 \% ; l'écart entre mélange EM et mélange VB est, lui, une question descriptive (de l'ordre d'une exception) et ne s'interprète pas comme une différence d'algorithme. (H6) L'intervalle de crédibilité de la VaR du VB est disponible sans calcul supplémentaire ; l'intervalle bootstrap de l'EM (au moins 1\,000 réplicats) mesure un autre objet (variabilité d'estimateur) et la comparaison de leurs largeurs n'est pas une comparaison de fiabilité.

\textbf{Ce qui est comparé. }Gaussienne, Student-t, GARCH(1,1) à innovations de Student, simulation historique, mélange EM (K choisi par le BIC), VB en évaluation plug-in (paramètres $\mathbb{E}[\pi_k], m_k, (\mathbb{E}[\Lambda_k])^{-1}$) et en loi prédictive de Student, et un HMM à deux états en filtrage \emph{forward} (aucune information future). La différence entre l'évaluation prédictive et l'évaluation plug-in d'un même VB isole l'effet de la loi prédictive de celui de l'inférence bayésienne. Les modèles sont ajustés une seule fois sur l'apprentissage puis figés, sans réestimation glissante. La VaR et l'ES de la prédictive de Student sont obtenues par simulation de 200\,000 tirages du mélange de Student (erreur de Monte Carlo en $1/\sqrt{np}$). Le backtest comprend les tests de Kupiec, de Christoffersen (indépendance et couverture conditionnelle) et le test de l'ES d'Acerbi et Székely (2014) (statistiques $Z_1$ et $Z_2$, positives en cas de risque sous-estimé).

\tableauGenere{sp500_descriptif}
\tableauGenere{sp500_backtests}
\tableauGenere{sp500_diebold_mariano}
\tableauGenere{sp500_intervalles}

\begin{figure}[H]
\centering
\includegraphics[width=0.95\textwidth]{figures/fig13.png}
\caption{Distribution des rendements quotidiens du S\&P 500 sur la période d'apprentissage et densités ajustées (échelle logarithmique de la densité). Source : série FRED SP500 (S\&P Dow Jones Indices), archive \texttt{data/sp500\_fred.csv}.}
\label{fig:3_cas_dist}
\end{figure}
\begin{figure}[H]
\centering
\includegraphics[width=0.95\textwidth]{figures/fig15.png}
\caption{Incertitude sur la VaR à 1 \% : tirages a posteriori sous la loi variationnelle et bootstrap non paramétrique de l'EM classique. Les deux distributions ne mesurent pas le même objet.}
\label{fig:3_cas_var}
\end{figure}

\textbf{Lecture. }Les décisions se lisent dans les tableaux générés, selon les critères annoncés ci-dessus et non selon leur résultat. Deux précisions de méthode s'imposent. Premièrement, à 1 \% l'écart entre les exceptions du mélange EM et du mélange VB est d'une exception environ ; franchir ou non le seuil de 5 \% du test de Kupiec n'est pas une différence entre algorithmes. Deuxièmement, la gaussienne se trompe dans des sens opposés selon le niveau (trop prudente à 5 \%, insuffisante à 1 \%) ce qui est cohérent avec des queues épaisses. Le HMM n'est pas évalué avec lissage : ses probabilités sont celles d'un filtre \emph{forward}, et sa VaR est conditionnelle. L'ancienne affirmation « VB mieux calibré à 1 \% » est retirée : elle ne reposait que d'un franchissement de seuil. Limites : un seul indice, dix ans de données, paramètres figés, séries non stationnaires, faible puissance du test de Kupiec à 1 \% sur environ 1\,200 jours, couverture des intervalles non évaluée sur ces données (elle l'est sur le jeu semi-synthétique du cas climatique).

""")

# ------------------------------------------------------------------ recommandation : revue de littérature
c.remplacer_entre(r"\subsection{Systèmes de recommandation}", r"\section{Implémentation de l'EM classique}", r"""\subsection{Systèmes de recommandation (revue de la littérature)}
Dans les systèmes de recommandation, la factorisation matricielle probabiliste place des priors gaussiens sur les vecteurs latents d'utilisateurs et d'articles, et l'inférence variationnelle donne une loi a posteriori exploitable pour l'exploration (échantillonnage de Thompson). L'intérêt de cette incertitude pour le démarrage à froid est une hypothèse de la littérature : \emph{non testé} ici, aucune expérience de recommandation n'ayant été conduite.

\begin{table}[H]
\centering
\small
\setlength{\tabcolsep}{0.14cm}
\begin{tabular}{|p{3.6cm}|p{5.4cm}|p{5.2cm}|}
\hline
\textbf{Domaine} & \textbf{Usage décrit} & \textbf{Statut de la preuve dans ce mémoire} \\
\hline
Climat (cas principal) & Régimes climatiques, mélanges gaussiens & Expériences répliquées (section 3.1.1) \\
\hline
Texte & Modèles de thèmes (pLSA, LDA) & Expérience répliquée sur corpus réel \\
\hline
Finance & VaR, ES, régimes de marché & Expérience unique sur un indice, période de test non stationnaire \\
\hline
Vision & Segmentation, soustraction de fond & Revue : non testé \\
\hline
Bio-informatique & Sous-populations cellulaires, annotation de séquences & Revue : non testé \\
\hline
Recommandation & Factorisation matricielle probabiliste, démarrage à froid & Revue : non testé \\
\hline
\end{tabular}
\caption{Statut de la preuve par domaine d'application}
\label{tab:3_1}
\end{table}
""")

# ------------------------------------------------------------------ §3.2.1 : critère d'arrêt
c.remplacer_ligne("Deux initialisations sont disponibles : par k-means",
                  r"""Deux initialisations sont disponibles : par k-means (avec initialisation k-means++), qui donne un point de départ proche de la solution, et aléatoire (K points de données tirés au hasard et covariance globale, section 1.6.2.a). L'algorithme est relancé n\_init fois et la solution de plus grande log-vraisemblance est conservée. Le critère d'arrêt est celui de la figure~\ref{fig:boucle_arret}, commun à l'EM, au MAP-EM, au VB et au pLSA : variation relative du critère \emph{total} inférieure à $10^{-6}$, plafond de 500 étapes M, la sortie rapportant \texttt{converge} (faux si le plafond est atteint : l'exécution est alors « non convergée »). Chaque covariance reçoit $+\,\varepsilon I$, $\varepsilon = 10^{-6}$ (constante \texttt{REG\_EM}) : l'EM utilisé dans ce mémoire est donc régularisé, ce qui en fait un maximum local de la vraisemblance régularisée (section 1.6.3.a). Le code retourne aussi l'ICL, l'entropie des affectations et un indicateur de dégénérescence.""")
c.remplacer_jusqua_suivant(r"def _em_une_fois(X, K, cov_type, n_iter, tol, reg, init, graine, tol_par_obs):",
                  r"\end{lstlisting}",
                  r"""def _em_une_fois(X, K, cov_type, n_iter, tol, reg, init, graine, prior=None):
    N, D = X.shape
    pi, mu, cov = _init_em(X, K, cov_type, init, graine, reg)
    hist, converge, n_m = [], False, 0
    while True:
        r, log_norm = _etape_e(X, pi, mu, cov)
        hist.append(float(log_norm.sum()))
        if len(hist) > 1 and a_converge(hist[-2], hist[-1], tol):
            converge = True
            break
        if n_m >= n_iter:
            break
        pi, mu, cov = _etape_m(X, r, cov_type, reg)
        n_m += 1
    return {"pi": pi, "mu": mu, "cov": cov, "r": r, "loglik": hist[-1],
            "ll_hist": hist, "n_iter": n_m, "converge": converge}""")

# ------------------------------------------------------------------ §3.3 : variantes tied/diag/sphérique
c.remplacer_ligne("Les variantes de covariance tied, diag et spherical, absentes du chapitre 1",
                  r"""Les variantes de covariance tied, diag et spherical, absentes du chapitre 1, sont obtenues avec un prior de Wishart partagé ou des priors Gamma sur les précisions. Leur ELBO n'est ni dérivé ni implémenté : le critère d'arrêt est la somme des log-normalisations de l'étape E, c'est-à-dire l'ELBO privé du terme $\mathrm{KL}[q(\theta)\Vert p(\theta)]$, qui n'est pas nécessairement monotone. Ces variantes sont donc une \emph{approximation} (clé \texttt{critere\_nom} = \texttt{approximation\_log\_norm}) et les conclusions qui les concernent sont formulées en conséquence ; le terme $D/\beta_k$ de l'étape E reste exact pour ces priors.""")

# ------------------------------------------------------------------ tableaux 3.x saisis à la main -> générés
c.remplacer_table("tab:3_2", r"\tableauGenere{init_priors}")
c.remplacer_table("tab:3_3", r"\tableauGenere{grille_axe_preuve}")
c.remplacer_ligne("Le tableau~\\ref{tab:3_3} consolide",
                  r"Le tableau~\ref{tab:2_17} (grille « axe $\times$ preuve ») consolide les résultats du chapitre 2 et des cas du présent chapitre ; chaque valeur numérique y est lue dans un fichier produit par le code et chaque ligne porte son niveau de preuve.")
c.remplacer_ligne("Cette synthèse fait apparaître un motif récurrent",
                  r"Cette synthèse ne désigne pas un algorithme supérieur. Elle montre que l'élagage et la quantification d'une incertitude approchée par le VB ont une contrepartie documentée (sensibilité aux priors et à $K_{\max}$, coût par ajustement, couverture à vérifier), et que plusieurs inconvénients restent « non testés ». Les conclusions s'arrêtent à ce que les niveaux de preuve de la grille autorisent.")
c.remplacer_ligne("Deux enseignements se dégagent.",
                  r"Deux enseignements se dégagent du tableau~\ref{tab:init_priors}. D'abord, l'initialisation aléatoire exige plus d'itérations que k-means ; une exécution du VB qui atteint le plafond de 500 étapes M est marquée « non convergée » et n'est pas un résultat à interpréter comme les autres. Ensuite, le résultat qualitatif dépend des priors : le VB déplace la sensibilité de l'initialisation vers les hyperparamètres (sections 1.7.4 et 2.3.14).")
c.remplacer_ligne("L'exécution du protocole du chapitre 2 avec ces implémentations donne",
                  r"L'exécution du protocole du chapitre 2 avec ces implémentations produit les tableaux de la section 2.3, générés par le code et non saisis à la main ; ce chapitre n'en reprend pas les valeurs.")
c.remplacer_ligne("Il convient de nuancer cette conclusion par les limites identifiées",
                  r"Les limites identifiées à la section 1.7.9 (sensibilité aux hyperparamètres du prior, surcoût de calcul, dépendance à $K_{\max}$, irréversibilité de l'élagage) s'appliquent ; les variantes stochastiques (SVI, EM online) répondent à la question de la taille des données pour les deux algorithmes.")
# guide de décision (tableau 3.8 dans la numérotation finale) : remplacé par un guide avec niveau de preuve
c.remplacer_table("tab:3_4", r"\tableauGenere{guide_decision}")
c.remplacer_ligne("Au-delà de ce guide de décision, l'expérience acquise",
                  r"""Ce guide ne recommande pas un algorithme dans l'absolu : chaque ligne indique le niveau de preuve disponible (théorème, expérience répliquée, expérience unique ou non testé). Il est complété par trois bonnes pratiques indépendantes de l'algorithme. Premièrement, standardiser les données avant l'ajustement, les deux algorithmes étant sensibles à l'échelle relative des dimensions. Deuxièmement, multiplier les initialisations (\texttt{n\_init} > 1) pour l'EM comme pour le VB. Troisièmement, utiliser un critère d'arrêt commun lorsque l'on compare des nombres d'itérations ou des temps, et rapporter les exécutions non convergées.""")
c.sauver()
print("chapitre 3 révisé")
