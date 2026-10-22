"""Conclusion générale, bibliographie, annexes, corrections de forme (T0.4, T5.14, T5.15, T5.16). À exécuter une seule fois."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from outils_patch import Corps

c = Corps()

# ------------------------------------------------------------------ introduction générale (avant le chapitre 1)
c.avant("%% ==== CHAPITRE : FONDEMENTS THÉORIQUES ET ALGORITHMES EM ====", "\\input{introduction}\n")

# ------------------------------------------------------------------ T0.4 : tableaux 1.1 et 1.4 (colonnes qui se chevauchent)
bs = chr(92)
k4 = next(k for k, l in enumerate(c.lignes) if l.startswith(bs + "label{tab:1_4}"))
d4 = max(k for k in range(k4) if c.lignes[k].startswith(bs + "begin{tabular}"))
c.lignes[d4] = bs + "begin{tabular}{|p{0.8cm}|p{2.3cm}|p{1.6cm}|p{1.6cm}|p{1.6cm}|p{1.6cm}|p{1.6cm}|p{1.6cm}|}"
i = c._idx(r"\textbf{Modèle} & \textbf{Variables latentes} & \textbf{Paramètres} & \textbf{Application} \\")
for k in range(i, 0, -1):
    if c.lignes[k].startswith(r"\begin{tabular}{|p{3.54cm}|p{3.54cm}|p{3.54cm}|p{3.54cm}|}"):
        c.lignes[k] = r"\begin{tabular}{|>{\raggedright\arraybackslash}p{3.4cm}|>{\raggedright\arraybackslash}p{3.7cm}|>{\raggedright\arraybackslash}p{2.9cm}|>{\raggedright\arraybackslash}p{3.7cm}|}"
        break

# ------------------------------------------------------------------ conclusion du chapitre 3
c.remplacer_ligne("Ce troisième chapitre a replacé la comparaison théorique et expérimentale",
                  r"""Ce troisième chapitre a replacé la comparaison dans trois contextes de preuve distincts : un cas principal sur données climatiques réelles (régimes climatiques du Cameroun), un cas secondaire sur le risque de marché (S\&P 500), et une comparaison pLSA contre LDA sur un corpus réel. Les domaines de la vision, de la bio-informatique et de la recommandation sont traités en revue de la littérature, et leurs affirmations sont « non testées » dans ce mémoire. Les implémentations en PyTorch, écrites à partir des équations du chapitre 1, ont servi de validation de la démarche théorique par des tests unitaires : croissance de la log-vraisemblance, de l'ELBO et du log-posterior, retour du MAP-EM à l'EM pour un prior plat, tableaux 1.4 et 1.5.""")
c.remplacer_ligne("Le chapitre souligne aussi les conditions de validité des conclusions",
                  r"""Les conditions de validité des conclusions sont explicites : l'élagage dépend du calibrage des priors, de $K_{\max}$ et du seuil d'activité ; les variantes de covariance non pleines utilisent un critère approché ; le cas S\&P 500 mesure en partie un changement de régime ; et le cas climatique dépend de la disponibilité d'un zonage de référence, à défaut duquel Köppen--Geiger sert seul de référence. La conclusion générale revient sur l'ensemble de cette démarche.""")

# ------------------------------------------------------------------ conclusion générale (chapitre) : T5.14
c.avant(r"\section*{Synthèse des contributions}", r"""\chapter*{Conclusion générale}
\addcontentsline{toc}{chapter}{Conclusion générale}
\markboth{CONCLUSION GÉNÉRALE}{CONCLUSION GÉNÉRALE}
Ce mémoire a comparé, sur trois niveaux d'inférence (EM classique, EM variationnel à $\theta$ ponctuel, Bayes variationnel à $\theta$ aléatoire), l'EM classique et l'EM variationnel pour les modèles de mélange, en reliant chaque avantage et chaque inconvénient à une preuve : un théorème, une expérience répliquée, une expérience unique, ou la mention « non testé » (grille du tableau~\ref{tab:2_17}).
""")
c.remplacer_entre(r"\section*{Synthèse des contributions}", r"\section*{Limites du travail}", r"""\section*{Synthèse des contributions}
\addcontentsline{toc}{section}{Synthèse des contributions}
Ce travail apporte les éléments suivants, sans prétention de nouveauté théorique :

