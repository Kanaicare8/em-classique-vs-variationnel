"""Rend cas_pratique_climat.py parallélisable par effectif (--effectifs, --partie) et corrige la comparaison des effectifs. À exécuter une fois."""
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "cas_pratique_climat.py"
s = p.read_text(encoding="utf-8")


def rep(old, new, n=1):
    global s
    assert s.count(old) >= 1, old[:60]
    s = s.replace(old, new, n)


rep("def sous_echantillons(X, km, blocs, refs, rapide, d19):",
    "def sous_echantillons(X, km, blocs, refs, rapide, d19, effectifs=None, R=None):")
rep("    R = 5 if rapide else 100\n    n_init = 3 if rapide else 10\n    dist_min = 15.0",
    "    R = R or (5 if rapide else 100)\n    n_init = 3 if rapide else 10\n    dist_min = 15.0")
rep('    for N in EFFECTIFS + ("complet",):\n        reps = 1 if N == "complet" else R',
    '    for N in (effectifs or EFFECTIFS + ("complet",)):\n        reps = 1 if N == "complet" else R')
rep("def semi_synthetique(X, rapide):", "def semi_synthetique(X, rapide, effectifs=None, R=None, B=None):")
rep("    R = 8 if rapide else 200\n    n_init = 3 if rapide else 10\n    ref = A.em_classique(X, K_REF",
    "    R = R or (8 if rapide else 200)\n    n_init = 3 if rapide else 10\n    ref = A.em_classique(X, K_REF")
rep("    for N in EFFECTIFS:\n        for r in range(R if N <= 500 else max(R // 4, 4)):",
    "    for N in (effectifs or EFFECTIFS):\n        for r in range(R if N <= 500 else max(R // 4, 4)):")
rep("                B = 20 if rapide else 100", "                B = B or (20 if rapide else 100)")
# comparaisons robustes sur N (après relecture CSV, N peut être une chaîne)
rep('    c = sous[(sous.N == "complet")]', '    sous = sous.assign(N=sous.N.astype(str))\n    semi = semi.assign(N=semi.N.astype(str))\n    c = sous[(sous.N == "complet")]')
rep("        s = sous[(sous.N == N) & (~sous.echec.astype(bool))]", "        s = sous[(sous.N == str(N)) & (~sous.echec.astype(bool))]")
rep("        s = sous[sous.N == N]", "        s = sous[sous.N == str(N)]")
rep("    s = semi[semi.N == 2000]", '    s = semi[semi.N == "2000"]')

# main : découpage en parties
a = s.index("def main():")
b = s.index('if __name__ == "__main__":')
nouveau = '''def fusion(d19=False):
    """Concatène les morceaux par effectif et calcule la grille des hypothèses avec la correction de Holm."""
    import glob
    sous = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(str(OUT / "sous_echantillons_D*_N*.csv")))], ignore_index=True)
    sous.to_csv(OUT / f"sous_echantillons_D{int(sous.D.iloc[0])}.csv", index=False)
    if d19:
        return
    semi = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(str(OUT / "semi_synthetique_N*.csv")))], ignore_index=True)
    couv = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(str(OUT / "couverture_N*.csv")))], ignore_index=True)
    semi.to_csv(OUT / "semi_synthetique.csv", index=False)
    couv.to_csv(OUT / "couverture.csv", index=False)
    dec = pd.read_csv(OUT / "decomposition_variance.csv")
    var = pd.read_csv(OUT / "variances_h5.csv").iloc[0]
    grille = pd.DataFrame(hypotheses(sous, semi, couv, float(var.var_vb), float(var.var_em)))
    grille["p_holm"], grille["rejet_holm"] = C.holm(grille["pvalue"].fillna(1.0).tolist())
    grille.to_csv(OUT / "grille_hypotheses_climat.csv", index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preparer", action="store_true")
    ap.add_argument("--rapide", action="store_true")
    ap.add_argument("--d19", action="store_true")
    ap.add_argument("--frontiere"); ap.add_argument("--koppen"); ap.add_argument("--zones")
    ap.add_argument("--partie", default="tout", choices=["tout", "sous", "semi", "sens", "cartes", "fusion"])
    ap.add_argument("--effectifs", default=None, help="liste séparée par des virgules, ex. 30,60,complet")
    ap.add_argument("--R", type=int, default=None, help="nombre de sous-échantillons par effectif (défaut 100)")
    ap.add_argument("--Rsemi", type=int, default=None, help="nombre de jeux semi-synthétiques par effectif (défaut 200)")
    ap.add_argument("--B", type=int, default=None, help="réplicats bootstrap de la couverture (défaut 100)")
    a = ap.parse_args()
    if a.preparer:
        preparer(); return
    OUT.mkdir(parents=True, exist_ok=True)
    if a.partie == "fusion":
        fusion(a.d19); return
    if not (DATA / "wc2.1_2.5m_elev.tif").exists():
        sys.exit("Données absentes : lancer d'abord  python cas_pratique_climat.py --preparer")
    X, km, refs, (lon, lat) = charger(a.d19, a.frontiere, a.koppen, a.zones)
    if not a.frontiere:
        print("AVERTISSEMENT : sans --frontiere l'emprise est rectangulaire (pays voisins inclus).")
    if refs["zones"] is None:
        print("Zones agro-écologiques absentes : la référence est Köppen-Geiger seul." if refs["koppen"] is not None
              else "Aucune référence fournie : ARI non calculé, seuls les critères sans étiquette sont rapportés.")
    X = standardiser(X)
    blocs = C.blocs_spatiaux(km, 100.0)
    print(f"N = {len(X)} cellules, D = {X.shape[1]}", flush=True)
    eff = None
    if a.effectifs:
        eff = tuple(e if e == "complet" else int(e) for e in a.effectifs.split(","))
    tag = "_".join(str(e) for e in eff) if eff else "tous"
    if a.partie in ("tout", "sous"):
        sous = sous_echantillons(X, km, blocs, refs, a.rapide, a.d19, eff, a.R)
        sous.to_csv(OUT / f"sous_echantillons_D{X.shape[1]}_N{tag}.csv", index=False)
    if not a.d19:
        if a.partie in ("tout", "semi"):
            eff_semi = tuple(e for e in eff if e != "complet") if eff else None
            if eff_semi is None or eff_semi:
                semi, couv, _ = semi_synthetique(X, a.rapide, eff_semi, a.Rsemi, a.B)
                semi.to_csv(OUT / f"semi_synthetique_N{tag}.csv", index=False)
                couv.to_csv(OUT / f"couverture_N{tag}.csv", index=False)
        if a.partie in ("tout", "sens"):
            plan, dec, vvb, vem = sensibilite_priors(X, a.rapide)
            plan.to_csv(OUT / "plan_factoriel.csv", index=False)
            pd.DataFrame([{"facteur": k, "part_variance": v} for k, v in dec.items()]).to_csv(OUT / "decomposition_variance.csv", index=False)
            pd.DataFrame([{"var_vb": vvb, "var_em": vem}]).to_csv(OUT / "variances_h5.csv", index=False)
        if a.partie in ("tout", "cartes"):
            cartes(X, lon, lat, refs, a.rapide)
    if a.partie == "tout":
        fusion(a.d19)


'''
s = s[:a] + nouveau + s[b:]
p.write_text(s, encoding="utf-8")
import ast
ast.parse(s)
print("cas_pratique_climat.py parallélisable")
