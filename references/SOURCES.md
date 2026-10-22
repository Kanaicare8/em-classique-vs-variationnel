# Sources consultées pour la vérification du mémoire

Les fichiers de ce dossier sont des copies locales de documents publics. Les points vérifiés sont cités dans `ANALYSE_COHERENCE.md` avec le numéro de source ci-dessous.

## Copies locales

| N° | Fichier | Source | Usage |
|----|---------|--------|-------|
| S1 | `sklearn_bayesian_mixture_source.py` | scikit-learn, `sklearn/mixture/_bayesian_mixture.py`. https://raw.githubusercontent.com/scikit-learn/scikit-learn/main/sklearn/mixture/_bayesian_mixture.py | Définition de `lower_bound_`, priors par défaut, type de prior de Dirichlet |
| S2 | `Dempster_Laird_Rubin_1977.pdf` | A. P. Dempster, N. M. Laird, D. B. Rubin, « Maximum likelihood from incomplete data via the EM algorithm », J. R. Stat. Soc. B, 39(1), 1-38, 1977. https://web.mit.edu/6.435/www/Dempster77.pdf | Matrice de taux de convergence de l'EM (section 3) |
| S3 | `Bishop_2006_PRML.pdf` | C. M. Bishop, *Pattern Recognition and Machine Learning*, Springer, 2006, chapitre 10.2. https://www.microsoft.com/en-us/research/wp-content/uploads/2006/01/Bishop-Pattern-Recognition-and-Machine-Learning-2006.pdf | Mises à jour Normal-Wishart (10.58 à 10.63) et ELBO (10.70 à 10.77), implémentées dans `algorithmes.py` |

## Copies locales ajoutées le 22 octobre 2026 (lues pour la révision des chapitres 1 à 3)

Le détail de ce que chaque source établit, et des affirmations du plan de travail qu'elle corrige, est dans `notes/ANALYSE_SOURCES.md`.

| N° | Fichier | Référence | Usage dans le texte |
|----|---------|-----------|---------------------|
| S13 | `Dempster_Laird_Rubin_1977_JSTOR.pdf` | Même article que S2 (copie JSTOR) | Doublon de S2, conservé pour la pagination JSTOR |
| S14 | `Neal_Hinton_1998_vue_EM.pdf` | Neal et Hinton (1998), voir S6. PDF à texte non extractible, lu en image | §2.1 : énergie libre F, lemmes 1 et 2, section 6 (« winner-take-all ») |
| S15 | `Corduneanu_Bishop_2001_selection_VB.pdf` | A. Corduneanu, C. M. Bishop, AISTATS 2001 | §1.7.1, §1.7.4 : π ponctuel (type II), non Dirichlet |
| S16 | `Blei_Ng_Jordan_2003_LDA.pdf` | D. M. Blei, A. Y. Ng, M. I. Jordan, JMLR 3, 993-1022, 2003 | §3.1 : EM variationnel bayes empirique (5.3), LDA lissée (5.4) |
| S17 | `Hoffman_2013_SVI.pdf` | M. D. Hoffman, D. M. Blei, C. Wang, J. Paisley, JMLR 14, 1303-1347, 2013 | §1.7.7 : variables locales et globales, gradient naturel, pas de Robbins-Monro |
| S18 | `Kingma_Welling_2014_AEVB.pdf` | D. P. Kingma, M. Welling, arXiv:1312.6114 (v11), ICLR 2014 | §1.7.7 : reparamétrisation, SGVB, inférence amortie |
| S19 | `Rezende_Mohamed_2015_flux_normalisants.pdf` | D. J. Rezende, S. Mohamed, ICML 2015 (arXiv:1505.05770) | §1.7.7 : flux planaires et radiaux, log-déterminant en O(D) |
| S20 | `Blei_Kucukelbir_McAuliffe_2017_revue_VI.pdf` | D. M. Blei, A. Kucukelbir, J. D. McAuliffe, JASA 112, 859-877, 2017 (arXiv v9, 2018) | §1.5.4, §1.7.9 : sous-estimation de la variance ; résultats de Wang et Titterington (section 5.2) |
| S21 | `Dwivedi_2018_EM_mal_specifie.pdf` | R. Dwivedi et al., NeurIPS 2018 | §1.6.3.d : sous-spécification, projection KL |
| S22 | `Dwivedi_2020_singularite_EM.pdf` | R. Dwivedi et al., Ann. Statist. 48(6), 3161-3182, 2020 | §1.6.3.d : sur-spécification, cas équilibré et déséquilibré |
| S23 | `Zhang_Gao_2020_taux_posterior_variationnel.pdf` | F. Zhang, C. Gao, Ann. Statist. 48(4), 2180-2207, 2020. **Ce n'est pas Wang et Blei (2019)** | §1.7.9 : taux de contraction du posterior variationnel |
| S24 | `Acerbi_Szekely_2014_backtesting_ES.pdf` | C. Acerbi, B. Székely, MSCI, décembre 2014 | §3.1.4 : tests Z1, Z2 de l'ES (`risque.py`) |
| S25 | `Paszke_2019_PyTorch.pdf` | A. Paszke et al., NeurIPS 2019 (arXiv:1912.01703) | Annexe A : bibliothèque de calcul |

