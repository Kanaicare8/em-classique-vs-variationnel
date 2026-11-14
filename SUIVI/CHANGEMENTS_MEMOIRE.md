# Modifications du mémoire, par section

Sauvegarde avant modification : `sauvegardes/body_20261104-125431.tex` (et PDF du 27 octobre dans `sauvegardes/`).
Vérification après modification : compilation `pdflatex` (deux passes) sans erreur, 124 pages ; références non
définies : uniquement des tableaux encore à générer (`tab:ill_*`, `tab:prix_*`, `tab:S9_variance`).

## 2026-11-04

| Section | Changement | Point du plan |
|---|---|---|
| Chap. 1, décomposition de l'ELBO | « ELBO plus élevé, donc évidence plus grande » remplacé : l'ELBO est une borne, l'écart KL dépend du modèle ; comparer des ELBO revient à comparer des bornes | P-14 (T-03) |
| Chap. 1, mises à jour du VB | $W_k^{-1}$ n'est pas la matrice de précision : c'est l'inverse de la matrice d'échelle de Wishart ; effet sur $\mathbb{E}[\Lambda_k] = \nu_k W_k$ et sur la loi de $\mu_k$ explicité | P-14 (T-03) |
| Chap. 2, EM comme cas particulier | « l'ELBO se réduit exactement à la log-vraisemblance » corrigé : à une constante divergente et à $\log p(\hat\theta)$ près, borne égale à $\ell(\hat\theta)$ quand $q(Z)$ est la loi a posteriori | P-14 (T-03) |
| Chap. 2, MAP-EM | « mêmes priors que le VB » corrigé : Normal-Wishart du VB, Dirichlet plat ($\alpha_0 = 1$) ; le MAP-EM n'élague pas ; ce que la comparaison sépare et ne sépare pas | P-05 (A-06) |
| Chap. 2, bras des scénarios | idem, dans la liste des bras | P-05 |
| Chap. 2, tableau 2.4 | composante active : $N_k/N \geq 1\,\%$ pour tous les bras et tous les plans | P-16 (T-10) |
| Chap. 2, texte (20 Newsgroups) | description alignée sur le code : archive lue directement, mots vides écartés par fréquence documentaire, sans liste externe ; documents de moins de 20 occurrences du vocabulaire exclus ; sensibilité au vocabulaire | P-13 (T-02) |
| Chap. 2, tests déclarés | marges fixées a priori avec leur justification (ARI 0,05, LL 0,05 nat) ; sensibilité moitié et double ; contrôle par le bruit d'optimisation ; estimateur de Hodges-Lehmann pour le sens | D-04, P-10 |
| Chap. 2, couverture (HP6) | VB contre bootstrap EM-BIC, différence appariée ; EM à K connu comme borne ; bootstraps conditionnels à K | D-07 |
| Chap. 2, calibrage (vagues 6 et 7) | marges contrôlées et non plus calibrées ; exclusion des hypothèses sans variance ; plafond de budget | D-04, D-05 |
| Chap. 2, menaces à la validité | validité interne : vérité semi-synthétique fabriquée par EM-BIC ; écart au protocole (5) : les cinq règles changées le 4 novembre avant tout résultat confirmatoire | P-09, D-04 à D-07, P-10 |
| Chap. 3, illustrations | 14 lectures de l'ancienne chaîne remplacées par `\aCompleter{...}` (ce qu'il faudra lire), en gardant les phrases de méthode et de théorie ; source des temps du tableau 3.x corrigée ; chronométrage : 20 répétitions (registre) au lieu de « dix fois » | P-12 (T-01), T-04 |
| Bibliographie | ajout de Hodges et Lehmann (1963), Lakens, Scheel et Isager (2018), Steinley (2004) ; renumérotation (60 entrées) | D-04, P-10 |
| `main.tex` | nouvelle commande `\aCompleter{...}` (encadré visible) | P-12 |

