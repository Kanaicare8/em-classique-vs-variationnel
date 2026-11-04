# Lancement des calculs

Toutes les commandes se lancent depuis le dossier du projet, dans PowerShell. Chaque commande peut être interrompue
(Ctrl+C, coupure, erreur) et **relancée telle quelle** : les unités terminées sont relues depuis le magasin
(`resultats/magasin/`), l'unité interrompue reprend à son dernier ajustement mémorisé et, dans un long ajustement, à son
dernier instantané. Rien n'est recalculé deux fois.

Une barre de progression par étape affiche le nombre d'unités faites, le temps écoulé et le temps restant estimé.

## 0. Préparation (une fois)

```powershell
$env:PYTHONUTF8 = "1"                      # accents corrects dans la console
pip install -r requirements.txt
```

Données :

| Fichier | Source | Remarque |
|---|---|---|
| `data/prix/wfp_cmr_panier.csv` | PAM, base de prix du Cameroun (HDX, CC BY-IGO) | **versionné** ; empreinte SHA-256 vérifiée au chargement ; recréé par `python outils/telecharger_prix_wfp.py` (provenance dans `data/prix/PROVENANCE.txt`) |
| `data/texte/20news-bydate.tar.gz` | 20 Newsgroups « bydate » | non versionné ; archive d'origine, lue sans extraction |
| `data/iris.csv` | Fisher (1936) | versionné |

Les cas climatique et S&P 500 des versions précédentes ont été retirés du mémoire et de la chaîne de calcul ; leur
code est conservé dans `legacy/`.

## 1. Vérifications (quelques minutes)

```powershell
python -m pytest -q tests
python run.py --statut
```

Attendu : `74 passed` (ou plus), aucun échec ; `--statut` liste les étapes et les paramètres non encore calibrés.

## 2. Essai complet réduit (magasin séparé, ne touche pas aux résultats réels)

```powershell
python run.py --rapide --autoriser-provisoire
```

Tout passe par `resultats/magasin_rapide/`, `resultats/calibrage_rapide/`, `resultats/tables_rapide/` et
`figures/rapide/`. Cet essai sert seulement à vérifier que toute la chaîne tourne de bout en bout sur votre machine.
**Envoyez-moi la sortie si une unité est en erreur** (le message `ERREUR <unité> : ...` suffit).

## 3. Calibrage (avant tout calcul confirmatoire)

```powershell
python run.py calibrage
```

Sept vagues enchaînées automatiquement (k-means, tolérance, régularisation, relances,
recherches heuristiques des priors / LDA / variantes, marges et tailles Monte Carlo, puissance). Chaque vague écrit
`resultats/calibrage/<id>.json` (valeurs, règle appliquée, détails). C'est l'étape la plus longue après les scénarios.

Contrôle : `python run.py --statut` doit afficher `paramètres non calibrés : aucun`.

## 4. Calculs confirmatoires et figures

```powershell
python run.py
```

Enchaîne : validation, illustrations, chronométrage (toujours un seul processus, pour des temps sans concurrence),
scénarios, prix (cas pratique), texte, puis les figures. Pour une étape seule : `python run.py scenarios`.
Nombre de processus : `--travailleurs 6` (par défaut, nombre de cœurs moins un).

## 4 bis. Calculs longs sans surveillance (recommandé)

```powershell
python superviseur.py --inactivite-max 120
python superviseur.py calibrage                         # mêmes arguments que run.py
```

Le superviseur relance `run.py` après tout arrêt non voulu (plantage, processus tué, manque de mémoire, blocage
détecté) avec une pause croissante, au plus 10 fois (`--relances`). Il s'arrête sans relancer si le calcul est
terminé, si vous appuyez sur Ctrl+C (arrêt propre, code 3) ou si la configuration est refusée (code 2).
`run.py` bloque la mise en veille de Windows pendant le calcul. Diagnostic : `resultats/magasin/_journal/erreurs.log`
(trace complète de chaque erreur) et `superviseur.log`.

Après une coupure de courant ou un redémarrage, pour que le calcul reprenne seul à l'ouverture de session :

```powershell
schtasks /Create /SC ONLOGON /TN "Icare-reprise" /TR "cmd /c cd /d \"$PWD\" && python superviseur.py >> resultats\superviseur_console.txt 2>&1"
schtasks /Delete /TN "Icare-reprise" /F                 # quand tout est terminé
```

## 5. Tableaux LaTeX et figures depuis le magasin (sans recalcul)

```powershell
python run.py --tables
python run.py --figures
python tex_tables.py
pdflatex main.tex; pdflatex main.tex; pdflatex main.tex
```

`tex_tables.py` écrit les tableaux **et les lectures factuelles** des décisions (`tables/lecture_*.tex`) : chaque
décision est rattachée à son hypothèse de recherche (RH1 à RH5) avec son verdict (conforme, contraire, non tranché).
Le mémoire les inclut par `\lectureGeneree{...}` dans la partie III ; rien n'est saisi à la main.

## 5 bis. Application de présentation du cas pratique (soutenance)

Application Dash dans `app/` : quatre pages (données, régimes, alerte, résultats du mémoire), figures Plotly
interactives (zoom, déplacement, sélection, rotation 3D, dessin, export PNG ; bouton « Agrandir » pour le plein écran).

```powershell
python app/precalcul.py --rapide      # essai : environ 25 minutes sur ce poste
python app/precalcul.py               # paramètres du registre : plus long (1000 bootstrap, 4000 tirages), à lancer la veille
python app/app.py                     # puis ouvrir http://127.0.0.1:8050
```

* Le précalcul exécute les unités officielles `reference` et `alerte` de `etape_prix.py` dans `resultats/app/`
  (magasin séparé) : le magasin confirmatoire n'est jamais touché. Il est reprenable comme `run.py`.
* Tant que des paramètres ne sont pas calibrés, les pages 2 et 3 affichent un bandeau « chiffres exploratoires ».
  Après le calibrage : supprimer `resultats/app/`, relancer `python app/precalcul.py` ; mêmes graines, mêmes paramètres,
  donc mêmes valeurs que le calcul confirmatoire.
* La page 4 lit le magasin confirmatoire et `resultats/tables/` (lecture seule) ; elle se remplit après `python run.py`
  puis `python run.py --tables --figures`.
* **Le jour de la soutenance** : lancer `python app/app.py` avant l'arrivée du jury (PyTorch met deux à quatre minutes
  à se charger sur ce poste), attendre « Prêt », ouvrir le navigateur. La carte utilise un fond CARTO (internet requis).

## 6. Ce qu'il faut m'envoyer

1. La sortie de `python run.py --statut`.
2. Le dossier `resultats/tables/` (CSV) et `resultats/calibrage/` (JSON).
3. Le dossier `figures/` (PNG).

Le magasin (`resultats/magasin/`) reste chez vous : il contient tous les ajustements et permet de regénérer
tableaux et figures sans rien recalculer.

## 7. Dépôt GitHub

La branche de travail est `main`, qui suit `origin/main`. Les données sous licence et les PDF d'articles sont
exclus par `.gitignore`. Pour publier :

```powershell
git push origin main
```
