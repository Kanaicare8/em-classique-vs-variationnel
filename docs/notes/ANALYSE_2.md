# Deuxième analyse : code et mémoire (22 octobre 2026)

Elle complète [CHECKUP_CODE.md](CHECKUP_CODE.md). Les constats ci-dessous sont nouveaux, et chacun a été vérifié dans le code, dans le texte ou par exécution.

## 1. Code : constats nouveaux

### N1. Le nombre d'initialisations crée un biais de comparaison (benchmark exécuté)
`outils/bench_n_init.py` lance 200 relances indépendantes par cas (`resultats/bench_n_init.csv`). p est la proportion de relances qui atteignent le meilleur optimum observé ; n est le nombre d'initialisations nécessaire pour l'atteindre avec une probabilité de 99 %.

| Cas | EM : p (n) | VB : p (n) | Écart médian des relances manquées (nat/obs) |
|---|---|---|---|
| Synthétique, K = 3 | 1,00 (1) | 0,995 (1) | 0 |
| Synthétique, K = 6 | 0,005 (919) | 0,99 (1) | EM 0,029 |
| Iris, K = 3 | 0,90 (2) | 0,10 (44) | VB 0,046 |
| Iris, K = 6 | 0,005 (919) | 0,06 (75) | EM 0,28 |
| S&P 500, K = 4 | 0,20 (21) | 0,28 (15) | EM 0,005 |
| Climat N = 500, K = 5 | 0,02 (228) | 0,225 (19) | EM 0,14 |
| Climat N = 500, K = 10 | 0,01 (459) | 0,01 (459) | EM 0,14, VB 0,08 |

**Conséquences** :
- Les 10 initialisations du protocole n'ont pas de justification, et elles sont insuffisantes dans la plupart des cas.
- La difficulté d'optimisation n'est pas la même pour les deux méthodes : selon le cas, l'une ou l'autre atteint plus facilement son optimum. À budget fixe, une partie des écarts EM/VB du mémoire mesure donc la difficulté d'optimisation, et non la qualité du modèle. C'est un facteur de confusion non contrôlé.

**Correction proposée** (au choix, ou les deux pour une analyse de sensibilité) :
- (a) Fixer n_init par configuration à partir d'une étude pilote, pour que la probabilité d'atteindre l'optimum, à une tolérance déclarée, soit au moins de 0,99.
- (b) Utiliser une règle d'arrêt adaptative sur les relances : s'arrêter quand le meilleur critère n'a pas progressé depuis m relances, m étant déduit de p.
- (c) Rapporter aussi les résultats à budget de calcul égal.

La stratégie d'initialisation de l'EM est traitée par Biernacki, Celeux et Govaert (2003, *Computational Statistics & Data Analysis* 41:561-575, référence vérifiée). Le contenu détaillé de l'article n'a pas été lu ; il n'est cité ici que comme référence du sujet.

### N2. K̂ n'est pas défini de la même façon pour tous les bras
- EM-K, EM-Kmax, EM-BIC et EM-ICL : K̂ est le K ajusté, même si certaines composantes sont vides ou minuscules.
- MAP-EM et VB : K̂ est le nombre de composantes dont N_k/N ≥ 1 %.

Les comparaisons de K̂ (H1, S1 à S3, H7) appliquent donc deux règles différentes. **Correction** : une règle unique pour tous les bras, et la sensibilité au seuil rapportée.

### N3. La référence Köppen–Geiger est presque dégénérée sur le Cameroun
Effectifs des classes : 7, 365, 6832, 13 396, 164, 929, 152 et 1 cellules. Deux classes couvrent 92 % du territoire. Un ARI d'environ 0,15 pour toutes les méthodes est donc peu informatif. Par ailleurs, K_réf = 5 vient des zones agro-écologiques, qui sont indisponibles, et non de Köppen. **Correction** : justifier K_réf autrement (ou le supprimer), et privilégier les critères sans étiquette, une fois la validation par blocs corrigée (C1).

### N4. Le modèle de référence du semi-synthétique n'est pas l'optimum annoncé
Le modèle de référence est un EM à K = 5 ajusté avec 10 initialisations. Or, à K = 5 sur le climat, p ≈ 0,02 (N1). Le modèle de référence n'est donc vraisemblablement pas le maximum de vraisemblance. Cela n'invalide pas le semi-synthétique, puisque la vérité est simplement le modèle choisi, mais le texte ne doit pas le présenter comme « le meilleur modèle à N complet ».

## 2. Mémoire : cohérence avec ce que vous faites

