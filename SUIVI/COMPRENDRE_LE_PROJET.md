# Comprendre le projet sans lire le mémoire

## 1. Le problème

Un modèle de mélange suppose que les données viennent de plusieurs groupes cachés (par exemple trois nuages de
points). Il faut estimer les paramètres de chaque groupe et, souvent, le nombre de groupes K.

- **L'EM classique** (Dempster, Laird et Rubin, 1977) alterne deux étapes : il calcule pour chaque point la
  probabilité d'appartenir à chaque groupe (étape E), puis réestime les paramètres (étape M). Il donne un seul jeu de
  paramètres et il faut lui imposer K. Pour choisir K, on l'ajuste pour K = 1, 2, ... et on garde le meilleur BIC.
- **L'EM variationnel** (VB, Bishop 2006, section 10.2) met des lois a priori sur les paramètres et donne une loi
  approchée sur ces paramètres, donc une incertitude. Si on lui donne un K trop grand (Kmax), il éteint de lui-même
  les groupes inutiles (élagage).

**Question du mémoire** : que gagne-t-on et que perd-on en passant de l'un à l'autre, et sur quelles preuves ?
**Thèse défendue** : le VB ne bat pas l'EM ; il déplace le choix de K vers le choix des priors et de Kmax, donne une
incertitude approchée, et coûte plus par ajustement.

## 2. Les cinq hypothèses de recherche

| Code | En clair | Comment on la teste |
|---|---|---|
| RH1 | Quand les groupes sont nets, VB et EM-BIC donnent des résultats équivalents | tests d'équivalence sur l'ARI et la log-vraisemblance (scénarios, cas des prix) |
| RH2 | Le K du VB dépend de ses priors au moins autant que celui de l'EM de ses propres choix | S3, HP5 (variance de K̂) |
| RH3 | Les intervalles du VB sont trop étroits | couverture à 90 % sur des données à vérité connue (HP6) |
| RH4 | À petit effectif, le VB dégénère moins que l'EM, grâce aux priors | S6, HP3, HP7, texte (HT1) |
| RH5 | Un VB coûte plus qu'un EM, mais moins que tout le balayage EM-BIC | chronométrage (HP4) |

## 3. Les données

| Données | Rôle | Où |
|---|---|---|
| Jeux synthétiques (S1 à S10) | facteurs isolés : chevauchement, déséquilibre, dimension, petit N, aberrations, priors | générés par `scenarios.py` |
| Iris (150 fleurs, 3 espèces) | première vérification sur données réelles | `data/iris.csv` |
| Prix du PAM au Cameroun (maïs, riz importé, niébé ; 2021 à 2026) | cas pratique : repérer des régimes de tension des prix | `data/prix/wfp_cmr_panier.csv` |
| 20 Newsgroups (4 groupes) | comparaison pLSA (EM) contre LDA (variationnel) | `data/texte/20news-bydate.tar.gz` |

## 4. La chaîne de traitement

```
données ──> calibrage (7 vagues : k-means, tolérance, régularisation, relances,
            priors/LDA/variantes, marges et tailles Monte Carlo, puissance)
              │  écrit resultats/calibrage/*.json  (valeurs « calibrées » du registre)
              ▼
        étapes confirmatoires : validation ─ illustrations ─ chronométrage ─ scénarios ─ prix ─ texte
              │  chaque unité écrite dans resultats/magasin/<étape>/ (reprise exacte après arrêt)
              ▼
        run.py --tables / --figures  ──>  emvb/tex_tables.py  ──>  memoire/tables/*.tex  ──>  latexmk (dans memoire/)
```

Le calibrage doit être fini avant tout le reste : tant qu'un paramètre n'est pas calibré, `run.py` refuse les étapes
confirmatoires.

## 5. Ce qui est acquis, ce qui manque (2026-11-04)

- **Acquis** : la théorie (chapitre 1), le protocole (chapitre 2), le code de toute la chaîne, les données du cas.
- **Manque** : tous les résultats de la nouvelle chaîne. Le calibrage repart sur l'instance cloud (E-01).
- **À corriger avant les calculs** : voir `PLAN_DE_TRAVAIL.md`, lot 1 et lot 2 (marges d'équivalence, nombre de
  réplications, définition de la dégénérescence, unité de calibrage qui bloque tout).

## 6. Carte du code

| Fichier | Rôle | Lancement |
|---|---|---|
| `run.py` (code dans `emvb/cli.py`) | orchestre les étapes, en parallèle, avec reprise | `python run.py [étape]`, `--statut`, `--rapide`, `--tables`, `--figures` |
| `emvb/superviseur.py` | relance `run.py` après un arrêt non voulu | `python -m emvb.superviseur calibrage --inactivite-max 120` |
| `emvb/algorithmes.py` | EM, MAP-EM, VB, ELBO, variantes, LDA, pLSA, métriques | importé |
| `emvb/comparaison.py` | les bras (EM-K, EM-Kmax, EM-BIC, EM-ICL, MAP-EM, VB-emp, VB-diff, VB-cal), règle de K̂ | importé |
| `emvb/statistique.py` | Wilcoxon exact, TOST, Holm, bootstrap, puissance | importé |
| `emvb/hypotheses.py` | RH1 à RH5 et tests déclarés | importé |
| `emvb/parametres.py` | registre des paramètres (valeur, statut, justification) | importé |
| `emvb/calibrage.py` | les sept vagues de calibrage | `python run.py calibrage` |
| `emvb/scenarios.py`, `emvb/etape_prix.py`, `emvb/etape_texte.py`, `emvb/etape_chronometrage.py`, `emvb/etape_validation.py`, `emvb/etape_illustrations.py` | les étapes | `python run.py <étape>` |
| `emvb/persistance.py`, `emvb/etapes.py`, `emvb/progression.py` | magasin, unités, barre de progression | importés |
| `emvb/tex_tables.py`, `emvb/figures.py` | tableaux LaTeX et figures depuis le magasin | `python -m emvb.tex_tables`, `python run.py --figures` |
| `demo/` | application Dash de présentation du cas | `python demo/app.py` |
| `tests/` | tests unitaires | `python -m pytest -q tests` |
| `legacy/` | ancien code (climat, S&P 500, première chaîne) | ne plus utiliser |

## 7. Glossaire

- **ARI** : indice de Rand ajusté, accord entre deux partitions (1 = identiques, 0 = hasard).
- **BIC, ICL** : critères pour choisir K avec l'EM (vraisemblance pénalisée ; l'ICL pénalise aussi le chevauchement).
- **ELBO** : borne inférieure de la log-évidence, le critère que maximise le VB.
- **Élagage** : extinction par le VB des composantes inutiles, pilotée par α0 (prior de Dirichlet).
- **Bras** : une méthode comparée, avec ses réglages (par exemple VB-emp = VB à priors empiriques).
- **TOST** : test d'équivalence (deux tests unilatéraux) ; conclut « équivalent » si la différence est dans ± la marge.
- **Marge d'équivalence** : plus petite différence jugée importante ; en dessous, on parle d'équivalence.
- **Holm** : correction des tests multiples au sein d'une famille d'hypothèses.
- **Couverture** : part des intervalles à 90 % qui contiennent la vraie valeur (90 % attendus).
- **Magasin** : dossier où chaque unité de calcul terminée est enregistrée ; permet la reprise.
- **Unité** : plus petit morceau de calcul indépendant (par exemple un scénario, une réplication).
- **Calibrage** : étape qui fixe les paramètres non mathématiques selon des règles écrites à l'avance.

## 8. Questions probables du jury (à compléter en phase 5)

À compléter quand les résultats existeront.
