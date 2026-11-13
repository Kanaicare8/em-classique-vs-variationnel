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

## D-00 Décisions antérieures au suivi, reprises des `notes/` (P-23, 2026-11-05)

Prises avant la création de ce dossier ; reprises telles qu'écrites dans les notes, sans nouvelle vérification sauf
mention.

| Date | Décision | Source | Mise en œuvre |
|---|---|---|---|
| 2026-10-22 | Un seul test déclaré à l'avance par hypothèse (équivalence ou supériorité) et décision sur la p ajustée par Holm, par famille (C2) | `notes/CHECKUP_CODE.md` § C2 | `statistique.decider_famille` (d'après `notes/ANALYSE_3_...md` § 1) |
| 2026-10-22 | Bootstrap de l'EM démarré depuis l'EM à `n_init` relances, et non à une seule (C3) | `notes/CHECKUP_CODE.md` § C3 | `etape_prix.unite_couverture` (même source) |
| 2026-10-22 | Validation croisée par blocs avant l'échantillonnage, sans fuite apprentissage / test (C1) | `notes/CHECKUP_CODE.md` § C1 | cas climat, retiré depuis ; principe repris par les plis temporels des prix (`calibrage.plis_temporels`) |
| 2026-10-22 | Paramètres réunis dans un registre (`parametres.py`) et calibrés par une étape dédiée ; chaîne reprenable ; sklearn, nltk, matplotlib et Jupyter retirés | `notes/ANALYSE_2.md` § 4 | `parametres.py`, `calibrage.py`, `run.py` |
| 2026-10-22 | Wang et Blei (2019), Attias (2000), Balakrishnan et al. (2017) cités comme renvois seulement, faute de copie lue | `notes/ANALYSE_SOURCES.md` § 4, `references/SOURCES.md` | texte |
| 2026-10-27 | Seul le cas des prix alimentaires du PAM est retenu ; climat et S&P 500 retirés du mémoire et de la chaîne, code gardé dans `legacy/` | `notes/ANALYSE_3_...md`, en-tête | `etape_prix.py`, `hypotheses.py` (HP, HPP), section 3.1 |

## D-17 Contrôles du calibrage complet : marge LL, puissance de HP7-N120, sous-tâches du texte (2026-11-06)

- **Contexte** : calibrage terminé le 2026-11-06 à 06 h 04 UTC sur `34e02b3` (590 unités sur 590, 88 tests passés),
  fichiers récupérés dans le dépôt (`7782ae6`, `resultats/calibrage/`). Lu dans les fichiers :
  - `marges.json` : bruit d'optimisation (quantile à 95 % de l'écart absolu entre deux ajustements d'un même bras,
    128 paires) ARI 0,0443 sous la marge 0,05 ; LL 0,0657, au-dessus de la marge 0,05 (« ATTENTION »).
  - `puissance.json` : R = 110 (scénarios), 100 (prix_semi), 200 (prix_sous), 50 (prix_sensibilite), 10 (texte) ;
    facteur de budget 1,0 (535 853 s requises pour 10 713 600 s) ; HP7-N120 : plafond atteint, puissance 0,743.
- **Décisions** (application des règles déjà validées, aucun changement de méthode) :
  1. **Marge LL gardée à 0,05**, le contrôle étant déclaré comme limite. Raisons : D-04 fixe les marges a priori, et les
     relever après avoir vu le bruit reviendrait à la règle abandonnée ; le bruit est l'écart d'une seule paire, alors
     que le TOST porte sur la moyenne de R différences : ce bruit augmente la variance (donc baisse la puissance, déjà
     simulée sur les pilotes) sans biaiser la décision ; la sensibilité au double de la marge (0,10, au-dessus du bruit)
     est rapportée (`decision_marge_double`). Conséquence à écrire : une équivalence en LL non démontrée à 0,05 peut
     refléter le bruit d'optimisation plutôt qu'une différence entre méthodes.
  2. **HP7-N120 accepté à 0,743** : D-05 plafonne R à 200 et rapporte la puissance obtenue ; étendre la grille après
     avoir vu la puissance serait un réglage a posteriori. Puissance à rapporter avec le test.
  3. **Sous-tâches pour les unités texte à N = 1 000** : accord de principe, à condition que (a) la session de l'instance
     prépare le changement dans un commit à part, que je relis avant le lancement ; (b) la vérification bit à bit sur un
     petit cas montre des résultats identiques avec et sans sous-tâches ; (c) les sous-processus ne tournent pas pendant
     le chronométrage (étape exécutée seule, P-11) ; (d) le nombre total de processus ne dépasse pas les cœurs.
