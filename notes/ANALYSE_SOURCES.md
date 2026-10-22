# Confrontation du plan de travail avec les sources (22 octobre 2026)

Le plan proposé (4 axes d'enrichissement, Parties 1 et 2 en 4 chapitres) a été vérifié point par point dans les 14 PDF de l'espace de travail, désormais rangés dans `references/` (voir `references/SOURCES.md`, S13 à S25). Une affirmation n'est reprise dans `body.tex` que si elle figure dans une source lue ; sinon elle est corrigée, ou bien marquée « cité d'après ... ; non consulté ».

## 1. Affirmations du plan : verdict

| Affirmation du plan | Verdict | Ce que dit la source |
|---|---|---|
| Dwivedi et al. (2018, 2020) : sur-spécification, π ≠ 1/2 en O((d/n)^1/2), π = 1/2 en O((d/n)^1/4) | **Exact, mais seulement pour 2020** | Les taux sont dans Dwivedi et al. (2020, Ann. Statist.). Ils valent pour un modèle très contraint : mélange symétrique ±θ, poids et variance **connus**, données N(0, σ²I). L'article de 2018 (NeurIPS) traite la **sous**-spécification. |
| « Ralentissement logarithmique » dans le cas équilibré | **Faux** | Dans le cas équilibré, c'est le cas *déséquilibré* qui converge en O(log(n/d)) itérations. Le cas équilibré demande O((n/d)^1/2) itérations ; l'EM de population demande ≍ log(1/ε)/ε² itérations, soit une convergence « exponentiellement plus lente ». |
| La matrice de Fisher « devient singulière » | **À nuancer** | Les auteurs disent qu'elle *peut* l'être ; le lien entre singularité et taux est donné comme une justification heuristique (annexe D). |
| Sous-spécification : convergence vers la projection KL, « population EM » géométrique | **Exact, avec conditions** | Dwivedi et al. (2018) : univarié, variance connue, vrai mélange à 3 composantes ajusté à 2, initialisation convenable ; EM empirique à O(n^-1/2) de la projection. |
| Wang et Blei (2019), « CONVERGENCE RATES... » | **Mauvaise attribution** | Le PDF est **Zhang et Gao (2020)**, Ann. Statist. 48(4). Wang et Blei (2019, JASA) n'y est que cité (réf. [36]) ; il n'est pas dans l'espace de travail. |
| Zhang et Gao donnent la consistance du champ moyen pour notre VB | **Non** | Le taux est la somme de deux termes, celui du posterior exact et l'erreur variationnelle. Le résultat porte sur une famille définie sur les paramètres, sans facteur q(Z), et pour les mélanges il concerne l'estimation de densité (Hellinger). Il ne s'applique pas tel quel au VB du texte. Le résultat le plus proche du GMM est Wang et Titterington (2005, 2006), cités par Blei et al. (2017, §5.2). |
| Attias (2000) / Corduneanu et Bishop : élagage par E[log π_k] | **Faux pour Corduneanu et Bishop** | Corduneanu et Bishop (2001) n'ont **pas** de Dirichlet sur π : π est estimé ponctuellement (type II), et l'élagage se fait par π_k → 0 (Bishop 2006, éq. 10.83). Le mécanisme par E[log π_k] est celui de Bishop (2006, §10.2). Attias (2000) n'est pas dans l'espace de travail. |
| Neal et Hinton (1998) : l'EM est le VB avec q(θ) = Dirac | **Pas dans l'article** | Neal et Hinton gardent θ ponctuel : F(P̃, θ) = E[log P] + H(P̃) = L(θ) − KL (éq. 2 et 3, lemmes 1 et 2). Leur seule restriction à des masses ponctuelles porte sur P̃, la loi des latentes (§6 : « winner-take-all », k-moyennes). Le passage à la Dirac sur θ est un raisonnement du texte (§2.1.1). |
| Blei et al. (2018) | **Date** | Article publié dans JASA en 2017 (vol. 112) ; 2018 est la date de la version arXiv v9. |
| SVI : variables locales et globales, gradient naturel, mini-lots, millions de documents | **Exact** | Hoffman et al. (2013) : 350 000 articles de *Nature*, 1,8 M du *New York Times*, 3,8 M de Wikipédia. Le pas ρ_t = (t + τ)^-κ, avec κ ∈ (0,5 ; 1], correspond exactement à `svi_gmm`. |
| VAE : inférence amortie, reparamétrisation | **Exact** | Avec une limite pour le GMM : la reparamétrisation suppose des latentes **continues**, alors que z est discret. |
| Flux normalisants planaires et radiaux contre la rigidité du champ moyen | **Exact** | Log-déterminant en O(D) pour les flux planaires. Les auteurs parlent d'approcher le vrai posterior « dans le régime asymptotique ». |
| LDA : θ_d, z_dn locaux et β_k global | **Exact pour la LDA lissée seulement** | Dans la LDA de base (Blei et al., 2003, §5.3), β est un paramètre ponctuel (niveau 2). Il ne devient aléatoire, et donc variable globale, que dans la version lissée (§5.4), reprise par Hoffman et al. (2013). |
| Acerbi et Székely : backtest de l'ES | **Exact, déjà intégré** | Z1 et Z2 sont implémentés dans `risque.py`. |
| Plan : 4 chapitres (EM, VI, typologie, protocole) | **Non appliqué tel quel** | Voir §3. |

## 2. Ce qui a été modifié dans `body.tex`

Une copie avant modification est dans `legacy/body_v8_avant_sources.tex`.

| Axe du plan | Emplacement | Modification |
|---|---|---|
| Structure | Avant les ch. 1, 2 et 3 | Trois `\part` : revue de la littérature, méthodologie et confrontation, applications |
| 1.3 Mauvaise spécification | §1.6.3.d (nouvelle) | Sur-spécification (Dwivedi 2020), sous-spécification (Dwivedi 2018), portée et limites pour l'EM-Kmax et les cas réels |
| 2.2 Élagage | §1.7.1, §1.7.4 | Corduneanu et Bishop corrigé (π ponctuel, variante hybride niveaux 2 et 3) ; terme ln K! (Bishop §10.2.4) |
| 2.3 SVI, VAE, flux | §1.7.7 réécrite | Contenu tiré des articles ; ce qui est implémenté (`svi_gmm`) et ce qui ne l'est pas ; limites pour le GMM |
| 2.3 Garanties fréquentistes | §1.7.9, item réécrit | Wang et Titterington (cités), Zhang et Gao (2020), Wang et Blei (cité) ; portée exacte |
| 3.2 Neal et Hinton | §2.1, §2.1.1 | Attribution corrigée ; nouveau titre « De l'énergie libre de Neal et Hinton au cas limite de Dirac » |
| 3.1 LDA | §3.1 (pLSA contre LDA) | Bayes empirique (§5.3), LDA lissée (§5.4), local/global selon Hoffman ; conséquence pour la comparaison |
| Conclusion du ch. 1 | §1.8 | « Lever les limites » remplacé par « les déplacer » (thèse), renvois aux nouveaux résultats |
| Grille axe × preuve | `tex_tables.py`, `tables/grille_axe_preuve.tex` | 3 lignes « non testé » : taux en sur-spécification, cible en sous-spécification, consistance des paramètres du VB |
| Bibliographie | 43 → 51 entrées | Dwivedi 2018 et 2020, Zhang et Gao 2020 ; Balakrishnan 2017, Chen 1995, Wang et Titterington 2005 et 2006, Wang et Blei 2019 marqués « non consulté » |

## 3. Pourquoi les chapitres n'ont pas été redécoupés en 4

Le texte contient 165 renvois de section écrits en dur (« section 1.7.4 », « §2.3.13 »...), en plus de ceux de `tex_tables.py`, des légendes et des tableaux générés. Séparer le chapitre 1 en deux (EM, puis VI) et le chapitre 2 en deux (typologie, puis protocole et résultats) renumérote presque tout. Le plan est donc réalisé par les Parties et par les ajouts ci-dessus, et chaque axe a désormais un emplacement :

| Plan | Texte actuel |
|---|---|
| Ch. 1 (1.1 à 1.3) | §1.6 (1.6.1 à 1.6.3.d, 1.6.8) |
| Ch. 2 (2.1 à 2.3) | §1.5, §1.7 (1.7.3, 1.7.4, 1.7.7, 1.7.9) |
| Ch. 3 (3.1, 3.2) | §2.1 (2.1.1 à 2.1.3) et §3.1 (LDA) |
| Ch. 4 (4.1 à 4.3) | §2.2, §2.3, §3.1.4 |

Le redécoupage reste possible : il faudrait passer les renvois en `\label`/`\ref`, puis déplacer les blocs. C'est un chantier à part entière.

## 4. À faire de ton côté

1. Compiler `main.tex` (trois passes) et vérifier : pages de Partie, table des matières, absence de référence indéfinie.
2. Relire §1.6.3.d, §1.7.7 et l'item « Garanties fréquentistes partielles » de §1.7.9.
3. Si tu veux citer Wang et Blei (2019), Attias (2000) ou Balakrishnan et al. (2017) comme appuis, et non comme simples renvois, ajoute les PDF dans `references/`.
