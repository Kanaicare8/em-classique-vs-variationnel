"""
================================================================================
SUPERVISEUR : relance automatique de run.py après un arrêt NON voulu
================================================================================

  python -m emvb.superviseur [arguments de run.py]           ex. : python -m emvb.superviseur scenarios --travailleurs 6
  python -m emvb.superviseur --relances 20 --inactivite-max 90 -- --rapide --autoriser-provisoire

Lance run.py, attend sa fin et le relance tant qu'il ne s'est pas terminé normalement. Comme run.py
reprend exactement où il s'était arrêté (magasin, ajustements mémorisés, instantanés), une relance
ne recalcule rien. Codes de sortie de run.py :
  0  terminé                       -> fin
  2  configuration refusée         -> fin (paramètres non calibrés, argument invalide)
  3  arrêt demandé (Ctrl+C)        -> fin
  autre (1, plantage, processus tué, blocage)  -> relance après une pause croissante (30 s, 1 min, 2 min... 10 min)

Blocage : run.py écrit un battement toutes les 30 s (resultats/magasin*/_battement.json). Si le battement
s'arrête plus de 5 min, ou (option --inactivite-max, en minutes) si aucun fichier du magasin n'a été écrit
depuis ce délai alors que des unités sont en cours, l'arbre de processus est tué puis relancé. Les
instantanés étant écrits tous les 20 passages, choisir --inactivite-max nettement au-dessus de la durée
de 20 passages de l'ajustement le plus long.

Après une coupure de courant, le superviseur lui-même s'arrête : le relancer (ou l'inscrire dans le
planificateur de tâches de Windows, voir docs/LANCEMENT.md). Journal : resultats/magasin*/_journal/superviseur.log.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from emvb.chemins import RACINE
FIN = {0: "terminé", 2: "configuration refusée", 3: "arrêt demandé"}
BATTEMENT_MAX_S = 300


def _journal(dossier: Path, texte: str):
    ligne = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {texte}"
    print(f"[superviseur] {ligne}", flush=True)
    f = dossier / "_journal" / "superviseur.log"
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "a", encoding="utf-8") as h:
        h.write(ligne + "\n")


def _tuer_arbre(p: subprocess.Popen):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
    else:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            p.kill()


def _derniere_ecriture(dossier: Path) -> float:
    t = 0.0
    for p in dossier.rglob("*.pt"):
        try:
            t = max(t, p.stat().st_mtime)
        except OSError:
            pass
    return t


def _lire_battement(dossier: Path) -> dict | None:
    try:
        return json.loads((dossier / "_battement.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def superviser(args_run: list[str], relances: int, inactivite_max_min: float) -> int:
    dossier = RACINE / "resultats" / ("magasin_rapide" if "--rapide" in args_run else "magasin")
    arret = {"demande": False}

    def gestionnaire(signum, frame):
        arret["demande"] = True          # run.py reçoit le même Ctrl+C et s'arrête proprement (code 3)
    signal.signal(signal.SIGINT, gestionnaire)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, gestionnaire)

    cmd = [sys.executable, str(RACINE / "run.py"), *args_run]
    env = dict(os.environ, PYTHONUTF8="1")
    for essai in range(relances + 1):
        _journal(dossier, f"lancement {essai + 1}/{relances + 1} : {' '.join(cmd[1:])}")
        t0 = time.time()
        p = subprocess.Popen(cmd, cwd=RACINE, env=env, start_new_session=(os.name != "nt"))
        bloque = None
        while p.poll() is None:
            try:
                p.wait(timeout=60)
                break
            except subprocess.TimeoutExpired:
                pass
            if arret["demande"]:
                continue
            b = _lire_battement(dossier)
            maintenant = time.time()
            if b and b.get("pid") == p.pid and b.get("actif") and maintenant - b["t"] > BATTEMENT_MAX_S:
                bloque = f"battement arrêté depuis {int(maintenant - b['t'])} s"
            elif (inactivite_max_min > 0 and maintenant - t0 > 60 * inactivite_max_min and b and b.get("en_cours")
                  and maintenant - _derniere_ecriture(dossier) > 60 * inactivite_max_min):
                bloque = f"aucune écriture dans le magasin depuis {inactivite_max_min} min (en cours : {b['en_cours'][:3]})"
            if bloque:
                _journal(dossier, f"blocage détecté ({bloque}) : arrêt forcé de l'arbre de processus")
                _tuer_arbre(p)
                p.wait()
                break
        code = p.returncode
        if arret["demande"] or code in FIN:
            _journal(dossier, f"fin : code {code} ({FIN.get(code, 'arrêt demandé')})")
            return 0 if code == 0 else code
        if essai == relances:
            break
        pause = min(600, 30 * 2 ** essai)
        _journal(dossier, f"arrêt non voulu (code {code}{', ' + bloque if bloque else ''}) ; relance dans {pause} s")
        for _ in range(pause):
            if arret["demande"]:
                _journal(dossier, "arrêt demandé pendant la pause : pas de relance")
                return 3
            time.sleep(1)
    _journal(dossier, f"abandon après {relances} relances : voir _journal/erreurs.log")
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--relances", type=int, default=10, help="nombre maximum de relances (défaut 10)")
    ap.add_argument("--inactivite-max", type=float, default=0.0,
                    help="minutes sans écriture dans le magasin avant de considérer un calcul bloqué (0 = désactivé)")
    a, reste = ap.parse_known_args()
    if reste and reste[0] == "--":
        reste = reste[1:]
    sys.path.insert(0, str(RACINE))
    from emvb.persistance import desactiver_selection_console
    desactiver_selection_console()
    sys.exit(superviser(reste, a.relances, a.inactivite_max))


if __name__ == "__main__":
    main()
