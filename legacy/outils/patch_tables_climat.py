"""Ajoute à tex_tables.py les tableaux de synthèse du cas climatique (climat_sous, climat_semi). À exécuter une fois."""
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "tex_tables.py"
s = p.read_text(encoding="utf-8")
ajout = r'''    d = lire("climat/sous_echantillons_D5.csv")
    if d is not None:
        d = d.assign(N=d.N.astype(str))
        ordre = {"30": 0, "60": 1, "120": 2, "500": 3, "2000": 4, "complet": 5}
        lig = []
        for (N, bras), s in sorted(d.groupby(["N", "bras"]), key=lambda t: (ordre.get(t[0][0], 9), t[0][1])):
            ok = s[~s.echec.astype(bool)]
            ari = ok["ARI_koppen"].mean() if "ARI_koppen" in ok.columns else float("nan")
            lig.append([esc(N), esc(bras), num(float(ok.k_hat.mean()), 1), num(float(ari), 3), num(float(ok.loglik_plugin.median()), 2),
                        num(float(ok.loglik_predictive.median()), 2) if ok.loglik_predictive.notna().any() else "n/d",
                        num(100 * float(ok.degenere.astype(float).mean()), 0) + r"\,\%", num(float(ok.temps_s.median()), 2), str(len(s))])
        ecrire("climat_sous", [r"$N$", "Bras", r"$\hat K$ moy.", "ARI Köppen", "LL hors bloc (méd.)", "LL prédictive VB (méd.)", "Dégénérés", "Temps méd. (s)", "Rép."], lig,
               r"Cas climatique, sous-échantillons espacés ($D=5$, référence Köppen--Geiger seule) : moyennes sur les réplications", "tab:climat_sous",
               largeurs=[1.1, 1.8, 1.3, 1.6, 2.3, 2.3, 1.7, 1.7, 1.0],
               note=r"LL : log-vraisemblance moyenne par observation sur des blocs de 100 km sans point d'apprentissage ; $\hat K$ des bras MAP-EM et VB : composantes avec $N_k/N\geq1\,\%$. Une seule exécution à $N$ complet.")
    d = lire("climat/semi_synthetique.csv")
    if d is not None:
        d = d.assign(N=d.N.astype(str))
        lig = []
        for (N, bras), s in sorted(d.groupby(["N", "bras"]), key=lambda t: (int(t[0][0]), t[0][1])):
            lig.append([esc(N), esc(bras), num(float(s.k_hat.mean()), 2), num(float(s.erreur_k.mean()), 2), num(float(s.ARI.mean()), 3),
                        num(100 * float(s.degenere.astype(float).mean()), 0) + r"\,\%", str(len(s))])
        ecrire("climat_semi", [r"$N$", "Bras", r"$\hat K$ moy.", r"$\lvert\hat K-5\rvert$", "ARI vérité", "Dégénérés", "Jeux"], lig,
               r"Jeu semi-synthétique ($K_{\text{réf}}=5$, modèle ajusté à $N$ complet) : sélection de $K$ et qualité de partition", "tab:climat_semi")
'''
ancre = '''    d = lire("climat/sous_echantillons_D5.csv")
    if d is not None:
        lig = []
        for N, s in d.groupby("N", sort=False):'''
assert ancre in s
s = s.replace(ancre, ajout + ancre, 1)
import ast
ast.parse(s)
p.write_text(s, encoding="utf-8")
print("tableaux climat_sous et climat_semi ajoutés")
