# Registre des décisions

Une fiche par décision : contexte, question, options et conséquences, recommandation, choix de l'étudiant,
justification, impact, ce qui reste en attente. Les décisions antérieures au 2026-11-04 consignées dans `notes/`
(notamment le choix du seul cas des prix le 2026-10-27, `notes/ANALYSE_3_CAS_PRATIQUE_RIGUEUR_OPTIMISATION.md`)
seront reprises ici en phase 1, après lecture complète de ces notes.

## D-01 Contraintes du projet (2026-11-04)

- **Contexte** : informations introuvables dans le projet lors de l'inventaire (phase 0).
- **Réponse de l'étudiant** :
  1. Échéance de dépôt : **22 novembre 2026**, sans sacrifier la rigueur.
  2. Volume : **112 pages au plus, annexes non comptées**.
  3. Machine de calcul : **tous les calculs tournent sur une instance cloud** c8g.8xlarge (spot), 32 cœurs, 61,6 Go,
     0,177 $/h ; budget du projet 40 $, 3,59 $ engagés le 2026-11-04 à 08:21 (tableau de suivi collé par l'étudiant).
     Chaque instance s'arrête seule à 95 % de son budget (d'après le même tableau).
- **Conséquences** :
  - 18 jours restent à partir du 2026-11-04 ; les calculs longs doivent repartir au plus tôt (lot 3 du plan).
  - Le corps du mémoire compilé le 27 octobre occupe les pages 1 à 102 en numérotation arabe (`main.toc` : annexes à la
    page 103), sous la limite de 112 pages ; à recontrôler après intégration des nouveaux résultats.
  - Au tarif affiché, il reste environ 36 $ soit environ 200 heures d'instance (estimation : 36,4 / 0,177 ; ne tient
    pas compte d'éventuels frais de stockage ou de transfert).
  - La machine locale (4 cœurs) ne sert plus au calcul ; le calibrage local arrêté le 2026-11-01 n'a pas à être repris.

## D-02 Version du code exécutée sur l'instance cloud (tranchée le 2026-11-04)

- **Contexte** : voir `NOTES_TECHNIQUES.md`, N-01. L'instance exécute le commit `97dcb95` (22 octobre), antérieur au
  retrait des cas climat et S&P 500 et à l'ajout du cas des prix ; le code local, qui porte ces changements, n'est pas
  commité.
- **Question** : que faire du calcul en cours sur l'instance ?
- **Options** :
  - A. Arrêter le calibrage cloud en cours, commiter et pousser l'état local après sa vérification (tests et essai
    réduit), puis relancer le calibrage sur l'instance à partir de ce commit, dans un magasin vide. Coût : le calcul
    déjà fait est perdu (environ 3,6 $ et 20 h d'instance) ; une demi-journée de vérification avant relance.
    Conséquence : un seul calibrage, sur le code décrit dans le mémoire.
  - B. Laisser finir le calibrage cloud et en réutiliser les unités communes (synthétique, Iris, texte). Coût : environ
    1 h 10 de plus selon le tableau. Conséquence : il faudrait démontrer que ces unités donnent le même résultat avec le
    code actuel (`calibrage.py` et `parametres.py` diffèrent de 116 lignes ajoutées et 208 supprimées depuis
    `97dcb95`) ; sans cette preuve, le calibrage ne correspond pas au code qui produira les résultats.
  - C. Laisser l'essai réduit (`--rapide`, 173 / 177) finir, puisqu'il ne coûte que quelques minutes et vérifie que la
    chaîne tourne sur l'instance, mais arrêter le calibrage complet (combinaison de A pour le calibrage).
- **Recommandation de Claude** : C puis A. L'essai réduit ne sert qu'à vérifier la chaîne et n'entre pas dans les
  résultats ; le calibrage complet de l'ancien code ne peut pas servir au mémoire sans une preuve d'équivalence qui
  coûterait plus cher que le recalcul.
- **Choix de l'étudiant (2026-11-04)** : **option A**. L'étudiant arrête le calibrage en ligne ; Claude pousse le code
  local ; l'étudiant récupère le code sur l'instance et relance.
- **Justification** : le calibrage doit porter sur le code décrit dans le mémoire.
- **Impact** : commit `e5eeaf8` (sans `SUIVI/` ni `resultats/calibrage/` local) ; ancien magasin de l'instance mis de
  côté dans `resultats/archive_97dcb95/` ; relance décrite dans `EXPERIENCES/E-01.md`.
- **En attente** : sorties de E-01.

## D-03 Validation du plan de travail (2026-11-04)

- **Contexte** : plan de la phase 3 (`PLAN_DE_TRAVAIL.md`, P-01 à P-24).
- **Choix de l'étudiant** : P-01 à P-23 **acceptés** ; P-19 accepté **sous condition de disposer du canevas officiel
  de l'école** ; P-24 (étiquette Git, archive Zenodo) **reporté à la fin du travail**.
- **Remarque** : pour P-02, la réponse écrite renvoyait à « options B et C de Q-2 » ; la décision finale donnée pour
  Q-1 (option B) fait foi (D-04). P-07 suit Q-1.
- **Impact** : exécution par lots (phase 4) dans l'ordre du plan ; chaque changement de méthode suit la fiche D-xx
  correspondante.

## D-04 Marge d'équivalence (Q-1, P-02, P-07)

- **Options** : A garder la règle actuelle (quantile 95 % du bruit numérique, plancher 0,001) ; B marges fixées à
  l'avance par l'importance pratique ; C marge tirée de la variabilité d'échantillonnage.
- **Recommandation de Claude** : B.
- **Choix de l'étudiant** : **option B, avec une justification scientifique préalable des deux marges** (ARI et
  log-vraisemblance par observation).