Le fichier `Allocation de Dirichlet latente.pdf` était une copie octet pour octet de S16 : il a été supprimé.

## Références citées d'après une source locale, non consultées

| Référence | Citée d'après |
|-----------|---------------|
| S. Balakrishnan, M. J. Wainwright, B. Yu, Ann. Statist. 45, 77-120, 2017 | S22, réf. [1] |
| J. H. Chen, Ann. Statist. 23, 221-233, 1995 | S22, réf. [5] |
| B. Wang, D. M. Titterington, AISTATS 2005 ; Bayesian Analysis 1, 625-650, 2006 | S20, section 5.2 |
| Y. Wang, D. M. Blei, JASA 114, 1147-1161, 2019 | S23, réf. [36] |
| H. Attias, NIPS 12, 2000 | Aucune copie ; cité pour l'historique seulement |

## Références vérifiées en ligne (pas de copie locale)

| N° | Référence | Lien |
|----|-----------|------|
| S4 | L. E. Baum, T. Petrie, G. Soules, N. Weiss, « A maximization technique occurring in the statistical analysis of probabilistic functions of Markov chains », Ann. Math. Statist., 41(1), 164-171, 1970 | https://projecteuclid.org/euclid.aoms/1177697196 |
| S5 | C. F. J. Wu, « On the convergence properties of the EM algorithm », Ann. Statist., 11(1), 95-103, 1983 | https://projecteuclid.org/journals/annals-of-statistics/volume-11/issue-1/On-the-Convergence-Properties-of-the-EM-Algorithm/10.1214/aos/1176346060.full |
| S6 | R. M. Neal, G. E. Hinton, « A view of the EM algorithm that justifies incremental, sparse, and other variants », in *Learning in Graphical Models*, 355-368, 1998 | https://link.springer.com/chapter/10.1007/978-94-011-5014-9_12 |
| S7 | T. A. Louis, « Finding the observed information matrix when using the EM algorithm », J. R. Stat. Soc. B, 44(2), 226-233, 1982 | https://rss.onlinelibrary.wiley.com/doi/10.1111/j.2517-6161.1982.tb01203.x |
| S8 | M. Sato, S. Ishii, « On-line EM algorithm for the normalized Gaussian network », Neural Computation, 12(2), 407-432, 2000 | https://pubmed.ncbi.nlm.nih.gov/10636949/ |
| S9 | O. Cappé, E. Moulines, « On-line expectation-maximization algorithm for latent data models », J. R. Stat. Soc. B, 71(3), 593-613, 2009 | https://academic.oup.com/jrsssb/article-abstract/71/3/593/7092936 |
| S10 | C. E. Rasmussen, « The infinite Gaussian mixture model », NIPS 12, 554-560, 2000 | https://groups.seas.harvard.edu/courses/cs281/papers/rasmussen-1999a.pdf |
| S11 | G. Celeux, J. Diebolt, « The SEM algorithm... », Computational Statistics Quarterly, 2, 73-82, 1985 | https://link.springer.com/article/10.1023/B:STCO.0000039481.32211.5a (référence indirecte, via citations) |
| S12 | X.-L. Meng, D. B. Rubin, « Using EM to obtain asymptotic variance-covariance matrices: the SEM algorithm », JASA, 86(416), 899-909, 1991 | Cité par S2 pour la matrice DM |

