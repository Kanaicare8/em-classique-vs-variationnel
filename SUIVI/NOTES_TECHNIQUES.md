# Notes techniques

Explications données à l'étudiant, avec leur source.

## N-01 L'instance cloud calcule avec l'ancienne version du code (2026-11-04, gravité : Bloquant)

**Ce qui a été vu.** Le tableau de suivi de l'instance (collé par l'étudiant le 2026-11-04 à 08:21) affiche les
étapes `climat` (827 unités) et `sp500` (21 unités), un calibrage de 628 unités, des unités en cours nommées
`n_init/climat/D=20/N=500` et `n_init/sp500`, et des paramètres `hmm_etats` et `n_simulation_var`.

**Preuve dans les fichiers.**
- Le commit `97dcb95` (22 octobre, identique à `origin/main`) contient ces étapes : `git show HEAD:run.py`, ligne 37
  (`ORDRE = [..., "climat", "sp500", "texte"]`) ; `git show HEAD:calibrage.py`, lignes 84 à 87 (unités sp500 et climat) ;
  `git show HEAD:parametres.py`, ligne 161 (`n_simulation_var`).
- Le code local actuel ne les contient plus : aucune occurrence de « climat » ou « sp500 » dans `run.py`,
  `calibrage.py` et `parametres.py` (seul un commentaire de `etapes.py`, ligne 6, en parle) ; le cas des prix
  (`etape_prix.py`) n'est pas suivi par Git.
- `notes/ANALYSE_3_CAS_PRATIQUE_RIGUEUR_OPTIMISATION.md` comptait 628 unités de calibrage et 827 unités climat avant la
  décision du 27 octobre ; le calibrage local du nouveau code compte 554 unités (`resultats/magasin/_battement.json`).

**Pourquoi c'est un problème.** Le calibrage fixe les paramètres (nombre de relances, priors, marges, tailles Monte
Carlo) qui servent ensuite à tous les calculs confirmatoires. Fait sur une autre version du code, il ne garantit pas
que les valeurs retenues sont celles que le code actuel aurait choisies ; il dépense aussi du budget sur deux cas
retirés du mémoire, et il ne calibre pas le cas des prix, qui est le cas pratique retenu.

**Ce que la commande affichée signifie.** `--rapide --autoriser-provisoire` est l'essai réduit de `LANCEMENT.md` § 2 :
il sert à vérifier que la chaîne tourne et écrit dans un magasin séparé ; ses chiffres n'entrent pas dans le mémoire.

**Non vérifié.** Le code effectivement déployé sur l'instance (seul le tableau de suivi a été vu) ; la façon dont
l'instance récupère le code (clonage de GitHub supposé, puisque le dépôt distant est au commit `97dcb95`).

## N-02 Analyse du commit `315a21c` (calcul parallèle des sous-tâches du calibrage), 2026-11-04

Lecture du diff `e5eeaf8..315a21c` (`calibrage.py`, `etapes.py`, `run.py`, `outils/verifier_parallele.py`) ;
`py_compile` des quatre fichiers : OK. Aucun calcul lancé.

**Ce qui change.** Avant, l'unité `n_init/texte` enchaînait 4 cas × 200 relances dans un seul processus ; les unités
de la vague 5 (`priors/synthetique`, `priors/prix`, `fin/texte`, `fin/variantes`) enchaînaient de même leurs
évaluations. Désormais, `etapes.sous_taches_paralleles` (`etapes.py` l. 98-120) confie chaque sous-calcul absent du
magasin à un processus (un fil chacun), qui l'écrit sous `<unité>/_sous/<clé>` ; la boucle d'origine relit ensuite ces
valeurs par `Memo` (`etapes.py` l. 64-65), sans changer son ordre ni ses agrégats.

**Pourquoi le résultat ne change pas (lecture).**
1. Mêmes clés : la clé écrite par le processus (`{prefixe}/_sous/{c}`) est celle que lit `Memo.__call__` ; pour les
   variantes, le préfixe `meth/` du précalcul correspond à l'enveloppe `sous` de `unite_variantes`.
