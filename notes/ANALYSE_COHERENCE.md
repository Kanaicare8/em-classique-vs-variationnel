# Analyse de cohérence du mémoire et nouvelle implémentation

Mémoire analysé : `body.tex` (copie avant modification : `legacy/body_v0.tex`).
Code précédent : `legacy/main_numpy_sklearn_v0.py`.
Sources externes : voir `../references/SOURCES.md` (références S1 à S12 citées ci-dessous).

## 1. Ce qui a été fait

| Élément | Fichier | Contenu |
|---|---|---|
| Algorithmes | `algorithmes.py` | PyTorch seul : EM classique (4 types de covariance), EM variationnel et ELBO complet (éq. 1.31), SEM, EM online, SVI, forward-backward et Baum-Welch (discret et gaussien), LDA variationnel, BIC, AIC, ARI, silhouette |
| Expériences | `main.py` | 12 expériences du chapitre 2 et validations du chapitre 1, avec Pandas (tableaux) et Plotly (figures aux couleurs de la charte) |
| Carnet | `code.ipynb` | Mis à jour : appelle `algorithmes.py` et `main.py` |
| Sorties | `resultats/` | .csv, .html, .png, `journal.txt`, `comparaison_memoire.csv` |
| Mémoire | `body.tex` | Retrait de la dédicace, de l'avant-propos, des remerciements, de l'annexe E (glossaire), de l'annexe F (questions) et du doublon de la section « Recommandations pratiques » |

Chaque algorithme cite dans son code les numéros d'équations du mémoire. Propriétés vérifiées numériquement : la log-vraisemblance de l'EM croît à chaque itération, l'ELBO croît à chaque itération et reste inférieure à la log-vraisemblance, F(q*, theta) égale la log-vraisemblance après l'étape E (équivalence de Neal et Hinton), la borne de la LDA croît, la log-vraisemblance de Baum-Welch croît. Les tableaux 1.4 et 1.5 du mémoire sont retrouvés exactement.

Limites de la reproduction. Les données sont générées avec le générateur de PyTorch, donc les 300 points ne sont pas ceux de `make_blobs` de scikit-learn : les valeurs exactes (ARI, silhouette) diffèrent de quelques centièmes. Je n'ai pas relancé scikit-learn pour une comparaison point à point. Les conclusions ci-dessous portent sur des écarts qualitatifs ou très supérieurs à cette variabilité.

## 2. Incohérences du mémoire, classées par gravité

### A. Erreurs de calcul ou de résultat

**A1. Tableau 1.2 (EM sur 8 points) faux.** Le tableau donne mu = 1,300 et 7,500, sigma = 0,474 et 0,440, log-vraisemblance -9,97 en 5 itérations. L'EM bien exécuté converge en 3 itérations vers mu = 1,125 et 7,725, sigma = 0,466 et 0,460, log-vraisemblance -10,736. Ce sont les moyennes empiriques de {0,5; 1,0; 1,2; 1,8} et {7,1; 7,5; 8,0; 8,3}. Le texte « le premier centré sur 1,3 » est donc faux. Conséquences en cascade :
- Section 1.3.5, éq. (1.10) : p(2,0 | theta) vaut 0,0734 avec les bons paramètres, pas 0,1414 (0,1414 vient des paramètres erronés).
- Section 1.7.5 : « moyennes 7,724 et 1,126 qui correspondent, à un écart d'arrondi près, à 7,5 et 1,3 » est faux. Les deux algorithmes donnent la même solution (7,725 et 1,125).
- Figure 1.1 : à régénérer.

**A2. ELBO de scikit-learn mal décrite.** Le texte (2.3.3, 2.3.8, annexe F) parle de « moyenne par échantillon » pour `lower_bound_` de `BayesianGaussianMixture`. Le code source (S1) ne divise pas par n_samples et indique « removed all the constant terms ». C'est donc une ELBO totale sans constantes, qui n'est pas la vraie ELBO. Preuve : une ELBO exacte est toujours inférieure à la log-vraisemblance maximale (-946 pour le jeu de référence, mon ELBO exacte vaut -1047 à convergence), alors que le mémoire rapporte -485,23, supérieur à la log-vraisemblance -930,42. Les valeurs -567,00 et -485,23 de la section 2.3.8 ne sont pas des ELBO au sens de l'éq. (1.31). Pour `GaussianMixture`, `lower_bound_` est bien une moyenne par échantillon (S1, `_base.py`).

**A3. Comparaison des itérations (14 contre 29) biaisée.** Avec `tol = 1e-3`, `GaussianMixture` teste la variation par échantillon, `BayesianGaussianMixture` la variation totale (S1). Les deux seuils ne sont pas comparables. Avec les mêmes conventions, je trouve 8 itérations pour l'EM et 25 pour l'EM variationnel : le rapport « environ deux fois plus » du texte est un artefact de normalisation, le rapport réel est plus grand.

