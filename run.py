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
  --tentatives 3                     relances d'une unité dont le processus a planté (mémoire, erreur système)

Étapes : calibrage, validation, illustrations, chronometrage, scenarios, prix, texte.
Le chronométrage s'exécute toujours avec un seul processus (temps mesurés sans concurrence).

Protections : la mise en veille de Windows est bloquée pendant le calcul ; un processus de travail qui
meurt (BrokenProcessPool) est remplacé et ses unités relancées ; une unité dont le fichier est tronqué est
recalculée ; chaque erreur est journalisée avec sa trace dans resultats/magasin/_journal/erreurs.log.
Codes de sortie : 0 terminé, 1 unités en erreur, 3 arrêt demandé (Ctrl+C). Pour une relance automatique
après plantage ou coupure : python superviseur.py [mêmes arguments].
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import importlib
import multiprocessing as mp
import os
import sys
import time
import traceback
from concurrent.futures.process import BrokenProcessPool

SORTIE_ERREUR, SORTIE_ARRET = 1, 3
ERREURS_SYSTEME = (MemoryError, OSError, BrokenProcessPool)      # relancées ; les autres erreurs sont déterministes

import etapes as E
import parametres as PARAM
import persistance as PE
from progression import Barre

ORDRE = ["calibrage", "validation", "illustrations", "chronometrage", "scenarios", "prix", "texte"]
MODULES = {"calibrage": "calibrage", "validation": "etape_validation", "illustrations": "etape_illustrations",
           "chronometrage": "etape_chronometrage", "scenarios": "scenarios", "prix": "etape_prix", "texte": "etape_texte"}
CONFIRMATOIRES = {"chronometrage", "scenarios", "prix", "texte", "illustrations", "validation"}


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
        faites = sum(PE.fichier_complet(mag.chemin(u.cle)) for u in us)
        print(f"{e:15s} : {faites:5d} / {len(us):5d} unités terminées")
    nc = PARAM.non_calibres()
    print("paramètres non calibrés :", ", ".join(nc) if nc else "aucun")


def _erreur_systeme(ex: BaseException) -> bool:
    """Erreur due à la machine (mémoire, disque, processus tué) plutôt qu'au calcul : une relance peut réussir."""
    return isinstance(ex, ERREURS_SYSTEME) or (isinstance(ex, RuntimeError) and "memory" in str(ex).lower())


def _journaliser_erreur(mag, cle: str, ex: BaseException, tentative: int):
    """Trace complète (y compris celle du processus de travail, transmise dans __cause__) dans _journal/erreurs.log."""
    f = mag.dossier.parent / "_journal" / "erreurs.log"
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "a", encoding="utf-8") as h:
        h.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')}  {mag.etape}  {cle}  tentative {tentative}\n")
        h.write("".join(traceback.format_exception(type(ex), ex, ex.__traceback__)))


def _travail_en_cours(mag, unites) -> str:
    """« 3 en cours, 57 ajustements » : ajustements intermédiaires déjà sauvegardés par les unités en cours (preuve
    que le calcul avance à l'intérieur d'une longue unité), puis la clé de la première unité en cours."""
    unites = list(unites)
    if not unites:
        return ""
    n = 0
    for u in unites:
        d = mag.dossier.joinpath(*[PE._nom_fichier(p) for p in u.cle.split("/")]) / "_sous"
        if d.exists():
            n += sum(1 for _ in d.rglob("*.pt"))
    return f"{len(unites)} en cours, {n} ajustements | {unites[0].cle}"


def _nouveau_pool(travailleurs: int) -> cf.ProcessPoolExecutor:
    return cf.ProcessPoolExecutor(max_workers=travailleurs, mp_context=mp.get_context("spawn"),
                                  initializer=PE.ignorer_interruption)


