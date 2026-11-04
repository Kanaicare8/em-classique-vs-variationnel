# Analyse 3 : cas pratique, rigueur scientifique, robustesse et optimisation (27 octobre 2026)

> **Décision du 27 octobre 2026 (après cette analyse).** Seul le volet B (régimes de tension des prix alimentaires,
> données du PAM) est retenu comme cas pratique. Le cas climatique (volet A) et le cas S&P 500 sont retirés du mémoire
> et de la chaîne de calcul ; leur code est conservé dans `legacy/`. Mise en œuvre : `etape_prix.py`, `donnees.charger_prix`,
> hypothèses HP1 à HP6 et HPP1 à HPP6 dans `hypotheses.py`, section 3.1 de `body.tex`. Les §2.2 et §2.3 ci-dessous
> décrivent le raisonnement qui a précédé ce choix.

Point de départ : le dossier local (aucun commit) a été **remplacé par `origin/main`** (commit `97dcb95 validation`).
Une copie intégrale de l'ancien dossier local est conservée dans `Desktop\Icare_sauvegarde_locale_20261027`.
Les données non versionnées (`data/sp500_fred.csv`, PDF de `references/`) ont été restaurées depuis cette copie.

---

## 1. État réel du projet

| Constat | Preuve | Conséquence |
|---|---|---|
| La nouvelle chaîne (PyTorch par lots, reprenable) **n'a jamais été exécutée** | `python run.py --statut` : 0 / 5 435 unités, 16 paramètres non calibrés | **Tous** les chiffres actuels du mémoire viennent de l'ancienne chaîne, celle qui contenait les défauts C1 à C3 (`notes/CHECKUP_CODE.md`). Le mémoire n'est pas soutenable en l'état. |
| C1 (fuite apprentissage / test du climat) corrigé dans le code | `etape_climat.unite_sous` : plis par blocs, `assert` d'absence de fuite | Corrigé, mais seulement après réexécution |
| C2 (Holm après décision, test choisi a posteriori) corrigé | `statistique.decider_famille` : un test déclaré par hypothèse, décision sur p ajustée | idem |
| C3 (bootstrap EM à 1 initialisation) corrigé | `unite_couverture` : démarrage chaud à partir de l'EM à `n_init` relances | idem |
| Tests | 65 réussis + 1 échec d'import au départ ; **71 réussis** après ce travail | — |
| Volume de calcul | 5 435 unités (scénarios 3 750, climat 827, calibrage 628) ; machine : 4 cœurs logiques, 7,9 Go | Plusieurs jours de calcul sur ce poste (voir §5) |

---

## 2. Cas pratique

### 2.1 Diagnostic du cas actuel

Le **cas principal est déjà camerounais** : il s'agit des régimes climatiques du Cameroun (WorldClim 2.1, D = 5 ou 20, K_réf = 5).
C'est un bon choix : données réelles, structure chevauchante et déséquilibrée, effectif modulable de 30 à N complet, et une
question naturelle sur le choix de K. Sa faiblesse était la **référence externe**. Le mémoire (§3.1, « Références ») affirmait
qu'aucun fichier numérique du zonage officiel n'existait, et Köppen–Geiger servait seul de vérité de comparaison. Or l'ARI
contre Köppen–Geiger est faible (0,1 à 0,17), ce qui fragilise la lecture.

Le cas secondaire (S&P 500) n'a **aucun lien avec le Cameroun ni la sous-région**. Un jury local le jugera hors sujet par
rapport à l'ancrage annoncé.

### 2.2 Ce qui a été trouvé (vérifié en ligne et téléchargé)

