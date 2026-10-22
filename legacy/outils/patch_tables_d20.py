"""Ajoute le tableau climat_sous20 (D = 20) à tex_tables.py et l'inclut dans body.tex. À exécuter une fois."""
from pathlib import Path

R = Path(__file__).resolve().parent.parent
p = R / "tex_tables.py"
s = p.read_text(encoding="utf-8")
ajout = r'''

def climat_d20():
    d = lire("climat/sous_echantillons_D20.csv")
    if d is None:
        return
    d = d.assign(N=d.N.astype(str))
    lig = []
    for (N, bras), s in sorted(d.groupby(["N", "bras"]), key=lambda t: (int(t[0][0]), t[0][1])):
        ok = s[~s.echec.astype(bool)]
        lig.append([esc(N), esc(bras), num(float(ok.k_hat.mean()), 1) if len(ok) else "n/d",
                    num(float(ok["ARI_koppen"].mean()), 3) if len(ok) else "n/d",
                    num(100 * float(s.echec.astype(float).mean()), 0) + r"\,\%",
                    num(100 * float(s.apply(lambda r: True if bool(r.echec) else bool(r.degenere), axis=1).mean()), 0) + r"\,\%", str(len(s))])
    ecrire("climat_sous20", [r"$N$", "Bras", r"$\hat K$ moy.", "ARI Köppen", "Échecs numériques", "Dégénérés (échecs inclus)", "Rép."], lig,
           r"Cas climatique, extension à $D=20$ (19 variables bioclimatiques et l'altitude) : sous-échantillons espacés", "tab:climat_sous20",
           note=r"Un échec numérique (covariance non définie positive) est compté comme ajustement dégénéré ; moyennes calculées sur les ajustements qui ont abouti.")
'''
ancre = "\n\n# ------------------------------------------------------------------ S&P 500"
assert ancre in s
s = s.replace(ancre, ajout + ancre, 1)
s = s.replace("for f in (chap1, chap2, scenarios, grille_scenarios, climat, sp500, texte, grille):", "for f in (chap1, chap2, scenarios, grille_scenarios, climat, climat_d20, sp500, texte, grille):")
import ast
ast.parse(s)
p.write_text(s, encoding="utf-8")

b = R / "body.tex"
t = b.read_text(encoding="utf-8")
t = t.replace("\\tableauGenere{climat_semi}\n", "\\tableauGenere{climat_semi}\n\\tableauGenere{climat_sous20}\n", 1)
b.write_text(t, encoding="utf-8")
print("climat_sous20 ajouté")
