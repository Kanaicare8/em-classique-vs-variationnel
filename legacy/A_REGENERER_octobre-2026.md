# Régénérer tous les résultats et le mémoire

Aucun nombre des tableaux n'est saisi à la main : `tex_tables.py` les écrit dans `tables/` à partir de `resultats/`.
Tous les calculs ci-dessous ont été exécutés les 13 et 14 octobre 2026 (journaux dans `logs/`).

Ordre d'exécution (depuis la racine) :

1. `python -m pytest tests -q` : 17 tests unitaires.
2. `python main.py` (environ 7 minutes, seul sur la machine pour les temps de la section 2.3.6).
3. `python scenarios.py S1` … `S10` (un processus par scénario, `OMP_NUM_THREADS=1` ; S7 se découpe avec la variable `S7_PROPS=0.01`, `0.05`, `0.10`), puis `python scenarios.py --fusionner` (ou `--regrille` pour recalculer les décisions depuis les fichiers bruts).
4. Cas climatique :
   - `python cas_pratique_climat.py --preparer` (WorldClim 2.1 ; usage académique, redistribution interdite : ne pas déposer les rasters) ;
   - contour du pays : `python outils/extraire_cameroun.py` (Natural Earth, domaine public) ;
   - Köppen–Geiger : Beck_KG_V1.zip, figshare 6396959 (licence CC BY 4.0 sur la notice figshare) ;
   - calculs (par parties, effectifs en parallèle) : `--partie sous --effectifs 30,60,120,500 --R 40`, `--partie sous --effectifs 2000 --R 40`, `--partie sous --effectifs complet`, `--partie semi --effectifs 30,60,120 --Rsemi 60 --B 50`, `--partie semi --effectifs 500,2000 --Rsemi 60 --B 50`, `--partie sens`, `--partie cartes`, `--d19 --partie sous --effectifs 120|500|2000 --R 20`, puis `--d19 --partie fusion` et `--partie fusion` ;
   - arguments communs : `--koppen data/climat/koppen/Beck_KG_V1_present_0p0083.tif --frontiere data/climat/frontiere/cameroun.shp` ;
   - cartes en PNG : `python figures_climat.py`.
5. `python cas_pratique.py` puis `python cas_pratique_sp500_complement.py` (B = 1000).
6. `python texte_plsa_lda.py`.
7. `python -c "import main; main.exporter_figures()"` (copie des PNG vers `figures/`), `python tex_tables.py`, `python outils/lint_tex.py`, `python controle_chiffres.py`.
8. `pdflatex main.tex` trois fois (aucune référence indéfinie, aucun label dupliqué à la dernière compilation).

## Écarts au plan, à déclarer
- Cas climatique : 40 sous-échantillons par effectif (au lieu de 100), 60 jeux semi-synthétiques par effectif et 15 à N = 2000 (au lieu de 200), 50 réplicats de bootstrap pour la couverture (au lieu de 100 prévus pour le bootstrap, 100 par effectif pour la couverture), extension D = 20 (19 variables bioclimatiques et l'altitude) avec 20 sous-échantillons pour N = 120, 500, 2000 seulement. Raison : durée de calcul sur une seule machine.
- Zones agro-écologiques officielles : aucun shapefile trouvé, référence Köppen–Geiger seule.
- Texte : 10 réplications par taille ; la LDA du code lisse β (1e-3), le pLSA non.
- Les temps des scénarios et du cas climatique sont mesurés avec plusieurs processus simultanés : ils ne se comparent qu'au sein d'un même run.

## Reste à faire (non automatisable)
- Étiquette Git et DOI Zenodo (annexe A) : aucun commit n'a été possible (le hook de commit refuse le compte courant).
- Validation agronomique des cartes par un expert ; recherche d'un zonage agro-écologique officiel (IRAD, FAO GeoNetwork, HDX).
- Licences à confirmer avant tout dépôt public : carte Köppen–Geiger (la page gloh2o.org est contradictoire entre CC BY 4.0 et CC BY-NC 4.0 pour la version 3 ; la notice figshare de la version 1 indique CC BY 4.0), fichier S&P 500 (S&P Dow Jones Indices).

## Fichiers de modification du mémoire (historique)
`outils/patch_*.py` ont servi à réviser `body.tex` (copie avant révision : `legacy/body_v7_avant_revision.tex`). Ne pas les relancer.
