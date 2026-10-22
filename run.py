"""
================================================================================
ORCHESTRATEUR : python run.py [étapes...] [options]
================================================================================

Exécute les étapes dans l'ordre ; chaque étape exécute ses unités manquantes (en parallèle) puis agrège
ses tableaux. Relancer la même commande après une interruption (erreur, Ctrl+C, coupure de courant)
reprend exactement où le calcul s'était arrêté : les unités terminées sont relues, l'unité interrompue
reprend à son dernier ajustement mémorisé et, dans un long ajustement, à son dernier instantané.

  python run.py                      toutes les étapes
  python run.py calibrage            une étape
  python run.py --statut             avancement de chaque étape, sans rien calculer
  python run.py --rapide             version réduite (magasin séparé : resultats/magasin_rapide)
  python run.py --travailleurs 6     nombre de processus (défaut : nombre de coeurs logiques - 1)
  python run.py --tables --figures   seulement l'agrégation et les figures, depuis le magasin
  --autoriser-provisoire             autorise des valeurs de paramètres non calibrées (essais seulement)

Étapes : calibrage, validation, illustrations, chronometrage, scenarios, climat, sp500, texte.
Le chronométrage s'exécute toujours avec un seul processus (temps mesurés sans concurrence).
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import importlib
import multiprocessing as mp
import os
import sys

import etapes as E
import parametres as PARAM
import persistance as PE
from progression import Barre

ORDRE = ["calibrage", "validation", "illustrations", "chronometrage", "scenarios", "climat", "sp500", "texte"]
MODULES = {"calibrage": "calibrage", "validation": "etape_validation", "illustrations": "etape_illustrations",
           "chronometrage": "etape_chronometrage", "scenarios": "scenarios", "climat": "etape_climat",
           "sp500": "etape_sp500", "texte": "etape_texte"}
CONFIRMATOIRES = {"chronometrage", "scenarios", "climat", "sp500", "texte", "illustrations", "validation"}


def unites_de(etape: str, rapide: bool) -> list[E.Unite]:
    return importlib.import_module(MODULES[etape]).unites(rapide)


def statut(etapes, rapide):
    for e in etapes:
        try:
            us = unites_de(e, rapide)
        except Exception as ex:
            print(f"{e:15s} : non évaluable ({type(ex).__name__}: {ex})")
            continue
        mag = E.magasin(e, rapide)
        faites = sum(mag.existe(u.cle) for u in us)
        print(f"{e:15s} : {faites:5d} / {len(us):5d} unités terminées")
    nc = PARAM.non_calibres()
    print("paramètres non calibrés :", ", ".join(nc) if nc else "aucun")


def executer_etape(etape: str, rapide: bool, travailleurs: int) -> bool:
    unites = unites_de(etape, rapide)
    mag = E.magasin(etape, rapide)
    restantes = [u for u in unites if not mag.existe(u.cle)]
    print(f"\n=== {etape} : {len(unites) - len(restantes)} / {len(unites)} unités déjà faites ; {len(restantes)} à calculer",
          flush=True)
    if etape == "chronometrage":
        travailleurs = 1
    erreurs = []
    if restantes:
        barre = Barre(len(restantes), etape)
        ctx = mp.get_context("spawn")
        attente = list(restantes)
        echouees = set()
        with cf.ProcessPoolExecutor(max_workers=travailleurs, mp_context=ctx) as pool:
            en_cours = {}
            try:
                while attente or en_cours:
                    pretes = [u for u in attente if all(mag.existe(d) for d in u.depend)]
                    bloquees = [u for u in attente if any(d in echouees for d in u.depend)]
                    for u in bloquees:
                        attente.remove(u)
                        echouees.add(u.cle)
                        erreurs.append((u.cle, "dépendance en erreur"))
                        barre.message(f"  ignorée (dépendance en erreur) : {u.cle}")
                    for u in pretes:
                        if PE.arret_demande():
                            break
                        attente.remove(u)
                        en_cours[pool.submit(E.executer_unite, u, rapide)] = u
                    if not en_cours:
                        if attente and not PE.arret_demande():
                            erreurs.append(("?", "dépendances introuvables : " + ", ".join(u.cle for u in attente[:5])))
                        break
                    fini, _ = cf.wait(list(en_cours), return_when=cf.FIRST_COMPLETED)
                    for fu in fini:
                        u = en_cours.pop(fu)
                        try:
                            fu.result()
                        except Exception as ex:
                            erreurs.append((u.cle, f"{type(ex).__name__}: {ex}"))
                            echouees.add(u.cle)
                            barre.message(f"  ERREUR {u.cle} : {type(ex).__name__}: {ex}")
                        barre.avancer(info=u.cle)
                    if PE.arret_demande() and not en_cours:
                        barre.message("  arrêt demandé : unités terminées enregistrées ; relancer la même commande pour reprendre.")
                        break
            except KeyboardInterrupt:
                for f2 in en_cours:
                    f2.cancel()
                raise
        barre.fermer()
    if erreurs:
        print(f"{etape} : {len(erreurs)} unité(s) en erreur ; relancer la commande pour les reprendre.")
        return False
    if PE.arret_demande():
        return False
    importlib.import_module(MODULES[etape]).agreger(rapide)
    print(f"{etape} : agrégation terminée.", flush=True)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("etapes", nargs="*", choices=ORDRE + [[]], default=[])
    ap.add_argument("--rapide", action="store_true")
    ap.add_argument("--travailleurs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--statut", action="store_true")
    ap.add_argument("--tables", action="store_true", help="agréger les tableaux depuis le magasin, sans calcul")
    ap.add_argument("--figures", action="store_true", help="produire les figures depuis le magasin, sans calcul")
    ap.add_argument("--autoriser-provisoire", action="store_true")
    a = ap.parse_args()
    if a.rapide:
        os.environ["ICARE_RAPIDE"] = "1"          # calibrage d'essai séparé (hérité par les processus de travail)
    choix = a.etapes or ORDRE
    if a.statut:
        statut(choix, a.rapide)
        return
    if a.tables or a.figures:
        for e in choix:
            if a.tables:
                importlib.import_module(MODULES[e]).agreger(a.rapide)
        if a.figures:
            importlib.import_module("figures").produire(a.rapide)
        return
    PE.installer_arret_propre()
    for e in choix:
        if e in CONFIRMATOIRES and not a.autoriser_provisoire:
            nc = PARAM.non_calibres()
            if nc:
                sys.exit(f"Étape {e} refusée : paramètres non calibrés ({', '.join(nc)}). "
                         "Lancer d'abord  python run.py calibrage  (ou --autoriser-provisoire pour un essai).")
        if not executer_etape(e, a.rapide, a.travailleurs):
            sys.exit(1)
    if not a.etapes:
        importlib.import_module("figures").produire(a.rapide)


if __name__ == "__main__":
    main()
