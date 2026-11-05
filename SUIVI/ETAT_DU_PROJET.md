# État du projet (2026-11-04)

## 1. Topo

**Lu en entier** : `introduction.tex`, `body.tex` (chapitres 1 à 3, conclusion, bibliographie, annexes A, B en partie,
D, E en partie, F), `hypotheses.py`, `parametres.py`, `calibrage.py`, `comparaison.py`, `statistique.py`,
`scenarios.py`, `etape_chronometrage.py`, `LANCEMENT.md`, `A_REGENERER.md`.
**Lu en partie** : `algorithmes.py` (dégénérescence, EM, MAP-EM, VB), `etape_prix.py` (couverture, sensibilité),
`persistance.py` (magasin), `run.py` (ordonnancement), `donnees.py` (20 Newsgroups), notes `ANALYSE_3` (début).
**Non vérifié** : `etape_texte.py`, `etape_validation.py`, `etape_illustrations.py`, `risque.py`, `tex_tables.py`,
`figures.py`, `app/`, `tests/` (tests non relancés), annexes B, C et E en détail, notes `CHECKUP_CODE.md`,
`ANALYSE_COHERENCE.md`, `ANALYSE_SOURCES.md`, `ANALYSE_2.md`, `references/SOURCES.md`, figures TikZ.

**Situation** : le protocole est écrit et le code qui l'exécute existe ; **aucun résultat confirmatoire n'existe
encore** pour la nouvelle chaîne. Le calibrage repart sur l'instance cloud avec le commit `e5eeaf8` (E-01). Tous les
tableaux du chapitre 3 sont « à générer » ; plusieurs paragraphes du chapitre 3 contiennent encore des lectures de
l'ancienne chaîne.

## 2. Forces du travail

- Protocole déclaré dans le code avant l'exécution (`hypotheses.py`), un seul test par hypothèse, Holm par famille,
  équivalence admise comme issue, écarts au protocole déclarés (`body.tex` l. 1123).
- Registre des paramètres avec statut, règle et référence (`parametres.py`) ; refus des étapes confirmatoires tant
  qu'un paramètre n'est pas calibré.
- Comparateurs bien choisis : EM-BIC et EM-ICL comme baseline (et non EM à K imposé), MAP-EM pour isoler les priors,
  critère d'arrêt commun.
- Cas pratique réel et local (prix du PAM au Cameroun), validation temporelle, variable causale, nettoyage déclaré,
  Diebold-Mariano sur la série mensuelle.
- Ton prudent et honnête : « non testé » explicite, thèse sans « supériorité », limites concrètes.
- Chaîne reprenable, graines dérivées du rôle, tableaux produits par le code.

## 3. Matrice d'avancement

| ID | Engagement (source) | Code | Exécuté | Décrit | Statut |
|---|---|---|---|---|---|
| M-01 | Calibrage en sept vagues (`body.tex` l. 969-980) | `calibrage.py` | relancé sur le cloud (E-01) ; ancien calcul au commit `97dcb95` abandonné | oui | Implémenté, jamais exécuté (version actuelle) |
| M-02 | Validation numérique des propriétés (l. 1135) | `etape_validation.py` | non | tableau à générer | Implémenté, jamais exécuté (non vérifié) |
| M-03 | Illustrations sur le jeu de référence, Iris, aberrations (l. 1132-1275) | `etape_illustrations.py` | non (nouvelle chaîne) | oui, avec lectures de l'ancienne chaîne | Décrit avec d'anciens résultats |
| M-04 | Scalabilité et coût du pipeline EM-BIC, HP4 (l. 1193-1205, 1312) | `etape_chronometrage.py` | non | oui | Implémenté, jamais exécuté |
| M-05 | Scénarios S1 à S7 confirmatoires (l. 866-902, 1277-1302) | `scenarios.py` | non | tableaux à générer | Implémenté, jamais exécuté |
| M-06 | S8, S9, S10 descriptifs (l. 1270-1310) | `scenarios.py` | non | lectures de l'ancienne chaîne | Décrit avec d'anciens résultats |
| M-07 | Cas des prix : référence, sous-échantillons, semi-synthétique, couverture, sensibilité, prévision, alerte (l. 907-939, 1316-1358) | `etape_prix.py` | essai réduit local seulement (`resultats/magasin_rapide/prix`) | oui | Implémenté, jamais exécuté (confirmatoire) |
| M-08 | Comparaison pLSA contre LDA, HT1 (l. 941-950, 1361-1368) | `etape_texte.py` | non | oui | Implémenté, jamais exécuté |
| M-09 | Bilan RH1 à RH5, grille axe × preuve, guide (l. 1370-1420) | `tex_tables.py` | non | oui | Dépend de M-04 à M-08 |
| M-10 | Application de présentation (LANCEMENT § 5 bis) | `app/` | non vérifié | non (hors mémoire) | Fait, non vérifié |
| M-11 | Dépôt public, étiquette Git et DOI Zenodo (annexe A) | dépôt | dépôt public à jour (`e5eeaf8`) ; étiquette et DOI absents | oui | Partiel |
| M-12 | Environnement enregistré dans `environnement.json` (annexe D) | aucun dans la chaîne actuelle (seulement `legacy/main.py`) | non | oui | Décrit, non implémenté |
| M-13 | Variantes SEM, EM online, SVI (« vérification, non bras de comparaison », l. 595) | `algorithmes.py`, calibrage V5 | non | oui | Implémenté, jamais exécuté |
| M-14 | Tests unitaires (74 annoncés, `LANCEMENT.md`) | `tests/` | non relancés depuis l'inventaire | oui | Fait, non vérifié |