**A4. Taux de convergence de l'EM, éq. (1.19).** Le mémoire écrit r = lambda_max(I_obs^-1 I_man). La matrice de taux de Dempster, Laird et Rubin (S2, section 3) est I_com^-1 I_man (égale à I - I_com^-1 I_obs). L'information à inverser est l'information complète, pas l'observée.

**A5. Tableau 2.3, complexité.** L'étape M de l'EM variationnel est annoncée O(NKD^3) à cause de l'inversion de W_k. L'inversion coûte O(KD^3), indépendante de N. Les deux algorithmes ont le même ordre O(NKD^2 + KD^3) : l'EM classique inverse aussi (ou factorise) K covariances. Cela contredit la section 2.3.6, qui explique la baisse du rapport de temps quand D augmente par le coût en D^3 des deux algorithmes.

### B. Désaccords entre le texte et le code

**B1. Priors de l'EM variationnel : deux jeux différents.** Le code from scratch (3.3.1) et le mémoire utilisent beta0 = 1e-3, W0 = I, nu0 = D. Les résultats du chapitre 2 viennent de scikit-learn, dont les priors par défaut sont beta0 = 1, nu0 = D, W0^-1 = covariance empirique (S1). Cela change les résultats. Mes mesures (20 initialisations, n_init = 1) :

| Résultat | Mémoire | Priors du mémoire | Priors scikit-learn |
|---|---|---|---|
| Composantes actives, alpha0 = 1/6, K = 6 | 3 | 4 | 3 |
| Retrouve 3 composantes, 20 initialisations | 19 sur 20 | 4 sur 20 (init aléatoire) | 20 sur 20 |
| ARI Iris, Kmax = 3 | 0,684 | 0,568 | 0,684 (exact) |
| ARI selon type de covariance | 1,000 partout | 0,83 à 1,00 | 0,99 à 1,00 |

L'élagage du chapitre 2 est donc obtenu avec les priors de scikit-learn, pas avec ceux de la section 1.7 et du code from scratch. Il faut le dire et indiquer les hyperparamètres utilisés (beta0, W0, nu0, m0).

**B2. Type de prior de Dirichlet.** Le tableau 2.4 indique `weight_concentration_prior_type = 'dirichlet_process'` (valeur par défaut de scikit-learn, stick-breaking, S1) alors que tous les scripts et la théorie utilisent `'dirichlet_distribution'` (Dirichlet fini). Ce sont deux modèles différents. Le tableau doit indiquer `'dirichlet_distribution'`.

**B3. Variance ou écart-type.** Le tableau 2.4 et le texte (2.3.1) parlent d'une « covariance isotrope de variance 0,7 ». Le code utilise `cluster_std = 0.7`, c'est-à-dire un écart-type de 0,7 et une variance de 0,49.

**B4. Code from scratch de l'EM variationnel (3.3.1, annexe).** La boucle n'a ni calcul d'ELBO ni test d'arrêt : elle exécute toujours `n_iter = 200` itérations et renvoie `it + 1 = 200`. La sortie « 82 itérations » ne peut pas venir de ce code. Le mémoire décrit pourtant la convergence sur l'ELBO (1.7.6). L'annexe B est annoncée comme « détail du calcul de l'ELBO » mais ne contient que trois fonctions auxiliaires, sans l'ELBO. La nouvelle implémentation (`elbo_gmm_bayesien`) comble ce manque.

**B5. Section 3.2.1.** Le code cite les équations « (1.13), (1.14), (1.17) ». Les équations réelles sont (1.15), (1.16) et (1.18).

**B6. Initialisation.** La section 1.7.3.d décrit « m_k = m_0 + perturbation aléatoire » ; le code tire K points de données. Les algorithmes 3.2.1 et 3.3.1 utilisent une initialisation aléatoire, scikit-learn une initialisation k-means : c'est une des raisons de l'écart d'itérations (77 contre 14), à côté de A3.

### C. Résultats expérimentaux non reproduits ou fragiles

| Expérience | Mémoire | Reproduit | Commentaire |
|---|---|---|---|
| Valeurs aberrantes (2.3.12) | EM variationnel : 4 actives, trace 174,7 ; EM : 6 actives, trace 68,9 | 5 actives, trace 98,4 ; 6 actives, trace 6,2 | Le mémoire ne dit pas comment les 10 points sont générés ; le résultat dépend de ces points |
| Iris, Kmax = 6 (2.3.11) | 4 actives, ARI 0,602 | 3 actives, ARI 0,562 | Même tendance : l'EM variationnel ne fait pas mieux que l'EM classique (0,641) |
| Silhouette EM classique, K = 6 | 0,395 | 0,450 | Écart attribuable aux données générées différemment |
| Poids du tableau 2.5 | Aucun poids inférieur à 0,10 | Un poids de 0,013 apparaît selon l'initialisation | L'affirmation « aucun poids ne s'annule » dépend de l'initialisation |
| Temps de la scalabilité | Rapport 2 à 13 | Rapport 4 à 17 (PyTorch) | Dépend de la bibliothèque ; le rapport ne se transpose pas |

