# Plan de travail (proposé le 2026-11-04, validé le 2026-11-04 : D-03 à D-09)

Colonne « Décision » : à remplir par l'étudiant (*Accepté*, *Refusé* avec motif, *Modifié* avec consigne).
Les constats (A-xx, T-xx) sont détaillés dans `ETAT_DU_PROJET.md`.

| ID | Constat | Preuve | Action proposée | Nature | Effort / coût | Dépend de | Décision |
|---|---|---|---|---|---|---|---|
| P-01 | A-01 : `n_init/texte` bloque tout le calibrage | `calibrage.py` l. 329-360 | Découper l'unité en 16 unités (4 cas × 4 blocs de 50 relances), exécutées en parallèle, plus une unité d'agrégation ; mêmes graines, mêmes ajustements : résultat identique. Script de vérification : comparaison avec l'ancienne fonction en mode rapide | Développement (numériquement neutre) | 1 h de code ; relance du calibrage par toi (les unités finies sont conservées) | E-01 lancé || Accepté ; réalisé autrement par le commit `315a21c` (D-09), vérification à faire |
| P-02 | A-02 : marge d'équivalence au plancher du bruit numérique | `calibrage.py` l. 607-616 | Voir question Q-1 | Changement de méthode | selon l'option | avant la vague 6 du calibrage || Accepté : Q-1 option B, marges justifiées avant fixation (D-04) ; **fait** : code `9ece8ce` (D-04) |
| P-03 | A-03 : R = 200 imposé à toute une famille par une hypothèse sans variance | `calibrage.py` l. 722-761 | Voir question Q-2 | Changement de méthode | selon l'option | avant la vague 7 || Accepté : Q-2 options B et C (D-05) ; **fait** : code `9ece8ce` (D-05) |
| P-04 | A-04, A-05 : dégénérescence asymétrique et définie autrement dans le texte | `algorithmes.py` l. 567-585 | Voir question Q-3 | Changement de méthode | 30 min de code + texte | avant les scénarios || Accepté : Q-3 option B (D-06) ; **fait** : code `9ece8ce` (D-06) ; texte au lot 5 |
| P-05 | A-06 : le MAP-EM n'a pas le prior de Dirichlet du VB | `parametres.py` l. 122 | Corriger le texte (RH4, l. 738, 954, tableau des hypothèses) : le MAP-EM porte les priors Normal-Wishart du VB et un Dirichlet plat ; il isole l'effet des priors sur les composantes, pas celui de l'élagage | Correction factuelle | 1 h | aucune || Accepté (D-03) ; **fait** : texte et hypotheses.py |
| P-06 | A-07 : couverture HP6 comparée à K connu pour l'EM | `etape_prix.py` l. 199-218 | Voir question Q-4 | Changement de méthode ou rédaction | 0 (déclarer) à 2 h (ajouter EM-BIC) | avant l'étape prix || Accepté : Q-4 option B (D-07) ; **fait** : code `f73142e` (D-07), texte |
| P-07 | A-08 : HP5 dépend de la marge | `etape_prix.py` l. 223-235 | Réglé par la décision Q-1 ; sinon déclarer la dépendance | suit Q-1 | 0 | P-02 || Accepté, suit Q-1 (D-04) |
| P-08 | A-09 : temps d'EM-BIC sous-estimés dans les tableaux de scénarios | `comparaison.py` l. 72-129 | Ne pas rapporter `temps_s` d'EM-BIC dans les tableaux de scénarios et du cas (le coût est jugé par HP4, mesuré à part) ; le dire en une phrase | Correction factuelle | 30 min (`tex_tables.py`) | aucune || Accepté (D-03) |
| P-09 | A-10, A-12 : vérité semi-synthétique fabriquée par EM-BIC ; test sur 3 régions | `etape_prix.py` l. 12-15 | Ajouter la première limite à la section 2.8 et au chapitre 3 (la seconde y est déjà) | Rédaction | 15 min | aucune || Accepté (D-03) ; **fait** : section 2.8 |
| P-10 | A-11 : sens d'une différence donné par la moyenne | `statistique.py` l. 207 | Rapporter en plus l'estimateur de Hodges-Lehmann (médiane des moyennes de Walsh), cohérent avec Wilcoxon, et donner le sens par lui | Changement de méthode (mineur) | 30 min | avant les agrégations || Accepté (D-03) ; **fait** : code `f73142e`, texte |
| P-11 | A-13 : chronométrage sous charge | tableau de suivi | Consigne d'exécution : lancer `python run.py chronometrage` seul sur l'instance (aucun autre calcul), et enregistrer la machine (voir P-17) | Expérience (consigne) | 0 | après calibrage || Accepté (D-03) |
| P-12 | T-01 : anciennes lectures dans le chapitre 3 | `body.tex` l. 1147-1310 | Remplacer chaque lecture chiffrée par « À compléter (calcul E-xx) » maintenant ; réécrire depuis les sorties au lot 4 | Rédaction | 1 h maintenant, puis lot 4 | aucune || Accepté (D-03) ; **fait** : 14 lectures remplacées (illustrations) ; réécriture au lot 4 |
| P-13 | T-02 : corpus texte décrit autrement | `body.tex` l. 950 | Aligner le texte sur le code (archive lue sans extraction, mots fréquents écartés par fréquence documentaire, aucune liste externe) | Correction factuelle | 15 min | aucune || Accepté (D-03) ; **fait** : texte |
| P-14 | T-03 : trois erreurs mathématiques | `body.tex` l. 467, 509, 673 | Corriger les trois passages | Correction factuelle | 30 min | aucune || Accepté (D-03) ; **fait** : trois passages |
| P-15 | T-04, M-12 : références et annexes périmées | voir T-04 | Mettre à jour annexes A et D et les renvois ; décrire l'instance cloud ; soit écrire `environnement.json` depuis `run.py`, soit retirer la phrase | Correction factuelle (+ petit développement) | 1 h | P-17 || Accepté (D-03) ; **fait** : annexes A et D |
| P-16 | T-10 : seuil d'activité | `body.tex` l. 852 | Aligner le tableau 2.4 et les lectures sur N_k/N ≥ 1 % (S10 garde la sensibilité) | Correction factuelle | 15 min | aucune || Accepté (D-03) ; **fait** : tableau 2.4 |
| P-17 | Machine et environnement non enregistrés | `run.py` | Écrire `resultats/environnement.json` à chaque lancement (processeur, cœurs, mémoire, système, versions) | Développement | 30 min | aucune || Accepté (D-03) ; **fait** : code `9ece8ce` |
| P-18 | T-05 : bibliographie non IEEE | `body.tex` l. 1454-1572 | Passer à BibTeX (`references.bib`, style IEEEtran), citations `\cite{}` numérotées par ordre d'apparition ; contrôle des entrées non citées | Rédaction | 1 jour | aucune || Accepté (D-03) ; **fait** : biblatex IEEE ; 4 entrées non citées à trancher |
| P-19 | T-06 : plan de l'école incomplet | plan de `body.tex` | Ajouter les sous-sections manquantes de la revue et de la méthodologie (voir Q-5) | Rédaction | 1 à 1,5 jour | P-20 || Accepté sous condition : canevas officiel requis (D-08) |
| P-20 | T-12 : volume | `main.toc` | Budget de pages : réduire le chapitre 1 (exemples numériques, variantes avancées, garanties détaillées) vers les annexes pour libérer 8 à 12 pages | Rédaction | 0,5 jour | Q-5 || Accepté (D-08) |
| P-21 | T-07, T-08, T-09, T-11 : forme | voir audit | Renvois automatiques (`\label`, `\ref`, `\cref`), doubles espaces, environnements `theorem` et `definition`, ordre des annexes | Rédaction (forme) | 0,5 jour | P-19 || Accepté (D-03) ; **fait** : renvois, doubles espaces, théorèmes, ordre des annexes |
| P-22 | M-14 : tests non relancés | `tests/` | Tu lances `python -m pytest -q tests` sur l'instance (déjà dans E-01) | Expérience (vérification) | quelques minutes | E-01 || Accepté (D-03) |
| P-23 | Lecture non faite | voir topo | Finir la lecture de `etape_texte.py`, `etape_illustrations.py`, `etape_validation.py`, `risque.py`, `tex_tables.py`, `app/`, notes, `SOURCES.md` ; reprendre les décisions des notes dans `DECISIONS.md` | Lecture | 2 à 3 h | aucune || Accepté (D-03) |
| P-24 | M-11 : étiquette Git et DOI | annexe A | À la version finale : étiquette `v1.0`, archive Zenodo (accord requis : service externe) | Question ouverte | 30 min | fin du travail || Reporté à la fin du travail (D-03) |