2. Mêmes calculs : les corps des fonctions `evaluer` ont été déplacés tels quels dans des fonctions de module
   (`_relance_n_init_texte`, `_evaluer_priors`, `_evaluer_texte`, `_evaluer_variantes`), avec les mêmes graines
   (`_g(...)`), les mêmes données et le même `n_init`.
3. Même environnement numérique : un fil par processus (`torch.set_num_threads(1)`), comme dans `executer_unite`.
4. Écritures atomiques (fichier temporaire puis `os.replace`, `persistance.py` l. 57-64) : un processus arrêté en cours
   d'écriture ne laisse pas de fichier tronqué.
5. Compatibilité : les clés sont celles de `e5eeaf8`, donc les relances déjà faites séquentiellement sur l'instance
   sont relues, pas recalculées.

**Points de vigilance (sans effet sur les résultats).**
- *Surcharge de l'instance* : chaque unité qui appelle `sous_taches_paralleles` ouvre jusqu'à 31 processus
  (`ICARE_SOUS_TRAVAILLEURS`, défaut : cœurs − 1), en plus des 31 travailleurs de `run.py`. En vague 5, quatre unités
  peuvent tourner ensemble : jusqu'à environ 124 processus de calcul plus 31 travailleurs, chacun chargeant PyTorch,
  sur 32 cœurs et 61,6 Go. Risque : lenteur par surcharge et, au pire, manque de mémoire (arrêt, puis reprise par le
  superviseur). Parade : `export ICARE_SOUS_TRAVAILLEURS=8` avant de lancer le superviseur (4 × 8 = 32).
- *Verrou du magasin* : sans effet sous Windows (pas de `fcntl`) ; sur l'instance Linux, il évite deux commandes
  concurrentes sur le même magasin.
- *Vérification* : `outils/verifier_parallele.py` recalcule en séquentiel quelques relances de `n_init/texte` et
  quelques évaluations de `fin/texte`, et les compare bit à bit ; il ne couvre pas `priors/*` ni `fin/variantes`, qui
  passent par le même mécanisme.
- *Effet sur l'audit* : aucun constat A-02 à A-13 n'est modifié par ce commit ; A-01 est réglé sous réserve de la
  vérification.

## N-03 Code des décisions D-04, D-05, D-06 et du point P-17 (2026-11-04)

| Fichier | Changement | Effet sur les résultats |
|---|---|---|
| `parametres.py` | `marges_equivalence` = {ARI 0,05 ; LL 0,05}, statut « plan », sans calibrage ; nouveau `budget_replications` ; références `lakens2018`, `steinley2004` | change les tests d'équivalence et la puissance (voulu, D-04, D-05) |
| `calibrage.py` | `fin_marges` ne fixe plus les marges : il mesure le bruit d'optimisation et contrôle « marge > bruit » ; `_r_requis` exclut les hypothèses sans variance ; `fin_puissance` applique le plafond de budget et rapporte R requis, R retenu, puissance requise et obtenue | change R (voulu, D-05) ; graines de la puissance inchangées |
| `etapes.py` | `executer_unite` enregistre `duree_s` dans chaque unité | aucun (donnée de suivi) |
| `algorithmes.py` | `indicateurs_degenerescence(cov, Nk, D)` : petite composante, ou valeur propre minimale < 1e-6 × trace, pour tous les bras ; clé `plancher_regularisation` renommée `effondrement` | change `degenere` (voulu, D-06) ; HS6, HP3, HP7 |
| `scenarios.py`, `etape_prix.py`, `persistance.py` | renommage de la clé | aucun |
| `run.py` | `resultats/environnement.json` et `environnement_historique.jsonl` à chaque lancement | aucun |
| `tests/test_algorithmes.py` | test T14 mis à la nouvelle définition | |

