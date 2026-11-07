# E-02 : retour de l'instance et instructions pour l'assistant (07/11/2026)

Destinataire : l'assistant IA qui suit ce dépôt pour KANA TIODONG ICARE BRICHEL. Ce fichier accompagne la branche
`resultats-e02`, poussée par MOUKOKO EKAMBI GEORGES MIGUEL depuis la session qui a fait tourner l'instance AWS. Lis-le en
entier avant de toucher au dépôt. Les décisions restent à Icare : tu prépares, tu vérifies, tu lui soumets.

## 1. Ce qui s'est passé

- Instance AWS c8g.8xlarge (32 coeurs, spot), code `bfcc3ff` (main), commande de la fiche `E-02.md` lancée par
  `superviseur.py validation illustrations chronometrage scenarios prix texte --inactivite-max 360`.
- Début : 06/11/2026 08:37 UTC (12,87 $ déjà engagés). Fin : 07/11/2026 04:32 UTC (16,78 $). E-02 : 3,91 $ et 19 h 55,
  interruptions comprises. Budget du projet : 40 $ (D-01).
- L'instance a été supprimée le 07/11 après la fin, à la demande de Miguel. Le magasin complet (30 Go) reste copié
  sur S3, dans un compte de Miguel auquel Icare n'a pas accès : le demander à Miguel si une unité manque.

## 2. Contenu de la branche `resultats-e02`

| Chemin | Contenu |
|---|---|
| `tables/*.tex` | 49 tableaux écrits par `tex_tables.py` à la fin de la chaîne |
| `resultats/tables/*.csv` | sorties CSV des étapes (la fiche les annonce dans `tables/`, elles sont ici) |
| `resultats/calibrage/*.json` | calibrage E-01 (inchangé depuis `7782ae6`, fins de ligne seulement) |
| `resultats/environnement.json`, `resultats/environnement_historique.jsonl` | annexe D |
| `resultats/statut.json` | statut des unités |
| `resultats/magasin/_journal/erreurs.log.gz` | journal des erreurs, compressé (1,8 million de lignes) |
| `resultats/magasin/{validation,illustrations}/`, `resultats/magasin/prix/{alerte,reference,complet}.pt` | les seules unités du magasin que lisent les figures (4,6 Mo), ajoutées malgré le `.gitignore` |
| `resultats/E02_etat.md` | état détaillé, analyse du journal d'erreurs, coût et durée |
| `SUIVI/EXPERIENCES/E-02_RETOUR.md` | ce fichier |

Rien d'autre n'a changé : aucun fichier de code, aucun texte du mémoire, aucun fichier de `SUIVI/` hors de celui-ci.

## 3. Critères de réussite de la fiche E-02

1. **Toutes les unités faites : oui.** calibrage 590/590, validation 23/23, illustrations 249/249, chronométrage 14/14,
   scénarios 13 750/13 750, prix 1 653/1 653, texte 51/51 ; paramètres non calibrés : aucun (`resultats/statut.json`).
2. **Journal d'erreurs sans erreur non résolue : oui.** 1 047 entrées, toutes `BrokenProcessPool` (pool tué par une
   interruption spot ou une relance), toutes refaites ensuite. Détail par date dans `resultats/E02_etat.md`.
3. **`tex_tables.py` sans tableau « à générer » : à confirmer.** La chaîne a écrit 49 tableaux et le journal de la chaîne
   ne contient aucune ligne « à générer ». Vérifie-le toi-même (section 5, étape 3).
4. **Coût sous le budget : oui** (16,78 $ sur 40 $).

## 4. Écarts et points ouverts, à soumettre à Icare

1. **Sous-tâches du texte.** D-17 a validé `ICARE_SOUS_TRAVAILLEURS=2`. Le 06/11 à 21:24 UTC, il ne restait que 4 unités
   de texte et 8 coeurs sur 32 travaillaient ; Miguel a fait passer la valeur à 8 pour ces 4 unités (V=1500/N=1000/rep=001,
   V=3000/N=1000/rep=000 à 002). Le code annonce des résultats identiques bit à bit quel que soit ce réglage
   (`tests/test_texte_sous_taches.py::test_identique_bit_a_bit`), mais le test ne vérifie pas la valeur 8 elle-même.
   À consigner dans `DECISIONS.md` si Icare l'accepte.
