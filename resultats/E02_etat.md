# E-02 : état des sorties au 07/11/2026 (étapes terminées, figures PNG manquantes)

Branche `resultats-e02` : sorties de l'instance AWS, sans le magasin (`resultats/magasin/`, 30 Go, ignoré par git).
Code exécuté : `bfcc3ff`, `ICARE_SOUS_TRAVAILLEURS=2`, puis 8 pour les 4 dernières unités de texte (à partir du
06/11 21:24 UTC ; les résultats ne dépendent pas de ce réglage, `test_identique_bit_a_bit`).

## Avancement (`python run.py --statut`)

| Étape | Unités |
|---|---|
| calibrage | 590 / 590 |
| validation | 23 / 23 |
| illustrations | 249 / 249 |
| chronométrage | 14 / 14 |
| scénarios | 13 750 / 13 750 |
| prix | 1 653 / 1 653 |
| texte | 51 / 51 |

Paramètres non calibrés : aucun. Chaîne terminée le 07/11 à 04:32 UTC (`E-02 TERMINEE` dans `chaine.log`).

## Ce qui est dans la branche

- `tables/*.tex` : 49 tableaux de `tex_tables.py`, dont `decisions_scenarios`, `decisions_prix`, `decisions_texte`,
  `sensibilite_marges`, `environnement`, `registre_parametres`.
- `resultats/tables/*.csv` : sorties des étapes (dont les tableaux de décision).
- `resultats/calibrage/*.json`, `resultats/environnement.json`, `resultats/environnement_historique.jsonl`,
  `resultats/statut.json`.
- `resultats/magasin/_journal/erreurs.log.gz` (1,8 million de lignes, 0,5 Mo compressé).

## Figures : non produites en PNG

`run.py --figures` a échoué pour les 18 figures (fig01 à fig12, prix_marches, prix_selection, prix_alerte,
prix_alerte_mois, prix_decisions, texte_decisions) : « Kaleido requires Google Chrome to be installed ». Chrome n'est
pas installé sur l'instance, supprimée depuis. Les unités du magasin que lisent les figures sont jointes à la branche
(`resultats/magasin/validation`, `illustrations`, `prix/{alerte,reference,complet}.pt`) : les figures se refont sur
n'importe quel poste avec Chrome (`plotly_get_chrome`, puis `python run.py --figures`). Procédure complète :
`SUIVI/EXPERIENCES/E-02_RETOUR.md`. Les PNG de `figures/` dans la branche datent encore du 04/11.

## erreurs.log : analyse

1 047 entrées, toutes `concurrent.futures.process.BrokenProcessPool`. C'est le pool de processus tué pendant une
unité, aucune autre exception n'apparaît. Chaque groupe correspond à une interruption ou à une relance :

| Date (UTC) | Étape | Entrées | Cause |
|---|---|---|---|
| 04/11 12:25, 22:13, 23:25 ; 05/11 01:36 | calibrage | 4 | arrêts du calibrage, cause non revérifiée (antérieurs au journal des relances) |
| 05/11 22:40 | calibrage | 8 | interruption spot (relance 22:42) |
| 06/11 08:46 | illustrations | 1 | interruption spot (relance 08:51) |
| 06/11 09:19 | chronométrage | 6 | interruption spot (relance 09:20) |
| 06/11 10:14 et 10:23 | prix | 1 020 | interruptions spot (relances 10:16 et 10:29) |
| 06/11 20:09 | texte | 4 | interruption spot (relance 20:15) |
| 06/11 21:24 | texte | 4 | arrêt voulu pour passer à 8 sous-tâches |

Aucune entrée après le 06/11 21:24. Toutes les unités concernées ont été refaites : le statut les compte terminées.
Aucune erreur non résolue (critère 2 de la fiche).

**À trancher par toi :** le chronométrage a été interrompu le 06/11 à 09:19 UTC puis relancé. Faut-il refaire ses
mesures ?

## Coût et durée

- Départ d'E-02 : 06/11 08:37 UTC, 12,87 $ engagés sur l'instance.
- Fin : 07/11 04:32 UTC, 16,78 $.
- E-02 : 3,91 $, 19 h 55 de bout en bout (interruptions et relances comprises).
- Budget Icare : 40 $ (D-01).
