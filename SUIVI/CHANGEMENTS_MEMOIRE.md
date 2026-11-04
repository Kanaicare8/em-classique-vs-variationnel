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