**Non vérifié** : les seuils 0,65 / 0,80 / 0,90 dans l'article de Steinley (2004) (source secondaire seulement).
**Reste** : lectures du chapitre 3 au-delà des illustrations, à réécrire au lot 4 depuis les sorties ; annexes A et D
(P-15) ; structure du canevas (P-19, P-20) ; bibliographie IEEE (P-18).

## 2026-11-04 (suite)

| Section | Changement | Point du plan |
|---|---|---|
| Annexe A | tableau fonctions / sections / équations en renvois automatiques (`\ref`), ligne LDA corrigée (section du corpus texte, pas « 3.1.1 ») ; A.4 décrit `donnees.py` et `etape_texte.py` au lieu du script `texte_plsa_lda.py` (ancien) | P-15, T-04 |
| Annexe D | réécrite : instance cloud ; tableau `environnement` produit par `tex_tables.py` depuis `resultats/environnement_historique.jsonl` ; un fil par processus, sous-processus du calibrage ; graines toutes dérivées du rôle ; vérification bit à bit du parallélisme | P-15, P-17 |
| Chap. 2 et 3 | graines « 42 » et « 7 » retirées (le code dérive toutes les graines du rôle) ; boîte des aberrations décrite comme dans le code | T-04 |
| Chap. 1 et 2 | « implémentations présentées au chapitre 3 » corrigé en renvoi à la section d'implémentation (chapitre 2) ; étiquettes ajoutées à 11 sections | T-04, T-07 |
| Bibliographie | passage à biblatex (style IEEE, numérotation par ordre d'apparition, « vol. », `references.bib`) ; 95 citations auteur-année converties en `\cite{}` (nom de l'auteur gardé dans les citations narratives) ; Porter (1980) ajouté (cité mais absent de la liste) ; PyTorch cité dans l'implémentation | P-18 (T-05) |
| Grille « axe × preuve » (`tex_tables.py`) | numéros de section d'une ancienne version (« §2.3.16 »…) remplacés par des renvois ; citations en `\cite` | T-07, P-18 |

**Entrées non citées (ne s'impriment plus en IEEE)** : Blei et Jordan (2006), Frühwirth-Schnatter (2006), McLachlan
et Peel (2000), McLachlan et Krishnan (2008). Décision de l'étudiant : les citer à un endroit pertinent, ou les retirer.

**À vérifier au lot 4** : chiffres descriptifs restant au chapitre 3 (par exemple l'écart moyen du maïs, +0,04 puis
−0,12, section du cas pratique), à confronter au tableau `prix_descriptif` une fois généré.

Sauvegardes : `sauvegardes/body_*_avant_bibtex.tex`, `sauvegardes/introduction_*.tex`. Compilation :
`pdflatex`, `biber`, `pdflatex` ×2 sans erreur ni citation indéfinie, 124 pages.

## 2026-11-04 (forme, P-21)

| Section | Changement | Point du plan |
|---|---|---|
| Tout le document | 190 renvois internes saisis à la main (sections, équations, tableaux, chapitres) remplacés par des renvois automatiques, d'après les numéros actuels ; 64 sections et les 3 chapitres étiquetés ; renvois vers des sections d'ouvrages cités laissés tels quels | P-21 (T-07) |
| Annexes | deux renvois périmés corrigés (variable du cas pratique : section de méthodologie, pas « 3.1.1 » ; digamma : implémentation du VB, pas « chapitre 3, sections 3.2.1 et 3.3.1 ») | T-04 |
| Annexes E et F | lettres échangées pour suivre l'ordre du document (E : registre ; F : rappels mathématiques, F.1 à F.4) | P-21 (T-11) |
| Texte | 28 phrases où un tiret d'incise avait été retiré (double espace) : parenthèses ou deux-points ; doubles espaces des formules réduits | P-21 (T-08) |
| Chap. 1 | environnements `theoreme` (amsthm) : Jensen (hypothèses d'intégrabilité ; condition d'égalité énoncée pour f strictement concave), Gibbs, convergence de l'EM, Rousseau et Mengersen (énoncé simplifié) | P-21 (T-09), P-14 |

**À vérifier par l'étudiant** : l'énoncé du théorème de Wu (1983). La clause « ou si la suite elle-même est
convergente » (tautologique) a été retirée ; la condition exacte de convergence de la suite (par exemple
‖θ^{t+1} − θ^t‖ → 0 et points stationnaires isolés) n'a pas été ajoutée, faute d'avoir lu l'article.
**À vérifier au lot 4** : l'exemple numérique de la section 1.7.5 (« 5 à 15 itérations », « dix essais, graines 0 à
4 ») doit correspondre aux sorties de l'étape de validation.
Compilation : 125 pages, sans erreur ; renvois non définis : tableaux encore à générer seulement.

