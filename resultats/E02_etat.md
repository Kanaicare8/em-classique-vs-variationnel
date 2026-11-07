# E-02 : état des sorties au 07/11/2026, 04:00 UTC (partiel)

Branche `resultats-e02` : sorties de l'instance AWS, sans le magasin (`resultats/magasin/`, 30 Go, ignoré par git).
Code exécuté : `bfcc3ff`, `ICARE_SOUS_TRAVAILLEURS=8` pour les 4 dernières unités de texte (2 jusqu'au 06/11 21:24 UTC).

## Avancement (`python run.py --statut`)

| Étape | Unités |
|---|---|
| calibrage | 590 / 590 |
| validation | 23 / 23 |
| illustrations | 249 / 249 |
| chronométrage | 14 / 14 |
| scénarios | 13 750 / 13 750 |
| prix | 1 653 / 1 653 |
| texte | 50 / 51 (V=3000/N=1000/rep=002 en cours) |

## Ce qui est dans la branche

- `resultats/tables/*.csv` : sorties des étapes finies, écrites par le superviseur. `texte_decisions.csv` n'existe pas encore.
- `resultats/calibrage/*.json`, `resultats/environnement.json`, `resultats/environnement_historique.jsonl`,
  `resultats/statut.json`.
- `resultats/magasin/_journal/erreurs.log.gz` (1,8 million de lignes, 0,5 Mo compressé).

Pas encore produits : `tables/*.csv` et `tables/*.tex` de `run.py --tables` et `tex_tables.py`, figures de
`run.py --figures`. Les dossiers `tables/` et `figures/` de la branche datent toujours du 04/11. La chaîne les produit
à la fin du texte ; la branche sera mise à jour à ce moment-là.

## erreurs.log : analyse

1 047 entrées, toutes `concurrent.futures.process.BrokenProcessPool`. C'est le pool de processus tué pendant une
unité, aucune autre exception n'apparaît. Chaque groupe correspond à une interruption spot ou à une relance :

| Date (UTC) | Étape | Entrées | Cause |
|---|---|---|---|
| 04/11 12:25, 22:13, 23:25 ; 05/11 01:36 | calibrage | 4 | arrêts du calibrage, cause non revérifiée (antérieurs au journal des relances) |
| 05/11 22:40 | calibrage | 8 | interruption spot (relance 22:42) |
| 06/11 08:46 | illustrations | 1 | interruption spot (relance 08:51) |
| 06/11 09:19 | chronométrage | 6 | interruption spot (relance 09:20) |
| 06/11 10:14 et 10:23 | prix | 1 020 | interruptions spot (relances 10:16 et 10:29) |
| 06/11 20:09 | texte | 4 | interruption spot (relance 20:15) |
| 06/11 21:24 | texte | 4 | arrêt voulu pour passer à 8 sous-tâches |

Toutes les unités concernées ont été refaites à la relance : le statut ci-dessus les compte terminées. Aucune erreur
non résolue (critère 2 de la fiche).

**À trancher par toi :** le chronométrage a été interrompu le 06/11 à 09:19 UTC puis relancé. Faut-il refaire ses
mesures dans une machine sans autre interruption ?

## Coût et durée

Départ d'E-02 : 12,87 $ (06/11 08:37 UTC). Au 07/11 02:54 UTC : 16,45 $, soit 3,58 $ engagés pour E-02 jusque-là.
Coût total et durée finale : à la fin de la chaîne.