| Point | Constat (lignes de `body.tex`) | Correction |
|---|---|---|
| **Collision des numéros d'hypothèses** | H1 à H3 (réplication, §2.3.13), H1 à H8 (climat), H4 à H6 (S&P 500) : « H4 » vaut coût (l. 578, 770, 1027) et log-vraisemblance (l. 1176, 1198) ; « H6 » vaut couverture et intervalle de VaR | Préfixes distincts : HR (réplication), HS1 à HS10 (scénarios), HC1 à HC8 (climat), HF1 à HF3 (finance), HT1 (texte) |
| **Affirmations résiduelles contraires à la thèse** | Conclusion du ch. 1 : « le cadre bayésien permet de lever une grande partie de ces limites » ; introduction du ch. 2 : « douze expériences complémentaires et indépendantes » (elles portent sur le même jeu) et « se distingue par son ampleur » ; §2.5 : « démonstration rigoureuse », « garantie de supériorité universelle » | Réécrire selon la thèse (déplacement, non levée) ; retirer « indépendantes » et le ton promotionnel |
| **Passages périmés** | §2.5 : « scalabilité et aberrations non répliquées » (elles le sont : 10 répétitions, S7) ; introduction du ch. 3 et description de §3.2.1 | Mettre à jour |
| **« Fixées avant l'analyse »** | Plusieurs hypothèses ont été modifiées après la première exécution : H2 passée de N complet à N = 2000, H1 étendue à tous les N, H8 réduite à la dégénérescence, paires de Diebold–Mariano « contre la gaussienne » ajoutées | Section « Écarts au protocole » qui liste chaque modification et sa raison ; protocole figé et daté dans le dépôt |
| **Résultats invalides ou biaisés** | H2 climat (fuite, C1) ; décisions des grilles (Holm, C2) ; H6 et intervalles de VaR (bootstrap, C3) ; tous les écarts EM/VB à budget fixe (N1) | Recalculer après correction ; retirer d'ici là |
| **Thèse non opérationnalisée** | « Le VB déplace la sélection de K vers les hyperparamètres » n'est testée que par H5, qui est mal posée (M1) | Définir une mesure testable : sensibilité de K̂ aux hyperparamètres sur un domaine justifié, comparée à la sensibilité de K̂ aux choix de l'EM-BIC (initialisation, critère) |

## 3. La structure de la recherche est-elle digne d'un mémoire de Master ?

**Ce qui est au niveau** :
- une question de recherche explicite et une thèse falsifiable ;
- les trois niveaux d'inférence et le MAP-EM comme contrôle de l'effet des priors ;
- des hypothèses chiffrées avec critères de décision, des tests appariés, des tests d'équivalence et une correction pour comparaisons multiples ;
- des réplications, un jeu semi-synthétique à vérité connue, la reproductibilité par le code et les résultats défavorables conservés.

Ce design dépasse ce qu'on attend habituellement d'un Master.

**Ce qui empêche de le défendre en l'état** :
1. **Il manque un chapitre de méthodologie.** Le protocole, les tests, les métriques et les données sont dispersés entre le §2.3.1, le §2.3.14 et le §3.1. L'implémentation (§3.2-3.3) arrive après les résultats qui en dépendent.
2. **L'exploratoire et le confirmatoire sont mélangés.** Les expériences à graine unique et K = 6 imposé (§2.3.2 à 2.3.12) précèdent les scénarios confirmatoires, avec le même statut apparent.
3. **Trois défauts d'exécution invalident des résultats** (C1 à C3), et un facteur de confusion n'est pas contrôlé (N1).
4. **Des paramètres sont arbitraires** (E6 du checkup), contraire à votre exigence.

**Structure recommandée** (contenu conservé, réordonné) :
1. **Introduction générale** : problématique, thèse, hypothèses préfixées, plan.
2. **Chapitre 1 – Fondements** : actuel ch. 1 et §2.1-2.2 (comparaison théorique et algorithmique, MAP-EM).
3. **Chapitre 2 – Méthodologie** :
   - implémentation tensorielle et reprenable ;
   - critère d'arrêt commun et calibrage des paramètres (registre, benchmarks, recherche heuristique) ;
   - données (synthétiques, Iris, climat, S&P 500, texte) ;
   - métriques, tests déclarés, règle de décision après Holm ;
   - hypothèses et écarts au protocole.
4. **Chapitre 3 – Résultats** :
   - 3.1 illustrations exploratoires (K = 6, Iris, ELBO) ;
   - 3.2 scénarios confirmatoires S1 à S10 ;
   - 3.3 cas réels (climat, S&P 500, texte).
5. **Chapitre 4 – Discussion** : grille axe × preuve, menaces à la validité (interne, externe, de construit, statistique), recommandations avec niveau de preuve, revue des domaines non testés.
6. **Conclusion générale**.

## 4. Ordre de travail proposé
1. Corriger C1 à C3, M5 et N2 dans le code. Ce sont les corrections sans lesquelles les résultats ne valent rien.
2. Construire le registre des paramètres et l'étape de calibrage : n_init (N1), tolérance, `reg`, marges d'équivalence, taille des blocs, priors par recherche heuristique sur validation croisée.
3. Terminer l'architecture demandée : `run.py` reprenable, artefacts, figures depuis les artefacts, suppression de sklearn, nltk, matplotlib et Jupyter.
4. Relancer toutes les expériences.
5. Réorganiser le mémoire selon le §3 et réécrire les résultats.