Vérifications faites : `py_compile` des fichiers modifiés ; import du registre (les marges ne sont plus « non
calibrées »). Non fait : `pytest` (à lancer par l'étudiant, règle 4).

**Interaction avec la régularisation de l'EM.** La covariance plug-in de l'EM contient `reg · I`. Si la valeur
calibrée de `reg` dépasse 1e-6 fois la trace d'une composante, un effondrement de l'EM est masqué par la régularisation
(il reste visible par l'indicateur « petite composante »). Le VB a la même protection par son prior. Le critère compare
donc les estimations finales telles que chaque méthode les rend, ce qui est la question de RH4 ; à écrire au chapitre 2.

**Ordre d'arrivée sur l'instance.** Le code doit être sur l'instance avant les vagues 6 (`fin/marges`) et 7 (unités
pilotes `puissance/pilote/...` et `fin/puissance`). Les unités pilotes calculées avant ce code n'ont ni durée ni
nouvelle définition de la dégénérescence : il faudrait alors les déplacer pour qu'elles soient recalculées.

## N-04 Retours de la session qui pilote l'instance (2026-11-04)

1. **18 tests en échec sur l'instance, 76 passent sur une copie propre.** Cause : `tests/test_etapes.py` fixait
   `ICARE_RAPIDE=1` au chargement, sans le rétablir ; et, plus largement, les tests lisaient le calibrage présent dans
   `resultats/` (sur l'instance : essai rapide de l'ancien code, puis calibrage réel en cours). Correction `de26220` :
   `tests/conftest.py` redirige le calibrage vers un dossier vide pour toute la session de tests
   (`ICARE_DOSSIER_CALIBRAGE`, lu par `parametres.dossier_calibrage`) ; `ICARE_RAPIDE` n'est plus fixé que pour
   `test_etapes.py`.
2. **Régularisation 0,01 : 477 itérations contre 221.** Cause probable : les tests appelaient le noyau par lots sans
   `tol`, `n_iter` ni `reg`, qui lisait donc le registre calibré (`reg_covariance` = 0,01 sur l'instance), alors que la
   référence garde ses constantes (`REG_EM` = 1e-6). Les deux ne calculaient pas le même ajustement. Nouveau test
   `test_em_equivalent_reglages_explicites` (reg 1e-6 et 1e-2, mêmes réglages passés aux deux) : s'il passe sur
   l'instance, la vectorisation est hors de cause. Non lancé ici (règle 4).
3. **Essai rapide de l'ancien code** dans `resultats/magasin_rapide` et `resultats/calibrage_rapide` : sans effet sur
   les résultats du mémoire (magasin séparé) ni désormais sur les tests ; à mettre de côté sur l'instance (commande
   dans E-01).
4. **`fin/texte` sur 8 cœurs** : voir D-11.

## N-05 Relecture des commits `3e1d4b0` et `4269bda` (session de l'instance), 2026-11-05

**Problème réglé.** Avec 200 relances, une évaluation de la recherche LDA (`fin/texte`) enchaînait 200 ajustements sur
un cœur sans rien écrire (environ 12 h) ; le superviseur l'a tuée cinq fois le 4 novembre et le travail a été perdu. Le
même risque existait dans `etape_texte.unite_echantillon` (mémoire de la seule boucle complète).

**Ce qui change.** Recherche LDA : chaque relance est une sous-tâche qui mémorise sa borne finale ; l'évaluation
réajuste ensuite la meilleure relance avec sa graine et range son score sous la même clé qu'avant. Étape texte :
`_meilleur` mémorise le critère de chaque relance (`<nom>/relances/s=<s>`) ; sans interruption, rien n'est recalculé ;
après une reprise, la meilleure relance relue est réajustée avec sa graine. `etapes.sous_taches_paralleles` lance
aussi un processus pour une sous-tâche unique.

**Neutralité (lecture).** Même règle de choix (plus grand critère, la première à égalité : inégalité stricte dans les
deux versions) ; un ajustement à graine fixée, un fil, est déterministe, donc le réajustement redonne le même modèle ;
clés des scores inchangées. Vérifications de la session : 84 tests passent sur l'instance (dont
`tests/test_relances_memorisees.py` : pLSA réel, reprise partielle, égalité) ; `outils/verifier_parallele.py --texte 4` :
13 valeurs sur 13 identiques, dont une évaluation LDA en deux temps (−6,751938501440624 des deux côtés). Surcoût : un
ajustement par évaluation (environ 0,5 %).

**État au 2026-11-05 à 0 h 45 (Douala)** : calibrage, 1 unité faite sur 448 ; `fin/texte` sur 32 cœurs (environ
7 LDA par minute, environ 32 h au total pour environ 13 600 ajustements) ; coût 6,65 $ sur 40 $.