## Questions à trancher

**Q-1 (P-02) Marge d'équivalence.**
- *Option A, garder la règle actuelle* : aucun changement. Conséquence : l'équivalence ne sera probablement démontrée
  nulle part, ce que le texte devra lire comme un artefact de la marge, pas comme une différence entre les méthodes ;
  les réplications montent au plafond (coût, A-03).
- *Option B, marges fixées à l'avance par l'importance pratique* (recommandée) : par exemple ARI 0,05 et
  log-vraisemblance 0,05 nat par observation, déclarées avant tout résultat confirmatoire, avec une phrase de
  justification et un tableau de sensibilité (moitié et double de la marge). Conséquence : l'équivalence devient
  testable ; c'est un écart au protocole à déclarer (la règle change avant les résultats). Les valeurs exactes sont
  ta décision : je peux te proposer des appuis dans la littérature, à vérifier.
- *Option C, marge tirée de la variabilité d'échantillonnage* : par exemple 0,5 écart-type des différences entre
  deux jeux de données indépendants du même générateur. Conséquence : marge objective mais moins lisible pour un jury.

**Q-2 (P-03) Nombre de réplications.**
- *Option A, garder* : R = 200 probable pour toute la famille des scénarios ; durée à mesurer, risque de dépasser
  le 22 novembre.