L'affirmation « les deux groupes restants se chevauchent partiellement » (2.3.2) est contredite par la géométrie du jeu : centres à distance 5, 5 et 7,1, écart-type 0,7, donc des groupes séparés de plus de 7 écarts-types.

### D. LDA

- Le tableau du corps du texte et la table A.1 ne sont pas cohérents avec les thèmes décrits : le document « bourse » est affecté au « topic 0 » dont les mots sont ceux du football ; le document 9 (chat) est dans un autre topic que les documents 0 et 2 (chat). Les commentaires de l'annexe A.5 reconnaissent le mélange sans l'expliquer.
- Ma LDA variationnelle (éq. 3.1 et 3.2, point fixe de Blei) produit aussi des thèmes mélangés sur ces 12 documents (pureté 0,67 sur 10 initialisations). Le résultat est instable sur un corpus aussi petit. La mention « sortie réelle » n'est pas vérifiable. Je recommande de conclure sur la borne variationnelle croissante et de ne pas interpréter les thèmes.
- La section 3.1.1 présente la LDA de scikit-learn comme un EM variationnel avec élagage. Scikit-learn utilise la version en ligne de Hoffman et al., avec un prior sur les thèmes, alors que l'éq. (3.2) correspond à l'algorithme original de Blei avec beta ponctuel.

### E. Références croisées et structure

- Les références aux équations sont fixes dans le texte et décalées : « (1.13) » désigne les responsabilités (réellement 1.15) en 1.3.5, 1.6.6 et 3.1.1 ; « (1.14) » désigne la mise à jour des poids (réellement 1.16) ; l'annexe B cite « (1.29) » pour l'ELBO (réellement 1.31).
- Tableaux : « tableau 1.3 » pour le résultat variationnel (réellement 1.5) ; « tableau 2.13 » pour la covariance (réellement 2.12).
- Figures des annexes : A.2 cite « figure 2.4 » (réellement 2.5), A.3 « figure 2.5 » (réellement 2.6), A.4 « figure 2.7 » (réellement 2.1).
- La section 3.1.2 renvoie à l'EM online en « 1.6.6 » (réellement 1.6.5).
- La section « Recommandations pratiques » était déclarée deux fois (corrigé).
- Annexe G.3 : l'espérance de log pi est présentée comme « appliquée à la section 1.4.4 », où seul E[pi] est calculé.
- L'énoncé « attracteur universel de la loi des grands nombres, conformément au théorème central limite » mélange les deux théorèmes.

### F. Bibliographie

- [1] : le premier auteur est **L. E. Baum** (pas A. C. Baum). Référence confirmée : Ann. Math. Statist., 41(1), 164-171, 1970 (S4).
- Références vérifiées sans erreur : Wu 1983 (S5), Neal et Hinton 1998 (S6), Louis 1982 (S7), Sato et Ishii 2000 (S8), Cappé et Moulines 2009 (S9), Rasmussen 2000 (S10), Celeux et Diebolt 1985 (S11).
- Citées dans le texte mais absentes de la bibliographie : Boyles (1983), Stauffer et Grimson (1999), Fisher (1936). Attias (2000) et Corduneanu et Bishop (2001), références classiques de l'EM variationnel pour le GMM, ne sont citées nulle part.
- La liste est annoncée comme alphabétique mais [20] Pedregosa et [21] Rasmussen suivent [19] Sato.
- Présentes dans la bibliographie mais jamais citées dans le texte : Bishop [2], Pedregosa [20], Rasmussen [21]. Les mentions de « processus de Dirichlet » (3.1.1) n'ont pas de citation.
- Le texte cite en auteur-année alors que la bibliographie est numérotée.

### G. Points théoriques confirmés

Tableau 1.4 (forward-backward) exact. Exemple Dirichlet (éq. 1.12) exact. Mises à jour Normal-Wishart (1.26, 1.28) conformes à Bishop (10.58 à 10.63) (S3). Équivalence de Neal et Hinton vérifiée numériquement. Le résultat du tableau 1.5 (alpha_k, élagage exact de la composante 3) est reproduit. BIC et AIC choisissent K = 3 (exp. 10). Baum-Welch : la log-vraisemblance estimée dépasse celle des vrais paramètres sur une séquence de 1000 observations, ce qui rappelle que le maximum de vraisemblance n'est pas la vérité sur une séquence courte.

## 3. Ce que je n'ai pas modifié

Hormis le retrait des parties non essentielles, `body.tex` est inchangé : les corrections ci-dessus changent des résultats et des conclusions, et je préfère que vous les validiez. Les plus urgentes sont A1, A2, B1 et B2. Je peux les appliquer dans `body.tex` (tableaux, textes, bibliographie) si vous me le demandez.

Autres points à décider : l'annexe A du mémoire (scripts sklearn) devra être remplacée par `algorithmes.py` et `main.py`, et l'annexe D (versions logicielles) par PyTorch, Pandas et Plotly.
