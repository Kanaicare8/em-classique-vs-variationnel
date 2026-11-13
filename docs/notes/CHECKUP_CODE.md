# Checkup du code (22 octobre 2026)

Relecture complète des modules Python, avec vérifications exécutées. Chaque défaut porte sa preuve, sa conséquence et sa correction.
Gravité : **critique** = invalide un résultat rapporté dans le mémoire ; **majeur** = biaise une comparaison ou contredit le protocole annoncé ; **mineur** = inexactitude sans effet probable sur les conclusions.

## 1. Défauts critiques (résultats du mémoire à invalider ou refaire)

### C1. Fuite apprentissage / test dans le cas climatique (N ≥ 500)
- **Où** : `cas_pratique_climat.py`, `sous_echantillons()` (lignes 155-161).
- **Preuve** (`outils/verif_fuite_climat.py`, exécuté) : le territoire compte 68 blocs de 100 km. Dès N = 500, presque tous les blocs contiennent un point d'apprentissage. Le code se replie alors sur 2000 cellules tirées au hasard dans **tout** le pays, y compris des points d'apprentissage :

  | N | blocs pris | repli | points de test présents dans l'apprentissage |
  |---|---|---|---|
  | 500 | 65-66 / 68 | 1 fois sur 3 | 0 ou 500 ; sinon test de 50-72 cellules |
  | 2000 | 66-67 / 68 | toujours | 177 à 191 sur 2000 |
  | complet | 68 / 68 | toujours | 2000 sur 2000 |