1. **Zonage agro-écologique officiel IRAD (2005), en vecteur.** Il est diffusé par la FAO (portail GAEZ, « Zones Agroecologiques de
   Cameroun ») sous forme de service ArcGIS public. Il compte cinq zones : soudano-sahélienne, hautes savanes, hauts plateaux,
   forêt mono-modale, forêt bi-modale. Contrôle sur 9 villes : Maroua, Garoua, Ngaoundéré, Bafoussam, Bamenda, Kribi, Yaoundé et
   Bertoua tombent dans la bonne zone. Douala tombe hors zonage au point exact (tracé grossier de l'estuaire) et en zone forêt
   mono-modale à 5 km, ce qui est correct. Licence non précisée par la FAO : le fichier n'est pas versionné.
2. **Prix alimentaires WFP du Cameroun (HDX).** 77 267 lignes, 83 marchés, 9 régions, de janvier 2005 à août 2026. Licence
   CC BY-IGO, mise à jour du 4 octobre 2026. Denrées les mieux couvertes : riz importé, bœuf, maïs blanc (gros et détail), sucre,
   huile de palme, oignon, arachide, niébé. Séries courtes par marché : environ 50 à 205 mois pour le maïs au détail.
3. **Prix mondial du cacao (FRED, PCOCOUSDM).** Mensuel, de 1992 à juillet 2026, soit environ 415 observations.

### 2.3 Proposition retenue : un cas en deux volets, tous deux camerounais

**Volet A (cas principal renforcé) : « Où le zonage agro-écologique officiel de 2005 est-il encore pertinent ? »**

- *Problème réel.* Le zonage IRAD oriente la recommandation variétale, le calendrier cultural et la vulgarisation agricole.
  Il date de 2005, alors que le climat a évolué. Le ministère de l'Agriculture (MINADER) et l'IRAD ont besoin de savoir **où les
  frontières de zones sont incertaines** : c'est là qu'une recommandation uniforme par zone est la plus risquée.
- *Lien direct avec la thèse.* L'EM-BIC donne une partition. Le VB donne une partition **et** une incertitude : l'entropie des
  responsabilités et la carte de la probabilité d'appartenance maximale. La comparaison porte ainsi exactement sur l'axe
  « incertitude » du mémoire, sur un enjeu concret.
- *Déjà implémenté.* La métrique `ARI_zae` (ARI contre le zonage IRAD) est calculée dans toutes les unités `sous`, `complet` et
  `d20` ; les cartes reçoivent la zone IRAD de chaque cellule. Ce volet est **exploratoire** : il a été trouvé après le gel des
  hypothèses et n'entre dans aucune décision, ce qui est écrit dans le code et dans le mémoire.
- *Livrables, faciles à présenter en soutenance :*
  1. trois cartes côte à côte (zonage IRAD, classes EM-BIC, classes VB) ;
  2. la carte d'entropie du VB, avec le contour des zones IRAD en surimpression ;
  3. le tableau croisé zones IRAD × classes ;
  4. la liste des départements en zone de transition (entropie élevée).
- *Extension facultative.* Refaire l'ajustement sur une climatologie plus récente (WorldClim 2.1 mensuel historique 2000–2021, ou
  CHELSA 1981–2010) et cartographier les cellules qui changent de classe. Cela donne une mesure du « glissement » des zones.
  Ce n'est à faire que si le temps le permet.

**Volet B (remplace ou complète le S&P 500) : « Régimes de tension des prix alimentaires sur les marchés camerounais »**

- *Problème réel.* L'insécurité alimentaire touche plus de 2,8 millions de personnes (Cadre Harmonisé, octobre 2025),
  surtout dans l'Extrême-Nord, le Nord-Ouest et le Sud-Ouest. Les prix y passent par des chocs brusques : le maïs a pris 24 % en
  un mois dans l'Extrême-Nord en août 2023 (WFP), puis les céréales ont baissé de 40 à 50 % en 2026 à Kousseri, Mokolo et Mora
  (FEWS NET). Le WFP et FEWS NET ont besoin d'un indicateur d'alerte **probabiliste** par marché.
- *Modèle.* Une observation correspond à un couple (marché, mois). Les variables sont les variations logarithmiques mensuelles
  d'un panier de 4 à 5 denrées : maïs, riz importé, huile de palme, niébé, sorgho dans le Nord. Un mélange gaussien en tire des
  régimes (par exemple stable, tension, choc), et la probabilité a posteriori du régime « choc » sert d'indicateur.
- *Lien direct avec la thèse.*
  1. C'est le domaine du **petit N** : environ 50 mois par marché, et quelques milliers d'observations au total.
  2. K est inconnu : comparer K̂ de l'EM-BIC et du VB.
  3. Les queues sont épaisses, comme dans le scénario S4.
  4. La structure temporelle peut être prise en compte par le HMM, déjà codé pour le S&P 500 (`etape_sp500`).
  5. La sensibilité aux priors pèse sur le nombre de régimes.
- *Validation honnête.*
  1. Découpage temporel : apprentissage jusqu'à 2022, test de 2023 à 2026, avec la log-vraisemblance hors échantillon.
  2. Concordance des alertes avec les épisodes datés des bulletins WFP et FEWS NET. Cette concordance est qualitative et doit
     être présentée comme telle.
