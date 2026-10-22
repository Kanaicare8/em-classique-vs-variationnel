"""Profil rapide : où passe le temps dans em_classique / em_variationnel (jeu de référence, K = 6, 10 relances)."""
import cProfile
import pstats
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import torch

import algorithmes as A

X, _ = A.jeu_reference(42)
for nom, f in (("EM", lambda: A.em_classique(X, 6, n_init=10, graine=42)),
               ("VB", lambda: A.em_variationnel(X, 6, alpha0=1 / 6, n_init=10, graine=42))):
    t0 = time.perf_counter()
    pr = cProfile.Profile()
    pr.enable()
    r = f()
    pr.disable()
    print(f"== {nom} : {time.perf_counter() - t0:.2f} s, {r['n_iter']} itérations (meilleure relance)")
    pstats.Stats(pr).sort_stats("cumulative").print_stats(8)
print("threads torch :", torch.get_num_threads())