- **Impact** : `fin_marges` (`calibrage.py` l. 607-616) ne fixe plus les marges ; elles deviennent des valeurs du
  registre (`parametres.py`) au statut « fixée a priori », avec leur justification ; tableau de sensibilité (moitié et
  double de chaque marge) ; écart au protocole déclaré au chapitre 2 (règle changée avant tout résultat confirmatoire).
  HP5 (P-07) utilise la même marge.
- **En attente** : proposition par Claude des deux valeurs avec leurs appuis (sources vérifiées), puis **accord de
  l'étudiant sur les valeurs** avant écriture du code. À faire avant la vague 6 du calibrage.

## D-05 Nombre de réplications (Q-2, P-03)

- **Options** : A garder ; B exclure du maximum les hypothèses sans variance pilote ; C plafonner R par le budget de
  temps.
- **Recommandation de Claude** : B et C.
- **Choix de l'étudiant** : **options B et C**.
- **Impact** : `_r_requis` et `fin_puissance` (`calibrage.py` l. 722-761) : une hypothèse dont les différences pilotes
  sont toutes identiques est marquée « sans variance » et ne fixe plus R ; R retenu = min(R calculé, R tenable) ; la
  puissance atteinte est rapportée pour chaque hypothèse ; R tenable calculé depuis la durée mesurée des unités
  pilotes et l'échéance des calculs (15 novembre).
- **En attente** : écriture du code (lot 2), avant la vague 7 du calibrage ; la règle de calcul de R tenable sera
  soumise à l'étudiant avec le code.

## D-06 Dégénérescence (Q-3, P-04)

- **Choix de l'étudiant** : **option B** : un même critère pour tous les bras (valeur propre minimale < 1e-6 × trace,
  ou 1 ≤ N_k < D + 1), appliqué à la covariance plug-in de chaque bras.
- **Impact** : `algorithmes.py` (`indicateurs_degenerescence`) et ses appels ; texte du chapitre 2 aligné. Avant
  l'étape des scénarios.

## D-07 Couverture HP6 (Q-4, P-06)

- **Choix de l'étudiant** : **option B** : bootstrap d'EM-BIC (K choisi sur chaque rééchantillon) ajouté à côté de
  celui d'EM-K ; RH3 lue sur EM-BIC contre VB, EM-K servant de borne.
- **Impact** : `etape_prix.py` (`unite_couverture`), tableaux et texte de HP6. Avant l'étape des prix.

## D-08 Conformité au plan de l'école et volume (Q-5, P-19, P-20)