- *Effort.* Un nouveau module `etape_prix.py` (environ 200 lignes), sur le modèle de `etape_sp500.py`, plus une hypothèse
  déclarée **avant** tout calcul.

**Variante légère du volet B, si le temps manque : le cacao.** Le Cameroun est un grand producteur. Les régimes des rendements
mensuels du prix mondial (FRED PCOCOUSDM) et la VaR pour une coopérative se traitent comme le cas S&P 500 actuel, avec ses
fonctions réutilisées telles quelles. C'est moins original, sans dimension spatiale, mais faisable en une journée.

| Critère | A. Zonage IRAD | B. Prix WFP | B'. Cacao |
|---|---|---|---|
| Ancrage Cameroun / CEMAC | très fort | très fort | fort (filière exportatrice) |
| Données publiques vérifiées | oui (FAO GAEZ) | oui (HDX, CC BY-IGO) | oui (FRED) |
| Code déjà prêt | **oui (fait)** | non (environ 200 lignes) | presque (réutilise le S&P 500) |
| Teste l'axe « incertitude » du VB | oui (cartes d'entropie) | oui (probabilité d'alerte) | partiellement |
| Teste le « petit N » | via les sous-échantillons | **naturellement** | oui (environ 415 mois) |
| Présentation orale | cartes | carte des marchés et courbes | courbes |

**Recommandation :** garder le volet A comme cas principal (il est prêt). Remplacer le S&P 500 par le volet B si vous disposez
d'une à deux semaines ; sinon par la variante cacao.

---

## 3. Rigueur scientifique : audit du mémoire et du code

Gravité : **critique** = invalide un résultat ; **majeur** = contredit le protocole annoncé ; **mineur** = inexactitude.

| # | Gravité | Constat | Où | Action |
|---|---|---|---|---|
| R1 | critique | Tous les tableaux, figures et lectures des chapitres 2 et 3 proviennent de l'ancienne chaîne, avant les corrections C1 à C3 | commit `2d22c16` (« état des résultats de l'ancienne chaîne avant réexécution ») ; `--statut` à 0 | Calibrer, réexécuter, régénérer `tables/`, puis **réécrire les « Lecture »** |
| R2 | majeur | « Hypothèses fixées avant l'analyse » alors que `hypotheses.py` déclare qu'elles ont été formalisées **après** une première exécution | introduction.tex l. 18 ; body.tex l. 1107, 1134, 1187, 1210 | Écrire « figées le JJ/MM/2026, avant la réexécution, après une première exécution exploratoire » et ajouter une section « Écarts au protocole » |
| R3 | majeur | Le texte dit « Holm sur l'ensemble des tests » ; le code applique Holm **par famille** (scénarios, climat, texte), et HC4, HC5, HC6 sont décidées par intervalle, hors Holm | introduction l. 18, body l. 1107 / `statistique.decider_famille` | Aligner le texte sur le code (une famille par cas) |
| R4 | majeur | Collision de noms : H1 à H8 dans le texte, HC1 à HC8 dans le code, et « H4 » désigne à la fois le coût (climat) et la finance (body l. 1210) | body.tex | Préfixes du code partout : HS, HC, HF, HT |
| R5 | majeur | Valeurs écrites en dur dans le texte (tolérance 1e-6, 500 itérations, 10 initialisations, 100 sous-échantillons, 200 jeux semi-synthétiques) alors qu'elles sont **à calibrer** dans le registre ; le plan réel en prévoit 40 et 60 | introduction l. 21, body l. 845–847, 1101, 1103 | Citer `tables/registre_parametres.tex` après calibrage |
| R6 | majeur, **corrigé** | Couverture HC6 de μ : fraction de coordonnées couvertes, arrondie puis passée à Wilson, qui suppose des épreuves indépendantes, alors que les composantes d'une même réplication sont dépendantes | `etape_climat.py` | Une indicatrice 0/1 par coordonnée et un IC bootstrap **par grappes** (réplications) ; test ajouté |
| R7 | majeur | `hypotheses.diffs` écarte en silence les réplications où un bras est en échec. Si l'échec dépend du bras (le VB dégénère moins par construction), la comparaison est biaisée | `hypotheses.py` | Rapporter le nombre d'exclusions par hypothèse, avec une analyse de sensibilité « échec = pire valeur » |
| R8 | mineur | Pour un TOST à α = 5 %, l'intervalle cohérent est à **90 %** (Schuirmann 1987 ; Lakens 2017), alors que l'IC rapporté est à 95 % | `decider_famille` | IC à 90 % pour les hypothèses d'équivalence |
| R9 | mineur | Le sens « A > B » est lu sur la moyenne, alors que le test de Wilcoxon porte sur la pseudo-médiane | `decider_famille` | Utiliser l'estimateur de Hodges–Lehmann pour le sens et l'estimation |
| R10 | mineur | HC5 compare deux sources de variabilité différentes (configurations de priors contre graines) | `etape_climat.agreger` | Garder l'étiquette « descriptif », sans conclusion inférentielle |
| R11 | mineur | La sous-couverture attendue du VB en champ moyen (variance a posteriori sous-estimée) n'est pas annoncée comme prédiction théorique | §3.1 | Citer Blei, Kucukelbir et McAuliffe (2017, §5) et Wang et Titterington (2005) : la couverture devient une **prédiction testée** |
| R12 | mineur | Ton promotionnel signalé par l'analyse 2 et toujours présent : « se distingue par son ampleur », « douze expériences complémentaires » | body l. 642 | Retirer |

