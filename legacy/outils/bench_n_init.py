"""
Benchmark du nombre d'initialisations : pour chaque cas, 200 relances indépendantes (en lot).
p = proportion des relances qui atteignent le meilleur optimum observé (écart relatif <= 1e-5).
n_init requis pour atteindre l'optimum avec probabilité 0,99 : ceil(ln 0,01 / ln(1 - p)).
Sorties : resultats/bench_n_init.csv.
"""
import csv
import math
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
import torch

import algorithmes as A

NB = 200
TOL_OPT = 1e-5


def cas():
    X, _ = A.jeu_reference(42)
    yield "synthétique N=300 D=2", X, (3, 6)
    lignes = list(csv.reader(open(R / "data" / "iris.csv", encoding="utf-8")))[1:]
    Xi = torch.tensor([[float(v) for v in l[:4]] for l in lignes])
    yield "Iris N=150 D=4", Xi, (3, 6)
    import cas_pratique as CP
    df = CP.charger_rendements()
    xr = torch.tensor(df[df.date <= CP.FIN_APPRENTISSAGE].r.values).reshape(-1, 1)
    yield "S&P 500 N=1318 D=1", xr, (4, 6)
    try:
        import cas_pratique_climat as CC
        d = R / "data" / "climat"
        Xc, _, _, _ = CC.charger(False, str(d / "frontiere" / "cameroun.shp"), None, None)
        Xc = CC.standardiser(Xc)
        idx = torch.randperm(len(Xc), generator=A.generateur(1))[:500]
        yield "climat N=500 D=5", Xc[idx], (5, 10)
    except Exception as e:
        print("climat indisponible :", e)


def n_requis(p):
    return 1 if p >= 0.99 else (math.inf if p == 0 else math.ceil(math.log(0.01) / math.log(1 - p)))


def mesurer(crits, N):
    c = torch.tensor([v for v in crits if v == v])
    meilleur = c.max()
    p = float(((meilleur - c).abs() <= TOL_OPT * meilleur.abs()).double().mean())
    ecart = (meilleur - c) / N                                    # écart au meilleur, en nat par observation
    p1 = float((ecart <= 1e-3).double().mean())
    p2 = float((ecart <= 1e-2).double().mean())
    return {"p_optimum": round(p, 3), "n_init_99pct": n_requis(p),
            "p_ecart_1e-3": round(p1, 3), "n_init_ecart_1e-3": n_requis(p1),
            "p_ecart_1e-2": round(p2, 3), "n_init_ecart_1e-2": n_requis(p2),
            "ecart_median_nat_obs": round(float(ecart.median()), 5), "ecart_max_nat_obs": round(float(ecart.max()), 4)}, len(c)


sortie = []
for nom, X, Ks in cas():
    for K in Ks:
        for algo in ("EM", "VB"):
            try:
                if algo == "EM":
                    r = A.em_classique(X, K, n_init=NB, graine=10_000)
                    crits = r["relances"]["loglik"]
                else:
                    r = A.em_variationnel(X, K, alpha0=1 / K, n_init=NB, graine=10_000)
                    crits = r["relances"]["critere"]
                mes, m = mesurer(crits, X.shape[0])
            except Exception as e:
                mes, m = {}, 0
                print(nom, K, algo, "échec", e)
            sortie.append({"cas": nom, "K": K, "algo": algo, "relances_valides": m, **mes})
            print(sortie[-1], flush=True)
with open(R / "resultats" / "bench_n_init.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(sortie[0]))
    w.writeheader()
    w.writerows(sortie)