\begin{itemize}
\item une présentation unifiée des fondements communs (inégalité de Jensen, ELBO, divergence de Kullback-Leibler) et des mises à jour de chaque algorithme, avec une distinction explicite de trois niveaux d'inférence ;
\item une reformulation didactique et rigoureuse (passage à la limite d'une famille de lois) de l'équivalence de Neal et Hinton (1998) entre EM classique et EM variationnel (section 2.1.2) ; il ne s'agit pas d'une contribution originale ;
\item un comparateur MAP-EM, qui isole l'effet du prior de celui de l'inférence bayésienne complète ;
\item un protocole de comparaison à critère d'arrêt commun, avec baseline EM-BIC et EM-ICL, tests appariés, tests d'équivalence et correction de Holm, appliqué à dix scénarios synthétiques (S1 à S10) et à un jeu semi-synthétique ;
\item un cas principal sur données climatiques réelles (Cameroun) évaluant huit hypothèses, un cas secondaire sur le risque de marché (S\&P 500) avec backtests de Kupiec, de Christoffersen et de l'ES, et une comparaison pLSA contre LDA ;
\item une implémentation en PyTorch de l'ensemble, avec tests unitaires, dont le code, les graines et les tableaux sont archivés pour que chaque tableau soit regénéré par le code.
\end{itemize}
""")
c.remplacer_ligne("Ce travail présente cependant plusieurs limites",
                  r"""Ce travail présente des limites, discutées à la section 2.5. (1) Les scénarios synthétiques reposent sur des mélanges gaussiens (ou de Student) simples ; leur dimension reste modeste (jusqu'à $D=20$ pour la scalabilité, $D=19$ pour le cas climatique). (2) Les priors empiriques réutilisent les données (Bayes empirique) ; un jeu de priors fixés avant les données est comparé dans le plan factoriel, mais n'épuise pas la question. (3) Les variantes tied, diag et sphérique du VB n'ont pas d'ELBO dérivé : leur critère est une approximation. (4) Le seuil théorique $d/2$ pour $\alpha_0$ concerne le posterior exact : son transfert au champ moyen est testé, non démontré. (5) L'irréversibilité de l'élagage, la dépendance à $K_{\max}$ et l'absence de garantie de consistance restent « non testées » ou partiellement testées. (6) Le cas climatique suppose un échantillonnage spatial approché de l'indépendance, des étiquettes de référence définies à partir du climat, et, à défaut d'un zonage officiel disponible, Köppen--Geiger seul. (7) Le cas S\&P 500 porte sur un seul indice et dix ans ; la période de test diffère de l'apprentissage, de sorte que le backtest mesure en partie un changement de régime ; les modèles ne sont pas réestimés. (8) La comparaison pLSA contre LDA porte sur un corpus de quatre groupes, la LDA du code étant un EM variationnel à $\beta$ ponctuel et non un VB complet. (9) Les temps de calcul dépendent d'une machine et d'une implémentation (annexe D). (10) Vision, bio-informatique et recommandation ne sont pas testées.""")
c.remplacer_ligne("Plusieurs perspectives de recherche et de développement se dégagent",
                  r"""Plusieurs prolongements se dégagent. Sur le plan expérimental : étendre la comparaison à des dimensions plus grandes avec des covariances structurées, évaluer l'irréversibilité de l'élagage par des initialisations adverses, et réestimer les modèles de risque en fenêtre glissante. Sur le plan méthodologique : dériver l'ELBO des variantes de covariance, comparer le champ moyen à des familles variationnelles plus riches (flux normalisants) ou à des divergences autres que la KL inverse, et confronter les seuils de type $d/2$ à un posterior approché par MCMC. Sur le plan applicatif : généraliser le cas climatique à d'autres pays de la CEMAC (une généralisation à tester, non un acquis) avec validation par un expert agronome.""")
c.remplacer_ligne("En définitive, ce mémoire aura permis de démontrer",
                  r"""En définitive, le VB ne « bat » pas l'EM : il déplace la sélection de $K$ vers le choix des hyperparamètres, apporte une incertitude approchée, au prix d'un coût et d'une sensibilité aux priors. Chaque terme de cette phrase est soutenu, ou explicitement non soutenu, par une ligne de la grille du tableau~\ref{tab:2_17}.""")

# ------------------------------------------------------------------ en-têtes courants (bibliographie, annexes)
c.apres(r"\addcontentsline{toc}{chapter}{Bibliographie}", r"\markboth{BIBLIOGRAPHIE}{BIBLIOGRAPHIE}")
c.apres(r"\addcontentsline{toc}{chapter}{Annexes}", r"\markboth{ANNEXES}{ANNEXES}")

# ------------------------------------------------------------------ annexes (T5.15)
c.remplacer_ligne("Les résultats de ce mémoire sont produits par quatre fichiers Python",
                  r"""Les résultats de ce mémoire sont produits par les fichiers Python suivants : \texttt{algorithmes.py} (EM classique, MAP-EM, EM variationnel, ELBO, variantes, Baum-Welch, LDA, pLSA, métriques), \texttt{risque.py} (VaR, ES, tests de Kupiec, de Christoffersen, de Diebold--Mariano et d'Acerbi--Székely), \texttt{comparaison.py} (protocole « 5 EM + VB », statistiques de comparaison), \texttt{scenarios.py} (scénarios synthétiques S1 à S10), \texttt{main.py} (expériences du chapitre 2 et validations du chapitre 1), \texttt{cas\_pratique\_climat.py} (cas principal), \texttt{cas\_pratique.py} et \texttt{cas\_pratique\_sp500\_complement.py} (cas secondaire), \texttt{texte\_plsa\_lda.py} (comparaison pLSA contre LDA) et \texttt{tex\_tables.py} (production des tableaux \LaTeX{} depuis les fichiers de résultats). Le dépôt complet, avec son jeu de tests (\texttt{tests/}), est archivé : étiquette Git et DOI Zenodo à renseigner au dépôt définitif (\texttt{DOI à créer au moment de l'archivage}). Le tableau suivant indique, pour chaque fonction de la bibliothèque, la section et l'équation correspondantes.""")
c.remplacer_ligne("Les fichiers \\texttt{main.py} et \\texttt{cas\\_pratique.py} orchestrent les expériences",
                  r"""Les fichiers \texttt{main.py}, \texttt{scenarios.py}, \texttt{cas\_pratique\_climat.py}, \texttt{cas\_pratique.py}, \texttt{cas\_pratique\_sp500\_complement.py} et \texttt{texte\_plsa\_lda.py} orchestrent les expériences : génération des données, appels aux fonctions ci-dessus, calcul des métriques, tableaux (Pandas) et figures (Plotly). Ils s'exécutent par \texttt{python <fichier>.py} (option \texttt{--rapide} pour une version réduite) ; puis \texttt{python tex\_tables.py} régénère tous les tableaux du mémoire à partir de \texttt{resultats/}. Aucun nombre des tableaux n'est saisi à la main. Le contrôle de cohérence \texttt{python controle\_chiffres.py} liste les nombres du texte qui ne proviennent pas d'un fichier de résultats.""")
# A.4 : corpus jouet supprimé
c.remplacer_entre(r"\subsection*{A.4 Corpus et résultats détaillés de la démonstration LDA}", r"\section*{Annexe B : Détail du calcul de l'ELBO pour le GMM bayésien}",
                  r"""\subsection*{A.4 Corpus et résultats de la comparaison pLSA contre LDA}
Le corpus (sous-ensemble de 20 Newsgroups), le prétraitement et les résultats détaillés sont produits par \texttt{texte\_plsa\_lda.py} et écrits dans \texttt{resultats/texte\_plsa\_lda\_brut.csv} (une ligne par modèle, par taille $N$ et par réplication). La démonstration sur douze phrases des versions précédentes est supprimée.

""")
c.ajouter_fin_ligne("Les graines suivantes sont fixées explicitement", r" Les graines des scénarios (5000 et suivantes), du cas climatique (9000 et suivantes) et de la comparaison de texte sont fixées dans les fichiers correspondants. La machine d'exécution (modèle de processeur, nombre de coeurs et de fils effectifs, mémoire) est enregistrée dans \texttt{environnement.json}, et les versions exactes des bibliothèques dans \texttt{requirements.txt} (verrouillé par \texttt{pip freeze}) : les temps de calcul ne sont comparables qu'à ces conditions.")
c.sub_ligne(r"\subsection*{G.1 Identités de calcul matriciel}", r"G\.1", "E.1")
c.sub_ligne(r"\subsection*{G.2 La distribution de Wishart}", r"G\.2", "E.2")
c.sub_ligne(r"\subsection*{G.3 La distribution de Dirichlet}", r"G\.3", "E.3")
c.sub_ligne(r"\subsection*{G.4 La fonction digamma}", r"G\.4", "E.4")
c.sub_ligne("La fonction digamma $\\psi $(x)", r"scipy\.special\.digamma, utilisée dans les deux implémentations from scratch du chapitre 3 \(sections 3\.2\.1 et 3\.3\.1\)",
            r"torch.special.digamma, utilisée dans les implémentations du chapitre 3 (sections 3.2.1 et 3.3.1) : le code n'utilise ni SciPy ni NumPy")
c.sub_ligne(r"\textbf{Trace et forme quadratique. }", r"tr\(\$Axx\^\{T\}A\^\{0\}\$\)", "tr($Axx^{T}$)")
c.sauver()

# tags d'équation (G.1) (G.2) -> (E.1) (E.2) dans l'annexe E
s = Path(__file__).resolve().parent.parent.joinpath("body.tex").read_text(encoding="utf-8")
s = s.replace(r"\tag{G.1}", r"\tag{E.1}").replace(r"\tag{G.2}", r"\tag{E.2}")
s = s.replace("(G.1)", "(E.1)").replace("(G.2)", "(E.2)")
Path(__file__).resolve().parent.parent.joinpath("body.tex").write_text(s, encoding="utf-8")

# ------------------------------------------------------------------ bibliographie : ajout, tri alphabétique, renumérotation (T5.16)
corps = Path(__file__).resolve().parent.parent.joinpath("body.tex").read_text(encoding="utf-8").split("\n")
d = next(k for k, l in enumerate(corps) if l.startswith(r"\chapter*{Bibliographie}"))
f = next(k for k, l in enumerate(corps) if l.startswith("%% ==== Annexes ===="))
entrees = []
for l in corps[d:f]:
    m = re.match(r"\\textbf\{\[\d+\]\s*\}(.*)$", l)
    if m:
        entrees.append(m.group(1).strip())
nouvelles = [
    "C. Acerbi et B. Székely, « Back-testing expected shortfall », Risk, 2014 (version de travail MSCI, décembre 2014).",
    "H. E. Beck, N. E. Zimmermann, T. R. McVicar, N. Vergopolan, A. Berg et E. F. Wood, « Present and future Köppen-Geiger climate classification maps at 1-km resolution », Scientific Data, vol. 5, art. 180214, 2018.",
    "C. Biernacki, G. Celeux et G. Govaert, « Assessing a mixture model for clustering with the integrated completed likelihood », IEEE Transactions on Pattern Analysis and Machine Intelligence, vol. 22, n° 7, p. 719-725, 2000.",
    "D. M. Blei et M. I. Jordan, « Variational inference for Dirichlet process mixtures », Bayesian Analysis, vol. 1, n° 1, p. 121-143, 2006.",
    "P. F. Christoffersen, « Evaluating interval forecasts », International Economic Review, vol. 39, n° 4, p. 841-862, 1998.",
    "F. X. Diebold et R. S. Mariano, « Comparing predictive accuracy », Journal of Business \\& Economic Statistics, vol. 13, n° 3, p. 253-263, 1995.",
    "S. E. Fick et R. J. Hijmans, « WorldClim 2: new 1-km spatial resolution climate surfaces for global land areas », International Journal of Climatology, vol. 37, n° 12, p. 4302-4315, 2017.",
    "S. Frühwirth-Schnatter, Finite Mixture and Markov Switching Models. New York : Springer, 2006.",
    "D. Harvey, S. Leybourne et P. Newbold, « Testing the equality of prediction mean squared errors », International Journal of Forecasting, vol. 13, n° 2, p. 281-291, 1997.",
    "T. Hofmann, « Probabilistic latent semantic indexing », in Proceedings of the 22nd Annual International ACM SIGIR Conference on Research and Development in Information Retrieval, 1999, p. 50-57.",
    "K. Lang, « NewsWeeder: Learning to filter netnews », in Proceedings of the 12th International Conference on Machine Learning, 1995, p. 331-339.",
    "G. J. McLachlan et D. Peel, Finite Mixture Models. New York : Wiley, 2000.",
    "X.-L. Meng et D. B. Rubin, « Using EM to obtain asymptotic variance-covariance matrices: The SEM algorithm », Journal of the American Statistical Association, vol. 86, n° 416, p. 899-909, 1991.",
    "J. Rousseau et K. Mengersen, « Asymptotic behaviour of the posterior distribution in overfitted mixture models », Journal of the Royal Statistical Society: Series B, vol. 73, n° 5, p. 689-710, 2011.",
]


def cle(e):
    m = re.match(r"^((?:[A-ZÉ]\.(?:-[A-Z]\.)?\s?)+)([^,]+?)(?:,| et |\.\s| and )", e)
    nom = (m.group(2) if m else e.split()[0]).lower()
    return (nom.replace("é", "e").replace("ü", "u"), e.lower())


tous = sorted(entrees + nouvelles, key=cle)
bloc = [r"\chapter*{Bibliographie}", r"\addcontentsline{toc}{chapter}{Bibliographie}", r"\markboth{BIBLIOGRAPHIE}{BIBLIOGRAPHIE}",
        r"\emph{Références numérotées dans l'ordre alphabétique des premiers auteurs (format IEEE). Les références ajoutées à la révision ont été vérifiées par une recherche en ligne de leur existence, de leur revue et de leurs pages, sauf Frühwirth-Schnatter (2006), McLachlan et Peel (2000), Biernacki et al. (2000), Diebold et Mariano (1995), Harvey et al. (1997), Lang (1995) et Corduneanu et Bishop (2001), vérifiées sur la seule base de la littérature connue de l'auteur et à confirmer.}", ""]
for n, e in enumerate(tous, 1):
    bloc += [rf"\textbf{{[{n}]  }}" + e, ""]
corps[d:f] = bloc + [""]
Path(__file__).resolve().parent.parent.joinpath("body.tex").write_text("\n".join(corps), encoding="utf-8")
print("conclusion, annexes et bibliographie révisées :", len(tous), "références")