- **Ensuite** : la session de l'instance récupère le code (D-16 inclus), vérifie qu'aucun résultat
  `validation/proprietes` ni `illustrations/variantes` n'existe (consigne E-02), relance les tests, puis lance E-02.
- **Suite (2026-11-06)** : commit `620852a` (branche `texte-sous-taches`) relu et fusionné dans `main` ; les quatre conditions sont remplies (commit séparé ; résultats identiques avec et sans sous-tâches sur un cas de 20 documents, pas de comparaison à N = 1 000 ; actif seulement dans l'étape texte avec `ICARE_SOUS_TRAVAILLEURS` > 1 ; unités simultanées limitées à cœurs ÷ sous-tâches). Réglage E-02 : `ICARE_SOUS_TRAVAILLEURS=2` ; 100 tests passés sur l'instance. Coût : un réajustement de la meilleure relance de plus par unité ; gain estimé (non mesuré) : 4 à 6 h au lieu de 7 à 11 h par unité à N = 1 000.

## D-18 Résultats E-02 intégrés au mémoire (lot 4), 2026-11-07

- **Contexte** : E-02 terminée le 2026-11-07 à 04 h 32 UTC sur `bfcc3ff` (toutes les unités des sept étapes, aucune
  erreur non résolue, 3,91 $ pour E-02, 16,78 $ engagés au total sur 40 $) ; sorties poussées par la session de
  l'instance sur la branche `resultats-e02` (`a35320e`, `5e6bd89`), fusionnée en avance rapide dans `main`.
  Demande de l'étudiant : « analyse les et termine une fois mon mémoire ».
- **Corrections de code (mise en forme, aucun résultat recalculé)** :
  1. `tex_tables._verdict` ne reconnaissait pas l'attendu « VB < EM-BIC » de HP6-diff et classait ces deux décisions
     « non tranché » alors qu'elles sont conformes. Corrigé (comparaisons orientées nommées) ; RH3 passe de 2 à 4
     décisions conformes, 1 non tranchée. Seuls `bilan_recherche`, `lecture_prix`, `lecture_recherche` changent.
  2. Caractères Unicode des tableaux générés (α, ₀, ≥, K̂...) : 149 erreurs LaTeX. `K̂` converti dans les en-têtes et
     légendes (`ecrire`), les autres déclarés dans `main.tex` (`\DeclareUnicodeCharacter`).
- **Constats de l'analyse** (dans les fichiers) :
  - HT1 : moyennes des différences dominées par les probabilités nulles du pLSA (2,39e42 à N = 50) ; décision par
    rangs, lecture par Hodges-Lehmann.
  - Sens d'une différence : la moyenne remplace Hodges-Lehmann quand celui-ci est nul (indicatrices), règle du code
    désormais écrite au chapitre 3.
  - Chronométrage : le VB atteint le plafond de 1 800 étapes dans 11 répétitions sur 20 à N = 5 000 et 20 sur 20 à
    N = 20 000 (`chronometrage_brut.csv`) : temps = borne inférieure, déclaré. Lignes « N = 2001 » : jeu de la grille
    en D (`N_FIXE`), texte corrigé.
  - Le texte écrit avant les résultats contenait des affirmations fausses ou périmées, corrigées : « dix
    initialisations » (20 depuis D-15), « K de 1 à 8 » (1 à 6), « 20 graines » (110), « médianes de dix répétitions »
    (vingt), grille de α0 (neuf valeurs), « partition de l'EM fragmentée » (ARI 0,995), « l'EM conserve par
    construction ses six composantes » (5 et 24 exécutions sur 110 passent sous le seuil de 1 %), renvoi du coût
    vers la bonne section.
- **Question de la session de l'instance (chronométrage interrompu le 06/11 à 09 h 19)** : pas de nouvelle mesure.
  Chaque répétition est mémorisée et l'étape tourne seule ; seules les répétitions en cours ont été refaites, sur
  une instance du même type. Déclaré dans la discussion critique (limite 6).
- **Mémoire** : les 16 cadres « À compléter » sont remplis à partir des tableaux ; synthèses ajoutées pour les
  scénarios, le cas des prix et le texte ; mise en relation avec la littérature, limites des résultats et
  perspectives écrites ; conclusion générale complétée (« Réponses aux hypothèses de recherche ») ; résumé, abstract
  et liste des abréviations ajoutés (`liminaires.tex`, canevas de l'école). Détail : `CHANGEMENTS_MEMOIRE.md`.
- **Reste à faire** : figures PNG (Chrome absent sur l'instance, les PNG de `figures/` datent du 04/11 et ne
  correspondent pas aux résultats) ; relecture par l'étudiant ; P-24 (étiquette Git et archive).
- **Volume (D-12)** : avec les tableaux générés, le contenu principal atteignait environ 124 pages. Déplacés en
  annexe H (nouvelle) : moyennes par bras des scénarios S1 à S7, grille S8, `prix_resume`, `prix_ecartes`, lectures
  détaillées décision par décision (scénarios, prix, texte) et `sensibilite_marges` ; le chapitre garde les tableaux
  de décision et des synthèses rédigées. Résultat : introduction page 3, conclusion jusqu'à la page 114, soit 112
  pages, à la limite. Corrections de génération au passage : en-têtes `N_k` et `K_ref`, note de `prix_complet`
  (`ef` lu comme retour chariot), valeur de `tol_rel` du registre ; renvois `tab:1_2`, `tab:1_4`, `tab:1_5`
  devenus `tab:t1_*`. Compilation : 0 erreur, aucune référence indéfinie, 168 pages au total.

## D-19 Alignement des réplicats du bootstrap de l'EM (cas des prix), 2026-11-07, recalcul le 2026-11-09

- **Défaut** : les bootstraps de l'EM de l'étape des prix (`etape_prix.unite_alerte` et les 300 unités
  `couverture/*` de HP6) alignaient chaque réplicat sur le modèle de référence par appariement hongrois sur les seules
  moyennes (`cdist(mu)`). Le modèle de référence a K = 2 composantes aux moyennes voisines (tension 10,5 %, maïs
  +0,11 ; calme 89,5 %) : dans 47 réplicats sur 200, l'alignement prenait la grosse composante pour la tension.
- **Diagnostic** (script `diag_alerte_em.py` de la session du 07/11) : largeur moyenne de l'IC à 90 % de
  P(tension), EM-BIC : 0,94 avec l'ancien alignement (IC contenant 0,5 : 100 %), 0,10 avec l'alignement par
  responsabilités (7 %), à comparer à 0,08 pour VB-emp (6 %). L'alignement par responsabilités est identique au
  démarrage chaud dans 200 cas sur 200.
- **Correctif** : `comparaison.aligner_bootstrap`, appariement hongrois sur le recouvrement des responsabilités
  calculées sur les données d'origine, utilisé par `unite_couverture` et `unite_alerte` (commit `a0eead6`) ; test
  `tests/test_alignement_bootstrap.py` ; suite complète : 102 tests passés (sur l'instance, le 2026-11-09).
- **Effet attendu** : la couverture du bootstrap EM-BIC (66 % pour pi, 82 % pour mu) et la décision HP6-diff
  « VB < EM-BIC » (RH3) étaient sans doute gonflées ; à relire sur les résultats recalculés. La couverture du VB
  (22 % et 64 %) n'est pas touchée.
- **Unités recalculées** : `couverture/*` (300) et `alerte` (1) ; les ajustements mémorisés (`_sous/`) sont relus,
  seuls les bootstraps sont refaits. 23 unités faites en local le 2026-11-08, les 278 autres sur une instance spot
  c8g.8xlarge (32 cœurs, `--travailleurs 31`) le 2026-11-09 (la c8g.16xlarge choisie dépassait le quota spot du
  compte, 96 vCPU, dont 64 pris par MKAN). Anciennes unités et anciens tableaux gardés pour comparaison.
- **Non refait, déclaré** : le pilote de `n_bootstrap_modele` (`calibrage.py`, l. 821) utilise encore l'ancien
  alignement ; la valeur calibrée, B = 10 000 (la plus grande de la grille ; 1 000 n'est que la valeur provisoire
  du registre), reste prudente, le calibrage n'est pas refait.
- **Données** : `.gitattributes` (`data/** -text`) garde le CSV des prix en octets exacts ; sans lui, Git sous Windows
  ajoute des CRLF et l'empreinte SHA-256 vérifiée par `donnees.py` échoue.
- **Résultats du recalcul (2026-11-09)** : 278 unités en 1 h 20 sur la c8g.8xlarge (code 0, aucune erreur), coût
  d'environ 0,30 $ ; instance et disque supprimés automatiquement après copie des sorties. Agrégation refaite en local
  (`run.py prix --tables`) avec les unités de chronométrage du magasin du 07/11, que l'instance n'avait pas (sans
  elles, les lignes HP4 disparaissaient). Tableaux non touchés par D-19 (`prix_descriptif`, `prix_diebold_mariano`,
  `prix_resume`) gardés dans leur version commitée : seuls des écarts d'arrondi (au plus 2e-15) les distinguaient.
  Couverture à 90 % du bootstrap EM-BIC : 44 % pour pi et 78 % pour mu (contre 66 % et 82 %) ; EM-K : 48 % et 82 %
  (contre 72 % et 86 %) ; VB inchangé (22 % et 64 %). HP6-diff : -0,215 pour pi (IC [-0,27 ; -0,157], contre -0,44)
  et -0,146 pour mu ; verdict « VB < EM-BIC » inchangé. Largeur moyenne de l'IC90 de P(tension) pour EM-BIC : 0,087
  (apprentissage) et 0,124 (test), contre 0,946 et 0,921. Aucun verdict ne change : bilan 31 conformes, 4 contraires,
  22 non tranchées, 6 sans sens prédit, comme avant. Texte mis à jour (synthèse du cas, épisodes, RH3, conclusion) et
  défaut déclaré comme écart au protocole (8) au chapitre 3. Commit du recalcul renseigné à la main dans
  l'historique d'environnement (`dd538fc`) : l'instance tournait sur une archive sans dossier `.git`.

## D-20 Outil opérationnel tiré du cas des prix (dossier `outil/`), 2026-11-09

- **Demande** : faire du cas pratique un outil utilisable par un ministère ou une ONG (bulletin mensuel, saisie de
  relevés), déployable plus tard (Railway par exemple). Le mémoire n'est pas modifié : « cas pratique » y garde son
  sens académique (méthodes appliquées à des données réelles).
- **Modèle** : le modèle du mémoire (EM-BIC et VB-emp ajustés sur 2021-04 à 2023-12, standardisation, tirages de
  l'unité « alerte ») est exporté tel quel et reste la référence, jamais modifié. Une réestimation, lancée à la main
  et versionnée (nouveau dossier de modèle, date, données, code), peut s'y ajouter ; l'outil affiche les deux et
  dit lequel produit chaque chiffre.
- **Emplacement** : dossier `outil/` de ce dépôt (choix de l'étudiant). Le code du mémoire n'est pas touché ; le
  dépôt sera étiqueté avant la soutenance (P-24) pour figer l'état du mémoire.
- **Saisie** : relevés saisis enregistrés dès la première version, dans une base (SQLite en local, Postgres en
  ligne), avec comptes et rôles (administrateur, analyste, agent de collecte).
- **Exécution sans PyTorch** : l'outil calcule les probabilités en NumPy à partir des paramètres exportés ;
  l'équivalence avec le calcul du mémoire est un test (`outil/tests`), pas une hypothèse.
- **Données** : l'outil lit tout extrait du PAM au format de `outils/telecharger_prix_wfp.py` ; l'empreinte figée
  (`donnees.SHA256_PRIX`) ne concerne que le mémoire, l'outil enregistre celle de chaque extrait qu'il charge.

## D-21 Rédaction seulement : registre des décisions, seuil d'alerte, guide de décision, 2026-11-12

- **Plus aucun calcul** (Miguel, 12/11) : ni sensibilité, ni ablation, ni réestimation ; la réestimation versionnée de
  l'outil (D-20) est abandonnée. Les améliorations restantes passent par la rédaction, à partir des résultats existants.
- **Seuil d'alerte** : 0,5 déclaré comme règle de Bayes à coûts égaux (chap. 3) ; le seuil général
  c_FA/(c_FA + c_AM) dépend de coûts qui relèvent des organismes de sécurité alimentaire ; aucun autre seuil étudié.
- **Choix posés** : panier, fenêtre de 12 mois, 3 relevés au minimum, facteur 3 du nettoyage et seuil d'alerte
  déclarés « posés sans alternative testée » (limite 4) ; registre des 17 décisions du cas pratique en annexe E
  (retenu, alternatives, raison, vérification), sur le modèle des registres de NERA et de MKAN.
- **Guide de décision** (chap. 4) corrigé pour suivre les verdicts ; en particulier, le bootstrap d'EM-BIC est
  recommandé plutôt que les intervalles du VB (HP6), aucun n'atteignant 90 %.
- Corps maintenu à 112 pages (bibliographie page 113). Détail : `CHANGEMENTS_MEMOIRE.md`.

## D-22 Version finale : étiquette v1.0, présentation complétée, 2026-11-13

- **Étiquette** `v1.0` posée sur le commit qui contient le mémoire relu (D-21 et relecture finale) et ce suivi ;
  poussée sur GitHub. Toute correction ultérieure se fera par une nouvelle étiquette (`v1.0.1`), jamais en déplaçant
  `v1.0`.
- **Zenodo (DOI)** : non fait. L'intégration GitHub-Zenodo doit être activée par le propriétaire du dépôt
  (compte Kanaicare8) ; l'annexe A ne cite pas de DOI, donc rien à modifier dans le mémoire. Si Icare l'active,
  une version publiée sur GitHub à partir de `v1.0` produira le DOI.
- **Archive locale** : code étiqueté (`git archive`), PDF du mémoire et présentation, dans
  `M:/Travail/Icare_archive_v1.0/`.
- **Présentation de pré-soutenance** (hors dépôt) : partie III ajoutée (bilan des 63 décisions, scénarios, prix,
  alerte, incertitude, régularisation et coût, conclusion), 26 diapositives, notes minutées pour 20 minutes ;
  chiffres repris des tableaux du mémoire.

## D-23 Rangement du dépôt, présentation dans le dépôt, métadonnées Zenodo, 2026-11-13

- **Présentation** : `presentation/Presoutenance_Icare_v1.pptx` (26 diapositives) et `presentation/NOTES.md` (notes
  de l'orateur, lisibles) rejoignent le dépôt. Le générateur reste hors dépôt (il dépend d'outils locaux).
- **Page d'accueil** : `README.md` (carte du dépôt, commandes de reproduction, données, citation). Le dépôt n'en avait pas.
- **Rangement limité** : les modules Python, les sources LaTeX, `SUIVI/`, `notes/` et `LANCEMENT.md` ne bougent pas.
  Les modules s'importent par leur nom, le mémoire renvoie à `algorithmes.py`, `risque.py`, `comparaison.py`,
  `scenarios.py` et `run.py` par QR code sur `main`, `LANCEMENT.md` est cité en annexe A, et les documents de
  `SUIVI/` se renvoient par chemin. Seul `A_REGENERER.md`, périmé (ancienne chaîne : `main.py`, cas climatique),
  passe dans `legacy/A_REGENERER_octobre-2026.md`.
- **Zenodo** : `.zenodo.json` et `CITATION.cff` ajoutés (auteur, directeurs, mots-clés, lien du dépôt), pour que le
  DOI porte le nom de l'auteur et non le compte GitHub. Aucune licence n'est choisie : c'est à l'auteur de la
  décider. Étiquette `v1.0.1` (ces fichiers ne sont pas dans `v1.0`).

## D-24 Réorganisation du dépôt en projet structuré, 2026-11-13

- **Demande** : un projet bien organisé, sans se limiter par les QR codes ni par `LANCEMENT.md`, qui peuvent être
  régénérés ou modifiés. D-23 s'était interdit de déplacer les modules ; cette limite est levée.
- **Structure** : le code devient le paquet Python `emvb/` ; les sources LaTeX, tableaux et figures vont dans
  `memoire/` ; `app/` devient `demo/`, `outil/` devient `bulletin/`, `outils/` devient `scripts/` ; `LANCEMENT.md` et
  `notes/` vont dans `docs/`. Tous les déplacements sont faits avec `git mv` : l'historique de chaque fichier est
  conservé. `run.py` reste à la racine comme point d'entrée (`python -m emvb` équivaut).
- **Code** : imports réécrits (`from emvb import ...`, 140 lignes), emplacements définis une seule fois dans
  `emvb/chemins.py`, `etapes.charger_module` résout les étapes par leur nom court, `pyproject.toml` ajouté
  (`pip install -e .`). Aucun calcul n'est modifié.
- **Mémoire** : chemins de fichiers cités mis à jour (scripts, `docs/LANCEMENT.md`, `python -m emvb.tex_tables`),
  QR codes régénérés vers `emvb/*.py`, une phrase ajoutée à l'annexe A.1. Texte, chiffres et pagination inchangés
  (bibliographie page 113).
- **Vérifications** : 102 tests du projet et 4 tests du bulletin passent ; le mémoire compile sans erreur ni
  référence indéfinie ; `run.py --statut` relit le magasin au même endroit ; le serveur du bulletin répond ; la
  démo charge ses 1 055 observations ; l'arbre de `v1.0.1` est comparé à l'arbre final (aucun fichier perdu).
- **Espace de travail nettoyé** : caches Python, fichiers de compilation LaTeX, base de test du bulletin supprimés ;
  sauvegarde de session et anciens journaux de calcul du cas climatique abandonné déplacés dans
  `M:/Travail/Icare_archive_v1.0/` (hors dépôt, non supprimés).
- **Historique** : les documents de `SUIVI/` datés d'avant ce jour gardent les anciens chemins (ils étaient vrais le
  jour de leur écriture) ; une table de correspondance est dans `SUIVI/LISEZMOI.md`. Seul
  `COMPRENDRE_LE_PROJET.md`, qui décrit le code, est mis à jour.
- **Guide Zenodo** : `docs/GUIDE_ZENODO.md`, pour qu'Icare publie lui-même (étiquette `v1.1`).

## D-25 Présentation refaite : thème du mémoire, peu de texte, autre mise en page, 2026-11-13

- **Retour de Miguel** : la présentation doit porter sur le thème du mémoire (EM classique contre EM variationnel),
  avoir peu de texte, des illustrations, des schémas et de gros titres, et ne pas reprendre la mise en page de la sienne.
- **Refonte** : 20 diapositives (au lieu de 26), 34 mots affichés par diapositive en moyenne ; un gros titre et un seul
  visuel chacune. Plus de bandeau, de cartes arrondies ni de pied de page à nom : étiquette de partie, titre de 40 pt,
  visuel pleine page, grand chiffre. Le thème passe devant l'application : une seule diapositive sur les prix du
  Cameroun (diapositive 18), contre cinq auparavant.
- **Visuels** : figures réelles du mémoire re-tracées depuis les résultats déjà calculés (groupes, ellipses EM contre
  VB, poids, sensibilité aux priors, carte d'alerte), en palette verte et grosses polices ; graphiques natifs
  (bilan des 63 décisions, gains d'ARI) ; deux schémas conceptuels marqués « illustration » (un point contre une loi,
  les deux effets de la KL inverse) ; aucun résultat nouveau, aucun calcul de modèle.
- **Fichiers** : `presentation/Presoutenance_Icare.pptx` et `.pdf`, `presentation/NOTES.md` (notes minutées, 18 à 19
  minutes). Les anciennes diapositives de contexte, de revue de la littérature et de limites disparaissent de l'écran
  mais leur contenu reste dans les notes et dans le mémoire.
- **Mémoire** : même remarque (« pareil pour le mémoire ») : l'introduction s'ouvre sur les prix alimentaires ; une
  réécriture du paragraphe « Contexte » est proposée à Miguel, en attente de sa validation.
