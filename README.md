# Comparaison entre l'algorithme EM classique et l'EM variationnel

*Avantages, inconvénients et applications.* Mémoire de Master recherche de **KANA TIODONG Icare Brichel**
(Master of Science en Data Science et Intelligence Artificielle, ENSPD, Université de Douala, 2025-2026), co-encadré
par le Prof. Dr. habil. P. NJIONOU SADJANG (ENSPD) et le Prof. Patrice TAKAM SOH (Université de Yaoundé 1).

Ce dépôt contient le texte du mémoire, le code qui produit chaque tableau et chaque figure, les résultats, et deux
applications. Les étiquettes `v1.0` et `v1.0.1` sont les versions rendues ; la version `v1.1` range le dépôt sans
changer le texte ni les résultats.

## Ce que le mémoire établit

L'EM variationnel ne bat pas l'EM classique : il déplace la sélection du nombre de composantes vers ses
hyperparamètres, régularise par ses priors (le MAP-EM fait de même) et donne des intervalles qu'il ne faut pas lire
comme calibrés. Cinq hypothèses de recherche sont mises à l'épreuve par 63 tests déclarés avant les calculs
(31 conformes, 4 contraires, 22 non tranchés, 6 sans sens prédit), sur dix scénarios synthétiques, sur un cas réel
d'alerte sur les prix alimentaires du Cameroun (données publiques du PAM) et sur une comparaison pLSA contre LDA.

## Où trouver quoi

| Je veux… | Où |
|---|---|
| lire le mémoire | [`memoire/main.pdf`](memoire/main.pdf) (sources dans [`memoire/`](memoire/)) |
| voir la présentation de pré-soutenance et ses notes | [`presentation/`](presentation/) |
| relancer les calculs | [`docs/LANCEMENT.md`](docs/LANCEMENT.md), puis `python run.py --statut` |
| publier une version sur Zenodo | [`docs/GUIDE_ZENODO.pdf`](docs/GUIDE_ZENODO.pdf) (aussi en [Word](docs/GUIDE_ZENODO.docx) et en [Markdown](docs/GUIDE_ZENODO.md)) |
| comprendre une décision méthodologique | [`SUIVI/DECISIONS.md`](SUIVI/DECISIONS.md) (D-00 à D-24), registre en annexe E du mémoire |
| voir ce qui a changé dans le texte | [`SUIVI/CHANGEMENTS_MEMOIRE.md`](SUIVI/CHANGEMENTS_MEMOIRE.md) |
| utiliser le bulletin mensuel des marchés | [`bulletin/`](bulletin/README.md) |
| montrer le cas pratique en soutenance | [`demo/`](demo/app.py) |

## Organisation

```
emvb/             le code du mémoire, un paquet Python
  algorithmes, risque               EM, EM variationnel, MAP-EM, pLSA, LDA, gestion du risque
  comparaison, scenarios            protocole de comparaison et scénarios S1 à S10
  hypotheses, statistique           hypothèses déclarées et tests (TOST, Wilcoxon, Holm, Diebold-Mariano)
  parametres, calibrage             registre des paramètres et calibrage écrit à l'avance
  donnees                           jeux de données (synthétique, Iris, prix du PAM, texte)
  etapes, etape_*, cli, superviseur étapes du calcul, orchestrateur reprenable, relance automatique
  persistance, progression          magasin d'artefacts, journal, barre de progression
  figures, tex_tables               figures et tableaux du mémoire, produits depuis les résultats
  chemins                           emplacements du projet, définis une seule fois
memoire/          sources LaTeX (main, body, introduction, liminaires), bibliographie, tableaux, figures, PDF
data/             données publiques (prix du PAM, Iris) et leur provenance
resultats/        tableaux produits par le code (le magasin d'artefacts n'est pas versionné)
tests/            102 tests unitaires et d'équivalence
demo/             application de démonstration du cas pratique, six pages
bulletin/         bulletin mensuel et saisie de relevés, déployable, avec ses propres tests
scripts/          utilitaires : téléchargement des prix du PAM, contrôle LaTeX, mesures
docs/             mode d'emploi, guide Zenodo, notes d'analyse
presentation/     présentation de pré-soutenance et notes de l'orateur
SUIVI/            journal, décisions, état du projet
references/       sources lues, avec leur provenance
legacy/           anciennes versions du texte et documents périmés, gardés pour mémoire
run.py            point d'entrée : python run.py (équivalent à python -m emvb)
```

## Reproduire

```
pip install -e ".[dev]"              # installe le paquet emvb et pytest (requirements.txt donne les versions figées)
python -m pytest -q                  # 102 tests
python run.py --statut               # avancement de chaque étape, sans rien calculer
python run.py --tables --figures     # tableaux et figures, depuis les résultats déjà calculés
cd memoire && latexmk -pdf main.tex  # le mémoire
```

Un calcul complet est long et se reprend où il s'est arrêté (voir [`docs/LANCEMENT.md`](docs/LANCEMENT.md)). Les graines
sont fixées et l'empreinte SHA-256 de l'extrait de prix est vérifiée au chargement, de sorte que le même code donne
les mêmes chiffres.

## Données

Base de prix du Programme alimentaire mondial pour le Cameroun, diffusée sur HDX (licence CC BY-IGO) : *World Food
Programme, Cameroon - Food Prices, Humanitarian Data Exchange*. L'extrait utilisé et sa provenance sont dans
`data/prix/`.

## Citer

Voir [`CITATION.cff`](CITATION.cff).
