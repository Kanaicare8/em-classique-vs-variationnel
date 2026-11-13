# Comparaison entre l'algorithme EM classique et l'EM variationnel

*Avantages, inconvénients et applications.* Mémoire de Master recherche de **KANA TIODONG Icare Brichel**
(Master of Science en Data Science et Intelligence Artificielle, ENSPD, Université de Douala, 2025-2026), co-encadré
par le Prof. Dr. habil. P. NJIONOU SADJANG (ENSPD) et le Prof. Patrice TAKAM SOH (Université de Yaoundé 1).

Ce dépôt contient le texte du mémoire, le code qui produit chaque tableau et chaque figure, les résultats, et deux
applications. La version finale porte l'étiquette `v1.0`.

## Ce que le mémoire établit

L'EM variationnel ne bat pas l'EM classique : il déplace la sélection du nombre de composantes vers ses
hyperparamètres, régularise par ses priors (le MAP-EM fait de même) et donne des intervalles qu'il ne faut pas lire
comme calibrés. Cinq hypothèses de recherche sont mises à l'épreuve par 63 tests déclarés avant les calculs
(31 conformes, 4 contraires, 22 non tranchés, 6 sans sens prédit), sur dix scénarios synthétiques, sur un cas réel
d'alerte sur les prix alimentaires du Cameroun (données publiques du PAM) et sur une comparaison pLSA contre LDA.

## Où trouver quoi

| Je veux… | Fichier ou dossier |
|---|---|
| lire le mémoire | [`main.pdf`](main.pdf) (sources : `main.tex`, `introduction.tex`, `body.tex`, `liminaires.tex`, `references.bib`) |
| voir la présentation de pré-soutenance et ses notes | [`presentation/`](presentation/) |
| relancer les calculs | [`LANCEMENT.md`](LANCEMENT.md), puis `python run.py --statut` |
| comprendre une décision méthodologique | [`SUIVI/DECISIONS.md`](SUIVI/DECISIONS.md) (D-00 à D-22), registre en annexe E du mémoire |
| voir ce qui a changé dans le texte | [`SUIVI/CHANGEMENTS_MEMOIRE.md`](SUIVI/CHANGEMENTS_MEMOIRE.md) |
| utiliser le bulletin des marchés | [`outil/`](outil/README.md) |
| montrer le cas pratique en soutenance | [`app/`](app/app.py) |

## Organisation

```
algorithmes.py, risque.py, comparaison.py    EM, EM variationnel, MAP-EM, protocole de comparaison
scenarios.py, hypotheses.py, statistique.py  scénarios S1 à S10, hypothèses déclarées, tests (TOST, Wilcoxon, Holm)
etape_*.py, etapes.py, run.py, superviseur.py  étapes du calcul et orchestrateur reprenable
calibrage.py, parametres.py                  calibrage écrit à l'avance et registre des paramètres
donnees.py, figures.py, tex_tables.py        données, figures et tableaux du mémoire
data/            données publiques (prix du PAM, Iris) et leur provenance
resultats/       tableaux produits par le code (le magasin d'artefacts n'est pas versionné)
tables/, figures/, figures_tikz/             tableaux et figures inclus dans le mémoire
tests/           tests unitaires et d'équivalence
app/             application de démonstration du cas pratique (six pages)
outil/           bulletin mensuel et saisie de relevés, déployable (D-20)
outils/          scripts utilitaires (téléchargement des prix du PAM, contrôles LaTeX, mesures)
presentation/    présentation de pré-soutenance et notes de l'orateur
SUIVI/           journal, décisions, état du projet, relais entre sessions
notes/           analyses et contrôles de cohérence
references/      sources lues, avec leur provenance
legacy/          anciennes versions du texte et documents périmés, gardés pour mémoire
```

Les modules Python sont à la racine à dessein : ils s'importent par leur nom, et le mémoire renvoie à ces fichiers
par QR code (annexe A).

## Reproduire

```
pip install -r requirements.txt
python -m pytest tests -q            # tests
python run.py --statut               # avancement de chaque étape, sans rien calculer
python run.py --tables --figures     # tableaux et figures, depuis les résultats déjà calculés
latexmk -pdf main.tex                # le mémoire
```

Un calcul complet est long et se reprend où il s'est arrêté (voir [`LANCEMENT.md`](LANCEMENT.md)). Les graines sont
fixées et l'empreinte SHA-256 de l'extrait de prix est vérifiée au chargement, de sorte que le même code donne les
mêmes chiffres.

## Données

Base de prix du Programme alimentaire mondial pour le Cameroun, diffusée sur HDX (licence CC BY-IGO) : *World Food
Programme, Cameroon - Food Prices, Humanitarian Data Exchange*. L'extrait utilisé et sa provenance sont dans
`data/prix/`.

## Citer

Voir [`CITATION.cff`](CITATION.cff).
