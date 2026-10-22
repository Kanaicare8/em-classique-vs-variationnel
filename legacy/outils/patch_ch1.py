"""Passe de révision du chapitre 1 et de la section 2.1 (tâches T5.2 à T5.9). À exécuter une seule fois."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from outils_patch import Corps

c = Corps()

# T5.2 : non-identifiabilité des mélanges sur-paramétrés
c.apres("Une question importante en théorie de l'estimation concerne l'identifiabilité", r"""
Une seconde forme de non-identifiabilité, distincte du label switching, est propre aux mélanges sur-paramétrés, c'est-à-dire ajustés avec plus de composantes que la loi génératrice n'en contient. Si un poids $\pi_k$ est nul, les paramètres $(\mu_k, \Sigma_k)$ de la composante correspondante n'interviennent plus dans la densité : ils sont arbitraires. Si deux composantes ont la même moyenne et la même covariance, seule la somme $\pi_j + \pi_k$ est identifiée. Dans ces deux cas, l'ensemble des paramètres qui donnent la même densité n'est plus un ensemble fini de $K!$ permutations mais une sous-variété de l'espace des paramètres : la vraisemblance est plate dans certaines directions et la matrice d'information de Fisher est singulière (Rousseau et Mengersen, 2011). Cette propriété a deux conséquences utilisées plus loin. Elle rend fausses, pour un mélange sur-paramétré, les hypothèses de régularité des théorèmes asymptotiques usuels. Elle est aussi le phénomène que l'élagage de l'EM variationnel met à profit (section 1.7.4), dont l'effet sur le champ moyen reste, en l'état, une hypothèse à tester et non un résultat établi.
""")

# T5.3 : mécanisme d'élagage
c.remplacer_ligne("Lors de l'optimisation variationnelle, une composante k pour laquelle", r"""Lors de l'optimisation variationnelle, l'élagage ne provient pas de l'espérance $\mathbb{E}[\pi_k] = (\alpha_0 + N_k)/(K\alpha_0 + N)$ : celle-ci est tirée vers la valeur uniforme $1/K$ pour tout $\alpha_0$ (section 1.4.4) et ne s'annule jamais. Il provient de l'espérance du logarithme du poids, qui intervient dans l'étape E (équation 1.29) :
\begin{equation*}
\mathbb{E}[\log \pi_k] = \psi(\alpha_k) - \psi\Big(\sum_{j}\alpha_j\Big), \qquad \alpha_k = \alpha_0 + N_k .
\end{equation*}
Pour $\alpha_k < 1$, on a $\psi(\alpha_k) = \psi(\alpha_k + 1) - 1/\alpha_k \approx -1/\alpha_k$, qui tend vers $-\infty$ quand $\alpha_k \to 0$. Une composante qui capte peu d'observations a donc un $\alpha_k$ proche de $\alpha_0$, un $\mathbb{E}[\log \pi_k]$ très négatif et des responsabilités $r_{ik}$ qui s'effondrent : $N_k$ diminue, ce qui accentue encore l'effet (rétroaction positive). La figure~\ref{fig:elagage} illustre ce mécanisme. Il est difficilement réversible : une composante dont $\alpha_k$ est tombé près de $\alpha_0$ ne reçoit plus de responsabilité et ne peut plus être réactivée par les itérations suivantes.

\input{figures_tikz/elagage}

