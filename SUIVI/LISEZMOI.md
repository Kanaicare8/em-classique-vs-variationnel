# Dossier de suivi du mémoire (point d'entrée)

Mémoire de Master SDIA, ENSPD (Université de Douala), 2025-2026 : « Comparaison entre l'algorithme EM classique et
l'EM variationnel (avantages, inconvénients et applications) », par KANA TIODONG ICARE BRICHEL ; co-encadrants
Prof. P. NJIONOU SADJANG et Prof. P. TAKAM SOH (source : page de titre de `main.tex`).

Ce dossier permet de comprendre tout le travail et chaque décision sans lire le mémoire. Chaque entrée porte un
identifiant : P-xx (point du plan), D-xx (décision), E-xx (expérience).

## Ordre de lecture

| Fichier | À quoi il sert | État |
|---|---|---|
| `LISEZMOI.md` | ce fichier : carte du dossier et état du jour | créé le 2026-11-04 |
| `JOURNAL.md` | une ligne par action, datée | créé le 2026-11-04 |
| `COMPRENDRE_LE_PROJET.md` | le projet expliqué sans le mémoire, carte du code, glossaire | à écrire (phase 1) |
| `ETAT_DU_PROJET.md` | matrice d'avancement et audit de rigueur | à écrire (phases 1 et 2) |
| `PLAN_DE_TRAVAIL.md` | points du plan et leur statut | à écrire (phase 3) |
| `DECISIONS.md` | une fiche par décision de l'étudiant | à écrire ; reprendra les décisions déjà consignées dans `notes/` |
| `NOTES_TECHNIQUES.md` | explications données (concepts, défauts trouvés) | au fil de l'eau |
| `EXPERIENCES/E-xx.md` | une fiche par expérience ou calcul | à la spécification |
| `CANEVAS_ECOLE.md` | plan imposé par l'école (transcription) | créé le 2026-11-04 |
| `CHANGEMENTS_MEMOIRE.md` | modifications du document, par section | créé le 2026-11-04 |

## État du jour (2026-11-04 soir, phase 4 : lots 1 et 2 faits, lot 5 commencé)

Code poussé : `315a21c` (tiers), `9ece8ce` (D-04 à D-06, P-17), `f73142e` (D-07, P-10). À récupérer sur l'instance avant
la vague 6 (E-01, mise à jour 2). Mémoire : corrections factuelles et mathématiques, écarts au protocole déclarés,
lectures de l'ancienne chaîne retirées (`CHANGEMENTS_MEMOIRE.md`). Reste au lot 5 : P-15 (annexes A et D), P-19 et
P-20 (canevas, volume). Lot 6 : P-18 (BibTeX IEEE), P-21 (forme). À vérifier par l'étudiant : Steinley 2004.

1. Document : `main.tex` + `body.tex` (35 224 mots) + `introduction.tex` ; PDF compilé du 27 octobre, 125 pages.
2. Plan actuel : introduction ; partie I (revue, chap. 1 fondements théoriques) ; chap. 2 méthodologie ; chap. 3 résultats et discussion ; conclusion ; bibliographie annoncée IEEE ; annexes A à F.
3. Code : nouvelle chaîne par étapes reprenables (`run.py`, `etape_*.py`, `calibrage.py`, PyTorch) ; anciens scripts dans `legacy/`.
4. Cas pratique retenu le 27 octobre : prix alimentaires du PAM au Cameroun (`etape_prix.py`) ; climat et S&P 500 retirés (`notes/ANALYSE_3_...md`).
5. Calcul : sur une instance cloud (D-01). Elle calibre avec l'ancien code `97dcb95` (climat et S&P 500 encore présents, prix absents) : constat bloquant N-01. D-02 tranchée (option A) : code local commité (`e5eeaf8`) et poussé, GitHub vérifié à jour le 2026-11-04 ; relance par l'étudiant selon `EXPERIENCES/E-01.md`. Le calibrage local (101 / 554) est abandonné.
6. Conséquence (d'après `notes/ANALYSE_3_...md`, à vérifier) : les chiffres du chapitre 3 viennent encore de l'ancienne chaîne.
7. 82 fichiers modifiés ou non suivis par Git depuis le dernier commit (`97dcb95`, 22 octobre).
8. Rien n'a été modifié dans le projet hors de ce dossier `SUIVI/`.
9. Prochaine étape : lecture complète du document, du protocole et du code (phase 1), puis matrice d'avancement.
10. Contraintes (D-01) : dépôt le 22 novembre 2026 ; 112 pages au plus hors annexes (corps actuel : 102 pages) ; budget cloud 40 $, 3,59 $ engagés.