Ce qui est solide :
- l'implémentation des statistiques (Wilcoxon exact par programmation dynamique, TOST de Student, Holm) ;
- la validation croisée spatiale par blocs avec l'assertion anti-fuite ;
- les graines dérivées par rôle ;
- le critère d'arrêt commun ;
- le chronométrage sur un seul processus ;
- la reprise exacte d'un ajustement interrompu, testée par un vrai `os._exit`.

---

## 4. Protection contre les bogues et les arrêts non voulus

Existant, déjà bon : magasin à écriture atomique (fichier temporaire, fsync, `os.replace`), une unité par fichier, instantanés
tous les 20 passages dans les boucles EM et VB, reprise exacte, arrêt propre au premier Ctrl+C.

Ajouté et testé :

| Risque | Avant | Après |
|---|---|---|
| Ctrl+C sous Windows | atteint aussi les processus de travail : `KeyboardInterrupt` et arrêt brutal | les processus de travail ignorent Ctrl+C ; seul l'orchestrateur décide (`PE.ignorer_interruption`) |
| Processus de travail tué (mémoire, plantage natif de torch) | `BrokenProcessPool` : toute l'étape échoue | pool recréé, unités en cours relancées, jusqu'à `--tentatives` lancements (test : `test_pool_recree_apres_processus_tue`) |
| Erreur système passagère (MemoryError, OSError, « not enough memory ») | erreur définitive | relancée ; les erreurs de calcul (déterministes) ne le sont pas |
| Fichier d'unité tronqué (copie, disque plein) | compté comme fait, puis ignoré **en silence** à l'agrégation | contrôle de la fin d'archive zip, mise en quarantaine dans `_quarantaine/`, recalcul (test) |
| Fichiers `.tmp<pid>` orphelins | s'accumulent | supprimés au démarrage de l'étape |
| Mise en veille de Windows pendant la nuit | calcul suspendu | bloquée pendant `run.py` (`SetThreadExecutionState`) |
| Plantage complet ou blocage | relance manuelle | `superviseur.py` : relance automatique avec pause croissante, détection de blocage (battement toutes les 30 s, option `--inactivite-max`) |
| Coupure de courant ou redémarrage | relance manuelle | tâche planifiée à l'ouverture de session (`LANCEMENT.md` §4 bis) |
| Diagnostic | message d'une ligne | trace complète, y compris celle du processus de travail, dans `_journal/erreurs.log` |
| Codes de sortie | toujours 1 | 0 terminé, 1 erreurs, 2 configuration refusée, 3 arrêt demandé |

---

## 5. Pistes d'optimisation, par niveau

**Exécution et matériel (gain le plus important).**
- Mesure sur ce poste (N = 2 000, D = 5, K = 10, 10 relances) : EM 3,8 s, VB 3,8 s. **Passer de 1 à 4 threads n'apporte rien**
  (3,7 s et 4,1 s). Le parallélisme par processus, déjà en place, est donc le bon, et le temps total est à peu près
  proportionnel au nombre de cœurs.
- Avec 4 cœurs, `--travailleurs 3`, et 5 435 unités, il faut compter **plusieurs jours**. Chronométrer d'abord
  `python run.py --rapide --autoriser-provisoire` pour extrapoler. Une machine de laboratoire à 16 ou 32 cœurs, ou une VM de
  calcul louée quelques heures, divise ce temps d'autant.