2. **Chronométrage interrompu.** L'étape a été coupée par une interruption spot le 06/11 à 09:19 UTC, puis relancée à
   09:20 ; les unités en cours ont été refaites. Question pour Icare : les mesures de temps sont-elles acceptables, ou
   faut-il refaire le chronométrage sur une machine sans interruption ?
3. **Figures PNG non produites.** `run.py --figures` a échoué pour les 18 figures : Kaleido (export PNG de Plotly) exige
   Google Chrome, absent de l'instance. Les PNG de `figures/` datent encore du 04/11, et `prix_marches.png`,
   `prix_selection.png`, `prix_alerte.png`, `prix_alerte_mois.png`, `prix_decisions.png`, `texte_decisions.png` n'existent
   pas : `body.tex` les inclut, la compilation échouera tant qu'ils manquent. Correction : section 5, étape 4.

## 5. Ce que tu dois faire, dans l'ordre

Travaille dans un dossier propre et ne pousse rien sur `main` sans l'accord d'Icare.

1. **Récupérer la branche.**
   ```bash
   git fetch origin
   git switch resultats-e02          # ou : git worktree add ../icare-e02 resultats-e02
   git log --oneline -3              # attendu : commits « E-02 ... » au-dessus de bfcc3ff
   ```
2. **Vérifier le code et les tests** (environnement de `requirements.txt`, `PYTHONUTF8=1`) :
   ```bash
   python -m pytest -q tests         # attendu : tout passe (88 tests sur l'instance)
   ```
3. **Vérifier les tableaux.**
   ```bash
   python tex_tables.py              # relit resultats/tables/*.csv ; attendu : aucun tableau « à générer » pour le
                                     # chapitre 4 et l'annexe D
   git status --short tables         # attendu : aucune différence avec les .tex de la branche
   ```
   Si un tableau diffère, ne corrige rien à la main (P-12) : signale-le à Icare avec le nom du tableau.
4. **Produire les figures PNG.** Elles ne lisent que les tableaux CSV et les unités du magasin jointes à la branche.
   ```bash
   pip install -r requirements.txt   # plotly et kaleido
   plotly_get_chrome                 # installe un Chrome pour Kaleido, sauf si Chrome est déjà installé
   python run.py --figures           # n'agrège rien, ne relance aucun calcul
   ```
   Attendu : 18 figures dans `figures/` (fig01 à fig12, prix_marches, prix_selection, prix_alerte, prix_alerte_mois,
   prix_decisions, texte_decisions) et aucune ligne « figures manquantes ». N'utilise pas `--tables` : l'agrégation
   relirait tout le magasin, absent ici, et écraserait les CSV.
   Puis vérifie à l'oeil chaque PNG (étiquettes, légendes, axes) avant de les committer sur la branche.
5. **Compiler le mémoire** (`main.tex`) et vérifier que les 49 tableaux et les 18 figures s'affichent, sans référence
   indéfinie.
6. **Mettre à jour le suivi**, selon les règles du dossier `SUIVI/` :
   - `EXPERIENCES/E-02.md`, section « Résultats obtenus » : statut, critères 1 à 4 ci-dessus, coût 3,91 $, durée
     19 h 55, renvoi vers `resultats/E02_etat.md` ;
   - `JOURNAL.md` : une ligne datée pour la réception et une pour les figures ;
   - `DECISIONS.md` : seulement après la réponse d'Icare sur les points 4.1 et 4.2 ;
   - `LISEZMOI.md`, « État du jour » : E-02 terminée, lot 4 (résultats dans le mémoire) à commencer.
7. **Soumettre à Icare** : le résumé des vérifications, les deux questions de la section 4, la liste des figures
   produites. Après son accord, fusionne `resultats-e02` dans `main` (fusion normale, jamais de push forcé).
8. **Lot 4.** Les chiffres du chapitre 4 et de l'annexe D viennent uniquement des tableaux et figures produits
   (P-12) : aucun nombre saisi à la main.

## 6. Ce qu'il ne faut pas faire

- Ne pas relancer d'étape de calcul (`run.py` sans `--figures`, `superviseur.py`) : le magasin complet n'est pas là,
  le calcul repartirait de zéro.
- Ne pas modifier les CSV ni les `.tex` à la main.
- Ne pas supprimer `resultats/magasin/` de la branche : les figures en ont besoin.
- Ne pas pousser directement sur `main` sans l'accord d'Icare.
