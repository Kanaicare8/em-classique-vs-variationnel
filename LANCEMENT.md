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

Données attendues (non versionnées, licences restrictives) :

| Fichier | Source | Remarque |
|---|---|---|
| `data/sp500_fred.csv` | FRED, série SP500 | empreinte SHA-256 vérifiée au chargement |
| `data/climat/cache_D5.pt`, `cache_D20.pt` | WorldClim 2.1 et Köppen-Geiger (Beck et al. 2018) | déjà construits ; sinon `python outils/extraire_cameroun.py` |
| `data/texte/20news-bydate.tar.gz` | 20 Newsgroups « bydate » | archive d'origine, lue sans extraction |
| `data/iris.csv` | Fisher (1936) | versionné |

## 1. Vérifications (quelques minutes)

```powershell
python -m pytest -q tests
python run.py --statut
```

Attendu : `66 passed` (ou plus) ; `--statut` liste les étapes et les paramètres non encore calibrés.

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

Sept vagues enchaînées automatiquement (k-means et variogramme, tolérance, régularisation, relances et HMM,
recherches heuristiques des priors / LDA / variantes, marges et tailles Monte Carlo, puissance). Chaque vague écrit
`resultats/calibrage/<id>.json` (valeurs, règle appliquée, détails). C'est l'étape la plus longue après les scénarios.

Contrôle : `python run.py --statut` doit afficher `paramètres non calibrés : aucun`.

## 4. Calculs confirmatoires et figures

```powershell
python run.py
```

Enchaîne : validation, illustrations, chronométrage (toujours un seul processus, pour des temps sans concurrence),
scénarios, climat, S&P 500, texte, puis les figures. Pour une étape seule : `python run.py scenarios`.
Nombre de processus : `--travailleurs 6` (par défaut, nombre de cœurs moins un).

## 5. Tableaux LaTeX et figures depuis le magasin (sans recalcul)

```powershell
python run.py --tables
python run.py --figures
python tex_tables.py
```

## 6. Ce qu'il faut m'envoyer

1. La sortie de `python run.py --statut`.
2. Le dossier `resultats/tables/` (CSV) et `resultats/calibrage/` (JSON).
3. Le dossier `figures/` (PNG).

Le magasin (`resultats/magasin/`) reste chez vous : il contient tous les ajustements et permet de regénérer
tableaux et figures sans rien recalculer.

## 7. Dépôt GitHub

Le dépôt local a un premier commit ; rien n'a été poussé. Les données sous licence et les PDF d'articles sont
exclus par `.gitignore`. Pour publier :

```powershell
git push -u origin master
```