- *Option B, exclure les hypothèses sans variance du maximum* (recommandée, avec C) : une hypothèse dont toutes les
  différences pilotes sont identiques est décidée sans ambiguïté par le TOST (cas `se = 0` de `statistique.tost`) ou
  rapportée comme « sans variance » ; elle ne fixe plus R pour les autres.
- *Option C, plafond par le budget de temps* : R = min(R calculé, R tenable avant le 15 novembre), la puissance obtenue
  étant rapportée pour chaque hypothèse. Conséquence : puissance inférieure à 0,8 pour certaines hypothèses, déclarée.

**Q-3 (P-04) Dégénérescence.**
- *Option A* : garder le code, corriger le texte et déclarer l'asymétrie comme limite de HS6, HP3 et HP7.
- *Option B* (recommandée) : un même critère pour tous les bras, celui que décrit déjà le texte (valeur propre minimale
  < 1e-6 × trace, ou 1 ≤ N_k < D + 1), appliqué à la covariance plug-in de chaque bras.

**Q-4 (P-06) Couverture HP6.**
- *Option A* : garder et déclarer que l'EM connaît K (comparaison favorable à l'EM).
- *Option B* (recommandée) : ajouter le bootstrap d'EM-BIC (K choisi sur chaque jeu) à côté de celui d'EM-K, et lire
  RH3 sur EM-BIC contre VB, EM-K servant de borne.

**Q-5 (P-19, P-20) Conformité au plan de l'école et volume.** Faut-il suivre exactement l'ordre des sous-sections du
gabarit (revue en six points, méthodologie en neuf points), ou suffit-il que chaque point soit présent et repérable ?
Le gabarit officiel de l'école est-il disponible (fichier ou courriel) ? Je recommande de faire apparaître chaque
point comme une sous-section titrée, en compensant par un déplacement d'environ 10 pages du chapitre 1 vers les annexes.

## Lots, dans l'ordre

1. **Lot 1, urgent (aujourd'hui)** : P-01 (débloque le calibrage), P-17 ; décisions Q-1 et Q-2, à prendre avant que
   le calibrage atteigne les vagues 6 et 7.
2. **Lot 2, méthode (avant les étapes confirmatoires)** : P-02, P-03, P-04, P-06, P-07, P-10 selon tes décisions.
3. **Lot 3, calculs longs (lancés dès la fin du calibrage)** : `python run.py` sur l'instance, chronométrage seul
   (P-11), fiches E-02 et suivantes.
4. **Lot 4, résultats dans le document** : P-08, P-12 (réécriture depuis les sorties), bilan des hypothèses.
5. **Lot 5, structure et conformité** : P-19, P-20, P-05, P-09, P-13, P-14, P-15, P-16.
6. **Lot 6, littérature et forme** : P-18, P-21, P-24.

Les lots 5 et 6 ne dépendent pas des calculs : ils peuvent avancer pendant que l'instance calcule.

## Calendrier (échéance : 22 novembre 2026)

| Dates | Travail | Condition |
|---|---|---|
| 4-5 novembre | Lot 1 ; tes décisions Q-1 à Q-5 ; relance du calibrage | tes réponses |
| 5-8 novembre | Calibrage sur l'instance ; lot 2 ; lots 5 et 6 en parallèle | durée du calibrage non mesurée : à estimer depuis ton tableau de suivi |
| 8-15 novembre | Calculs confirmatoires (lot 3) ; suite des lots 5 et 6 | R tenable (Q-2) |
| 15-19 novembre | Lot 4 : tableaux, figures, lectures depuis les sorties | fin des calculs le 15 novembre au plus tard |
| 19-21 novembre | Relecture, compilation, contrôle du volume, bilan final (phase 5) | |
| 22 novembre | Dépôt | |