- **Choix de l'étudiant** : **recommandation acceptée** (chaque point du plan de l'école en sous-section titrée ;
  environ 10 pages du chapitre 1 déplacées vers les annexes), **sous réserve de vérifier le canevas officiel**.
- **En attente** : le canevas officiel de l'école (fichier ou courriel), à fournir par l'étudiant. P-19 ne commence
  pas sans lui ; P-20 peut être préparé.

## D-09 Découpage de l'unité `n_init/texte` (P-01) réalisé par le commit `315a21c`

- **Constat (2026-11-04)** : le dépôt distant porte un commit `315a21c` (auteur Git « Georges Moukoko », 2026-11-04
  09:27) qui règle A-01 autrement que P-01 : les sous-calculs des unités longues (`n_init/texte`, `priors/*`,
  `fin/texte`, `fin/variantes`) sont calculés en parallèle par `etapes.sous_taches_paralleles`, sous leurs clés de
  mémoire habituelles, puis relus par la boucle d'origine ; verrou du magasin dans `run.py` ; script
  `outils/verifier_parallele.py` de comparaison bit à bit avec le calcul séquentiel.
- **Analyse de Claude** : voir `NOTES_TECHNIQUES.md`, N-02. Numériquement neutre d'après la lecture du code ; reste à
  le vérifier par le script.
- **Décision proposée** : retenir `315a21c` à la place du découpage en 16 unités de P-01 (même effet, couvre aussi la
  vague 5).
- **En attente** : confirmation par l'étudiant de l'auteur du commit (attribution) ; sortie de
  `python outils/verifier_parallele.py --n 3` sur l'instance.

## Suites du 2026-11-04 (réponses de l'étudiant : « pour la suite c'est ok, gère comme ça et pousse le code »)