- **Conséquence** : H2 (« EM-BIC supérieur au VB en log-vraisemblance hors bloc à N = 2000 ») et la colonne « LL hors bloc » à N ≥ 500 sont en partie **intra-échantillon**. Or l'intra-échantillon récompense le modèle le plus flexible : ce résultat défavorable au VB n'est pas établi.
- **Correction** : validation croisée par blocs **avant** l'échantillonnage. Les blocs sont répartis en plis, le sous-échantillon d'apprentissage est tiré dans les blocs d'apprentissage seulement, et l'évaluation porte sur le pli retenu. La taille des blocs doit être estimée sur les données (portée de l'autocorrélation spatiale, voir E6).

### C2. Décisions prises avant la correction de Holm, et test choisi après coup
- **Où** : `comparaison.py`, `rapport_hypothese()` (lignes 384-397). Holm est appliqué ensuite, sans modifier la colonne `decision`.
- **Preuve** : `resultats/grille_scenarios.csv`, ligne S6[N=300] : décision « A < B » avec p de Holm = 0,0507. La décision affichée n'est pas celle d'un test corrigé.
- **Problème supplémentaire** : pour chaque hypothèse, le code calcule un TOST et un Wilcoxon, puis retient la p-valeur du test qui a conclu. C'est un choix a posteriori qui gonfle l'erreur de première espèce.
- **Conséquence** : toutes les grilles (scénarios, climat, texte) affichent des décisions non corrigées. La correction de Holm est décorative.
- **Correction** : pour chaque hypothèse, **un seul test déclaré à l'avance** (équivalence **ou** supériorité), et des décisions recalculées après Holm sur la famille déclarée.

### C3. Bootstrap de l'EM avec 1 initialisation contre 10 pour les ajustements principaux
- **Où** : `cas_pratique_climat.py`, couverture (`em_classique(Xs[ib], K_REF, n_init=1, ...)`) ; `cas_pratique_sp500_complement.py`, intervalles de VaR (`n_init=1`).
- **Conséquence** : la variabilité due aux optima locaux élargit les intervalles bootstrap de l'EM. Cela favorise artificiellement la couverture de l'EM (H6) et rend l'intervalle du VB « plus étroit » par comparaison. Les conclusions H6 et « intervalle VB environ un tiers plus étroit » sont biaisées.
- **Correction** : même `n_init` dans le bootstrap que dans l'ajustement principal. Le gain de vitesse du noyau par lots rend cela abordable.

## 2. Défauts majeurs

| # | Défaut | Où | Conséquence | Correction |
|---|---|---|---|---|
| M1 | H5 mal posée : la variance de K̂ du VB est mesurée sur une grille d'hyperparamètres choisie arbitrairement (α0 de 0,1 à 10, échelle de W0 de 0,1 à 10), puis comparée à la variance entre graines de l'EM-BIC | `cas_pratique_climat.py`, `sensibilite_priors()` | Le résultat dépend surtout de l'étendue de la grille : l'hypothèse ne peut pas être réfutée | Comparer (a) la variance entre graines à priors fixés, pour les deux méthodes ; (b) la sensibilité aux priors sur un domaine justifié, issu de la recherche de calibration (E6) |
| M2 | Couverture H6 conditionnée aux jeux où le VB trouve K̂ = 5 ; couverture de μ moyennée sur les coordonnées | `semi_synthetique()` | Biais de sélection, couverture « de μ » mal définie | Couverture inconditionnelle, ou conditionnelle annoncée comme telle ; une couverture par coordonnée |
| M3 | GARCH-t ajusté par 100 pas d'Adam (lr 0,05) sans test de convergence ; Student-t par L-BFGS sans contrôle | `cas_pratique_sp500_complement.py` | La supériorité du GARCH-t et les VaR associées reposent peut-être sur un optimum non atteint | Optimiseur avec critère d'arrêt (norme du gradient, variation relative), plusieurs départs, convergence enregistrée |
| M4 | TOST et Wilcoxon par approximation normale, y compris pour n = 10 (texte) et n = 20 (D = 20) | `comparaison.py` | p-valeurs inexactes. Exemple : 10 différences positives donnent p = 0,0051 par approximation, contre 0,0020 exactement | Wilcoxon exact par énumération (n ≤ 50) ; TOST avec la loi de Student (bêta incomplète écrite en PyTorch) |
| M5 | Même graine pour générer les données et initialiser les algorithmes (`GRAINE0 + r` des deux côtés) | `scenarios.py`, `cas_pratique_climat.py` | Les tirages de k-means++ réutilisent la suite aléatoire qui a généré les données : dépendance parasite | Graines dérivées et indépendantes par rôle (données, ajustement, bootstrap) |
| M6 | LDA : le terme constant `lgamma(Kα) − K lgamma(α)` de la borne est compté une fois au lieu de D fois ; `n_iter` compte les étapes E ; β est renvoyé après une étape M non évaluée | `algorithmes.py`, `lda_variationnel()` | Valeur de la borne fausse et critère relatif affecté ; le décompte d'itérations est différent du « critère commun » annoncé | Constante × D ; boucle alignée sur le pilote commun (E, critère, test, M) |
| M7 | La dégénérescence du VB est déclarée dès que N_k < D + 1, alors que sa covariance a posteriori est régularisée par le prior | `indicateur_degenerescence()` | H3, H8 et S6 comparent un défaut numérique de l'EM à une simple « petite composante » du VB | Deux indicateurs séparés et justifiés : covariance quasi singulière, et effectif inférieur à D + 1 (où l'estimateur du maximum de vraisemblance est singulier, un fait mathématique) |
| M8 | Temps mesurés avec jusqu'à 8 processus simultanés | scénarios, climat | H4 (coût) mesuré sous charge variable | Étape de chronométrage dédiée, exécutée seule, avec médiane de répétitions |
| M9 | S7 : les points aberrants gardent l'étiquette de leur groupe d'origine dans l'ARI | `scenarios.py`, `s7_aberrations()` | ARI « sur tous les points » mal défini | ARI hors aberrations, ou aberrations comme classe à part, annoncé avant l'analyse |
| M10 | `ic_bootstrap` boucle 5000 fois en Python | `comparaison.py` | Lenteur sans effet sur le résultat | Vectorisation (`v[idx].mean(1)`) |

## 3. Défauts mineurs
- Baum-Welch utilise une tolérance absolue et son propre décompte d'itérations, pas le critère commun. Ce n'est pas annoncé comme commun, mais c'est à harmoniser.
- `choisir_k_critere` s'arrête quand K > N/2 sans justification. À N = 30 et D = 5, l'EM complet avec K proche de 10 est mal posé de toute façon : il faut une règle justifiée, par exemple un nombre de paramètres inférieur à N.
- `echantillon_espace` réduit silencieusement la distance minimale de 10 % par essai, et la distance effective n'est pas enregistrée.
- `em_stochastique` et `em_online` ont des pas, des burn-in et des tailles de lot sans justification (voir E6).

## 4. Conformité à vos exigences

