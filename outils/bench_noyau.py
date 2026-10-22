"""Compare le temps du noyau par lots à la référence séquentielle figée (médiane de 5 répétitions)."""
import importlib.util
import statistics
import sys
import time
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
import torch

import algorithmes as A

spec = importlib.util.spec_from_file_location("ref", R / "tests" / "algorithmes_reference.py")
REF = importlib.util.module_from_spec(spec)
sys.modules["ref"] = REF
spec.loader.exec_module(REF)


def mediane(f, n=5):
    t = []
    for _ in range(n):
        t0 = time.perf_counter()
        f()
        t.append(time.perf_counter() - t0)
    return statistics.median(t)


cas = [("N=300, D=2", A.jeu_reference(42)[0])]
g = A.generateur(0)
cas.append(("N=5000, D=5", torch.randn(5000, 5, generator=g) + torch.randint(0, 3, (5000, 1), generator=g) * 4.0))
for nom, X in cas:
    for lib, fa, fr in [
        ("EM K=6 n_init=10", lambda: A.em_classique(X, 6, n_init=10, graine=1), lambda: REF.em_classique(X, 6, n_init=10, graine=1)),
        ("VB K=6 n_init=10", lambda: A.em_variationnel(X, 6, alpha0=1 / 6, n_init=10, graine=1),
         lambda: REF.em_variationnel(X, 6, alpha0=1 / 6, n_init=10, graine=1)),
    ]:
        ta, tr = mediane(fa), mediane(fr)
        print(f"{nom:13s} {lib:18s} séquentiel {tr:7.3f} s   lots {ta:7.3f} s   gain x{tr / ta:5.1f}")