- **D-09, attribution** : « Georges Moukoko » est un tiers qui travaille avec l'étudiant. Le commit `315a21c` lui est
  attribué tel quel dans l'historique Git ; il devra être cité (remerciements ou annexe A, au choix de l'étudiant).
  Vérification bit à bit : en attente (calibrage en cours sur l'instance).
- **D-08, canevas** : reçu (`Structure du memoire.pdf`), transcrit dans `CANEVAS_ECOLE.md`. P-19 peut commencer. Le
  canevas ajoute un plan en 5 points pour le chapitre Résultats et discussion.
- **D-04, valeurs retenues sur délégation de l'étudiant** : ARI 0,05 ; log-vraisemblance moyenne par observation
  0,05 nat. Justification écrite dans `parametres.py` (statut « plan ») :
  - ARI : moitié de la largeur d'une classe de l'échelle usuelle de qualité de récupération (0,65 / 0,80 / 0,90).
    **Source à vérifier** : l'échelle est attribuée à Steinley (2004, Psychol. Methods 9(3), 386-396) par la
    documentation du paquet R CrossClustering ; je n'ai pas pu lire l'article. Si l'article ne la donne pas, il faudra
    citer la source secondaire ou une autre justification.
  - Log-vraisemblance : 0,05 ≈ log(1,05), soit une densité prédictive plus forte d'au plus 5 % en moyenne géométrique.
  - Appui méthodologique : Lakens, Scheel et Isager (2018, Adv. Methods Pract. Psychol. Sci. 1(2), 259-269), sur la
    plus petite différence d'intérêt fixée avant l'analyse.
  - Le bruit d'optimisation, mesuré par la vague « marges », sert désormais de contrôle (la marge doit le dépasser).
  - Tableau de sensibilité (moitié et double) : à produire avec les tableaux (lot 4).
  - **L'étudiant peut encore changer ces deux valeurs** tant qu'aucune étape confirmatoire n'a tourné.
- **D-05, règle écrite** : exclusion des hypothèses sans variance ; plafond commun par un budget de 96 heures
  d'instance (paramètre `budget_replications`), avec réduction proportionnelle de toutes les clés et puissance obtenue
  rapportée par hypothèse. Le budget (96 h, environ 17 $) est modifiable par l'étudiant.
- **D-06** : écrit (même critère pour tous les bras, sur la covariance plug-in finale).

## D-10 Structure de la partie I (P-19, P-20), 2026-11-04

- **Options** : A, deux chapitres dans la partie I (chapitre 1 : cadre conceptuel ; nouveau chapitre 2 : état de
  l'art, limites de la littérature, lien avec la recherche, synthèse) ; B, sections ajoutées au chapitre 1.
- **Recommandation de Claude** : A.
- **Choix de l'étudiant** : **A**.
- **Impact** : la méthodologie devient le chapitre 3 et les résultats le chapitre 4 (renvois automatiques) ; la section
  « Portée : domaines non testés » (revue) passe dans l'état de l'art ; points manquants de la méthodologie ajoutés ;
  environ 10 pages du chapitre 1 vers les annexes.

## D-11 Sous-processus de l'unité fin/texte, 2026-11-04

- **Contexte** : la session qui pilote l'instance signale que `fin/texte` n'utilise que 8 cœurs sur 32
  (`ICARE_SOUS_TRAVAILLEURS=8`, consigne N-02 prévue pour quatre unités simultanées en vague 5).
- **Décision** (réglage d'exécution, sans effet sur les résultats : mêmes graines, un fil par processus, vérification
  bit à bit par `outils/verifier_parallele.py`) : si `fin/texte` est la seule unité de la vague 5 encore en cours,
  relancer avec `ICARE_SOUS_TRAVAILLEURS=31` ; si une autre unité de la vague tourne encore, 24. Les sous-calculs déjà
  écrits sont relus.

## D-12 Ce que comptent les 112 pages (2026-11-04)

- **Réponse de l'étudiant** : seul le contenu principal compte (introduction générale à conclusion générale) ; la
  bibliographie et les annexes n'entrent pas dans les 112 pages.
- **Impact** : le corps se termine à la page 101 (compilation du 2026-11-04) ; marge d'environ 11 pages pour les
  tableaux et figures des résultats (lot 4). Pas d'allègement supplémentaire pour l'instant ; contrôle du volume au lot 4.

## D-13 Vérifications que l'étudiant ne peut pas faire (2026-11-04)

- **Contexte** : l'étudiant ne peut pas lire Wu (1983) ni vérifier ce que contiennent toutes les sources citées ;
  consigne : « gère comme tu peux ».
- **Décision prise par Claude** : (1) le théorème de Wu ne contient que ce qui est vérifié (résumé de l'article pour le
  cas unimodal ; reformulations secondaires pour la convergence de la vraisemblance et des points d'accumulation) ; aucune
  condition supplémentaire n'est ajoutée. (2) Les lacunes de la littérature (section 2.6), la synthèse (2.8) et
  l'introduction de la méthodologie sont formulées comme « nous n'avons pas trouvé, dans les sources citées… », vraies
  même si une source contient davantage. (3) L'échelle de Steinley reste retirée.
- **Conséquence pour la soutenance** : si le jury cite un travail qui comble une des lacunes, la réponse est que le
  constat porte sur les sources citées, et que le protocole de ce mémoire (critère d'arrêt commun, base EM-BIC, tests
  déclarés) reste sa contribution.

## D-14 Relances et sensibilité au vocabulaire de l'étape texte (2026-11-05)

- **Contexte** (session de l'instance) : la règle « n_init » donne 200 relances pour le texte (pLSA : p = 0,005 de
  retrouver la même solution, plafond atteint) ; l'étape confirmatoire texte (93 unités, jusqu'à 1 000 documents, plus
  d'une heure par ajustement) représenterait environ 37 000 ajustements, hors budget.
- **Options présentées** : règle par l'écart au meilleur (recommandée) ; plafond fixe à 10 ; garder 200 et augmenter
  le budget (80 $ ou plus). Pour le vocabulaire : garder 500 et 3 000 avec 3 réplications (recommandé) ; tel quel ;
  retirer.
- **Réponse de l'étudiant** : « fais ce qu'on demande de faire », comprise comme : appliquer les recommandations.
- **Règle retenue** : paramètre `n_init_texte_confirmatoire`, par algorithme, plus petit n ≤ 20 tel que la meilleure
  de n relances (tirées parmi les 200 relances pilotes de `n_init/texte`) soit à moins de 0,1 % du meilleur critère
  pilote avec probabilité ≥ 0,99 ; LDA : maximum sur les trois alpha. Calculé par l'unité `fin/n_init_texte`, sans
  nouvel ajustement ; les pilotes de puissance texte l'attendent. `fin/texte` (recherche LDA, en cours) garde 200.
  Tailles de vocabulaire 500 et 3 000 : 3 réplications ; HT1 (taille principale) inchangé.
- **Impact** : au plus 20 relances au lieu de 200 (au moins 10 fois moins d'ajustements) ; unités texte de sensibilité
  ramenées de 6 × R à 18. Écart au protocole (6) déclaré au chapitre 3. Commit `5bd4fe7`.
- **Limite déclarée** : la règle est estimée sur le pilote à 200 documents ; la difficulté peut être plus grande à
  1 000 documents.

## D-15 Tolérance, relances, étape E de la LDA et grille de régularisation (2026-11-05)

- **Contexte** (session de l'instance, calibrage mis en pause à 1 unité sur 448, 6,99 $ engagés ; chiffres lus dans le
  magasin, sans nouvel ajustement, rapportés dans son message du 2026-11-05) :
  1. `fin_tolerance` : aucune tolérance n'atteint 99 % d'accord (critère et ARI) ; le code gardait en silence
     min(GRILLE_TOL) = 1e-9 et écrivait la règle comme remplie. Parts d'accord critère + ARI / critère seul :
     1e-6 64,3 % / 88,5 % ; 1e-7 83,3 % / 97,1 % ; 1e-8 92,8 % / 99,4 % ; 1e-9 96,8 % / 99,8 %. À 1e-9, 28 désaccords
     sur 30 ont le même critère (écart médian 1e-7 par observation) et un ARI juste sous 0,99 (médiane 0,987), presque
     tous des EM à K = 3 sur S1 (classes qui se chevauchent). Itérations moyennes 134 à 1e-8, 161 à 1e-9.
  2. `fin_n_init` : le maximum sur les cas atteint le plafond de 200 pour toutes les familles, même avec un seuil de
     succès de 5e-4 par observation ; 74 cas pilotes sur 226 demandent au moins 200 relances, médiane 26 (VB à Kmax
     avec priors diffus ou aléatoires ; EM à Kmax sur S3, S7 et les prix ; p de 0,015 à 0,02).
  3. `lda_variationnel` : la boucle de l'étape E était bornée par `n_iter_max` (2 200), comme la boucle externe ;
     `fin/texte` est passé de 7 à 1,5 LDA par minute.
  4. `fin_regularisation` : `reg_covariance` = 0,1, plus grande valeur de la grille, le rang moyen s'améliorant encore
     (2,91 à 0,01 ; 2,71 à 0,1).
  Vérifié dans le code avant décision : `calibrage.py` (repli `choix = min(GRILLE_TOL)`, règle du maximum dans
  `fin_n_init`, `GRILLE_REG` jusqu'à 1e-1), `algorithmes.py` (`for _ in range(n_iter)` dans l'étape E). Le texte du
  registre pour `tol_rel` décrivait en outre une autre règle que le code (comparaison à une tolérance 100 fois plus
  stricte) : corrigé.
- **Options présentées** : (1) tolérance sur le critère seul, ARI rapporté, arrêt si aucune valeur ; (2) 20 relances
  fixes pour toutes les familles, probabilité rapportée par cas, 10 si le coût dépasse le budget ; (3) étape E de la
  LDA plafonnée à 100 ; (4) grille étendue à 0,3 et 1, valeur au bord signalée. Alternatives : 10 relances fixes ;
  garder la règle des relances et augmenter le budget.
- **Réponse de l'étudiant** : « Appliquer les 4 (Recommandé) ».
- **Règles retenues** :
  1. `fin_tolerance` : accord = écart du critère par observation < 5e-4 ; la part d'accord critère et ARI est rapportée
     (`part_accord_critere_et_ARI_par_tol`) ; `RuntimeError` si aucune tolérance de la grille n'atteint 99 %. L'accord
     est recalculé depuis les écarts mémorisés : les unités `tolerance/<jeu>` restent valables.
  2. `N_INIT_FIXE` = 20 ; `n_init` = 20 pour synthetique, iris, prix et texte (la valeur texte sert à la recherche LDA
     `fin/texte` ; les étapes confirmatoires du texte gardent D-14). Pour chaque cas pilote, `n_init.json` rapporte la
     probabilité exacte (tirage sans remise, loi hypergéométrique, `proba_meilleur`) que la meilleure de 20 relances soit
     à moins de 5e-4 par observation du meilleur des 200 relances pilotes, et la valeur qu'aurait donnée la règle initiale.
  3. Paramètre `lda_iter_e` = 100 (statut source : `max_doc_update_iter` de scikit-learn) ; `etapes_e_plafonnees`
     rapporté par `lda_variationnel`. Chaque itération de point fixe augmente la borne : le critère reste croissant.
  4. `GRILLE_REG` = 0, 1e-10, 1e-8, 1e-6, 1e-4, 1e-3, 1e-2, 1e-1, 0,3, 1 ; `au_bord_de_la_grille` dans
     `regularisation.json`.
- **Résultats à recalculer** (les clés du magasin ne contiennent pas la tolérance) : `fin/tolerance`, `regularisation/*`,
  `fin/regularisation`, `n_init/*`, `fin/n_init`, `priors/*`, `fin/priors`, `fin/texte`, `fin/variantes`,
  `fin/n_init_texte`, avec leurs sous-calculs `_sous/`, et les fichiers correspondants de `resultats/calibrage/`.
  Restent valables : `kmeans/*`, `fin/kmeans`, `tolerance/<jeu>`, `corpus/V=*`. Procédure : E-01, mise à jour (5).
- **Impact** : 20 relances au lieu de 200 (10 fois moins d'ajustements) dans le calibrage et les étapes confirmatoires ;
  tolérance attendue 1e-8 et plafond d'environ 1 800 étapes M (d'après les parts ci-dessus, à confirmer par
  `tolerance.json`). Écart au protocole (7) déclaré au chapitre 3 ; règles de calibrage et description de la LDA mises à
  jour ; correction au passage : « EM variationnel à $\theta$ ponctuel » devient « à $\beta$ ponctuel » (le texte
  disait ensuite que $\beta$ est ponctuel).
- **Limites déclarées** : avec 20 relances, la probabilité d'atteindre le meilleur optimum pilote peut être faible pour
  certains cas (VB à Kmax avec priors diffus) ; elle est rapportée, et EM et VB ont le même nombre de relances. Si la
  meilleure régularisation est encore au bord de la grille, elle est déclarée comme telle.

## D-16 Vérification des propriétés sans régularisation, baisses mesurées, régularisation d'Iris (2026-11-05)

- **Contexte** : lecture P-23 (N-06), constats A-14, A-15, A-16 de `ETAT_DU_PROJET.md`.
- **Options présentées et réponses de l'étudiant** :
  1. A-14 : ε = 0 pour la vérification des propriétés (recommandé) ou garder et déclarer. **Choix : ε = 0.**
  2. A-15 : mesurer les baisses de l'EM en lot complet (recommandé) ou laisser le 0 écrit en dur. **Choix : mesurer.**
  3. A-16 : garder la valeur unique et déclarer la limite (recommandé, échéance), valeur par famille (vagues suivantes
     du calibrage à refaire) ou standardiser Iris. **Choix : garder et déclarer.**
- **Réalisé** : `etape_validation.py` (`REG_PROPRIETES = 0.0` ; échecs de l'EM comptés à part ; part d'EM dégénérés ;
  maxima sur les seules graines où la mesure existe) ; `etape_illustrations.py` (baisses mesurées depuis `ll_hist`,
  docstring) ; `body.tex` (voir `CHANGEMENTS_MEMOIRE.md`). Sauvegarde : `sauvegardes/20261105-135939_A14/`.
- **Impact** : étapes validation et illustrations seulement ; le calibrage en cours n'est pas touché. Ces deux étapes
  doivent tourner avec ce code (à récupérer sur l'instance avant E-02).
- **Limite déclarée** : sur Iris, ε = 0,1 (valeur reçue de l'instance, à confirmer par `regularisation.json`) dépasse
  les variances intra-espèce de la largeur des pétales (0,0115, 0,039, 0,075 cm², calculées sur `data/iris.csv`).
