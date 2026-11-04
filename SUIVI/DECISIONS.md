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