- La variable `ICARE_MAGASIN` (ajoutée) permet de placer le magasin sur un autre disque, par exemple un SSD.
- 7,9 Go de RAM : ne pas dépasser 3 processus pour les unités climat à N complet en D = 20.

**Plan d'expérience.**
- Le nombre de réplications est déjà fixé par un calcul de puissance (vague « puissance »). C'est le bon levier : ne pas augmenter
  R au-delà de la puissance visée.
- La couverture (B = 1 000 bootstraps × 3 effectifs × 60 réplications) est l'unité la plus chère du climat. Rapporter l'erreur
  Monte Carlo de la couverture (√(p(1−p)/B)) et retenir le B le plus petit qui la rend négligeable devant la largeur de l'IC.

**Algorithmique, sans biaiser la comparaison.**
- *Short-EM* (Biernacki, Celeux et Govaert 2003) : lancer les `n_init` relances quelques itérations seulement, puis ne
  poursuivre que les meilleures. C'est un gain important sur EM-BIC (balayage de K = 1 à 10 avec 10 relances), mais il faut
  l'appliquer **à l'identique** à l'EM et au VB et le déclarer dans le protocole.
- *SQUAREM* et autres accélérations : **à ne pas utiliser** dans les comparaisons. Ils changent la trajectoire et le nombre
  d'itérations, donc l'axe « coût ». Ils restent utilisables pour les seules cartes du volet A.
- Garder float64 : la tolérance relative de 1e-6 n'est qu'à environ 10 fois l'epsilon de float32 (1,2e-7). En float32, le
  critère d'arrêt deviendrait du bruit numérique.

**Rédaction et chaîne de production.**
- Aucune valeur en dur dans `body.tex` : tout passe par `tables/*.tex` (déjà le cas pour les tableaux) et, à étendre, par des
  macros `\newcommand` générées par `tex_tables.py` pour les nombres cités dans le texte.
- Lancer `outils/lint_tex.py` avant chaque compilation.

---

## 6. Ordre de travail

1. `python -m pytest -q tests` (71 réussis attendus).
2. `python outils/extraire_zae_irad.py` (déjà fait sur ce poste).
3. `python superviseur.py --rapide --autoriser-provisoire` : essai complet chronométré.
4. `python superviseur.py calibrage`, puis `python superviseur.py --inactivite-max 120`.
5. Corriger le texte (R2 à R5, R11, R12), puis R7 à R9 dans le code **avant** la réexécution confirmatoire.
6. Volet B (prix WFP) ou variante cacao : déclarer l'hypothèse dans `hypotheses.py` **avant** le premier calcul.

## Sources
- FAO GAEZ, « Zones Agroecologiques de Cameroun » (IRAD 2005) : https://gaez.fao.org/datasets/zones-agroecologiques-de-cameroun
- HDX, Cameroon – Food Prices (WFP) : https://data.humdata.org/dataset/wfp-food-prices-for-cameroon
- Banque mondiale, Cameroon monthly food price estimates : https://microdata.worldbank.org/index.php/catalog/4487
- WFP Cameroon, bulletin de suivi des marchés, août 2023 : https://reliefweb.int/report/cameroon/wfp-cameroon-monthly-market-monitoring-bulletin-august-2023
- FEWS NET Cameroun, avril 2026 : https://fews.net/west-africa/cameroon/food-security-outlook-update/april-2026
- FEWS NET Cameroun, juin 2026 : https://fews.net/west-africa/cameroon/food-security-outlook/june-2026
- FAO GIEWS, fiche pays Cameroun : https://www.fao.org/giews/countrybrief/country/CMR/pdf/CMR.pdf
- FRED, Global price of Cocoa (PCOCOUSDM) : https://alfred.stlouisfed.org/series?seid=PCOCOUSDM
- UNCTAD, Basic information on Agriculture Development in Cameroon (noms des zones IRAD) : https://unctad.org/system/files/non-official-document/cw070823_p02_Cameroon.pdf
- Biernacki, Celeux, Govaert (2003), *Choosing starting values for the EM algorithm…*, CSDA 41 ; Blei, Kucukelbir, McAuliffe (2017), *Variational Inference: A Review for Statisticians*, JASA ; Wang, Titterington (2005), *Inadequacy of interval estimates corresponding to variational Bayesian approximations*, AISTATS ; Lakens (2017), *Equivalence tests*, SPPS.
