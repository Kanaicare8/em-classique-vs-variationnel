# Journal des actions

Une ligne par action : date ; ce qui a été fait ; pourquoi (P-xx, D-xx ou phase) ; fichiers touchés ; vérification ; résultat.

| Date | Action | Pourquoi | Fichiers touchés | Vérification | Résultat |
|---|---|---|---|---|---|
| 2026-11-04 | Inventaire en lecture seule : arborescence, état Git, empreintes SHA-256 des données, plan de `body.tex`, état du magasin de résultats, notes existantes | Phase 0 | aucun (lecture) | empreinte de `data/prix/wfp_cmr_panier.csv` identique à celle de `data/prix/PROVENANCE.txt` (6b865e40...) ; idem pour le fichier brut (98fcdc74...) | inventaire consigné ci-dessous |
| 2026-11-04 | Création de `SUIVI/LISEZMOI.md` et `SUIVI/JOURNAL.md` | Phase 0, § 2 du prompt de reprise | `SUIVI/LISEZMOI.md`, `SUIVI/JOURNAL.md` | relecture | créés |
| 2026-11-04 | Réponses de l'étudiant consignées (échéance 22 novembre, 112 pages hors annexes, calcul sur instance cloud c8g.8xlarge) | D-01 | `SUIVI/DECISIONS.md` | page des annexes lue dans `main.toc` (103) | corps actuel : 102 pages |
| 2026-11-04 | Comparaison du tableau de suivi cloud avec le code : l'instance exécute le commit `97dcb95` (climat et S&P 500 encore présents, cas des prix absent) | N-01, D-02 | `SUIVI/NOTES_TECHNIQUES.md`, `SUIVI/DECISIONS.md` | `git show HEAD:run.py`, `HEAD:calibrage.py`, `HEAD:parametres.py` contre fichiers locaux | constat Bloquant, décision D-02 demandée |
| 2026-11-04 | Choix de l'étudiant pour D-02 : option A (arrêt du calibrage cloud, push du code local, relance par l'étudiant) | D-02 | `SUIVI/DECISIONS.md` | | décision consignée |
| 2026-11-04 | Constat : le magasin identifie une unité par son seul nom, sans version du code ; l'ancien magasin de l'instance doit être mis de côté avant relance | D-02, E-01 | `SUIVI/EXPERIENCES/E-01.md` | lecture de `persistance.py` (`Magasin.chemin`, `Magasin.complete`) et `parametres.py` l. 237 | consigne ajoutée à E-01 |
| 2026-11-04 | Commit `e5eeaf8` de tout l'état local (92 fichiers), sauf `SUIVI/` et `resultats/calibrage/` (calibrage local partiel, à ne pas réutiliser) ; push vers `origin/main` lancé | D-02 | dépôt Git | `py_compile` de tous les `.py` actuels : OK ; recherche de secrets : aucun | push en attente de l'identification GitHub (gestionnaire d'identifiants ouvert) |
| 2026-11-04 | Push bloqué sur la fenêtre d'identification : processus arrêtés, push relancé avec connexion GitHub par le navigateur (`credential.gitHubAuthModes=browser`), à la demande de l'étudiant ; GitHub Desktop non utilisé | D-02 | dépôt Git | `git ls-remote origin main` à la fin | échec (« Logon failed ») ; nouvel essai sans fenêtre : aucun identifiant enregistré ; relance par code d'appareil (`credential.gitHubAuthModes=device`) : échec identique ; quatrième essai à la demande de l'étudiant : échec identique (aucune fenêtre possible depuis la session de Claude) ; push à faire par l'étudiant dans son propre terminal |
| 2026-11-04 | Push fait par l'étudiant depuis son terminal | D-02 | dépôt Git | `git ls-remote origin main` = `e5eeaf8b7ed3...`, identique à HEAD local | GitHub à jour ; relance E-01 possible |
| 2026-11-04 | Phase 1 et 2 : lecture complète du mémoire et du code du protocole ; matrice d'avancement et audit | Phases 1-2 | `SUIVI/ETAT_DU_PROJET.md`, `SUIVI/COMPRENDRE_LE_PROJET.md` | constats avec fichier:ligne ; parties non lues listées comme « non vérifié » | 14 lignes de matrice, 13 constats code, 12 constats document |
| 2026-11-04 | Phase 3 : plan de travail en 24 points, 5 questions, 6 lots, calendrier | Phase 3 | `SUIVI/PLAN_DE_TRAVAIL.md` | | en attente de validation |
| 2026-11-04 | Fiche E-01 (calibrage complet sur l'instance) : commandes de récupération, mise de côté de l'ancien magasin, vérifications, lancement | D-02 | `SUIVI/EXPERIENCES/E-01.md` | | à lancer par l'étudiant |
| 2026-11-04 | Sauvegarde horodatée du dossier `SUIVI/` avant modification | règle 10 | `SUIVI_sauvegarde_20261104-122015/` (racine du projet) | `ls` | faite |
| 2026-11-04 | Récupération du dépôt distant à la demande de l'étudiant : nouveau commit `315a21c` (auteur Git « Georges Moukoko »), `git pull --ff-only` | demande de l'étudiant | `calibrage.py`, `etapes.py`, `run.py`, `outils/verifier_parallele.py` | HEAD = `315a21c` ; `py_compile` OK ; état antérieur récupérable par `e5eeaf8` | à jour |
| 2026-11-04 | Analyse du commit `315a21c` : calcul parallèle des sous-tâches du calibrage, neutre d'après la lecture ; risque de surcharge en vague 5 | refaire l'analyse, A-01 | `NOTES_TECHNIQUES.md` (N-02), `DECISIONS.md` (D-09), `EXPERIENCES/E-01.md` | lecture du diff, des clés de `Memo` et des écritures atomiques | vérification bit à bit à lancer par l'étudiant |
| 2026-11-04 | Numéros de ligne de `calibrage.py` mis à jour dans `SUIVI/` (+58 lignes après la l. 360) | cohérence des preuves | `ETAT_DU_PROJET.md`, `PLAN_DE_TRAVAIL.md` et autres | `grep` des renvois | fait |
| 2026-11-04 | Validation du plan par l'étudiant : P-01 à P-23 acceptés (P-19 sous condition du canevas), P-24 reporté ; Q-1 B, Q-2 B+C, Q-3 B, Q-4 B, Q-5 recommandation sous réserve du canevas | phase 3 → 4 | `DECISIONS.md` (D-03 à D-08), `PLAN_DE_TRAVAIL.md` (colonne Décision) | | phase 4 ouverte |
| 2026-11-04 | Réponses de l'étudiant : Georges Moukoko est un tiers collaborateur ; canevas de l'école fourni ; délégation (« gère comme ça et pousse le code ») | D-08, D-09 | `DECISIONS.md`, `CANEVAS_ECOLE.md` | | consigné |
| 2026-11-04 | Recherche de sources pour les marges : Lakens, Scheel et Isager 2018 confirmé (référence) ; échelle ARI 0,65 / 0,80 / 0,90 trouvée seulement dans une source secondaire (documentation CrossClustering) | D-04 | `parametres.py` | recherche web | Steinley 2004 « à vérifier » |
| 2026-11-04 | Code de D-04, D-05, D-06 et P-17 ; commit `9ece8ce` poussé | D-04 à D-06, P-17 | 9 fichiers (voir N-03) | `py_compile` ; import du registre ; `git ls-remote` = `9ece8ce` ; pytest non lancé (règle 4) | à récupérer sur l'instance avant la vague 6 (E-01) |
| 2026-11-04 | Commit `2f782aa` du dossier `SUIVI/` (9 fichiers), poussé à la demande de l'étudiant ; les 7 mentions de l'assistant dans `DECISIONS.md` et `JOURNAL.md` sont gardées telles quelles (choix de l'étudiant) | demande de l'étudiant | dépôt Git | `git ls-remote` = `2f782aa` | sur GitHub ; sauvegarde locale `SUIVI_sauvegarde_*` et `resultats/calibrage/` non poussés |
| 2026-11-04 | Lot 2 : bootstrap EM-BIC pour HP6 (D-07) et estimateur de Hodges-Lehmann (P-10) ; commit `f73142e` poussé | D-07, P-10 | `etape_prix.py`, `hypotheses.py`, `statistique.py`, `tex_tables.py`, `tests/test_statistique.py` | `py_compile` ; rattachement des identifiants HP6 vérifié ; test HL calculé à la main (non lancé) | à récupérer sur l'instance avant l'étape prix |
| 2026-11-04 | Lot 5 (première partie) : corrections du mémoire P-05, P-09, P-12, P-13, P-14, P-16, déclaration des écarts au protocole, trois références ajoutées | lot 5 | `body.tex`, `main.tex`, `hypotheses.py`, `comparaison.py` ; sauvegarde `sauvegardes/body_20261104-125431.tex` | `pdflatex` deux passes sans erreur, 124 pages ; références non définies : tableaux à générer seulement | détail dans `CHANGEMENTS_MEMOIRE.md` |

## Inventaire du 2026-11-04 (phase 0)

**Document.** `main.tex` (préambule, page de titre, `\input{body.tex}`), `body.tex` (1 860 lignes environ, 35 224 mots),
`introduction.tex` (910 mots, inclus par `body.tex`), `main.pdf` (125 pages, compilé le 2026-10-27 18:14).
Compilation déclarée : `pdflatex main.tex` trois fois (`LANCEMENT.md`). Le journal `main.log` contient 41 occurrences
de « undefined » (non analysées). Versions antérieures : `legacy/body_v0.tex` à `legacy/body_v9_avant_restructuration.tex`.
Tableaux inclus depuis `tables/` (produits par `tex_tables.py`) ; schémas TikZ dans `figures_tikz/` ; figures PNG dans `figures/`.

**Protocole et notes.** Protocole décrit dans `body.tex` (chap. 2, sections `sec:hypotheses` à `sec:validite`) et dans
`hypotheses.py`, `parametres.py`, `tables/plan_tests.tex`, `tables/hypotheses_recherche.tex`. Notes d'analyse :
`notes/CHECKUP_CODE.md`, `notes/ANALYSE_COHERENCE.md`, `notes/ANALYSE_SOURCES.md`, `notes/ANALYSE_2.md` (22 octobre),
`notes/ANALYSE_3_CAS_PRATIQUE_RIGUEUR_OPTIMISATION.md` (27 octobre, contient la décision de retenir le seul cas des prix).
Mode d'emploi : `LANCEMENT.md` (nouvelle chaîne), `A_REGENERER.md` (ancienne chaîne, périmé).

**Code.** Branche `main`, suit `origin` = github.com/Kanaicare8/em-classique-vs-variationnel ; 3 commits ; 82 entrées
modifiées ou non suivies. Noyau : `algorithmes.py`, `statistique.py`, `risque.py`, `comparaison.py`. Chaîne :
`run.py`, `superviseur.py`, `etapes.py`, `persistance.py`, `progression.py`, `calibrage.py`, `parametres.py`,
`hypotheses.py`, `scenarios.py`, `etape_validation.py`, `etape_illustrations.py`, `etape_chronometrage.py`,
`etape_prix.py`, `etape_texte.py`, `donnees.py`, `figures.py`, `tex_tables.py`. Tests : `tests/` (7 fichiers ; 74 tests
annoncés par `LANCEMENT.md`, non relancés). Outil livré : application Dash `app/` (4 pages). Ancien code : `legacy/`.

**Données (empreintes SHA-256).**

| Fichier | Taille | Date | SHA-256 | Statut |
|---|---|---|---|---|
| `data/iris.csv` | 4 758 o | 2026-10-06 | 0281504e...8853b13 | versionné |
| `data/prix/wfp_cmr_panier.csv` | 635 669 o | 2026-10-27 | 6b865e40...6b976f | non suivi ; conforme à `PROVENANCE.txt` |
| `data/prix/brut/wfp_food_prices_cmr.csv` | 9 656 600 o | 2026-10-27 | 98fcdc74...0127544 | ignoré ; conforme à `PROVENANCE.txt` |
| `data/texte/20news-bydate.tar.gz` | 14 464 277 o | 2026-10-27 20:57 | 8f1b2514...d95610 | ignoré |
| `data/sp500_fred.csv` | 48 903 o | 2026-10-06 | 551b282c...c90dc | ancien cas, retiré |
| `data/climat/zae/zae_irad.geojson` | 425 556 o | 2026-10-27 | 3db98559...87f01c | ancien cas, retiré |

**Sorties de calcul.** `resultats/` (115 entrées à la racine, plus de 33 000 fichiers au total, en grande partie de
l'ancienne chaîne). Magasin confirmatoire `resultats/magasin/` : seul le dossier `calibrage/` existe (kmeans,
tolerance, regularisation, corpus, fin, n_init). Battement : étape calibrage, 101 unités faites sur 554, unité en cours
`n_init/texte`, dernier battement 2026-11-01 17:22. `superviseur.log` : trois lancements (27 octobre), dernier arrêt
« non voulu (code 1073807364) » le 2026-11-01 17:22, pas de relance visible ; aucun `python.exe` actif le 2026-11-04.
Dernière unité terminée dans les journaux : `n_init/prix/N=562` le 2026-10-28 15:33 (l'unité `n_init/texte` a donc
tourné ou attendu près de quatre jours sans se terminer : à examiner). `erreurs.log` : échec du 27 octobre sur
l'absence de l'archive 20 Newsgroups, archive présente depuis 20:57 le même jour. `resultats/calibrage/` : trois JSON
(kmeans, tolerance, regularisation) sur sept vagues. Magasin d'essai `resultats/magasin_rapide/` (prix, validation).

**Bibliographie.** Intégrée à `body.tex` (`\chapter*{Bibliographie}`, entrées `[n]` saisies à la main, annoncées IEEE) ;
copies locales dans `references/` (Bishop 2006, Dempster et al. 1977, source scikit-learn) et liste `references/SOURCES.md`.

**Machine (annexe D du mémoire).** Windows 10, Intel Core i7-1165G7 (4 cœurs, 8 fils), 7,9 Go de mémoire (d'après
`notes/ANALYSE_3_...md`).

**Introuvable dans le projet.** Échéance de dépôt ; volume attendu (pages ou mots).