## 2026-11-04 (structure, D-10 option A ; P-19, P-20)

| Partie | Changement |
|---|---|
| Partie I | deux chapitres : 1 « Cadre conceptuel : fondements théoriques et algorithmes EM », 2 « État de l'art et positionnement de la recherche » ; la méthodologie devient le chapitre 3, les résultats le chapitre 4 (renvois automatiques) |
| Chap. 1 | section « Introduction de la revue » (rôle, contexte, structure) au lieu du paragraphe d'ouverture ; historique de l'EM (ancienne 1.6.1) supprimé, repris en 2.1 ; « variantes avancées » déplacées en 2.3 ; exemples numériques (densité d'un GMM, Dirichlet--Catégorielle, EM détaillé, VB) et Baum-Welch déplacés en annexe G (G.1 à G.5), une phrase de renvoi à leur place |
| Chap. 2 (nouveau) | 2.1 travaux sur l'EM ; 2.2 travaux sur l'inférence variationnelle ; 2.3 tendances (SVI, AEVB, flux) ; 2.4 comparaison critique (tableau, quatre controverses) ; 2.5 domaines d'application (ancienne section « Portée » du chapitre des résultats, plus le suivi des prix par le PAM) ; 2.6 limites de la littérature (5) ; 2.7 lien avec la recherche (limites → RH1 à RH5) ; 2.8 synthèse. Rédigé à partir de ce que le mémoire disait déjà de chaque source ; les constats de lacunes portent « sur les seules sources examinées » |
| Chap. 3 | sections ajoutées : introduction du chapitre, type et approche, cadre de recherche, plan d'échantillonnage, considérations éthiques, synthèse et transition ; renommées : « Sources, collecte et préparation des données » (avec validité et fiabilité), « Méthodes d'analyse : protocole de comparaison », « Limites de la méthodologie : menaces à la validité et écarts au protocole » |
| Chap. 3, données | phrase corrigée : seule l'empreinte du fichier des prix est vérifiée par le code (et non « les données réelles ») |
| Chap. 4 | « Introduction du chapitre » ; « Analyse et interprétation : bilan des hypothèses » avec « Mise en relation avec la littérature » (encadré à compléter) ; « Discussion critique » (limites à compléter, six précautions d'interprétation indépendantes des résultats, perspectives) ; « Synthèse du chapitre » |
| Introduction | plan en quatre chapitres ; MAP-EM décrit avec le Dirichlet plat ; « Elle est décomposée » → « La thèse est décomposée » |
| Divers | renvoi erroné corrigé (« section 2.1 de l'article » de Hoffman et al. avait été converti en renvoi interne) ; renvoi Neal et Hinton dans la conclusion corrigé vers la section du cas limite de Dirac ; citations des annexes converties |

Volume : corps (introduction à conclusion générale) jusqu'à la page 101, bibliographie 102 à 106, annexes à partir de
107 (135 pages au total). Avant : corps jusqu'à 107. Marge pour les résultats à venir : environ 6 pages si la
bibliographie compte dans les 112, 11 sinon (à préciser par l'étudiant).

**À relire par l'étudiant** : le chapitre 2 en entier (nouveau texte), en particulier les constats de la section 2.6
sur ce qui manque dans la littérature, qui n'engagent que les sources citées.

## 2026-11-04 (vérifications et relecture du chapitre 2)

| Section | Changement | Source ou motif |
|---|---|---|
| Chap. 3, tests ; registre | justification de la marge ARI réécrite **sans** l'échelle 0,65 / 0,80 / 0,90 : 0,05 = 5 % de l'écart entre accord dû au hasard (0) et accord parfait (1), même seuil relatif que la log-vraisemblance ; Steinley (2004) cité seulement comme référence de l'ARI en validation des classifications | l'échelle n'a pu être vérifiée dans l'article ; les sources secondaires donnent des seuils différents (0,9 / 0,65 / 0,3) |
| Chap. 1, théorème de Wu | (iii) : « si ℓ est unimodale et sous une condition de différentiabilité, la suite converge vers l'unique estimateur du maximum de vraisemblance » | résumé de l'article (Project Euclid) ; (i) et (ii) conformes aux reformulations secondaires du théorème 1 de Wu |
| Chap. 2 | McLachlan et Peel (2000), McLachlan et Krishnan (2008) cités en 2.1 ; Frühwirth-Schnatter (2006) en 2.2 ; Blei et Jordan (2006) dans le périmètre de l'introduction : les 61 entrées sont citées | entrées non citées (P-18) |
| Chap. 2, relecture | affirmation non sourcée sur la vitesse du gradient naturel retirée ; ouverture : plus d'affirmation « les sources ont été consultées » au nom de l'étudiant ; origine « physique statistique » retirée (non présente dans le texte de l'étudiant) ; titres de 2.5.2 et 2.5.3 allégés ; portée des résultats de Dwivedi et al. formulée comme une interprétation | relecture critique |

**Reste à vérifier par l'étudiant** : la condition exacte de convergence de la suite des paramètres dans Wu (1983),
si une version plus précise que (iii) est voulue (article non téléchargeable ici).

## 2026-11-05 : D-15 (tolérance, relances, LDA, régularisation)

| Endroit | Changement | Raison |
|---|---|---|
| Chap. 3, calibrage, points 2 à 4 | tolérance jugée sur le critère final (ARI rapporté, arrêt si aucune valeur) ; grille de régularisation de 0 à 1, valeur au bord signalée ; 20 relances pour toutes les familles et tous les bras, probabilité rapportée par cas | D-15 |
| Chap. 3, niveaux d'inférence de la LDA | « à $\theta$ ponctuel » corrigé en « à $\beta$ ponctuel » ; étape E limitée à 100 itérations par étape M (scikit-learn), borne toujours croissante | coquille ; D-15 |
| Chap. 3, écarts au protocole | écart (7) du 5 novembre 2026 | D-15 |
| Bibliographie | Pedregosa et al. (2011), scikit-learn (déjà cité dans le registre) | D-15 |

## 2026-11-05 : D-16 (régularisation dans le texte, propriétés, Iris)

| Endroit | Changement | Raison |
|---|---|---|
| Chap. 1, propriétés de l'EM (l. 313) | « ε = 10⁻⁶ (constante REG_EM) » remplacé par ε calibré (`reg_covariance`) | texte périmé : ε est calibré depuis la nouvelle chaîne |
| Chap. 1, dégénérescence (l. 865) | même correction | idem |
| Chap. 3, données Iris (l. 996) | limite : ε absolu unique, plus grand que certaines variances d'Iris (valeurs calculées sur le fichier) | D-16, A-16 |
| Chap. 4, validation (l. 1327) | propriétés vérifiées sur l'EM sans régularisation, échecs comptés à part, renvoi au tableau | D-16, A-14 |

## 2026-11-07 : résultats E-02 (D-18)

| Endroit | Changement | Raison |
|---|---|---|
| Pages liminaires | résumé, abstract, liste des abréviations (`liminaires.tex`) | canevas de l'école |
| Chap. 3, tests | sens d'une différence : moyenne quand Hodges-Lehmann est nul | règle du code non écrite |
| Chap. 4, illustrations | 13 cadres remplis depuis les tableaux `ill_*`, `S8_alpha0`, `S9_variance`, `S10_seuil`, `validation_proprietes` ; affirmations périmées corrigées (20 initialisations, K de 1 à 6, 110 graines, vingt répétitions, grille de alpha0, ARI de l'EM à K = 6, composantes de l'EM sous le seuil, N = 2001, plafond atteint par le VB à grand N) | résultats E-02 |
| Chap. 4, scénarios, prix, texte | paragraphes de synthèse | résultats E-02 |
| Chap. 4, analyse | mise en relation avec la littérature (RH2, RH3, RH1/RH4, RH5, HT1), limites des résultats (6 points), perspectives | canevas, résultats |
| Chap. 4, synthèse ; conclusion | bilan chiffré (63 décisions) ; section « Réponses aux hypothèses de recherche » | résultats E-02 |
| Tableaux générés | verdict de HP6-diff corrigé (conforme) ; caractères Unicode | D-18 |

## 2026-11-09 : audit de la session des articles (reprise du travail d'Icare)

Sauvegarde avant modification : `sauvegardes/20261109-011511_avant_audit_b6/`.

| Endroit | Changement | Raison |
|---|---|---|
| Introduction | sections « Contexte » (enjeu réel : Cadre Harmonisé, chocs de prix, seuils du PAM, mêmes sources que le chap. 3) et « Problématique » séparées ; section « Objectifs » ajoutée (objectif général, cinq objectifs spécifiques reliés à RH1 à RH5 et au cas des prix) | canevas : contexte, problématique, hypothèses, objectifs |
| Introduction, périmètre | le modèle de Markov caché est dit traité en théorie seulement (annexe G), sans expérience | le périmètre l'annonçait comme objet d'étude |
| Introduction, thèse | « soupçon méthodique » et « termes bannis » reformulés | ton défensif |
| Chap. 4, introduction | rappel des cinq hypothèses de recherche | canevas, point 1 du chapitre des résultats |
| Chap. 4, bilan et recommandations | phrase après la grille et ouverture des recommandations resserrées ; recommandation de standardiser reliée au cas d'Iris | ton ; contradiction avec Iris non standardisé |
| Chap. 3, validité interne | valeur calibrée de la régularisation précisée (ε = 0,1) | « εI » laissait croire à un ε infinitésimal |
| Chap. 4, discussion critique | précautions réduites à ce qui n'est pas dans la section 3 des limites ; perspectives générales renvoyées à la conclusion (« reprises suggérées par les résultats ») | limites écrites trois fois, perspectives deux fois |
| Conclusion | « Limites du travail » réduite aux limites absentes ailleurs ; perspectives resserrées, avec le critère d'élagage reporté de la discussion ; contributions 1 et 2 fusionnées ; paragraphe final redondant retiré (renvoi à la grille reporté dans les réponses aux hypothèses) | redites ; volume |
| Chap. 1 | prose autour des équations condensée (loi gaussienne univariée, cadre bayésien, interprétation de la KL) ; taxonomie fusionnée avec les exemples ; deux lignes du tableau 1.1 retirées (analyse factorielle, IRT) ; conclusion du chapitre de 669 à environ 250 mots | volume (D-12) ; cours général sans usage dans la suite |
| Volume | corps de la page 1 à la page 112 (bibliographie page 113), contre 114 pages au départ | limite de 112 pages (D-12) |

Restent, après le recalcul D-19 : chiffres de la synthèse du cas des prix, de la discussion de RH3 et des réponses aux hypothèses ; paragraphe sur les épisodes de prix (tableau `prix_episodes`) ; nouvelle mesure du volume.

## 2026-11-09 : résultats recalculés après D-19

| Endroit | Changement | Raison |
|---|---|---|
| Chap. 4, synthèse du cas des prix | couverture du bootstrap EM-BIC 44 % et 78 % (au lieu de 66 % et 82 %), écart au VB chiffré ; phrase « dix fois plus étroit… n'est pas une précision » remplacée : largeurs comparables (0,075 à 0,093 pour le VB, 0,087 à 0,124 pour EM-BIC) | D-19 |
| Chap. 4, cas des prix | paragraphe sur les épisodes datés (tableau `prix_episodes`, figure `prix_carte_alerte`), définitions différentes de la tension (maïs pour EM-BIC, niébé pour le VB) ; limites du cas réduites aux points qui lui sont propres | relais du 09/11 ; redite avec la section 3 des limites |
| Chap. 4, RH3 et littérature | couvertures recalculées ; nuance : sous-couverture aussi à K connu (EM-K) | D-19 |
| Chap. 3, écarts au protocole | point (8) : défaut d'alignement corrigé après les résultats, unités recalculées, verdicts inchangés | transparence |
| Conclusion, RH3 | couverture du bootstrap EM-BIC chiffrée | D-19 |
| Annexe D | ligne du recalcul (instance aarch64, commit `dd538fc`) | traçabilité |

## 2026-11-12 : registre des décisions, seuil d'alerte, guide de décision (D-21)

| Endroit | Changement | Raison |
|---|---|---|
| Chap. 3, cas des prix, « Bras » | définition de l'alerte (P > 0,5) comme règle de Bayes à coûts égaux, seuil général c_FA/(c_FA + c_AM), coûts laissés aux organismes de sécurité alimentaire | le seuil n'était défini que dans deux légendes |
| Chap. 4, recommandations pratiques | guide de décision aligné sur les verdicts : K inconnu (coût total), chevauchement et dimension (VB, HS1, HS5), incertitude (bootstrap d'EM-BIC plutôt que VB, aucun à 90 %), petit effectif (priors, HP7), prévision (gaussienne simple d'abord), seuil d'alerte ; phrase suivant le tableau raccourcie | l'ancien guide recommandait le VB pour l'incertitude, contredit par HP6 |
| Conclusion, limites | point (4) : choix de construction des variables des prix et seuil de 0,5 posés sans alternative testée ; phrase d'introduction des limites condensée | démarche de NERA et MKAN (choix posés déclarés comme tels) |
| Annexe E | tableau « Registre des décisions du cas pratique » (retenu, alternatives, raison, vérification), 17 décisions | idem |
| Chap. 4, synthèse | `\enlargethispage` de deux lignes | corps maintenu à 112 pages (bibliographie page 113) |

Aucun calcul refait (décision de Miguel du 12/11 : plus aucun calcul).

## 2026-11-12 : relecture finale, contrôles automatiques

| Endroit | Changement | Raison |
|---|---|---|
| Chap. 1 et 3, annexe C et G | indices mal convertis depuis Word, imprimés tels quels (« E_q », « I_comp », « a_max », « argmax_θ », « θ̂_MLE », « x_N », « K_effectif ») réécrits en vrais indices ; équation (1.19) en romain | artefacts de conversion visibles dans le PDF |
| Chap. 1 | trois incises dont les tirets avaient disparu (virgule détachée, espace double) remises entre parenthèses | ponctuation cassée |
| Contrôles | journal de compilation sans débordement ni référence indéfinie ; chiffres du texte (cas des prix, scénarios, bilan 31/4/22/6, coût par itération 1,1 à 2,2) retrouvés dans les tableaux ; résumé et abstract concordants | relecture |

## 2026-11-12 : relecture finale, lecture complète (trois relecteurs, corrections vérifiées une à une)

| Endroit | Changement | Raison |
|---|---|---|
| Chap. 1 et annexes F, G | 63 sommes écrites avec la lettre Σ réécrites avec le symbole de somme ; Σ_k ne désigne plus que la covariance | confusion « Σ_k π_k = 1 » lu comme covariance × poids |
| Chap. 1 | indices perdus (θ_enc, ℓ_c, π_K, α_K, σ_D, a_max, R^{D×D}, diag), ELBO et KL en romain et q^{*} dans les équations, « + constante » en romain ; initialisation du VB écrite avec K_max ; ensemble des paramètres variationnels noté 𝓛 (Λ est la précision) ; « estimateurs consistants » ; π_k avec l'indice i | notation cohérente |
| Chap. 1 | renvois corrigés : log-sum-exp (étape E), illustration de la surestimation de K (chap. 4), ligne inexistante « Gestion du risque » retirée ; taux de convergence rapporté à la fraction d'information manquante ; sous-estimation de la variance attribuée à la factorisation et à la KL inverse ; phrase cassée sur l'information de Fisher | renvois faux, formulations inexactes |
| Chap. 3 | équations renumérotées 3.1 à 3.5b (numéros 2.x hérités de l'ancien plan) ; θ̂_K dans BIC et AIC ; renvois (implémentation, comportement numérique, sections de la comparaison) ; orientation des tests par hypothèse corrigée d'après le plan des tests ; nombre de relances (20 pour tous) ; β_k du pLSA ; « Bayes empirique » ; deux phrases qui annonçaient un résultat (Iris, surcoût du VB) rendues méthodologiques | cohérence avec le plan des tests et le registre ; Partie II sans résultats |
| Chap. 4 | 9 équivalences non démontrées sur les 22 décisions non tranchées (au lieu de « la plupart ») ; S3 équivalent au double de la marge seulement à K = 4 et 5 ; renvois S7 et critère approché ; titre K_max ; deux tournures fautives | vérifié dans `decisions_*.tex` et `sensibilite_marges.tex` |
| Annexes | phrase sans verbe de l'annexe E ; « bien que… mais » ; exposant imprimé « ^{α_k-1} » ; α_3(P) = 0,090 ; renvois « ci-dessus » vers la section de l'élagage ; « Cette dernière annexe » | idem |
| Partout | accord féminin de l'ELBO | majorité des occurrences au féminin |

Compilation sans erreur, sans renvoi indéfini ni débordement ; corps à 112 pages (bibliographie page 113).

## 2026-11-13 : introduction recentrée sur le thème (D-26)

| Endroit | Changement | Raison |
|---|---|---|
| Introduction, « Contexte » | paragraphe réécrit : il s'ouvre sur les modèles de mélange et la comparaison EM classique contre EM variationnel (126 mots, au lieu de 179) ; les chiffres du Cadre Harmonisé et du PAM sortent de l'introduction, le cas des prix n'est plus qu'une phrase d'application | l'introduction s'ouvrait sur les prix alimentaires, alors que la question est la comparaison des deux algorithmes ; remarque de Miguel, texte validé |

Références conservées : `giews2026`, `fewsnet2026`, `pam2023bulletin` (citées dans l'introduction et au chapitre 3) ;
`pam2014alps` reste citée au chapitre 3. Chiffres et pagination inchangés (bibliographie page 113). Aucun calcul.

## 2026-11-14 : réduction de concision (D-19)

Mesure : contenu principal de l'introduction à la fin de la conclusion. Avant : pages 1 à 112 (`main.pdf` de v1.5).
Après : pages 1 à 111. Sauvegarde : `sauvegardes/20261114-081345_reduction/`.

| N° | Passage | Modification | Raison | Gain |
|---|---|---|---|---|
| 1 | 4.2.2, 4.2.3, 4.2.4 | fusionnées en « EM à K = 6 imposé et EM variationnel à Kmax = 6 » (étiquettes `sec:res_em_k6`, `sec:res_vb_k6`, `sec:res_partition` conservées) ; toutes les valeurs, le tableau et les deux figures gardés ; retrait de « EM à composantes fragmentées » (contredit par l'ARI de 0,995) et du « constat antérieur » | même expérience racontée trois fois | environ 0,5 page |
| 2 | Ch. 1, quatre paragraphes « Renvois à la grille » | remplacés par une phrase unique au début de 1.7.4 | chaque paragraphe répétait la liste qui le précède | environ 0,4 page |
| 3 | Ch. 1, listes d'avantages et d'inconvénients | monotonie, coût par itération, singularités, lenteur, scalabilité, régularisation, ELBO raccourcis avec renvoi à 1.7.2, 3.5.1, 3.5.2 ; « Convergence rapide loin de l'optimum » fusionné dans le coût par itération ; « Convergence monotone de l'ELBO » fusionné dans le point ELBO ; « Garanties fréquentistes partielles » gardé intact | répétitions entre chapitres 1 et 3 | environ 0,3 page |
| 4 | 4.3.1, 4.3.2, 4.3.3 | titres presque vides regroupés dans l'introduction de 4.3 (étiquettes conservées) | tableaux déjà en annexe H | environ 0,2 page |
| 5 | Conclusion, limites | sept points regroupés en trois, sans en retirer | lisibilité | moins de 0,1 page |

Contrôles : compilation sans erreur ni avertissement LaTeX, aucune référence indéfinie ni multiple, 169 pages au
total ; hypothèses RH1 à RH5, HP4, HP6, HP7, HT1 citées autant de fois qu'avant ; aucun résultat chiffré modifié ;
distinction entre K fixé de l'extérieur (EM) et K estimé par élagage sous l'influence des priors et de Kmax (VB)
conservée (remarque (2) de la section fusionnée, 1.8.4, RH2).

## 2026-11-14 : réduction du total des pages (D-20), étape 1

Objectif de l'étudiant : 120 à 125 pages au total. Avant : 169 pages (PDF complet). Après cette étape : 141 pages,
contenu principal de la page 1 à la page 104. Sauvegarde : `sauvegardes/20261114-090000_reduction_total/`.

| Passage | Modification | Raison | Gain (PDF) |
|---|---|---|---|
| Annexe H | tableaux descriptifs (S1 à S7, S8, `prix_resume`, `prix_ecartes`) et lectures détaillées archivés dans le dépôt (fichiers cités) ; trois figures et sensibilité aux marges gardées | descriptif, reproductible par le code | environ 16 |
| Annexe E | registre complet (9 pages) remplacé par les valeurs calibrées principales (tableau `tab:registre_resume`, lues dans `resultats/calibrage/`) et un renvoi au dépôt ; registre des décisions du cas pratique gardé | détail reproductible | environ 7 |
| Annexe A | coquille de v1.5 corrigée (`\texttt` devenu une tabulation) | erreur | 0 |
| Annexe G | Baum-Welch et son exemple retirés (aucune expérience) ; renvois corrigés (chap. 1, tableau du code, introduction) | hors périmètre expérimental | environ 3 |
| 3.11 | extraits de code retirés (dont `_em_une_fois`, fonction qui n'existe plus) ; renvoi au code exécuté de l'annexe A | redondance et extrait périmé | environ 2 |
| 4.2.5 et S8 | grille S8 fusionnée dans la sous-section sur α0 ; phrase sur un tableau retiré corrigée | même sujet en deux endroits | environ 0,5 |
| 2.5.2 et 2.5.3 | domaines non testés réunis en un paragraphe ; références et tableau 3.1 gardés | revue sans expérience | environ 1 |
| 3.7.4 | description d'ALPS remplacée par un renvoi à 2.5.1 ; « Lien avec la thèse » resserré | répétitions | environ 0,3 |
| 1.2 à 1.5 | rappels de manuel resserrés, sous-sections fusionnées ; toutes les équations (1.1 à 1.11) et le théorème de Jensen gardés | concision | environ 1,5 |
| 3.4 | trois niveaux d'inférence en un paragraphe (tableau 2.2 gardé) ; ligne « Traitement de K » du tableau 2.1 : K fixé à la main ou par critère externe (EM), estimé par élagage sous Kmax et sous l'influence des priors (VB) | redondance avec le tableau ; distinction demandée | environ 0,7 |
| 3.5 | conclusion sur le temps total écrite une seule fois ; stabilité et Cholesky resserrés | répétitions | environ 0,5 |
| 4.2 | introductions des sous-sections (scalabilité, K = 3, ELBO, initialisation, covariance, Iris, aberrations) resserrées | redites du chapitre 1 et de 4.2.2 | environ 1 |
| Liste des abréviations | interligne local 0,92 pour supprimer une page blanche | page vide | 1 |

Gardés intacts : équations, figures, tableaux de décision, bilan des hypothèses, écarts au protocole, rappels
mathématiques (annexe F), garanties théoriques du VB. Compilation : 0 erreur, aucune référence indéfinie.