Niveau de confiance : S1, S2, S3, S4 ont été lues à la source. S5 à S10 ont été confirmées par les pages éditeur ou les moteurs de recherche. S11 repose sur des citations dans des articles Springer, pas sur une page de l'éditeur.

## Références du registre des paramètres (vérifiées en ligne le 22 octobre 2026)

Clés utilisées dans `parametres.py` (dictionnaire `REFERENCES` ; une clé absente fait échouer l'import du registre).

| Clé | Référence | Vérification |
|-----|-----------|--------------|
| bergstra2012 | J. Bergstra, Y. Bengio, « Random search for hyper-parameter optimization », JMLR 13, 281-305, 2012 | https://jmlr.org/papers/v13/bergstra12a.html |
| biernacki2003 | C. Biernacki, G. Celeux, G. Govaert, « Choosing starting values for the EM algorithm for getting the highest likelihood in multivariate Gaussian mixture models », Comput. Stat. Data Anal. 41(3-4), 561-575, 2003 | documentation CRAN Rmixmod et GMMinit (titre et pages) |
| cohen1988 | J. Cohen, *Statistical Power Analysis for the Behavioral Sciences*, 2e éd., Lawrence Erlbaum, 1988 (d = 0,5 « moyen ») | https://utstat.toronto.edu/brunner/oldclass/378f16/readings/CohenPower.pdf |
| holm1979 | S. Holm, « A simple sequentially rejective multiple test procedure », Scand. J. Statist. 6(2), 65-70, 1979, doi:10.2307/4615733 | JSTOR via documentation R |
| jamieson2016 | K. Jamieson, A. Talwalkar, « Non-stochastic best arm identification and hyperparameter optimization », AISTATS, PMLR 51, 240-248, 2016 | https://proceedings.mlr.press/v51/jamieson16.html |
| lakens2017 | D. Lakens, « Equivalence tests: a practical primer for t tests, correlations, and meta-analyses », Soc. Psychol. Personal. Sci. 8(4), 355-362, 2017 | https://pmc.ncbi.nlm.nih.gov/articles/PMC5502906 |
| pedregosa2011 | F. Pedregosa et al., « Scikit-learn: Machine learning in Python », JMLR 12, 2825-2830, 2011 | https://jmlr.org/papers/v12/pedregosa11a.html |
| porter1980 | M. F. Porter, « An algorithm for suffix stripping », Program 14(3), 130-137, 1980, doi:10.1108/eb046814 | https://tartarus.org/martin/PorterStemmer/ |
| robbins1951 | H. Robbins, S. Monro, « A stochastic approximation method », Ann. Math. Statist. 22(3), 400-407, 1951, doi:10.1214/aoms/1177729586 | https://www.columbia.edu/~ww2040/8100F16/RM51.pdf |
| roberts2017 | D. R. Roberts et al., « Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure », Ecography 40(8), 913-929, 2017, doi:10.1111/ecog.02881 | https://www.biometrie.uni-freiburg.de/mitarbeiter/dormann/roberts-et-al-2017-ecography.pdf |
| schuirmann1987 | D. J. Schuirmann, « A comparison of the two one-sided tests procedure and the power approach for assessing the equivalence of average bioavailability », J. Pharmacokinet. Biopharm. 15(6), 657-680, 1987, doi:10.1007/BF01068419 | https://zenodo.org/record/1232484 |
| schwarz1978 | G. Schwarz, « Estimating the dimension of a model », Ann. Statist. 6(2), 461-464, 1978 | https://sites.stat.washington.edu/courses/stat527/s13/readings/ann_stat1978.pdf |
| bishop2006, blei2003, cappe2009, hoffman2013 | voir S3, S9 et la copie locale de Blei et al. 2003 et Hoffman et al. 2013 | copies locales |

Non retenue faute de vérification : N. Cressie, *Statistics for Spatial Data* (1993). La règle du palier du variogramme repose sur un calcul élémentaire (variables réduites), sans citation.