## 4. Audit de rigueur

Gravité : **Bloquant** (fausse un résultat ou une conclusion), **Majeur** (affaiblit la démonstration ou la
conformité), **Mineur** (forme).

### 4.1 Projet et expériences

| ID | Gravité | Constat | Preuve | Pourquoi c'est un problème |
|---|---|---|---|---|
| A-01 | Bloquant | L'unité `n_init/texte` enchaîne 800 ajustements (pLSA et 3 LDA × 200 relances) dans un seul processus, et toutes les vagues 5 à 7 l'attendent | `calibrage.py` l. 329-360 et l. 786-788 ; en local elle a tourné du 28 octobre au 1er novembre sans finir (`resultats/magasin/_journal/`) | Elle bloque tout le calibrage, donc tous les calculs confirmatoires, alors que l'échéance est le 22 novembre. **Mise à jour 2026-11-04** : réglé par le commit `315a21c` sous réserve de la vérification bit à bit (N-02, D-09) |
| A-02 | Bloquant | La marge d'équivalence est le quantile à 95 % de l'écart entre deux ajustements de la même méthode (bruit d'optimisation), avec un plancher de 0,001 | `calibrage.py` l. 607-616 ; `parametres.py` l. 147-150 | Avec un nombre de relances calibré pour atteindre presque toujours le même optimum, cet écart est proche de 0 : la marge tombe au plancher et l'équivalence (RH1, HS1, HS3, HS7, HP2) devient presque impossible à démontrer, quelle que soit la qualité réelle des deux méthodes. Lakens (2017) définit la marge par ce qui est jugé important, pas par le bruit numérique |
| A-03 | Bloquant | Le nombre de réplications est le maximum sur toutes les hypothèses d'une famille, et une hypothèse dont le pilote n'a aucune variance reçoit d'office le plafond de 200 | `calibrage.py` l. 722-729 et 703 | Une seule hypothèse sans variance (cas possible, non vérifié : HS6 à N = 1000 si aucun bras ne dégénère dans le pilote) impose R = 200 à tous les scénarios : 125 × 200 = 25 000 unités au lieu de 3 750, coût et durée multipliés par près de 7. A-02 aggrave l'effet (marge minuscule, donc R maximal) |
| A-04 | Majeur | La dégénérescence n'est pas mesurée de la même façon selon le bras : le critère « plancher » (valeur propre ≤ 2 reg) ne s'applique qu'à l'EM et au MAP-EM ; pour le VB il vaut toujours faux | `algorithmes.py` l. 567-585 et l. 1058 ; tests HS6, HP3, HP7 (`hypotheses.py` l. 98-125) | L'EM a deux façons d'être compté dégénéré, le VB une seule : le test « VB moins dégénéré que l'EM » (RH4) est favorisé par construction |
| A-05 | Majeur | Définition de la dégénérescence différente dans le texte et le code | texte : valeur propre < 1e-6 × trace ou N_k < D + 1 (`body.tex` l. 774, 959) ; code : N_k < D + 1 ou valeur propre ≤ 2 reg (`algorithmes.py` l. 567-585) | Le lecteur ne sait pas ce qui est réellement compté |
| A-06 | Majeur | Le MAP-EM n'a pas les mêmes priors que le VB : α0 = 1 (registre `alpha0_map`) contre α0 = 1/Kmax pour le VB | `parametres.py` l. 122-124 ; `comparaison.py` l. 53-59 ; `algorithmes.py` l. 659 | RH4 (« le MAP-EM, qui porte les mêmes priors ») et `body.tex` l. 738, 954 sont inexacts : le MAP-EM ne porte que la partie Normal-Wishart ; il ne peut pas élaguer par le Dirichlet |
| A-07 | Majeur | Couverture HP6 : le VB doit trouver K seul (Kmax = 8, élagage), le bootstrap de l'EM est fait au K vrai (`EM-K`, K_ref) | `etape_prix.py` l. 199-218 | La comparaison avantage l'EM, qui connaît le nombre de composantes ; le texte (l. 935, 967) ne le dit pas |
| A-08 | Majeur | Sensibilité HP5 : les configurations « plausibles » sont celles à moins de la marge LL du meilleur score ; avec une marge au plancher (A-02), il n'en reste qu'une, donc var(K̂) du VB = 0 | `etape_prix.py` l. 223-235, 266-267 | HP5 (RH2) ne peut alors pas donner « A > B » : l'issue dépend du défaut A-02, pas des données |
| A-09 | Majeur | Le temps de EM-BIC dans les scénarios et le cas des prix est mesuré en relisant des ajustements déjà mémorisés (EM-K, EM-Kmax partagent les clés `EM/K=`) | `comparaison.py` l. 72-93 et 120-129 | `temps_s` d'EM-BIC sous-estime le coût réel du balayage ; HP4 n'est pas touchée (chronométrage séparé, `etape_chronometrage.py` l. 63-93), mais les colonnes de temps des tableaux de scénarios le seraient |
| A-10 | Majeur | Le semi-synthétique est tiré du modèle EM-BIC de référence, et HP1 mesure l'écart à ce K_ref | `etape_prix.py` l. 12-15, 124-140 | La vérité est fabriquée par l'un des deux bras comparés ; à déclarer comme limite (ce n'est pas une fuite, c'est un avantage de construction possible pour EM-BIC) |
| A-11 | Mineur | Le sens d'une différence est donné par le signe de la moyenne alors que le test est un test de rangs (Wilcoxon) | `statistique.py` l. 207-208 | Moyenne et rangs peuvent être de signes opposés avec des valeurs extrêmes |
| A-12 | Majeur | La période de test ne couvre que 3 régions sur 6 et a une distribution différente | `body.tex` l. 922, 1358 | Déjà déclaré comme limite : rien à corriger, à garder en tête pour la soutenance |
| A-13 | Majeur | Le chronométrage doit tourner seul ; le tableau de suivi montrait deux calculs simultanés sur l'instance | tableau collé le 2026-11-04 ; `run.py` l. 115-116 (un seul travailleur, mais rien n'empêche un autre `run.py` en parallèle) | Des temps mesurés sous charge faussent HP4 et la scalabilité |
| A-14 | Majeur | Les propriétés théoriques (monotonie de la log-vraisemblance, ELBO ≤ log-vraisemblance maximale) sont vérifiées sur l'EM régularisé par la valeur calibrée `reg_covariance` (0,1 depuis D-15), alors que la garantie de monotonie ne vaut que pour l'EM non régularisé | `etape_validation.py` l. 87 et 93 (aucun `reg=` passé, donc le registre) ; `algorithmes.py` l. 618-621 ; `body.tex` l. 1327 | Une baisse de la log-vraisemblance ou un ELBO supérieur à la log-vraisemblance de l'EM peut apparaître sans contredire la théorie, et le texte l'annonce comme vérifié. Le tableau 1.2 passe déjà `reg = 0` (l. 48) |
| A-15 | Mineur | Le nombre de baisses de la log-vraisemblance de l'EM en lot complet est écrit 0 dans le code, sans être mesuré | `etape_illustrations.py` l. 188 ; tableau `tex_tables.py` l. 146 | Chiffre non calculé dans un tableau du mémoire ; avec la régularisation à 0,1 il n'est pas garanti nul |
| A-16 | Question | Une seule valeur absolue de `reg_covariance` pour toutes les familles, choisie par rang moyen où les jeux synthétiques sont majoritaires ; Iris est en centimètres non standardisés (variance de la largeur des pétales de setosa d'environ 0,01 cm², source : jeu Iris, à vérifier dans `data/iris.csv`) | `calibrage.py` l. 81-88 et 254-275 ; `body.tex` l. 996 | 0,1 ajouté à chaque variance peut changer fortement les ajustements EM sur Iris ; non vérifié par calcul |
| A-17 | Mineur | Docstring périmée : renvoie aux étapes climat et sp500 retirées | `etape_illustrations.py` l. 7-8 | aucun effet sur les résultats |

### 4.2 Document

| ID | Gravité | Constat | Preuve | Pourquoi c'est un problème |
|---|---|---|---|---|
| T-01 | Bloquant | Lectures et chiffres de l'ancienne chaîne restés dans le chapitre 3 | `body.tex` l. 1147, 1152, 1158-1160, 1177 (« moyennes sur les 30 jeux »), 1191, 1211, 1234, 1246, 1260-1262 (poids 0,16, 0,33, 0,51), 1275, 1310 | Ils ne correspondent à aucun fichier de la nouvelle chaîne |
| T-02 | Majeur | Corpus texte : le texte dit `sklearn.datasets.fetch_20newsgroups` et une liste de mots vides de scikit-learn ; le code lit l'archive et écarte les mots fréquents par fréquence documentaire | `body.tex` l. 950 ; `donnees.py` l. 11-12, 301, 336 ; `parametres.py` l. 208-213 | Méthode décrite ≠ méthode exécutée |
| T-03 | Majeur | Erreurs mathématiques | l. 467 (« ELBO plus élevé, donc évidence plus grande » : faux, l'écart KL varie d'un modèle à l'autre, ce que dit d'ailleurs l. 606) ; l. 509 (W_k^{-1} appelé « matrice de précision », lecture de l'effet inversée) ; l. 673 (« l'ELBO se réduit exactement à la log-vraisemblance », contredit par l. 690-694) | Un jury de mathématiciens les relèvera |
| T-04 | Majeur | Références périmées | l. 313 et 628 (implémentation « au chapitre 3 ») ; annexe A.4 (`texte_plsa_lda.py`, legacy) ; table de l'annexe A (`lda_variationnel`, section 3.1.1, équations 3.1-3.2 inexistantes) ; annexe D (machine Windows 4 cœurs, sections 2.3.6, 2.3.9, 2.3.13, `environnement.json` non produit, « dix fois » l. 1194 contre 20 répétitions dans le registre) | Fidélité du document au projet |
| T-05 | Majeur | Bibliographie non conforme IEEE : citations auteur-année dans le texte, numérotation alphabétique, entrées saisies à la main | `body.tex` l. 1458 et partout (« Dempster, Laird et Rubin (1977) ») | IEEE impose [n] dans le texte, numérotés par ordre de première citation |
| T-06 | Majeur | Plan de l'école incomplet : revue de littérature sans introduction de chapitre structurée, sans section « travaux antérieurs » comparative, « limites de la littérature », « lien avec la recherche » ni synthèse ; méthodologie sans type et approche de recherche, cadre (population, critères d'inclusion), plan d'échantillonnage, considérations éthiques, synthèse | plan de `body.tex` (l. 38-640, 639-1124) contre § 4 du prompt de reprise | Conformité au gabarit officiel |
| T-07 | Mineur | Renvois écrits en dur (« section 1.6.4 », « tableau 1.2 », numéros d'équation par `\tag`) | partout dans le chapitre 1 et 2 | Ils deviennent faux dès qu'une section bouge (règle de style 13) |
| T-08 | Mineur | Doubles espaces laissés par la suppression des tirets cadratins | l. 39, 114, 214, 255, 257, 259 et suivantes | Forme |
| T-09 | Mineur | Théorèmes et définitions sans environnement dédié | chapitre 1 (Jensen, Gibbs, Wu, Rousseau et Mengersen) | Exigence de l'audit (§ 6) |
| T-10 | Majeur | Seuil d'activité : le tableau 2.4 annonce N_k ≥ 1 pour les illustrations, le code applique N_k/N ≥ 1 % à tous les bras | `body.tex` l. 852, 1152, 1158 ; `comparaison.py` l. 32-34 | Étiquette définie autrement dans le texte et le code |
| T-11 | Mineur | Annexe F placée avant l'annexe E | `body.tex` l. 1814-1820 | Ordre |
| T-12 | Majeur | Volume : 102 pages de corps aujourd'hui, avec la limite de 112 ; les ajouts T-06 et les résultats vont l'augmenter | `main.toc` (annexes p. 103) ; D-01 | Il faudra déplacer du chapitre 1 vers les annexes ou condenser |