Le seuil en deçà duquel l'élagage opère n'est pas $\alpha_0 = 1$. Pour un mélange sur-paramétré, la théorie de Rousseau et Mengersen (2011) établit que la loi a posteriori exacte vide les composantes superflues lorsque $\alpha_0 < d/2$, où $d$ est le nombre de paramètres libres d'une composante ($d = 5$ pour une covariance pleine en dimension 2, soit un seuil de 2,5 ; $d = 4$ pour une covariance diagonale, seuil de 2 ; $d = 3$ pour une covariance sphérique, seuil de 1,5). Ce résultat concerne le posterior exact, non l'approximation de champ moyen. Son transfert à l'EM variationnel est donc une \emph{hypothèse à tester}, et non un fait acquis : l'expérience S8 (section 2.3.14) mesure le nombre de composantes actives sur une grille de $\alpha_0$ de 1 à 10 autour de ces seuils.""")
c.apres("Ce mécanisme d'élagage automatique constitue une forme de rasoir d'Occam bayésien", r"""
Ce rasoir d'Occam a un coût que le texte précédent ne doit pas masquer : le résultat dépend de $K_{\max}$ (il ne peut pas retrouver plus de composantes que $K_{\max}$), des hyperparamètres $(\alpha_0, \beta_0, \nu_0, W_0)$ qui déplacent la sensibilité de l'initialisation vers les priors, et du seuil d'activité choisi pour décréter qu'une composante est éteinte (le seuil $N_k \geq 1$ est une convention, dont la sensibilité est mesurée par l'expérience S10).""")

c.ajouter_fin_ligne("La distribution a posteriori sur les poids de mélange est donc Dir(8, 5, 2)",
                    r" Ce calcul porte sur $\mathbb{E}[\pi_k]$ ; il ne doit pas être confondu avec le mécanisme d'élagage, qui repose sur $\mathbb{E}[\log \pi_k] = \psi(\alpha_k) - \psi(\sum_j \alpha_j)$ (section 1.7.4).")

# T5.3 (chapitre 2) : phrase non testée remplacée par l'hypothèse
c.sub_ligne("Ces résultats confirment la prédiction théorique : pour $\\alpha _{0} \\leq 0{,}1$",
            r"Le prior de Dirichlet n.est donc pas le seul mécanisme à l.œuvre.*?mais non testée isolément ici\.",
            r"Ce comportement à $\\alpha_0 = 1$ est compatible avec le seuil $d/2 = 2{,}5$ de Rousseau et Mengersen (2011) pour une covariance pleine en dimension 2 : à $\\alpha_0 = 1$, on est en deçà du seuil. Cette lecture reste une hypothèse, la théorie portant sur le posterior exact et non sur le champ moyen ; la grille de la section 2.3.14 la teste autour du seuil.")
c.sub_ligne("Ces résultats confirment la prédiction théorique : pour $\\alpha _{0} \\leq 0{,}1$",
            r"est plus nuancé que ne le laissait attendre la théorie : l.élagage persiste",
            r"montre que l'élagage persiste")

# T5.4 : mode-seeking et sous-estimation de variance
c.remplacer_ligne("Ce choix a toutefois une conséquence importante sur la forme de l'approximation", r"""Ce choix a toutefois deux conséquences distinctes, qu'il faut nommer séparément car leurs remèdes diffèrent.

\textbf{Premier effet : le mode-seeking, dû à la divergence KL inverse. }La divergence KL inverse pénalise très fortement les régions où $q(z) > 0$ mais $p(z) \approx 0$, et tolère les régions où $q(z) \approx 0$ mais $p(z) > 0$. Lorsque la loi a posteriori $p$ est multimodale, $q$ se concentre donc sur un seul mode plutôt que de couvrir tous les modes (mode-seeking ou zero-forcing). Le posterior d'un GMM à $K$ composantes est multimodal : il possède $K!$ modes symétriques par permutation des étiquettes, dont $q$ n'en capture qu'un. Le remède relève du choix de la divergence (KL directe, divergences $\alpha$) ou de la famille variationnelle.

\textbf{Second effet : la sous-estimation de la variance, due à la factorisation. }Même pour un posterior unimodal, l'hypothèse de champ moyen $q(Z, \theta) = q(Z)q(\theta)$ ignore la corrélation entre variables latentes et paramètres. La variance de $q$ est alors mécaniquement inférieure à celle du posterior marginal, comme pour une gaussienne bivariée corrélée approchée par un produit de lois marginales. Ce second effet n'est pas lié à la multimodalité, et le remède relève d'une famille variationnelle plus riche (structurée, flux normalisants) plutôt que d'un changement de divergence.

La figure~\ref{fig:kl_inverse} illustre le premier effet. Les deux effets conduisent à des intervalles de crédibilité plus étroits que ceux d'une caractérisation exacte, un biais optimiste dont le praticien doit tenir compte. Leur importance quantitative dans le GMM n'est pas établie par ce chapitre : elle est mesurée par la couverture empirique de l'hypothèse H6 (section 2.3.15).

\input{figures_tikz/kl_inverse}""")

# T5.5 : Wu (1983) et GMM non borné
c.apres("Il est important de noter que l'EM n'est pas garanti de converger vers le maximum global", r"""
\textbf{Limite du théorème pour le GMM. }Les résultats de Wu (1983) supposent une vraisemblance continue et un ensemble de niveau compact. Le GMM à covariances libres ne les vérifie pas : sa vraisemblance est non bornée (si une composante s'effondre sur une observation, $\det\Sigma_k \to 0$ et $\ell \to +\infty$, section 1.6.8). Le théorème ne s'applique donc pas tel quel. Deux issues sont possibles : borner inférieurement les valeurs propres de $\Sigma_k$, ou parler de maximum local \emph{restreint}. Le code utilise la première : chaque covariance reçoit $+\,\varepsilon I$ avec $\varepsilon = 10^{-6}$ (constante \texttt{REG\_EM}, section 3.2.1). Les points stationnaires obtenus sont alors ceux de la vraisemblance régularisée, non ceux de la vraisemblance d'origine.""")

# T5.6 : incertitude EM / VB et ELBO
c.sub_ligne("Bien que l'EM classique ne fournisse pas directement d'estimations d'incertitude",
            r".{0,3}limitation que l'EM variationnel permet précisément de lever, comme nous le verrons à la section 1\.7\.",
            r". Il existe des remèdes : le bootstrap (utilisé à la section 3.1.4), l'EM stochastique, l'EM supplémenté de Meng et Rubin (1991). L'EM variationnel ne « lève » pas cette limitation : les deux approches ne répondent pas à la même question. Un intervalle de confiance décrit la variabilité de l'estimateur sur des échantillons répétés ; un intervalle de crédibilité décrit la loi de $\\theta$ sachant les données sous un prior donné, et celui du champ moyen n'est de plus qu'approché (section 1.5.4).")
c.remplacer_ligne(r"\item \textbf{ELBO comme critère de convergence et de sélection : }",
                  r"\item \textbf{ELBO comme critère de convergence : }l'ELBO borne inférieurement la log-évidence et fournit un critère de convergence croissant. Pour comparer des modèles, l'ELBO peut servir à comparer des valeurs de $K$ \emph{au sein du même algorithme variationnel}, avec les réserves de Corduneanu et Bishop (2001) : l'écart entre l'ELBO et la log-évidence (une divergence KL) varie d'un modèle à l'autre, ce qui biaise la comparaison. L'ELBO n'est pas comparable à un BIC ou à une log-vraisemblance d'EM (sections 2.2.3 et 2.3.3) : cette position est la seule retenue dans ce mémoire.")

# T5.7 : rééquilibrage des avantages et inconvénients
c.remplacer_ligne(r"\item \textbf{Absence de quantification de l'incertitude : }",
                  r"\item \textbf{Incertitude non native : }l'EM classique fournit une estimation ponctuelle $\hat{\theta}$ ; une incertitude s'obtient a posteriori (formule de Louis, 1982, bootstrap, EM supplémenté de Meng et Rubin, 1991, EM stochastique), au prix de calculs supplémentaires. Ces intervalles sont de confiance, non de crédibilité (section 1.6.3.c).")
c.ajouter_fin_ligne(r"\item \textbf{Lenteur de convergence : }", r" Ce défaut n'est pas propre à l'EM classique : l'EM variationnel batch a le même ordre de coût par itération (section 2.2.1) ; la comparaison du nombre d'itérations exige un critère d'arrêt commun (sections 2.3.1 et 2.3.8).")
c.ajouter_fin_ligne(r"\item \textbf{Scalabilité limitée : }", r" La même limite vaut pour la version batch de l'EM variationnel ; les variantes online (EM online) et stochastique (SVI) existent pour les deux (sections 1.6.5 et 1.7.7).")
c.apres(r"\item \textbf{Applicabilité restreinte aux modèles conjugués : }", r"""\item \textbf{Irréversibilité de l'élagage : }une composante dont le poids s'est effondré ne reçoit plus de responsabilité et ne peut plus revenir (section 1.7.4). Une mauvaise trajectoire initiale peut donc éliminer définitivement une composante utile. Cet effet n'a pas été testé directement dans ce mémoire (« non testé » dans la grille de synthèse).
\item \textbf{Dépendance à $K_{\max}$ : }l'élagage ne peut retrouver que $K \leq K_{\max}$ composantes ; la sélection de $K$ est déplacée vers le choix de $K_{\max}$ et des hyperparamètres.
\item \textbf{Absence de garantie de consistance : }l'approximation de champ moyen n'offre pas, en général, de garantie de consistance pour la sélection de $K$ ; les résultats théoriques existants (Rousseau et Mengersen, 2011) portent sur le posterior exact.
\item \textbf{Double usage des données avec des priors empiriques : }fixer $m_0$ et $W_0^{-1}$ à partir des données (Bayes empirique) utilise l'échantillon deux fois ; l'ELBO et les intervalles de crédibilité n'ont plus leur lecture bayésienne stricte. Un jeu de priors fixés avant les données doit être comparé (expérience S9).""")
c.ajouter_fin_ligne(r"\item \textbf{Quantification complète de l'incertitude : }", r" Cette distribution est une approximation (section 1.5.4) : sa fiabilité est mesurée par la couverture empirique de l'hypothèse H6.")
c.sub_ligne(r"\item \textbf{Sélection automatique du nombre de composantes : }",
            r"plutôt qu'une série d'exécutions pour différentes valeurs de K\.",
            r"plutôt qu'une série d'exécutions pour différentes valeurs de K, au prix du choix de $K_{\\max}$ et des hyperparamètres. Le gain en temps n'est pas acquis : il doit être mesuré en temps total jusqu'au modèle final (hypothèse H4).")

# T5.8 : Neal et Hinton comme re-démonstration rigoureuse
c.remplacer_ligne("Le dernier terme, log $\\delta $(0), est une constante formellement infinie", r"""Les deux derniers termes appellent une précaution : la masse de Dirac n'est pas une densité, et $\log\delta(0)$ n'a pas de sens. Il faut passer à la limite d'une famille de lois. Posons $q_\varepsilon(\theta) = \mathcal{N}(\hat\theta, \varepsilon I_d)$ et faisons tendre $\varepsilon \to 0$. Par continuité de $\log p(X, Z \mid \theta)$ et de $\log p(\theta)$, les deux espérances convergent vers leurs valeurs en $\hat\theta$. Le terme d'entropie vaut $-\mathbb{E}_{q_\varepsilon}[\log q_\varepsilon] = \tfrac{d}{2}\log(2\pi e\,\varepsilon)$ : il diverge quand $\varepsilon \to 0$, mais il ne dépend ni de $q(Z)$ ni de $\hat\theta$. L'ELBO s'écrit donc
\begin{equation*}
\mathrm{ELBO}(q(Z), q_\varepsilon) = \underbrace{\mathbb{E}_{q(Z)}[\log p(X, Z \mid \hat\theta)] - \mathbb{E}_{q(Z)}[\log q(Z)]}_{\mathrm{ELBO}(q(Z),\,\hat\theta)} + \log p(\hat\theta) + \tfrac{d}{2}\log(2\pi e\,\varepsilon) + o(1),
\end{equation*}
et la constante divergente n'affecte pas la localisation de l'optimum en $(q(Z), \hat\theta)$. Reste le terme $\log p(\hat\theta)$ : avec un prior plat (impropre), il est constant et l'on obtient l'EM du maximum de vraisemblance ; \emph{sans} prior plat, on maximise l'ELBO plus $\log p(\hat\theta)$ et l'on obtient le MAP-EM (section 2.1.3), non le MLE-EM. L'équation (2.3) est donc exacte pour un prior plat et à $\log p(\hat\theta)$ près sinon. Ce paragraphe est une re-démonstration rigoureuse, à des fins pédagogiques, du résultat de Neal et Hinton (1998), repris dans Bishop (2006, chapitres 9 et 10) : il ne constitue pas une contribution originale.""")

# T5.9 : MAP-EM développé
c.sub_ligne("\\textbf{Deuxième niveau : le maximum a posteriori (MAP).", r"Il serait possible de définir un « EM-MAP ».*$",
            r"Le MAP-EM, qui maximise à l'étape M non plus $Q(\\theta|\\theta^t)$ seule mais $Q(\\theta|\\theta^t) + \\log p(\\theta)$, est développé à la section 2.1.3 ; il est implémenté (fonction \\texttt{map\\_em}) et intégré à toutes les comparaisons, car il isole l'effet du prior de celui de l'inférence bayésienne complète.")
c.sub_ligne("Le tableau 2.2 synthétise cette hiérarchie à trois niveaux", r", non développé algorithmiquement dans ce mémoire mais utile", r", développé et implémenté dans ce mémoire (section 2.1.3), utile")
c.sub_ligne("MAP & argmax", r"« EM-MAP » \(non développé ici\)", r"MAP-EM (section 2.1.3)")
c.avant("\\section{Comparaison algorithmique}", r"""\subsection{Le MAP-EM : isoler l'effet du prior}
Avec les priors conjugués du modèle bayésien (Dirichlet sur $\pi$, Normale-Inverse-Wishart sur $(\mu_k, \Sigma_k)$ de paramètres $\alpha_0, m_0, \beta_0, \Psi_0 = W_0^{-1}, \nu_0$), l'étape M du MAP-EM maximise $Q(\theta \mid \theta^t) + \log p(\theta)$ en forme close. Avec $N_k = \sum_i r_{ik}$, $\bar x_k$ la moyenne pondérée et $S_k = \sum_i r_{ik}(x_i - \bar x_k)(x_i - \bar x_k)^\top$ :
\begin{align*}
\pi_k &= \frac{N_k + \alpha_0 - 1}{N + K(\alpha_0 - 1)}, \qquad \mu_k = \frac{\beta_0 m_0 + N_k \bar x_k}{\beta_0 + N_k},\\
\Sigma_k &= \frac{\Psi_0 + S_k + \frac{\beta_0 N_k}{\beta_0 + N_k}(\bar x_k - m_0)(\bar x_k - m_0)^\top}{\nu_0 + N_k + D + 2}.
\end{align*}
Ce sont les modes conjoints en $(\pi, \mu, \Sigma)$ (la densité est prise en $\Sigma$, non en $\Lambda$) ; la formule de $\pi_k$ exige $\alpha_0 \geq 1$. Un prior plat ($\alpha_0 = 1$, $\beta_0 = 0$, $\Psi_0 = 0$, $\nu_0 = -D-2$) redonne exactement l'EM classique, ce que vérifie un test unitaire, et le log-posterior $\ell(\theta) + \log p(\theta)$ croît à chaque itération. Le MAP-EM porte les mêmes priors que le VB mais ne fournit qu'un point : comparer EM, MAP-EM et VB permet d'attribuer à la régularisation ce qui lui revient et à la distribution sur $\theta$ ce qui lui revient. Le schéma de la figure~\ref{fig:trois_niveaux} situe les trois algorithmes.

\input{figures_tikz/trois_niveaux}

""")
c.sauver()
print("chapitre 1 et section 2.1 révisés")