| Exigence | État avant le checkup | Fait depuis | Reste à faire |
|---|---|---|---|
| E1 Calcul tensoriel | Boucles Python sur K et sur les relances (environ 370 appels par itération) | Noyau EM, MAP-EM et VB par lots ; 20 tests d'équivalence avec la référence séquentielle figée ; gain ×4 (N = 300) à ×2 (N = 5000, D = 5) | Supprimer la matérialisation de (B, K, N, D) (statistiques suffisantes Xᵀ diag(r) X) ; paralléliser le balayage de K et les réplications ; vectoriser bootstrap, Wilcoxon et HMM |
| E2 Instantanés et reprise | Aucun : un arrêt perd tout le cas en cours | Mécanisme d'instantané dans la boucle EM/VB, avec reprise exacte testée | Points de reprise par unité de travail (réplication, effectif, bras), écritures atomiques, gestion des signaux, orchestrateur `run.py` |
| E3 Données d'entraînement enregistrées | Seulement des CSV agrégés ; X, y, ajustements et historiques sont perdus | — | Artefacts par unité : données, graines, paramètres, responsabilités, historiques ; figures regénérées depuis les artefacts seulement |
| E4 Pas de Jupyter | `code.ipynb` présent et documenté | — | Retirer le carnet (déplacé dans `legacy/`) ; tout passe par `python run.py` |
| E5 From scratch, PyTorch et Plotly | sklearn et nltk (corpus, mots vides, racinisation), matplotlib (cartes), numpy (climat) | — | Corpus 20 Newsgroups lu par `tarfile`, liste de mots vides et racinisation de Porter écrites à la main, cartes en Plotly. Lecture GeoTIFF/shapefile : voir la question plus bas |
| E6 Aucun paramètre arbitraire | Plus de 40 valeurs codées en dur, la plupart sans source | — | Registre `parametres.py` (source vérifiée, benchmark ou recherche heuristique pour chaque valeur), test qui échoue sinon, et étape `calibrage` |

### Inventaire des paramètres à justifier (E6)
- **Une source suffit** :
  - Robbins–Monro κ ∈ (0,5 ; 1] (Cappé et Moulines 2009, Hoffman et al. 2013).
  - Seuil N_k < D + 1 : fait mathématique, la covariance empirique de n points est de rang au plus n − 1.
  - α0 < d/2 (Rousseau et Mengersen 2011).
  - Correction de Holm (Holm 1979).
- **Benchmark** :
  - Tolérance 1e-6 et plafond 500 : stabilité des résultats selon la tolérance.
  - `reg` = 1e-6 ; n_init = 10 : probabilité d'atteindre le meilleur optimum.
  - Itérations et tolérances de k-means.
  - Nombre de tirages bootstrap (5000, 1000, 100, 50) et tirages Monte Carlo (200 000, 4000) : erreur Monte Carlo.
  - Nombre de réplications (30, 40, 60, 20, 10) : puissance.
  - Seuil de valeur propre 1e-6.
- **Recherche heuristique sur un grand espace** (validation croisée, sans toucher au test) :
  - Priors du VB (α0, β0, ν0, échelle de W0) et du MAP-EM (α0 = 2 actuellement).
  - LDA (α = 0,1, lissage 1e-3) et taille du vocabulaire (1500, df ≥ 5).
  - Pas de la SVI, de l'EM online et du SEM.
  - Nombre d'états du HMM.
- **Estimé sur les données** :
  - Taille des blocs (100 km) et distance minimale (15 km), par la portée de l'autocorrélation spatiale estimée sur les données. Roberts et al. (2017, Ecography 40:913-929, vérifié) établit la nécessité de la validation par blocs ; sa recommandation précise sur la taille des blocs n'a pas pu être lue dans le texte intégral (serveur indisponible) et n'est pas citée tant qu'elle n'est pas vérifiée.
  - Marges d'équivalence (0,03 en ARI, 0,5 composante, 0,1, 0,02 nat), par la plus petite différence d'intérêt (Lakens 2017) calibrée sur la variabilité entre graines.
- **Fixé par votre plan** : effectifs N, séparations S1, poids 80/15/5, ν = 3, grille de D, grille d'α0 autour de d/2. À citer comme choix de conception du plan.

Les sources ci-dessus seront vérifiées en ligne une par une avant d'entrer dans le registre. Aucune ne sera citée sans vérification.

## 5. Conséquences pour le mémoire
- **H2 (climat)** : à retirer tant que la validation par blocs n'est pas refaite (C1).
- **Décisions des grilles** : à recalculer après Holm, avec un seul test déclaré par hypothèse (C2). Au moins S6[N=300] change.
- **H6** : à refaire avec un bootstrap à `n_init` égal (C3), et la couverture conditionnelle à déclarer (M2).
- **H5** : à reformuler (M1).
- **GARCH-t** : la conclusion attend une optimisation contrôlée (M3).
- **Échecs du VB à D = 20** : ils venaient en partie de l'inversion numérique de W. Le nouveau noyau inverse par Cholesky et exclut les relances en échec au lieu d'abandonner l'ajustement. Le phénomène doit être remesuré avant d'être décrit.
- **Coûts (H4, scalabilité)** : à remesurer, car le noyau par lots change les temps relatifs.