def executer_etape(etape: str, rapide: bool, travailleurs: int, tentatives: int = 3) -> bool:
    unites = unites_de(etape, rapide)
    mag = E.magasin(etape, rapide)
    if mag.nettoyer_temporaires():
        print(f"{etape} : fichiers temporaires d'une écriture interrompue supprimés.")
    restantes = [u for u in unites if not mag.complete(u.cle)]
    print(f"\n=== {etape} : {len(unites) - len(restantes)} / {len(unites)} unités déjà faites ; {len(restantes)} à calculer",
          flush=True)
    if etape == "chronometrage":
        travailleurs = 1
    erreurs = []
    if restantes:
        barre = Barre(len(restantes), etape)
        attente = list(restantes)
        echouees = set()
        essais = {}                              # clé -> nombre de lancements
        pool = _nouveau_pool(travailleurs)
        en_cours = {}
        try:
            while attente or en_cours:
                bloquees = [u for u in attente if any(d in echouees for d in u.depend)]
                for u in bloquees:
                    attente.remove(u)
                    echouees.add(u.cle)
                    erreurs.append((u.cle, "dépendance en erreur"))
                    barre.message(f"  ignorée (dépendance en erreur) : {u.cle}")
                pretes = [u for u in attente if all(mag.existe(d) for d in u.depend)]
                for u in pretes:
                    if PE.arret_demande():
                        break
                    attente.remove(u)
                    essais[u.cle] = essais.get(u.cle, 0) + 1
                    en_cours[pool.submit(E.executer_unite, u, rapide)] = u
                if not en_cours:
                    if attente and not PE.arret_demande():
                        erreurs.append(("?", "dépendances introuvables : " + ", ".join(u.cle for u in attente[:5])))
                    break
                # attente bornée : la barre est redessinée toutes les 5 s (temps écoulé, travail en cours) et le
                # battement prouve au superviseur que l'orchestrateur est vivant
                fini, _ = cf.wait(list(en_cours), timeout=5, return_when=cf.FIRST_COMPLETED)
                PE.battement(mag.dossier.parent, actif=True, etape=etape, faites=barre.n, total=barre.total,
                             en_cours=[u.cle for u in en_cours.values()])
                barre.rafraichir(_travail_en_cours(mag, en_cours.values()))
                pool_casse = False
                for fu in fini:
                    u = en_cours.pop(fu)
                    try:
                        fu.result()
                    except Exception as ex:
                        _journaliser_erreur(mag, u.cle, ex, essais[u.cle])
                        if _erreur_systeme(ex) and essais[u.cle] < tentatives:
                            pool_casse |= isinstance(ex, BrokenProcessPool)
                            attente.append(u)
                            barre.message(f"  relance {essais[u.cle]}/{tentatives - 1} de {u.cle} "
                                          f"({type(ex).__name__} : erreur système)")
                            continue
                        erreurs.append((u.cle, f"{type(ex).__name__}: {ex}"))
                        echouees.add(u.cle)
                        barre.message(f"  ERREUR {u.cle} : {type(ex).__name__}: {ex}")
                    barre.avancer(info=u.cle)
                if pool_casse:
                    # un processus est mort : toutes les unités en cours sont perdues pour ce pool ; on les remet
                    # en attente (sans compter une tentative de plus) et on recrée le pool
                    for fu, u in list(en_cours.items()):
                        attente.append(u)
                        essais[u.cle] -= 1
                    en_cours.clear()
                    pool.shutdown(wait=False, cancel_futures=True)
                    pool = _nouveau_pool(travailleurs)
                    barre.message("  processus de travail perdu : pool recréé, unités en cours relancées.")
                if PE.arret_demande() and not en_cours:
                    barre.message("  arrêt demandé : unités terminées enregistrées ; relancer la même commande pour reprendre.")
                    break
        except BaseException:
            # second Ctrl+C ou erreur imprévue de l'orchestrateur : sans cela, Python attendrait la fin des unités en
            # cours avant de quitter (plusieurs minutes, sans battement). On termine les processus de travail : leurs
            # ajustements et instantanés déjà écrits sont conservés, et le superviseur relance aussitôt.
            for p in list(getattr(pool, "_processes", {}).values()):
                try:
                    p.terminate()
                except Exception:
                    pass
            pool.shutdown(wait=False, cancel_futures=True)
            raise
        pool.shutdown(wait=True)
        PE.battement(mag.dossier.parent, actif=False, etape=etape)     # agrégation et figures : pas de battement
        barre.fermer()
    if erreurs:
        print(f"{etape} : {len(erreurs)} unité(s) en erreur ; relancer la commande pour les reprendre.")
        return False
    if PE.arret_demande():
        return False
    importlib.import_module(MODULES[etape]).agreger(rapide)
    print(f"{etape} : agrégation terminée.", flush=True)
    return True


def _verrouiller(rapide: bool):
    """
    Verrou exclusif sur le magasin (complet ou réduit) : une seconde commande de calcul sur le même magasin attend que
    la première se termine, puis relit les unités faites au lieu de les recalculer en double. Sans effet sous Windows.
    """
    try:
        import fcntl
    except ImportError:
        return None
    racine = E.racine_magasin(rapide)
    racine.mkdir(parents=True, exist_ok=True)
    f = open(racine / ".verrou", "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(f"Une autre commande calcule déjà dans {racine} : attente de sa fin.", flush=True)
        fcntl.flock(f, fcntl.LOCK_EX)
    return f


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("etapes", nargs="*", choices=ORDRE + [[]], default=[])
    ap.add_argument("--rapide", action="store_true")
    ap.add_argument("--travailleurs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--statut", action="store_true")
    ap.add_argument("--tables", action="store_true", help="agréger les tableaux depuis le magasin, sans calcul")
    ap.add_argument("--figures", action="store_true", help="produire les figures depuis le magasin, sans calcul")
    ap.add_argument("--autoriser-provisoire", action="store_true")
    ap.add_argument("--tentatives", type=int, default=3, help="lancements maximum d'une unité après une erreur système")
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
    verrou = _verrouiller(a.rapide)
    PE.installer_arret_propre()
    PE.desactiver_selection_console()
    with PE.empecher_veille():
        for e in choix:
            if e in CONFIRMATOIRES and not a.autoriser_provisoire:
                nc = PARAM.non_calibres()
                if nc:
                    print(f"Étape {e} refusée : paramètres non calibrés ({', '.join(nc)}). "
                          "Lancer d'abord  python run.py calibrage  (ou --autoriser-provisoire pour un essai).", file=sys.stderr)
                    sys.exit(2)
            if not executer_etape(e, a.rapide, a.travailleurs, a.tentatives):
                sys.exit(SORTIE_ARRET if PE.arret_demande() else SORTIE_ERREUR)
        if not a.etapes:
            importlib.import_module("figures").produire(a.rapide)


if __name__ == "__main__":
    main()
