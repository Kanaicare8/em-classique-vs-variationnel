"""
Vérifie que le calcul parallèle des sous-tâches du calibrage (etapes.sous_taches_paralleles) donne exactement les
valeurs du calcul séquentiel d'origine.

Les valeurs écrites dans le magasin par les processus de travail (relances du pilote n_init du texte, évaluations de la
recherche LDA) sont recalculées ici, une à une, dans le processus principal, avec la même fonction et la même graine
qu'auparavant, puis comparées bit à bit. Lecture seule : rien n'est écrit dans le magasin.

    python scripts/verifier_parallele.py [--rapide] [--n 3]
"""

import argparse
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapide", action="store_true", help="magasin de l'essai réduit")
    ap.add_argument("--n", type=int, default=3, help="valeurs vérifiées par famille de sous-tâches")
    ap.add_argument("--texte", type=int, default=0, metavar="R",
                    help="compare aussi, sur R relances, l'évaluation LDA d'origine (relances enchaînées) et celle "
                         "en deux temps (bornes par relance, puis réajustement de la meilleure)")
    a = ap.parse_args()
    if a.rapide:
        os.environ["ICARE_RAPIDE"] = "1"
    import torch
    torch.set_num_threads(1)                     # comme dans les processus de travail
    from emvb import calibrage as CA
    from emvb import etapes as E
    from emvb import parametres as PARAM

    mag = E.magasin("calibrage", a.rapide)
    esp = PARAM.valeur("espace_lda")
    alphas = {f"LDA-alpha={x}": x for x in (esp["alpha"][0], math.sqrt(esp["alpha"][0] * esp["alpha"][1]), esp["alpha"][1])}
    alphas["pLSA"] = None
    cas = []
    for nom, al in alphas.items():
        for s in range(a.n):
            cas.append((f"n_init/texte/_sous/{nom}/s={s}", lambda al=al, s=s: CA._relance_n_init_texte(a.rapide, al, s)))
    configs = CA._configs_texte(a.rapide)
    for i in range(min(a.n, len(configs))):
        cas.append((f"fin/texte/_sous/cfg={i}/tache=0", lambda i=i: {"v": CA._evaluer_texte(a.rapide, configs[i], 0)}))

    ok, vus = True, 0
    if a.texte:
        CA._n_init_texte = lambda rapide: a.texte                # mêmes graines 0..R-1 que les R premières relances
        cfg = configs[0]
        origine = CA._evaluer_texte(a.rapide, cfg, 0)
        bornes = [CA._borne_texte(a.rapide, cfg, 0, s)["b"] for s in range(a.texte)]
        deux_temps = CA._evaluer_texte(a.rapide, cfg, 0, bornes=bornes)
        egal = origine == deux_temps
        ok &= egal
        vus += 1
        print(f"{'IDENTIQUE' if egal else 'DIFFERENT'}  évaluation LDA cfg=0/tache=0 sur {a.texte} relances  "
              f"origine={origine}  deux temps={deux_temps}  (meilleure relance : {bornes.index(max(bornes))})", flush=True)
    for cle, recalcul in cas:
        if not mag.existe(cle):
            print(f"ABSENT     {cle} (pas encore calculé)", flush=True)
            continue
        stocke, nouveau = mag.lire(cle), recalcul()
        egal = stocke == nouveau
        ok &= egal
        vus += 1
        print(f"{'IDENTIQUE' if egal else 'DIFFERENT'}  {cle}  parallèle={stocke}  séquentiel={nouveau}", flush=True)
    if not vus:
        print("RIEN A VERIFIER : aucune sous-tâche encore écrite", flush=True)
        sys.exit(2)
    print(f"VERIFICATION {'REUSSIE' if ok else 'ECHOUEE'} ({vus} valeurs)", flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
